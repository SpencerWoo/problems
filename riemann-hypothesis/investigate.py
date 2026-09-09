"""Riemann Hypothesis — toy numerical investigation (stdlib only).

Checks the hypothesis' flavor: zeta(0.5 + i*t) gets *very* close to zero
at t ≈ 14.1347, 21.0220, ... while zeta elsewhere typically does not.

Method: zeta(s) = eta(s) / (1 - 2^(1-s)), with the Dirichlet eta function
accelerated by Euler's binomial transform for alternating series:
  eta(s) = sum_{k>=0} 1/2^(k+1) * sum_{j=0..k} C(k,j) (-1)^j / (j+1)^s
K ~ 40 terms gives ~1e-12 accuracy for Re(s) > 0. No mpmath needed.

Run: python3 investigate.py
"""

import cmath
import math

K = 40  # Euler-acceleration terms


def eta(s):
    total = 0j
    for k in range(K):
        inner = 0j
        for j in range(k + 1):
            inner += ((-1) ** j) * math.comb(k, j) / ((j + 1) ** s)
        total += inner / (2 ** (k + 1))
    return total


def zeta(s):
    return eta(s) / (1 - 2 ** (1 - s))


def self_test():
    # zeta(2) = pi^2/6
    assert abs(zeta(2) - math.pi**2 / 6) < 1e-9, zeta(2)
    # zeta(4) = pi^4/90
    assert abs(zeta(4) - math.pi**4 / 90) < 1e-9, zeta(4)
    # trivial: zeta(s) has a pole at s=1 -> large magnitude nearby
    assert abs(zeta(1 + 1e-6)) > 1e5
    print("self-test OK")


def scan_critical_line(t_max=30.0, step=0.25):
    """Return list of (t, |zeta(0.5+it)|) samples."""
    out = []
    t = 0.0
    while t <= t_max:
        out.append((t, abs(zeta(complex(0.5, t)))))
        t += step
    return out


def find_local_minima(samples):
    mins = []
    for i in range(1, len(samples) - 1):
        if samples[i][1] < samples[i - 1][1] and samples[i][1] <= samples[i + 1][1]:
            mins.append(samples[i])
    return mins


def refine_zero(t_guess):
    """Golden-section minimisation of |zeta(0.5+it)| near t_guess."""
    gr = (math.sqrt(5) - 1) / 2
    a, b = t_guess - 0.5, t_guess + 0.5
    c, d = b - gr * (b - a), a + gr * (b - a)
    for _ in range(60):
        if abs(zeta(complex(0.5, c))) < abs(zeta(complex(0.5, d))):
            b = d
        else:
            a = c
        c, d = b - gr * (b - a), a + gr * (b - a)
    return (a + b) / 2


if __name__ == "__main__":
    self_test()
    print("\nScanning |zeta(1/2 + i t)| for t in [0, 30] ...")
    samples = scan_critical_line()
    for t, m in find_local_minima(samples):
        if m < 0.5:  # only deep dips = near-zeros
            t_star = refine_zero(t)
            print(
                f"  dip near t={t:5.2f} -> refined t={t_star:.4f}, "
                f"|zeta|={abs(zeta(complex(0.5, t_star))):.2e}"
            )
    print("\nKnown first zeros: t = 14.1347, 21.0220, 25.0109.")
    print("A counterexample would be a zero with Re(s) != 1/2;")
    print("this script only probes the critical line, it cannot prove RH.")
