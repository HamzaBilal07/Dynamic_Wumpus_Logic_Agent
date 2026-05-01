from __future__ import annotations

import base64
import json
import zlib
from html import escape
from urllib.parse import parse_qs

from wumpus_logic import LogicAgent, coord


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


def encode_agent(agent: LogicAgent) -> str:
    payload = json.dumps(agent.to_state(), separators=(",", ":")).encode("utf-8")
    compressed = zlib.compress(payload, level=9)
    return base64.urlsafe_b64encode(compressed).decode("ascii")


def decode_agent(value: str) -> LogicAgent:
    if not value:
        return LogicAgent()

    try:
        compressed = base64.urlsafe_b64decode(value.encode("ascii"))
        payload = zlib.decompress(compressed)
        data = json.loads(payload.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Agent payload is not an object")
        return LogicAgent.from_state(data)
    except Exception:
        return LogicAgent()


def render_badge(text: str, class_name: str) -> str:
    return f'<span class="badge {class_name}">{escape(text)}</span>'


def hidden_state(agent: LogicAgent) -> str:
    return f'<input type="hidden" name="state" value="{escape(encode_agent(agent), quote=True)}">'


def render_cell(agent: LogicAgent, cell: tuple[int, int]) -> str:
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


def render_grid(agent: LogicAgent) -> str:
    cells = []
    for row in range(agent.rows):
        for col in range(agent.cols):
            cells.append(render_cell(agent, (row, col)))

    return f"""
      <form method="post" action="/action" id="grid" class="grid" style="grid-template-columns: repeat({agent.cols}, minmax(0, 1fr)); grid-template-rows: repeat({agent.rows}, minmax(0, 1fr));">
        {hidden_state(agent)}
        {''.join(cells)}
      </form>
    """


def render_move_summary(agent: LogicAgent) -> str:
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


def render_percepts(agent: LogicAgent) -> str:
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


def render_page(agent: LogicAgent) -> bytes:
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
          <p>Python serverless knowledge-based pathfinding with propositional logic, CNF conversion, and resolution refutation.</p>
        </div>

        <form class="controls" method="post" action="/action">
          {hidden_state(agent)}
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
          {render_move_summary(agent)}
          {render_grid(agent)}
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
            <div class="percept-line">{render_percepts(agent)}</div>
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


def agent_from_form(form: dict[str, list[str]]) -> LogicAgent:
    action = form.get("action", [""])[0]
    if action == "new":
        rows = clamp_int(form.get("rows", ["4"])[0], 2, 8, 4)
        cols = clamp_int(form.get("cols", ["4"])[0], 2, 8, 4)
        density = clamp_float(form.get("density", ["18"])[0], 0, 35, 18) / 100
        return LogicAgent(rows, cols, density)

    agent = decode_agent(form.get("state", [""])[0])
    if action == "step":
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

    return agent


def render_get() -> bytes:
    return render_page(LogicAgent())


def render_post(raw_body: bytes) -> bytes:
    form = parse_qs(raw_body.decode("utf-8"))
    return render_page(agent_from_form(form))
