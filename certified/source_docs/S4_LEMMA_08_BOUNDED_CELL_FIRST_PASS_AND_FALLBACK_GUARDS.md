# S4 Lemma 08: Bounded-Cell First-Pass And Fallback Guards

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-08-BOUNDED-CELL-FIRST-PASS-FALLBACK-GUARDS-2026-06-21`
review status: finite-ledger lemma draft

## Purpose

This lemma records the bounded-cell finite ledger for the two representative signed-ray classes:

```text
TREE_007, TREE_021.
```

It combines:

1. the bounded cell-cover protocol;
2. the first-pass bounded-cell guard;
3. residual shared-edge fallback ledgers;
4. residual shared-face face-normal fallback ledgers;
5. residual shared-face edge-branch `G1`-`G4` fallback ledgers;
6. the final bounded-cell overlay reconstruction.

The output is a finite bounded-domain ledger over the all-free bounded cells. It is not a full physical hingeability theorem and not a global dynamic-class connection theorem.

## Source Anchors

- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `docs/S4_LEMMA_04_SIGNED_RAY_CLASSES.md`
- `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`
- `docs/S4_LEMMA_06_NEAR_ZERO_BRIDGE_FORMULAS.md`
- `docs/S4_LEMMA_07_REFINED_EDGE_RESIDUAL_CLOSURE.md`
- `results/historical_s4_median_planes/bounded_cell_cover_protocol_spec_report.json`
- `results/historical_s4_median_planes/bounded_cell_guard_first_pass_report.json`
- `results/historical_s4_median_planes/bounded_cell_shared_edge_common_edge_overlay_report.json`
- `results/historical_s4_median_planes/bounded_cell_tree021_p1p2_shared_edge_adaptive_probe_report.json`
- `results/historical_s4_median_planes/bounded_cell_tree021_p1p2_endgame_failure_classifier_report.json`
- `results/historical_s4_median_planes/bounded_cell_tree021_p1p2_support_stability_endgame_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_tree021_p1p2_margin_endgame_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_tree021_p0p3_closure_stack_report.json`
- `results/historical_s4_median_planes/bounded_cell_tree007_shared_edge_closure_stack_report.json`
- `results/historical_s4_median_planes/bounded_cell_residual_shared_face_inventory_report.json`
- `results/historical_s4_median_planes/bounded_cell_face_normal_formula_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_edge_branch_stability_classifier_report.json`
- `results/historical_s4_median_planes/bounded_cell_edge_branch_guard_plan_report.json`
- `results/historical_s4_median_planes/bounded_cell_edge_branch_g1_fixed_axis_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_edge_branch_g2_multi_axis_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_edge_branch_g3_hybrid_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_edge_branch_g4_adaptive_isolation_guard_report.json`
- `results/historical_s4_median_planes/bounded_cell_closure_overlay_report.json`
- `docs/S4_BOUNDED_CELL_COVER_PROTOCOL_SPEC_SUMMARY.md`
- `docs/S4_BOUNDED_CELL_GUARD_FIRST_PASS_SUMMARY.md`
- `docs/S4_BOUNDED_CELL_SHARED_EDGE_COMMON_EDGE_OVERLAY_SUMMARY.md`
- `docs/S4_BOUNDED_CELL_CLOSURE_OVERLAY_SUMMARY.md`

## Bounded-Cell Domain

The bounded-cell protocol constructs cylindrical wedge cells around each representative component. For each representative:

| Quantity | `TREE_007` | `TREE_021` |
| --- | ---: | ---: |
| Total protocol cells | `864` | `864` |
| All-vertices-free cells | `768` | `768` |
| Cells with a blocked sampled vertex | `96` | `96` |
| All-free face-adjacent components | `1` | `1` |
| Largest all-free component size | `768` | `768` |

The finite target of this lemma is only the all-free part:

```text
768 + 768 = 1536 all-free bounded cells.
```

Each bounded cell has six unordered piece-pairs. Therefore the original pair-cell ledger is:

```text
1536 * 6 = 9216 pair-cells.
```

The protocol starts at `theta = 0.5` degrees and does not cover the closed endpoint `theta = 0`. Cells with blocked sampled vertices are not part of this finite target.

## First-Pass Guard Layer

The first-pass bounded-cell guard checks the complete all-free bounded-cell target.

| Metric | Value |
| --- | ---: |
| Candidate all-free bounded cells | `1536` |
| Center-sample collision-free cells | `1536` |
| First-pass fully covered cells | `173` |
| First-pass not-fully-covered cells | `1363` |
| Original pair-cells | `9216` |
| First-pass covered pair-cells | `5421` |
| First-pass uncovered pair-cells | `3795` |

The first-pass pair-cell coverage splits as:

| First-pass method | Pair-cells |
| --- | ---: |
| Selected-hinge orientation full-cell guard | `4608` |
| Clearance full-cell guard | `813` |
| **Total** | **`5421`** |

The first pass is a conservative guard. A first-pass-uncovered pair-cell is not a collision claim; it is a pair-cell that must be routed to a residual fallback family.

## Residual Fallback Split

The final overlay reconstructs the first-pass-uncovered front as:

| Residual fallback class | Pair-cells |
| --- | ---: |
| Shared-edge fallback closures | `2528` |
| Shared-face face-normal formula guard | `544` |
| Shared-face edge-branch `G1`-`G4` guards | `723` |
| **Total** | **`3795`** |

The accounting identity is:

```text
2528 + 544 + 723 = 3795.
```

Together with the first pass:

```text
5421 + 3795 = 9216.
```

## Shared-Edge Fallback Ledger

The direct common-edge overlay targets the first-pass-uncovered residual shared-edge pair-cells.

| Metric | Value |
| --- | ---: |
| Input residual shared-edge pair-cells | `2528` |
| Direct common-edge certified pair-cells | `624` |
| Direct common-edge uncovered pair-cells | `1904` |

The direct common-edge overlay is not itself closed. Closure comes from the shared-edge fallback stacks below.

### TREE_021 P1-P2

The hardest shared-edge target is `TREE_021 P1-P2`.

| Stage | Count |
| --- | ---: |
| Base pair-cells | `768` |
| Depth-5 certified terminal boxes | `4510` |
| Depth-5 failed terminal boxes | `993` |
| Fully covered base pair-cells at depth 5 | `633` |
| Partially covered base pair-cells at depth 5 | `135` |

The endgame classifier splits the `993` failed terminal boxes as:

| Endgame class | Boxes |
| --- | ---: |
| Stability-only | `775` |
| Margin-only | `218` |
| **Total** | **`993`** |

The stability endgame guard certifies:

| Metric | Value |
| --- | ---: |
| Stability-only target boxes | `775` |
| Stability-only certified boxes | `775` |
| Remaining failed terminal boxes after stability guard | `218` |
| Fully covered base pair-cells after stability guard | `729` |
| Remaining failed base pair-cells | `39` |

The margin endgame guard then certifies:

| Metric | Value |
| --- | ---: |
| Margin-only target boxes | `218` |
| Replacement terminal leaves | `871` |
| Certified replacement terminal leaves | `871` |
| Failed replacement terminal leaves | `0` |
| Refined terminal elements after margin guard | `6156/6156` |
| Fully covered base pair-cells after margin guard | `768/768` |

Thus `TREE_021 P1-P2` contributes `768` closed shared-edge fallback pair-cells to the final overlay.

### TREE_021 P0-P3

The `TREE_021 P0-P3` closure stack records:

| Metric | Value |
| --- | ---: |
| Direct target pair-cells | `592` |
| Direct certified pair-cells | `208` |
| Direct failed pair-cells | `384` |
| Replacement terminal leaves | `756` |
| Certified replacement terminal leaves | `756` |
| Refined terminal elements after closure | `964/964` |
| Fully covered base pair-cells after closure | `592/592` |

Thus `TREE_021 P0-P3` contributes `592` closed shared-edge fallback pair-cells.

### TREE_007 Shared-Edge Pairs

The `TREE_007` shared-edge closure stack covers the `P0-P3` and `P1-P2` shared-edge fallback pairs.

| Metric | Value |
| --- | ---: |
| Target pair count | `2` |
| Direct target pair-cells | `1168` |
| Direct certified pair-cells | `416` |
| Direct failed pair-cells | `752` |
| Replacement terminal leaves | `1502` |
| Certified replacement terminal leaves | `1502` |
| Refined terminal elements after closure | `1918/1918` |
| Fully covered base pair-cells after closure | `1168/1168` |

In the final overlay this appears as:

| Tree-pair source | Pair-cells |
| --- | ---: |
| `TREE_007 P0-P3` closure stack | `592` |
| `TREE_007 P1-P2` closure stack | `576` |
| **Total** | **`1168`** |

The shared-edge fallback total is therefore:

```text
768 + 592 + 1168 = 2528.
```

## Shared-Face Face-Normal Fallback Ledger

After the shared-edge front is routed, the residual shared-face inventory reconstructs the remaining first-pass-uncovered shared-face cells.

| Metric | Value |
| --- | ---: |
| First-pass-uncovered shared-face cells | `1267` |
| Center-axis face-normal cells | `544` |
| Center-axis edge-branch cells | `723` |
| Center-axis other cells | `0` |

The bounded-cell face-normal formula guard certifies:

| Metric | Value |
| --- | ---: |
| Input face-normal cells | `544` |
| Formula-certified cells | `544` |
| Formula-uncovered cells | `0` |
| Formula/direct-geometry sample checks | `4720` |

Thus the face-normal fallback contributes `544` closed pair-cells to the final bounded-cell overlay.

## Shared-Face Edge-Branch Fallback Ledger

The edge-branch stability classifier evaluates the `723` residual shared-face edge-branch cells at center and vertex samples.

| Metric | Value |
| --- | ---: |
| Input edge-branch cells | `723` |
| Sample checks | `6203` |
| Assigned edge-axis sample-stable cells | `150` |
| Assigned-axis separating at all samples | `701` |
| Assigned-axis nonseparating at some sample | `22` |

The guard-plan report partitions the `723` edge-branch cells into four executable routes:

| Route | Meaning | Cells |
| --- | --- | ---: |
| `G1` | fixed assigned-axis lower-bound guard | `150` |
| `G2` | multi-edge-axis switch guard | `371` |
| `G3` | hybrid edge/face axis-switch guard | `180` |
| `G4` | adaptive nonseparating-axis isolation | `22` |
| **Total** |  | **`723`** |

The route reports certify:

| Route | Cells certified | Subcells certified |
| --- | ---: | ---: |
| `G1` fixed assigned axis | `150/150` | `9600/9600` |
| `G2` multi-edge axis | `371/371` | `23744/23744` |
| `G3` hybrid edge/face | `180/180` | `11520/11520` |
| `G4` adaptive isolation | `22/22` | `1408/1408` |
| **Total** | **`723/723`** | **`46272/46272`** |

Route details:

| Route | Internal split |
| --- | --- |
| `G1` | all `9600` subcells certified by the fixed assigned-axis support-component guard |
| `G2` | `23212` subcells by sampled/assigned edge-axis family; `532` by local named-edge-axis fallback |
| `G3` | `10751` subcells by sampled edge-axis family; `218` by local edge-axis fallback; `551` by face-normal formula fallback |
| `G4` | `1400` subcells by sampled edge-axis family; `8` by local edge-axis fallback |

Thus the edge-branch fallback contributes `723` closed pair-cells to the final bounded-cell overlay.

## Overlay Reconstruction Invariant

The final bounded-cell overlay regenerates the first-pass pair-cell keys and attaches every first-pass-uncovered key to exactly one residual fallback certificate.

The reconstructed base ledger is:

| Tree | Bounded cells | Pair-cells |
| --- | ---: | ---: |
| `TREE_007` | `768` | `4608` |
| `TREE_021` | `768` | `4608` |
| **Total** | **`1536`** | **`9216`** |

Coverage-source counts:

| Source | Pair-cells |
| --- | ---: |
| First-pass selected-hinge orientation | `4608` |
| First-pass clearance full-cell guard | `813` |
| `TREE_021 P1-P2` margin endgame | `768` |
| `TREE_007 P0-P3` closure stack | `592` |
| `TREE_021 P0-P3` closure stack | `592` |
| `TREE_007 P1-P2` closure stack | `576` |
| Shared-face face-normal formula guard | `544` |
| Edge-branch `G2` multi-axis guard | `371` |
| Edge-branch `G3` hybrid guard | `180` |
| Edge-branch `G1` fixed-axis guard | `150` |
| Edge-branch `G4` adaptive-isolation guard | `22` |
| **Total** | **`9216`** |

The final overlay records:

| Metric | Value |
| --- | ---: |
| Candidate bounded cells | `1536` |
| Center-sample collision-free cells | `1536` |
| Original pair-cells | `9216` |
| First-pass covered pair-cells | `5421` |
| Fallback covered pair-cells | `3795` |
| Final covered pair-cells | `9216` |
| Final uncovered pair-cells | `0` |
| Final fully covered bounded cells | `1536` |
| Final uncovered bounded cells | `0` |
| Bounded-cell overlay closed | `true` |

Each of the `12` `(tree, piece-pair)` blocks has `768/768` pair-cells covered.

## Lemma Statement

For the catalogued S4 zero-thickness model and the representative hinge trees `TREE_007` and `TREE_021`, the bounded-cell all-free target is finite-covered as follows:

1. the bounded-cell protocol contributes `768` all-free cells for each representative, hence `1536` all-free cells total;
2. the associated pair-cell ledger has `9216` pair-cells;
3. the first-pass bounded-cell guard covers `5421` pair-cells;
4. the remaining `3795` pair-cells are routed to residual fallback ledgers;
5. the residual shared-edge fallback ledgers cover `2528` pair-cells;
6. the residual shared-face face-normal formula guard covers `544` pair-cells;
7. the residual shared-face edge-branch route guards cover `723` pair-cells, with `46272/46272` certified subcells across `G1`-`G4`;
8. the final overlay reconstructs the original pair-cell ledger and records zero uncovered pair-cells.

Thus the finite bounded-cell overlay coverage is:

| Domain | Covered | Total |
| --- | ---: | ---: |
| All-free bounded cells | `1536` | `1536` |
| Pair-cells | `9216` | `9216` |

## Proof Skeleton

The proof has four finite-ledger steps.

First, the bounded cell-cover protocol defines a finite all-free target: `768` cells per representative, excluding cells with blocked sampled vertices and excluding the endpoint `theta = 0`.

Second, the first-pass bounded-cell guard gives a pair-cell ledger with `5421` pair-cells already covered and `3795` pair-cells routed to residual fallback classes.

Third, the residual fallback reports close the routed classes:

- shared-edge pair-cells by common-edge/adaptive shared-edge stacks;
- shared-face face-normal pair-cells by formula guards;
- shared-face edge-branch pair-cells by `G1`-`G4` support-component and fallback guards.

Fourth, the overlay reconstruction verifies that the first-pass-covered keys and fallback-covered keys recombine to the complete `9216` pair-cell ledger, with no uncovered cell and no uncovered pair-cell.

The conclusion is a finite coverage statement over recorded bounded-cell keys. It becomes a mathematical non-overlap lemma only after the guard soundness and exactness blockers below are resolved.

## Explicit Non-Claims

This lemma does not prove:

- coverage of cells with blocked sampled vertices;
- coverage of `theta = 0`;
- positive endpoint clearance at `theta = 0`;
- dynamic connectedness between `TREE_007` and `TREE_021`;
- physical hingeability, hinge thickness, offsets, CAD, mesh validity, tolerances, or printability;
- global S4 hingeability outside the audited representatives and bounded-cell target;
- CL5 theorem promotion.

## Exactness And Theorem-Promotion Blockers

Before theorem promotion, the following must be closed or explicitly demoted:

1. the first-pass selected-hinge orientation guard must be stated as a geometric non-interpenetration lemma over a full cell;
2. the first-pass clearance guard must be stated as a conservative separating-axis or support-gap lemma with rigorous interval bounds;
3. the shared-edge common-edge/adaptive stacks must be proved to cover each parent pair-cell when terminal children replace a failed parent box;
4. the face-normal bounded-cell formula guard must include reviewer-readable derivations and support-extremality proofs over the cell intervals;
5. the `G1`-`G4` edge-branch route guards must be rewritten as support-component inequalities over their subcells;
6. adaptive subdivision must be formalized as a parent-cover invariant: certified terminal leaves cover the original base key;
7. overlay keys must be formalized so first-pass and fallback records are disjoint where required and complete when unioned;
8. floating tolerances, safety factors, sampled support choices, and formula-check errors must be separated from exact algebraic claims;
9. the final theorem wrapper must keep the bounded-cell ledger separate from the near-zero bridge, refined-edge ledger, and theta-zero closed-contact endpoint.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
