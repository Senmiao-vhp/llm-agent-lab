# app3 llm-agent-lab

学习导向的 **LangGraph** + **LangChain 工具**（技能）。

## 安装

```bash
cd llm-agent-lab/app3
pip install -e .
```

## 运行

```bash
python -m app3 "你的问题"
```

没有 `OPENAI_API_KEY` 时，图会在 `parse` 后停止，并在状态中设置 `fatal_error`（按设计）。

## 项目结构

| 路径 | 功能 |
|------|------|
| `app3/graph/` | `StateGraph` (`builder.py`), `edges.py`, `constants.py`, `context.py` |
| `app3/state/` | `AgentState`, `build_initial_state` |
| `app3/nodes/` | 节点存根 (`parse` … `explain`, `handle_error`) |
| `app3/skills/` | GIS 占位符工具 |
| `app3/runtime/` | `GraphSession.invoke` / `stream` |


## 测试

```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
