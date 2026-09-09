# Findings log

## 2026-09-10 — R001: bounded-width XOR reasoning

**Question.** Does retaining small XOR relations reduce branching on mixed
parity/3-CNF formulas, and does allowing wider relations always help?

**Method.** Implemented pairwise XOR closure after CNF unit propagation stalls.
The module restricts source equations under current assignments, retains support
size at most k, and repeatedly adds eligible pairwise sums. It supplies forced
literals or a contradiction to the shared DPLL loop. The complete original CNF
remains available, so incomplete inference cannot drop a constraint.

Recorded [run 001](runs/001/manifest.json): sizes 6, 10, 14; seeds 0–7; k=0,2,3,4;
100,000 search nodes and 20,000 pair attempts per solve. Each mixed formula has
floor(n/2) XOR3 rows and 2n ordinary 3-CNF clauses. Planted controls force every
constraint to accept a random witness; this deliberately biases their distribution.
There are 24 unplanted mixed instances, 24 planted instances, 24 ordinary CNF
controls, six parity cycles, and two four-equation controls: **80 formulas, 320
results**. The random distributions are small, chosen samples, not a claim about
typical SAT behavior. All answers agreed, every SAT witness passed a raw CNF/XOR
check, and every formula's answer was subsequently checked by a truth table.

Reproduce with `python3 -B p-vs-np/mixed.py --check p-vs-np/research/runs/001`.
The full counts are in [results.csv](runs/001/results.csv); the following are
sums within each stated family, including SAT and UNSAT:

| Family | Variant | Decisions | CNF literal inspections | XOR pair attempts |
| --- | --- | ---: | ---: | ---: |
| Mixed (24) | DPLL | 115 | 32,306 | 0 |
| Mixed (24) | k=2 | 111 | 31,289 | 812 |
| Mixed (24) | k=3 | 77 | 24,694 | 9,467 |
| Mixed (24) | k=4 | 77 | 24,694 | 34,353 |
| Planted (24) | DPLL | 88 | 23,757 | 0 |
| Planted (24) | k=3 | 62 | 17,468 | 8,154 |
| Planted (24) | k=4 | 62 | 17,468 | 26,628 |

The 24 CNF-only controls had identical witnesses and base counters across variants.
All 320 results completed without UNKNOWN. However, width four hit its inference
budget on three cycle solves. Those cutoffs did not compromise correctness.

**Supported conclusion.** Retained relations reduced branching on these mixed
samples. Wider closure sometimes only generated extra work, and bounded-resource
inference is sensitive to scheduling. Fewer branches do not establish lower total
runtime, nor a worst-case upper bound for SAT.

### Counterexample A: width three can miss a contradiction

Saved as `width-three-stalls` in [counterexamples.json](counterexamples.json):

```text
x1 XOR x2 XOR x3 = 0
x1 XOR x4 XOR x5 = 0
x2 XOR x4 XOR x6 = 0
x3 XOR x5 XOR x6 = 1
```

Every variable occurs twice, so summing all four equations gives 0=1. Every two
distinct rows share exactly one variable; their sum therefore has width four.
At k=3, closure is saturated with the four source equations, no units, and no
contradiction. At k=4, summing the first pair and the second pair gives the same
four-variable left side with opposite right sides, exposing the contradiction.
Deleting any one row makes the system satisfiable, as checked by truth tables.

For this inconsistent fixture, DPLL used seven decisions, k=2 used three, k=3
used one, and k=4 used zero. The k=3 solver succeeds after a decision shrinks
relations; root-level inference failure is not solver failure.

This refutes completeness of **this width-three pairwise proof rule**, not every
possible width-three proof method or every SAT algorithm.

### Counterexample B: more width can lose under the same budget

Saved as `width-is-not-budget-monotone`: the six-variable inconsistent parity
cycle from the original lab. With 33 pair attempts, k=2 detects contradiction;
k=4 reaches its budget without doing so. Peak retained rows are 15 versus 29.
Both complete hybrid solvers still correctly return UNSAT.

`python3 -B p-vs-np/counterexamples.py` finds this by increasing cycle size from
3 to 8 and cap from 1 to 100, then greedily deleting constraints while preserving
the gap. The retained case is deletion-minimal for this predicate. The statement
is tied to the implementation's deterministic pair order and cap. Uncapped
consistent closures retain monotonically more relations as k grows; that fact
says nothing about how soon a useful relation is scheduled under a cap.

**Next experiment pursued immediately:** retain a linear basis rather than
materializing so many consequences. This led to R002 below.

## 2026-09-10 — R002: Gaussian basis versus enumerated closure

**Question.** Can a Gaussian basis preserve the useful deductions with less
algebraic work on exactly the same inputs?

Added forward elimination and pivot-column reduction to the same DPLL inference
hook. At most n independent rows are retained per call. With no inference cutoff,
reduced rows expose every forced variable of the supplied XOR subsystem. The
implementation rebuilds the basis per call; it does not cache across branches,
learn clauses, or recognize hidden XORs.

Recorded [run 002](runs/002/manifest.json), created with
`python3 -B p-vs-np/mixed.py --gaussian --output-dir p-vs-np/research/runs/002`.
Its `cases.json` is byte-for-byte identical to R001. This adds one Gaussian variant,
for **400 results**; all answers agree, with no UNKNOWN. Gaussian uses a 20,000
row-addition budget, with no cutoffs in this run.

| Family | DPLL decisions | k=3 decisions / pairs | Gaussian decisions / row additions |
| --- | ---: | ---: | ---: |
| Mixed (24) | 115 | 77 / 9,467 | 77 / 616 |
| Planted (24) | 88 | 62 / 8,154 | 62 / 404 |
| Cycles (6) | 6 | 3 / 6,603 | 3 / 78 |
| Four-equation controls (2) | 10 | 4 / 38 | 3 / 11 |

Gaussian matches k=3's decisions and CNF inspections on the mixed/planted samples,
while performing far fewer row additions than closure pair attempts. The two
kinds of operation have different surrounding overhead, so this is an operation
count result, not a measured wall-time speedup. The inconsistent four-equation
fixture is refuted at the root after three Gaussian row additions.

**Why the representation helps here.** Pairwise closure stores many redundant
consequences. In a consistent n-variable system, it can retain up to
sum(i=1..min(k,n)) binomial(n,i) different nonzero masks. Pair enumeration may
try quadratically many pairs in that quantity per call. For fixed k this is
polynomial, but the degree depends on k. A Gaussian basis stores at most n
independent rows, each possibly n bits wide. Forward elimination takes at most
m*n row additions and pivot reduction at most n*(n-1)/2, in addition to scans
and bit costs. Neither bound removes the potentially exponential DPLL search.

This is an experimental reconstruction of established ideas, not a new SAT
algorithm: [Soos's Gaussian integration paper](https://www.msoos.org/wordpress/wp-content/uploads/2010/08/PoS10-Soos.pdf)
and [Laitinen–Junttila–Niemelä's complete parity reasoning paper](https://arxiv.org/abs/1207.0988)
study SAT solvers coupled with XOR reasoning. Our implementation is deliberately
smaller, without their production solver machinery or performance claims.

### Remaining obstruction: complete linear reasoning is not complete mixed reasoning

Take the supplied equation `x1 XOR x2 XOR x3 = 0`, together with ordinary clauses:

```text
(x1 OR x2 OR x3)
(x1 OR NOT x2 OR NOT x3)
(NOT x1 OR x2 OR NOT x3)
(NOT x1 OR NOT x2 OR x3)
```

The CNF requires odd parity, so the conjunction is inconsistent. The supplied
linear subsystem is satisfiable and forces no single variable. Gaussian inference
alone makes no root deduction; our hybrid still needs three decisions. Removing
any clause or the supplied equation restores satisfiability. This example is
protected by `test_complete_xor_inference_does_not_decide_all_mixed_formulas`.

It identifies a representation boundary: the module sees only the **supplied**
linear equations, even when the ordinary CNF contains another explicit parity
block. Pure linear reasoning has not decided the whole mixed problem.

**Next falsifiable question (R003).** Can a sound recognizer of complete width-two
and width-three parity blocks in CNF recover these missing relations without
changing the formula's model set? Keep the original clauses; add only equations
whose entire set of forbidden-parity clauses is present. Test all small clause
subsets, missing-block near misses, duplicates, tautologies, sign flips, and
opposite parities before measuring branching on the existing 80-case corpus and
new disguised-parity controls. Broader algebraic recognition remains outside that
restricted experiment. Soos's paper discusses this explicit-block recognition
pattern; it is not a proposed new route to resolving P vs NP.

## Regression status after R002

**41 test methods pass.** New coverage includes 640 exhaustive tiny mixed cases,
100 seeded mixed formulas checked at five width settings and with Gaussian
inference, entailment checks for retained relations, 280 systems checking exactly
which variables Gaussian inference forces, both counterexample reproducers,
cutoffs, permutations/sign flips, snapshot tamper detection, and refusal to
overwrite old runs. All 80 benchmark answers receive independent truth-table
checks. The 76 original baseline results and both new runs replay exactly.

Historical performance claims are tied to their inputs and counters. Changes in
heuristics or representation require a new run and an explanation; existing
counterexamples and correctness requirements remain in the regression suite.
