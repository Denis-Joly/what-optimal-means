#!/usr/bin/env python3
"""Build the static, accessible figure used by Post 5."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
OUT_DIR = ROOT / "out"
RESULTS_PATH = OUT_DIR / "results.json"


def svg_document(results: dict) -> str:
    runs = results["runs"]
    colours = ["#7b8794", "#d08b32", "#168579"]
    rows = []
    chart_left = 246
    chart_width = 500

    for position, (run, colour) in enumerate(zip(runs, colours, strict=True)):
        y = 190 + 105 * position
        value = max(0.0, float(run["profit"]))
        width = chart_width * value / 400.0
        label = html.escape(run["label"])
        start_index = run["start_index"]
        rows.extend(
            [
                f'<text class="row-label" x="36" y="{y + 2}">{label}</text>',
                f'<text class="row-sub" x="36" y="{y + 25}">fixed start #{start_index}</text>',
                f'<line class="track" x1="{chart_left}" y1="{y}" x2="{chart_left + chart_width}" y2="{y}"/>',
            ]
        )
        if width < 2:
            rows.append(
                f'<circle cx="{chart_left}" cy="{y}" r="7" fill="{colour}" aria-hidden="true"/>'
            )
        else:
            rows.append(
                f'<rect x="{chart_left}" y="{y - 12}" width="{width:.2f}" height="24" rx="12" fill="{colour}"/>'
            )
        value_x = chart_left + max(width, 16) + 12
        if value_x > 708:
            value_x = 700
        rows.append(
            f'<text class="value" x="{value_x:.2f}" y="{y + 5}">${value:.0f}</text>'
        )
        rows.extend(
            [
                f'<rect class="status-pill" x="795" y="{y - 15}" width="88" height="30" rx="15"/>',
                f'<text class="status" x="839" y="{y + 5}" text-anchor="middle">success</text>',
            ]
        )

    ticks = []
    for value in range(0, 401, 100):
        x = chart_left + chart_width * value / 400
        ticks.extend(
            [
                f'<line class="grid" x1="{x:.2f}" y1="138" x2="{x:.2f}" y2="420"/>',
                f'<text class="tick" x="{x:.2f}" y="124" text-anchor="middle">${value}</text>',
            ]
        )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 920 520" role="img" aria-labelledby="post5-fig1-title post5-fig1-desc">
  <title id="post5-fig1-title">Three successful local-solver terminations on the Haverly pooling problem</title>
  <desc id="post5-fig1-desc">Horizontal comparison of three SLSQP runs. Fixed start 7 returns zero dollars, fixed start 8 returns one hundred dollars, and fixed start 0 returns four hundred dollars. Every run has solver status success. Only the four-hundred-dollar result is independently documented as globally optimal.</desc>
  <style>
    text {{ font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; fill: #23313d; }}
    .eyebrow {{ font-size: 13px; font-weight: 750; letter-spacing: .12em; text-transform: uppercase; fill: #5a6975; }}
    .headline {{ font-family: Georgia, "Times New Roman", serif; font-size: 29px; font-weight: 700; }}
    .subhead {{ font-size: 15px; fill: #5a6975; }}
    .grid {{ stroke: #dce3e8; stroke-width: 1; }}
    .track {{ stroke: #dce3e8; stroke-width: 24; stroke-linecap: round; }}
    .tick {{ font-size: 12px; fill: #65737e; }}
    .row-label {{ font-size: 15px; font-weight: 720; }}
    .row-sub {{ font-size: 12px; fill: #65737e; }}
    .value {{ font-size: 15px; font-weight: 780; }}
    .status-pill {{ fill: #e3f3ed; stroke: #84b9a7; }}
    .status {{ font-size: 12px; font-weight: 750; fill: #176c5a; }}
    .global-note {{ font-size: 13px; font-weight: 720; fill: #176c5a; }}
    .global-line {{ stroke: #168579; stroke-width: 1.5; stroke-dasharray: 4 4; }}
    @media (prefers-color-scheme: dark) {{
      text {{ fill: #e9eef2; }}
      .eyebrow, .subhead, .tick, .row-sub {{ fill: #a9b4bd; }}
      .grid {{ stroke: #394750; }}
      .track {{ stroke: #394750; }}
      .status-pill {{ fill: #153f37; stroke: #3f8877; }}
      .status, .global-note {{ fill: #77d1bc; }}
      .global-line {{ stroke: #77d1bc; }}
    }}
  </style>
  <rect width="920" height="520" rx="18" fill="transparent"/>
  <text class="eyebrow" x="36" y="38">same model · same method · different starts</text>
  <text class="headline" x="36" y="76">A success message is not a global bound</text>
  <text class="subhead" x="36" y="103">Haverly pooling data · SciPy SLSQP · fixed seed 20260820</text>
  {''.join(ticks)}
  {''.join(rows)}
  <line class="global-line" x1="746" y1="138" x2="746" y2="449"/>
  <text class="global-note" x="746" y="474" text-anchor="end">independently documented global optimum</text>
  <text class="subhead" x="36" y="505">“success” records the local solver's stopping test, not a proof over the full feasible region.</text>
</svg>'''


def html_fragment(svg: str, results: dict) -> str:
    scipy_version = html.escape(results["runtime"]["scipy"])
    return f'''<figure class="fig fig-wide post5-local-successes">
  <style>
    .post5-local-successes .post5-mobile-hint {{ display: none; }}
    .post5-local-successes .post5-chart-scroll {{ overflow-x: auto; -webkit-overflow-scrolling: touch; }}
    .post5-local-successes svg {{ display: block; width: 100%; height: auto; }}
    @media (max-width: 680px) {{
      .post5-local-successes .post5-mobile-hint {{ display: block; margin: 0 0 .5rem; color: var(--muted, #65737e); font-size: .82rem; }}
      .post5-local-successes svg {{ min-width: 680px; }}
    }}
  </style>
  <p class="post5-mobile-hint" aria-hidden="true">Scroll horizontally to inspect all three solver outcomes →</p>
  <div class="post5-chart-scroll" tabindex="0" role="region" aria-label="Scrollable comparison of three local-solver outcomes">
    {svg}
  </div>
  <figcaption><strong>Figure 1 — Three successful terminations are not one global certificate.</strong> Using Haverly's data, the same SLSQP configuration returns feasible plans worth $0, $100 and $400 from three fixed starting points. All three runs report <code>success</code>. The $400 label comes from an independent global benchmark, not from SLSQP's local status. SciPy {scipy_version}; fixed seed 20260820.</figcaption>
</figure>
'''


def main() -> None:
    results = json.loads(RESULTS_PATH.read_text(encoding="utf-8"))
    svg = svg_document(results)
    fragment = html_fragment(svg, results)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "fig1-local-successes.svg").write_text(svg + "\n", encoding="utf-8")
    (OUT_DIR / "fig1-local-successes.html").write_text(fragment, encoding="utf-8")
    demo = f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Post 5 figure preview</title>
  <style>
    body {{ margin: 0; background: #f3f0e8; color: #23313d; font: 17px/1.55 Georgia, serif; }}
    main {{ max-width: 1040px; margin: 4rem auto; padding: 0 1.25rem; }}
    figure {{ margin: 0; padding: 1.25rem; background: #fff; border: 1px solid #dce3e8; border-radius: 18px; }}
    figcaption {{ margin-top: 1rem; color: #52616c; }}
    @media (prefers-color-scheme: dark) {{
      body {{ background: #10181d; color: #e9eef2; }}
      figure {{ background: #172229; border-color: #394750; }}
      figcaption {{ color: #b6c0c8; }}
    }}
  </style>
</head>
<body><main>{fragment}</main></body>
</html>
'''
    (ROOT / "demo.html").write_text(demo, encoding="utf-8")


if __name__ == "__main__":
    main()
