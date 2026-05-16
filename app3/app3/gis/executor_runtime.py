from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Dict, List, Optional

from app3.gis.executor_cache import FileCache
from app3.gis.executor_models import ExecutionMetrics, ExecutionResult, ExecutorConfig
from app3.gis.gee_client import GeeClient, GeeConfig
from app3.gis.operators import GisOperators


logger = logging.getLogger(__name__)


class WorkflowExecutor:
    """
    GIS 工作流运行时：DAG 调度 + 算子注册表 + 幂等缓存 + 子计划并发。

    该类承载执行细节；对外智能体门面见 `executor.py` 中的 `ExecutorAgent`。
    """

    def __init__(self, cfg: ExecutorConfig):
        self.cfg = cfg
        self.metrics = ExecutionMetrics(start_time=time.time())
        self.context: Dict[str, Any] = {}  # 全局任务上下文：{taskId: 执行结果}
        self.cache = FileCache(cfg.cache_dir) if cfg.use_cache else None
        gee = GeeClient(GeeConfig(project_id=cfg.gee_project_id))
        self.ops = GisOperators(gee, cfg)

        self.registry = {
            "resolve_geometry": self.ops.resolve_geometry,
            "load_globeland30": self.ops.load_globeland30,
            "search_satellite": self.ops.search_satellite,
            "calculate_ndvi": self.ops.calculate_ndvi,
            "detect_change": self.ops.detect_change,
            "area_stats": self.ops.area_stats,
            "calculate_holdings": self.ops.calculate_holdings,
            "trend_cropland_loss": self.ops.trend_cropland_loss,
            "compliance_check_point": self.ops.compliance_check_point,
            "region_compare_baseline": self.ops.region_compare_baseline,
            "land_transfer_after_loss": self.ops.land_transfer_after_loss,
        }

    def execute(
        self,
        dsl: Dict[str, Any],
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> ExecutionResult:
        """
        主入口：执行 Planner 输出的 DSL 工作流。

        执行策略：
        1. OTHER意图空任务 -> 直接返回 no_op
        2. 多子计划 + 开并发 -> 分组并行执行
        3. 否则 -> 按拓扑顺序串行
        任何异常都返回标准化 ExecutionResult。
        """
        self.metrics = ExecutionMetrics(start_time=time.time())
        self.context = {}

        tasks: List[Dict[str, Any]] = dsl.get("tasks") or []
        if not tasks:
            self.metrics.end_time = time.time()
            return ExecutionResult(
                success=True,
                message="No executable GIS tasks for this intent.",
                data={"final_output": {"type": "no_op", "note": "No GIS execution required."}, "context": {}},
                metrics=self.metrics,
            )

        # 多意图并发优化
        meta = dsl.get("metadata") or {}
        subplans = meta.get("subplans") if isinstance(meta, dict) else None
        if (
            isinstance(subplans, list)
            and len(subplans) >= 2
            and self.cfg.executor_parallel
        ):
            try:
                return self._execute_subplans_parallel(tasks, subplans, on_progress=on_progress)
            except Exception as e:  # noqa: BLE001
                # 降级
                logger.warning("Parallel execution failed, fallback to sequential: %s", e)

        total = len(tasks)
        for idx, task in enumerate(tasks, start=1):
            task_id = task["id"]
            op = task["op"]
            params = task.get("params", {}) or {}
            inputs_ref = task.get("inputs", []) or []

            if on_progress:
                on_progress((idx - 1) / total * 100.0, f"Running {task_id} ({op})")

            t0 = time.perf_counter()
            try:
                # 第一步：解析 $geom.output 这种依赖引用
                resolved_inputs = self._resolve_inputs(inputs_ref)
                # 第二步：输入格式校验
                self._validate_task_io(op, params, resolved_inputs)
                # 第三步：查缓存
                if self.cache:
                    cached = self.cache.get(op, params, resolved_inputs)
                    if cached is not None:
                        self.context[task_id] = cached
                        self.metrics.task_durations[task_id] = 0.0
                        self.metrics.task_durations_ms[task_id] = 0
                        continue

                # 第四步：注册表查算子，执行
                fn = self.registry.get(op)
                if not fn:
                    raise NotImplementedError(f"Operator not implemented in app3 executor: {op}")

                result = fn(params, resolved_inputs)
                # 第五步：输出格式校验
                self._validate_operator_output(op, result)
                self.context[task_id] = result
                # 第六步：写入缓存
                if self.cache:
                    self.cache.set(op, params, resolved_inputs, result)

                elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
                self.metrics.task_durations_ms[task_id] = elapsed_ms
                self.metrics.task_durations[task_id] = round(elapsed_ms / 1000.0, 3)
            except Exception as e:
                # 防御式编程：任何任务失败，都返回标准化错误，不崩溃
                self.metrics.end_time = time.time()
                return ExecutionResult(
                    success=False,
                    message=f"Task failed: {task_id} ({op}): {e}",
                    data={"failed_task": task_id, "op": op, "context": self._clean_context()},
                    metrics=self.metrics,
                )

        self.metrics.end_time = time.time()
        final_id = tasks[-1]["id"]
        if on_progress:
            on_progress(100.0, "Done")
        return ExecutionResult(
            success=True,
            message="Workflow executed successfully.",
            data={"final_output": self._clean_value(self.context.get(final_id)), "context": self._clean_context()},
            metrics=self.metrics,
        )

    def _execute_subplans_parallel(
        self,
        tasks: List[Dict[str, Any]],
        subplans: List[Dict[str, Any]],
        *,
        on_progress: Optional[Callable[[float, str], None]] = None,
    ) -> ExecutionResult:
        """
        多意图并发执行：按 q1_/q2_/q3_ 前缀分组线程池执行。

        组内串行，组间并行。
        """
        prefixes: List[str] = []
        for sp in subplans:
            if not isinstance(sp, dict):
                continue
            pfx = sp.get("task_prefix")
            if isinstance(pfx, str) and pfx:
                prefixes.append(pfx)
        prefixes = list(dict.fromkeys(prefixes))
        if len(prefixes) < 2:
            raise ValueError("subplans missing task_prefix; cannot parallelize.")

        # 第一步：任务按前缀分组 q1_xxx, q2_xxx
        groups: Dict[str, List[Dict[str, Any]]] = {p: [] for p in prefixes}
        for t in tasks:
            tid = str(t.get("id") or "")
            for p in prefixes:
                if tid.startswith(p):
                    groups[p].append(t)
                    break

        total_groups = sum(1 for p in prefixes if groups.get(p))
        if total_groups < 2:
            raise ValueError("insufficient task groups for parallel execution.")

        # 第二步：每个组独立的执行函数，拥有独立的上下文
        # 这样就不会互相污染依赖引用
        def _run_group(pfx: str, tlist: List[Dict[str, Any]]) -> Dict[str, Any]:
            ctx: Dict[str, Any] = {}  # 独立上下文
            durations: Dict[str, float] = {}
            durations_ms: Dict[str, int] = {}
            for task in tlist:
                task_id = task["id"]
                op = task["op"]
                params = task.get("params", {}) or {}
                inputs_ref = task.get("inputs", []) or []
                t0 = time.perf_counter()
                resolved_inputs = self._resolve_inputs_in(ctx, inputs_ref)
                self._validate_task_io(op, params, resolved_inputs)
                if self.cache:
                    cached = self.cache.get(op, params, resolved_inputs)
                    if cached is not None:
                        ctx[task_id] = cached
                        durations[task_id] = 0.0
                        durations_ms[task_id] = 0
                        continue
                fn = self.registry.get(op)
                if not fn:
                    raise NotImplementedError(f"Operator not implemented in app3 executor: {op}")
                result = fn(params, resolved_inputs)
                self._validate_operator_output(op, result)
                ctx[task_id] = result
                if self.cache:
                    self.cache.set(op, params, resolved_inputs, result)
                elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
                durations_ms[task_id] = elapsed_ms
                durations[task_id] = round(elapsed_ms / 1000.0, 3)
            return {"prefix": pfx, "context": ctx, "durations": durations, "durations_ms": durations_ms}

        max_workers = self.cfg.executor_parallel_workers if self.cfg.executor_parallel_workers is not None else min(4, total_groups)
        done_groups = 0
        try:
            # 第三步：线程池并发执行，最多4个worker
            with ThreadPoolExecutor(max_workers=max_workers) as ex:
                futs = []
                for pfx in prefixes:
                    tlist = groups.get(pfx) or []
                    if not tlist:
                        continue
                    futs.append(ex.submit(_run_group, pfx, tlist))
                # 哪个组先跑完就先合并哪个
                for fut in as_completed(futs):
                    pack = fut.result()
                    gctx = pack["context"]
                    gdur = pack["durations"]
                    gdur_ms = pack.get("durations_ms") or {}
                    # 第四步：所有组执行完合并回全局上下文
                    self.context.update(gctx)
                    self.metrics.task_durations.update(gdur)
                    self.metrics.task_durations_ms.update(gdur_ms)
                    done_groups += 1
                    if on_progress:
                        on_progress(done_groups / max(1, len(futs)) * 100.0, f"Subplan {pack['prefix']} done")
        except Exception as e:
            self.metrics.end_time = time.time()
            return ExecutionResult(
                success=False,
                message=f"Task failed (parallel subplans): {e}",
                data={"failed_task": "<parallel_subplan>", "op": "<parallel>", "context": self._clean_context()},
                metrics=self.metrics,
            )

        self.metrics.end_time = time.time()
        final_id = tasks[-1]["id"]
        if on_progress:
            on_progress(100.0, "Done")
        return ExecutionResult(
            success=True,
            message="Workflow executed successfully (parallel subplans).",
            data={"final_output": self._clean_value(self.context.get(final_id)), "context": self._clean_context()},
            metrics=self.metrics,
        )

    def _resolve_inputs(self, inputs: List[str]) -> Any:
        """
        解析声明式依赖：["$geom.output", "$sat.output"] -> [真实结果1, 真实结果2]。

        单输入直接返回，多输入返回列表。
        """
        if not inputs:
            return []
        if len(inputs) == 1:
            return self._resolve_ref(inputs[0])
        return [self._resolve_ref(i) for i in inputs]

    def _resolve_inputs_in(self, ctx: Dict[str, Any], inputs: List[str]) -> Any:
        """并发场景专用：从指定上下文解析依赖（而不是全局 self.context）。"""
        if not inputs:
            return []
        if len(inputs) == 1:
            return self._resolve_ref_in(ctx, inputs[0])
        return [self._resolve_ref_in(ctx, i) for i in inputs]

    def _resolve_ref_in(self, ctx: Dict[str, Any], ref: str) -> Any:
        """
        DSL 依赖解析核心：把字符串引用 "$taskId.output" 变成真实执行结果。

        用在并发分组场景，每个组有独立的上下文。
        """
        if not (isinstance(ref, str) and ref.startswith("$") and ref.endswith(".output")):
            raise ValueError(f"Invalid input reference: {ref}")
        task_id = ref[1 : -len(".output")]
        if task_id not in ctx:
            raise ValueError(f"Missing dependency output: {task_id}")
        return ctx[task_id]

    def _resolve_ref(self, ref: str) -> Any:
        """DSL 依赖解析核心：把字符串引用 "$taskId.output" 变成真实执行结果。"""
        if not (isinstance(ref, str) and ref.startswith("$") and ref.endswith(".output")):
            raise ValueError(f"Invalid input reference: {ref}")
        task_id = ref[1 : -len(".output")]
        if task_id not in self.context:
            raise ValueError(f"Missing dependency output: {task_id}")
        return self.context[task_id]

    def _validate_task_io(self, op: str, params: Dict[str, Any], resolved_inputs: Any) -> None:
        """算子输入校验。"""
        if not isinstance(params, dict):
            raise TypeError(f"Task params must be dict (op={op}).")
        # 特殊算子必须传入单个字典
        if op in ("area_stats_worldcover_cropland",):
            if not isinstance(resolved_inputs, dict):
                raise TypeError(f"{op} expects a single dict input.")

    def _validate_operator_output(self, op: str, result: Any) -> None:
        """
        算子输出校验契约：所有算子必须返回带 type 字段的字典。

        下游报表生成器靠 type 字段判断用什么模板渲染。
        """
        if not isinstance(result, dict) or "type" not in result:
            raise TypeError(f"Operator output must be a dict with `type` (op={op}).")

    def _slim_for_response(self, v: Any) -> Any:
        """
        - GeoJSON 直接略去，用占位符代替
        - numpy 数组只保留形状和类型
        """
        try:
            import numpy as np  # type: ignore
        except Exception:  # pragma: no cover
            np = None  # type: ignore

        if np is not None and isinstance(v, np.ndarray):
            return f"<ndarray shape={v.shape} dtype={v.dtype}>"
        if isinstance(v, dict):
            d = v
            out: Dict[str, Any] = {}
            for k, vv in d.items():
                if k in ("geometry_geojson", "boundary_geojson"):
                    out[k] = "<geojson omitted>"
                elif k == "change_geojson":
                    if d.get("change_geojson_path"):
                        out[k] = "<omitted: see change_geojson_path>"
                    else:
                        out[k] = "<omitted: feature collection>"
                else:
                    out[k] = self._slim_for_response(vv)
            return out
        if isinstance(v, list):
            return [self._slim_for_response(i) for i in v]
        return v

    def _clean_context(self) -> Dict[str, Any]:
        """全局上下文压缩：所有任务结果都 slim 一遍再返回前端。"""
        out: Dict[str, Any] = {}
        for k, v in self.context.items():
            out[k] = self._slim_for_response(v)
        return out

    def _clean_value(self, v: Any) -> Any:
        """最终结果压缩：和上下文用同一个压缩规则。"""
        return self._slim_for_response(v)
