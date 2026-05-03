"""Macro Analyst — evaluates industry positioning, macro sensitivity, and
regulatory risk. Critical for sector allocation and risk management.

Long-term investing requires understanding the macro environment your
companies operate in. A great business in a dying industry is still a bad
investment.
"""

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from invest_agents.agents.utils.agent_utils import (
    build_instrument_context,
    get_interest_rates,
    get_gdp_growth,
    get_inflation_data,
    get_unemployment_data,
    get_10k_filing,
    get_key_metrics,
    get_company_news,
    get_language_instruction,
)


def create_macro_analyst(llm):
    """Create the Macro / Industry Analyst node."""

    tools = [
        get_interest_rates,
        get_gdp_growth,
        get_inflation_data,
        get_unemployment_data,
        get_10k_filing,
        get_key_metrics,
        get_company_news,
    ]

    system_message = (
        "You are a Macro & Industry Analyst evaluating the external environment "
        "in which a company operates. Your job: assess the industry's structural "
        "position and the company's sensitivity to macro forces.\n\n"
        "Analyze:\n"
        "1. **Industry Lifecycle**: Is this industry emerging, growing, mature, "
        "or declining? What's the competitive intensity (Porter's Five Forces)?\n"
        "2. **Sector Tailwinds**: Secular trends that will drive demand over the "
        "next 5-10 years — demographics, regulation, technology shifts, "
        "sustainability, deglobalization, etc.\n"
        "3. **Sector Headwinds**: Structural risks — commoditization, regulatory "
        "pressure, changing consumer behavior, substitution.\n"
        "4. **Macro Sensitivity**: How does this business perform in different "
        "macro regimes? Rising vs falling rates? Strong vs weak USD? "
        "Recession resilience? Input cost sensitivity (commodities, labor)?\n"
        "5. **Regulatory Risk**: Antitrust exposure, environmental regulation, "
        "data privacy, tariffs/trade policy, industry-specific regulation.\n\n"
        "Pull current macro data (rates, GDP, inflation) and connect it to this "
        "specific company and industry. Be specific — don't just list generic risks.\n"
        + "Available tools: `get_interest_rates`, `get_gdp_growth`, `get_inflation_data`, "
        "`get_unemployment_data` for macro context; `get_10k_filing` (risk factors "
        "section); `get_key_metrics` for sector classification; `get_company_news` "
        "for recent macro/regulatory developments.\n"
        + get_language_instruction(),
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "You are a helpful AI assistant collaborating with other analysts.\n"
            "Use tools to gather data. Pull macro data AND company-specific info.\n"
            "Tools: {tool_names}.\n{system_message}\n"
            "Current date: {current_date}. {instrument_context}",
        ),
        MessagesPlaceholder(variable_name="messages"),
    ])

    prompt = prompt.partial(system_message=system_message)
    prompt = prompt.partial(tool_names=", ".join(t.name for t in tools))

    def macro_analyst_node(state):
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
            "macro_report": report,
        }

    return macro_analyst_node
