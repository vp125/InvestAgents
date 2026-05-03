"""Moat Analyst — evaluates competitive advantage, management quality, and ROIC trends.

This is the most important analyst for long-term investing.  A durable moat
is the single best predictor of sustained high returns on capital.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from invest_agents.agents.utils.agent_utils import (
    build_instrument_context,
    get_10k_filing,
    get_balance_sheet,
    get_cashflow,
    get_income_statement,
    get_key_metrics,
    get_roe_roic_trends,
    get_language_instruction,
)
from invest_agents.agents.utils.structured import (
    bind_structured,
    invoke_structured_or_freetext,
)
from invest_agents.agents.schemas import MoatReport


def create_moat_analyst(llm):
    """Create the Moat Analyst node — competitive advantage + management quality."""

    tools = [
        get_key_metrics,
        get_roe_roic_trends,
        get_income_statement,
        get_balance_sheet,
        get_cashflow,
        get_10k_filing,
    ]

    system_message = (
        "You are a Moat & Quality Analyst evaluating a company's long-term "
        "competitive position. Your job is to determine whether the company "
        "has a durable competitive advantage (moat) that will protect returns "
        "on capital over a 5+ year horizon.\n\n"
        "Analyze:\n"
        "1. **Moat Sources**: switching costs, network effects, intangible assets "
        "(brands, patents, regulatory licenses), cost advantage, efficient scale.\n"
        "2. **ROIC Trends**: Is ROIC consistently above WACC? Is it stable, "
        "growing, or declining? What drives it?\n"
        "3. **Management**: Capital allocation track record — smart buybacks? "
        "Value-creating M&A? Insider ownership? Compensation aligned with long-term?\n"
        "4. **Competitive Threats**: Disruption risk, new entrants, substitution.\n\n"
        "Be specific. Name competitors. Cite historical ROIC numbers. "
        "This is the foundation of a long-term investment thesis.\n\n"
        + "Use the available tools: `get_key_metrics`, `get_roe_roic_trends` "
        "for profitability data, `get_income_statement`/`get_balance_sheet`/`get_cashflow` "
        "for financial statements, and `get_10k_filing` for the business description.\n"
        + get_language_instruction(),
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant, collaborating with other analysts.\n"
            "Use the provided tools to gather data. If you can't answer everything, "
            "that's OK — other analysts will fill gaps.\n"
            "You have access to: {tool_names}.\n{system_message}\n"
            "Current date: {current_date}. {instrument_context}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join(t.name for t in tools))

    def moat_analyst_node(state):
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
            "moat_report": report,
        }

    return moat_analyst_node
