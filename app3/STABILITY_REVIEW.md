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
| 无 API key 时无法本地跑通 | `GraphSession` 捕获 `LLMConfigError` 得 `llm=None`；`parse_node` 写 `fatal_error`；`route_after_parse` → `END` |
| `last_tool_error` 单独触发恢复（易脏数据） | `route_after_act` 仅看 `error_class == recoverable`；`act_node` 负责在成功/失败时成对更新字段（见 TODO） |
| `SkillDefinition` 不可实例化 | `to_structured_tool` 实现为 `StructuredTool.from_function` |

## 仍建议在开发阶段补强的点（非阻塞）

1. **LLM 节点实现时**：`plan` / `explain` 若需调用 `ctx.llm`，需与 `parse` 一致处理 `ctx.llm is None`（当前图中若 `fatal_error` 已从 parse 终止则不会进入后续节点）。
2. **`handle_error` 与 `retry_count` 语义**：每次进入 `handle_error` 都会 `+1`；`route_after_error` 在 `retry_count >= max_retries` 时结束。若你希望「重试次数」只统计工具失败而非解析失败，可后续拆分计数器。
3. **`explain` 固定连 `END`**：若将来需要「解释不满意再打回 plan」，需改成条件边。
4. **`langgraph` / `langchain-core` 版本**：`pyproject` 使用下界版本；生产/复现可再锁 `uv.lock` / `pip-tools`。
5. **安全**：真实 GIS/HTTP 工具需加超时、白名单、配额；本框架未内建。

## 质量门

- `python -m unittest discover -s tests`：无 `OPENAI_API_KEY` 时 `invoke` 以 `fatal_error` 结束；`build_compiled_graph` 在 `llm=None` 下可编译。

达到以上即可认为 **可进入业务开发**。
