# P vs NP: a small experimental lab

**Status: open.** The question is whether every decision problem with polynomially
checkable, polynomial-length witnesses also has a deterministic polynomial-time
decision algorithm. P is contained in NP; the unknown is the reverse inclusion.
SAT and 3-SAT are NP-complete, so a polynomial-time algorithm for either would
establish P = NP. “NP” means nondeterministic polynomial time, not “non-polynomial.”
See [Cook's official problem description](https://www.claymath.org/wp-content/uploads/2022/06/pvsnp.pdf)
and the [Clay problem page](https://www.claymath.org/millennium/p-vs-np/).

This lab studies concrete search strategies and tries to falsify tempting claims.
It does not establish a lower bound against every algorithm. Start with
[THEORY.md](THEORY.md) for the arguments and [EXPERIMENTS.md](EXPERIMENTS.md) for
measured results.

## Mixed XOR/CNF research

The next research direction now has two completed experiments, logged in
[research/FINDINGS.md](research/FINDINGS.md): bounded-width XOR inference followed
by a Gaussian-basis comparison on identical inputs. The lab includes reproducible
counterexamples showing why a width bound can miss contradictions and why more
width can lose under an inference budget.

[hybrid.py](hybrid.py) provides `solve_hybrid` and `solve_gaussian` for ordinary CNF
conjoined with supplied width-at-most-three XOR equations. Both reuse the original
DPLL search loop. [mixed.py](mixed.py) saves full input corpora, witnesses, counters,
and manifests to new run directories and checks existing runs without rewriting
them. [counterexamples.py](counterexamples.py) reproduces and deletion-minimizes
the inference-budget counterexample.

There are now **41 test methods**, including independent truth-table checks for
all 80 mixed-research benchmark formulas and exact replay of the original 76
baseline results. The [research record](research/README.md) explains how to extend
the experiments without erasing old findings. GitHub Actions runs the suite on
Python 3.11 for changes to this lab.

```bash
python3 -B p-vs-np/mixed.py --check p-vs-np/research/runs/001
python3 -B p-vs-np/mixed.py --check p-vs-np/research/runs/002
```

## Run

Python 3.10+, standard library only. From the repository root:

```bash
python3 -B -m unittest discover -s p-vs-np/tests -v
python3 -B p-vs-np/investigate.py
python3 -B p-vs-np/investigate.py --sizes 6 10 14 --seeds 0 1 2 --densities 2 4.25 6 --limit 100000 --json
```

The default runs 38 instances through two CNF solvers: unit clauses, satisfiable
and inconsistent parity cycles, random 3-SAT at three clause/variable ratios and
three seeds, and two pigeonhole formulas. Only the random family is guaranteed
to have exactly three distinct variables per clause. JSON contains deterministic
operation counts and configuration; human output also includes elapsed seconds
converted to milliseconds. Use smaller sizes for exhaustive exploration.

`--limit` caps assignments for brute force and search nodes for DPLL, separately
for each instance. These are different units, and neither is a wall-time or memory
limit. Formula construction and processing within a node are not capped. Reaching
the budget returns **UNKNOWN**, never UNSAT. A zero limit exercises this path.

## Programs

| File | Purpose |
| --- | --- |
| [sat.py](sat.py) | CNF verifier, exhaustive solver, instrumented DPLL, search via decision, formula generators |
| [parity.py](parity.py) | Gaussian elimination over GF(2), XOR-to-CNF encoding for width at most 3, parity cycles |
| [investigate.py](investigate.py) | Reproducible comparisons, witness checks, agreement checks, text/JSON output |
| [tests/test_sat.py](tests/test_sat.py) | Independent truth tables, exhaustive tiny cases, seeded and transformed formulas, budgets and CLI checks |

CNF uses signed one-based integers: `[[1, -2], [2]]` means
`(x1 OR NOT x2) AND x2`. Assignments are tuples of booleans. The empty formula
is true; a formula containing an empty clause is false. Invalid variable indices
and non-Boolean witnesses raise `ValueError`. Duplicate literals are collapsed
and tautological clauses removed without changing the input.

`solve_brute_force` and `solve_dpll` return a `Result` with `status`, an optional
complete `assignment`, and `stats`. Missing variables in a DPLL witness are filled
with False. The original `verify`, `brute_force`, and `random_3sat` names remain
importable from `investigate.py`; `brute_force` retains its tuple-or-None API.
`solve_xor` also returns a tuple or None and has no search budget.

DPLL uses unit propagation and branches on the first variable of the shortest
remaining clause, False first. It is deliberately simple, with no clause learning
or restarts. Its algorithmic ancestry is
[Davis–Logemann–Loveland (1962)](https://web.stanford.edu/class/cs357/DPLL62.pdf).

Counters describe these implementations: `assignments` counts full brute-force
candidates, `nodes` counts visited DPLL states, `decisions` counts binary splits,
`propagations` counts unit assignments, `conflicts` counts DPLL contradiction
leaves, and `literal_checks` counts solver-loop literal inspections. Counters omit
normalization, allocation, copying, and final witness verification. Node counts
alone are not runtime: this simple propagation implementation repeatedly scans
clauses.

The tests check all 512 clause sets over the nine non-tautological two-variable
clauses (including the empty clause), 125 seeded random SAT instances, variable
renaming and sign flips, pigeonhole boundary cases, 280 random linear systems,
XOR encoding truth tables, and decision-to-witness recovery. These finite checks
support implementation correctness; they cannot establish asymptotic complexity.
