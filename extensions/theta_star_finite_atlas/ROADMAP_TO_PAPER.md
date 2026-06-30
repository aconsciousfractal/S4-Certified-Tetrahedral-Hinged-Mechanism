# Roadmap to a theta-star paper/addendum

Status: promoted public companion addendum.  This roadmap records what is now
closed, what remains deliberately out of scope, and what optional future work
would require a separate release decision.

The addendum is intentionally scoped to the zero-thickness, equal-magnitude,
one-parameter finite S4 atlas over 108 connected three-hinge trees.

## Current verified state

The extension has a real addendum paper and support package:

```text
paper_draft/theta_star_finite_atlas.tex
paper_draft/theta_star_finite_atlas.pdf
paper_draft/theta_star_finite_atlas_flat.tex
paper_draft/refs.bib
paper_package/artifacts/proof_spine/
```

The theorem shape supported by the proof spine is:

```text
final classes: 8 positive-jam, 36 endpoint-free, 60 instant-jam, 4 wrapper-scope
exact t*:      8 at sqrt(2), 40 endpoint-reaching at sqrt(3), 60 at 0
scope:         zero-thickness, equal-magnitude, one-parameter finite atlas
```

The addendum remains separate from the main paper theorem.  The main paper only
points to it as a companion addendum and does not use it to broaden its own
claim boundary.

## Closed promotion gates

```text
- stale status-map labels are superseded by the current T6 proof spine;
- proof-spine artifacts are materialized under paper_package/artifacts/proof_spine/;
- finite-angle conjugacy, signed transport, eight-row bijection, theta-star
  invariance, and 108-tree assembly are written in TeX proof prose;
- theorem name and scope are locked to the S4 equal-magnitude theta-star
  finite-atlas theorem;
- the four class proofs are written: endpoint-free, wrapper-scope,
  positive-jam, and instant-jam;
- paper-grade checkers cover claim language, proof prose, table rows,
  package hashes, and public-package synchronization;
- external mathematical red-team reports PASS in the stated scope;
- human promotion decision records the extension as a public companion addendum.
```

## Synchronization discipline

The addendum has its own bibliography.  The tracked source is `refs.bib`; build
auxiliaries (`*.bbl`, `*.blg`, `*.aux`, `*.log`, `*.out`) are not part of the
public source package.

Before release tags or future edits, rerun:

```text
python scripts/check_theta_star_claim_language.py
python scripts/check_theta_star_paper_package.py
python scripts/check_theta_star_proof_prose.py
python scripts/check_theta_star_extension.py
python scripts/run_all_reproducibility_checks.py
```

## Optional future release work

Optional future work is not a blocker for the current companion addendum:

```text
- journal-style exposition polish;
- release tag metadata;
- a future paper revision that deliberately merges the addendum into a larger
  paper structure;
- extensions beyond equal-magnitude, zero-thickness, one-parameter S4.
```

Each item above requires a separate release decision and must preserve the
claim boundary below.

## Nonclaims preserved throughout

This roadmap does not authorize claims about physical hingeability, positive
thickness, fabrication, global physical collision-free motion, non-equal-angle
motion, three-parameter motion, or arbitrary hinged dissections.

## Historical notes

Earlier P0 entries in this file were milestones used to convert proof-spine
records into prose.  They are superseded by the current addendum TeX/PDF and
closure records in `paper_package/`.
