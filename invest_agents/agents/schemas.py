"""Pydantic schemas for InvestAgents structured outputs.

Unlike TradingAgents which produces trade signals, InvestAgents produces:
  - **Investment Theses**: why own a stock for 3-5 years, catalysts, exit criteria
  - **Portfolio Allocations**: multi-stock construction with conviction-weighted sizing
  - **Thesis Reviews**: periodic check-ins — is the thesis still intact?
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared types
# ---------------------------------------------------------------------------


class Conviction(str, Enum):
    """5-tier conviction scale for long-term theses."""

    HIGH = "High"               # Strong edge, durable moat, great price
    ABOVE_AVERAGE = "Above Average"
    AVERAGE = "Average"
    BELOW_AVERAGE = "Below Average"
    LOW = "Low"                 # Speculative, or thesis not well-formed


class ThesisStatus(str, Enum):
    """Status of an active thesis during review cycles."""

    INTACT = "Intact"                   # Playing out as expected
    NEEDS_MONITORING = "Needs Monitoring"  # Some concern, but not broken
    WEAKENING = "Weakening"             # Thesis stress, consider reducing
    INVALIDATED = "Invalidated"         # Thesis broken — exit


class MoatRating(str, Enum):
    """Morningstar-style moat assessment."""

    WIDE = "Wide"               # Durable competitive advantage
    NARROW = "Narrow"           # Some advantage but less durable
    NONE = "None"               # No moat — commodity business


# ---------------------------------------------------------------------------
# Analyst report schemas
# ---------------------------------------------------------------------------


class MoatReport(BaseModel):
    """Structured moat / competitive advantage analysis."""

    moat_rating: MoatRating = Field(
        description="Overall moat assessment: Wide, Narrow, or None."
    )
    moat_sources: str = Field(
        description=(
            "Specific sources of competitive advantage: switching costs, "
            "network effects, intangible assets (brands/patents), cost advantage, "
            "or efficient scale. Be specific — name the advantage and why it persists."
        ),
    )
    roic_trend: str = Field(
        description=(
            "ROIC trend analysis: current ROIC, 5-year trend, comparison to "
            "cost of capital. Is the company earning above its WACC consistently?"
        ),
    )
    management_quality: str = Field(
        description=(
            "Capital allocation track record: share buybacks at good prices? "
            "Smart M&A or empire-building? Insider ownership alignment? "
            "Compensation structure incentivizes long-term value?"
        ),
    )
    competitive_threats: str = Field(
        description="Key competitive risks: disruption, new entrants, substitution, etc.",
    )


class ValuationReport(BaseModel):
    """Structured valuation analysis."""

    fair_value_range: str = Field(
        description="Estimated fair value range (e.g., '$150-180 per share')."
    )
    current_margin_of_safety: str = Field(
        description=(
            "Current price vs fair value: percentage upside/downside. "
            "Is there a sufficient margin of safety?"
        ),
    )
    valuation_method: str = Field(
        description=(
            "Primary valuation method used: DCF, P/E historical range, "
            "EV/EBITDA comps, sum-of-parts, etc."
        ),
    )
    key_assumptions: str = Field(
        description=(
            "The 2-3 assumptions that matter most: revenue growth rate, "
            "terminal multiple, margin expansion, etc."
        ),
    )
    historical_multiple_context: str = Field(
        description=(
            "Where are current multiples (P/E, EV/EBITDA) relative to "
            "5-10 year history? Undervalued, fairly valued, or overvalued?"
        ),
    )


class GrowthReport(BaseModel):
    """Structured growth analysis."""

    revenue_cagr_5yr: Optional[float] = Field(
        default=None,
        description="5-year revenue CAGR (%).",
    )
    earnings_cagr_5yr: Optional[float] = Field(
        default=None,
        description="5-year earnings CAGR (%).",
    )
    growth_drivers: str = Field(
        description=(
            "Key growth drivers: unit volume vs price, new markets, "
            "product cycles, acquisitions, secular tailwinds."
        ),
    )
    tam_analysis: str = Field(
        description="Total Addressable Market assessment: size, penetration, runway.",
    )
    reinvestment_runway: str = Field(
        description=(
            "Can the company reinvest at high rates of return? "
            "ROIC on incremental capital, capacity to deploy retained earnings."
        ),
    )
    growth_quality: str = Field(
        description=(
            "Is growth profitable or value-destructive? Unit economics, "
            "customer acquisition costs, LTV/CAC trends."
        ),
    )


class MacroReport(BaseModel):
    """Structured macro / industry context analysis."""

    industry_stage: str = Field(
        description="Industry lifecycle: emerging, growth, mature, declining."
    )
    sector_tailwinds: str = Field(
        description="Secular trends favoring the industry (demographics, regulation, tech)."
    ),
    sector_headwinds: str = Field(
        description="Structural risks facing the industry."
    ),
    macro_sensitivity: str = Field(
        description=(
            "How sensitive is this business to: interest rates, commodity prices, "
            "FX, consumer confidence? Which macro scenarios hurt/help most?"
        ),
    )
    regulatory_risk: str = Field(
        description="Key regulatory/political risks: antitrust, environmental, tariffs, etc.",
    )


# ---------------------------------------------------------------------------
# Investment Thesis (the main output of stock deep-dive)
# ---------------------------------------------------------------------------


class InvestmentThesis(BaseModel):
    """The core output: a complete long-term investment thesis.

    This is what the Thesis Manager produces after digesting all analyst
    reports and the bull/bear debate.
    """

    ticker: str = Field(description="Ticker symbol.")
    date: str = Field(description="Date of analysis (yyyy-mm-dd).")
    conviction: Conviction = Field(
        description="Overall conviction level based on moat, valuation, growth, and macro.",
    )

    # The narrative
    one_sentence_thesis: str = Field(
        description=(
            "One sentence summary: what is this investment and why does it work? "
            "Example: 'Costco is a best-in-class retailer with a subscription moat "
            "that earns high ROIC and compounds store count at 5% annually.'"
        ),
    )
    full_thesis: str = Field(
        description=(
            "Detailed thesis: 3-5 paragraphs covering business quality, growth "
            "drivers, valuation context, and key insights from the bull/bear debate."
        ),
    )

    # Catalysts
    catalysts: str = Field(
        description=(
            "Specific events that would drive value realization over the holding "
            "period. Each catalyst should be observable and time-bound (e.g., "
            "'Store count reaches 1,000 by 2027', 'Operating margins expand to 15% "
            "as automation investment pays off')."
        ),
    )

    # Risks & exit criteria
    key_risks: str = Field(
        description="Top 3-5 risks that could break the thesis.",
    )
    exit_criteria: str = Field(
        description=(
            "Clear, observable conditions that would trigger an exit: "
            "thesis invalidation signals (not just price moves). "
            "E.g., 'ROIC falls below WACC for 4 consecutive quarters', "
            "'CEO departure', 'Regulatory action prevents core business activity'."
        ),
    )

    # Valuation
    fair_value_range: str = Field(description="Estimated intrinsic value range.")
    buy_below_price: Optional[float] = Field(
        default=None,
        description="Price below which to consider initiating/adding.",
    )
    sell_above_price: Optional[float] = Field(
        default=None,
        description="Price above which thesis becomes purely speculative (trim/reduce).",
    )

    # Holding parameters
    expected_holding_period: str = Field(
        description="Expected holding period: '3-5 years', '5-10 years', etc.",
    )
    suggested_portfolio_weight_pct: float = Field(
        description="Suggested portfolio weight as percentage (0-10).",
    )


def render_thesis(thesis: InvestmentThesis) -> str:
    """Render an InvestmentThesis to markdown for storage and display."""
    parts = [
        f"**Ticker**: {thesis.ticker}",
        f"**Date**: {thesis.date}",
        f"**Conviction**: {thesis.conviction.value}",
        f"**Suggested Weight**: {thesis.suggested_portfolio_weight_pct:.1f}%",
        "",
        f"**One-Sentence Thesis**: {thesis.one_sentence_thesis}",
        "",
        f"**Full Thesis**:\n{thesis.full_thesis}",
        "",
        f"**Catalysts**:\n{thesis.catalysts}",
        "",
        f"**Key Risks**:\n{thesis.key_risks}",
        "",
        f"**Exit Criteria**:\n{thesis.exit_criteria}",
        "",
        f"**Fair Value Range**: {thesis.fair_value_range}",
    ]
    if thesis.buy_below_price is not None:
        parts.append(f"**Buy Below**: ${thesis.buy_below_price:.2f}")
    if thesis.sell_above_price is not None:
        parts.append(f"**Sell Above**: ${thesis.sell_above_price:.2f}")
    parts.extend([
        "",
        f"**Holding Period**: {thesis.expected_holding_period}",
    ])
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Thesis Review (periodic check-in)
# ---------------------------------------------------------------------------


class ThesisReview(BaseModel):
    """Output of a periodic thesis re-evaluation."""

    ticker: str
    original_date: str = Field(description="When the thesis was originally written.")
    review_date: str = Field(description="Date of this review.")
    status: ThesisStatus = Field(description="Current thesis health.")

    what_played_out: str = Field(
        description="Which catalysts have materialized since the last review?"
    )
    what_hasnt: str = Field(
        description="Which catalysts are lagging or appear unlikely?"
    )
    new_developments: str = Field(
        description="Material changes since last review: business, industry, macro."
    )
    updated_conviction: Conviction = Field(description="Revised conviction level.")
    action: str = Field(
        description="Recommended action: maintain, add, trim, exit, or watch closely."
    )


# ---------------------------------------------------------------------------
# Portfolio Construction
# ---------------------------------------------------------------------------


class PositionSizing(BaseModel):
    """Sizing for a single position within the portfolio."""

    ticker: str
    conviction: Conviction
    weight_pct: float = Field(description="Target portfolio weight (0-100).")
    thesis_summary: str = Field(description="One-line thesis summary.")
    risk_contribution: str = Field(
        description="How this position contributes to portfolio risk: growth, value, "
                    "defensive, cyclical, international, etc."
    )


class PortfolioConstructionResult(BaseModel):
    """Output of the Portfolio Constructor agent."""

    date: str = Field(description="Portfolio construction date.")
    total_positions: int

    # Allocation
    positions: list[PositionSizing] = Field(
        description="Target positions with weights.",
    )
    cash_reserve_pct: float = Field(
        default=5.0,
        description="Recommended cash reserve as percentage.",
    )

    # Portfolio-level reasoning
    macro_overlay: str = Field(
        description=(
            "How the current macro environment affects sector weights: "
            "overweight/underweight calls based on rates, cycle position, etc."
        ),
    )
    diversification_assessment: str = Field(
        description=(
            "Portfolio concentration risks: sector over-concentration, "
            "factor exposures, correlation risks identified."
        ),
    )
    rebalancing_plan: str = Field(
        description=(
            "Specific rebalancing actions: which positions to trim, add to, "
            "or exit based on current vs target weights and thesis health."
        ),
    )


def render_portfolio(result: PortfolioConstructionResult) -> str:
    """Render PortfolioConstructionResult to markdown."""
    lines = [
        f"# Portfolio Construction — {result.date}",
        f"**Positions**: {result.total_positions} | **Cash Reserve**: {result.cash_reserve_pct:.1f}%",
        "",
        "## Target Allocations",
        "",
    ]

    # Positions table
    lines.append("| Ticker | Weight % | Conviction | Role | Thesis |")
    lines.append("|--------|----------|------------|------|--------|")
    for p in result.positions:
        lines.append(
            f"| {p.ticker} | {p.weight_pct:.1f}% | {p.conviction.value} "
            f"| {p.risk_contribution} | {p.thesis_summary} |"
        )

    lines.extend([
        "",
        "## Macro Overlay",
        result.macro_overlay,
        "",
        "## Diversification Assessment",
        result.diversification_assessment,
        "",
        "## Rebalancing Plan",
        result.rebalancing_plan,
    ])
    return "\n".join(lines)
