"""LLM client abstraction for InvestAgents.

Minimal factory that creates LangChain-compatible chat models for each provider.
Heavily inspired by TradingAgents' llm_clients module.
"""

from .factory import create_llm_client

__all__ = ["create_llm_client"]
