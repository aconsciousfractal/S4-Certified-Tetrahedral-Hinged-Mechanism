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
