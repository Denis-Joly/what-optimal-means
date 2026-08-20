#!/usr/bin/env python3
"""Generate Post 3's SVG fallbacks, interactive fragments and local demo."""

from __future__ import annotations

import html
import json
from fractions import Fraction

from branch_and_bound import snapshot_as_json, trace
from example import (
    HERE,
    OUT,
    Point,
    format_fraction,
    integer_feasible_points,
    load_model,
    nearest_feasible_integer,
    nearest_integer,
    objective,
    relaxation_vertices,
    solve_integer_exact,
    solve_relaxation,
)


WIDTH = 748


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_start(height: int, prefix: str, title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="100%" role="img" aria-labelledby="{prefix}-title {prefix}-desc">',
        f'<title id="{prefix}-title">{esc(title)}</title>',
        f'<desc id="{prefix}-desc">{esc(desc)}</desc>',
        "<style>",
        'text{font-family:"Plex Mono",ui-monospace,monospace;fill:var(--viz-ink,#0a0a0a);font-size:12px}',
        '.headline{font-family:"Archivo",Helvetica,Arial,sans-serif;font-size:24px;font-weight:700;letter-spacing:-.5px}',
        '.section{font-family:"Archivo",Helvetica,Arial,sans-serif;font-size:16px;font-weight:700}',
        '.small,.source{fill:var(--viz-muted,#676762);font-size:10.5px}',
        '.value{font-family:"Archivo",Helvetica,Arial,sans-serif;font-size:18px;font-weight:700}',
        '.signal{fill:var(--viz-signal,#d6001c)}.good{fill:var(--viz-good,#087f5b)}.muted{fill:var(--viz-muted,#676762)}',
        '.paper{fill:var(--viz-paper,#fff)}.panel{fill:var(--viz-panel,#f2f2f0)}.grid{stroke:var(--viz-rule,#dcdcda)}.axis{stroke:var(--viz-ink,#0a0a0a)}',
        "</style>",
        f'<rect class="paper" width="{WIDTH}" height="{height}"/>',
    ]


def chart_coordinates(point: Point) -> tuple[float, float]:
    left, top, chart_w, chart_h = 48.0, 116.0, 422.0, 378.0
    return left + chart_w * float(point.x1) / 6.5, top + chart_h * (1 - float(point.x2) / 6.0)


def polygon_path(points: list[Point]) -> str:
    coords = [chart_coordinates(point) for point in points]
    return "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in coords) + " Z"


def rounding_svg() -> str:
    model = load_model()
    vertices = relaxation_vertices(model)
    lp_point, lp_value = solve_relaxation(model)  # type: ignore[misc]
    rounded = nearest_integer(lp_point)
    nearest = nearest_feasible_integer(model, lp_point)
    integer_point, integer_value = solve_integer_exact(model)
    height = 620
    out = svg_start(
        height,
        "fig1-rounding",
        "Rounding the linear-programming relaxation fails",
        "The LP relaxation allows fractional decisions and reaches 2.25, 3.75. Rounding to 2, 4 violates the second constraint. The nearest feasible integer is 2, 3, while the integer optimum is elsewhere at 0, 5.",
    )
    out += [
        '<text class="headline" x="24" y="38">The nearest integer is illegal. The best integer is elsewhere.</text>',
        '<text class="small" x="24" y="63">LP relaxation = the same model after temporarily allowing fractional x₁ and x₂</text>',
        '<rect class="panel" x="24" y="88" width="470" height="438" rx="3"/>',
    ]

    # Axes and integer lattice.
    for tick in range(7):
        x, _ = chart_coordinates(Point(Fraction(tick), Fraction(0)))
        out += [
            f'<line class="grid" x1="{x:.1f}" y1="116" x2="{x:.1f}" y2="494"/>',
            f'<text class="small" x="{x:.1f}" y="513" text-anchor="middle">{tick}</text>',
        ]
    for tick in range(7):
        _, y = chart_coordinates(Point(Fraction(0), Fraction(tick)))
        out += [
            f'<line class="grid" x1="48" y1="{y:.1f}" x2="470" y2="{y:.1f}"/>',
            f'<text class="small" x="37" y="{y + 4:.1f}" text-anchor="end">{tick}</text>',
        ]
    out += [
        f'<path d="{polygon_path(vertices)}" fill="var(--viz-region,#d8d8d3)" stroke="var(--viz-muted,#5c5c56)" stroke-width="1.5"/>',
        '<text class="small" x="70" y="476">LP-feasible region</text>',
        '<text x="466" y="518" text-anchor="end">x₁</text>',
        '<text x="31" y="108">x₂</text>',
    ]
    for point in integer_feasible_points(model):
        x, y = chart_coordinates(point)
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="var(--viz-muted,#5c5c56)"/>')

    # LP point and failed rounding, including a dashed movement arrow.
    lp_x, lp_y = chart_coordinates(lp_point)
    rounded_x, rounded_y = chart_coordinates(rounded)
    nearest_x, nearest_y = chart_coordinates(nearest)
    integer_x, integer_y = chart_coordinates(integer_point)
    out += [
        '<defs><marker id="rounding-arrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><path d="M0,0 L0,7 L7,3.5 Z" fill="var(--viz-signal,#d6001c)"/></marker></defs>',
        f'<line x1="{lp_x:.1f}" y1="{lp_y:.1f}" x2="{rounded_x:.1f}" y2="{rounded_y:.1f}" stroke="var(--viz-signal,#d6001c)" stroke-width="1.5" stroke-dasharray="4 3" marker-end="url(#rounding-arrow)"/>',
        f'<circle cx="{lp_x:.1f}" cy="{lp_y:.1f}" r="8" fill="var(--viz-paper,#fff)" stroke="var(--viz-ink,#0a0a0a)" stroke-width="2.5"/>',
        f'<text x="{lp_x + 11:.1f}" y="{lp_y + 22:.1f}">LP · (2.25, 3.75)</text>',
        f'<circle cx="{rounded_x:.1f}" cy="{rounded_y:.1f}" r="9" fill="var(--viz-paper,#fff)" stroke="var(--viz-signal,#d6001c)" stroke-width="3"/>',
        f'<path d="M {rounded_x - 4:.1f} {rounded_y - 4:.1f} L {rounded_x + 4:.1f} {rounded_y + 4:.1f} M {rounded_x + 4:.1f} {rounded_y - 4:.1f} L {rounded_x - 4:.1f} {rounded_y + 4:.1f}" stroke="var(--viz-signal,#d6001c)" stroke-width="2"/>',
        f'<text class="signal" x="{rounded_x + 12:.1f}" y="{rounded_y - 8:.1f}">rounded · (2, 4)</text>',
        f'<text class="signal" x="{rounded_x + 12:.1f}" y="{rounded_y + 8:.1f}">46 &gt; 45 · infeasible</text>',
        f'<circle cx="{nearest_x:.1f}" cy="{nearest_y:.1f}" r="7" fill="var(--viz-paper,#fff)" stroke="var(--viz-muted,#676762)" stroke-width="2"/>',
        f'<text class="muted" x="{nearest_x + 10:.1f}" y="{nearest_y + 16:.1f}">nearest feasible · (2, 3), z = 34</text>',
        f'<circle cx="{integer_x:.1f}" cy="{integer_y:.1f}" r="9" fill="var(--viz-good,#087f5b)" stroke="var(--viz-paper,#fff)" stroke-width="2"/>',
        f'<text class="good" x="{integer_x + 12:.1f}" y="{integer_y + 4:.1f}">integer optimum · (0, 5), z = 40</text>',
    ]

    out += [
        '<text class="section" x="518" y="114">Four different answers</text>',
        '<text class="small" x="518" y="144">1 · LP RELAXATION</text>',
        f'<text class="value" x="518" y="169">z = {float(lp_value):.2f}</text>',
        '<text class="small" x="518" y="187">Fractions are temporarily legal.</text>',
        '<line class="grid" x1="518" y1="205" x2="724" y2="205"/>',
        '<text class="small signal" x="518" y="232">2 · NEAREST ROUNDING</text>',
        '<text class="value signal" x="518" y="257">(2, 4) is illegal</text>',
        '<text class="small signal" x="518" y="275">The second row is exceeded by 1.</text>',
        '<line class="grid" x1="518" y1="293" x2="724" y2="293"/>',
        '<text class="small" x="518" y="320">3 · NEAREST FEASIBLE</text>',
        '<text class="value" x="518" y="345">(2, 3) · z = 34</text>',
        '<text class="small" x="518" y="363">Legal does not mean best.</text>',
        '<line class="grid" x1="518" y1="381" x2="724" y2="381"/>',
        '<text class="small good" x="518" y="408">4 · INTEGER OPTIMUM</text>',
        f'<text class="value good" x="518" y="433">(0, 5) · z = {integer_value}</text>',
        '<text class="small" x="518" y="451">The best legal lattice point.</text>',
        '<text class="section" x="24" y="562">Rounding is not approximation here. It first breaks feasibility, then misses the optimum.</text>',
        '<text class="source" x="24" y="594">Source: Bradley, Hax &amp; Magnanti (1977), ch. 9 · Exact values regenerated by the companion code.</text>',
        "</svg>",
    ]
    svg = "\n".join(out) + "\n"
    (OUT / "fig1-rounding-fails.svg").write_text(svg, encoding="utf-8")
    return svg


def branch_svg() -> str:
    model = load_model()
    nodes, snapshots = trace(model)
    height = 650
    out = svg_start(
        height,
        "fig2-bnb",
        "Branch-and-bound turns the proof into a narrowing interval",
        "For this maximization problem, the incumbent L is a certified lower bound and the open-node relaxations give an upper bound U. The root LP bound is 165/4. L2 gives incumbent 39; L4 lowers the raw LP upper bound to 365/9, which can be floored to 40 because the integer objective is integral; L5 does not improve; L6 closes the interval at 40.",
    )
    out += [
        '<text class="headline" x="24" y="38">Branch-and-bound turns proof into a narrowing interval</text>',
        '<text class="small" x="24" y="63">Maximisation certificate: incumbent L ≤ true integer optimum z* ≤ raw LP bound U</text>',
        '<text class="section" x="24" y="105">The textbook branching tree</text>',
        '<text class="small" x="275" y="105">green = incumbent · red = infeasible</text>',
    ]
    positions = {
        "L0": (250, 137), "L1": (142, 225), "L2": (358, 225),
        "L3": (65, 321), "L4": (210, 321), "L5": (150, 423), "L6": (282, 423),
    }
    edges = [("L0", "L1"), ("L0", "L2"), ("L1", "L3"), ("L1", "L4"), ("L4", "L5"), ("L4", "L6")]
    for parent, child in edges:
        x1, y1 = positions[parent]
        x2, y2 = positions[child]
        out.append(f'<line x1="{x1}" y1="{y1 + 28}" x2="{x2}" y2="{y2 - 28}" stroke="var(--viz-muted,#9a9a94)" stroke-width="1.5"/>')
    edge_labels = [
        (177, 183, "x₂ ≥ 4"), (316, 183, "x₂ ≤ 3"),
        (90, 277, "x₁ ≥ 2"), (185, 277, "x₁ ≤ 1"),
        (153, 377, "x₂ ≤ 4"), (272, 377, "x₂ ≥ 5"),
    ]
    for x, y, label in edge_labels:
        out.append(f'<text class="small" x="{x}" y="{y}">{esc(label)}</text>')

    for name, (x, y) in positions.items():
        node = nodes[name]
        fill = "var(--viz-panel,#ededeb)"
        stroke = "var(--viz-muted,#676762)"
        if node.disposition == "infeasible":
            stroke = "var(--viz-signal,#d6001c)"
        elif name in {"L2", "L6"}:
            fill, stroke = "var(--viz-good-soft,#dff3eb)", "var(--viz-good,#087f5b)"
        out += [
            f'<rect x="{x - 54}" y="{y - 27}" width="108" height="54" rx="4" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>',
            f'<text class="section" x="{x - 44}" y="{y - 7}">{name}</text>',
        ]
        if node.point is None:
            out += [f'<text class="signal" x="{x - 44}" y="{y + 13}">infeasible</text>']
        else:
            point = f"({format_fraction(node.point.x1)}, {format_fraction(node.point.x2)})"
            out += [
                f'<text x="{x - 15}" y="{y - 7}">{esc(point)}</text>',
                f'<text x="{x - 44}" y="{y + 13}">LP bound · {esc(format_fraction(node.lp_bound))}</text>',
            ]
    out += [
        '<text class="small muted" x="150" y="482" text-anchor="middle">integer 37 · no improvement</text>',
        '<text class="small good" x="282" y="500" text-anchor="middle">incumbent · L = 40</text>',
        '<text class="small good" x="358" y="263" text-anchor="middle">first incumbent · L = 39</text>',
        '<line class="grid" x1="494" y1="88" x2="494" y2="500"/>',
        '<text class="section" x="518" y="105">The certificate</text>',
        '<text class="small" x="518" y="134">L = best integer found</text>',
        '<text class="small" x="518" y="151">U = raw open-node LP bound</text>',
        '<text class="small" x="518" y="185">AFTER L1 / L2</text>',
        f'<text class="value" x="518" y="212">{format_fraction(snapshots[1].lower)} ≤ z* ≤ {format_fraction(snapshots[1].upper)}</text>',
        '<line x1="518" y1="226" x2="690" y2="226" stroke="#676762" stroke-width="8"/><circle cx="518" cy="226" r="6" fill="#087f5b"/><circle cx="690" cy="226" r="5" fill="#0a0a0a"/>',
        '<text class="small" x="518" y="255">AFTER L3 / L4</text>',
        f'<text class="value" x="518" y="282">{format_fraction(snapshots[2].lower)} ≤ z* ≤ {format_fraction(snapshots[2].upper)}</text>',
        '<line x1="518" y1="296" x2="652" y2="296" stroke="#676762" stroke-width="8"/><circle cx="518" cy="296" r="6" fill="#087f5b"/><circle cx="652" cy="296" r="5" fill="#0a0a0a"/>',
        '<text class="small" x="518" y="320">L5 leaves this interval unchanged.</text>',
        '<text class="small good" x="518" y="349">AFTER L6</text>',
        f'<text class="value good" x="518" y="376">{format_fraction(snapshots[4].lower)} = z* = {format_fraction(snapshots[4].upper)}</text>',
        '<circle cx="604" cy="394" r="7" fill="#087f5b"/>',
        '<text class="small" x="518" y="420">The optimality gap is U − L.</text>',
        '<text class="small" x="518" y="438">It closes when no open node</text>',
        '<text class="small" x="518" y="456">can beat the incumbent.</text>',
        '<rect class="panel" x="24" y="516" width="700" height="85" rx="3"/>',
        '<text class="section" x="42" y="544">The LP is still doing the proving.</text>',
        '<text x="42" y="568">Every node drops integrality, solves an LP relaxation, then uses that bound</text>',
        '<text x="42" y="588">to prune a whole region without enumerating every integer point inside it.</text>',
        '<text class="source" x="24" y="630">Raw-LP-bound trace on the Bradley–Hax–Magnanti tree. Not a HiGHS internal solver log.</text>',
        "</svg>",
    ]
    svg = "\n".join(out) + "\n"
    (OUT / "fig2-branch-and-bound.svg").write_text(svg, encoding="utf-8")
    return svg


def rounding_fragment(static_svg: str) -> str:
    model = load_model()
    lp_point, lp_value = solve_relaxation(model)  # type: ignore[misc]
    rounded = nearest_integer(lp_point)
    nearest = nearest_feasible_integer(model, lp_point)
    integer_point, integer_value = solve_integer_exact(model)
    steps = [
        {"key": "lp", "label": "LP relaxation", "point": "(2.25, 3.75)", "value": "z = 41.25", "tone": "neutral", "message": "Drop the integer rule temporarily. Fractions are legal, and the best point is where both constraint lines meet."},
        {"key": "round", "label": "Nearest rounding", "point": "(2, 4)", "value": "infeasible", "tone": "bad", "message": "Rounding keeps x₁ + x₂ = 6, but makes 5x₁ + 9x₂ = 46. The limit is 45: the rounded answer is not approximately right; it is illegal."},
        {"key": "nearest", "label": "Nearest feasible", "point": "(2, 3)", "value": "z = 34", "tone": "neutral", "message": "The closest legal lattice point in Euclidean distance repairs feasibility, but it is still not the best integer decision."},
        {"key": "integer", "label": "Integer optimum", "point": "(0, 5)", "value": "z = 40", "tone": "good", "message": "Exhaustive enumeration and HiGHS agree: the best integer point sits elsewhere. Legal proximity to the LP point does not imply quality."},
    ]
    dots = []
    for point in integer_feasible_points(model):
        x, y = chart_coordinates(point)
        dots.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="integrality-lattice-dot"/>')

    # The enhanced chart carries the same grid, ticks and axis titles as the
    # static fallback. Without them a reader cannot tell (2, 3) from (2, 4).
    grid = []
    for tick in range(7):
        x, _ = chart_coordinates(Point(Fraction(tick), Fraction(0)))
        grid.append(f'<line class="integrality-grid" x1="{x:.1f}" y1="116" x2="{x:.1f}" y2="494"/>')
        grid.append(f'<text class="integrality-tick" x="{x:.1f}" y="513" text-anchor="middle">{tick}</text>')
        _, y = chart_coordinates(Point(Fraction(0), Fraction(tick)))
        grid.append(f'<line class="integrality-grid" x1="48" y1="{y:.1f}" x2="470" y2="{y:.1f}"/>')
        grid.append(f'<text class="integrality-tick" x="37" y="{y + 4:.1f}" text-anchor="end">{tick}</text>')
    grid.append('<text class="integrality-axis-title" x="466" y="513" text-anchor="end">x₁</text>')
    grid.append('<text class="integrality-axis-title" x="31" y="108">x₂</text>')
    special = []
    for key, point, label in [
        ("lp", lp_point, "LP relaxation (2.25, 3.75)"),
        ("round", rounded, "Nearest rounding (2, 4), infeasible"),
        ("nearest", nearest, "Nearest feasible integer (2, 3)"),
        ("integer", integer_point, "Integer optimum (0, 5)"),
    ]:
        x, y = chart_coordinates(point)
        special.append(f'<g class="integrality-special integrality-special-{key}" data-stage-point="{key}"><circle cx="{x:.1f}" cy="{y:.1f}" r="10"/><text x="{x + 13:.1f}" y="{y + 4:.1f}">{esc(label)}</text></g>')
    vertices = relaxation_vertices(model)
    controls = "\n".join(
        f'<button type="button" data-integrality-step="{step["key"]}" aria-pressed="{"true" if index == 0 else "false"}"><span>{index + 1}</span>{esc(step["label"])}</button>'
        for index, step in enumerate(steps)
    )
    payload = json.dumps({"steps": steps}, separators=(",", ":"), ensure_ascii=False)
    fragment = f'''<div class="viz-integrality" data-viz="integer-rounding" aria-labelledby="integrality-heading">
  <header class="integrality-heading">
    <div class="integrality-kicker">LP relaxation → integer decision</div>
    <h3 id="integrality-heading">The nearest integer is illegal. The best integer is elsewhere.</h3>
    <p>An <strong>LP relaxation</strong> keeps the objective and constraints but temporarily allows the integer variables to be fractional. <strong>Rounding</strong> moves that fractional answer to nearby integers; the <strong>nearest feasible</strong> point here is the legal lattice point closest in Euclidean distance; the <strong>integer optimum</strong> is the legal point with the best objective.</p>
  </header>
  <div class="integrality-fallback">{static_svg}</div>
  <div class="integrality-enhanced" hidden>
    <div class="integrality-steps" aria-label="Follow the failed rounding argument">{controls}</div>
    <div class="integrality-layout">
      <svg class="integrality-chart" viewBox="20 84 480 474" role="img" aria-labelledby="integrality-live-title integrality-live-desc">
        <title id="integrality-live-title">The LP relaxation and three integer alternatives</title>
        <desc id="integrality-live-desc">Select a step to compare the fractional LP optimum, its infeasible rounding, the nearest feasible integer, and the integer optimum.</desc>
        <rect x="24" y="88" width="470" height="438" rx="3" class="integrality-panel"/>
        {''.join(grid)}
        <path d="{polygon_path(vertices)}" class="integrality-region"/>
        {''.join(dots)}
        {''.join(special)}
        <text x="48" y="546" class="integrality-axis-label">LP-feasible region · 25 feasible lattice points</text>
      </svg>
      <div class="integrality-readout" data-integrality-readout aria-live="polite">
        <small>LP relaxation</small><strong>(2.25, 3.75)</strong><b>z = 41.25</b>
        <p>Drop the integer rule temporarily. Fractions are legal, and the best point is where both constraint lines meet.</p>
      </div>
    </div>
  </div>
  <script type="application/json" class="integrality-data">{payload}</script>
  <p class="integrality-source">Source: Bradley, Hax &amp; Magnanti (1977), chapter 9. Exact rational enumeration; independently cross-checked with HiGHS.</p>
</div>'''
    (OUT / "fig1-rounding-fails.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def branch_fragment(static_svg: str) -> str:
    model = load_model()
    _, snapshots = trace(model)
    all_bounds = [float(item.upper) for item in snapshots]
    all_bounds += [float(item.lower) for item in snapshots if item.lower is not None]
    payload = json.dumps(
        {
            "snapshots": [snapshot_as_json(item) for item in snapshots],
            "scale_minimum": min(all_bounds),
            "scale_maximum": max(all_bounds),
        },
        separators=(",", ":"),
        ensure_ascii=False,
    )
    controls = "\n".join(
        f'<button type="button" data-bnb-step="{item.step}" aria-pressed="{"true" if item.step == 0 else "false"}"><span>{item.step}</span>{esc(item.event)}</button>'
        for item in snapshots
    )
    fragment = f'''<div class="viz-bnb" data-viz="branch-bound" aria-labelledby="bnb-heading">
  <header class="bnb-heading">
    <div class="bnb-kicker">A proof in progress</div>
    <h3 id="bnb-heading">Branch-and-bound narrows a certified interval</h3>
    <p>For this <strong>maximisation</strong>, the best integer solution found is the incumbent <i>L</i>, a lower bound. Open-node LP relaxations supply a valid raw upper bound <i>U</i>. At every step with an incumbent: <strong><i>L</i> ≤ <i>z</i>* ≤ <i>U</i></strong>.</p>
  </header>
  <div class="bnb-fallback">{static_svg}</div>
  <div class="bnb-enhanced" hidden>
    <h4 class="bnb-live-heading">Step through the certificate</h4>
    <div class="bnb-layout">
      <div class="bnb-steps" aria-label="Step through the exact branch-and-bound trace">{controls}</div>
      <div class="bnb-certificate" data-bnb-certificate aria-live="polite">
        <small>Before an integer solution is found</small>
        <strong>No incumbent yet</strong>
        <div class="bnb-interval" aria-hidden="true"><i style="--bnb-left:0%;--bnb-width:100%"></i></div>
        <p>Solve root relaxation L0</p>
        <span>Open node: L0 · raw LP upper bound U = 41.25</span>
      </div>
    </div>
  </div>
  <script type="application/json" class="bnb-data">{payload}</script>
  <p class="bnb-source">Each node solves an LP relaxation with exact rational arithmetic. The figure follows the textbook branch tree on an explicit deterministic schedule, in which both root children are solved first. It is not a log of HiGHS's internal MIP search. Green marks incumbents; red marks infeasibility.</p>
</div>'''
    (OUT / "fig2-branch-and-bound.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_demo(rounding: str, branch: str) -> None:
    document = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>When the Answer Is Yes or No: figure demo</title>
  <link rel="stylesheet" href="visuals.css">
  <style>body{{margin:0;background:#e8e8e5;color:#0a0a0a;font-family:Arial,sans-serif}}main{{max-width:900px;margin:auto;padding:32px 16px}}figure{{margin:0 0 48px}}figcaption{{font-size:14px;line-height:1.5;margin-top:10px}}</style>
</head>
<body><main>
  <figure>{rounding}<figcaption>The relaxed answer, failed rounding, nearest feasible point and integer optimum are four distinct objects.</figcaption></figure>
  <figure>{branch}<figcaption>For maximisation, the live certificate is L ≤ z* ≤ U.</figcaption></figure>
</main><script src="article-viz.js"></script></body>
</html>'''
    (HERE / "demo.html").write_text(document + "\n", encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    rounding = rounding_fragment(rounding_svg())
    branch = branch_fragment(branch_svg())
    write_demo(rounding, branch)
    print("wrote out/fig1-rounding-fails.svg and .html")
    print("wrote out/fig2-branch-and-bound.svg and .html")
    print("wrote demo.html")
