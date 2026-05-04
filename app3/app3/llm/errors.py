from __future__ import annotations


class LLMConfigError(RuntimeError):
    """Raised when API keys / base URL / model are missing or invalid."""


class LLMInvocationError(RuntimeError):
    """Raised when the chat model call fails (timeout, 429, etc.)."""
