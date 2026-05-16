# app3 小样本评测报告（**端到端** LangGraph）

## 1. 运行元数据

- **评测模式**：`full`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。
- **生成时间**：2026-05-15T21:07:30.022681
- **金标文件**：`D:\Users\资料夹\智能体\llm-agent-lab\app3\data\eval_cases_210.jsonl`
- **主意图过滤**：`（未过滤）`
- **样本条数**：35
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

- **任务成功率 `success_rate`**：0.9429
- **意图准确率 `intent_acc`**：0.9143
- **槽位三项合取准确率 `slot_acc`**：0.9667
- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：1.0
- **时间单项 `time_range_acc`**：0.9667
- **对象单项 `target_object_acc`**：1.0
- **响应时间 p50（ms）**：23061.565
- **响应时间 p90（ms）**：48675.904

## 4. 分意图统计（按 `gold.primary_intent`）

| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |
|----------|-----:|-----------:|-------------------------:|
| `change_detection` | 5 | 0.6 | 0.8 |
| `compliance_check` | 5 | 1.0 | 1.0 |
| `current_status_estimate` | 5 | 1.0 | 1.0 |
| `multi_region_compare` | 5 | 1.0 | 1.0 |
| `other` | 5 | 0.8 | — |
| `transfer_analysis` | 5 | 1.0 | 1.0 |
| `trend_evolution` | 5 | 1.0 | 1.0 |

## 5. 逐条结果（总表）

| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |
|-----------|------------:|--------------|--------------|---------|------|--------|-------|
| eval210_cse_001 | 23740.38 | True | True | True | True | True | explain |
| eval210_cse_002 | 19007.274 | True | True | True | True | True | explain |
| eval210_cse_003 | 23061.565 | True | True | True | True | True | explain |
| eval210_cse_004 | 27617.402 | True | True | True | True | True | explain |
| eval210_cse_005 | 20996.3 | True | True | True | True | True | explain |
| eval210_cd_001 | 57492.259 | True | False | True | True | True | explain |
| eval210_cd_002 | 17231.648 | True | True | True | True | True | explain |
| eval210_cd_003 | 28907.573 | True | True | True | False | True | explain |
| eval210_cd_004 | 29598.881 | True | False | True | True | True | explain |
| eval210_cd_005 | 21594.633 | True | True | True | True | True | explain |
| eval210_te_001 | 43602.074 | True | True | True | True | True | explain |
| eval210_te_002 | 42390.666 | True | True | True | True | True | explain |
| eval210_te_003 | 43659.606 | True | True | True | True | True | explain |
| eval210_te_004 | 51778.321 | True | True | True | True | True | explain |
| eval210_te_005 | 115283.849 | True | True | True | True | True | explain |
| eval210_cc_001 | 22845.67 | True | True | True | True | True | explain |
| eval210_cc_002 | 23900.815 | True | True | True | True | True | explain |
| eval210_cc_003 | 17146.576 | True | True | True | True | True | explain |
| eval210_cc_004 | 79854.673 | True | True | True | True | True | explain |
| eval210_cc_005 | 31070.937 | True | True | True | True | True | explain |
| eval210_mr_001 | 16521.583 | True | True | True | True | True | explain |
| eval210_mr_002 | 15865.687 | True | True | True | True | True | explain |
| eval210_mr_003 | 22375.491 | True | True | True | True | True | explain |
| eval210_mr_004 | 16886.932 | True | True | True | True | True | explain |
| eval210_mr_005 | 10760.465 | True | True | True | True | True | explain |
| eval210_tf_001 | 29497.682 | True | True | True | True | True | explain |
| eval210_tf_002 | 44022.279 | True | True | True | True | True | explain |
| eval210_tf_003 | 13917.396 | False | True | True | True | True | explain |
| eval210_tf_004 | 38448.799 | False | True | True | True | True | explain |
| eval210_tf_005 | 39391.05 | True | True | True | True | True | explain |
| eval210_ot_001 | 9467.912 | True | True | None | None | None | explain |
| eval210_ot_002 | 2471.708 | True | True | None | None | None | explain |
| eval210_ot_003 | 3200.29 | True | True | None | None | None | explain |
| eval210_ot_004 | 3768.557 | True | False | None | None | None | explain |
| eval210_ot_005 | 2484.801 | True | True | None | None | None | explain |

## 6. 未通过 `task_success` 的样本

- **`eval210_tf_003`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": true}
- **`eval210_tf_004`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": true}

## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval210_cd_003` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河北省保定市容城县']` / `['2020', '2021', '2022', '2023', '2024']` | `['河北省保定市容城县']` / `['2020', '2024']` |
| `eval210_tf_003` | False | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": true} | `['安徽省合肥市']` / `['2022']` | `['安徽省合肥市']` / `['2022']` |
| `eval210_tf_004` | False | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": true} | `['江西省南昌市']` / `['2023']` | `['江西省南昌市']` / `['2023']` |
| `eval210_ot_001` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_002` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_003` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_004` | True | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_005` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |

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

