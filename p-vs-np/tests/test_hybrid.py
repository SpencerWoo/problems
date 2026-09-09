"""Check mixed reasoning against raw truth tables, not just another solver."""

from dataclasses import asdict
import itertools
import json
from pathlib import Path
import random
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from hybrid import (bounded_closure, gaussian_consequences, mixed_cnf,
                    solve_gaussian, solve_hybrid)
from parity import parity_cycle, solve_xor
from sat import solve_dpll

ROOT = Path(__file__).resolve().parents[1]


def models(clauses, equations, n):
    return [bits for bits in itertools.product((False, True), repeat=n)
            if all(any(bits[abs(v)-1] if v > 0 else not bits[abs(v)-1] for v in c)
                   for c in clauses)
            and all(sum(bits[v-1] for v in vs) % 2 == rhs for vs, rhs in equations)]


class HybridTests(unittest.TestCase):
    def check_mixed(self, clauses, equations, n):
        expected = models(clauses, equations, n)
        encoded = mixed_cnf(clauses, equations, n)
        self.assertEqual(models(encoded, [], n), expected)
        baseline = solve_dpll(encoded, n)
        self.assertEqual(baseline.status, "SAT" if expected else "UNSAT")
        gaussian = solve_gaussian(clauses, equations, n, elimination_limit=2000)
        self.assertEqual(gaussian.status, "SAT" if expected else "UNSAT")
        self.assertLessEqual(gaussian.stats.xor_peak_rows, n)
        self.assertLessEqual(gaussian.stats.xor_eliminations, 2000)
        if expected:
            self.assertIn(gaussian.assignment, expected)
        for width in (0, 1, 2, 3, 4):
            result = solve_hybrid(clauses, equations, n, width, pair_limit=2000)
            self.assertEqual(result.status, "SAT" if expected else "UNSAT",
                             (clauses, equations, width))
            if expected:
                self.assertIn(result.assignment, expected)
            self.assertLessEqual(result.stats.xor_pairs, 2000)
            if width == 0:
                self.assertEqual(result.assignment, baseline.assignment)
                for name, count in asdict(baseline.stats).items():
                    self.assertEqual(getattr(result.stats, name), count)

    def test_exhaustive_two_variable_mixtures(self):
        # All 64 subsets of six nonconstant normalized XOR equations, crossed
        # with every single non-tautological two-variable clause, plus no clause.
        equations = [(vs, rhs) for vs in ([1], [2], [1, 2]) for rhs in (0, 1)]
        clauses = [[s * (i + 1) for i, s in enumerate(signs) if s]
                   for signs in itertools.product((0, 1, -1), repeat=2)]
        for mask in range(64):
            rows = [eq for i, eq in enumerate(equations) if mask & (1 << i)]
            for cnf in [[]] + [[c] for c in clauses]:
                self.check_mixed(cnf, rows, 2)

    def test_random_mixed_formulas(self):
        rng = random.Random(618)
        for n in range(3, 8):
            for _ in range(20):
                equations = [(rng.sample(range(1, n + 1), rng.randrange(1, 4)),
                              rng.randrange(2)) for _ in range(n)]
                clauses = [[v * rng.choice((-1, 1))
                            for v in rng.sample(range(1, n + 1), 3)] for _ in range(n)]
                self.check_mixed(clauses, equations, n)

    def test_closure_relations_are_entailed(self):
        rng = random.Random(177)
        for _ in range(80):
            equations = [(rng.sample(range(1, 6), rng.randrange(1, 4)), rng.randrange(2))
                         for _ in range(4)]
            expected = models([], equations, 5)
            for width in (1, 2, 3, 4):
                closure, _ = bounded_closure(equations, 5, width)
                if closure.conflict:
                    self.assertFalse(expected)
                for mask, rhs in closure.relations:
                    self.assertLessEqual(mask.bit_count(), width)
                    for bits in expected:
                        self.assertEqual(sum(bits[i] for i in range(5) if mask & (1 << i)) % 2, rhs)

    def test_fixture_width_gap_and_deletion_minimality(self):
        case = json.loads((ROOT / 'research/counterexamples.json').read_text())['cases'][0]
        equations, n = case['equations'], case['n_vars']
        self.assertFalse(models([], equations, n))
        self.assertIsNone(solve_xor(equations, n))
        narrow, _ = bounded_closure(equations, n, width=3)
        wide, _ = bounded_closure(equations, n, width=4)
        self.assertTrue(narrow.saturated)
        self.assertFalse(narrow.conflict)
        self.assertFalse(narrow.units)
        self.assertEqual(len(narrow.relations), 4)
        self.assertTrue(wide.conflict)
        result = solve_hybrid([], equations, n, width=4)
        self.assertEqual(result.status, 'UNSAT')
        self.assertEqual(result.stats.decisions, 0)
        self.assertGreater(solve_hybrid([], equations, n, width=3).stats.decisions, 0)
        for i in range(len(equations)):
            self.assertTrue(models([], equations[:i] + equations[i+1:], n))
        self.check_mixed([], equations, n)

    def test_more_width_retains_more_relations_on_consistent_input(self):
        equations = [([1, 2, 3], 0), ([1, 4, 5], 0), ([2, 4, 6], 0)]
        previous = set()
        for width in range(1, 7):
            closure, _ = bounded_closure(equations, 6, width)
            self.assertFalse(closure.conflict)
            self.assertTrue(closure.saturated)
            self.assertLessEqual(previous, set(closure.relations))
            previous = set(closure.relations)

    def test_inference_budget_falls_back_to_exact_search(self):
        equations = parity_cycle(6)
        for cap in (0, 1, 5):
            result = solve_hybrid([], equations, 6, width=3, pair_limit=cap)
            self.assertEqual(result.status, 'UNSAT')
            self.assertLessEqual(result.stats.xor_pairs, cap)
            self.assertGreater(result.stats.xor_cutoffs, 0)
        closure, stats = bounded_closure(equations, 6, pair_limit=0)
        self.assertFalse(closure.conflict)
        self.assertFalse(closure.saturated)
        self.assertEqual(stats.xor_pairs, 0)
        limited = solve_hybrid([], equations, 6, limit=1, pair_limit=0)
        self.assertEqual(limited.status, 'UNKNOWN')
        self.assertIsNone(limited.assignment)
        self.assertEqual(solve_hybrid([], equations, 6, limit=0).status, 'UNKNOWN')

    def test_xor_derived_units_feed_cnf_propagation(self):
        equations = [([1, 2, 3], 0), ([1, 2], 0)]
        clauses = [[3, 4], [-4, 5]]
        result = solve_hybrid(clauses, equations, 5)
        self.assertEqual(result.status, 'SAT')
        self.assertGreater(result.stats.xor_forced, 0)
        self.assertEqual(result.assignment[2:], (False, True, True))
        self.check_mixed(clauses, equations, 5)

    def test_separately_satisfiable_parts_can_conflict(self):
        equations = [([1, 2, 3], 0)]
        # CNF encodes the opposite parity, so its standalone model is insufficient.
        clauses = [[1, 2, 3], [1, -2, -3], [-1, 2, -3], [-1, -2, 3]]
        self.assertTrue(models(clauses, [], 3))
        self.assertTrue(models([], equations, 3))
        self.assertFalse(models(clauses, equations, 3))
        self.check_mixed(clauses, equations, 3)

    def test_complete_xor_inference_does_not_decide_all_mixed_formulas(self):
        equations = [([1, 2, 3], 0)]
        clauses = [[1, 2, 3], [1, -2, -3], [-1, 2, -3], [-1, -2, 3]]
        root, _ = gaussian_consequences(equations, 3)
        self.assertFalse(root.conflict)
        self.assertEqual(root.units, {})
        result = solve_gaussian(clauses, equations, 3)
        self.assertEqual(result.status, 'UNSAT')
        self.assertEqual(result.stats.decisions, 3)
        # Every constraint is essential to this contradiction.
        for i in range(len(clauses)):
            self.assertTrue(models(clauses[:i] + clauses[i+1:], equations, 3))
        self.assertTrue(models(clauses, [], 3))

    def test_empty_duplicate_tautological_and_unused_variables(self):
        for clauses, equations, n in [([], [], 0), ([[]], [], 0), ([], [([], 1)], 0),
                ([], [([], 0)], 0), ([[1, -1]], [([1, 1], 0)], 5),
                ([], [([1, 1], 1)], 1), ([], [([1, 2], 0), ([1, 2], 0)], 3)]:
            self.check_mixed(clauses, equations, n)

    def test_inputs_and_iterators(self):
        clauses, equations = [[1, 2]], [([1, 2, 3], 1)]
        before = json.dumps([clauses, equations])
        first = solve_hybrid(clauses, equations, 3)
        second = solve_hybrid((iter(c) for c in clauses),
                              ((iter(vs), rhs) for vs, rhs in equations), 3)
        self.assertEqual(first, second)
        self.assertEqual(json.dumps([clauses, equations]), before)

    def test_renaming_flips_and_order(self):
        clauses = [[1, 3, -5], [-2, 4, 5]]
        equations = [([1, 2, 3], 0), ([1, 4, 5], 1), ([2, 4], 0)]
        baseline = solve_hybrid(clauses, equations, 5)
        names = [4, 1, 5, 2, 3]
        flips = [True, False, True, False, False]
        moved_clauses = [[names[abs(v)-1] * (1 if (v > 0) != flips[abs(v)-1] else -1)
                          for v in reversed(c)] for c in reversed(clauses)]
        moved_rows = [(list(reversed([names[v-1] for v in vs])),
                       rhs ^ (sum(flips[v-1] for v in vs) % 2))
                      for vs, rhs in reversed(equations)]
        self.check_mixed(moved_clauses, moved_rows, 5)
        self.assertEqual(solve_hybrid(moved_clauses, moved_rows, 5).status, baseline.status)

    def test_gaussian_finds_exactly_all_forced_variables(self):
        rng = random.Random(241)
        for n in range(7):
            for _ in range(40):
                equations = [(rng.sample(range(1, n + 1), rng.randrange(n + 1)),
                              rng.randrange(2)) for _ in range(5)]
                expected = models([], equations, n)
                inference, stats = gaussian_consequences(equations, n)
                self.assertTrue(inference.saturated)
                self.assertEqual(inference.conflict, not bool(expected))
                self.assertLessEqual(stats.xor_peak_rows, n)
                if expected:
                    forced = {i + 1: expected[0][i] for i in range(n)
                              if len({bits[i] for bits in expected}) == 1}
                    self.assertEqual(inference.units, forced)

    def test_gaussian_cutoffs_preserve_soundness_and_exact_search(self):
        equations = parity_cycle(6)
        for cap in (0, 1, 3):
            inference, stats = gaussian_consequences(equations, 6, cap)
            self.assertLessEqual(stats.xor_eliminations, cap)
            self.assertFalse(inference.saturated)
            result = solve_gaussian([], equations, 6, elimination_limit=cap)
            self.assertEqual(result.status, 'UNSAT')
            self.assertGreater(result.stats.xor_cutoffs, 0)
            self.assertLessEqual(result.stats.xor_eliminations, cap)
        result = solve_gaussian([], equations, 6, limit=1, elimination_limit=0)
        self.assertEqual(result.status, 'UNKNOWN')
        # A partially reduced basis can yield units, but every one must be sound.
        rows = [([1], 1), ([1, 2], 0), ([2, 3], 1), ([3, 4], 0)]
        expected = models([], rows, 4)
        for cap in range(6):
            inference, _ = gaussian_consequences(rows, 4, cap)
            for var, value in inference.units.items():
                self.assertTrue(all(bits[var-1] == value for bits in expected))

    def test_gaussian_back_reduction_is_needed_for_forced_units(self):
        # Forward echelon rows can still contain already-forced lower pivots.
        equations = [([1, 2], 0), ([1], 1)]
        inference, _ = gaussian_consequences(equations, 2)
        self.assertEqual(inference.units, {1: True, 2: True})
        for options in (dict(limit=-1), dict(elimination_limit=-1)):
            with self.assertRaises(ValueError):
                solve_gaussian([], [], 0, **options)

    def test_invalid_inputs(self):
        for options in [dict(width=-1), dict(width=True), dict(limit=-1), dict(pair_limit=-1)]:
            with self.assertRaises(ValueError):
                solve_hybrid([], [], 0, **options)
        for equations in [[([0], 0)], [([1], 2)], [([1, 2, 3, 4], 0)]]:
            with self.assertRaises(ValueError):
                solve_hybrid([], equations, 4)


if __name__ == '__main__':
    unittest.main()
