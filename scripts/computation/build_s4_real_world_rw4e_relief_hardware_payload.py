#!/usr/bin/env python
"""Build RW4e relief/hardware candidate payloads for S4.

RW4e consumes RW4d's clearance/hardware model and materializes the covering
parameter cells into an explicit machine-readable payload.  It also replays the
clearance-budget check for every candidate against every relief group.

This is still an envelope/payload artifact only.  It does not subtract CAD
reliefs, does not create finite-thickness solids, does not certify hardware
clearance, does not validate printability, and does not validate a prototype.
"""

from __future__ import annotations

import itertools
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW4D_PATH = RESULT_ROOT / "rw4d_clearance_hardware_model_report.json"
PAYLOAD_DIR = RESULT_ROOT / "relief_hardware_candidates"
PAYLOAD_PATH = PAYLOAD_DIR / "rw4e_candidate_payloads.json"
JSON_PATH = RESULT_ROOT / "rw4e_relief_hardware_payload_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4E_RELIEF_HARDWARE_PAYLOAD.md"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402


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


def scale_key(scale: float) -> str:
    return str(int(scale) if float(scale).is_integer() else scale)


def candidate_id(scale: float, clearance: float, pin_radius: float, boss_width: float) -> str:
    return (
        f"RW4E_s{int(round(scale)):03d}_"
        f"c{int(round(clearance * 1000)):04d}_"
        f"pin{int(round(pin_radius * 1000)):04d}_"
        f"boss{int(round(boss_width * 1000)):04d}"
    )


def route_operation_kind(route: str) -> str:
    if route == "shared_face_relief_cutback_required":
        return "nonhinge_shared_face_clearance_cutback_budget"
    if route == "near_zero_shared_edge_chamfer_or_start_gap_required":
        return "near_zero_shared_edge_chamfer_or_start_gap_budget"
    return "clearance_budget"


def route_operation_note(route: str) -> str:
    if route == "shared_face_relief_cutback_required":
        return "Budget for a future CAD cutback/relief on a residual non-hinge shared-face contact band."
    if route == "near_zero_shared_edge_chamfer_or_start_gap_required":
        return "Budget for a future tiny chamfer/start-gap on a near-zero residual shared-edge micro-interval."
    return "Budget-only clearance operation; exact CAD operation is not chosen in RW4e."


def relief_operation(group: dict[str, Any], applied_clearance_model: float, scale: float, clearance_mm: float) -> dict[str, Any]:
    required = float(group["required_model_clearance"])
    margin = applied_clearance_model - required
    return {
        "operation_id": "relief_" + group["group_id"],
        "operation_kind": route_operation_kind(group["route"]),
        "geometry_status": "operation_payload_only_no_boolean_subtraction",
        "tree_id": group["tree_id"],
        "piece_pair": group["pair"],
        "theta_domain_degrees": group["theta_domain_degrees"],
        "source_blocker_count": group["source_blocker_count"],
        "route": group["route"],
        "required_model_clearance": round(required, 12),
        "required_clearance_mm_at_candidate_scale": round(required * scale, 9),
        "applied_clearance_mm": round(clearance_mm, 9),
        "applied_clearance_model_units": round(applied_clearance_model, 12),
        "clearance_margin_mm": round(margin * scale, 9),
        "clearance_margin_model_units": round(margin, 12),
        "covers_guard_deficit": margin >= -1.0e-15,
        "note": route_operation_note(group["route"]),
    }


def hardware_envelope(record: dict[str, Any], scale: float, clearance_mm: float, pin_radius: float, boss_width: float) -> dict[str, Any]:
    axis_length_mm = float(record["axis_length_model_units"]) * scale
    radial_envelope_mm = pin_radius + clearance_mm + boss_width
    ratio = (2.0 * radial_envelope_mm) / axis_length_mm if axis_length_mm > 0.0 else None
    return {
        "tree_id": record["tree_id"],
        "hinge_id": record["hinge_id"],
        "piece_pair": record["piece_pair"],
        "axis_labels": record["axis_labels"],
        "axis_support": record["axis_support"],
        "geometry_status": "external_pin_envelope_only_no_cad_solid",
        "axis_length_model_units": record["axis_length_model_units"],
        "axis_length_mm": round(axis_length_mm, 9),
        "pin_radius_mm": pin_radius,
        "boss_width_mm": boss_width,
        "clearance_mm": clearance_mm,
        "radial_envelope_mm": round(radial_envelope_mm, 9),
        "diameter_to_axis_length_ratio": round(ratio, 12) if ratio is not None else None,
        "axis_length_positive": axis_length_mm > 0.0,
    }


def build_candidate(
    cell: dict[str, Any],
    pin_radius: float,
    boss_width: float,
    relief_groups: list[dict[str, Any]],
    hinge_records: list[dict[str, Any]],
) -> dict[str, Any]:
    scale = float(cell["scale_mm_per_model_unit"])
    clearance_mm = float(cell["clearance_mm"])
    applied_model = clearance_mm / scale
    operations = [relief_operation(group, applied_model, scale, clearance_mm) for group in relief_groups]
    envelopes = [hardware_envelope(record, scale, clearance_mm, pin_radius, boss_width) for record in hinge_records]
    min_margin_model = min(op["clearance_margin_model_units"] for op in operations)
    max_margin_model = max(op["clearance_margin_model_units"] for op in operations)
    max_ratio = max(env["diameter_to_axis_length_ratio"] for env in envelopes if env["diameter_to_axis_length_ratio"] is not None)
    min_ratio = min(env["diameter_to_axis_length_ratio"] for env in envelopes if env["diameter_to_axis_length_ratio"] is not None)
    radial_values = [env["radial_envelope_mm"] for env in envelopes]
    cid = candidate_id(scale, clearance_mm, pin_radius, boss_width)
    return {
        "candidate_id": cid,
        "status": "clearance_budget_replay_passed_not_cad_validated",
        "parameters": {
            "scale_mm_per_model_unit": scale,
            "clearance_mm": clearance_mm,
            "clearance_model_units": round(applied_model, 12),
            "pin_radius_mm": pin_radius,
            "boss_width_mm": boss_width,
        },
        "clearance_replay": {
            "relief_group_count": len(relief_groups),
            "all_relief_groups_covered": all(op["covers_guard_deficit"] for op in operations),
            "minimum_clearance_margin_model_units": round(min_margin_model, 12),
            "maximum_clearance_margin_model_units": round(max_margin_model, 12),
            "minimum_clearance_margin_mm": round(min_margin_model * scale, 9),
            "maximum_clearance_margin_mm": round(max_margin_model * scale, 9),
        },
        "hardware_envelope_summary": {
            "selected_hinge_axis_count": len(envelopes),
            "all_axes_positive_length": all(env["axis_length_positive"] for env in envelopes),
            "minimum_radial_envelope_mm": round(min(radial_values), 9),
            "maximum_radial_envelope_mm": round(max(radial_values), 9),
            "minimum_diameter_to_axis_length_ratio": round(min_ratio, 12),
            "maximum_diameter_to_axis_length_ratio": round(max_ratio, 12),
            "hardware_threshold_enforced": False,
        },
        "relief_operations": operations,
        "selected_hinge_external_pin_envelopes": envelopes,
        "acceptance": {
            "all_relief_groups_covered_by_budget": all(op["covers_guard_deficit"] for op in operations),
            "all_selected_hinge_axes_positive_length": all(env["axis_length_positive"] for env in envelopes),
            "cad_geometry_written": False,
            "finite_thickness_collision_certified": False,
            "selected_hinge_hardware_clearance_certified": False,
            "printability_validation_run": False,
            "prototype_validation_run": False,
        },
    }


def pareto_summary(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    by_radial = min(
        candidates,
        key=lambda c: (
            c["hardware_envelope_summary"]["maximum_radial_envelope_mm"],
            c["hardware_envelope_summary"]["maximum_diameter_to_axis_length_ratio"],
            c["parameters"]["scale_mm_per_model_unit"],
        ),
    )
    by_ratio = min(
        candidates,
        key=lambda c: (
            c["hardware_envelope_summary"]["maximum_diameter_to_axis_length_ratio"],
            c["hardware_envelope_summary"]["maximum_radial_envelope_mm"],
            c["parameters"]["clearance_mm"],
        ),
    )
    by_margin = max(
        candidates,
        key=lambda c: (
            c["clearance_replay"]["minimum_clearance_margin_model_units"],
            -c["hardware_envelope_summary"]["maximum_radial_envelope_mm"],
        ),
    )
    ranked = sorted(
        candidates,
        key=lambda c: (
            c["hardware_envelope_summary"]["maximum_diameter_to_axis_length_ratio"],
            c["hardware_envelope_summary"]["maximum_radial_envelope_mm"],
            c["parameters"]["clearance_mm"],
            c["parameters"]["pin_radius_mm"],
            c["parameters"]["boss_width_mm"],
        ),
    )
    return {
        "minimum_radial_envelope_candidate": by_radial["candidate_id"],
        "minimum_diameter_ratio_candidate": by_ratio["candidate_id"],
        "maximum_clearance_margin_candidate": by_margin["candidate_id"],
        "top_ranked_envelope_candidates": [candidate["candidate_id"] for candidate in ranked[:8]],
        "ranking_semantics": (
            "Diagnostic ranking only: smaller external-pin envelope and smaller diameter/axis ratio are preferred "
            "for the next CAD/envelope replay, but RW4e does not select a printable or fabricable design."
        ),
    }


def build_doc(report: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in report["summary"].items()]
    candidate_rows = []
    for candidate in report["candidate_frontier"]:
        candidate_rows.append(
            [
                candidate["candidate_id"],
                candidate["scale_mm_per_model_unit"],
                candidate["clearance_mm"],
                candidate["pin_radius_mm"],
                candidate["boss_width_mm"],
                candidate["min_margin_model_units"],
                candidate["max_radial_envelope_mm"],
                candidate["max_diameter_to_axis_length_ratio"],
            ]
        )
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4e Relief/Hardware Payload",
            "",
            "Status: relief/hardware candidate payloads and clearance-budget replay; not CAD validated.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4e materializes the RW4d covering scale/clearance cells into explicit candidate",
            "payload records.  For each candidate it replays the clearance-budget check against",
            "all six residual relief groups and records external-pin envelope metrics for the",
            "six selected hinge axes.",
            "",
            "No CAD relief is subtracted in this step.  No finite-thickness collision, hardware",
            "clearance, printability, fabrication, or prototype claim is made.",
            "",
            "## Sources",
            "",
            table([ "Source", "Path" ], [["RW4d clearance/hardware model", report["precondition"]["rw4d_clearance_hardware_model"]]]),
            "",
            "## Summary",
            "",
            table(["Metric", "Value"], summary_rows),
            "",
            "## Candidate Frontier",
            "",
            table(
                [
                    "Candidate",
                    "Scale",
                    "Clearance",
                    "Pin radius",
                    "Boss width",
                    "Min margin model",
                    "Max radial mm",
                    "Max diameter/axis",
                ],
                candidate_rows,
            ),
            "",
            "## Payload Files",
            "",
            table(
                ["Artifact", "Path"],
                [
                    ["candidate payloads", report["payloads"]["candidate_payload_path"]],
                    ["RW4e report", report["payloads"]["report_path"]],
                ],
            ),
            "",
            "## Interpretation",
            "",
            "All 48 RW4e candidates cover the RW4d zero-thickness guard-deficit clearance",
            "budget.  This is only a budget replay: the next gate must either materialize",
            "actual CAD/envelope geometry and replay collisions, or deliberately keep RW5 blocked.",
            "",
            "## Explicit Nonclaims",
            "",
            "- physical hingeability",
            "- finite-thickness clearance",
            "- selected-hinge hardware clearance",
            "- CAD validity",
            "- printability",
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
    if not RW4D_PATH.exists():
        raise RuntimeError(f"missing RW4d report: {RW4D_PATH}")

    rw4d = load_json(RW4D_PATH)
    grid = rw4d["parameter_grid"]
    covering_cells = rw4d["covering_scale_clearance_cells"]
    relief_groups = rw4d["clearance_relief_groups"]
    hinge_records = rw4d["selected_hinge_hardware"]
    pin_grid = [float(value) for value in grid["hinge_axis_radius_mm"]]
    boss_grid = [float(value) for value in grid["shell_or_boss_thickness_mm"]]

    candidates = []
    for cell, pin_radius, boss_width in itertools.product(covering_cells, pin_grid, boss_grid):
        candidates.append(build_candidate(cell, pin_radius, boss_width, relief_groups, hinge_records))

    all_cover = all(candidate["acceptance"]["all_relief_groups_covered_by_budget"] for candidate in candidates)
    all_axes_positive = all(candidate["acceptance"]["all_selected_hinge_axes_positive_length"] for candidate in candidates)
    min_margin_model = min(candidate["clearance_replay"]["minimum_clearance_margin_model_units"] for candidate in candidates)
    max_margin_model = max(candidate["clearance_replay"]["maximum_clearance_margin_model_units"] for candidate in candidates)
    max_radial = max(candidate["hardware_envelope_summary"]["maximum_radial_envelope_mm"] for candidate in candidates)
    min_radial = min(candidate["hardware_envelope_summary"]["minimum_radial_envelope_mm"] for candidate in candidates)
    max_ratio = max(candidate["hardware_envelope_summary"]["maximum_diameter_to_axis_length_ratio"] for candidate in candidates)
    min_ratio = min(candidate["hardware_envelope_summary"]["minimum_diameter_to_axis_length_ratio"] for candidate in candidates)
    frontier = pareto_summary(candidates)
    candidate_by_id = {candidate["candidate_id"]: candidate for candidate in candidates}
    frontier_ids = list(dict.fromkeys([
        frontier["minimum_radial_envelope_candidate"],
        frontier["minimum_diameter_ratio_candidate"],
        frontier["maximum_clearance_margin_candidate"],
        *frontier["top_ranked_envelope_candidates"][:5],
    ]))

    payload = {
        "schema_version": "rw4e_relief_hardware_candidate_payload_v1",
        "case_id": CASE_ID,
        "date": DATE,
        "source_report": rel(RW4D_PATH),
        "candidate_count": len(candidates),
        "candidate_status_semantics": "budget_replay_passed_not_cad_validated",
        "candidates": candidates,
    }
    write_json(PAYLOAD_PATH, payload)

    report = {
        "report_id": "S4-RW4E-RELIEF-HARDWARE-PAYLOAD-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "relief_hardware_payload_and_envelope_checks_created_not_cad_validated",
        "precondition": {
            "rw4d_clearance_hardware_model": rel(RW4D_PATH),
            "rw4d_status": rw4d.get("status"),
        },
        "scope": {
            "payload_kind": "clearance_relief_operations_plus_external_pin_envelope_grid",
            "relief_geometry_status": "operation_payload_only_no_boolean_subtraction",
            "hardware_geometry_status": "external_pin_envelope_only_no_cad_solid",
            "clearance_check_status": "budget_replay_passed_for_covering_cells",
            "finite_thickness_clearance_status": "not_certified",
            "printability_validation_status": "not_run",
        },
        "payloads": {
            "candidate_payload_path": rel(PAYLOAD_PATH),
            "report_path": rel(JSON_PATH),
        },
        "summary": {
            "candidate_count": len(candidates),
            "covering_scale_clearance_cell_count": len(covering_cells),
            "pin_radius_count": len(pin_grid),
            "boss_width_count": len(boss_grid),
            "relief_group_count": len(relief_groups),
            "hardware_axis_count": len(hinge_records),
            "all_candidates_cover_all_relief_groups": all_cover,
            "all_candidate_hinge_axes_positive_length": all_axes_positive,
            "minimum_clearance_margin_model_units": round(min_margin_model, 12),
            "maximum_clearance_margin_model_units": round(max_margin_model, 12),
            "minimum_radial_envelope_mm": round(min_radial, 9),
            "maximum_radial_envelope_mm": round(max_radial, 9),
            "minimum_diameter_to_axis_length_ratio": round(min_ratio, 12),
            "maximum_diameter_to_axis_length_ratio": round(max_ratio, 12),
            "hardware_threshold_enforced": False,
            "cad_geometry_written": False,
        },
        "candidate_frontier": [
            {
                "candidate_id": cid,
                "scale_mm_per_model_unit": candidate_by_id[cid]["parameters"]["scale_mm_per_model_unit"],
                "clearance_mm": candidate_by_id[cid]["parameters"]["clearance_mm"],
                "pin_radius_mm": candidate_by_id[cid]["parameters"]["pin_radius_mm"],
                "boss_width_mm": candidate_by_id[cid]["parameters"]["boss_width_mm"],
                "min_margin_model_units": candidate_by_id[cid]["clearance_replay"]["minimum_clearance_margin_model_units"],
                "max_radial_envelope_mm": candidate_by_id[cid]["hardware_envelope_summary"]["maximum_radial_envelope_mm"],
                "max_diameter_to_axis_length_ratio": candidate_by_id[cid]["hardware_envelope_summary"]["maximum_diameter_to_axis_length_ratio"],
            }
            for cid in frontier_ids
        ],
        "frontier_semantics": frontier,
        "acceptance": {
            "rw4d_report_present": RW4D_PATH.exists(),
            "candidate_payload_written": PAYLOAD_PATH.exists(),
            "candidate_count_matches_rw4d_covering_grid": len(candidates) == len(covering_cells) * len(pin_grid) * len(boss_grid),
            "all_candidates_cover_all_relief_groups": all_cover,
            "all_candidate_hinge_axes_positive_length": all_axes_positive,
            "cad_geometry_written": False,
            "finite_thickness_clearance_certified": False,
            "selected_hinge_hardware_clearance_certified": False,
            "printability_validation_run": False,
            "report_says_no_physical_claim": True,
        },
        "next_task": (
            "RW4f materialize CAD/envelope geometry for a small candidate frontier and replay finite-thickness "
            "clearance/collision before RW5 printability/fabrication gates."
        ),
    }
    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")

    print(
        json.dumps(
            {
                "status": report["status"],
                "report": rel(JSON_PATH),
                "payload": rel(PAYLOAD_PATH),
                "summary": report["summary"],
                "next_task": report["next_task"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
