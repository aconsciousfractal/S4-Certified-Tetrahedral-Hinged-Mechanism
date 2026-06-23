# Claim ledger

Status: release-review scoped paper package after B04/A7c bridge integration and local package gates.

## S4-PAPER-001: S4 median-plane geometry

Claim: the unit regular tetrahedron is split by the two opposite-edge median planes into four congruent closed tetrahedral pieces with disjoint relative interiors and closed union equal to the ambient tetrahedron.

Status: paper-level mathematical lemma, source-locked.

Evidence:
- `paper/s4_certified_tetrahedral_hinged_mechanism.tex`
- `paper/sections/02_model_and_notation.tex`
- `certified/source_docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`
- `certified/source_docs/S4_LEMMA_01_GEOMETRY_AND_TILING.md`

## S4-PAPER-010: Route-wrapper scope

Claim: the package records a scoped zero-thickness, one-parameter route-wrapper ledger on the exact A7d domain `theta=0 plus 0<theta<=120 degrees` for audited S4 representatives `TREE_007` and `TREE_021`.

Status: supported by package-local certified manifest.

Evidence:
- `certified/a7d_one_parameter_theorem_wrapper_manifest.json`
- `certified/source_docs/S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md`
- `paper/sections/04_one_parameter_theorem.tex`

## S4-PAPER-020: B04/A7c selected hinge contact-side bridge

Claim: for the six selected hinge rows, A7c exact signed orientation plus the package-local B04 bridge proves the selected parent/child contact-side implication and no strict local interior overlap at the contact plane, excluding the hinge axis.

Status: integrated, scoped to six rows.

Evidence:
- `certified/a7c_selected_hinge_contact_side_certificate_manifest.json`
- `certified/a7c_selected_hinge_contact_side_records/`
- `certified/b04_a7c_contact_side_bridge_manifest.json`
- `certified/a7c_b04_contact_side_bridge_records/`
- `certified/source_docs/S4_CL5_A7C_B04_CONTACT_SIDE_BRIDGE_CERTIFICATE.md`
- `paper/sections/06_b04_bridge.tex`

Guardrail: this claim is not A7c-alone and does not extend beyond the six selected rows.

## S4-PAPER-030: Public package reproducibility

Claim: the release-review repository is locally replayable as a frozen-snapshot package: required files exist, bridge/RW12 consistency checks pass, forbidden physical-validation phrases are absent from public surfaces checked by the gate, and manifest hashes match.

Status: supported after local gate rerun.

Evidence:
- `scripts/check_public_package.py`
- `scripts/run_all_reproducibility_checks.py`
- `tests/test_public_package.py`
- `results/public_package_check.json`
- `paper/PUBLIC_PACKAGE_MANIFEST.json`

## S4-PAPER-040: RW12 supplementary handoff

Claim: the package includes the RW12 corrected compact handoff as supplementary digital reviewer/fabricator material, not theorem evidence and not physical validation.

Status: included, supplementary only.

Evidence:
- `results/rw12_external_fabrication_review_package/`
- `docs/RW12_EDITORIAL_DECISION.md`
- `paper/sections/08_rw12_boundary.tex`

## Blocked claims

- Physical mechanism validation.
- Positive-thickness and global collision-free motion.
- Three-parameter bounded-cell generalization.
- Bridge generalization beyond six selected rows.
- General hinged-dissection, reversible-net, or fabrication theorem.

## Remaining release hardening

- Fresh public-clone A8/source replay is optional hardening after remote publication setup; see `docs/SOURCE_REPLAY_A8_STATUS.md` and `docs/PORTABLE_REPLAY_PROVENANCE.md`.
- Final human/operator remote publication decision and metadata review.
