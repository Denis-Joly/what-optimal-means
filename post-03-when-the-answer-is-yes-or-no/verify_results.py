#!/usr/bin/env python3
"""Fail loudly if a number or certificate used in Post 3 drifts."""

from __future__ import annotations

import argparse
from fractions import Fraction as F

from branch_and_bound import trace
from example import (
    Point,
    feasible,
    integer_feasible_points,
    load_model,
    nearest_feasible_integer,
    nearest_integer,
    objective,
    solve_integer_exact,
    solve_relaxation,
    solve_with_highs,
)


def close(actual: float, expected: float, tolerance: float = 1e-7) -> None:
    assert abs(actual - expected) <= tolerance, (actual, expected)


def verify(with_highs: bool = True) -> None:
    model = load_model()
    lp_point, lp_value = solve_relaxation(model)  # type: ignore[misc]
    assert lp_point == Point(F(9, 4), F(15, 4))
    assert lp_value == F(165, 4)

    rounded = nearest_integer(lp_point)
    assert rounded == Point(F(2), F(4))
    assert not feasible(model, rounded)
    assert rounded.x1 + rounded.x2 == 6
    assert 5 * rounded.x1 + 9 * rounded.x2 == 46

    points = integer_feasible_points(model)
    assert len(points) == 25
    nearest = nearest_feasible_integer(model, lp_point)
    assert nearest == Point(F(2), F(3))
    assert objective(model, nearest) == 34
    integer_point, integer_value = solve_integer_exact(model)
    assert integer_point == Point(F(0), F(5))
    assert integer_value == 40
    ranked = sorted(((objective(model, point), point) for point in points), reverse=True)
    assert ranked[:3] == [
        (F(40), Point(F(0), F(5))),
        (F(39), Point(F(3), F(3))),
        (F(37), Point(F(1), F(4))),
    ]
    assert lp_value - integer_value == F(5, 4)

    # Gomory's valid inequality removes the fractional root without excluding
    # any of this model's 25 feasible integer decisions.
    assert 2 * lp_point.x1 + 3 * lp_point.x2 == F(63, 4)
    assert F(63, 4) > 15
    assert all(2 * point.x1 + 3 * point.x2 <= 15 for point in points)

    nodes, snapshots = trace(model)
    expected = {
        "L0": (Point(F(9, 4), F(15, 4)), F(165, 4), "fractional"),
        "L1": (Point(F(9, 5), F(4)), F(41), "fractional"),
        "L2": (Point(F(3), F(3)), F(39), "integer"),
        "L3": (None, None, "infeasible"),
        "L4": (Point(F(1), F(40, 9)), F(365, 9), "fractional"),
        "L5": (Point(F(1), F(4)), F(37), "integer"),
        "L6": (Point(F(0), F(5)), F(40), "integer"),
    }
    for name, wanted in expected.items():
        got = nodes[name]
        assert (got.point, got.lp_bound, got.disposition) == wanted, (name, got, wanted)

    expected_snapshots = [
        (None, F(165, 4), None, (("L0", F(165, 4)),)),
        (F(39), F(41), Point(F(3), F(3)), (("L1", F(41)),)),
        (F(39), F(365, 9), Point(F(3), F(3)), (("L4", F(365, 9)),)),
        (F(39), F(365, 9), Point(F(3), F(3)), (("L6", F(365, 9)),)),
        (F(40), F(40), Point(F(0), F(5)), ()),
    ]
    assert len(snapshots) == len(expected_snapshots)
    for snapshot, wanted in zip(snapshots, expected_snapshots):
        got = (snapshot.lower, snapshot.upper, snapshot.incumbent, snapshot.open_bounds)
        assert got == wanted, (snapshot.step, got, wanted)

    previous_lower = None
    previous_upper = snapshots[0].upper
    for snapshot in snapshots:
        # U is not hand-authored: it is the maximum of every still-valid
        # frontier bound and the incumbent (the latter closes an empty tree).
        candidates = [bound for _, bound in snapshot.open_bounds]
        if snapshot.lower is not None:
            candidates.append(snapshot.lower)
        assert candidates and snapshot.upper == max(candidates)
        assert snapshot.upper <= previous_upper
        previous_upper = snapshot.upper
        if snapshot.lower is not None:
            if previous_lower is not None:
                assert snapshot.lower >= previous_lower
            assert snapshot.lower <= integer_value <= snapshot.upper
            previous_lower = snapshot.lower

    if with_highs:
        lp_highs, lp_highs_value = solve_with_highs(model, integer=False)
        mip_highs, mip_highs_value = solve_with_highs(model, integer=True)
        close(lp_highs[0], 2.25)
        close(lp_highs[1], 3.75)
        close(lp_highs_value, 41.25)
        close(mip_highs[0], 0.0)
        close(mip_highs[1], 5.0)
        close(mip_highs_value, 40.0)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--no-highs", action="store_true", help="run exact checks without the optional solver cross-check")
    args = parser.parse_args()
    verify(with_highs=not args.no_highs)
    suffix = " and solver cross-check" if not args.no_highs else ""
    print(f"OK: exact enumeration and raw-LP-bound branch-and-bound certificates{suffix} agree.")
