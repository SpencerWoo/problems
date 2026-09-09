"""P vs NP — toy investigation: verification is easy, search is hard.

Does NOT prove P != NP or P == NP. It demonstrates the core asymmetry:
- verifying a 3-SAT assignment is O(#clauses)  (in P)
- finding one by brute force is O(2^n)         (exponential)

Run: python3 investigate.py
Stdlib only.
"""

import itertools
import random
import time


def verify(clauses, assignment):
    """Check a 3-SAT assignment. `assignment[i]` is truth of x_{i+1}."""
    for clause in clauses:
        if not any(assignment[abs(lit) - 1] == (lit > 0) for lit in clause):
            return False
    return True


def brute_force(clauses, n_vars):
    """Exhaustive search over all 2^n assignments. Returns first satisfying one or None."""
    for bits in itertools.product((False, True), repeat=n_vars):
        if verify(clauses, bits):
            return bits
    return None


def random_3sat(n_vars, n_clauses, seed=0):
    rng = random.Random(seed)
    clauses = []
    for _ in range(n_clauses):
        vs = rng.sample(range(1, n_vars + 1), 3)
        clauses.append([v if rng.random() < 0.5 else -v for v in vs])
    return clauses


def demo_scaling():
    print("n_vars | clauses | brute_force_time | verify_time (single assignment)")
    print("---------------------------------------------------------------------")
    for n in (10, 14, 18, 22):
        clauses = random_3sat(n, 4 * n, seed=n)
        guess = tuple(random.Random(99).random() < 0.5 for _ in range(n))

        t0 = time.perf_counter()
        verify(clauses, guess)
        t_verify = time.perf_counter() - t0

        t0 = time.perf_counter()
        brute_force(clauses, n)
        t_search = time.perf_counter() - t0
        print(f"{n:6d} | {4*n:7d} | {t_search:14.4f}s | {t_verify*1e6:10.1f} us")


def self_test():
    # (x1 | x2 | ~x3) & (~x1 | x2 | x3) is satisfied by x1=x2=x3=True
    clauses = [[1, 2, -3], [-1, 2, 3]]
    assert verify(clauses, (True, True, True))
    assert not verify(clauses, (False, False, True))
    sol = brute_force(clauses, 3)
    assert sol is not None and verify(clauses, sol)
    # unsatisfiable: x1 & ~x1
    assert brute_force([[1], [-1]], 1) is None
    print("self-test OK")


if __name__ == "__main__":
    self_test()
    print()
    print("P vs NP toy: SAT verification (P) vs brute-force search (exponential).")
    print("If P == NP, every such search would have a polynomial shortcut.")
    print("No such shortcut is known; timing below shows the blowup.\n")
    demo_scaling()
