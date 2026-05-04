# app3 稳定度审查（修补后第二遍）

> 目标：达到「可开始写业务（LLM 解析、工具调用、报告）」的基线。  
> 范围：[`llm-agent-lab/app3`](.) 已落盘代码，非 app2。

## 已关闭的设计问题（相对初版脚手架）

| 问题 | 处理 |
|------|------|
| 路由键 `fail` 与节点名 `handle_error` 不一致 | 统一为 `graph/constants` 的 `NodeName` / `RouteKey`；`add_conditional_edges` 的 `path_map` 与路由函数返回值一致 |
| `handle_error` 未接入 | 已注册；`act` → `RECOVERABLE` → `handle_error` → 条件边回 `plan` 或 `END` |
| `user_input` 与 `messages` 不同步 | `state/initial_state.build_initial_state` 同时写入 `HumanMessage` |
| `Settings` / `llm` 未注入 | `GraphContext` 持有 `settings`、`tools`、`llm`；节点用 `partial(..., ctx=ctx)` |
| 无 API key 时无法本地跑通 | `GraphSession` 捕获 `LLMConfigError` 得 `llm=None`；`parse_node` 写 `fatal_error` + `fatal_subtype`；`route_after_parse` → `END` |
| `last_tool_error` 单独触发恢复（易脏数据） | `route_after_act` 仅看 `error_class == recoverable`；`act_node` 成功/失败时需显式维护 `error_class` 与 `recoverable_subtype`（见 TODO） |
| `SkillDefinition` 不可实例化 | `to_structured_tool` 实现为 `StructuredTool.from_function` |

## 错误子系统（fatal / recoverable 子类型、分级重试、退避）

| 模块 | 说明 |
|------|------|
| [`app3/errors/taxonomy.py`](app3/errors/taxonomy.py) | `FatalSubtype`、`RecoverableSubtype`（`StrEnum`） |
| [`app3/errors/envelope.py`](app3/errors/envelope.py) | `ErrorEnvelope` 序列化 |
| [`app3/errors/classify.py`](app3/errors/classify.py) | `classify_exception`、`map_http_status` |
| [`app3/errors/policy.py`](app3/errors/policy.py) | 按 recoverable 子类型的 `MAX_RETRIES_*`、`compute_backoff_seconds`（指数 + 抖动 + cap） |
| [`app3/errors/state.py`](app3/errors/state.py) | `envelope_to_agent_patch` |
| [`app3/nodes/delay.py`](app3/nodes/delay.py) | 同步 `time.sleep`；环境变量 `APP3_BACKOFF_MAX_SECONDS` 再次 clamp |

**状态字段**：`fatal_subtype`、`recoverable_subtype`、`recovery_attempts`、`pending_sleep_seconds`、`last_error_envelope`。

**图**：`handle_error` → `route_after_handle_error` → `delay`（`pending_sleep_seconds > 0`）或 `plan`；用尽恢复次数时写入 `fatal_error` 与 `fatal_retries_exhausted` 并 `END`。

**阻塞说明**：`delay` 节点会阻塞当前线程；异步图可改为 `asyncio.sleep` 或外部队列调度。

## 仍建议在开发阶段补强的点（非阻塞）

1. **LLM 节点**：在 `except` 中调用 `classify_exception` + `envelope_to_agent_patch` 写入状态。
2. **`explain` 固定连 `END`**：若需要「解释不满意再打回 plan」，改为条件边。
3. **依赖版本锁**：生产可锁 `uv.lock` / `pip-tools`。
4. **工具安全**：GIS/HTTP 真实调用需超时、白名单、配额。

## 质量门

- `python -m unittest discover -s tests`：无 Key 路径、`policy`、`delay`、冒烟测试均通过。

达到以上即可认为 **可进入业务开发**。
