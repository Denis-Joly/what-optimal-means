"""Hand-rolled SVG so the figures inherit the site's own CSS variables.

Colour is doing one job here: separating a small number of marks. The palette
is the site's four-level grey ramp plus the signal red, referenced as CSS
custom properties, so a figure inlined into a page takes its colours from the
stylesheet instead of carrying its own. That is also what makes them work in
dark mode: the ramp is defined relative to the background, so --d4 stays the
most prominent mark whichever way round the page is. Hex fallbacks are supplied
for viewers that open the SVG on its own.

    python3 make_figures.py

Reads out/stigler_duals.csv (written by stigler.py) for figure 2. Figure 1 is
computed here from the same constants blend.py uses.
"""
import csv
import pathlib

import blend

HERE = pathlib.Path(__file__).parent
OUT = HERE / "out"

# The site's light values, from its styleguide. Kept here only as fallbacks:
# inlined into a page, the figures take their colours from the stylesheet, and
# the dark scheme redefines these same tokens.
FALLBACK = {"--d1": "#b4b4ae", "--d2": "#8a8a83", "--d3": "#5c5c56",
            "--d4": "#2b2b28", "--signal": "#d6001c", "--ink": "#0a0a0a",
            "--body": "#1a1a1a", "--muted": "#6b6b6b", "--rule": "#dcdcda",
            "--panel": "#f2f2f0", "--paper": "#ffffff"}


def c(name):
    return f"var({name}, {FALLBACK[name]})"


def head(w, h, title, desc):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="100%" role="img" aria-label="{title}">\n'
            f'<title>{title}</title><desc>{desc}</desc>\n'
            f'<style>text{{font:11px/1.2 "IBM Plex Mono",ui-monospace,monospace;'
            f'fill:{c("--ink")}}} .lbl{{font-size:10px;fill:{c("--muted")}}} '
            f'.tag{{font-size:10px;fill:{c("--d4")}}}</style>\n')


# ------------------------------------------------------------------ figure 1
def fig_polytope(out=OUT / "fig1-blend-polytope.svg"):
    import math

    W, H = 760, 360
    PAD = dict(l=52, r=46, t=26, b=40)
    XMAX, YMAX = 125.0, 76.0

    def px(v):
        return PAD["l"] + v / XMAX * (W - PAD["l"] - PAD["r"])

    def py(v):
        return H - PAD["b"] - v / YMAX * (H - PAD["t"] - PAD["b"])

    verts = blend.vertices()
    cx = sum(v[0] for v in verts) / len(verts)
    cy = sum(v[1] for v in verts) / len(verts)
    verts.sort(key=lambda p: math.atan2(p[1] - cy, p[0] - cx))

    s = head(W, H,
             "The feasible blends, and the cheapest one",
             "A two-variable linear program drawn as a polygon. Every blend "
             "satisfying the batch, protein, fibre and silo constraints lies "
             "inside the shaded region. The cheapest blend sits on a corner.")

    # grid
    for v in range(0, int(YMAX) + 1, 20):
        s += (f'<line x1="{PAD["l"]}" x2="{W-PAD["r"]}" y1="{py(v):.1f}" '
              f'y2="{py(v):.1f}" stroke="{c("--rule")}" stroke-width=".5"/>\n'
              f'<text class="lbl" x="{PAD["l"]-6}" y="{py(v)+3:.1f}" '
              f'text-anchor="end">{v}</text>\n')
    for v in range(0, int(XMAX) + 1, 20):
        s += (f'<text class="lbl" x="{px(v):.1f}" y="{H-PAD["b"]+15}" '
              f'text-anchor="middle">{v}</text>\n')

    # feasible region
    pts = " ".join(f"{px(x):.1f},{py(y):.1f}" for x, y in verts)
    s += f'<polygon points="{pts}" fill="{c("--d1")}" opacity=".28"/>\n'

    def clip(a, b, rhs):
        """The segment of a*x + b*y = rhs inside the axes box."""
        ends = []
        if b:
            for x in (0.0, XMAX):
                y = (rhs - a * x) / b
                if -1e-9 <= y <= YMAX + 1e-9:
                    ends.append((x, y))
        if a:
            for y in (0.0, YMAX):
                x = (rhs - b * y) / a
                if -1e-9 <= x <= XMAX + 1e-9:
                    ends.append((x, y))
        ends = sorted(set((round(p, 6), round(q, 6)) for p, q in ends))
        return ends[0], ends[-1]

    def seg(a, b, rhs, label, t, dash=False, anchor="start"):
        """Draw the constraint boundary and label it at fraction t along it."""
        (x1, y1), (x2, y2) = clip(a, b, rhs)
        d = ' stroke-dasharray="4 3"' if dash else ""
        lx, ly = x1 + t * (x2 - x1), y1 + t * (y2 - y1)
        dx = 8 if anchor == "start" else -8
        return (f'<line x1="{px(x1):.1f}" y1="{py(y1):.1f}" x2="{px(x2):.1f}" '
                f'y2="{py(y2):.1f}" stroke="{c("--d3")}" stroke-width="1"{d}/>\n'
                f'<text class="tag" x="{px(lx)+dx:.1f}" y="{py(ly)-5:.1f}" '
                f'text-anchor="{anchor}">{label}</text>\n')

    s += seg(0, 1, blend.CORN_MAX, "silo &#8804; 60 lb corn", 0.06)
    s += seg(1, 1, blend.BATCH_MIN, "batch &#8805; 100 lb", 0.62, anchor="end")
    s += seg(blend.PROTEIN["soybean"], blend.PROTEIN["corn"],
             blend.PROTEIN_MIN, "protein &#8805; 30 lb", 0.72, anchor="end")
    s += seg(blend.FIBRE["soybean"], blend.FIBRE["corn"],
             blend.FIBRE_MAX, "fibre &#8804; 7 lb", 0.55)

    # iso-cost line through the optimum
    _, sol = blend.solve()
    ox, oy = sol["soybean"], sol["corn"]
    cost = blend.COST["soybean"] * ox + blend.COST["corn"] * oy
    s += seg(blend.COST["soybean"], blend.COST["corn"], cost,
             f"every blend on this line costs ${cost:.2f}", 0.56,
             dash=True, anchor="end")

    # corners, cost labels pushed outward from the centroid
    for x, y in verts:
        cc = blend.COST["soybean"] * x + blend.COST["corn"] * y
        best = abs(cc - cost) < 1e-6
        s += (f'<circle cx="{px(x):.1f}" cy="{py(y):.1f}" r="{4.5 if best else 3}" '
              f'fill="{c("--signal") if best else c("--paper")}" '
              f'stroke="{c("--d4")}" stroke-width="1"/>\n')
        if not best:
            # offset in pixel space, straight out from the centroid
            ux, uy = px(x) - px(cx), py(y) - py(cy)
            n = math.hypot(ux, uy) or 1
            if y < 1e-6:          # on the x axis: label above, not under the ticks
                lx, ly = px(x) + (22 if ux > 0 else -22), py(y) - 11
            else:
                lx = min(max(px(x) + 28 * ux / n, PAD["l"] + 18), W - 22)
                ly = py(y) + 26 * uy / n + 3
            s += (f'<text class="lbl" x="{lx:.1f}" y="{ly:.1f}" '
                  f'text-anchor="middle">${cc:.2f}</text>\n')
    s += (f'<text x="{px(ox)+11:.1f}" y="{py(oy)+4:.1f}" '
          f'fill="{c("--signal")}" style="font-size:11px">'
          f'{ox:.0f} lb soybean, {oy:.0f} lb corn &#8212; ${cost:.2f}</text>\n')

    # axes
    s += (f'<line x1="{PAD["l"]}" y1="{py(0):.1f}" x2="{W-PAD["r"]}" '
          f'y2="{py(0):.1f}" stroke="{c("--d4")}" stroke-width="1"/>\n'
          f'<line x1="{PAD["l"]}" y1="{PAD["t"]}" x2="{PAD["l"]}" '
          f'y2="{py(0):.1f}" stroke="{c("--d4")}" stroke-width="1"/>\n')
    s += (f'<text class="lbl" x="{(PAD["l"]+W-PAD["r"])/2:.0f}" y="{H-4}" '
          f'text-anchor="middle">soybean meal, lb</text>\n'
          f'<text class="lbl" x="14" y="{(PAD["t"]+py(0))/2:.0f}" '
          f'transform="rotate(-90 14 {(PAD["t"]+py(0))/2:.0f})" '
          f'text-anchor="middle">corn meal, lb</text>\n')

    out.write_text(s + "</svg>\n")
    print("wrote", out)


# ------------------------------------------------------------------ figure 2
def fig_certificate(out=OUT / "fig2-what-the-diet-pays-for.svg"):
    """The dual solution, drawn as the thing it actually is: a decomposition
    of the daily cost into what each nutritional requirement is responsible
    for. Shadow price times requirement, summed over the nine constraints,
    equals the cost of the diet exactly. That identity is the proof."""
    W, H = 760, 172
    PAD = dict(l=20, r=52, t=46, b=56)

    allowances = dict(calories_kcal_thousands=3.0, protein_g=70.0,
                      calcium_g=0.8, iron_mg=12.0, vitamin_a_kiu=5.0,
                      thiamine_mg=1.8, riboflavin_mg=2.7, niacin_mg=18.0,
                      ascorbic_acid_mg=75.0)
    pretty = {"calories_kcal_thousands": "calories", "protein_g": "protein",
              "calcium_g": "calcium", "iron_mg": "iron",
              "vitamin_a_kiu": "vitamin A", "thiamine_mg": "thiamine",
              "riboflavin_mg": "riboflavin", "niacin_mg": "niacin",
              "ascorbic_acid_mg": "vitamin C"}

    with (OUT / "stigler_duals.csv").open() as fh:
        rows = list(csv.DictReader(fh))
    share = [(pretty[r["nutrient"]],
              float(r["shadow_price_usd_per_day"]) * allowances[r["nutrient"]])
             for r in rows]
    total = sum(v for _, v in share)
    share = [(n, v) for n, v in sorted(share, key=lambda kv: -kv[1]) if v > 1e-9]
    idle = [pretty[r["nutrient"]] for r in rows
            if float(r["shadow_price_usd_per_day"]) <= 1e-9]

    s = head(W, H,
             "What each of the nine nutritional minimums costs per day",
             "A single horizontal bar, the daily cost of the cheapest diet, "
             "split into the contribution of each binding constraint. Four of "
             "the nine minimums contribute nothing.")

    bw = W - PAD["l"] - PAD["r"]
    y0, bh = PAD["t"], H - PAD["t"] - PAD["b"]
    fills = [c("--d4"), c("--d3"), c("--d2"), c("--d1"), c("--rule")]
    x = PAD["l"]
    for i, (name, v) in enumerate(share):
        w = v / total * bw
        s += (f'<rect x="{x:.1f}" y="{y0}" width="{w:.1f}" height="{bh}" '
              f'fill="{fills[i % len(fills)]}" stroke="{c("--paper")}" '
              f'stroke-width="1"/>\n')
        if w > 46:
            s += (f'<text x="{x + w/2:.1f}" y="{y0 + bh/2 + 4:.0f}" '
                  f'text-anchor="middle" '
                  f'fill="{c("--paper") if i < 2 else c("--ink")}">'
                  f'{name}</text>\n')
            s += (f'<text class="lbl" x="{x + w/2:.1f}" y="{y0 - 8:.0f}" '
                  f'text-anchor="middle">{v*100:.2f}&#162;</text>\n')
        else:
            s += (f'<text class="lbl" x="{x + w/2:.1f}" y="{y0 + bh + 14:.0f}" '
                  f'text-anchor="middle">{name}</text>\n'
                  f'<text class="lbl" x="{x + w/2:.1f}" y="{y0 - 8:.0f}" '
                  f'text-anchor="middle">{v*100:.2f}&#162;</text>\n')
        x += w

    s += (f'<text x="{PAD["l"]}" y="20">the whole bar is '
          f'{total*100:.2f}&#162; a day, which is the price of the diet</text>\n')
    s += (f'<text class="lbl" x="{W-PAD["r"]}" y="{H-8}" text-anchor="end">'
          f'costing nothing at the margin: {", ".join(idle)}</text>\n')

    out.write_text(s + "</svg>\n")
    print("wrote", out)


# ------------------------------------------------------------------ figure 3
def fig_saddle(out=OUT / "fig3-saddle.svg"):
    """What a saddle point is, in the only way that matters here: the same
    point is a minimum along one direction and a maximum along another, and
    the gradient is zero either way. A first-order condition cannot tell the
    two panels apart."""
    W, H = 760, 250
    s = head(W, H,
             "A saddle point, in two slices",
             "Two small plots of the surface z = x squared minus y squared "
             "through the same point. Along one direction the point is the "
             "bottom of a curve; along the other it is the top.")

    panels = [
        (60, "slice along x:  z = x&#178;", "a minimum", +1),
        (415, "slice along y:  z = &#8722;y&#178;", "a maximum", -1),
    ]
    pw, ph, top = 285, 140, 62
    for x0, title, verdict, sign in panels:
        mid = top + ph / 2
        s += (f'<text x="{x0}" y="{top-24}">{title}</text>\n'
              f'<line x1="{x0}" y1="{mid:.0f}" x2="{x0+pw}" y2="{mid:.0f}" '
              f'stroke="{c("--rule")}" stroke-width=".5"/>\n')
        pts = []
        for i in range(61):
            t = -1 + 2 * i / 60
            pts.append(f"{x0 + pw*(t+1)/2:.1f},{mid - sign*(t*t)*ph/2 + sign*ph/4:.1f}")
        s += (f'<polyline points="{" ".join(pts)}" fill="none" '
              f'stroke="{c("--d4")}" stroke-width="1.6"/>\n')
        cx0, cy0 = x0 + pw / 2, mid + sign * ph / 4
        s += (f'<circle cx="{cx0:.1f}" cy="{cy0:.1f}" r="4.5" '
              f'fill="{c("--signal")}"/>\n'
              f'<line x1="{cx0-46:.1f}" y1="{cy0:.1f}" x2="{cx0+46:.1f}" '
              f'y2="{cy0:.1f}" stroke="{c("--signal")}" stroke-width="1" '
              f'stroke-dasharray="3 3"/>\n'
              f'<text class="tag" x="{cx0:.1f}" y="{cy0 + (24 if sign>0 else -14):.1f}" '
              f'text-anchor="middle">{verdict}</text>\n')

    s += (f'<text class="lbl" x="{W/2:.0f}" y="{H-14}" text-anchor="middle">'
          f'the same point, and a flat tangent in both cases, which is why a '
          f'first-order condition cannot separate them</text>\n')
    out.write_text(s + "</svg>\n")
    print("wrote", out)


# ------------------------------------------------------------------ figure 4
def fig_two_tracks(out=OUT / "fig4-two-tracks.svg"):
    """Two origin stories on parallel rails, with no rung between them."""
    W, H = 760, 236
    L, R = 96, W - 26
    Y1, Y2 = 76, 168

    def x(year):
        return L + (year - 1937) / (1976 - 1937) * (R - L)

    s = head(W, H,
             "Two origins, no contact",
             "A timeline with two parallel tracks, Leningrad from 1938 and "
             "Washington from 1946, converging on the same mathematics and "
             "meeting the Nobel committee in 1975 without ever meeting each "
             "other.")

    for y, name in [(Y1, "Leningrad"), (Y2, "Washington")]:
        s += (f'<line x1="{L}" y1="{y}" x2="{R}" y2="{y}" '
              f'stroke="{c("--d3")}" stroke-width="1"/>\n'
              f'<text class="tag" x="{L-10}" y="{y+4}" text-anchor="end">'
              f'{name}</text>\n')

    events = [
        (Y1, 1938.5, "1938&#8211;39", "the Plywood Trust asks, and the booklet follows", -1, "start"),
        (Y1, 1975, "1975", "Nobel, shared with Koopmans", -1, "end"),
        (Y2, 1946.5, "1946&#8211;47", "the Air Force asks, then von Neumann answers", 1, "start"),
        (Y2, 1975, "1975", "National Medal of Science", 1, "end"),
    ]
    for y, year, when, label, side, anchor in events:
        s += (f'<circle cx="{x(year):.1f}" cy="{y}" r="4" '
              f'fill="{c("--paper")}" stroke="{c("--d4")}" stroke-width="1.2"/>\n')
        ty = y - 14 if side < 0 else y + 20
        tx = x(year) + (-6 if anchor == "start" else 6)
        tx = x(year) + (6 if anchor == "start" else -6)
        s += (f'<text class="tag" x="{tx:.1f}" y="{ty}" text-anchor="{anchor}">'
              f'{when}</text>\n'
              f'<text class="lbl" x="{tx:.1f}" y="{ty + (-14 if side < 0 else 14)}" '
              f'text-anchor="{anchor}">{label}</text>\n')

    s += (f'<text x="{L}" y="26">The same mathematics, invented twice, eight '
          f'years and one iron curtain apart.</text>\n')
    s += (f'<text class="lbl" x="{R}" y="{H-10}" text-anchor="end">'
          f'no rung between the two rails</text>\n')
    out.write_text(s + "</svg>\n")
    print("wrote", out)


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    fig_polytope()
    fig_certificate()
    fig_saddle()
    fig_two_tracks()
