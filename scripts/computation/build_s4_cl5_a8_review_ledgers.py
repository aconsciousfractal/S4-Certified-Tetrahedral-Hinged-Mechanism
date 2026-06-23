#!/usr/bin/env python
"""
Build A8 PAPP experiment and claim ledgers for the post-A7d review gate.

A8.1/A8.2 is a packaging/review layer.  It reads the completed A6/A7a/A7b/A7c
and A7d manifests, then emits project-local experiment and claim ledgers in both
Markdown and JSON form.  It does not promote the A7d wrapper, does not create a
paper package, and does not claim physical hingeability or three-parameter
bounded-cell closure.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PROJECT_ID = "tetra_mechanical_extension"
PAPER_ID = "s4_cl5_one_parameter_wrapper"
DATE = "2026-06-22"

MANIFESTS = {
    "A6": {
        "route": "B05 common-edge symbolic one-parameter closure",
        "claim_id": "S4-CL5-A6-B05-SYMBOLIC-CLOSURE",
        "command": "python scripts/build_s4_cl5_a6_one_parameter_ray_closure_package.py",
        "path": Path("results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/manifests/b05_a6_one_parameter_ray_closure_package_manifest.json"),
        "expected": {"record_count": 7, "one_parameter_symbolic_closed_count": 7},
    },
    "A7A": {
        "route": "B06/B07 shared-face residual Sturm certificate",
        "claim_id": "S4-CL5-A7A-SHARED-FACE-RESIDUAL-STURM",
        "command": "python scripts/build_s4_cl5_a7a_shared_face_residual_sturm_certificate.py",
        "path": Path("results/historical_s4_median_planes/exact_interval/shared_face_residual/manifests/shared_face_a7a_residual_sturm_certificate_manifest.json"),
        "expected": {"record_count": 2, "positive_on_open_ray_superset_count": 2},
    },
    "A7B": {
        "route": "B03 ordinary non-contact ray-vacuity certificate",
        "claim_id": "S4-CL5-A7B-B03-RAY-VACUITY",
        "command": "python scripts/build_s4_cl5_a7b_b03_ray_vacuity_certificate.py",
        "path": Path("results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/manifests/b03_a7b_ray_vacuity_certificate_manifest.json"),
        "expected": {"record_count": 2, "pair_count": 12, "sturm_obligation_count": 0},
    },
    "A7C": {
        "route": "B04 selected-hinge contact-side certificate",
        "claim_id": "S4-CL5-A7C-B04-CONTACT-SIDE",
        "command": "python scripts/build_s4_cl5_a7c_selected_hinge_contact_side_certificate.py",
        "path": Path("results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json"),
        "expected": {"record_count": 6, "contact_side_certificate_count": 6},
    },
    "A7D": {
        "route": "Scoped zero-thickness one-parameter wrapper",
        "claim_id": "S4-CL5-A7D-ONE-PARAMETER-WRAPPER",
        "command": "python scripts/build_s4_cl5_a7d_one_parameter_theorem_wrapper.py",
        "path": Path("results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/manifests/a7d_one_parameter_theorem_wrapper_manifest.json"),
        "expected": {"record_count": 2, "wrapper_closed_count": 2},
    },
}

OUT_DIR = Path("results/historical_s4_median_planes/exact_interval/papp_review")
EXP_JSON = OUT_DIR / "a8_experiment_ledger.json"
CLAIM_JSON = OUT_DIR / "a8_claim_ledger.json"
EXP_MD = Path("docs/S4_CL5_A8_EXPERIMENT_LEDGER.md")
CLAIM_MD = Path("docs/S4_CL5_A8_CLAIM_LEDGER.md")

NONCLAIMS = [
    "no_physical_hingeability_claim",
    "no_three_parameter_bounded_cell_claim",
    "no_global_s4_hingeability_claim",
    "no_dynamic_connectedness_claim",
    "no_accepted_schema_v1_report_claim",
    "no_positive_clearance_for_selected_hinges_claim",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(path)
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def validate_expected(step: str, data: dict[str, Any], expected: dict[str, int]) -> list[str]:
    failures = []
    for key, value in expected.items():
        if data.get(key) != value:
            failures.append(f"{step}:{key}: expected {value}, got {data.get(key)}")
    return failures


def build_experiment_rows() -> tuple[list[dict[str, Any]], list[str]]:
    rows = []
    failures: list[str] = []
    for step, spec in MANIFESTS.items():
        manifest_path = ROOT / spec["path"]
        data = read_json(manifest_path)
        failures.extend(validate_expected(step, data, spec["expected"]))
        rows.append({
            "experiment_id": f"S4-CL5-{step}-REPLAY",
            "route": spec["route"],
            "claim_ids": [spec["claim_id"]],
            "inputs": [rel(manifest_path)],
            "parameters": {"case_id": CASE_ID, "domain": "theta=0 plus 0<theta<=120 degrees"},
            "output_artifacts": [rel(manifest_path)] + [item.get("object_record") for item in data.get("records", []) if item.get("object_record")],
            "status": "pass" if not validate_expected(step, data, spec["expected"]) else "fail",
            "replay_command": spec["command"],
            "expected_metrics": spec["expected"],
            "observed_metrics": {key: data.get(key) for key in spec["expected"]},
            "manifest_id": data.get("manifest_id"),
            "claim_level_project_local": data.get("claim_level"),
            "nonclaim": data.get("nonclaim", []),
            "sha256": sha256(manifest_path),
        })
    return rows, failures


def build_claims() -> list[dict[str, Any]]:
    a7d_path = ROOT / MANIFESTS["A7D"]["path"]
    a7d = read_json(a7d_path)
    return [
        {
            "claim_id": "S4-CL5-A6-B05-SYMBOLIC-CLOSURE",
            "short_name": "A6 B05 symbolic one-parameter closure",
            "statement": "All seven current B05 common-edge symbolic one-parameter records are closed by the A3/A4 and A5 algebraic certificate layers.",
            "objects": ["TREE_007", "TREE_021"],
            "scope": "B05 common-edge layer only; zero-thickness one-parameter symbolic ray; no accepted schema-v1 B05 reports.",
            "claim_level": "CL3_certified_finite_result",
            "status": "active",
            "evidence": {"manifest": rel(ROOT / MANIFESTS["A6"]["path"]), "expected": MANIFESTS["A6"]["expected"]},
            "dependencies": ["A3/A4 Weierstrass/Sturm sign certificate", "A5 support-switch root audit"],
            "red_team_status": "pending_A8_red_team",
            "public_claim_boundary": "May be described as a certified finite symbolic layer, not as full hingeability.",
            "what_can_be_said": "A6 closes the B05 symbolic one-parameter common-edge layer under its declared scope.",
            "what_cannot_be_said": "A6 closes all pair predicates, physical hingeability, or accepted B05 operation enclosures.",
            "last_reviewed": DATE,
        },
        {
            "claim_id": "S4-CL5-A7A-SHARED-FACE-RESIDUAL-STURM",
            "short_name": "A7a shared-face residual Sturm certificate",
            "statement": "The two residual shared-face formula targets are positive on the certified open one-parameter superset.",
            "objects": ["TREE_007 P2-P3", "TREE_021 P0-P2"],
            "scope": "B06/B07 shared-face residual formula-sign layer on 0<t<2; no accepted schema-v1 reports.",
            "claim_level": "CL3_certified_finite_result",
            "status": "active",
            "evidence": {"manifest": rel(ROOT / MANIFESTS["A7A"]["path"]), "expected": MANIFESTS["A7A"]["expected"]},
            "dependencies": ["Lemma-06 residual shared-face formula source"],
            "red_team_status": "pending_A8_red_team",
            "public_claim_boundary": "May be described as exact formula-sign certification for two routed pairs.",
            "what_can_be_said": "A7a closes the two shared-face residual formula targets on the ray superset.",
            "what_cannot_be_said": "A7a proves all shared-face geometry, physical clearance, or global S4 hingeability.",
            "last_reviewed": DATE,
        },
        {
            "claim_id": "S4-CL5-A7B-B03-RAY-VACUITY",
            "short_name": "A7b B03 ray-vacuity certificate",
            "statement": "The scoped one-parameter representative ray has zero route-clean ordinary non-contact B03 obligations; all twelve pair routes are B04, B05, or B06/B07.",
            "objects": ["TREE_007", "TREE_021"],
            "scope": "Route/vacuity claim only for the representative one-parameter ray; not a B03 positive-margin certificate.",
            "claim_level": "CL3_certified_finite_result",
            "status": "active",
            "evidence": {"manifest": rel(ROOT / MANIFESTS["A7B"]["path"]), "expected": MANIFESTS["A7B"]["expected"]},
            "dependencies": ["two_class_ray_cell_guard routing ledger", "A7d route ledger"],
            "red_team_status": "pending_A8_red_team",
            "public_claim_boundary": "May say B03 is vacuous on this scoped ray, not that ordinary clearance is globally solved.",
            "what_can_be_said": "A7b records zero B03 Sturm obligations for the scoped ray.",
            "what_cannot_be_said": "A7b proves positive B03 clearance or bounded-cell B03 closure.",
            "last_reviewed": DATE,
        },
        {
            "claim_id": "S4-CL5-A7C-B04-CONTACT-SIDE",
            "short_name": "A7c selected-hinge contact-side certificate",
            "statement": "All six selected-hinge contact-side records have constant nonzero signed orientation on the open ray superset.",
            "objects": ["TREE_007 selected hinges", "TREE_021 selected hinges"],
            "scope": "B04 selected-hinge zero-margin contact-side semantics on 0<t<2; not positive separation.",
            "claim_level": "CL3_certified_finite_result",
            "status": "active",
            "evidence": {"manifest": rel(ROOT / MANIFESTS["A7C"]["path"]), "expected": MANIFESTS["A7C"]["expected"]},
            "dependencies": ["Lemma 02 endpoint", "Lemma 03 kinematics/signs", "B04 contact-side review"],
            "red_team_status": "pending_A8_red_team",
            "public_claim_boundary": "May say contact side is certified; must not say positive clearance.",
            "what_can_be_said": "A7c closes selected-hinge contact-side orientation for the scoped ray.",
            "what_cannot_be_said": "A7c proves positive clearance, physical hinge hardware, or non-hinge contact closure.",
            "last_reviewed": DATE,
        },
        {
            "claim_id": "S4-CL5-A7D-ONE-PARAMETER-WRAPPER",
            "short_name": "A7d scoped one-parameter wrapper",
            "statement": "For TREE_007 and TREE_021, theta=0 plus 0<theta<=120 degrees is covered pair-by-pair by completed A6/A7a/A7b/A7c certificate layers, with aggregate routes B04=6, B05=4, B06/B07=2 and B03=0.",
            "objects": ["TREE_007", "TREE_021"],
            "scope": "Scoped zero-thickness one-parameter wrapper only; two representative trees; no physical hingeability or three-parameter bounded-cell closure.",
            "claim_level": "CL5_internal_theorem",
            "status": "draft",
            "evidence": {"manifest": rel(a7d_path), "expected": MANIFESTS["A7D"]["expected"], "route_counts": a7d.get("predicate_route_counts")},
            "dependencies": [
                "S4-CL5-A6-B05-SYMBOLIC-CLOSURE",
                "S4-CL5-A7A-SHARED-FACE-RESIDUAL-STURM",
                "S4-CL5-A7B-B03-RAY-VACUITY",
                "S4-CL5-A7C-B04-CONTACT-SIDE",
                "S4_LEMMA_02_CLOSED_ENDPOINT",
            ],
            "proof_obligations": ["A8 red-team must accept the scoped theorem wording before promotion"],
            "red_team_status": "pending_A8_red_team",
            "public_claim_boundary": "Candidate theorem wording must remain scoped to two trees, zero thickness, and one parameter.",
            "what_can_be_said": "A7d is a scoped one-parameter wrapper candidate assembled from completed certificate layers.",
            "what_cannot_be_said": "A7d proves physical buildability, CAD validity, 3-parameter clearance, dynamic connectedness, or global S4 hingeability.",
            "last_reviewed": DATE,
        },
        {
            "claim_id": "S4-CL5-THREE-PARAMETER-BOUNDED-CELLS",
            "short_name": "Three-parameter bounded-cell closure",
            "statement": "A bounded three-parameter neighborhood of the S4 motion is certified collision-safe.",
            "objects": ["S4 bounded cells"],
            "scope": "Future extension, not part of A7d.",
            "claim_level": "CLB_blocked",
            "status": "blocked",
            "evidence": {},
            "proof_obligations": ["Define 3-parameter cell model", "Build exact/interval guards", "Close operation enclosures"],
            "red_team_status": "not_applicable_until_started",
            "public_claim_boundary": "Must not be stated as complete.",
            "what_can_be_said": "Three-parameter bounded cells are a future branch.",
            "what_cannot_be_said": "A7d closes three-parameter bounded cells.",
            "last_reviewed": DATE,
        },
        {
            "claim_id": "S4-CL5-PHYSICAL-HINGEABILITY",
            "short_name": "Physical hingeability / real-world buildability",
            "statement": "A real S4 mechanism with thickness, tolerances, and hinge hardware is buildable and collision-safe.",
            "objects": ["physical S4 mechanism"],
            "scope": "Future real-world branch, not part of A7d.",
            "claim_level": "CLB_blocked",
            "status": "blocked",
            "evidence": {},
            "proof_obligations": ["Thickness model", "hinge hardware model", "CAD/mesh validation", "tolerance/sweep-volume checks"],
            "red_team_status": "not_applicable_until_started",
            "public_claim_boundary": "Must not be stated as complete.",
            "what_can_be_said": "Physical hingeability remains future work after package review.",
            "what_cannot_be_said": "A7d proves real-world buildability.",
            "last_reviewed": DATE,
        },
    ]


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def experiment_markdown(rows: list[dict[str, Any]], failures: list[str]) -> str:
    table = markdown_table(
        ["Experiment ID", "Route", "Claim IDs", "Inputs", "Parameters", "Output artifacts", "Status", "Replay command"],
        [[
            r["experiment_id"],
            r["route"],
            ", ".join(r["claim_ids"]),
            ", ".join(r["inputs"]),
            json.dumps(r["parameters"], sort_keys=True),
            f"{len(r['output_artifacts'])} artifacts; manifest={r['inputs'][0]}",
            r["status"],
            f"`{r['replay_command']}`",
        ] for r in rows],
    )
    return f"""# S4 CL5 A8 Experiment Ledger

Project: {PROJECT_ID}
Date: {DATE}

This ledger is generated by `scripts/build_s4_cl5_a8_review_ledgers.py` from
A6/A7a/A7b/A7c/A7d manifests.  It is a PAPP experiment-ledger artifact for the
post-A7d review gate, not a paper package release.

{table}

## Environment

Python: project default interpreter used by prior A6/A7d commands.
OS: Windows / PowerShell workspace.
Dependencies: Python standard library plus dependencies already required by the upstream A6/A7d scripts.
Random seeds: not applicable for these deterministic manifest-building commands.

## Expected Metrics

```json
{json.dumps({r['experiment_id']: r['expected_metrics'] for r in rows}, indent=2, sort_keys=True)}
```

## Observed Metrics

```json
{json.dumps({r['experiment_id']: r['observed_metrics'] for r in rows}, indent=2, sort_keys=True)}
```

## Generated Obligations

- Run A8 red-team before claim promotion.
- Keep public wording inside the A8 claim boundary.
- Build the reviewer package only after red-team passes or explicitly records blockers.

## Generated Negatives

- No route-clean B03 ordinary non-contact obligations on the scoped ray.
- No accepted schema-v1 reports are promoted by A6/A7d.
- No physical hingeability or three-parameter bounded-cell closure is claimed.

## Validation

Manifest metric failures: {len(failures)}

{chr(10).join('- ' + item for item in failures) if failures else '- none'}
"""


def claim_markdown(claims: list[dict[str, Any]]) -> str:
    claim_rows = [[
        c["claim_id"], c["claim_level"], c["status"], c["statement"], c["scope"], json.dumps(c.get("evidence", {}), sort_keys=True), c["public_claim_boundary"],
    ] for c in claims]
    blocked_rows = [[
        c["claim_id"], "; ".join(c.get("proof_obligations", [])) or "blocked by scope", c.get("what_cannot_be_said", ""), "Do not promote before required artifact/proof exists",
    ] for c in claims if c["claim_level"] in {"CLB_blocked", "CLO_obligation"} or c["status"] == "blocked"]
    return f"""# S4 CL5 A8 Claim Ledger

Project: {PROJECT_ID}
Paper/package candidate: {PAPER_ID}
Date: {DATE}

This ledger translates the project-local A6/A7d claim levels into PAPP claim
levels for the post-A7d review gate.  It proposes A7d only as a `draft`
`CL5_internal_theorem` candidate pending red-team; the component A6/A7a/A7b/A7c
layers are `CL3_certified_finite_result` under their declared finite scopes.

## Claim Levels Used

- `CL3_certified_finite_result`: exact/certified finite or symbolic certificate layer.
- `CL5_internal_theorem`: internal theorem candidate, requiring proof wording and red-team acceptance.
- `CLB_blocked`: future branch or overclaim blocked by missing artifacts.

## Claims

{markdown_table(['Claim ID', 'Level', 'Status', 'Statement', 'Scope', 'Evidence', 'Public boundary'], claim_rows)}

## Blocked Claims

{markdown_table(['Claim ID', 'Blocker', 'Needed artifact/proof', 'Next action'], blocked_rows)}

## Public Boundary Summary

Can say after red-team passes:

- A7d is a scoped zero-thickness one-parameter wrapper for `TREE_007` and `TREE_021`.
- On `theta=0` plus `0<theta<=120 degrees`, all 12 unordered piece-pair routes are covered by A6/A7a/A7b/A7c layers.

Must not say:

- S4 is physically buildable.
- Three-parameter bounded cells are closed.
- Global S4 hingeability is proved.
- Selected hinges have positive clearance.

## Nonclaims

{chr(10).join('- `' + item + '`' for item in NONCLAIMS)}
"""


def main() -> int:
    rows, failures = build_experiment_rows()
    claims = build_claims()
    exp = {
        "project_id": PROJECT_ID,
        "paper_id": PAPER_ID,
        "date": DATE,
        "experiments": rows,
        "validation_failures": failures,
        "status": "pass" if not failures else "fail",
    }
    claim = {
        "project_id": PROJECT_ID,
        "paper_id": PAPER_ID,
        "claims": claims,
        "status": "draft_pending_red_team",
    }
    write_json(ROOT / EXP_JSON, exp)
    write_json(ROOT / CLAIM_JSON, claim)
    write_text(ROOT / EXP_MD, experiment_markdown(rows, failures))
    write_text(ROOT / CLAIM_MD, claim_markdown(claims))
    print(f"A8 experiment ledger rows: {len(rows)}")
    print(f"A8 claim ledger rows: {len(claims)}")
    print(f"manifest metric failures: {len(failures)}")
    print(f"experiment ledger: {rel(ROOT / EXP_MD)}")
    print(f"claim ledger: {rel(ROOT / CLAIM_MD)}")
    print(f"experiment json: {rel(ROOT / EXP_JSON)}")
    print(f"claim json: {rel(ROOT / CLAIM_JSON)}")
    return 0 if not failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
