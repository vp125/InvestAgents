"""Bear Researcher — constructs and defends the bearish counter-argument.

Reads all four analyst reports and identifies the biggest risks, weakest
assumptions, and reasons this investment could fail.  The bear's job is to
stress-test the thesis — not to be negative for its own sake.
"""


def create_bear_researcher(llm):
    """Create the Bear Researcher node — argues AGAINST the investment."""

    def bear_node(state) -> dict:
        debate_state = state["thesis_debate_state"]
        history = debate_state.get("history", "")
        bear_history = debate_state.get("bear_history", "")
        bull_last = debate_state.get("current_bull_response", "")

        moat = state["moat_report"]
        valuation = state["valuation_report"]
        growth = state["growth_report"]
        macro = state["macro_report"]

        ticker = state["company_of_interest"]

        prompt = f"""You are the Bear Researcher challenging a long-term investment in {ticker}.

Your job: identify the biggest risks, weakest assumptions, and most dangerous
blind spots in the bullish case. You are the devil's advocate — your role is
to stress-test the thesis, not to be negative for its own sake.

Focus on:
- Where the moat might be eroding (disruption, competition)
- Why the valuation might be a value trap, not an opportunity
- Growth assumptions that look unrealistic
- Macro or regulatory risks being underestimated

Ground every criticism in specific evidence from the reports or well-reasoned
logic. Don't just say "it could go down." Explain exactly HOW the thesis could
break and what would need to happen.

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

**Last Bull Argument**: {bull_last if bull_last else "No bull argument yet — present your opening bear case."}

Respond directly to the bull's points if there are any. Challenge their
assumptions. Point out over-optimism. Identify what the bull is ignoring.
Use specific evidence from the reports.

Output conversationally as if speaking in an investment committee meeting.
Start with 'Bear Researcher:'"""

        response = llm.invoke(prompt)
        argument = f"Bear Researcher: {response.content}"

        new_debate = {
            "history": history + "\n" + argument,
            "bull_history": debate_state.get("bull_history", ""),
            "bear_history": bear_history + "\n" + argument,
            "current_response": "Bear:" + response.content[:100],
            "current_bull_response": debate_state.get("current_bull_response", ""),
            "current_bear_response": argument,
            "count": debate_state["count"] + 1,
        }

        return {"thesis_debate_state": new_debate}

    return bear_node
