# S4 Lemma 11: Scoped Zero-Thickness Theorem Wrapper

Status: theorem-wrapper draft / scope guard.  Not a CL5 theorem.

Date: 2026-06-21.

Case: `historical_s4_median_planes`.

Lemma ID: `S4-LEMMA-11-SCOPED-ZERO-THICKNESS-THEOREM-WRAPPER-2026-06-21`.

## Purpose

This note is the scoped wrapper for the S4 zero-thickness lemma package.  It
combines the written local lemmas only at their current support level:

- exact or definitional facts remain exact or definitional;
- formula-derived facts remain formula-derived unless a support/interval proof
  is already written;
- finite ledgers remain finite ledgers;
- floating or tolerance-dependent predicates remain demoted by Lemma 10.

This is not a final theorem.  It is the document that states what a final
theorem is allowed to say, what it is not allowed to say, and which remaining
proof obligations block CL5 promotion.

## Imported Notation

All notation is imported from
`docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`.

In particular:

```text
T = conv(A, B, C, D)
M_AB = (A + B)/2
M_CD = (C + D)/2
Pieces = {P0, P1, P2, P3}
Pairs = {P0-P1, P0-P2, P0-P3, P1-P2, P1-P3, P2-P3}
Contact IDs = C0, C1, C2, C3, C4, C5
Representative trees = TREE_007, TREE_021
Angle variables = theta_deg, theta_rad
```

The root piece for both representative trees is `P0`.  Moving-piece transforms
are denoted `F_i`, not `T_i`, to avoid collision with the ambient tetrahedron
symbol `T`.

## Imported Lemma Stack

| Lemma | Imported role | Current support level |
| --- | --- | --- |
| `L0` Definitions and notation lock | fixes labels, domains, and ledger keys | definitional |
| `L1` Catalogued geometry and tiling | defines the four median-plane pieces and closed tiling | exact coordinate/combinatorial draft |
| `L2` Closed-contact endpoint | separates closed-contact semantics from positive clearance | exact/closed-contact draft |
| `L3` Kinematics and signs | defines rigid-hinge transforms for `TREE_007` and `TREE_021` | exact kinematic model draft |
| `L4` Signed-ray classes | reduces four all-ambient-edge candidates to two root-preserving classes | finite combinatorial draft |
| `L5` Ray finite-cover ledger | covers `478` ray cells and `2868` pair-cells per representative on `0.5 <= theta_deg <= 120` | finite ledger with guard-soundness blockers |
| `L6` Near-zero bridge formulas | covers formula bridge on `0 < theta_deg <= 0.5` | formula-derived draft with support/exactness blockers |
| `L7` Refined-edge residual closure | covers `2528/2528` refined segments and `15168/15168` pair-segments per representative | finite ledger with guard-soundness blockers |
| `L8` Bounded-cell first-pass/fallback guards | covers `1536/1536` all-free bounded cells and `9216/9216` pair-cells | finite ledger with guard-soundness blockers |
| `L9` Adaptive subdivision and overlay invariant | folds terminal child certificates back to parent keys | finite overlay/accounting draft |
| `L10` Arithmetic and exactness boundary | classifies exact, symbolic, finite-ledger, interval, and floating layers | methodology and demotion lemma |

## Current Supported Statement

At the current proof state, the S4 package supports the following scoped
certificate statement:

```text
For the catalogued median-plane S4 tetrahedral dissection, in the
zero-thickness rigid-piece model and using the notation of Lemma 00, the
workspace has a written lemma stack and finite/certificate ledgers for the two
representative all-ambient-edge signed-ray trees TREE_007 and TREE_021.

The stack includes:

1. the exact catalogued closed assembly;
2. the closed-contact endpoint E0 at theta_deg = 0;
3. the representative signed-ray kinematic model;
4. finite ray-cell coverage on 0.5 <= theta_deg <= 120;
5. formula-derived near-zero bridge evidence on 0 < theta_deg <= 0.5;
6. refined-edge finite overlay coverage;
7. bounded all-free cell finite overlay coverage;
8. overlay-key accounting and exactness/demotion rules.

Every conclusion depending on numerical guards, floating tolerances, or
unproved interval support remains a finite/certificate or proof-obligation
statement, not a promoted CL5 theorem statement.
```

This is the strongest safe statement now available from the written lemma
package.

## Draft CL5 Theorem Candidate

The following is the theorem shape that may be promoted only after the blockers
listed later in this file are resolved:

```text
For the catalogued median-plane S4 dissection inside the regular tetrahedron
T, under the zero-thickness rigid-piece edge-hinge model, the representative
signed-ray tree classes represented by TREE_007 and TREE_021 have
non-interpenetrating motions on their audited open domains, and the
configuration theta_deg = 0 is the catalogued closed-contact endpoint.

The statement covers only the audited representatives and audited domains.  It
does not assert physical hingeability, positive endpoint clearance, dynamic
connectedness between representatives, or global S4 hingeability.
```

This paragraph is a candidate wrapper, not a current theorem claim.

## Domain Decomposition

The wrapper keeps the S4 domains separate.

| Domain | Range / parent universe | Source lemmas | Current wrapper status |
| --- | --- | --- | --- |
| Closed endpoint | `theta_deg = 0` | `L1`, `L2`, `L3` | closed-contact exact draft; no positive-clearance claim |
| Near-zero bridge | `0 < theta_deg <= 0.5` | `L6`, `L10` | formula-derived; support/exactness blockers remain |
| Ray finite cover | `0.5 <= theta_deg <= 120` | `L5`, `L10` | finite ray-cell ledger; guard-soundness blockers remain |
| Open representative ray | `0 < theta_deg <= 120` | `L5`, `L6` | union of bridge and ray ledger at their support levels |
| Refined-edge overlay | `2528` refined segments per representative | `L7`, `L9`, `L10` | finite parent-key ledger |
| Bounded all-free cells | `1536` cells / `9216` pair-cells across both representatives | `L8`, `L9`, `L10` | finite parent-key ledger |

No row in this table automatically covers a domain outside its recorded parent
universe.

## Closed Endpoint Clause

At `theta_deg = 0`, the statement is:

```text
The four closed pieces form the catalogued closed-contact assembly.  The six
unordered piece pairs are exactly the catalogued contacts C0 through C5, and
there is no strict interior overlap between distinct pieces.
```

This endpoint clause is closed-set and contact-allowing.  It does not assert:

```text
positive clearance at theta_deg = 0.
```

The endpoint is therefore compatible with the open-domain statements only as a
closed-contact limit, not as a positive-clearance certificate.

## Open Representative-Ray Clause

For each representative `tree_id in {TREE_007, TREE_021}`, the open
representative ray uses:

```text
0 < theta_deg <= 120.
```

It is split into:

```text
0 < theta_deg <= 0.5
0.5 <= theta_deg <= 120
```

The second subdomain has a finite ray-cell ledger:

```text
478 ray cells per representative
2868 pair-cells per representative
```

The first subdomain is handled by near-zero bridge formulas and remains subject
to the support/exactness boundary of Lemma 10.

The wrapper must not rewrite the open-ray clause as a physical hinge or
positive-thickness statement.

## Refined-Edge Clause

For each representative tree, the refined-edge parent universe is:

```text
2528 refined segment keys
15168 pair-segment keys = 2528 * 6
```

The current ledger records:

```text
TREE_007 refined segments: 2528/2528
TREE_007 pair-segments:    15168/15168

TREE_021 refined segments: 2528/2528
TREE_021 pair-segments:    15168/15168
```

This clause is a finite parent-key ledger.  It does not certify every possible
continuous graph edge, and it does not prove dynamic connectedness between the
two representative classes.

## Bounded-Cell Clause

The bounded all-free parent universe across `TREE_007` and `TREE_021` is:

```text
1536 all-free bounded cells
9216 pair-cells = 1536 * 6
```

The current ledger records:

```text
bounded all-free cells: 1536/1536
bounded pair-cells:     9216/9216
```

This clause excludes:

```text
the 96 + 96 blocked sampled-vertex cells
theta_deg = 0
domains not represented by the bounded-cell parent universe
```

The bounded-cell clause is therefore not a global configuration-space theorem.

## Overlay-Key Clause

The wrapper uses the parent-key rule from Lemma 09:

```text
terminal child certificates certify their parent key only when their terminal
family covers the audited part of that parent key and every terminal child is
certified by an accepted route.
```

Terminal child keys are witness keys.  They do not enlarge the theorem domain.
The final scope is always the parent-key universe fixed by the source ledger.

## Exactness Clause

By Lemma 10, every component of the wrapper must be routed through one of these
layers:

```text
Layer A: exact coordinate and combinatorial facts
Layer B: symbolic or formula-derived claims
Layer C: finite ledger and overlay facts
Layer D: interval-support obligations
Layer E: floating or tolerance-dependent predicates
```

The wrapper may cite Layer A facts directly.  It may cite Layer B, C, and D
facts only with their stated support obligations.  It must not use Layer E
predicates as theorem premises unless an exact or interval replacement is
provided.

Therefore, at the current state, the wrapper is a scoped certificate and
proof-obligation wrapper, not a CL5 mathematical theorem.

## Current Proof Skeleton

A future CL5 proof would have the following shape:

1. Use Lemma 00 to fix notation and domains.
2. Use Lemma 01 to define the catalogued median-plane S4 pieces and closed
   assembly.
3. Use Lemma 02 to handle the closed endpoint under contact-allowing semantics.
4. Use Lemma 03 to define the representative rigid-hinge kinematics.
5. Use Lemma 04 to justify reducing the audited all-ambient-edge signed-ray
   candidates to `TREE_007` and `TREE_021`.
6. Use Lemmas 05 and 06 to cover the representative open rays.
7. Use Lemmas 07 through 09 to cover the recorded refined-edge and bounded-cell
   parent-key universes.
8. Use Lemma 10 to decide which components are exact theorem premises and
   which remain finite/certificate or interval-support obligations.
9. Conclude only inside the audited domains and only at the support level
   allowed by the prior steps.

The current package completes the written skeleton and scope boundary.  It
does not complete every guard-soundness or exactness proof needed for CL5.

## Promotion Checklist

Before this wrapper can become a CL5 theorem, all of the following must be
true:

1. The exact coordinate and contact facts from Lemmas 01 and 02 have been
   reviewed against Lemma 00 notation.
2. The transform and sign conventions from Lemma 03 have been reviewed against
   the source scripts and report payloads.
3. The finite group-action reduction in Lemma 04 has a reviewer-readable
   proof independent of sampled motion.
4. Every guard route used by Lemma 05 has a proved separating-axis,
   orientation, formula, or interval-support lemma.
5. The near-zero bridge formulas in Lemma 06 have derivations and active-branch
   support over the full stated bridge.
6. Every refined-edge residual guard route in Lemma 07 has a proved geometric
   implication over its parent or terminal key.
7. Every bounded-cell first-pass or fallback guard route in Lemma 08 has a
   proved geometric implication over its parent or terminal key.
8. Lemma 09's adaptive parent-cover assumptions are checked for every adaptive
   fallback ledger used by the wrapper.
9. Lemma 10's exactness conditions are satisfied or the affected claim is
   explicitly demoted in the theorem statement.
10. The final statement still excludes physical hingeability, dynamic
    connectedness, positive endpoint clearance, global S4 hingeability, and
    non-catalogued dissections.

If any item fails, the wrapper must remain at the finite/certificate or
proof-obligation level.

## Explicit Nonclaims

This wrapper does not claim:

- `S4` is globally hingeable;
- `S4` is physically hingeable;
- any positive-thickness hinge realization exists;
- `TREE_007` and `TREE_021` are dynamically connected by an open path;
- the endpoint `theta_deg = 0` has positive clearance;
- the finite replay is already a CL5 proof;
- the bounded-cell ledger covers blocked sampled-vertex cells;
- the refined-edge ledger covers every possible continuous graph edge;
- Demaine-style hinged-dissection existence theory proves this fixed-piece
  mechanism.

## Wrapper Result

The S4 zero-thickness statement is now wrapped at the correct scope:

```text
catalogued median-plane S4
zero-thickness rigid-piece model
representatives TREE_007 and TREE_021
audited open representative-ray and finite parent-key domains
closed-contact endpoint at theta_deg = 0
finite/certificate and proof-obligation status preserved
physical, dynamic-connection, positive-clearance, global, and CL5 overclaims excluded
```

This completes the R6l theorem-wrapper draft without promoting the package
beyond its current proof boundary.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
