"""LangGraph setup for InvestAgents.

Builds two graphs:
  1. **Stock Deep-Dive Graph**: Analysts → Bull/Bear Debate → Thesis Manager
  2. **Portfolio Construction Graph**: Aggregate Theses → Portfolio Constructor

The deep-dive graph is run per-stock; results feed into the portfolio graph.
"""

from typing import Any, Dict

from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from invest_agents.agents import (
    create_moat_analyst,
    create_valuation_analyst,
    create_growth_analyst,
    create_macro_analyst,
    create_bull_researcher,
    create_bear_researcher,
    create_thesis_manager,
    create_portfolio_constructor,
)
from invest_agents.agents.utils.agent_states import AgentState, PortfolioState
from invest_agents.agents.utils.agent_utils import create_msg_delete

from .conditional_logic import ConditionalLogic


class DeepDiveGraphSetup:
    """Sets up the per-stock deep-dive analysis graph."""

    def __init__(
        self,
        quick_thinking_llm: Any,
        deep_thinking_llm: Any,
        tool_nodes: Dict[str, ToolNode],
        conditional_logic: ConditionalLogic,
    ):
        self.quick_llm = quick_thinking_llm
        self.deep_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.conditional = conditional_logic

    def setup_graph(self) -> StateGraph:
        """Build the stock deep-dive workflow:

        START → Moat Analyst ⇄ tools_moat → Msg Clear Moat
              → Valuation Analyst ⇄ tools_valuation → Msg Clear Valuation
              → Growth Analyst ⇄ tools_growth → Msg Clear Growth
              → Macro Analyst ⇄ tools_macro → Msg Clear Macro
              → Bull Researcher ⇄ Bear Researcher (debate loop)
              → Thesis Manager → END
        """
        workflow = StateGraph(AgentState)

        # -- Analyst nodes --
        workflow.add_node("Moat Analyst", create_moat_analyst(self.quick_llm))
        workflow.add_node("Msg Clear Moat", create_msg_delete())
        workflow.add_node("tools_moat", self.tool_nodes["moat"])

        workflow.add_node("Valuation Analyst", create_valuation_analyst(self.quick_llm))
        workflow.add_node("Msg Clear Valuation", create_msg_delete())
        workflow.add_node("tools_valuation", self.tool_nodes["valuation"])

        workflow.add_node("Growth Analyst", create_growth_analyst(self.quick_llm))
        workflow.add_node("Msg Clear Growth", create_msg_delete())
        workflow.add_node("tools_growth", self.tool_nodes["growth"])

        workflow.add_node("Macro Analyst", create_macro_analyst(self.quick_llm))
        workflow.add_node("Msg Clear Macro", create_msg_delete())
        workflow.add_node("tools_macro", self.tool_nodes["macro"])

        # -- Researchers & Manager --
        workflow.add_node("Bull Researcher", create_bull_researcher(self.quick_llm))
        workflow.add_node("Bear Researcher", create_bear_researcher(self.quick_llm))
        workflow.add_node("Thesis Manager", create_thesis_manager(self.deep_llm))

        # -- Edges: Analyst chain --
        # Moat
        workflow.add_edge(START, "Moat Analyst")
        workflow.add_conditional_edges(
            "Moat Analyst",
            self.conditional.should_continue_analyst("tools_moat", "Msg Clear Moat"),
            ["tools_moat", "Msg Clear Moat"],
        )
        workflow.add_edge("tools_moat", "Moat Analyst")
        workflow.add_edge("Msg Clear Moat", "Valuation Analyst")

        # Valuation
        workflow.add_conditional_edges(
            "Valuation Analyst",
            self.conditional.should_continue_analyst("tools_valuation", "Msg Clear Valuation"),
            ["tools_valuation", "Msg Clear Valuation"],
        )
        workflow.add_edge("tools_valuation", "Valuation Analyst")
        workflow.add_edge("Msg Clear Valuation", "Growth Analyst")

        # Growth
        workflow.add_conditional_edges(
            "Growth Analyst",
            self.conditional.should_continue_analyst("tools_growth", "Msg Clear Growth"),
            ["tools_growth", "Msg Clear Growth"],
        )
        workflow.add_edge("tools_growth", "Growth Analyst")
        workflow.add_edge("Msg Clear Growth", "Macro Analyst")

        # Macro
        workflow.add_conditional_edges(
            "Macro Analyst",
            self.conditional.should_continue_analyst("tools_macro", "Msg Clear Macro"),
            ["tools_macro", "Msg Clear Macro"],
        )
        workflow.add_edge("tools_macro", "Macro Analyst")
        workflow.add_edge("Msg Clear Macro", "Bull Researcher")

        # -- Debate loop --
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Thesis Manager": "Thesis Manager",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Thesis Manager": "Thesis Manager",
            },
        )

        # -- Final --
        workflow.add_edge("Thesis Manager", END)

        return workflow


class PortfolioGraphSetup:
    """Sets up the portfolio construction graph (run after all stocks analyzed)."""

    def __init__(self, deep_thinking_llm: Any):
        self.deep_llm = deep_thinking_llm

    def setup_graph(self) -> StateGraph:
        """Build the portfolio construction workflow:

        START → Portfolio Constructor → END
        """
        workflow = StateGraph(PortfolioState)

        workflow.add_node(
            "Portfolio Constructor",
            create_portfolio_constructor(self.deep_llm),
        )
        workflow.add_edge(START, "Portfolio Constructor")
        workflow.add_edge("Portfolio Constructor", END)

        return workflow
