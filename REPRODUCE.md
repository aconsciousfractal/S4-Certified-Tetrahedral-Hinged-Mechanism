# Reproduce

## Public package checks

From repository root:

```powershell
python -m pytest -q
python scripts/run_all_reproducibility_checks.py
```

The combined report is written to `results/public_package_check.json`.

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
