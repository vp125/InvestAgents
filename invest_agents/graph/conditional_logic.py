"""Conditional logic for InvestAgents LangGraph routing.

Controls:
  - Tool-call loops within each analyst
  - Bull/Bear debate round limits
"""

from typing import Callable

from invest_agents.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles all conditional edges in the agent graph."""

    def __init__(self, max_debate_rounds: int = 2):
        self.max_debate_rounds = max_debate_rounds

    def should_continue_analyst(
        self, tool_node: str, clear_node: str
    ) -> Callable[[AgentState], str]:
        """Return a routing function for analyst tool loops."""

        def router(state: AgentState) -> str:
            messages = state["messages"]
            last_message = messages[-1]
            if hasattr(last_message, "tool_calls") and last_message.tool_calls:
                return tool_node
            return clear_node

        return router

    def should_continue_debate(self, state: AgentState) -> str:
        """Route between Bull/Bear researchers and Thesis Manager.

        After max_debate_rounds * 2 exchanges (one bull + one bear per round),
        the debate ends and flows to the Thesis Manager.
        """
        debate_state = state["thesis_debate_state"]
        count = debate_state.get("count", 0)
        max_exchanges = 2 * self.max_debate_rounds

        if count >= max_exchanges:
            return "Thesis Manager"

        current = debate_state.get("current_response", "")
        if current.startswith("Bull"):
            return "Bear Researcher"
        return "Bull Researcher"
