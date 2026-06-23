> **Package provenance note.** This is a historical or future-scope source
> snapshot retained for audit trail only. It may contain words such as
> `draft`, `blocker`, or `Not a CL5 theorem`; those statements are not public
> claims of the current paper-as-public-package and do not widen the scoped
> zero-thickness theorem.

# S4 CL5 Selected-Hinge Contact Orientation Exact Report Implementation Plan

Date: 2026-06-21
Case: `historical_s4_median_planes`
Plan id: `S4-CL5-SELECTED-HINGE-CONTACT-ORIENTATION-EXACT-REPORT-IMPLEMENTATION-PLAN-2026-06-21`
Status: B04 selected-hinge contact-orientation exact-report
implementation plan. Not a report generator. Not a replay checker
implementation. Not an exact contact proof. Not a theorem promotion.

## Template Basis

This document instantiates the local local development templates under:

```text
the local development template used during preparation
```

Template sections used:

1. `CLAIM_LEDGER.md`: claim level, planned B04 implementation claim, and
   blocked theorem boundary;
2. `PROOF_OBLIGATIONS.md`: B04 exact-report obligations and non-obligations;
3. `PUBLIC_CLAIM_BOUNDARY.md`: can-say / must-not-say wording;
4. `NORMALIZATION_LOCK.md`: selected hinge IDs, contact IDs, axis labels,
   tree IDs, signs, and endpoint semantics;
5. `SOURCE_LOCK.md`: B04 review, R21 backend/schema lock, and finite
   selected-hinge orientation report sources;
6. `PAPER_TO_ENGINE_TRACEABILITY.md`: B04 report-to-schema mapping and
   replay fixture plan;
7. `README_REVIEWER.md`: reviewer path for future B04 generator work.

This S4 instantiation keeps the review structure but uses ASCII only.

## Purpose

R23 instantiates the locked exact/interval report schema for:

```text
B04_SELECTED_HINGE_CONTACT_ORIENTATION
```

It defines how future selected-hinge contact-orientation reports should be
generated, which selected hinge contacts they may target, what signed-angle
and opening-side fields they must emit, which exact backends are allowed, and
which fixture classes are required before any accepted B04 report can be
trusted.

R23 does not implement the generator or checker. It is the implementation
contract for future B04 generator/checker work.

## Decision

```text
R23_SELECTED_HINGE_CONTACT_ORIENTATION_EXACT_REPORT_IMPLEMENTATION_PLAN_IS_WRITTEN.
B04_REPORTS_MUST_TARGET_SCHEMA_S4_CL5_EXACT_INTERVAL_REPORT_SCHEMA_V1.
B04_REPORTS_MUST_USE_FRACTION_INTERVAL_V1_OR_SYMBOLIC_SIGN_V1_ONLY.
B04_CERTIFIES_BOUNDARY_CONTACT_ORIENTATION_NOT_POSITIVE_CLEARANCE.
B04_SELECTED_HINGE_PAIRS_ARE_EXCLUDED_FROM_B03_CLEARANCE_SAT.
RESIDUAL_COMMON_EDGE_FACE_NORMAL_AND_EDGE_BRANCH_CONTACTS_ROUTE_TO_B05_B06_B07.
NO_B04_ACCEPTED_TRUE_REPORTS_UNTIL_THE_REPLAY_CHECKER_EXISTS.
THEOREM_WRAPPER_REMAINS_NON_PROMOTED.
PHYSICAL_BRANCH_REMAINS_BLOCKED.
```

Rejected outcome:

```text
TREAT_FINITE_SIGNED_ANGLE_OVERLAYS_AS_EXACT_B04_REPORTS
TREAT_SELECTED_HINGES_AS_POSITIVE_CLEARANCE_SAT_CASES
```

## Claim Level

This document uses the package-local claim level:

```text
SELECTED_HINGE_CONTACT_ORIENTATION_EXACT_REPORT_IMPLEMENTATION_PLAN
```

meaning:

```text
An implementation plan for B04 selected-hinge contact-orientation
exact/interval reports; not a B04 exact report, replay-check implementation,
contact proof, or theorem proof.
```

## Source Lock

Allowed internal sources:

1. `docs/S4_CL5_SELECTED_HINGE_CONTACT_ORIENTATION_REVIEW.md`;
2. `docs/S4_CL5_EXACT_INTERVAL_BACKEND_AND_SCHEMA_LOCK.md`;
3. `schemas/s4_cl5_exact_interval_report_schema_v1.yaml`;
4. `docs/S4_CL5_EXACT_INTERVAL_REPORT_IMPLEMENTATION_PLAN.md`;
5. `docs/S4_CL5_EXACT_INTERVAL_ARITHMETIC_POLICY.md`;
6. `docs/S4_CL5_STRICT_CONVEX_SAT_EXACT_REPORT_IMPLEMENTATION_PLAN.md`;
7. `docs/S4_CL5_STRICT_CONVEX_SAT_SOUNDNESS_REVIEW.md`;
8. `docs/S4_CL5_COMMON_EDGE_PROJECTION_SOUNDNESS_REVIEW.md`;
9. `docs/S4_CL5_FACE_NORMAL_SUPPORT_GAP_SOUNDNESS_REVIEW.md`;
10. `docs/S4_CL5_EDGE_BRANCH_SUPPORT_COMPONENT_SOUNDNESS_REVIEW.md`;
11. `docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`;
12. `docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`;
13. `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`;
14. `docs/S4_TWO_CLASS_CONTACT_ORIENTATION_SUMMARY.md`;
15. `docs/S4_BOUNDED_CELL_GUARD_FIRST_PASS_SUMMARY.md`;
16. `scripts/audit_historical_s4_two_class_contact_orientation.py`;
17. `scripts/audit_historical_s4_bounded_cell_guard_first_pass.py`;
18. `results/historical_s4_median_planes/two_class_contact_orientation_report.json`;
19. `results/historical_s4_median_planes/bounded_cell_guard_first_pass_report.json`;
20. `registry/claim_register.yaml`.

Rejected premises:

1. finite signed-angle overlays as exact interval proofs;
2. center-sample collision freedom as a full-cell contact proof;
3. selected hinge contacts as positive-clearance SAT cases;
4. opening-side signs inferred from sampled visual motion only;
5. signed-angle branches accepted when the interval touches zero or crosses an
   open half-turn boundary;
6. unaudited `numpy`/`scipy`/`sympy.evalf`/`mpmath` angle values in accepted
   proof fields;
7. physical hinge thickness, offsets, CAD validity, or printability as support
   for the zero-thickness B04 predicate.

## B04 Scope

B04 is only the selected-hinge boundary-contact orientation route.

It may target:

1. ray-cell selected-hinge pair-cells from the two-class contact-orientation
   overlay;
2. bounded-cell selected-hinge pair-cells from the bounded first-pass selected
   hinge guard;
3. synthetic fixtures used to develop the future B04 replay checker.

B04 must not target:

1. positive-clearance non-hinge SAT pair-cells; route to B03;
2. residual shared-edge common-edge cases; route to B05;
3. residual shared-face face-normal cases; route to B06;
4. residual shared-face edge-branch cases; route to B07;
5. adaptive parent/child reconstruction; route to B08;
6. endpoint positive-clearance claims at `theta_deg = 0`; handled only by
   Lemma 02 and the theta-zero closed-contact boundary.

## Selected Hinge Inventory

The B04 generator must reject any selected-hinge report whose `hinge_id`,
`pair_key`, `contact_id`, or oriented axis does not match this inventory.

| Hinge ID | Pair | Contact | Oriented axis | Ambient support |
| --- | --- | --- | --- | --- |
| `H0_A_M_AB` | `P0-P1` | `C0` | `A -> M_AB` | `AB` |
| `H4_C_M_CD` | `P0-P2` | `C1` | `C -> M_CD` | `CD` |
| `H7_D_M_CD` | `P1-P3` | `C4` | `D -> M_CD` | `CD` |
| `H9_B_M_AB` | `P2-P3` | `C5` | `B -> M_AB` | `AB` |

The current two-representative package selects:

| Tree | Selected pairs | Hinge IDs | Signed-ray signs |
| --- | --- | --- | --- |
| `TREE_007` | `P0-P1`, `P0-P2`, `P1-P3` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `+1`, `+1`, `-1` |
| `TREE_021` | `P0-P1`, `P1-P3`, `P2-P3` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `+1`, `-1`, `+1` |

These are the only pair routes admitted by B04 in the current S4 package.

## Orientation Predicate Shape

For a selected hinge `h` joining pieces `Pi` and `Pj`, let `L_h` be its
closed-endpoint hinge line segment with oriented endpoints from Lemma 00. Let
`d_h(q)` be the signed hinge angle in degrees at configuration parameter `q`.

For a reported cell or segment `C`, the report must enclose:

```text
D_h(C) = { d_h(q) : q in C }.
```

The B04 report is accepted only if the replay checker proves all of the
following:

1. `h` is the selected hinge for the unordered pair `Pi-Pj`;
2. the rooted kinematic model is well-defined on the reported domain;
3. the two piece transforms preserve the same hinge axis `L_h`;
4. `D_h(C)` excludes zero;
5. `D_h(C)` lies inside one open half-turn:

```text
D_h(C) subset (0, 180)
```

or:

```text
D_h(C) subset (-180, 0);
```

6. the sign of `D_h(C)` matches the package-approved opening side for the
   source contact;
7. the boundary-contact certificate proves that the opened contact route gives
   boundary hinge contact and no strict interior overlap from that contact
   route.

The accepted B04 conclusion is:

```text
boundary-contact orientation is certified for the selected hinge pair on the
reported domain.
```

It is not:

```text
the selected hinge pair has positive SAT clearance.
```

## Schema Mapping

Every B04 report must use:

```yaml
schema_id: S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1
backend_lock_id: S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21
predicate_id: B04_SELECTED_HINGE_CONTACT_ORIENTATION
claim_level: exact_interval_report
```

Required B04 route extension fields from schema v1:

```yaml
contact_id: ""
hinge_axis: {}
signed_orientation_expression: ""
angle_interval: {}
opening_side_interval: {}
branch_interval: {}
boundary_contact_certificate: ""
no_positive_clearance_nonclaim: true
```

R23 narrows these fields for implementation:

```yaml
b04_orientation:
  tree_id: ""
  representative_class: TREE_007 | TREE_021
  domain_family: ray_cell | bounded_cell | synthetic_fixture
  pair_key: ""
  contact_id: ""
  hinge_id: ""
  source_contact: ""
  hinge_axis:
    endpoint_labels: []
    exact_endpoint_coordinates: []
    nonzero_length_certificate: ""
    axis_preservation_reference: S4-LEMMA-03-KINEMATICS-SIGNS-2026-06-21
  signed_orientation_expression: ""
  signed_angle_interval_degrees: {}
  angle_sign_status: positive | negative
  open_half_turn_status: inside_open_half_turn
  opening_side_interval: {}
  opening_side_status: proved_opening_side
  branch_interval: {}
  branch_stability_status: accepted
  boundary_contact_certificate: ""
  no_positive_clearance_nonclaim: true
```

The canonical `margin_interval` at top level should encode the signed
exclusion from the wrong side or from zero:

```text
wrong_side_interval_excluded
```

For positive opening:

```text
signed_angle_interval_degrees.lo > 0
and signed_angle_interval_degrees.hi < 180
```

For negative opening:

```text
signed_angle_interval_degrees.lo > -180
and signed_angle_interval_degrees.hi < 0
```

In both cases, the report must also prove:

```text
opening_side_status == proved_opening_side
boundary_contact_certificate is present and replayable
no_positive_clearance_nonclaim == true
```

## Accepted Backend Routes

B04 may emit accepted reports only through the R21 accepted backends.

| Route | Backend | Allowed B04 use |
| --- | --- | --- |
| `B04-FI` | `fraction_interval_v1` | exact rational signed-angle or branch-coordinate intervals when the expression has already been reduced to rational interval operations |
| `B04-SS` | `symbolic_sign_v1` | source-locked symbolic sign rule for signed orientation, opening side, and branch exclusion |

Blocked in R23:

| Route | Reason |
| --- | --- |
| finite signed-angle overlay | diagnostic only; not independent exact replay |
| center-sample contact orientation | finite evidence only |
| general trigonometric interval angle | no audited general trig interval backend in R21 |
| visual opening-side check | not a proof field |
| positive SAT clearance fallback | wrong predicate for selected hinge contacts |

Existing finite ray-cell and bounded-cell selected-hinge orientation reports
cannot be converted into accepted B04 reports by copying their numbers. They
must be regenerated through `B04-FI` or `B04-SS`, or remain diagnostic.

## Report Families

R23 defines three future B04 report families.

### B04-RAY-SELECTED-HINGE

Targets selected-hinge ray-cell pair-cells from:

```text
results/historical_s4_median_planes/two_class_contact_orientation_report.json
```

Requirements:

1. map each report to `tree_id`, `ray_cell_key`, `pair_key`, `hinge_id`, and
   `contact_id`;
2. reject non-selected pair-cells with `failure_reason:
   route_to_B03_or_residual_fallback`;
3. certify the signed angle interval for the selected hinge;
4. certify that the interval stays inside one open half-turn;
5. certify the package-approved opening side;
6. record the boundary-contact certificate;
7. preserve the open-domain exclusion of `theta_deg = 0`.

### B04-BOUNDED-SELECTED-HINGE

Targets bounded-cell selected-hinge pair-cells from:

```text
results/historical_s4_median_planes/bounded_cell_guard_first_pass_report.json
```

Requirements:

1. map each report to bounded cell, pair-cell, tree, and selected hinge;
2. reject all positive-clearance SAT candidates to B03;
3. reject residual shared-edge/common-edge pairs to B05;
4. reject residual shared-face face-normal pairs to B06;
5. reject residual shared-face edge-branch pairs to B07;
6. certify only the selected-hinge boundary-contact orientation predicate
   under R21.

### B04-SYNTHETIC-FIXTURES

Targets synthetic reports used to develop the replay checker before real S4
reports are accepted.

Required fixtures:

1. accepted positive opening side inside `(0, 180)`;
2. accepted negative opening side inside `(-180, 0)`;
3. rejected interval touching zero;
4. rejected interval crossing an open half-turn boundary;
5. rejected wrong opening-side sign;
6. malformed report missing `contact_id` or `hinge_axis`;
7. unsupported backend report citing `float64_numpy_scipy`;
8. diagnostic selected-hinge row routed out of B03 and into B04;
9. diagnostic non-selected pair row rejected by the B04 route classifier.

Synthetic fixtures are not S4 proof evidence. They are checker development
tools.

## Replay Checker Requirements For B04

The future replay checker must:

1. verify schema, policy, backend lock, and predicate IDs;
2. reject any B04 report with `accepted: true` before recomputing acceptance;
3. verify that `pair_key`, `hinge_id`, `contact_id`, and oriented axis match
   the selected hinge inventory;
4. verify exact endpoint coordinate objects and the nonzero hinge-axis
   certificate;
5. verify rooted kinematic axis preservation against the declared Lemma 03
   reference;
6. recompute or replay the signed orientation expression;
7. verify that the angle interval excludes zero and stays inside one open
   half-turn;
8. verify that the signed side matches the package-approved opening side;
9. verify the boundary-contact certificate;
10. verify `no_positive_clearance_nonclaim: true`;
11. verify ledger reconstruction to the claimed parent key;
12. return the R21 locked exit code.

The checker may initially support only `B04-SYNTHETIC-FIXTURES`. Real S4 B04
reports should remain `accepted: false` until the checker and the corresponding
operation enclosures exist.

## Generator Boundary

The future B04 generator should be split into:

1. a source-ledger reader;
2. a selected-hinge route classifier;
3. a hinge-axis exact-coordinate emitter;
4. a signed-orientation expression emitter;
5. an interval/sign enclosure layer;
6. an opening-side and boundary-contact certificate layer;
7. a report writer;
8. a replay invocation layer.

The report writer may emit diagnostic reports before the replay checker is
implemented. It must not emit `accepted: true` unless replay has returned exit
code `0`.

## Output Plan

Future B04 artifacts should use paths of this shape:

```text
results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_orientation/
  manifests/
  fixtures/
  ray_selected_hinge/
  bounded_selected_hinge/
```

Suggested manifest:

```yaml
manifest_id: S4-CL5-B04-SELECTED-HINGE-CONTACT-ORIENTATION-EXACT-REPORT-MANIFEST
schema_id: S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1
backend_lock_id: S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21
predicate_id: B04_SELECTED_HINGE_CONTACT_ORIENTATION
report_counts:
  accepted: 0
  rejected: 0
  diagnostic: 0
route_in_counts:
  from_B03_selected_hinge_contact: 0
route_out_counts:
  B03_strict_convex_sat: 0
  B05_common_edge_projection: 0
  B06_face_normal_support_gap: 0
  B07_edge_branch_support_component: 0
replay_summary:
  exit_code_0: 0
  exit_code_1: 0
  exit_code_2: 0
  exit_code_3: 0
  exit_code_4: 0
nonclaim:
  - no_positive_clearance_claim_for_selected_hinges
  - no_theorem_wrapper_promotion
  - no_physical_hingeability
```

## Proof Obligations

| Obligation ID | Claim ID | Precise statement needed | Current evidence | Status |
| --- | --- | --- | --- | --- |
| `R23-O1` | B04 schema mapping | every B04 field maps to schema v1 and route extension fields | this plan | open |
| `R23-O2` | selected hinge inventory | every B04 row matches the selected hinge inventory and tree selection | B04 review | open |
| `R23-O3` | axis preservation replay | selected hinge axis is preserved by both piece transforms on the reported domain | Lemma 03 draft, R21 lock | open |
| `R23-O4` | signed-angle replay | signed angle interval is recomputed exactly or symbolically under R21 | R21 lock | open |
| `R23-O5` | opening-side replay | signed interval is proved to be the package-approved opening side | B04 review | open |
| `R23-O6` | boundary-contact certificate | contact orientation implies no strict interior overlap from the selected contact route | B04 review | open written proof/source-lock |
| `R23-O7` | route classifier | B03, B05, B06, and B07 cases are excluded before B04 acceptance | R22, B04 review | open |
| `R23-O8` | B04 fixtures | accepted/rejected/malformed/unsupported/diagnostic fixtures exist | none | open |
| `R23-O9` | B04 generator | report writer emits schema v1 reports and blocks accepted true without replay | none | open |

## Non-Obligations

R23 does not need to implement:

1. the B04 generator;
2. the replay checker;
3. exact rational interval arithmetic code;
4. general trigonometric interval arithmetic;
5. positive-clearance SAT reports for selected hinges;
6. common-edge, face-normal, or edge-branch fallback reports;
7. adaptive overlay reconstruction;
8. theorem-wrapper promotion;
9. physical hingeability, CAD, mesh, or printability checks.

## Public Claim Boundary

Can say:

```text
The S4 package now has a B04 selected-hinge contact-orientation exact-report
implementation plan that maps boundary-contact orientation reports to the
locked exact/interval schema and defines selected hinge inventory, accepted
backend routes, replay requirements, fixtures, and route boundaries.
```

Can say internally:

```text
The next B04 work should start with synthetic fixtures and replay-check support
before any real selected-hinge contact-orientation report is allowed to set
accepted: true.
```

Must not say:

```text
B04 exact contact-orientation reports exist.
The current finite signed-angle overlays are exact reports.
The B04 replay checker is implemented.
Selected hinge-contact pairs have positive clearance.
Lemma 11 is promoted.
The physical branch is open.
```

## Paper-To-Engine Traceability

Future B04 artifacts should expose:

```yaml
predicate_id: R23_SELECTED_HINGE_CONTACT_ORIENTATION_EXACT_REPORT_IMPLEMENTATION_PLAN
plan_id: S4-CL5-SELECTED-HINGE-CONTACT-ORIENTATION-EXACT-REPORT-IMPLEMENTATION-PLAN-2026-06-21
target_predicate_id: B04_SELECTED_HINGE_CONTACT_ORIENTATION
schema_id: S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1
backend_lock_id: S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21
accepted_backend_routes:
  - B04-FI
  - B04-SS
blocked_backend_routes:
  - finite_signed_angle_overlay
  - center_sample_contact_orientation
  - general_trig_interval_angle
  - positive_sat_clearance_for_selected_hinge
route_in:
  B03: selected_hinge_contact
route_out:
  B03: strict_convex_sat_nonhinge_clearance
  B05: residual_common_edge
  B06: residual_face_normal
  B07: residual_edge_branch
replay_checker_status: not_implemented
generator_status: not_implemented
promotion_status: blocked
next_artifact: docs/S4_CL5_COMMON_EDGE_PROJECTION_EXACT_REPORT_IMPLEMENTATION_PLAN.md
```

## Review Outcome

R23 records the B04 selected-hinge contact-orientation exact-report
implementation plan as complete.

The package now knows how future B04 reports must fit the R21 backend/schema
lock. It still lacks fixtures, replay checker code, generator code, and real
accepted selected-hinge contact-orientation reports.

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
