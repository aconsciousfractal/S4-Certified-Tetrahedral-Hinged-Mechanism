> **Package provenance note.** This is a historical or future-scope source
> snapshot retained for audit trail only. It may contain words such as
> `draft`, `blocker`, or `Not a CL5 theorem`; those statements are not public
> claims of the current paper-as-public-package and do not widen the scoped
> zero-thickness theorem.

# S4 Lemma 04: Signed-Ray Representative Classes

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-04-SIGNED-RAY-CLASSES-2026-06-21`
review status: local lemma draft

## Purpose

This lemma records the finite signed-ray class reduction used by the S4 zero-thickness package.

It justifies why the later certificate work may use `TREE_007` and `TREE_021` as representatives of the two root-preserving signed-ray classes among the four all-ambient-edge candidates.

This is not a dynamic connectedness result. It is not a collision-free path result. It is not a physical hingeability result.

## Source Anchors

- `docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
- `results/historical_s4_median_planes/hinge_tree_report.json`
- `results/historical_s4_median_planes/ambient_edge_dense_refinement_report.json`
- `results/historical_s4_median_planes/signed_ray_symmetry_report.json`
- `results/historical_s4_median_planes/two_class_representative_audit_report.json`
- `scripts/audit_historical_s4_signed_ray_symmetry.py`

## Candidate Set

Let `A` be the finite set of all-ambient-edge S4 hinge trees:

```text
A = {TREE_007, TREE_009, TREE_021, TREE_093}.
```

The hinge axes and ray signs recorded by the dense refinement reports are:

| Tree | Hinge IDs | Signed ray |
| --- | --- | --- |
| `TREE_007` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `(+,+,-)` |
| `TREE_009` | `H0_A_M_AB`, `H4_C_M_CD`, `H9_B_M_AB` | `(+,+,-)` on the listed hinge IDs |
| `TREE_021` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `(+,-,+)` |
| `TREE_093` | `H4_C_M_CD`, `H7_D_M_CD`, `H9_B_M_AB` | `(+,+,-)` on the listed hinge IDs |

All four trees use three ambient-edge subsegment axes and no internal hinge axis.

## Symmetry Group

Let `G` be the vertex-permutation group of the tetrahedron preserving the unordered opposite-edge pair `{AB, CD}`.

The signed-ray symmetry report enumerates:

```text
|G| = 8
checked transforms = 4 source trees * 8 permutations = 32
```

For each `g in G`, the induced affine map transports:

1. the hinge axis labels;
2. the rooted piece labels;
3. the oriented hinge-axis direction;
4. the sign of each one-parameter hinge angle.

Root-preserving equivalence is reported separately and requires the induced piece map to keep the root piece `P0` fixed.

## Sign Transport Rule

For a source hinge with signed angle `s`, its transported sign is:

```text
target_angle_sign = determinant_sign(isometry) * axis_orientation_sign * s
```

where:

- `determinant_sign(isometry) = +1` for a proper tetrahedral isometry;
- `determinant_sign(isometry) = -1` for an improper/reflectional tetrahedral isometry;
- `axis_orientation_sign = +1` when the mapped oriented hinge axis agrees with the target hinge-axis label orientation;
- `axis_orientation_sign = -1` when the mapped oriented hinge axis is opposite to the target hinge-axis label orientation.

Two signed rays match when the transported hinge-axis set and every transported sign agree with the target tree data.

## Statement

Under the finite action of `G`, the root-preserving signed-ray equivalence classes in `A` are exactly:

```text
C_A = {TREE_007, TREE_009}
C_B = {TREE_021, TREE_093}
```

Therefore the pair:

```text
TREE_007, TREE_021
```

is a valid representative set for the two root-preserving signed-ray classes among the four all-ambient-edge candidates.

There is no root-preserving signed-ray equivalence, under this finite symmetry group and this sign-transport convention, between a tree in `C_A` and a tree in `C_B`.

## Finite Proof

The proof is a finite enumeration over the explicitly stated group `G`.

The report `signed_ray_symmetry_report.json` checks every pair:

```text
(source tree in A, permutation in G)
```

and computes the transported hinge labels and signs using the sign rule above.

It reports:

```text
signed_ray_exact_match_count = 8
root_preserving_signed_ray_exact_match_count = 8
signed_ray_orbit_classes_ignoring_root = [[TREE_007, TREE_009], [TREE_021, TREE_093]]
signed_ray_orbit_classes_root_preserving = [[TREE_007, TREE_009], [TREE_021, TREE_093]]
all_signed_rays_same_orbit_ignoring_root = false
all_signed_rays_same_orbit_with_root_preserved = false
```

The within-class witnesses are:

| Source | Target | Vertex permutation | Determinant | Root preserved |
| --- | --- | --- | --- | --- |
| `TREE_007` | `TREE_007` | identity | `+1` | yes |
| `TREE_007` | `TREE_009` | `A->C, B->D, C->A, D->B` | `+1` | yes |
| `TREE_009` | `TREE_009` | identity | `+1` | yes |
| `TREE_009` | `TREE_007` | `A->C, B->D, C->A, D->B` | `+1` | yes |
| `TREE_021` | `TREE_021` | identity | `+1` | yes |
| `TREE_021` | `TREE_093` | `A->C, B->D, C->A, D->B` | `+1` | yes |
| `TREE_093` | `TREE_093` | identity | `+1` | yes |
| `TREE_093` | `TREE_021` | `A->C, B->D, C->A, D->B` | `+1` | yes |

The reported reachability matrix has no signed-ray match from either `C_A` tree to either `C_B` tree, and no signed-ray match from either `C_B` tree to either `C_A` tree. Since all `32` allowed finite transforms are enumerated, the two classes above are exhaustive for this finite group action.

This proves the finite class-reduction statement.

## Relation To The Representative Certificates

The two-class representative audit selects:

```text
C_A representative: TREE_007
C_B representative: TREE_021
```

This lemma justifies that selection at the signed-ray symmetry level only. Later ray-cell, refined-edge, bounded-cell, and open-limit certificate claims must still be stated for the representative motions themselves and must not be inferred from this lemma alone.

## Explicit Non-Claims

This lemma does not prove:

- collision freedom on any angle interval;
- clearance at `theta = 0`;
- a continuous path connecting `C_A` and `C_B`;
- dynamic disconnection between `C_A` and `C_B`;
- global S4 hingeability;
- physical hingeability with hinge thickness, offsets, tolerances, CAD, or printability.

The phrase "two signed-ray classes" here means only two classes under the stated finite vertex-permutation action and the stated sign-transport rule.

## Exactness Boundary

The enumeration is finite and uses affine maps induced by vertex permutations of the regular tetrahedron. The class claim is therefore a finite algebraic/symbolic reduction once the input hinge labels and signs are accepted.

However, the inputs are still workspace certificate data. Before theorem promotion, the final paper package must lock the definitions of:

1. the tetrahedron vertex labels;
2. the oriented hinge-axis label convention;
3. the root piece convention;
4. the sign transport rule;
5. the exact finite group `G`.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
