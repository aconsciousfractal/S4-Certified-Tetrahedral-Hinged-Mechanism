# Paper-to-engine traceability

| Paper component | Engine/package evidence | Status |
|---|---|---|
| Median-plane geometry and notation | `certified/source_docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`, `certified/source_docs/S4_LEMMA_01_GEOMETRY_AND_TILING.md` | source-locked paper lemma |
| Closed endpoint and kinematics | `certified/source_docs/S4_LEMMA_02_CLOSED_ENDPOINT.md`, `certified/source_docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md` | source-locked supporting lemmas |
| Route-wrapper ledger | `certified/a7d_one_parameter_theorem_wrapper_manifest.json` | scoped release-review claim |
| A6 B05 layer | `certified/source_docs/S4_CL5_A6_ONE_PARAMETER_RAY_CLOSURE_PACKAGE.md` | supporting certificate layer |
| A7a shared-face layer | `certified/source_docs/S4_CL5_A7A_SHARED_FACE_RESIDUAL_STURM_CERTIFICATE.md` | supporting certificate layer |
| A7b B03 route vacuity | `certified/source_docs/S4_CL5_A7B_B03_RAY_VACUITY_CERTIFICATE.md` | supporting certificate layer |
| A7c signed selected-hinge evidence | `certified/a7c_selected_hinge_contact_side_certificate_manifest.json` | package-local snapshot |
| B04/A7c selected-hinge bridge | `certified/b04_a7c_contact_side_bridge_manifest.json` and `certified/a7c_b04_contact_side_bridge_records/` | integrated, scoped to 6 rows |
| RW12 digital handoff | `results/rw12_external_fabrication_review_package/` | supplementary only; not physical validation |
| Release-review repository gate | `results/public_package_check.json`, `paper/PUBLIC_PACKAGE_MANIFEST.json` | local gates pass after manifest regeneration |
