# app3 小样本评测报告（**端到端** LangGraph）

## 1. 运行元数据

- **评测模式**：`full`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。
- **生成时间**：2026-05-15T20:40:02.733146
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

- **任务成功率 `success_rate`**：0.2
- **意图准确率 `intent_acc`**：0.2
- **槽位三项合取准确率 `slot_acc`**：0.2667
- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：0.3
- **时间单项 `time_range_acc`**：0.2667
- **对象单项 `target_object_acc`**：0.3
- **响应时间 p50（ms）**：16339.462
- **响应时间 p90（ms）**：24513.44

## 4. 分意图统计（按 `gold.primary_intent`）

| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |
|----------|-----:|-----------:|-------------------------:|
| `change_detection` | 5 | 0.4 | 0.6 |
| `compliance_check` | 5 | 0.0 | 0.0 |
| `current_status_estimate` | 5 | 1.0 | 1.0 |
| `multi_region_compare` | 5 | 0.0 | 0.0 |
| `other` | 5 | 0.0 | — |
| `transfer_analysis` | 5 | 0.0 | 0.0 |
| `trend_evolution` | 5 | 0.0 | 0.0 |

## 5. 逐条结果（总表）

| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |
|-----------|------------:|--------------|--------------|---------|------|--------|-------|
| eval210_cse_001 | 20083.409 | True | True | True | True | True | explain |
| eval210_cse_002 | 11706.327 | False | True | True | True | True | explain |
| eval210_cse_003 | 27466.794 | True | True | True | True | True | explain |
| eval210_cse_004 | 36792.453 | True | True | True | True | True | explain |
| eval210_cse_005 | 20035.144 | True | True | True | True | True | explain |
| eval210_cd_001 | 100879.051 | True | False | True | True | True | explain |
| eval210_cd_002 | 16509.198 | True | True | True | True | True | explain |
| eval210_cd_003 | 19066.855 | True | True | True | False | True | explain |
| eval210_cd_004 | 152679.812 | False | False | True | True | True | explain |
| eval210_cd_005 | 16339.462 | False | False | False | False | False | plan |
| eval210_te_001 | 16157.85 | False | False | False | False | False | plan |
| eval210_te_002 | 16260.83 | False | False | False | False | False | plan |
| eval210_te_003 | 16472.758 | False | False | False | False | False | plan |
| eval210_te_004 | 16473.331 | False | False | False | False | False | plan |
| eval210_te_005 | 16261.416 | False | False | False | False | False | plan |
| eval210_cc_001 | 16193.812 | False | False | False | False | False | plan |
| eval210_cc_002 | 16388.241 | False | False | False | False | False | plan |
| eval210_cc_003 | 16278.898 | False | False | False | False | False | plan |
| eval210_cc_004 | 16358.719 | False | False | False | False | False | plan |
| eval210_cc_005 | 16332.97 | False | False | False | False | False | plan |
| eval210_mr_001 | 16297.451 | False | False | False | False | False | plan |
| eval210_mr_002 | 16376.565 | False | False | False | False | False | plan |
| eval210_mr_003 | 16235.766 | False | False | False | False | False | plan |
| eval210_mr_004 | 16266.976 | False | False | False | False | False | plan |
| eval210_mr_005 | 16328.178 | False | False | False | False | False | plan |
| eval210_tf_001 | 16333.457 | False | False | False | False | False | plan |
| eval210_tf_002 | 16291.142 | False | False | False | False | False | plan |
| eval210_tf_003 | 16272.956 | False | False | False | False | False | plan |
| eval210_tf_004 | 16381.742 | False | False | False | False | False | plan |
| eval210_tf_005 | 16255.198 | False | False | False | False | False | plan |
| eval210_ot_001 | 16491.76 | False | False | None | None | None | plan |
| eval210_ot_002 | 16339.992 | False | False | None | None | None | plan |
| eval210_ot_003 | 16253.77 | False | False | None | None | None | plan |
| eval210_ot_004 | 16261.048 | False | False | None | None | None | plan |
| eval210_ot_005 | 16364.338 | False | False | None | None | None | plan |

## 6. 未通过 `task_success` 的样本

- **`eval210_cse_002`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": true}
- **`eval210_cd_004`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": false, "regions_match": true, "time_range_match": true, "target_object_match": true}
- **`eval210_cd_005`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_te_001`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_te_002`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_te_003`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_te_004`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_te_005`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_cc_001`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_cc_002`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_cc_003`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_cc_004`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_cc_005`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_mr_001`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_mr_002`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_mr_003`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_mr_004`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_mr_005`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_tf_001`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_tf_002`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_tf_003`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_tf_004`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_tf_005`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_ot_001`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}
- **`eval210_ot_002`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}
- **`eval210_ot_003`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}
- **`eval210_ot_004`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}
- **`eval210_ot_005`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}

## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval210_cse_002` | False | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": true} | `['浙江省杭州市']` / `['2021']` | `['浙江省杭州市']` / `['2021']` |
| `eval210_cd_003` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河北省保定市容城县']` / `['2020', '2021', '2022', '2023', '2024']` | `['河北省保定市容城县']` / `['2020', '2024']` |
| `eval210_cd_004` | False | {"intent_match": false, "regions_match": true, "time_range_match": true, "target_object_match": true} | `['北京市']` / `['2020', '2022']` | `['北京市']` / `['2020', '2022']` |
| `eval210_cd_005` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['福建省厦门市']` / `['2023', '2024', '2025']` | `[]` / `[]` |
| `eval210_te_001` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['北京市']` / `['2020', '2021', '2022', '2023']` | `[]` / `[]` |
| `eval210_te_002` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['福建省厦门市']` / `['2021', '2022', '2023', '2024', '2025']` | `[]` / `[]` |
| `eval210_te_003` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['江苏省苏州市']` / `['2022', '2023', '2024', '2025']` | `[]` / `[]` |
| `eval210_te_004` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['广东省深圳市南山区']` / `['2023', '2024', '2025']` | `[]` / `[]` |
| `eval210_te_005` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['河南省郑州市']` / `['2020', '2021', '2022', '2023', '2024']` | `[]` / `[]` |
| `eval210_cc_001` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['河南省郑州市']` / `['2020']` | `[]` / `[]` |
| `eval210_cc_002` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['山东省济南市历下区']` / `['2021']` | `[]` / `[]` |
| `eval210_cc_003` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['湖北省武汉市']` / `['2022']` | `[]` / `[]` |
| `eval210_cc_004` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['云南省昆明市']` / `['2023']` | `[]` / `[]` |
| `eval210_cc_005` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['辽宁省沈阳市']` / `['2024']` | `[]` / `[]` |
| `eval210_mr_001` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['四川省成都市郫都区', '江苏省苏州市']` / `['2020']` | `[]` / `[]` |
| `eval210_mr_002` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['浙江省杭州市', '广东省深圳市南山区']` / `['2021']` | `[]` / `[]` |
| `eval210_mr_003` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['河北省保定市容城县', '河南省郑州市']` / `['2022']` | `[]` / `[]` |
| `eval210_mr_004` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['北京市', '山东省济南市历下区']` / `['2023']` | `[]` / `[]` |
| `eval210_mr_005` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['福建省厦门市', '湖北省武汉市']` / `['2024']` | `[]` / `[]` |
| `eval210_tf_001` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['辽宁省沈阳市']` / `['2020']` | `[]` / `[]` |
| `eval210_tf_002` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['陕西省西安市']` / `['2021']` | `[]` / `[]` |
| `eval210_tf_003` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['安徽省合肥市']` / `['2022']` | `[]` / `[]` |
| `eval210_tf_004` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['江西省南昌市']` / `['2023']` | `[]` / `[]` |
| `eval210_tf_005` | False | {"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['四川省成都市郫都区']` / `['2024']` | `[]` / `[]` |
| `eval210_ot_001` | False | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_002` | False | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_003` | False | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_004` | False | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_005` | False | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |

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

