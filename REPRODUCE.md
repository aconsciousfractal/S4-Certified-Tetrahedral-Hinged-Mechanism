# Reproduce

## Public package checks

From repository root:

```powershell
python scripts/run_all_reproducibility_checks.py
```

This meta-gate runs the public package checker, the theta-star bounded review
checkers when present on this branch, the proof-spine path-hygiene checker, and
`pytest -q`.  The public-package subcheck writes
`results/public_package_check.json`; the theta-star gates report to stdout and
validate their manifest/proof-spine artifacts in place.

## Build the paper

From `paper/`:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error s4_certified_tetrahedral_hinged_mechanism.tex
bibtex s4_certified_tetrahedral_hinged_mechanism
pdflatex -interaction=nonstopmode -halt-on-error s4_certified_tetrahedral_hinged_mechanism.tex
pdflatex -interaction=nonstopmode -halt-on-error s4_certified_tetrahedral_hinged_mechanism.tex
```

The paper build is intended to be hash-stable: after the build, rerun `python scripts/run_all_reproducibility_checks.py` from the repository root.  The checker verifies the PDF hash against `paper/PUBLIC_PACKAGE_MANIFEST.json` and fails if the build introduced nondeterministic metadata or stale hashes.

## Computation source

The public computation source scripts are under `scripts/computation/`.  They
are included for auditability; the public package checks use curated manifests
and certificates rather than rerunning the full exploratory workspace.

## Theta-star extension review checks

On branch `theta-star-addendum-review`, the finite-atlas theta-star material is
kept under `extensions/theta_star_finite_atlas/`.  This extension has bounded review checkers listed in
`extensions/theta_star_finite_atlas/THETA_STAR_REPRODUCE.md`.  The branch-level
`run_all_reproducibility_checks.py` command runs them as part of the standard
replay.  These are review-package consistency checks, not a full mathematical
replay and not theorem promotion.
