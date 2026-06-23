# review agent package invocation records

Target package: `S4-Certified-Tetrahedral-Hinged-Mechanism`.

These records document the standard review routing used for the release-review paper/reviewer package. They are invocation records, not independent approvals.

## source_lock_agent

Reason: the paper depends on exact S4 geometry, notation, route-wrapper manifests, and B04/A7c bridge source documents.

Success criteria:
- Source documents are package-local under `certified/source_docs/`.
- Paper notation and theorem statements cite package-local source locks.
- Historical source paths are provenance breadcrumbs, not required replay dependencies.

Output artifacts:
- `docs/SOURCE_LOCK.md`
- `docs/PORTABLE_REPLAY_PROVENANCE.md`
- `paper/SOURCE_MAP.md`

## experiment_ledger_agent

Reason: package-local certified records, row manifests, PDF build, RW12 handoff, and package checks must remain evidence/interpretation separated.

Success criteria:
- A7c and bridge records are copied package-locally.
- Original source lineage is retained as provenance.
- Package checks verify bridge counts, RW12 hash, manifest hashes, and forbidden claim phrases.

Output artifacts:
- `certified/a7c_selected_hinge_contact_side_certificate_manifest.json`
- `certified/b04_a7c_contact_side_bridge_manifest.json`
- `docs/EXPERIMENT_LEDGER.md`
- `results/public_package_check.json`

## claim_curator_agent

Reason: public paper prose and README language needed claim-level correction after the A7c/B04 overclaim finding.

Success criteria:
- Claim ledger distinguishes A7c signed evidence from B04 bridge semantics.
- The strongest public claim is scoped to zero-thickness, one-parameter, audited representatives.
- Physical/global/three-parameter claims remain blocked.

Output artifacts:
- `docs/CLAIM_LEDGER.md`
- `docs/PUBLIC_CLAIM_BOUNDARY.md`
- `docs/THEOREM_PROSE_AUDIT.md`

## red_team_agent

Reason: external red-team found a mathematical/semantic overclaim in B04/A7c implication and public packaging must fail closed on wider claims.

Success criteria:
- RT-EXT-1 is resolved only through package-local bridge integration.
- Publication limits remain explicit.
- Red-team status records that gates are policy/hash/manifest checks, not independent theorem proof.

Output artifacts:
- `docs/RED_TEAM_REPORT.md`
- `docs/PROOF_OBLIGATIONS.md`

## reviewer_kit_agent

Reason: make the release-review repository navigable without HAN private workspace access.

Success criteria:
- Reviewer guide points to bridge manifest and row records.
- Reproduction instructions are package-local.
- Package manifest lists all shipped payload files with hashes.
- RW12 is packaged as supplementary digital material only.

Output artifacts:
- `README_REVIEWER.md`
- `REPRODUCE.md`
- `paper/PUBLIC_PACKAGE_MANIFEST.json`

## Gates completed, skipped, or deferred

- Current-workspace full A8 source replay: completed 2026-06-23; see `docs/SOURCE_REPLAY_A8_STATUS.md`.
- Paper PDF build: completed from TeX in this release-review repository.
- Public package checker and pytest wrapper: required after each manifest-affecting edit.
- Fresh public-clone source replay: optional release hardening after remote repository setup.
- Physical/material validation: not performed and not claimed.
