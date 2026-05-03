"""SEC EDGAR data source — company filings (10-K, 10-Q) from sec.gov.

Free, no API key, rate-limited to ~10 req/sec (be a good citizen).
Perfect for long-term analysis: you get the real narrative — risk factors,
MD&A, business description — not just numbers.

Uses the SEC's `sec-api.io`-compatible REST endpoints and/or direct
EDGAR xbrl APIs for structured data.
"""

from __future__ import annotations

import logging
import re
import time
from datetime import datetime
from typing import Annotated, Optional

import requests

from .interface import register_vendor, VendorRateLimitError

logger = logging.getLogger(__name__)

SEC_BASE = "https://www.sec.gov"
HEADERS = {
    "User-Agent": "InvestAgents/0.1 (your-email@example.com)",
    "Accept-Encoding": "gzip, deflate",
}
_session = requests.Session()
_session.headers.update(HEADERS)


def _sec_get(url: str, params: dict = None) -> dict | list:
    """GET from SEC with rate-limit awareness."""
    resp = _session.get(url, params=params, timeout=30)
    if resp.status_code == 429:
        raise VendorRateLimitError("SEC EDGAR rate limit hit")
    resp.raise_for_status()
    return resp.json()


# ---------------------------------------------------------------------------
# CIK lookup
# ---------------------------------------------------------------------------


def _ticker_to_cik(ticker: str) -> Optional[str]:
    """Convert ticker to CIK (Central Index Key) for SEC lookups."""
    ticker = ticker.upper().strip()
    try:
        data = _sec_get(
            "https://www.sec.gov/files/company_tickers.json",
        )
        # SEC's company_tickers.json uses CIK as key with leading zeros stripped
        for cik_str, info in data.items():
            if info.get("ticker", "").upper() == ticker:
                # Pad CIK to 10 digits
                return str(int(cik_str)).zfill(10)
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Submissions (list of filings)
# ---------------------------------------------------------------------------


def _get_submissions(cik: str) -> dict:
    """Get recent filings for a CIK."""
    return _sec_get(f"https://data.sec.gov/submissions/CIK{cik}.json")


def _find_recent_filings(cik: str, form_types: list[str], limit: int = 3):
    """Return accession numbers for recent filings of given form types."""
    try:
        subs = _get_submissions(cik)
        recent = subs.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        accessions = recent.get("accessionNumber", [])
        filing_dates = recent.get("filingDate", [])

        results = []
        for form, acc, date in zip(forms, accessions, filing_dates):
            if form in form_types:
                results.append({
                    "form": form,
                    "accession": acc,
                    "filing_date": date,
                })
                if len(results) >= limit:
                    break
        return results
    except Exception as e:
        logger.warning("Could not fetch SEC filings: %s", e)
        return []


# ---------------------------------------------------------------------------
# Filing content retrieval
# ---------------------------------------------------------------------------


def _get_filing_text(cik: str, accession: str) -> str:
    """Retrieve full text of a filing (strips HTML tags)."""
    # SEC URL pattern:
    # https://www.sec.gov/Archives/edgar/data/{cik}/{acc_no_dashes}/{acc}.txt
    acc_no_dashes = accession.replace("-", "")
    url = f"{SEC_BASE}/Archives/edgar/data/{int(cik)}/{acc_no_dashes}/{accession}.txt"
    resp = _session.get(url, timeout=30, headers=HEADERS)
    resp.raise_for_status()
    return resp.text


def _strip_html(text: str) -> str:
    """Naive HTML tag stripper — good enough for SEC filings."""
    clean = re.sub(r"<[^>]+>", " ", text)
    clean = re.sub(r"&nbsp;", " ", clean)
    clean = re.sub(r"&#\d+;", " ", clean)
    clean = re.sub(r"\s+", " ", clean)
    return clean.strip()


def _extract_section(text: str, section_start: str, section_end: str = None) -> str:
    """Extract a section from filing text by heading markers."""
    pattern = re.escape(section_start)
    match = re.search(pattern, text, re.IGNORECASE)
    if not match:
        return ""

    start = match.start()
    if section_end:
        end_match = re.search(re.escape(section_end), text[start + len(section_start):], re.IGNORECASE)
        if end_match:
            return text[start:start + len(section_start) + end_match.start()]

    # Return next ~5000 chars if no end marker
    snippet = text[start:start + 5000]
    return snippet


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def get_10k_filing(
    symbol: Annotated[str, "Ticker symbol"],
    sections: Annotated[str, "Comma-separated sections to extract, e.g. 'business,risk,mdna'"] = "business,risk,mdna",
) -> str:
    """Fetch the most recent 10-K filing and extract specified sections.

    Available sections: business, risk, mdna, financial, notes
    """
    cik = _ticker_to_cik(symbol)
    if not cik:
        return f"Could not find CIK for ticker {symbol.upper()}"

    filings = _find_recent_filings(cik, ["10-K", "10-K/A"], limit=1)
    if not filings:
        return f"No recent 10-K filings found for {symbol.upper()}"

    f = filings[0]
    text = _get_filing_text(cik, f["accession"])
    clean = _strip_html(text)

    requested = [s.strip().lower() for s in sections.split(",")]

    section_map = {
        "business": ("Item 1.", "Item 1A."),
        "risk": ("Item 1A.", "Item 1B."),
        "mdna": ("Management's Discussion", "Item 8."),
        "financial": ("Item 8.", "Item 9."),
        "notes": ("Notes to", "Item 9."),
    }

    output_parts = [
        f"# 10-K Filing: {symbol.upper()} | Filed: {f['filing_date']} | Form: {f['form']}\n",
    ]

    for section in requested:
        if section in section_map:
            start_tag, end_tag = section_map[section]
            extracted = _extract_section(clean, start_tag, end_tag)
            if extracted:
                # Truncate to reasonable length for LLM context
                max_len = 8000
                if len(extracted) > max_len:
                    extracted = extracted[:max_len] + "\n\n[... truncated for length ...]"
                output_parts.append(f"\n## {section.upper()}\n{extracted}\n")
            else:
                output_parts.append(f"\n## {section.upper()}\n[Section not found]\n")

    return "\n".join(output_parts)


def get_10q_filing(
    symbol: Annotated[str, "Ticker symbol"],
    sections: Annotated[str, "Comma-separated sections to extract"] = "risk,mdna,financial",
) -> str:
    """Fetch the most recent 10-Q filing and extract specified sections."""
    cik = _ticker_to_cik(symbol)
    if not cik:
        return f"Could not find CIK for ticker {symbol.upper()}"

    filings = _find_recent_filings(cik, ["10-Q", "10-Q/A"], limit=1)
    if not filings:
        return f"No recent 10-Q filings found for {symbol.upper()}"

    f = filings[0]
    text = _get_filing_text(cik, f["accession"])
    clean = _strip_html(text)

    requested = [s.strip().lower() for s in sections.split(",")]

    section_map = {
        "risk": ("Item 1A.", "Item 2."),
        "mdna": ("Management's Discussion", "Item 1."),
        "financial": ("Item 1.", "Item 2."),
    }

    output_parts = [
        f"# 10-Q Filing: {symbol.upper()} | Filed: {f['filing_date']} | Form: {f['form']}\n",
    ]

    for section in requested:
        if section in section_map:
            start_tag, end_tag = section_map[section]
            extracted = _extract_section(clean, start_tag, end_tag)
            if extracted:
                max_len = 8000
                if len(extracted) > max_len:
                    extracted = extracted[:max_len] + "\n\n[... truncated for length ...]"
                output_parts.append(f"\n## {section.upper()}\n{extracted}\n")
            else:
                output_parts.append(f"\n## {section.upper()}\n[Section not found]\n")

    return "\n".join(output_parts)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

register_vendor(
    "sec_edgar",
    {
        "get_10k_filing": get_10k_filing,
        "get_10q_filing": get_10q_filing,
    },
)
