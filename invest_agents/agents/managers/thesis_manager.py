"""Thesis Manager — produces the final InvestmentThesis after digesting all
analyst reports and the bull/bear debate.

Uses structured output (with free-text fallback) to produce a typed
InvestmentThesis that includes:
  - Conviction level
  - Full thesis narrative
  - Catalysts (observable, time-bound)
  - Exit criteria (thesis invalidation signals)
  - Valuation guardrails (buy below / sell above)
  - Suggested portfolio weight
"""

from __future__ import annotations

from invest_agents.agents.schemas import InvestmentThesis, render_thesis
from invest_agents.agents.utils.agent_utils import (
    build_instrument_context,
    get_language_instruction,
)
from invest_agents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)


def create_thesis_manager(llm):
    """Create the Thesis Manager node."""
    structured_llm = bind_structured(llm, InvestmentThesis, "Thesis Manager")

    def thesis_manager_node(state) -> dict:
        instrument_context = build_instrument_context(state["company_of_interest"])
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        debate = state["thesis_debate_state"]
        history = debate.get("history", "")

        moat = state["moat_report"]
        valuation = state["valuation_report"]
        growth = state["growth_report"]
        macro = state["macro_report"]

        past_context = state.get("past_context", "")
        lessons_line = (
            f"**Lessons from prior analyses**:\n{past_context}\n\n"
            if past_context
            else ""
        )

        prompt = f"""You are the Thesis Manager — the final decision-maker in the investment
committee. Synthesize all the research below into a complete long-term
investment thesis for {ticker}.

{instrument_context}

---

**Conviction Scale** (use exactly one):
- **High**: Exceptional business, wide moat, great price, strong catalysts
- **Above Average**: Good business, fair price, reasonable catalysts
- **Average**: Decent business but some concerns on moat/valuation/growth
- **Below Average**: Too many red flags — better opportunities elsewhere
- **Low**: Speculative, unclear thesis, or thesis appears broken

---

{lessons_line}
**Analyst Reports**:

### MOAT & QUALITY
{moat}

### VALUATION
{valuation}

### GROWTH
{growth}

### MACRO & INDUSTRY
{macro}

### BULL/BEAR DEBATE
{history}

---

**Instructions**:
1. Write a **one-sentence thesis** that captures the essence of the investment case.
2. Write a **full thesis** (3-5 paragraphs) covering business quality, growth drivers,
   valuation, and which side of the debate won.
3. List **specific catalysts** — observable, time-bound events that would drive value.
4. List **key risks** — the top 3-5 things that could break the thesis.
5. Define **exit criteria** — clear conditions that trigger a sell (NOT just price moves).
6. Provide a **fair value range** and optional buy-below / sell-above prices.
7. State the **expected holding period** and **suggested portfolio weight** (0-10%).

Be decisive. A 'Hold' is an acceptable outcome if the evidence is balanced.
Do not recommend buying just because the analysis was done.
{get_language_instruction()}"""

        thesis_md = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_thesis,
            "Thesis Manager",
        )

        # Build a lightweight dict version for portfolio construction
        thesis_dict = {
            "ticker": ticker,
            "date": current_date,
            "thesis_markdown": thesis_md,
        }

        return {
            "investment_thesis": thesis_md,
            "investment_thesis_structured": thesis_dict,
        }

    return thesis_manager_node
