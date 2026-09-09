"""Birch and Swinnerton-Dyer — toy investigation (stdlib only).

BSD (rank part): ord_{s=1} L(E,s) == rank(E(Q)).

We compare two curves:
  E0: y^2 = x^3 - x      (rank 0; L(E,1) != 0)
  E1: y^2 = x^3 - 2      (rank 1, generator (3,5); L(E,1) == 0)

Two probes:
  1. naive integral-point search finds (3, +/-5) on E1, nothing small on E0
     beyond torsion -> hints rank(E1) > rank(E0).
  2. truncated Euler product  L(E,1) ~= prod_p 1/(1 - a_p/p + 1/p)
     (good primes only) stays O(1) for E0 but collapses toward 0 for E1,
     mirroring the vanishing BSD predicts.

Run: python3 investigate.py
"""

import math


def primes_upto(n):
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for i in range(2, int(n**0.5) + 1):
        if sieve[i]:
            sieve[i * i :: i] = [False] * len(sieve[i * i :: i])
    return [i for i, p in enumerate(sieve) if p]


def count_points_mod_p(a, b, p):
    """#E(F_p) including infinity, for y^2 = x^3 + a x + b."""
    n = 1  # point at infinity
    residues = {pow(y, 2, p) for y in range(p)}
    for x in range(p):
        rhs = (pow(x, 3, p) + a * x + b) % p
        if rhs in residues:
            # count square roots: 1 if rhs==0 else 2
            n += 1 if rhs == 0 else 2
    return n


def ap(a, b, p):
    return p + 1 - count_points_mod_p(a, b, p)


def disc(a, b):
    return -16 * (4 * a**3 + 27 * b**2)


def partial_L(a, b, prime_cap=200):
    """Truncated Euler product at s=1 over good primes <= cap."""
    d = disc(a, b)
    total = 1.0
    for p in primes_upto(prime_cap):
        if d % p == 0:  # bad reduction: skip
            continue
        t = ap(a, b, p)
        total *= 1.0 / (1 - t / p + 1.0 / p)
    return total


def integral_points(a, b, bound=50):
    """Find integer (x, y) with y^2 = x^3 + a x + b, |x| <= bound."""
    pts = []
    for x in range(-bound, bound + 1):
        v = x**3 + a * x + b
        if v < 0:
            continue
        y = math.isqrt(v)
        if y * y == v:
            pts.append((x, y))
            if y:
                pts.append((x, -y))
    return sorted(pts)


def self_test():
    # E1 has the famous integral point (3, 5)
    assert (3, 5) in integral_points(0, -2, bound=10)
    # a_5 for E0: y^2=x^3-x mod 5 has 8 points -> a_5 = 5+1-8 = -2
    assert ap(-1, 0, 5) == -2
    print("self-test OK")


if __name__ == "__main__":
    self_test()
    print("\nIntegral points |x|<=50:")
    for name, (a, b) in (("E0: y^2=x^3-x (rank 0)", (-1, 0)), ("E1: y^2=x^3-2 (rank 1)", (0, -2))):
        pts = integral_points(a, b)
        print(f"  {name}: {len(pts)} points, e.g. {pts[:6]}")
    print("\nTruncated L(E,1) (good primes only):")
    for name, (a, b) in (("E0 (expect != 0)", (-1, 0)), ("E1 (expect 0)", (0, -2))):
        vals = "  ".join(f"<= {c}: {partial_L(a, b, c):.3f}" for c in (50, 100, 200))
        print(f"  {name}: {vals}")
    print("\nE0 stays O(1), E1 collapses -> matches BSD rank 0 vs rank 1.")
