"""Reproduce and deletion-minimize a bounded-inference budget counterexample.

Run: python3 -B p-vs-np/counterexamples.py
The search is deterministic: increasing cycle size (3..8), then cap (1..100).
Minimal means no single remaining constraint can be deleted while preserving
the predicate; it does not mean globally smallest across all formulas.
"""

import copy
import json

from hybrid import bounded_closure
from parity import parity_cycle


def minimize_constraints(case, predicate):
    candidate = copy.deepcopy(case)
    if not predicate(candidate):
        raise ValueError('input does not satisfy the counterexample predicate')
    changed = True
    while changed:
        changed = False
        for key in ('clauses', 'equations'):
            for i in range(len(candidate[key])):
                smaller = copy.deepcopy(candidate)
                del smaller[key][i]
                if predicate(smaller):
                    candidate = smaller
                    changed = True
                    break
            if changed:
                break
    return candidate


def budget_gap(case):
    narrow, _ = bounded_closure(case['equations'], case['n_vars'], 2, case['pair_limit'])
    wide, _ = bounded_closure(case['equations'], case['n_vars'], 4, case['pair_limit'])
    return narrow.conflict and not wide.conflict and not wide.saturated


def find_budget_gap(max_vars=8, max_pairs=100):
    for n in range(3, max_vars + 1):
        for cap in range(1, max_pairs + 1):
            case = dict(id='width-is-not-budget-monotone', n_vars=n, pair_limit=cap,
                        clauses=[], equations=parity_cycle(n), expected_status='UNSAT',
                        claim_refuted='Wider XOR closure is always at least as effective under the same pair-attempt budget.')
            if budget_gap(case):
                return minimize_constraints(case, budget_gap)
    return None


if __name__ == '__main__':
    print(json.dumps(find_budget_gap(), indent=2))
