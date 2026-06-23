# S4 Lemma 00: Definitions And Notation Lock

Status: lemma draft / notation lock.  Not a theorem promotion.

Date: 2026-06-21.

Case: `historical_s4_median_planes`.

Lemma ID: `S4-LEMMA-00-DEFINITIONS-NOTATION-LOCK-2026-06-21`.

## Purpose

This note fixes the canonical notation used by the S4 mathematical lemma
package.  It is deliberately placed as Lemma 00 because it is not a geometric
or collision-freedom proof.  It is a definitions layer imported by
`S4_LEMMA_01` through `S4_LEMMA_10` and by the next scoped theorem wrapper.

The goal is to prevent drift among:

- ambient tetrahedron coordinates;
- midpoint and median-plane labels;
- piece, pair, contact, hinge, and tree IDs;
- signed angle variables and degree/radian conventions;
- endpoint, near-zero, ray-cell, refined-edge, and bounded-cell domains;
- finite ledger key schemas.

If older exploratory summaries use different local wording, this notation lock
governs the current S4 lemma package.

## Source Anchors

This lock consolidates definitions already used in:

- `docs/S4_FINAL_STATEMENT_FREEZE.md`;
- `docs/S4_LEMMA_01_GEOMETRY_AND_TILING.md`;
- `docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`;
- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`;
- `docs/S4_LEMMA_04_SIGNED_RAY_CLASSES.md`;
- `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`;
- `docs/S4_LEMMA_06_NEAR_ZERO_BRIDGE_FORMULAS.md`;
- `docs/S4_LEMMA_07_REFINED_EDGE_RESIDUAL_CLOSURE.md`;
- `docs/S4_LEMMA_08_BOUNDED_CELL_FIRST_PASS_AND_FALLBACK_GUARDS.md`;
- `docs/S4_LEMMA_09_ADAPTIVE_SUBDIVISION_AND_OVERLAY_INVARIANT.md`;
- `docs/S4_LEMMA_10_ARITHMETIC_AND_EXACTNESS_BOUNDARY.md`;
- `docs/S4_PROOF_OBLIGATIONS.md`;
- `registry/claim_register.yaml`.

## Ambient Tetrahedron

The ambient tetrahedron is the regular tetrahedron:

```text
T = conv(A, B, C, D)

A = (0, 0, 0)
B = (1, 0, 0)
C = (1/2, sqrt(3)/2, 0)
D = (1/2, sqrt(3)/6, sqrt(6)/3)
```

The two midpoint labels used throughout the S4 package are:

```text
M_AB = (A + B)/2 = (1/2, 0, 0)
M_CD = (C + D)/2 = (1/2, sqrt(3)/3, sqrt(6)/6)
```

The barycentric coordinates relative to `(A, B, C, D)` are written:

```text
(alpha, beta, gamma, delta)
```

with `alpha + beta + gamma + delta = 1`.  The two median planes are:

```text
alpha = beta
gamma = delta
```

The ambient tetrahedron alone is denoted `T`.  To avoid collision with this
letter, the theorem wrapper should denote moving-piece rigid transforms by
`F_i`, not by `T_i`.

## Piece Labels

The four closed median-plane pieces are:

```text
P0 = conv(A, M_AB, C, M_CD)
P1 = conv(A, M_AB, D, M_CD)
P2 = conv(B, M_AB, C, M_CD)
P3 = conv(B, M_AB, D, M_CD)
```

Equivalently, in barycentric half-space form:

```text
P0: alpha >= beta, gamma >= delta
P1: alpha >= beta, delta >= gamma
P2: beta  >= alpha, gamma >= delta
P3: beta  >= alpha, delta >= gamma
```

The piece labels `P0`, `P1`, `P2`, `P3` are fixed.  They are not to be
renumbered inside theorem statements, ledgers, or proof-obligation references.

## Pair Labels

Unordered piece-pair labels are always written in increasing piece-index order:

```text
P0-P1
P0-P2
P0-P3
P1-P2
P1-P3
P2-P3
```

The mathematical pair universe is:

```text
Pairs = {P0-P1, P0-P2, P0-P3, P1-P2, P1-P3, P2-P3}.
```

When a source script stores an ordered or tuple representation, the lemma
package reads it through this canonical unordered label.

## Contact IDs

At the closed endpoint, the six catalogued contacts are:

| Contact ID | Pair | Closed intersection |
| --- | --- | --- |
| `C0` | `P0-P1` | `conv(A, M_AB, M_CD)` |
| `C1` | `P0-P2` | `conv(C, M_AB, M_CD)` |
| `C2` | `P0-P3` | `conv(M_AB, M_CD)` |
| `C3` | `P1-P2` | `conv(M_AB, M_CD)` |
| `C4` | `P1-P3` | `conv(D, M_AB, M_CD)` |
| `C5` | `P2-P3` | `conv(B, M_AB, M_CD)` |

The symbols `C0` through `C5` are contact IDs only.  They should not be reused
for signed-ray class names.

## Closed-Contact Semantics

All pieces are closed tetrahedra.  At `theta_deg = 0`, the model permits the
catalogued contacts above:

1. face contacts;
2. edge contacts;
3. vertex contacts, if present in a later subproblem;
4. zero clearance at catalogued contacts.

The forbidden event is strict interior overlap: two pieces sharing an ordinary
three-dimensional interior point.  Zero clearance at a catalogued shared face
or shared edge is not a collision in the closed-contact endpoint statement.

The closed endpoint is denoted:

```text
E0: theta_deg = 0.
```

The endpoint certificate does not assert positive clearance.

## Hinge Axis IDs

The current representative S4 mechanism package uses four selected ambient-edge
hinge axes:

| Hinge ID | Pair | Contact | Oriented axis | Ambient support |
| --- | --- | --- | --- | --- |
| `H0_A_M_AB` | `P0-P1` | `C0` | `A -> M_AB` | `AB` |
| `H4_C_M_CD` | `P0-P2` | `C1` | `C -> M_CD` | `CD` |
| `H7_D_M_CD` | `P1-P3` | `C4` | `D -> M_CD` | `CD` |
| `H9_B_M_AB` | `P2-P3` | `C5` | `B -> M_AB` | `AB` |

Each listed axis has length `1/2`.  The orientation in the table is part of the
sign convention.  The IDs are fixed labels for this package; this note does not
claim that `H0`, `H4`, `H7`, and `H9` are a complete global hinge numbering
scheme outside the audited S4 representatives.

## Representative Tree IDs

The two representative signed-ray trees used by the current package are:

```text
TREE_007
TREE_021
```

The root piece for both representatives is `P0`.

For `TREE_007`, the selected hinge graph and rooted paths are:

```text
Hinges: H0_A_M_AB, H4_C_M_CD, H7_D_M_CD
Edges:  P0-P1, P0-P2, P1-P3
Root:   P0

Path(P0) = identity
Path(P1) = P0 --H0_A_M_AB--> P1
Path(P2) = P0 --H4_C_M_CD--> P2
Path(P3) = P0 --H0_A_M_AB--> P1 --H7_D_M_CD--> P3
```

For `TREE_021`, the selected hinge graph and rooted paths are:

```text
Hinges: H0_A_M_AB, H7_D_M_CD, H9_B_M_AB
Edges:  P0-P1, P1-P3, P2-P3
Root:   P0

Path(P0) = identity
Path(P1) = P0 --H0_A_M_AB--> P1
Path(P3) = P0 --H0_A_M_AB--> P1 --H7_D_M_CD--> P3
Path(P2) = P0 --H0_A_M_AB--> P1 --H7_D_M_CD--> P3 --H9_B_M_AB--> P2
```

The broader all-ambient-edge candidate set used in the signed-ray class
reduction is:

```text
{TREE_007, TREE_009, TREE_021, TREE_093}.
```

Its root-preserving signed-ray classes are:

```text
Class_A = {TREE_007, TREE_009}
Class_B = {TREE_021, TREE_093}
```

The class names `Class_A` and `Class_B` should be used in theorem prose to
avoid confusion with the contact IDs `C0` through `C5`.

## Signed Angle Variables

The scalar ray parameter in reports and domain statements is:

```text
theta_deg
```

It is measured in degrees and is nonnegative on the audited rays.  The
corresponding radian parameter is:

```text
theta_rad = pi * theta_deg / 180.
```

If a formula lemma writes only `theta`, it must explicitly state whether
`theta` means degrees or radians.  The theorem wrapper should use `theta_deg`
and `theta_rad` instead of the bare symbol whenever both conventions appear in
the same paragraph.

For a hinge `h`, the signed hinge angle in degrees is:

```text
d_h(theta_deg) = sign_h * theta_deg.
```

The signed angle passed to the axis-rotation map is:

```text
phi_h = pi * d_h(theta_deg) / 180.
```

For the representative rays, the signed degree conventions are:

| Tree | Hinge order | Sign vector |
| --- | --- | --- |
| `TREE_007` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `(+1, +1, -1)` |
| `TREE_021` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `(+1, -1, +1)` |

Thus:

```text
TREE_007: d_H0(theta_deg) =  theta_deg
          d_H4(theta_deg) =  theta_deg
          d_H7(theta_deg) = -theta_deg

TREE_021: d_H0(theta_deg) =  theta_deg
          d_H7(theta_deg) = -theta_deg
          d_H9(theta_deg) =  theta_deg
```

## Axis Rotation Convention

For an oriented axis from point `a` to point `b`, let:

```text
u = (b - a) / |b - a|.
```

The right-handed rotation by radian angle `phi` is:

```text
Rot(a, b, phi)(x) = Q_u(phi) x + a - Q_u(phi) a,
```

where `Q_u(phi)` is the usual three-dimensional rotation matrix about the
oriented unit vector `u`.

The moving transform for piece `Pi` in a tree should be denoted:

```text
F_i(tree_id, theta_deg)
```

on the one-dimensional representative rays, and by a correspondingly explicit
multi-parameter notation in bounded-cell statements.  The root transform is
the identity:

```text
F_0 = Id.
```

## Domain Conventions

The S4 package currently separates five domains:

| Domain name | Parameter range | Role |
| --- | --- | --- |
| Closed endpoint | `theta_deg = 0` | closed-contact endpoint `E0` |
| Near-zero bridge | `0 < theta_deg <= 0.5` | formula bridge to the open ray |
| Representative ray finite cover | `0.5 <= theta_deg <= 120` | 478 ray cells per representative |
| Open representative ray | `0 < theta_deg <= 120` | union of near-zero bridge and finite ray cover |
| Bounded all-free cells | finite 3-parameter cells | all-free bounded-cell overlay for the two representatives |

The finite ray-cell ledger does not cover `theta_deg = 0`.  The closed endpoint
does not claim positive clearance.  The bounded-cell ledger excludes the
endpoint and excludes cells with blocked sampled vertices, exactly as recorded
in `S4_LEMMA_08`.

## Ray-Cell Ledger Keys

The finite representative-ray ledger uses:

```text
I_k = [0.5 + 0.25 k, 0.75 + 0.25 k] degrees
k = 0, ..., 477.
```

There are:

```text
478 ray cells per representative
6 unordered piece pairs per ray cell
2868 pair-cells per representative
```

A normalized ray pair-cell key is:

```text
(tree_id, ray_cell_id, pair)
```

where:

```text
tree_id in {TREE_007, TREE_021}
pair in Pairs
```

and `ray_cell_id` is the stable report identifier for the interval `I_k`.

## Refined-Edge Ledger Keys

The refined spanning-edge ledger uses parent segment keys:

```text
(tree_id, segment_id)
```

and pair-segment keys:

```text
(tree_id, segment_id, pair)
```

Report examples have segment IDs such as:

```text
seg_00000
```

For each representative:

```text
2528 refined segment keys
15168 pair-segment keys = 2528 * 6
```

The refined-edge ledger is a finite parent-key universe.  It is not the full
continuous three-parameter configuration space.

## Bounded-Cell Ledger Keys

The bounded-cell overlay uses normalized pair-cell keys:

```text
(tree_id, cell_id, pair)
```

Concrete serialized report keys may appear as:

```text
TREE_007|P0-P1|theta00_radial00_dir00
```

For this example:

```text
tree_id = TREE_007
pair    = P0-P1
cell_id = theta00_radial00_dir00
```

The bounded all-free parent universe across the two representative trees is:

```text
1536 all-free bounded cells
9216 pair-cells = 1536 * 6
```

The `96 + 96` blocked sampled-vertex cells are not part of this parent
universe.

## Terminal Child Keys

Adaptive fallback reports refine failed parent keys into terminal children or
terminal leaves.  The normalized terminal witness schemas are:

```text
(parent_key, route_id, local_leaf_id)
```

or:

```text
(parent_key, route_id, subcell_id)
```

Terminal child keys do not enlarge the final theorem domain.  They are witness
keys below an already existing parent key.  Once every terminal child covering
the audited part of a parent is certified, the conclusion folds back to the
parent key.

## Coverage Vocabulary

For a finite parent-key universe `U`, use:

```text
covered(K)
uncovered(K)
```

for parent keys `K in U`.

The statement:

```text
covered(K)
```

means that the current ledger assigns `K` to at least one accepted certificate
route.  The geometric implication of a certificate route depends on the guard
soundness and exactness level recorded in Lemma 10.

The word `uncovered` means "not certified by the current finite ledger."  It is
not a collision claim.

## Evidence Levels

The S4 package uses the following informal evidence levels in prose:

```text
LEMMA_DRAFT
FINITE_REPLAY_REPORT
PROOF_OBLIGATION_LEDGER
LEMMA_PLAN
```

For guarded claim levels, the current package distinguishes:

- exact coordinate and combinatorial facts;
- symbolic or formula-derived facts;
- finite ledger facts;
- interval-support obligations;
- floating or tolerance-dependent predicates.

The exactness boundary is fixed by `S4_LEMMA_10`.  This notation lock does not
upgrade any finite replay or formula check to CL5.

## Canonical Theorem-Wrapper Wording

The scoped theorem wrapper should use the following supported vocabulary:

```text
catalogued median-plane S4
zero-thickness rigid-piece model
closed-contact endpoint
representative signed-ray trees TREE_007 and TREE_021
open representative-ray domain 0 < theta_deg <= 120
finite ray-cell ledger on 0.5 <= theta_deg <= 120
near-zero bridge on 0 < theta_deg <= 0.5
bounded all-free cell domain
finite parent-key ledger
guard-soundness and exactness blockers
```

The theorem wrapper should avoid:

```text
S4 is globally hingeable
S4 is physically hingeable
positive clearance at theta_deg = 0
TREE_007 and TREE_021 are dynamically connected
finite replay is already a theorem
Demaine's theorem proves this fixed-piece mechanism
```

## Lemma 00 Claim

For the catalogued median-plane S4 package, the notation in this file fixes the
canonical labels and domains used by the mathematical lemma stack:

1. ambient tetrahedron coordinates and midpoint labels;
2. piece labels `P0` through `P3`;
3. unordered pair labels and closed contact IDs `C0` through `C5`;
4. selected hinge IDs `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD`, `H9_B_M_AB`;
5. representative tree IDs `TREE_007` and `TREE_021`;
6. signed degree/radian angle conventions;
7. endpoint, near-zero, ray-cell, refined-edge, and bounded-cell domains;
8. ray pair-cell, refined-edge, bounded-cell, and terminal child key schemas.

This is a notation and scope lock.  It is imported by later claims, but by
itself it does not prove collision freedom, dynamic connectedness, physical
hingeability, exact guard soundness, or theorem promotion.

## Proof Status

The content above is definitional and reconciles already-used labels.  The
coordinate and contact facts are proved in Lemmas 01 and 02.  The kinematic
tree and sign conventions are recorded in Lemmas 03 and 04.  The finite ledger
domains are recorded in Lemmas 05, 07, 08, and 09.  The exactness boundary is
recorded in Lemma 10.

Therefore this lemma should be read as a dependency-normalization layer rather
than as an independent geometric proof.

## Nonclaims

This note does not claim:

- positive clearance at `theta_deg = 0`;
- continuous collision-freedom outside the audited domains;
- dynamic connectedness between representative classes;
- physical hinge thickness or printability;
- global S4 hingeability;
- CL5 exact arithmetic soundness for all numerical guards;
- theorem promotion of the finite replay package.

## R6k Result

The definitions and notation lock is now in place for the S4 lemma package.
The next draft can write a scoped zero-thickness theorem wrapper without
renaming pieces, hinges, trees, domains, or finite-ledger key universes.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
