"""Yang-Mills mass gap — toy Z2 lattice-gauge investigation (stdlib only).

The Clay problem: pure SU(N) Yang-Mills on R^4 exists as a QFT and has a
mass gap Delta > 0. We demo the *phenomenon* in miniature: 2-D Z2 lattice
gauge theory, where confinement shows up as an area law for Wilson loops,

    <W(R,T)> ~ exp(-sigma * R*T),

and a non-zero string tension sigma is the toy analogue of a mass gap.
A short Metropolis Monte Carlo at strong coupling (small beta) exhibits it.

Run: python3 investigate.py  (a few seconds; seed fixed for determinism)
"""

import math
import random

L = 6          # lattice size (periodic)
BETA = 0.6     # strong coupling -> confined / gapped phase
SWEEPS = 1500
MEASURE_EVERY = 5


def site(x, y):
    return x % L, y % L


class Z2Gauge:
    def __init__(self, rng):
        # xlink[(x,y)] lives on edge (x,y)->(x+1,y); ylink on (x,y)->(x,y+1)
        self.xlink = {(x, y): rng.choice((-1, 1)) for x in range(L) for y in range(L)}
        self.ylink = {(x, y): rng.choice((-1, 1)) for x in range(L) for y in range(L)}

    def plaquette(self, x, y):
        x0, y0 = site(x, y)
        x1, y1 = site(x + 1, y)
        return (
            self.xlink[(x0, y0)] * self.ylink[(x1, y0)]
            * self.xlink[(x0, (y0 + 1) % L)] * self.ylink[(x0, y0)]
        )

    def staples(self, x, y, direction):
        """Sum of the 3-link staples coupling to link (x,y,dir); Z2 => each is +/-1."""
        x0, y0 = site(x, y)
        if direction == "x":
            s = 0
            # plaquette above (x,y) and below (x,y-1)
            s += self.ylink[site(x + 1, y)[0], y0] * self.xlink[(x0, (y0 + 1) % L)] * self.ylink[x0, y0]
            ym = (y0 - 1) % L
            s += self.ylink[site(x + 1, ym)[0], ym] * self.xlink[(x0, ym)] * self.ylink[x0, ym]
            return s
        s = 0
        s += self.xlink[(x0, site(x, y + 1)[1])] * self.ylink[((x0 + 1) % L, y0)] * self.xlink[(x0, y0)]
        xm = (x0 - 1) % L
        s += self.xlink[(xm, site(x, y + 1)[1])] * self.ylink[(xm, y0)] * self.xlink[(xm, y0)]
        return s

    def sweep(self, rng):
        for x in range(L):
            for y in range(L):
                for links, direction in ((self.xlink, "x"), (self.ylink, "y")):
                    old = links[(x, y)]
                    # Z2 heatbath: P(+1) propto exp(beta*staple)
                    st = self.staples(x, y, direction)
                    p_plus = 1.0 / (1.0 + math.exp(-2 * BETA * st))
                    links[(x, y)] = 1 if rng.random() < p_plus else -1

    def avg_plaquette(self):
        return sum(self.plaquette(x, y) for x in range(L) for y in range(L)) / (L * L)

    def wilson(self, R, T):
        """Average R x T rectangular Wilson loop over all positions."""
        total, n = 0, 0
        for x in range(L):
            for y in range(L):
                w = 1
                for i in range(R):
                    w *= self.xlink[((x + i) % L, y)]
                for j in range(T):
                    w *= self.ylink[((x + R) % L, (y + j) % L)]
                for i in range(R):
                    w *= self.xlink[((x + i) % L, (y + T) % L)]
                for j in range(T):
                    w *= self.ylink[(x, (y + j) % L)]
                total += w
                n += 1
        return total / n


def self_test():
    rng = random.Random(0)
    g = Z2Gauge(rng)
    # plaquettes are always +/-1, Wilson loops too
    assert g.plaquette(0, 0) in (-1, 1)
    assert -1.0 <= g.avg_plaquette() <= 1.0
    print("self-test OK")


def main():
    rng = random.Random(0)
    g = Z2Gauge(rng)
    for _ in range(SWEEPS // 2):  # thermalize
        g.sweep(rng)
    plaq, wilsons = [], {size: [] for size in ((1, 1), (1, 2), (2, 2))}
    for i in range(SWEEPS):
        g.sweep(rng)
        if i % MEASURE_EVERY == 0:
            plaq.append(g.avg_plaquette())
            for size in wilsons:
                wilsons[size].append(g.wilson(*size))
    mean_p = sum(plaq) / len(plaq)
    print(f"<plaquette> = {mean_p:.3f}  (1.0 = fully ordered, 0 = disordered)")
    print("Wilson loops <W(R,T)>:")
    for (R, T), vals in wilsons.items():
        m = sum(vals) / len(vals)
        print(f"  W({R}x{T}) area={R*T}: {m:.3f}")
    w11 = sum(wilsons[(1, 1)]) / len(wilsons[(1, 1)])
    w22 = sum(wilsons[(2, 2)]) / len(wilsons[(2, 2)])
    if w11 > 0 and w22 > 0:
        sigma = -(math.log(w22) - math.log(w11)) / (4 - 1)
        print(f"string tension proxy sigma ~= {sigma:.3f} (> 0 signals area law / gap-like behavior)")
    print("\nToy Z2 result only — SU(3) in 4-D with a rigorous gap is the real problem.")


if __name__ == "__main__":
    self_test()
    print()
    main()
