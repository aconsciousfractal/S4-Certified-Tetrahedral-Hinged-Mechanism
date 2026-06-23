# S4 Lemma 01: Geometry And Closed Tiling

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-01-GEOMETRY-TILING-2026-06-21`
review gate: R6a first mathematical lemma draft

## Purpose

This document writes the first exact mathematical lemma for the S4 mechanical-extension package.

It handles only the static catalogued geometry:

```text
ambient tetrahedron
median-plane S4 pieces
equal volumes
closed tiling
contact graph
closed ambient containment
```

It does not prove hingeability, motion, dynamic connection, positive clearance, physical hinge thickness, or any global theorem.

## Source Anchors

- `../../06-computational/src/tetrahedron.py::regular_tetrahedron`
- `../../06-computational/src/dissections.py::dissect_n4`
- `results/historical_s4_median_planes/geometry_payload.json`
- `results/historical_s4_median_planes/hinge_candidate_report.json`
- `results/historical_s4_median_planes/theta_zero_closed_contact_certificate_report.json`
- `docs/S4_PROOF_OBLIGATIONS.md`
- `docs/S4_MATHEMATICAL_LEMMA_PLAN.md`

The proof below is coordinate/barycentric. The JSON reports are consistency anchors, not substitutes for the derivation.

## Statement

Let `T = conv(A,B,C,D)` be the unit-edge regular tetrahedron with

```text
A = (0, 0, 0)
B = (1, 0, 0)
C = (1/2, sqrt(3)/2, 0)
D = (1/2, sqrt(3)/6, sqrt(6)/3)
```

Define the opposite-edge midpoints

```text
M_AB = (A + B) / 2 = (1/2, 0, 0)
M_CD = (C + D) / 2 = (1/2, sqrt(3)/3, sqrt(6)/6)
```

and define four closed tetrahedra

```text
P0 = conv(A, M_AB, C, M_CD)
P1 = conv(A, M_AB, D, M_CD)
P2 = conv(B, M_AB, C, M_CD)
P3 = conv(B, M_AB, D, M_CD)
```

Then:

1. `A,B,C,D` form a unit-edge regular tetrahedron with volume `sqrt(2)/12`.
2. Each `Pi` is a tetrahedron of volume `sqrt(2)/48`.
3. The four `Pi` are congruent, with edge-length multiset

```text
{1/2, 1/2, sqrt(2)/2, sqrt(3)/2, sqrt(3)/2, 1}.
```

4. The closed union `P0 union P1 union P2 union P3` equals `T`.
5. The relative interiors of the four pieces are pairwise disjoint.
6. The pairwise contact graph is:

| Pair | Contact type | Shared set |
| --- | --- | --- |
| `P0-P1` | shared face | `conv(A, M_AB, M_CD)` |
| `P0-P2` | shared face | `conv(C, M_AB, M_CD)` |
| `P0-P3` | shared edge | `conv(M_AB, M_CD)` |
| `P1-P2` | shared edge | `conv(M_AB, M_CD)` |
| `P1-P3` | shared face | `conv(D, M_AB, M_CD)` |
| `P2-P3` | shared face | `conv(B, M_AB, M_CD)` |

This is the catalogued closed S4 median-plane tiling used by the mechanical-extension audit.

## Proof

### 1. Ambient Tetrahedron

The coordinate differences give

```text
|A-B| = 1
|A-C| = |B-C| = 1
|A-D| = |B-D| = |C-D| = 1.
```

Hence `T` is a unit-edge regular tetrahedron. Its volume is

```text
Vol(T) = |det(B-A, C-A, D-A)| / 6 = sqrt(2) / 12.
```

This matches the local constructor value recorded in `geometry_payload.json`.

### 2. Median Planes In Barycentric Coordinates

Write a point `x in T` in barycentric coordinates

```text
x = alpha A + beta B + gamma C + delta D,
alpha,beta,gamma,delta >= 0,
alpha + beta + gamma + delta = 1.
```

The plane through `C,D,M_AB` is the barycentric plane

```text
alpha = beta.
```

Indeed, `C` and `D` have `alpha = beta = 0`, while `M_AB` has
`alpha = beta = 1/2`.

The plane through `A,B,M_CD` is the barycentric plane

```text
gamma = delta.
```

Indeed, `A` and `B` have `gamma = delta = 0`, while `M_CD` has
`gamma = delta = 1/2`.

The two planes partition `T` into the four closed sign cells:

| Cell | Barycentric inequalities | Piece |
| --- | --- | --- |
| `alpha >= beta`, `gamma >= delta` | first side of both cuts | `P0` |
| `alpha >= beta`, `delta >= gamma` | first side of first cut, second side of second cut | `P1` |
| `beta >= alpha`, `gamma >= delta` | second side of first cut, first side of second cut | `P2` |
| `beta >= alpha`, `delta >= gamma` | second side of both cuts | `P3` |

For example, if `alpha >= beta` and `gamma >= delta`, then

```text
x
= (alpha - beta) A
 + 2 beta M_AB
 + (gamma - delta) C
 + 2 delta M_CD.
```

All four coefficients are nonnegative and sum to `1`; hence `x in P0`.
Conversely every vertex of `P0` satisfies `alpha >= beta` and
`gamma >= delta`, so convexity gives the reverse inclusion.

The same calculation gives:

```text
P1 = {alpha >= beta, delta >= gamma}:
x = (alpha - beta) A + 2 beta M_AB + (delta - gamma) D + 2 gamma M_CD.

P2 = {beta >= alpha, gamma >= delta}:
x = (beta - alpha) B + 2 alpha M_AB + (gamma - delta) C + 2 delta M_CD.

P3 = {beta >= alpha, delta >= gamma}:
x = (beta - alpha) B + 2 alpha M_AB + (delta - gamma) D + 2 gamma M_CD.
```

Therefore the four closed pieces cover `T`.

### 3. Interior Disjointness

The relative interior of each piece is obtained by making the two sign
inequalities strict, except on the piece's own tetrahedral boundary.

Two different sign cells require at least one opposite strict inequality, for
example `gamma > delta` versus `delta > gamma`, or `alpha > beta` versus
`beta > alpha`. Hence two different pieces cannot share a point in their
relative interiors.

Their intersections are therefore lower-dimensional boundary contacts only.

### 4. Volumes And Congruence

For `P0`,

```text
Vol(P0)
= |det(M_AB - A, C - A, M_CD - A)| / 6
= sqrt(2) / 48.
```

The other three pieces are obtained from `P0` by the ambient symmetries
interchanging `A` with `B` and/or `C` with `D`, so they have the same volume.
Thus

```text
Vol(P0) + Vol(P1) + Vol(P2) + Vol(P3)
= 4 * sqrt(2)/48
= sqrt(2)/12
= Vol(T).
```

The edge lengths of `P0` are:

```text
|A-M_AB|      = 1/2
|C-M_CD|      = 1/2
|M_AB-M_CD|   = sqrt(2)/2
|A-M_CD|      = sqrt(3)/2
|M_AB-C|      = sqrt(3)/2
|A-C|         = 1.
```

The same ambient symmetries give the same edge spectrum for all pieces:

```text
{1/2, 1/2, sqrt(2)/2, sqrt(3)/2, sqrt(3)/2, 1}.
```

This proves the pieces are congruent tetrahedra.

### 5. Contact Graph

The contact graph follows from equality cases of the two barycentric cuts.

For adjacent cells differing only by the `gamma >= delta` sign, the contact
lies in `gamma = delta`; for adjacent cells differing only by the
`alpha >= beta` sign, the contact lies in `alpha = beta`.

Thus:

- `P0 cap P1 = conv(A, M_AB, M_CD)`, a shared face.
- `P0 cap P2 = conv(C, M_AB, M_CD)`, a shared face.
- `P1 cap P3 = conv(D, M_AB, M_CD)`, a shared face.
- `P2 cap P3 = conv(B, M_AB, M_CD)`, a shared face.

The diagonally opposite sign cells differ in both inequalities. Their
intersection imposes

```text
alpha = beta
gamma = delta
```

which is exactly the segment `conv(M_AB, M_CD)`. Hence:

- `P0 cap P3 = conv(M_AB, M_CD)`, a shared edge.
- `P1 cap P2 = conv(M_AB, M_CD)`, a shared edge.

These six contacts match the ledger in `hinge_candidate_report.json` and the
closed endpoint certificate.

### 6. Closed Ambient Containment

All piece vertices are either ambient vertices of `T` or midpoints of ambient
edges. Since `T` is convex, each piece vertex lies in the closed ambient
tetrahedron, and each piece, being the convex hull of such vertices, lies in
`T`.

The barycentric partition above also gives the stronger statement:

```text
Pi subset T for i = 0,1,2,3,
P0 union P1 union P2 union P3 = T,
relative interiors are pairwise disjoint.
```

This is the closed tiling assertion needed by `S4-PO-001`.

## Exactness Status

This lemma uses only exact coordinates, midpoint definitions, convexity,
barycentric inequalities, and determinant volume calculations.

No floating SAT predicate, sampled motion report, tolerance, or numerical
formula check is used in the proof.

The finite reports remain useful as consistency anchors:

| Report | Matching fact |
| --- | --- |
| `geometry_payload.json` | `piece_count = 4`, equal volumes, congruent edge spectra |
| `hinge_candidate_report.json` | `4` shared-face contacts and `2` shared-edge-only contacts |
| `theta_zero_closed_contact_certificate_report.json` | closed containment and contact ledger at `theta = 0` |

## Claim Boundary

This lemma supports only the catalogued geometry and closed tiling of `S4`.

Do not infer from it:

```text
S4 hingeability
TREE_007/TREE_021 motion validity
dynamic connectedness
positive clearance at theta = 0
physical hinge thickness or CAD validity
global S4 theorem promotion
```

Those are handled, if at all, by later lemmas and certificates.

## R6a Result

This draft resolves the first writing target from `docs/S4_MATHEMATICAL_LEMMA_PLAN.md`:

```text
L1 Catalogued S4 geometry and tiling
S4-PO-001 geometry/tiling
```

It does not resolve `S4-PO-002`, because the closed-contact endpoint needs its
own semantics for zero-margin contact and strict interior non-overlap.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
