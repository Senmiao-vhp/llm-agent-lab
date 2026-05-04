# llm-agent-lab

个人学习与实验仓库：LangGraph + LangChain Tools（app3 包），与 `farmland-monitoring/app2` **无代码依赖**。

## 目录

| 路径 | 说明 |
|------|------|
| [`app3/`](app3/) | Python 包 `app3`：图编排、错误子系统（`app3/errors`）、`delay` 退避、GIS 占位 Skill、测试 |

补充说明见 [`app3/STABILITY_REVIEW.md`](app3/STABILITY_REVIEW.md)。

## 分支约定

| 分支 | 用途 |
|------|------|
| `main` | 默认可发布 / 稳定快照 |
| `develop` | 日常开发与合并目标 |

功能开发建议：`develop` 上开 `feature/*`，合并回 `develop`；发布时再合入 `main`。

## 本地运行（app3）

```bash
cd app3
pip install -e .
python -m unittest discover -s tests -v
```

## CI

- **GitHub Actions**：见 [`.github/workflows/ci.yml`](.github/workflows/ci.yml)（`push` 到 `main` / `develop` 时在 `app3` 下执行测试）。
- **Gitee Go**：**不会**自动跑上述 workflow。请在「Python 构建 / 编译」中执行：
  - `bash scripts/ci_gitee.sh`，或
  - `make test`（需已安装 `make`），或
  - 手动：`cd app3 && pip install -e . && python -m unittest discover -s tests -p "test_*.py" -v`

若流水线仍只认 `requirements.txt`：仓库根目录已提供 [requirements.txt](requirements.txt)（内容仅为 `-e ./app3`），**在仓库根执行** `pip install -r requirements.txt` 即会按 `app3/pyproject.toml` 安装依赖与可编辑包。

**Gitee 编译阶段常见失败原因**

1. 在**仓库根目录**误执行 `pip install -e .`：根目录无独立包定义；请改用 **`pip install -r requirements.txt`**（会安装 `-e ./app3`），或 `cd app3 && pip install -e .`。
2. 构建机 **Python 版本低于 3.11**：`app3/pyproject.toml` 要求 `requires-python = ">=3.11"`。
3. 拉取 PyPI 依赖**超时**（约 3 分钟仍停在 `Collecting` 或 `ReadTimeout`）：可换国内镜像或调大 pip 超时。

若仍失败，请在 Gitee 打开 **「Python 构建」** 步骤的**完整日志**，查看第一条 `Error` / `Traceback`。
