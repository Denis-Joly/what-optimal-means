#!/usr/bin/env python3
"""Verify the numerical and scientific invariants of the article 4 results."""

from __future__ import annotations

import argparse
import json
import math
import xml.etree.ElementTree as ET
from pathlib import Path

import highspy
import pulp


ROOT = Path(__file__).resolve().parent
DEFAULT_MODEL = ROOT / "data" / "model.json"
DEFAULT_RESULTS = ROOT / "out" / "results.json"
Z_975 = 1.959963984540054


class Verifier:
    def __init__(self) -> None:
        self.check_count = 0
        self.failures: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        self.check_count += 1
        if not condition:
            self.failures.append(message)

    def close(self) -> None:
        if self.failures:
            print(f"FAIL ({len(self.failures)} of {self.check_count} checks failed)")
            for failure in self.failures:
                print(f"- {failure}")
            raise SystemExit(1)
        print(f"PASS ({self.check_count} checks)")
        print("- Figure 1 Monte Carlo agrees with independent quadrature.")
        print("- Figure 2 satisfies every robust constraint and exact-LP cross-check.")
        print("- No simulated violation occurs inside its declared robust set.")
        print("- Guarantee, empirical simulation, and absent concentration bound remain distinct.")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def independent_expected_maximum(alternatives: int) -> float:
    """Composite Simpson check using the order-statistic density.

    This deliberately uses a different identity and quadrature rule from
    run_experiments.py:
      E[max Z_i] = integral n*x*phi(x)*Phi(x)^(n-1) dx.
    """

    lower = -9.0
    upper = 9.0
    panels = 200_000
    step = (upper - lower) / panels

    def integrand(value: float) -> float:
        density = math.exp(-(value**2) / 2.0) / math.sqrt(2.0 * math.pi)
        cdf = 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))
        return alternatives * value * density * cdf ** (alternatives - 1)

    weighted_sum = integrand(lower) + integrand(upper)
    for index in range(1, panels):
        weight = 4.0 if index % 2 else 2.0
        weighted_sum += weight * integrand(lower + index * step)
    return weighted_sum * step / 3.0


def analytic_budgeted_loss(exposures: list[float], gamma: float) -> float:
    ordered = sorted(exposures, reverse=True)
    full = min(int(math.floor(gamma + 1e-12)), len(ordered))
    fractional = max(0.0, gamma - full)
    value = sum(ordered[:full])
    if full < len(ordered):
        value += fractional * ordered[full]
    return value


def wilson_interval(count: int, total: int) -> list[float]:
    rate = count / total
    z_squared = Z_975**2
    denominator = 1.0 + z_squared / total
    centre = (rate + z_squared / (2.0 * total)) / denominator
    half_width = (
        Z_975
        * math.sqrt(
            rate * (1.0 - rate) / total + z_squared / (4.0 * total**2)
        )
        / denominator
    )
    return [centre - half_width, centre + half_width]


def verify_figure1(verifier: Verifier, model: dict, results: dict) -> None:
    config = model["figure1"]
    design = results["design"]
    monte_carlo = results["monte_carlo"]
    quadrature = results["quadrature_check"]
    alternatives = int(config["alternatives"])
    replications = int(config["replications"])

    verifier.check(design["seed"] == 20260820, "Figure 1 seed changed")
    verifier.check(
        float(config["true_value"]) == 0.0,
        "Figure 1 true value changed although the check targets standard normals",
    )
    verifier.check(
        float(config["estimation_sd"]) == 1.0
        and float(config["out_of_sample_sd"]) == 1.0,
        "Figure 1 standard deviations changed although quadrature targets N(0,1)",
    )
    verifier.check(replications >= 100_000, "Figure 1 has fewer than 100,000 replications")
    verifier.check(
        design["replications"] == replications,
        "Figure 1 result count does not match model.json",
    )
    verifier.check(
        sum(monte_carlo["selection_counts"]) == replications,
        "Figure 1 selection counts do not sum to the replication count",
    )
    verifier.check(
        len(monte_carlo["selection_counts"]) == alternatives,
        "Figure 1 selection-count dimension is wrong",
    )
    verifier.check(
        len(results["figure_data"]["scatter_points"])
        == int(config["scatter_sample_size"]),
        "Figure 1 stored scatter sample has the wrong size",
    )

    independent = independent_expected_maximum(alternatives)
    reported = float(quadrature["expected_maximum"])
    verifier.check(
        abs(independent - reported) < 2e-9,
        f"Two quadrature identities disagree: {independent:.12g} vs {reported:.12g}",
    )
    verifier.check(
        abs(reported - 1.53875273083517) < 2e-9,
        "The n=10 expected maximum misses its high-precision reference",
    )
    verifier.check(
        abs(monte_carlo["mean_selected_estimate"] - reported)
        <= 4.0 * monte_carlo["se_selected_estimate"],
        "Selected-estimate Monte Carlo mean is more than four MC SE from quadrature",
    )
    verifier.check(
        abs(monte_carlo["mean_selected_out_of_sample"])
        <= 4.0 * monte_carlo["se_selected_out_of_sample"],
        "Independent out-of-sample mean is more than four MC SE from zero",
    )
    verifier.check(
        abs(monte_carlo["mean_disappointment"] - reported)
        <= 4.0 * monte_carlo["se_disappointment"],
        "Mean in-sample/out-of-sample gap is more than four MC SE from theory",
    )
    verifier.check(
        monte_carlo["ci95_selected_out_of_sample"][0]
        <= 0.0
        <= monte_carlo["ci95_selected_out_of_sample"][1],
        "The fresh-outcome 95% interval does not cover its true mean zero",
    )
    verifier.check(
        quadrature["omitted_tail_upper_bound"] < 1e-20,
        "The quadrature truncation tail is too large",
    )


def verify_figure2(verifier: Verifier, model: dict, results: dict) -> None:
    config = model["figure2"]
    assets = config["assets"]
    asset_ids = [asset["id"] for asset in assets]
    nominal = [float(asset["nominal_return"]) for asset in assets]
    deviations = [float(asset["max_deviation"]) for asset in assets]
    costs = [float(asset["defensive_cost"]) for asset in assets]
    target = float(config["target_return"])
    maximum_weight = float(config["max_weight"])
    draws = int(config["simulation_draws"])
    expected_gammas = [index / 2.0 for index in range(2 * len(assets) + 1)]
    solutions = results["solutions"]

    verifier.check(
        [solution["gamma"] for solution in solutions] == expected_gammas,
        "Gamma grid is not 0, 0.5, ..., n",
    )
    verifier.check(bool(pulp.HiGHS(msg=False).available()), "PuLP cannot access HiGHS")
    verifier.check(
        results["simulation_design"]["distribution"] == "iid Uniform[-1, 1]",
        "Simulation law is not explicitly iid Uniform[-1,1]",
    )
    verifier.check(
        results["interpretation"]["concentration_bound"] is None,
        "A concentration bound appeared without a specified theorem",
    )

    previous_objective = -math.inf
    baseline = float(solutions[0]["objective"])
    for solution in solutions:
        gamma = float(solution["gamma"])
        weights = [float(solution["weights"][asset_id]) for asset_id in asset_ids]
        exposures = [deviations[index] * weights[index] for index in range(len(assets))]
        objective = sum(costs[index] * weights[index] for index in range(len(assets)))
        nominal_return = sum(
            nominal[index] * weights[index] for index in range(len(assets))
        )
        loss = analytic_budgeted_loss(exposures, gamma)
        simulation = solution["simulation"]
        expected_interval = wilson_interval(simulation["violation_count"], draws)

        verifier.check(
            abs(sum(weights) - 1.0) < 2e-8,
            f"Gamma={gamma:g}: weights do not sum to one",
        )
        verifier.check(
            all(-1e-9 <= weight <= maximum_weight + 1e-9 for weight in weights),
            f"Gamma={gamma:g}: a weight violates its bounds",
        )
        verifier.check(
            abs(objective - solution["objective"]) < 2e-9,
            f"Gamma={gamma:g}: objective is inconsistent with weights",
        )
        verifier.check(
            abs(nominal_return - solution["nominal_return"]) < 2e-9,
            f"Gamma={gamma:g}: nominal return is inconsistent with weights",
        )
        verifier.check(
            abs(loss - solution["worst_case_loss"]) < 2e-9,
            f"Gamma={gamma:g}: analytic budgeted loss is inconsistent",
        )
        verifier.check(
            abs(loss - solution["counterpart"]["represented_penalty"]) < 2e-8,
            f"Gamma={gamma:g}: z/p_i do not represent the exact worst loss",
        )
        verifier.check(
            nominal_return - loss >= target - 2e-8,
            f"Gamma={gamma:g}: deterministic robust guarantee fails",
        )
        verifier.check(
            solution["enumerated_cross_check"]["objective_absolute_gap"] < 2e-8,
            f"Gamma={gamma:g}: compact and enumerated LP objectives disagree",
        )
        verifier.check(
            solution["enumerated_cross_check"]["maximum_weight_absolute_gap"] < 2e-7,
            f"Gamma={gamma:g}: compact and enumerated LP weights disagree",
        )
        verifier.check(
            objective >= previous_objective - 2e-8,
            f"Gamma={gamma:g}: price decreases although uncertainty sets are nested",
        )
        verifier.check(
            abs(solution["price_of_robustness"] - (objective - baseline) / baseline)
            < 2e-9,
            f"Gamma={gamma:g}: price of robustness is miscomputed",
        )
        verifier.check(
            simulation["violation_count"]
            <= simulation["outside_effective_adverse_budget_count"],
            f"Gamma={gamma:g}: more violations than draws outside the effective adverse budget",
        )
        verifier.check(
            simulation["violations_inside_effective_adverse_budget"] == 0,
            f"Gamma={gamma:g}: a simulated point inside the effective adverse budget violates the guarantee",
        )
        verifier.check(
            all(
                abs(left - right) < 2e-12
                for left, right in zip(
                    simulation["violation_rate_ci95_wilson"], expected_interval
                )
            ),
            f"Gamma={gamma:g}: Wilson interval is inconsistent with counts",
        )
        verifier.check(
            abs(simulation["mean_realised_return"] - nominal_return)
            <= 5.0 * simulation["se_mean_realised_return"],
            f"Gamma={gamma:g}: simulated mean return is implausible under centred shocks",
        )
        previous_objective = objective


def verify_generated_assets(verifier: Verifier) -> None:
    output_dir = ROOT / "out"
    svg_paths = [
        output_dir / "fig1-optimizer-curse.svg",
        output_dir / "fig2-price-of-robustness.svg",
    ]
    fragment_paths = [
        output_dir / "fig1-optimizer-curse.html",
        output_dir / "fig2-price-of-robustness.html",
    ]
    required_paths = [
        ROOT / "README.md",
        ROOT / "data" / "model.json",
        ROOT / "requirements.txt",
        ROOT / "run_experiments.py",
        ROOT / "verify_results.py",
        ROOT / "make_figures.py",
        ROOT / "demo.html",
        output_dir / "results.json",
        output_dir / "results.txt",
        *svg_paths,
        *fragment_paths,
    ]
    for path in required_paths:
        verifier.check(path.is_file() and path.stat().st_size > 0, f"Missing or empty file: {path.name}")

    namespace = {"svg": "http://www.w3.org/2000/svg"}
    for path in svg_paths:
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as error:
            verifier.check(False, f"Invalid SVG {path.name}: {error}")
            continue
        verifier.check(root.tag.endswith("svg"), f"{path.name} has no SVG root")
        verifier.check(root.attrib.get("role") == "img", f"{path.name} lacks role=img")
        verifier.check(
            bool(root.attrib.get("aria-labelledby")),
            f"{path.name} lacks aria-labelledby",
        )
        verifier.check(
            root.find("svg:title", namespace) is not None,
            f"{path.name} lacks an accessible title",
        )
        verifier.check(
            root.find("svg:desc", namespace) is not None,
            f"{path.name} lacks an accessible description",
        )

    for path in fragment_paths:
        source = path.read_text(encoding="utf-8")
        verifier.check(
            source.count("<figure ") == 1 and source.count("</figure>") == 1,
            f"{path.name} does not contain exactly one figure wrapper",
        )
        verifier.check(
            'class="fig fig-wide sn-repro-figure ' in source,
            f"{path.name} lacks the article figure classes",
        )
        verifier.check("<svg " in source, f"{path.name} does not inline its SVG")
        verifier.check(
            '<div class="sn-repro-scroll">' in source,
            f"{path.name} lacks its mobile scroll wrapper",
        )
        verifier.check("<figcaption>" in source, f"{path.name} lacks a caption")
        verifier.check("<script" not in source.lower(), f"{path.name} is not static")
        verifier.check(
            "var(--ink," in source and "var(--muted," in source,
            f"{path.name} caption colours do not inherit the site's dark-mode variables",
        )
        verifier.check(
            "min-width: 700px" in source and "overflow-x: auto" in source,
            f"{path.name} does not preserve readable labels on narrow screens",
        )

    demo = (ROOT / "demo.html").read_text(encoding="utf-8")
    verifier.check(demo.count("<figure ") == 2, "demo.html does not contain both figures")
    verifier.check(
        demo.count('role="img"') == 2,
        "demo.html does not expose both inline SVGs as images",
    )
    text_result = (output_dir / "results.txt").read_text(encoding="utf-8")
    verifier.check(
        "Outside effective adverse budget" in text_result,
        "results.txt ambiguously labels the effective adverse projection",
    )
    verifier.check(
        "Concentration bound: none computed or plotted." in text_result,
        "results.txt does not distinguish the absent concentration bound",
    )
    raw_result = (output_dir / "results.json").read_text(encoding="utf-8")
    verifier.check(
        "outside_robust_budget" not in raw_result,
        "results.json retains the ambiguous old outside-budget key",
    )
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    verifier.check("/Users/" not in readme, "README.md contains a machine-specific path")
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
    verifier.check(
        requirements == ["pulp==3.3.2", "highspy==1.15.1"],
        "requirements.txt does not exactly pin the tested LP runtime",
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    model = load_json(args.model)
    results = load_json(args.results)
    verifier = Verifier()
    verifier.check(results["schema_version"] == "1.0", "Unknown result schema")
    verifier.check(
        results["software"]["lp_solver"] == "HiGHS through pulp.HiGHS",
        "Results do not identify the HiGHS solver path",
    )
    verifier.check(
        results["software"]["pulp"] == pulp.__version__ == "3.3.2",
        "PuLP runtime or recorded version does not match requirements.txt",
    )
    verifier.check(
        results["software"]["highspy"] == highspy.Highs().version() == "1.15.1",
        "highspy runtime or recorded version does not match requirements.txt",
    )
    verify_figure1(verifier, model, results["figure1"])
    verify_figure2(verifier, model, results["figure2"])
    verify_generated_assets(verifier)
    verifier.close()


if __name__ == "__main__":
    main()
