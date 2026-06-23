# Certified source document snapshots

Status: package-local source snapshots and provenance notes.

This directory intentionally contains two kinds of documents:

1. **Current scoped release-review sources** used by the paper and package gates:
   - `S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md`
   - `S4_LEMMA_01_GEOMETRY_AND_TILING.md`
   - `S4_LEMMA_02_CLOSED_ENDPOINT.md`
   - `S4_LEMMA_03_KINEMATICS_AND_SIGNS.md`
   - `S4_CL5_A6_ONE_PARAMETER_RAY_CLOSURE_PACKAGE.md`
   - `S4_CL5_A7A_SHARED_FACE_RESIDUAL_STURM_CERTIFICATE.md`
   - `S4_CL5_A7B_B03_RAY_VACUITY_CERTIFICATE.md`
   - `S4_CL5_A7C_SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE.md`
   - `S4_CL5_A7C_B04_CONTACT_SIDE_BRIDGE_CERTIFICATE.md`
   - `S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md`

2. **Historical or future-scope snapshots** retained for provenance. Some of these files contain words such as `draft`, `blocker`, or `Not a CL5 theorem`. Those statements are not public claims and are not used to widen the theorem. They document earlier bounded-cell, three-parameter, or full-source replay work that remains outside this package boundary.

Operational rule: package-local manifests must use `package_local_*` or `source_dependencies` fields for required files. Fields named `source_original_*` are provenance breadcrumbs and are not required to exist in this public repository.
