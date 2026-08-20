#!/usr/bin/env python3
"""Create accessible static SVGs, inline HTML fragments, and a local demo page."""

from __future__ import annotations

import argparse
import html
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DEFAULT_RESULTS = ROOT / "out" / "results.json"
DEFAULT_OUTPUT_DIR = ROOT / "out"
INK = "#17232F"
MUTED = "#526475"
GRID = "#D8E0E6"
PAPER = "#FFFFFF"
TEAL = "#087F8C"
TEAL_DARK = "#075A63"
ORANGE = "#C15F1B"
ORANGE_DARK = "#7C3D12"
GREEN = "#237A57"
PANEL = "#F4F7F8"


def load_results(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def text_element(
    x: float,
    y: float,
    value: str,
    css_class: str = "label",
    anchor: str = "start",
    extra: str = "",
) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" class="{css_class}" '
        f'text-anchor="{anchor}" {extra}>{html.escape(value)}</text>'
    )


def multiline_text(
    x: float,
    y: float,
    lines: list[str],
    css_class: str = "small",
    line_height: float = 19.0,
) -> str:
    spans = []
    for index, line in enumerate(lines):
        dy = 0.0 if index == 0 else line_height
        spans.append(
            f'<tspan x="{x:.2f}" dy="{dy:.2f}">{html.escape(line)}</tspan>'
        )
    return f'<text x="{x:.2f}" y="{y:.2f}" class="{css_class}">' + "".join(spans) + "</text>"


def svg_style() -> str:
    return f"""
    <style>
      text {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: {INK}; }}
      .title {{ font-size: 24px; font-weight: 720; letter-spacing: -0.3px; }}
      .subtitle {{ font-size: 14px; fill: {MUTED}; }}
      .axis-title {{ font-size: 13px; font-weight: 650; fill: {INK}; }}
      .tick {{ font-size: 12px; fill: {MUTED}; }}
      .label {{ font-size: 13px; fill: {INK}; }}
      .small {{ font-size: 12px; fill: {MUTED}; }}
      .metric {{ font-size: 17px; font-weight: 720; fill: {INK}; }}
      .kicker {{ font-size: 11px; font-weight: 760; letter-spacing: 1.1px; fill: {MUTED}; }}
      .grid {{ stroke: {GRID}; stroke-width: 1; }}
      .axis {{ stroke: {INK}; stroke-width: 1.2; }}
    </style>
    """.strip()


def make_figure1(results: dict) -> str:
    width, height = 960, 610
    left, right, top, bottom = 76.0, 636.0, 112.0, 526.0
    x_min, x_max = -0.5, 4.0
    y_min, y_max = -4.0, 4.0

    def sx(value: float) -> float:
        return left + (value - x_min) / (x_max - x_min) * (right - left)

    def sy(value: float) -> float:
        return bottom - (value - y_min) / (y_max - y_min) * (bottom - top)

    monte_carlo = results["monte_carlo"]
    quadrature = results["quadrature_check"]
    points = results["figure_data"]["scatter_points"]
    replications = results["design"]["replications"]
    selected_mean = monte_carlo["mean_selected_estimate"]
    fresh_mean = monte_carlo["mean_selected_out_of_sample"]
    selected_half = (
        monte_carlo["ci95_selected_estimate"][1]
        - monte_carlo["ci95_selected_estimate"][0]
    ) / 2.0
    fresh_half = (
        monte_carlo["ci95_selected_out_of_sample"][1]
        - monte_carlo["ci95_selected_out_of_sample"][0]
    ) / 2.0

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            'role="img" aria-labelledby="fig1-title fig1-desc">'
        ),
        '<title id="fig1-title">Selection creates an in-sample winner that does not persist out of sample</title>',
        (
            '<desc id="fig1-desc">Scatterplot of 600 stored replications from a 200,000-replication experiment. '
            'The horizontal axis is the largest of ten independent standard-normal estimates and the vertical '
            'axis is an independent outcome for the selected alternative. The cloud is centred near 1.54 '
            'horizontally and zero vertically. A side panel reports Monte Carlo confidence intervals and the '
            'quadrature value for the expected maximum.</desc>'
        ),
        svg_style(),
        '<defs><clipPath id="fig1-clip"><rect x="76" y="112" width="560" height="414"/></clipPath></defs>',
        f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
        text_element(48, 43, "The optimiser’s curse, in one controlled experiment", "title"),
        text_element(
            48,
            69,
            "Ten alternatives are equally good. Selection acts only on noisy estimates.",
            "subtitle",
        ),
    ]

    for tick in [-4, -2, 0, 2, 4]:
        y = sy(float(tick))
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" class="grid"/>')
        parts.append(text_element(left - 11, y + 4, f"{tick:g}", "tick", "end"))
    for tick in [0, 1, 2, 3, 4]:
        x = sx(float(tick))
        parts.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" class="grid"/>')
        parts.append(text_element(x, bottom + 23, f"{tick:g}", "tick", "middle"))

    parts.extend(
        [
            f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{bottom}" class="axis"/>',
            f'<line x1="{left}" y1="{top}" x2="{left}" y2="{bottom}" class="axis"/>',
            text_element((left + right) / 2.0, 578, "Selected in-sample estimate", "axis-title", "middle"),
            text_element(
                20,
                (top + bottom) / 2.0,
                "Fresh out-of-sample outcome",
                "axis-title",
                "middle",
                f'transform="rotate(-90 20 {(top + bottom) / 2.0:.2f})"',
            ),
            '<g clip-path="url(#fig1-clip)">',
            (
                f'<line x1="{sx(x_min):.2f}" y1="{sy(x_min):.2f}" '
                f'x2="{sx(x_max):.2f}" y2="{sy(x_max):.2f}" '
                f'stroke="{MUTED}" stroke-width="1.5" stroke-dasharray="6 5" opacity="0.8"/>'
            ),
            (
                f'<line x1="{sx(quadrature["expected_maximum"]):.2f}" y1="{top}" '
                f'x2="{sx(quadrature["expected_maximum"]):.2f}" y2="{bottom}" '
                f'stroke="{GREEN}" stroke-width="2" stroke-dasharray="3 4"/>'
            ),
        ]
    )
    for selected, fresh, _selected_index in points:
        parts.append(
            f'<circle cx="{sx(float(selected)):.2f}" cy="{sy(float(fresh)):.2f}" r="2.8" '
            f'fill="{TEAL}" fill-opacity="0.25"/>'
        )
    mean_x = sx(selected_mean)
    mean_y = sy(fresh_mean)
    parts.extend(
        [
            "</g>",
            (
                f'<path d="M {mean_x:.2f} {mean_y - 8:.2f} L {mean_x + 8:.2f} {mean_y:.2f} '
                f'L {mean_x:.2f} {mean_y + 8:.2f} L {mean_x - 8:.2f} {mean_y:.2f} Z" '
                f'fill="{ORANGE}" stroke="{PAPER}" stroke-width="2"/>'
            ),
            text_element(sx(3.92), sy(3.92) + 14, "equal in and out", "small", "end"),
            text_element(
                sx(quadrature["expected_maximum"]) + 6,
                top + 18,
                "theory E[max]",
                "small",
            ),
            f'<rect x="666" y="112" width="252" height="414" rx="14" fill="{PANEL}"/>',
            text_element(690, 143, "RESULT", "kicker"),
            text_element(690, 174, f"{replications:,} repetitions", "metric"),
            text_element(690, 207, "Selected estimate", "label"),
            text_element(690, 232, f"{selected_mean:.3f} ± {selected_half:.3f}", "metric"),
            text_element(690, 251, "mean ± 95% MC half-width", "small"),
            text_element(690, 291, "Fresh outcome", "label"),
            text_element(690, 316, f"{fresh_mean:.3f} ± {fresh_half:.3f}", "metric"),
            text_element(690, 335, "mean ± 95% MC half-width", "small"),
            text_element(690, 375, "Independent quadrature", "label"),
            text_element(
                690,
                400,
                f"E[max] = {quadrature['expected_maximum']:.6f}",
                "metric",
            ),
            text_element(
                690,
                427,
                f"MC gap = {quadrature['gap_in_monte_carlo_standard_errors']:.2f} SE",
                "small",
            ),
            f'<line x1="690" y1="456" x2="894" y2="456" stroke="{GRID}"/>',
            multiline_text(
                690,
                480,
                ["Orange diamond: joint mean", "Dots: first 600 stored trials"],
            ),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def make_figure2(results: dict) -> str:
    width, height = 960, 700
    left, right = 76.0, 684.0
    top_a, bottom_a = 118.0, 319.0
    top_b, bottom_b = 402.0, 612.0
    solutions = results["solutions"]
    gamma_max = max(float(solution["gamma"]) for solution in solutions)
    price_max = max(float(solution["price_of_robustness"]) for solution in solutions)
    price_axis_max = max(0.1, math.ceil(price_max * 10.0) / 10.0)
    violation_axis_max = 0.12

    def sx(value: float) -> float:
        return left + value / gamma_max * (right - left)

    def sy_price(value: float) -> float:
        return bottom_a - value / price_axis_max * (bottom_a - top_a)

    def sy_violation(value: float) -> float:
        return bottom_b - value / violation_axis_max * (bottom_b - top_b)

    price_points = " ".join(
        f"{sx(float(solution['gamma'])):.2f},{sy_price(float(solution['price_of_robustness'])):.2f}"
        for solution in solutions
    )
    violation_points = " ".join(
        f"{sx(float(solution['gamma'])):.2f},{sy_violation(float(solution['simulation']['violation_rate'])):.2f}"
        for solution in solutions
    )
    draws = int(results["simulation_design"]["draws"])
    target = float(results["design"]["target_return"])
    final_price = float(solutions[-1]["price_of_robustness"])

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" '
            'role="img" aria-labelledby="fig2-title fig2-desc">'
        ),
        '<title id="fig2-title">Higher robustness budgets cost more and reduce empirical violations</title>',
        (
            '<desc id="fig2-desc">Two line charts over Gamma from zero to six. The upper chart shows '
            'the defensive allocation cost rising by 59.46 percent. The lower chart shows an empirical '
            'violation rate falling from 10.33 percent to zero in 150,000 uniform-shock simulations. '
            'A side panel states separately the deterministic robust guarantee, the empirical sampling '
            'statement, and that no concentration bound is shown.</desc>'
        ),
        svg_style(),
        f'<rect width="{width}" height="{height}" fill="{PAPER}"/>',
        text_element(48, 43, "The price of robustness is a curve, not a slogan", "title"),
        text_element(
            48,
            69,
            "A six-asset linear portfolio; Γ admits half-unit protection budgets.",
            "subtitle",
        ),
        text_element(left, 101, "DEFENSIVE COST ABOVE Γ = 0", "kicker"),
        text_element(left, 385, "EMPIRICAL RETURN-CONSTRAINT VIOLATIONS", "kicker"),
    ]

    for fraction in [0.0, 0.2, 0.4, 0.6]:
        if fraction > price_axis_max + 1e-12:
            continue
        y = sy_price(fraction)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" class="grid"/>')
        parts.append(text_element(left - 11, y + 4, f"{fraction:.0%}", "tick", "end"))
    for fraction in [0.0, 0.03, 0.06, 0.09, 0.12]:
        y = sy_violation(fraction)
        parts.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" class="grid"/>')
        parts.append(text_element(left - 11, y + 4, f"{fraction:.0%}", "tick", "end"))
    for gamma in range(int(gamma_max) + 1):
        x = sx(float(gamma))
        parts.extend(
            [
                f'<line x1="{x:.2f}" y1="{top_a}" x2="{x:.2f}" y2="{bottom_a}" class="grid"/>',
                f'<line x1="{x:.2f}" y1="{top_b}" x2="{x:.2f}" y2="{bottom_b}" class="grid"/>',
                text_element(x, bottom_b + 24, str(gamma), "tick", "middle"),
            ]
        )

    parts.extend(
        [
            f'<line x1="{left}" y1="{bottom_a}" x2="{right}" y2="{bottom_a}" class="axis"/>',
            f'<line x1="{left}" y1="{top_a}" x2="{left}" y2="{bottom_a}" class="axis"/>',
            f'<line x1="{left}" y1="{bottom_b}" x2="{right}" y2="{bottom_b}" class="axis"/>',
            f'<line x1="{left}" y1="{top_b}" x2="{left}" y2="{bottom_b}" class="axis"/>',
            f'<polyline points="{price_points}" fill="none" stroke="{ORANGE}" stroke-width="3" stroke-linejoin="round"/>',
            f'<polyline points="{violation_points}" fill="none" stroke="{TEAL}" stroke-width="3" stroke-linejoin="round"/>',
        ]
    )

    for solution in solutions:
        gamma = float(solution["gamma"])
        x = sx(gamma)
        price_y = sy_price(float(solution["price_of_robustness"]))
        simulation = solution["simulation"]
        violation_y = sy_violation(float(simulation["violation_rate"]))
        interval = simulation["violation_rate_ci95_wilson"]
        upper_y = sy_violation(min(interval[1], violation_axis_max))
        lower_y = sy_violation(max(interval[0], 0.0))
        parts.extend(
            [
                f'<circle cx="{x:.2f}" cy="{price_y:.2f}" r="4.5" fill="{PAPER}" stroke="{ORANGE_DARK}" stroke-width="2"/>',
                f'<line x1="{x:.2f}" y1="{upper_y:.2f}" x2="{x:.2f}" y2="{lower_y:.2f}" stroke="{TEAL_DARK}" stroke-width="1.2"/>',
                f'<line x1="{x - 4:.2f}" y1="{upper_y:.2f}" x2="{x + 4:.2f}" y2="{upper_y:.2f}" stroke="{TEAL_DARK}" stroke-width="1.2"/>',
                f'<line x1="{x - 4:.2f}" y1="{lower_y:.2f}" x2="{x + 4:.2f}" y2="{lower_y:.2f}" stroke="{TEAL_DARK}" stroke-width="1.2"/>',
                f'<rect x="{x - 4:.2f}" y="{violation_y - 4:.2f}" width="8" height="8" fill="{TEAL}" stroke="{PAPER}" stroke-width="1"/>',
            ]
        )

    parts.extend(
        [
            text_element((left + right) / 2.0, 665, "Robustness budget Γ", "axis-title", "middle"),
            text_element(
                left + 8,
                top_a + 20,
                f"Cost reaches +{final_price:.1%}",
                "label",
            ),
            text_element(
                left + 8,
                top_b + 20,
                "Squares: empirical rates; bars: 95% Wilson MC intervals",
                "small",
            ),
            f'<rect x="716" y="108" width="214" height="504" rx="14" fill="{PANEL}"/>',
            text_element(738, 139, "ROBUST GUARANTEE", "kicker"),
            multiline_text(
                738,
                165,
                [
                    "For every Γ, the exact LP",
                    f"keeps worst-case return ≥ {target:.1%}",
                    "inside that Γ-budget set.",
                ],
                "small",
            ),
            f'<line x1="738" y1="228" x2="906" y2="228" stroke="{GRID}"/>',
            text_element(738, 257, "EMPIRICAL SIMULATION", "kicker"),
            multiline_text(
                738,
                283,
                [
                    f"{draws:,} common iid draws",
                    "from Uniform[−1, 1]. Draws",
                    "outside the robust set remain",
                    "in the empirical rate.",
                ],
                "small",
            ),
            f'<line x1="738" y1="365" x2="906" y2="365" stroke="{GRID}"/>',
            text_element(738, 394, "CONCENTRATION BOUND", "kicker"),
            multiline_text(
                738,
                420,
                [
                    "None is computed or plotted.",
                    "Such a bound would be a third,",
                    "assumption-dependent object.",
                ],
                "small",
            ),
            f'<line x1="738" y1="486" x2="906" y2="486" stroke="{GRID}"/>',
            text_element(738, 515, "ENDPOINTS", "kicker"),
            text_element(
                738,
                543,
                f"Violation: {solutions[0]['simulation']['violation_rate']:.2%} → {solutions[-1]['simulation']['violation_rate']:.2%}",
                "label",
            ),
            text_element(738, 570, f"Cost: 0% → +{final_price:.2%}", "label"),
            "</svg>",
        ]
    )
    return "\n".join(parts)


def html_fragment(svg: str, figure_number: int, caption: str, css_suffix: str) -> str:
    return f"""<figure class="fig fig-wide sn-repro-figure sn-repro-figure--{css_suffix}" id="figure-{figure_number}">
  <style>
    .sn-repro-figure {{ margin: 2.25rem auto; max-width: 60rem; color: var(--ink, #17232f); }}
    .sn-repro-scroll {{ overflow-x: visible; }}
    .sn-repro-mobile-hint {{ display: none; }}
    .sn-repro-figure svg {{ display: block; width: 100%; height: auto; background: #fff; border: 1px solid var(--rule, #d8e0e6); border-radius: 0.8rem; }}
    .sn-repro-figure figcaption {{ margin: 0.8rem 0.2rem 0; font: 0.94rem/1.55 ui-sans-serif, system-ui, sans-serif; color: var(--muted, #526475); }}
    .sn-repro-figure figcaption strong {{ color: var(--ink, #17232f); }}
    @media (max-width: 640px) {{
      .sn-repro-scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
      .sn-repro-scroll svg {{ min-width: 700px; }}
      .sn-repro-mobile-hint {{ display: block; margin: 0.45rem 0.2rem 0; color: var(--muted, #526475); font: 0.72rem/1.4 ui-monospace, monospace; letter-spacing: 0.02em; }}
    }}
  </style>
  <div class="sn-repro-scroll">
{svg}
  </div>
  <span class="sn-repro-mobile-hint">Swipe horizontally to inspect the full chart →</span>
  <figcaption><strong>Figure {figure_number}.</strong> {html.escape(caption)}</figcaption>
</figure>
"""


def demo_page(fragment1: str, fragment2: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Article 4 — reproducible figure preview</title>
  <style>
    :root {{ color-scheme: light; background: #eef2f4; color: #17232f; }}
    body {{ margin: 0; font-family: ui-sans-serif, system-ui, sans-serif; }}
    main {{ width: min(68rem, calc(100% - 2rem)); margin: 3rem auto 5rem; }}
    header {{ max-width: 60rem; margin: 0 auto 2.5rem; }}
    h1 {{ margin: 0 0 0.7rem; font-size: clamp(2rem, 5vw, 3.3rem); letter-spacing: -0.04em; }}
    header p {{ color: #526475; font-size: 1.08rem; line-height: 1.6; max-width: 48rem; }}
    code {{ background: #e1e8eb; border-radius: 0.2rem; padding: 0.1rem 0.3rem; }}
  </style>
</head>
<body>
<main>
  <header>
    <p>OPTIMISATION PRIMER · ARTICLE 4</p>
    <h1>Optimising against a guess</h1>
    <p>Static, accessible previews generated solely from <code>out/results.json</code>. The numerical claims are checked by <code>verify_results.py</code>.</p>
  </header>
{fragment1.rstrip()}
{fragment2.rstrip()}
</main>
</body>
</html>
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=DEFAULT_RESULTS)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--demo", type=Path, default=ROOT / "demo.html")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    results = load_results(args.results)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    figure1_svg = make_figure1(results["figure1"])
    figure2_svg = make_figure2(results["figure2"])
    figure1_caption = (
        "All ten alternatives have true value zero. Selection lifts the in-sample mean to "
        f"{results['figure1']['monte_carlo']['mean_selected_estimate']:.3f}, while an independent "
        f"out-of-sample outcome remains centred near zero. Error ranges are Monte Carlo intervals."
    )
    figure2_caption = (
        "The orange series is the optimisation cost relative to Γ = 0; the teal series is an "
        "empirical violation rate under the stated iid Uniform[−1, 1] law. The robust guarantee "
        "applies deterministically inside each Γ-budget set. No concentration bound is shown."
    )
    fragment1 = html_fragment(figure1_svg, 1, figure1_caption, "optimizer-curse")
    fragment2 = html_fragment(figure2_svg, 2, figure2_caption, "price-of-robustness")

    outputs = {
        args.output_dir / "fig1-optimizer-curse.svg": figure1_svg + "\n",
        args.output_dir / "fig1-optimizer-curse.html": fragment1,
        args.output_dir / "fig2-price-of-robustness.svg": figure2_svg + "\n",
        args.output_dir / "fig2-price-of-robustness.html": fragment2,
        args.demo: demo_page(fragment1, fragment2),
    }
    for path, content in outputs.items():
        path.write_text(content, encoding="utf-8")
        print(f"Wrote {path}")


if __name__ == "__main__":
    main()
