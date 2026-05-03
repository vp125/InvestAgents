"""Structured output helpers for InvestAgents.

Mirrors TradingAgents' pattern: bind native structured-output modes per
provider, with graceful fallback to free-text + rendering.
"""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional, Type

from pydantic import BaseModel

logger = logging.getLogger(__name__)


def bind_structured(llm: Any, schema: Type[BaseModel], agent_name: str = "") -> Any:
    """Attempt to bind structured output to the LLM.

    Uses the provider's native mode when available (json_schema for OpenAI,
    response_schema for Google, tool-use for Anthropic).  Returns the wrapped
    LLM on success, or the original LLM if structured output isn't supported.
    """
    try:
        return llm.with_structured_output(schema)
    except (NotImplementedError, AttributeError, TypeError):
        logger.debug(
            "%s: structured output not available for %s, using free-text fallback",
            agent_name,
            type(llm).__name__,
        )
        return llm


def invoke_structured_or_freetext(
    structured_llm: Any,
    raw_llm: Any,
    prompt: str,
    render_fn: Callable[[BaseModel], str],
    agent_name: str = "",
) -> str:
    """Invoke the LLM, preferring structured output with free-text fallback.

    Returns a markdown string (either rendered from Pydantic or used as-is).
    """
    try:
        result = structured_llm.invoke(prompt)
        if isinstance(result, BaseModel):
            return render_fn(result)
        # Structured output wasn't used — result is a regular message
        return result.content if hasattr(result, "content") else str(result)
    except Exception as e:
        logger.warning(
            "%s: structured invoke failed (%s), falling back to free-text",
            agent_name,
            e,
        )
        fallback = raw_llm.invoke(prompt)
        return fallback.content if hasattr(fallback, "content") else str(fallback)
