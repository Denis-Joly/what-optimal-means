# Article 4 reproducibility package

This directory reproduces the two numerical figures for **“Optimising against a guess”** without modifying the article draft. It uses the Python standard library plus PuLP’s in-process HiGHS interface.

## Reproduce everything

From this directory, create an isolated local environment and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python run_experiments.py
python make_figures.py
python verify_results.py
```

The publication run uses Python 3.14.6, PuLP 3.3.2, highspy 1.15.1, and `pulp.HiGHS`. Both experiments use fixed seeds. The result files contain no timestamps or measured run times. They are byte-identical when rerun in this exact tested runtime; on another Python version or platform, metadata or solver tie-breaking can differ, so `verify_results.py` is the portable criterion for scientifically equivalent results.

Open `demo.html` locally to inspect both figures together. The `.html` files under `out/` are self-contained article fragments with inline SVG; the `.svg` files are their standalone static counterparts.

## Files

```text
README.md
requirements.txt                 pinned LP runtime dependencies
data/model.json                    fixed experiment inputs
run_experiments.py                 Monte Carlo, quadrature, and robust LPs
verify_results.py                  independent numerical and scientific checks
make_figures.py                    accessible static SVG and inline HTML generator
demo.html                          local figure preview
out/results.json                   complete machine-readable result
out/results.txt                    compact human-readable result
out/fig1-optimizer-curse.svg       standalone Figure 1
out/fig1-optimizer-curse.html      inline-SVG Figure 1 fragment
out/fig2-price-of-robustness.svg   standalone Figure 2
out/fig2-price-of-robustness.html  inline-SVG Figure 2 fragment
```

## Figure 1: the optimiser’s curse

The experiment creates ten alternatives with identical true value zero. In every replication:

1. draw ten independent estimates from `Normal(0, 1)`;
2. select the alternative with the largest estimate;
3. draw a fresh, independent `Normal(0, 1)` outcome for every alternative and reveal the selected one.

The publication run uses seed `20260820` and 200,000 replications. It reports the selected estimate, the selected fresh outcome, their difference, Monte Carlo standard errors, and 95% normal-approximation Monte Carlo intervals.

The exact comparison is obtained by adaptive quadrature of

```text
E[max(Z_1,...,Z_n)]
  = integral from 0 to infinity of
    [1 - Phi(t)^n - (1 - Phi(t))^n] dt.
```

For `n = 10`, quadrature gives `1.538752731`. The simulation gives a selected-estimate mean of `1.539858` (0.84 Monte Carlo standard errors above quadrature) and a fresh-outcome mean of `0.003842`, whose 95% interval includes zero.

`verify_results.py` independently checks this number using the order-statistic density `n x phi(x) Phi(x)^(n-1)` and a composite Simpson rule. Thus the verification does not reuse the experiment’s integral identity or adaptive integrator.

The scatterplot contains only the first 600 stored pairs for legibility. Every reported mean, standard error, and interval uses all 200,000 replications.

## Figure 2: a budgeted robust portfolio LP

This is a deliberately small synthetic portfolio, not an investment recommendation. Asset `i` has nominal return `mu_i`, maximum adverse coefficient deviation `d_i`, and a linear defensive-allocation cost `c_i`. The portfolio is fully invested, non-negative, and capped at 55% per asset. It minimises `sum(c_i x_i)` while requiring a target return of 6.7%.

Write the coefficient shock as `U_i`. The full symmetric Bertsimas–Sim set is

```text
|U_i| <= 1
sum(|U_i|) <= Gamma.
```

Because this is a lower-return constraint and every portfolio weight is non-negative, its worst point has `U_i <= 0`. Defining the adverse projection `q_i = max(0, -U_i)` therefore reduces the loss subproblem exactly to `0 <= q_i <= 1`, `sum(q_i) <= Gamma`.

The worst-case return constraint is represented by the exact Bertsimas–Sim linear counterpart:

```text
sum(mu_i x_i) - Gamma z - sum(p_i) >= target
z + p_i >= d_i x_i                         for every i
z >= 0, p_i >= 0.
```

The grid is `Gamma = 0, 0.5, ..., n`, where `n = 6`. For fractional `Gamma = k + f`, the adversary may use `k` deviations fully and one additional deviation at fraction `f`; it is not rounded to an integer.

Every compact `z/p_i` solution is independently checked against an LP containing all relevant adversarial extreme-point constraints. The largest reported objective gap is about `4.2e-15`, and no simulated point inside its declared robust set violates the return target.

### Three objects that must not be conflated

- **Robust guarantee:** deterministic. For each `Gamma`, the reported portfolio meets the target for every shock in the full symmetric budgeted set. For this one-sided constraint the same guarantee extends to any shock whose effective adverse projection satisfies `sum(max(0, -U_i)) <= Gamma`.
- **Empirical simulation:** distribution-specific. The reported violation rate uses 150,000 common random draws with independent `Uniform[-1, 1]` shocks. Those draws are not conditioned to lie inside the robust set.
- **Concentration bound:** not computed or plotted. Such a bound would be a separate, assumption-dependent theorem, not an empirical rate and not the set-wise guarantee.

Under this declared simulation law, the violation estimate falls from 10.331% at `Gamma = 0` to zero observed violations at `Gamma = 5` and above. The cost index rises by 59.46% at the fully robust endpoint. Violation-rate intervals use the Wilson score method, which remains informative when the observed count is zero.

The result schema names `sum(max(0, -U_i))` the **effective adverse budget**. Positive shocks do not consume this one-sided loss budget because they cannot hurt the lower-return constraint. It is the projection relevant to the robust counterpart and is deliberately not labelled `sum(abs(U_i))`, the absolute budget of a full symmetric shock vector.

## Interpretation and scope

- Figure 1 isolates selection bias under a fully specified Gaussian experiment. It does not claim that every fitted optimisation model has this exact bias magnitude.
- Figure 2 prices robustness in a synthetic linear cost index. “Price” is an objective trade-off, not a monetary forecast or a general measure of financial risk.
- The exact LP counterpart applies to the stated budgeted coefficient-uncertainty set. It does not make arbitrary uncertainty models linear.
- Monte Carlo confidence intervals quantify finite-simulation error only. They do not account for model misspecification.

The robust formulation follows Dimitris Bertsimas and Melvyn Sim, “The Price of Robustness,” *Operations Research* 52(1), 2004, <https://doi.org/10.1287/opre.1030.0065>.
