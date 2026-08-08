"""The smallest interesting linear program: two variables, so it can be drawn.

A feed producer blends soybean meal and corn meal into a daily batch. Soybean
meal costs more and carries more protein and more fibre. The batch must reach
a size, clear a protein floor, stay under a fibre ceiling, and use no more
corn meal than the silo holds.

Two variables means the feasible set is a polygon on a page, and the optimum
sits on one of its corners. That is not a coincidence and it is the reason the
simplex method works by walking from corner to corner.

    python3 blend.py
"""
import itertools
import pathlib

import pulp

HERE = pathlib.Path(__file__).parent

COST = {"soybean": 0.50, "corn": 0.18}          # dollars per lb
PROTEIN = {"soybean": 0.44, "corn": 0.09}       # lb protein per lb
FIBRE = {"soybean": 0.06, "corn": 0.02}         # lb fibre per lb
BATCH_MIN = 100.0                               # lb
PROTEIN_MIN = 30.0                              # lb
FIBRE_MAX = 7.0                                 # lb
CORN_MAX = 60.0                                 # lb, silo capacity


def solve():
    prob = pulp.LpProblem("feed_blend", pulp.LpMinimize)
    x = {k: pulp.LpVariable(k, lowBound=0) for k in COST}

    prob += pulp.lpSum(COST[k] * x[k] for k in COST), "cost_usd"
    prob += pulp.lpSum(x.values()) >= BATCH_MIN, "batch"
    prob += pulp.lpSum(PROTEIN[k] * x[k] for k in COST) >= PROTEIN_MIN, "protein"
    prob += pulp.lpSum(FIBRE[k] * x[k] for k in COST) <= FIBRE_MAX, "fibre"
    prob += x["corn"] <= CORN_MAX, "silo"

    prob.solve(pulp.HiGHS(msg=False))
    assert pulp.LpStatus[prob.status] == "Optimal"
    return prob, {k: v.value() for k, v in x.items()}


def vertices():
    """Every corner of the feasible polygon, found the slow honest way.

    Take the constraint boundaries two at a time, intersect them, keep the
    intersections that satisfy everything else. For two variables this is
    cheap; in a real model it is hopeless, which is the whole point of having
    an algorithm.
    """
    lines = [
        (1.0, 1.0, BATCH_MIN),                       # x + y = 100
        (PROTEIN["soybean"], PROTEIN["corn"], PROTEIN_MIN),
        (FIBRE["soybean"], FIBRE["corn"], FIBRE_MAX),
        (0.0, 1.0, CORN_MAX),                        # y = 60
        (1.0, 0.0, 0.0),                             # x = 0
        (0.0, 1.0, 0.0),                             # y = 0
    ]
    found = []
    for (a1, b1, c1), (a2, b2, c2) in itertools.combinations(lines, 2):
        det = a1 * b2 - a2 * b1
        if abs(det) < 1e-12:
            continue
        x = (c1 * b2 - c2 * b1) / det
        y = (a1 * c2 - a2 * c1) / det
        if x < -1e-9 or y < -1e-9:
            continue
        if (x + y < BATCH_MIN - 1e-9
                or PROTEIN["soybean"] * x + PROTEIN["corn"] * y < PROTEIN_MIN - 1e-9
                or FIBRE["soybean"] * x + FIBRE["corn"] * y > FIBRE_MAX + 1e-9
                or y > CORN_MAX + 1e-9):
            continue
        found.append((round(x, 6), round(y, 6)))
    return sorted(set(found))


def main():
    prob, sol = solve()
    cost = pulp.value(prob.objective)

    print("optimal blend")
    print("-------------")
    for k, v in sol.items():
        print(f"  {k:<10}{v:>8.2f} lb")
    print(f"  {'cost':<10}${cost:>7.2f}")

    print("\nconstraints at the optimum")
    print("--------------------------")
    print(f"{'name':<10}{'slack':>10}{'shadow price':>15}")
    for name, con in prob.constraints.items():
        print(f"{name:<10}{con.slack:>10.3f}{con.pi:>15.4f}")

    print("\nevery corner of the feasible polygon")
    print("------------------------------------")
    print(f"{'soybean':>10}{'corn':>10}{'cost':>10}")
    for x, y in vertices():
        c = COST["soybean"] * x + COST["corn"] * y
        star = "  <- optimum" if abs(c - cost) < 1e-6 else ""
        print(f"{x:>10.2f}{y:>10.2f}{c:>10.2f}{star}")
    print("\nThe cheapest corner is the cheapest point. That is the theorem "
          "the\nsimplex method exploits: it never looks anywhere else.")


if __name__ == "__main__":
    main()
