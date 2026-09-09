"""Independent truth tables, exhaustive tiny formulas, metamorphic checks."""

import itertools
from pathlib import Path
import random
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sat import (brute_force, pigeonhole, random_3sat, search_via_decision,
                 solve_brute_force, solve_dpll, verify)
from parity import parity_cycle, solve_xor, xor_to_cnf


def truth(clauses, bits):
    # Deliberately independent of the production verifier and normalizer.
    return all(any(bits[abs(v) - 1] if v > 0 else not bits[abs(v) - 1]
                   for v in clause) for clause in clauses)


def oracle(clauses, n):
    return next((bits for bits in itertools.product((False, True), repeat=n)
                 if truth(clauses, bits)), None)


class SatTests(unittest.TestCase):
    def check_formula(self, clauses, n):
        expected = oracle(clauses, n)
        for solver in (solve_brute_force, solve_dpll):
            result = solver(clauses, n)
            self.assertEqual(result.status, "UNSAT" if expected is None else "SAT",
                             (solver.__name__, clauses))
            if result.assignment is not None:
                self.assertEqual(len(result.assignment), n)
                self.assertTrue(truth(clauses, result.assignment))
        return expected

    def test_all_two_variable_cnf_formulas(self):
        # Each variable absent, positive, or negative: 9 non-tautological
        # clauses (including the empty clause), hence all 2**9 clause sets.
        universe = [tuple(sign * (i + 1) for i, sign in enumerate(signs) if sign)
                    for signs in itertools.product((0, 1, -1), repeat=2)]
        for mask in range(1 << len(universe)):
            self.check_formula([c for i, c in enumerate(universe) if mask & (1 << i)], 2)

    def test_boundary_and_normalization_cases(self):
        for clauses, n in [([], 0), ([[]], 0), ([], 4), ([[1], [-1]], 1),
                           ([[1, 1], [-1, -1]], 1), ([[1, -1]], 1),
                           ([[3, 3], [-3, 2]], 5), ([[1, -1], []], 1)]:
            self.check_formula(clauses, n)
        self.assertEqual(brute_force([], 0), ())
        self.assertFalse(verify([[]], ()))
        self.assertTrue(verify([], ()))

    def test_seeded_random_and_witness_verifier(self):
        for n in range(3, 8):
            for seed in range(25):
                clauses = random_3sat(n, 4 * n, seed)
                expected = self.check_formula(clauses, n)
                if expected is not None:
                    self.assertTrue(verify(clauses, expected))
        for bits in itertools.product((False, True), repeat=3):
            self.assertEqual(verify([[1, -2], [2, 3]], bits), truth([[1, -2], [2, 3]], bits))

    def test_renaming_sign_flips_and_permutations(self):
        rng = random.Random(91)
        for seed in range(30):
            original = random_3sat(5, 20, seed)
            names = list(range(1, 6))
            rng.shuffle(names)
            flips = [rng.choice((-1, 1)) for _ in names]
            changed = [[names[abs(v)-1] * flips[abs(v)-1] * (1 if v > 0 else -1)
                        for v in reversed(c)] for c in reversed(original)]
            changed += changed[:2] + [[1, -1]]
            expected = self.check_formula(original, 5)
            transformed = self.check_formula(changed, 5)
            self.assertEqual(expected is None, transformed is None)

    def test_inputs_are_not_mutated(self):
        clauses = [[1, 1, -2], [2], [-3, 3]]
        before = [c[:] for c in clauses]
        self.check_formula(clauses, 3)
        self.assertEqual(clauses, before)

    def test_budget_is_unknown_not_unsat(self):
        for solver in (solve_brute_force, solve_dpll):
            result = solver([[1]], 1, limit=0)
            self.assertEqual(result.status, "UNKNOWN")
            self.assertIsNone(result.assignment)
        self.assertEqual(solve_brute_force([[1]], 1, limit=1).status, "UNKNOWN")
        self.assertEqual(solve_brute_force([[1]], 1, limit=2).status, "SAT")
        self.assertEqual(solve_brute_force([[1], [-1]], 1, limit=2).status, "UNSAT")
        no_units = [[1, 2], [1, -2], [-1, 2], [-1, -2]]
        self.assertEqual(solve_dpll(no_units, 2, limit=1).status, "UNKNOWN")
        self.assertEqual(solve_dpll(no_units, 2, limit=3).status, "UNSAT")

    def test_unit_family_exact_work(self):
        for n in range(1, 9):
            clauses = [[v] for v in range(1, n + 1)]
            brute = solve_brute_force(clauses, n)
            dpll = solve_dpll(clauses, n)
            self.assertEqual(brute.stats.assignments, 2 ** n)
            self.assertEqual(dpll.stats.decisions, 0)
            self.assertEqual(dpll.stats.propagations, n)
            self.assertEqual(dpll.assignment, (True,) * n)

    def test_pigeonhole(self):
        for pigeons in range(4):
            for holes in range(4):
                clauses, n = pigeonhole(pigeons, holes)
                result = self.check_formula(clauses, n)
                self.assertEqual(result is not None, pigeons <= holes)

    def test_search_to_decision(self):
        for clauses, n in [([], 0), ([[]], 0), ([], 3), ([[1], [-1]], 1)] + [
                (random_3sat(5, 21, seed), 5) for seed in range(20)]:
            calls = []

            def decide(formula, n_vars):
                calls.append(formula)
                return oracle(formula, n_vars) is not None

            witness = search_via_decision(clauses, n, decide)
            self.assertEqual(witness is None, oracle(clauses, n) is None)
            self.assertLessEqual(len(calls), n + 1)
            if witness is not None:
                self.assertTrue(truth(clauses, witness))
        with self.assertRaises(ValueError):
            search_via_decision([[1]], 1, lambda *_: "UNKNOWN")

    def test_invalid_inputs(self):
        for solver in (solve_brute_force, solve_dpll):
            for clauses, n in [([[0]], 1), ([[2]], 1), ([[True]], 1),
                               ([[1.0]], 1), ([], -1), ([], True)]:
                with self.assertRaises(ValueError):
                    solver(clauses, n)
            with self.assertRaises(ValueError):
                solver([], 0, limit=-1)
        with self.assertRaises(ValueError):
            verify([[1]], (1,))
        with self.assertRaises(ValueError):
            random_3sat(2, 1)
        with self.assertRaises(ValueError):
            random_3sat(3, -1)

    def test_generator_seed(self):
        self.assertEqual(random_3sat(10, 20, 3), random_3sat(10, 20, 3))
        self.assertNotEqual(random_3sat(10, 20, 3), random_3sat(10, 20, 4))
        for c in random_3sat(10, 20):
            self.assertEqual(len({abs(v) for v in c}), 3)


class ParityTests(unittest.TestCase):
    def test_encoding_truth_tables(self):
        for width in range(4):
            for rhs in (0, 1):
                clauses = xor_to_cnf([(list(range(1, width + 1)), rhs)], width)
                for bits in itertools.product((False, True), repeat=width):
                    self.assertEqual(truth(clauses, bits), sum(bits) % 2 == rhs)

    def test_gaussian_against_truth_tables(self):
        rng = random.Random(9)
        for n in range(7):
            for _ in range(40):
                equations = [(rng.sample(range(1, n + 1), rng.randrange(n + 1)),
                              rng.randrange(2)) for _ in range(8)]
                expected = next((bits for bits in itertools.product((False, True), repeat=n)
                                 if all(sum(bits[v-1] for v in vs) % 2 == rhs
                                        for vs, rhs in equations)), None)
                witness = solve_xor(equations, n)
                self.assertEqual(witness is None, expected is None)
                if witness is not None:
                    self.assertTrue(all(sum(witness[v-1] for v in vs) % 2 == rhs
                                        for vs, rhs in equations))

    def test_parity_cycle_and_local_reasoning_gap(self):
        for n in range(3, 9):
            for inconsistent in (False, True):
                equations = parity_cycle(n, inconsistent)
                clauses = xor_to_cnf(equations, n)
                self.assertTrue(all(len(c) == 2 for c in clauses))
                result = solve_dpll(clauses, n)
                self.assertEqual(result.status, "UNSAT" if inconsistent else "SAT")
                self.assertEqual(solve_xor(equations, n) is None, inconsistent)
                self.assertEqual(result.stats.decisions, 1)
                self.assertEqual(result.stats.nodes, 3 if inconsistent else 2)

    def test_repeats_constants_and_width_limit(self):
        self.assertEqual(solve_xor([([1, 1], 0)], 1), (False,))
        self.assertIsNone(solve_xor([([1, 1], 1)], 1))
        self.assertEqual(xor_to_cnf([([1, 1], 1)], 1), [[]])
        self.assertEqual(solve_xor([], 0), ())
        with self.assertRaises(ValueError):
            xor_to_cnf([([1, 2, 3, 4], 0)], 4)
        for fn in (xor_to_cnf, solve_xor):
            for rows in [([([0], 0)]), ([([2], 0)]), ([([1], 2)])]:
                with self.assertRaises(ValueError):
                    fn(rows, 1)


class CliTests(unittest.TestCase):
    def test_json_is_reproducible_and_unknown_is_preserved(self):
        import json
        script = str(Path(__file__).resolve().parents[1] / "investigate.py")
        command = [sys.executable, script, "--sizes", "3", "--seeds", "7",
                   "--densities", "4", "--limit", "0", "--json"]
        first = subprocess.check_output(command, text=True)
        self.assertEqual(first, subprocess.check_output(command, text=True))
        rows = json.loads(first)
        self.assertTrue(rows)
        self.assertTrue(all(row["status"] == "UNKNOWN" for row in rows))
        self.assertTrue(all("seconds" not in row for row in rows))


if __name__ == "__main__":
    unittest.main()
