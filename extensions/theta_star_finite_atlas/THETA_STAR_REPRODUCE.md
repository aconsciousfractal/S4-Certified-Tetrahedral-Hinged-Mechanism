# Theta-star reproduce notes

Status: addendum-review candidate.

The current public paper-package checks remain:

```powershell
python -m pytest -q
python scripts/run_all_reproducibility_checks.py
```

The theta-star extension has its own bounded consistency checker:

```powershell
python scripts/check_theta_star_extension.py
```

The theta-star checker verifies the imported artifact hashes, theorem-class
counts, source-map visibility, proof-gate status, extension manifest, and
claim-boundary wording.  It is a bounded consistency check for external review,
not a full mathematical replay and not theorem promotion.

The heavy exploratory local workspace is intentionally not rerun from this
public repository.  This extension imports a curated, hashable subset of exact
artifacts and replay docs.

Additional proof-prose hygiene gate:

```powershell
python scripts/check_theta_star_proof_prose.py
```


`python scripts/check_theta_star_proof_prose.py` also validates the generated 108-tree table comments against the T6 assembly `final_records`.

Optional local TeX smoke build, if `pdflatex` is available:

```powershell
cd extensions/theta_star_finite_atlas/paper_draft
pdflatex -interaction=nonstopmode -halt-on-error theta_star_addendum_skeleton.tex
```

The skeleton is a review draft only and is not included in the main paper.

## Build the standalone PDF

```powershell
cd extensions/theta_star_finite_atlas/paper_draft
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
```

The output is `theta_star_finite_atlas.pdf`.
