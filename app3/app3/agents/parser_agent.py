"""解析门面：仅用大模型结构化产出 CompositeQuery；失败由调用方处理为致命错误。"""

from __future__ import annotations

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app3.contracts.query import CompositeQuery


def parse_composite_query(user_text: str, llm: BaseChatModel) -> CompositeQuery:
    """
    调用 `with_structured_output(CompositeQuery)`。
    失败时抛出异常，由 `parse_node` 转为 fatal（不做占位结果）。
    """
    text = (user_text or "").strip()
    structured = llm.with_structured_output(CompositeQuery)
    out = structured.invoke([HumanMessage(content=text or "(empty)")])
    if not isinstance(out, CompositeQuery):
        raise TypeError(f"structured parse returned {type(out)!r}, expected CompositeQuery")
    if not (out.original_query or "").strip():
        out = out.model_copy(update={"original_query": text})
    return out
