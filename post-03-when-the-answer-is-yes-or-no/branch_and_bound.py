#!/usr/bin/env python3
"""A deterministic, exact trace on the textbook Post 3 branch-and-bound tree.

This is explanatory code, not a general mixed-integer solver. It uses Bradley,
Hax and Magnanti's branch tree with an explicit schedule—both root children
are solved first—and solves each two-dimensional LP by enumerating vertices
with exact rational arithmetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from example import F, Model, Point, format_fraction, objective, solve_relaxation


Bound = tuple[str, str, int]


@dataclass(frozen=True)
class NodeSpec:
    name: str
    parent: str | None
    added_bound: Bound | None
    bounds: tuple[Bound, ...]


@dataclass(frozen=True)
class NodeResult:
    name: str
    parent: str | None
    added_bound: Bound | None
    point: Point | None
    lp_bound: Fraction | None
    disposition: str


@dataclass(frozen=True)
class Snapshot:
    step: int
    event: str
    lower: Fraction | None
    upper: Fraction
    incumbent: Point | None
    open_bounds: tuple[tuple[str, Fraction], ...]

    @property
    def open_nodes(self) -> tuple[str, ...]:
        return tuple(name for name, _ in self.open_bounds)


NODE_SPECS = (
    NodeSpec("L0", None, None, ()),
    NodeSpec("L1", "L0", ("x2", ">=", 4), (("x2", ">=", 4),)),
    NodeSpec("L2", "L0", ("x2", "<=", 3), (("x2", "<=", 3),)),
    NodeSpec("L3", "L1", ("x1", ">=", 2), (("x2", ">=", 4), ("x1", ">=", 2))),
    NodeSpec("L4", "L1", ("x1", "<=", 1), (("x2", ">=", 4), ("x1", "<=", 1))),
    NodeSpec("L5", "L4", ("x2", "<=", 4), (("x2", ">=", 4), ("x1", "<=", 1), ("x2", "<=", 4))),
    NodeSpec("L6", "L4", ("x2", ">=", 5), (("x2", ">=", 5), ("x1", "<=", 1))),
)


def is_integer(point: Point) -> bool:
    return point.x1.denominator == 1 and point.x2.denominator == 1


def solve_nodes(model: Model) -> dict[str, NodeResult]:
    results: dict[str, NodeResult] = {}
    for spec in NODE_SPECS:
        solved = solve_relaxation(model, spec.bounds)
        if solved is None:
            results[spec.name] = NodeResult(spec.name, spec.parent, spec.added_bound, None, None, "infeasible")
            continue
        point, bound = solved
        disposition = "integer" if is_integer(point) else "fractional"
        results[spec.name] = NodeResult(spec.name, spec.parent, spec.added_bound, point, bound, disposition)
    return results


def trace(model: Model) -> tuple[dict[str, NodeResult], list[Snapshot]]:
    """Return a tight, deterministic trace with bounds derived from state.

    L2 is solved with L1. Its LP optimum is already integer, so it becomes the
    first incumbent at 39. When L4 branches, unresolved L6 inherits its
    parent's valid bound until it is processed.
    """
    nodes = solve_nodes(model)

    incumbent: Point | None = None
    lower: Fraction | None = None
    frontier: dict[str, Fraction] = {}
    snapshots: list[Snapshot] = []

    def accept_integer(name: str) -> None:
        nonlocal incumbent, lower
        node = nodes[name]
        if node.point is None or node.lp_bound is None or node.disposition != "integer":
            raise AssertionError(f"{name} is not an integer node")
        if lower is None or node.lp_bound > lower:
            incumbent, lower = node.point, node.lp_bound

    def record(event: str) -> None:
        candidates = list(frontier.values())
        if lower is not None:
            candidates.append(lower)
        if not candidates:
            raise AssertionError("A certificate needs a frontier bound or incumbent")
        snapshots.append(Snapshot(
            step=len(snapshots),
            event=event,
            lower=lower,
            upper=max(candidates),
            incumbent=incumbent,
            open_bounds=tuple(sorted(frontier.items())),
        ))

    frontier["L0"] = nodes["L0"].lp_bound  # type: ignore[assignment]
    record("Solve root relaxation L0")

    frontier.pop("L0")
    frontier["L1"] = nodes["L1"].lp_bound  # type: ignore[assignment]
    accept_integer("L2")
    record("Solve both root children: L2 gives the first incumbent")

    frontier.pop("L1")
    frontier["L4"] = nodes["L4"].lp_bound  # type: ignore[assignment]
    record("L3 is infeasible; L4 tightens the global upper bound")

    inherited_l6_bound = frontier.pop("L4")
    frontier["L6"] = inherited_l6_bound
    accept_integer("L5")  # 37 cannot improve the incumbent of 39.
    record("L5 is integer but cannot improve the incumbent; L6 remains open")

    frontier.pop("L6")
    accept_integer("L6")
    record("L6 improves the incumbent and closes the certificate")
    return nodes, snapshots


def node_as_json(node: NodeResult) -> dict[str, object]:
    return {
        "name": node.name,
        "parent": node.parent,
        "added_bound": list(node.added_bound) if node.added_bound else None,
        "solution": None if node.point is None else {
            "x1": format_fraction(node.point.x1),
            "x2": format_fraction(node.point.x2),
        },
        "lp_bound": None if node.lp_bound is None else format_fraction(node.lp_bound),
        "disposition": node.disposition,
    }


def snapshot_as_json(snapshot: Snapshot) -> dict[str, object]:
    return {
        "step": snapshot.step,
        "event": snapshot.event,
        "lower": None if snapshot.lower is None else format_fraction(snapshot.lower),
        "upper": format_fraction(snapshot.upper),
        "incumbent": None if snapshot.incumbent is None else {
            "x1": format_fraction(snapshot.incumbent.x1),
            "x2": format_fraction(snapshot.incumbent.x2),
        },
        "open_nodes": list(snapshot.open_nodes),
        "open_bounds": {name: format_fraction(bound) for name, bound in snapshot.open_bounds},
    }
