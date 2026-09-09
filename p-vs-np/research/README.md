# Research record

Start with the [dated findings](FINDINGS.md). These files preserve hypotheses,
negative results, exact inputs, and replayable counters across iterations.
This is the repository's research log; it does not depend on session memory.

| Artifact | What it preserves |
| --- | --- |
| [baseline-v1.json](baseline-v1.json) | The 76 original results from commit `b026211`, before the shared search loop changed |
| [counterexamples.json](counterexamples.json) | Explicit width-limit and inference-budget counterexamples |
| [runs/001](runs/001/manifest.json) | Four DPLL/bounded-width variants on 80 fixed formulas: 320 results |
| [runs/002](runs/002/manifest.json) | The same 80 formulas with a Gaussian variant added: 400 results |

Every run has `cases.json` with the complete formulas, `results.csv` with witnesses
and deterministic counters, and `manifest.json` with configuration, Python version,
source fingerprints, artifact hashes, and per-family summaries. Run 002 uses
`method=gaussian, width=-1` for the Gaussian variant; -1 is a data marker, not a
supported bound in `solve_hybrid`.

## Replay and extend

From the repo root, with Python 3.11 (the recorded generator environment):

```bash
python3 -B -m unittest discover -s p-vs-np/tests -v
python3 -B p-vs-np/mixed.py --check p-vs-np/research/runs/001
python3 -B p-vs-np/mixed.py --check p-vs-np/research/runs/002
python3 -B p-vs-np/counterexamples.py
```

The test suite checks both frozen runs, the original 76-result baseline,
independent truth-table answers for all 80 benchmark formulas, mixed-formula
correctness, and inference soundness. GitHub Actions runs it on Python 3.11.
No third-party packages are needed. Solver code supports Python 3.10+; the frozen
generator comparisons are pinned to 3.11 rather than promising cross-version
stability of every `random` helper.

For a **new** experiment, choose a new directory:

```bash
python3 -B p-vs-np/mixed.py --gaussian --output-dir p-vs-np/research/runs/003
```

The writer refuses to overwrite a directory. `--check` reads the recorded inputs
and solver settings, validates artifact hashes and summaries, and compares every
deterministic result. It also reports source-fingerprint differences separately:
code can change while producing identical results. Run 001 predates Gaussian
support, so its source fingerprints differ from the later implementation while
its outputs still reproduce exactly. Git history records the code that replays
these runs; fingerprints identify the working source at capture time.

After an intentional change in solver behavior, retain the old inputs, results,
and explanation. Add a new run and describe which counts changed and why. Update
only the specifically affected replay expectation to assert the new relationship
on the old inputs; never erase a failing snapshot just to turn the tests green.
Correctness, original plain-DPLL behavior, and counterexample claims remain
separate regression requirements. A harmless counter change is not automatically
a correctness bug, but it must be accounted for before citing historical counts.

For each finding, record the question, method, exact commands/run IDs, controls,
observations, supported conclusion, limitations, and next falsifiable question.
Keep disproved claims and their smallest available fixtures. The minimizer checks
single-constraint deletion to a fixed point; this is not global minimization over
all encodings, variable orders, or possible formulas.

## Measurement contract

All variants receive the same ordinary CNF plus the same width-at-most-three
XOR equations, encoded into CNF in the same order. The hybrid methods also receive
the original equation structure. They neither infer it from arbitrary CNF nor
receive an oracle answer. CNF propagation, branching order, and node accounting
share one search loop. Width zero disables extra inference and reproduces plain
DPLL answers, witnesses, and counters exactly.

Bounded closure retains only equations of support at most k, adding pairwise XOR
sums to a fixed point or a conflict. Wider source rows stay in the CNF but are
ignored by the module until assignment restriction makes them eligible. Gaussian
inference instead retains at most n independent rows and reduces pivot columns
to detect all forced literals and inconsistency in the supplied linear subsystem,
provided its inference pass completes.

The node budget returns UNKNOWN when exhausted. The inference budget counts
pair attempts (bounded) or row additions (Gaussian), cumulatively for each solve.
Exhausting inference leaves sound deductions and falls back to CNF search; it
does not assert SAT, UNSAT, or UNKNOWN by itself. Defaults are 100,000 search
nodes and 20,000 inference operations in these experiments. These are not time
or memory limits; input processing, scans, and pivot tests still take work.

`xor_source_rows/literals` record normalized source size. `xor_row_checks` counts
source rows inspected after assignment restriction; `xor_derived` counts new
retained pairwise sums; `xor_peak_rows` is peak storage per inference pass;
`xor_forced` counts values passed to CNF propagation. Calls and cutoffs are also
recorded. Pair/row-addition counts and their summed maximum operand bit lengths
track distinct kinds of algebraic work. They exclude pivot comparisons, hashing,
allocations, encoding, and copying and are **not** interchangeable with runtime
or CNF literal inspections. No speedup claim is made from these counts.
