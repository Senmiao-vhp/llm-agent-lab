# app3

学习型 LangGraph 智能体骨架：`StateGraph` + LangChain Tools、`MemorySaver`、**fatal/recoverable 子类型**与按子类型的重试 + **`delay` 指数退避**。

详细设计与字段说明见 [`STABILITY_REVIEW.md`](STABILITY_REVIEW.md)。

```bash
pip install -e .
python -m unittest discover -s tests -v
```

本地密钥与 GraphRAG：复制 [`app3/.env.example`](.env.example) 为 **`app3/.env`** 并填写（该文件已列入 `.gitignore`）。可选设置 **`APP3_ENV_FILE`** 指向其它路径；单测会设置 **`APP3_SKIP_ENV_FILE=1`** 跳过加载。

环境变量（可选）：

- `APP3_BACKOFF_MAX_SECONDS`：单次退避上限（秒），默认 120  
- `APP3_BACKOFF_JITTER_RATIO`：相对抖动的比例，默认 0.12  
