# Building The Paper

From this directory:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error s4_certified_tetrahedral_hinged_mechanism.tex
bibtex s4_certified_tetrahedral_hinged_mechanism
pdflatex -interaction=nonstopmode -halt-on-error s4_certified_tetrahedral_hinged_mechanism.tex
pdflatex -interaction=nonstopmode -halt-on-error s4_certified_tetrahedral_hinged_mechanism.tex
```

Known build target:

```text
engine: pdfLaTeX
primary source: s4_certified_tetrahedral_hinged_mechanism.tex
bibliography: refs.bib
status: release-review PDF builds from this companion source tree
```

Deterministic build note: the TeX source suppresses PDF date/trailer metadata with pdfLaTeX primitives (`pdfinfoomitdate`, `pdfsuppressptexinfo`, `pdftrailerid`).  A full rebuild should preserve the PDF hash recorded in `paper/PUBLIC_PACKAGE_MANIFEST.json` when the TeX source and bibliography are unchanged.

