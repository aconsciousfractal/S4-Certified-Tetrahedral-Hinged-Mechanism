# Theorem prose audit

Status: theorem-prose audit after B04/A7c bridge integration.

## Binding interpretation

Paper prose may state only the scoped zero-thickness, one-parameter route-wrapper theorem for the audited representatives `TREE_007` and `TREE_021`. For selected-hinge contact-side/no-strict-overlap semantics, the prose must cite the package-local B04/A7c bridge, not A7c alone.

## Allowed sentence form

"For the six selected hinge rows, the A7c exact signed-orientation records together with the B04 bridge records certify the selected contact-side implication and no strict local interior overlap for the parent/child pair at the contact plane, excluding the hinge axis."

## Disallowed sentence forms

- "A7c proves B04 contact-side closure."
- "The mechanism is collision-free."
- "The model has physical prototype validation."
- "RW12 proves the real-world prototype."
- "The package proves the three-parameter theorem."

## Evidence

- `certified/a7c_selected_hinge_contact_side_certificate_manifest.json`
- `certified/b04_a7c_contact_side_bridge_manifest.json`
- `certified/source_docs/S4_CL5_A7C_B04_CONTACT_SIDE_BRIDGE_CERTIFICATE.md`
- `paper/sections/06_b04_bridge.tex`
