# S4 CL5 A7d One-Parameter Theorem Wrapper

Date: 2026-06-22
Case: `historical_s4_median_planes`
Status: completed scoped one-parameter zero-thickness wrapper for `TREE_007`
and `TREE_021`.

## Template Basis

This note follows the local development structure under:

```text
the local development template used during preparation
```

Template roles used: claim ledger, proof obligations, public claim boundary,
normalization/source lock, and paper-to-engine traceability.

## Purpose

A7d assembles the completed one-parameter predicate layers into a scoped
theorem-wrapper record.  It is deliberately pair-routed: every unordered piece
pair in each representative tree must be covered by exactly one completed
certificate layer.

The wrapper covers:

```text
theta = 0                       closed-contact endpoint
0 < theta <= 120 degrees        open zero-thickness one-parameter ray
```

with half-angle coordinate:

```text
t = tan(theta/2),  0 < t <= sqrt(3)
```

The exact sign certificates use the rational open superset:

```text
0 < t < 2
```

## Certificate

Generator:

```text
scripts/build_s4_cl5_a7d_one_parameter_theorem_wrapper.py
```

Manifest:

```text
results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/manifests/a7d_one_parameter_theorem_wrapper_manifest.json
```

Record directory:

```text
results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/a7d_one_parameter_theorem_wrapper/records
```

Run summary:

```text
A7d tree wrapper records emitted: 2
A7d wrappers closed: 2/2
predicate route counts: {'B04_SELECTED_HINGE_CONTACT_SIDE': 6, 'B05_COMMON_EDGE_PROJECTION': 4, 'B06_B07_SHARED_FACE_RESIDUAL': 2}
object status counts: {'a7d_one_parameter_ray_wrapper_closed': 2}
```

## Source-Locked Inputs

| Layer | Role | Manifest |
| --- | --- | --- |
| A6 | `B05` residual shared-edge/common-edge closure | `b05_a6_one_parameter_ray_closure_package_manifest.json` |
| A7a | `B06/B07` residual shared-face sign closure | `shared_face_a7a_residual_sturm_certificate_manifest.json` |
| A7b | `B03` ray-vacuity certificate | `b03_a7b_ray_vacuity_certificate_manifest.json` |
| A7c | `B04` selected-hinge contact-side closure | `b04_a7c_selected_hinge_contact_side_certificate_manifest.json` |

The closed endpoint clause is source-locked to `S4_LEMMA_02_CLOSED_ENDPOINT`.
The kinematic/sign convention is source-locked to
`S4_LEMMA_03_KINEMATICS_AND_SIGNS`.

## Pair Routing

The wrapper verifies the following full pair ledger.

### TREE_007

| Pair | Route |
| --- | --- |
| `P0-P1` | `B04_SELECTED_HINGE_CONTACT_SIDE` |
| `P0-P2` | `B04_SELECTED_HINGE_CONTACT_SIDE` |
| `P0-P3` | `B05_COMMON_EDGE_PROJECTION` |
| `P1-P2` | `B05_COMMON_EDGE_PROJECTION` |
| `P1-P3` | `B04_SELECTED_HINGE_CONTACT_SIDE` |
| `P2-P3` | `B06_B07_SHARED_FACE_RESIDUAL` |

### TREE_021

| Pair | Route |
| --- | --- |
| `P0-P1` | `B04_SELECTED_HINGE_CONTACT_SIDE` |
| `P0-P2` | `B06_B07_SHARED_FACE_RESIDUAL` |
| `P0-P3` | `B05_COMMON_EDGE_PROJECTION` |
| `P1-P2` | `B05_COMMON_EDGE_PROJECTION` |
| `P1-P3` | `B04_SELECTED_HINGE_CONTACT_SIDE` |
| `P2-P3` | `B04_SELECTED_HINGE_CONTACT_SIDE` |

There are no route-clean `B03` ordinary non-contact obligations on the
one-parameter representative ray.

## Scoped Wrapper Statement

For the catalogued S4 median-plane pieces, `TREE_007` and `TREE_021` have a
zero-thickness one-parameter ray wrapper on:

```text
theta = 0  plus  0 < theta <= 120 degrees.
```

At `theta=0`, the configuration is the catalogued closed-contact endpoint.  On
the open ray, every unordered piece pair routes to a completed A6/A7a/A7b/A7c
certificate layer.

## Nonclaims

This wrapper does not claim:

1. accepted schema-v1 exact/interval reports;
2. operation enclosures;
3. three-parameter bounded-cell closure;
4. physical hingeability, hinge thickness, CAD, or printability;
5. dynamic connectedness between the two representative rays;
6. global S4 hingeability outside the scoped representatives;
7. positive clearance at `theta=0`;
8. positive clearance for selected hinge pairs;
9. any theorem for domains outside `0<theta<=120`.

## Consequence

The A1-A7d algebraic one-parameter spine is complete at the scoped
zero-thickness wrapper level:

```text
A1 finite SAT axis reduction                    completed draft
A2 symbolic ray model                           completed
A3/A4 Weierstrass/Sturm sign layer              completed
A5 support-switch split                         completed
A6 B05 one-parameter closure                    completed
A7a B06/B07 shared-face sign closure            completed
A7b B03 ray-vacuity                             completed
A7c B04 selected-hinge contact-side closure     completed
A7d one-parameter theorem wrapper               completed
```

The next coherent step is not more B05/B04/B03 mechanics on this ray.  It is a
post-A7d review/red-team of the scoped wrapper, or a deliberate new branch
for 3-parameter bounded cells / physical hingeability.
