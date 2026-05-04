# llm-agent-lab

个人学习与实验仓库：LangGraph + LangChain Tools（app3 包），与 `farmland-monitoring/app2` **无代码依赖**。

## 目录

| 路径 | 说明 |
|------|------|
| [`app3/`](app3/) | Python 包 `app3`，含图编排、节点占位、GIS 占位 Skill、冒烟测试 |

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

推送至 Gitee/GitHub 后，工作流在 `app3` 目录执行安装与单元测试。若在 Gitee 未自动运行，可在「流水线 / Jenkins」中配置等价命令：`cd app3 && pip install -e . && python -m unittest discover -s tests -v`。
