"""Poincare Conjecture (proved by Perelman) — toy topological investigation.

The conjecture: every simply connected closed 3-manifold is homeomorphic
to the 3-sphere. We obviously can't test that computationally here; instead
this script demonstrates the 2-D analogue's key invariant, the Euler
characteristic chi = V - E + F:

  sphere-like surfaces  -> chi = 2
  torus-like surfaces   -> chi = 0

so chi already distinguishes "simply connected" (sphere) from "holey"
(torus) triangulations. Same spirit as the invariants in Perelman's proof.

Run: python3 investigate.py
Stdlib only.
"""


def chi_from_triangles(triangles):
    verts = set()
    edges = set()
    for a, b, c in triangles:
        verts.update((a, b, c))
        edges.update((tuple(sorted(e)) for e in ((a, b), (b, c), (a, c))))
    return len(verts) - len(edges) + len(triangles)


def tetrahedron():
    return [(0, 1, 2), (0, 1, 3), (0, 2, 3), (1, 2, 3)]


def octahedron():
    return [
        (0, 1, 2), (0, 2, 3), (0, 3, 4), (0, 4, 1),
        (5, 1, 2), (5, 2, 3), (5, 3, 4), (5, 4, 1),
    ]


def torus_grid(n=3, m=3):
    """Triangulated torus: n*m vertices on a periodic grid, 2 triangles/cell."""
    tris = []
    for i in range(n):
        for j in range(m):
            v00 = i * m + j
            v10 = ((i + 1) % n) * m + j
            v01 = i * m + (j + 1) % m
            v11 = ((i + 1) % n) * m + (j + 1) % m
            tris += [(v00, v10, v11), (v00, v11, v01)]
    return tris


def self_test():
    assert chi_from_triangles(tetrahedron()) == 2
    assert chi_from_triangles(octahedron()) == 2
    assert chi_from_triangles(torus_grid()) == 0
    print("self-test OK")


if __name__ == "__main__":
    self_test()
    print("\nEuler characteristic chi = V - E + F:")
    for name, tris in (
        ("tetrahedron (sphere)", tetrahedron()),
        ("octahedron  (sphere)", octahedron()),
        ("3x3 torus   (1 hole) ", torus_grid()),
    ):
        print(f"  {name}: chi = {chi_from_triangles(tris)}")
    print("\nSphere chi=2 vs torus chi=0: topology is detectable combinatorially.")
    print("Perelman's Ricci-flow proof is the 3-D analogue, vastly deeper.")
