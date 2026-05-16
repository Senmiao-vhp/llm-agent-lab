# app3 小样本评测报告（**端到端** LangGraph）

## 1. 运行元数据

- **评测模式**：`full`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。
- **生成时间**：2026-05-16T12:00:30.870961
- **金标文件**：`D:\Users\资料夹\智能体\llm-agent-lab\app3\data\eval_runs\eval_pipeline_retry_cd_008.jsonl`
- **主意图过滤**：`（未过滤）`
- **样本条数**：1
- **GIS 任务磁盘缓存**：评测过程已强制 **`gis_use_cache=false`**（等价环境变量 `APP3_GIS_USE_CACHE=false`）。
- **完全冷启动（子进程）**：否（单进程；进程内边界/解压内存缓存仍可能存在）。

## 2. 指标与 app3 状态字段对应

| 论文/实验表述 | app3 取值来源 | 本报告计算方式 |
|----------------|----------------|----------------|
| 系统响应时间（端到端） | `GraphSession.invoke` 墙钟 | 单条 `duration_ms` 的 p50 / p90 |
| 分析任务执行成功率 | 最终 `phase`、`fatal_error`、`error_class`、`plan_result.skip_gis`、`gis_context.pipeline` | `task_success`：到达 `phase=explain` 且无 fatal；若未 `skip_gis` 则要求 `gis_context.pipeline.success==true` |
| 意图识别是否准确 | `parse_result.queries[0].intent` vs `gold.primary_intent` | `intent_match`（默认要求单条子查询） |
| 空间语义：行政区 / 时间 / 对象 | 同上首条 `regions`、`time_range`、`target_object` | 与金标 **列表严格字符串相等** |

> 说明：行政区金标为全称时，解析若返回简称会导致 `regions_match=false`，可在附录中人工复核。

## 3. 总体结果

- **任务成功率 `success_rate`**：1.0
- **意图准确率 `intent_acc`**：1.0
- **槽位三项合取准确率 `slot_acc`**：0.0
- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：1.0
- **时间单项 `time_range_acc`**：0.0
- **对象单项 `target_object_acc`**：1.0
- **响应时间 p50（ms）**：34836.21
- **响应时间 p90（ms）**：34836.21

## 4. 分意图统计（按 `gold.primary_intent`）

| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |
|----------|-----:|-----------:|-------------------------:|
| `change_detection` | 1 | 1.0 | 0.0 |

## 5. 逐条结果（总表）

| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |
|-----------|------------:|--------------|--------------|---------|------|--------|-------|
| eval210_cd_008 | 34836.21 | True | True | True | False | True | explain |

## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval210_cd_008` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2021', '2022', '2023']` | `['河南省郑州市']` / `['2020', '2023']` |

## 8. 复现实验命令

```bash
cd <llm-agent-lab/app3>   # 含 pyproject.toml 的目录
pip install -e ".[gis]"   # 仅端到端全图时需要；只测 parse 可不装 gis
# 端到端（invoke 全图）：
app3-eval-paper6 --cases <path/to/cases.jsonl> --max-cases 30 \
  --primary-intent current_status_estimate
# 只测 parse 节点：
app3-eval-paper6 --cases <path/to/cases.jsonl> --max-cases 30 --parse-only
# 完全冷启动（每条子进程）：
# app3-eval-paper6 ... --cold-subprocess
```

## 9. 组件级分项耗时（二期）

若需解析/规划/GIS 分项毫秒表：可在后续版本使用 LangGraph `stream_events`，或对 `parse_composite_query` / `build_plan_result_from_parse_dict` / 工具执行分别微基准。

