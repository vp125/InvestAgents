"""yfinance data source — price history, financial statements, news, insider trades.

Free, no API key required.  Used as the default vendor for most categories
because of zero-friction setup.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated

import pandas as pd
import yfinance as yf

from .interface import register_vendor, VendorRateLimitError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _retry(func, max_attempts=3):
    """Simple retry wrapper around yfinance calls (network can be flaky)."""
    import time

    for attempt in range(max_attempts):
        try:
            return func()
        except Exception:
            if attempt == max_attempts - 1:
                raise
            time.sleep(1.0 * (attempt + 1))


def _df_to_csv(df: pd.DataFrame, header: str = "") -> str:
    """Convert DataFrame to CSV string with optional header."""
    if df.empty:
        return f"{header}# No data available\n"
    csv = df.to_csv()
    return f"{header}{csv}"


# ---------------------------------------------------------------------------
# Price history
# ---------------------------------------------------------------------------


def get_price_history(
    symbol: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date yyyy-mm-dd"],
    end_date: Annotated[str, "End date yyyy-mm-dd"],
) -> str:
    """Fetch OHLCV price history from yfinance."""
    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    ticker = yf.Ticker(symbol.upper())
    data = _retry(lambda: ticker.history(start=start_date, end=end_date))

    if data.empty:
        return f"No price data found for {symbol.upper()} [{start_date} → {end_date}]"

    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    for col in ["Open", "High", "Low", "Close", "Adj Close"]:
        if col in data.columns:
            data[col] = data[col].round(2)

    header = (
        f"# Price history: {symbol.upper()} | {start_date} → {end_date}\n"
        f"# Records: {len(data)}\n\n"
    )
    return _df_to_csv(data, header)


# ---------------------------------------------------------------------------
# Financial statements (annual + quarterly)
# ---------------------------------------------------------------------------


def get_income_statement(
    symbol: Annotated[str, "Ticker symbol"],
    years: Annotated[int, "Years of history to fetch"] = 5,
) -> str:
    """Fetch annual income statements."""
    ticker = yf.Ticker(symbol.upper())
    data = _retry(lambda: ticker.income_stmt)
    if data is None or data.empty:
        return f"No income statement data for {symbol.upper()}"
    return _df_to_csv(data, f"# Income Statement: {symbol.upper()}\n\n")


def get_balance_sheet(
    symbol: Annotated[str, "Ticker symbol"],
    years: Annotated[int, "Years of history to fetch"] = 5,
) -> str:
    """Fetch annual balance sheets."""
    ticker = yf.Ticker(symbol.upper())
    data = _retry(lambda: ticker.balance_sheet)
    if data is None or data.empty:
        return f"No balance sheet data for {symbol.upper()}"
    return _df_to_csv(data, f"# Balance Sheet: {symbol.upper()}\n\n")


def get_cashflow(
    symbol: Annotated[str, "Ticker symbol"],
    years: Annotated[int, "Years of history to fetch"] = 5,
) -> str:
    """Fetch annual cash flow statements."""
    ticker = yf.Ticker(symbol.upper())
    data = _retry(lambda: ticker.cashflow)
    if data is None or data.empty:
        return f"No cash flow data for {symbol.upper()}"
    return _df_to_csv(data, f"# Cash Flow Statement: {symbol.upper()}\n\n")


# ---------------------------------------------------------------------------
# Key metrics & valuation
# ---------------------------------------------------------------------------


def get_key_metrics(
    symbol: Annotated[str, "Ticker symbol"],
) -> str:
    """Fetch key financial metrics (P/E, P/B, ROE, margins, etc.) from yfinance info."""
    ticker = yf.Ticker(symbol.upper())
    info = _retry(lambda: ticker.info) or {}

    # Pull out the most relevant long-term-investing metrics
    wanted = [
        "marketCap", "enterpriseValue", "trailingPE", "forwardPE",
        "priceToBook", "priceToSales", "enterpriseToRevenue", "enterpriseToEbitda",
        "returnOnEquity", "returnOnAssets", "returnOnCapital",
        "profitMargins", "operatingMargins", "grossMargins",
        "revenueGrowth", "earningsGrowth", "freeCashflow",
        "debtToEquity", "currentRatio", "quickRatio",
        "dividendYield", "payoutRatio", "fiveYearAvgDividendYield",
        "beta", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
        "sector", "industry", "fullTimeEmployees",
        "longBusinessSummary",
    ]

    lines = [f"# Key Metrics: {symbol.upper()}\n"]
    for key in wanted:
        if key in info and info[key] is not None:
            val = info[key]
            if isinstance(val, float):
                lines.append(f"{key}: {val:.4f}")
            else:
                lines.append(f"{key}: {val}")
    return "\n".join(lines)


def get_roe_roic_trends(
    symbol: Annotated[str, "Ticker symbol"],
) -> str:
    """Pull ROE / ROIC from info + compute simple trends from financials."""
    # yfinance info has current ROE; for trends we need multiple years
    ticker = yf.Ticker(symbol.upper())
    info = _retry(lambda: ticker.info) or {}

    lines = [f"# ROE / ROIC Snapshot: {symbol.upper()}\n"]
    for key in ["returnOnEquity", "returnOnAssets", "returnOnCapital"]:
        val = info.get(key)
        if val is not None:
            lines.append(f"{key}: {val:.4f}")

    # Add any quarterly ROE data if available
    try:
        income = _retry(lambda: ticker.income_stmt)
        balance = _retry(lambda: ticker.balance_sheet)
        if income is not None and balance is not None and not income.empty and not balance.empty:
            years = min(income.shape[1], balance.shape[1])
            common_cols = income.columns[:years]
            ni = income.loc["Net Income", common_cols] if "Net Income" in income.index else None
            equity = balance.loc["Stockholders Equity", common_cols] if "Stockholders Equity" in balance.index else None
            if ni is not None and equity is not None:
                roe_series = (ni / equity.replace(0, None) * 100).round(2)
                lines.append(f"\n# Annual ROE %:\n{roe_series.to_string()}")
    except Exception:
        pass

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# News
# ---------------------------------------------------------------------------


def get_company_news(
    symbol: Annotated[str, "Ticker symbol"],
    count: Annotated[int, "Number of articles"] = 10,
) -> str:
    """Fetch recent company news from yfinance."""
    ticker = yf.Ticker(symbol.upper())
    try:
        news = _retry(lambda: ticker.news)[:count]
    except Exception:
        return f"No news available for {symbol.upper()}"

    if not news:
        return f"No recent news for {symbol.upper()}"

    lines = [f"# Recent News: {symbol.upper()}\n"]
    for i, item in enumerate(news, 1):
        title = item.get("title", "N/A")
        publisher = item.get("publisher", "N/A")
        link = item.get("link", "")
        pub_time = item.get("providerPublishTime", "")
        if pub_time:
            pub_time = datetime.fromtimestamp(pub_time).strftime("%Y-%m-%d")
        lines.append(f"{i}. [{publisher}] {title} ({pub_time})")
        if link:
            lines.append(f"   {link}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Insider transactions
# ---------------------------------------------------------------------------


def get_insider_trades(
    symbol: Annotated[str, "Ticker symbol"],
) -> str:
    """Fetch recent insider transactions from yfinance."""
    ticker = yf.Ticker(symbol.upper())
    try:
        insider = _retry(lambda: ticker.insider_transactions)
    except Exception:
        return f"No insider transaction data for {symbol.upper()}"

    if insider is None or insider.empty:
        return f"No insider transactions reported for {symbol.upper()}"
    return _df_to_csv(insider, f"# Insider Transactions: {symbol.upper()}\n\n")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_vendor(
    "yfinance",
    {
        "get_price_history": get_price_history,
        "get_income_statement": get_income_statement,
        "get_balance_sheet": get_balance_sheet,
        "get_cashflow": get_cashflow,
        "get_key_metrics": get_key_metrics,
        "get_roe_roic_trends": get_roe_roic_trends,
        "get_company_news": get_company_news,
        "get_insider_trades": get_insider_trades,
    },
)
