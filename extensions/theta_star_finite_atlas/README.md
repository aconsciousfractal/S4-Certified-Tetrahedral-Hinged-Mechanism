# S4 theta-star finite-atlas extension

Status: addendum-review candidate on branch `theta-star-addendum-review`.

This directory stages the local S4 theta-star finite-atlas theorem candidate for
external mathematical review.  It is intentionally separate from the current
paper theorem and from the already released route-wrapper package for
`TREE_007`/`TREE_021`.

## Candidate statement under review

For the zero-thickness S4 median-plane mechanism, restricted to the finite
atlas of 108 connected three-hinge trees and equal-magnitude one-parameter
opening rays, each tree has an exact theta-star value in the scoped atlas.  The
local classification currently has the following shape:

```text
full_open_to_120                 36
full_open_to_120_public_scope      4
jam_at_positive_t                 8
theta_star_zero / instant_jam     60
```

Exact theta-star values observed in the local package:

```text
t = sqrt(3) endpoint reached      40
t = sqrt(2) positive jam           8
t = 0 instant jam                 60
```

This is a finite-atlas theorem candidate, not a physical mechanism theorem.

## What this extension is not

It is not a proof of positive-thickness hingeability, fabrication, a global
collision-free physical motion, a three-parameter motion theorem, a non-equal
motion theorem, or a general hinged-dissection/reversible-net theorem.

## Roadmap to paper/addendum

The concrete conversion plan from review package to mathematical paper is in `ROADMAP_TO_PAPER.md`.  The next blocker is resolving the historical `STATUS_MAP` conflict before any TeX/PDF promotion.

## Review order

1. Read `THETA_STAR_CLAIM_BOUNDARY.md`.
2. Read `THETA_STAR_REPRODUCE.md`.
3. Inspect `artifacts/README.md` and the imported artifacts once copied.
4. Review the proof draft/crosswalk files when they are imported from the local
   workspace.
5. Only after a successful mathematical red-team should this extension be
   considered for a separate addendum TeX/PDF.
## Review entry point

The human-readable draft is `paper_draft/theta_star_finite_atlas.tex`; the built PDF is `paper_draft/theta_star_finite_atlas.pdf`. The `paper_package/` directory is supporting proof-spine material, not the paper itself.
