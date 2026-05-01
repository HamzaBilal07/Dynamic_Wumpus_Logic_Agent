from __future__ import annotations

from dataclasses import dataclass
import random
from typing import Iterable


Cell = tuple[int, int]
Clause = tuple[str, ...]


@dataclass(frozen=True)
class Formula:
    kind: str
    name: str | None = None
    value: "Formula | None" = None
    values: tuple["Formula", ...] = ()
    left: "Formula | None" = None
    right: "Formula | None" = None


def sym(name: str) -> Formula:
    return Formula("sym", name=name)


def neg(value: Formula) -> Formula:
    return Formula("not", value=value)


def connective(kind: str, values: Iterable[Formula]) -> Formula:
    flattened: list[Formula] = []
    for value in values:
        if value.kind == kind:
            flattened.extend(value.values)
        else:
            flattened.append(value)

    if not flattened:
        raise ValueError(f"{kind.upper()} requires at least one operand")
    if len(flattened) == 1:
        return flattened[0]
    return Formula(kind, values=tuple(flattened))


def conj(*values: Formula) -> Formula:
    return connective("and", values)


def disj(*values: Formula) -> Formula:
    return connective("or", values)


def imp(left: Formula, right: Formula) -> Formula:
    return Formula("imp", left=left, right=right)


def iff(left: Formula, right: Formula) -> Formula:
    return Formula("iff", left=left, right=right)


def pit_symbol(cell: Cell) -> str:
    row, col = cell
    return f"P_{row + 1}_{col + 1}"


def wumpus_symbol(cell: Cell) -> str:
    row, col = cell
    return f"W_{row + 1}_{col + 1}"


def breeze_symbol(cell: Cell) -> str:
    row, col = cell
    return f"B_{row + 1}_{col + 1}"


def stench_symbol(cell: Cell) -> str:
    row, col = cell
    return f"S_{row + 1}_{col + 1}"


def coord(cell: Cell) -> str:
    row, col = cell
    return f"({row + 1},{col + 1})"


def display_symbol(name: str) -> str:
    kind, row, col = name.split("_")
    return f"{kind}({row},{col})"


def formula_to_text(formula: Formula) -> str:
    if formula.kind == "sym":
        return display_symbol(formula.name or "")
    if formula.kind == "not":
        return f"~{formula_to_text(required(formula.value))}"
    if formula.kind == "and":
        return "(" + " & ".join(formula_to_text(value) for value in formula.values) + ")"
    if formula.kind == "or":
        return "(" + " v ".join(formula_to_text(value) for value in formula.values) + ")"
    if formula.kind == "imp":
        return f"({formula_to_text(required(formula.left))} => {formula_to_text(required(formula.right))})"
    if formula.kind == "iff":
        return f"({formula_to_text(required(formula.left))} <=> {formula_to_text(required(formula.right))})"
    return "?"


def required(value: Formula | None) -> Formula:
    if value is None:
        raise ValueError("Malformed formula")
    return value


def eliminate_implications(formula: Formula) -> Formula:
    if formula.kind == "sym":
        return formula
    if formula.kind == "not":
        return neg(eliminate_implications(required(formula.value)))
    if formula.kind in {"and", "or"}:
        return connective(
            formula.kind,
            (eliminate_implications(value) for value in formula.values),
        )
    if formula.kind == "imp":
        left = eliminate_implications(required(formula.left))
        right = eliminate_implications(required(formula.right))
        return disj(neg(left), right)
    if formula.kind == "iff":
        left = eliminate_implications(required(formula.left))
        right = eliminate_implications(required(formula.right))
        return conj(disj(neg(left), right), disj(neg(right), left))
    raise ValueError(f"Unknown formula kind: {formula.kind}")


def move_not_inward(formula: Formula) -> Formula:
    if formula.kind == "sym":
        return formula
    if formula.kind in {"and", "or"}:
        return connective(
            formula.kind,
            (move_not_inward(value) for value in formula.values),
        )
    if formula.kind != "not":
        return move_not_inward(eliminate_implications(formula))

    value = required(formula.value)
    if value.kind == "sym":
        return formula
    if value.kind == "not":
        return move_not_inward(required(value.value))
    if value.kind == "and":
        return disj(*(move_not_inward(neg(child)) for child in value.values))
    if value.kind == "or":
        return conj(*(move_not_inward(neg(child)) for child in value.values))
    return move_not_inward(neg(eliminate_implications(value)))


def distribute_ors(formula: Formula) -> Formula:
    if formula.kind in {"sym", "not"}:
        return formula
    if formula.kind == "and":
        return conj(*(distribute_ors(value) for value in formula.values))
    if formula.kind == "or":
        values = [distribute_ors(value) for value in formula.values]
        result = values[0]
        for value in values[1:]:
            result = distribute_pair(result, value)
        return result
    return distribute_ors(move_not_inward(eliminate_implications(formula)))


def distribute_pair(left: Formula, right: Formula) -> Formula:
    if left.kind == "and":
        return conj(*(distribute_pair(value, right) for value in left.values))
    if right.kind == "and":
        return conj(*(distribute_pair(left, value) for value in right.values))
    return disj(left, right)


def to_cnf(formula: Formula) -> Formula:
    return distribute_ors(move_not_inward(eliminate_implications(formula)))


def formula_to_clauses(formula: Formula) -> list[Clause]:
    cnf = to_cnf(formula)
    clause_formulas = cnf.values if cnf.kind == "and" else (cnf,)
    clauses: list[Clause] = []

    for clause_formula in clause_formulas:
        literals: list[str] = []
        collect_clause_literals(clause_formula, literals)
        normalized = normalize_clause(literals)
        if normalized is not None:
            clauses.append(normalized)

    return clauses


def collect_clause_literals(formula: Formula, literals: list[str]) -> None:
    if formula.kind == "or":
        for child in formula.values:
            collect_clause_literals(child, literals)
        return
    if formula.kind == "sym":
        literals.append(formula.name or "")
        return
    if formula.kind == "not" and required(formula.value).kind == "sym":
        literals.append(f"~{required(formula.value).name}")
        return
    raise ValueError(f"Formula is not a CNF clause: {formula_to_text(formula)}")


def normalize_clause(literals: Iterable[str]) -> Clause | None:
    unique: set[str] = set()
    for literal in literals:
        if complement(literal) in unique:
            return None
        unique.add(literal)

    return tuple(sorted(unique, key=lambda item: (item.replace("~", ""), item)))


def complement(literal: str) -> str:
    return literal[1:] if literal.startswith("~") else f"~{literal}"


def literal_to_text(literal: str) -> str:
    if literal.startswith("~"):
        return f"~{display_symbol(literal[1:])}"
    return display_symbol(literal)


def clause_to_text(clause: Clause) -> str:
    if not clause:
        return "{}"
    return " v ".join(literal_to_text(literal) for literal in clause)


def resolve_pair(left: Clause, right: Clause) -> list[Clause]:
    right_set = set(right)
    resolvents: list[Clause] = []

    for literal in left:
        opposite = complement(literal)
        if opposite not in right_set:
            continue

        merged = [
            *(item for item in left if item != literal),
            *(item for item in right if item != opposite),
        ]
        normalized = normalize_clause(merged)
        if normalized is not None:
            resolvents.append(normalized)

    return resolvents


def resolution_refutation(
    kb_clauses: list[Clause],
    negated_query_clauses: list[Clause],
    max_steps: int = 6000,
) -> dict[str, object]:
    clauses: list[Clause] = []
    clause_set: set[Clause] = set()
    support: set[Clause] = set()
    trace: list[str] = []

    def add_clause(clause: Clause) -> bool:
        if clause in clause_set:
            return False
        clause_set.add(clause)
        clauses.append(clause)
        return True

    for clause in kb_clauses:
        add_clause(clause)

    for clause in negated_query_clauses:
        add_clause(clause)
        support.add(clause)

    active_support = set(support)
    steps = 0
    rounds = 0

    while active_support and steps < max_steps:
        newly_derived: set[Clause] = set()
        support_clauses = sorted(
            (clause for clause in clauses if clause in active_support),
            key=lambda clause: (len(clause), clause),
        )
        base_clauses = sorted(clauses, key=lambda clause: (len(clause), clause))

        for support_clause in support_clauses:
            for base_clause in base_clauses:
                if support_clause == base_clause:
                    continue

                for resolvent in resolve_pair(support_clause, base_clause):
                    steps += 1

                    if len(trace) < 8:
                        trace.append(
                            f"{clause_to_text(support_clause)}  +  "
                            f"{clause_to_text(base_clause)}  ->  "
                            f"{clause_to_text(resolvent)}"
                        )

                    if not resolvent:
                        return {
                            "entailed": True,
                            "incomplete": False,
                            "steps": steps,
                            "rounds": rounds + 1,
                            "trace": trace,
                        }

                    if add_clause(resolvent):
                        newly_derived.add(resolvent)

                    if steps >= max_steps:
                        return {
                            "entailed": False,
                            "incomplete": True,
                            "steps": steps,
                            "rounds": rounds + 1,
                            "trace": trace,
                        }

        if not newly_derived:
            return {
                "entailed": False,
                "incomplete": False,
                "steps": steps,
                "rounds": rounds + 1,
                "trace": trace,
            }

        active_support = newly_derived
        rounds += 1

    return {
        "entailed": False,
        "incomplete": True,
        "steps": steps,
        "rounds": rounds,
        "trace": trace,
    }


@dataclass
class TellEntry:
    label: str
    text: str
    clauses_added: int


class KnowledgeBase:
    def __init__(self) -> None:
        self.clauses: list[Clause] = []
        self._clause_set: set[Clause] = set()
        self.tell_log: list[TellEntry] = []

    def tell(self, formula: Formula, label: str) -> int:
        added = 0
        for clause in formula_to_clauses(formula):
            if clause not in self._clause_set:
                self._clause_set.add(clause)
                self.clauses.append(clause)
                added += 1

        self.tell_log.insert(0, TellEntry(label, formula_to_text(formula), added))
        del self.tell_log[14:]
        return added

    def to_state(self) -> dict[str, object]:
        return {
            "clauses": [list(clause) for clause in self.clauses],
            "tell_log": [
                {
                    "label": entry.label,
                    "text": entry.text,
                    "clauses_added": entry.clauses_added,
                }
                for entry in self.tell_log
            ],
        }

    @classmethod
    def from_state(cls, data: dict[str, object]) -> "KnowledgeBase":
        kb = cls()
        kb.clauses = [
            tuple(str(literal) for literal in clause)
            for clause in data.get("clauses", [])
            if isinstance(clause, list)
        ]
        kb._clause_set = set(kb.clauses)
        kb.tell_log = [
            TellEntry(
                str(entry.get("label", "")),
                str(entry.get("text", "")),
                int(entry.get("clauses_added", 0)),
            )
            for entry in data.get("tell_log", [])
            if isinstance(entry, dict)
        ]
        return kb


@dataclass
class WumpusWorld:
    rows: int
    cols: int
    pits: set[Cell]
    wumpus: Cell

    @classmethod
    def random_episode(cls, rows: int, cols: int, pit_rate: float) -> "WumpusWorld":
        start = (0, 0)
        candidates = [(r, c) for r in range(rows) for c in range(cols) if (r, c) != start]
        start_neighbors = {
            (r, c)
            for r, c in ((1, 0), (0, 1))
            if 0 <= r < rows and 0 <= c < cols
        }
        # Keep the first percept clean when the grid is large enough, so Step Agent
        # visibly moves before it reaches a genuinely uncertain frontier.
        demo_candidates = [cell for cell in candidates if cell not in start_neighbors]
        hazard_candidates = demo_candidates if demo_candidates else candidates
        wumpus = random.choice(hazard_candidates)
        pit_candidates = [cell for cell in hazard_candidates if cell != wumpus]
        pits = {
            cell
            for cell in pit_candidates
            if random.random() < pit_rate
        }

        if pit_rate > 0 and not pits:
            if pit_candidates:
                pits.add(random.choice(pit_candidates))

        return cls(rows, cols, pits, wumpus)

    def all_cells(self) -> list[Cell]:
        return [(r, c) for r in range(self.rows) for c in range(self.cols)]

    def neighbors(self, cell: Cell) -> list[Cell]:
        row, col = cell
        candidates = [(row - 1, col), (row + 1, col), (row, col - 1), (row, col + 1)]
        return [
            (r, c)
            for r, c in candidates
            if 0 <= r < self.rows and 0 <= c < self.cols
        ]

    def percepts(self, cell: Cell) -> dict[str, bool]:
        around = self.neighbors(cell)
        return {
            "breeze": any(near in self.pits for near in around),
            "stench": any(near == self.wumpus for near in around),
        }


class LogicAgent:
    def __init__(self, rows: int = 4, cols: int = 4, pit_rate: float = 0.18) -> None:
        self.rows = max(2, min(8, rows))
        self.cols = max(2, min(8, cols))
        self.pit_rate = max(0.0, min(0.35, pit_rate))
        self.world = WumpusWorld.random_episode(self.rows, self.cols, self.pit_rate)
        self.kb = KnowledgeBase()
        self.visited: set[Cell] = set()
        self.safe: set[Cell] = set()
        self.confirmed_pits: set[Cell] = set()
        self.confirmed_wumpus: set[Cell] = set()
        self.told_percept_rules: set[Cell] = set()
        self.agent: Cell = (0, 0)
        self.last_from: Cell | None = None
        self.last_to: Cell | None = None
        self.move_count = 0
        self.active_percepts = {"breeze": False, "stench": False}
        self.metrics: dict[str, object] = {
            "total_steps": 0,
            "last_steps": 0,
            "last_ask": "No queries yet.",
            "last_trace": [],
        }
        self.status = "New episode created. The agent only knows that (1,1) is safe."
        self.over = False
        self.won = False
        self.tell_initial_axioms()
        self.enter_cell((0, 0))
        self.deduce_frontier()

    def tell_initial_axioms(self) -> None:
        start = (0, 0)
        candidates = [cell for cell in self.world.all_cells() if cell != start]

        self.kb.tell(neg(sym(pit_symbol(start))), "Start has no pit")
        self.kb.tell(neg(sym(wumpus_symbol(start))), "Start has no Wumpus")
        self.safe.add(start)

        self.kb.tell(
            disj(*(sym(wumpus_symbol(cell)) for cell in candidates)),
            "At least one Wumpus exists outside the start",
        )

        for index, first in enumerate(candidates):
            for second in candidates[index + 1 :]:
                self.kb.tell(
                    disj(neg(sym(wumpus_symbol(first))), neg(sym(wumpus_symbol(second)))),
                    "At most one Wumpus",
                )

        for cell in self.world.all_cells():
            self.kb.tell(
                disj(neg(sym(pit_symbol(cell))), neg(sym(wumpus_symbol(cell)))),
                "Pit and Wumpus cannot share a cell",
            )

    def enter_cell(self, cell: Cell) -> None:
        previous = self.agent
        if self.visited and cell != previous:
            self.last_from = previous
            self.last_to = cell
            self.move_count += 1

        self.agent = cell
        self.visited.add(cell)
        self.safe.add(cell)

        self.kb.tell(neg(sym(pit_symbol(cell))), f"Visited {coord(cell)}: no pit")
        self.kb.tell(neg(sym(wumpus_symbol(cell))), f"Visited {coord(cell)}: no Wumpus")

        if cell in self.world.pits:
            self.confirmed_pits.add(cell)
            self.over = True
            self.status = f"The agent moved to {coord(cell)} and found a pit. Episode failed."
            return

        if cell == self.world.wumpus:
            self.confirmed_wumpus.add(cell)
            self.over = True
            self.status = f"The agent moved to {coord(cell)} and found the Wumpus. Episode failed."
            return

        self.active_percepts = self.world.percepts(cell)
        self.tell_percepts(cell, self.active_percepts)
        if self.last_to == cell and self.last_from is not None:
            self.status = f"Moved from {coord(self.last_from)} to {coord(cell)}. Percepts: {self.percepts_text()}."
        else:
            self.status = f"Visited {coord(cell)}. Percepts: {self.percepts_text()}."
        self.check_win()

    def tell_percepts(self, cell: Cell, percepts: dict[str, bool]) -> None:
        if cell not in self.told_percept_rules:
            around = self.world.neighbors(cell)
            self.kb.tell(
                iff(sym(breeze_symbol(cell)), disj(*(sym(pit_symbol(near)) for near in around))),
                f"Breeze rule at {coord(cell)}",
            )
            self.kb.tell(
                iff(sym(stench_symbol(cell)), disj(*(sym(wumpus_symbol(near)) for near in around))),
                f"Stench rule at {coord(cell)}",
            )
            self.told_percept_rules.add(cell)

        self.kb.tell(
            sym(breeze_symbol(cell)) if percepts["breeze"] else neg(sym(breeze_symbol(cell))),
            f"{'Breeze' if percepts['breeze'] else 'No breeze'} at {coord(cell)}",
        )
        self.kb.tell(
            sym(stench_symbol(cell)) if percepts["stench"] else neg(sym(stench_symbol(cell))),
            f"{'Stench' if percepts['stench'] else 'No stench'} at {coord(cell)}",
        )

    def frontier_cells(self) -> list[Cell]:
        frontier: set[Cell] = set()
        for visited in self.visited:
            for near in self.world.neighbors(visited):
                if near not in self.visited:
                    frontier.add(near)
        return sorted(frontier)

    def deduce_frontier(self) -> None:
        for cell in self.frontier_cells():
            if cell not in self.safe and cell not in self.confirmed_pits and cell not in self.confirmed_wumpus:
                if self.ask_safe(cell)["entailed"]:
                    self.safe.add(cell)

            if cell not in self.safe and cell not in self.confirmed_pits:
                if self.ask_formula(sym(pit_symbol(cell)), f"PIT {coord(cell)}")["entailed"]:
                    self.confirmed_pits.add(cell)

            if cell not in self.safe and cell not in self.confirmed_wumpus:
                if self.ask_formula(sym(wumpus_symbol(cell)), f"WUMPUS {coord(cell)}")["entailed"]:
                    self.confirmed_wumpus.add(cell)

    def ask_safe(self, cell: Cell) -> dict[str, object]:
        pit_result = self.ask_formula(
            neg(sym(pit_symbol(cell))),
            f"NO PIT {coord(cell)}",
        )
        if not pit_result["entailed"]:
            self.metrics["last_ask"] = (
                f"SAFE {coord(cell)}: not proved because no-pit was not entailed "
                f"in {int(pit_result['steps']):,} step"
                f"{'s' if int(pit_result['steps']) != 1 else ''}"
            )
            return {
                "entailed": False,
                "incomplete": pit_result["incomplete"],
                "steps": pit_result["steps"],
                "rounds": pit_result["rounds"],
                "trace": pit_result["trace"],
            }

        wumpus_result = self.ask_formula(
            neg(sym(wumpus_symbol(cell))),
            f"NO WUMPUS {coord(cell)}",
        )
        steps = int(pit_result["steps"]) + int(wumpus_result["steps"])
        entailed = bool(pit_result["entailed"] and wumpus_result["entailed"])
        trace = list(pit_result["trace"])[:4] + list(wumpus_result["trace"])[:4]
        result = {
            "entailed": entailed,
            "incomplete": bool(pit_result["incomplete"] or wumpus_result["incomplete"]),
            "steps": steps,
            "rounds": int(pit_result["rounds"]) + int(wumpus_result["rounds"]),
            "trace": trace,
        }
        self.metrics["last_steps"] = steps
        self.metrics["last_trace"] = trace
        self.metrics["last_ask"] = (
            f"SAFE {coord(cell)}: {'proved' if entailed else 'not proved'} "
            f"by proving no-pit and no-Wumpus in {steps:,} step"
            f"{'s' if steps != 1 else ''}"
        )
        return result

    def ask_formula(self, query: Formula, label: str) -> dict[str, object]:
        negated_query_clauses = formula_to_clauses(neg(query))
        result = resolution_refutation(self.kb.clauses, negated_query_clauses)

        steps = int(result["steps"])
        self.metrics["total_steps"] = int(self.metrics["total_steps"]) + steps
        self.metrics["last_steps"] = steps
        self.metrics["last_trace"] = result["trace"]
        self.metrics["last_ask"] = (
            f"{label}: {'proved' if result['entailed'] else 'not proved'} "
            f"in {steps:,} step{'s' if steps != 1 else ''}"
            f"{' (step cap reached)' if result['incomplete'] else ''}"
        )
        return result

    def step(self) -> bool:
        if self.over:
            self.status = "Episode already solved." if self.won else "Episode is over. Start a new one to continue."
            return False

        self.deduce_frontier()
        path = self.path_to_known_safe_frontier()
        if path is None:
            self.status = "No provably safe frontier cell is reachable yet. The agent refuses to guess."
            return False

        next_cell = path[1]
        if next_cell not in self.visited:
            safety = self.ask_safe(next_cell)
            if not safety["entailed"]:
                self.status = f"Blocked: {coord(next_cell)} is adjacent but not provably safe."
                return False
            self.safe.add(next_cell)

        self.enter_cell(next_cell)
        self.deduce_frontier()
        return True

    def move_to(self, cell: Cell) -> bool:
        if self.over:
            return False
        if cell not in self.world.neighbors(self.agent):
            self.status = f"Manual move rejected: {coord(cell)} is not adjacent to the agent."
            return False
        if cell not in self.safe:
            safety = self.ask_safe(cell)
            if not safety["entailed"]:
                self.status = f"Manual move rejected: {coord(cell)} is not provably safe."
                return False
            self.safe.add(cell)

        self.enter_cell(cell)
        self.deduce_frontier()
        return True

    def path_to_known_safe_frontier(self) -> list[Cell] | None:
        targets = {
            cell
            for cell in self.safe
            if cell not in self.visited
            and cell not in self.confirmed_pits
            and cell not in self.confirmed_wumpus
        }
        if not targets:
            return None

        queue = [self.agent]
        parents: dict[Cell, Cell | None] = {self.agent: None}

        while queue:
            current = queue.pop(0)
            if current in targets:
                return self.rebuild_path(current, parents)

            for near in self.world.neighbors(current):
                if near in parents:
                    continue
                if near not in self.safe:
                    continue
                if near in self.confirmed_pits or near in self.confirmed_wumpus:
                    continue
                parents[near] = current
                queue.append(near)

        return None

    @staticmethod
    def rebuild_path(target: Cell, parents: dict[Cell, Cell | None]) -> list[Cell]:
        path: list[Cell] = []
        cursor: Cell | None = target
        while cursor is not None:
            path.append(cursor)
            cursor = parents[cursor]
        return list(reversed(path))

    def check_win(self) -> None:
        hazard_count = len(self.world.pits) + 1
        safe_cell_count = self.rows * self.cols - hazard_count
        if len(self.visited) >= safe_cell_count:
            self.won = True
            self.over = True
            self.status = "All non-hazard cells have been visited using only provably safe moves."

    def percepts_text(self) -> str:
        active = []
        if self.active_percepts["breeze"]:
            active.append("Breeze")
        if self.active_percepts["stench"]:
            active.append("Stench")
        return ", ".join(active) if active else "None"

    def to_state(self) -> dict[str, object]:
        return {
            "rows": self.rows,
            "cols": self.cols,
            "pit_rate": self.pit_rate,
            "world": {
                "rows": self.world.rows,
                "cols": self.world.cols,
                "pits": [list(cell) for cell in sorted(self.world.pits)],
                "wumpus": list(self.world.wumpus),
            },
            "kb": self.kb.to_state(),
            "visited": [list(cell) for cell in sorted(self.visited)],
            "safe": [list(cell) for cell in sorted(self.safe)],
            "confirmed_pits": [list(cell) for cell in sorted(self.confirmed_pits)],
            "confirmed_wumpus": [list(cell) for cell in sorted(self.confirmed_wumpus)],
            "told_percept_rules": [list(cell) for cell in sorted(self.told_percept_rules)],
            "agent": list(self.agent),
            "last_from": list(self.last_from) if self.last_from is not None else None,
            "last_to": list(self.last_to) if self.last_to is not None else None,
            "move_count": self.move_count,
            "active_percepts": dict(self.active_percepts),
            "metrics": {
                "total_steps": int(self.metrics.get("total_steps", 0)),
                "last_steps": int(self.metrics.get("last_steps", 0)),
                "last_ask": str(self.metrics.get("last_ask", "No queries yet.")),
                "last_trace": list(self.metrics.get("last_trace", [])),
            },
            "status": self.status,
            "over": self.over,
            "won": self.won,
        }

    @classmethod
    def from_state(cls, data: dict[str, object]) -> "LogicAgent":
        world_data = data.get("world", {})
        if not isinstance(world_data, dict):
            raise ValueError("Missing world state")

        agent = cls.__new__(cls)
        agent.rows = int(data.get("rows", world_data.get("rows", 4)))
        agent.cols = int(data.get("cols", world_data.get("cols", 4)))
        agent.pit_rate = float(data.get("pit_rate", 0.18))
        agent.world = WumpusWorld(
            int(world_data.get("rows", agent.rows)),
            int(world_data.get("cols", agent.cols)),
            set(read_cells(world_data.get("pits", []))),
            read_cell(world_data.get("wumpus", [0, 1])),
        )
        kb_data = data.get("kb", {})
        agent.kb = KnowledgeBase.from_state(kb_data if isinstance(kb_data, dict) else {})
        agent.visited = set(read_cells(data.get("visited", [])))
        agent.safe = set(read_cells(data.get("safe", [])))
        agent.confirmed_pits = set(read_cells(data.get("confirmed_pits", [])))
        agent.confirmed_wumpus = set(read_cells(data.get("confirmed_wumpus", [])))
        agent.told_percept_rules = set(read_cells(data.get("told_percept_rules", [])))
        agent.agent = read_cell(data.get("agent", [0, 0]))
        last_from = data.get("last_from")
        last_to = data.get("last_to")
        agent.last_from = read_cell(last_from) if last_from is not None else None
        agent.last_to = read_cell(last_to) if last_to is not None else None
        agent.move_count = int(data.get("move_count", 0))
        percepts = data.get("active_percepts", {})
        agent.active_percepts = {
            "breeze": bool(percepts.get("breeze", False)) if isinstance(percepts, dict) else False,
            "stench": bool(percepts.get("stench", False)) if isinstance(percepts, dict) else False,
        }
        metrics = data.get("metrics", {})
        agent.metrics = {
            "total_steps": int(metrics.get("total_steps", 0)) if isinstance(metrics, dict) else 0,
            "last_steps": int(metrics.get("last_steps", 0)) if isinstance(metrics, dict) else 0,
            "last_ask": str(metrics.get("last_ask", "No queries yet.")) if isinstance(metrics, dict) else "No queries yet.",
            "last_trace": list(metrics.get("last_trace", [])) if isinstance(metrics, dict) else [],
        }
        agent.status = str(data.get("status", "Ready."))
        agent.over = bool(data.get("over", False))
        agent.won = bool(data.get("won", False))
        return agent


def read_cell(value: object) -> Cell:
    if not isinstance(value, list) and not isinstance(value, tuple):
        raise ValueError("Cell must be a list or tuple")
    if len(value) != 2:
        raise ValueError("Cell must have two coordinates")
    return int(value[0]), int(value[1])


def read_cells(value: object) -> list[Cell]:
    if not isinstance(value, list):
        return []
    cells: list[Cell] = []
    for item in value:
        try:
            cells.append(read_cell(item))
        except (TypeError, ValueError):
            continue
    return cells
