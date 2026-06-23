# S4 CL5 A7c Selected-Hinge Contact-Side Certificate

Date: 2026-06-22
Case: `historical_s4_median_planes`
Status: completed one-parameter B04 contact-side certificate; not theorem
promotion.

## Template Basis

This note follows the local development structure under:

```text
the local development template used during preparation
```

Template roles used: claim ledger, proof obligations, public claim boundary,
normalization/source lock, and paper-to-engine traceability.

## Purpose

A7c closes the selected-hinge `B04` layer on the one-parameter representative
ray for:

```text
TREE_007
TREE_021
```

Selected hinges are zero-margin boundary contacts.  They are intentionally not
certified by positive SAT clearance.  The exact target is the contact-side
predicate:

```text
the selected hinge axis is preserved, the signed hinge angle is nonzero,
the signed angle remains inside one open half-turn, and its sign is the
package-approved opening side.
```

## Certificate

Generator:

```text
scripts/build_s4_cl5_a7c_selected_hinge_contact_side_certificate.py
```

Manifest:

```text
results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json
```

Record directory:

```text
results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/a7c_selected_hinge_contact_side_certificate/records
```

Run summary:

```text
A7c selected-hinge records emitted: 6
A7c contact-side certificates: 6/6
ray sign counts: {'-1': 2, '1': 4}
object status counts: {'a7c_selected_hinge_contact_side_certified_on_open_ray_superset': 6}
```

## Exact Sign Argument

Lemma 03 fixes the signed-ray convention:

```text
d_h(theta) = s_h * theta,  s_h in {+1,-1}
```

Use the half-angle parameter:

```text
t = tan(theta/2)
```

On the open rational superset:

```text
0 < t < 2
```

the signed orientation has the same sign as:

```text
s_h * t
```

The generator emits a Sturm certificate for `s_h*t`: it has no root in the
open interval, with sample sign `s_h` at `t=1`.  The endpoint root `t=0`
corresponds to the closed-contact endpoint and is excluded from the open ray.

The interval `0<t<2` contains the S4 ray domain:

```text
0 < t <= sqrt(3)    <=>    0 < theta <= 120 degrees
```

It also lies inside one open half-turn because:

```text
theta = 2*atan(t), and 0 < t < 2 implies 0 < theta < 2*atan(2) < pi.
```

## Contact-Side Semantics

The record-level contact-side conclusion is source-locked to:

1. `S4_LEMMA_02_CLOSED_ENDPOINT`, which proves the shared-face closed contact
   at `theta=0`;
2. `S4_LEMMA_03_KINEMATICS_AND_SIGNS`, which proves selected hinge-axis
   preservation under rooted rigid kinematics;
3. `S4_CL5_SELECTED_HINGE_CONTACT_ORIENTATION_REVIEW`, which defines the B04
   boundary-contact semantics and the package-approved opening-side sign.

Thus A7c certifies selected shared-face boundary contact on the open
one-parameter ray.  It does not claim positive separation of selected hinge
pairs.

## Certified Objects

| Tree | Hinge | Pair | Ray sign | Status |
| --- | --- | --- | ---: | --- |
| `TREE_007` | `H0_A_M_AB` | `P0-P1` | `+1` | certified |
| `TREE_007` | `H4_C_M_CD` | `P0-P2` | `+1` | certified |
| `TREE_007` | `H7_D_M_CD` | `P1-P3` | `-1` | certified |
| `TREE_021` | `H0_A_M_AB` | `P0-P1` | `+1` | certified |
| `TREE_021` | `H7_D_M_CD` | `P1-P3` | `-1` | certified |
| `TREE_021` | `H9_B_M_AB` | `P2-P3` | `+1` | certified |

## Nonclaims

This certificate does not emit accepted schema-v1 B04 reports, B03 positive
clearance reports, bounded-cell B04 claims, non-hinge contact claims, residual
contact claims, operation enclosures, 3-parameter bounded-cell closure,
physical hingeability, or theorem promotion.

## Consequence

The one-parameter predicate layers now stand as:

```text
B05 common-edge residual      closed by A3/A4/A5/A6
B06/B07 shared-face residual  closed at formula-sign level by A7a
B03 ordinary non-contact SAT  vacuous on the ray by A7b
B04 selected-hinge contact    closed on the ray by A7c
```

A7d is now completed by `S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md`.  The next task is a post-A7d review/red-team of the scoped wrapper.
