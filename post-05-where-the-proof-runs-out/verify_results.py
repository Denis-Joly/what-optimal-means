#!/usr/bin/env python3
"""Check the Post 5 numerical outputs and static visual artefacts."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from run_experiment import equalities, generated_starts, inequalities, profit, solve


ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"
failures: list[str] = []
checks = 0


def check(condition: bool, message: str) -> None:
    global checks
    checks += 1
    if not condition:
        failures.append(message)


def close(left: float, right: float, tolerance: float = 1e-6) -> bool:
    return abs(left - right) <= tolerance


def main() -> None:
    model = json.loads((ROOT / "data" / "model.json").read_text(encoding="utf-8"))
    results = json.loads((OUT / "results.json").read_text(encoding="utf-8"))
    text_results = (OUT / "results.txt").read_text(encoding="utf-8")
    figure = (OUT / "fig1-local-successes.html").read_text(encoding="utf-8")
    svg = (OUT / "fig1-local-successes.svg").read_text(encoding="utf-8")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    tolerance = float(model["experiment"]["feasibility_tolerance"])

    check(results["schema_version"] == 1, "unexpected results schema")
    check(results["model"] == model["name"], "model name drift")
    check(results["runtime"]["numpy"] == "2.5.2", "NumPy version is not pinned output")
    check(results["runtime"]["scipy"] == "1.18.0", "SciPy version is not pinned output")
    check("numpy==2.5.2" in requirements, "NumPy pin missing")
    check("scipy==1.18.0" in requirements, "SciPy pin missing")
    check(
        model["experiment"]["generated_start_count"] == 9,
        "expected a nine-point generated start sequence",
    )

    expected_profits = [0.0, 100.0, 400.0]
    expected_solutions = [
        [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 2.11234],
        [50.0, 0.0, 50.0, 0.0, 50.0, 0.0, 3.0],
        [0.0, 100.0, 0.0, 100.0, 0.0, 100.0, 1.0],
    ]
    indices = model["experiment"]["selected_start_indices"]
    starts = generated_starts(
        model["experiment"]["random_seed"],
        model["experiment"]["generated_start_count"],
    )
    check(len(results["runs"]) == 3, "expected exactly three runs")

    for position, (run, expected_profit, expected_solution, index) in enumerate(
        zip(results["runs"], expected_profits, expected_solutions, indices, strict=True)
    ):
        values = np.asarray(run["solution"], dtype=float)
        check(run["start_index"] == index, f"run {position}: start index drift")
        check(run["success"] is True, f"run {position}: solver did not report success")
        check(run["status"] == 0, f"run {position}: unexpected solver status")
        check("successfully" in run["message"].lower(), f"run {position}: unexpected message")
        check(close(run["profit"], expected_profit), f"run {position}: profit drift")
        check(
            np.allclose(values, expected_solution, atol=tolerance, rtol=0),
            f"run {position}: solution drift",
        )
        check(
            np.max(np.abs(equalities(values))) <= tolerance,
            f"run {position}: equality infeasible",
        )
        check(
            np.min(inequalities(values)) >= -tolerance,
            f"run {position}: inequality infeasible",
        )
        check(
            close(profit(values), expected_profit, tolerance),
            f"run {position}: objective mismatch",
        )
        check(
            np.allclose(run["start"], starts[index], atol=tolerance, rtol=0),
            f"run {position}: stored start drift",
        )

        rerun = solve(starts[index], model)
        check(rerun["success"] is True, f"run {position}: fresh rerun failed")
        check(close(rerun["profit"], expected_profit), f"run {position}: fresh rerun profit drift")
        check(
            np.allclose(rerun["solution"], expected_solution, atol=tolerance, rtol=0),
            f"run {position}: fresh rerun solution drift",
        )

    benchmark = model["independent_global_benchmark"]
    benchmark_values = np.array(
        [benchmark["solution"][name] for name in model["variables"]], dtype=float
    )
    check(close(profit(benchmark_values), benchmark["profit"]), "benchmark profit mismatch")
    check(
        np.max(np.abs(equalities(benchmark_values))) <= tolerance,
        "benchmark equality infeasible",
    )
    check(
        np.min(inequalities(benchmark_values)) >= -tolerance,
        "benchmark inequality infeasible",
    )

    for token in ("$0.00", "$100.00", "$400.00", "Optimization terminated successfully"):
        check(token in text_results, f"results.txt missing {token}")
    check(figure.count("<figure") == 1, "HTML fragment must contain exactly one figure")
    check("<title id=\"post5-fig1-title\"" in figure, "SVG title missing")
    check("<desc id=\"post5-fig1-desc\"" in figure, "SVG description missing")
    check("role=\"img\"" in figure, "SVG image role missing")
    check("tabindex=\"0\"" in figure, "scroll region is not keyboard focusable")
    check("post5-mobile-hint" in figure, "mobile scroll hint missing")
    check("min-width: 680px" in figure, "mobile minimum width missing")
    check("independently documented global optimum" in svg, "global annotation missing")
    check("/Users/" not in readme, "README contains an absolute local path")

    if failures:
        for failure in failures:
            print(f"FAIL: {failure}")
        raise SystemExit(f"{len(failures)} of {checks} checks failed")
    print(f"PASS: {checks}/{checks} checks")


if __name__ == "__main__":
    main()
