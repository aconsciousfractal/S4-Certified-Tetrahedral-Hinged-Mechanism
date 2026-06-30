# Roadmap to a theta-star paper/addendum

Status: paper-reachable, not paper-form yet.  This roadmap records the exact
work needed to turn the current theta-star review package into a mathematical
paper/addendum draft.  It is intentionally scoped to the zero-thickness,
equal-magnitude, finite S4 atlas over 108 connected three-hinge trees.

## Current verified state

The current extension package has a candidate theorem shape supported by local
artifacts and review gates:

```text
final classes: 8 positive-jam, 36 endpoint-free, 60 instant-jam, 4 wrapper-scope
exact t*:      8 at sqrt(2), 40 endpoint-reaching at sqrt(3), 60 at 0
scope:         zero-thickness, equal-magnitude, one-parameter finite atlas
```

The present package is still a review package.  It is not yet a paper proof,
because the proof spine is distributed across documents and JSON gates rather
than written as self-contained definitions, lemmas, theorem, proof, tables,
and a paper-grade checker.

## P0 blockers before TeX/PDF promotion

### P0-01: Resolve the status-map conflict

`docs/S4_THETA_STAR_108_TREE_STATUS_MAP.md` is a historical guardrail map and
still contains pre-T4/T5/T6 labels such as
`orbit_inherited_label_not_finite_angle_transport`.  This conflicts with the
current transport proof spine unless it is explicitly superseded.

Exit criteria:

```text
- STATUS_MAP has a top-level supersession note.
- Historical orbit-inherited labels are marked pre-T4/T5/T6.
- A checker fails if stale labels appear without that supersession context.
```

### P0-02: Materialize the proof spine inside the paper package

The crosswalk must not point to a private workspace.  Every proof-spine artifact
named by the crosswalk must be present in the extension package, either as a
full JSON file or as a digest with source sha256, scope, counts, and replay
status.

Required proof-spine artifacts or digests:

```text
s4_theta_star_finite_angle_transport_ledger.json
s4_theta_star_finite_angle_transport_ledger_replay.json
s4_theta_star_transport_theorem_readiness_audit.json
s4_theta_star_finite_root_regauge_replay_gate.json
s4_theta_star_endpoint_free_witness_transport_gate.json
s4_theta_star_108_tree_theorem_assembly_gate.json
s4_theta_star_108_tree_theorem_assembly_gate_replay.json
s4_theta_star_theorem_sabotage_gate.json
s4_theta_star_source_map_visibility_audit.json
s4_theta_star_positive_jam_max_over_8_certificate.json
s4_theta_star_t6b_theorem_prose_audit.json
s4_theta_star_108_tree_theorem_proof_package_gate.json
```

Exit criteria:

```text
- paper_package/artifacts/proof_spine/ or proof_spine_digest/ exists.
- hashes are recorded.
- checker verifies every crosswalk artifact exists or has a digest.
```

### P0-03: Promote the proof spine into self-contained mathematics

The paper must not rely on a phrase like "Source proof note" as the proof.
The core proof must be written in the paper itself.

Required mathematical sections:

```text
finite-angle scaffold conjugacy
signed equal-magnitude row transport
eight-row bijection
theta-star orbit invariance
108-tree assembly
```

Exit criteria:

```text
- Theorem A/B proofs are written in TeX prose.
- Source artifacts are cited as certificate support, not as substitutes for proof.
```

### P0-04: Lock the theorem name and scope

Use this title/scope language:

```text
S4 equal-magnitude theta-star finite-atlas theorem
```

Do not use:

```text
global motion theorem
physical hingeability theorem
positive-thickness theorem
three-parameter theorem
non-equal-angle theorem
general hinged-dissection theorem
```

Exit criteria:

```text
- claim-language checker passes.
- sqrt(3) is always described as endpoint reached, not first contact.
```

### P0-05: Write the four class proofs

The final theorem needs one proof subsection per class:

```text
positive jam:   8 trees, t=sqrt(2), selected row attains and max-over-8 caps
endpoint-free:  36 trees, endpoint sqrt(3), no blocking contact on 0<t<=sqrt(3)
instant jam:    60 trees, all eight rows obstruct at t=0, TREE_043 override visible
wrapper scope:   4 trees, endpoint-reaching but kept separate from endpoint-free
```

Exit criteria:

```text
- each class proof names its source artifacts and transport route.
- wrapper-scope class does not widen the current public paper theorem.
```

### P0-06: Add paper-grade checkers

The existing checker is review-grade.  Add paper-grade checks for:

```text
crosswalk artifact presence/digests
status-map supersession
forbidden claim language
108 unique tree ids
18 representatives
8/36/60/4 final class counts
40/8/60 t-star distribution
TeX tables matching JSON/digest counts
PDF build log/manifests once the paper exists
```

Exit criteria:

```text
python scripts/check_theta_star_extension.py
python scripts/check_theta_star_paper_package.py
python scripts/check_theta_star_claim_language.py
python scripts/check_theta_star_tables.py
python -m pytest -q
```

## P1 paper construction after P0

Only after the P0 blockers are closed, create the addendum/paper tree:

```text
extensions/theta_star_finite_atlas/paper/
  s4_equal_magnitude_theta_star_finite_atlas.tex
  refs.bib
  BUILD.md
  PAPER_MANIFEST.json
  SHA256SUMS.txt
  sections/
  tables/
  appendix/
```

The paper should be an addendum or separate theta-star manuscript, not a silent
change to the current main paper theorem.

## Promotion decision

Before setting any paper-ready flag, create:

```text
extensions/theta_star_finite_atlas/paper/PAPER_PROMOTION_DECISION.md
extensions/theta_star_finite_atlas/paper/RED_TEAM_CLOSURE_REPORT.md
```

Promotion is allowed only after the proof text, proof-spine artifacts, checkers,
tables, PDF build, and external mathematical red-team all pass.

## Nonclaims preserved throughout

This roadmap does not authorize claims about physical hingeability, positive
thickness, fabrication, global physical collision-free motion, non-equal-angle
motion, three-parameter motion, or arbitrary hinged dissections.


## P0-06 Proof-Prose Checker

`python scripts/check_theta_star_proof_prose.py` is the bounded paper-grade checker for the local TeX proof-prose draft. It checks theorem name/scope, class counts, exact values, class decomposition, and forbidden overclaim phrases against the materialized T6 proof spine.


## P0-07 formal definitions and generated 108-tree table - 2026-06-29

Status: local proof-prose hardening. Added `paper_draft/sections/02_formal_objects_and_tree_status_table.tex`, generated from the T6 assembly `final_records`. The proof-prose checker now validates every hidden `% RECORD` table row against target/source/orbit/final class/t-star/theta status/support gate in the JSON. This is still a bounded coherence checker, not a geometric replay, but it removes a major dependency on prose-only artifact summaries before any addendum/PDF decision.


## P0-08 local addendum skeleton - 2026-06-29

Status: local TeX skeleton only. Added `paper_draft/theta_star_addendum_skeleton.tex`, a standalone review build that inputs sections 02--08. This does not modify the main paper and is not a publication-ready addendum; it exists to expose the proof prose as a single compilable document before external mathematical review.
