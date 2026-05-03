# 🐶📈 InvestAgents

> **Multi-agent LLM framework for long-term stock investing — thesis-driven, debate-powered, portfolio-aware.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

Born from the architecture of [TradingAgents](https://github.com/TauricResearch/TradingAgents) but bred for the long game: **3-10 year holding periods**, moat analysis, DCF valuation, thesis tracking, and portfolio construction.

---

## 🤔 Why InvestAgents?

TradingAgents is brilliant for short-term tactical trading — but **long-term investing is a different sport**. You need:

- 📋 **Thesis tracking**: *Why* did I buy this? What needs to happen? When do I sell?
- 🏰 **Moat analysis**: Is the competitive advantage *durable* over 5-10 years?
- 💰 **Valuation patience**: Not "is it cheap today?" but "is the price fair for a multi-year hold?"
- 📊 **Portfolio thinking**: How do positions fit together? Sector balance? Macro overlay?
- 🧠 **Memory over years**: Did my thesis play out? What did I learn?

InvestAgents addresses **all of these** with a team of 8 specialized LLM agents that research, debate, and synthesize a complete investment thesis for every stock you analyze.

---

## 🏗️ Architecture — The 8-Agent Pipeline

```
                         📊 InvestAgents
                               │
            ┌──────────────────┼──────────────────┐
            │                  │                  │
      STOCK DEEP-DIVE    PORTFOLIO CONST.    THESIS MEMORY
            │                  │                  │
      ┌─────┴─────┐      Aggregate theses    Track outcomes
      │           │      + macro overlay     over quarters/years
     Moat    Valuation   + diversification   Learn from mistakes
      │           │           │
     Growth    Macro     Position sizing
      │           │      + weights
      └─────┬─────┘           │
            ↓                 ↓
      Bull ←→ Bear       Portfolio Plan
       (debate)          (rebalancing,
            ↓              entry/exit)
      Thesis Manager
      (conviction,
       catalysts,
       exit criteria)
```

### The Agent Team

| Agent | Role | What It Uses |
|-------|------|-------------|
| 🏰 **Moat Analyst** | Competitive advantage, ROIC trends, management quality | Financials, key metrics, 10-K filings |
| 💰 **Valuation Analyst** | Intrinsic value, margin of safety, historical multiples | Price history, financials, metrics |
| 📈 **Growth Analyst** | Revenue/earnings trends, TAM, reinvestment runway | Financials, 10-K, news |
| 🌐 **Macro Analyst** | Industry lifecycle, macro sensitivity, regulatory risk | FRED macro data, 10-K, news |
| 🐂 **Bull Researcher** | Builds and defends the bullish investment case | Reads all analyst reports |
| 🐻 **Bear Researcher** | Stress-tests assumptions, identifies blind spots | Reads all analyst reports |
| 📋 **Thesis Manager** | Final thesis: conviction, catalysts, exit criteria | Reads debate + all reports |
| 📊 **Portfolio Constructor** | Multi-stock allocation, sector balance, rebalancing | Reads all theses + macro |

### Data Sources (multi-vendor with fallback)

| Category | Primary | Fallback |
|----------|---------|----------|
| Price History | yfinance (free) | Alpha Vantage |
| Financial Statements | yfinance (free) | Alpha Vantage, FMP |
| Key Metrics | yfinance (free) | FMP |
| SEC Filings (10-K/10-Q) | SEC EDGAR (free, **no key needed**) | — |
| Macro Data | FRED (free, needs key) | — |
| News | yfinance (free) | NewsAPI |
| Insider Transactions | yfinance (free) | Alpha Vantage |
| Earnings Transcripts | FMP (needs key) | — |

### LLM Providers

OpenAI, Anthropic (Claude), Google (Gemini), DeepSeek — extensible to all providers supported by TradingAgents (xAI Grok, Qwen, GLM, Ollama, Azure, OpenRouter, and more).

---

## 🚀 Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/vp125/InvestAgents.git
cd InvestAgents
pip install .
```

### 2. Set API Keys

```bash
# Required: at least one LLM provider
export DEEPSEEK_API_KEY="sk-..."        # DeepSeek
# or: OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY

# Optional: for macro data (free from https://fred.stlouisfed.org)
export FRED_API_KEY="..."
```

> 💡 **Tip:** Copy the included `config.sh` template for a quick start:
> ```bash
> cp config.sh my_config.sh
> # Edit my_config.sh with your keys, then:
> source my_config.sh
> ```

### 3. Run Your First Analysis

**Simple mode** — one command, straight to results:

```bash
# Single stock deep-dive
python main.py COST

# Multi-stock + automatic portfolio construction
python main.py COST GOOGL BRK.B V JPM
```

**Interactive CLI** — guided menus, live progress dashboard:

```bash
# Full interactive TUI
python cli/main.py

# Quick mode (skip menus, use env vars)
python cli/main.py COST GOOGL BRK.B
```

The interactive CLI walks you through:
1. Choose LLM provider (auto-detects your keys)
2. Pick models (deep vs quick thinking)
3. Enter ticker symbols
4. Set analysis date
5. Choose debate depth (0 = fast, 1 = standard, 2 = deep)
6. Select output language
7. Watch the live progress dashboard as all 8 agents do their work

---

## 🐍 Python API

```python
from invest_agents.graph.invest_graph import InvestAgentsGraph
from invest_agents.default_config import DEFAULT_CONFIG

# Configure
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "openai"
config["deep_think_llm"] = "gpt-4o"           # for thesis & portfolio
config["quick_think_llm"] = "gpt-4o-mini"     # for analyst reports
config["max_debate_rounds"] = 2
config["output_language"] = "English"

lta = InvestAgentsGraph(config=config)

# Deep-dive one stock
state, thesis = lta.analyze_stock("COST")
print(thesis)

# Build portfolio from multiple theses
theses = [
    {"ticker": "COST", "thesis_markdown": thesis, "conviction": "High"}
]
portfolio = lta.build_portfolio(theses)
print(portfolio)

# Full cycle: analyze multiple → portfolio
theses, portfolio = lta.run_full_cycle(["COST", "GOOGL", "BRK.B"])
```

---

## ⚙️ Configuration Reference

Set via environment variables or `config.sh`:

| Variable | Default | Description |
|----------|---------|-------------|
| `INVESTAGENTS_LLM_PROVIDER` | `deepseek` | LLM provider: `openai`, `anthropic`, `google`, `deepseek` |
| `INVESTAGENTS_DEEP_MODEL` | `deepseek-chat` | Model for thesis synthesis & portfolio construction |
| `INVESTAGENTS_QUICK_MODEL` | `deepseek-chat` | Model for analyst reports & debate |
| `INVESTAGENTS_DEBATE_ROUNDS` | `1` | Bull/Bear debate rounds: `0` (off), `1` (standard), `2` (deep) |
| `INVESTAGENTS_OUTPUT_LANGUAGE` | `English` | Output language for all reports and theses |
| `INVESTAGENTS_RESULTS_DIR` | `~/.invest_agents/results` | Where results are saved |
| `INVESTAGENTS_CACHE_DIR` | `~/.invest_agents/cache` | Data cache location |

---

## 📊 InvestAgents vs TradingAgents

| | TradingAgents | InvestAgents |
|---|---|---|
| **Horizon** | Days to weeks | Years to decades |
| **Output** | Trade signal (Buy/Hold/Sell) | Investment thesis + catalysts + exit criteria |
| **Analysts** | Market, Social, News, Fundamentals | Moat, Valuation, Growth, Macro |
| **Debate** | Bull/Bear on trade + Risk debate | Bull/Bear on thesis quality |
| **Memory** | 5-day returns vs SPY | Quarterly/annual thesis reviews |
| **Portfolio** | Single-stock risk debate | Multi-stock portfolio construction |
| **Data** | Recent price + technicals | 5-10 year financials + SEC filings + macro |
| **Data Sources** | 2 vendors | 5 vendors with fallback chains |

---

## 🗺️ Roadmap

- [x] Multi-source data layer with fallback chains
- [x] 4 deep-dive analysts (Moat, Valuation, Growth, Macro)
- [x] Bull/Bear thesis debate
- [x] Thesis Manager with structured output
- [x] Portfolio Constructor (multi-stock allocation)
- [x] SEC EDGAR + FRED integration
- [x] Interactive CLI with live progress dashboard
- [ ] Thesis memory log (track outcomes over quarters/years)
- [ ] Thesis review scheduler (periodic re-evaluation)
- [ ] Backtesting framework (full market cycles)
- [ ] DCF computation engine (structured, not LLM-hallucinated)
- [ ] Factor exposure analysis
- [ ] Tax-loss harvesting optimization

---

## 📄 License

MIT — same as TradingAgents. Build on it, learn from it, make it better.

---

> *"In the short run, the market is a voting machine. In the long run, it's a weighing machine."* — Benjamin Graham

**InvestAgents is built for the weighing machine.** 🐶📈
