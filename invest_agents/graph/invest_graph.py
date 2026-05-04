"""InvestAgentsGraph — the main orchestrator for thesis-driven long-term
stock analysis and portfolio construction.

Usage:
    from invest_agents.graph.invest_graph import InvestAgentsGraph
    from invest_agents.default_config import DEFAULT_CONFIG

    lta = InvestAgentsGraph(config=DEFAULT_CONFIG.copy())

    # Deep-dive one stock
    thesis = lta.analyze_stock("COST", "2025-06-15")
    print(thesis)

    # Build portfolio from multiple theses
    portfolio = lta.build_portfolio(thesis_dicts, macro_context="...")
    print(portfolio)
"""

from __future__ import annotations

import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langgraph.prebuilt import ToolNode

from invest_agents.default_config import DEFAULT_CONFIG
from invest_agents.dataflows.config import set_config
from invest_agents.dataflows.utils import safe_ticker_component

from invest_agents.agents.utils.agent_states import AgentState, ThesisDebateState
from invest_agents.agents.utils.agent_utils import (
    get_price_history,
    get_income_statement,
    get_balance_sheet,
    get_cashflow,
    get_key_metrics,
    get_roe_roic_trends,
    get_10k_filing,
    get_10q_filing,
    get_interest_rates,
    get_gdp_growth,
    get_inflation_data,
    get_unemployment_data,
    get_company_news,
    get_insider_trades,
)

from .setup import DeepDiveGraphSetup, PortfolioGraphSetup
from .conditional_logic import ConditionalLogic

logger = logging.getLogger(__name__)


class InvestAgentsGraph:
    """Orchestrates long-term investment thesis generation & portfolio construction."""

    def __init__(
        self,
        debug: bool = False,
        config: Dict[str, Any] = None,
    ):
        self.debug = debug
        self.config = config or DEFAULT_CONFIG.copy()

        # Make config available to data routing layer
        set_config(self.config)

        # Create cache & results dirs
        os.makedirs(self.config["data_cache_dir"], exist_ok=True)
        os.makedirs(self.config["results_dir"], exist_ok=True)

        # LLM clients — we import here to avoid coupling to specific providers
        from invest_agents.llm_clients.factory import create_llm_client

        provider = self.config.get("llm_provider", "openai")
        deep_model = self.config.get("deep_think_llm", "gpt-5.4")
        quick_model = self.config.get("quick_think_llm", "gpt-5.4-mini")

        deep_client = create_llm_client(
            provider=provider,
            model=deep_model,
            base_url=self.config.get("backend_url"),
        )
        quick_client = create_llm_client(
            provider=provider,
            model=quick_model,
            base_url=self.config.get("backend_url"),
        )

        self.deep_llm = deep_client.get_llm()
        self.quick_llm = quick_client.get_llm()

        # Build tool nodes for each analyst
        self.tool_nodes = self._create_tool_nodes()

        # Conditional logic
        self.conditional = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 2),
        )

        # Graph setups
        self.deep_dive_setup = DeepDiveGraphSetup(
            self.quick_llm,
            self.deep_llm,
            self.tool_nodes,
            self.conditional,
            parallel_analysts=self.config.get("parallel_analysts", True),
        )
        self.portfolio_setup = PortfolioGraphSetup(self.deep_llm)

        # Compile graphs
        self.deep_dive_workflow = self.deep_dive_setup.setup_graph()
        self.deep_dive_graph = self.deep_dive_workflow.compile()
        self.portfolio_workflow = self.portfolio_setup.setup_graph()
        self.portfolio_graph = self.portfolio_workflow.compile()

    # ------------------------------------------------------------------
    # Tool nodes
    # ------------------------------------------------------------------

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create per-analyst ToolNodes with the right tool sets."""
        return {
            "moat": ToolNode([
                get_key_metrics,
                get_roe_roic_trends,
                get_income_statement,
                get_balance_sheet,
                get_cashflow,
                get_10k_filing,
            ]),
            "valuation": ToolNode([
                get_price_history,
                get_key_metrics,
                get_income_statement,
                get_balance_sheet,
                get_cashflow,
            ]),
            "growth": ToolNode([
                get_key_metrics,
                get_income_statement,
                get_cashflow,
                get_10k_filing,
                get_company_news,
            ]),
            "macro": ToolNode([
                get_interest_rates,
                get_gdp_growth,
                get_inflation_data,
                get_unemployment_data,
                get_10k_filing,
                get_key_metrics,
                get_company_news,
            ]),
        }

    # ------------------------------------------------------------------
    # Stock deep-dive
    # ------------------------------------------------------------------

    def analyze_stock(
        self,
        ticker: str,
        analysis_date: str = None,
    ) -> Tuple[Dict, str]:
        """Run the full deep-dive analysis for a single stock.

        Returns (final_state_dict, thesis_markdown_string).
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        initial_state: AgentState = {
            "company_of_interest": ticker,
            "trade_date": analysis_date,
            "messages": [],
            "moat_report": "",
            "valuation_report": "",
            "growth_report": "",
            "macro_report": "",
            "thesis_debate_state": ThesisDebateState(
                history="",
                bull_history="",
                bear_history="",
                current_response="",
                current_bull_response="",
                current_bear_response="",
                count=0,
            ),
            "investment_thesis": "",
            "investment_thesis_structured": {},
            "past_context": "",
        }

        if self.debug:
            trace = []
            for chunk in self.deep_dive_graph.stream(initial_state):
                if chunk.get("messages") and len(chunk["messages"]) > 0:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)
            final_state = trace[-1] if trace else initial_state
        else:
            final_state = self.deep_dive_graph.invoke(initial_state)

        # Persist to disk
        self._save_thesis(ticker, analysis_date, final_state)

        thesis = final_state.get("investment_thesis", "")
        return final_state, thesis

    # ------------------------------------------------------------------
    # Portfolio construction
    # ------------------------------------------------------------------

    def build_portfolio(
        self,
        theses: List[Dict],
        macro_context: str = "",
        date: str = None,
    ) -> str:
        """Build a portfolio from multiple stock theses.

        Args:
            theses: List of thesis dicts (from analyze_stock or manual).
            macro_context: Macro data / context string.
            date: Portfolio construction date.

        Returns:
            Portfolio construction result as markdown string.
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        # If macro_context not provided, try to pull it
        if not macro_context:
            macro_context = self._gather_macro_context()

        initial_state = {
            "date": date,
            "active_theses": theses,
            "macro_context": macro_context,
            "portfolio_result": "",
        }

        if self.debug:
            for chunk in self.portfolio_graph.stream(initial_state):
                if chunk:
                    for v in chunk.values():
                        if isinstance(v, str) and v:
                            print(v[:500])
            final_state = self.portfolio_graph.invoke(initial_state)
        else:
            final_state = self.portfolio_graph.invoke(initial_state)

        result = final_state.get("portfolio_result", "")
        return result

    # ------------------------------------------------------------------
    # Batch: analyze multiple stocks → build portfolio
    # ------------------------------------------------------------------

    def run_full_cycle(
        self,
        tickers: List[str],
        analysis_date: str = None,
    ) -> Tuple[List[Dict], str]:
        """Run deep-dive on each ticker, then build the portfolio.

        Returns (list_of_thesis_dicts, portfolio_markdown).
        """
        if analysis_date is None:
            analysis_date = datetime.now().strftime("%Y-%m-%d")

        theses = []
        for ticker in tickers:
            logger.info("Analyzing %s...", ticker)
            state, thesis_md = self.analyze_stock(ticker, analysis_date)
            theses.append({
                "ticker": ticker,
                "date": analysis_date,
                "thesis_markdown": thesis_md,
            })

        macro = self._gather_macro_context()
        portfolio = self.build_portfolio(theses, macro_context=macro, date=analysis_date)

        return theses, portfolio

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _gather_macro_context(self) -> str:
        """Pull current macro data for portfolio construction overlay."""
        parts = []
        try:
            parts.append(get_interest_rates(days_back=365))
        except Exception:
            pass
        try:
            parts.append(get_inflation_data(days_back=365 * 3))
        except Exception:
            pass
        try:
            parts.append(get_gdp_growth(days_back=365 * 3))
        except Exception:
            pass
        try:
            parts.append(get_unemployment_data(days_back=365 * 2))
        except Exception:
            pass
        return "\n\n".join(parts)

    def _save_thesis(
        self, ticker: str, date: str, state: Dict
    ) -> None:
        """Persist thesis + reports to disk."""
        safe_ticker = safe_ticker_component(ticker)
        directory = (
            Path(self.config["results_dir"])
            / safe_ticker
            / "thesis_logs"
        )
        directory.mkdir(parents=True, exist_ok=True)

        log_data = {
            "ticker": ticker,
            "date": date,
            "moat_report": state.get("moat_report", ""),
            "valuation_report": state.get("valuation_report", ""),
            "growth_report": state.get("growth_report", ""),
            "macro_report": state.get("macro_report", ""),
            "debate_history": state.get("thesis_debate_state", {}).get("history", ""),
            "investment_thesis": state.get("investment_thesis", ""),
        }

        log_path = directory / f"thesis_{date}.json"
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump(log_data, f, indent=2, default=str)
