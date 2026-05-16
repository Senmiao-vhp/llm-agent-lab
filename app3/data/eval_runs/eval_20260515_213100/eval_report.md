# app3 小样本评测报告（**端到端** LangGraph）

## 1. 运行元数据

- **评测模式**：`full`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。
- **生成时间**：2026-05-15T23:07:56.079988
- **金标文件**：`D:\Users\资料夹\智能体\llm-agent-lab\app3\data\eval_cases_210.jsonl`
- **主意图过滤**：`（未过滤）`
- **样本条数**：210
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

- **任务成功率 `success_rate`**：0.9952
- **意图准确率 `intent_acc`**：0.8952
- **槽位三项合取准确率 `slot_acc`**：0.9667
- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：1.0
- **时间单项 `time_range_acc`**：0.9722
- **对象单项 `target_object_acc`**：0.9944
- **响应时间 p50（ms）**：22558.181
- **响应时间 p90（ms）**：57470.123

## 4. 分意图统计（按 `gold.primary_intent`）

| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |
|----------|-----:|-----------:|-------------------------:|
| `change_detection` | 30 | 0.5 | 0.8 |
| `compliance_check` | 30 | 1.0 | 1.0 |
| `current_status_estimate` | 30 | 1.0 | 1.0 |
| `multi_region_compare` | 30 | 1.0 | 1.0 |
| `other` | 30 | 0.8333 | — |
| `transfer_analysis` | 30 | 1.0 | 1.0 |
| `trend_evolution` | 30 | 0.9333 | 1.0 |

## 5. 逐条结果（总表）

| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |
|-----------|------------:|--------------|--------------|---------|------|--------|-------|
| eval210_cse_001 | 20412.504 | True | True | True | True | True | explain |
| eval210_cse_002 | 27050.952 | True | True | True | True | True | explain |
| eval210_cse_003 | 35395.552 | True | True | True | True | True | explain |
| eval210_cse_004 | 33371.303 | True | True | True | True | True | explain |
| eval210_cse_005 | 28693.286 | True | True | True | True | True | explain |
| eval210_cse_006 | 23403.23 | True | True | True | True | True | explain |
| eval210_cse_007 | 13999.906 | True | True | True | True | True | explain |
| eval210_cse_008 | 29816.522 | True | True | True | True | True | explain |
| eval210_cse_009 | 26458.981 | True | True | True | True | True | explain |
| eval210_cse_010 | 26052.76 | True | True | True | True | True | explain |
| eval210_cse_011 | 29268.6 | True | True | True | True | True | explain |
| eval210_cse_012 | 23019.424 | True | True | True | True | True | explain |
| eval210_cse_013 | 10525.012 | True | True | True | True | True | explain |
| eval210_cse_014 | 22948.043 | True | True | True | True | True | explain |
| eval210_cse_015 | 30720.182 | True | True | True | True | True | explain |
| eval210_cse_016 | 18360.638 | True | True | True | True | True | explain |
| eval210_cse_017 | 26197.088 | True | True | True | True | True | explain |
| eval210_cse_018 | 22628.635 | True | True | True | True | True | explain |
| eval210_cse_019 | 14735.553 | True | True | True | True | True | explain |
| eval210_cse_020 | 25499.721 | True | True | True | True | True | explain |
| eval210_cse_021 | 24606.605 | True | True | True | True | True | explain |
| eval210_cse_022 | 21994.634 | True | True | True | True | True | explain |
| eval210_cse_023 | 24839.534 | True | True | True | True | True | explain |
| eval210_cse_024 | 27206.473 | True | True | True | True | True | explain |
| eval210_cse_025 | 12284.16 | True | True | True | True | True | explain |
| eval210_cse_026 | 19826.844 | True | True | True | True | True | explain |
| eval210_cse_027 | 27390.429 | True | True | True | True | True | explain |
| eval210_cse_028 | 23836.795 | True | True | True | True | True | explain |
| eval210_cse_029 | 21102.838 | True | True | True | True | True | explain |
| eval210_cse_030 | 48546.091 | True | True | True | True | True | explain |
| eval210_cd_001 | 19846.081 | True | True | True | True | True | explain |
| eval210_cd_002 | 24620.789 | True | True | True | True | True | explain |
| eval210_cd_003 | 32729.85 | True | True | True | False | True | explain |
| eval210_cd_004 | 24081.709 | True | False | True | True | True | explain |
| eval210_cd_005 | 22237.59 | True | True | True | True | True | explain |
| eval210_cd_006 | 51678.309 | True | False | True | True | True | explain |
| eval210_cd_007 | 20342.885 | True | False | True | True | True | explain |
| eval210_cd_008 | 8484.851 | False | False | True | False | True | explain |
| eval210_cd_009 | 20357.254 | True | True | True | True | True | explain |
| eval210_cd_010 | 48377.908 | True | False | True | True | True | explain |
| eval210_cd_011 | 27761.738 | True | False | True | True | True | explain |
| eval210_cd_012 | 20147.544 | True | True | True | True | True | explain |
| eval210_cd_013 | 21451.89 | True | True | True | True | False | explain |
| eval210_cd_014 | 38750.176 | True | False | True | True | True | explain |
| eval210_cd_015 | 25159.805 | True | True | True | True | True | explain |
| eval210_cd_016 | 22085.468 | True | True | True | True | True | explain |
| eval210_cd_017 | 18841.714 | True | True | True | True | True | explain |
| eval210_cd_018 | 19851.634 | True | True | True | True | True | explain |
| eval210_cd_019 | 22894.587 | True | False | True | True | True | explain |
| eval210_cd_020 | 26919.484 | True | False | True | True | True | explain |
| eval210_cd_021 | 37079.031 | True | False | True | False | True | explain |
| eval210_cd_022 | 17613.29 | True | True | True | True | True | explain |
| eval210_cd_023 | 101288.072 | True | False | True | True | True | explain |
| eval210_cd_024 | 20414.004 | True | True | True | False | True | explain |
| eval210_cd_025 | 22485.571 | True | True | True | True | True | explain |
| eval210_cd_026 | 42232.37 | True | False | True | True | True | explain |
| eval210_cd_027 | 29975.544 | True | True | True | True | True | explain |
| eval210_cd_028 | 32567.546 | True | False | True | True | True | explain |
| eval210_cd_029 | 41333.474 | True | False | True | True | True | explain |
| eval210_cd_030 | 72976.844 | True | False | True | False | True | explain |
| eval210_te_001 | 39489.337 | True | True | True | True | True | explain |
| eval210_te_002 | 60537.371 | True | True | True | True | True | explain |
| eval210_te_003 | 98723.24 | True | True | True | True | True | explain |
| eval210_te_004 | 55633.678 | True | True | True | True | True | explain |
| eval210_te_005 | 78737.961 | True | True | True | True | True | explain |
| eval210_te_006 | 68031.118 | True | True | True | True | True | explain |
| eval210_te_007 | 70897.93 | True | True | True | True | True | explain |
| eval210_te_008 | 43093.23 | True | True | True | True | True | explain |
| eval210_te_009 | 82985.681 | True | True | True | True | True | explain |
| eval210_te_010 | 60381.248 | True | True | True | True | True | explain |
| eval210_te_011 | 63298.594 | True | True | True | True | True | explain |
| eval210_te_012 | 103534.831 | True | True | True | True | True | explain |
| eval210_te_013 | 39460.364 | True | True | True | True | True | explain |
| eval210_te_014 | 58889.272 | True | True | True | True | True | explain |
| eval210_te_015 | 39373.12 | True | True | True | True | True | explain |
| eval210_te_016 | 59537.996 | True | True | True | True | True | explain |
| eval210_te_017 | 65048.925 | True | True | True | True | True | explain |
| eval210_te_018 | 48941.7 | True | True | True | True | True | explain |
| eval210_te_019 | 55191.302 | True | True | True | True | True | explain |
| eval210_te_020 | 36052.171 | True | True | True | True | True | explain |
| eval210_te_021 | 61512.227 | True | True | True | True | True | explain |
| eval210_te_022 | 40472.501 | True | False | True | True | True | explain |
| eval210_te_023 | 58835.073 | True | True | True | True | True | explain |
| eval210_te_024 | 57160.02 | True | True | True | True | True | explain |
| eval210_te_025 | 54775.502 | True | True | True | True | True | explain |
| eval210_te_026 | 62860.111 | True | True | True | True | True | explain |
| eval210_te_027 | 78726.678 | True | True | True | True | True | explain |
| eval210_te_028 | 52004.826 | True | True | True | True | True | explain |
| eval210_te_029 | 60886.919 | True | False | True | True | True | explain |
| eval210_te_030 | 57318.462 | True | True | True | True | True | explain |
| eval210_cc_001 | 18766.779 | True | True | True | True | True | explain |
| eval210_cc_002 | 17154.02 | True | True | True | True | True | explain |
| eval210_cc_003 | 16923.277 | True | True | True | True | True | explain |
| eval210_cc_004 | 16645.99 | True | True | True | True | True | explain |
| eval210_cc_005 | 17687.289 | True | True | True | True | True | explain |
| eval210_cc_006 | 18916.261 | True | True | True | True | True | explain |
| eval210_cc_007 | 22626.266 | True | True | True | True | True | explain |
| eval210_cc_008 | 23088.018 | True | True | True | True | True | explain |
| eval210_cc_009 | 14427.906 | True | True | True | True | True | explain |
| eval210_cc_010 | 13951.591 | True | True | True | True | True | explain |
| eval210_cc_011 | 19957.853 | True | True | True | True | True | explain |
| eval210_cc_012 | 18685.847 | True | True | True | True | True | explain |
| eval210_cc_013 | 19361.871 | True | True | True | True | True | explain |
| eval210_cc_014 | 20357.575 | True | True | True | True | True | explain |
| eval210_cc_015 | 76125.361 | True | True | True | True | True | explain |
| eval210_cc_016 | 21777.628 | True | True | True | True | True | explain |
| eval210_cc_017 | 21180.469 | True | True | True | True | True | explain |
| eval210_cc_018 | 18640.512 | True | True | True | True | True | explain |
| eval210_cc_019 | 19011.72 | True | True | True | True | True | explain |
| eval210_cc_020 | 24585.585 | True | True | True | True | True | explain |
| eval210_cc_021 | 18977.222 | True | True | True | True | True | explain |
| eval210_cc_022 | 17732.137 | True | True | True | True | True | explain |
| eval210_cc_023 | 20415.788 | True | True | True | True | True | explain |
| eval210_cc_024 | 20053.318 | True | True | True | True | True | explain |
| eval210_cc_025 | 18580.204 | True | True | True | True | True | explain |
| eval210_cc_026 | 28228.841 | True | True | True | True | True | explain |
| eval210_cc_027 | 20404.313 | True | True | True | True | True | explain |
| eval210_cc_028 | 22490.096 | True | True | True | True | True | explain |
| eval210_cc_029 | 18427.555 | True | True | True | True | True | explain |
| eval210_cc_030 | 17003.903 | True | True | True | True | True | explain |
| eval210_mr_001 | 14474.49 | True | True | True | True | True | explain |
| eval210_mr_002 | 16101.546 | True | True | True | True | True | explain |
| eval210_mr_003 | 17156.87 | True | True | True | True | True | explain |
| eval210_mr_004 | 19453.951 | True | True | True | True | True | explain |
| eval210_mr_005 | 14396.891 | True | True | True | True | True | explain |
| eval210_mr_006 | 15579.106 | True | True | True | True | True | explain |
| eval210_mr_007 | 18020.266 | True | True | True | True | True | explain |
| eval210_mr_008 | 18272.796 | True | True | True | True | True | explain |
| eval210_mr_009 | 13403.711 | True | True | True | True | True | explain |
| eval210_mr_010 | 40630.765 | True | True | True | True | True | explain |
| eval210_mr_011 | 19750.799 | True | True | True | True | True | explain |
| eval210_mr_012 | 10827.529 | True | True | True | True | True | explain |
| eval210_mr_013 | 18461.105 | True | True | True | True | True | explain |
| eval210_mr_014 | 16312.09 | True | True | True | True | True | explain |
| eval210_mr_015 | 28556.364 | True | True | True | True | True | explain |
| eval210_mr_016 | 17084.24 | True | True | True | True | True | explain |
| eval210_mr_017 | 17723.296 | True | True | True | True | True | explain |
| eval210_mr_018 | 34112.326 | True | True | True | True | True | explain |
| eval210_mr_019 | 21065.656 | True | True | True | True | True | explain |
| eval210_mr_020 | 15761.817 | True | True | True | True | True | explain |
| eval210_mr_021 | 13710.929 | True | True | True | True | True | explain |
| eval210_mr_022 | 28052.902 | True | True | True | True | True | explain |
| eval210_mr_023 | 19828.983 | True | True | True | True | True | explain |
| eval210_mr_024 | 16682.359 | True | True | True | True | True | explain |
| eval210_mr_025 | 21961.727 | True | True | True | True | True | explain |
| eval210_mr_026 | 17442.585 | True | True | True | True | True | explain |
| eval210_mr_027 | 11766.766 | True | True | True | True | True | explain |
| eval210_mr_028 | 15853.549 | True | True | True | True | True | explain |
| eval210_mr_029 | 19993.797 | True | True | True | True | True | explain |
| eval210_mr_030 | 11605.953 | True | True | True | True | True | explain |
| eval210_tf_001 | 18618.335 | True | True | True | True | True | explain |
| eval210_tf_002 | 38263.948 | True | True | True | True | True | explain |
| eval210_tf_003 | 30963.327 | True | True | True | True | True | explain |
| eval210_tf_004 | 40780.653 | True | True | True | True | True | explain |
| eval210_tf_005 | 36575.64 | True | True | True | True | True | explain |
| eval210_tf_006 | 32072.173 | True | True | True | True | True | explain |
| eval210_tf_007 | 43547.801 | True | True | True | True | True | explain |
| eval210_tf_008 | 29193.075 | True | True | True | True | True | explain |
| eval210_tf_009 | 35322.051 | True | True | True | True | True | explain |
| eval210_tf_010 | 29283.984 | True | True | True | True | True | explain |
| eval210_tf_011 | 44890.095 | True | True | True | True | True | explain |
| eval210_tf_012 | 25090.827 | True | True | True | True | True | explain |
| eval210_tf_013 | 23800.649 | True | True | True | True | True | explain |
| eval210_tf_014 | 24571.796 | True | True | True | True | True | explain |
| eval210_tf_015 | 23769.196 | True | True | True | True | True | explain |
| eval210_tf_016 | 26064.744 | True | True | True | True | True | explain |
| eval210_tf_017 | 16984.023 | True | True | True | True | True | explain |
| eval210_tf_018 | 33169.019 | True | True | True | True | True | explain |
| eval210_tf_019 | 41941.976 | True | True | True | True | True | explain |
| eval210_tf_020 | 31630.591 | True | True | True | True | True | explain |
| eval210_tf_021 | 32346.669 | True | True | True | True | True | explain |
| eval210_tf_022 | 28354.196 | True | True | True | True | True | explain |
| eval210_tf_023 | 28831.205 | True | True | True | True | True | explain |
| eval210_tf_024 | 95148.88 | True | True | True | True | True | explain |
| eval210_tf_025 | 53818.667 | True | True | True | True | True | explain |
| eval210_tf_026 | 37306.92 | True | True | True | True | True | explain |
| eval210_tf_027 | 26342.169 | True | True | True | True | True | explain |
| eval210_tf_028 | 27077.398 | True | True | True | True | True | explain |
| eval210_tf_029 | 24287.614 | True | True | True | True | True | explain |
| eval210_tf_030 | 34477.748 | True | True | True | True | True | explain |
| eval210_ot_001 | 5242.055 | True | True | None | None | None | explain |
| eval210_ot_002 | 14008.898 | True | True | None | None | None | explain |
| eval210_ot_003 | 2319.298 | True | True | None | None | None | explain |
| eval210_ot_004 | 4476.5 | True | False | None | None | None | explain |
| eval210_ot_005 | 2150.997 | True | True | None | None | None | explain |
| eval210_ot_006 | 2897.045 | True | True | None | None | None | explain |
| eval210_ot_007 | 2400.087 | True | True | None | None | None | explain |
| eval210_ot_008 | 2999.948 | True | False | None | None | None | explain |
| eval210_ot_009 | 4051.668 | True | False | None | None | None | explain |
| eval210_ot_010 | 2575.421 | True | True | None | None | None | explain |
| eval210_ot_011 | 2560.88 | True | True | None | None | None | explain |
| eval210_ot_012 | 3520.273 | True | True | None | None | None | explain |
| eval210_ot_013 | 3815.259 | True | True | None | None | None | explain |
| eval210_ot_014 | 3459.681 | True | True | None | None | None | explain |
| eval210_ot_015 | 2724.582 | True | True | None | None | None | explain |
| eval210_ot_016 | 3227.792 | True | True | None | None | None | explain |
| eval210_ot_017 | 2798.884 | True | True | None | None | None | explain |
| eval210_ot_018 | 2712.271 | True | True | None | None | None | explain |
| eval210_ot_019 | 3023.321 | True | True | None | None | None | explain |
| eval210_ot_020 | 2908.967 | True | True | None | None | None | explain |
| eval210_ot_021 | 5316.178 | True | False | None | None | None | explain |
| eval210_ot_022 | 2975.866 | True | True | None | None | None | explain |
| eval210_ot_023 | 2846.465 | True | True | None | None | None | explain |
| eval210_ot_024 | 2772.311 | True | True | None | None | None | explain |
| eval210_ot_025 | 2843.945 | True | True | None | None | None | explain |
| eval210_ot_026 | 2920.172 | True | True | None | None | None | explain |
| eval210_ot_027 | 3439.731 | True | False | None | None | None | explain |
| eval210_ot_028 | 3076.083 | True | True | None | None | None | explain |
| eval210_ot_029 | 2712.555 | True | True | None | None | None | explain |
| eval210_ot_030 | 5171.611 | True | True | None | None | None | explain |

## 6. 未通过 `task_success` 的样本

- **`eval210_cd_008`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true}

## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval210_cd_003` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河北省保定市容城县']` / `['2020', '2021', '2022', '2023', '2024']` | `['河北省保定市容城县']` / `['2020', '2024']` |
| `eval210_cd_008` | False | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2021', '2022', '2023']` | `['河南省郑州市']` / `['2020', '2023']` |
| `eval210_cd_013` | True | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": false} | `['陕西省西安市']` / `['2022', '2023', '2024', '2025']` | `['陕西省西安市']` / `['2022', '2023', '2024', '2025']` |
| `eval210_cd_021` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['江苏省苏州市']` / `['2020', '2021', '2022', '2023', '2024', '2025']` | `['江苏省苏州市']` / `['2020', '2025']` |
| `eval210_cd_024` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['山东省济南市历下区']` / `['2020', '2021', '2022', '2023', '2024']` | `['山东省济南市历下区']` / `['2020', '2024']` |
| `eval210_cd_030` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['江西省南昌市']` / `['2020', '2021', '2022', '2024', '2025']` | `['江西省南昌市']` / `['2020', '2022', '2024', '2025']` |
| `eval210_ot_001` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_002` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_003` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_004` | True | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_005` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_006` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_007` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_008` | True | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_009` | True | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_010` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_011` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_012` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_013` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_014` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_015` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_016` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_017` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_018` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_019` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_020` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_021` | True | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_022` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_023` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_024` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_025` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_026` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_027` | True | {"intent_match": false} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_028` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_029` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |
| `eval210_ot_030` | True | {"intent_match": true} | `[]` / `[]` | `[]` / `[]` |

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

