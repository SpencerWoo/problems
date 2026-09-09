"""Reproducible SAT experiments, not a test of whether P equals NP.

Run from the repo root: python3 p-vs-np/investigate.py --help
Stdlib only, Python 3.10+. JSON omits wall times so runs are reproducible.
"""

import argparse
from dataclasses import asdict
import json
import time

from parity import parity_cycle, solve_xor, xor_to_cnf
from sat import (brute_force, pigeonhole, random_3sat, solve_brute_force,
                 solve_dpll, verify)


def cases(sizes, seeds, densities):
    for n in sizes:
        # Unique all-True witness: last in the brute-force enumeration order.
        yield "unit-sat", n, None, None, [[v] for v in range(1, n + 1)], None
        for inconsistent in (False, True):
            equations = parity_cycle(n, inconsistent)
            yield ("parity-unsat" if inconsistent else "parity-sat",
                   n, None, None, xor_to_cnf(equations, n), equations)
        for density in densities:
            for seed in seeds:
                yield ("random-3sat", n, density, seed,
                       random_3sat(n, round(density * n), seed), None)
    for holes in (2, 3):
        clauses, n = pigeonhole(holes + 1, holes)
        yield "pigeonhole-unsat", n, None, None, clauses, None


def run(sizes, seeds, densities, limit):
    rows = []
    for family, n, density, seed, clauses, equations in cases(sizes, seeds, densities):
        results = []
        for name, solver in (("brute", solve_brute_force), ("dpll", solve_dpll)):
            start = time.perf_counter()
            result = solver(clauses, n, limit)
            elapsed = time.perf_counter() - start
            if result.status == "SAT" and not verify(clauses, result.assignment):
                raise AssertionError(f"invalid witness: {name} {family}")
            results.append(result)
            row = dict(family=family, n_vars=n, n_clauses=len(clauses),
                       literals=sum(map(len, clauses)), density=density, seed=seed,
                       solver=name, status=result.status, limit=limit,
                       **asdict(result.stats), seconds=elapsed)
            if equations is not None:
                witness = solve_xor(equations, n)
                xor_status = "UNSAT" if witness is None else "SAT"
                if witness is not None and not verify(clauses, witness):
                    raise AssertionError("invalid XOR witness")
                if result.status != "UNKNOWN" and result.status != xor_status:
                    raise AssertionError("CNF and XOR solvers disagree")
                row["xor_status"] = xor_status
            rows.append(row)
        known = {result.status for result in results if result.status != "UNKNOWN"}
        if len(known) > 1:
            raise AssertionError(f"solvers disagree: {family}")
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[6, 10, 14])
    parser.add_argument("--seeds", type=int, nargs="+", default=[0, 1, 2])
    parser.add_argument("--densities", type=float, nargs="+", default=[2, 4.25, 6])
    parser.add_argument("--limit", type=int, default=100_000,
                        help="per solver: assignments for brute, search nodes for DPLL")
    parser.add_argument("--json", action="store_true", help="deterministic JSON, no timings")
    args = parser.parse_args()
    if any(n < 3 for n in args.sizes):
        parser.error("sizes must be >= 3")
    if any(not 0 <= d < float('inf') for d in args.densities):
        parser.error("densities must be finite and nonnegative")
    if args.limit < 0:
        parser.error("limit must be nonnegative")
    rows = run(args.sizes, args.seeds, args.densities, args.limit)
    if args.json:
        print(json.dumps([{k: v for k, v in row.items() if k != "seconds"}
                          for row in rows], indent=2, sort_keys=True))
    else:
        print("Finite experiments only. UNKNOWN means the work budget was exhausted.")
        print("Brute assignments and DPLL nodes are different units; neither is a time limit.")
        print("family              n   m ratio seed solver status  assignments nodes decisions checks     ms")
        for r in rows:
            print(f"{r['family']:19} {r['n_vars']:2} {r['n_clauses']:3} "
                  f"{str(r['density']):>5} {str(r['seed']):>4} {r['solver']:6} {r['status']:7} "
                  f"{r['assignments']:11} {r['nodes']:5} {r['decisions']:9} "
                  f"{r['literal_checks']:6} {r['seconds'] * 1000:7.2f}")


if __name__ == "__main__":
    main()
