"""Navier-Stokes regularity — toy 1-D Burgers investigation (stdlib only).

The Clay problem: do smooth solutions of 3-D Navier-Stokes stay smooth for
all time, or can they blow up? We demo the mechanism in 1-D with Burgers':

    u_t + u u_x = nu u_xx,   periodic, u(x,0) = sin(2 pi x).

  - nu > 0 (viscous): diffusion wins, max|u_x| stays bounded, energy decays.
  - nu = 0 (inviscid): the wave steepens and max|u_x| explodes (shock).

Same competition — nonlinearity steepening vs diffusion smoothing — sits at
the heart of the real regularity question.

Run: python3 investigate.py
"""

import math

N = 64      # grid points
STEPS = 400
DT = 0.0008


def run(nu):
    dx = 1.0 / N
    u = [math.sin(2 * math.pi * i / N) for i in range(N)]
    max_grad, energies = 0.0, []
    for _ in range(STEPS):
        energy = sum(v * v for v in u) / N
        energies.append(energy)
        grad = max(abs(u[(i + 1) % N] - u[i]) / dx for i in range(N))
        max_grad = max(max_grad, grad)
        nxt = [0.0] * N
        for i in range(N):
            um, u0, up = u[(i - 1) % N], u[i], u[(i + 1) % N]
            adv = u0 * (up - um) / (2 * dx)          # u u_x (centered)
            diff = (up - 2 * u0 + um) / (dx * dx)    # u_xx
            nxt[i] = u0 + DT * (-adv + nu * diff)
        u = nxt
    return max_grad, energies[0], energies[-1]


def self_test():
    g, e0, e1 = run(nu=0.05)
    assert math.isfinite(g) and e1 < e0  # viscosity dissipates energy
    print("self-test OK")


if __name__ == "__main__":
    self_test()
    print("\n1-D Burgers, sin initial data:")
    for nu in (0.05, 0.0):
        g, e0, e1 = run(nu=nu)
        print(f"  nu={nu:4.2f}: max|u_x|={g:9.1f}  energy {e0:.3f} -> {e1:.3f}")
    print("\nViscous stays smooth and decays; inviscid gradient explodes (shock).")
    print("Whether 3-D Navier-Stokes can similarly blow up is the open problem.")
