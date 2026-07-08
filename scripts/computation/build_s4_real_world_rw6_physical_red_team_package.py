#!/usr/bin/env python
"""Build RW6 physical red-team/reviewer package for the S4 real-world branch.

RW6 is a serious review gate over RW1-RW5.  It packages evidence, blockers,
claim boundaries, a recommended frontier candidate, and the explicit route to a
future prototype.  It does not assert physical hingeability, direct
printability, CAD boolean validity, G-code readiness, fabrication readiness, or
prototype validation.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
JSON_PATH = RESULT_ROOT / "rw6_physical_red_team_package.json"
DOC_PATH = ROOT / "docs" / "S4_RW6_PHYSICAL_RED_TEAM_PACKAGE.md"
PACKAGE_ROOT = ROOT / "paper" / "s4_real_world_physical_review"
PACKAGE_JSON_PATH = PACKAGE_ROOT / "results" / "rw6_physical_red_team_package.json"

RW_SOURCES = [
    ("RW1", "physical source lock", RESULT_ROOT / "rw1_physical_source_lock.json"),
    ("RW2", "mesh/CAD payload adapter", RESULT_ROOT / "rw2_mesh_payload_manifest.json"),
    ("RW3", "kinematics adapter", RESULT_ROOT / "rw3_kinematics_adapter_manifest.json"),
    ("RW4", "sampled collision/sweep evidence", RESULT_ROOT / "rw4_collision_sweep_report.json"),
    ("RW4b", "conservative interval/swept validation", RESULT_ROOT / "rw4b_interval_sweep_validation_report.json"),
    ("RW4c", "targeted blocker reduction", RESULT_ROOT / "rw4c_blocker_reduction_report.json"),
    ("RW4d", "clearance/hardware model", RESULT_ROOT / "rw4d_clearance_hardware_model_report.json"),
    ("RW4e", "relief/hardware payload", RESULT_ROOT / "rw4e_relief_hardware_payload_report.json"),
    ("RW4f", "CAD/envelope replay", RESULT_ROOT / "rw4f_cad_envelope_replay_report.json"),
    ("RW4g", "hardware mitigation replay", RESULT_ROOT / "rw4g_hardware_mitigation_replay_report.json"),
    ("RW4h", "combined CAD-mesh proxy", RESULT_ROOT / "rw4h_combined_cad_mesh_proxy_report.json"),
    ("RW5", "printability/fabrication preflight", RESULT_ROOT / "rw5_printability_fabrication_preflight_report.json"),
]

PACKAGE_FILES = [
    "README.md",
    "README_REVIEWER.md",
    "REPRODUCE.md",
    "CITATION.cff",
    "LICENSE",
    "LICENSE_NOTE.md",
    "docs/CLAIM_LEDGER.md",
    "docs/EVIDENCE_LEDGER.md",
    "docs/BLOCKER_LEDGER.md",
    "docs/RED_TEAM_REPORT.md",
    "docs/PUBLIC_CLAIM_BOUNDARY.md",
    "docs/PROTOTYPE_ROUTE.md",
    "docs/PAPER_TO_ENGINE_TRACEABILITY.md",
    "results/rw6_physical_red_team_package.json",
]

ALLOWED_INTERNAL_CLAIMS = [
    "RW1-RW5 evidence is packaged for physical red-team review.",
    "RW5 selects a recommended frontier candidate for post-RW6 prototype work.",
    "The post-RW6 prototype route is explicit and ordered.",
    "Direct fabrication remains blocked until CAD repair, export, slicer, and physical test gates pass.",
]

BLOCKED_CLAIMS = [
    "physical hingeability",
    "finite-thickness continuous clearance certification",
    "CAD boolean validity",
    "direct printability",
    "STL/3MF export readiness",
    "G-code readiness",
    "fabrication readiness",
    "prototype validation",
    "measured moving prototype success",
]

PHYSICAL_REVIEW_BLOCKERS = [
    "real hinge pin/boss/knuckle geometry is not designed",
    "segmented endpoint setback is an envelope model, not assembled hardware",
    "assembly access is heuristic and not validated by real hardware insertion",
    "material strength, anisotropy, friction, wear, and pin retention are untested",
    "sampled envelope replay is not a continuous finite-thickness proof",
    "static fit coupon has not been printed or measured",
    "moving prototype has not been printed or measured",
]

OVERCLAIM_RISKS = [
    "calling RW4h CAD without saying diagnostic proxy",
    "using manifold/watertight permissive gate as direct printability",
    "treating the RW5 candidate as physically optimal rather than review-selected",
    "confusing sampled envelope replay with continuous clearance proof",
    "confusing clearance-budget replay with finite-thickness hingeability",
    "saying RW6 approves a prototype rather than approving the next prototype route",
]

POST_RW6_PROTOTYPE_CHECKLIST = [
    "convert relief proxy boxes into candidate-only boolean-subtracted CAD features",
    "design real hinge hardware: pin, boss/knuckle, setback, and assembly access",
    "run mesh repair and winding normalization on the selected candidate only",
    "export STL or 3MF for the selected candidate",
    "run slicer/layer preview with a chosen machine, material, orientation, and support policy",
    "print a low-risk static fit coupon first",
    "measure hinge-axis fit, relief clearance, and opening range on the coupon",
    "print and measure a moving prototype only after the coupon gate passes",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def package_rel(path: Path) -> str:
    return path.relative_to(PACKAGE_ROOT).as_posix()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def yes(value: bool) -> str:
    return "yes" if value else "NO"


def metric(d: dict[str, Any], dotted: str, default: Any = None) -> Any:
    cur: Any = d
    for part in dotted.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def stage_metrics(stage: str, d: dict[str, Any]) -> dict[str, Any]:
    if stage == "RW1":
        return {
            "first_tree_named": metric(d, "acceptance.first_tree_named"),
            "second_tree_named": metric(d, "acceptance.second_tree_named"),
            "exploratory_values": metric(d, "acceptance.numeric_values_are_marked_exploratory"),
        }
    if stage == "RW2":
        return {
            "piece_count_is_4": metric(d, "acceptance.piece_count_is_4"),
            "all_axes_nonzero_length": metric(d, "acceptance.all_axes_nonzero_length"),
            "hardware_geometry_absent": metric(d, "acceptance.hardware_geometry_absent"),
        }
    if stage == "RW3":
        return {
            "sample_count": metric(d, "acceptance.sample_count"),
            "all_samples_collision_free": metric(d, "acceptance.all_samples_collision_free"),
            "hardware_geometry_absent": metric(d, "acceptance.hardware_geometry_absent"),
        }
    if stage == "RW4":
        return {
            "total_sample_count": metric(d, "summary.total_sample_count"),
            "nonhinge_candidate_segments": metric(d, "summary.total_nonhinge_tier2_candidate_segment_count"),
            "sampled_collision_free": metric(d, "summary.all_samples_collision_free"),
        }
    if stage == "RW4b":
        return {
            "candidate_segments": metric(d, "summary.total_candidate_segment_count"),
            "certified_segments": metric(d, "summary.total_certified_segment_count"),
            "blocked_segments": metric(d, "summary.total_blocked_segment_count"),
        }
    if stage == "RW4c":
        return {
            "residual_shared_edge": metric(d, "summary.residual_shared_edge_blocker_count"),
            "residual_shared_face": metric(d, "summary.residual_shared_face_blocker_count"),
            "clearance_model_required": metric(d, "summary.clearance_model_required"),
        }
    if stage == "RW4d":
        return {
            "relief_groups": metric(d, "summary.clearance_relief_group_count"),
            "full_grid_candidates": metric(d, "summary.full_parameter_grid_candidate_count_before_cad"),
            "max_required_model_clearance": metric(d, "summary.maximum_required_model_clearance"),
        }
    if stage == "RW4e":
        return {
            "candidate_count": metric(d, "summary.candidate_count"),
            "relief_group_count": metric(d, "summary.relief_group_count"),
            "min_clearance_margin_model_units": metric(d, "summary.minimum_clearance_margin_model_units"),
        }
    if stage == "RW4f":
        return {
            "frontier_candidates": metric(d, "summary.frontier_candidate_count"),
            "passing_candidates": metric(d, "summary.candidates_passing_sampled_envelope_replay"),
            "rw5_unblocked": metric(d, "summary.rw5_unblocked"),
        }
    if stage == "RW4g":
        return {
            "frontier_candidates": metric(d, "summary.frontier_candidate_count"),
            "passing_after_setback": metric(d, "summary.candidates_passing_after_setback"),
            "minimum_remaining_axis_fraction": metric(d, "summary.minimum_remaining_axis_length_fraction"),
        }
    if stage == "RW4h":
        return {
            "candidate_count": metric(d, "summary.combined_proxy_candidate_count"),
            "relief_proxy_count": metric(d, "summary.relief_proxy_count"),
            "mesh_smoke_valid": metric(d, "summary.mesh_smoke_valid"),
        }
    if stage == "RW5":
        return {
            "candidate_count": metric(d, "summary.candidate_count"),
            "rw6_ready_candidates": metric(d, "summary.proxy_candidates_ready_for_rw6_review"),
            "direct_fabrication_ready": metric(d, "summary.direct_fabrication_ready_candidates"),
            "recommended": metric(d, "summary.recommended_rw6_frontier_candidate"),
        }
    return {}


def build_evidence_ledger() -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    ledger = []
    loaded = {}
    for stage, label, path in RW_SOURCES:
        present = path.exists()
        payload = load_json(path) if present else {}
        if present:
            loaded[stage] = payload
        ledger.append(
            {
                "stage": stage,
                "label": label,
                "path": rel(path),
                "present": present,
                "status": payload.get("status", "missing"),
                "report_id": payload.get("report_id"),
                "next_task": payload.get("next_task"),
                "key_metrics": stage_metrics(stage, payload),
            }
        )
    return ledger, loaded


def recommended_candidate(rw5: dict[str, Any]) -> dict[str, Any]:
    rec = metric(rw5, "summary.recommended_rw6_frontier_candidate")
    for item in rw5.get("candidate_results", []):
        if item.get("candidate_id") == rec:
            return item
    return {}


def build_red_team_checks(evidence: list[dict[str, Any]], loaded: dict[str, dict[str, Any]], rec: dict[str, Any]) -> list[dict[str, Any]]:
    rw5 = loaded.get("RW5", {})
    blockers = set(rw5.get("fabrication_blockers", []))
    acceptance = rw5.get("acceptance", {})
    checks = [
        ("RW6-RT-01", all(item["present"] for item in evidence), "critical", "RW1-RW5 evidence artifacts are present", "Restore missing source artifacts before review"),
        ("RW6-RT-02", metric(rw5, "summary.rw6_unblocked") is True, "critical", "RW5 explicitly unblocks RW6 review", "Re-run RW5 or keep RW6 blocked"),
        ("RW6-RT-03", bool(rec), "critical", "Recommended frontier candidate is present in RW5 candidate list", "Select a concrete candidate before prototype routing"),
        ("RW6-RT-04", metric(rw5, "summary.direct_fabrication_ready_candidates") == 0, "critical", "Direct fabrication remains blocked, as expected", "Do not claim fabrication readiness"),
        ("RW6-RT-05", "relief_geometry_is_proxy_boxes_not_boolean_subtracted" in blockers, "major", "CAD boolean relief blocker is explicit", "Document boolean CAD repair before prototype"),
        ("RW6-RT-06", "mesh_winding_repair_required_before_export" in blockers, "major", "Mesh winding repair blocker is explicit", "Normalize winding before STL/3MF export"),
        ("RW6-RT-07", "slicer_gcode_not_run" in blockers and acceptance.get("slicer_gcode_run") is False, "major", "Slicer/G-code gate is explicit and not run", "Run slicer/layer preview only after CAD repair"),
        ("RW6-RT-08", acceptance.get("prototype_validation_run") is False, "major", "Prototype validation is explicitly not run", "Do not claim prototype success"),
        ("RW6-RT-09", metric(rw5, "papp_proxy_gate.winding_bfs_ok") is False, "major", "PAPP proxy gate winding issue is visible", "Repair or re-export selected candidate mesh"),
        ("RW6-RT-10", len(rw5.get("post_rw6_prototype_route", [])) >= 6, "major", "Post-RW6 prototype route has ordered gates", "Record full route before physical build"),
        ("RW6-RT-11", acceptance.get("report_says_no_physical_claim") is True, "critical", "RW5 preserves no-physical-claim boundary", "Keep public wording inside claim boundary"),
        ("RW6-RT-12", metric(rw5, "summary.papp_proxy_gate_strict_export_ready") is False, "major", "Strict export readiness is false", "Export only after candidate-only CAD/mesh repair"),
    ]
    return [
        {
            "id": cid,
            "status": "pass" if ok else "fail",
            "severity": severity,
            "finding": finding,
            "required_action_if_fail": action,
        }
        for cid, ok, severity, finding, action in checks
    ]


def build_claim_ledger() -> list[dict[str, Any]]:
    rows = []
    for claim in ALLOWED_INTERNAL_CLAIMS:
        rows.append({"claim": claim, "scope": "internal RW6 review", "status": "allowed"})
    for claim in BLOCKED_CLAIMS:
        rows.append({"claim": claim, "scope": "physical/prototype", "status": "blocked"})
    return rows


def build_result() -> dict[str, Any]:
    evidence, loaded = build_evidence_ledger()
    rw5 = loaded.get("RW5", {})
    rec = recommended_candidate(rw5)
    red_team = build_red_team_checks(evidence, loaded, rec)
    hard_failures = [c for c in red_team if c["status"] != "pass" and c["severity"] in {"critical", "major"}]
    rw5_route = rw5.get("post_rw6_prototype_route", [])
    candidate_summary = {
        "candidate_id": rec.get("candidate_id"),
        "parameters": rec.get("parameters", {}),
        "preflight_ok_profiles": rec.get("preflight_ok_profiles", []),
        "preflight_ok_profile_count": rec.get("preflight_ok_profile_count"),
        "endpoint_access_margin_mm": metric(rec, "feature_checks.endpoint_access_margin_mm"),
        "minimum_remaining_axis_mm": metric(rec, "feature_checks.minimum_remaining_axis_mm"),
        "minimum_relief_clearance_margin_mm": metric(rec, "feature_checks.minimum_relief_clearance_margin_mm"),
        "fabrication_ready_without_cad_repair": rec.get("fabrication_ready_without_cad_repair"),
    }
    status = "rw6_physical_red_team_completed_prototype_route_unblocked_direct_fabrication_blocked"
    return {
        "report_id": "S4-RW6-PHYSICAL-RED-TEAM-PACKAGE-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": status,
        "template_source": "<private-workspace>/PAPP/projects/PAPP v4/templates/paper_package",
        "evidence_ledger": evidence,
        "recommended_frontier_candidate": candidate_summary,
        "fabrication_blockers": rw5.get("fabrication_blockers", []),
        "physical_review_blockers": PHYSICAL_REVIEW_BLOCKERS,
        "overclaim_risks": OVERCLAIM_RISKS,
        "blocked_claims": BLOCKED_CLAIMS,
        "allowed_internal_claims": ALLOWED_INTERNAL_CLAIMS,
        "claim_ledger": build_claim_ledger(),
        "red_team_checks": red_team,
        "red_team_status_counts": {
            "pass": sum(1 for c in red_team if c["status"] == "pass"),
            "fail": sum(1 for c in red_team if c["status"] == "fail"),
        },
        "hard_failures": hard_failures,
        "post_rw6_prototype_route": rw5_route,
        "post_rw6_prototype_checklist": POST_RW6_PROTOTYPE_CHECKLIST,
        "rw6_package_ready": len(hard_failures) == 0,
        "post_rw6_prototype_route_unblocked": len(hard_failures) == 0 and len(rw5_route) >= 6,
        "direct_fabrication_ready": False,
        "physical_hingeability_claim_allowed": False,
        "public_export_ready": False,
        "claim_promotion_allowed": False,
        "acceptance": {
            "rw1_to_rw5_artifacts_present": all(item["present"] for item in evidence),
            "rw5_unblocks_rw6": metric(rw5, "summary.rw6_unblocked") is True,
            "recommended_candidate_selected": bool(rec),
            "direct_fabrication_blocked": metric(rw5, "summary.direct_fabrication_ready_candidates") == 0,
            "fabrication_blockers_recorded": len(rw5.get("fabrication_blockers", [])) >= 1,
            "physical_review_blockers_recorded": len(PHYSICAL_REVIEW_BLOCKERS) >= 1,
            "prototype_route_recorded": len(rw5_route) >= 6,
            "prototype_checklist_recorded": len(POST_RW6_PROTOTYPE_CHECKLIST) >= 8,
            "physical_claim_blocked": True,
            "cad_boolean_validity_blocked": True,
            "slicer_gcode_blocked": True,
            "prototype_validation_blocked": True,
        },
        "next_task": "Post-RW6 prototype route: candidate-only CAD boolean reliefs, mesh repair/winding normalization, STL/3MF export, slicer/layer preview, static fit coupon, then measured moving prototype.",
    }


def evidence_markdown(result: dict[str, Any]) -> str:
    rows = []
    for item in result["evidence_ledger"]:
        metrics = "; ".join(f"{k}={v}" for k, v in item["key_metrics"].items())
        rows.append([item["stage"], item["label"], item["path"], yes(item["present"]), item["status"], metrics])
    return "# RW6 Evidence Ledger\n\n" + table(["Stage", "Scope", "Artifact", "Present", "Status", "Key metrics"], rows) + "\n"


def blocker_markdown(result: dict[str, Any]) -> str:
    rows = [[i + 1, blocker, "blocks direct fabrication/prototype claim"] for i, blocker in enumerate(result["fabrication_blockers"])]
    physical_rows = [[i + 1, blocker, "blocks physical hingeability/prototype claim"] for i, blocker in enumerate(result["physical_review_blockers"])]
    return (
        "# RW6 Blocker Ledger\n\n"
        "## Fabrication/CAD/Slicer Blockers\n\n"
        + table(["#", "Blocker", "Effect"], rows)
        + "\n\n## Physical Prototype Blockers\n\n"
        + table(["#", "Blocker", "Effect"], physical_rows)
        + "\n"
    )


def claim_markdown(result: dict[str, Any]) -> str:
    rows = [[item["claim"], item["scope"], item["status"]] for item in result["claim_ledger"]]
    return "# RW6 Claim Ledger\n\n" + table(["Claim", "Scope", "Status"], rows) + "\n"


def red_team_markdown(result: dict[str, Any]) -> str:
    rows = [[c["id"], c["status"], c["severity"], c["finding"], c["required_action_if_fail"]] for c in result["red_team_checks"]]
    return f"""# RW6 Physical Red-Team Report

Status: {'passed for post-RW6 prototype routing' if result['rw6_package_ready'] else 'blocked'}
Date: {DATE}

Publication blocked: yes
Claim promotion allowed: no
Physical hingeability claim allowed: no
Direct fabrication ready: no

{table(['ID', 'Status', 'Severity', 'Finding', 'Required action if fail'], rows)}

## Residual Risk

RW6 is a review package.  The major residual risks are CAD boolean conversion,
mesh repair/winding normalization, candidate-only export, slicer/layer preview,
static fit measurement, and measured moving prototype validation.

## Overclaim Risks

""" + "\n".join(f"- {risk}" for risk in result["overclaim_risks"]) + "\n"


def public_boundary_markdown(result: dict[str, Any]) -> str:
    can_say = "\n".join(f"- {claim}" for claim in result["allowed_internal_claims"])
    must_not = "\n".join(f"- {claim}" for claim in result["blocked_claims"])
    return f"""# RW6 Public Claim Boundary

## Can Say Internally

{can_say}

## Can Say Publicly

- A physical review package exists for the S4 real-world branch.
- The package identifies a recommended candidate and explicit blockers before fabrication.

## Must Not Say

{must_not}

## Abstract/README Language Check

Status: public export remains blocked.

Notes: RW6 authorizes only the post-RW6 prototype route, not a prototype claim.
"""


def prototype_route_markdown(result: dict[str, Any]) -> str:
    rows = [[i + 1, step, "required before prototype claim"] for i, step in enumerate(result["post_rw6_prototype_checklist"])]
    rec = result["recommended_frontier_candidate"]
    return f"""# RW6 Post-RW6 Prototype Route

Recommended frontier candidate: `{rec.get('candidate_id')}`

## Candidate Snapshot

| Field | Value |
| --- | --- |
| parameters | `{rec.get('parameters')}` |
| preflight_ok_profiles | `{rec.get('preflight_ok_profiles')}` |
| endpoint_access_margin_mm | `{rec.get('endpoint_access_margin_mm')}` |
| minimum_remaining_axis_mm | `{rec.get('minimum_remaining_axis_mm')}` |
| minimum_relief_clearance_margin_mm | `{rec.get('minimum_relief_clearance_margin_mm')}` |
| fabrication_ready_without_cad_repair | `{rec.get('fabrication_ready_without_cad_repair')}` |

## Ordered Route

{table(['Step', 'Action', 'Gate'], rows)}

No step in this route has been executed by RW6.  The route starts after RW6.
"""


def traceability_markdown(result: dict[str, Any]) -> str:
    rows = [[item["stage"], item["path"], item["report_id"] or "", item["status"]] for item in result["evidence_ledger"]]
    return "# RW6 Paper-To-Engine Traceability\n\n" + table(["Stage", "Artifact", "Report ID", "Status"], rows) + "\n"


def reproduce_markdown() -> str:
    script = "scripts/build_s4_real_world_rw6_physical_red_team_package.py"
    return f"""# RW6 Reproduce

From `<private-workspace>/Tetra/08-mechanical-extension`:

```powershell
python {script}
```

Expected outputs:

- `docs/S4_RW6_PHYSICAL_RED_TEAM_PACKAGE.md`
- `results/historical_s4_median_planes/real_world/rw6_physical_red_team_package.json`
- `paper/s4_real_world_physical_review/`

This replay is a package/review gate.  It does not run CAD booleans, mesh repair,
STL/3MF export, slicer/G-code, or physical prototype validation.
"""


def package_readme(result: dict[str, Any]) -> str:
    rec = result["recommended_frontier_candidate"].get("candidate_id")
    return f"""# S4 Real-World Physical Review Package

Status: RW6 review package ready; direct fabrication blocked.
Date: {DATE}

This package collects RW1-RW5 evidence for the S4 real-world physical branch.
It identifies `{rec}` as the recommended frontier candidate for post-RW6
prototype work, while keeping physical hingeability and direct fabrication
claims blocked.

Read first:

1. `README_REVIEWER.md`
2. `docs/PUBLIC_CLAIM_BOUNDARY.md`
3. `docs/EVIDENCE_LEDGER.md`
4. `docs/BLOCKER_LEDGER.md`
5. `docs/PROTOTYPE_ROUTE.md`
6. `docs/RED_TEAM_REPORT.md`

This package must remain internal until a later package explicitly authorizes
public export.
"""


def reviewer_readme(result: dict[str, Any]) -> str:
    return f"""# RW6 Reviewer Guide

## Ten-Minute Path

1. Read `docs/PUBLIC_CLAIM_BOUNDARY.md`.
2. Read `docs/BLOCKER_LEDGER.md`.
3. Read `docs/PROTOTYPE_ROUTE.md`.
4. Confirm `results/rw6_physical_red_team_package.json` has `rw6_package_ready=true` and `direct_fabrication_ready=false`.

## Thirty-Minute Path

1. Inspect `docs/EVIDENCE_LEDGER.md` stage by stage.
2. Inspect `docs/RED_TEAM_REPORT.md`.
3. Run the command in `REPRODUCE.md`.
4. Verify the recommended candidate and blockers against RW5.

## Standard Agent Package Record

| Package ID | Output Artifact | Status | Notes |
| --- | --- | --- | --- |
| source_lock_agent | RW1 source lock included | done | physical inputs still exploratory |
| claim_curator_agent | `docs/CLAIM_LEDGER.md` | done | direct fabrication blocked |
| experiment_ledger_agent | `docs/EVIDENCE_LEDGER.md` | done | RW1-RW5 present |
| red_team_agent | `docs/RED_TEAM_REPORT.md` | done | no hard RW6 failures |
| reviewer_kit_agent | package docs | done | public export false |

## Known Limits

RW6 does not execute CAD boolean repair, mesh repair, STL/3MF export, slicer
preview, static fit testing, or moving prototype validation.
"""


def license_text() -> str:
    return """MIT License

Copyright (c) 2026

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""


def citation_text() -> str:
    return f"""cff-version: 1.2.0
title: S4 Real-World Physical Review Package
message: Cite this internal review package only with its repository context.
type: dataset
authors:
  - family-names: PAPP
    given-names: S4 Mechanical Extension Workspace
date-released: {DATE}
license: MIT
"""


def package_docs(result: dict[str, Any]) -> dict[str, str]:
    return {
        "README.md": package_readme(result),
        "README_REVIEWER.md": reviewer_readme(result),
        "REPRODUCE.md": reproduce_markdown(),
        "CITATION.cff": citation_text(),
        "LICENSE": license_text(),
        "LICENSE_NOTE.md": "# License Note\n\nPackage/code artifacts use MIT. Future paper text/PDF artifacts remain under the repository's public-paper policy unless a later release note supersedes it.\n",
        "docs/CLAIM_LEDGER.md": claim_markdown(result),
        "docs/EVIDENCE_LEDGER.md": evidence_markdown(result),
        "docs/BLOCKER_LEDGER.md": blocker_markdown(result),
        "docs/RED_TEAM_REPORT.md": red_team_markdown(result),
        "docs/PUBLIC_CLAIM_BOUNDARY.md": public_boundary_markdown(result),
        "docs/PROTOTYPE_ROUTE.md": prototype_route_markdown(result),
        "docs/PAPER_TO_ENGINE_TRACEABILITY.md": traceability_markdown(result),
    }


def main_doc(result: dict[str, Any]) -> str:
    rec = result["recommended_frontier_candidate"]
    summary_rows = [
        ["rw6_package_ready", result["rw6_package_ready"]],
        ["post_rw6_prototype_route_unblocked", result["post_rw6_prototype_route_unblocked"]],
        ["recommended_frontier_candidate", rec.get("candidate_id")],
        ["direct_fabrication_ready", result["direct_fabrication_ready"]],
        ["physical_hingeability_claim_allowed", result["physical_hingeability_claim_allowed"]],
        ["public_export_ready", result["public_export_ready"]],
        ["claim_promotion_allowed", result["claim_promotion_allowed"]],
    ]
    blocker_rows = [[i + 1, b] for i, b in enumerate(result["fabrication_blockers"])]
    physical_blocker_rows = [[i + 1, b] for i, b in enumerate(result["physical_review_blockers"])]
    return f"""# S4 RW6 Physical Red-Team Package

Status: RW6 package completed; post-RW6 prototype route unblocked; direct fabrication blocked.
Date: {DATE}

## Scope

RW6 packages RW1-RW5 evidence for physical review.  It creates a reviewer
package, checks that blockers and nonclaims are visible, and selects the next
candidate route.  It does not make a fabrication or physical hingeability
claim.

## Summary

{table(['Metric', 'Value'], summary_rows)}

## Recommended Candidate

| Field | Value |
| --- | --- |
| candidate_id | `{rec.get('candidate_id')}` |
| parameters | `{rec.get('parameters')}` |
| preflight_ok_profiles | `{rec.get('preflight_ok_profiles')}` |
| endpoint_access_margin_mm | `{rec.get('endpoint_access_margin_mm')}` |
| minimum_remaining_axis_mm | `{rec.get('minimum_remaining_axis_mm')}` |
| minimum_relief_clearance_margin_mm | `{rec.get('minimum_relief_clearance_margin_mm')}` |
| fabrication_ready_without_cad_repair | `{rec.get('fabrication_ready_without_cad_repair')}` |

## Fabrication Blockers

{table(['#', 'Blocker'], blocker_rows)}

## Physical Prototype Blockers

{table(['#', 'Blocker'], physical_blocker_rows)}

## Package Root

`{PACKAGE_ROOT.relative_to(ROOT).as_posix()}`

## Explicit Nonclaims

""" + "\n".join(f"- {claim}" for claim in result["blocked_claims"]) + f"""

## Next Task

{result['next_task']}
"""


def write_package(result: dict[str, Any]) -> None:
    for rel_path, text in package_docs(result).items():
        write_text(PACKAGE_ROOT / rel_path, text)
    write_json(PACKAGE_JSON_PATH, result)


def package_status() -> list[dict[str, Any]]:
    out = []
    for rel_path in PACKAGE_FILES:
        path = PACKAGE_ROOT / rel_path
        out.append({"path": rel_path, "present": path.exists() and path.stat().st_size > 0})
    return out


def main() -> int:
    result = build_result()
    write_package(result)
    result["package_root"] = PACKAGE_ROOT.relative_to(ROOT).as_posix()
    result["package_files"] = package_status()
    result["package_files_ready"] = all(item["present"] for item in result["package_files"])
    result["rw6_package_ready"] = bool(result["rw6_package_ready"] and result["package_files_ready"])
    result["post_rw6_prototype_route_unblocked"] = bool(result["post_rw6_prototype_route_unblocked"] and result["rw6_package_ready"])
    write_package(result)
    write_json(JSON_PATH, result)
    write_text(DOC_PATH, main_doc(result))
    print(f"status={result['status']}")
    print(f"rw6_package_ready={result['rw6_package_ready']}")
    print(f"post_rw6_prototype_route_unblocked={result['post_rw6_prototype_route_unblocked']}")
    print(f"recommended={result['recommended_frontier_candidate'].get('candidate_id')}")
    print(f"direct_fabrication_ready={result['direct_fabrication_ready']}")
    print(f"wrote {DOC_PATH.relative_to(ROOT).as_posix()}")
    print(f"wrote {JSON_PATH.relative_to(ROOT).as_posix()}")
    print(f"wrote {PACKAGE_ROOT.relative_to(ROOT).as_posix()}")
    return 0 if result["rw6_package_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
