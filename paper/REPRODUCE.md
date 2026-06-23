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

## Computation source

The public computation source scripts are under `scripts/computation/`.  They
are included for auditability; the public package checks use curated manifests
and certificates rather than rerunning the full exploratory workspace.
