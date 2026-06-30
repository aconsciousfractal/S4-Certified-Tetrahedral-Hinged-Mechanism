# Publication plan

Status: release-review repository.

1. Keep the claim boundary narrow and source-backed.
2. Use `paper/` as the manuscript source/PDF directory.
3. Keep RW12 under `results/rw12_external_fabrication_review_package/` as
   supplementary digital fabrication material only.
4. Run `python -m pytest -q` and `python scripts/run_all_reproducibility_checks.py`
   before release tags.
5. Do not promote physical or three-parameter claims without new evidence.

## Theta-star addendum-review branch

Branch: `theta-star-addendum-review`.

Purpose: stage the local S4 theta-star finite-atlas theorem candidate for
external mathematical review while keeping the already closed public theorem
unchanged.  The main paper may carry only a branch-local companion-extension
note; the theta-star theorem itself remains in the extension draft.

Rules for this branch:

1. Keep the current paper theorem unchanged; any main-paper mention must be a non-claim companion-extension note.
2. Place theta-star material under `extensions/theta_star_finite_atlas/`.
3. Describe it as an addendum-review candidate, not as a promoted public theorem.
4. Keep the scope equal-magnitude, zero-thickness, finite S4 atlas only.
5. Do not promote positive-thickness, physical, global collision-free,
   three-parameter, non-equal motion, or general hinged-dissection claims.
6. Before any addendum promotion, require a dedicated theta-star extension
   checker and external mathematical red-team focused on the proof chain.

Possible promotion outcomes after review:

- keep the material as a research extension;
- keep the existing separate addendum TeX/PDF as a review draft;
- later prepare a paper revision only after a human release decision.

## Theta-star path from review package to paper

The concrete roadmap is `extensions/theta_star_finite_atlas/ROADMAP_TO_PAPER.md`.
The next sequence is intentionally mathematical, not cosmetic:

1. resolve the historical `STATUS_MAP` conflict against the T4/T5/T6 proof spine;
2. materialize or digest every proof-spine artifact named by the crosswalk;
3. add paper-grade checkers for crosswalk artifacts, claim language, tree counts,
   tables, and stale status labels;
4. rewrite Theorem A/B as self-contained proof prose;
5. maintain the four class proofs: positive jam, endpoint-free, instant jam, and
   wrapper-scope;
6. keep the addendum TeX/PDF, local bibliography, manifest, and proof-spine
   package synchronized.

A theta-star TeX/PDF now exists under the extension.  It is not promoted into
the main paper unless external mathematical red-team and a human release
decision explicitly approve that promotion.
