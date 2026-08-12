#!/usr/bin/env python3
"""Build the static and interactive visualisations for Post 2.

The SVG files are complete, shareable fallbacks for GitHub and social use.
The responsive HTML fragments explain the model anatomy, Netlib comparison,
basis, algorithm routes, sparse fill-in, Klee-Minty path and solver progress.
The Netlib chart progressively enhances with JavaScript; the other interactions
use native controls and CSS. No runtime library or network request is required.
"""

from __future__ import annotations

import html
import json
import statistics
from pathlib import Path

from analyze_structure import OUT, inclusive_quartiles, load_netlib, stigler_problem
from verify_klee_minty import klee_minty_path


WIDTH = 748


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def svg_start(height: int, prefix: str, title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {height}" width="100%" role="img" aria-labelledby="{prefix}-title {prefix}-desc">',
        f'<title id="{prefix}-title">{esc(title)}</title>',
        f'<desc id="{prefix}-desc">{esc(desc)}</desc>',
        "<style>",
        'text{font-family:"Plex Mono",ui-monospace,monospace;fill:#0a0a0a;font-size:12px}',
        '.headline{font-family:"Archivo",Helvetica,Arial,sans-serif;font-size:24px;font-weight:700;letter-spacing:-.5px}',
        '.subtitle,.source{fill:#6b6b6b;font-size:11px}',
        '.section{font-family:"Archivo",Helvetica,Arial,sans-serif;font-size:16px;font-weight:700}',
        '.value{font-size:18px;font-weight:500}',
        '.signal{fill:#d6001c}',
        '.muted{fill:#6b6b6b}',
        '.paper{fill:#fff}',
        '.panel{fill:#f2f2f0}',
        '.rule{stroke:#dcdcda}',
        "</style>",
        f'<rect class="paper" width="{WIDTH}" height="{height}"/>',
    ]


def write_structure_svg() -> str:
    problems = load_netlib()
    stigler = stigler_problem()
    densities = [100 * p.density for p in problems]
    coupling = [p.nonzeros_per_col for p in problems]
    q1, median, q3 = inclusive_quartiles(coupling)
    median_density = statistics.median(densities)
    above = sum(value > stigler.nonzeros_per_col for value in coupling)
    height = 510
    out = svg_start(
        height,
        "fig1-static",
        "Stigler looks extreme by percentage, not by relationships per choice",
        f"Two direct comparisons with 98 Netlib linear programs. Stigler is {100 * stigler.density:.1f} percent dense versus a Netlib median of {median_density:.2f} percent. It has {stigler.nonzeros_per_col:.1f} nonzeros per column versus a Netlib median of {median:.1f}; {above} Netlib models have more.",
    )
    out += [
        '<text class="headline" x="24" y="36">Stigler looks extreme by percentage—</text>',
        '<text class="headline" x="24" y="64">not by relationships per choice</text>',
        '<text class="subtitle" x="24" y="87">Compared with 98 Netlib LPs · objective row included on both sides</text>',
    ]

    left, right = 54.0, 708.0
    plot_w = right - left

    # Percentage density: a direct benchmark comparison on a 0–100 scale.
    out += [
        '<text class="section" x="24" y="132">Percentage of the matrix filled</text>',
        '<line class="rule" x1="54" y1="171" x2="708" y2="171" stroke-width="2"/>',
    ]
    for tick in (0, 25, 50, 75, 100):
        x = left + plot_w * tick / 100
        out += [
            f'<line class="rule" x1="{x:.1f}" y1="164" x2="{x:.1f}" y2="178"/>',
            f'<text class="subtitle" x="{x:.1f}" y="195" text-anchor="middle">{tick}%</text>',
        ]
    netlib_x = left + plot_w * median_density / 100
    stigler_x = left + plot_w * (100 * stigler.density) / 100
    out += [
        f'<circle cx="{netlib_x:.1f}" cy="171" r="7" fill="#5c5c56"/>',
        f'<text class="muted" x="{max(left, netlib_x):.1f}" y="151">Netlib median · {median_density:.2f}%</text>',
        f'<circle cx="{stigler_x:.1f}" cy="171" r="8" fill="#d6001c"/>',
        f'<text class="signal value" x="{stigler_x:.1f}" y="151" text-anchor="middle">Stigler · {100 * stigler.density:.1f}%</text>',
    ]

    # Relationships per column: distribution, IQR, median and Stigler.
    out += [
        '<text class="section" x="24" y="252">Rows touched by one decision column</text>',
        '<text class="subtitle" x="24" y="273">Each dot is one Netlib model</text>',
    ]
    axis_y = 346.0
    max_coupling = 30.0

    def cx(value: float) -> float:
        return left + plot_w * min(value, max_coupling) / max_coupling

    for tick in (0, 5, 10, 20, 30):
        x = cx(tick)
        out += [
            f'<line class="rule" x1="{x:.1f}" y1="306" x2="{x:.1f}" y2="370"/>',
            f'<text class="subtitle" x="{x:.1f}" y="389" text-anchor="middle">{tick}</text>',
        ]
    out.append(f'<rect x="{cx(q1):.1f}" y="310" width="{cx(q3) - cx(q1):.1f}" height="60" fill="#b4b4ae" opacity=".45"/>')
    for i, p in enumerate(problems):
        # Deterministic vertical jitter; the x-position carries the value.
        y = 326 + ((i * 17) % 37)
        out.append(f'<circle cx="{cx(p.nonzeros_per_col):.1f}" cy="{y}" r="2.4" fill="#5c5c56" opacity=".65"><title>{esc(p.name)} · {p.nonzeros_per_col:.1f} rows per decision</title></circle>')
    out += [
        f'<line x1="{cx(median):.1f}" y1="300" x2="{cx(median):.1f}" y2="376" stroke="#0a0a0a" stroke-width="1.5"/>',
        f'<text x="{cx(median):.1f}" y="294" text-anchor="middle">median · {median:.1f}</text>',
        f'<circle cx="{cx(stigler.nonzeros_per_col):.1f}" cy="346" r="8" fill="#d6001c" stroke="#fff" stroke-width="2"/>',
        f'<text class="signal value" x="{cx(stigler.nonzeros_per_col) + 12:.1f}" y="350">Stigler · {stigler.nonzeros_per_col:.1f}</text>',
        f'<text class="subtitle" x="24" y="429">Netlib middle half: {q1:.1f}–{q3:.1f} · {above} of 98 models touch more rows per decision than Stigler</text>',
        '<text class="source" x="24" y="468">Source: Netlib LP/DATA summary snapshot · 11 Aug 2026</text>',
        '<text class="source" x="24" y="488">Code and data: github.com/Denis-Joly/what-optimal-means · post-02 folder</text>',
        "</svg>",
    ]
    svg = "\n".join(out) + "\n"
    (OUT / "fig1-structure-not-size.svg").write_text(svg, encoding="utf-8")
    return svg


def write_basis_svg() -> str:
    height = 500
    out = svg_start(
        height,
        "fig2-static",
        "Four loose nutrient floors leave room for only five foods",
        "Stigler's standard-form model has 77 food columns and 9 surplus columns. A basis uses 9 columns. In the reported optimum four positive surpluses occupy four positions, leaving five food positions.",
    )
    out += [
        '<text class="headline" x="24" y="38">Four loose nutrient floors leave room for five foods</text>',
        '<text class="subtitle" x="24" y="63">From 86 available columns to the nine positions in one solved basis</text>',
        '<text class="section" x="24" y="108">1 · Candidate pool</text>',
        '<rect x="24" y="126" width="609" height="42" fill="#b4b4ae"/>',
        '<rect x="633" y="126" width="71" height="42" fill="#5c5c56"/>',
        '<text x="328" y="152" text-anchor="middle">77 food columns</text>',
        '<text x="669" y="152" text-anchor="middle" style="fill:#fff">9</text>',
        '<text class="subtitle" x="704" y="184" text-anchor="end">9 surplus columns</text>',
        '<text class="section" x="24" y="226">2 · A basis uses nine columns</text>',
        '<text class="signal" x="24" y="260" style="font-size:29px;font-weight:500">459,856,441,980</text>',
        '<text class="subtitle" x="24" y="281">candidate nine-column selections · many are singular or infeasible</text>',
        '<text class="section" x="24" y="329">3 · This solved basis</text>',
    ]
    slots = [
        ("protein", "surplus"), ("iron", "surplus"), ("B1", "surplus"), ("niacin", "surplus"),
        ("flour", "food"), ("cabbage", "food"), ("spinach", "food"), ("beans", "food"), ("liver", "food"),
    ]
    gap, slot_w, x0, y = 5.0, 70.0, 24.0, 350.0
    for i, (label, kind) in enumerate(slots):
        x = x0 + i * (slot_w + gap)
        fill = "#8a8a83" if kind == "surplus" else "#d6001c"
        text_fill = "#fff"
        out += [
            f'<rect x="{x:.1f}" y="{y}" width="{slot_w}" height="65" fill="{fill}"/>',
            f'<text x="{x + slot_w / 2:.1f}" y="{y + 28}" text-anchor="middle" style="fill:{text_fill}">{esc(label)}</text>',
            f'<text x="{x + slot_w / 2:.1f}" y="{y + 48}" text-anchor="middle" style="fill:{text_fill};font-size:10px">{kind}</text>',
        ]
    out += [
        '<text class="subtitle" x="164" y="442" text-anchor="middle">4 positive surpluses · floors exceeded</text>',
        '<text class="signal" x="516" y="442" text-anchor="middle">5 foods · all remaining positions</text>',
        '<text class="source" x="24" y="480">A sparse optimal basic solution exists; this does not mean every optimum is sparse.</text>',
        "</svg>",
    ]
    svg = "\n".join(out) + "\n"
    (OUT / "fig2-nine-positions.svg").write_text(svg, encoding="utf-8")
    return svg


def write_structure_fragment(static_svg: str) -> str:
    problems = load_netlib()
    stigler = stigler_problem()
    q1, median, q3 = inclusive_quartiles([p.nonzeros_per_col for p in problems])
    median_density = statistics.median([100 * p.density for p in problems])
    above = sum(p.nonzeros_per_col > stigler.nonzeros_per_col for p in problems)
    dataset = [
        {
            "name": p.name,
            "rows": p.rows,
            "cols": p.cols,
            "nonzeros": p.nonzeros,
            "cells": p.cells,
            "density": 100 * p.density,
            "coupling": p.nonzeros_per_col,
            "benchmark": "Netlib",
        }
        for p in problems
    ]
    dataset.append({
        "name": "STIGLER",
        "rows": stigler.rows,
        "cols": stigler.cols,
        "nonzeros": stigler.nonzeros,
        "cells": stigler.cells,
        "density": 100 * stigler.density,
        "coupling": stigler.nonzeros_per_col,
        "benchmark": "Stigler",
    })
    options = "\n".join(
        f'<option value="{esc(p["name"])}"{" selected" if p["name"] == "STIGLER" else ""}>{esc(p["name"].title() if p["name"] != "STIGLER" else "Stigler")}</option>'
        for p in sorted(dataset, key=lambda item: (item["name"] != "STIGLER", item["name"]))
    )
    payload = json.dumps({
        "models": dataset,
        "summary": {
            "couplingQ1": q1,
            "couplingMedian": median,
            "couplingQ3": q3,
            "densityMedian": median_density,
            "aboveStigler": above,
        },
    }, separators=(",", ":"))
    fragment = f'''<div class="viz-shell viz-netlib" data-viz="netlib" aria-labelledby="netlib-viz-heading">
  <header class="viz-heading">
    <div class="viz-kicker">Netlib · 98 linear programs</div>
    <h3 id="netlib-viz-heading">Stigler looks extreme by percentage—not by relationships per choice</h3>
    <p>Switch the denominator and watch the same models tell a different story. The objective row is included on both sides.</p>
  </header>
  <div class="viz-fallback">{static_svg}</div>
  <div class="viz-enhanced" hidden>
    <div class="viz-toolbar">
      <fieldset class="viz-segment" aria-label="Measure shown on the vertical axis">
        <legend>Measure</legend>
        <label><input type="radio" name="netlib-metric" value="density"> Density (%)</label>
        <label><input type="radio" name="netlib-metric" value="coupling" checked> Rows touched per decision</label>
      </fieldset>
      <label class="viz-select">Inspect a model
        <select data-viz-model>{options}</select>
      </label>
    </div>
    <p class="viz-annotation" data-viz-annotation>Stigler touches 8.4 rows per choice; 21 of 98 Netlib models touch more.</p>
    <div class="viz-chart-wrap">
      <svg class="viz-chart" data-viz-canvas role="img" aria-labelledby="netlib-live-title netlib-live-desc">
        <title id="netlib-live-title">Netlib benchmark comparison</title>
        <desc id="netlib-live-desc">Interactive plot. Choose density or rows touched per decision, then choose a model for exact values.</desc>
      </svg>
    </div>
    <output class="viz-readout" data-viz-readout aria-live="polite">Stigler · 10 rows × 77 columns · 647 non-zero cells · 84.0% dense · 8.4 rows touched per decision.</output>
  </div>
  <script type="application/json" class="viz-data">{payload}</script>
  <p class="viz-source">Source: Netlib LP/DATA summary snapshot, 11 August 2026. Select a model for exact values.</p>
</div>'''
    (OUT / "fig1-structure-not-size.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_basis_fragment() -> str:
    slots = [
        ("protein", "surplus"), ("iron", "surplus"), ("B1", "surplus"), ("niacin", "surplus"),
        ("flour", "food"), ("cabbage", "food"), ("spinach", "food"), ("beans", "food"), ("liver", "food"),
    ]
    slot_html = "\n".join(
        f'''<div class="basis-slot basis-slot-{kind}">
          <span class="basis-slot-position">position {i}</span>
          <span class="basis-slot-final">{esc(label)}</span>
          <small>{kind}</small>
        </div>'''
        for i, (label, kind) in enumerate(slots, 1)
    )
    fragment = f'''<div class="viz-shell basis-figure" aria-labelledby="basis-viz-heading">
  <header class="viz-heading">
    <div class="viz-kicker">Read the basis in three steps</div>
    <h3 id="basis-viz-heading">Four loose nutrient floors leave room for five foods</h3>
    <p>The diagram separates available columns, candidate selections and the basis found at this optimum.</p>
  </header>
  <div class="viz-segment basis-controls" aria-label="Basis diagram step">
    <label><input type="radio" name="basis-step" id="basis-step-1"><span>1</span> Available</label>
    <label><input type="radio" name="basis-step" id="basis-step-2"><span>2</span> Select nine</label>
    <label><input type="radio" name="basis-step" id="basis-step-3" checked><span>3</span> Solved basis</label>
  </div>
  <div class="basis-story">
    <section class="basis-pool" aria-label="The 86 available columns">
      <div class="basis-step-label">1 · Candidate pool</div>
      <div class="basis-pool-bar" role="img" aria-label="77 food columns and 9 surplus columns, shown in proportion">
        <div class="basis-food-pool"><strong>77</strong><span>food columns</span></div>
        <div class="basis-surplus-pool"><strong>9</strong><span>surplus</span></div>
      </div>
    </section>
    <section class="basis-count">
      <div class="basis-step-label">2 · Choose nine columns</div>
      <strong>459,856,441,980</strong>
      <p>candidate selections—not bases or vertices. Many are singular or infeasible.</p>
    </section>
    <section class="basis-solution">
      <div class="basis-step-label">3 · This solved basis</div>
      <div class="basis-slots">{slot_html}</div>
      <div class="basis-explanation">
        <span><strong>4</strong> exceeded floors → positive surpluses</span>
        <span><strong>5</strong> positions remain for foods</span>
      </div>
    </section>
  </div>
  <p class="viz-source">A sparse optimal basic solution exists; this does not mean every optimum is sparse.</p>
</div>'''
    (OUT / "fig2-nine-positions.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_model_anatomy_fragment() -> str:
    fragment = '''<div class="viz-shell model-anatomy" aria-labelledby="model-anatomy-heading">
  <header class="viz-heading">
    <div class="viz-kicker">The linear program, unpacked</div>
    <h3 id="model-anatomy-heading">Four objects make one model</h3>
    <p>The notation is compact because each symbol has one job.</p>
  </header>
  <div class="model-lines" role="group" aria-label="Minimise c transpose x, subject to A x greater than or equal to b and x non-negative">
    <div class="model-line model-line-objective">
      <span class="model-verb">minimise</span>
      <span class="model-symbol model-c"><i>c</i><sup>T</sup></span>
      <span class="model-symbol model-x"><i>x</i></span>
      <span class="model-purpose">one total cost</span>
    </div>
    <div class="model-line model-line-constraints">
      <span class="model-verb">subject to</span>
      <span class="model-symbol model-a"><i>A</i></span>
      <span class="model-symbol model-x"><i>x</i></span>
      <span class="model-relation">≥</span>
      <span class="model-symbol model-b"><i>b</i></span>
      <span class="model-purpose">nine promises</span>
    </div>
    <div class="model-line model-line-domain">
      <span class="model-verb">with</span>
      <span class="model-symbol model-x"><i>x</i></span>
      <span class="model-relation">≥</span>
      <span class="model-symbol model-zero">0</span>
      <span class="model-purpose">no negative purchases</span>
    </div>
  </div>
  <dl class="model-key">
    <div class="model-key-x"><dt><i>x</i></dt><dd><strong>77 choices</strong><span>daily food expenditures</span></dd></div>
    <div class="model-key-c"><dt><i>c</i></dt><dd><strong>77 weights</strong><span>all equal to one</span></dd></div>
    <div class="model-key-a"><dt><i>A</i></dt><dd><strong>9 × 77 coefficients</strong><span>how each food affects each nutrient</span></dd></div>
    <div class="model-key-b"><dt><i>b</i></dt><dd><strong>9 floors</strong><span>minimum daily allowances</span></dd></div>
  </dl>
</div>'''
    (OUT / "fig0-model-anatomy.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_routes_fragment() -> str:
    polygon = "26,166 63,54 170,28 250,91 219,181 106,202"
    fragment = f'''<div class="viz-shell routes-figure" aria-labelledby="routes-heading">
  <header class="viz-heading">
    <div class="viz-kicker">Two algorithm families</div>
    <h3 id="routes-heading">Same feasible region, different route</h3>
    <p>The geometry is shared; the objects updated at each step are not.</p>
  </header>
  <div class="routes-grid">
    <section class="route-panel">
      <h4>Simplex</h4>
      <svg viewBox="0 0 280 220" role="img" aria-label="A path following the boundary from vertex to vertex">
        <polygon class="route-region" points="{polygon}"/>
        <polyline class="route-path" points="26,166 106,202 219,181 250,91 170,28"/>
        <g class="route-nodes"><circle cx="26" cy="166" r="5"/><circle cx="106" cy="202" r="5"/><circle cx="219" cy="181" r="5"/><circle cx="250" cy="91" r="5"/><circle cx="170" cy="28" r="6"/></g>
      </svg>
      <p>Walks along edges. Each pivot exchanges one column in the basis.</p>
    </section>
    <section class="route-panel">
      <h4>Interior point</h4>
      <svg viewBox="0 0 280 220" role="img" aria-label="A curved path starting inside the feasible region and approaching the optimum, followed by an optional dashed crossover to the vertex">
        <polygon class="route-region" points="{polygon}"/>
        <path class="route-path" d="M82 160 C101 135 116 118 139 102 C158 84 166 61 169 43"/>
        <path class="route-limit" d="M169 43 L170 28"/>
        <circle class="route-start" cx="82" cy="160" r="5"/><circle class="route-iterate" cx="169" cy="43" r="5"/><circle class="route-end" cx="170" cy="28" r="6"/>
      </svg>
      <p>Moves through the interior toward the boundary. Each iteration solves a Newton system; optional crossover recovers a vertex.</p>
    </section>
  </div>
</div>'''
    (OUT / "fig3-two-routes.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_fill_fragment() -> str:
    center = (260.0, 146.0)
    leaves = [(260.0, 35.0), (385.0, 112.0), (337.0, 250.0), (183.0, 250.0), (135.0, 112.0)]

    def edge(a: tuple[float, float], b: tuple[float, float], css: str) -> str:
        return f'<line class="{css}" x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}"/>'

    star_edges = "".join(edge(center, leaf, "fill-original-edge") for leaf in leaves)
    clique_edges = "".join(
        edge(leaves[i], leaves[j], "fill-new-edge")
        for i in range(len(leaves)) for j in range(i + 1, len(leaves))
    )
    leaf_nodes = "".join(f'<circle class="fill-leaf" cx="{x}" cy="{y}" r="17"/>' for x, y in leaves)
    fragment = f'''<div class="viz-shell fill-figure" aria-labelledby="fill-heading">
  <header class="viz-heading">
    <div class="viz-kicker">Sparse elimination</div>
    <h3 id="fill-heading">Eliminate the hub first and ten new links appear</h3>
    <p>The starting graph never changes. Only the order does.</p>
  </header>
  <fieldset class="viz-segment fill-controls" aria-label="Elimination order">
    <legend>Elimination order</legend>
    <label><input type="radio" name="fill-step" id="fill-original" checked> Original star</label>
    <label><input type="radio" name="fill-step" id="fill-hub"> Hub first</label>
    <label><input type="radio" name="fill-step" id="fill-leaves"> Leaves first</label>
  </fieldset>
  <div class="fill-stage">
    <svg viewBox="0 0 520 285" role="img" aria-labelledby="fill-svg-title fill-svg-desc">
      <title id="fill-svg-title">Fill-in created by eliminating a star graph</title>
      <desc id="fill-svg-desc">The original graph has one hub and five leaves. Eliminating the hub first connects every pair of leaves, creating ten fill edges. Eliminating leaves first creates none.</desc>
      <g class="fill-state fill-state-original">{star_edges}<circle class="fill-hub" cx="{center[0]}" cy="{center[1]}" r="21"/>{leaf_nodes}</g>
      <g class="fill-state fill-state-hub">{clique_edges}<circle class="fill-ghost" cx="{center[0]}" cy="{center[1]}" r="21"/>{leaf_nodes}</g>
      <g class="fill-state fill-state-leaves"><circle class="fill-hub" cx="{center[0]}" cy="{center[1]}" r="21"/><g class="fill-eliminated">{leaf_nodes}</g></g>
    </svg>
  </div>
  <div class="fill-messages" aria-live="polite">
    <p class="fill-message fill-message-original"><strong>5 original edges</strong><span>No fill has been created.</span></p>
    <p class="fill-message fill-message-hub"><strong>C(5, 2) = 10 fill edges</strong><span>The five surviving neighbours become a clique.</span></p>
    <p class="fill-message fill-message-leaves"><strong>0 fill edges</strong><span>A leaf has only one surviving neighbour, so there is no pair to connect.</span></p>
  </div>
</div>'''
    (OUT / "fig4-fill-in.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_klee_minty_fragment() -> str:
    # Classic 3-variable Klee-Minty instance:
    # max 100x1 + 10x2 + x3
    # x1 <= 1; 20x1+x2 <= 100; 200x1+20x2+x3 <= 10000; x >= 0.
    # Dantzig's largest-reduced-cost rule follows this Gray-code path.
    codes = ["000", "100", "110", "010", "011", "111", "101", "001"]
    verified = klee_minty_path()
    path = [
        (code, tuple(float(value) for value in point), int(objective))
        for code, (point, objective) in zip(codes, verified)
    ]
    assert all(path[i][2] < path[i + 1][2] for i in range(len(path) - 1))

    def project(point: tuple[float, float, float]) -> tuple[float, float]:
        x1, x2, x3 = point
        y2, z3 = x2 / 100.0, x3 / 10000.0
        return 80 + 240 * x1 + 140 * y2, 320 - 50 * x1 + 35 * y2 - 220 * z3

    points = {code: project(point) for code, point, _ in path}
    cube_edges = [
        ("000", "100"), ("000", "010"), ("000", "001"),
        ("100", "110"), ("100", "101"), ("010", "110"),
        ("010", "011"), ("001", "101"), ("001", "011"),
        ("110", "111"), ("101", "111"), ("011", "111"),
    ]
    edges = "".join(
        f'<line class="km-edge" x1="{points[a][0]:.1f}" y1="{points[a][1]:.1f}" x2="{points[b][0]:.1f}" y2="{points[b][1]:.1f}"/>'
        for a, b in cube_edges
    )
    path_points = " ".join(f"{points[code][0]:.1f},{points[code][1]:.1f}" for code, _, _ in path)
    nodes = "".join(
        f'<g><circle class="km-node" cx="{points[code][0]:.1f}" cy="{points[code][1]:.1f}" r="16"/><text x="{points[code][0]:.1f}" y="{points[code][1] + 5:.1f}" text-anchor="middle">{i}</text></g>'
        for i, (code, _, _) in enumerate(path, 1)
    )
    fragment = f'''<div class="viz-shell km-figure" aria-labelledby="km-heading">
  <header class="viz-heading">
    <div class="viz-kicker">Klee–Minty · three dimensions</div>
    <h3 id="km-heading">The largest-reduced-cost rule takes the long way around</h3>
    <p>A distorted cube keeps every pivot improving while forcing a visit to every vertex.</p>
  </header>
  <div class="km-layout">
    <svg viewBox="0 0 500 380" role="img" aria-labelledby="km-svg-title km-svg-desc">
      <title id="km-svg-title">The eight-vertex Klee-Minty path</title>
      <desc id="km-svg-desc">A projection of a distorted three-dimensional cube. A red path numbered one through eight visits every vertex in increasing objective order.</desc>
      <g>{edges}</g><polyline class="km-path" points="{path_points}"/>{nodes}
    </svg>
    <div class="km-equations" aria-label="Klee-Minty linear program">
      <div><span>maximise</span><strong>100<i>x</i><sub>1</sub> + 10<i>x</i><sub>2</sub> + <i>x</i><sub>3</sub></strong></div>
      <div><span>subject to</span><strong><i>x</i><sub>1</sub> ≤ 1</strong></div>
      <div><span></span><strong>20<i>x</i><sub>1</sub> + <i>x</i><sub>2</sub> ≤ 100</strong></div>
      <div><span></span><strong>200<i>x</i><sub>1</sub> + 20<i>x</i><sub>2</sub> + <i>x</i><sub>3</sub> ≤ 10,000</strong></div>
      <div><span></span><strong><i>x</i> ≥ 0</strong></div>
    </div>
  </div>
  <div class="km-counts"><div><strong>3 variables</strong><span>8 vertices · 7 pivots</span></div><div><strong><i>n</i> variables</strong><span>2<sup><i>n</i></sup> vertices · 2<sup><i>n</i></sup> − 1 pivots</span></div></div>
</div>'''
    (OUT / "fig5-klee-minty.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_solver_progress_fragment() -> str:
    fragment = '''<div class="viz-shell progress-figure" aria-labelledby="progress-heading">
  <header class="viz-heading">
    <div class="viz-kicker">LP solver progress · roughly 2001 to 2020</div>
    <h3 id="progress-heading">Two levers produced about 180 times more speed</h3>
    <p>The factors come from different experiments and should be read as estimates, not physical constants.</p>
  </header>
  <div class="progress-flow" role="img" aria-label="Old LP code gained about twenty times from modern hardware; newer solver software added about nine times; combined estimate about one hundred eighty times">
    <div class="progress-stage"><small>Starting point</small><strong>1×</strong><span>old LP code<br>old hardware</span></div>
    <div class="progress-arrow"><strong>≈20×</strong><span>hardware</span></div>
    <div class="progress-stage"><small>Controlled rerun</small><strong>20×</strong><span>old LP code<br>modern hardware</span></div>
    <div class="progress-arrow"><strong>≈9×</strong><span>software</span></div>
    <div class="progress-stage progress-stage-final"><small>Combined estimate</small><strong>≈180×</strong><span>2020-era virtual-best<br>modern hardware</span></div>
  </div>
  <div class="progress-evidence">
    <span><strong>56 shared LPs</strong>solved by old and new portfolios within 24 hours</span>
    <span><strong>Slowest old-day case → &lt;3 min</strong>for the newer portfolio</span>
  </div>
  <p class="viz-source">Koch, Berthold, Pedersen &amp; Vanaret (2022), §§2.1, 3.2 and 4.1. Candidates taking under 10 seconds on old software or under one second on new software were excluded; remaining sub-second timings were clipped to one second.</p>
</div>'''
    (OUT / "fig6-solver-progress.html").write_text(fragment + "\n", encoding="utf-8")
    return fragment


def write_demo(fragments: list[str]) -> None:
    figures = "\n".join(f"<figure>{fragment}</figure>" for fragment in fragments)
    demo = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Post 02 visualisations</title><link rel="stylesheet" href="visuals.css"></head>
<body class="viz-demo-page"><main><h1>Rows, Columns, and What They Cost — figures</h1>
{figures}
</main><script defer src="article-viz.js"></script></body></html>
'''
    (OUT.parent / "demo.html").write_text(demo, encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    structure_svg = write_structure_svg()
    write_basis_svg()
    model_fragment = write_model_anatomy_fragment()
    structure_fragment = write_structure_fragment(structure_svg)
    basis_fragment = write_basis_fragment()
    routes_fragment = write_routes_fragment()
    fill_fragment = write_fill_fragment()
    klee_minty_fragment = write_klee_minty_fragment()
    solver_progress_fragment = write_solver_progress_fragment()
    write_demo([
        model_fragment,
        structure_fragment,
        basis_fragment,
        routes_fragment,
        fill_fragment,
        klee_minty_fragment,
        solver_progress_fragment,
    ])
    for name in (
        "fig0-model-anatomy.html",
        "fig1-structure-not-size.svg",
        "fig1-structure-not-size.html",
        "fig2-nine-positions.svg",
        "fig2-nine-positions.html",
        "fig3-two-routes.html",
        "fig4-fill-in.html",
        "fig5-klee-minty.html",
        "fig6-solver-progress.html",
    ):
        print(f"wrote {OUT / name}")
    print(f"wrote {OUT.parent / 'demo.html'}")


if __name__ == "__main__":
    main()
