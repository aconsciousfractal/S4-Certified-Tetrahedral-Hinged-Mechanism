# S4 theta-star 108-tree theorem crosswalk

Status: local theorem-support crosswalk.  Not a public-paper update.
Date: 2026-06-29

This document maps the theorem/lemma proof spine to concrete replay artifacts.

## Claim To Artifact Map

| Claim | Meaning | Gate | Artifact |
| --- | --- | --- | --- |
| Theorem A | Finite-angle scaffold conjugacy by pose-level piece relabeling and root re-gauge | lemma prose | `docs/S4_FINITE_ANGLE_SCAFFOLD_CONJUGACY_LEMMA.md` |
| Theorem B | Theta-star orbit invariance under the valid S4 scaffold kinematic groupoid | transport lemma + T4/T5b | `docs/S4_THETA_STAR_CERTIFICATE_TRANSPORT_LEMMA.md` |
| Theorem C | Representative theta-star spectrum over the 18 source representatives | representative status ledger consumed by T4 | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_108_tree_status_map.json` |
| Theorem D | 108-tree local theta-star spectrum | T6 assembly | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_108_tree_theorem_assembly_gate.json` |
| 108-tree coverage | Every connected S4 three-hinge tree has one final record | T4 ledger + T6 assembly | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_finite_angle_transport_ledger.json` |
| Root re-gauge | 72 non-root-preserving targets preserve pairwise relative geometry | T5b | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_finite_root_regauge_replay_gate.json` |
| Endpoint-free rows | 36 full-open records have transported exact endpoint-free witness rows | T5c | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_endpoint_free_witness_transport_gate.json` |
| Proof hygiene | Corrupted theorem artifacts are rejected by local invariants | sabotage gate | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_theorem_sabotage_gate.json` |
| Source-map visibility | Selected hinge-side rows and positive-jam support-feature/SAT-axis witnesses are exposed | source-map visibility audit | `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_theta_star_source_map_visibility_audit.json` |

## Certificate Class Crosswalk

| Final class | Count | Geometric meaning | Support route |
| --- | ---: | --- | --- |
| `exact_positive_theta_jam_package_source_locked` | 8 | first blocking contact at t=sqrt(2) | T5a Stage3a/3b/3c source locks + max-over-8 + source-map support audit |
| `exact_endpoint_free_witness_transport_certificate` | 36 | endpoint reached at sqrt(3); not first contact | T5c exact endpoint witness transport |
| `exact_instant_jam_8_row_gate_source_locked` | 60 | all eight sign rows obstruct at t=0 | T5a instant-jam 8-row digest |
| `one_parameter_wrapper_scope_source_locked` | 4 | wrapper-scoped endpoint-reaching class kept separate | T5a wrapper source locks + source-map selected-hinge-side audit |

## Sabotage Hygiene

The sabotage gate is deliberately not an independent proof.  It is a replay hygiene check answering whether the artifact layer notices controlled corruptions.

```text
script  scripts/replay_s4_theta_star_theorem_sabotage_gate.py
status  pass
checks  19/19 pass
```

It detects corruption of class labels, `t*` labels, sign multipliers, endpoint-free piece maps, endpoint-free pair coverage, final class counts, final `t*` counts, target coverage, root-regauge closure, and orbit/source alignment.

## Current Decision

The assembly gate and proof-hygiene sabotage gate pass, and T6b records `pass_with_review_obligations`. The previous positive-jam exact max-over-8 blocker and source-map visibility blockers are closed; closed theorem promotion still requires theorem-name/scope hygiene and external mathematical red-team. Public promotion remains a separate later decision; public_promotion_ready=false.

## Nonclaims Preserved

This crosswalk does not claim non-equal angle motion, three-parameter motion, positive thickness, physical hingeability, CAD validity, fabrication, or public paper promotion.
