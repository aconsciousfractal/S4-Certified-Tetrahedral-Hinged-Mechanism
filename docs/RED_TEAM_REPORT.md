# Red-team report

Status: release-review repository red-team boundary after B04/A7c bridge integration.

## Final local package red-team posture

The external red team identified one serious mathematical/semantic blocker: A7c signed orientation had been promoted too strongly as B04 contact-side closure. That blocker is addressed only by the package-local B04/A7c bridge, and only for the six selected hinge rows.

Resolved findings:

- RT-EXT-1 / B04-A7c semantic gap: resolved for six package-local selected hinge rows by `certified/b04_a7c_contact_side_bridge_manifest.json` and `certified/a7c_b04_contact_side_bridge_records/`.
- Portable replay provenance: resolved as a frozen-snapshot release-review repository, not a full source-replay bundle.
- License/citation metadata: aligned to the public-paper convention used under `P:\GitHub_puba`.
- RW12 overclaim risk: resolved by keeping RW12 supplementary-only and explicitly outside theorem evidence.



## Post-package red-team regression, 2026-06-23

A later external red-team pass found package-level, not theorem-level, blockers in the release-review repository.  The repository now treats those as release blockers and the checker enforces them directly.

Resolved in this regression:

- Deterministic PDF hash: the TeX source suppresses PDF date/trailer metadata, and two consecutive full pdfLaTeX/BibTeX builds produced the same PDF hash.
- Package-local versus historical provenance: required replay dependencies now use package-local paths; historical exploratory paths are retained only under `source_original_*` / provenance-labelled fields.
- B04/A7c bridge records: the six bridge rows keep package-local A7c row references and label historical row paths as source provenance only.
- A7d wording: the wrapper route now names the `A7c-plus-B04/A7c-bridge` layer rather than treating A7c alone as contact-side closure.
- Source-doc status boundary: `certified/source_docs/README.md` marks draft/blocker historical snapshots as provenance, not as current theorem claims.
- Legacy A7c row schema: `accepted_real_report=false` is explicitly documented as a legacy positive-clearance/SAT flag, not the current contact-side predicate.
- Hardened checker: `scripts/check_public_package.py` now fails on stale blocker phrases, nonlocal operational paths, missing B04 bridge dependencies, unlabelled historical JSON references, and missing deterministic-PDF policy.

Current remaining limits are unchanged: zero-thickness, one-parameter, selected hinge rows only; no physical validation, no positive-thickness fabrication theorem, no global collision-free CAD claim, and no three-parameter bounded-cell theorem.

## Remaining red-team limits

- The package does not prove physical mechanism validation, positive-thickness printability, global collision-free motion, CAD/STL validation, or a three-parameter theorem.
- The package does not generalize the B04 bridge beyond the six selected rows.
- The package-local gate is a policy/hash/manifest checker plus row-count consistency; it is not an independent mathematical proof checker.
- A fresh public-clone source replay remains optional release hardening.

## Release decision

The local release-review repository may be used for human external review or remote repository publication if the claim boundary is preserved and local gates are rerun after final metadata edits.
