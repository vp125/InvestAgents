"""Shared utilities for InvestAgents: tool implementations, message helpers,
and language instruction injection.

Tools are registered as @tool-decorated functions — the LangGraph ToolNode wraps
them automatically so LLM agents can invoke them via tool_calls.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.tools import tool

from invest_agents.dataflows.interface import route
from invest_agents.dataflows.config import get_config


# ---------------------------------------------------------------------------
# Language helper (mirrors TradingAgents pattern)
# ---------------------------------------------------------------------------


def get_language_instruction() -> str:
    """Return prompt instruction for non-English output, or empty string."""
    lang = get_config().get("output_language", "English")
    if lang.strip().lower() == "english":
        return ""
    return f" Write your entire response in {lang}."


# ---------------------------------------------------------------------------
# Instrument context
# ---------------------------------------------------------------------------


def build_instrument_context(ticker: str) -> str:
    """Tell the agent exactly which instrument to work with."""
    return (
        f"The company to analyze is `{ticker}`. "
        "Use this exact ticker in every tool call, report, and recommendation, "
        "preserving any exchange suffix (e.g. `.TO`, `.L`, `.HK`, `.T`)."
    )


# ---------------------------------------------------------------------------
# Tool: Price History
# ---------------------------------------------------------------------------


@tool
def get_price_history(
    symbol: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date yyyy-mm-dd"],
    end_date: Annotated[str, "End date yyyy-mm-dd"],
) -> str:
    """Fetch multi-year OHLCV price data for trend & volatility analysis."""
    return route("get_price_history", symbol=symbol, start_date=start_date, end_date=end_date)


# ---------------------------------------------------------------------------
# Tools: Financial Statements
# ---------------------------------------------------------------------------


@tool
def get_income_statement(
    symbol: Annotated[str, "Ticker symbol"],
    years: Annotated[int, "Years of history"] = 7,
) -> str:
    """Fetch annual income statements for multi-year margin/earnings analysis."""
    return route("get_income_statement", symbol=symbol, years=years)


@tool
def get_balance_sheet(
    symbol: Annotated[str, "Ticker symbol"],
    years: Annotated[int, "Years of history"] = 7,
) -> str:
    """Fetch annual balance sheets for capital structure & asset quality analysis."""
    return route("get_balance_sheet", symbol=symbol, years=years)


@tool
def get_cashflow(
    symbol: Annotated[str, "Ticker symbol"],
    years: Annotated[int, "Years of history"] = 7,
) -> str:
    """Fetch annual cash flow statements for FCF yield & capex analysis."""
    return route("get_cashflow", symbol=symbol, years=years)


# ---------------------------------------------------------------------------
# Tools: Key Metrics & Valuation
# ---------------------------------------------------------------------------


@tool
def get_key_metrics(
    symbol: Annotated[str, "Ticker symbol"],
) -> str:
    """Fetch key financial metrics: P/E, P/B, ROE, margins, growth rates, etc."""
    return route("get_key_metrics", symbol=symbol)


@tool
def get_roe_roic_trends(
    symbol: Annotated[str, "Ticker symbol"],
) -> str:
    """Fetch ROE/ROIC trends over time for moat/quality assessment."""
    return route("get_roe_roic_trends", symbol=symbol)


# ---------------------------------------------------------------------------
# Tools: SEC Filings
# ---------------------------------------------------------------------------


@tool
def get_10k_filing(
    symbol: Annotated[str, "Ticker symbol"],
    sections: Annotated[str, "Comma-separated sections: business,risk,mdna,financial"] = "business,risk,mdna",
) -> str:
    """Fetch and extract sections from the most recent 10-K annual filing."""
    return route("get_10k_filing", symbol=symbol, sections=sections)


@tool
def get_10q_filing(
    symbol: Annotated[str, "Ticker symbol"],
    sections: Annotated[str, "Comma-separated sections: risk,mdna,financial"] = "mdna,financial",
) -> str:
    """Fetch and extract sections from the most recent 10-Q quarterly filing."""
    return route("get_10q_filing", symbol=symbol, sections=sections)


# ---------------------------------------------------------------------------
# Tools: Macro Data
# ---------------------------------------------------------------------------


@tool
def get_interest_rates(
    days_back: Annotated[int, "Days of history"] = 365,
) -> str:
    """Fetch Fed Funds rate, Treasury yields, mortgage rates."""
    return route("get_interest_rates", days_back=days_back)


@tool
def get_gdp_growth(
    days_back: Annotated[int, "Days of history"] = 365 * 5,
) -> str:
    """Fetch GDP levels and growth rates."""
    return route("get_gdp_growth", days_back=days_back)


@tool
def get_inflation_data(
    days_back: Annotated[int, "Days of history"] = 365 * 3,
) -> str:
    """Fetch CPI, Core CPI, PCE inflation data."""
    return route("get_inflation_data", days_back=days_back)


@tool
def get_unemployment_data(
    days_back: Annotated[int, "Days of history"] = 365 * 3,
) -> str:
    """Fetch unemployment rate and labor market indicators."""
    return route("get_unemployment_data", days_back=days_back)


# ---------------------------------------------------------------------------
# Tools: News & Insider
# ---------------------------------------------------------------------------


@tool
def get_company_news(
    symbol: Annotated[str, "Ticker symbol"],
    count: Annotated[int, "Number of articles"] = 10,
) -> str:
    """Fetch recent company-specific news."""
    return route("get_company_news", symbol=symbol, count=count)


@tool
def get_insider_trades(
    symbol: Annotated[str, "Ticker symbol"],
) -> str:
    """Fetch recent insider buy/sell transactions."""
    return route("get_insider_trades", symbol=symbol)


# ---------------------------------------------------------------------------
# Message management
# ---------------------------------------------------------------------------


def create_msg_delete():
    """Create a node that clears the message stack (for Anthropic compat)."""

    def delete_messages(state):
        messages = state["messages"]
        removal_ops = [RemoveMessage(id=m.id) for m in messages]
        placeholder = HumanMessage(content="Continue")
        return {"messages": removal_ops + [placeholder]}

    return delete_messages
