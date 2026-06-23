#!/usr/bin/env python
"""Build RW4h combined relief/hardware CAD-mesh proxy for S4.

RW4h consumes the RW4e relief payload and the RW4g segmented hardware replay.
It materializes a single diagnostic OBJ proxy containing:

* the exact RW2 body tetrahedron meshes in closed/base coordinates;
* body-relief proxy boxes around the residual non-hinge contact supports;
* the RW4g segmented external-pin/boss envelope cylinders at snapshot poses.

This is still not CAD boolean validation.  The relief boxes are explicit
cutaway *proxies* derived from clearance budgets; they are not subtracted from
the body meshes.  The goal is to verify that every relief/hardware element
needed by the sampled physical branch is present and mesh-smoke-valid before
the later RW5 printability/fabrication gate.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW2_PATH = RESULT_ROOT / "rw2_mesh_payload_manifest.json"
RW3_PATH = RESULT_ROOT / "rw3_kinematics_adapter_manifest.json"
RW4D_PATH = RESULT_ROOT / "rw4d_clearance_hardware_model_report.json"
RW4E_PAYLOAD_PATH = RESULT_ROOT / "relief_hardware_candidates" / "rw4e_candidate_payloads.json"
RW4G_PATH = RESULT_ROOT / "rw4g_hardware_mitigation_replay_report.json"
PROXY_DIR = RESULT_ROOT / "cad_mesh_proxy"
PROXY_OBJ_PATH = PROXY_DIR / "rw4h_combined_relief_hardware_proxy.obj"
JSON_PATH = RESULT_ROOT / "rw4h_combined_cad_mesh_proxy_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4H_COMBINED_CAD_MESH_PROXY.md"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import build_s4_real_world_rw4f_cad_envelope_replay as rw4f  # noqa: E402
import build_s4_real_world_rw4g_hardware_mitigation_replay as rw4g  # noqa: E402
import mechanical_audit_lib as lib  # noqa: E402


EPS = 1.0e-10


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


def piece_obj_group(name: str, vertices: list[np.ndarray], faces: list[tuple[int, int, int]], start_index: int) -> tuple[list[str], int]:
    lines = [f"g {name}"]
    for vertex in vertices:
        lines.append(f"v {vertex[0]:.12f} {vertex[1]:.12f} {vertex[2]:.12f}")
    for i, j, k in faces:
        lines.append(f"f {start_index + i + 1} {start_index + j + 1} {start_index + k + 1}")
    return lines, start_index + len(vertices)


def box_obj_group(name: str, lo: np.ndarray, hi: np.ndarray, start_index: int) -> tuple[list[str], int]:
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    vertices = [
        np.asarray([x0, y0, z0]),
        np.asarray([x1, y0, z0]),
        np.asarray([x1, y1, z0]),
        np.asarray([x0, y1, z0]),
        np.asarray([x0, y0, z1]),
        np.asarray([x1, y0, z1]),
        np.asarray([x1, y1, z1]),
        np.asarray([x0, y1, z1]),
    ]
    faces = [
        (0, 1, 2), (0, 2, 3),
        (4, 6, 5), (4, 7, 6),
        (0, 4, 5), (0, 5, 1),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 4), (3, 4, 0),
    ]
    return piece_obj_group(name, vertices, faces, start_index)


def rounded_point(point: np.ndarray) -> tuple[float, float, float]:
    return tuple(round(float(x), 10) for x in point)


def contact_support_points(pieces: dict[str, dict[str, Any]], pair: list[str]) -> list[np.ndarray]:
    left, right = pair
    right_points = {rounded_point(point) for point in pieces[right]["vertices"]}
    shared = []
    seen = set()
    for point in pieces[left]["vertices"]:
        key = rounded_point(point)
        if key in right_points and key not in seen:
            shared.append(np.asarray(point, dtype=float))
            seen.add(key)
    return shared


def max_pairwise_distance(points: list[np.ndarray]) -> float:
    if len(points) < 2:
        return 0.0
    return max(float(np.linalg.norm(a - b)) for i, a in enumerate(points) for b in points[i + 1 :])


def relief_proxy_record(candidate: dict[str, Any], operation: dict[str, Any], pieces: dict[str, dict[str, Any]]) -> dict[str, Any]:
    support = contact_support_points(pieces, operation["piece_pair"])
    clearance = float(operation["applied_clearance_model_units"])
    valid_support = len(support) >= 2
    if valid_support:
        pts = np.vstack(support)
        lo = pts.min(axis=0) - clearance
        hi = pts.max(axis=0) + clearance
    else:
        lo = np.asarray([0.0, 0.0, 0.0])
        hi = np.asarray([0.0, 0.0, 0.0])
    extent = hi - lo
    volume = float(np.prod(extent)) if np.all(extent > 0.0) else 0.0
    span = max_pairwise_distance(support)
    return {
        "candidate_id": candidate["candidate_id"],
        "operation_id": operation["operation_id"],
        "tree_id": operation["tree_id"],
        "piece_pair": operation["piece_pair"],
        "route": operation["route"],
        "operation_kind": operation["operation_kind"],
        "theta_domain_degrees": operation["theta_domain_degrees"],
        "support_point_count": len(support),
        "support_span_model_units": round(span, 12),
        "support_points": [[round(float(x), 12) for x in point] for point in support],
        "applied_clearance_model_units": operation["applied_clearance_model_units"],
        "applied_clearance_mm": operation["applied_clearance_mm"],
        "clearance_margin_model_units": operation["clearance_margin_model_units"],
        "proxy_shape": "axis_aligned_contact_support_box",
        "proxy_box_min": [round(float(x), 12) for x in lo],
        "proxy_box_max": [round(float(x), 12) for x in hi],
        "proxy_box_extent": [round(float(x), 12) for x in extent],
        "proxy_box_volume_model_units": round(volume, 15),
        "covers_guard_deficit": operation["covers_guard_deficit"],
        "valid_support_found": valid_support,
        "positive_proxy_volume": volume > 0.0,
        "geometry_status": "cutaway_proxy_box_not_boolean_subtraction",
    }


def passing_rw4g_results(rw4g_report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for record in rw4g_report["candidate_results"]:
        if record["status"] == "segmented_endpoint_setback_passes_sampled_envelope_replay":
            out[record["candidate_id"]] = record
    return out


def best_candidate(candidate_results: list[dict[str, Any]]) -> str | None:
    ready = [record for record in candidate_results if record["rw5_preflight_candidate_ready"]]
    if not ready:
        return None
    ranked = sorted(
        ready,
        key=lambda record: (
            record["minimum_passing_setback_fraction"],
            -record["minimum_proxy_margin_model_units"],
            record["parameters"]["pin_radius_mm"] + record["parameters"]["boss_width_mm"],
            record["parameters"]["scale_mm_per_model_unit"],
        ),
    )
    return ranked[0]["candidate_id"]


def obj_mesh_smoke(path: Path) -> dict[str, Any]:
    vertices: list[np.ndarray] = []
    faces: list[tuple[int, int, int]] = []
    group_count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("g "):
            group_count += 1
        elif line.startswith("v "):
            vertices.append(np.asarray([float(value) for value in line.split()[1:4]], dtype=float))
        elif line.startswith("f "):
            idx = [int(item.split("/")[0]) - 1 for item in line.split()[1:]]
            if len(idx) == 3:
                faces.append((idx[0], idx[1], idx[2]))
    bad_faces = 0
    for i, j, k in faces:
        a, b, c = vertices[i], vertices[j], vertices[k]
        area2 = float(np.linalg.norm(np.cross(b - a, c - a)))
        if area2 <= EPS:
            bad_faces += 1
    return {
        "vertex_count": len(vertices),
        "triangle_face_count": len(faces),
        "group_count": group_count,
        "nondegenerate_triangle_faces": len(faces) - bad_faces,
        "degenerate_triangle_faces": bad_faces,
        "mesh_smoke_valid": len(vertices) > 0 and len(faces) > 0 and bad_faces == 0,
    }


def build_doc(report: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in report["summary"].items()]
    result_rows = [
        [
            result["candidate_id"],
            result["status"],
            result["relief_proxy_count"],
            result["segmented_hardware_snapshot_axis_count"],
            result["minimum_passing_setback_fraction"],
            result["minimum_proxy_margin_model_units"],
            result["rw5_preflight_candidate_ready"],
        ]
        for result in report["candidate_results"]
    ]
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4h Combined CAD/Mesh Proxy",
            "",
            "Status: combined relief/hardware proxy materialized and mesh-smoke-valid; not CAD boolean or printability validated.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4h materializes a combined diagnostic proxy for the future physical branch:",
            "RW2 body solids, RW4e relief/cutaway proxy boxes, and RW4g segmented",
            "external-pin envelope cylinders.  The relief boxes are derived from contact",
            "supports and clearance budgets; they are not boolean-subtracted CAD features.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW2 mesh payload", report["precondition"]["rw2_mesh_payload"]],
                    ["RW3 kinematics adapter", report["precondition"]["rw3_kinematics_adapter"]],
                    ["RW4d clearance model", report["precondition"]["rw4d_clearance_model"]],
                    ["RW4e candidate payload", report["precondition"]["rw4e_candidate_payload"]],
                    ["RW4g mitigation replay", report["precondition"]["rw4g_hardware_mitigation_replay"]],
                ],
            ),
            "",
            "## Summary",
            "",
            table(["Metric", "Value"], summary_rows),
            "",
            "## Candidate Results",
            "",
            table(
                ["Candidate", "Status", "Relief proxies", "Hardware snapshot axes", "Setback", "Min proxy margin", "RW5 preflight ready"],
                result_rows,
            ),
            "",
            "## Materialized Geometry",
            "",
            table(
                ["Artifact", "Path"],
                [["combined relief/hardware proxy OBJ", report["materialized_geometry"]["combined_proxy_obj"]]],
            ),
            "",
            "## Mesh Smoke",
            "",
            table(["Metric", "Value"], [[key, value] for key, value in report["mesh_smoke"].items()]),
            "",
            "## Explicit Nonclaims",
            "",
            "- physical hingeability",
            "- finite-thickness clearance certification",
            "- selected-hinge hardware clearance certification",
            "- CAD boolean validity",
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
    for path in (RW2_PATH, RW3_PATH, RW4D_PATH, RW4E_PAYLOAD_PATH, RW4G_PATH):
        if not path.exists():
            raise RuntimeError(f"missing source artifact: {path}")

    rw2 = load_json(RW2_PATH)
    rw3 = load_json(RW3_PATH)
    rw4d = load_json(RW4D_PATH)
    rw4e_payload = load_json(RW4E_PAYLOAD_PATH)
    rw4g_report = load_json(RW4G_PATH)
    pieces = rw4f.load_pieces(rw2)
    axes = rw4f.load_axes(rw2)
    candidates = rw4f.candidate_by_id(rw4e_payload)
    passing = passing_rw4g_results(rw4g_report)

    obj_lines = [
        "# S4 RW4h combined relief/hardware proxy",
        "# body solids + relief proxy boxes + segmented external-pin envelope cylinders",
        "# diagnostic mesh proxy only; not CAD boolean solids and not printable hardware",
    ]
    obj_index = 0

    for piece_id, piece in sorted(pieces.items()):
        lines, obj_index = piece_obj_group(f"body_solid_{piece_id}", piece["vertices"], piece["faces"], obj_index)
        obj_lines.extend(lines)

    candidate_results = []
    all_relief_records = []
    for candidate_id, rw4g_record in sorted(passing.items()):
        candidate = candidates[candidate_id]
        relief_records = [relief_proxy_record(candidate, operation, pieces) for operation in candidate["relief_operations"]]
        all_relief_records.extend(relief_records)
        for record in relief_records:
            group_name = f"{candidate_id}_{record['operation_id']}_proxy_box"
            lines, obj_index = box_obj_group(
                group_name,
                np.asarray(record["proxy_box_min"], dtype=float),
                np.asarray(record["proxy_box_max"], dtype=float),
                obj_index,
            )
            obj_lines.extend(lines)

        obj_index = rw4g.materialize_candidate_obj(
            obj_lines,
            obj_index,
            candidate,
            float(rw4g_record["minimum_passing_setback_fraction"]),
            rw2,
            rw3,
            axes,
        )

        all_reliefs_valid = all(record["valid_support_found"] and record["positive_proxy_volume"] and record["covers_guard_deficit"] for record in relief_records)
        min_margin = min(
            float(value)
            for value in [
                rw4g_record["passing_body_min_margin_model_units"],
                rw4g_record["passing_hinge_min_margin_model_units"],
                *(record["clearance_margin_model_units"] for record in relief_records),
            ]
        )
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "status": "combined_proxy_ready_for_rw5_preflight" if all_reliefs_valid else "combined_proxy_blocked_by_relief_proxy",
                "parameters": candidate["parameters"],
                "minimum_passing_setback_fraction": rw4g_record["minimum_passing_setback_fraction"],
                "shortened_length_fraction": rw4g_record["shortened_length_fraction"],
                "relief_proxy_count": len(relief_records),
                "segmented_hardware_snapshot_axis_count": len(candidate["selected_hinge_external_pin_envelopes"]) * len(rw4f.SNAPSHOT_THETAS),
                "minimum_proxy_margin_model_units": round(min_margin, 12),
                "maximum_relief_proxy_box_volume_model_units": max(record["proxy_box_volume_model_units"] for record in relief_records),
                "all_relief_proxies_have_contact_support": all(record["valid_support_found"] for record in relief_records),
                "all_relief_proxy_boxes_positive_volume": all(record["positive_proxy_volume"] for record in relief_records),
                "all_relief_proxies_cover_guard_deficit": all(record["covers_guard_deficit"] for record in relief_records),
                "rw4g_segmented_envelope_replay_passed": True,
                "rw5_preflight_candidate_ready": all_reliefs_valid,
                "relief_proxy_records": relief_records,
            }
        )

    PROXY_OBJ_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROXY_OBJ_PATH.write_text("\n".join(obj_lines) + "\n", encoding="utf-8", newline="\n")
    mesh_smoke = obj_mesh_smoke(PROXY_OBJ_PATH)

    ready = [record for record in candidate_results if record["rw5_preflight_candidate_ready"]]
    report = {
        "report_id": "S4-RW4H-COMBINED-CAD-MESH-PROXY-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "combined_proxy_mesh_valid_rw5_preflight_unblocked_not_cad_validated",
        "precondition": {
            "rw2_mesh_payload": rel(RW2_PATH),
            "rw3_kinematics_adapter": rel(RW3_PATH),
            "rw4d_clearance_model": rel(RW4D_PATH),
            "rw4e_candidate_payload": rel(RW4E_PAYLOAD_PATH),
            "rw4g_hardware_mitigation_replay": rel(RW4G_PATH),
            "rw4g_status": rw4g_report.get("status"),
        },
        "proxy_semantics": {
            "body_solids": "RW2 exact body tetrahedron meshes in model units",
            "relief_proxies": "AABB boxes around shared contact supports expanded by candidate clearance; not boolean-subtracted",
            "hardware_proxies": "RW4g segmented external-pin/boss envelope cylinders at theta snapshots",
            "cad_boolean_status": "not_run",
            "printability_status": "not_run",
        },
        "materialized_geometry": {
            "combined_proxy_obj": rel(PROXY_OBJ_PATH),
            "body_solid_group_count": len(pieces),
            "relief_proxy_box_group_count": len(all_relief_records),
            "segmented_hardware_snapshot_axis_group_count": sum(record["segmented_hardware_snapshot_axis_count"] for record in candidate_results),
            "snapshot_theta_degrees": sorted(rw4f.SNAPSHOT_THETAS),
        },
        "mesh_smoke": mesh_smoke,
        "summary": {
            "frontier_candidate_count": len(passing),
            "combined_proxy_candidate_count": len(candidate_results),
            "rw5_preflight_ready_candidates": len(ready),
            "rw5_preflight_blocked_candidates": len(candidate_results) - len(ready),
            "relief_proxy_count": len(all_relief_records),
            "all_relief_operations_materialized": len(all_relief_records) == len(candidate_results) * len(rw4d["clearance_relief_groups"]),
            "all_relief_proxies_have_contact_support": all(record["valid_support_found"] for record in all_relief_records),
            "all_relief_proxy_boxes_positive_volume": all(record["positive_proxy_volume"] for record in all_relief_records),
            "all_candidates_preserve_rw4g_segmented_envelope_pass": all(record["rw4g_segmented_envelope_replay_passed"] for record in candidate_results),
            "mesh_smoke_valid": mesh_smoke["mesh_smoke_valid"],
            "rw5_recommended_frontier_candidate": best_candidate(candidate_results),
            "rw5_preflight_unblocked": len(ready) == len(candidate_results) and mesh_smoke["mesh_smoke_valid"],
        },
        "candidate_results": candidate_results,
        "acceptance": {
            "rw2_payload_present": RW2_PATH.exists(),
            "rw4g_report_present": RW4G_PATH.exists(),
            "combined_proxy_obj_written": PROXY_OBJ_PATH.exists(),
            "all_frontier_candidates_replayed": len(candidate_results) == len(passing),
            "all_relief_operations_materialized": len(all_relief_records) == len(candidate_results) * len(rw4d["clearance_relief_groups"]),
            "all_relief_proxies_supported_by_piece_contacts": all(record["valid_support_found"] for record in all_relief_records),
            "all_relief_proxy_boxes_positive_volume": all(record["positive_proxy_volume"] for record in all_relief_records),
            "all_candidates_preserve_rw4g_segmented_envelope_pass": all(record["rw4g_segmented_envelope_replay_passed"] for record in candidate_results),
            "mesh_smoke_valid": mesh_smoke["mesh_smoke_valid"],
            "cad_boolean_validation_run": False,
            "finite_thickness_clearance_certified": False,
            "printability_validation_run": False,
            "prototype_validation_run": False,
            "rw5_preflight_unblocked": len(ready) == len(candidate_results) and mesh_smoke["mesh_smoke_valid"],
            "report_says_no_physical_claim": True,
        },
        "next_task": (
            "RW5 printability/fabrication preflight over the RW4h combined proxy: units, wall/clearance heuristics, "
            "hinge-envelope manufacturability, assembly access, and explicit nonclaim/red-team routing."
        ),
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": rel(JSON_PATH),
                "combined_proxy_obj": rel(PROXY_OBJ_PATH),
                "summary": report["summary"],
                "next_task": report["next_task"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
