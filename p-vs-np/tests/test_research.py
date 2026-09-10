"""Durable research artifacts must replay, retain old results, and reject drift."""

import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from counterexamples import budget_gap, find_budget_gap, minimize_constraints
from hybrid import solve_hybrid
from investigate import run
from mixed import check_run, corpus, generated_case, measure, satisfies

ROOT = Path(__file__).resolve().parents[1]


class ResearchTests(unittest.TestCase):
    def test_original_76_results_remain_unchanged(self):
        baseline = json.loads((ROOT / 'research/baseline-v1.json').read_text())
        rows = run(**baseline['config'])
        actual = [{k: v for k, v in r.items() if k != 'seconds'} for r in rows]
        self.assertEqual(actual, baseline['results'])

    def test_recorded_experiments_replay_without_count_drift(self):
        for name in ('001', '002'):
            with self.subTest(run=name):
                check_run(ROOT / 'research/runs' / name)

    def test_all_80_benchmark_answers_against_independent_truth_tables(self):
        import csv
        from itertools import product
        directory = ROOT / 'research/runs/002'
        cases = json.loads((directory / 'cases.json').read_text())
        with (directory / 'results.csv').open() as source:
            statuses = {r['case_id']: r['status'] for r in csv.DictReader(source)}
        for case in cases:
            satisfiable = any(satisfies(case, bits)
                              for bits in product((False, True), repeat=case['n_vars']))
            self.assertEqual(statuses[case['id']], 'SAT' if satisfiable else 'UNSAT', case['id'])

    def test_paired_experiments_use_identical_instances(self):
        runs = ROOT / 'research/runs'
        first = (runs / '001/cases.json').read_bytes()
        self.assertEqual(first, (runs / '002/cases.json').read_bytes())
        self.assertEqual(json.loads(first), json.loads(json.dumps(corpus())))

    def test_budget_counterexample_reproduces_and_is_deletion_minimal(self):
        fixture = json.loads((ROOT / 'research/counterexamples.json').read_text())['cases'][1]
        found = find_budget_gap()
        for key in ('n_vars', 'pair_limit', 'clauses', 'equations'):
            self.assertEqual(json.loads(json.dumps(found[key])), fixture[key])
        self.assertTrue(budget_gap(fixture))
        for i in range(len(fixture['equations'])):
            smaller = dict(fixture, equations=fixture['equations'][:i] + fixture['equations'][i+1:])
            self.assertFalse(budget_gap(smaller))
        for width in (2, 4):
            self.assertEqual(solve_hybrid([], fixture['equations'], fixture['n_vars'], width,
                                         pair_limit=fixture['pair_limit']).status, 'UNSAT')

    def test_minimizer_removes_irrelevant_constraints_without_mutating_input(self):
        case = dict(clauses=[[1], [-1], [2]], equations=[([2], 0)], n_vars=2)
        before = json.dumps(case)
        predicate = lambda c: [1] in c['clauses'] and [-1] in c['clauses']
        result = minimize_constraints(case, predicate)
        self.assertEqual(result['clauses'], [[1], [-1]])
        self.assertEqual(result['equations'], [])
        self.assertEqual(json.dumps(case), before)
        with self.assertRaises(ValueError):
            minimize_constraints(case, lambda _: False)

    def test_artifact_tampering_is_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / 'run'
            shutil.copytree(ROOT / 'research/runs/001', copy)
            with (copy / 'results.csv').open('a') as out:
                out.write('changed\n')
            with self.assertRaisesRegex(ValueError, 'hash mismatch'):
                check_run(copy)

    def test_cli_refuses_to_overwrite_an_existing_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'mixed.py'),
                                     '--output-dir', tmp], capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('already exists', result.stderr)
            self.assertEqual(list(Path(tmp).iterdir()), [])

    def test_planted_generation_and_budget_output(self):
        from itertools import product
        case = generated_case(5, 17, planted=True)
        self.assertEqual(case, generated_case(5, 17, planted=True))
        self.assertTrue(any(satisfies(case, bits) for bits in product((False, True), repeat=5)))
        rows = measure([case], node_limit=0, include_gaussian=True)
        self.assertEqual(len(rows), 5)
        self.assertTrue(all(r['status'] == 'UNKNOWN' and r['witness'] == '' for r in rows))


if __name__ == '__main__':
    unittest.main()
