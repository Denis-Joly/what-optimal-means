#!/usr/bin/env python3
"""Reproduce every matrix-size calculation used in Post 2.

The Netlib source is committed as a dated snapshot because the post's `make`
target must not depend on a network connection.  Its own header explains its
counting convention: row and nonzero counts include the objective row, while
column and nonzero counts exclude slack and surplus columns. We apply the same
convention to Stigler.
"""

from __future__ import annotations

import csv
import math
import re
import statistics
from dataclasses import dataclass
from pathlib import Path


HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE / "out"


@dataclass(frozen=True)
class Problem:
    name: str
    rows: int
    cols: int
    nonzeros: int

    @property
    def cells(self) -> int:
        return self.rows * self.cols

    @property
    def density(self) -> float:
        return self.nonzeros / self.cells

    @property
    def nonzeros_per_col(self) -> float:
        return self.nonzeros / self.cols


def load_stigler() -> tuple[list[str], list[list[float]]]:
    """Return nutrient labels and the 9 by 77 nutrient matrix."""
    with (DATA / "stigler_1939.csv").open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if len(rows) != 77:
        raise ValueError(f"Expected 77 Stigler commodities, found {len(rows)}")

    metadata = {"commodity", "unit", "price_cents_aug1939"}
    nutrients = [name for name in rows[0] if name not in metadata]
    matrix = [[float(row[name]) for row in rows] for name in nutrients]
    if len(matrix) != 9:
        raise ValueError(f"Expected 9 nutrient rows, found {len(matrix)}")
    return nutrients, matrix


def stigler_problem() -> Problem:
    """Count Stigler as Netlib does, including the all-ones objective row."""
    _, matrix = load_stigler()
    constraint_nonzeros = sum(value != 0 for row in matrix for value in row)
    objective_nonzeros = len(matrix[0])
    return Problem(
        name="STIGLER",
        rows=len(matrix) + 1,
        cols=len(matrix[0]),
        nonzeros=constraint_nonzeros + objective_nonzeros,
    )


def load_netlib() -> list[Problem]:
    text = (DATA / "netlib-lp-readme-2026-08-11.txt").read_text(encoding="utf-8")
    # Both headings are mentioned in the prose before the actual table, so use
    # its column-header line and the indented heading that follows the rows.
    start = text.index("\nName       Rows   Cols   Nonzeros")
    end = text.index("\n        BOUND-TYPE TABLE", start)
    table = text[start:end]
    pattern = re.compile(r"^([A-Z0-9.\-]+)\s+(\d+)\s+(\d+)\s+(\d+)", re.MULTILINE)
    problems = [
        Problem(name, int(rows), int(cols), int(nonzeros))
        for name, rows, cols, nonzeros in pattern.findall(table)
    ]
    if len(problems) != 98:
        raise ValueError(f"Expected 98 Netlib summary rows, found {len(problems)}")
    return problems


def inclusive_quartiles(values: list[float]) -> tuple[float, float, float]:
    return tuple(statistics.quantiles(values, n=4, method="inclusive"))  # type: ignore[return-value]


def write_netlib_csv(problems: list[Problem]) -> None:
    OUT.mkdir(exist_ok=True)
    with (OUT / "netlib-summary.csv").open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(["name", "rows", "cols", "nonzeros", "cells", "density", "nonzeros_per_col"])
        for p in problems:
            writer.writerow([
                p.name,
                p.rows,
                p.cols,
                p.nonzeros,
                p.cells,
                f"{p.density:.12g}",
                f"{p.nonzeros_per_col:.12g}",
            ])


def report() -> str:
    stigler = stigler_problem()
    netlib = load_netlib()
    per_col = [p.nonzeros_per_col for p in netlib]
    density = [p.density for p in netlib]
    q1, median, q3 = inclusive_quartiles(per_col)
    small = [p.nonzeros_per_col for p in netlib if p.cells < 100_000]
    large = [p.nonzeros_per_col for p in netlib if p.cells > 10_000_000]

    foods = 77
    nutrient_rows = 9
    standard_form_cols = foods + nutrient_rows
    bases = math.comb(standard_form_cols, nutrient_rows)
    days_at_one_microsecond = bases / 1_000_000 / 86_400

    write_netlib_csv(netlib)

    return "\n".join([
        "Stigler, counted with Netlib's convention",
        "------------------------------------------",
        f"rows (9 constraints + objective)  {stigler.rows}",
        f"food columns                      {stigler.cols}",
        f"nonzeros                          {stigler.nonzeros}",
        f"density                           {100 * stigler.density:.1f}%",
        f"nonzeros per column               {stigler.nonzeros_per_col:.1f}",
        "",
        "Standard-form selection count",
        "-----------------------------",
        f"food columns                      {foods}",
        f"surplus columns                   {nutrient_rows}",
        f"columns total                     {standard_form_cols}",
        f"columns in one basis              {nutrient_rows}",
        f"candidate column sets C(86, 9)    {bases:,}",
        f"at one microsecond per candidate  {days_at_one_microsecond:.2f} days",
        "",
        "Netlib LP/DATA summary",
        "----------------------",
        f"problems parsed                    {len(netlib)}",
        f"median density                     {100 * statistics.median(density):.3f}%",
        f"nonzeros/column Q1                 {q1:.2f}",
        f"nonzeros/column median             {median:.2f}",
        f"nonzeros/column Q3                 {q3:.2f}",
        f"under 100,000 cells                n={len(small)}, median={statistics.median(small):.2f}",
        f"over 10,000,000 cells              n={len(large)}, median={statistics.median(large):.2f}",
        "",
        "The combinations are candidate column sets, not bases or vertices.",
        "Singular selections, infeasible basic solutions, and multiple bases for",
        "one degenerate vertex all separate this count from the vertex count.",
    ]) + "\n"


if __name__ == "__main__":
    print(report(), end="")
