# S4 Lemma 05: Ray Finite-Cover Ledger

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-05-RAY-FINITE-COVER-LEDGER-2026-06-21`
review status: local finite-ledger lemma draft

## Purpose

This lemma records the finite ray-cell cover on the audited interval:

```text
0.5 <= theta <= 120 degrees
```

for the two signed-ray representatives:

```text
TREE_007, TREE_021
```

It is a ledger lemma: it states the finite domain, guard families, overlay order, and final coverage counts.

It is not a CL5 theorem, not an exact arithmetic proof, not a physical hingeability claim, and not a statement about `theta = 0`.

## Source Anchors

- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `docs/S4_LEMMA_04_SIGNED_RAY_CLASSES.md`
- `results/historical_s4_median_planes/two_class_ray_cell_guard_report.json`
- `results/historical_s4_median_planes/two_class_contact_orientation_report.json`
- `results/historical_s4_median_planes/residual_shared_face_analytic_certificate_report.json`
- `results/historical_s4_median_planes/tree021_residual_edge_targeted_guard_report.json`
- `docs/S4_TWO_CLASS_RAY_CELL_CERTIFICATE_SUMMARY.md`

## Domain

The audited representative set is:

```text
R = {TREE_007, TREE_021}.
```

The theta interval is subdivided into base ray cells:

```text
I_k = [0.5 + 0.25 k, 0.75 + 0.25 k] degrees, for k = 0, ..., 477.
```

Thus each representative has:

```text
478 ray cells
```

For each representative and each ray cell, the ledger checks the six unordered piece pairs:

```text
P0-P1, P0-P2, P0-P3, P1-P2, P1-P3, P2-P3.
```

Therefore each representative has:

```text
478 * 6 = 2868 pair-cells.
```

## Representative Signed Rays

The representatives and signed rays are inherited from Lemma 04:

| Representative | Hinge IDs | Signs |
| --- | --- | --- |
| `TREE_007` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `(+,+,-)` |
| `TREE_021` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `(+,-,+)` |

The selected hinge-contact pairs are:

| Representative | Selected hinge-contact pairs |
| --- | --- |
| `TREE_007` | `P0-P1`, `P0-P2`, `P1-P3` |
| `TREE_021` | `P0-P1`, `P1-P3`, `P2-P3` |

Each representative therefore has:

```text
1434 selected hinge-contact pair-cells
1434 non-hinge or residual-contact pair-cells
```

## Guard Families

The finite cover uses four guard families.

### G1. Clearance Guard

The ray-cell clearance guard uses a center separating-axis check plus a local angular displacement bound.

Report parameters:

```text
theta_start_degrees = 0.5
theta_end_degrees = 120.0
theta_step_degrees = 0.25
sat_tolerance = 1e-8
displacement_safety_factor = 1.25
```

The report describes the rule as:

```text
center separating-axis overlap plus local angular displacement bound must stay <= SAT tolerance
```

This guard is used only where it yields a positive separating-margin certificate under the finite protocol.

### G2. Selected-Hinge Contact Orientation

Selected hinge contacts are zero-margin contact pairs, so they are not certified by strict clearance.

The orientation overlay certifies them when:

```text
selected hinge angle interval excludes zero and stays within an open half-turn;
the midpoint sample is collision-free.
```

This covers the selected hinge-contact pair-cells.

### G3. Residual Shared-Face Formula Overlay

The residual shared-face overlay applies the formula:

```text
sin(theta/2)^3 * cos(theta/2)
```

on:

```text
0.5 <= theta <= 120 degrees.
```

The report records:

```text
formula_positive_on_interval = true
```

because:

```text
0 < theta/2 <= 60 degrees
```

so `sin(theta/2)` and `cos(theta/2)` are positive on this interval.

This lemma uses the formula overlay as a finite ledger component. It does not derive the formula from first principles.

### G4. Targeted TREE_021 Residual Shared-Edge Guard

After the shared-face overlay, the only remaining pair-cells are:

```text
TREE_021, pair P1-P2, theta intervals [0.5, 0.75] and [0.75, 1.0].
```

The targeted guard subdivides:

```text
0.5 <= theta <= 1.0
```

into:

```text
10 subcells of width 0.05 degrees.
```

All 10 subcells are clearance-certified by the targeted finite guard, adding the final two parent pair-cells.

## Coverage Ledger

### Stage 1: Clearance Guard

| Tree | Ray cells with collision-free center sample | Pair-cells clearance-certified | Non-hinge pair-cells certified | Non-hinge pair-cells unresolved |
| --- | ---: | ---: | ---: | ---: |
| `TREE_007` | `478/478` | `1373/2868` | `1373/1434` | `61` |
| `TREE_021` | `478/478` | `1371/2868` | `1371/1434` | `63` |

Pair-level clearance results:

| Tree | Pair | Role | Certified cells | Uncertified cells |
| --- | --- | --- | ---: | ---: |
| `TREE_007` | `P0-P1` | selected hinge contact | `0` | `478` |
| `TREE_007` | `P0-P2` | selected hinge contact | `0` | `478` |
| `TREE_007` | `P0-P3` | residual shared edge | `478` | `0` |
| `TREE_007` | `P1-P2` | residual shared edge | `478` | `0` |
| `TREE_007` | `P1-P3` | selected hinge contact | `0` | `478` |
| `TREE_007` | `P2-P3` | residual shared face | `417` | `61` |
| `TREE_021` | `P0-P1` | selected hinge contact | `0` | `478` |
| `TREE_021` | `P0-P2` | residual shared face | `417` | `61` |
| `TREE_021` | `P0-P3` | residual shared edge | `478` | `0` |
| `TREE_021` | `P1-P2` | residual shared edge | `476` | `2` |
| `TREE_021` | `P1-P3` | selected hinge contact | `0` | `478` |
| `TREE_021` | `P2-P3` | selected hinge contact | `0` | `478` |

### Stage 2: Selected-Hinge Contact Orientation

The selected-hinge orientation overlay certifies:

```text
1434 selected hinge-contact pair-cells per representative.
```

After Stage 2:

| Tree | Covered pair-cells | Uncovered pair-cells | Fully covered ray cells |
| --- | ---: | ---: | ---: |
| `TREE_007` | `2807/2868` | `61` | `417/478` |
| `TREE_021` | `2805/2868` | `63` | `417/478` |

### Stage 3: Residual Shared-Face Overlay

The residual shared-face formula overlay adds:

```text
61 pair-cells for TREE_007 P2-P3
61 pair-cells for TREE_021 P0-P2
122 pair-cells total
```

After Stage 3:

| Tree | Covered ray cells | Covered pair-cells | Remaining unresolved pair-cells |
| --- | ---: | ---: | ---: |
| `TREE_007` | `478/478` | `2868/2868` | `0` |
| `TREE_021` | `476/478` | `2866/2868` | `2` |

The remaining two pair-cells are exactly:

| Tree | Pair | Role | Theta interval |
| --- | --- | --- | --- |
| `TREE_021` | `P1-P2` | residual shared edge | `[0.5, 0.75]` |
| `TREE_021` | `P1-P2` | residual shared edge | `[0.75, 1.0]` |

### Stage 4: Targeted TREE_021 Residual Shared-Edge Guard

The targeted guard subdivides `[0.5, 1.0]` into `10` subcells and clearance-certifies all `10/10`.

It adds:

```text
2 parent pair-cells
```

After Stage 4:

| Tree | Covered ray cells | Covered pair-cells | Remaining unresolved pair-cells |
| --- | ---: | ---: | ---: |
| `TREE_007` | `478/478` | `2868/2868` | `0` |
| `TREE_021` | `478/478` | `2868/2868` | `0` |

The final report records:

```text
all_representative_ray_cells_fully_certified_after_targeted_guard = true
```

## Statement

For the catalogued S4 zero-thickness representative rays `TREE_007` and `TREE_021`, the finite ledger above assigns at least one guard certificate to every pair-cell in:

```text
R * {ray_cell_0000, ..., ray_cell_0477} * {six unordered piece pairs}.
```

Equivalently, for each representative:

```text
478/478 ray cells are fully covered
2868/2868 pair-cells are covered
0 pair-cells remain unresolved
```

This is a finite cover statement for the audited ray interval `0.5 <= theta <= 120 degrees`.

## Conditional Geometric Meaning

If the four guard families have their intended geometric implication:

```text
covered pair-cell => the corresponding two closed pieces have no strict interior overlap over that cell
```

then the representative rays `TREE_007` and `TREE_021` are certified non-interpenetrating over:

```text
0.5 <= theta <= 120 degrees.
```

The implication above is a proof obligation. This lemma records the finite coverage ledger; it does not by itself close all guard-soundness and exactness issues.

## Finite Proof

The proof is finite ledger arithmetic.

1. There are `478` base ray cells per representative.
2. There are six unordered piece pairs per ray cell.
3. Therefore each representative has `2868` pair-cells.
4. The clearance guard covers the positive-clearance pair-cells listed in Stage 1.
5. The orientation overlay covers all `1434` selected hinge-contact pair-cells per representative.
6. The shared-face formula overlay covers the `61 + 61 = 122` residual shared-face pair-cells left after Stage 2.
7. The targeted residual-edge guard covers the final `2` parent pair-cells for `TREE_021 P1-P2`.
8. The final report has zero unresolved pair-cells for both representatives.

Thus every pair-cell in the finite domain has a ledger entry assigning it to one of the guard families.

## Explicit Non-Claims

This lemma does not prove:

- the closed endpoint `theta = 0`;
- the near-zero bridge `0 < theta <= 0.5`;
- the full 3-parameter cylindrical component graph;
- dynamic connectedness between `TREE_007` and `TREE_021`;
- global S4 hingeability;
- physical hingeability, hinge thickness, offsets, CAD, mesh validity, tolerances, or printability;
- CL5 theorem status.

## Exactness And Theorem-Promotion Blockers

The main blockers before theorem promotion are:

1. the clearance guard still depends on floating SAT values, a tolerance `1e-8`, and a displacement bound;
2. the selected-hinge orientation guard needs a written geometric implication lemma;
3. the shared-face formula is used here as a certificate overlay, but its algebraic derivation must be written separately;
4. the targeted residual-edge guard is finite and numerical, so its guard implication needs exact or interval justification;
5. coverage on `0 < theta <= 0.5` belongs to the near-zero bridge lemmas, not to this finite ray-cell ledger.

Until those blockers are resolved, this document remains a finite-ledger lemma draft, not a final theorem.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
