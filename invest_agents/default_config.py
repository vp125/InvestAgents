"""Default configuration for InvestAgents — a multi-agent long-term
investment framework for thesis-driven stock analysis and portfolio construction.

Heavily inspired by TradingAgents but re-oriented from short-term tactical
trading toward multi-year thesis-driven investing.
"""

import os

_LT_HOME = os.path.join(os.path.expanduser("~"), ".invest_agents")

DEFAULT_CONFIG = {
    # --- Paths ---
    "project_dir": os.path.abspath(os.path.join(os.path.dirname(__file__), ".")),
    "results_dir": os.getenv(
        "INVESTAGENTS_RESULTS_DIR", os.path.join(_LT_HOME, "results")
    ),
    "data_cache_dir": os.getenv(
        "INVESTAGENTS_CACHE_DIR", os.path.join(_LT_HOME, "cache")
    ),
    "thesis_log_path": os.getenv(
        "INVESTAGENTS_THESIS_LOG_PATH",
        os.path.join(_LT_HOME, "theses", "thesis_memory.md"),
    ),
    # Cap on resolved thesis entries before rotation. None = unlimited.
    "thesis_log_max_entries": None,

    # --- LLM settings ---
    "llm_provider": "openai",           # openai, google, anthropic, deepseek, etc.
    "deep_think_llm": "gpt-5.4",        # For thesis synthesis & portfolio construction
    "quick_think_llm": "gpt-5.4-mini",  # For analyst reports & debate arguments
    "backend_url": None,                # Override API endpoint

    # Provider-specific thinking knobs
    "google_thinking_level": None,
    "openai_reasoning_effort": "high",  # Long-term analysis benefits from deep reasoning
    "anthropic_effort": None,

    # --- Data vendor configuration ---
    # Each category can specify a comma-separated fallback chain.
    # The first available vendor that doesn't rate-limit wins.
    "data_vendors": {
        "price_history":     "yfinance",          # yfinance, alpha_vantage
        "financial_statements": "yfinance",       # yfinance, alpha_vantage, fmp
        "key_metrics":       "yfinance",          # yfinance, alpha_vantage, fmp
        "sec_filings":       "sec_edgar",         # sec_edgar (free, no key needed)
        "macro_data":        "fred",              # fred (free, needs FRED_API_KEY)
        "news_sentiment":    "yfinance",          # yfinance, newsapi
        "insider_transactions": "yfinance",       # yfinance, alpha_vantage
        "earnings_transcripts": "fmp",            # fmp (needs FMP_API_KEY)
    },

    # Per-tool overrides (takes precedence over category-level)
    "tool_vendors": {},

    # --- Analysis depth ---
    "years_of_history": 7,               # Years of financials to pull
    "max_debate_rounds": 2,             # Bull/Bear debate rounds
    "parallel_analysts": True,           # Run Moat/Valuation/Growth/Macro in parallel
    "min_market_cap_billions": 1.0,     # Filter out micro-caps (set 0 to disable)

    # --- Portfolio construction ---
    "max_portfolio_positions": 25,       # Max stocks in portfolio
    "max_single_position_pct": 0.10,    # 10% max per position
    "min_conviction_for_entry": 3,      # 1-5 scale, minimum to enter position
    "rebalance_frequency_months": 3,    # Quarterly review

    # --- Thesis tracking ---
    "thesis_review_frequency_months": 6,  # How often to re-evaluate active theses
    "max_invalid_thesis_age_days": 30,    # How long to keep an invalidated thesis

    # --- Output ---
    "output_language": "English",

    # --- Checkpoint / resume ---
    "checkpoint_enabled": False,
}
