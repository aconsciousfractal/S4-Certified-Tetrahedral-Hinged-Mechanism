# Related-work positioning

Status: citation audit pass for internal review.  This note is a
positioning document, not a public novelty claim by itself.

## Scope of the novelty candidate

The strongest honest novelty candidate is not "we solved hinged dissections."
It is narrower:

1. a specific tetrahedral S4 median-plane construction;
2. a reproducible certificate stack for audited representative trees;
3. a claim ledger that prevents mathematical, digital, and physical
   evidence from being conflated;
4. a corrected digital fabrication handoff that keeps the original body
   geometry intact after earlier CAD routes failed.

The current public boundary remains: scoped zero-thickness one-parameter wrapper
for `TREE_007` and `TREE_021`, endpoint `theta=0` plus open domain
`0<theta<=120 degrees`, and RW12 as a digital external fabrication/reviewer
handoff for `TREE_007`.  Physical hingeability, print success, and global
three-parameter closure are not claimed.

## Hinged dissections

Abbott, Abel, Charlton, Demaine, Demaine, and Kominers prove broad existence
results for hinged dissections: any finite set of equal-area polygons has a
common hinged dissection, and the paper also discusses edge-hinged 3D polyhedra
under common unhinged-dissection hypotheses [1].  Therefore S4 should not be
presented as a general hinged-dissection existence theorem.

S4 is positioned differently: it is a concrete tetrahedral median-plane
mechanism plus a reproducible certificate/replay package.  The contribution is
in the specific construction, the checked claim ledger, and the separation of
mathematical evidence from fabrication evidence.

## Reversible hinged dissections and common nets

Akiyama, Demaine, and Langerman characterize reversible hinged dissections in
terms of noncrossing nets of a common polyhedron, with a convex-polyhedron
condition for monotone reversible motions [2].  Akiyama, Langerman, and
Matsunaga also study reversible nets of convex polyhedra and isotetrahedron
cases [3].

The present S4 package does not claim a reversible-net characterization and does
not prove that the RW12 solids form a validated physical reversible net.  Any
comparison to this literature must stay at the level of related mechanisms and
folding/unfolding background, unless a later theorem explicitly connects S4 to a
common-net model.

## Polyhedral linkages, unfolding, and folding background

Demaine and O'Rourke's book site is the standard background entry point for
linkages, origami, and polyhedral folding algorithms [4].  Demaine et al. also
study continuous flattening/reversing of convex polyhedral linkages after edge
subdivision [5].  Vertex-unfolding work for simplicial polyhedra gives another
adjacent algorithmic geometry context [6].

S4 should be cited against this background as a small, certificate-led artifact,
not as a replacement for those general linkage/unfolding results.

## Digital fabrication and jointed assemblies

The fabrication appendix belongs to a separate evidence class.  Adjacent work
such as RodSteward addresses design/fabrication workflows for structures with
3D-printed joints and precision-cut rods [7], while JoinABLe provides CAD
assembly/joint datasets and assembly reasoning resources [8].  These references
support the claim-boundary decision: fabrication and assembly validation require
explicit workflow, tolerance, profile, and measurement evidence.

RW12 currently supplies only a digital handoff: corrected body components,
practical pin variants, manifest hashes, checklist, and operating instructions.
It is not physical evidence.

## Current novelty posture

After this citation audit, the package remains potentially serious as a
reproducible-artifact paper, not as a broad hinged-dissection theorem.  The
paper can honestly say:

- the general hinged-dissection and reversible-net landscape already exists;
- S4 is a specific tetrahedral mechanism/certificate package inside that
  landscape;
- the digital fabrication branch is useful for external review but does not
  promote physical claims;
- license/citation metadata now follows the public-paper convention; current-workspace full A8 source replay has passed; RW12 is now positioned as supplementary digital fabrication material; public export still requires the final release operator decision.

## References

[1] Timothy G. Abbott, Zachary Abel, David Charlton, Erik D. Demaine, Martin L.
Demaine, Scott D. Kominers, "Hinged Dissections Exist," arXiv:0712.2094,
https://arxiv.org/abs/0712.2094.

[2] Jin Akiyama, Erik D. Demaine, Stefan Langerman, "Polyhedral
Characterization of Reversible Hinged Dissections," arXiv:1803.01172,
https://arxiv.org/abs/1803.01172.

[3] Jin Akiyama, Stefan Langerman, Kiyoko Matsunaga, "Reversible Nets of
Polyhedra," arXiv:1607.00538, https://arxiv.org/abs/1607.00538.

[4] Erik D. Demaine, Joseph O'Rourke, "Geometric Folding Algorithms: Linkages,
Origami, Polyhedra," book site, https://www.gfalop.org/.

[5] Erik D. Demaine, Martin L. Demaine, Markus Hecher, Rebecca Lin, Victor H.
Luo, Chie Nara, "Continuous Flattening and Reversing of Convex Polyhedral
Linkages," arXiv:2412.15130, https://arxiv.org/abs/2412.15130.

[6] Erik D. Demaine, David Eppstein, Jeff Erickson, George W. Hart, Joseph
O'Rourke, "Vertex-Unfoldings of Simplicial Polyhedra," arXiv:cs/0107023,
https://arxiv.org/abs/cs/0107023.

[7] "RodSteward: A Design-to-Assembly System for Fabrication using 3D-Printed
Joints and Precision-Cut Rods," arXiv:1906.05710,
https://arxiv.org/abs/1906.05710.

[8] "JoinABLe: Learning Bottom-up Assembly of Parametric CAD Joints,"
arXiv:2111.12772, https://arxiv.org/abs/2111.12772.
