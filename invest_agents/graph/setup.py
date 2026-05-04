"""LangGraph setup for InvestAgents.

Builds two graphs:
  1. **Stock Deep-Dive Graph**: Analysts → Bull/Bear Debate → Thesis Manager
  2. **Portfolio Construction Graph**: Aggregate Theses → Portfolio Constructor

The deep-dive graph is run per-stock; results feed into the portfolio graph.

Analyst execution mode:
  - **parallel** (default): All 4 analysts (Moat, Valuation, Growth, Macro) run
    concurrently via ThreadPoolExecutor. ~2-4x faster on LLM latency.
  - **sequential**: Analysts run one after another. Original behaviour.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

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


# ---------------------------------------------------------------------------
# Helper: run a single analyst with its tool loop → return messages + report
# ---------------------------------------------------------------------------

ANALYST_NAMES = ["Moat", "Valuation", "Growth", "Macro"]
ANALYST_REPORT_KEYS = {
    "Moat": "moat_report",
    "Valuation": "valuation_report",
    "Growth": "growth_report",
    "Macro": "macro_report",
}

def _run_analyst_loop(
    name: str,
    analyst_fn,
    tools_by_name: dict,
    messages: List,
    current_date: str,
    ticker: str,
) -> tuple:
    """Run one analyst with its tool-calling loop, return (name, msg, report).

    Designed to be called from a thread — each analyst gets its own copy
    of the message list and runs independently.  We call tool functions
    directly (not via ToolNode.invoke) because LangGraph's ToolNode
    requires a runtime config that doesn't exist inside raw threads.
    """
    from langchain_core.messages import AIMessage, ToolMessage

    msgs = list(messages)

    max_turns = 6
    for _ in range(max_turns):
        state = {
            "company_of_interest": ticker,
            "trade_date": current_date,
            "messages": msgs,
        }
        result = analyst_fn(state)
        msgs.extend(result.get("messages", []))

        last_msg = msgs[-1] if msgs else None
        if last_msg and hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
            # Execute tool calls directly (no LangGraph config needed)
            for tc in last_msg.tool_calls:
                tool_name = tc.get("name", "")
                tool_fn = tools_by_name.get(tool_name)
                if tool_fn is not None:
                    try:
                        tool_output = tool_fn.invoke(tc.get("args", {}))
                        msgs.append(ToolMessage(
                            content=str(tool_output),
                            tool_call_id=tc.get("id", ""),
                            name=tool_name,
                        ))
                    except Exception as e:
                        msgs.append(ToolMessage(
                            content=f"Tool error: {e}",
                            tool_call_id=tc.get("id", ""),
                            name=tool_name,
                        ))
                else:
                    msgs.append(ToolMessage(
                        content=f"Unknown tool: {tool_name}",
                        tool_call_id=tc.get("id", ""),
                        name=tool_name,
                    ))
        else:
            break

    # Extract report from last non-tool AI message
    report = ""
    for m in reversed(msgs):
        content = getattr(m, "content", "") or ""
        has_tools = hasattr(m, "tool_calls") and m.tool_calls
        if content and not has_tools:
            report = content
            break

    return name, AIMessage(content=report or f"[{name}] Analysis complete."), report
    return name, AIMessage(content=report or f"[{name}] Analysis complete."), report


# ---------------------------------------------------------------------------
# Deep-Dive Graph
# ---------------------------------------------------------------------------


class DeepDiveGraphSetup:
    """Sets up the per-stock deep-dive analysis graph."""

    def __init__(
        self,
        quick_thinking_llm: Any,
        deep_thinking_llm: Any,
        tool_nodes: Dict[str, ToolNode],
        conditional_logic: ConditionalLogic,
        parallel_analysts: bool = True,
    ):
        self.quick_llm = quick_thinking_llm
        self.deep_llm = deep_thinking_llm
        self.tool_nodes = tool_nodes
        self.conditional = conditional_logic
        self.parallel = parallel_analysts

    # ------------------------------------------------------------------
    # Analyst node factories
    # ------------------------------------------------------------------

    def _create_analyst_nodes(self) -> Dict[str, Any]:
        return {
            "Moat": create_moat_analyst(self.quick_llm),
            "Valuation": create_valuation_analyst(self.quick_llm),
            "Growth": create_growth_analyst(self.quick_llm),
            "Macro": create_macro_analyst(self.quick_llm),
        }

    # ------------------------------------------------------------------
    # Parallel mode: single node runs all 4 analysts via ThreadPoolExecutor
    # ------------------------------------------------------------------

    def _create_parallel_analysts_node(self):
        """Return a node function that runs all 4 analysts in parallel threads.

        Each analyst runs its own tool-calling loop independently.
        Results are merged and returned as a single state update.
        """
        analysts = self._create_analyst_nodes()
        # Build tools_by_name dicts for each analyst (needed for direct tool
        # invocation in threads — ToolNode.invoke requires LangGraph config)
        tools_by_analyst = {}
        for name in ANALYST_NAMES:
            tn = self.tool_nodes[name.lower()]
            tools_by_analyst[name] = tn.tools_by_name if hasattr(tn, 'tools_by_name') else {}

        def parallel_analysts_node(state: AgentState) -> dict:
            ticker = state["company_of_interest"]
            current_date = state["trade_date"]
            messages = state["messages"]

            results: Dict[str, tuple] = {}

            with ThreadPoolExecutor(max_workers=4) as executor:
                futures = {}
                for name in ANALYST_NAMES:
                    future = executor.submit(
                        _run_analyst_loop,
                        name,
                        analysts[name],
                        tools_by_analyst[name],
                        messages,
                        current_date,
                        ticker,
                    )
                    futures[future] = name

                for future in as_completed(futures):
                    name, final_msg, report = future.result()
                    results[name] = (final_msg, report)

            # Merge: one clean AIMessage per analyst + report fields
            all_messages = []
            report_updates = {}
            for name, (msg, report) in results.items():
                all_messages.append(msg)
                report_key = ANALYST_REPORT_KEYS[name]
                report_updates[report_key] = report

            return {
                "messages": all_messages,
                **report_updates,
            }

        return parallel_analysts_node

    # ------------------------------------------------------------------
    # Sequential mode (original)
    # ------------------------------------------------------------------

    def _setup_sequential(self, workflow: StateGraph) -> None:
        """Original sequential analyst chain."""
        analysts = self._create_analyst_nodes()

        prev_clear_node = None
        for i, name in enumerate(ANALYST_NAMES):
            clear_node = f"Msg Clear {name}"
            tools_node = f"tools_{name.lower()}"

            workflow.add_node(name, analysts[name])
            workflow.add_node(clear_node, create_msg_delete())
            workflow.add_node(tools_node, self.tool_nodes[name.lower()])

            if i == 0:
                workflow.add_edge(START, name)
            else:
                workflow.add_edge(prev_clear_node, name)

            workflow.add_conditional_edges(
                name,
                self.conditional.should_continue_analyst(tools_node, clear_node),
                [tools_node, clear_node],
            )
            workflow.add_edge(tools_node, name)
            prev_clear_node = clear_node

        workflow.add_edge(prev_clear_node, "Bull Researcher")

    # ------------------------------------------------------------------
    # Common: debate + thesis
    # ------------------------------------------------------------------

    def _setup_debate_and_thesis(self, workflow: StateGraph) -> None:
        workflow.add_node("Bull Researcher", create_bull_researcher(self.quick_llm))
        workflow.add_node("Bear Researcher", create_bear_researcher(self.quick_llm))
        workflow.add_node("Thesis Manager", create_thesis_manager(self.deep_llm))

        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional.should_continue_debate,
            {"Bear Researcher": "Bear Researcher", "Thesis Manager": "Thesis Manager"},
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional.should_continue_debate,
            {"Bull Researcher": "Bull Researcher", "Thesis Manager": "Thesis Manager"},
        )
        workflow.add_edge("Thesis Manager", END)

    # ------------------------------------------------------------------
    # Main entry
    # ------------------------------------------------------------------

    def setup_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        if self.parallel:
            workflow.add_node("Analysts", self._create_parallel_analysts_node())
            workflow.add_edge(START, "Analysts")
            workflow.add_edge("Analysts", "Bull Researcher")
        else:
            self._setup_sequential(workflow)

        self._setup_debate_and_thesis(workflow)
        return workflow


# ---------------------------------------------------------------------------
# Portfolio Construction Graph (unchanged)
# ---------------------------------------------------------------------------


class PortfolioGraphSetup:
    """Sets up the portfolio construction graph (run after all stocks analyzed)."""

    def __init__(self, deep_thinking_llm: Any):
        self.deep_llm = deep_thinking_llm

    def setup_graph(self) -> StateGraph:
        workflow = StateGraph(PortfolioState)
        workflow.add_node(
            "Portfolio Constructor",
            create_portfolio_constructor(self.deep_llm),
        )
        workflow.add_edge(START, "Portfolio Constructor")
        workflow.add_edge("Portfolio Constructor", END)
        return workflow
