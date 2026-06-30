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

## Current review draft

The addendum-review draft now exists as a real TeX/PDF artifact:

```text
paper_draft/theta_star_finite_atlas.tex
paper_draft/theta_star_finite_atlas.pdf
paper_draft/theta_star_finite_atlas_flat.tex
paper_draft/refs.bib
```

The bibliography is local to the addendum draft.  LaTeX auxiliary files such as
`*.bbl` and `*.blg` are generated during build and are intentionally not tracked.
The `paper_package/` directory is supporting proof-spine material, not the paper
itself.

## Roadmap to paper/addendum

The concrete conversion and promotion plan is in `ROADMAP_TO_PAPER.md`.  The
remaining decision is not whether TeX/PDF exists; it is whether external
mathematical red-team accepts the proof chain strongly enough to promote this
review draft as an addendum or companion paper.

## Review order

1. Start from `EXTERNAL_RED_TEAM_HANDOFF.md`.
2. Read `paper_draft/theta_star_finite_atlas.pdf` or
   `paper_draft/theta_star_finite_atlas_flat.tex`.
3. Read `THETA_STAR_CLAIM_BOUNDARY.md`.
4. Run the checkers listed in `THETA_STAR_REPRODUCE.md`.
5. Inspect `paper_package/artifacts/proof_spine/` for the supporting records.
6. Treat the extension as a mathematical review target, not as physical or
   fabrication evidence.
