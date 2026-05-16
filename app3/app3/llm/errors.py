from __future__ import annotations


class LLMConfigError(RuntimeError):
    """当缺少或无效的 API 密钥 / 基础 URL / 模型时抛出。"""


class LLMInvocationError(RuntimeError):
    """当聊天模型调用失败（超时、429 等）时抛出。"""
