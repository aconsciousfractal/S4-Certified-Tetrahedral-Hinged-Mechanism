# S4 finite-angle scaffold conjugacy lemma

Status: local theorem-support lemma prose. Not a public-paper update.
Date: 2026-06-30

## Statement

Let `T` be a connected S4 three-hinge tree in the zero-thickness scaffold,
and let `g` be one of the finite scaffold relabeling/re-gauge maps used by the
S4 theta-star transport ledger.  For every equal-magnitude sign row of `T`,
there is a corresponding sign row of `g(T)` such that every pairwise relative
pose used by the separating-axis predicates is conjugate by the same rigid
orthogonal relabeling.

Equivalently, if `C_i(t)` and `C_j(t)` are the piece poses along a row and
`G` is the scaffold relabeling matrix, then the transported row has relative
poses

```text
(G C_j(t))^{-1} (G C_i(t)) = C_j(t)^{-1} C_i(t)
```

up to the recorded root re-gauge and axis-sign normalization.  Therefore the
finite SAT row predicates, their zero/nonzero status, and the theta-star event
classification are preserved under the transport recorded in the ledger.

## Proof Ingredients

1. The transformation `g` is a finite scaffold relabeling, so it acts by an
   orthogonal matrix and a piece relabeling on every static tetrahedral piece.
2. Pairwise collision predicates depend only on relative poses and transformed
   SAT axes.  Global conjugation cancels in the relative pose calculation.
3. The root convention does not change pairwise relative geometry; non-root-
   preserving targets are closed by the finite root re-gauge replay gate.
4. Axis orientation is normalized row-by-row.  The transported row sign is
   recorded by the finite-angle transport ledger, so an axis sign flip changes
   only the representative of the same inequality, not the predicate truth.

## Source Locks

This lemma is the document-level source lock for Theorem A in the theta-star
crosswalk.  The paper-draft prose version is mirrored in
`paper_draft/sections/03_finite_angle_conjugacy.tex`; the transport and
invariance consequences are used in
`paper_draft/sections/04_transport_and_theta_star_invariance.tex`.

The replay artifacts that instantiate this lemma are packaged under
`paper_package/artifacts/proof_spine/`, especially:

- `s4_theta_star_finite_angle_transport_ledger.json`
- `s4_theta_star_finite_angle_transport_ledger_replay.json`
- `s4_theta_star_finite_root_regauge_replay_gate.json`

## Nonclaims

This lemma does not assert positive thickness, fabrication, physical
hingeability, a non-equal-angle theorem, or a three-parameter motion theorem.
It is only a finite-angle conjugacy and row-transport lemma for the scoped
zero-thickness equal-magnitude S4 theta-star atlas.
