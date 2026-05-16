# 210 例评测 · 按指标类别的错误样本与金标对照

数据源：本目录 `results.jsonl`（与 `eval_report.md` 同次运行）。


## 1. 端到端失败（`task_success = false`）

条数：**0**

（无）


## 2. 意图不一致（`intent_match = false`）

条数：**22**

| sample_id | 金标 vs 预测（本项） | task_success |
|-------------|----------------------|--------------|
| `eval210_cd_004` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_006` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_007` | 意图 金标 `change_detection` vs 预测 `current_status_estimate` （子查询数 1） | True |
| `eval210_cd_010` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_011` | 意图 金标 `change_detection` vs 预测 `transfer_analysis` （子查询数 1） | True |
| `eval210_cd_014` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_019` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_020` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_021` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_023` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_026` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_028` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_029` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |
| `eval210_cd_030` | 意图 金标 `change_detection` vs 预测 `trend_evolution` （子查询数 1） | True |



## 3. 行政区不一致（`regions_match = false`）

条数：**0**

（无）

## 4. 时间范围不一致（`time_range_match = false`）

条数：**2**

| sample_id | task_success | checks | 金标 regions / time | 预测 regions / time |
|-------------|--------------|--------|---------------------|---------------------|
| `eval210_cd_003` | True | {"intent_match": true, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河北省保定市容城县']` / `['2020', '2021', '2022', '2023', '2024']` | `['河北省保定市容城县']` / `['2020', '2024']` |
| `eval210_cd_008` | True | {"intent_match": false, "regions_match": true, "time_range_match": false, "target_object_match": true} | `['河南省郑州市']` / `['2020', '2021', '2022', '2023']` | `['河南省郑州市']` / `['2020', '2023']` |

## 5. 目标对象不一致（`target_object_match = false`）

条数：**0**

（无）
