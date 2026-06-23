# S4 Lemma 03: Hinge-Tree Kinematics And Sign Conventions

Date: 2026-06-21
Case: `historical_s4_median_planes`
Lemma ID: `S4-LEMMA-03-KINEMATICS-SIGNS-2026-06-21`
review gate: R6c third mathematical lemma draft

## Purpose

This document fixes the mathematical kinematic model used for the two S4
representative hinge trees:

```text
TREE_007
TREE_021
```

It defines root piece, selected hinge axes, tree propagation, angle units, and
signed-ray conventions.

It does not prove collision-freedom, clearance, bounded-cell coverage, dynamic
connectedness, physical hinge thickness, or global hingeability.

## Source Anchors

- `docs/S4_LEMMA_01_GEOMETRY_AND_TILING.md`
- `docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`
- `results/historical_s4_median_planes/hinge_candidate_report.json`
- `results/historical_s4_median_planes/hinge_tree_report.json`
- `results/historical_s4_median_planes/two_class_representative_audit_report.json`
- `results/historical_s4_median_planes/theta_zero_closed_contact_certificate_report.json`
- `scripts/mechanical_audit_lib.py::axis_rotation_transform`
- `scripts/mechanical_audit_lib.py::transforms_for_hinge_tree`
- `scripts/audit_historical_s4_two_class_ray_cell_guard.py::transforms_for_degrees`

The proof below is a mathematical restatement of the rigid-transform model. The
finite reports are consistency anchors for IDs, axes, signs, and root
conventions.

## Static Input From Lemmas 01 And 02

The closed pieces are:

```text
P0 = conv(A, M_AB, C, M_CD)
P1 = conv(A, M_AB, D, M_CD)
P2 = conv(B, M_AB, C, M_CD)
P3 = conv(B, M_AB, D, M_CD)
```

At `theta = 0`, Lemma 02 proves that these pieces form the catalogued closed
contact endpoint. Lemma 03 starts from that endpoint and defines how a rooted
hinge tree assigns rigid transforms to pieces.

## Selected Hinge Axes

The selected ambient-edge subsegment axes are:

| Hinge ID | Pieces | Contact | Oriented axis | Ambient support |
| --- | --- | --- | --- | --- |
| `H0_A_M_AB` | `P0-P1` | `C0` shared face | `A -> M_AB` | edge `AB` |
| `H4_C_M_CD` | `P0-P2` | `C1` shared face | `C -> M_CD` | edge `CD` |
| `H7_D_M_CD` | `P1-P3` | `C4` shared face | `D -> M_CD` | edge `CD` |
| `H9_B_M_AB` | `P2-P3` | `C5` shared face | `B -> M_AB` | edge `AB` |

All four axes have length `1/2` and are boundary ambient-edge subsegments in
the audited model.

The two representative trees are:

| Tree | Hinge IDs | Piece graph |
| --- | --- | --- |
| `TREE_007` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `P0-P1`, `P0-P2`, `P1-P3` |
| `TREE_021` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `P0-P1`, `P1-P3`, `P2-P3` |

Both graphs are trees on the four pieces. The root convention is:

```text
root_piece = P0.
```

## Rooted Piece Paths

With root `P0`, the unique propagation paths are:

| Tree | Piece | Rooted path |
| --- | --- | --- |
| `TREE_007` | `P0` | empty |
| `TREE_007` | `P1` | `P0 --H0_A_M_AB--> P1` |
| `TREE_007` | `P2` | `P0 --H4_C_M_CD--> P2` |
| `TREE_007` | `P3` | `P0 --H0_A_M_AB--> P1 --H7_D_M_CD--> P3` |
| `TREE_021` | `P0` | empty |
| `TREE_021` | `P1` | `P0 --H0_A_M_AB--> P1` |
| `TREE_021` | `P3` | `P0 --H0_A_M_AB--> P1 --H7_D_M_CD--> P3` |
| `TREE_021` | `P2` | `P0 --H0_A_M_AB--> P1 --H7_D_M_CD--> P3 --H9_B_M_AB--> P2` |

Because each selected graph is a tree, each piece has exactly one rooted path.
This is the key well-definedness condition for transform propagation.

## Rigid Rotation Convention

Let an oriented hinge axis be represented by two distinct points `a,b` in the
closed endpoint coordinates. Let `u = (b-a)/|b-a|`.

For an angle `phi` in radians, define `Q_u(phi)` by Rodrigues' formula:

```text
Q_u(phi) x
= x cos(phi)
 + (u x x) sin(phi)
 + u (u dot x) (1 - cos(phi)).
```

The rigid rotation about the affine line through `a,b` is

```text
Rot(a,b,phi)(x) = Q_u(phi) x + a - Q_u(phi) a.
```

This fixes every point on the hinge line:

```text
if x in line(a,b), then Rot(a,b,phi)(x) = x.
```

The audit's `axis_rotation_transform(p0,p1,angle_radians)` implements exactly
this affine rotation form.

## Transform Propagation

Each piece transform is written as

```text
T_i(x) = R_i x + t_i,
```

with `R_i` orthogonal and orientation-preserving, and `t_i` a translation.

Set the root transform to identity:

```text
T_0(x) = x.
```

Suppose the rooted tree edge from parent piece `Pp` to child piece `Pc` uses
hinge `h` with endpoint labels `a_h,b_h` and angle `phi_h`.

The parent places the hinge axis in world coordinates at:

```text
a_world = T_p(a_h)
b_world = T_p(b_h).
```

Then the child transform is:

```text
T_c = Rot(a_world, b_world, phi_h) o T_p.
```

Equivalently,

```text
T_c(x) = Rot(a_world, b_world, phi_h)(T_p(x)).
```

This is exactly the propagation rule used by
`transforms_for_hinge_tree`: breadth-first traversal from `P0`, transformed
axis endpoints, axis rotation, then composition with the parent transform.

## Hinge Constraint Preservation

For every selected tree edge, the parent and child transforms agree on the
hinge axis.

Indeed, if `x` lies on the closed endpoint hinge line through `a_h,b_h`, then
`T_p(x)` lies on the world line through `a_world,b_world`. Since
`Rot(a_world,b_world,phi_h)` fixes that world line,

```text
T_c(x)
= Rot(a_world,b_world,phi_h)(T_p(x))
= T_p(x).
```

Thus the two pieces remain continuously joined along the selected hinge axis
in the zero-thickness rigid model.

This proves the kinematic hinge constraint only for selected axes. It says
nothing about non-hinge contacts, self-intersection, or clearance.

## Degree/Radian Convention

External reports and user-facing audit cells record hinge coordinates in
degrees.

The transform formula uses radians. The conversion is:

```text
phi_h = pi * d_h / 180,
```

where `d_h` is the signed angle in degrees for hinge `h`.

The helper `transforms_for_degrees` applies this conversion before calling the
rigid-transform propagation.

## Signed-Ray Convention

A signed ray assigns one scalar magnitude `theta` in degrees and a sign
`s_h in {+1,-1}` to each hinge in the tree:

```text
d_h(theta) = s_h * theta.
```

The certified representative signed rays use the hinge order recorded in each
tree:

| Tree | Ordered hinge IDs | Signs |
| --- | --- | --- |
| `TREE_007` | `H0_A_M_AB`, `H4_C_M_CD`, `H7_D_M_CD` | `+1`, `+1`, `-1` |
| `TREE_021` | `H0_A_M_AB`, `H7_D_M_CD`, `H9_B_M_AB` | `+1`, `-1`, `+1` |

Thus:

```text
TREE_007:
d_H0(theta) =  theta
d_H4(theta) =  theta
d_H7(theta) = -theta

TREE_021:
d_H0(theta) =  theta
d_H7(theta) = -theta
d_H9(theta) =  theta
```

The open-ray certificates use `0 < theta <= 120` degrees. Lemma 03 only fixes
the coordinate convention for that ray; it does not prove that any positive
`theta` is collision-free.

## Zero-Angle Identity

At `theta = 0`, every signed hinge angle is zero:

```text
d_h(0) = 0
phi_h(0) = 0.
```

Then `Q_u(0)` is the identity matrix and

```text
Rot(a,b,0)(x) = x.
```

By induction along the rooted tree:

```text
T_0 = identity
T_c = identity o T_p = identity
```

for every child piece. Therefore every piece transform in `TREE_007` and
`TREE_021` is identity at `theta = 0`, matching Lemma 02 and the theta-zero
certificate.

## Well-Definedness Lemma

For each of `TREE_007` and `TREE_021`, and for every assignment of real signed
hinge angles to the selected hinge IDs, the rooted propagation rule above
assigns exactly one rigid transform to each of `P0,P1,P2,P3`.

Proof:

1. each selected graph has four vertices and three edges;
2. each selected graph is connected by the listed rooted paths;
3. hence each selected graph is a tree;
4. a tree has a unique simple path from the root to every vertex;
5. the propagation rule assigns the root transform first and then one child
   transform along each path edge;
6. composition of rigid rotations and translations is a rigid transform.

Therefore the scripted model and the mathematical model define the same
piecewise rigid zero-thickness hinge-tree kinematics for these two
representatives.

## Certificate Consistency Check

The exact model above matches the report fields:

| Report | Matching kinematic fact |
| --- | --- |
| `hinge_candidate_report.json` | selected axes, endpoint labels, ambient-edge support |
| `hinge_tree_report.json` | `TREE_007` and `TREE_021` hinge IDs and piece graphs |
| `two_class_representative_audit_report.json` | signed-ray signs for both representatives |
| `theta_zero_closed_contact_certificate_report.json` | zero-angle transforms are identity on vertices |

The collision-free status in later reports is not used in this lemma.

## Exactness Status

This lemma is exact at the level of rigid-transform definitions:

- the axes are endpoint-labelled line segments from Lemma 01 geometry;
- axis rotations are standard `SE(3)` transformations;
- the tree path from root `P0` is unique;
- degree-to-radian conversion is explicit;
- zero-angle identity is exact.

The lemma does not address floating SAT tolerances, sampled collision reports,
formula guards, interval coverage, or physical clearances.

## Claim Boundary

This lemma supports only:

```text
TREE_007 and TREE_021 have a well-defined rooted zero-thickness rigid-hinge
kinematic model with the stated signed-ray coordinates.
```

Do not infer:

```text
collision-free positive-angle motion
open-ray certificate validity
bounded-cell certificate validity
dynamic connectedness between signed-ray classes
positive clearance at theta = 0
physical hinge thickness, offsets, CAD, or printability
global S4 hingeability
CL5 theorem promotion
```

Those are separate proof obligations.

## R6c Result

This draft resolves the third initial writing target from
`docs/S4_MATHEMATICAL_LEMMA_PLAN.md`:

```text
L3 Hinge-tree kinematics
S4-PO-003 kinematics/sign conventions
```

It does not resolve `S4-PO-004`, because representative-class reduction needs
the finite symmetry/group-action argument in a separate lemma.

## Next Task

Prossima task: implement `scripts/generate_s4_cl5_b03_strict_convex_sat_reports.py` in diagnostic-only mode, wiring real B03 report skeletons to the replay checker without setting accepted true for S4 data.
