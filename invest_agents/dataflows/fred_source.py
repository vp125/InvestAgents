"""FRED (Federal Reserve Economic Data) source — macro indicators.

Free with FRED_API_KEY from https://fred.stlouisfed.org/docs/api/api_key.html
Covers interest rates, GDP, inflation, employment — critical context for
long-term sector rotation and macro-aware position sizing.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta
from typing import Annotated, Optional

import requests

from .interface import register_vendor, VendorRateLimitError

logger = logging.getLogger(__name__)

FRED_BASE = "https://api.stlouisfed.org/fred"


def _fred_api_key() -> str:
    """Get FRED API key from env or config."""
    key = os.getenv("FRED_API_KEY", "")
    if not key:
        raise VendorRateLimitError("FRED_API_KEY not set")
    return key


def _fred_get(endpoint: str, params: dict) -> dict:
    """GET from FRED API with rate-limit awareness."""
    params["api_key"] = _fred_api_key()
    params["file_type"] = "json"
    resp = requests.get(f"{FRED_BASE}/{endpoint}", params=params, timeout=30)
    if resp.status_code == 429:
        raise VendorRateLimitError("FRED rate limit hit")
    resp.raise_for_status()
    return resp.json()


def _series_to_markdown(series_id: str, label: str, days_back: int = 365) -> str:
    """Fetch a FRED series and return recent observations as markdown."""
    end_date = datetime.now().strftime("%Y-%m-%d")
    start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")

    try:
        data = _fred_get("series/observations", {
            "series_id": series_id,
            "observation_start": start_date,
            "observation_end": end_date,
            "sort_order": "desc",
            "limit": 60,
        })
        obs = data.get("observations", [])
        if not obs:
            return f"**{label}** ({series_id}): No recent data\n"

        vals = [f"{o['date']}: {o['value']}" for o in obs[:20]]
        return f"**{label}** ({series_id}) — last {len(vals)} observations:\n" + "\n".join(vals)
    except Exception as e:
        logger.warning("FRED series %s failed: %s", series_id, e)
        return f"**{label}** ({series_id}): Unavailable ({e})\n"


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def get_interest_rates(
    days_back: Annotated[int, "Days of history to fetch"] = 365,
) -> str:
    """Fetch key interest rates: Fed Funds, 10Y Treasury, 2Y Treasury, 30Y mortgage."""
    series = [
        ("DFF", "Federal Funds Rate"),
        ("DGS10", "10-Year Treasury"),
        ("DGS2", "2-Year Treasury"),
        ("MORTGAGE30US", "30-Year Fixed Mortgage"),
    ]

    lines = ["# Interest Rates (FRED)\n"]
    for sid, label in series:
        lines.append(_series_to_markdown(sid, label, days_back))
        lines.append("")
    return "\n".join(lines)


def get_gdp_growth(
    days_back: Annotated[int, "Days of history to fetch"] = 365 * 5,
) -> str:
    """Fetch GDP and GDP growth rate."""
    lines = ["# GDP Data (FRED)\n"]
    lines.append(_series_to_markdown("GDP", "Nominal GDP (billions)", days_back))
    lines.append("")
    lines.append(_series_to_markdown("GDPC1", "Real GDP (billions, chained 2017$)", days_back))
    lines.append("")
    # Try GDPNow or GDP_PCT for growth rate
    lines.append(_series_to_markdown("A191RL1Q225SBEA", "Real GDP Growth Rate (QoQ %)", days_back))
    return "\n".join(lines)


def get_inflation_data(
    days_back: Annotated[int, "Days of history to fetch"] = 365 * 3,
) -> str:
    """Fetch CPI, Core CPI, PCE, Core PCE."""
    series = [
        ("CPIAUCSL", "CPI (All Urban Consumers)"),
        ("CPILFESL", "Core CPI (ex Food & Energy)"),
        ("PCEPI", "PCE Price Index"),
        ("PCEPILFE", "Core PCE (ex Food & Energy)"),
    ]
    lines = ["# Inflation Data (FRED)\n"]
    for sid, label in series:
        lines.append(_series_to_markdown(sid, label, days_back))
        lines.append("")
    return "\n".join(lines)


def get_unemployment_data(
    days_back: Annotated[int, "Days of history to fetch"] = 365 * 3,
) -> str:
    """Fetch unemployment rate and labor force participation."""
    series = [
        ("UNRATE", "Unemployment Rate (%)"),
        ("CIVPART", "Labor Force Participation Rate (%)"),
        ("PAYEMS", "Total Nonfarm Payrolls (thousands)"),
        ("JTSJOL", "Job Openings: Total Nonfarm (thousands)"),
    ]
    lines = ["# Employment Data (FRED)\n"]
    for sid, label in series:
        lines.append(_series_to_markdown(sid, label, days_back))
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_vendor(
    "fred",
    {
        "get_interest_rates": get_interest_rates,
        "get_gdp_growth": get_gdp_growth,
        "get_inflation_data": get_inflation_data,
        "get_unemployment_data": get_unemployment_data,
    },
)
