# Theorycraft: which information lets us avoid search?

The working direction is to examine **what a solver retains about a formula**.
Unit propagation retains forced variable values; linear algebra also retains
relations among variables. When a strategy fails, we want an explicit input and
an explanation of the information it lost. This is a research exercise, not a
new proposed solution to P vs NP.

## What would actually settle the problem?

For P = NP, one route is a correct SAT decision algorithm together with a
polynomial worst-case bound in the encoded input length L, including preprocessing
and intermediate representations. For P != NP, showing that SAT is outside P
would suffice; proving one particular solver slow would not. Superpolynomial
lower bounds, rather than necessarily exponential ones, are the relevant target.
These criteria follow from SAT's NP-completeness; see
[Cook's problem description](https://www.claymath.org/wp-content/uploads/2022/06/pvsnp.pdf).

In the code, n counts declared variables and m counts clauses. Formulas can have
irrelevant declared variables; theoretical SAT can discard those and densely
renumber occurring variables. A bound in n alone must not hide the cost of reading
m clauses or long variable identifiers. Here witness construction includes n bits.

## Experiment 1: exponential enumeration can hide an easy problem

Take F_n = (x1) AND (x2) AND ... AND (xn). It has exactly one witness, all True.
Our False-first lexicographic exhaustive solver visits exactly 2^n assignments
before finding it. But each clause supplies a forced value, so unit propagation
solves it without making any decision.

**Derivation:** there are 2^n tuples; all True is last; any other tuple falsifies
at least one unit clause. This proves the count for this enumeration order on
this family, not a complexity lower bound for SAT. Our unit propagator rescans
remaining clauses and uses quadratic work here, still polynomial. A different
brute-force enumeration order can put this witness first.

**Rejected claim:** “The formula has one solution among exponentially many
possibilities, therefore finding it needs exponential time.” Rarity alone says
nothing about exploitable structure. `test_unit_family_exact_work` checks both
the exhaustive count and zero DPLL decisions.

## Experiment 2: local consistency misses a global contradiction

For n >= 3, impose x_i XOR x_(i+1) = 0 along a path, then
x_n XOR x_1 = 1. The path makes every variable equal, whereas the closing edge
requires unequal endpoints. Adding all equations over GF(2) gives 0 = 1: each
variable appears twice and cancels.

Encode equality of a,b as `(a OR NOT b) AND (NOT a OR b)`, and inequality as
`(a OR b) AND (NOT a OR NOT b)`. All clauses have width two. There is no unit
clause and no empty clause initially, so unit propagation alone makes no progress,
even though the formula is inconsistent.

**Rejected claim:** “If unit propagation stops without a contradiction, the
formula is satisfiable.” This family is a counterexample. But it is also easy
for our complete DPLL solver: branching on one variable propagates around the
path; both values conflict. That is exactly one decision and three visited nodes.
Changing the closing parity to zero gives a satisfiable control: two nodes.

The GF(2) solver detects inconsistency by eliminating variables. It accepts the
original equations as input; we have not solved the problem of discovering useful
linear structure inside arbitrary CNF. The cycle example is 2-CNF, and is not
intended as a hard family for general SAT algorithms.

**Candidate direction:** preserve relations, not just assignments. A hybrid
solver could retain XOR relations alongside clauses. Before calling this a general
shortcut, we would need to specify which relations it derives, how many it stores,
how expensive derivation is, and why the resulting reasoning decides every CNF.
None of those universal claims follows from solving parity systems.

## Experiment 3: a fast decision algorithm would also find SAT witnesses

Assume an exact SAT decision subroutine D. First ask whether F is satisfiable.
If yes, ask whether F AND (NOT x1) is satisfiable. Keep x1=False if yes and
x1=True otherwise, then repeat under the accumulated choices.

**Invariant:** the current constrained formula has a satisfying extension. If
its False restriction is unsatisfiable, its True restriction must be satisfiable.
After n choices we therefore have a full witness. This takes at most n+1 calls,
and each query adds at most n unit clauses, a polynomial increase in size.
`search_via_decision` implements the reduction; tests supply an independent
truth-table oracle.

This shows why decision and witness search are closely linked for SAT. It also
identifies the circular step in “just ask if this partial assignment extends”:
that question is itself SAT. Our actual subroutines may take exponential time;
using them in the reduction does not improve that bound. UNKNOWN is not a valid
Boolean oracle answer.

## Why the complete solver is exact

The implementation has a simple invariant: each search state represents precisely
those extensions of its current partial assignment that satisfy its residual
formula. Removing a satisfied clause, or a false literal, preserves that set.
An empty residual clause means there are no extensions; no remaining clauses
means any assignment of the remaining variables works. A unit clause forces its
literal. Otherwise, the two values of an unassigned variable partition all
possible extensions, so exploring both branches is complete.

Each propagation or decision assigns a previously unassigned variable. Thus an
unbounded run terminates. There are at most 2^(n+1)-1 states in a full binary
branching tree of depth n, with polynomial work per state in n and the formula
size. This is an exponential upper bound for this implementation, not a lower
bound for SAT. A budget interrupts that proof of exhaustive coverage, which is
why its result is UNKNOWN. Tests probe whether the code implements these rules.

## What the proof barriers rule out

| Barrier | Precise obstacle for a proposed general argument |
| --- | --- |
| Relativization | There are oracles giving equality and others giving inequality. A proof that works unchanged relative to every oracle cannot settle the unrelativized question. See [Baker–Gill–Solovay](https://doi.org/10.1137/0204037). |
| Natural proofs | Under the strong pseudorandomness assumptions in the theorem, circuit lower-bound properties that are constructive, large, and useful cannot yield the desired general circuit lower bounds. “Constructive” here is relative to truth-table size. This is a conditional barrier to a defined class of methods, not a ban on every combinatorial argument. See [Razborov–Rudich](https://www.sciencedirect.com/science/article/pii/S002200009791494X). |
| Algebrization | Even some techniques that go beyond ordinary oracle access, using low-degree algebraic extensions, are insufficient. An approach settling P vs NP must go beyond the formal algebrizing framework. Merely introducing polynomials does not do that. See [Aaronson–Wigderson](https://www.scottaaronson.com/papers/alg.pdf). |

The circuit route needs its own care: proving that an NP language requires
superpolynomial general Boolean circuits would imply P != NP, because a
polynomial-time computation can be unrolled into polynomial-size circuits.
This is a stronger target than merely separating uniform polynomial time from NP.
A bound limited to one restricted circuit or proof model does not transfer
automatically to general algorithms.

## Next hypothesis to try to break

A concrete follow-up is: **Can bounded-width XOR reasoning substantially reduce
branching on mixtures of parity constraints and ordinary 3-CNF clauses?**
Specify the width bound k first, retain the source equations, and count relation
construction and elimination as well as search. Compare against ordinary DPLL
on the identical CNF, with satisfiable controls and inconsistent instances.

If it wins, the result is a measured advantage on that family. If it loses,
minimize the losing input and identify the relation the strategy needs but cannot
retain. A possible later theorem would characterize this restricted method's
limits. To reach P vs NP, an argument must still quantify over every relevant
polynomial-time algorithm; changing the vocabulary from “search” to “relations”
does not discharge that obligation.

Finite success cannot establish a polynomial bound. A finite failure can refute
a universal correctness claim, which is why counterexample hunting is useful
here. Random formulas are exploratory distributions; they are not a substitute
for a worst-case argument.
