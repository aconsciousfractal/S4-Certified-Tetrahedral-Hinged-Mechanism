# S4 theta-star theorem class predicate audit

Status: T6b proof-prose audit. Not a public-paper update.
Date: 2026-06-29

This document records which predicates are geometrically transported, which are source-locked, which are directly replayed, and which were tracked before public addendum promotion.

| final class | geometric transport by Theorem A/B | source-locked predicates | directly replayed gates | not applicable | open / required fix |
| --- | --- | --- | --- | --- | --- |
| `exact_endpoint_free_witness_transport_certificate` | piece maps, pair maps, sign rows, endpoint-free witness rows, SAT/contact status under rigid conjugacy | five representative endpoint-free witness sources | T5c endpoint-free witness transport gate: 36 targets, 216 transported pair rows | positive-jam binding pair, instant right-germ obstruction | none known at T6b level |
| `one_parameter_wrapper_scope_source_locked` | finite-angle orbit transport can carry wrapper-scoped status only inside the same one-parameter semantics | public/local wrapper artifacts; selected-hinge B04/A7c contact-side semantics | source manifests, T4/T6 source-lock checks, and source-map visibility audit | positive-jam max-over-8, instant 8-row gate | closed by `s4_theta_star_source_map_visibility_audit.json` |
| `exact_positive_theta_jam_package_source_locked` | binding pair, contact axes, non-hinge residual pair labels, sign rows, support features, SAT-axis sources, and algebraic `t=sqrt(2)` are transportable once source proof is complete | TREE_000/TREE_003 Stage3a/3b/3c selected binding-row packages plus max-over-8 certificate | Stage3a full-SAT contact, Stage3b no-earlier-overlap for selected binding pair, Stage3c non-hinge residual replay, max-over-8 exact cap for all sign rows, and source-map visibility audit | instant right-germ gate, endpoint-free witness | closed by `s4_theta_star_positive_jam_max_over_8_certificate.json`; closed by `s4_theta_star_source_map_visibility_audit.json` |
| `exact_instant_jam_8_row_gate_source_locked` | signed-row bijection on `{+/-1}^3` transports all row obstructions to target rows | representative instant-jam row artifacts and hard-row overrides | ten representative instant-jam gates cover all 8 sign rows; T4/T6 transport counts cover 60 targets | positive-jam first contact, endpoint-free interval | expose row-bijection wording in theorem prose, but source quantifier is closed |

## Required Fixes Before Theorem Promotion

1. `O-positive-jam-max-over-8-exact-certificate`: closed; for `TREE_000` and `TREE_003`, exact row artifacts now prove no sign row exceeds `t=sqrt(2)`, and the selected Stage3 rows attain `t=sqrt(2)`.
2. `O-selected-hinge-side-map-visibility`: closed; wrapper/B04 selected hinge-side records are exposed by `s4_theta_star_source_map_visibility_audit.json`.
3. `O-support-feature-map-visibility`: closed; positive-jam Stage3 support features, SAT-axis sources, and support witnesses are exposed by `s4_theta_star_source_map_visibility_audit.json`.
4. `O-theorem-name-scope`: use `S4 equal-magnitude theta-star finite-atlas theorem`; do not call this a global motion theorem.

## Correction to T6 Wording

The T6 assembly artifact is a useful finite ledger. T6b treats it as theorem-support evidence, not as a final proof by itself. The previous positive-jam selected-row scoping blocker is now closed by the max-over-8 certificate; remaining obligations are theorem-name/scope wording, not a known missing positive-jam row certificate.
