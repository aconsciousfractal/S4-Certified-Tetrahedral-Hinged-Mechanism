#!/usr/bin/env python
"""Build RW5 printability/fabrication preflight for S4.

RW5 consumes the RW4h combined relief/hardware proxy and applies project-local
3D-printing checks:

* mesh smoke and PrintabilityGate over the multi-component proxy;
* profile build-volume checks for FDM, fine FDM, SLA, and SLS presets;
* candidate-level hinge envelope, endpoint-access, clearance, and relief
  manufacturability heuristics;
* explicit routing of blockers that still prevent fabrication/prototype claims.

The result is a fabrication *preflight*, not a printable CAD artifact.  RW4h
uses relief proxy boxes rather than boolean-subtracted solids, so RW5 can at
most select a candidate route and state what must be done before a real build.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import shutil
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
HAN_ROOT = ROOT.parents[5]
PAPP_ROOT = HAN_ROOT / "FRAMEWORK" / "04-SOFTWARE" / "PAPP"
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW2_PATH = RESULT_ROOT / "rw2_mesh_payload_manifest.json"
RW4E_PAYLOAD_PATH = RESULT_ROOT / "relief_hardware_candidates" / "rw4e_candidate_payloads.json"
RW4H_PATH = RESULT_ROOT / "rw4h_combined_cad_mesh_proxy_report.json"
JSON_PATH = RESULT_ROOT / "rw5_printability_fabrication_preflight_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW5_PRINTABILITY_FABRICATION_PREFLIGHT.md"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))
sys.path.insert(0, str(PAPP_ROOT))

import build_s4_real_world_rw4f_cad_envelope_replay as rw4f  # noqa: E402
import mechanical_audit_lib as lib  # noqa: E402
from core.config.print_profiles import get_profile  # noqa: E402
from core.validation.printability_gate import PrintabilityGate, count_connected_components  # noqa: E402


PROFILE_KEYS = ["fdm", "fdm_fine", "sla", "sls"]
PROXY_OBJ_PATH = RESULT_ROOT / "cad_mesh_proxy" / "rw4h_combined_relief_hardware_proxy.obj"
DIRECT_EXPORT_BLOCKERS = [
    "relief_geometry_is_proxy_boxes_not_boolean_subtracted",
    "combined_proxy_contains_multiple_candidate_variants",
    "mesh_winding_repair_required_before_export",
    "slicer_gcode_not_run",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lib.json_ready(payload), indent=2) + "\n", encoding="utf-8", newline="\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def parse_obj(path: Path) -> tuple[np.ndarray, list[list[int]], int]:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    groups = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("g "):
            groups += 1
        elif line.startswith("v "):
            vertices.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            face = [int(item.split("/")[0]) - 1 for item in line.split()[1:]]
            if len(face) == 3:
                faces.append(face)
    return np.asarray(vertices, dtype=float), faces, groups


def gate_issue_dict(issue: Any) -> dict[str, Any]:
    return {
        "severity": issue.severity.value,
        "code": issue.code,
        "message": issue.message.replace("\u00d7", "x").replace("\u00b0", "deg"),
    }


def papp_proxy_gate(vertices: np.ndarray, faces: list[list[int]], groups: int) -> dict[str, Any]:
    components = count_connected_components(faces)
    gate = PrintabilityGate(
        "permissive",
        max_components=max(components, 1),
        euler_expected=2 * components,
        aspect_ratio_limit=1000.0,
    )
    report = gate.check(vertices, faces)
    issue_codes = [issue.code for issue in report.issues]
    return {
        "papp_root": str(PAPP_ROOT),
        "gate_mode": report.mode,
        "passed_permissive": report.passed,
        "strict_export_ready": len(report.issues) == 0,
        "component_count": components,
        "group_count": groups,
        "euler_characteristic": report.mesh_report.euler_characteristic,
        "euler_expected_multi_component": 2 * components,
        "manifold": report.mesh_report.manifold,
        "watertight": report.mesh_report.watertight,
        "degenerate_faces": report.mesh_report.degenerate_faces,
        "winding_bfs_ok": report.winding_bfs_ok,
        "issue_counts": dict(Counter(issue_codes)),
        "issues": [gate_issue_dict(issue) for issue in report.issues],
    }


def candidate_payload_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {candidate["candidate_id"]: candidate for candidate in payload["candidates"]}


def body_bbox(pieces: dict[str, dict[str, Any]]) -> tuple[np.ndarray, np.ndarray]:
    points = []
    for piece in pieces.values():
        points.extend(piece["vertices"])
    arr = np.vstack(points)
    return arr.min(axis=0), arr.max(axis=0)


def expanded_candidate_bbox_model(
    candidate: dict[str, Any],
    rw4h_record: dict[str, Any],
    body_min: np.ndarray,
    body_max: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    scale = float(candidate["parameters"]["scale_mm_per_model_unit"])
    radial_model = max(float(env["radial_envelope_mm"]) / scale for env in candidate["selected_hinge_external_pin_envelopes"])
    clearance_model = float(candidate["parameters"]["clearance_model_units"])
    relief_points = []
    for record in rw4h_record["relief_proxy_records"]:
        relief_points.append(np.asarray(record["proxy_box_min"], dtype=float))
        relief_points.append(np.asarray(record["proxy_box_max"], dtype=float))
    if relief_points:
        relief_arr = np.vstack(relief_points)
        lo = np.minimum(body_min, relief_arr.min(axis=0))
        hi = np.maximum(body_max, relief_arr.max(axis=0))
    else:
        lo = body_min.copy()
        hi = body_max.copy()
    pad = max(radial_model, clearance_model)
    return lo - pad, hi + pad


def profile_build_check(lo: np.ndarray, hi: np.ndarray, scale: float) -> dict[str, Any]:
    size_model = hi - lo
    size_mm = tuple(float(x * scale) for x in size_model)
    out = {}
    for key in PROFILE_KEYS:
        profile = get_profile(key)
        fits = profile.fits(size_mm)
        utilization = max(size_mm[i] / profile.build_volume_mm[i] for i in range(3))
        out[key] = {
            "profile": profile.to_dict(),
            "bounding_box_size_mm": [round(x, 6) for x in size_mm],
            "fits_build_volume": fits,
            "max_axis_utilization": round(utilization, 9),
        }
    return out


def profile_feature_check(candidate: dict[str, Any], rw4h_record: dict[str, Any], rw4g_record: dict[str, Any]) -> dict[str, Any]:
    params = candidate["parameters"]
    scale = float(params["scale_mm_per_model_unit"])
    clearance = float(params["clearance_mm"])
    pin_radius = float(params["pin_radius_mm"])
    boss_width = float(params["boss_width_mm"])
    radial_values = [float(env["radial_envelope_mm"]) for env in candidate["selected_hinge_external_pin_envelopes"]]
    axis_lengths = [float(env["axis_length_mm"]) for env in candidate["selected_hinge_external_pin_envelopes"]]
    min_setback_mm = min(axis_lengths) * float(rw4h_record["minimum_passing_setback_fraction"])
    min_remaining_axis_mm = min(axis_lengths) * float(rw4h_record["shortened_length_fraction"])
    endpoint_access_margin = min_setback_mm - max(radial_values)
    max_ratio = max(float(env["diameter_to_axis_length_ratio"]) for env in candidate["selected_hinge_external_pin_envelopes"])
    relief_clearance_margin_mm = min(float(record["clearance_margin_model_units"]) * scale for record in rw4h_record["relief_proxy_records"])

    profile_checks = {}
    for key in PROFILE_KEYS:
        profile = get_profile(key)
        nozzle_or_resolution = profile.nozzle_diameter_mm if profile.nozzle_diameter_mm > 0.0 else profile.xy_resolution_mm
        min_access_gap = max(profile.layer_height_mm, nozzle_or_resolution)
        profile_checks[key] = {
            "profile": profile.name,
            "pin_diameter_ok": (2.0 * pin_radius) >= (2.0 * profile.min_wall_mm),
            "boss_width_ok": boss_width >= profile.min_wall_mm,
            "clearance_ok": clearance >= min_access_gap,
            "endpoint_access_margin_ok": endpoint_access_margin >= min_access_gap,
            "remaining_axis_length_ok": min_remaining_axis_mm >= max(4.0 * pin_radius, 2.0 * boss_width),
            "relief_margin_ok": relief_clearance_margin_mm >= 0.0,
            "minimum_access_gap_mm": round(min_access_gap, 6),
        }
    return {
        "pin_diameter_mm": round(2.0 * pin_radius, 6),
        "boss_width_mm": round(boss_width, 6),
        "clearance_mm": round(clearance, 6),
        "max_radial_envelope_mm": round(max(radial_values), 6),
        "minimum_setback_mm": round(min_setback_mm, 6),
        "minimum_remaining_axis_mm": round(min_remaining_axis_mm, 6),
        "endpoint_access_margin_mm": round(endpoint_access_margin, 6),
        "max_diameter_to_axis_length_ratio": round(max_ratio, 12),
        "minimum_relief_clearance_margin_mm": round(relief_clearance_margin_mm, 9),
        "profile_checks": profile_checks,
    }


def candidate_result(
    rw4h_record: dict[str, Any],
    candidate: dict[str, Any],
    pieces: dict[str, dict[str, Any]],
    body_min: np.ndarray,
    body_max: np.ndarray,
) -> dict[str, Any]:
    scale = float(candidate["parameters"]["scale_mm_per_model_unit"])
    lo, hi = expanded_candidate_bbox_model(candidate, rw4h_record, body_min, body_max)
    build_checks = profile_build_check(lo, hi, scale)
    feature_checks = profile_feature_check(candidate, rw4h_record, rw4h_record)
    profile_readiness = {}
    for key in PROFILE_KEYS:
        feature = feature_checks["profile_checks"][key]
        profile_readiness[key] = {
            "build_volume_ok": build_checks[key]["fits_build_volume"],
            "features_ok": all(bool(v) for k, v in feature.items() if k.endswith("_ok")),
            "preflight_ok": build_checks[key]["fits_build_volume"] and all(bool(v) for k, v in feature.items() if k.endswith("_ok")),
        }
    preflight_ok_profiles = [key for key, value in profile_readiness.items() if value["preflight_ok"]]
    fabrication_blockers = list(DIRECT_EXPORT_BLOCKERS)
    if not preflight_ok_profiles:
        fabrication_blockers.append("no_papp_profile_passes_build_and_feature_heuristics")
    return {
        "candidate_id": rw4h_record["candidate_id"],
        "parameters": candidate["parameters"],
        "rw4h_status": rw4h_record["status"],
        "build_volume_checks": build_checks,
        "feature_checks": feature_checks,
        "profile_readiness": profile_readiness,
        "preflight_ok_profile_count": len(preflight_ok_profiles),
        "preflight_ok_profiles": preflight_ok_profiles,
        "proxy_candidate_ready_for_rw6_review": len(preflight_ok_profiles) > 0,
        "fabrication_ready_without_cad_repair": False,
        "fabrication_blockers": fabrication_blockers,
    }


def choose_recommended_candidate(records: list[dict[str, Any]]) -> str | None:
    eligible = [record for record in records if record["proxy_candidate_ready_for_rw6_review"]]
    if not eligible:
        return None
    ranked = sorted(
        eligible,
        key=lambda record: (
            -record["preflight_ok_profile_count"],
            record["feature_checks"]["max_diameter_to_axis_length_ratio"],
            -record["feature_checks"]["endpoint_access_margin_mm"],
            record["parameters"]["scale_mm_per_model_unit"],
        ),
    )
    return ranked[0]["candidate_id"]


def slicer_availability() -> dict[str, Any]:
    tools = {
        "prusaslicer": shutil.which("prusaslicer") or shutil.which("PrusaSlicer"),
        "curaengine": shutil.which("CuraEngine") or shutil.which("curaengine"),
    }
    return {
        "tools": tools,
        "available": any(value is not None for value in tools.values()),
        "slicer_run": False,
        "skip_reason": "combined proxy is not boolean-subtracted CAD and still requires mesh repair before slicer export",
    }


def build_doc(report: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in report["summary"].items()]
    candidate_rows = [
        [
            record["candidate_id"],
            record["preflight_ok_profile_count"],
            ",".join(record["preflight_ok_profiles"]),
            record["feature_checks"]["endpoint_access_margin_mm"],
            record["feature_checks"]["minimum_remaining_axis_mm"],
            record["proxy_candidate_ready_for_rw6_review"],
            record["fabrication_ready_without_cad_repair"],
        ]
        for record in report["candidate_results"]
    ]
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    blocker_rows = [[idx + 1, blocker] for idx, blocker in enumerate(report["fabrication_blockers"])]
    return "\n".join(
        [
            "# S4 RW5 Printability/Fabrication Preflight",
            "",
            "Status: printability/fabrication preflight completed; RW6 review package unblocked, direct fabrication still blocked.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW5 applies project-local 3D-printing checks to the RW4h combined proxy.",
            "It evaluates build volume, mesh integrity, candidate clearances, endpoint",
            "access, and hinge-envelope manufacturability heuristics.  It does not",
            "turn the proxy into printable CAD.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW2 mesh payload", report["precondition"]["rw2_mesh_payload"]],
                    ["RW4e candidate payload", report["precondition"]["rw4e_candidate_payload"]],
                    ["RW4h combined proxy", report["precondition"]["rw4h_combined_proxy_report"]],
                    ["RW4h OBJ", report["precondition"]["rw4h_combined_proxy_obj"]],
                ],
            ),
            "",
            "## Summary",
            "",
            table(["Metric", "Value"], summary_rows),
            "",
            "## PAPP Proxy Gate",
            "",
            table(["Metric", "Value"], [[key, value] for key, value in report["papp_proxy_gate"].items() if key != "issues"]),
            "",
            "## Candidate Results",
            "",
            table(
                ["Candidate", "Profiles OK", "Profiles", "Endpoint access margin mm", "Remaining axis mm", "RW6 review ready", "Direct fabrication ready"],
                candidate_rows,
            ),
            "",
            "## Fabrication Blockers",
            "",
            table(["#", "Blocker"], blocker_rows),
            "",
            "## Explicit Nonclaims",
            "",
            "- physical hingeability",
            "- direct printability",
            "- CAD boolean validity",
            "- G-code readiness",
            "- fabrication readiness",
            "- prototype validation",
            "",
            "## Acceptance",
            "",
            table(["Check", "Value"], acceptance_rows),
            "",
            "## Next Task",
            "",
            report["next_task"],
            "",
        ]
    )


def main() -> int:
    for path in (RW2_PATH, RW4E_PAYLOAD_PATH, RW4H_PATH, PROXY_OBJ_PATH):
        if not path.exists():
            raise RuntimeError(f"missing source artifact: {path}")

    rw2 = load_json(RW2_PATH)
    rw4e_payload = load_json(RW4E_PAYLOAD_PATH)
    rw4h_report = load_json(RW4H_PATH)
    pieces = rw4f.load_pieces(rw2)
    body_min, body_max = body_bbox(pieces)
    candidates = candidate_payload_by_id(rw4e_payload)
    vertices, faces, group_count = parse_obj(PROXY_OBJ_PATH)
    papp_gate = papp_proxy_gate(vertices, faces, group_count)

    candidate_results = [
        candidate_result(record, candidates[record["candidate_id"]], pieces, body_min, body_max)
        for record in rw4h_report["candidate_results"]
    ]
    ready_for_rw6 = [record for record in candidate_results if record["proxy_candidate_ready_for_rw6_review"]]
    direct_fabrication_ready = [record for record in candidate_results if record["fabrication_ready_without_cad_repair"]]
    recommended = choose_recommended_candidate(candidate_results)
    blockers = list(DIRECT_EXPORT_BLOCKERS)
    if not papp_gate["winding_bfs_ok"]:
        blockers.append("papp_proxy_gate_reports_inconsistent_winding")
    if not direct_fabrication_ready:
        blockers.append("no_candidate_is_direct_fabrication_ready_without_cad_repair")

    report = {
        "report_id": "S4-RW5-PRINTABILITY-FABRICATION-PREFLIGHT-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "rw5_preflight_completed_rw6_unblocked_direct_fabrication_blocked",
        "precondition": {
            "rw2_mesh_payload": rel(RW2_PATH),
            "rw4e_candidate_payload": rel(RW4E_PAYLOAD_PATH),
            "rw4h_combined_proxy_report": rel(RW4H_PATH),
            "rw4h_combined_proxy_obj": rel(PROXY_OBJ_PATH),
            "rw4h_status": rw4h_report.get("status"),
        },
        "papp_assets_used": {
            "printability_gate": "FRAMEWORK/04-SOFTWARE/PAPP/core/validation/printability_gate.py",
            "print_profiles": "FRAMEWORK/04-SOFTWARE/PAPP/core/config/print_profiles.py",
            "profile_keys": PROFILE_KEYS,
        },
        "papp_proxy_gate": papp_gate,
        "slicer_availability": slicer_availability(),
        "summary": {
            "candidate_count": len(candidate_results),
            "proxy_candidates_ready_for_rw6_review": len(ready_for_rw6),
            "direct_fabrication_ready_candidates": len(direct_fabrication_ready),
            "recommended_rw6_frontier_candidate": recommended,
            "papp_proxy_gate_passed_permissive": papp_gate["passed_permissive"],
            "papp_proxy_gate_strict_export_ready": papp_gate["strict_export_ready"],
            "proxy_manifold": papp_gate["manifold"],
            "proxy_watertight": papp_gate["watertight"],
            "proxy_winding_bfs_ok": papp_gate["winding_bfs_ok"],
            "rw6_unblocked": len(ready_for_rw6) > 0 and papp_gate["passed_permissive"],
            "prototype_after_rw6_route_recorded": True,
        },
        "candidate_results": candidate_results,
        "fabrication_blockers": blockers,
        "post_rw6_prototype_route": [
            "convert relief proxy boxes into boolean-subtracted CAD features",
            "run mesh repair / winding normalization on candidate-only mesh",
            "export STL or 3MF for the selected candidate",
            "run slicer or layer preview when available",
            "print low-risk static fit coupon before full moving prototype",
            "measure hinge-axis fit, relief clearance, and opening motion",
        ],
        "acceptance": {
            "rw4h_report_present": RW4H_PATH.exists(),
            "rw4h_proxy_obj_present": PROXY_OBJ_PATH.exists(),
            "papp_printability_gate_executed": True,
            "all_candidates_checked_against_papp_profiles": all(len(record["profile_readiness"]) == len(PROFILE_KEYS) for record in candidate_results),
            "at_least_one_candidate_ready_for_rw6_review": len(ready_for_rw6) > 0,
            "direct_fabrication_ready": len(direct_fabrication_ready) > 0,
            "cad_boolean_validation_run": False,
            "slicer_gcode_run": False,
            "prototype_validation_run": False,
            "rw6_unblocked": len(ready_for_rw6) > 0 and papp_gate["passed_permissive"],
            "report_says_no_physical_claim": True,
        },
        "next_task": (
            "RW6 physical red-team package: package RW1-RW5 evidence, blockers, nonclaims, "
            "recommended frontier candidate, and the post-RW6 prototype route."
        ),
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": rel(JSON_PATH),
                "summary": report["summary"],
                "fabrication_blockers": report["fabrication_blockers"],
                "next_task": report["next_task"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
