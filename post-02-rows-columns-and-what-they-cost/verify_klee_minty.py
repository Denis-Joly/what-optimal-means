#!/usr/bin/env python3
"""Verify the three-variable Klee-Minty path with exact arithmetic.

The instance is written with <= constraints and an initial slack basis.  At
each iteration the entering variable is the one with the largest positive
reduced cost (Dantzig's original rule); the usual minimum-ratio test chooses
the leaving variable.  Fractions keep the path independent of floating-point
rounding.
"""

from __future__ import annotations

from fractions import Fraction


Number = Fraction


def solve(matrix: list[list[Number]], rhs: list[Number]) -> list[Number]:
    """Solve a small square system by exact Gauss-Jordan elimination."""
    n = len(rhs)
    aug = [row[:] + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = next((row for row in range(col, n) if aug[row][col]), None)
        if pivot is None:
            raise ValueError("singular basis")
        aug[col], aug[pivot] = aug[pivot], aug[col]
        scale = aug[col][col]
        aug[col] = [value / scale for value in aug[col]]
        for row in range(n):
            if row == col or not aug[row][col]:
                continue
            factor = aug[row][col]
            aug[row] = [aug[row][j] - factor * aug[col][j] for j in range(n + 1)]
    return [aug[i][-1] for i in range(n)]


def dot(left: list[Number], right: list[Number]) -> Number:
    return sum((a * b for a, b in zip(left, right)), start=Fraction(0))


def klee_minty_path() -> list[tuple[tuple[Number, Number, Number], Number]]:
    """Return every primal vertex visited by Dantzig's pivot rule."""
    columns = [
        [Fraction(1), Fraction(20), Fraction(200)],  # x1
        [Fraction(0), Fraction(1), Fraction(20)],    # x2
        [Fraction(0), Fraction(0), Fraction(1)],     # x3
        [Fraction(1), Fraction(0), Fraction(0)],     # s1
        [Fraction(0), Fraction(1), Fraction(0)],     # s2
        [Fraction(0), Fraction(0), Fraction(1)],     # s3
    ]
    costs = [Fraction(100), Fraction(10), Fraction(1), Fraction(0), Fraction(0), Fraction(0)]
    rhs = [Fraction(1), Fraction(100), Fraction(10000)]
    basis = [3, 4, 5]
    visited: list[tuple[tuple[Number, Number, Number], Number]] = []

    while True:
        basis_matrix = [[columns[basis[col]][row] for col in range(3)] for row in range(3)]
        basic_values = solve(basis_matrix, rhs)
        solution = [Fraction(0) for _ in columns]
        for variable, value in zip(basis, basic_values):
            solution[variable] = value
        objective = dot(costs, solution)
        visited.append(((solution[0], solution[1], solution[2]), objective))

        basis_costs = [costs[variable] for variable in basis]
        transpose = [[basis_matrix[row][col] for row in range(3)] for col in range(3)]
        dual = solve(transpose, basis_costs)
        reduced = [costs[j] - dot(dual, columns[j]) for j in range(len(columns))]
        candidates = [j for j in range(len(columns)) if j not in basis and reduced[j] > 0]
        if not candidates:
            break
        entering = max(candidates, key=lambda j: (reduced[j], -j))

        direction = solve(basis_matrix, columns[entering])
        ratios = [(basic_values[row] / direction[row], row) for row in range(3) if direction[row] > 0]
        if not ratios:
            raise ValueError("unbounded direction")
        _, leaving_row = min(ratios)
        basis[leaving_row] = entering

    return visited


def main() -> None:
    expected = [
        ((0, 0, 0), 0),
        ((1, 0, 0), 100),
        ((1, 80, 0), 900),
        ((0, 100, 0), 1000),
        ((0, 100, 8000), 9000),
        ((1, 80, 8200), 9100),
        ((1, 0, 9800), 9900),
        ((0, 0, 10000), 10000),
    ]
    path = klee_minty_path()
    simplified = [((int(x), int(y), int(z)), int(value)) for (x, y, z), value in path]
    assert simplified == expected, simplified
    print("step  x1    x2     x3       objective")
    for step, ((x1, x2, x3), objective) in enumerate(simplified):
        print(f"{step:>4}  {x1:>2}  {x2:>4}  {x3:>5}  {objective:>14}")


if __name__ == "__main__":
    main()
