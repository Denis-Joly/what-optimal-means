# Post 5 companion: Where the Proof Runs Out

This folder reproduces the numerical figure in the fifth and final article of the *What Optimal Means* series. It solves the same continuous, non-convex Haverly pooling model with SciPy's local SLSQP method from three fixed starting points.

The experiment is deliberately narrow. It verifies that all three returned plans are feasible and worth $0, $100 and $400 respectively. It does **not** turn SLSQP into a global solver. The documented global value of $400 is recorded separately from the local-solver statuses and cross-checked against the GAMS Model Library benchmark.

## Reproduce

From this folder:

```sh
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python run_experiment.py
./.venv/bin/python make_figure.py
./.venv/bin/python verify_results.py
```

Open `demo.html` to inspect the rendered static figure. The article includes the complete fragment in `out/fig1-local-successes.html`.

The pinned NumPy and SciPy releases require Python 3.12 or later.

## What is fixed

- Haverly's feed costs, sulphur concentrations, product prices and limits;
- the first nine initial guesses from NumPy's PCG64 generator with seed `20260820`;
- the three selected start indices, `7`, `8` and `0`;
- NumPy `2.5.2`, SciPy `1.18.0`, SLSQP tolerance `1e-11`, and 3,000 maximum iterations.

`success` means that SLSQP satisfied its own termination tests. It is not a proof of strict local optimality and does not bound undiscovered solutions elsewhere in the feasible region.

## Files

- `data/model.json`: model data, equations, run settings and independent benchmark;
- `run_experiment.py`: numerical experiment and machine-readable output;
- `make_figure.py`: static SVG and HTML figure generator;
- `verify_results.py`: numerical, provenance and accessibility checks;
- `out/results.json` and `out/results.txt`: generated results;
- `out/fig1-local-successes.svg` and `.html`: generated figure.

## Sources

- C. A. Haverly, “Studies of the Behavior of Recursion for the Pooling Problem,” *ACM SIGMAP Bulletin* 25 (1978), 19–28. <https://doi.org/10.1145/1111237.1111238>
- GAMS Model Library, “A Pooling Problem (POOL),” instance `haverly1`. <https://www.gams.com/latest/gamslib_ml/libhtml/gamslib_pool.html>
