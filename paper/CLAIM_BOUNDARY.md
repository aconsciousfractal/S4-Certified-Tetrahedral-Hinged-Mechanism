# Public claim boundary

Status: release-review repository boundary after B04/A7c bridge integration and local package gates.

## Allowed public claims

- The S4 median-plane construction partitions the unit regular tetrahedron into four congruent closed tetrahedral pieces with disjoint relative interiors.
- The package records a scoped zero-thickness, one-parameter route-wrapper ledger on the exact A7d domain `theta=0 plus 0<theta<=120 degrees` for audited representatives `TREE_007` and `TREE_021`.
- A7c provides exact signed-orientation rows for the six selected hinge rows.
- The package-local B04/A7c bridge adds the required selected-row semantics: contact-side orientation and no strict local interior overlap for the parent/child pair at the contact plane, excluding the hinge axis.
- RW12 is a supplementary digital reviewer/fabricator handoff for `TREE_007`; it is not theorem evidence and not physical validation.

## Disallowed claims

The following claims are not allowed in this package:

- A7c alone proves contact-side closure.
- The bridge covers more than the six selected hinge rows.
- The package proves physical hingeability, positive-thickness printability, global collision-free motion, CAD/STL validation, or a three-parameter theorem.
- RW12 proves a fabricated prototype or physical mechanism.
- The result is a general hinged-dissection theorem, reversible-net theorem, or fabrication theorem.

## Release status

The repository is a local release-review repository with `public_export_ready=true` in `paper/PUBLIC_PACKAGE_MANIFEST.json` after local gates. Remote publication remains a human/operator action. Any release must preserve this claim boundary and rerun the package checks after final metadata edits.
