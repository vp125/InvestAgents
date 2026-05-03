"""Growth Analyst — evaluates revenue/earnings trends, TAM, and reinvestment runway.

Long-term returns are driven by earnings growth. This analyst assesses whether
growth is high-quality (profitable, sustainable) or value-destructive.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from invest_agents.agents.utils.agent_utils import (
    build_instrument_context,
    get_income_statement,
    get_cashflow,
    get_key_metrics,
    get_10k_filing,
    get_company_news,
    get_language_instruction,
)


def create_growth_analyst(llm):
    """Create the Growth Analyst node."""

    tools = [
        get_key_metrics,
        get_income_statement,
        get_cashflow,
        get_10k_filing,
        get_company_news,
    ]

    system_message = (
        "You are a Growth Analyst evaluating a company's growth trajectory over "
        "a 3-7 year horizon. Your job: assess whether growth is sustainable, "
        "profitable, and has a long runway.\n\n"
        "Analyze:\n"
        "1. **Historical Growth**: 5-year revenue CAGR, earnings CAGR, FCF/share "
        "CAGR. Is growth accelerating, steady, or decelerating?\n"
        "2. **Growth Drivers**: Unit volume vs price increases. New markets or "
        "geographies. Product cycles. M&A contribution. Secular tailwinds.\n"
        "3. **TAM Assessment**: Total Addressable Market size and current penetration. "
        "How much runway remains? Is the company gaining or losing share?\n"
        "4. **Reinvestment Opportunity**: Can the company reinvest earnings at high "
        "rates of return? What's the incremental ROIC? Are there organic growth "
        "opportunities or is capital being wasted on low-return projects?\n"
        "5. **Growth Quality**: Is growth profitable? Look at unit economics. "
        "Are margins expanding with scale (operating leverage) or being sacrificed "
        "for growth (land-grab dynamics)? FCF conversion rate?\n\n"
        "Cite specific growth rates, margin trends, and market data.\n"
        + "Available tools: `get_key_metrics` for growth rates and margins, "
        "`get_income_statement`/`get_cashflow` for trend analysis, "
        "`get_10k_filing` for business/TAM description, and `get_company_news` "
        "for recent growth developments.\n"
        + get_language_instruction(),
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant collaborating with other analysts.\n"
            "Use tools to gather data. If you can't answer everything, that's OK.\n"
            "Tools: {tool_names}.\n{system_message}\n"
            "Current date: {current_date}. {instrument_context}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join(t.name for t in tools))

    def growth_analyst_node(state):
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
            "growth_report": report,
        }

    return growth_analyst_node
