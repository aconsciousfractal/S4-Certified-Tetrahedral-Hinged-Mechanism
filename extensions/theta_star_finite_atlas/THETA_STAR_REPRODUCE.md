# Theta-star reproduce notes

Status: public companion addendum.

## Branch-level gate

The branch-level replay command is now a meta-gate for the public package and
theta-star review package:

```powershell
python scripts/run_all_reproducibility_checks.py
```

It runs the public package checker, all theta-star bounded checkers, the
proof-spine path-hygiene checker, and `pytest -q`.  It does not perform a full
geometric recomputation from the historical exploratory workspace and does not
build LaTeX PDFs.

## Individual gates

```powershell
python scripts/check_public_package.py
python scripts/check_theta_star_claim_language.py
python scripts/check_theta_star_paper_package.py
python scripts/check_theta_star_proof_prose.py
python scripts/check_theta_star_extension.py
python scripts/check_theta_star_proof_spine_paths.py
python -m pytest -q
```

## Gate meaning

| Command | Checks | Does not check |
| --- | --- | --- |
| `check_public_package.py` | Main paper package files, manifest hashes, PDF hash/page count, public claim guardrails. | Full theta-star proof replay; LaTeX rebuild. |
| `check_theta_star_claim_language.py` | Addendum claim boundary, forbidden overclaim phrases, required theorem-scope wording. | Geometry/SAT recomputation. |
| `check_theta_star_paper_package.py` | Proof-spine artifact presence, hashes, closure files, class/t-star counts, draft support files. | Independent regeneration of every proof-spine artifact. |
| `check_theta_star_proof_prose.py` | Theorem/proof prose, generated 108-tree table comments against T6 records, class statements. | Formal proof verification outside the recorded finite atlas. |
| `check_theta_star_extension.py` | Extension manifest, imported artifact hashes, source-map visibility, proof-gate status, claim boundary. | Heavy exploratory workspace replay. |
| `check_theta_star_proof_spine_paths.py` | No private absolute local paths outside whitelisted non-operational provenance fields. | Mathematical validity of source artifacts. |
| `pytest -q` | Repository unit tests. | Paper theorem proof obligations. |

The checkers are bounded consistency/review gates.  They support external
mathematical review; they are not a substitute for reading the TeX proof and
proof-spine records.

## Build the standalone PDF

If `pdflatex`/`bibtex` are available, rebuild the active companion addendum:

```powershell
cd extensions/theta_star_finite_atlas/paper_draft
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
bibtex theta_star_finite_atlas
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
```

The output is `theta_star_finite_atlas.pdf`.  The legacy
`theta_star_addendum_skeleton.tex` is retained only as a compatibility/smoke
entry point and is superseded by `theta_star_finite_atlas.tex`.
