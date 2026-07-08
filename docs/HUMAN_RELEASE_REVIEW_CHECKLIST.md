# Human release review checklist

Status: local release-review repository prepared; final remote publication remains a human/operator action.

## Decision gate

A human reviewer must explicitly decide whether this local release-review repository should be published remotely as-is, after minor metadata edits, or held for further red-team review. The current package manifest records `public_export_ready=true` for the local candidate, but this is not an automatic remote-publication approval.

Important: RT-EXT-1, RT-EXT-4, RT-13, RW12 editorial routing, and the current-workspace full A8 source replay are resolved for this package boundary. Stronger theorem claims remain blocked by `docs/PUBLIC_CLAIM_BOUNDARY.md`.

## Files to inspect

| File | Review purpose |
|---|---|
| `paper/s4_certified_tetrahedral_hinged_mechanism.tex` | Confirm theorem prose, B04/A7c bridge wording, related-work citations, and nonclaim boundary. |
| `paper/s4_certified_tetrahedral_hinged_mechanism.pdf` | Confirm rendered paper is the TeX manuscript and not a short package note. |
| `docs/RED_TEAM_REPORT.md` | Confirm red-team disposition and remaining limits. |
| `docs/SUPERSESSION_STATUS_NOTE.md` | Confirm copied A7 source language is not over-promoted. |
| `CITATION.cff` | Confirm title, authors, version/date, repository metadata, and preferred citation. |
| `LICENSE` | Confirm code/package license matches the intended public repository policy. |
| `LICENSE_NOTE.md` | Confirm distinction between code/package license, paper text/PDF policy, CAD/STL artifacts, and copied source materials. |
| `docs/RELATED_WORK_POSITIONING.md` | Confirm citation list and novelty positioning. |
| `docs/CLAIM_LEDGER.md` | Confirm no claim is promoted beyond evidence. |
| `docs/PUBLIC_CLAIM_BOUNDARY.md` | Confirm public-facing allowed/not-allowed language. |
| `docs/PUBLIC_EXPORT_DECISION_PACKET.md` | Confirm the operator decision and post-copy gates. |
| `REPRODUCE.md` | Confirm replay provenance is honest and portable enough for the intended release class. |
| `results/rw12_external_fabrication_review_package/` | Confirm RW12 remains supplementary digital handoff only and no physical claim is implied. |

## Required human checks

- [x] Author/citation metadata follows the public-paper convention: Oleksiy Babanskyy, MIT package metadata, CC-BY-4.0 paper text policy.
- [x] Public repository/license policy matches the author's other public paper repositories.
- [x] Paper text/license policy is explicitly recorded.
- [x] CAD/STL/3MF artifact policy is recorded as generated package artifacts unless file-specific notice says otherwise.
- [ ] Copied source docs and generated artifacts are acceptable to redistribute.
- [ ] Citation list is acceptable, sufficiently complete for public release, and formatted consistently.
- [ ] The paper does not imply general hinged-dissection novelty.
- [ ] The paper does not imply reversible-net characterization novelty.
- [ ] The paper does not imply physical print/prototype/hingeability validation.
- [ ] A7c is described only as exact selected-hinge signed-orientation evidence unless paired with the B04 bridge artifact.
- [x] Current-workspace full A8 source replay passed; see `docs/SOURCE_REPLAY_A8_STATUS.md`.
- [ ] If required for publication, rerun from a fresh public-repository clone after the release repo is created remotely.
- [x] RW12 editorial status is decided: supplementary digital fabrication artifact, not theorem appendix evidence; see `docs/RW12_EDITORIAL_DECISION.md`.
- [x] Public export decision packet is prepared; see `docs/PUBLIC_EXPORT_DECISION_PACKET.md`.
- [ ] Operator confirms final remote publication metadata after this rebuild.

## Current known blockers

```text
RT-EXT-1  Closed in package by B04/A7c six-row bridge.
RT-EXT-4  Closed in package as frozen_snapshot_package provenance.
RT-13     Closed in package by public-paper license/citation alignment.
```

This checklist is evidence that review is prepared, not evidence that human review is complete.
