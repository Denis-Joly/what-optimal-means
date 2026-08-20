#!/usr/bin/env python3
"""Run the reproducible numerical experiments for article 4.

Dependencies are deliberately limited to the Python standard library and PuLP.
PuLP's in-process HiGHS interface is used for the robust portfolio LPs.
"""

from __future__ import annotations

import argparse
import itertools
import json
import math
import random
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Sequence

import highspy
import pulp


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "data" / "model.json"
DEFAULT_OUTPUT_DIR = ROOT / "out"
Z_975 = 1.959963984540054


@dataclass
class OnlineStats:
    """Numerically stable one-pass sample moments."""

    n: int = 0
    mean: float = 0.0
    m2: float = 0.0

    def add(self, value: float) -> None:
        self.n += 1
        delta = value - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (value - self.mean)

    @property
    def sample_variance(self) -> float:
        if self.n < 2:
            raise ValueError("At least two observations are required")
        return self.m2 / (self.n - 1)

    @property
    def standard_error(self) -> float:
        return math.sqrt(self.sample_variance / self.n)

    def confidence_interval_95(self) -> list[float]:
        half_width = Z_975 * self.standard_error
        return [self.mean - half_width, self.mean + half_width]


def load_model(path: Path = DEFAULT_MODEL) -> dict:
    with path.open(encoding="utf-8") as handle:
        model = json.load(handle)
    validate_model(model)
    return model


def validate_model(model: dict) -> None:
    figure1 = model["figure1"]
    if int(figure1["alternatives"]) < 2:
        raise ValueError("Figure 1 needs at least two alternatives")
    if int(figure1["replications"]) < 100_000:
        raise ValueError("Figure 1 needs at least 100,000 replications")
    if int(figure1["seed"]) != 20260820:
        raise ValueError("Figure 1's publication seed must be 20260820")

    figure2 = model["figure2"]
    assets = figure2["assets"]
    if not assets:
        raise ValueError("Figure 2 needs at least one asset")
    if not math.isclose(float(figure2["gamma_start"]), 0.0):
        raise ValueError("The Gamma grid must start at zero")
    if not math.isclose(float(figure2["gamma_stop"]), float(len(assets))):
        raise ValueError("The Gamma grid must stop at the number of assets")
    if not math.isclose(float(figure2["gamma_step"]), 0.5):
        raise ValueError("The Gamma grid must use half-unit steps")
    if figure2["shock_distribution"] != "iid Uniform[-1, 1]":
        raise ValueError("The published simulation distribution must remain explicit")
    if figure2["robust_uncertainty_set"] != "|U_i| <= 1 and sum(|U_i|) <= Gamma":
        raise ValueError("The full symmetric Bertsimas-Sim set must remain explicit")
    if figure2["effective_adverse_projection"] != "q_i = max(0, -U_i)":
        raise ValueError("The one-sided adverse projection must remain explicit")
    for asset in assets:
        if float(asset["max_deviation"]) < 0.0:
            raise ValueError("Maximum deviations must be non-negative")
        if float(asset["defensive_cost"]) <= 0.0:
            raise ValueError("Defensive costs must be positive")


def standard_normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def adaptive_simpson(
    function: Callable[[float], float],
    lower: float,
    upper: float,
    tolerance: float,
    max_depth: int = 24,
) -> tuple[float, float]:
    """Integrate a smooth scalar function and return value plus error estimate."""

    midpoint = (lower + upper) / 2.0
    f_lower = function(lower)
    f_midpoint = function(midpoint)
    f_upper = function(upper)
    whole = (upper - lower) * (f_lower + 4.0 * f_midpoint + f_upper) / 6.0

    def recurse(
        a: float,
        b: float,
        f_a: float,
        f_mid: float,
        f_b: float,
        estimate: float,
        local_tolerance: float,
        depth: int,
    ) -> tuple[float, float]:
        mid = (a + b) / 2.0
        left_mid = (a + mid) / 2.0
        right_mid = (mid + b) / 2.0
        f_left_mid = function(left_mid)
        f_right_mid = function(right_mid)
        left = (mid - a) * (f_a + 4.0 * f_left_mid + f_mid) / 6.0
        right = (b - mid) * (f_mid + 4.0 * f_right_mid + f_b) / 6.0
        correction = left + right - estimate
        if depth <= 0 or abs(correction) <= 15.0 * local_tolerance:
            corrected = left + right + correction / 15.0
            return corrected, abs(correction) / 15.0
        left_value, left_error = recurse(
            a,
            mid,
            f_a,
            f_left_mid,
            f_mid,
            left,
            local_tolerance / 2.0,
            depth - 1,
        )
        right_value, right_error = recurse(
            mid,
            b,
            f_mid,
            f_right_mid,
            f_b,
            right,
            local_tolerance / 2.0,
            depth - 1,
        )
        return left_value + right_value, left_error + right_error

    return recurse(
        lower,
        upper,
        f_lower,
        f_midpoint,
        f_upper,
        whole,
        tolerance,
        max_depth,
    )


def expected_maximum_standard_normals(
    alternatives: int,
    upper_limit: float,
    tolerance: float,
) -> tuple[float, float, float]:
    """Compute E[max Z_i] using a stable one-dimensional tail integral.

    For iid standard normals,
      E[max Z_i] = integral_0^inf [1-Phi(t)^n-(1-Phi(t))^n] dt.
    The omitted positive tail is bounded by n * (1-Phi(upper_limit)) integrated
    to infinity, itself bounded by n * phi(upper_limit).
    """

    def integrand(value: float) -> float:
        cdf = standard_normal_cdf(value)
        return 1.0 - cdf**alternatives - (1.0 - cdf) ** alternatives

    value, quadrature_error = adaptive_simpson(
        integrand,
        0.0,
        upper_limit,
        tolerance,
    )
    tail_bound = alternatives * math.exp(-(upper_limit**2) / 2.0) / math.sqrt(
        2.0 * math.pi
    )
    return value, quadrature_error, tail_bound


def run_optimizer_curse(config: dict) -> dict:
    seed = int(config["seed"])
    alternatives = int(config["alternatives"])
    replications = int(config["replications"])
    true_value = float(config["true_value"])
    estimation_sd = float(config["estimation_sd"])
    out_of_sample_sd = float(config["out_of_sample_sd"])
    scatter_size = int(config["scatter_sample_size"])
    rng = random.Random(seed)

    selected_estimate_stats = OnlineStats()
    selected_outcome_stats = OnlineStats()
    disappointment_stats = OnlineStats()
    selection_counts = [0 for _ in range(alternatives)]
    scatter_points: list[list[float | int]] = []

    for replication in range(replications):
        estimates = [
            rng.gauss(true_value, estimation_sd) for _ in range(alternatives)
        ]
        selected_index = max(range(alternatives), key=estimates.__getitem__)
        # Draw a fresh outcome for every alternative, then reveal only the selected one.
        # This makes the out-of-sample independence literal rather than distributional.
        outcomes = [
            rng.gauss(true_value, out_of_sample_sd) for _ in range(alternatives)
        ]
        selected_estimate = estimates[selected_index]
        selected_outcome = outcomes[selected_index]
        disappointment = selected_estimate - selected_outcome

        selected_estimate_stats.add(selected_estimate)
        selected_outcome_stats.add(selected_outcome)
        disappointment_stats.add(disappointment)
        selection_counts[selected_index] += 1
        if replication < scatter_size:
            scatter_points.append(
                [
                    round(selected_estimate, 8),
                    round(selected_outcome, 8),
                    selected_index,
                ]
            )

    expected_max, quadrature_error, tail_bound = expected_maximum_standard_normals(
        alternatives,
        float(config["quadrature_upper_limit"]),
        float(config["quadrature_tolerance"]),
    )
    estimate_se = selected_estimate_stats.standard_error
    standardised_quadrature_gap = (
        selected_estimate_stats.mean - expected_max
    ) / estimate_se

    return {
        "design": {
            "seed": seed,
            "alternatives": alternatives,
            "true_value_each": true_value,
            "estimation_distribution": f"Normal({true_value:g}, {estimation_sd:g}^2)",
            "out_of_sample_distribution": f"Normal({true_value:g}, {out_of_sample_sd:g}^2)",
            "replications": replications,
            "selection_rule": "Choose the alternative with the largest estimate",
        },
        "monte_carlo": {
            "mean_selected_estimate": selected_estimate_stats.mean,
            "se_selected_estimate": estimate_se,
            "ci95_selected_estimate": selected_estimate_stats.confidence_interval_95(),
            "mean_selected_out_of_sample": selected_outcome_stats.mean,
            "se_selected_out_of_sample": selected_outcome_stats.standard_error,
            "ci95_selected_out_of_sample": selected_outcome_stats.confidence_interval_95(),
            "mean_disappointment": disappointment_stats.mean,
            "se_disappointment": disappointment_stats.standard_error,
            "ci95_disappointment": disappointment_stats.confidence_interval_95(),
            "selection_counts": selection_counts,
            "selection_rate_min": min(selection_counts) / replications,
            "selection_rate_max": max(selection_counts) / replications,
        },
        "quadrature_check": {
            "identity": "E[max Z_i] = integral_0^infinity (1-Phi(t)^n-(1-Phi(t))^n) dt",
            "expected_maximum": expected_max,
            "reported_quadrature_error": quadrature_error,
            "omitted_tail_upper_bound": tail_bound,
            "monte_carlo_minus_quadrature": selected_estimate_stats.mean
            - expected_max,
            "gap_in_monte_carlo_standard_errors": standardised_quadrature_gap,
        },
        "interpretation": {
            "optimizer_optimism": "The selected estimate is biased upward although every true value is zero.",
            "independent_check": "The fresh outcome for the selected alternative remains centred on zero.",
            "uncertainty": "Monte Carlo standard errors and normal-approximation 95% confidence intervals describe simulation error, not model uncertainty.",
        },
        "figure_data": {
            "scatter_columns": [
                "selected_estimate",
                "selected_out_of_sample",
                "selected_alternative_index",
            ],
            "scatter_points": scatter_points,
        },
    }


def gamma_grid(config: dict) -> list[float]:
    start = float(config["gamma_start"])
    stop = float(config["gamma_stop"])
    step = float(config["gamma_step"])
    count = int(round((stop - start) / step))
    return [round(start + index * step, 10) for index in range(count + 1)]


def highs_solver() -> pulp.HiGHS:
    return pulp.HiGHS(msg=False)


def asset_vectors(config: dict) -> tuple[list[str], list[float], list[float], list[float]]:
    assets = config["assets"]
    return (
        [str(asset["id"]) for asset in assets],
        [float(asset["nominal_return"]) for asset in assets],
        [float(asset["max_deviation"]) for asset in assets],
        [float(asset["defensive_cost"]) for asset in assets],
    )


def solve_counterpart(config: dict, gamma: float) -> dict:
    """Solve the exact Bertsimas-Sim linear counterpart with z and p_i."""

    ids, nominal, deviations, costs = asset_vectors(config)
    maximum_weight = float(config["max_weight"])
    target_return = float(config["target_return"])
    problem = pulp.LpProblem(f"robust_portfolio_gamma_{gamma:g}", pulp.LpMinimize)
    weights = {
        asset_id: pulp.LpVariable(
            f"x_{asset_id}", lowBound=0.0, upBound=maximum_weight
        )
        for asset_id in ids
    }
    z = pulp.LpVariable("z", lowBound=0.0)
    p = {
        asset_id: pulp.LpVariable(f"p_{asset_id}", lowBound=0.0)
        for asset_id in ids
    }

    problem += pulp.lpSum(
        costs[index] * weights[asset_id] for index, asset_id in enumerate(ids)
    )
    problem += pulp.lpSum(weights.values()) == 1.0, "fully_invested"
    problem += (
        pulp.lpSum(
            nominal[index] * weights[asset_id]
            for index, asset_id in enumerate(ids)
        )
        - gamma * z
        - pulp.lpSum(p.values())
        >= target_return,
        "robust_return",
    )
    for index, asset_id in enumerate(ids):
        problem += (
            z + p[asset_id] >= deviations[index] * weights[asset_id],
            f"exposure_{asset_id}",
        )

    status = problem.solve(highs_solver())
    if status != pulp.LpStatusOptimal:
        raise RuntimeError(
            f"HiGHS failed for Gamma={gamma:g}: {pulp.LpStatus[status]}"
        )
    solved_weights = [float(pulp.value(weights[asset_id])) for asset_id in ids]
    solved_p = [float(pulp.value(p[asset_id])) for asset_id in ids]
    return {
        "weights": solved_weights,
        "objective": float(pulp.value(problem.objective)),
        "z": float(pulp.value(z)),
        "p": solved_p,
        "counterpart_penalty": gamma * float(pulp.value(z)) + sum(solved_p),
    }


def adversarial_extreme_points(size: int, gamma: float) -> Iterable[tuple[float, ...]]:
    """Enumerate the vertices needed for a non-negative budgeted loss."""

    full = int(math.floor(gamma + 1e-12))
    fractional = gamma - full
    if full >= size:
        yield tuple(1.0 for _ in range(size))
        return
    for selected in itertools.combinations(range(size), full):
        selected_set = set(selected)
        if fractional <= 1e-12:
            yield tuple(1.0 if index in selected_set else 0.0 for index in range(size))
        else:
            for fractional_index in range(size):
                if fractional_index in selected_set:
                    continue
                yield tuple(
                    1.0
                    if index in selected_set
                    else fractional
                    if index == fractional_index
                    else 0.0
                    for index in range(size)
                )


def solve_enumerated(config: dict, gamma: float) -> dict:
    """Independently solve all adversarial-vertex constraints for validation."""

    ids, nominal, deviations, costs = asset_vectors(config)
    maximum_weight = float(config["max_weight"])
    target_return = float(config["target_return"])
    problem = pulp.LpProblem(f"enumerated_portfolio_gamma_{gamma:g}", pulp.LpMinimize)
    weights = {
        asset_id: pulp.LpVariable(
            f"xe_{asset_id}", lowBound=0.0, upBound=maximum_weight
        )
        for asset_id in ids
    }
    problem += pulp.lpSum(
        costs[index] * weights[asset_id] for index, asset_id in enumerate(ids)
    )
    problem += pulp.lpSum(weights.values()) == 1.0, "fully_invested"
    nominal_expression = pulp.lpSum(
        nominal[index] * weights[asset_id] for index, asset_id in enumerate(ids)
    )
    for vertex_index, vertex in enumerate(adversarial_extreme_points(len(ids), gamma)):
        loss = pulp.lpSum(
            deviations[index] * vertex[index] * weights[asset_id]
            for index, asset_id in enumerate(ids)
        )
        problem += nominal_expression - loss >= target_return, f"vertex_{vertex_index}"

    status = problem.solve(highs_solver())
    if status != pulp.LpStatusOptimal:
        raise RuntimeError(
            f"Enumerated LP failed for Gamma={gamma:g}: {pulp.LpStatus[status]}"
        )
    return {
        "weights": [float(pulp.value(weights[asset_id])) for asset_id in ids],
        "objective": float(pulp.value(problem.objective)),
    }


def budgeted_loss(exposures: Sequence[float], gamma: float) -> float:
    ordered = sorted((float(value) for value in exposures), reverse=True)
    full = min(int(math.floor(gamma + 1e-12)), len(ordered))
    fractional = max(0.0, gamma - full)
    loss = sum(ordered[:full])
    if full < len(ordered):
        loss += fractional * ordered[full]
    return loss


def wilson_interval(count: int, total: int, z_value: float = Z_975) -> list[float]:
    """Two-sided Wilson score interval, well behaved even when count is zero."""

    rate = count / total
    z_squared = z_value**2
    denominator = 1.0 + z_squared / total
    centre = (rate + z_squared / (2.0 * total)) / denominator
    half_width = (
        z_value
        * math.sqrt(
            rate * (1.0 - rate) / total + z_squared / (4.0 * total**2)
        )
        / denominator
    )
    return [max(0.0, centre - half_width), min(1.0, centre + half_width)]


def run_robust_portfolio(config: dict) -> dict:
    ids, nominal, deviations, costs = asset_vectors(config)
    target_return = float(config["target_return"])
    gammas = gamma_grid(config)
    solutions = []

    for gamma in gammas:
        counterpart = solve_counterpart(config, gamma)
        enumerated = solve_enumerated(config, gamma)
        weights = counterpart["weights"]
        nominal_return = sum(
            nominal[index] * weights[index] for index in range(len(ids))
        )
        exposures = [
            deviations[index] * weights[index] for index in range(len(ids))
        ]
        worst_case_loss = budgeted_loss(exposures, gamma)
        solutions.append(
            {
                "gamma": gamma,
                "objective": counterpart["objective"],
                "weights": dict(zip(ids, weights)),
                "nominal_return": nominal_return,
                "worst_case_loss": worst_case_loss,
                "robust_worst_case_return": nominal_return - worst_case_loss,
                "robust_margin": nominal_return - worst_case_loss - target_return,
                "counterpart": {
                    "z": counterpart["z"],
                    "p": dict(zip(ids, counterpart["p"])),
                    "represented_penalty": counterpart["counterpart_penalty"],
                },
                "enumerated_cross_check": {
                    "objective": enumerated["objective"],
                    "objective_absolute_gap": abs(
                        counterpart["objective"] - enumerated["objective"]
                    ),
                    "maximum_weight_absolute_gap": max(
                        abs(left - right)
                        for left, right in zip(weights, enumerated["weights"])
                    ),
                },
            }
        )

    baseline = solutions[0]["objective"]
    for solution in solutions:
        solution["price_of_robustness"] = (
            solution["objective"] - baseline
        ) / baseline

    rng = random.Random(int(config["simulation_seed"]))
    draws = int(config["simulation_draws"])
    violations = [0 for _ in solutions]
    outside_effective_adverse_budget = [0 for _ in solutions]
    violations_inside_effective_adverse_budget = [0 for _ in solutions]
    mean_return_stats = [OnlineStats() for _ in solutions]
    weight_rows = [
        [solution["weights"][asset_id] for asset_id in ids] for solution in solutions
    ]

    for _ in range(draws):
        shocks = [rng.uniform(-1.0, 1.0) for _ in ids]
        adverse_budget = sum(max(0.0, -shock) for shock in shocks)
        realised_asset_returns = [
            nominal[index] + deviations[index] * shocks[index]
            for index in range(len(ids))
        ]
        for solution_index, (gamma, weights) in enumerate(zip(gammas, weight_rows)):
            realised_return = sum(
                weights[index] * realised_asset_returns[index]
                for index in range(len(ids))
            )
            mean_return_stats[solution_index].add(realised_return)
            is_violation = realised_return < target_return - 1e-12
            is_outside = adverse_budget > gamma + 1e-12
            violations[solution_index] += int(is_violation)
            outside_effective_adverse_budget[solution_index] += int(is_outside)
            violations_inside_effective_adverse_budget[solution_index] += int(
                is_violation and not is_outside
            )

    for index, solution in enumerate(solutions):
        count = violations[index]
        rate = count / draws
        binomial_se = math.sqrt(rate * (1.0 - rate) / draws)
        solution["simulation"] = {
            "violation_count": count,
            "violation_rate": rate,
            "violation_rate_mc_se": binomial_se,
            "violation_rate_ci95_wilson": wilson_interval(count, draws),
            "outside_effective_adverse_budget_count": outside_effective_adverse_budget[
                index
            ],
            "outside_effective_adverse_budget_rate": outside_effective_adverse_budget[
                index
            ]
            / draws,
            "violations_inside_effective_adverse_budget": violations_inside_effective_adverse_budget[
                index
            ],
            "mean_realised_return": mean_return_stats[index].mean,
            "se_mean_realised_return": mean_return_stats[index].standard_error,
        }

    return {
        "design": {
            "assets": config["assets"],
            "target_return": target_return,
            "maximum_weight_per_asset": float(config["max_weight"]),
            "gamma_grid": gammas,
            "full_symmetric_robust_uncertainty_set": config[
                "robust_uncertainty_set"
            ],
            "effective_adverse_projection": config["effective_adverse_projection"],
            "worst_case_reduction": "For this lower-return constraint with x_i >= 0, the worst point has U_i <= 0, so q_i = -U_i and the compact loss problem is 0 <= q_i <= 1, sum(q_i) <= Gamma.",
            "exact_counterpart": "nominal_return - Gamma*z - sum(p_i) >= target; z + p_i >= deviation_i*x_i; z,p_i >= 0.",
            "objective": "Minimise the linear defensive-allocation cost of a fully invested portfolio.",
        },
        "solutions": solutions,
        "simulation_design": {
            "seed": int(config["simulation_seed"]),
            "draws": draws,
            "distribution": config["shock_distribution"],
            "common_random_numbers": True,
            "effective_adverse_budget_in_a_draw": "sum(max(0, -U_i))",
            "effective_budget_scope_note": "This is the one-sided adverse projection relevant to the lower-return constraint, not sum(abs(U_i)) for the full symmetric shock vector.",
        },
        "interpretation": {
            "robust_guarantee": "Each reported worst-case return is deterministic and covers every point in the full symmetric budgeted set. For this one-sided lower-return constraint it also covers any shock whose effective adverse projection has sum(max(0,-U_i)) <= Gamma.",
            "empirical_simulation": "Violation rates are Monte Carlo estimates under the stated iid Uniform[-1,1] sampling law, including draws outside the robust set.",
            "concentration_bound": None,
            "concentration_bound_note": "No concentration bound is computed or plotted; it would be a third, assumption-dependent object and must not be confused with either the set-wise guarantee or the empirical rate.",
        },
    }


def compact_float(value: float, digits: int = 6) -> str:
    return f"{value:.{digits}f}"


def results_as_text(results: dict) -> str:
    figure1 = results["figure1"]
    monte_carlo = figure1["monte_carlo"]
    quadrature = figure1["quadrature_check"]
    lines = [
        "ARTICLE 4 — REPRODUCIBLE RESULTS",
        "==================================",
        "",
        "FIGURE 1 — THE OPTIMIZER'S CURSE",
        f"Seed: {figure1['design']['seed']}",
        f"Alternatives: {figure1['design']['alternatives']} (true value 0 for each)",
        f"Replications: {figure1['design']['replications']}",
        (
            "Selected estimate: "
            f"{compact_float(monte_carlo['mean_selected_estimate'])} "
            f"(MC SE {compact_float(monte_carlo['se_selected_estimate'])}; "
            f"95% CI [{compact_float(monte_carlo['ci95_selected_estimate'][0])}, "
            f"{compact_float(monte_carlo['ci95_selected_estimate'][1])}])"
        ),
        (
            "Selected out-of-sample outcome: "
            f"{compact_float(monte_carlo['mean_selected_out_of_sample'])} "
            f"(MC SE {compact_float(monte_carlo['se_selected_out_of_sample'])}; "
            f"95% CI [{compact_float(monte_carlo['ci95_selected_out_of_sample'][0])}, "
            f"{compact_float(monte_carlo['ci95_selected_out_of_sample'][1])}])"
        ),
        (
            "In-sample minus out-of-sample: "
            f"{compact_float(monte_carlo['mean_disappointment'])} "
            f"(MC SE {compact_float(monte_carlo['se_disappointment'])}; "
            f"95% CI [{compact_float(monte_carlo['ci95_disappointment'][0])}, "
            f"{compact_float(monte_carlo['ci95_disappointment'][1])}])"
        ),
        (
            "Quadrature E[max of 10 N(0,1)]: "
            f"{compact_float(quadrature['expected_maximum'], 9)}"
        ),
        (
            "Monte Carlo minus quadrature: "
            f"{compact_float(quadrature['monte_carlo_minus_quadrature'])} "
            f"({compact_float(quadrature['gap_in_monte_carlo_standard_errors'], 3)} MC SE)"
        ),
        "",
        "FIGURE 2 — PRICE OF ROBUSTNESS",
        (
            "Gamma  Cost      Price     Worst return  Violation [95% MC CI]  "
            "Outside effective adverse budget  Exact-LP gap"
        ),
    ]
    for solution in results["figure2"]["solutions"]:
        simulation = solution["simulation"]
        interval = simulation["violation_rate_ci95_wilson"]
        lines.append(
            f"{solution['gamma']:>4.1f}   "
            f"{solution['objective']:.6f}  "
            f"{solution['price_of_robustness']:>7.2%}  "
            f"{solution['robust_worst_case_return']:.6f}      "
            f"{simulation['violation_rate']:>7.3%} "
            f"[{interval[0]:.3%}, {interval[1]:.3%}]  "
            f"{simulation['outside_effective_adverse_budget_rate']:>7.3%}      "
            f"{solution['enumerated_cross_check']['objective_absolute_gap']:.2e}"
        )
    lines.extend(
        [
            "",
            "Interpretation boundary:",
            "- Robust guarantee: deterministic coverage of every adverse vector inside the stated Gamma-budget set.",
            "- Empirical simulation: iid Uniform[-1,1] Monte Carlo rates; draws outside that set are allowed.",
            "- Concentration bound: none computed or plotted.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_all(model: dict) -> dict:
    return {
        "schema_version": "1.0",
        "software": {
            "python": sys.version.split()[0],
            "pulp": pulp.__version__,
            "highspy": highspy.Highs().version(),
            "lp_solver": "HiGHS through pulp.HiGHS",
            "random_number_generator": "random.Random (MT19937)",
        },
        "figure1": run_optimizer_curse(model["figure1"]),
        "figure2": run_robust_portfolio(model["figure2"]),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_model(args.model)
    results = run_all(model)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "results.json"
    text_path = args.output_dir / "results.txt"
    json_path.write_text(
        json.dumps(results, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    text_path.write_text(results_as_text(results), encoding="utf-8")
    print(f"Wrote {json_path}")
    print(f"Wrote {text_path}")


if __name__ == "__main__":
    main()
