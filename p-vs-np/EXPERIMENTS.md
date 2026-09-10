# Baseline experiment, 2026-09-10

Ran from the repository root with Python 3.11.16 (the lab requires 3.10+):

```bash
python3 -B p-vs-np/investigate.py --sizes 6 10 14 --seeds 0 1 2 --densities 2 4.25 6 --limit 100000 --json
python3 -B -m unittest discover -s p-vs-np/tests -v
```

The run produced **76 solver results over 38 instances**, with no UNKNOWN
results or disagreements. Every returned SAT witness was verified. All **16 test
methods** passed, including exhaustive two-variable formulas and independent
truth-table comparisons. The separate zero-budget CLI test verifies that UNKNOWN
is preserved in the output.

The following selection reports the largest default n for each scalable
structured family, all three seeds at n=14 and density=4.25, and both pigeonhole
cases. Rerun the command for all densities and sizes; this is not an aggregate or
a worst-case estimate. “Brute attempts” and “DPLL nodes” are different operations.

| Formula | n | m | Status | Brute attempts | DPLL nodes | DPLL decisions | Brute / DPLL literal checks |
| --- | ---: | ---: | --- | ---: | ---: | ---: | ---: |
| Unit clauses | 14 | 14 | SAT | 16,384 | 1 | 0 | 32,766 / 119 |
| Consistent parity cycle | 14 | 28 | SAT | 1 | 2 | 1 | 42 / 436 |
| Inconsistent parity cycle | 14 | 28 | UNSAT | 16,384 | 3 | 1 | 90,106 / 816 |
| Random 3-SAT, seed 0 | 14 | 60 | SAT | 2,073 | 11 | 7 | 32,213 / 1,642 |
| Random 3-SAT, seed 1 | 14 | 60 | SAT | 2,268 | 20 | 10 | 32,625 / 4,610 |
| Random 3-SAT, seed 2 | 14 | 60 | SAT | 2,199 | 7 | 4 | 31,747 / 1,608 |
| 3 pigeons, 2 holes | 6 | 9 | UNSAT | 64 | 3 | 1 | 323 / 120 |
| 4 pigeons, 3 holes | 12 | 22 | UNSAT | 4,096 | 11 | 5 | 37,343 / 987 |

The random generator samples three distinct variables per clause, with independent
random signs. Clauses can repeat. The actual clause count is
`round(density * n)` using Python rounding, hence 60 at 4.25 × 14. This is a small
fixed seed set, with no claim about a phase transition or typical asymptotics.

## Conclusions supported by this run

- Exhaustive enumeration can grow exponentially even on a family solved by
  elementary propagation. The exact counts have the direct derivation in
  [THEORY.md](THEORY.md), beyond the observed sample sizes.
- Lack of initial unit clauses does not establish satisfiability or hardness.
  The inconsistent cycle has no initial units and takes only one DPLL decision;
  Gaussian elimination independently agrees that it is inconsistent.
- Enumeration can beat DPLL on an instance where its first guess succeeds:
  the consistent cycle uses fewer literal checks in brute force. No solver
  dominance is inferred from these counts.
- Seeds and structure matter. DPLL decisions vary even within the three
  displayed formulas of equal size. Neither this variation nor the pigeonhole
  samples gives a lower bound against other solvers.

Literal counts exclude preprocessing and allocation. Timings are intentionally
absent from this record and JSON because hardware, interpreter, and load affect
them. Text output provides illustrative wall times. These tests establish finite
agreements among implementations, not P = NP or P != NP, and UNSAT results are
not accompanied by independently checkable proof certificates.


## Subsequent experiments

This historical baseline is frozen in [research/baseline-v1.json](research/baseline-v1.json)
and replayed by the regression tests. The mixed XOR/CNF and Gaussian-basis
comparisons are recorded separately in [research/FINDINGS.md](research/FINDINGS.md),
with full inputs and 320/400-result snapshots. The current suite has 41 test
methods; the 16-method count above describes the original baseline run.
