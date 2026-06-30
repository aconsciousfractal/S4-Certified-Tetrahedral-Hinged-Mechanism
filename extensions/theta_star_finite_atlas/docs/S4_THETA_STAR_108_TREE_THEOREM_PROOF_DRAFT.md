# S4 theta-star 108-tree theorem proof draft

Status: theorem-support proof draft for the promoted public companion addendum.  Not a main-paper theorem update; T6b records the historical review obligations that were closed before promotion.
Date: 2026-06-29

## Scope

This document states the local finite-atlas theorem supported by the S4 mechanical-extension artifacts.  It concerns only:

```text
historical S4 median-plane zero-thickness scaffold;
108 connected three-hinge trees in the finite S4 atlas;
equal-magnitude one-parameter signed rays;
t = tan(theta/2), with endpoint t = sqrt(3) for theta = 120 degrees.
```

It does not concern non-equal angle motion, three-parameter motion, positive thickness, CAD validity, fabrication, or physical hingeability.

## Basic Definitions

A sign row assigns one sign to each of the three hinges of a tree.  Along an equal-magnitude ray, every hinge angle has magnitude `theta`; the sign row chooses its orientation.  For a tree `T`, `t*(T)` is the maximum event value in half-angle coordinates over the eight equal-magnitude sign rows under the current zero-thickness collision/contact predicates.

The words used below have the following strict meanings.

```text
endpoint reached at sqrt(3): no blocking non-hinge contact on 0 < t <= sqrt(3)
positive jam at sqrt(2):    first blocking event at t = sqrt(2); max-over-8 sign-row closure is exact-certified locally
instant jam at 0:           every equal-magnitude sign row has right-germ obstruction at t = 0
wrapper scope:              source-locked one-parameter wrapper class, kept semantically separate
```

For full-open records, `sqrt(3)` is an endpoint, not a first-contact value.

## Theorem A -- Finite-Angle Scaffold Conjugacy

Let `g` be a valid scaffold isometry of the historical S4 zero-thickness scaffold.  It induces a piece map, hinge map, and tree map.  If an oriented source hinge axis `u_h` maps to the target catalogue axis by

```text
R_g u_h = orient_g(h) u_{g(h)},       orient_g(h) in {+1,-1},
```

then the transported equal-magnitude sign row is

```text
s'_{g(h)} = det(R_g) * orient_g(h) * s_h.
```

The finite-angle conjugacy lemma states that the target configuration for `(g(T), s')` is congruent to the source configuration for `(T, s)`, after piece relabeling and finite root re-gauge by one common rigid transform.  Therefore pairwise relative configurations, strict interior overlap, contact, non-overlap, and SAT predicates are preserved.

Source proof note:

```text
docs/S4_FINITE_ANGLE_SCAFFOLD_CONJUGACY_LEMMA.md
```

## Theorem B -- Theta-Star Orbit Invariance

The map `s -> s'` above is a bijection of the eight equal-magnitude sign rows.  Since finite-angle scaffold conjugacy preserves the pairwise collision/contact status for every admissible `t`, it preserves the best attainable `t` on each sign row.  Taking the maximum over all eight rows gives

```text
t*(T) = t*(g(T)).
```

Thus `t*` and the theta-star status are invariant under the valid S4 scaffold kinematic groupoid, including finite root re-gauge.  In the implementation, this is hardened by the T4 finite-angle transport ledger, the T5b finite root-regauge replay, and the T5c endpoint-free witness transport gate.

## Theorem C -- Representative Theta-Star Spectrum

The 18 representative trees have exact local source certificates in four classes.  The source-level classes before final theorem relabeling are:

```text
exact_free_witness_candidate                5
public_wrapper_scope_certificate            1
stage3a_stage3b_stage3c_local_tree_package  2
instant_jam_row_gate                        10
```

The representative evidence is not a physical claim.  It is a zero-thickness equal-magnitude theta-star classification layer for representative trees, source-locked through the local certificate stack.  The explicit 18-row source table is:

```text
docs/S4_THETA_STAR_REPRESENTATIVE_SOURCE_CERTIFICATE_TABLE.md
```

T6b correction: the two positive-jam representatives (`TREE_000`, `TREE_003`) now have exact selected-row Stage-3 packages plus the dedicated max-over-all-8-sign-rows certificate. The selected hinge-side map and the positive-jam support-feature/SAT-axis map are exposed by the source-map visibility audit. Instant-jam representatives are checked as 8-row gates. See:

```text
docs/S4_THETA_STAR_THEOREM_CLASS_PREDICATE_AUDIT.md
```

## Theorem D -- 108-Tree S4 Theta-Star Spectrum

Combining Theorem A, Theorem B, the representative spectrum, and the T4/T5/T6 certificate assembly gives the local finite-atlas theorem candidate. T6b now marks the positive-jam max-over-8 quantifier and source-map visibility obligations as exact-closed; the remaining local promotion item is theorem-name/scope hygiene before external red-team:

For every connected three-hinge tree `T` in the historical S4 scaffold, `T` has exactly one final theta-star certificate class.  The final classes are:

```text
exact_positive_theta_jam_package_source_locked     8
exact_endpoint_free_witness_transport_certificate  36
exact_instant_jam_8_row_gate_source_locked         60
one_parameter_wrapper_scope_source_locked          4
```

The theta-star status distribution is:

```text
full_open_to_120               36
instant_jam_t0                 60
jam_at_positive_t              8
full_open_to_120_public_scope  4
```

Equivalently, the exact event parameter distribution is:

```text
sqrt(3) endpoint reached  40
0                         60
sqrt(2)                   8
```

The positive jam value `t = sqrt(2)` corresponds to

```text
theta = 2 atan(sqrt(2)) = arccos(-1/3),
```

the regular tetrahedral angle.

The statement is supported by:

```text
results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_108_tree_theorem_assembly_gate.json
results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_108_tree_theorem_assembly_gate_replay.json
```

The assembly gate reports:

```text
T6 local_theorem_supported = true
T6 public_promotion_ready  = false
T6b status                = pass_with_review_obligations
```

## Proof Skeleton

1. **Finite atlas coverage.**  The S4 scaffold has 108 connected three-hinge trees in the current atlas.  T4 and T6 verify that every target appears once and only once.

2. **Source representatives.**  The 18 structural representatives carry source status classes: endpoint-free full-open, wrapper full-open, positive jam at `sqrt(2)`, or instant jam at `0`.  T6b exposes the source artifacts row-by-row and records the positive-jam max-over-8 closure as exact-closed.

3. **Configuration-level transport.**  The finite-angle scaffold conjugacy lemma transports configurations, not only row labels.  The T4 ledger records the finite piece map, hinge map, signed hinge-coordinate multiplier, pair map, algebraic event value, and source representative class for every target.

4. **Root re-gauge.**  T5b closes the 72 non-root-preserving records by replaying the pairwise identity

```text
inv(G*Cj)*(G*Ci) = inv(Cj)*Ci
```

on all six unordered piece pairs.  Root changes are therefore global frame changes, not changes of pairwise geometry.

5. **Endpoint-free witness proof polish.**  T5c replaces the historical `exact_free_witness_candidate` label by transported exact endpoint-free witness rows: 30 source rows over five representatives and 216 transported pair rows over 36 targets.

6. **Assembly and replay.**  T6 consumes T4, T5a, T5b, and T5c.  It checks the final 108 records, class counts, target coverage, root-regauge closure, endpoint-free transport closure, instant-jam digests, positive-jam selected-row source locks, wrapper source locks, and final distribution.  T6b prevents overclaim by separating the now-closed positive-jam max-over-8 certificate and source-map visibility audit from the remaining theorem-name/scope obligation.

7. **Sabotage hygiene.**  The sabotage gate mutates deep copies of T4/T5c/T6 artifacts and requires the replay invariants to reject corrupted classes, `t*` values, sign multipliers, piece maps, pair coverage, target coverage, root-regauge closure, and orbit/source alignment.

```text
results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_theorem_sabotage_gate.json
status = pass, checks = 19/19
```

## Claim-To-Artifact Spine

```text
finite-angle conjugacy lemma       docs/S4_FINITE_ANGLE_SCAFFOLD_CONJUGACY_LEMMA.md
certificate transport lemma        docs/S4_THETA_STAR_CERTIFICATE_TRANSPORT_LEMMA.md
T4 transport ledger                results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_finite_angle_transport_ledger.json
T4 replay                          results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_finite_angle_transport_ledger_replay.json
T5a readiness audit                results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_transport_theorem_readiness_audit.json
T5b root-regauge replay            results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_finite_root_regauge_replay_gate.json
T5c endpoint witness transport     results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_endpoint_free_witness_transport_gate.json
T6 theorem assembly                results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_108_tree_theorem_assembly_gate.json
T6 assembly replay                 results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_108_tree_theorem_assembly_gate_replay.json
sabotage hygiene gate              results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_theorem_sabotage_gate.json
source-map visibility audit        results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_source_map_visibility_audit.json
```

## Nonclaims

The theorem does not claim:

```text
non_equal_angle_motion                            1
three_parameter_motion_classification             1
positive_thickness_or_physical_hingeability       1
CAD_or_fabrication_validity                       1
public_paper_promotion_without_separate_red_team  1
```

## Promotion Boundary

This proof draft is a local theorem-support document.  Before use in a public paper or addendum, it needs focused external mathematical red-team review and a separate promotion decision.  The public S4 paper is not updated by this local draft.
