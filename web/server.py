#!/usr/bin/env python3
"""InvestAgents Web Dashboard — zero-dependency report viewer.

Usage:
    python3 web/server.py              # default: http://localhost:8080
    python3 web/server.py --port 9090  # custom port

Serves:
    /              Interactive dashboard (HTML)
    /api/theses    JSON list of all analyses
    /api/thesis/{ticker}/{date}  Single thesis detail

Reads from ~/.invest_agents/results/ (configurable via INVESTAGENTS_RESULTS_DIR).
"""

from __future__ import annotations

import json
import os
import sys
import re
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_DIR = Path(
    os.getenv(
        "INVESTAGENTS_RESULTS_DIR",
        os.path.join(os.path.expanduser("~"), ".invest_agents", "results"),
    )
)

# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------


def list_all_theses() -> list[dict]:
    """Scan results directory and return all thesis metadata, sorted newest first."""
    entries = []
    if not RESULTS_DIR.exists():
        return entries

    for ticker_dir in sorted(RESULTS_DIR.iterdir()):
        if not ticker_dir.is_dir():
            continue
        ticker = ticker_dir.name
        logs_dir = ticker_dir / "thesis_logs"
        if not logs_dir.exists():
            continue

        for thesis_file in sorted(logs_dir.glob("thesis_*.json"), reverse=True):
            # Parse date from filename: thesis_2026-05-03.json
            match = re.match(r"thesis_(\d{4}-\d{2}-\d{2})\.json$", thesis_file.name)
            date_str = match.group(1) if match else "unknown"

            # Peek at the file to get summary stats
            try:
                data = json.loads(thesis_file.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue

            entries.append({
                "ticker": ticker,
                "date": date_str,
                "file": str(thesis_file.relative_to(RESULTS_DIR)),
                "has_moat": bool(data.get("moat_report")),
                "has_valuation": bool(data.get("valuation_report")),
                "has_growth": bool(data.get("growth_report")),
                "has_macro": bool(data.get("macro_report")),
                "has_debate": bool(data.get("debate_history")),
                "has_thesis": bool(data.get("investment_thesis")),
                # First 200 chars as preview
                "preview": (data.get("investment_thesis", "") or data.get("moat_report", ""))[:200],
            })

    return entries


def load_thesis(ticker: str, date: str) -> dict | None:
    """Load a specific thesis JSON file."""
    file_path = RESULTS_DIR / ticker / "thesis_logs" / f"thesis_{date}.json"
    if not file_path.exists():
        return None
    try:
        return json.loads(file_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


# ---------------------------------------------------------------------------
# HTML template (inline — no external template engine needed)
# ---------------------------------------------------------------------------

HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>InvestAgents — Dashboard</title>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<style>
  :root {
    --bg: #0d1117; --card: #161b22; --border: #30363d;
    --text: #c9d1d9; --dim: #8b949e; --accent: #58a6ff;
    --green: #3fb950; --red: #f85149; --yellow: #d2991d;
    --purple: #a371f7;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; min-height:100vh; }
  .app { display:flex; min-height:100vh; }
  /* Sidebar */
  .sidebar { width:320px; min-width:320px; background:var(--card); border-right:1px solid var(--border); display:flex; flex-direction:column; overflow:hidden; }
  .sidebar-header { padding:20px; border-bottom:1px solid var(--border); }
  .sidebar-header h1 { font-size:20px; margin-bottom:4px; }
  .sidebar-header .sub { color:var(--dim); font-size:13px; }
  .thesis-list { flex:1; overflow-y:auto; padding:8px; }
  .thesis-item { padding:12px; border-radius:8px; cursor:pointer; margin-bottom:4px; transition:background .15s; border:1px solid transparent; }
  .thesis-item:hover { background:rgba(88,166,255,.06); }
  .thesis-item.active { background:rgba(88,166,255,.12); border-color:var(--accent); }
  .thesis-item .ticker { font-weight:600; font-size:15px; }
  .thesis-item .date { font-size:12px; color:var(--dim); margin-left:8px; }
  .thesis-item .preview { font-size:12px; color:var(--dim); margin-top:4px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
  .badges { display:flex; gap:4px; margin-top:6px; flex-wrap:wrap; }
  .badge { font-size:10px; padding:2px 6px; border-radius:4px; background:var(--border); color:var(--dim); }
  .badge.ok { background:rgba(63,185,80,.15); color:var(--green); }
  /* Main */
  .main { flex:1; display:flex; flex-direction:column; overflow:hidden; }
  .main-header { padding:20px 24px; border-bottom:1px solid var(--border); display:flex; align-items:center; gap:12px; }
  .main-header .ticker-big { font-size:24px; font-weight:700; }
  .main-header .date-big { color:var(--dim); font-size:14px; }
  .report-tabs { display:flex; gap:0; border-bottom:1px solid var(--border); padding:0 24px; }
  .tab { padding:10px 18px; cursor:pointer; font-size:13px; color:var(--dim); border-bottom:2px solid transparent; transition:all .15s; background:none; border-top:none; border-left:none; border-right:none; }
  .tab:hover { color:var(--text); }
  .tab.active { color:var(--accent); border-bottom-color:var(--accent); }
  .report-content { flex:1; overflow-y:auto; padding:24px; }
  .report-content .markdown { max-width:900px; line-height:1.7; }
  .report-content .markdown h1 { font-size:22px; margin:24px 0 12px; color:var(--accent); }
  .report-content .markdown h2 { font-size:18px; margin:20px 0 10px; border-bottom:1px solid var(--border); padding-bottom:6px; }
  .report-content .markdown h3 { font-size:15px; margin:16px 0 8px; }
  .report-content .markdown p { margin:8px 0; }
  .report-content .markdown ul, .markdown ol { margin:8px 0; padding-left:24px; }
  .report-content .markdown li { margin:4px 0; }
  .report-content .markdown table { border-collapse:collapse; width:100%; margin:12px 0; }
  .report-content .markdown th, .markdown td { border:1px solid var(--border); padding:8px 12px; text-align:left; font-size:13px; }
  .report-content .markdown th { background:var(--card); }
  .report-content .markdown code { background:var(--card); padding:2px 6px; border-radius:4px; font-size:12px; }
  .report-content .markdown pre { background:var(--card); padding:12px; border-radius:8px; overflow-x:auto; }
  .report-content .markdown blockquote { border-left:3px solid var(--accent); padding-left:12px; color:var(--dim); margin:12px 0; }
  .empty-state { display:flex; flex-direction:column; align-items:center; justify-content:center; height:100%; color:var(--dim); gap:12px; }
  .empty-state .icon { font-size:64px; }
  .refresh-btn { padding:6px 12px; border:1px solid var(--border); border-radius:6px; background:var(--card); color:var(--text); cursor:pointer; font-size:12px; }
  .refresh-btn:hover { border-color:var(--accent); }
  .stats-row { display:flex; gap:16px; padding:8px 20px; font-size:12px; color:var(--dim); }
  @media (max-width:768px) { .app { flex-direction:column; } .sidebar { width:100%; min-width:100%; max-height:40vh; } }
</style>
</head>
<body>
<div class="app">
  <!-- Sidebar -->
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1>🐶 InvestAgents</h1>
      <div class="sub">Long-term thesis dashboard</div>
    </div>
    <div class="stats-row">
      <span id="stat-count">—</span>
      <button class="refresh-btn" onclick="loadThesisList()">🔄 Refresh</button>
    </div>
    <div class="thesis-list" id="thesis-list">
      <div class="empty-state"><div class="icon">📭</div><div>No analyses yet.<br>Run the CLI to generate some!</div></div>
    </div>
  </aside>

  <!-- Main -->
  <main class="main" id="main-panel">
    <div class="empty-state">
      <div class="icon">🐶</div>
      <div>Select an analysis from the sidebar</div>
      <div style="font-size:13px">or run <code>python3 cli/main.py TICKER</code></div>
    </div>
  </main>
</div>

<script>
  marked.setOptions({breaks:true, gfm:true});

  let currentThesis = null;
  let currentTab = 'thesis';

  const TAB_LABELS = {
    thesis: '📋 Investment Thesis',
    moat: '🏰 Moat & Quality',
    valuation: '💰 Valuation',
    growth: '📈 Growth',
    macro: '🌍 Macro',
    debate: '⚔️ Bull/Bear Debate'
  };

  async function loadThesisList() {
    const resp = await fetch('/api/theses');
    const theses = await resp.json();
    document.getElementById('stat-count').textContent = `${theses.length} analysis${theses.length!==1?'e':''}s`;

    const container = document.getElementById('thesis-list');
    if (!theses.length) {
      container.innerHTML = '<div class="empty-state"><div class="icon">📭</div><div>No analyses yet.<br>Run the CLI to generate some!</div></div>';
      return;
    }

    container.innerHTML = theses.map((t, i) => {
      const isActive = currentThesis && currentThesis.ticker === t.ticker && currentThesis.date === t.date;
      const badges = [];
      if (t.has_thesis) badges.push('<span class="badge ok">thesis</span>');
      if (t.has_moat) badges.push('<span class="badge ok">moat</span>');
      if (t.has_valuation) badges.push('<span class="badge ok">val</span>');
      if (t.has_growth) badges.push('<span class="badge ok">growth</span>');
      if (t.has_macro) badges.push('<span class="badge ok">macro</span>');
      if (t.has_debate) badges.push('<span class="badge ok">debate</span>');
      return `
        <div class="thesis-item${isActive?' active':''}" onclick="selectThesis('${t.ticker}','${t.date}')" data-ticker="${t.ticker}" data-date="${t.date}">
          <span class="ticker">${t.ticker}</span><span class="date">${t.date}</span>
          <div class="preview">${escHtml(t.preview)}</div>
          <div class="badges">${badges.join('')}</div>
        </div>`;
    }).join('');
  }

  async function selectThesis(ticker, date) {
    const resp = await fetch(`/api/thesis/${ticker}/${date}`);
    if (!resp.ok) return;
    currentThesis = await resp.json();
    currentTab = currentThesis.investment_thesis ? 'thesis'
               : currentThesis.moat_report ? 'moat'
               : currentThesis.valuation_report ? 'valuation'
               : 'growth';
    renderMain();
    loadThesisList(); // refresh active state
  }

  function renderMain() {
    if (!currentThesis) return;
    const t = currentThesis;
    const main = document.getElementById('main-panel');

    // Build tab list — only show tabs that have content
    const tabs = [];
    for (const [key, label] of Object.entries(TAB_LABELS)) {
      const content = key === 'thesis' ? t.investment_thesis
                    : key === 'moat' ? t.moat_report
                    : key === 'valuation' ? t.valuation_report
                    : key === 'growth' ? t.growth_report
                    : key === 'macro' ? t.macro_report
                    : key === 'debate' ? t.debate_history
                    : '';
      if (content) tabs.push({key, label, content});
    }

    if (!tabs.length) {
      main.innerHTML = '<div class="empty-state"><div>No report data found.</div></div>';
      return;
    }

    // Ensure current tab is valid
    if (!tabs.find(tb => tb.key === currentTab)) currentTab = tabs[0].key;

    const activeContent = tabs.find(tb => tb.key === currentTab)?.content || '';

    main.innerHTML = `
      <div class="main-header">
        <span class="ticker-big">${t.ticker}</span>
        <span class="date-big">${t.date}</span>
      </div>
      <div class="report-tabs">
        ${tabs.map(tb => `
          <button class="tab${tb.key===currentTab?' active':''}" onclick="switchTab('${tb.key}')">${tb.label}</button>
        `).join('')}
      </div>
      <div class="report-content">
        <div class="markdown" id="report-body">${marked.parse(activeContent)}</div>
      </div>`;
  }

  function switchTab(key) {
    currentTab = key;
    renderMain();
  }

  function escHtml(s) {
    return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  // Init
  loadThesisList();
</script>
</body>
</html>"""

# ---------------------------------------------------------------------------
# HTTP Request Handler
# ---------------------------------------------------------------------------


class DashboardHandler(BaseHTTPRequestHandler):
    """Serves the dashboard HTML and JSON API endpoints."""

    def log_message(self, format, *args):
        """Quiet logging."""
        pass

    def _send_html(self, html: str, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))

    def _send_json(self, data, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _send_error(self, status: int, message: str):
        self._send_json({"error": message}, status)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path).rstrip("/") or "/"

        # ---- API: list all theses ----
        if path == "/api/theses":
            theses = list_all_theses()
            self._send_json(theses)
            return

        # ---- API: single thesis detail ----
        match = re.match(r"^/api/thesis/([^/]+)/([\d\-]+)$", path)
        if match:
            ticker = match.group(1)
            date = match.group(2)
            thesis = load_thesis(ticker, date)
            if thesis is None:
                self._send_error(404, f"No thesis found for {ticker} on {date}")
                return
            # Add ticker/date to payload for frontend convenience
            thesis["ticker"] = ticker
            thesis["date"] = date
            self._send_json(thesis)
            return

        # ---- Dashboard page ----
        if path == "/" or path == "/index.html":
            # Inject a timestamp for cache busting
            html = HTML_TEMPLATE.replace(
                "</body>",
                f"<!-- rendered: {datetime.now().isoformat()} --></body>",
            )
            self._send_html(html)
            return

        # ---- 404 ----
        self._send_error(404, f"Not found: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    import argparse

    parser = argparse.ArgumentParser(description="InvestAgents Web Dashboard")
    parser.add_argument("--port", type=int, default=8080, help="Port to listen on (default: 8080)")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), DashboardHandler)

    print(f"🐶 InvestAgents Dashboard")
    print(f"   http://localhost:{args.port}")
    print(f"   Results dir: {RESULTS_DIR}")
    print(f"   Press Ctrl+C to stop.")
    print()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Shutting down.")
        server.shutdown()


if __name__ == "__main__":
    main()
