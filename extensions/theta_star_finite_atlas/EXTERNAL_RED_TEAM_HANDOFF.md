# Theta-Star Extension: External Red-Team Handoff

This is the handoff for reviewing the S4 equal-magnitude theta-star finite-atlas extension.

## Start Here

1. Read the PDF:
   `extensions/theta_star_finite_atlas/paper_draft/theta_star_finite_atlas.pdf`
2. If source review is needed without many files, read the single-file TeX:
   `extensions/theta_star_finite_atlas/paper_draft/theta_star_finite_atlas_flat.tex`
3. The modular repo source is also available, but requires `paper_draft/sections/`:
   `extensions/theta_star_finite_atlas/paper_draft/theta_star_finite_atlas.tex`
4. Use the proof-spine artifacts only as support evidence:
   `extensions/theta_star_finite_atlas/paper_package/artifacts/proof_spine/`
5. Check closure/supersession decisions:
   `extensions/theta_star_finite_atlas/paper_package/PAPER_PROOF_SPINE_CLOSURE.json`
   `extensions/theta_star_finite_atlas/paper_package/RED_TEAM_CLOSURE_REPORT.md`
   `extensions/theta_star_finite_atlas/paper_package/PAPER_PROMOTION_DECISION.md`

## What To Red-Team

Check whether the standalone draft really proves the stated local theorem:

```text
S4 equal-magnitude theta-star finite-atlas theorem
for the zero-thickness historical S4 scaffold over 108 connected three-hinge trees.
```

The claimed classification is:

```text
40 trees: endpoint reached at t = sqrt(3)
 8 trees: positive jam at t = sqrt(2)
60 trees: instant jam at t = 0
```

Please focus on the mathematical chain:

- definitions of rows, t, row event value, and theta-star;
- finite-angle scaffold conjugacy;
- row/sign transport and root re-gauge;
- theta-star invariance under the finite tree symmetries;
- the four certificate classes and their counts;
- source-locking of endpoint-free, wrapper, positive-jam, and instant-jam classes;
- whether the generated 108-tree table is genuinely supported by the proof spine.

## What Is Not Claimed

This is not a physical hingeability theorem, not a positive-thickness theorem, not a non-equal-angle theorem, not a three-parameter theorem, and not a general hinged-dissection theorem.

## Verification Commands

From repository root:

```powershell
python scripts/check_theta_star_claim_language.py
python scripts/check_theta_star_proof_prose.py
python scripts/check_theta_star_paper_package.py
python scripts/check_theta_star_extension.py
python scripts/check_public_package.py
python scripts/run_all_reproducibility_checks.py
```

The first five commands are specific to this extension. The last two are repository-level sanity gates; `run_all_reproducibility_checks.py` replays the same bounded public/theta-star gate set as a single command.

## Important Distinction

`paper_package/` is not the paper. It is the supporting proof-spine package: manifests, hashes, replay JSON, and source-locked certificates.

The review draft is `paper_draft/theta_star_finite_atlas.pdf`. For source review without many files, use `paper_draft/theta_star_finite_atlas_flat.tex`. The modular repo source is `paper_draft/theta_star_finite_atlas.tex` plus `paper_draft/sections/`.
