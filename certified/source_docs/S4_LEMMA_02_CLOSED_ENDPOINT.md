# S4 Lemma 02: Closed-Contact Endpoint At Theta Zero

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-02-CLOSED-ENDPOINT-2026-06-21`
review gate: R6b second mathematical lemma draft

## Purpose

This document writes the closed endpoint lemma for the S4 mechanical-extension
package.

It handles only the configuration

```text
theta = 0
catalogued closed S4 assembly
zero-thickness rigid pieces
closed-set non-interpenetration
```

It does not prove one-sided motion, positive clearance, physical hinge
realizability, dynamic class-connection, or global S4 hingeability.

## Source Anchors

- `docs/S4_LEMMA_01_GEOMETRY_AND_TILING.md`
- `results/historical_s4_median_planes/theta_zero_closed_contact_certificate_report.json`
- `docs/S4_THETA_ZERO_CLOSED_CONTACT_CERTIFICATE_SUMMARY.md`
- `results/historical_s4_median_planes/hinge_candidate_report.json`
- `docs/S4_PROOF_OBLIGATIONS.md`
- `docs/S4_MATHEMATICAL_LEMMA_PLAN.md`

The proof below uses Lemma 01 for the exact closed tiling. The JSON report is
used as a consistency anchor for the computational certificate semantics and
the representative zero-angle transform records.

## Closed-Contact Semantics

For this lemma, a closed-contact endpoint means:

1. each piece is a closed tetrahedron;
2. pieces may touch along catalogued lower-dimensional intersections;
3. touching along a face, edge, or vertex is allowed;
4. strict interior overlap is not allowed;
5. no positive-clearance condition is imposed at catalogued contacts.

In particular, a pair of pieces sharing a face or edge has zero clearance at
`theta = 0`. That is expected and is not a failure under closed-contact
semantics.

## Statement

Let `T` and `P0,P1,P2,P3` be the catalogued S4 median-plane tetrahedra from
`S4_LEMMA_01_GEOMETRY_AND_TILING.md`.

Consider the endpoint configuration `E0` in which the four pieces are placed
in their catalogued closed tiling positions, with no hinge rotation applied.
Then:

1. every `Pi` lies in the closed ambient tetrahedron `T`;
2. the four piece volumes sum to `Vol(T)`;
3. all six unordered piece pairs are catalogued contacts;
4. the six contacts consist of four shared-face contacts and two shared-edge
   contacts;
5. no unordered pair has strict interior overlap;
6. `E0` is not a positive-clearance configuration;
7. for the representative hinge trees `TREE_007` and `TREE_021`, assigning
   zero angle to every selected hinge gives the identity transform on every
   piece vertex, so both representatives have the same catalogued endpoint.

Thus `theta = 0` is a valid zero-thickness closed-contact endpoint for the
audited S4 representatives, but not a positive-clearance or physical hinge
certificate.

## Pair Contact Ledger

The complete unordered pair ledger is:

| Pair | Contact ID | Contact type | Shared set | Strict interior overlap |
| --- | --- | --- | --- | --- |
| `P0-P1` | `C0` | shared face | `conv(A, M_AB, M_CD)` | no |
| `P0-P2` | `C1` | shared face | `conv(C, M_AB, M_CD)` | no |
| `P0-P3` | `C2` | shared edge | `conv(M_AB, M_CD)` | no |
| `P1-P2` | `C3` | shared edge | `conv(M_AB, M_CD)` | no |
| `P1-P3` | `C4` | shared face | `conv(D, M_AB, M_CD)` | no |
| `P2-P3` | `C5` | shared face | `conv(B, M_AB, M_CD)` | no |

Consequently:

```text
pair_count = 6
catalogued_contact_pair_count = 6
shared_face_contact_pair_count = 4
shared_edge_contact_pair_count = 2
noncatalogued_pair_count = 0
strict_interior_overlap_pair_count = 0
```

## Proof

### 1. Containment And Volume

By Lemma 01,

```text
Pi subset T for i = 0,1,2,3,
P0 union P1 union P2 union P3 = T,
Vol(Pi) = sqrt(2)/48,
Vol(T) = sqrt(2)/12.
```

Therefore every piece lies in the closed ambient tetrahedron and

```text
sum_i Vol(Pi) = 4 * sqrt(2)/48 = sqrt(2)/12 = Vol(T).
```

This proves the containment and volume-sum parts of the endpoint claim.

### 2. Catalogued Contacts

Lemma 01 gives the exact pairwise intersections:

```text
P0 cap P1 = conv(A, M_AB, M_CD)
P0 cap P2 = conv(C, M_AB, M_CD)
P0 cap P3 = conv(M_AB, M_CD)
P1 cap P2 = conv(M_AB, M_CD)
P1 cap P3 = conv(D, M_AB, M_CD)
P2 cap P3 = conv(B, M_AB, M_CD)
```

There are exactly `binomial(4,2) = 6` unordered pairs of pieces. The list above
contains all six. Hence every unordered pair is a catalogued contact pair, and
there are no noncatalogued piece-pair intersections to classify.

Four intersections are two-dimensional shared faces, and two intersections are
the one-dimensional shared edge `conv(M_AB,M_CD)`.

### 3. No Strict Interior Overlap

Lemma 01 also proves that the relative interiors of `P0,P1,P2,P3` are pairwise
disjoint.

For closed tetrahedral pieces in the same ambient three-space, a strict
interior overlap would require a point lying in the ordinary interior of both
pieces. Since the relative interiors are pairwise disjoint, no such point
exists.

Equivalently, every pairwise intersection listed above is contained in a
proper face or edge of each involved piece. Those intersections have dimension
at most `2`, not dimension `3`, and therefore contain no common interior
volume.

Thus the strict interior-overlap pair count is `0`.

### 4. Zero-Angle Representative Endpoint

The representative endpoint statement is only a zero-angle identity statement.
It does not prove any positive-angle motion.

The selected representatives in the certificate are:

| Class | Representative | Hinge IDs |
| --- | --- | --- |
| `CLASS_A_TREE007_TREE009` | `TREE_007` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` |
| `CLASS_B_TREE021_TREE093` | `TREE_021` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` |

For a rigid rotation about an axis through points `p0,p1`, the transform used
by the audit has the form

```text
x -> R_theta x + p0 - R_theta p0.
```

At `theta = 0`, `R_0` is the identity matrix, and the translation term is

```text
p0 - R_0 p0 = p0 - p0 = 0.
```

Therefore every selected hinge transform at zero angle is the identity. A
composition of identity transforms is still the identity, so every piece vertex
is fixed. Consequently `TREE_007` and `TREE_021` share the same endpoint
configuration `E0`.

This resolves only the endpoint identity part of the representative records.
It does not resolve the positive-angle kinematic lemma planned for
`S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`.

### 5. Why This Is Not Positive Clearance

The contact ledger contains shared faces and shared edges. For example,

```text
P0 cap P1 = conv(A, M_AB, M_CD)
```

is a full triangular face. Therefore the distance between `P0` and `P1` is
zero at `theta = 0`. The same is true for every catalogued contact pair.

Hence the endpoint is closed-contact non-interpenetrating, not
positive-clearance. This distinction is part of the statement, not a technical
defect.

## Certificate Consistency Check

The exact argument above matches the theta-zero report:

| Report metric | Value |
| --- | --- |
| `status` | `theta_zero_closed_contact_certificate_completed` |
| `pair_count` | `6` |
| `catalogued_contact_pair_count` | `6` |
| `shared_face_contact_pair_count` | `4` |
| `shared_edge_contact_pair_count` | `2` |
| `noncatalogued_pair_count` | `0` |
| `strict_interior_overlap_pair_count` | `0` |
| `all_piece_vertices_inside_ambient_closed_tetrahedron` | `true` |
| `volume_sum_matches_ambient` | `true` |
| `all_zero_angle_transforms_identity_on_vertices` | `true` |

The report's SAT/tolerance machinery is not needed for the exact proof of the
static tiling endpoint. It remains useful as executable confirmation that the
workspace implementation is checking the same closed-contact semantics.

## Exactness Status

The main endpoint claims are exact consequences of Lemma 01:

- containment;
- volume sum;
- contact graph;
- no strict interior overlap;
- no positive clearance.

The representative zero-angle transform statement is exact because it uses
only the identity property of a zero-angle rotation and composition of
identity transforms.

No sampled positive-angle motion, finite cell ledger, interval guard, or
floating tolerance is used as a proof ingredient here.

## Claim Boundary

This lemma supports only the closed endpoint:

```text
theta = 0 is the catalogued closed-contact endpoint for the audited S4 representatives.
```

Do not infer:

```text
positive clearance at theta = 0
positive-angle motion
open-domain ray validity
bounded-cell motion validity
dynamic connectedness between TREE_007 and TREE_021
physical hinge thickness, offsets, CAD, or printability
global S4 hingeability
CL5 theorem promotion
```

Those remain controlled by later lemmas, certificate ledgers, and red-team
review.

## R6b Result

This draft resolves the second initial writing target from
`docs/S4_MATHEMATICAL_LEMMA_PLAN.md`:

```text
L2 Closed-contact endpoint
S4-PO-002 theta-zero endpoint, endpoint-contact part
```

It also records the zero-angle identity endpoint for `TREE_007` and
`TREE_021`, but it does not resolve the full kinematic transform lemma
`S4-PO-003`.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
