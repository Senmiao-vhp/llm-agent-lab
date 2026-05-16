# app3 小样本评测报告（仅 **parse** 节点）

## 1. 运行元数据

- **评测模式**：`parse`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。
- **生成时间**：2026-05-16T12:07:26.114659
- **金标文件**：`D:\Users\资料夹\智能体\llm-agent-lab\app3\data\eval_cases_210.jsonl`
- **主意图过滤**：`current_status_estimate`
- **样本条数**：5
- **GIS 任务磁盘缓存**：评测过程已强制 **`gis_use_cache=false`**（等价环境变量 `APP3_GIS_USE_CACHE=false`）。
- **完全冷启动（子进程）**：否（单进程；进程内边界/解压内存缓存仍可能存在）。

## 2. 指标与 app3 状态字段对应

| 论文/实验表述 | app3 取值来源 | 本报告计算方式 |
|----------------|----------------|----------------|
| 解析阶段响应时间 | 仅 `parse_node` 墙钟 | 单条 `duration_ms` 的 p50 / p90 |
| 解析任务成功率（技术） | `parse_result` 与 fatal | `task_success`：无 fatal 且 `queries` 非空 |
| 意图 / 空间语义（主观对齐） | `parse_result.queries[0]` vs `gold` | 与全链路相同：`intent_match`、槽位三项严格相等 |

> **注意**：`parse` 模式 **不执行** plan / act / explain，故不涉及 `gis_context`、`skip_gis`、GIS 流水线。

## 3. 总体结果

- **任务成功率 `success_rate`**：1.0（此处为「解析成功」占比，非端到端 GIS）
- **意图准确率 `intent_acc`**：0.6
- **槽位三项合取准确率 `slot_acc`**：0.2
- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：1.0
- **时间单项 `time_range_acc`**：0.2
- **对象单项 `target_object_acc`**：1.0
- **响应时间 p50（ms）**：3890.284
- **响应时间 p90（ms）**：5133.75

## 4. 分意图统计（按 `gold.primary_intent`）

| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |
|----------|-----:|-----------:|-------------------------:|
| `change_detection` | 5 | 0.6 | 0.2 |

## 5. 逐条结果（总表）

| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |
|-----------|------------:|--------------|--------------|---------|------|--------|-------|
| eval210_cd_003 | 5879.723 | True | True | True | False | True | parse |
| eval210_cd_008 | 4014.79 | True | False | True | False | True | parse |
| eval210_cd_021 | 3890.284 | True | True | True | False | True | parse |
| eval210_cd_024 | 3095.474 | True | True | True | True | True | parse |
| eval210_cd_030 | 3139.392 | True | False | True | False | True | parse |

## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval210_cd_003` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河北省保定市容城县']` / `['2020', '2021', '2022', '2023', '2024']` | `['河北省保定市容城县']` / `['2020', '2024']` |
| `eval210_cd_008` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2021', '2022', '2023']` | `['河南省郑州市']` / `['2020', '2023']` |
| `eval210_cd_021` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['江苏省苏州市']` / `['2020', '2021', '2022', '2023', '2024', '2025']` | `['江苏省苏州市']` / `['2020', '2025']` |
| `eval210_cd_030` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['江西省南昌市']` / `['2020', '2021', '2022', '2024', '2025']` | `['江西省南昌市']` / `['2020', '2022', '2024', '2025']` |

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

