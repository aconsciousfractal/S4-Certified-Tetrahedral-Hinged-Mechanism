# Build the theta-star review PDF

From this directory:

```powershell
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
bibtex theta_star_finite_atlas
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
pdflatex -interaction=nonstopmode -halt-on-error theta_star_finite_atlas.tex
```

Expected output: `theta_star_finite_atlas.pdf`.

This is a standalone review draft for the theta-star extension. It is not part of the main public paper unless explicitly promoted after review.
