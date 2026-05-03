"""Shared dataflow utilities — safe path handling, retry wrappers, etc."""

import re
from pathlib import Path


def safe_ticker_component(ticker: str) -> str:
    """Return a filesystem-safe version of a ticker for use in paths.

    Rejects values that contain path traversal or other dangerous patterns.
    """
    # Allow alphanumeric, dots, hyphens, underscores, carets (e.g. ^GSPC)
    # Reject anything with slashes, backslashes, or null bytes
    if re.search(r"[/\\\x00]", ticker):
        raise ValueError(f"Unsafe ticker value: {ticker!r}")
    cleaned = re.sub(r"[^a-zA-Z0-9.\-_^]", "_", ticker)
    if not cleaned:
        raise ValueError(f"Empty ticker after sanitisation: {ticker!r}")
    return cleaned
