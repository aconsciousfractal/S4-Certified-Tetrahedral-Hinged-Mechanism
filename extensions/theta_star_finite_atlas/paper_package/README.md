# Theta-star proof spine paper package

Status: proof-spine support package for the promoted theta-star finite-atlas
public companion addendum.

This directory materializes the T4/T5/T6 proof-spine artifacts cited by the
addendum and crosswalk.  It is not itself the TeX/PDF paper; the addendum paper
lives in `extensions/theta_star_finite_atlas/paper_draft/`.  The purpose of
this directory is to make the theorem support layer hashable and reviewable
inside the public repository instead of requiring a private workspace path.

Historical local source paths in packaged proof-spine records are redacted as
provenance-only basenames/relative result paths; operational checks must use
repository-relative packaged artifacts.

Scope remains restricted to the zero-thickness, equal-magnitude, one-parameter
finite S4 atlas over 108 connected three-hinge trees.

Nonclaims: no physical hingeability, no positive-thickness claim, no fabrication
claim, no global physical motion theorem, no three-parameter theorem, and no
non-equal-angle theorem.

Run from repository root:

```powershell
python scripts/check_theta_star_extension.py
python scripts/check_theta_star_paper_package.py
python scripts/check_theta_star_proof_prose.py
python scripts/check_theta_star_claim_language.py
```
