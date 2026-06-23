# S4 Lemma 09: Adaptive Subdivision And Overlay-Key Invariant

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-09-ADAPTIVE-SUBDIVISION-OVERLAY-INVARIANT-2026-06-21`
review status: finite-ledger lemma draft

## Purpose

This lemma records the shared finite-ledger invariant behind the adaptive
subdivision and overlay reports used by the S4 representative mechanisms:

```text
TREE_007, TREE_021.
```

The purpose is narrow.  It does not prove that any individual geometric guard
is sound.  It proves the ledger rule used by the written S4 lemmas:

```text
if every terminal child/leaf replacing a parent target is certified,
then the parent target is certified in the finite overlay ledger.
```

The same rule is used in:

1. refined-edge residual-contact overlays;
2. refined-edge interval-certificate overlays;
3. bounded-cell first-pass/fallback overlays;
4. bounded-cell adaptive shared-edge and edge-branch subledgers.

## Source Anchors

- `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`
- `docs/S4_LEMMA_06_NEAR_ZERO_BRIDGE_FORMULAS.md`
- `docs/S4_LEMMA_07_REFINED_EDGE_RESIDUAL_CLOSURE.md`
- `docs/S4_LEMMA_08_BOUNDED_CELL_FIRST_PASS_AND_FALLBACK_GUARDS.md`
- `results/historical_s4_median_planes/tree007_residual_contact_closure_overlay_report.json`
- `results/historical_s4_median_planes/tree021_residual_contact_closure_overlay_report.json`
- `results/historical_s4_median_planes/tree007_refined_edge_interval_certificate_overlay_report.json`
- `results/historical_s4_median_planes/tree021_refined_edge_interval_certificate_overlay_report.json`
- `results/historical_s4_median_planes/bounded_cell_closure_overlay_report.json`
- `docs/S4_TREE007_REFINED_EDGE_INTERVAL_CERTIFICATE_OVERLAY_SUMMARY.md`
- `docs/S4_TREE021_REFINED_EDGE_INTERVAL_CERTIFICATE_OVERLAY_SUMMARY.md`
- `docs/S4_TREE007_RESIDUAL_CONTACT_CLOSURE_OVERLAY_SUMMARY.md`
- `docs/S4_TREE021_RESIDUAL_CONTACT_CLOSURE_OVERLAY_SUMMARY.md`
- `docs/S4_BOUNDED_CELL_CLOSURE_OVERLAY_SUMMARY.md`

## Key Universes

The reports use concrete string keys.  For the mathematical ledger it is useful
to normalize them into parent keys and terminal child keys.

### Refined-Edge Parent Keys

For each representative tree, the refined spanning-edge ledger has:

```text
2528 refined segment keys.
```

A normalized parent segment key is:

```text
(tree_id, segment_id)
```

where examples in the report have `segment_id` values such as `seg_00000`.

Each segment has six unordered piece-pairs, so the normalized pair-segment key
is:

```text
(tree_id, segment_id, pair)
```

The refined-edge parent universe per representative is therefore:

```text
2528 segment keys
15168 pair-segment keys = 2528 * 6.
```

### Bounded-Cell Parent Keys

For the bounded-cell overlay, a normalized pair-cell key is:

```text
(tree_id, cell_id, pair)
```

The report serializes this as strings such as:

```text
TREE_007|P0-P1|theta00_radial00_dir00
```

where:

```text
tree_id = TREE_007
pair    = P0-P1
cell_id = theta00_radial00_dir00
```

The bounded-cell parent universe across both representatives is:

```text
1536 all-free bounded cells
9216 pair-cells = 1536 * 6.
```

The `96 + 96` blocked sampled-vertex cells are not in this parent universe.

### Terminal Child Keys

Adaptive reports refine a failed parent target into finitely many terminal
children or leaves.  Their local keys are internal to the source guard report.
Mathematically they have the normalized form:

```text
(parent_key, route_id, local_leaf_id)
```

or, for route-based edge-branch ledgers:

```text
(parent_key, route_id, subcell_id)
```

Terminal child keys are not added to the final parent universe.  They are a
certificate witness that the parent key is covered.

## Parent-Cover Invariant

Let `K` be a parent target, either:

```text
refined pair-segment, refined segment, bounded pair-cell, or bounded cell.
```

An adaptive ledger for `K` consists of a finite terminal family:

```text
children(K) = {K_1, ..., K_m}.
```

The ledger is parent-covering when the following three finite checks hold:

1. every child key records `K` as its parent;
2. the child parameter boxes/subsegments partition the audited part of `K`;
3. every terminal child is certified by one of the accepted guard routes.

Then the overlay may replace:

```text
K is directly certified
```

by:

```text
all terminal children of K are certified.
```

This replacement is only a ledger rule.  It depends on the separate geometric
soundness of the guard route assigned to each terminal child.

## Overlay-Key Invariant

The final overlay records coverage over parent keys, not over every internal
terminal child.

For a parent-key universe `U`, an overlay is valid when:

1. every `K in U` is assigned a status `covered` or `uncovered`;
2. no covered parent key is counted twice in incompatible parent sources;
3. if multiple terminal certificates replace one parent key, they are folded
   back under the same parent key;
4. the final uncovered set is empty;
5. reconstructing the covered and uncovered sets gives exactly `U`.

The invariant permits one parent key to have many terminal child certificates,
but the final ledger count is still one parent key.

## Refined-Edge Overlay Ledger

For each representative tree, the refined-edge interval-certificate overlay
reconstructs:

```text
2528 refined segment keys
15168 pair-segment keys.
```

### TREE_007

The `TREE_007` refined-edge overlay records:

| Metric | Value |
| --- | ---: |
| Refined segment count | `2528` |
| Original interval-guard certified segments | `1464` |
| Residual-contact closure segments | `1064` |
| Certified refined segments | `2528` |
| Uncertified refined segments | `0` |
| Total pair-segments | `15168` |
| Original probe covered pair-segments | `13443` |
| Residual closure pair-segments | `1725` |
| Combined certified pair-segments | `15168` |
| Uncertified pair-segments | `0` |

The residual-contact overlay records:

| Metric | Value |
| --- | ---: |
| Original residual pair-segments | `1725` |
| Covered residual pair-segments | `1725` |
| Uncovered residual pair-segments | `0` |
| Original failed refined segments | `1064` |
| Fully closed failed refined segments | `1064` |
| Incomplete failed refined segments | `0` |

Its adaptive/shared-edge witness includes:

```text
7550/7550 adaptive leaf subsegments certified.
```

The final parent-level consequence is:

```text
TREE_007 refined segments: 2528/2528
TREE_007 pair-segments:    15168/15168.
```

### TREE_021

The `TREE_021` refined-edge overlay records:

| Metric | Value |
| --- | ---: |
| Refined segment count | `2528` |
| Original interval-guard certified segments | `1463` |
| Residual-contact closure segments | `1065` |
| Certified refined segments | `2528` |
| Uncertified refined segments | `0` |
| Total pair-segments | `15168` |
| Original probe covered pair-segments | `13213` |
| Residual closure pair-segments | `1955` |
| Combined certified pair-segments | `15168` |
| Uncertified pair-segments | `0` |

The residual-contact overlay records:

| Metric | Value |
| --- | ---: |
| Original residual pair-segments | `1955` |
| Covered residual pair-segments | `1955` |
| Uncovered residual pair-segments | `0` |
| Original failed refined segments | `1065` |
| Fully closed failed refined segments | `1065` |
| Incomplete failed refined segments | `0` |

Its adaptive/shared-edge witness includes:

```text
11850/11850 adaptive leaf subsegments certified.
```

The final parent-level consequence is:

```text
TREE_021 refined segments: 2528/2528
TREE_021 pair-segments:    15168/15168.
```

## Bounded-Cell Overlay Ledger

The bounded-cell overlay reconstructs the all-free bounded-cell universe:

```text
1536 all-free bounded cells
9216 pair-cells.
```

Its summary metrics record:

| Metric | Value |
| --- | ---: |
| Tree count | `2` |
| Candidate all-free cells | `1536` |
| Center-sample collision-free cells | `1536` |
| Original pair-cells | `9216` |
| First-pass covered pair-cells | `5421` |
| Fallback covered pair-cells | `3795` |
| Final covered pair-cells | `9216` |
| Final uncovered pair-cells | `0` |
| Final fully covered cells | `1536` |
| Final uncovered cells | `0` |

The fallback partition is:

| Fallback route | Parent pair-cells |
| --- | ---: |
| Shared-edge fallback closures | `2528` |
| Shared-face face-normal formula guard | `544` |
| Shared-face edge-branch `G1`-`G4` guards | `723` |
| **Total** | **`3795`** |

The arithmetic identity is:

```text
5421 + 3795 = 9216.
```

The adaptive terminal witnesses include:

| Source | Parent pair-cells | Terminal evidence |
| --- | ---: | ---: |
| `TREE_021 P1-P2` shared-edge closure | `768` | `6156/6156` terminal elements |
| `TREE_021 P0-P3` shared-edge closure | `592` | `964/964` terminal elements |
| `TREE_007 P0-P3` and `P1-P2` shared-edge closure | `1168` | `1918/1918` terminal elements |
| Edge-branch `G1`-`G4` routes | `723` | `46272/46272` subcells |

The final parent-level consequence is:

```text
bounded all-free cells: 1536/1536
bounded pair-cells:     9216/9216.
```

## Lemma Statement

For the recorded S4 representative ledgers, assume:

1. the parent key universes are the finite refined-edge and bounded-cell
   universes stated above;
2. every direct parent certificate listed in the source reports is sound for
   its parent key;
3. every adaptive terminal certificate is sound for its terminal child;
4. every adaptive child family partitions the audited part of its parent key;
5. every overlay reconstruction check holds.

Then:

1. `TREE_007` and `TREE_021` refined-edge overlays cover all `2528/2528`
   refined segments and all `15168/15168` pair-segments per representative;
2. the bounded-cell overlay covers all `1536/1536` all-free bounded cells and
   all `9216/9216` pair-cells across the two representatives;
3. no terminal child key expands the final claim scope beyond its parent
   refined segment, pair-segment, bounded cell, or pair-cell.

## Proof Skeleton

First, fix the parent universe `U` from the source report.  For refined edges,
`U` is the `2528` segment ledger, or the induced `15168` pair-segment ledger,
for one representative tree.  For bounded cells, `U` is the `1536` all-free
cell ledger, or the induced `9216` pair-cell ledger, across both trees.

Second, partition `U` into direct and residual keys:

```text
U = U_direct union U_residual.
```

The refined-edge overlays use:

```text
TREE_007: 1464 direct segment keys + 1064 residual segment keys = 2528.
TREE_021: 1463 direct segment keys + 1065 residual segment keys = 2528.
```

The bounded-cell overlay uses:

```text
5421 first-pass pair-cells + 3795 fallback pair-cells = 9216.
```

Third, for each residual parent key, use either a direct fallback guard or an
adaptive replacement ledger.  In the adaptive case, certify all terminal
children and fold the result back to the parent key.

Fourth, use the overlay reconstruction checks.  The reports record zero final
uncovered refined pair-segments and zero final uncovered bounded pair-cells.
Therefore every parent key in the audited universe is covered.

Fifth, the terminal children do not enlarge the theorem domain.  They are
witness keys below an already existing parent target; after certification they
are counted only through the parent key.

## Explicit Non-Claims

This lemma does not claim:

- guard soundness for clearance, selected-hinge orientation, common-edge,
  face-normal, edge-branch, support-stability, or margin guards;
- exact arithmetic soundness for floating or tolerance-dependent predicates;
- coverage of `theta = 0` positive clearance;
- coverage of bounded cells with blocked sampled vertices;
- coverage of a full continuous 3-parameter component outside the audited
  finite ledgers;
- dynamic connectedness of `TREE_007` and `TREE_021`;
- physical hingeability, hinge thickness, CAD validity, or printability;
- theorem-level promotion.

## Remaining Blockers

Before theorem wrapping, the following blockers remain:

1. each geometric guard route must be proved sound on its certified parent or
   terminal child keys;
2. formula-derived guards must have their exact algebraic or interval-support
   boundary stated separately;
3. tolerance-dependent floating predicates must be isolated from exact
   coordinate and finite-ledger claims;
4. the final theorem wrapper must preserve the parent-key scope recorded here.

## Conclusion

This lemma closes the overlay-key and adaptive-parent accounting gap in the S4
finite ledger stack.  It says that adaptive child certificates can be used to
certify their parent keys, and that the refined-edge and bounded-cell overlays
reconstruct exactly their original audited parent universes.

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
