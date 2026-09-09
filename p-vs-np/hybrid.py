"""DPLL augmented with bounded-width pairwise XOR closure.

The input is ordinary CNF AND supplied XOR equations of width <=3. Both solvers
can receive exactly the same CNF via mixed_cnf(); the hybrid additionally knows
which clauses came from equations. This module does not discover XORs in CNF.
"""

from dataclasses import dataclass

from parity import _rows, xor_to_cnf
from sat import Stats, _budget, _search_dpll, natural, normalize


@dataclass
class HybridStats(Stats):
    xor_source_rows: int = 0
    xor_source_literals: int = 0
    xor_calls: int = 0
    xor_row_checks: int = 0
    xor_pairs: int = 0
    xor_pair_bit_volume: int = 0
    xor_derived: int = 0
    xor_peak_rows: int = 0
    xor_cutoffs: int = 0
    xor_forced: int = 0


@dataclass
class Closure:
    # A mask's bit i represents variable i+1; rhs is the equation's parity.
    relations: tuple
    conflict: bool
    saturated: bool  # False means a pair budget interrupted closure.

    @property
    def units(self):
        return {mask.bit_length(): bool(rhs) for mask, rhs in self.relations
                if mask.bit_count() == 1}


def _closure(rows, values, width, pair_limit, stats):
    stats.xor_calls += 1
    assigned = sum(1 << (v - 1) for v in values)
    true = sum(1 << (v - 1) for v, value in values.items() if value)
    known = {}
    retained = []

    def add(mask, rhs, derived=False):
        if not mask:
            return rhs == 1
        if mask.bit_count() > width:
            return False
        if mask in known:
            return known[mask] != rhs
        known[mask] = rhs
        retained.append((mask, rhs))
        stats.xor_derived += int(derived)
        stats.xor_peak_rows = max(stats.xor_peak_rows, len(retained))
        return False

    for mask, rhs in rows:
        stats.xor_row_checks += 1
        rhs ^= (mask & true).bit_count() % 2
        mask &= ~assigned
        if add(mask, rhs):
            return Closure(tuple(retained), True, True)

    i = 0
    # Every unordered pair of distinct retained equations is tried once per call.
    # Newly retained rows get their own turn, yielding closure when uncapped.
    while i < len(retained):
        mask, rhs = retained[i]
        for j in range(i):
            if pair_limit is not None and stats.xor_pairs >= pair_limit:
                stats.xor_cutoffs += 1
                return Closure(tuple(retained), False, False)
            other, parity = retained[j]
            stats.xor_pairs += 1
            stats.xor_pair_bit_volume += max(mask.bit_length(), other.bit_length())
            if add(mask ^ other, rhs ^ parity, derived=True):
                return Closure(tuple(retained), True, True)
        i += 1
    return Closure(tuple(retained), False, True)


def bounded_closure(equations, n_vars, width=3, pair_limit=None):
    """Root XOR closure for research; return (Closure, HybridStats).

    Retain inputs and pairwise sums only if their support size is <=width.
    Wider input rows are ignored by this *incomplete* inference function.
    An absent conflict is not a satisfiability decision, even when saturated.
    """
    natural(width, "width")
    _budget(pair_limit)
    rows = _rows(equations, n_vars)
    stats = HybridStats(xor_source_rows=len(rows),
                        xor_source_literals=sum(m.bit_count() for m, _ in rows))
    return _closure(rows, {}, width, pair_limit, stats), stats


def mixed_cnf(clauses, equations, n_vars):
    """Encode the conjunction; equations must have normalized width <=3."""
    return normalize(clauses, n_vars) + normalize(xor_to_cnf(equations, n_vars), n_vars)


def solve_hybrid(clauses, equations, n_vars, width=3, limit=None, pair_limit=100_000):
    """Exact SAT search plus optional bounded-width inference at each stalled node.

    limit is the search-node budget (UNKNOWN on exhaustion). pair_limit is the
    total pair-attempt budget across the entire solve. Once it is exhausted,
    search continues using sound deductions already found and ordinary CNF.
    No derived relation is carried between calls or branches. width=0 disables
    the module, providing a control identical to ordinary DPLL on mixed_cnf().
    """
    natural(width, "width")
    _budget(limit)
    _budget(pair_limit)
    equations = [(tuple(vs), rhs) for vs, rhs in equations]
    rows = _rows(equations, n_vars)
    formula = mixed_cnf(clauses, equations, n_vars)
    stats = HybridStats(xor_source_rows=len(rows),
                        xor_source_literals=sum(m.bit_count() for m, _ in rows))

    def infer(values):
        closure = _closure(rows, values, width, pair_limit, stats)
        if closure.conflict:
            return None
        forced = closure.units
        stats.xor_forced += len(forced)
        return forced

    return _search_dpll(formula, n_vars, limit, stats,
                        infer if width and rows else None)


@dataclass
class GaussianStats(HybridStats):
    xor_eliminations: int = 0
    xor_elimination_bit_volume: int = 0


def _gaussian(rows, values, elimination_limit, stats):
    """Restrict, build an echelon basis, then reduce every pivot column.

    A reduced row has one pivot plus free variables. It forces its pivot iff
    there are no free variables in that row. Free variables are not forced.
    """
    stats.xor_calls += 1
    assigned = sum(1 << (v - 1) for v in values)
    true = sum(1 << (v - 1) for v, value in values.items() if value)
    basis = {}

    def exhausted():
        if elimination_limit is not None and stats.xor_eliminations >= elimination_limit:
            stats.xor_cutoffs += 1
            return True
        return False

    def record_addition(a, b):
        stats.xor_eliminations += 1
        stats.xor_elimination_bit_volume += max(a.bit_length(), b.bit_length())

    for mask, rhs in rows:
        stats.xor_row_checks += 1
        rhs ^= (mask & true).bit_count() % 2
        mask &= ~assigned
        while mask:
            pivot = mask.bit_length() - 1
            if pivot not in basis:
                basis[pivot] = (mask, rhs)
                stats.xor_peak_rows = max(stats.xor_peak_rows, len(basis))
                break
            if exhausted():
                return Closure(tuple(basis.values()), False, False)
            other, parity = basis[pivot]
            record_addition(mask, other)
            mask ^= other
            rhs ^= parity
        if not mask and rhs:
            return Closure(tuple(basis.values()), True, True)

    pivots = sorted(basis)
    for i, pivot in enumerate(pivots):
        mask, rhs = basis[pivot]
        for higher in pivots[i + 1:]:
            other, parity = basis[higher]
            if other & (1 << pivot):
                if exhausted():
                    return Closure(tuple(basis.values()), False, False)
                record_addition(mask, other)
                basis[higher] = (mask ^ other, rhs ^ parity)
    return Closure(tuple(basis.values()), False, True)


def gaussian_consequences(equations, n_vars, elimination_limit=None):
    """Return all forced XOR literals / inconsistency when inference completes.

    The retained relations form a basis, not an enumerated closure. A cutoff
    leaves sound but potentially incomplete deductions, as in bounded_closure.
    """
    _budget(elimination_limit)
    rows = _rows(equations, n_vars)
    stats = GaussianStats(xor_source_rows=len(rows),
                          xor_source_literals=sum(m.bit_count() for m, _ in rows))
    return _gaussian(rows, {}, elimination_limit, stats), stats


def solve_gaussian(clauses, equations, n_vars, limit=None, elimination_limit=100_000):
    """Exact mixed SAT search, with Gaussian inference after CNF propagation.

    Only n independent rows are retained per inference call. The global row-XOR
    budget limits inference, not search correctness. No cross-call basis cache.
    """
    _budget(limit)
    _budget(elimination_limit)
    equations = [(tuple(vs), rhs) for vs, rhs in equations]
    rows = _rows(equations, n_vars)
    formula = mixed_cnf(clauses, equations, n_vars)
    stats = GaussianStats(xor_source_rows=len(rows),
                          xor_source_literals=sum(m.bit_count() for m, _ in rows))

    def infer(values):
        result = _gaussian(rows, values, elimination_limit, stats)
        if result.conflict:
            return None
        forced = result.units
        stats.xor_forced += len(forced)
        return forced

    return _search_dpll(formula, n_vars, limit, stats, infer if rows else None)
