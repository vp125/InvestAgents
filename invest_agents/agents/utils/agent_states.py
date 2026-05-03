"""Agent state definitions for InvestAgents LangGraph.

The state flows through two phases:
  1. STOCK DEEP-DIVE: analysts → debate → thesis
  2. PORTFOLIO CONSTRUCTION: aggregate theses → allocations
"""

from __future__ import annotations

from typing import Annotated, List, TypedDict
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class ThesisDebateState(TypedDict):
    """State for the bull/bear debate phase."""

    history: str          # Full debate transcript
    bull_history: str     # Only bull arguments
    bear_history: str     # Only bear arguments
    current_response: str  # Latest argument (starts with "Bull" or "Bear")
    count: int            # Number of exchanges (2 per round)


class AgentState(TypedDict):
    """Top-level state flowing through the entire stock analysis graph."""

    # Identity
    company_of_interest: str
    trade_date: str                      # Date of analysis

    # Message stack (managed by LangGraph)
    messages: Annotated[List[BaseMessage], add_messages]

    # Analyst reports (filled in sequence by each analyst)
    moat_report: str
    valuation_report: str
    growth_report: str
    macro_report: str

    # Debate state
    thesis_debate_state: ThesisDebateState

    # Manager outputs
    investment_thesis: str              # Rendered InvestmentThesis markdown
    investment_thesis_structured: dict  # Raw dict for programmatic use

    # Portfolio construction (populated after all stocks analyzed)
    past_context: str                   # Memory log context for thesis manager


class PortfolioState(TypedDict):
    """State for the portfolio construction phase."""

    date: str
    active_theses: List[dict]           # List of thesis dicts for candidate stocks
    macro_context: str                  # Macro data for sector overlay
    portfolio_result: str               # Rendered PortfolioConstructionResult markdown
