# Roadmap to a theta-star paper/addendum

Status: addendum-review draft exists, not release/promoted form yet.  This
roadmap records the exact work needed to promote the current theta-star TeX/PDF
review draft and proof-spine package into a public addendum or companion paper.
It is intentionally scoped to the zero-thickness, equal-magnitude, finite S4
atlas over 108 connected three-hinge trees.

## Current verified state

The extension now has a real review draft and support package:

```text
paper_draft/theta_star_finite_atlas.tex
paper_draft/theta_star_finite_atlas.pdf
paper_draft/theta_star_finite_atlas_flat.tex
paper_draft/refs.bib
paper_package/artifacts/proof_spine/
```

The local theorem shape supported by the current proof spine is:

```text
final classes: 8 positive-jam, 36 endpoint-free, 60 instant-jam, 4 wrapper-scope
exact t*:      8 at sqrt(2), 40 endpoint-reaching at sqrt(3), 60 at 0
scope:         zero-thickness, equal-magnitude, one-parameter finite atlas
```

The draft is still an addendum-review candidate.  It is not yet merged into the
main paper theorem, and the main paper may only point to it as a separate
companion review draft.

The following earlier P0 hardening items are already closed in the current
review draft/proof-spine state:

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
  package hashes, and public-package synchronization.
```

## P0 promotion checks still required

### P0-01: External mathematical red-team

The next blocker is external mathematical review of the paper draft, flat TeX,
claim boundary, and proof-spine package.

Exit criteria:

```text
- external review finds no mathematical blocker in row reach / upper cap semantics;
- wrapper-scope trees TREE_007/TREE_009/TREE_021/TREE_093 remain correctly scoped;
- the finite-angle scaffold conjugacy and SAT/contact predicate vocabulary are accepted;
- no physical, positive-thickness, non-equal, three-parameter, or global claim leaks in.
```

### P0-02: Main-paper promotion decision

The current branch may mention the addendum review draft in the main paper only
as a non-claim companion note.  Promotion into the main theorem, appendix, or a
separate public addendum requires an explicit human release decision after
red-team.

Exit criteria:

```text
- choose one: keep extension-only, publish as companion addendum, or revise main paper;
- if promoted, update claim ledger, proof obligations, public manifest, TeX/PDF, and release notes;
- if not promoted, keep the extension as a review/research package.
```

### P0-03: Synchronization discipline

The addendum has its own bibliography.  The tracked source is `refs.bib`; build
auxiliaries (`*.bbl`, `*.blg`, `*.aux`, `*.log`, `*.out`) are not part of the
public source package.

Exit criteria:

```text
- addendum TeX/PDF/flat TeX are synchronized;
- extension manifest and public package manifest hashes match;
- check_theta_star_* gates pass;
- check_public_package.py and run_all_reproducibility_checks.py pass.
```

## P1 release-shape decision after P0

Only after the P0 blockers are closed, decide the release shape of the existing
review draft.  The current working files live under:

```text
extensions/theta_star_finite_atlas/paper_draft/
  theta_star_finite_atlas.tex
  theta_star_finite_atlas.pdf
  theta_star_finite_atlas_flat.tex
  refs.bib
  sections/
```

For a public addendum/companion release, either keep this tree and add release
metadata, or promote/copy it to a final paper tree such as:

```text
extensions/theta_star_finite_atlas/paper/
  s4_equal_magnitude_theta_star_finite_atlas.tex
  refs.bib
  BUILD.md
  PAPER_MANIFEST.json
  SHA256SUMS.txt
  sections/
  tables/
  appendix/
```

The result should be an addendum or separate theta-star manuscript, not a silent
change to the current main paper theorem.

## Promotion decision

Before setting any paper-ready flag, create:

```text
extensions/theta_star_finite_atlas/paper/PAPER_PROMOTION_DECISION.md
extensions/theta_star_finite_atlas/paper/RED_TEAM_CLOSURE_REPORT.md
```

Promotion is allowed only after the proof text, proof-spine artifacts, checkers,
tables, PDF build, and external mathematical red-team all pass.

## Nonclaims preserved throughout

This roadmap does not authorize claims about physical hingeability, positive
thickness, fabrication, global physical collision-free motion, non-equal-angle
motion, three-parameter motion, or arbitrary hinged dissections.


## P0-06 Proof-Prose Checker

`python scripts/check_theta_star_proof_prose.py` is the bounded paper-grade checker for the local TeX proof-prose draft. It checks theorem name/scope, class counts, exact values, class decomposition, and forbidden overclaim phrases against the materialized T6 proof spine.


## P0-07 formal definitions and generated 108-tree table - 2026-06-29

Status: local proof-prose hardening. Added `paper_draft/sections/02_formal_objects_and_tree_status_table.tex`, generated from the T6 assembly `final_records`. The proof-prose checker now validates every hidden `% RECORD` table row against target/source/orbit/final class/t-star/theta status/support gate in the JSON. This is still a bounded coherence checker, not a geometric replay, but it removes a major dependency on prose-only artifact summaries before any addendum/PDF decision.


## P0-08 local addendum skeleton - 2026-06-29

Status: superseded by the current `paper_draft/theta_star_finite_atlas.tex` review draft and PDF. The old skeleton step served to expose the proof prose as one compilable document; the active review target is now the full draft listed in the current verified state above.
