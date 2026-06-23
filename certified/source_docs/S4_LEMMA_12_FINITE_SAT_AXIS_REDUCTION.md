> **Package provenance note.** This is a historical or future-scope source
> snapshot retained for audit trail only. It may contain words such as
> `draft`, `blocker`, or `Not a CL5 theorem`; those statements are not public
> claims of the current paper-as-public-package and do not widen the scoped
> zero-thickness theorem.

# S4 Lemma 12: Finite SAT Axis Reduction

Date: 2026-06-22
Case: `historical_s4_median_planes`
Status: algebraic proof-spine lemma draft; not a positivity certificate.

## Purpose

Reduce one-parameter tetrahedron-pair non-overlap checks to a finite list of
candidate separating axes and exact one-variable sign conditions. This is A1 of
the post-R61 algebraic proof spine.

## Statement

Let `P(theta)` and `Q(theta)` be two catalogued S4 tetrahedral pieces under a
fixed one-parameter hinge-tree ray from Lemma 03. For every fixed theta where
both transformed tetrahedra are nondegenerate, strict interior separation can be
certified by a separating axis from the finite SAT set:

```text
4 face normals of P(theta)
4 face normals of Q(theta)
6 x 6 edge-edge cross-product axes e_i(theta) x f_j(theta)
```

Thus at most 44 axis families are needed per tetrahedron pair. Axis families
whose cross product is zero are degenerate and must be routed to the adjacent
parallel-edge or face-normal cases, or split at roots of the exact nonzero-axis
condition.

For an oriented candidate axis `a(theta)`, define the unnormalized projection
gap

```text
G_a(theta) =
    min_{v in Vert(Q)} <a(theta), v(theta)>
  - max_{u in Vert(P)} <a(theta), u(theta)>.
```

If `G_a(theta) > 0`, then `P(theta)` and `Q(theta)` have disjoint interiors.
The same statement with reversed orientation swaps `P` and `Q`. For selected
hinges and common-edge boundary contacts, the strict positive-gap requirement is
not the correct endpoint predicate; those cases require their contact-side or
common-edge orientation predicates instead.

## Proof Sketch

The standard separating axis theorem for convex polytopes says that two
disjoint convex polyhedra in three dimensions have a separating axis parallel
to either a face normal of one polyhedron or the cross product of an edge of one
polyhedron with an edge of the other. A tetrahedron has four faces and six
edges, so the candidate set has size at most `4 + 4 + 6*6 = 44`.

Rigid hinge-tree motions preserve the tetrahedron combinatorics and convexity.
For a fixed theta, projection extrema of a tetrahedron on any axis occur at
vertices, giving the finite vertex min/max formula for `G_a(theta)`.

For the one-parameter S4 rays, every transformed vertex coordinate and every
axis coordinate is an exact trigonometric expression in theta. On any interval
where the support vertices and the axis branch are fixed, `G_a(theta)` is an
exact trigonometric expression. The Weierstrass substitution
`t = tan(theta/2)` converts it to a rational function, so sign certification
reduces to univariate polynomial sign/root checks.

## Branch And Support Stability

Support changes can occur only when two vertex projections on the same axis are
equal:

```text
<a(theta), u_i(theta)> = <a(theta), u_j(theta)>
<a(theta), v_i(theta)> = <a(theta), v_j(theta)>
```

Axis degeneracy can occur only when

```text
||e_i(theta) x f_j(theta)||^2 = 0.
```

After Weierstrass substitution these are finite polynomial root problems on a
one-parameter interval. The proof must split at those roots, or prove that none
occur on the target interval.

## Consequence For The Project

A1 replaces the R62 checker/report continuation as the primary mathematical
next step. It does not prove any gap positive. It defines the finite exact
objects that A2-A6 must build and certify:

```text
finite SAT axis families
exact transformed vertices
axis nondegeneracy roots
support-switch roots
projection-gap sign polynomials
Sturm/root-counting certificates
```

## Scope Boundaries

This lemma is for one-parameter ray certificates first. It does not solve
three-parameter bounded cells, adaptive overlay reconstruction, physical
hingeability, or dynamic connectedness. Those remain separate proof or audit
targets.
