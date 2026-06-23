# Source lock

This reviewer package is source-locked as a frozen snapshot.

## Package-local evidence

The package contains local copies of the certified manifests, row records, source-note snapshots, RW12 supplementary artifact, and red-team result required by `scripts/replay_s4_post_rw12_package_gate.py`.

## Provenance breadcrumbs

Source paths inside copied manifests and historical reports are retained to preserve lineage. They are not required for package replay.

## Non-goal

This source lock is not itself a source-replay bundle. A current-workspace full A8 source replay passed on 2026-06-23 and is recorded in `docs/SOURCE_REPLAY_A8_STATUS.md`; a fresh public-clone replay can still be run as final release hardening after repository creation.
