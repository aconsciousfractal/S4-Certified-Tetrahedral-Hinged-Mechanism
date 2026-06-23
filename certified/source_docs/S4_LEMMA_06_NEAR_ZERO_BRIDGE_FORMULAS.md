# S4 Lemma 06: Near-Zero Bridge Formulas

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-06-NEAR-ZERO-BRIDGE-FORMULAS-2026-06-21`
review status: local formula-bridge lemma draft

## Purpose

This lemma records the formula bridge for the open interval:

```text
0 < theta <= 0.5 degrees
```

for the representative rays:

```text
TREE_007, TREE_021.
```

It connects the closed endpoint excluded at `theta = 0` to the finite ray-cell ledger starting at `theta = 0.5`.

This is a zero-thickness ray-line statement only. It is not a physical hingeability claim, not a full 3-parameter component proof, and not a positive-clearance statement at `theta = 0`.

## Source Anchors

- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`
- `results/historical_s4_median_planes/near_zero_gap_inventory_report.json`
- `results/historical_s4_median_planes/residual_shared_face_formula_check_report.json`
- `results/historical_s4_median_planes/residual_shared_edge_formula_check_report.json`
- `results/historical_s4_median_planes/open_limit_ray_certificate_report.json`
- `scripts/audit_historical_s4_residual_shared_face_formula_check.py`
- `scripts/audit_historical_s4_residual_shared_edge_formula_check.py`
- `scripts/audit_historical_s4_open_limit_ray_certificate.py`

## Angle Convention

The reports store probe values in degrees.

The formulas in this lemma use:

```text
theta = the corresponding angle in radians.
```

Thus the bridge interval is:

```text
0 < theta <= pi / 360.
```

The larger shared-face formula is also positive up to `120` degrees, but this lemma uses it only for the near-zero bridge unless explicitly stated otherwise.

## Near-Zero Inventory

The near-zero inventory reports the following shape for each representative:

```text
3 selected hinge-contact pairs
2 residual shared-edge targets
1 residual shared-face target
```

### TREE_007

| Pair | Role | Bridge handling |
| --- | --- | --- |
| `P0-P1` | selected hinge contact | selected-hinge orientation |
| `P0-P2` | selected hinge contact | selected-hinge orientation |
| `P1-P3` | selected hinge contact | selected-hinge orientation |
| `P0-P3` | residual shared edge | shared-edge normalized-gap formula |
| `P1-P2` | residual shared edge | shared-edge normalized-gap formula |
| `P2-P3` | residual shared face | shared-face cubic formula |

### TREE_021

| Pair | Role | Bridge handling |
| --- | --- | --- |
| `P0-P1` | selected hinge contact | selected-hinge orientation |
| `P1-P3` | selected hinge contact | selected-hinge orientation |
| `P2-P3` | selected hinge contact | selected-hinge orientation |
| `P0-P3` | residual shared edge | shared-edge normalized-gap formula |
| `P1-P2` | residual shared edge | shared-edge normalized-gap formula |
| `P0-P2` | residual shared face | shared-face cubic formula |

## Selected-Hinge Contact Bridge

Selected hinge-contact pairs are zero-margin contact pairs. They are not certified by positive clearance near `theta = 0`.

The open-limit report uses the selected-hinge orientation rule:

```text
signed hinge angles keep constant nonzero sign on the open bridge and remain within an open half-turn.
```

For this lemma, selected hinge-contact pairs are therefore treated as non-interpenetrating open-contact pairs on:

```text
0 < theta <= 0.5 degrees
```

subject to the later guard-soundness review of the selected-hinge orientation rule.

## Residual Shared-Face Formula

The residual shared-face targets are:

| Target | Tree | Pair | Separator data in script |
| --- | --- | --- | --- |
| `TREE_007_P2_P3` | `TREE_007` | `P2-P3` | edge `B-M_CD` against edge `B-M_AB`; vector `P2:M_AB -> P3:B` |
| `TREE_021_P0_P2` | `TREE_021` | `P0-P2` | edge `M_AB-C` against edge `C-M_CD`; vector `P0:M_CD -> P2:C` |

For each target, the script computes:

```text
axis = left_edge_vector x right_edge_vector
triple(theta) = separation_vector dot axis
```

The symbolic reduction for both targets is:

```text
triple(theta) = (1 - cos(theta)) * sin(theta) / 4
```

Using:

```text
1 - cos(theta) = 2 sin(theta/2)^2
sin(theta) = 2 sin(theta/2) cos(theta/2)
```

we obtain:

```text
triple(theta)
= [2 sin(theta/2)^2] [2 sin(theta/2) cos(theta/2)] / 4
= sin(theta/2)^3 * cos(theta/2).
```

On:

```text
0 < theta <= pi / 360
```

we have:

```text
0 < theta/2 <= pi / 720 < pi/2.
```

Therefore:

```text
sin(theta/2) > 0
cos(theta/2) > 0
```

and hence:

```text
sin(theta/2)^3 * cos(theta/2) > 0.
```

This gives a positive separating triple product for the two residual shared-face bridge targets, provided the stated separator remains the active valid separator on the bridge interval.

### Numerical Check

The report `residual_shared_face_formula_check_report.json` records:

| Metric | Value |
| --- | ---: |
| Target count | `2` |
| Probe count per target | `12` |
| All formula checks within tolerance | `true` |
| All sampled triples positive | `true` |
| Max formula absolute error | `1.11e-16` |
| Minimum normalized gap at checked probes | `2.34957307e-07` |

The check is finite numerical evidence, not a replacement for the algebraic separator/support proof.

## Residual Shared-Edge Formula

The residual shared-edge targets are:

| Target | Tree | Pair | Separator |
| --- | --- | --- | --- |
| `TREE_007_P0_P3` | `TREE_007` | `P0-P3` | common-edge separator `M_AB-M_CD x M_AB-M_CD` |
| `TREE_007_P1_P2` | `TREE_007` | `P1-P2` | common-edge separator `M_AB-M_CD x M_AB-M_CD` |
| `TREE_021_P0_P3` | `TREE_021` | `P0-P3` | common-edge separator `M_AB-M_CD x M_AB-M_CD` |
| `TREE_021_P1_P2` | `TREE_021` | `P1-P2` | common-edge separator `M_AB-M_CD x M_AB-M_CD` |

For the common-edge separator, let:

```text
axis(theta) = moving_common_edge_vector_1 x moving_common_edge_vector_2.
```

For the bridge targets, the algebraic reduction has:

```text
axis_norm(theta)^2 = sin(theta)^2 * (1 + cos(theta)^2) / 4
support_numerator(theta) = sqrt(2) * sin(theta)^2 / 4.
```

For `0 < theta <= pi/360`, `sin(theta) > 0`, so:

```text
axis_norm(theta) = sin(theta) * sqrt(1 + cos(theta)^2) / 2.
```

The normalized separating gap is therefore:

```text
gap(theta)
= support_numerator(theta) / axis_norm(theta)
= [sqrt(2) sin(theta)^2 / 4] / [sin(theta) sqrt(1 + cos(theta)^2) / 2]
= sin(theta) / sqrt(2 * (1 + cos(theta)^2)).
```

On:

```text
0 < theta <= pi / 360
```

we have:

```text
sin(theta) > 0
2 * (1 + cos(theta)^2) > 0.
```

Therefore:

```text
sin(theta) / sqrt(2 * (1 + cos(theta)^2)) > 0.
```

This gives a positive normalized separating gap for the four residual shared-edge bridge targets, provided the stated support extrema and common-edge separator remain valid on the bridge interval.

### Numerical Check

The report `residual_shared_edge_formula_check_report.json` records:

| Metric | Value |
| --- | ---: |
| Target count | `4` |
| Probe count per target | `5` |
| All formula checks within tolerance | `true` |
| All sampled gaps positive | `true` |
| Max formula absolute error | `2.04e-16` |
| Minimum normalized gap at checked probes | `0.000272707702384` |

The check probes:

```text
0.03125, 0.0625, 0.125, 0.25, 0.5 degrees.
```

It supports the formula and support-branch selection, but final theorem promotion still requires exact or interval validation over the whole open bridge.

## Bridge Statement

For the two representative rays `TREE_007` and `TREE_021`, the near-zero bridge on:

```text
0 < theta <= 0.5 degrees
```

is covered by:

1. selected-hinge orientation for the three selected hinge-contact pairs per tree;
2. the positive shared-face formula for the one residual shared-face target per tree;
3. the positive shared-edge formula for the two residual shared-edge targets per tree.

Together with Lemma 05 on:

```text
0.5 <= theta <= 120 degrees
```

this supports the open representative ray interval:

```text
0 < theta <= 120 degrees.
```

The open-limit report records:

| Metric | Value |
| --- | --- |
| finite certificate on `0.5..120` | `true` |
| near-zero bridge on `(0,0.5]` | `true` |
| near-zero inventory shape confirmed | `true` |
| open-limit representative ray certificate | `true` |

## Explicit Non-Claims

This lemma does not prove:

- positive clearance or strict separation at `theta = 0`;
- physical hingeability, hinge thickness, offsets, CAD, mesh validity, tolerances, or printability;
- the full 3-parameter cylindrical component graph;
- dynamic connectedness between `TREE_007` and `TREE_021`;
- global S4 hingeability;
- theorem promotion beyond the current local-draft boundary.

## Exactness And Theorem-Promotion Blockers

Before theorem promotion, the following must be closed or explicitly demoted:

1. the separator/support branches used in the formulas must be proved stable over the bridge interval;
2. the selected-hinge orientation rule must be written as a geometric non-interpenetration lemma;
3. the symbolic reductions above must be reproduced in a reviewer-readable exact derivation, not only as script-guided algebra;
4. floating probe checks must be separated from exact algebraic claims;
5. the formulas must be integrated with the final theorem wrapper without including `theta = 0` in any positive-clearance claim.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
