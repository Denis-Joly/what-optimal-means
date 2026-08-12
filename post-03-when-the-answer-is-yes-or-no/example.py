#!/usr/bin/env python3
"""Exact model utilities and an independent HiGHS cross-check for Post 3."""

from __future__ import annotations

import json
from dataclasses import dataclass
from fractions import Fraction
from itertools import combinations
from pathlib import Path
from typing import Iterable, Sequence


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"
F = Fraction


@dataclass(frozen=True)
class Model:
    objective: tuple[int, int]
    constraints: tuple[tuple[tuple[int, int], int], ...]


@dataclass(frozen=True)
class Point:
    x1: Fraction
    x2: Fraction

    @property
    def pair(self) -> tuple[Fraction, Fraction]:
        return self.x1, self.x2


def load_model() -> Model:
    payload = json.loads((DATA / "bradley-hax-magnanti.json").read_text(encoding="utf-8"))
    if payload["sense"] != "maximize" or payload["variables"] != ["x1", "x2"]:
        raise ValueError("This companion expects the documented two-variable maximization model")
    if any(item.get("sense") != "<=" for item in payload["constraints"]):
        raise ValueError("Every documented constraint must use the <= sense")
    if payload.get("bounds", {}).get("lower") != [0, 0]:
        raise ValueError("The documented lower bounds must be [0, 0]")
    if payload.get("integer_variables") != ["x1", "x2"]:
        raise ValueError("Both and only x1 and x2 must be declared integer")
    constraints = tuple(
        (tuple(int(value) for value in item["coefficients"]), int(item["rhs"]))
        for item in payload["constraints"]
    )
    return Model(tuple(int(value) for value in payload["objective"]), constraints)  # type: ignore[arg-type]


def objective(model: Model, point: Point) -> Fraction:
    return model.objective[0] * point.x1 + model.objective[1] * point.x2


def feasible(model: Model, point: Point) -> bool:
    if point.x1 < 0 or point.x2 < 0:
        return False
    return all(a * point.x1 + b * point.x2 <= rhs for (a, b), rhs in model.constraints)


def integer_feasible_points(model: Model) -> list[Point]:
    max_x1 = min(rhs // a for (a, _), rhs in model.constraints if a > 0)
    max_x2 = min(rhs // b for (_, b), rhs in model.constraints if b > 0)
    return [
        Point(F(x1), F(x2))
        for x1 in range(max_x1 + 1)
        for x2 in range(max_x2 + 1)
        if feasible(model, Point(F(x1), F(x2)))
    ]


def _intersection(
    first: tuple[tuple[int, int], int], second: tuple[tuple[int, int], int]
) -> Point | None:
    (a1, b1), c1 = first
    (a2, b2), c2 = second
    determinant = a1 * b2 - a2 * b1
    if determinant == 0:
        return None
    return Point(F(c1 * b2 - c2 * b1, determinant), F(a1 * c2 - a2 * c1, determinant))


def relaxation_vertices(
    model: Model,
    extra_bounds: Iterable[tuple[str, str, int]] = (),
) -> list[Point]:
    """Enumerate all vertices of one 2-D LP using exact rational arithmetic."""
    inequalities: list[tuple[tuple[int, int], int]] = list(model.constraints)
    inequalities.extend([((-1, 0), 0), ((0, -1), 0)])
    for variable, sense, value in extra_bounds:
        index = 0 if variable == "x1" else 1
        coefficient = [0, 0]
        coefficient[index] = 1 if sense == "<=" else -1
        inequalities.append((tuple(coefficient), value if sense == "<=" else -value))  # type: ignore[arg-type]

    def satisfies(point: Point) -> bool:
        return all(a * point.x1 + b * point.x2 <= rhs for (a, b), rhs in inequalities)

    vertices = {
        point
        for first, second in combinations(inequalities, 2)
        if (point := _intersection(first, second)) is not None and satisfies(point)
    }
    return sorted(vertices, key=lambda p: (p.x1, p.x2))


def solve_relaxation(
    model: Model,
    extra_bounds: Sequence[tuple[str, str, int]] = (),
) -> tuple[Point, Fraction] | None:
    vertices = relaxation_vertices(model, extra_bounds)
    if not vertices:
        return None
    point = max(vertices, key=lambda candidate: (objective(model, candidate), -candidate.x1, -candidate.x2))
    return point, objective(model, point)


def solve_integer_exact(model: Model) -> tuple[Point, Fraction]:
    points = integer_feasible_points(model)
    point = max(points, key=lambda candidate: (objective(model, candidate), -candidate.x1, -candidate.x2))
    return point, objective(model, point)


def nearest_integer(point: Point) -> Point:
    """Round non-negative halves upward; this example has no half ties."""
    return Point(F(int(point.x1 + F(1, 2))), F(int(point.x2 + F(1, 2))))


def squared_distance(first: Point, second: Point) -> Fraction:
    return (first.x1 - second.x1) ** 2 + (first.x2 - second.x2) ** 2


def nearest_feasible_integer(model: Model, point: Point) -> Point:
    return min(
        integer_feasible_points(model),
        key=lambda candidate: (squared_distance(candidate, point), -objective(model, candidate)),
    )


def solve_with_highs(model: Model, integer: bool) -> tuple[tuple[float, float], float]:
    """Solve through PuLP/HiGHS. Imports stay local so exact scripts need no package."""
    try:
        import pulp
    except ImportError as exc:  # pragma: no cover - exercised by users without dependencies
        raise RuntimeError("PuLP and HiGHS are required for the independent solver cross-check") from exc

    category = pulp.LpInteger if integer else pulp.LpContinuous
    problem = pulp.LpProblem("answer_yes_or_no", pulp.LpMaximize)
    x1 = pulp.LpVariable("x1", lowBound=0, cat=category)
    x2 = pulp.LpVariable("x2", lowBound=0, cat=category)
    problem += model.objective[0] * x1 + model.objective[1] * x2
    for index, ((a, b), rhs) in enumerate(model.constraints, 1):
        problem += a * x1 + b * x2 <= rhs, f"constraint_{index}"
    status = problem.solve(pulp.HiGHS(msg=False))
    if pulp.LpStatus[status] != "Optimal":
        raise RuntimeError(f"HiGHS returned {pulp.LpStatus[status]}")
    return (float(x1.value()), float(x2.value())), float(pulp.value(problem.objective))


def format_fraction(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"
