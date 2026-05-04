#!/usr/bin/env python3
"""Benchmark: sequential vs parallel analyst execution in InvestAgents.

Simulates LLM calls with fixed delays so we measure the graph orchestration
overhead, not API latency variance.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

# Ensure invest_agents is importable
_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

import logging

logging.basicConfig(level=logging.WARNING)  # quiet

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.outputs import ChatResult, ChatGeneration

from invest_agents.default_config import DEFAULT_CONFIG
from invest_agents.dataflows.config import set_config


# ---------------------------------------------------------------------------
# Mock LLM: simulates a model that "thinks" for `delay` seconds
# ---------------------------------------------------------------------------


class MockDelayedLLM(BaseChatModel):
    """Fake LLM that sleeps then returns a fixed response with no tool calls."""

    delay: float = 0.5
    model_name: str = "mock-delayed"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        time.sleep(self.delay)
        return ChatResult(
            generations=[
                ChatGeneration(
                    message=AIMessage(content=f"[Mock analysis after {self.delay}s]")
                )
            ]
        )

    def _llm_type(self) -> str:
        return "mock-delayed"

    def bind_tools(self, tools, **kwargs):
        """Return a copy that also has bind_tools (for chaining)."""
        return self


# ---------------------------------------------------------------------------
# Benchmark
# ---------------------------------------------------------------------------


def build_and_run(parallel: bool, delay: float, ticker: str = "COST") -> float:
    """Build graph and run one invocation, return elapsed seconds."""
    from invest_agents.graph.invest_graph import InvestAgentsGraph
    from invest_agents.graph.setup import DeepDiveGraphSetup, PortfolioGraphSetup

    config = DEFAULT_CONFIG.copy()
    config["parallel_analysts"] = parallel
    config["max_debate_rounds"] = 1
    config["llm_provider"] = "openai"  # won't matter — we replace the LLMs
    set_config(config)

    mock = MockDelayedLLM(delay=delay)

    # Build InvestAgentsGraph normally, then swap LLMs + rebuild
    lta = InvestAgentsGraph.__new__(InvestAgentsGraph)
    lta.debug = False
    lta.config = config
    lta.quick_llm = mock
    lta.deep_llm = mock
    lta.tool_nodes = lta._create_tool_nodes()
    from invest_agents.graph.conditional_logic import ConditionalLogic

    lta.conditional = ConditionalLogic(
        max_debate_rounds=config.get("max_debate_rounds", 2),
    )
    lta.deep_dive_setup = DeepDiveGraphSetup(
        lta.quick_llm, lta.deep_llm, lta.tool_nodes, lta.conditional,
        parallel_analysts=parallel,
    )
    lta.portfolio_setup = PortfolioGraphSetup(lta.deep_llm)
    lta.deep_dive_workflow = lta.deep_dive_setup.setup_graph()
    lta.deep_dive_graph = lta.deep_dive_workflow.compile()

    initial_state = {
        "company_of_interest": ticker,
        "trade_date": "2025-01-01",
        "messages": [HumanMessage(content=f"Analyze {ticker}.")],
        "moat_report": "",
        "valuation_report": "",
        "growth_report": "",
        "macro_report": "",
        "thesis_debate_state": {
            "history": "",
            "bull_history": "",
            "bear_history": "",
            "current_response": "",
            "current_bull_response": "",
            "current_bear_response": "",
            "count": 0,
        },
        "investment_thesis": "",
        "investment_thesis_structured": {},
        "past_context": "",
    }

    t0 = time.perf_counter()
    lta.deep_dive_graph.invoke(initial_state)
    return time.perf_counter() - t0


def main():
    delay = float(sys.argv[1]) if len(sys.argv) > 1 else 0.5

    print(f"🧪 InvestAgents Parallelism Benchmark")
    print(f"   Mock LLM delay per call: {delay}s")
    print()

    # Theory
    seq_analyst = 4 * delay
    par_analyst = delay
    debate_thesis = 3 * delay  # bull + bear + thesis
    pred_seq = seq_analyst + debate_thesis
    pred_par = par_analyst + debate_thesis
    pred_speedup = pred_seq / pred_par

    print("  ┌────────────────────────────────────────┐")
    print("  │  Theoretical prediction                │")
    print(f"  │  Sequential analysts: {seq_analyst:.1f}s  (4 × {delay}s)        │")
    print(f"  │  Parallel analysts:   {par_analyst:.1f}s  (max of 4 × {delay}s)  │")
    print(f"  │  Debate + Thesis:     {debate_thesis:.1f}s  (shared)              │")
    print(f"  │  Predicted speedup:   {pred_speedup:.2f}x                      │")
    print("  └────────────────────────────────────────┘")
    print()

    # Warmup
    print("  Warming up...")
    build_and_run(parallel=False, delay=delay)
    build_and_run(parallel=True, delay=delay)

    # Benchmark
    runs_per_mode = 3
    print(f"  Running benchmark ({runs_per_mode} runs each)...")
    print()

    for mode, parallel in [("sequential", False), ("parallel", True)]:
        label = f"⚡ {mode}" if parallel else f"🐢 {mode}"
        times = []
        for i in range(runs_per_mode):
            elapsed = build_and_run(parallel=parallel, delay=delay)
            times.append(elapsed)
            print(f"    {label}  run {i+1}: {elapsed:.3f}s")

        avg = sum(times) / len(times)
        print(f"    {label}  avg: {avg:.3f}s  min: {min(times):.3f}s")
        print()

        if mode == "sequential":
            seq_avg = avg
            seq_times = times
        else:
            par_avg = avg
            par_times = times

    speedup = seq_avg / par_avg
    time_saved = seq_avg - par_avg

    print("  ╔════════════════════════════════════════╗")
    print(f"  ║  ⚡ SPEEDUP: {speedup:.2f}x faster                  ║")
    print(f"  ║  🐢 Sequential: {seq_avg:.3f}s                     ║")
    print(f"  ║  ⚡ Parallel:   {par_avg:.3f}s                     ║")
    print(f"  ║  💰 Saved/stock: {time_saved:.3f}s                    ║")
    print("  ╚════════════════════════════════════════╝")

    if speedup > 1.3:
        print(f"\n  ✅ Worth it! {speedup:.1f}x means ~{time_saved*10:.0f}s saved per 10 stocks.")
    else:
        print(f"\n  ⚠️  Overhead is eating gains. Speedup {speedup:.2f}x.")


if __name__ == "__main__":
    main()
