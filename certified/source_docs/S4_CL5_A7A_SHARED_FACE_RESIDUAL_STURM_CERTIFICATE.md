# S4 CL5 A7a: Shared-face residual Sturm certificate

Status: completed formula-sign certificate; not accepted reports.

## Scope

A7a certifies the Lemma-06 residual shared-face formula for the two current
one-parameter shared-face targets:

```text
TREE_007 P2-P3
TREE_021 P0-P2
```

The source formula is the unnormalized shared-face triple product

```text
((1 - cos(theta)) * sin(theta)) / 4
  = sin(theta/2)^3 * cos(theta/2).
```

With the Weierstrass substitution `t = tan(theta/2)`, this becomes

```text
t^3 / (1 + t^2)^2.
```

The certificate proves positivity on the open rational superset
`0 < t < 2`, which contains the audited S4 one-parameter ray domain
`0 < t <= sqrt(3)` (`0 < theta <= 120 degrees`).

## Generated Artifacts

```text
scripts/build_s4_cl5_a7a_shared_face_residual_sturm_certificate.py
results/historical_s4_median_planes/exact_interval/shared_face_residual/a7a_shared_face_residual_sturm_certificate/
results/historical_s4_median_planes/exact_interval/shared_face_residual/manifests/shared_face_a7a_residual_sturm_certificate_manifest.json
```

## Result

```text
A7a records emitted: 2
shared-face residual formula positive: 2/2
accepted real reports: 0
object status counts:
  a7a_shared_face_residual_formula_positive_on_open_ray_superset: 2
```

The shared certificate is:

```text
numerator:   t^3
denominator: (t^2 + 1)^2
interval:    0 < t < 2
```

Sturm root counts certify that neither numerator nor denominator has an open
root on `0 < t < 2`; the sample point `t=1` fixes both signs as positive.  The
endpoint root `t=0` is excluded because it is the closed-contact boundary.

## Nonclaims

A7a does not emit schema-v1 accepted reports.  It does not prove B03
strict-clearance SAT, B04 selected-hinge contact side, operation enclosures,
three-parameter bounded-cell closure, physical hingeability, or theorem
promotion.

It closes only the shared-face residual formula-sign layer needed by the
one-parameter completion program.

## Next Tasks

The exact one-parameter ray still needs:

```text
A7b route-clean B03 clearance SAT layer (completed vacuously on the ray)
A7c selected-hinge B04 contact-side exact lemma (completed)
A7d one-parameter theorem wrapper after A7c
```

