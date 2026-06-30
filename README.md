# S4 Certified Tetrahedral Hinged Mechanism

Companion repository for the paper:

```text
A Scoped Zero-Thickness S4 Tetrahedral Hinge-Tree Certificate Package
```

Author: Oleksiy Babanskyy

This repository contains the paper source/PDF, curated certificate artifacts,
computation scripts, claim-boundary documentation, and supplementary RW12
digital fabrication handoff for the S4 tetrahedral hinged mechanism work.  It
is organized as a paper-as-public-package: the manuscript, replay checks,
hash manifest, certificate rows, and claim-boundary ledgers are shipped
together so that the computational evidence can be audited without widening
the mathematical claim.  It is a curated public companion repository, not a
dump of the development workspace.

## Status

Local reproducibility checks and red-team guardrail checks pass.  The
claim remains intentionally narrow: zero-thickness, one-parameter,
selected-row route-wrapper/bridge certificate evidence for `TREE_007` and
`TREE_021`; RW12 is supplementary digital fabrication material only.

On the `theta-star-addendum-review` branch, `extensions/theta_star_finite_atlas/`
contains a promoted companion addendum for the equal-magnitude,
zero-thickness S4 theta-star finite atlas.  It is not part of the main paper
theorem and does not broaden the paper/PDF theorem; the main paper only carries
a companion-addendum note.

## Layout

```text
paper/      TeX manuscript source, PDF, bibliography, build notes
certified/  copied certified manifests and row records used by the paper
docs/       claim ledger, source locks, proof obligations, red-team notes
results/    curated package reports and RW12 supplementary fabrication package
extensions/ companion addenda kept outside the main paper claim
scripts/    public checks plus computation source scripts
tests/      pytest public-package guardrails
data/       intentionally empty unless curated public inputs are later approved
```

## Quick Check

```powershell
python -m pytest -q
python scripts/run_all_reproducibility_checks.py
```

The checks verify public package structure, paper/PDF presence, manifest/hash
coherence, and that physical claims are not promoted.  They do not replace the
mathematical arguments or the certified records cited by the paper.

## Paper

```text
paper/s4_certified_tetrahedral_hinged_mechanism.tex
paper/s4_certified_tetrahedral_hinged_mechanism.pdf
paper/BUILD.md
paper/refs.bib
```

Build instructions are in `paper/BUILD.md`.

## Claim Boundary

Read `docs/PUBLIC_CLAIM_BOUNDARY.md` before widening any statement.  This repo
does not claim physical prototype validation, positive-thickness printability,
global collision-free motion, a three-parameter theorem, or a general hinged
dissection/reversible-net theorem.
