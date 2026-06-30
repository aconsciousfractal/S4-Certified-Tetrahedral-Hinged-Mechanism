# Reviewer guide

This repository is designed for external inspection of the S4
route-wrapper certificate, the B04/A7c selected-hinge bridge, and the RW12
supplementary digital fabrication handoff.

## Ten-minute path

1. Read `docs/PUBLIC_CLAIM_BOUNDARY.md`.
2. Read `paper/s4_certified_tetrahedral_hinged_mechanism.pdf` or the TeX source.
3. Inspect `certified/b04_a7c_contact_side_bridge_manifest.json`.
4. Open one row in `certified/a7c_b04_contact_side_bridge_records/`.
5. Run `python -m pytest -q`.

## Thirty-minute path

1. Compare `certified/a7c_selected_hinge_contact_side_certificate_manifest.json`
   with `certified/b04_a7c_contact_side_bridge_manifest.json`.
2. Run `python scripts/check_public_package.py`.
3. Run `python scripts/run_all_reproducibility_checks.py`.
4. Review `docs/PROOF_OBLIGATIONS.md` and `docs/NEGATIVE_RESULTS_ATLAS.md`.
5. Inspect `results/rw12_external_fabrication_review_package/` only as a
   supplementary digital fabrication handoff, not as physical evidence.

## Red-team questions

- Does any claim extend beyond the six selected B04 bridge rows?
- Does any claim become physical, positive-thickness, globally collision-free,
  CAD/STL validated, or three-parameter?
- Is RW12 still described as supplementary digital material only?

## Optional theta-star addendum-review path

This path applies only on branch `theta-star-addendum-review` and only to the
review-candidate extension under `extensions/theta_star_finite_atlas/`.  It is
separate from the current paper theorem.

1. Read `extensions/theta_star_finite_atlas/README.md`.
2. Read `extensions/theta_star_finite_atlas/THETA_STAR_CLAIM_BOUNDARY.md`.
3. Read `extensions/theta_star_finite_atlas/THETA_STAR_REPRODUCE.md`.
4. Run `python scripts/check_theta_star_extension.py`.
5. Inspect the imported local proof artifacts listed in
   `extensions/theta_star_finite_atlas/artifacts/README.md`.
6. Treat the extension as a mathematical review target, not as physical or
   fabrication evidence.
