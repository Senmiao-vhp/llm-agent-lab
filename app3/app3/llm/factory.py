"""通过 LangChain 构建 OpenAI 兼容服务器的聊天模型。"""
from __future__ import annotations

from langchain_openai import ChatOpenAI

from app3.config import Settings
from app3.llm.errors import LLMConfigError


def build_chat_model(settings: Settings, *, temperature: float = 0.2) -> ChatOpenAI:
    """创建默认的聊天模型。"""
    if not settings.openai_api_key:
        raise LLMConfigError("OPENAI_API_KEY 未设置。")
    return ChatOpenAI(
        model=settings.default_chat_model,
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        temperature=temperature,
    )
