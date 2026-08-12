#!/usr/bin/env python3
"""Build the static and interactive visualisations for Post 2.

The SVG files are complete, shareable fallbacks for GitHub and social use.
The HTML fragments progressively enhance inside the article: the Netlib chart
becomes an explorable metric switch, while the basis diagram uses native radio
controls and CSS only. No runtime library or network request is required.
"""

from __future__ import annotations

import html
import json
import statistics
from pathlib import Path

from analyze_structure import OUT, inclusive_quartiles, load_netlib, stigler_problem


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


def write_demo(structure_fragment: str, basis_fragment: str) -> None:
    demo = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Post 02 visualisations</title><link rel="stylesheet" href="visuals.css"></head>
<body class="viz-demo-page"><main><h1>Rows, Columns, and What They Cost — figures</h1>
<figure>{structure_fragment}</figure><figure>{basis_fragment}</figure>
</main><script defer src="article-viz.js"></script></body></html>
'''
    (OUT.parent / "demo.html").write_text(demo, encoding="utf-8")


def main() -> None:
    OUT.mkdir(exist_ok=True)
    structure_svg = write_structure_svg()
    write_basis_svg()
    structure_fragment = write_structure_fragment(structure_svg)
    basis_fragment = write_basis_fragment()
    write_demo(structure_fragment, basis_fragment)
    for name in (
        "fig1-structure-not-size.svg",
        "fig1-structure-not-size.html",
        "fig2-nine-positions.svg",
        "fig2-nine-positions.html",
    ):
        print(f"wrote {OUT / name}")
    print(f"wrote {OUT.parent / 'demo.html'}")


if __name__ == "__main__":
    main()
