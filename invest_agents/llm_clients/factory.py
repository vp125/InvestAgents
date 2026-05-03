"""Minimal LLM client factory supporting OpenAI, Anthropic, Google, DeepSeek.

Reuses langchain_* community integrations.  Each provider-specific module
returns a simple wrapper with a `get_llm()` method that returns a
LangChain BaseChatModel.

For a more comprehensive provider catalog, copy the full llm_clients/
from TradingAgents — it's API-compatible.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


class _LLMClient:
    """Thin wrapper around a LangChain chat model."""

    def __init__(self, llm: Any):
        self._llm = llm

    def get_llm(self) -> Any:
        return self._llm


def _create_openai(model: str, base_url: str = None, **kwargs) -> _LLMClient:
    """Create OpenAI / OpenAI-compatible client."""
    from langchain_openai import ChatOpenAI

    api_key = os.getenv("OPENAI_API_KEY", "")
    client_kwargs = {"model": model, "api_key": api_key, "temperature": 0.3}
    if base_url:
        client_kwargs["base_url"] = base_url
    client_kwargs.update(kwargs)
    return _LLMClient(ChatOpenAI(**client_kwargs))


def _create_anthropic(model: str, **kwargs) -> _LLMClient:
    """Create Anthropic Claude client."""
    from langchain_anthropic import ChatAnthropic

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    return _LLMClient(ChatAnthropic(
        model=model,
        api_key=api_key,
        temperature=0.3,
        max_tokens=4096,
        **kwargs,
    ))


def _create_google(model: str, **kwargs) -> _LLMClient:
    """Create Google Gemini client."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    api_key = os.getenv("GOOGLE_API_KEY", "")
    return _LLMClient(ChatGoogleGenerativeAI(
        model=model,
        google_api_key=api_key,
        temperature=0.3,
        **kwargs,
    ))


def _create_deepseek(model: str, base_url: str = None, **kwargs) -> _LLMClient:
    """Create DeepSeek client (OpenAI-compatible endpoint)."""
    api_key = os.getenv("DEEPSEEK_API_KEY", "")
    base = base_url or "https://api.deepseek.com/v1"
    return _create_openai(
        model=model,
        base_url=base,
        api_key=api_key,
        **kwargs,
    )


# Registry
_PROVIDER_MAP = {
    "openai": _create_openai,
    "anthropic": _create_anthropic,
    "google": _create_google,
    "deepseek": _create_deepseek,
    # Additional providers from TradingAgents can be added here:
    # "xai": _create_xai,
    # "qwen": _create_qwen,
    # "glm": _create_glm,
    # "ollama": _create_ollama,  # local models
    # "azure": _create_azure,
    # "openrouter": _create_openrouter,
}


def create_llm_client(
    provider: str,
    model: str,
    base_url: str = None,
    **kwargs,
) -> _LLMClient:
    """Create an LLM client for the given provider and model.

    Args:
        provider: Provider name (openai, anthropic, google, deepseek, ...)
        model: Model name (e.g., gpt-5.4, claude-sonnet-4-20250514)
        base_url: Override API endpoint (for proxies / compatible APIs)
        **kwargs: Passed through to the LangChain chat model constructor.
    """
    provider = provider.lower().strip()
    factory = _PROVIDER_MAP.get(provider)
    if factory is None:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {list(_PROVIDER_MAP.keys())}"
        )
    return factory(model=model, base_url=base_url, **kwargs)
