#!/usr/bin/env python3
"""Interactive CLI for InvestAgents — thesis-driven long-term stock analysis.

Usage:
    invest-agents              # interactive mode (full TUI)
    invest-agents AEHR         # quick single-stock analysis
    invest-agents AEHR COST    # multi-stock + portfolio construction
    invest-agents --help       # show options
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.layout import Layout
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.prompt import Prompt, Confirm
from rich.align import Align

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SUPPORTED_PROVIDERS = {
    "deepseek": {"env": "DEEPSEEK_API_KEY", "label": "DeepSeek (V3/R1)"},
    "openai": {"env": "OPENAI_API_KEY", "label": "OpenAI (GPT-5.x)"},
    "anthropic": {"env": "ANTHROPIC_API_KEY", "label": "Anthropic (Claude)"},
    "google": {"env": "GOOGLE_API_KEY", "label": "Google (Gemini)"},
}

PROVIDER_MODELS = {
    "deepseek": ["deepseek-chat", "deepseek-reasoner"],
    "openai": ["gpt-5.4-mini", "gpt-5.4", "gpt-4o-mini", "gpt-4o"],
    "anthropic": ["claude-sonnet-4-20250514", "claude-haiku-3-5-20250514"],
    "google": ["gemini-2.5-flash", "gemini-2.5-pro"],
}

LANGUAGES = ["English", "Vietnamese", "Japanese", "Korean", "Chinese", "French",
             "German", "Spanish", "Portuguese", "Russian"]

console = Console()
logger = logging.getLogger("investagents.cli")


# ---------------------------------------------------------------------------
# API key detection
# ---------------------------------------------------------------------------

def detect_available_providers() -> list[str]:
    """Return providers whose API keys are set."""
    available = []
    for name, info in SUPPORTED_PROVIDERS.items():
        if os.getenv(info["env"]):
            available.append(name)
    return available


def detect_fred_key() -> bool:
    return bool(os.getenv("FRED_API_KEY"))


# ---------------------------------------------------------------------------
# Interactive menus
# ---------------------------------------------------------------------------

def show_welcome():
    """Display the welcome banner."""
    banner_path = Path(__file__).parent / "static" / "welcome.txt"
    if banner_path.exists():
        console.print(banner_path.read_text(), style="bold cyan")
    else:
        console.print(Panel("🐶 InvestAgents", style="bold cyan"))


def select_provider() -> str:
    """Let user pick an LLM provider."""
    available = detect_available_providers()

    table = Table(title="Available LLM Providers", border_style="cyan")
    table.add_column("#", style="dim")
    table.add_column("Provider")
    table.add_column("Status")

    for i, (name, info) in enumerate(SUPPORTED_PROVIDERS.items(), 1):
        status = "[green]✅ Key found[/green]" if name in available else "[red]❌ No key[/red]"
        table.add_row(str(i), info["label"], status)

    console.print(table)

    if not available:
        console.print(
            "\n[red]No API keys found! Set one in your .env file:[/red]\n"
            "  DEEPSEEK_API_KEY=sk-...\n"
            "  OPENAI_API_KEY=sk-...\n"
            "  ANTHROPIC_API_KEY=sk-...\n"
            "  GOOGLE_API_KEY=..."
        )
        sys.exit(1)

    # Default to first available
    default_idx = 1
    for i, name in enumerate(SUPPORTED_PROVIDERS, 1):
        if name in available:
            default_idx = i
            break

    choice = Prompt.ask(
        f"Select provider",
        choices=[str(i) for i in range(1, len(SUPPORTED_PROVIDERS) + 1)],
        default=str(default_idx),
    )
    return list(SUPPORTED_PROVIDERS.keys())[int(choice) - 1]


def select_models(provider: str) -> tuple[str, str]:
    """Let user pick deep and quick thinking models."""
    models = PROVIDER_MODELS.get(provider, ["default"])
    console.print(f"\n[bold]Models for {provider}:[/bold]")

    for i, m in enumerate(models, 1):
        tag = ""
        if "mini" in m.lower() or "haiku" in m.lower() or "flash" in m.lower():
            tag = " [dim](fast)[/dim]"
        elif "reasoner" in m.lower() or "pro" in m.lower() or "sonnet" in m.lower():
            tag = " [yellow](deep)[/yellow]"
        console.print(f"  {i}. {m}{tag}")

    deep_choice = Prompt.ask(
        "Deep thinking model (thesis synthesis, portfolio construction)",
        choices=[str(i) for i in range(1, len(models) + 1)],
        default=str(min(2, len(models))),
    )
    quick_choice = Prompt.ask(
        "Quick thinking model (analyst reports, debate)",
        choices=[str(i) for i in range(1, len(models) + 1)],
        default="1",
    )

    return models[int(deep_choice) - 1], models[int(quick_choice) - 1]


def select_language() -> str:
    """Let user pick output language."""
    console.print("\n[bold]Output Language:[/bold]")
    for i, lang in enumerate(LANGUAGES, 1):
        console.print(f"  {i}. {lang}")

    choice = Prompt.ask(
        "Select language",
        choices=[str(i) for i in range(1, len(LANGUAGES) + 1)],
        default="1",
    )
    return LANGUAGES[int(choice) - 1]


def select_debate_rounds() -> int:
    """Let user pick research depth."""
    console.print("\n[bold]Research Depth (Bull/Bear Debate Rounds):[/bold]")
    console.print("  0. Quick — analyst reports only, no debate")
    console.print("  1. Standard — one bull/bear exchange [dim](recommended)[/dim]")
    console.print("  2. Deep — two rounds of back-and-forth [dim](slower, more thorough)[/dim]")

    choice = Prompt.ask("Select depth", choices=["0", "1", "2"], default="1")
    return int(choice)


def get_tickers() -> list[str]:
    """Get tickers from user input."""
    console.print("\n[bold]Ticker Symbols:[/bold]")
    console.print("  Enter one or more tickers separated by spaces or commas.")
    console.print("  Examples: [dim]COST[/dim], [dim]AEHR GOOGL BRK.B[/dim]")

    raw = Prompt.ask("Tickers")
    # Split on spaces or commas
    tickers = [t.strip().upper() for t in raw.replace(",", " ").split() if t.strip()]
    if not tickers:
        console.print("[red]No tickers entered![/red]")
        return get_tickers()
    return tickers


def select_date() -> str:
    """Let user pick analysis date (default: latest available trading day)."""
    today = datetime.now()
    # Default to yesterday for data availability
    default = (today - timedelta(days=1)).strftime("%Y-%m-%d")
    if today.weekday() == 0:  # Monday → use Friday
        default = (today - timedelta(days=3)).strftime("%Y-%m-%d")

    date_str = Prompt.ask(
        "Analysis date (YYYY-MM-DD), or Enter for latest",
        default=default,
    )
    # Validate
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return date_str
    except ValueError:
        console.print("[red]Invalid date format![/red]")
        return select_date()


# ---------------------------------------------------------------------------
# Live progress display
# ---------------------------------------------------------------------------

class AnalysisProgress:
    """Live progress tracker for the analysis pipeline."""

    def __init__(self, ticker: str):
        self.ticker = ticker
        self.status = {
            "moat": "⏳ Pending",
            "valuation": "⏳ Pending",
            "growth": "⏳ Pending",
            "macro": "⏳ Pending",
            "bull": "⏳ Pending",
            "bear": "⏳ Pending",
            "thesis": "⏳ Pending",
        }
        self.current_stage = "Initializing..."
        self.moat_report = ""
        self.valuation_report = ""
        self.growth_report = ""
        self.macro_report = ""
        self.thesis_output = ""
        self._lock = threading.Lock()

    def update_stage(self, stage: str):
        with self._lock:
            self.current_stage = stage

    def update_status(self, key: str, status: str, report: str = ""):
        with self._lock:
            self.status[key] = status
            if report:
                if key == "moat":
                    self.moat_report = report
                elif key == "valuation":
                    self.valuation_report = report
                elif key == "growth":
                    self.growth_report = report
                elif key == "macro":
                    self.macro_report = report
                elif key == "thesis":
                    self.thesis_output = report

    def render(self) -> Layout:
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="body"),
        )

        # Header
        header_text = Text(f"🔬 Analyzing: {self.ticker}", style="bold cyan")
        header_text.append(f"\nStage: {self.current_stage}", style="dim")
        layout["header"].update(Panel(header_text))

        # Body: progress + latest reports
        body = Layout()
        body.split_row(
            Layout(name="progress", ratio=1),
            Layout(name="reports", ratio=2),
        )

        # Progress table
        progress_table = Table(show_header=False, box=None, padding=(0, 1))
        for key, label in [
            ("moat", "🏰 Moat Analyst"),
            ("valuation", "💰 Valuation Analyst"),
            ("growth", "📈 Growth Analyst"),
            ("macro", "🌐 Macro Analyst"),
            ("bull", "🐂 Bull Researcher"),
            ("bear", "🐻 Bear Researcher"),
            ("thesis", "📋 Thesis Manager"),
        ]:
            status = self.status.get(key, "⏳ Pending")
            style = "green" if "✅" in status else "yellow" if "🔄" in status else "dim"
            progress_table.add_row(f"[{style}]{status}[/{style}]  {label}")

        body["progress"].update(Panel(progress_table, title="Pipeline"))

        # Latest report
        report_text = ""
        if self.thesis_output:
            report_text = self.thesis_output[:800] + ("..." if len(self.thesis_output) > 800 else "")
        elif self.macro_report:
            report_text = self.macro_report[:800]
        elif self.growth_report:
            report_text = self.growth_report[:800]
        elif self.valuation_report:
            report_text = self.valuation_report[:800]
        elif self.moat_report:
            report_text = self.moat_report[:800]
        else:
            report_text = "[dim]Waiting for first analyst report...[/dim]"

        body["reports"].update(
            Panel(report_text, title="Latest Output", border_style="green")
        )

        layout["body"].update(body)
        return layout


# ---------------------------------------------------------------------------
# Main CLI entry
# ---------------------------------------------------------------------------

def main():
    """Main CLI entry point."""
    # Quick mode: if tickers passed as args, skip interactive menus
    args = sys.argv[1:]
    quick_mode = len(args) > 0 and not args[0].startswith("-")

    if quick_mode:
        return _run_quick_mode(args)

    # Interactive mode
    return _run_interactive_mode()


def _run_quick_mode(tickers: list[str]):
    """Non-interactive: just run analysis on given tickers."""
    from invest_agents.graph.invest_graph import InvestAgentsGraph
    from invest_agents.default_config import DEFAULT_CONFIG

    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = os.getenv("INVESTAGENTS_LLM_PROVIDER", "deepseek")
    config["deep_think_llm"] = os.getenv("INVESTAGENTS_DEEP_MODEL", "deepseek-chat")
    config["quick_think_llm"] = os.getenv("INVESTAGENTS_QUICK_MODEL", "deepseek-chat")
    config["max_debate_rounds"] = int(os.getenv("INVESTAGENTS_DEBATE_ROUNDS", "1"))
    config["output_language"] = os.getenv("INVESTAGENTS_OUTPUT_LANGUAGE", "English")

    console.print(f"[bold]🚀 InvestAgents Quick Mode[/bold]")
    console.print(f"   Provider: {config['llm_provider']} | Deep: {config['deep_think_llm']} | Quick: {config['quick_think_llm']}")
    console.print(f"   Tickers: {', '.join(tickers)} | Language: {config['output_language']}")
    console.print()

    lta = InvestAgentsGraph(debug=False, config=config)

    for ticker in tickers:
        console.print(f"[bold cyan]🔬 Analyzing {ticker}...[/bold cyan]")
        state, thesis = lta.analyze_stock(ticker)
        console.print(Panel(thesis[:2000], title=f"📋 Thesis: {ticker}", border_style="green"))
        console.print()

    console.print("[green]✅ Done![/green]")


def _run_interactive_mode():
    """Full interactive TUI experience."""
    from invest_agents.graph.invest_graph import InvestAgentsGraph
    from invest_agents.default_config import DEFAULT_CONFIG

    show_welcome()

    # 1. Provider
    provider = select_provider()
    console.print(f"\n[green]✓ Provider: {provider}[/green]")

    # 2. Models
    deep_model, quick_model = select_models(provider)
    console.print(f"[green]✓ Deep: {deep_model} | Quick: {quick_model}[/green]")

    # 3. Tickers
    tickers = get_tickers()
    console.print(f"[green]✓ Tickers: {', '.join(tickers)}[/green]")

    # 4. Date
    date = select_date()
    console.print(f"[green]✓ Date: {date}[/green]")

    # 5. Debate rounds
    rounds = select_debate_rounds()
    console.print(f"[green]✓ Debate rounds: {rounds}[/green]")

    # 6. Language
    language = select_language()
    console.print(f"[green]✓ Language: {language}[/green]")

    # 7. Summary & confirm
    console.print()
    summary = Table(title="Configuration Summary", border_style="cyan")
    summary.add_column("Setting", style="dim")
    summary.add_column("Value")
    summary.add_row("Provider", provider)
    summary.add_row("Deep Model", deep_model)
    summary.add_row("Quick Model", quick_model)
    summary.add_row("Tickers", ", ".join(tickers))
    summary.add_row("Date", date)
    summary.add_row("Debate Rounds", str(rounds))
    summary.add_row("Language", language)
    summary.add_row("FRED Macro", "✅ Available" if detect_fred_key() else "⚠️ Not set")
    console.print(summary)

    if not Confirm.ask("\n[bold]Start analysis?[/bold]", default=True):
        console.print("[dim]Cancelled.[/dim]")
        return

    # 8. Build config & graph
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = provider
    config["deep_think_llm"] = deep_model
    config["quick_think_llm"] = quick_model
    config["max_debate_rounds"] = rounds
    config["output_language"] = language

    console.print("\n[bold cyan]Initializing InvestAgents...[/bold cyan]")
    lta = InvestAgentsGraph(debug=False, config=config)

    # 9. Run analysis with live progress
    all_theses = []
    for ticker in tickers:
        progress = AnalysisProgress(ticker)

        with Live(progress.render(), console=console, refresh_per_second=4, screen=False) as live:
            # Run analysis — we can't easily stream progress from the graph
            # without callbacks, so we update stages manually
            progress.update_stage("Running Moat Analyst...")
            progress.update_status("moat", "🔄 Running")
            live.update(progress.render())

            state, thesis = lta.analyze_stock(ticker)

            # Update all statuses (best-effort from final state)
            if state.get("moat_report"):
                progress.update_status("moat", "✅ Complete", state["moat_report"])
            if state.get("valuation_report"):
                progress.update_status("valuation", "✅ Complete", state["valuation_report"])
            if state.get("growth_report"):
                progress.update_status("growth", "✅ Complete", state["growth_report"])
            if state.get("macro_report"):
                progress.update_status("macro", "✅ Complete", state["macro_report"])
            progress.update_status("bull", "✅ Complete")
            progress.update_status("bear", "✅ Complete")
            progress.update_status("thesis", "✅ Complete", thesis)
            progress.update_stage("Complete!")
            live.update(progress.render())
            time.sleep(0.5)  # brief pause to show final state

        # Print final thesis
        console.print()
        console.print(Panel(
            thesis,
            title=f"📋 Investment Thesis: {ticker}",
            border_style="green",
            subtitle=f"Date: {date} | Provider: {provider}",
        ))
        console.print()

        all_theses.append({
            "ticker": ticker,
            "date": date,
            "thesis_markdown": thesis,
        })

    # 10. Portfolio construction (if multiple tickers)
    if len(all_theses) >= 2:
        if Confirm.ask("\n[bold]Build portfolio from these theses?[/bold]", default=True):
            console.print("\n[bold cyan]🏗️ Constructing portfolio...[/bold cyan]")
            portfolio = lta.build_portfolio(all_theses)
            console.print()
            console.print(Panel(
                portfolio[:3000],
                title="📊 Portfolio Construction",
                border_style="magenta",
            ))

    # 11. Done
    console.print(f"\n[green]✅ Analysis complete! Results saved to {config['results_dir']}[/green]")


if __name__ == "__main__":
    main()
