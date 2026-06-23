> **Package provenance note.** This is a historical or future-scope source
> snapshot retained for audit trail only. It may contain words such as
> `draft`, `blocker`, or `Not a CL5 theorem`; those statements are not public
> claims of the current paper-as-public-package and do not widen the scoped
> zero-thickness theorem.

# S4 Lemma 10: Arithmetic And Exactness Boundary

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-10-ARITHMETIC-EXACTNESS-BOUNDARY-2026-06-21`
review status: exactness-boundary lemma draft

## Purpose

This lemma classifies the arithmetic status of the S4 zero-thickness package
before any theorem wrapper is attempted.

It separates:

```text
exact coordinate/combinatorial facts
symbolic or formula-derived claims
finite ledger and overlay facts
interval-support obligations
floating or tolerance-dependent predicates
```

The purpose is not to prove the remaining geometric guards.  The purpose is to
prevent a finite replay or floating predicate from being silently promoted to a
CL5 mathematical theorem.

## Source Anchors

- `docs/S4_LEMMA_01_GEOMETRY_AND_TILING.md`
- `docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`
- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `docs/S4_LEMMA_04_SIGNED_RAY_CLASSES.md`
- `docs/S4_LEMMA_05_RAY_FINITE_COVER_LEDGER.md`
- `docs/S4_LEMMA_06_NEAR_ZERO_BRIDGE_FORMULAS.md`
- `docs/S4_LEMMA_07_REFINED_EDGE_RESIDUAL_CLOSURE.md`
- `docs/S4_LEMMA_08_BOUNDED_CELL_FIRST_PASS_AND_FALLBACK_GUARDS.md`
- `docs/S4_LEMMA_09_ADAPTIVE_SUBDIVISION_AND_OVERLAY_INVARIANT.md`
- `docs/S4_PROOF_OBLIGATIONS.md`
- `docs/S4_MATHEMATICAL_LEMMA_PLAN.md`
- `docs/S4_RED_TEAM_REPORT.md`
- `docs/S4_FINAL_STATEMENT_FREEZE.md`
- `scripts/mechanical_audit_lib.py`
- representative reports under `results/historical_s4_median_planes/`

## Arithmetic Layers

### Layer A: Exact Coordinate And Combinatorial Facts

The following facts are already expressible without floating predicates:

1. the regular tetrahedron coordinates from Lemma 01;
2. the midpoint labels `M_AB` and `M_CD`;
3. the four closed pieces `P0..P3` as convex hulls;
4. the barycentric sign-cell partition of the ambient tetrahedron;
5. the closed contact graph at `theta = 0`;
6. the rooted hinge-tree combinatorics for `TREE_007` and `TREE_021`;
7. the finite signed-ray class reduction from Lemma 04;
8. the finite parent-key and terminal-child key schemas from Lemma 09.

These may be promoted inside a theorem wrapper once notation is locked and the
local derivations are reviewed.  Their proof does not depend on sampled SAT,
floating tolerances, or formula-check probes.

### Layer B: Symbolic Or Formula-Derived Claims

The following claims have formulas written in the lemma stack, but remain
separate from exact guard soundness:

1. the shared-face bridge formula

```text
sin(theta/2)^3 * cos(theta/2)
```

on `0 < theta <= 0.5` degrees;

2. the shared-edge bridge formula

```text
sin(theta) / sqrt(2 * (1 + cos(theta)^2))
```

on `0 < theta <= 0.5` degrees;

3. face-normal support-gap formulas used by refined-edge and bounded-cell
   fallback ledgers;
4. support-component lower-bound formulas used by edge-branch guards.

The positivity of the two near-zero bridge formulas is algebraic once the
formula and support branch are fixed.  The missing exactness item is branch
validity: the named separator, support extrema, and orientation predicate must
remain the intended ones over the full interval or cell.

Formula-check reports may support the derivation search, but they do not by
themselves prove a symbolic identity.

### Layer C: Finite Ledger And Overlay Facts

The following are finite ledger facts:

| Ledger | Parent universe | Covered universe |
| --- | ---: | ---: |
| Ray cells per representative | `478` | `478` |
| Ray pair-cells per representative | `2868` | `2868` |
| Refined-edge segments per representative | `2528` | `2528` |
| Refined-edge pair-segments per representative | `15168` | `15168` |
| Bounded all-free cells across representatives | `1536` | `1536` |
| Bounded pair-cells across representatives | `9216` | `9216` |

These facts are exact as finite accounting once the key universe is fixed and
the reports are replayed.  They prove ledger coverage, not geometric
non-overlap by themselves.

The promotion boundary is:

```text
finite parent-key coverage
does not imply
sound geometric guard over every parent key
```

unless every guard route assigned to those keys has an exact algebraic or
interval proof.

### Layer D: Interval-Support Obligations

The following predicates require interval or exact conservative support before
the package can be read as a theorem:

1. strict convex SAT / separating-axis non-overlap over full cells or segments;
2. selected-hinge contact orientation over ray cells and bounded cells;
3. common-edge projection guards for residual shared-edge contacts;
4. face-normal support-gap guards over recorded angle intervals;
5. edge-branch support-component guards `G1` through `G4`;
6. adaptive isolation guards and terminal child replacement;
7. support-extremality and branch-stability conditions.

An acceptable CL5 route is either:

```text
exact algebraic inequality proof
```

or:

```text
outward-rounded interval arithmetic with explicit endpoint and tolerance policy
```

for every guard predicate used by the theorem wrapper.

### Layer E: Floating Or Tolerance-Dependent Predicates

The current scripts use floating arithmetic in several places.  Visible
examples include:

| Source | Predicate or tolerance |
| --- | --- |
| `mechanical_audit_lib.py` | `TOL = 1.0e-9` |
| `mechanical_audit_lib.py` | `strict_interior_overlap(..., tol = 1.0e-8)` |
| `mechanical_audit_lib.py` | point/segment/triangle tests with `1.0e-8` style thresholds |
| `audit_historical_s4_bounded_cell_guard_first_pass.py` | `ANGLE_TOLERANCE_DEGREES = 1.0e-10` |
| `audit_historical_s4_bounded_cell_guard_first_pass.py` | clearance guard margins built from floating displacement bounds and `SAT_TOLERANCE` |
| `audit_historical_s4_bounded_cell_face_normal_formula_guard.py` | `FORMULA_TOLERANCE = 1.0e-12` |

Representative formula-check reports record small floating errors:

| Report | Metric |
| --- | ---: |
| `residual_shared_face_formula_check_report.json` | max formula abs error `1.11e-16` |
| `residual_shared_edge_formula_check_report.json` | max formula abs error `2.04e-16` |
| `bounded_cell_face_normal_formula_guard_report.json` | maximum formula check abs error `1.03e-16` |

These are good numerical consistency signals.  They are not exact proof
objects unless paired with an interval policy explaining rounding, comparison
direction, branch selection, and lower-bound margins.

## Boundary Table

| Component | Current evidence | Required promotion support | Current allowed claim |
| --- | --- | --- | --- |
| S4 geometry and tiling | exact coordinate/barycentric Lemma 01 | notation review | exact local lemma draft |
| `theta = 0` endpoint | closed-contact Lemma 02 plus report | final wrapper review; no positive-clearance wording | closed contact only |
| Hinge kinematics | rooted `SE(3)` Lemma 03 | angle-unit and sign notation lock | exact model draft |
| Signed-ray representatives | finite symmetry/class Lemma 04 | notation review | finite exact class draft |
| Ray finite cover | Lemma 05 ledger, `478/478`, `2868/2868` | guard soundness and interval/exact arithmetic | finite coverage ledger |
| Near-zero formulas | Lemma 06 formulas plus probe reports | exact derivation and branch-stability proof | formula-bridge draft |
| Refined-edge closure | Lemma 07 ledger, `2528/2528`, `15168/15168` | guard soundness and overlay exactness review | finite coverage ledger |
| Bounded-cell closure | Lemma 08 ledger, `1536/1536`, `9216/9216` | full guard soundness and interval support | finite coverage ledger |
| Adaptive subdivision | Lemma 09 parent-cover accounting | proof that child boxes partition parents | ledger invariant draft |
| Physical/CAD model | excluded | separate physical model and tolerances | no claim |
| Dynamic class connection | excluded | separate continuous-path audit/proof | no claim |

## Demotion Rules

Before theorem wording, apply these rules mechanically:

1. If a statement depends on a floating inequality and no exact or interval
   support is written, state it as finite replay or formula-check evidence.
2. If a finite ledger reconstructs a parent universe but the assigned guard is
   not proved, state only ledger coverage.
3. If a formula matches sampled/direct geometry up to a tolerance, state it as
   formula-check evidence unless the symbolic derivation is written.
4. If a guard uses a selected support branch, state the branch-stability
   obligation explicitly.
5. If a statement includes `theta = 0`, keep it under closed-contact semantics;
   never import positive-clearance language from positive-angle certificates.
6. If a result refers to physical thickness, offsets, CAD, mesh export, or
   printability, mark it out of scope for the current zero-thickness theorem.

These rules preserve the current CL2/CL3 boundary until every cited predicate
has proof-ready support.

## Acceptance Criterion For A CL5 Wrapper

A scoped theorem wrapper may cite a component of this package only after one of
the following is true:

1. the component is exact coordinate/combinatorial and has a written lemma;
2. the component is symbolic/formula-derived and the exact derivation plus
   branch-stability proof is written;
3. the component is a finite ledger and all guard predicates assigned to its
   keys have exact or interval proofs;
4. the component is explicitly demoted to finite/certificate evidence and not
   used as a theorem premise.

Additionally, the wrapper must preserve:

```text
catalogued median-plane S4 only
TREE_007 and TREE_021 representatives only
audited ray and bounded-cell domains only
theta = 0 as closed contact only
no physical hinge/CAD/printability claim
no dynamic connectedness claim
```

## Lemma Statement

For the current S4 zero-thickness package, the proof-ready material is exactly
the material that can be routed through Layers A, B, C, and D with the required
support stated above.  Any predicate remaining in Layer E is not theorem-ready
and must be either replaced by an exact/interval argument or demoted to
finite/certificate evidence.

Consequently, the existing package supports a controlled lemma stack and
finite certificate boundary, but it does not yet support a CL5 theorem wrapper
that treats all numeric guards as proved.

## Explicit Non-Claims

This lemma does not prove:

- SAT guard soundness;
- selected-hinge orientation soundness;
- common-edge, face-normal, or edge-branch guard soundness;
- exact rounding correctness for the existing floating scripts;
- dynamic connectedness between `TREE_007` and `TREE_021`;
- global S4 hingeability;
- physical hingeability, hinge thickness, CAD validity, or printability.

## R6j Result

This draft discharges `S4-PO-011` at the methodology level: the arithmetic and
exactness boundary is now written and can be cited by the final theorem-scope
work.  The underlying exact/interval proofs for guard soundness remain open
unless separately written.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
