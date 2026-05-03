"""Multi-source data routing layer.

Extends TradingAgents' vendor-fallback pattern to support the richer data
categories needed for long-term thesis-driven investing:
  - SEC EDGAR (10-K, 10-Q filings — free, no API key)
  - FRED (macro data — free with API key)
  - FMP (financial statements, transcripts, key metrics)
  - yfinance (price history, basic financials — free, no key)
  - Alpha Vantage (technicals, fundamentals, news)

Each data category declares a fallback chain; the router tries each vendor
in order and returns the first non-rate-limited response.
"""

from typing import Any, Dict, List

from .config import get_config

# ---------------------------------------------------------------------------
# Lazy vendor loading — sources self-register into VENDOR_REGISTRY on import.
# We import them once on first use to avoid circular imports at module level.
# ---------------------------------------------------------------------------
_vendors_loaded = False


def _ensure_vendors_loaded() -> None:
    """Import all data source modules so they register into VENDOR_REGISTRY."""
    global _vendors_loaded
    if _vendors_loaded:
        return
    from . import yfinance_source    # noqa: F401
    from . import sec_edgar_source   # noqa: F401
    from . import fred_source        # noqa: F401
    _vendors_loaded = True

# ---------------------------------------------------------------------------
# Tool → category mapping
# ---------------------------------------------------------------------------

TOOL_CATEGORIES: Dict[str, str] = {
    # price_history
    "get_price_history": "price_history",
    # financial_statements
    "get_income_statement": "financial_statements",
    "get_balance_sheet": "financial_statements",
    "get_cashflow": "financial_statements",
    # key_metrics
    "get_key_metrics": "key_metrics",
    "get_valuation_multiples": "key_metrics",
    "get_roe_roic_trends": "key_metrics",
    # sec_filings
    "get_10k_filing": "sec_filings",
    "get_10q_filing": "sec_filings",
    # macro_data
    "get_interest_rates": "macro_data",
    "get_gdp_growth": "macro_data",
    "get_inflation_data": "macro_data",
    "get_unemployment_data": "macro_data",
    # news_sentiment
    "get_company_news": "news_sentiment",
    "get_sector_news": "news_sentiment",
    # insider_transactions
    "get_insider_trades": "insider_transactions",
    # earnings_transcripts
    "get_earnings_transcript": "earnings_transcripts",
}

# ---------------------------------------------------------------------------
# Vendor implementations registry
# ---------------------------------------------------------------------------

VENDOR_REGISTRY: Dict[str, Dict[str, Any]] = {}


def register_vendor(vendor_name: str, methods: Dict[str, Any]) -> None:
    """Register a vendor's method implementations."""
    VENDOR_REGISTRY[vendor_name] = methods


def get_vendor_chain(tool_name: str) -> List[str]:
    """Return the ordered vendor chain for a tool, respecting config overrides."""
    _ensure_vendors_loaded()
    config = get_config()

    # 1. Per-tool override wins
    tool_vendors = config.get("tool_vendors", {})
    if tool_name in tool_vendors:
        return [v.strip() for v in tool_vendors[tool_name].split(",")]

    # 2. Category-level config
    category = TOOL_CATEGORIES.get(tool_name)
    if category:
        data_vendors = config.get("data_vendors", {})
        if category in data_vendors:
            return [v.strip() for v in data_vendors[category].split(",")]

    # 3. Fall back to all registered vendors
    return list(VENDOR_REGISTRY.keys())


class DataUnavailableError(Exception):
    """Raised when no vendor can fulfil a data request."""


class VendorRateLimitError(Exception):
    """Raised when a vendor hits a rate limit (triggers fallback)."""


def route(tool_name: str, *args: Any, **kwargs: Any) -> Any:
    """Route a data call through the vendor fallback chain.

    Tries each vendor in the configured chain.  ``VendorRateLimitError``
    triggers the next fallback; any other exception propagates immediately.
    """
    _ensure_vendors_loaded()
    vendors = get_vendor_chain(tool_name)

    for vendor in vendors:
        if vendor not in VENDOR_REGISTRY:
            continue
        impl = VENDOR_REGISTRY[vendor].get(tool_name)
        if impl is None:
            continue

        try:
            return impl(*args, **kwargs)
        except VendorRateLimitError:
            continue  # try next vendor
        except Exception:
            raise  # real error — don't silently swallow

    raise DataUnavailableError(
        f"No vendor in chain {vendors!r} could fulfil '{tool_name}'"
    )
