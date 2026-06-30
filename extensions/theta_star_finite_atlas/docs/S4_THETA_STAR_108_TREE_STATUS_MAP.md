# S4 theta-star 108-tree status map

## Supersession note - 2026-06-29

This file was originally a pre-finite-angle-transport guardrail map.  Rows
marked `orbit_inherited_label_not_finite_angle_transport` are historical/pre-T4
status, superseded by T4/T5/T6 proof spine, and are not the current theorem-
support status when the T4/T5/T6 artifacts are present and hash-verified.

Checker lock: historical/pre-T4 status, superseded by T4/T5/T6 proof spine.

Current theorem-support status is governed by:

- `S4_THETA_STAR_CERTIFICATE_TRANSPORT_LEMMA.md`, including the T5a update;
- `S4_THETA_STAR_108_TREE_THEOREM_CROSSWALK.md`;
- `s4_theta_star_finite_angle_transport_ledger.json`;
- `s4_theta_star_108_tree_theorem_assembly_gate.json`;
- `s4_theta_star_108_tree_theorem_assembly_gate_replay.json`.

If those artifacts are absent or not hash-verified, this file reverts to a
blocker.  If they are present and hash-verified, this file is a historical
guardrail/status map only.


Status: documentation/guardrail map.  Not a finite-angle transport theorem.

## Summary

```text
tree_count: 108
orbit_count: 18
first_order_counts_over_108: {'first_order_interior_open': 80, 'first_order_boundary_only_candidate': 24, 'first_order_cone_infeasible_candidate': 4}
theta_star_representative_status_counts_over_108: {'jam_at_positive_t': 8, 'full_open_to_120': 36, 'instant_jam_t0': 60, 'full_open_to_120_public_scope': 4}
theta_star_scope_counts_over_108: {'representative_exact_status': 18, 'orbit_inherited_label_not_finite_angle_transport': 90}
root_preserving_counts_over_108: {'root_preserving': 36, 'root_moving': 72}
```

## Claim Boundary

- does not prove finite-angle theta-star transport from representatives to all 108 trees
- does not prove continuous non-equal or three-parameter route existence/nonexistence
- does not update the public paper
- non-representative theta-star statuses are orbit-inherited labels until a finite-angle transport theorem exists

## Red Flags For Readers

- `representative_exact_status` means the row is one of the 18 representatives and has the listed local artifact status.
- `orbit_inherited_label_not_finite_angle_transport` means the tree lies in the representative's first-order structural orbit; it is not yet a signed finite-angle theta-star transport certificate.
- Equal-magnitude `instant_jam_t0` is not a three-parameter obstruction.  `TREE_044` remains the explicit guardrail for this distinction.

## Orbit Summary

| orbit | representative | size | first-order class | theta-star status | row certificate | tree ids |
| --- | --- | ---: | --- | --- | --- | --- |
| 0 | `TREE_001` | 8 | `first_order_interior_open` | `full_open_to_120` | `exact_free_witness_candidate` | `TREE_001, TREE_006, TREE_010, TREE_022, TREE_036, TREE_048, TREE_084, TREE_090` |
| 1 | `TREE_002` | 8 | `first_order_interior_open` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_002, TREE_012, TREE_038, TREE_050, TREE_064, TREE_076, TREE_087, TREE_099` |
| 2 | `TREE_004` | 8 | `first_order_interior_open` | `full_open_to_120` | `exact_free_witness_candidate` | `TREE_004, TREE_019, TREE_028, TREE_030, TREE_033, TREE_045, TREE_085, TREE_091` |
| 3 | `TREE_005` | 8 | `first_order_interior_open` | `full_open_to_120` | `exact_free_witness_candidate` | `TREE_005, TREE_020, TREE_035, TREE_040, TREE_057, TREE_072, TREE_097, TREE_103` |
| 4 | `TREE_008` | 8 | `first_order_boundary_only_candidate` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_008, TREE_011, TREE_013, TREE_023, TREE_063, TREE_075, TREE_096, TREE_102` |
| 5 | `TREE_016` | 8 | `first_order_interior_open` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_016, TREE_025, TREE_042, TREE_051, TREE_055, TREE_060, TREE_086, TREE_092` |
| 6 | `TREE_017` | 8 | `first_order_boundary_only_candidate` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_017, TREE_026, TREE_062, TREE_067, TREE_069, TREE_078, TREE_098, TREE_104` |
| 7 | `TREE_029` | 8 | `first_order_interior_open` | `full_open_to_120` | `exact_free_witness_candidate` | `TREE_029, TREE_032, TREE_039, TREE_047, TREE_058, TREE_073, TREE_088, TREE_100` |
| 8 | `TREE_044` | 8 | `first_order_interior_open` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_044, TREE_053, TREE_056, TREE_066, TREE_070, TREE_079, TREE_089, TREE_101` |
| 9 | `TREE_000` | 4 | `first_order_interior_open` | `jam_at_positive_t` | `stage3a_stage3b_stage3c_local_tree_package` | `TREE_000, TREE_037, TREE_049, TREE_081` |
| 10 | `TREE_003` | 4 | `first_order_interior_open` | `jam_at_positive_t` | `stage3a_stage3b_stage3c_local_tree_package` | `TREE_003, TREE_018, TREE_034, TREE_094` |
| 11 | `TREE_007` | 4 | `first_order_interior_open` | `full_open_to_120_public_scope` | `public_wrapper_scope_certificate` | `TREE_007, TREE_009, TREE_021, TREE_093` |
| 12 | `TREE_014` | 4 | `first_order_boundary_only_candidate` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_014, TREE_065, TREE_077, TREE_105` |
| 13 | `TREE_015` | 4 | `first_order_boundary_only_candidate` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_015, TREE_024, TREE_061, TREE_095` |
| 14 | `TREE_027` | 4 | `first_order_interior_open` | `full_open_to_120` | `exact_free_witness_candidate` | `TREE_027, TREE_031, TREE_046, TREE_082` |
| 15 | `TREE_041` | 4 | `first_order_interior_open` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_041, TREE_059, TREE_074, TREE_106` |
| 16 | `TREE_043` | 4 | `first_order_interior_open` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_043, TREE_052, TREE_054, TREE_083` |
| 17 | `TREE_068` | 4 | `first_order_cone_infeasible_candidate` | `instant_jam_t0` | `instant_jam_row_gate` | `TREE_068, TREE_071, TREE_080, TREE_107` |

## Full 108-Tree Map

| tree | orbit | representative | root preserving | first-order class | theta-star representative status | status scope | t* candidate | row certificate | 3-param status |
| --- | ---: | --- | --- | --- | --- | --- | --- | --- | --- |
| `TREE_000` | 9 | `TREE_000` | `True` | `first_order_interior_open` | `jam_at_positive_t` | `representative_exact_status` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_001` | 0 | `TREE_001` | `True` | `first_order_interior_open` | `full_open_to_120` | `representative_exact_status` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_002` | 1 | `TREE_002` | `True` | `first_order_interior_open` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_003` | 10 | `TREE_003` | `True` | `first_order_interior_open` | `jam_at_positive_t` | `representative_exact_status` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_004` | 2 | `TREE_004` | `True` | `first_order_interior_open` | `full_open_to_120` | `representative_exact_status` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_005` | 3 | `TREE_005` | `True` | `first_order_interior_open` | `full_open_to_120` | `representative_exact_status` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_006` | 0 | `TREE_001` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_007` | 11 | `TREE_007` | `True` | `first_order_interior_open` | `full_open_to_120_public_scope` | `representative_exact_status` | `sqrt(3) endpoint reached` | `public_wrapper_scope_certificate` | `not_classified_by_this_ledger` |
| `TREE_008` | 4 | `TREE_008` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_009` | 11 | `TREE_007` | `True` | `first_order_interior_open` | `full_open_to_120_public_scope` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `public_wrapper_scope_certificate` | `not_classified_by_this_ledger` |
| `TREE_010` | 0 | `TREE_001` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_011` | 4 | `TREE_008` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_012` | 1 | `TREE_002` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_013` | 4 | `TREE_008` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_014` | 12 | `TREE_014` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_015` | 13 | `TREE_015` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_016` | 5 | `TREE_016` | `True` | `first_order_interior_open` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_017` | 6 | `TREE_017` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_018` | 10 | `TREE_003` | `False` | `first_order_interior_open` | `jam_at_positive_t` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_019` | 2 | `TREE_004` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_020` | 3 | `TREE_005` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_021` | 11 | `TREE_007` | `False` | `first_order_interior_open` | `full_open_to_120_public_scope` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `public_wrapper_scope_certificate` | `not_classified_by_this_ledger` |
| `TREE_022` | 0 | `TREE_001` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_023` | 4 | `TREE_008` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_024` | 13 | `TREE_015` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_025` | 5 | `TREE_016` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_026` | 6 | `TREE_017` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_027` | 14 | `TREE_027` | `True` | `first_order_interior_open` | `full_open_to_120` | `representative_exact_status` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_028` | 2 | `TREE_004` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_029` | 7 | `TREE_029` | `True` | `first_order_interior_open` | `full_open_to_120` | `representative_exact_status` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_030` | 2 | `TREE_004` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_031` | 14 | `TREE_027` | `True` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_032` | 7 | `TREE_029` | `True` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_033` | 2 | `TREE_004` | `True` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_034` | 10 | `TREE_003` | `True` | `first_order_interior_open` | `jam_at_positive_t` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_035` | 3 | `TREE_005` | `True` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_036` | 0 | `TREE_001` | `True` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_037` | 9 | `TREE_000` | `True` | `first_order_interior_open` | `jam_at_positive_t` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_038` | 1 | `TREE_002` | `True` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_039` | 7 | `TREE_029` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_040` | 3 | `TREE_005` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_041` | 15 | `TREE_041` | `True` | `first_order_interior_open` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_042` | 5 | `TREE_016` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_043` | 16 | `TREE_043` | `True` | `first_order_interior_open` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_044` | 8 | `TREE_044` | `True` | `first_order_interior_open` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_045` | 2 | `TREE_004` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_046` | 14 | `TREE_027` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_047` | 7 | `TREE_029` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_048` | 0 | `TREE_001` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_049` | 9 | `TREE_000` | `False` | `first_order_interior_open` | `jam_at_positive_t` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_050` | 1 | `TREE_002` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_051` | 5 | `TREE_016` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_052` | 16 | `TREE_043` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_053` | 8 | `TREE_044` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_054` | 16 | `TREE_043` | `True` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_055` | 5 | `TREE_016` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_056` | 8 | `TREE_044` | `True` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_057` | 3 | `TREE_005` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_058` | 7 | `TREE_029` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_059` | 15 | `TREE_041` | `True` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_060` | 5 | `TREE_016` | `True` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_061` | 13 | `TREE_015` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_062` | 6 | `TREE_017` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_063` | 4 | `TREE_008` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_064` | 1 | `TREE_002` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_065` | 12 | `TREE_014` | `True` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_066` | 8 | `TREE_044` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_067` | 6 | `TREE_017` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_068` | 17 | `TREE_068` | `True` | `first_order_cone_infeasible_candidate` | `instant_jam_t0` | `representative_exact_status` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_069` | 6 | `TREE_017` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_070` | 8 | `TREE_044` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_071` | 17 | `TREE_068` | `True` | `first_order_cone_infeasible_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_072` | 3 | `TREE_005` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_073` | 7 | `TREE_029` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_074` | 15 | `TREE_041` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_075` | 4 | `TREE_008` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_076` | 1 | `TREE_002` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_077` | 12 | `TREE_014` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_078` | 6 | `TREE_017` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_079` | 8 | `TREE_044` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_080` | 17 | `TREE_068` | `False` | `first_order_cone_infeasible_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_081` | 9 | `TREE_000` | `False` | `first_order_interior_open` | `jam_at_positive_t` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_082` | 14 | `TREE_027` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_083` | 16 | `TREE_043` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_084` | 0 | `TREE_001` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_085` | 2 | `TREE_004` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_086` | 5 | `TREE_016` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_087` | 1 | `TREE_002` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_088` | 7 | `TREE_029` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_089` | 8 | `TREE_044` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_090` | 0 | `TREE_001` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_091` | 2 | `TREE_004` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_092` | 5 | `TREE_016` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_093` | 11 | `TREE_007` | `False` | `first_order_interior_open` | `full_open_to_120_public_scope` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `public_wrapper_scope_certificate` | `not_classified_by_this_ledger` |
| `TREE_094` | 10 | `TREE_003` | `False` | `first_order_interior_open` | `jam_at_positive_t` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(2)` | `stage3a_stage3b_stage3c_local_tree_package` | `unresolved` |
| `TREE_095` | 13 | `TREE_015` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_096` | 4 | `TREE_008` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_097` | 3 | `TREE_005` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_098` | 6 | `TREE_017` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_099` | 1 | `TREE_002` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_100` | 7 | `TREE_029` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_101` | 8 | `TREE_044` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `non_equal_open_direction_known_diagnostic` |
| `TREE_102` | 4 | `TREE_008` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_103` | 3 | `TREE_005` | `False` | `first_order_interior_open` | `full_open_to_120` | `orbit_inherited_label_not_finite_angle_transport` | `sqrt(3) endpoint reached` | `exact_free_witness_candidate` | `not_classified_by_endpoint_witness` |
| `TREE_104` | 6 | `TREE_017` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_105` | 12 | `TREE_014` | `False` | `first_order_boundary_only_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_106` | 15 | `TREE_041` | `False` | `first_order_interior_open` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |
| `TREE_107` | 17 | `TREE_068` | `False` | `first_order_cone_infeasible_candidate` | `instant_jam_t0` | `orbit_inherited_label_not_finite_angle_transport` | `0` | `instant_jam_row_gate` | `equal_ray_jam_only` |

## Checks

- PASS: rep ledger status pass (pass)
- PASS: transport ledger status pass (pass)
- PASS: 108 tree records (108)
- PASS: no duplicate tree ids ([])
- PASS: no missing TREE_000..TREE_107 ids ([])
- PASS: 18 orbit summaries (18)
- PASS: representative status has no unresolved label ({'jam_at_positive_t': 8, 'full_open_to_120': 36, 'instant_jam_t0': 60, 'full_open_to_120_public_scope': 4})
