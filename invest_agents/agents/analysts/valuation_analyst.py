"""Valuation Analyst — estimates intrinsic value via DCF, multiples, and
historical context.  Answers: "Is this a good price for a great business?"
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from invest_agents.agents.utils.agent_utils import (
    build_instrument_context,
    get_income_statement,
    get_balance_sheet,
    get_cashflow,
    get_key_metrics,
    get_price_history,
    get_language_instruction,
)


def create_valuation_analyst(llm):
    """Create the Valuation Analyst node."""

    tools = [
        get_price_history,
        get_key_metrics,
        get_income_statement,
        get_balance_sheet,
        get_cashflow,
    ]

    system_message = (
        "You are a Valuation Analyst estimating the intrinsic value of a company. "
        "Your job: determine whether the current stock price offers a sufficient "
        "margin of safety for a long-term (3-5+ year) investment.\n\n"
        "Analyze:\n"
        "1. **Current Multiples**: P/E (trailing & forward), EV/EBITDA, P/B, P/S, "
        "P/FCF. Compare to historical 5-10 year ranges.\n"
        "2. **Fair Value Estimate**: Use at least two methods — DCF (free cash flow "
        "projection), historical multiple range, and/or peer comparables.\n"
        "3. **Margin of Safety**: What percentage below fair value is the stock trading? "
        "Is this sufficient given the business quality?\n"
        "4. **Key Assumptions**: The 2-3 assumptions that matter most for your valuation. "
        "What has to go right/wrong?\n"
        "5. **Historical Context**: Is the stock cheap relative to its own history? "
        "Consider 3, 5, and 10-year valuation ranges.\n\n"
        "Be quantitative. Cite specific multiples and fair value ranges. "
        "If the data is insufficient for a DCF, say so and use alternative methods.\n"
        + "Available tools: `get_price_history` for long-term price data, "
        "`get_key_metrics` for current multiples, and financial statement tools "
        "for FCF and earnings data.\n"
        + get_language_instruction(),
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant collaborating with other analysts.\n"
            "Use tools to gather data. If you can't get perfect data, do your best "
            "with what's available.\n"
            "Tools: {tool_names}.\n{system_message}\n"
            "Current date: {current_date}. {instrument_context}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join(t.name for t in tools))

    def valuation_analyst_node(state):
        current_date = state["trade_date"]
        instrument_context = build_instrument_context(state["company_of_interest"])

        chain = prompt.partial(
            current_date=current_date,
            instrument_context=instrument_context,
        ) | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        report = ""
        if not result.tool_calls:
            report = result.content

        return {
            "messages": [result],
            "valuation_report": report,
        }

    return valuation_analyst_node
