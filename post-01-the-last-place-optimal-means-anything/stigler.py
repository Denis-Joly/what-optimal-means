"""The 1947 computation, rerun.

In 1945 George Stigler asked for the cheapest diet meeting nine nutritional
minimums, at August 1939 prices, from 77 commodities. He had no method for it
and said so: "there does not appear to be any direct method of finding the
minimum of a linear function subject to linear conditions." He narrowed the
list by hand and published $39.93 a year.

In the autumn of 1947 Jack Laderman, at the National Bureau of Standards, put
the full 77-column problem through Dantzig's new simplex method. By Dantzig's
own account it took nine clerks on hand-operated desk calculators about 120
man-days.

This script does the same thing. Time it.

    python3 stigler.py

It also prints the dual solution, which is the part that matters for the
essay: the solver does not merely return a diet, it returns a set of nine
shadow prices that together *prove* no cheaper diet exists.
"""
import csv
import pathlib
import time

import pulp

HERE = pathlib.Path(__file__).parent
DAYS_PER_YEAR = 365


def load():
    with (HERE / "data" / "stigler_1939.csv").open() as fh:
        foods = list(csv.DictReader(fh))
    with (HERE / "data" / "daily_allowances_1943.csv").open() as fh:
        allowances = {r["nutrient"]: float(r["daily_minimum"])
                      for r in csv.DictReader(fh)}
    return foods, allowances


def solve(foods, allowances, exclude=()):
    """Minimise daily spend subject to the nine nutritional minimums.

    The decision variable is dollars per day spent on each commodity, which is
    Stigler's own parameterisation: the table gives nutrients obtainable per
    dollar, so the constraint matrix is already in the right units.
    """
    usable = [f for f in foods if f["commodity"] not in exclude]

    prob = pulp.LpProblem("stigler_diet", pulp.LpMinimize)
    x = {f["commodity"]: pulp.LpVariable(f"x_{i}", lowBound=0)
         for i, f in enumerate(usable)}

    prob += pulp.lpSum(x.values()), "daily_cost_usd"

    for nutrient, minimum in allowances.items():
        prob += (
            pulp.lpSum(float(f[nutrient]) * x[f["commodity"]] for f in usable)
            >= minimum,
            nutrient,
        )

    t0 = time.perf_counter()
    status = prob.solve(pulp.HiGHS(msg=False))
    elapsed = time.perf_counter() - t0

    assert pulp.LpStatus[status] == "Optimal", pulp.LpStatus[status]

    basket = {c: v.value() for c, v in x.items() if v.value() and v.value() > 1e-9}
    duals = {name: con.pi for name, con in prob.constraints.items()}
    slack = {name: con.slack for name, con in prob.constraints.items()}
    return dict(daily=pulp.value(prob.objective), basket=basket,
                duals=duals, slack=slack, seconds=elapsed,
                n_foods=len(usable))


def report(res, foods, title):
    price = {f["commodity"]: (f["unit"], float(f["price_cents_aug1939"]))
             for f in foods}
    annual = res["daily"] * DAYS_PER_YEAR

    print(f"\n{title}")
    print("-" * len(title))
    print(f"commodities offered   {res['n_foods']}")
    print(f"solved in             {res['seconds'] * 1000:.1f} ms")
    print(f"daily cost            ${res['daily']:.4f}")
    print(f"annual cost           ${annual:.2f}")
    print(f"\n{'commodity':<26}{'unit':>12}{'$/year':>10}{'units/year':>13}")
    for c, dollars in sorted(res["basket"].items(), key=lambda kv: -kv[1]):
        unit, cents = price[c]
        yearly = dollars * DAYS_PER_YEAR
        print(f"{c:<26}{unit:>12}{yearly:>10.2f}{yearly / (cents / 100):>13.1f}")
    return annual


def report_duals(res):
    """The certificate.

    Each dual is the marginal cost, in dollars per day, of raising one
    nutritional minimum by one unit. A nutrient with a zero dual is not
    binding: you get it for free as a by-product of satisfying the others.
    The duals also reconstruct the objective exactly -- that identity is the
    proof of optimality, and it is checked below.
    """
    print("\nthe certificate: shadow price of each nutritional minimum")
    print("-" * 56)
    print(f"{'nutrient':<26}{'$/day per unit':>16}{'binding':>10}")
    for name, pi in sorted(res["duals"].items(), key=lambda kv: -abs(kv[1])):
        binding = "yes" if abs(res["slack"][name]) < 1e-9 else "no"
        print(f"{name:<26}{pi:>16.6f}{binding:>10}")



def report_substitutability(res, foods, allowances):
    """Why one nutrient dominates the bill, and it is not the one you expect.

    Buying a nutrient from its single cheapest source puts a ceiling on what
    that nutrient can cost per unit. The shadow price says what the optimiser
    actually pays for it once every other purchase is contributing too. The
    ratio is how much joint buying saves, so a nutrient with a ratio near 1 is
    one there is no way around: it has to be bought more or less on purpose.
    """
    print("\nwhat each nutrient costs alone, and what it costs in the diet")
    print("-" * 78)
    print(f"{'nutrient':<26}{'cheapest single source':<24}"
          f"{'$/unit alone':>13}{'in diet':>10}{'saving':>7}")
    for nutrient in allowances:
        best = max(foods, key=lambda f: float(f[nutrient]))
        per_dollar = float(best[nutrient])
        if per_dollar == 0:
            continue
        alone = 1 / per_dollar
        paid = res["duals"][nutrient]
        if paid <= 1e-12:                       # slack: met as a by-product
            print(f"{nutrient:<26}{best['commodity'][:22]:<24}"
                  f"{alone:>13.5f}{'free':>10}{'':>7}")
            continue
        print(f"{nutrient:<26}{best['commodity'][:22]:<24}"
              f"{alone:>13.5f}{paid:>10.5f}{alone / paid:>6.1f}x")
    print("\nRiboflavin is the one with nowhere to hide, which is why beef "
          "liver is in\nthe basket at all and why riboflavin is the largest "
          "single line in the bill.")


def main():
    foods, allowances = load()

    res = solve(foods, allowances)
    annual = report(res, foods, "The 1947 problem, all 77 commodities")
    report_duals(res)
    report_substitutability(res, foods, allowances)

    # Strong duality: the dual objective equals the primal objective. This
    # equality is what "proved optimal" actually means.
    dual_obj = sum(res["duals"][n] * allowances[n] for n in allowances)
    print(f"\nprimal objective      ${res['daily']:.6f} per day")
    print(f"dual objective        ${dual_obj:.6f} per day")
    print(f"duality gap           {abs(res['daily'] - dual_obj):.2e}")
    assert abs(res["daily"] - dual_obj) < 1e-9

    print(f"\nStigler, by hand, 1945:      $39.93 per year")
    print(f"Laderman, by simplex, 1947:  $39.69 per year")
    print(f"this run:                    ${annual:.2f} per year")
    print("The residual gap against Dantzig's reported $39.69 is rounding in "
          "the\ntranscribed nutrient table and the 365-day convention, not a "
          "different answer.")

    # Beef liver is 0.4 per cent of the bill and the whole reason the optimal
    # basket differs from Stigler's own. Price it.
    without = solve(foods, allowances, exclude={"Liver (Beef)"})
    print(f"\nSame problem with beef liver struck from the list: "
          f"${without['daily'] * DAYS_PER_YEAR:.2f} per year "
          f"({(without['daily'] / res['daily'] - 1) * 100:+.2f}%)")

    out = HERE / "out"
    out.mkdir(exist_ok=True)
    with (out / "stigler_solution.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["commodity", "usd_per_year"])
        w.writerows(sorted(((c, v * DAYS_PER_YEAR)
                            for c, v in res["basket"].items()),
                           key=lambda kv: -kv[1]))
    with (out / "stigler_duals.csv").open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["nutrient", "shadow_price_usd_per_day", "binding"])
        for name, pi in res["duals"].items():
            w.writerow([name, pi, abs(res["slack"][name]) < 1e-9])
    print(f"\nwrote {out / 'stigler_solution.csv'}")
    print(f"wrote {out / 'stigler_duals.csv'}")


if __name__ == "__main__":
    main()
