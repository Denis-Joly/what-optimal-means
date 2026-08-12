# Post 1 — The Last Place "Optimal" Means Anything

Three things run here.

## 1. The 1947 computation, rerun

`stigler.py` solves the problem George Stigler posed in 1945: the cheapest
diet meeting nine nutritional minimums, at August 1939 prices, chosen from 77
commodities. Stigler had no method for it and said so in the paper. He
narrowed the list by hand and published **$39.93 a year**.

In the autumn of 1947 Jack Laderman, at the National Bureau of Standards, put
the full 77-column problem through Dantzig's new simplex method. By Dantzig's
own later account it took nine clerks on hand-operated desk calculators about
120 man-days, and the answer was **$39.69**.

```
$ python3 stigler.py

The 1947 problem, all 77 commodities
------------------------------------
commodities offered   77
solved in             2.9 ms
daily cost            $0.1087
annual cost           $39.66

commodity                         unit    $/year   units/year
Navy Beans, Dried                1 lb.     22.28        377.5
Wheat Flour (Enriched)          10 lb.     10.77         29.9
Cabbage                          1 lb.      4.09        110.6
Spinach                          1 lb.      1.83         22.6
Liver (Beef)                     1 lb.      0.69          2.6
```

That block is pasted from the committed `out/stigler.txt`, which `make`
rewrites, so the timing is whatever this machine last did rather than a
number typed in by hand. It has landed anywhere between two and nine
milliseconds. Same five commodities and the same quantities Garille
and Gass report for the 1947 solution, to within the rounding in the transcribed table. Note what is
*not* in the basket: the evaporated milk that appears in Stigler's own
published diet. The optimum swaps it for two and a half pounds of beef liver
a year. Strike the liver from the list and the diet costs 0.35 per cent more,
which the script also computes.

The residual three cents against Dantzig's $39.69 is rounding in the nutrient
table and the 365-day convention. It is not a different answer.

The constraint matrix has nine nutrient rows and 77 food columns. Of its 693
entries, 570 are non-zero: 82.3 per cent. That percentage is descriptive, but
it is not a measure of solve difficulty; it depends mechanically on the small
number of rows. [Post 2](https://spatium-novum.com/posts/rows-columns-and-what-they-cost)
compares the same matrix with Netlib using one explicit counting convention.

## 2. The certificate

The part the post is actually about. The solver does not only return a diet;
it returns nine shadow prices, one per nutritional minimum, and the sum of
price times requirement over those nine equals the cost of the diet exactly.
That equality is what "proved optimal" means — nothing external has to check
the answer, the two halves of the solution check each other.

```
the certificate: shadow price of each nutritional minimum
---------------------------------------------------------
nutrient                    $/day per unit   binding
calcium_g                         0.031738       yes
riboflavin_mg                     0.016358       yes
calories_kcal_thousands           0.008765       yes
vitamin_a_kiu                     0.000400       yes
ascorbic_acid_mg                  0.000144       yes
protein_g                        -0.000000        no
iron_mg                          -0.000000        no
thiamine_mg                      -0.000000        no
niacin_mg                        -0.000000        no

primal objective      $0.108662 per day
dual objective        $0.108662 per day
duality gap           0.00e+00
```

Four of the nine minimums cost nothing at the margin: you get the protein,
iron, thiamine and niacin for free as a by-product of buying the rest.
Riboflavin, not calories, is the single most expensive thing about being
alive in 1939.


## 2b. Why riboflavin, and not calories

The script also prints the answer to the question the post's figure provokes.
Buying a nutrient from its single cheapest source puts a ceiling on its price
per unit; the shadow price says what the diet actually pays once everything
else is contributing too. The ratio is what joint buying saves.

```
what each nutrient costs alone, and what it costs in the diet
------------------------------------------------------------------------------
nutrient                  cheapest single source   $/unit alone   in diet saving
calories_kcal_thousands   Wheat Flour (Enriched)        0.02237   0.00877   2.6x
protein_g                 Navy Beans, Dried             0.00059      free       
calcium_g                 Cheese (Cheddar)              0.06098   0.03174   1.9x
iron_mg                   Navy Beans, Dried             0.00126      free       
vitamin_a_kiu             Spinach                       0.00109   0.00040   2.7x
thiamine_mg               Wheat Flour (Enriched)        0.01805      free       
riboflavin_mg             Liver (Beef)                  0.01969   0.01636   1.2x
niacin_mg                 Peanut Butter                 0.00212      free       
ascorbic_acid_mg          Cabbage                       0.00019   0.00014   1.3x

Riboflavin is the one with nowhere to hide, which is why beef liver is in
the basket at all and why riboflavin is the largest single line in the bill.

primal objective      $0.108662 per day
dual objective        $0.108662 per day
duality gap           0.00e+00

Stigler, by hand, 1945:      $39.93 per year
Laderman, by simplex, 1947:  $39.69 per year
this run:                    $39.66 per year
The residual gap against Dantzig's reported $39.69 is rounding in the
transcribed nutrient table and the 365-day convention, not a different answer.

Same problem with beef liver struck from the list: $39.80 per year (+0.35%)

wrote /tmp/zipcheck/post-01-the-last-place-optimal-means-anything/out/stigler_solution.csv
wrote /tmp/zipcheck/post-01-the-last-place-optimal-means-anything/out/stigler_duals.csv
```

Calories are cheap because they arrive as a by-product. Riboflavin is not,
and that is the whole reason beef liver is in a subsistence diet.

## 3. The smallest interesting LP

`blend.py` is a two-variable feed-blending problem — small enough that the
feasible set is a polygon on a page and the optimum is visibly sitting on one
of its corners. It also enumerates every corner by brute force, which is
tractable at two variables and hopeless at seventy-seven, which is why the
simplex method exists.

## Run it

From the repository root, once, so the two packages land in a Python of their
own rather than in the one your operating system maintains:

```
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install -r requirements.txt
```

Then either `make post01` from the root, or the scripts by hand from here:

```
python3 build_data.py     # writes the two CSVs, run once
python3 stigler.py
python3 blend.py
python3 make_figures.py   # writes out/*.svg
```

If `pip` answers `error: externally-managed-environment`, the virtual
environment is exactly what it is asking for. If a script answers
`ModuleNotFoundError`, the environment is not active: look for `(.venv)` in
your prompt. The root README covers both at length.

## Data

`data/stigler_1939.csv` — 77 commodities, August 1939 retail prices averaged
over 51 large cities, and for each commodity the amount of each of nine
nutrients obtainable for one dollar. This is Stigler's own Table 1. The
transcription is the one distributed with Google OR-Tools under Apache 2.0;
it is committed here as a plain CSV so the numbers being solved are visible
rather than buried inside a library.

`data/daily_allowances_1943.csv` — the nine daily minimums, from the National
Research Council's 1943 allowances, for a moderately active man weighing
154 lb.

## Sources

- Stigler, G. J., "The Cost of Subsistence," *Journal of Farm Economics*
  27(2), May 1945, 303–314. The $39.93 diet is his Table 2, p. 311; the
  admission that he had no method is on p. 310.
- Dantzig, G. B., "The Diet Problem," *Interfaces* 20(4), 1990, 43–47. The
  source of the nine clerks, the desk calculators and the 120 man-days —
  a personal recollection written 43 years after the fact, not an archival
  record, and worth flagging as such.
- Garille, S. G. and Gass, S. I., "Stigler's Diet Problem Revisited,"
  *Operations Research* 49(1), 2001, 1–13. The 1947 optimal basket, including
  the beef liver.
- Rockafellar, R. T., "Lagrange Multipliers and Optimality," *SIAM Review*
  35(2), 1993, 183–238. The watershed line is on p. 185.
- Boyd, S. and Vandenberghe, L., *Convex Optimization*, Cambridge, 2004.
  The certificate language is §5.5.1.
