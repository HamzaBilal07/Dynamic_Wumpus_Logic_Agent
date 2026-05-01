from __future__ import annotations

from html import escape
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import socket
import sys
from urllib.parse import parse_qs

from wumpus_logic import LogicAgent, coord


ROOT = Path(__file__).resolve().parent
CSS_PATH = ROOT / "styles.css"
agent = LogicAgent()


def safe_print(message: str) -> None:
    if sys.stdout is not None:
        print(message, flush=True)


def clamp_int(value: str, minimum: int, maximum: int, fallback: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, parsed))


def clamp_float(value: str, minimum: float, maximum: float, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    return max(minimum, min(maximum, parsed))


def render_badge(text: str, class_name: str) -> str:
    return f'<span class="badge {class_name}">{escape(text)}</span>'


def render_cell(cell: tuple[int, int]) -> str:
    classes = ["cell"]
    marker = ""

    if cell in agent.confirmed_pits or cell in agent.confirmed_wumpus:
        classes.append("danger")
    elif cell in agent.visited:
        classes.append("visited")
    elif cell in agent.safe:
        classes.append("safe")

    if cell == agent.last_from:
        classes.append("last-from")
    if cell == agent.last_to:
        classes.append("last-to")

    if cell == agent.agent:
        classes.append("agent")
        marker = "A"
    elif cell in agent.confirmed_wumpus:
        marker = "W"
    elif cell in agent.confirmed_pits:
        marker = "P"
    elif cell in agent.safe and cell not in agent.visited:
        marker = "OK"
    elif cell in agent.visited:
        marker = "V"

    percept_html = ""
    if cell in agent.visited:
        percepts = agent.world.percepts(cell)
        if percepts["breeze"]:
            percept_html += render_badge("B", "breeze")
        if percepts["stench"]:
            percept_html += render_badge("S", "stench")

    row, col = cell
    return f"""
      <button class="{escape(' '.join(classes))}" name="action" value="move:{row}:{col}" aria-label="Cell {coord(cell)}">
        <span class="coord">{coord(cell)}</span>
        <span class="marker">{escape(marker)}</span>
        <span class="percept-badges">{percept_html}</span>
      </button>
    """


def render_grid() -> str:
    cells = []
    for row in range(agent.rows):
        for col in range(agent.cols):
            cells.append(render_cell((row, col)))

    return f"""
      <form method="post" action="/action" id="grid" class="grid" style="grid-template-columns: repeat({agent.cols}, minmax(0, 1fr)); grid-template-rows: repeat({agent.rows}, minmax(0, 1fr));">
        {''.join(cells)}
      </form>
    """


def render_move_summary() -> str:
    last_move = "No movement yet."
    if agent.last_from is not None and agent.last_to is not None:
        last_move = f"{coord(agent.last_from)} -> {coord(agent.last_to)}"

    return f"""
      <div class="move-summary" aria-label="Agent movement">
        <div>
          <span>Agent position</span>
          <strong>{coord(agent.agent)}</strong>
        </div>
        <div>
          <span>Moves made</span>
          <strong>{agent.move_count}</strong>
        </div>
        <div>
          <span>Last move</span>
          <strong>{escape(last_move)}</strong>
        </div>
      </div>
    """


def render_percepts() -> str:
    if not agent.active_percepts["breeze"] and not agent.active_percepts["stench"]:
        return "None"

    parts = []
    if agent.active_percepts["breeze"]:
        parts.append(render_badge("Breeze", "breeze"))
    if agent.active_percepts["stench"]:
        parts.append(render_badge("Stench", "stench"))
    return "".join(parts)


def render_list(items: list[str], empty_text: str) -> str:
    if not items:
        return f"<li>{escape(empty_text)}</li>"
    return "".join(f"<li>{escape(item)}</li>" for item in items)


def render_page() -> bytes:
    kb_items = [
        f"{entry.label}: {entry.text}  [CNF +{entry.clauses_added}]"
        for entry in agent.kb.tell_log[:8]
    ]
    trace_items = list(agent.metrics["last_trace"])
    density_percent = round(agent.pit_rate * 100)

    html = f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Dynamic Wumpus Logic Agent</title>
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <main class="app-shell">
      <section class="control-band" aria-label="Episode controls">
        <div>
          <h1>Dynamic Wumpus Logic Agent</h1>
          <p>Python knowledge-based pathfinding with propositional logic, CNF conversion, and resolution refutation.</p>
        </div>

        <form class="controls" method="post" action="/action">
          <label>
            Rows
            <input name="rows" type="number" min="2" max="8" value="{agent.rows}">
          </label>
          <label>
            Columns
            <input name="cols" type="number" min="2" max="8" value="{agent.cols}">
          </label>
          <label class="range-label">
            Pit density
            <span>{density_percent}%</span>
            <input name="density" type="range" min="0" max="35" value="{density_percent}">
          </label>
          <button name="action" value="new" type="submit">New episode</button>
          <button name="action" value="step" type="submit">Step agent</button>
          <button name="action" value="auto" type="submit">Auto run</button>
        </form>
      </section>

      <section class="workspace">
        <section class="board-panel" aria-label="Wumpus grid">
          <div class="legend" aria-label="Cell colors">
            <span><i class="legend-chip safe"></i> Safe</span>
            <span><i class="legend-chip unknown"></i> Unknown</span>
            <span><i class="legend-chip danger"></i> Confirmed hazard</span>
            <span><i class="legend-chip visited"></i> Visited</span>
          </div>
          {render_move_summary()}
          {render_grid()}
        </section>

        <aside class="dashboard" aria-label="Metrics dashboard">
          <section>
            <h2>Metrics</h2>
            <div class="metric-grid">
              <div>
                <span>Total inference steps</span>
                <strong>{int(agent.metrics["total_steps"]):,}</strong>
              </div>
              <div>
                <span>Last resolution</span>
                <strong>{int(agent.metrics["last_steps"]):,}</strong>
              </div>
              <div>
                <span>CNF clauses in KB</span>
                <strong>{len(agent.kb.clauses):,}</strong>
              </div>
              <div>
                <span>Visited cells</span>
                <strong>{len(agent.visited)}/{agent.rows * agent.cols}</strong>
              </div>
            </div>
          </section>

          <section>
            <h2>Current Percepts</h2>
            <div class="percept-line">{render_percepts()}</div>
          </section>

          <section>
            <h2>Agent Status</h2>
            <p class="status-line">{escape(agent.status)}</p>
          </section>

          <section>
            <h2>Last ASK</h2>
            <p class="mono muted">{escape(str(agent.metrics["last_ask"]))}</p>
          </section>

          <section>
            <h2>Recent TELL Statements</h2>
            <ol class="kb-log">{render_list(kb_items, "No TELL statements yet.")}</ol>
          </section>

          <section>
            <h2>Resolution Trace</h2>
            <ol class="trace-log">{render_list(trace_items, "No resolvents generated for the last query.")}</ol>
          </section>
        </aside>
      </section>
    </main>
  </body>
</html>
"""
    return html.encode("utf-8")


class WumpusHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path == "/" or self.path.startswith("/?"):
            self.send_html(render_page())
            return
        if self.path == "/styles.css":
            self.send_response(200)
            self.send_header("Content-Type", "text/css; charset=utf-8")
            self.end_headers()
            self.wfile.write(CSS_PATH.read_bytes())
            return
        self.send_error(404)

    def do_POST(self) -> None:
        if self.path != "/action":
            self.send_error(404)
            return

        global agent
        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(raw_body)
        action = form.get("action", [""])[0]

        if action == "new":
            rows = clamp_int(form.get("rows", [str(agent.rows)])[0], 2, 8, agent.rows)
            cols = clamp_int(form.get("cols", [str(agent.cols)])[0], 2, 8, agent.cols)
            density = clamp_float(form.get("density", [str(round(agent.pit_rate * 100))])[0], 0, 35, 18) / 100
            agent = LogicAgent(rows, cols, density)
        elif action == "step":
            agent.step()
        elif action == "auto":
            moves = 0
            max_moves = agent.rows * agent.cols * 2
            while moves < max_moves and not agent.over:
                if not agent.step():
                    break
                moves += 1
            if moves:
                agent.status = f"Auto run completed {moves} safe move{'s' if moves != 1 else ''}. {agent.status}"
        elif action.startswith("move:"):
            _, row, col = action.split(":")
            agent.move_to((int(row), int(col)))

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

    def send_html(self, payload: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        safe_print(f"{self.address_string()} - {format % args}")


def pick_port(preferred_port: int) -> int:
    for port in range(preferred_port, preferred_port + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free local port found")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Python Wumpus Logic Agent web app.")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    port = pick_port(args.port)
    server = ThreadingHTTPServer(("127.0.0.1", port), WumpusHandler)
    safe_print(f"Dynamic Wumpus Logic Agent running at http://127.0.0.1:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
