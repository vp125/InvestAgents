"""Bull Researcher — constructs and defends the bullish investment case.

Reads all four analyst reports and builds the most compelling possible argument
for why this stock should be owned for the long term.
"""


def create_bull_researcher(llm):
    """Create the Bull Researcher node — argues FOR the investment."""

    def bull_node(state) -> dict:
        debate_state = state["thesis_debate_state"]
        history = debate_state.get("history", "")
        bull_history = debate_state.get("bull_history", "")
        bear_last = debate_state.get("current_bear_response", "")

        moat = state["moat_report"]
        valuation = state["valuation_report"]
        growth = state["growth_report"]
        macro = state["macro_report"]

        ticker = state["company_of_interest"]

        prompt = f"""You are the Bull Researcher defending a long-term investment in {ticker}.

Your job: build the most compelling, intellectually honest bullish case using the
analyst reports below. Address the bear's arguments directly if they exist.

Ground every claim in specific evidence from the reports. Don't just assert —
prove with data, trends, and logic.

**Analyst Reports**:

=== MOAT & QUALITY ===
{moat}

=== VALUATION ===
{valuation}

=== GROWTH ===
{growth}

=== MACRO & INDUSTRY ===
{macro}

**Debate History**: {history}

**Last Bear Argument**: {bear_last if bear_last else "No bear argument yet — present your opening bull case."}

Respond directly to the bear's points if there are any. Highlight where the bear
is overly pessimistic, missing context, or underestimating the business quality.
Use specific evidence from the reports. Be persuasive but honest — don't
exaggerate.

Output conversationally as if speaking in an investment committee meeting.
Start with 'Bull Researcher:'"""

        response = llm.invoke(prompt)
        argument = f"Bull Researcher: {response.content}"

        new_debate = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": debate_state.get("bear_history", ""),
            "current_response": "Bull:" + response.content[:100],
            "current_bull_response": argument,
            "current_bear_response": debate_state.get("current_bear_response", ""),
            "count": debate_state["count"] + 1,
        }

        return {"thesis_debate_state": new_debate}

    return bull_node
