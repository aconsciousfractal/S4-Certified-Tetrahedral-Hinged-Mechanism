# S4 CL5 A7c/B04 contact-side bridge certificate

Status: exact local bridge certificate for the one-parameter selected B04 rows.  Not a physical hinge-thickness claim.  Not a three-parameter bounded-cell certificate.

Date: 2026-06-23.

Case: `historical_s4_median_planes`.

Manifest:

```text
results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_contact_side_bridge_manifest.json
```

Generator:

```text
scripts/build_s4_cl5_a7c_b04_contact_side_bridge_certificate.py
```

A7c source manifest consumed by the bridge:

```text
results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json
```

The bridge rows are not an independent hardcoded list.  The generator reads the
A7c manifest, loads each referenced A7c object record, and asserts equality of
`tree_id`, `hinge_id`, `pair`, and `ray_sign` before building the local wedge
record.

## Purpose

The external red-team review correctly identified a semantic gap in the older A7c/B04 wording.  A7c proved a constant nonzero signed hinge angle, but the package also needed a self-contained geometric implication:

```text
package-approved selected-hinge opening side
+ hinge-axis preservation
=> boundary hinge contact and no strict interior overlap
```

This note supplies that bridge for the six selected shared-face B04 rows on the one-parameter ray domain:

```text
0 < theta <= 120 degrees
```

It does not claim positive SAT clearance.  The selected hinge remains a zero-margin boundary contact along the hinge axis.

## Certified rows

The bridge manifest emits six accepted records consumed from the A7c manifest:

| Tree | Pair | Hinge | Contact | Ray sign |
|---|---|---|---|---:|
| `TREE_007` | `P0-P1` | `H0_A_M_AB` | `C0` | `+1` |
| `TREE_007` | `P0-P2` | `H4_C_M_CD` | `C1` | `+1` |
| `TREE_007` | `P1-P3` | `H7_D_M_CD` | `C4` | `-1` |
| `TREE_021` | `P0-P1` | `H0_A_M_AB` | `C0` | `+1` |
| `TREE_021` | `P1-P3` | `H7_D_M_CD` | `C4` | `-1` |
| `TREE_021` | `P2-P3` | `H9_B_M_AB` | `C5` | `+1` |

Result:

```text
A7c/B04 bridge records accepted: 6/6
```

## Local wedge lemma

Fix one selected row.  Let the oriented hinge axis be `a -> b`, and let `F` be the third vertex of the source shared face, so the source face is:

```text
conv(a, b, F)
```

Let `Qp` be the parent apex not in this face, and `Qc` the child apex not in this face.  In the normal cross-section around the hinge axis, define the oriented side form

```text
Omega(X,Y) = (b-a) dot ((X-a) x (Y-a)).
```

For the A7c ray sign `sigma`, the checker verifies exactly:

```text
sigma * Omega(F, Qp) = -sqrt(2)/8 < 0
sigma * Omega(F, Qc) =  sqrt(2)/8 > 0
```

for every one of the six records.  Thus the A7c sign is not just nonzero: it is the child/opening side of the selected source face.

The same cross-section gives the sector angle `alpha` between the source face ray and either adjacent tetrahedral apex ray:

```text
cos(alpha) = sqrt(6)/3 > 1/2
```

Therefore:

```text
0 < alpha < 60 degrees.
```

Since the audited ray domain satisfies `0 < theta <= 120 degrees`, the opened child sector satisfies:

```text
theta + alpha < 180 degrees.
```

So the child sector cannot wrap around behind the hinge axis into the parent sector.

## Direct half-angle check

The generator also checks the actual rotated child vertices under

```text
t = tan(theta/2)
0 < t <= sqrt(3)
```

For the rotated third vertex of the source face, the signed side is exactly:

```text
t / (2 * (t^2 + 1)) > 0.
```

For the rotated child apex, each row reduces to one of the positive rational forms recorded in the row JSON.  The numerator has all positive roots strictly greater than `sqrt(3)`, the denominator is positive, and the sample signs at `t=1` and `t=sqrt(3)` are positive.  Hence the rotated child face vertex and rotated child apex are strictly on the child side for the full one-parameter ray domain.

By convexity, every non-axis point of the rotated child tetrahedron is strictly on the child side of the original source contact plane.  The parent tetrahedron lies on the opposite side, with equality only on its original source face.  Their intersection is therefore contained in the hinge axis.

Together with Lemma 03 hinge-axis preservation, the selected pair remains joined along the hinge axis and has no strict interior overlap.

## Claim boundary

Can say:

```text
For the six selected shared-face B04 rows on the one-parameter ray, A7c plus the local wedge bridge proves boundary hinge contact and no strict interior overlap in the zero-thickness model.
```

Must not say:

```text
selected hinges have positive SAT clearance;
physical hinges with thickness are certified by this bridge;
the three-parameter bounded-cell branch is certified by this bridge;
global S4 hingeability or dynamic connectedness is proved by this bridge.
```

## External red-team disposition

This artifact addresses the mathematical content of `RT-EXT-1` for the scoped one-parameter selected B04 rows.  A follow-up red-team hardening pass required two changes, both now implemented in the source generator and this release-review repository: bridge rows are consumed from the A7c manifest/object records, and the angular half-turn condition is recorded as an exact inequality certificate.  The controlled rebuild now integrates this manifest; release status is governed by `paper/PUBLIC_PACKAGE_MANIFEST.json` and the package gates.

## Source dependencies

- `certified/source_docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`
- `certified/source_docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`
- `certified/source_docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `certified/source_docs/S4_CL5_A7C_SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE.md`
- `certified/source_docs/S4_CL5_SELECTED_HINGE_CONTACT_ORIENTATION_REVIEW.md`
