"""Portfolio Constructor — aggregates multiple investment theses into a
coherent portfolio with position sizing, sector balance, and macro overlay.

This is the "top-down meets bottom-up" layer.  It reads all active theses,
applies macro context, and produces target weights.
"""

from __future__ import annotations

from datetime import datetime

from invest_agents.agents.schemas import (
    PortfolioConstructionResult,
    render_portfolio,
)
from invest_agents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from invest_agents.agents.utils.agent_utils import get_language_instruction


def create_portfolio_constructor(llm):
    """Create the Portfolio Constructor node."""
    structured_llm = bind_structured(
        llm, PortfolioConstructionResult, "Portfolio Constructor"
    )

    def portfolio_constructor_node(state) -> dict:
        """Build portfolio from a list of thesis dicts + macro context."""
        theses = state.get("active_theses", [])
        macro_context = state.get("macro_context", "")
        current_date = state.get("date", datetime.now().strftime("%Y-%m-%d"))

        if not theses:
            return {
                "portfolio_result": "# Portfolio Construction\n\nNo active theses to allocate."
            }

        # Format theses for the prompt
        thesis_blocks = []
        for i, t in enumerate(theses, 1):
            thesis_blocks.append(
                f"### Thesis {i}: {t.get('ticker', '???')}\n"
                f"Conviction: {t.get('conviction', 'N/A')}\n"
                f"Weight suggestion: {t.get('suggested_weight', 'N/A')}\n\n"
                f"{t.get('thesis_markdown', t.get('thesis', 'No thesis text'))}\n"
            )

        thesis_text = "\n---\n".join(thesis_blocks)

        prompt = f"""You are the Portfolio Constructor — responsible for turning individual
investment theses into a coherent, risk-managed portfolio.

---

**Macro Context**:
{macro_context if macro_context else "No macro data available. Use general diversification principles."}

---

**Candidate Theses**:

{thesis_text}

---

**Instructions**:

1. **Macro Overlay**: Given the macro environment, which sectors/themes should be
   overweighted or underweighted? E.g., if rates are rising, consider underweighting
   long-duration growth names.

2. **Position Sizing**: Assign a target weight (0-15%) to each thesis based on:
   - Conviction level
   - Market cap / liquidity
   - Correlation / diversification benefit
   - Macro tailwind/headwind alignment

3. **Diversification Check**: Identify any sector concentration, factor crowding,
   or hidden correlation risks.

4. **Rebalancing Plan**: If this is a rebalance, which positions should be
   trimmed, added to, or exited? If new construction, what's the phased entry plan?

5. **Cash Reserve**: Keep 2-10% cash for opportunistic deployment.

**Constraints**:
- Max single position: 10% of portfolio
- At least 3 different sectors represented
- Total weights must sum to (100% - cash reserve)

{get_language_instruction()}"""

        result_md = invoke_structured_or_freetext(
            structured_llm,
            llm,
            prompt,
            render_portfolio,
            "Portfolio Constructor",
        )

        return {"portfolio_result": result_md}

    return portfolio_constructor_node
