> **Package provenance note.** This is a historical or future-scope source
> snapshot retained for audit trail only. It may contain words such as
> `draft`, `blocker`, or `Not a CL5 theorem`; those statements are not public
> claims of the current paper-as-public-package and do not widen the scoped
> zero-thickness theorem.

# S4 Lemma 07: Refined-Edge Residual Closure

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-07-REFINED-EDGE-RESIDUAL-CLOSURE-2026-06-21`
review status: finite-ledger lemma draft

## Purpose

This lemma records the refined-edge finite ledger for the two representative signed-ray classes:

```text
TREE_007, TREE_021.
```

It combines:

1. the original refined-edge interval guard;
2. residual shared-edge common-edge guards;
3. residual shared-face edge-branch workflows;
4. residual shared-face face-normal formula guards;
5. overlay reconstruction checks.

The output is a refined spanning-edge ledger, not a full continuous 3-parameter theorem.

## Source Anchors

- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `docs/S4_LEMMA_04_SIGNED_RAY_CLASSES.md`
- `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`
- `docs/S4_LEMMA_06_NEAR_ZERO_BRIDGE_FORMULAS.md`
- `results/historical_s4_median_planes/tree007_refined_edge_interval_guard_probe_report.json`
- `results/historical_s4_median_planes/refined_edge_interval_guard_probe_report.json`
- `results/historical_s4_median_planes/tree007_residual_contact_failure_classification_report.json`
- `results/historical_s4_median_planes/residual_contact_failure_classification_report.json`
- `results/historical_s4_median_planes/tree007_residual_contact_closure_overlay_report.json`
- `results/historical_s4_median_planes/tree021_residual_contact_closure_overlay_report.json`
- `results/historical_s4_median_planes/tree007_refined_edge_interval_certificate_overlay_report.json`
- `results/historical_s4_median_planes/tree021_refined_edge_interval_certificate_overlay_report.json`
- `docs/S4_TREE007_REFINED_EDGE_INTERVAL_CERTIFICATE_OVERLAY_SUMMARY.md`
- `docs/S4_TREE021_REFINED_EDGE_INTERVAL_CERTIFICATE_OVERLAY_SUMMARY.md`
- `docs/S4_TREE007_RESIDUAL_CONTACT_CLOSURE_OVERLAY_SUMMARY.md`
- `docs/S4_TREE021_RESIDUAL_CONTACT_CLOSURE_OVERLAY_SUMMARY.md`

## Refined-Edge Domain

For each representative, the refined spanning-edge domain contains:

| Quantity | Value |
| --- | ---: |
| Refined BFS spanning-tree segments | `2528` |
| Piece-pairs per segment | `6` |
| Total pair-segments | `15168` |

The pair-segment count is:

```text
2528 * 6 = 15168.
```

This is the refined spanning-tree ledger inside the audited finite component workflow. It is not every possible graph edge and not the full continuous 3-parameter component.

## Original Interval-Guard Layer

The original interval guard gives the first layer of coverage.

| Tree | Certified refined segments | Failed refined segments | Covered pair-segments | Residual pair-segments |
| --- | ---: | ---: | ---: | ---: |
| `TREE_007` | `1464` | `1064` | `13443` | `1725` |
| `TREE_021` | `1463` | `1065` | `13213` | `1955` |

The interval guard is conservative. A failed segment is not a collision claim; it means the coarse interval guard did not certify every pair on the segment.

## Residual Ledger For TREE_007

The `TREE_007` residual-contact classification has:

| Pair | Role | Residual pair-segments |
| --- | --- | ---: |
| `P0-P3` | residual shared edge | `332` |
| `P1-P2` | residual shared edge | `329` |
| `P2-P3` | residual shared face | `1064` |
| **Total** |  | **`1725`** |

Failure patterns at refined-segment level:

| Pattern | Refined segments |
| --- | ---: |
| `P2-P3` | `714` |
| `P0-P3 + P1-P2 + P2-P3` | `311` |
| `P0-P3 + P2-P3` | `21` |
| `P1-P2 + P2-P3` | `18` |
| **Total failed segments** | **`1064`** |

Every failed `TREE_007` refined segment includes `P2-P3`.

### TREE_007 Residual Guards

| Evidence method | Pair-segments covered |
| --- | ---: |
| `tree007_shared_edge_common_edge_guard` | `661` |
| `tree007_p2p3_edge_branch_workflow` | `629` |
| `tree007_p2p3_face_normal_formula_guard` | `435` |
| **Total** | **`1725`** |

The shared-edge backlog is:

| Pair | Pair-segments |
| --- | ---: |
| `P0-P3` | `332` |
| `P1-P2` | `329` |
| **Total** | **`661`** |

The common-edge guard uses the stable separator:

```text
edge:M_AB-M_CD x M_AB-M_CD.
```

Its recorded subledger is:

| Metric | Value |
| --- | ---: |
| Direct common-edge certified | `443` |
| Adaptive completed | `true` |
| Adaptive leaf subsegments | `7550` |
| Adaptive certified leaf subsegments | `7550` |
| Adaptive uncovered leaf subsegments | `0` |

The `P2-P3` residual shared-face backlog splits as:

| Axis family | Pair-segments | Handling |
| --- | ---: | --- |
| `edge:B-M_AB x B-M_CD` | `317` | edge-branch workflow |
| `edge:B-M_CD x B-M_AB` | `312` | edge-branch workflow |
| `left_face:B-M_AB-M_CD` | `219` | face-normal formula guard |
| `right_face:B-M_AB-M_CD` | `216` | face-normal formula guard |

The two edge-edge branches give:

```text
317 + 312 = 629.
```

The two face-normal branches give:

```text
219 + 216 = 435.
```

The `TREE_007 P2-P3` edge-branch workflow records:

| Stage | Certified object |
| --- | ---: |
| Base edge-branch subsegments at `0.625` degrees | `5010` |
| Projected child coverage before endgame | `4463/4500` |
| Remaining children before targeted endgame | `37` |
| Adaptive endgame leaves | `1876/1876` |
| Uncovered endgame leaves | `0` |

The face-normal formula guard records:

| Metric | Value |
| --- | ---: |
| Input face-normal pair-segments | `435` |
| Formula-certified pair-segments | `435` |
| Uncovered pair-segments | `0` |
| Minimum raw-gap lower bound | `1.604e-09` |
| Minimum support lower bound | `1.4364e-07` |
| Maximum formula/direct-geometry error | `6.1e-17` |

### TREE_007 Closure

The closure overlay verifies:

| Metric | Value |
| --- | ---: |
| Original residual pair-segments | `1725` |
| Covered residual pair-segments | `1725` |
| Uncovered residual pair-segments | `0` |
| Original failed refined segments | `1064` |
| Fully closed failed refined segments | `1064` |
| Incomplete failed refined segments | `0` |

Therefore the final `TREE_007` refined-edge overlay records:

| Metric | Value |
| --- | ---: |
| Certified refined segments | `2528/2528` |
| Certified pair-segments | `15168/15168` |
| Uncertified refined segments | `0` |
| Uncertified pair-segments | `0` |

## Residual Ledger For TREE_021

The `TREE_021` residual-contact classification has:

| Pair | Role | Residual pair-segments |
| --- | --- | ---: |
| `P0-P2` | residual shared face | `1065` |
| `P0-P3` | residual shared edge | `329` |
| `P1-P2` | residual shared edge | `561` |
| **Total** |  | **`1955`** |

Failure patterns at refined-segment level:

| Pattern | Refined segments |
| --- | ---: |
| `P0-P2` | `501` |
| `P0-P2 + P0-P3 + P1-P2` | `326` |
| `P0-P2 + P1-P2` | `235` |
| `P0-P2 + P0-P3` | `3` |
| **Total failed segments** | **`1065`** |

Every failed `TREE_021` refined segment includes `P0-P2`.

### TREE_021 Residual Guards

| Evidence method | Pair-segments covered |
| --- | ---: |
| `tree021_shared_edge_common_edge_guard` | `890` |
| `p0p2_edge_branch_workflow` | `630` |
| `p0p2_face_normal_formula_guard` | `435` |
| **Total** | **`1955`** |

The shared-edge backlog is:

| Pair | Pair-segments |
| --- | ---: |
| `P0-P3` | `329` |
| `P1-P2` | `561` |
| **Total** | **`890`** |

The common-edge guard again uses:

```text
edge:M_AB-M_CD x M_AB-M_CD.
```

Its recorded subledger is:

| Metric | Value |
| --- | ---: |
| Direct common-edge certified | `430` |
| Adaptive completed | `true` |
| Adaptive leaf subsegments | `11850` |
| Adaptive certified leaf subsegments | `11850` |
| Adaptive uncovered leaf subsegments | `0` |

The `P0-P2` residual shared-face backlog splits as:

| Axis family | Pair-segments | Handling |
| --- | ---: | --- |
| `edge:M_AB-C x C-M_CD` | `316` | edge-branch workflow |
| `edge:C-M_CD x M_AB-C` | `314` | edge-branch workflow |
| `left_face:M_AB-C-M_CD` | `219` | face-normal formula guard |
| `right_face:M_AB-C-M_CD` | `216` | face-normal formula guard |

The two edge-edge branches give:

```text
316 + 314 = 630.
```

The two face-normal branches give:

```text
219 + 216 = 435.
```

The `TREE_021 P0-P2` edge-branch workflow records:

| Stage | Certified object |
| --- | ---: |
| Branch subsegments at `0.625` degrees | `5018` |
| Covered by initial branch lower bound | `3536` |
| Covered by same-branch support bound | `353` |
| Covered by same-branch refinement/theta/endgame base workflow | `1013` |
| Covered by axis-switch backlog guard | `116` |
| Coverage sum | `5018` |

The targeted endgame subledger inside the `1013` same-branch workflow records:

| Metric | Value |
| --- | ---: |
| Remaining children before targeted endgame | `53` |
| Adaptive endgame leaves | `1084/1084` |
| Uncovered endgame leaves | `0` |

The face-normal formula guard records:

| Metric | Value |
| --- | ---: |
| Input face-normal pair-segments | `435` |
| Formula-certified pair-segments | `435` |
| Uncovered pair-segments | `0` |
| Minimum raw-gap lower bound | `1.604e-09` |
| Minimum support lower bound | `1.4364e-07` |
| Maximum formula/direct-geometry error | `1.25e-16` |

### TREE_021 Closure

The closure overlay verifies:

| Metric | Value |
| --- | ---: |
| Original residual pair-segments | `1955` |
| Covered residual pair-segments | `1955` |
| Uncovered residual pair-segments | `0` |
| Original failed refined segments | `1065` |
| Fully closed failed refined segments | `1065` |
| Incomplete failed refined segments | `0` |

Therefore the final `TREE_021` refined-edge overlay records:

| Metric | Value |
| --- | ---: |
| Certified refined segments | `2528/2528` |
| Certified pair-segments | `15168/15168` |
| Uncertified refined segments | `0` |
| Uncertified pair-segments | `0` |

## Overlay Reconstruction Invariant

For each tree, the overlay reconstruction uses the same finite key invariant:

1. every refined segment has a stable segment ID `seg_XXXXX`;
2. every pair-segment is keyed by segment ID plus unordered pair key;
3. original interval-guard-certified pair-segments and residual-closure pair-segments are disjoint;
4. their union is the full `15168` pair-segment ledger;
5. failed refined segments are exactly the segments with at least one residual pair-segment;
6. residual closure covers every original residual pair-segment;
7. no residual key remains uncovered.

The reports record the following checks for both `TREE_007` and `TREE_021`:

| Check | `TREE_007` | `TREE_021` |
| --- | --- | --- |
| Segment IDs partition without overlap or gap | `true` | `true` |
| Residual segment count matches refined probe failed count | `true` | `true` |
| Original certified count matches refined probe | `true` | `true` |
| Residual closed count matches closure overlay | `true` | `true` |
| Residual pair count matches refined probe uncovered pair count | `true` | `true` |
| Combined pair-segment count matches total | `true` | `true` |
| All refined segments certified by overlay | `true` | `true` |
| All pair-segments certified by overlay | `true` | `true` |

## Lemma Statement

For the catalogued S4 zero-thickness model and the representative hinge trees `TREE_007` and `TREE_021`, the refined spanning-edge ledgers are finite-covered as follows:

1. each representative has `2528` refined BFS spanning-tree segments and `15168` associated pair-segments;
2. the original refined-edge interval guard certifies `1464` segments and `13443` pair-segments for `TREE_007`;
3. the original refined-edge interval guard certifies `1463` segments and `13213` pair-segments for `TREE_021`;
4. the remaining `TREE_007` residual ledger has `1725` pair-segments and is closed by `661` shared-edge common-edge records, `629` `P2-P3` edge-branch records, and `435` `P2-P3` face-normal records;
5. the remaining `TREE_021` residual ledger has `1955` pair-segments and is closed by `890` shared-edge common-edge records, `630` `P0-P2` edge-branch records, and `435` `P0-P2` face-normal records;
6. the overlay key checks certify that original interval-guard records and residual-closure records partition the complete pair-segment ledger for each representative.

Thus the finite refined-edge overlay coverage is:

| Tree | Refined segments | Pair-segments |
| --- | ---: | ---: |
| `TREE_007` | `2528/2528` | `15168/15168` |
| `TREE_021` | `2528/2528` | `15168/15168` |

## Proof Skeleton

The proof has three finite-ledger steps.

First, the refined-edge interval probe gives a finite partition of each representative's refined spanning-edge domain into interval-guard-certified segments and failed residual segments.

Second, the residual-contact classifiers reconstruct every failed pair-segment and classify it into one of the residual families listed above:

- common-edge residual shared-edge;
- residual shared-face edge-edge branch;
- residual shared-face face-normal branch.

Third, the closure overlays verify that each residual key is covered by exactly one completed evidence method and then recombine the original interval-guard ledger with the residual closure ledger.

The conclusion is a finite coverage statement over the recorded refined-edge keys. It becomes a mathematical non-overlap lemma only after the guard soundness and exactness blockers below are resolved.

## Explicit Non-Claims

This lemma does not prove:

- full continuous 3-parameter component coverage;
- every possible free graph edge segment;
- dynamic connectedness between `TREE_007` and `TREE_021`;
- positive clearance or strict separation at `theta = 0`;
- physical hingeability, hinge thickness, offsets, CAD, mesh validity, tolerances, or printability;
- CL5 theorem promotion.

## Exactness And Theorem-Promotion Blockers

Before theorem promotion, the following must be closed or explicitly demoted:

1. the original interval guard must be stated as a geometric separating-axis lemma with a rigorous interval displacement bound;
2. the common-edge projection-component guard must be proved to imply non-interpenetration over each terminal segment or leaf;
3. the residual shared-face edge-branch workflows must be rewritten as support-component inequalities, not only finite report counts;
4. the face-normal formula guards must include reviewer-readable derivations and support-extremality proofs for the recorded intervals;
5. adaptive replacement must be formalized as a parent-cover invariant: certified children cover the original parent residual key;
6. floating tolerances, safety factors, and formula-check errors must be separated from exact algebraic claims;
7. the final theorem wrapper must keep the refined-edge ledger separate from the bounded-cell ledger and the theta-zero closed-contact endpoint.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
