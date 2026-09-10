"""Linear equations over GF(2), with a bounded-width CNF encoding.

Rows are (variables, rhs), meaning XOR of those one-based variables equals
rhs (0 or 1). Repeated variables cancel. Gaussian elimination exploits the
supplied equation structure; this is not an arbitrary CNF-to-XOR recognizer.
"""

from itertools import product
from sat import natural


def _rows(equations, n_vars):
    natural(n_vars, "n_vars")
    rows = []
    for variables, rhs in equations:
        if type(rhs) is not int or rhs not in (0, 1):
            raise ValueError("rhs must be 0 or 1")
        mask = 0
        for var in variables:
            if type(var) is not int or not 1 <= var <= n_vars:
                raise ValueError("variables must be integers within n_vars")
            mask ^= 1 << (var - 1)
        rows.append((mask, rhs))
    return rows


def solve_xor(equations, n_vars):
    """Return a Boolean witness, or None on inconsistency; polynomial bit cost."""
    pivots = {}
    for mask, rhs in _rows(equations, n_vars):
        while mask:
            pivot = mask.bit_length() - 1
            if pivot not in pivots:
                pivots[pivot] = (mask, rhs)
                break
            old_mask, old_rhs = pivots[pivot]
            mask ^= old_mask
            rhs ^= old_rhs
        if not mask and rhs:
            return None
    solution = 0
    for pivot in sorted(pivots):
        mask, rhs = pivots[pivot]
        if (mask & solution).bit_count() % 2 != rhs:
            solution |= 1 << pivot
    return tuple(bool(solution & (1 << i)) for i in range(n_vars))


def xor_to_cnf(equations, n_vars):
    """Forbid each wrong-parity assignment; only rows of width <=3 allowed.

    Unbounded direct expansion would hide an exponential cost (2**(width-1)).
    Empty inconsistent rows produce an empty clause; tautological rows none.
    """
    clauses = []
    for mask, rhs in _rows(equations, n_vars):
        if mask.bit_count() > 3:
            raise ValueError("CNF expansion is restricted to XOR width <= 3")
        variables = [i + 1 for i in range(n_vars) if mask & (1 << i)]
        for bits in product((False, True), repeat=len(variables)):
            if sum(bits) % 2 != rhs:
                clauses.append([-v if bit else v for v, bit in zip(variables, bits)])
    return clauses


def parity_cycle(n_vars, inconsistent=True):
    """Equality along a cycle, with an optional contradictory closing edge."""
    natural(n_vars, "n_vars")
    if n_vars < 3:
        raise ValueError("cycle needs at least three variables")
    return [([i, i + 1], 0) for i in range(1, n_vars)] + [
        ([n_vars, 1], int(inconsistent))]
