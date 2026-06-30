# S4 theta-star certificate transport lemma

Status: local theorem-support draft, 2026-06-29. Not a public-paper update and not a 108-tree theorem gate.

## Purpose

The finite-angle scaffold conjugacy lemma explains how a signed equal-magnitude motion on one hinge tree is carried to a signed equal-magnitude motion on a symmetry-equivalent tree.  This note attaches that geometric transport to the certificate classes currently present in the local theta-star spectrum ledger.

The goal is narrow:

```text
18 representative theta-star certificates
        + finite-angle scaffold conjugacy
        + exact signed row transport
        -> candidate certificates for the 108-tree orbit lift
```

This note does not claim that the lift has already been replayed row-by-row.  It states the transport rule and the exact checks that the next gate must perform.

## Inputs

The transport lemma depends on these local artifacts:

- `docs/S4_FINITE_ANGLE_SCAFFOLD_CONJUGACY_LEMMA.md`
- `docs/S4_FIRST_ORDER_ROW_EQUIVARIANCE_LEMMA.md`
- `docs/S4_FIRST_ORDER_ROOT_GAUGE_INVARIANCE_LEMMA.md`
- `docs/S4_FIRST_ORDER_SIGNED_ROW_EQUIVARIANCE_PROOF.md`
- `docs/S4_THETA_STAR_108_TREE_STATUS_MAP.md`
- `results/historical_s4_median_planes/local_theorem/theta_star_spectrum/s4_rep_status_ledger_v2.json`

The representative ledger currently has four certificate classes:

```text
exact_free_witness_candidate                  full-open representatives
public_wrapper_scope_certificate              TREE_007 public-wrapper representative
stage3a_stage3b_stage3c_local_tree_package    positive-t jam representatives TREE_000/TREE_003
instant_jam_row_gate                          t*=0 representatives
```

The values are:

```text
full-open endpoint:        t_endpoint = sqrt(3)
positive first contact:    t* = sqrt(2)       for TREE_000 and TREE_003
instant jam:               t* = 0
```

Here `t = tan(theta/2)`, so `sqrt(3)` corresponds to `theta=120 deg` and `sqrt(2)` corresponds to `theta ~= 109.4712206 deg`, the regular tetrahedral angle.

## Transport Vocabulary

A certificate is transportable only when it is expressed in scaffold-invariant data, not in accidental script-local labels.  A target record must therefore store the following maps and normalizations.

```text
source_tree
source_sign_vector
source_certificate_id
source_certificate_class
symmetry_map g
piece_map
hinge_map
epsilon_map on hinges
sign_vector_map
root_regauge
pair_map
SAT_axis_family_map
axis_sign_normalization
support_feature_map
selected_hinge_side_map, when B04/contact-side rows are involved
algebraic_t_star
```

The finite sign rule is the one already used by the signed-row equivariance layer:

```text
target_sign[g(h)] = det(R_g) * orient_g(h) * source_sign[h]
```

where `R_g` is the tetrahedral symmetry acting on the scaffold and `orient_g(h)` records the orientation effect on the hinge axis row.  The finite-angle scaffold lemma says that after applying this sign rule and a global rigid re-gauge of the root, the entire moving configuration is congruent to the transported source configuration for every admissible `t`.

## Lemma 1: Certificate Transport

Let `C` be a local theta-star certificate for a representative tree `T`.  Let `g` be a valid tetrahedral scaffold symmetry carrying `T` to a target tree `T'`, with transported sign row `s'` given by the signed-row rule above.

If `C` is written in the transport vocabulary and every geometric predicate used by `C` is invariant under rigid motions and orientation-aware relabelling, then the transported record `g(C)` is a valid certificate for `(T', s')`.

The proof is formal once the finite-angle scaffold conjugacy lemma is accepted: every relevant point, edge, hinge line, SAT axis, support feature, and selected contact-side ray is mapped to its image by one rigid scaffold symmetry plus one global root re-gauge.  Rigid motions preserve strict separation, equality contact, SAT overlap/non-overlap signs up to recorded axis normalization, and algebraic event time `t`.

## Certificate Classes

### A. Full-Open Endpoint Certificates

Representative status:

```text
exact_free_witness_candidate
```

Current representatives:

```text
TREE_001, TREE_004, TREE_005, TREE_027, TREE_029
```

Meaning: the selected sign row has no blocking non-hinge contact for the equal-magnitude interval `0 < t <= sqrt(3)`.  The certificate reaches the endpoint `theta=120 deg`.

Transport consequence: if all separating rows and contact-side predicates are recorded in transport vocabulary, the target sign row also reaches `t=sqrt(3)` with the same endpoint status.

Important wording: this is not a claim that first contact occurs at `sqrt(3)`.  It is an endpoint-reaching/free-open claim on the scoped equal-magnitude ray.

### B. Public Wrapper Full-Open Certificate

Representative status:

```text
public_wrapper_scope_certificate
```

Current representative:

```text
TREE_007
```

Meaning: the representative is covered by the public wrapper scope, including the A7c/B04 contact-side bridge for the selected hinge rows.

Transport consequence: same as the full-open class, but the target ledger must cite the public wrapper artifact as the source certificate.  This local lemma does not reprove the public package; it only states how such a certificate would be transported once source-locked.

### C. Positive-t First-Contact Certificates

Representative status:

```text
stage3a_stage3b_stage3c_local_tree_package
```

Current representatives:

```text
TREE_000   t* = sqrt(2), binding pair P2/P3
TREE_003   t* = sqrt(2), binding pair P1/P3
```

Meaning: on the selected equal-magnitude sign row, the tree is free before the algebraic event and reaches a full-SAT first-contact witness at `t*=sqrt(2)` for the binding pair.

Transport consequence: the target tree has the same algebraic `t*`, with binding pair transported by `pair_map`.  The full-SAT witness, active axes, support features, and no-earlier-contact predicates are transported by the finite-angle scaffold conjugacy.

This class is the strongest finite-angle obstruction class currently available because it identifies an exact positive jam time, not merely an endpoint failure.

### D. Instant-Jam Row Gates

Representative status:

```text
instant_jam_row_gate
```

Current representatives:

```text
TREE_002, TREE_008, TREE_014, TREE_015, TREE_016,
TREE_017, TREE_041, TREE_043, TREE_044, TREE_068
```

Meaning: every one of the eight equal-magnitude sign rows has a right-germ obstruction at `t=0`.  Hence the representative has `theta*=0` in the equal-magnitude theta-star spectrum.

Transport consequence: the signed-row rule is a bijection on the eight sign rows, so all eight target rows inherit right-germ obstruction at `t=0` after transport.

Special note: `TREE_043` includes an exact hard-row override for the row that was not certified by the first numeric support seed.  A transport ledger must preserve the exact override record, not silently replace it with the scout seed.

## Lemma 2: Theta-Star Class Preservation

Under the hypotheses of Lemma 1, theta-star status is constant on a valid finite-angle transport orbit:

```text
full-open to 120       -> full-open to 120
positive jam at t*     -> positive jam at the same algebraic t*
instant jam at t=0     -> instant jam at t=0
```

The binding pair and support features need not have the same labels, but they must be exactly the transported labels.

## Required Gate Before a 108-Tree Claim

A 108-tree theorem gate must not merely copy representative statuses.  It must build and replay a finite-angle transport ledger with at least these checks.

```text
1. every target tree has a source representative and a valid symmetry map g
2. target sign row equals det(R_g)*orient_g*source row
3. root re-gauge is recorded and does not alter pairwise geometry
4. transported binding pair matches the target row record
5. SAT/contact-side/support-feature rows are transported with signed axis normalization
6. algebraic t* is preserved exactly: 0, sqrt(2), or sqrt(3)-endpoint
7. TREE_043 hard-row override is source-locked and transported as an exact row
8. all 108 target records are covered, with no orphan tree and no duplicate target row ambiguity
```

The minimal pilot should cover one tree from each certificate class:

```text
full-open endpoint transport
positive-t jam transport from TREE_000 or TREE_003
instant-jam transport, including the TREE_043 exact override if possible
public-wrapper transport from TREE_007, if the wrapper source artifact is included
```

## Failure Modes

The transport lemma must fail closed in these cases:

- the target is not actually the image of the source under the recorded symmetry;
- a target row is root- or parent-child-convention dependent and the re-gauge is missing;
- a SAT axis sign is compared without normalization;
- a contact-side row is transported without the selected hinge-side map;
- a source certificate is only a sampled scout and not an exact row certificate;
- a full-open endpoint record is described as first-contact at `sqrt(3)`.

## Current Boundary

This note is a proof-planning and proof-polishing artifact.  It upgrades the roadmap from a vague `18 -> 108 by symmetry` statement to a concrete transport theorem target.  The next step is mechanical: create a compact finite-angle transport ledger and a replay pilot that checks the fields listed above on a small set of transported records.


## T5a audit consequence (2026-06-29)

The certificate transport lemma is now backed by a complete T4 transport ledger, a T5a theorem-readiness audit, a T5b finite root-regauge replay gate, and a T5c endpoint-free witness transport gate.  The audit confirms that the transport bookkeeping is complete over 108 targets and that instant-jam rows carry an 8-row sign/pair digest.  The two proof-polishing obligations exposed by T5a are now closed at support-gate level:

```text
1. finite root-regauge row replay for the 72 non-root-preserving targets (closed by T5b: `s4_theta_star_finite_root_regauge_replay_gate.json`, replay `15/15`);
2. proof-polished endpoint-free witness statements for the 36 rows formerly labelled `exact_free_witness_candidate` (closed by T5c: `s4_theta_star_endpoint_free_witness_transport_gate.json`, replay `22/22`).
```

T6 now consumes T4, T5a, T5b, and T5c in `s4_theta_star_108_tree_theorem_assembly_gate.json` and replays with `18/18` checks.  The lemma is therefore assembled into a local theorem-support gate.  The remaining promotion step is proof prose plus focused external red-team, not another transport computation.
