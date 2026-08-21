#!/usr/bin/env python3
"""Reproduce three local SLSQP terminations on Haverly's pooling model."""

from __future__ import annotations

import json
import platform
from pathlib import Path

import numpy as np
import scipy
from scipy.optimize import minimize


ROOT = Path(__file__).resolve().parent
MODEL_PATH = ROOT / "data" / "model.json"
OUT_DIR = ROOT / "out"
MODEL = json.loads(MODEL_PATH.read_text(encoding="utf-8"))


def profit(values: np.ndarray) -> float:
    a, b, p_x, p_y, c_x, c_y, _q = values
    feeds = MODEL["feeds"]
    products = MODEL["products"]
    return float(
        products["X"]["price"] * (p_x + c_x)
        + products["Y"]["price"] * (p_y + c_y)
        - feeds["A"]["cost"] * a
        - feeds["B"]["cost"] * b
        - feeds["C"]["cost"] * (c_x + c_y)
    )


def equalities(values: np.ndarray) -> np.ndarray:
    a, b, p_x, p_y, _c_x, _c_y, q = values
    feeds = MODEL["feeds"]
    return np.array(
        [
            a + b - p_x - p_y,
            feeds["A"]["sulphur"] * a
            + feeds["B"]["sulphur"] * b
            - q * (a + b),
        ],
        dtype=float,
    )


def inequalities(values: np.ndarray) -> np.ndarray:
    _a, _b, p_x, p_y, c_x, c_y, q = values
    direct_sulphur = MODEL["feeds"]["C"]["sulphur"]
    product_x = MODEL["products"]["X"]
    product_y = MODEL["products"]["Y"]
    return np.array(
        [
            product_x["maximum_demand"] - p_x - c_x,
            product_y["maximum_demand"] - p_y - c_y,
            product_x["maximum_sulphur"] * (p_x + c_x)
            - q * p_x
            - direct_sulphur * c_x,
            product_y["maximum_sulphur"] * (p_y + c_y)
            - q * p_y
            - direct_sulphur * c_y,
        ],
        dtype=float,
    )


def canonical_vector(values: np.ndarray) -> list[float]:
    cleaned = np.where(np.abs(values) < 5e-8, 0.0, values)
    return [round(float(value), 6) for value in cleaned]


def generated_starts(seed: int, count: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    starts = []
    for _ in range(count):
        starts.append(
            np.concatenate(
                [
                    rng.uniform(0, 200, 2),
                    rng.uniform(0, 100, 4),
                    rng.uniform(1, 3, 1),
                ]
            )
        )
    return starts


def solve(start: np.ndarray, model: dict) -> dict:
    settings = model["experiment"]
    flow_bounds = tuple(model["bounds"]["flow"])
    q_bounds = tuple(model["bounds"]["pool_sulphur_q"])
    constraints = [
        {"type": "eq", "fun": equalities},
        {"type": "ineq", "fun": inequalities},
    ]
    result = minimize(
        lambda values: -profit(values),
        start,
        method="SLSQP",
        bounds=[flow_bounds] * 6 + [q_bounds],
        constraints=constraints,
        options={
            "ftol": settings["ftol"],
            "maxiter": settings["maximum_iterations"],
            "disp": False,
        },
    )
    eq = equalities(result.x)
    slack = inequalities(result.x)
    reported_profit = round(profit(result.x), 6)
    if abs(reported_profit) < 5e-8:
        reported_profit = 0.0
    return {
        "success": bool(result.success),
        "status": int(result.status),
        "message": str(result.message),
        "iterations": int(result.nit),
        "function_evaluations": int(result.nfev),
        "start": canonical_vector(start),
        "solution": canonical_vector(result.x),
        "profit": reported_profit,
        "maximum_equality_residual": round(float(np.max(np.abs(eq))), 12),
        "minimum_inequality_slack": round(float(np.min(slack)), 12),
    }


def main() -> None:
    model = MODEL
    settings = model["experiment"]
    starts = generated_starts(
        settings["random_seed"], settings["generated_start_count"]
    )
    labels = {
        7: "zero-flow result",
        8: "X-only result",
        0: "global result",
    }
    runs = []
    for index in settings["selected_start_indices"]:
        run = solve(starts[index], model)
        run["start_index"] = index
        run["label"] = labels[index]
        runs.append(run)

    payload = {
        "schema_version": 1,
        "model": model["name"],
        "runtime": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "platform": platform.platform(),
        },
        "settings": settings,
        "runs": runs,
        "independent_global_benchmark": model["independent_global_benchmark"],
        "interpretation": (
            "SLSQP success records satisfaction of that local solver's stopping tests. "
            "It is not a certificate of global optimality."
        ),
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "results.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    lines = [
        "Haverly pooling problem: fixed-start SLSQP experiment",
        f"Python {payload['runtime']['python']}; NumPy {np.__version__}; SciPy {scipy.__version__}",
        f"Seed {settings['random_seed']}",
        "",
    ]
    for run in runs:
        lines.extend(
            [
                f"Start {run['start_index']} ({run['label']})",
                f"  success: {run['success']} ({run['message']})",
                f"  profit: ${run['profit']:.2f}",
                f"  solution [a,b,p_x,p_y,c_x,c_y,q]: {run['solution']}",
                f"  max equality residual: {run['maximum_equality_residual']:.3e}",
                f"  min inequality slack: {run['minimum_inequality_slack']:.3e}",
                "",
            ]
        )
    lines.extend(
        [
            "Independent benchmark",
            "  documented global profit: $400.00",
            "  GAMS uses the opposite sign and reports -400 for haverly1.",
            "",
            payload["interpretation"],
        ]
    )
    (OUT_DIR / "results.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
