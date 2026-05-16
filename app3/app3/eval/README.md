# 论文第六章 app3 小样本评测

## 依赖

- 配置 `llm-agent-lab/app3/.env`：`OPENAI_API_KEY`（及 `OPENAI_BASE_URL` / `MOONSHOT_MODEL` 或 `OPENAI_MODEL` 等，见 `config.py`）。
- **端到端**（默认）：需要 `GEE_PROJECT_ID`（或 `APP3_GEE_PROJECT_ID`）及 `pip install -e ".[gis]"` 等；数据路径见 `APP3_DATA_DIR`。
- **`--parse-only`**：只跑 `parse_node`，**不需要** GEE / GIS 全链路；仍可能调用 Nominatim（见 `APP3_GIS_NOMINATIM`）。
- 金标文件：默认 `data/eval_cases_210.jsonl`（存在时）；否则 `data/paper6_cases.jsonl`；再否则同级 `farmland-monitoring/.../cases.jsonl`；也可 `--cases` 指定路径。

## 命令

在 **`llm-agent-lab/app3`** 目录下（使 `app3` 包可导入）：

```bash
# 端到端：GraphSession.invoke（parse→plan→act→explain）；脚本内强制 gis_use_cache=false
python -m app3.eval.batch --max-cases 30

# 只测 parse 节点（默认金标：优先 data/eval_cases_210.jsonl，否则 paper6 / farmland）
python -m app3.eval.batch --max-cases 30 --parse-only

# 跑满 210 条 parse（须为混合意图金标且关闭主意图过滤）
python -m app3.eval.batch --max-cases 210 --parse-only --no-intent-filter

# 显式指定金标
python -m app3.eval.batch --cases "D:/path/to/cases.jsonl" --max-cases 30

# 完全冷启动（每条子进程）
python -m app3.eval.batch --max-cases 30 --cold-subprocess
python -m app3.eval.batch --max-cases 30 --parse-only --cold-subprocess
```

输出目录：`data/eval_runs/eval_<时间戳>/`，含 `report.json`、`results.jsonl`、`summary.md`、**`eval_report.md`**（完整中文报告）。

也可使用入口：`app3-eval-paper6`（安装 editable 后）。

## 指标与论文对应

| 论文 | `report.json` |
|------|----------------|
| 系统响应时间 | `overall.duration_p50_ms` / `duration_p90_ms`；`parse-only` 时为 **仅 parse 阶段**墙钟 |
| 任务执行成功率 | `overall.success_rate`；`parse-only` 时为 **解析成功**（无 fatal 且产出 `queries`），非 GIS 端到端 |
| 意图 / 空间语义 | `overall.intent_acc`、`overall.slot_acc`；分项见每条 `checks.*` |

## 金标 `data/eval_cases_210.jsonl`

仓库内 **210 行 JSONL**：7 类 `gold.primary_intent` 各 **30** 条（`sample_id` 形如 `eval210_cse_*`、`eval210_cd_*` …），文件内按意图分块排列，便于覆盖与人工修订。年份类金标与 **GlobeLand30 2020** 叙事一致（问句 / `time_range` 中具体年份落在 **2020–2025（含）**）。**无自动生成脚本**，请直接编辑该文件。

跑 210 例 parse 示例（与上一节等价，显式写出 `--cases`）：

```bash
python -m app3.eval.batch --cases data/eval_cases_210.jsonl --max-cases 210 --parse-only --no-intent-filter
```

改完后可再跑 `python data/build_gold_review_html.py` 刷新 `data/eval_runs/samples_raw_210.html`。

## 二期（组件级耗时）

端到端默认使用 `GraphSession.invoke`。若需解析/规划/GIS 分项耗时，可在后续接入 LangGraph `stream_events` 或微基准脚本（见仓库计划）。
