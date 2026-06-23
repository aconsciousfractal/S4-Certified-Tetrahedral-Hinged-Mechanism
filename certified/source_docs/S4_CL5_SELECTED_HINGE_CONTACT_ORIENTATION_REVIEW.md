> **Package provenance note.** This is a historical or future-scope source
> snapshot retained for audit trail only. It may contain words such as
> `draft`, `blocker`, or `Not a CL5 theorem`; those statements are not public
> claims of the current paper-as-public-package and do not widen the scoped
> zero-thickness theorem.

# S4 CL5 Selected-Hinge Contact Orientation Review

Date: 2026-06-21
Case: `historical_s4_median_planes`
Review id: `S4-CL5-SELECTED-HINGE-CONTACT-ORIENTATION-REVIEW-2026-06-21`
Status: contact-orientation review and proof-obligation support. Not a
proof. Not an exact/interval implementation. Not a theorem promotion.

## Template Basis

This document instantiates the local local development templates under:

```text
the local development template used during preparation
```

Template sections used:

1. `CLAIM_LEDGER.md`: claim level, blocked claims, and promotion boundary;
2. `PROOF_OBLIGATIONS.md`: selected-hinge proof obligations and
   non-obligations;
3. `PUBLIC_CLAIM_BOUNDARY.md`: can-say / must-not-say wording;
4. `NORMALIZATION_LOCK.md`: Lemma 00 labels, domains, and endpoint semantics;
5. `SOURCE_LOCK.md`: script, report, and lemma sources used by this review;
6. `PAPER_TO_ENGINE_TRACEABILITY.md`: orientation predicate to report fields;
7. `README_REVIEWER.md`: reviewer path and known limits.

This S4 instantiation keeps the review structure but uses ASCII only.

## Purpose

This review states the selected-hinge contact-orientation predicate required
for zero-thickness S4 contact pairs that are intentionally not separated by
positive SAT clearance.

It follows:

1. `docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`;
2. `docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`;
3. `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`;
4. `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`;
5. `docs/S4_LEMMA_06_NEAR_ZERO_BRIDGE_FORMULAS.md`;
6. `docs/S4_LEMMA_08_BOUNDED_CELL_FIRST_PASS_AND_FALLBACK_GUARDS.md`;
7. `docs/S4_LEMMA_10_ARITHMETIC_AND_EXACTNESS_BOUNDARY.md`;
8. `docs/S4_CL5_STRICT_CONVEX_SAT_SOUNDNESS_REVIEW.md`.

The review does not prove that the current selected-hinge orientation reports
are exact. It defines what must be proved before selected-hinge orientation can
be promoted toward CL5.

## Decision

```text
B04_SELECTED_HINGE_CONTACT_ORIENTATION_IS_REVIEWED_NOT_PROVED.
SELECTED_HINGE_CONTACTS_ARE_ZERO_MARGIN_BOUNDARY_CONTACTS_NOT_SAT_CLEARANCE.
HINGE_AXIS_PRESERVATION_COMES_FROM_THE_ROOTED_KINEMATIC_MODEL.
CONSTANT_NONZERO_SIGNED_ANGLE_IN_AN_OPEN_HALF_TURN_IS_THE_ORIENTATION_GUARD.
CURRENT_RAY_AND_BOUNDED_ORIENTATION_REPORTS_REMAIN_FINITE_EVIDENCE.
EXACT_INTERVAL_SIGN_AND_BRANCH_STABILITY_REPORTS_ARE_REQUIRED_FOR_CL5.
B05_THROUGH_B08_REMAIN_OPEN.
PHYSICAL_BRANCH_REMAINS_BLOCKED.
```

## Claim Level

This document uses the package-local claim level:

```text
CONTACT_ORIENTATION_REVIEW
```

meaning:

```text
A selected-hinge contact-orientation predicate and proof-obligation review;
not an exact contact proof or theorem proof.
```

It is not `CL5_internal_theorem`.

## Source Lock

Allowed internal sources:

1. Lemma 00 through Lemma 11;
2. `docs/S4_CL5_EXACT_INTERVAL_ARITHMETIC_POLICY.md`;
3. `docs/S4_CL5_FORMULA_DERIVATION_REVIEW.md`;
4. `docs/S4_CL5_STRICT_CONVEX_SAT_SOUNDNESS_REVIEW.md`;
5. `docs/S4_TWO_CLASS_CONTACT_ORIENTATION_SUMMARY.md`;
6. `docs/S4_BOUNDED_CELL_GUARD_FIRST_PASS_SUMMARY.md`;
7. `scripts/audit_historical_s4_two_class_contact_orientation.py`;
8. `scripts/audit_historical_s4_bounded_cell_guard_first_pass.py`;
9. `results/historical_s4_median_planes/two_class_contact_orientation_report.json`;
10. `results/historical_s4_median_planes/bounded_cell_guard_first_pass_report.json`;
11. `registry/claim_register.yaml`.

Source risks tracked here:

1. treating selected hinge pairs as positive-clearance SAT pairs;
2. treating a finite signed-angle interval test as an exact proof;
3. treating midpoint collision-freedom as full-cell collision-freedom;
4. failing to prove that the chosen signed direction is the opening side;
5. failing to prove branch stability for bounded-cell hinge coordinates;
6. confusing the endpoint `theta_deg = 0` with open positive-angle cells;
7. importing physical hinge thickness or offsets into the zero-thickness claim.

## Semantics Boundary

Selected hinge contacts deliberately keep a zero-clearance set.

At the closed endpoint:

```text
theta_deg = 0
```

the selected pairs share a closed face contact. This is handled by Lemma 02 and
the theta-zero closed-contact certificate.

For positive-angle ray and bounded cells, the selected pair is not expected to
have positive separating-axis margin. The intended statement is instead:

```text
the two selected pieces remain joined along the selected hinge axis, and the
relative rotation opens the original shared face to the allowed side, so the
pair has no strict interior overlap from that contact route.
```

This is a boundary-contact predicate, not a clearance predicate.

## Selected Hinge Contacts

Lemma 00 fixes four ambient-edge subsegment hinges:

| Hinge ID | Pair | Contact | Oriented axis | Ambient support |
| --- | --- | --- | --- | --- |
| `H0_A_M_AB` | `P0-P1` | `C0` | `A -> M_AB` | `AB` |
| `H4_C_M_CD` | `P0-P2` | `C1` | `C -> M_CD` | `CD` |
| `H7_D_M_CD` | `P1-P3` | `C4` | `D -> M_CD` | `CD` |
| `H9_B_M_AB` | `P2-P3` | `C5` | `B -> M_AB` | `AB` |

The representative trees select:

| Tree | Selected pairs | Hinge IDs | Signed-ray signs |
| --- | --- | --- | --- |
| `TREE_007` | `P0-P1`, `P0-P2`, `P1-P3` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `+1`, `+1`, `-1` |
| `TREE_021` | `P0-P1`, `P1-P3`, `P2-P3` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `+1`, `-1`, `+1` |

These are the only pairs routed to B04 in the current two-representative
package.

## Exact Orientation Predicate

Let `h` be a selected hinge joining pieces `Pi` and `Pj`. Let `L_h` be its
closed-endpoint hinge line segment, with oriented endpoints from Lemma 00. Let
`d_h(q)` be the signed hinge angle in degrees at configuration parameter `q`.

For a cell `C`, define:

```text
D_h(C) = { d_h(q) : q in C }.
```

The selected-hinge orientation predicate for `C` is:

```text
HINGE_ORIENTED(h, C)
```

when all of the following hold:

1. `h` is the selected hinge for the unordered pair `Pi-Pj`;
2. the rooted kinematic model is well-defined for every `q in C`;
3. `F_i(q)` and `F_j(q)` agree on every point of `L_h`;
4. `0 notin D_h(C)`;
5. `D_h(C)` lies in one open half-turn:

```text
D_h(C) subset (0, 180) or D_h(C) subset (-180, 0);
```

6. the sign of `D_h(C)` is the package-approved opening side for the source
   contact face;
7. the local contact-side lemma proves that this opening side gives boundary
   hinge contact and no strict interior overlap for `Pi-Pj`.

Current finite reports implement only the computable proxy:

```text
center sample is collision_free
signed angle interval excludes 0
signed angle interval stays inside an open half-turn
```

That proxy is useful evidence, but the exact predicate above is the CL5 target.

## Boundary Contact Versus Positive Clearance

For a selected hinge pair, the following are intentionally different:

| Predicate | Meaning | Applies to selected hinges? |
| --- | --- | --- |
| positive SAT clearance | a nonzero separating margin exists for the whole pair | no |
| boundary hinge contact | the pieces share the hinge axis while opening to the correct side | yes |
| strict interior non-overlap | no common 3D interior point exists | target conclusion |

The selected hinge axis is fixed by both adjacent pieces. Therefore a
clearance-only SAT report should not be expected to certify these pairs.

This is why R13 routes selected hinge contacts out of B03 and into B04.

## Current Ray-Cell Orientation Overlay

Source:

```text
scripts/audit_historical_s4_two_class_contact_orientation.py
results/historical_s4_median_planes/two_class_contact_orientation_report.json
docs/S4_TWO_CLASS_CONTACT_ORIENTATION_SUMMARY.md
```

Domain:

```text
0.5 <= theta_deg <= 120
cell width = 0.25 degrees
478 ray cells per representative
```

Script-level rule:

```text
certified =
  center_sample_status == "collision_free"
  and signed_angle_interval excludes 0
  and signed_angle_interval is inside an open half-turn
```

Ray-cell selected-hinge metrics:

| Tree | Selected hinge pair-cells | Orientation-certified | Uncovered selected hinge pair-cells |
| --- | ---: | ---: | ---: |
| `TREE_007` | `1434` | `1434` | `0` |
| `TREE_021` | `1434` | `1434` | `0` |

Composite ray-cell metrics after adding clearance guards:

| Tree | Covered pair-cells | Total pair-cells | Fully covered cells | Total cells |
| --- | ---: | ---: | ---: | ---: |
| `TREE_007` | `2807` | `2868` | `417` | `478` |
| `TREE_021` | `2805` | `2868` | `417` | `478` |

Global report flags:

```text
all_center_samples_collision_free = true
all_selected_hinge_contacts_orientation_certified = true
all_cells_fully_composite_certified = false
```

Review status:

```text
FINITE_SELECTED_HINGE_ORIENTATION_EVIDENCE.
NOT AN EXACT_INTERVAL_CONTACT_PROOF.
SELECTED_HINGE_ZERO_MARGIN_ROUTE_IS CORRECTLY SEPARATED FROM SAT CLEARANCE.
RESIDUAL CONTACTS REMAIN OUTSIDE B04.
```

## Current Bounded-Cell Selected-Hinge Guard

Source:

```text
scripts/audit_historical_s4_bounded_cell_guard_first_pass.py
results/historical_s4_median_planes/bounded_cell_guard_first_pass_report.json
docs/S4_BOUNDED_CELL_GUARD_FIRST_PASS_SUMMARY.md
```

Domain:

```text
1536 all-vertices-free bounded cells
9216 pair-cells
```

The bounded first pass computes a conservative hinge-coordinate interval for
each full cell and applies:

```text
selected hinge angle interval must exclude zero
selected hinge angle interval must stay within an open half-turn
center sample must be collision-free
```

Bounded-cell selected-hinge metrics:

| Tree | Selected pairs | Cells per selected pair | Covered selected-hinge pair-cells |
| --- | ---: | ---: | ---: |
| `TREE_007` | `3` | `768` | `2304/2304` |
| `TREE_021` | `3` | `768` | `2304/2304` |

The full first pass is not complete:

| Metric | Value |
| --- | ---: |
| Candidate cells | `1536` |
| Center samples collision-free | `1536` |
| First-pass fully covered cells | `173` |
| First-pass covered pair-cells | `5421/9216` |
| Bounded cell-cover certificate completed by first pass | `false` |

The selected-hinge part is not the obstruction. The uncovered front comes from
residual shared-edge and residual shared-face pair-cells, which route to B05
through B08.

Review status:

```text
FINITE_BOUNDED_SELECTED_HINGE_ORIENTATION_EVIDENCE.
NOT AN EXACT_INTERVAL_CONTACT_PROOF.
BOUNDED FIRST PASS STILL DOES NOT PROMOTE THE THEOREM WRAPPER.
```

## Exact/Interval Replacement Shape

For a future B04 exact/interval report, each selected-hinge pair-cell must
record:

```yaml
policy_id: S4-CL5-EXACT-INTERVAL-ARITHMETIC-POLICY-2026-06-21
predicate_id: B04_SELECTED_HINGE_CONTACT_ORIENTATION
domain_key: ""
tree_id: ""
pair: ""
hinge_id: ""
source_contact: ""
axis:
  endpoint_labels: []
  exact_endpoint_coordinates: []
  nonzero_length_proof: ""
kinematics:
  parent_piece: ""
  child_piece: ""
  rooted_path_parent: []
  rooted_path_child: []
  axis_preservation_reference: S4-LEMMA-03-KINEMATICS-SIGNS-2026-06-21
signed_angle_interval_degrees:
  lo: null
  hi: null
angle_sign_status: positive | negative
open_half_turn_status: inside_open_half_turn
opening_side_status: proved_opening_side
contact_side_lemma: ""
accepted: false
```

The accepted condition should be:

```text
0 < signed_angle_interval.lo
and signed_angle_interval.hi < 180
```

or:

```text
-180 < signed_angle_interval.lo
and signed_angle_interval.hi < 0
```

plus a proof that the recorded sign is the correct opening side for the source
contact.

If a bounded cell has an interval that touches zero or crosses a sign branch,
the report must subdivide it or route it to:

```text
selected_hinge_orientation_subdivision_if_interval_touches_zero
```

## B04 Proof Obligations

| Obligation | Required statement | Current status |
| --- | --- | --- |
| `B04-O1` selected inventory | exact selected pairs, hinge IDs, axis endpoints, and source contacts match Lemma 00 | reviewed here, proof open |
| `B04-O2` axis preservation | parent and child transforms agree on the selected hinge axis for every cell configuration | Lemma 03 draft exists; CL5 proof open |
| `B04-O3` source contact geometry | each selected hinge axis lies in the closed source face contact and has nonzero length | Lemma 00/02 draft support; proof open |
| `B04-O4` opening-side sign | the listed signed-ray signs are outward/opening for the corresponding source contact | open |
| `B04-O5` half-turn branch | `|d_h| < 180` keeps the relative rotation on one contact-orientation branch | open |
| `B04-O6` exact interval sign | ray and bounded cells provide outward-rounded signed-angle intervals excluding zero | open |
| `B04-O7` bounded branch stability | bounded-cell hinge-coordinate intervals enclose the full cell and do not miss transverse offsets | open |
| `B04-O8` strict-overlap implication | boundary hinge contact plus opening-side orientation implies no strict interior overlap for the selected pair | open |
| `B04-O9` ledger mapping | every exact/interval B04 row maps back to ray or bounded pair-cell keys | open |
| `B04-O10` route boundary | residual shared-edge/shared-face contacts are excluded from B04 and routed to B05-B08 | reviewed here, proof open |

## Non-Obligations For B04

B04 does not need to prove:

1. positive SAT clearance for selected hinge pairs;
2. strict-convex SAT soundness for non-hinge pairs; route to B03;
3. residual shared-edge common-edge projection soundness; route to B05;
4. residual shared-face face-normal support-gap soundness; route to B06;
5. G1-G4 edge-branch support-component soundness; route to B07;
6. adaptive overlay reconstruction soundness; route to B08;
7. endpoint positive clearance at `theta_deg = 0`;
8. dynamic connectedness between `TREE_007` and `TREE_021`;
9. physical hinge offsets, thickness, mesh export, or printability.

## Paper-To-Engine Traceability

| Predicate family | Script source | Report source | Review result |
| --- | --- | --- | --- |
| Ray selected-hinge orientation | `audit_historical_s4_two_class_contact_orientation.py` | `two_class_contact_orientation_report.json` | finite evidence; needs exact/interval B04 |
| Bounded selected-hinge orientation | `audit_historical_s4_bounded_cell_guard_first_pass.py` | `bounded_cell_guard_first_pass_report.json` | finite evidence; needs exact/interval B04 |
| Kinematic hinge-axis preservation | `mechanical_audit_lib.py`, Lemma 03 | hinge-tree reports | exact model draft; needs CL5 proof text |
| SAT clearance for non-hinge pairs | SAT guard scripts | SAT reports | route to B03 |
| Residual shared-edge contacts | shared-edge closure scripts | shared-edge reports | route to B05 |
| Residual shared-face contacts | face-normal and edge-branch scripts | residual reports | route to B06-B07 |

## Public Claim Boundary

Can say inside the package:

```text
The S4 package now has a selected-hinge contact-orientation review. It states
the exact predicate needed for zero-margin hinge contacts and separates that
predicate from positive-clearance SAT.
```

Can say internally:

```text
The finite ray and bounded-cell orientation overlays cover every selected
hinge-contact pair-cell in the audited representatives, but CL5 promotion
requires exact signed-angle intervals and a proof that the recorded signs are
the opening side.
```

Must not say:

```text
The selected-hinge orientation reports are exact/interval proofs.
Selected hinge pairs have positive clearance.
B04 is proved.
Residual shared-edge or shared-face contacts are handled by B04.
Any guard is promoted to CL5.
The theorem wrapper is promoted.
The physical branch is open.
```

## Explicit Nonclaims

This review does not prove:

1. exact/interval selected-hinge contact-orientation soundness;
2. exact/interval SAT soundness;
3. common-edge projection soundness;
4. face-normal support-gap soundness;
5. edge-branch support-component soundness;
6. adaptive overlay soundness;
7. dynamic connectedness between `TREE_007` and `TREE_021`;
8. positive clearance at `theta_deg = 0`;
9. global S4 hingeability;
10. physical hingeability, hinge thickness, CAD validity, or printability.

## Decision

```text
B04 selected-hinge contact orientation is reviewed as a review
proof-obligation artifact.
The exact predicate is hinge-axis preservation plus constant nonzero
opening-side signed angle inside one open half-turn.
The current ray-cell and bounded-cell orientation reports remain finite
evidence.
Selected hinge contacts are boundary contacts, not positive-clearance SAT
pairs.
Exact/interval promotion requires signed-angle interval rows, opening-side
proofs, and branch-stability reconstruction.
B05 through B08 remain open.
The theorem wrapper remains non-promoted.
The physical branch remains blocked.
```

## Next Artifact

```text
docs/S4_CL5_COMMON_EDGE_PROJECTION_SOUNDNESS_REVIEW.md
```

Required contents:

1. state the exact common-edge projection predicate for residual shared-edge
   contacts;
2. distinguish common-edge endpoint/contact preservation from positive SAT
   clearance;
3. review the TREE_007 and TREE_021 shared-edge closure stacks;
4. state exact/interval projection, sign, and branch-stability obligations for
   B05;
5. keep residual shared-face and edge-branch routes assigned to B06 and B07.

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
