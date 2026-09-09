"""Versioned mixed XOR/CNF experiments. Stdlib, Python 3.10+.

Create: python3 -B p-vs-np/mixed.py --output-dir p-vs-np/research/runs/001
Replay: python3 -B p-vs-np/mixed.py --check p-vs-np/research/runs/001
Existing output directories are never overwritten. Raw formulas, deterministic
counters, and source fingerprints are retained; timings are intentionally omitted.
"""

import argparse
import csv
from dataclasses import asdict
import hashlib
import io
import json
from pathlib import Path
import platform
import random

from hybrid import mixed_cnf, solve_gaussian, solve_hybrid
from parity import parity_cycle
from sat import natural, random_3sat, solve_dpll

ROOT = Path(__file__).resolve().parent
SOURCE_FILES = ('sat.py', 'parity.py', 'hybrid.py', 'mixed.py', 'research/counterexamples.json')


def generated_case(n, seed, planted=False):
    """Half as many XOR3 rows as variables, plus 2*n ordinary 3-CNF clauses.

    Planted controls force every constraint to accept a known random witness.
    They are a biased distribution, not uniform random formulas conditioned SAT.
    """
    natural(n, 'n')
    if n < 3:
        raise ValueError('n must be >= 3')
    rng = random.Random(seed)
    witness = tuple(bool(rng.getrandbits(1)) for _ in range(n))
    equations = []
    for _ in range(n // 2):
        variables = rng.sample(range(1, n + 1), 3)
        rhs = (sum(witness[v-1] for v in variables) % 2 if planted else rng.randrange(2))
        equations.append((variables, rhs))
    clauses = []
    for _ in range(2 * n):
        clause = [v * rng.choice((-1, 1)) for v in rng.sample(range(1, n + 1), 3)]
        if planted and not any(witness[abs(v)-1] == (v > 0) for v in clause):
            clause[0] *= -1
        clauses.append(clause)
    return dict(id=f"{'planted' if planted else 'mixed'}-n{n}-s{seed}",
                family='planted' if planted else 'mixed', n_vars=n, seed=seed,
                clauses=clauses, equations=equations,
                expected_status='SAT' if planted else None)


def corpus(sizes=(6, 10, 14), seeds=range(8)):
    cases = []
    for n in sizes:
        for seed in seeds:
            cases += [generated_case(n, seed, planted=p) for p in (False, True)]
            cases.append(dict(id=f'cnf-only-n{n}-s{seed}', family='cnf-only',
                              n_vars=n, seed=seed, clauses=random_3sat(n, 4 * n, seed),
                              equations=[], expected_status=None))
        for inconsistent in (False, True):
            cases.append(dict(id=f'cycle-n{n}-{int(inconsistent)}', family='cycle',
                              n_vars=n, seed=None, clauses=[],
                              equations=parity_cycle(n, inconsistent),
                              expected_status='UNSAT' if inconsistent else 'SAT'))
    fixture = json.loads((ROOT / 'research/counterexamples.json').read_text())['cases'][0]
    for inconsistent in (False, True):
        equations = [(vs, rhs) for vs, rhs in fixture['equations']]
        equations[-1] = (equations[-1][0], int(inconsistent))
        cases.append(dict(id=f'width-gap-{int(inconsistent)}', family='width-gap',
                          n_vars=6, seed=None, clauses=[], equations=equations,
                          expected_status='UNSAT' if inconsistent else 'SAT'))
    return cases


def satisfies(case, bits):
    """Independent raw CNF/XOR witness check, without encoding or normalization."""
    return (len(bits) == case['n_vars'] and all(type(v) is bool for v in bits)
            and all(any(bits[abs(v)-1] if v > 0 else not bits[abs(v)-1] for v in c)
                    for c in case['clauses'])
            and all(sum(bits[v-1] for v in vs) % 2 == rhs for vs, rhs in case['equations']))


def measure(cases, widths=(0, 2, 3, 4), node_limit=100_000, pair_limit=20_000,
            include_gaussian=False):
    rows = []
    for case in cases:
        cnf = mixed_cnf(case['clauses'], case['equations'], case['n_vars'])
        results = []
        for width in list(widths) + ([-1] if include_gaussian else []):
            if width == -1:
                result = solve_gaussian(case['clauses'], case['equations'], case['n_vars'],
                                        node_limit, elimination_limit=pair_limit)
            else:
                result = solve_hybrid(case['clauses'], case['equations'], case['n_vars'],
                                      width, node_limit, pair_limit)
            if width == 0:
                baseline = solve_dpll(cnf, case['n_vars'], node_limit)
                if (result.status, result.assignment) != (baseline.status, baseline.assignment):
                    raise AssertionError('disabled hybrid changed baseline answer')
                if any(getattr(result.stats, k) != v for k, v in asdict(baseline.stats).items()):
                    raise AssertionError('disabled hybrid changed baseline counters')
            if result.status == 'SAT' and not satisfies(case, result.assignment):
                raise AssertionError(f"invalid witness for {case['id']}, width={width}")
            expected = case['expected_status']
            if expected and result.status not in (expected, 'UNKNOWN'):
                raise AssertionError(f"wrong control result for {case['id']}")
            results.append(result.status)
            rows.append(dict(case_id=case['id'], family=case['family'], n_vars=case['n_vars'],
                             n_clauses=len(cnf), width=width, status=result.status,
                             witness=(''.join(str(int(v)) for v in result.assignment)
                                      if result.assignment is not None else ''),
                             **asdict(result.stats)))
            if include_gaussian:
                rows[-1]['method'] = ('gaussian' if width == -1 else
                                      'dpll' if width == 0 else f'bounded-{width}')
        if len(set(results) - {'UNKNOWN'}) > 1:
            raise AssertionError(f"solver disagreement for {case['id']}")
    return rows


def csv_text(rows):
    out = io.StringIO(newline='')
    writer = csv.DictWriter(out, fieldnames=list(dict.fromkeys(k for r in rows for k in r)), lineterminator='\n')
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def summary(rows):
    rows = list(rows)
    metrics = ('decisions', 'literal_checks', 'xor_pairs', 'xor_cutoffs')
    if any('xor_eliminations' in row for row in rows):
        metrics += ('xor_eliminations',)
    groups = {}
    for row in rows:
        key = (row['family'], row['width'])
        group = groups.setdefault(key, dict(cases=0, SAT=0, UNSAT=0, UNKNOWN=0,
                                           **{name: 0 for name in metrics}))
        group['cases'] += 1
        group[row['status']] += 1
        for name in metrics:
            group[name] += row.get(name, 0)
    return [{'family': family, 'width': width, **values}
            for (family, width), values in sorted(groups.items())]


def check_run(directory):
    """Recompute frozen inputs and exact deterministic results; never rewrite them."""
    manifest = json.loads((directory / 'manifest.json').read_text())
    raw = (directory / 'cases.json').read_bytes()
    expected = (directory / 'results.csv').read_bytes()
    if digest(raw) != manifest['cases_sha256'] or digest(expected) != manifest['results_sha256']:
        raise ValueError('recorded artifact hash mismatch')
    cases = json.loads(raw)
    actual = csv_text(measure(cases, **manifest['solver_config'])).encode()
    if actual != expected:
        raise ValueError('result drift: inspect the change and record a NEW run; do not overwrite history')
    if summary(list(measure_rows(expected))) != manifest['summary']:
        raise ValueError('recorded summary does not match results')
    changed = [name for name, sha in manifest['source_sha256'].items()
               if digest((ROOT / name).read_bytes()) != sha]
    return changed


def measure_rows(csv_bytes):
    for row in csv.DictReader(io.StringIO(csv_bytes.decode())):
        yield {k: (v if k in ('case_id', 'family', 'status', 'witness', 'method') else int(v or 0))
               for k, v in row.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--output-dir', type=Path)
    action.add_argument('--check', type=Path)
    parser.add_argument('--gaussian', action='store_true', help='also compare Gaussian inference')
    args = parser.parse_args()
    if args.check:
        changed = check_run(args.check)
        print('Frozen inputs, hashes, summary, and deterministic results agree.')
        if changed:
            print('Source files differ from recorded run (results still agree): ' + ', '.join(changed))
        return
    if args.output_dir.exists():
        parser.error('output directory already exists; choose a new run id')
    cases = corpus()
    config = dict(widths=[0, 2, 3, 4], node_limit=100_000, pair_limit=20_000)
    if args.gaussian:
        config['include_gaussian'] = True
    rows = measure(cases, **config)
    # One complete instance per line keeps a formula together during review.
    raw = ('[\n' + ',\n'.join(json.dumps(c, sort_keys=True) for c in cases) + '\n]\n').encode()
    results = csv_text(rows).encode()
    manifest = dict(schema_version=1, experiment='mixed-xor-width-v1',
                    python=platform.python_version(),
                    generator_config=dict(sizes=[6, 10, 14], seeds=list(range(8))),
                    solver_config=config, cases_sha256=digest(raw),
                    results_sha256=digest(results),
                    source_sha256={name: digest((ROOT / name).read_bytes()) for name in SOURCE_FILES},
                    summary=summary(rows))
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / 'cases.json').write_bytes(raw)
    (args.output_dir / 'results.csv').write_bytes(results)
    (args.output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True) + '\n')
    print(json.dumps(manifest['summary'], indent=2))
    print(f"Saved {len(rows)} results for {len(cases)} cases to {args.output_dir}")


if __name__ == '__main__':
    main()
