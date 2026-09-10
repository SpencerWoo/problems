"""Small exact CNF solvers; standard library only, intentionally not optimized.

A literal +/-i refers to Boolean variable i (one-based). A formula is an
iterable of clauses. [] is true; [[]] is false. Inputs are never mutated.
"""

from dataclasses import dataclass, field
from itertools import product
import random


def natural(value, name):
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative integer")


def normalize(clauses, n_vars):
    natural(n_vars, "n_vars")
    result = []
    for clause in clauses:
        unique = []
        seen = set()
        for lit in clause:
            if type(lit) is not int or not 1 <= abs(lit) <= n_vars:
                raise ValueError("literals must be nonzero integers within n_vars")
            if lit not in seen:
                unique.append(lit)
                seen.add(lit)
        if not any(-lit in seen for lit in seen):
            result.append(tuple(unique))
    return tuple(result)


def verify(clauses, assignment):
    """Verify a complete Boolean witness, in O(n + total literal occurrences)."""
    bits = tuple(assignment)
    if any(type(bit) is not bool for bit in bits):
        raise ValueError("assignment must contain booleans")
    formula = normalize(clauses, len(bits))
    return all(any(bits[abs(lit) - 1] == (lit > 0) for lit in c) for c in formula)


@dataclass
class Stats:
    assignments: int = 0
    nodes: int = 0
    decisions: int = 0
    propagations: int = 0
    conflicts: int = 0
    literal_checks: int = 0


@dataclass
class Result:
    status: str  # SAT, UNSAT, or UNKNOWN (budget exhausted)
    assignment: tuple | None = None
    stats: Stats = field(default_factory=Stats)


def _budget(limit):
    if limit is not None:
        natural(limit, "limit")


def solve_brute_force(clauses, n_vars, limit=None):
    """Enumerate witnesses; limit counts attempted full assignments."""
    formula = normalize(clauses, n_vars)
    _budget(limit)
    stats = Stats()
    for bits in product((False, True), repeat=n_vars):
        if limit is not None and stats.assignments >= limit:
            return Result("UNKNOWN", stats=stats)
        stats.assignments += 1
        satisfied = True
        for clause in formula:
            clause_true = False
            for lit in clause:
                stats.literal_checks += 1
                if bits[abs(lit) - 1] == (lit > 0):
                    clause_true = True
                    break
            if not clause_true:
                satisfied = False
                break
        if satisfied:
            return Result("SAT", bits, stats)
    return Result("UNSAT", stats=stats)


def _simplify(formula, values, stats):
    residual = []
    for clause in formula:
        rest = []
        for lit in clause:
            stats.literal_checks += 1
            value = values.get(abs(lit))
            if value is None:
                rest.append(lit)
            elif value == (lit > 0):
                break
        else:
            if not rest:
                return None  # conflict; distinct from the satisfied empty formula
            residual.append(tuple(rest))
    return tuple(residual)


def solve_dpll(clauses, n_vars, limit=None):
    """Unit propagation + first literal of shortest clause, false branch first.

    No learning, pure-literal rule, or restarts. Iterative depth-first search.
    limit counts popped search nodes, not time or literal operations.
    """
    formula = normalize(clauses, n_vars)
    _budget(limit)
    return _search_dpll(formula, n_vars, limit, Stats())


def _search_dpll(formula, n_vars, limit, stats, infer=None):
    """Shared search loop; optional sound inference returns forced values or None.

    None means conflict. Empty dict means no additional information. Inference
    is invoked only after CNF unit propagation stalls, before branching.
    """
    stack = [(formula, {})]
    while stack:
        if limit is not None and stats.nodes >= limit:
            return Result("UNKNOWN", stats=stats)
        current, values = stack.pop()
        stats.nodes += 1
        while True:
            current = _simplify(current, values, stats)
            if current is None:
                stats.conflicts += 1
                break
            if not current:
                witness = tuple(values.get(i, False) for i in range(1, n_vars + 1))
                return Result("SAT", witness, stats)
            unit = next((c[0] for c in current if len(c) == 1), None)
            if unit is None:
                if infer is not None:
                    forced = infer(values)
                    if forced is None:
                        stats.conflicts += 1
                        break
                    if forced:
                        values.update(forced)
                        stats.propagations += len(forced)
                        continue
                var = abs(min(current, key=len)[0])
                stats.decisions += 1
                for value in (True, False):  # stack visits False first
                    stack.append((current, {**values, var: value}))
                break
            values[abs(unit)] = unit > 0
            stats.propagations += 1
    return Result("UNSAT", stats=stats)


def brute_force(clauses, n_vars):
    """Compatibility wrapper for the original unbounded demo API."""
    return solve_brute_force(clauses, n_vars).assignment


def search_via_decision(clauses, n_vars, decide):
    """Recover a witness with at most n+1 calls to an exact Boolean SAT oracle.

    Oracle signature: decide(clauses, n_vars) -> bool. A budget-limited result
    must not be treated as False. This reduction does not make the oracle fast.
    """
    formula = normalize(clauses, n_vars)

    def query(candidate):
        answer = decide(candidate, n_vars)
        if type(answer) is not bool:
            raise ValueError("decision oracle must return an exact boolean")
        return answer

    if not query(formula):
        return None
    bits = []
    for var in range(1, n_vars + 1):
        value = not query(formula + ((-var,),))
        bits.append(value)
        formula += ((var if value else -var,),)
    return tuple(bits)


def random_3sat(n_vars, n_clauses, seed=0):
    natural(n_vars, "n_vars")
    natural(n_clauses, "n_clauses")
    if n_vars < 3:
        raise ValueError("random 3-SAT needs at least three variables")
    rng = random.Random(seed)
    return [[v if rng.random() < 0.5 else -v
             for v in rng.sample(range(1, n_vars + 1), 3)]
            for _ in range(n_clauses)]


def pigeonhole(pigeons, holes):
    """CNF: each pigeon occupies a hole; no two pigeons share a hole.

    Multiple holes per pigeon are allowed, without changing satisfiability.
    Returns (clauses, number of variables). Clauses may have width other than 3.
    """
    natural(pigeons, "pigeons")
    natural(holes, "holes")
    var = lambda p, h: p * holes + h + 1
    clauses = [[var(p, h) for h in range(holes)] for p in range(pigeons)]
    clauses += [[-var(p, h), -var(q, h)] for h in range(holes)
                for p in range(pigeons) for q in range(p + 1, pigeons)]
    return clauses, pigeons * holes
