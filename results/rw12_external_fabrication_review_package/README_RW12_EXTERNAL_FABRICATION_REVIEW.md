# RW12 compact external fabrication/reviewer package

Status: `rw12_external_fabrication_review_package_ready_no_physical_claim`.

This is the compact handoff package for TREE_007. It contains only the files a
reviewer or fabricator should inspect first:

- four RW10 body-preserving printed body pieces (`STL` and `3MF`);
- three practical pin-diameter option sets from RW11 (`2.40`, `2.50`, `2.60` mm);
- checklist, operating instructions, tolerance matrix, and hash manifest.

Assembly preview files are intentionally omitted. They are useful for internal
inspection but too easy to mistake for fabrication geometry. Print the separate
body pieces and choose a pin strategy after review.

## Recommended review order

1. Read `CLAIM_BOUNDARY.md`.
2. Read `OPERATING_INSTRUCTIONS.md`.
3. Review `RW12_FABRICATOR_CHECKLIST.csv`.
4. Inspect the four body pieces under `fabrication_files/body_pieces`.
5. Choose pin strategy from `fabrication_files/pin_options` and
   `reference/RW11_TOLERANCE_DECISION_MATRIX.csv`.
6. Verify hashes against `RW12_FILE_MANIFEST.csv` before fabrication.

## Boundary

RW12 is a compact digital external-fabrication review package only. It does not claim physical print success, measured tolerances, insertion, rotation, durability, support-cleanup safety, or hingeability.
