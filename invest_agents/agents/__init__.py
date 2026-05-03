"""Agent creator functions for InvestAgents.

Each function takes an LLM and returns a LangGraph-compatible node function.
"""

from .analysts.moat_analyst import create_moat_analyst
from .analysts.valuation_analyst import create_valuation_analyst
from .analysts.growth_analyst import create_growth_analyst
from .analysts.macro_analyst import create_macro_analyst
from .researchers.bull_researcher import create_bull_researcher
from .researchers.bear_researcher import create_bear_researcher
from .managers.thesis_manager import create_thesis_manager
from .managers.portfolio_constructor import create_portfolio_constructor

__all__ = [
    "create_moat_analyst",
    "create_valuation_analyst",
    "create_growth_analyst",
    "create_macro_analyst",
    "create_bull_researcher",
    "create_bear_researcher",
    "create_thesis_manager",
    "create_portfolio_constructor",
]
