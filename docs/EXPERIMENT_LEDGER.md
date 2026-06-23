# Experiment ledger

## Package-local certified inputs

- A7d route-wrapper manifest: `certified/a7d_one_parameter_theorem_wrapper_manifest.json`.
- A7c selected-hinge manifest: `certified/a7c_selected_hinge_contact_side_certificate_manifest.json` with 6 package-local records.
- B04/A7c bridge manifest: `certified/b04_a7c_contact_side_bridge_manifest.json` with 6 accepted package-local bridge records.
- RW12 supplementary external handoff artifact: `results/rw12_external_fabrication_review_package/`.
- Paper source and PDF: `paper/s4_certified_tetrahedral_hinged_mechanism.tex` and `paper/s4_certified_tetrahedral_hinged_mechanism.pdf`.

## Verification gates

- `pdflatex`, `bibtex`, `pdflatex`, `pdflatex` build the 9-page PDF from the TeX sources.
- `python scripts/check_public_package.py` checks public package structure, bridge counts, RW12 hash consistency, forbidden phrase guardrails, manifest hashes, and physical-claim flags.
- `python scripts/run_all_reproducibility_checks.py` runs the same package checker.
- `python -m pytest -q` runs `tests/test_public_package.py`, which wraps the package checker.

## Interpretation

The package is a locally gated frozen-snapshot release-review repository. It is not a full upstream source-replay bundle and it is not physical validation. Computation output supports only the scoped claims recorded in `docs/CLAIM_LEDGER.md` and bounded by `docs/PUBLIC_CLAIM_BOUNDARY.md`.
