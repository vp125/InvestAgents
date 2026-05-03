#!/usr/bin/env python3
"""InvestAgents — multi-agent LLM framework for long-term stock investing.

Quick start:
    python main.py COST AAPL MSFT

Or run a full cycle with multiple stocks + portfolio construction:
    python main.py COST GOOGL BRK.B V JPM

Environment variables needed:
    OPENAI_API_KEY (or ANTHROPIC_API_KEY, GOOGLE_API_KEY, DEEPSEEK_API_KEY)
    FRED_API_KEY (optional, for macro data)
"""

import sys
import logging

from dotenv import load_dotenv

from invest_agents.graph.invest_graph import InvestAgentsGraph
from invest_agents.default_config import DEFAULT_CONFIG

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("investagents.main")


def main():
    if len(sys.argv) < 2:
        print("Usage: python main.py TICKER [TICKER ...]")
        print("Example: python main.py COST GOOGL BRK.B")
        sys.exit(1)

    tickers = [t.upper() for t in sys.argv[1:]]

    # Configure for long-term analysis
    config = DEFAULT_CONFIG.copy()
    config["max_debate_rounds"] = 2
    config["years_of_history"] = 7
    config["openai_reasoning_effort"] = "high"

    # Override provider/model via env if set
    import os
    if os.getenv("INVESTAGENTS_LLM_PROVIDER"):
        config["llm_provider"] = os.getenv("INVESTAGENTS_LLM_PROVIDER")
    if os.getenv("INVESTAGENTS_DEEP_MODEL"):
        config["deep_think_llm"] = os.getenv("INVESTAGENTS_DEEP_MODEL")
    if os.getenv("INVESTAGENTS_QUICK_MODEL"):
        config["quick_think_llm"] = os.getenv("INVESTAGENTS_QUICK_MODEL")

    logger.info("Initializing InvestAgents (provider=%s, deep=%s, quick=%s)...",
                config["llm_provider"], config["deep_think_llm"], config["quick_think_llm"])

    lta = InvestAgentsGraph(debug=True, config=config)

    # --- PHASE 1: Stock Deep-Dives ---
    all_theses = []
    for ticker in tickers:
        logger.info("=" * 60)
        logger.info("ANALYZING: %s", ticker)
        logger.info("=" * 60)

        state, thesis = lta.analyze_stock(ticker)

        print("\n" + "=" * 60)
        print(f"THESIS: {ticker}")
        print("=" * 60)
        print(thesis)
        print()

        all_theses.append({
            "ticker": ticker,
            "thesis_markdown": thesis,
            "conviction": "N/A",  # Would parse from structured output in production
        })

    # --- PHASE 2: Portfolio Construction ---
    if len(all_theses) >= 2:
        logger.info("=" * 60)
        logger.info("BUILDING PORTFOLIO FROM %d THESES", len(all_theses))
        logger.info("=" * 60)

        portfolio = lta.build_portfolio(all_theses)

        print("\n" + "=" * 60)
        print("PORTFOLIO CONSTRUCTION")
        print("=" * 60)
        print(portfolio)
        print()

    logger.info("Done! Results saved to %s", config["results_dir"])


if __name__ == "__main__":
    main()
