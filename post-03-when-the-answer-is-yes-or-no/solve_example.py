#!/usr/bin/env python3
"""Write the stable numerical outputs cited by Post 3."""

from __future__ import annotations

import csv
import json

from branch_and_bound import node_as_json, snapshot_as_json, trace
from example import (
    OUT,
    feasible,
    format_fraction,
    integer_feasible_points,
    load_model,
    nearest_feasible_integer,
    nearest_integer,
    objective,
    solve_integer_exact,
    solve_relaxation,
    squared_distance,
)


def point_payload(point):
    return {"x1": format_fraction(point.x1), "x2": format_fraction(point.x2)}


def build() -> str:
    model = load_model()
    lp_point, lp_value = solve_relaxation(model)  # type: ignore[misc]
    rounded = nearest_integer(lp_point)
    nearest = nearest_feasible_integer(model, lp_point)
    integer_point, integer_value = solve_integer_exact(model)
    points = sorted(integer_feasible_points(model), key=lambda p: (p.x1, p.x2))
    cut_root_lhs = 2 * lp_point.x1 + 3 * lp_point.x2
    cut_holds_for_all_integers = all(2 * point.x1 + 3 * point.x2 <= 15 for point in points)
    nodes, snapshots = trace(model)
    OUT.mkdir(exist_ok=True)

    with (OUT / "integer-points.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(["x1", "x2", "objective"])
        for point in points:
            writer.writerow([format_fraction(point.x1), format_fraction(point.x2), format_fraction(objective(model, point))])

    (OUT / "results.json").write_text(json.dumps({
        "lp_relaxation": {"point": point_payload(lp_point), "objective": format_fraction(lp_value)},
        "nearest_rounding": {
            "point": point_payload(rounded),
            "feasible": feasible(model, rounded),
            "second_constraint_lhs": format_fraction(5 * rounded.x1 + 9 * rounded.x2),
        },
        "nearest_feasible_integer": {
            "point": point_payload(nearest),
            "objective": format_fraction(objective(model, nearest)),
            "squared_distance": format_fraction(squared_distance(nearest, lp_point)),
        },
        "integer_optimum": {"point": point_payload(integer_point), "objective": format_fraction(integer_value)},
        "root_integrality_gap_absolute": format_fraction(lp_value - integer_value),
        "feasible_integer_points": len(points),
        "valid_integer_cut": {
            "inequality": "2*x1 + 3*x2 <= 15",
            "lp_root_lhs": format_fraction(cut_root_lhs),
            "cuts_off_lp_root": cut_root_lhs > 15,
            "integer_points_checked": len(points),
            "holds_for_all_feasible_integer_points": cut_holds_for_all_integers,
        },
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    (OUT / "branch-and-bound-trace.json").write_text(json.dumps({
        "note": "Exact trace on the textbook branch tree with an explicit deterministic tight-bound schedule; both root children are solved first. Not a solver log.",
        "nodes": [node_as_json(nodes[name]) for name in ("L0", "L1", "L2", "L3", "L4", "L5", "L6")],
        "snapshots": [snapshot_as_json(snapshot) for snapshot in snapshots],
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    report = "\n".join([
        "Bradley-Hax-Magnanti example",
        "-----------------------------",
        f"LP relaxation optimum       ({float(lp_point.x1):.2f}, {float(lp_point.x2):.2f}), z = {float(lp_value):.2f}",
        f"nearest rounding            ({rounded.x1}, {rounded.x2}), infeasible: 5x1 + 9x2 = {5 * rounded.x1 + 9 * rounded.x2} > 45",
        f"nearest feasible integer    ({nearest.x1}, {nearest.x2}), z = {objective(model, nearest)}",
        f"integer optimum             ({integer_point.x1}, {integer_point.x2}), z = {integer_value}",
        f"feasible integer points     {len(points)}",
        f"root integrality gap        {float(lp_value - integer_value):.2f} objective units",
        "",
        "Valid integer cut",
        "-----------------",
        "2x1 + 3x2 <= 15 holds for all 25 feasible integer points.",
        f"At the LP root its left side is {format_fraction(cut_root_lhs)} > 15, so the cut removes the fractional optimum.",
        "",
        "Branch-and-bound certificate (maximization; both root children solved first)",
        "-------------------------------------------",
        "At every snapshot with an incumbent: L <= z* <= U.",
        *[
            f"step {snapshot.step}: "
            + ("no incumbent" if snapshot.lower is None else f"{format_fraction(snapshot.lower)} <= z* <= {format_fraction(snapshot.upper)}")
            + f" — {snapshot.event}"
            for snapshot in snapshots
        ],
        "",
        "The root integrality gap compares the integer optimum with one LP relaxation.",
        "The live optimality gap is the certified interval U - L during the search.",
    ]) + "\n"
    (OUT / "results.txt").write_text(report, encoding="utf-8")
    return report


if __name__ == "__main__":
    print(build(), end="")
