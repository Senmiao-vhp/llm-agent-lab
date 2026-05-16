# app3 小样本评测报告（**端到端** LangGraph）

## 1. 运行元数据

- **评测模式**：`full`（`parse` = 只跑 `parse_node`；`full` = `invoke` 全图）。
- **生成时间**：2026-05-16T00:32:22.890931
- **金标文件**：`D:\Users\资料夹\智能体\llm-agent-lab\app3\data\eval_cases_350.jsonl`
- **主意图过滤**：`（未过滤）`
- **样本条数**：350
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

- **任务成功率 `success_rate`**：0.9457
- **意图准确率 `intent_acc`**：0.8229
- **槽位三项合取准确率 `slot_acc`**：0.33
- **行政区单项 `regions_acc`**（有 `regions_match` 的样本）：0.8833
- **时间单项 `time_range_acc`**：0.52
- **对象单项 `target_object_acc`**：0.6833
- **响应时间 p50（ms）**：24679.769
- **响应时间 p90（ms）**：63803.026

## 4. 分意图统计（按 `gold.primary_intent`）

| 金标意图 | 条数 | intent_acc | slot_acc（三项全对占比） |
|----------|-----:|-----------:|-------------------------:|
| `change_detection` | 50 | 0.76 | 0.48 |
| `compliance_check` | 50 | 0.9 | 0.3 |
| `current_status_estimate` | 50 | 0.64 | 0.74 |
| `multi_region_compare` | 50 | 0.82 | 0.46 |
| `other` | 50 | 0.96 | — |
| `transfer_analysis` | 50 | 0.94 | 0.0 |
| `trend_evolution` | 50 | 0.74 | 0.0 |

## 5. 逐条结果（总表）

| sample_id | duration_ms | task_success | intent_match | regions | time | target | phase |
|-----------|------------:|--------------|--------------|---------|------|--------|-------|
| eval50_cse_001 | 21584.327 | True | True | True | True | True | explain |
| eval50_cse_002 | 25264.552 | True | False | True | True | True | explain |
| eval50_cse_003 | 30265.401 | True | True | True | True | True | explain |
| eval50_cse_004 | 44880.304 | True | True | True | True | True | explain |
| eval50_cse_005 | 29277.283 | True | True | True | True | True | explain |
| eval50_cse_006 | 31131.702 | True | True | True | True | True | explain |
| eval50_cse_007 | 32317.428 | True | True | True | True | True | explain |
| eval50_cse_008 | 23038.335 | True | True | True | True | True | explain |
| eval50_cse_009 | 9701.506 | True | True | True | True | True | explain |
| eval50_cse_010 | 29331.727 | True | True | True | True | True | explain |
| eval50_cse_011 | 27240.26 | True | True | True | True | True | explain |
| eval50_cse_012 | 22419.743 | True | True | True | True | True | explain |
| eval50_cse_013 | 28016.828 | True | True | True | True | True | explain |
| eval50_cse_014 | 31348.887 | True | True | True | True | True | explain |
| eval50_cse_015 | 24650.18 | True | True | True | True | True | explain |
| eval50_cse_016 | 18579.26 | True | False | True | True | False | explain |
| eval50_cse_017 | 19681.735 | True | False | True | False | True | explain |
| eval50_cse_018 | 20753.8 | True | True | True | True | True | explain |
| eval50_cse_019 | 54791.019 | True | False | True | True | True | explain |
| eval50_cse_020 | 31706.377 | True | True | True | True | True | explain |
| eval50_cse_021 | 38370.952 | True | False | True | False | True | explain |
| eval50_cse_022 | 21012.366 | True | True | True | True | True | explain |
| eval50_cse_023 | 8281.168 | True | True | True | True | True | explain |
| eval50_cse_024 | 18330.928 | True | True | True | True | True | explain |
| eval50_cse_025 | 20511.974 | True | True | True | True | True | explain |
| eval50_cse_026 | 36923.468 | True | False | True | False | True | explain |
| eval50_cse_027 | 25942.875 | True | True | True | False | True | explain |
| eval50_cse_028 | 25992.517 | True | False | True | False | True | explain |
| eval50_cse_029 | 25895.792 | True | False | True | False | True | explain |
| eval50_cse_030 | 122520.849 | True | False | True | False | True | explain |
| eval50_cse_031 | 25262.88 | True | False | True | False | True | explain |
| eval50_cse_032 | 63782.812 | True | False | True | False | True | explain |
| eval50_cse_033 | 28375.062 | True | True | True | False | True | explain |
| eval50_cse_034 | 18539.616 | True | True | True | True | True | explain |
| eval50_cse_035 | 27618.22 | True | True | True | True | True | explain |
| eval50_cse_036 | 17261.107 | True | True | True | True | True | explain |
| eval50_cse_037 | 26194.369 | True | True | True | True | True | explain |
| eval50_cse_038 | 20588.228 | True | True | True | True | True | explain |
| eval50_cse_039 | 20989.177 | True | True | True | True | True | explain |
| eval50_cse_040 | 17882.985 | True | False | True | True | True | explain |
| eval50_cse_041 | 26476.532 | True | True | True | True | True | explain |
| eval50_cse_042 | 51199.093 | True | False | True | True | True | explain |
| eval50_cse_043 | 19838.36 | True | True | True | True | True | explain |
| eval50_cse_044 | 14350.672 | True | True | True | True | True | explain |
| eval50_cse_045 | 23958.366 | True | False | True | True | True | explain |
| eval50_cse_046 | 22287.552 | True | True | True | True | True | explain |
| eval50_cse_047 | 33874.971 | True | False | True | False | True | explain |
| eval50_cse_048 | 36141.846 | True | False | True | True | True | explain |
| eval50_cse_049 | 27209.463 | True | False | True | True | True | explain |
| eval50_cse_050 | 100821.137 | True | False | True | False | True | explain |
| eval50_cd_001 | 44989.651 | True | True | True | True | True | explain |
| eval50_cd_002 | 46221.901 | True | True | True | True | True | explain |
| eval50_cd_003 | 35159.418 | True | True | True | True | True | explain |
| eval50_cd_004 | 57363.416 | True | True | True | True | True | explain |
| eval50_cd_005 | 35565.925 | True | True | False | True | True | explain |
| eval50_cd_006 | 30510.738 | True | True | True | True | True | explain |
| eval50_cd_007 | 45534.551 | True | True | True | True | True | explain |
| eval50_cd_008 | 24709.358 | True | True | True | True | True | explain |
| eval50_cd_009 | 75821.256 | True | False | True | True | True | explain |
| eval50_cd_010 | 26727.912 | True | True | True | True | True | explain |
| eval50_cd_011 | 24604.967 | True | True | True | True | True | explain |
| eval50_cd_012 | 28879.8 | True | True | True | True | True | explain |
| eval50_cd_013 | 45727.847 | True | True | True | True | True | explain |
| eval50_cd_014 | 36665.799 | True | True | False | True | True | explain |
| eval50_cd_015 | 45499.461 | True | True | True | True | True | explain |
| eval50_cd_016 | 34900.281 | True | True | True | False | True | explain |
| eval50_cd_017 | 25301.265 | True | True | True | False | True | explain |
| eval50_cd_018 | 33116.37 | True | True | False | False | False | explain |
| eval50_cd_019 | 48151.591 | True | False | True | False | True | explain |
| eval50_cd_020 | 35348.583 | True | False | True | False | True | explain |
| eval50_cd_021 | 49417.514 | True | True | True | False | True | explain |
| eval50_cd_022 | 24367.23 | True | True | True | False | True | explain |
| eval50_cd_023 | 90429.627 | False | False | True | False | True | explain |
| eval50_cd_024 | 24602.099 | True | True | True | False | True | explain |
| eval50_cd_025 | 51991.181 | True | False | True | False | True | explain |
| eval50_cd_026 | 45194.487 | True | False | True | False | True | explain |
| eval50_cd_027 | 72411.125 | True | False | True | False | False | explain |
| eval50_cd_028 | 28316.877 | True | True | True | False | True | explain |
| eval50_cd_029 | 22698.312 | True | True | True | False | True | explain |
| eval50_cd_030 | 120073.658 | True | False | True | False | True | explain |
| eval50_cd_031 | 22029.661 | True | True | True | False | True | explain |
| eval50_cd_032 | 22945.461 | True | True | True | False | True | explain |
| eval50_cd_033 | 80542.302 | True | False | True | False | True | explain |
| eval50_cd_034 | 32274.104 | True | True | True | True | True | explain |
| eval50_cd_035 | 33955.122 | True | True | True | True | True | explain |
| eval50_cd_036 | 20976.892 | True | True | True | True | False | explain |
| eval50_cd_037 | 35732.626 | True | True | True | True | True | explain |
| eval50_cd_038 | 33811.931 | True | True | True | True | False | explain |
| eval50_cd_039 | 22700.807 | True | True | True | True | True | explain |
| eval50_cd_040 | 22732.485 | True | True | True | True | True | explain |
| eval50_cd_041 | 25296.658 | True | True | True | True | True | explain |
| eval50_cd_042 | 64995.062 | True | False | True | True | False | explain |
| eval50_cd_043 | 19979.906 | True | True | True | True | True | explain |
| eval50_cd_044 | 20354.624 | True | True | True | True | False | explain |
| eval50_cd_045 | 21205.019 | True | True | True | True | True | explain |
| eval50_cd_046 | 35021.115 | True | True | True | True | True | explain |
| eval50_cd_047 | 71264.7 | True | False | True | False | True | explain |
| eval50_cd_048 | 50868.122 | True | False | True | True | True | explain |
| eval50_cd_049 | 18698.013 | True | True | True | True | True | explain |
| eval50_cd_050 | 25461.303 | True | True | True | False | True | explain |
| eval50_cc_001 | 16769.611 | True | True | False | True | True | explain |
| eval50_cc_002 | 17315.169 | True | True | False | True | False | explain |
| eval50_cc_003 | 24203.23 | True | True | False | True | True | explain |
| eval50_cc_004 | 20091.102 | True | True | False | True | True | explain |
| eval50_cc_005 | 71985.128 | True | True | False | True | False | explain |
| eval50_cc_006 | 24241.031 | True | True | False | True | True | explain |
| eval50_cc_007 | 21579.305 | True | True | False | True | True | explain |
| eval50_cc_008 | 23361.678 | True | True | False | True | True | explain |
| eval50_cc_009 | 17872.559 | True | True | False | True | True | explain |
| eval50_cc_010 | 22387.839 | True | True | False | True | False | explain |
| eval50_cc_011 | 19754.109 | True | True | False | True | True | explain |
| eval50_cc_012 | 18692.498 | True | True | False | True | True | explain |
| eval50_cc_013 | 20967.436 | True | True | False | True | False | explain |
| eval50_cc_014 | 16336.009 | True | True | False | True | True | explain |
| eval50_cc_015 | 19092.384 | True | True | False | True | True | explain |
| eval50_cc_016 | 23790.102 | True | True | True | True | True | explain |
| eval50_cc_017 | 22216.07 | True | True | True | False | False | explain |
| eval50_cc_018 | 22533.685 | True | True | False | True | False | explain |
| eval50_cc_019 | 45376.207 | True | True | True | False | False | explain |
| eval50_cc_020 | 18525.596 | True | True | True | True | True | explain |
| eval50_cc_021 | 21385.877 | True | True | True | False | True | explain |
| eval50_cc_022 | 20082.106 | True | True | True | False | True | explain |
| eval50_cc_023 | 39419.022 | True | True | True | False | False | explain |
| eval50_cc_024 | 22852.284 | True | True | True | False | True | explain |
| eval50_cc_025 | 24884.721 | True | True | True | False | False | explain |
| eval50_cc_026 | 29587.587 | True | True | True | False | True | explain |
| eval50_cc_027 | 21898.807 | True | True | True | False | False | explain |
| eval50_cc_028 | 22875.301 | True | True | True | False | True | explain |
| eval50_cc_029 | 23921.242 | True | True | True | False | True | explain |
| eval50_cc_030 | 23102.963 | True | True | True | False | True | explain |
| eval50_cc_031 | 17886.139 | True | True | True | True | True | explain |
| eval50_cc_032 | 28920.204 | True | True | True | False | False | explain |
| eval50_cc_033 | 36552.547 | True | False | True | False | True | explain |
| eval50_cc_034 | 28925.952 | True | True | True | True | False | explain |
| eval50_cc_035 | 22379.336 | True | True | True | True | True | explain |
| eval50_cc_036 | 18633.195 | True | True | True | True | True | explain |
| eval50_cc_037 | 33540.293 | True | True | True | True | True | explain |
| eval50_cc_038 | 19794.739 | True | True | True | True | False | explain |
| eval50_cc_039 | 22832.098 | True | True | True | True | True | explain |
| eval50_cc_040 | 20693.898 | True | False | True | True | True | explain |
| eval50_cc_041 | 30629.957 | True | False | True | True | True | explain |
| eval50_cc_042 | 88305.728 | True | True | True | True | True | explain |
| eval50_cc_043 | 17674.947 | True | True | True | True | False | explain |
| eval50_cc_044 | 21868.221 | True | True | True | True | True | explain |
| eval50_cc_045 | 25260.798 | True | True | True | True | True | explain |
| eval50_cc_046 | 18935.329 | True | False | True | True | True | explain |
| eval50_cc_047 | 12036.187 | False | True | True | False | True | explain |
| eval50_cc_048 | 36175.44 | True | False | True | True | True | explain |
| eval50_cc_049 | 31293.685 | True | True | True | True | True | explain |
| eval50_cc_050 | 19587.706 | True | True | True | False | False | explain |
| eval50_te_001 | 74522.994 | True | True | True | False | True | explain |
| eval50_te_002 | 67150.898 | True | False | True | False | True | explain |
| eval50_te_003 | 40120.439 | True | True | True | False | True | explain |
| eval50_te_004 | 103661.679 | True | True | True | False | True | explain |
| eval50_te_005 | 96111.361 | True | True | True | False | True | explain |
| eval50_te_006 | 20492.259 | False | False | False | False | False | plan |
| eval50_te_007 | 68001.646 | True | True | True | False | True | explain |
| eval50_te_008 | 63704.687 | True | True | True | False | True | explain |
| eval50_te_009 | 62736.193 | True | True | True | False | True | explain |
| eval50_te_010 | 55355.561 | True | True | True | False | True | explain |
| eval50_te_011 | 51010.204 | True | True | True | False | True | explain |
| eval50_te_012 | 92951.829 | True | True | True | False | True | explain |
| eval50_te_013 | 69768.758 | True | True | True | False | True | explain |
| eval50_te_014 | 20636.323 | False | False | False | False | False | plan |
| eval50_te_015 | 91659.608 | True | True | True | False | True | explain |
| eval50_te_016 | 68600.224 | True | True | True | False | True | explain |
| eval50_te_017 | 35697.974 | True | True | True | False | True | explain |
| eval50_te_018 | 109416.812 | False | True | True | False | True | explain |
| eval50_te_019 | 54724.973 | True | True | True | False | False | explain |
| eval50_te_020 | 135581.165 | True | True | True | False | True | explain |
| eval50_te_021 | 58857.664 | True | True | True | False | True | explain |
| eval50_te_022 | 58576.55 | True | True | True | False | True | explain |
| eval50_te_023 | 52092.584 | True | True | True | False | True | explain |
| eval50_te_024 | 51856.866 | True | True | True | False | True | explain |
| eval50_te_025 | 52337.24 | True | True | True | False | False | explain |
| eval50_te_026 | 61931.838 | True | True | True | False | True | explain |
| eval50_te_027 | 76220.791 | True | True | True | False | True | explain |
| eval50_te_028 | 92747.631 | True | True | True | False | True | explain |
| eval50_te_029 | 57744.096 | True | True | True | False | True | explain |
| eval50_te_030 | 142791.771 | True | True | True | False | True | explain |
| eval50_te_031 | 68569.429 | True | True | True | False | False | explain |
| eval50_te_032 | 70774.329 | True | True | True | False | True | explain |
| eval50_te_033 | 88008.67 | True | True | True | False | True | explain |
| eval50_te_034 | 54856.516 | True | True | True | False | True | explain |
| eval50_te_035 | 66108.587 | True | True | True | False | True | explain |
| eval50_te_036 | 68631.729 | True | True | True | False | True | explain |
| eval50_te_037 | 117263.663 | True | True | True | False | True | explain |
| eval50_te_038 | 12349.525 | False | False | False | False | False | plan |
| eval50_te_039 | 4788.724 | False | False | False | False | False | plan |
| eval50_te_040 | 7831.21 | False | False | False | False | False | plan |
| eval50_te_041 | 6260.218 | False | False | False | False | False | plan |
| eval50_te_042 | 5380.298 | False | False | False | False | False | plan |
| eval50_te_043 | 6591.829 | False | False | False | False | False | plan |
| eval50_te_044 | 5600.475 | False | False | False | False | False | plan |
| eval50_te_045 | 6315.753 | False | False | False | False | False | plan |
| eval50_te_046 | 7764.265 | False | False | False | False | False | plan |
| eval50_te_047 | 52977.468 | True | True | True | False | True | explain |
| eval50_te_048 | 6547.792 | False | False | False | False | False | plan |
| eval50_te_049 | 63090.069 | True | True | True | False | True | explain |
| eval50_te_050 | 56023.585 | True | True | True | False | True | explain |
| eval50_mrc_001 | 16815.589 | True | True | True | True | True | explain |
| eval50_mrc_002 | 16687.893 | True | True | True | True | True | explain |
| eval50_mrc_003 | 14382.157 | True | True | True | True | True | explain |
| eval50_mrc_004 | 18331.142 | True | True | True | True | True | explain |
| eval50_mrc_005 | 28516.822 | True | True | True | True | True | explain |
| eval50_mrc_006 | 16146.964 | True | True | True | True | True | explain |
| eval50_mrc_007 | 14238.033 | True | True | True | True | True | explain |
| eval50_mrc_008 | 15196.236 | True | True | True | True | True | explain |
| eval50_mrc_009 | 13359.797 | True | True | True | True | True | explain |
| eval50_mrc_010 | 34239.12 | True | True | True | True | True | explain |
| eval50_mrc_011 | 16455.445 | True | True | True | True | True | explain |
| eval50_mrc_012 | 19071.419 | False | False | False | False | False | plan |
| eval50_mrc_013 | 19030.973 | True | True | True | True | True | explain |
| eval50_mrc_014 | 23400.216 | True | True | True | True | False | explain |
| eval50_mrc_015 | 15467.577 | True | True | True | True | True | explain |
| eval50_mrc_016 | 13572.345 | True | True | True | False | True | explain |
| eval50_mrc_017 | 17298.146 | True | True | True | False | True | explain |
| eval50_mrc_018 | 13798.857 | True | True | True | False | True | explain |
| eval50_mrc_019 | 22486.897 | True | True | True | False | True | explain |
| eval50_mrc_020 | 14876.115 | True | True | True | False | True | explain |
| eval50_mrc_021 | 15010.758 | True | True | True | False | True | explain |
| eval50_mrc_022 | 13901.816 | True | True | True | False | True | explain |
| eval50_mrc_023 | 18561.056 | True | True | True | False | True | explain |
| eval50_mrc_024 | 20129.372 | True | True | True | False | False | explain |
| eval50_mrc_025 | 13502.857 | True | True | True | False | True | explain |
| eval50_mrc_026 | 14620.271 | True | True | True | False | True | explain |
| eval50_mrc_027 | 23113.544 | True | True | True | False | True | explain |
| eval50_mrc_028 | 53969.627 | True | False | True | False | True | explain |
| eval50_mrc_029 | 16018.582 | True | True | True | False | True | explain |
| eval50_mrc_030 | 20540.398 | True | True | True | False | True | explain |
| eval50_mrc_031 | 19091.201 | True | True | True | False | True | explain |
| eval50_mrc_032 | 10049.501 | True | True | True | False | True | explain |
| eval50_mrc_033 | 21054.388 | True | True | True | False | True | explain |
| eval50_mrc_034 | 17460.312 | True | True | True | True | True | explain |
| eval50_mrc_035 | 74596.785 | True | False | True | True | True | explain |
| eval50_mrc_036 | 11431.426 | True | True | True | True | False | explain |
| eval50_mrc_037 | 15430.837 | True | True | True | True | True | explain |
| eval50_mrc_038 | 35311.927 | True | False | True | False | False | explain |
| eval50_mrc_039 | 15204.989 | True | True | True | True | True | explain |
| eval50_mrc_040 | 26463.401 | True | False | True | False | False | explain |
| eval50_mrc_041 | 18034.024 | True | True | True | True | True | explain |
| eval50_mrc_042 | 24041.738 | True | True | True | True | False | explain |
| eval50_mrc_043 | 13076.604 | True | True | True | True | True | explain |
| eval50_mrc_044 | 16505.554 | True | True | True | True | True | explain |
| eval50_mrc_045 | 27115.734 | True | False | True | True | False | explain |
| eval50_mrc_046 | 10637.232 | True | True | True | True | True | explain |
| eval50_mrc_047 | 15019.781 | True | True | True | False | True | explain |
| eval50_mrc_048 | 29327.133 | True | False | True | True | True | explain |
| eval50_mrc_049 | 62684.88 | True | False | True | True | True | explain |
| eval50_mrc_050 | 63984.957 | True | False | True | False | True | explain |
| eval50_ta_001 | 29260.389 | True | True | True | True | False | explain |
| eval50_ta_002 | 36692.536 | True | True | True | True | False | explain |
| eval50_ta_003 | 24268.056 | True | True | True | True | False | explain |
| eval50_ta_004 | 42127.585 | True | True | True | True | False | explain |
| eval50_ta_005 | 32237.484 | True | True | True | True | False | explain |
| eval50_ta_006 | 33572.057 | True | True | True | True | False | explain |
| eval50_ta_007 | 33907.85 | True | True | True | True | False | explain |
| eval50_ta_008 | 23590.954 | True | True | True | True | False | explain |
| eval50_ta_009 | 29905.957 | True | True | True | True | False | explain |
| eval50_ta_010 | 20319.92 | False | False | False | False | False | plan |
| eval50_ta_011 | 31770.978 | True | True | True | True | False | explain |
| eval50_ta_012 | 44488.58 | True | True | True | True | False | explain |
| eval50_ta_013 | 38473.519 | True | True | True | True | False | explain |
| eval50_ta_014 | 54103.556 | True | True | False | True | False | explain |
| eval50_ta_015 | 50248.957 | True | True | True | True | False | explain |
| eval50_ta_016 | 40468.523 | True | True | True | False | False | explain |
| eval50_ta_017 | 43223.541 | True | True | True | False | False | explain |
| eval50_ta_018 | 39065.345 | True | True | False | False | False | explain |
| eval50_ta_019 | 27896.383 | True | True | True | False | False | explain |
| eval50_ta_020 | 28701.426 | True | True | True | False | False | explain |
| eval50_ta_021 | 40112.99 | True | True | True | False | False | explain |
| eval50_ta_022 | 38042.371 | True | True | True | False | False | explain |
| eval50_ta_023 | 36398.065 | True | True | True | False | False | explain |
| eval50_ta_024 | 55683.164 | True | True | True | False | False | explain |
| eval50_ta_025 | 27001.601 | True | True | True | False | False | explain |
| eval50_ta_026 | 43389.485 | True | True | True | False | False | explain |
| eval50_ta_027 | 43483.057 | True | True | True | False | False | explain |
| eval50_ta_028 | 30624.07 | True | False | True | False | False | explain |
| eval50_ta_029 | 35910.52 | True | True | True | False | False | explain |
| eval50_ta_030 | 107668.842 | True | True | True | False | False | explain |
| eval50_ta_031 | 28038.598 | True | True | True | False | False | explain |
| eval50_ta_032 | 36289.603 | True | True | True | False | False | explain |
| eval50_ta_033 | 72945.632 | True | True | True | False | False | explain |
| eval50_ta_034 | 34674.049 | True | True | True | True | False | explain |
| eval50_ta_035 | 31211.176 | True | True | True | True | False | explain |
| eval50_ta_036 | 39848.658 | True | True | True | True | False | explain |
| eval50_ta_037 | 43458.426 | True | True | True | True | False | explain |
| eval50_ta_038 | 34894.392 | True | True | True | False | False | explain |
| eval50_ta_039 | 31654.216 | True | True | True | True | False | explain |
| eval50_ta_040 | 28302.858 | True | True | True | False | False | explain |
| eval50_ta_041 | 33192.075 | True | True | True | True | False | explain |
| eval50_ta_042 | 28560.65 | True | True | True | True | False | explain |
| eval50_ta_043 | 28104.964 | True | True | True | True | False | explain |
| eval50_ta_044 | 27031.959 | True | True | True | True | False | explain |
| eval50_ta_045 | 38442.13 | True | True | True | True | False | explain |
| eval50_ta_046 | 25763.22 | True | True | True | True | False | explain |
| eval50_ta_047 | 37365.914 | True | True | True | False | False | explain |
| eval50_ta_048 | 30295.672 | True | False | True | True | False | explain |
| eval50_ta_049 | 40941.265 | True | True | True | True | False | explain |
| eval50_ta_050 | 29477.358 | True | True | True | False | False | explain |
| eval210_other_001 | 3954.073 | True | True | None | None | None | explain |
| eval210_other_002 | 2443.588 | True | True | None | None | None | explain |
| eval210_other_003 | 2885.15 | True | True | None | None | None | explain |
| eval210_other_004 | 2450.895 | True | True | None | None | None | explain |
| eval210_other_005 | 2204.706 | True | True | None | None | None | explain |
| eval210_other_006 | 8301.099 | True | True | None | None | None | explain |
| eval210_other_007 | 2907.101 | True | True | None | None | None | explain |
| eval210_other_008 | 2586.841 | True | True | None | None | None | explain |
| eval210_other_009 | 2031.445 | False | False | None | None | None | plan |
| eval210_other_010 | 2556.832 | True | True | None | None | None | explain |
| eval210_other_011 | 2244.801 | True | True | None | None | None | explain |
| eval210_other_012 | 2431.221 | True | True | None | None | None | explain |
| eval210_other_013 | 2389.6 | True | True | None | None | None | explain |
| eval210_other_014 | 2790.683 | True | True | None | None | None | explain |
| eval210_other_015 | 2671.023 | True | True | None | None | None | explain |
| eval210_other_016 | 5468.269 | True | True | None | None | None | explain |
| eval210_other_017 | 3003.987 | True | True | None | None | None | explain |
| eval210_other_018 | 2856.318 | True | True | None | None | None | explain |
| eval210_other_019 | 2887.326 | True | True | None | None | None | explain |
| eval210_other_020 | 2420.359 | True | True | None | None | None | explain |
| eval210_other_021 | 3050.211 | True | True | None | None | None | explain |
| eval210_other_022 | 3316.339 | True | True | None | None | None | explain |
| eval210_other_023 | 20052.572 | False | False | None | None | None | plan |
| eval210_other_024 | 4290.762 | True | True | None | None | None | explain |
| eval210_other_025 | 3648.905 | True | True | None | None | None | explain |
| eval210_other_026 | 2927.418 | True | True | None | None | None | explain |
| eval210_other_027 | 3152.398 | True | True | None | None | None | explain |
| eval210_other_028 | 13509.928 | True | True | None | None | None | explain |
| eval210_other_029 | 2859.501 | True | True | None | None | None | explain |
| eval210_other_030 | 3016.7 | True | True | None | None | None | explain |
| eval210_other_031 | 2568.588 | True | True | None | None | None | explain |
| eval210_other_032 | 2819.127 | True | True | None | None | None | explain |
| eval210_other_033 | 2864.644 | True | True | None | None | None | explain |
| eval210_other_034 | 3111.327 | True | True | None | None | None | explain |
| eval210_other_035 | 2763.957 | True | True | None | None | None | explain |
| eval210_other_036 | 3091.205 | True | True | None | None | None | explain |
| eval210_other_037 | 3024.07 | True | True | None | None | None | explain |
| eval210_other_038 | 2452.522 | True | True | None | None | None | explain |
| eval210_other_039 | 2415.824 | True | True | None | None | None | explain |
| eval210_other_040 | 4472.395 | True | True | None | None | None | explain |
| eval210_other_041 | 2735.313 | True | True | None | None | None | explain |
| eval210_other_042 | 4003.963 | True | True | None | None | None | explain |
| eval210_other_043 | 3680.671 | True | True | None | None | None | explain |
| eval210_other_044 | 3491.934 | True | True | None | None | None | explain |
| eval210_other_045 | 4272.11 | True | True | None | None | None | explain |
| eval210_other_046 | 3323.914 | True | True | None | None | None | explain |
| eval210_other_047 | 3104.457 | True | True | None | None | None | explain |
| eval210_other_048 | 2714.71 | True | True | None | None | None | explain |
| eval210_other_049 | 2724.747 | True | True | None | None | None | explain |
| eval210_other_050 | 3220.023 | True | True | None | None | None | explain |

## 6. 未通过 `task_success` 的样本

- **`eval50_cd_023`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true}
  - **`gis_pipeline`**（GIS 摘要）：`{"success": false, "message": "Task failed: q1_trend (trend_cropland_loss): trend_cropland_loss year=2015 在多次重试后仍失败: GEE S2 拉取在 tenacity 重试后仍失败 (year=2015): GEE 未找到符合条件的 Sentinel-2 影像。请放宽时间范围/云量阈值或缩小 AOI。"}`
- **`eval50_cc_047`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true}
  - **`gis_pipeline`**（GIS 摘要）：`{"success": false, "message": "Task failed: q1_compliance (compliance_check_point): GlobeLand30 无法在该点采样，请检查坐标范围与本地分幅是否齐全。"}`
- **`eval50_te_006`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_014`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_018`**：phase=`explain` error_class=`none` fatal=`None` checks={"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true}
  - **`gis_pipeline`**（GIS 摘要）：`{"success": false, "message": "Task failed: q1_trend (trend_cropland_loss): trend_cropland_loss year=2015 在多次重试后仍失败: GEE S2 拉取在 tenacity 重试后仍失败 (year=2015): GEE 未找到符合条件的 Sentinel-2 影像。请放宽时间范围/云量阈值或缩小 AOI。"}`
- **`eval50_te_038`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_039`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_040`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_041`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_042`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_043`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_044`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_045`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_046`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_te_048`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_mrc_012`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval50_ta_010`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false, "regions_match": false, "time_range_match": false, "target_object_match": false}
- **`eval210_other_009`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}
- **`eval210_other_023`**：phase=`plan` error_class=`fatal` fatal=`DSL 规划需要有效的 parse_result.queries；请先完成解析或开启 APP3_PLAN_USE_LLM。` checks={"intent_match": false}

## 7. 槽位未全对或解析失败样本（前 50 条；金标 vs 预测）

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval50_cse_016` | True | {"intent_match": false, "regions_match": true, "time_range_match": true, "target_object_match": false} | `['广东省深圳市南山区']` / `['2024']` | `['广东省深圳市南山区']` / `['2024']` |
| `eval50_cse_017` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2023', '2025']` | `['河南省郑州市']` / `['2024', '2025']` |
| `eval50_cse_021` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['浙江省杭州市']` / `['2020', '2025']` | `['浙江省杭州市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cse_026` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['广东省佛山市']` / `['2020', '2025']` | `['广东省佛山市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cse_027` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['江苏省南通市']` / `['2020', '2023']` | `['江苏省南通市']` / `['2021', '2022', '2023', '2024', '2025']` |
| `eval50_cse_028` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['山东省青岛市']` / `['2020', '2025']` | `['山东省青岛市']` / `['2023', '2026']` |
| `eval50_cse_029` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['湖南省长沙市']` / `['2020', '2025']` | `['湖南省长沙市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cse_030` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['广东省珠海市']` / `['2020', '2025']` | `['广东省珠海市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cse_031` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['新疆维吾尔自治区乌鲁木齐市']` / `['2023', '2025']` | `['新疆维吾尔自治区乌鲁木齐市']` / `['2024', '2025']` |
| `eval50_cse_032` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['福建省福州市']` / `['2020', '2023']` | `['福建省福州市']` / `['2021', '2022', '2023', '2024', '2025']` |
| `eval50_cse_033` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['甘肃省兰州市']` / `['2022', '2025']` | `['甘肃省兰州市']` / `['2026']` |
| `eval50_cse_047` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2025']` | `['河南省郑州市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cse_050` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['湖北省武汉市']` / `['2020', '2025']` | `['湖北省武汉市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_005` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['江苏省苏州市']` / `['2024']` | `['江苏省苏州市工业园区']` / `['2024']` |
| `eval50_cd_014` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['天津市']` / `['2021']` | `['天津市滨海新区']` / `['2021']` |
| `eval50_cd_016` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['广东省深圳市']` / `['2020', '2025']` | `['广东省深圳市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_017` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2025']` | `['河南省郑州市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_018` | True | {"intent_match": true, "regions_match": false, "time_range_match": false, "target_object_match": false} | `['江苏省苏州市']` / `['2023', '2025']` | `['江苏省苏州市苏州工业园区']` / `['2025', '2026']` |
| `eval50_cd_019` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['湖北省武汉市']` / `['2022', '2025']` | `['湖北省武汉市']` / `['2022', '2026']` |
| `eval50_cd_020` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['北京市']` / `['2020', '2025']` | `['北京市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_021` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['浙江省杭州市']` / `['2021', '2025']` | `['浙江省杭州市']` / `[]` |
| `eval50_cd_022` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['福建省厦门市']` / `['2020', '2025']` | `['福建省厦门市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_023` | False | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['四川省成都市郫都区']` / `['2020', '2025']` | `['四川省成都市郫都区']` / `['2011', '2012', '2013', '2014', '2015', '2016', '2017', '2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025']` |
| `eval50_cd_024` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['安徽省合肥市']` / `['2021', '2025']` | `['安徽省合肥市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_025` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['云南省昆明市']` / `['2020', '2025']` | `['云南省昆明市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_026` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['广东省佛山市']` / `['2020', '2025']` | `['广东省佛山市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_027` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": false} | `['江苏省南通市']` / `['2020', '2023']` | `['江苏省南通市']` / `['2021', '2022', '2023', '2024', '2025']` |
| `eval50_cd_028` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['山东省青岛市']` / `['2020', '2025']` | `['山东省青岛市']` / `['2023', '2024', '2025', '2026']` |
| `eval50_cd_029` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['湖南省长沙市']` / `['2020', '2025']` | `['湖南省长沙市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_030` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['广东省珠海市']` / `['2020', '2025']` | `['广东省珠海市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_031` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['新疆维吾尔自治区乌鲁木齐市']` / `['2023', '2025']` | `['新疆维吾尔自治区乌鲁木齐市']` / `['2024', '2025']` |
| `eval50_cd_032` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['福建省福州市']` / `['2020', '2023']` | `['福建省福州市']` / `['2021', '2022', '2023', '2024', '2025']` |
| `eval50_cd_033` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['甘肃省兰州市']` / `['2022', '2025']` | `['甘肃省兰州市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_036` | True | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": false} | `['广东省深圳市南山区']` / `['2024']` | `['广东省深圳市南山区']` / `['2024']` |
| `eval50_cd_038` | True | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": false} | `['湖北省武汉市']` / `['2025']` | `['湖北省武汉市']` / `['2025']` |
| `eval50_cd_042` | True | {"intent_match": false, "regions_match": true, "time_range_match": true, "target_object_match": false} | `['福建省厦门市']` / `['2024']` | `['福建省厦门市']` / `['2024']` |
| `eval50_cd_044` | True | {"intent_match": true, "regions_match": true, "time_range_match": true, "target_object_match": false} | `['辽宁省沈阳市']` / `['2023']` | `['辽宁省沈阳市']` / `['2023']` |
| `eval50_cd_047` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2025']` | `['河南省郑州市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cd_050` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['湖北省武汉市']` / `['2020', '2025']` | `['湖北省武汉市']` / `['2022', '2023', '2024', '2025', '2026']` |
| `eval50_cc_001` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['四川省成都市']` / `['2020']` | `[]` / `['2020']` |
| `eval50_cc_002` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": false} | `['广东省深圳市']` / `['2021']` | `[]` / `['2021']` |
| `eval50_cc_003` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['湖北省武汉市']` / `['2022']` | `[]` / `['2022']` |
| `eval50_cc_004` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['浙江省杭州市']` / `['2023']` | `[]` / `['2023']` |
| `eval50_cc_005` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": false} | `['江苏省南京市']` / `['2024']` | `[]` / `['2024']` |
| `eval50_cc_006` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['河南省郑州市']` / `['2025']` | `[]` / `['2025']` |
| `eval50_cc_007` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['福建省厦门市']` / `['2021']` | `[]` / `['2021']` |
| `eval50_cc_008` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['山东省济南市']` / `['2022']` | `[]` / `['2022']` |
| `eval50_cc_009` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['辽宁省沈阳市']` / `['2020']` | `[]` / `['2020']` |
| `eval50_cc_010` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": false} | `['陕西省西安市']` / `['2024']` | `[]` / `['2024']` |
| `eval50_cc_011` | True | {"intent_match": true, "regions_match": false, "time_range_match": true, "target_object_match": true} | `['云南省昆明市']` / `['2023']` | `[]` / `['2023']` |

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

