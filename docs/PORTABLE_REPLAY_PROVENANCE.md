# Portable replay provenance

Status: frozen-snapshot provenance policy for the release-review repository.

## Classification

This repository is a `frozen_snapshot_package`, not a full upstream source-replay bundle.

The package-local replay proves that the files inside this package are internally consistent:

- all required public/reviewer files exist;
- all payload hashes in `paper/PUBLIC_PACKAGE_MANIFEST.json` match;
- RW12 ZIP hash matches its package-local report;
- A7c selected-hinge records exist package-locally;
- B04/A7c bridge records exist package-locally and point to the package-local A7c manifest;
- public claim boundary guardrails remain in force;
- physical validation is not claimed.

## What is package-local

The following evidence is self-contained in this package:

- `certified/a7d_one_parameter_theorem_wrapper_manifest.json`
- `certified/a7c_selected_hinge_contact_side_certificate_manifest.json`
- `certified/a7c_selected_hinge_contact_side_records/`
- `certified/b04_a7c_contact_side_bridge_manifest.json`
- `certified/a7c_b04_contact_side_bridge_records/`
- `certified/source_docs/`
- `results/rw12_external_fabrication_review_package/`
- `results/public_package_check.json`
- `paper/PUBLIC_PACKAGE_MANIFEST.json`

## What is provenance-only

Historical source paths preserved inside copied source docs, record metadata, and RW12 reports are provenance breadcrumbs. They are not operational dependencies for the package-local gate.

## What remains non-portable

A full upstream source replay is not packaged here. Replaying every upstream generator through the relevant A8 gate passed in the current workspace on 2026-06-23; see `docs/SOURCE_REPLAY_A8_STATUS.md`. A fresh public-clone replay can still be run as optional release hardening after remote repository setup.

## Release implication

This closes local package portability as a frozen snapshot. It does not widen any mathematical or physical claim beyond `docs/PUBLIC_CLAIM_BOUNDARY.md`.
