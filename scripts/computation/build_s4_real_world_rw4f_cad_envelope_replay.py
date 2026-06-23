#!/usr/bin/env python
"""Build RW4f CAD/envelope replay for S4 frontier candidates.

RW4f consumes RW4e candidate payloads and materializes a small frontier of
external-pin envelope geometry as OBJ cylinders on the RW3 sample poses.  It
then runs sampled envelope intrusion checks:

* selected hinge envelope versus non-incident body pieces;
* selected hinge envelope versus other selected hinge envelopes.

This is an envelope replay, not a CAD boolean validation.  It does not subtract
body reliefs, does not create printable CAD, does not certify finite-thickness
clearance, and does not validate a prototype.
"""

from __future__ import annotations

import itertools
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
RW4E_REPORT_PATH = RESULT_ROOT / "rw4e_relief_hardware_payload_report.json"
RW4E_PAYLOAD_PATH = RESULT_ROOT / "relief_hardware_candidates" / "rw4e_candidate_payloads.json"
ENVELOPE_DIR = RESULT_ROOT / "cad_envelope_replay"
ENVELOPE_OBJ_PATH = ENVELOPE_DIR / "rw4f_frontier_external_pin_envelopes.obj"
JSON_PATH = RESULT_ROOT / "rw4f_cad_envelope_replay_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4F_CAD_ENVELOPE_REPLAY.md"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402


SNAPSHOT_THETAS = {0.0, 60.0, 120.0}
CYLINDER_SEGMENTS = 16
EPS = 1.0e-12


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


def transform_point(transform: dict[str, Any], point: np.ndarray) -> np.ndarray:
    rotation = np.asarray(transform["R"], dtype=float)
    translation = np.asarray(transform["t"], dtype=float)
    return rotation @ point + translation


def parse_obj_piece(path: Path) -> tuple[list[np.ndarray], list[tuple[int, int, int]]]:
    vertices: list[np.ndarray] = []
    faces: list[tuple[int, int, int]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            vertices.append(np.asarray([float(value) for value in line.split()[1:4]], dtype=float))
        elif line.startswith("f "):
            idx = [int(item.split("/")[0]) - 1 for item in line.split()[1:]]
            if len(idx) != 3:
                raise RuntimeError(f"non-triangle face in {path}: {line}")
            faces.append((idx[0], idx[1], idx[2]))
    return vertices, faces


def load_pieces(rw2: dict[str, Any]) -> dict[str, dict[str, Any]]:
    pieces = {}
    for piece in rw2["exports"]["piece_objs"]:
        vertices, faces = parse_obj_piece(ROOT / piece["path"])
        pieces[piece["piece_id"]] = {"vertices": vertices, "faces": faces}
    return pieces


def load_axes(rw2: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    axes = {}
    for tree in rw2["hinge_axis_payload"]["trees"]:
        for hinge in tree["hinges"]:
            axes[(tree["tree_id"], hinge["hinge_id"])] = hinge
    return axes


def point_segment_distance(point: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
    direction = b - a
    denom = float(direction @ direction)
    if denom <= EPS:
        return float(np.linalg.norm(point - a))
    t = float(((point - a) @ direction) / denom)
    t = min(1.0, max(0.0, t))
    closest = a + t * direction
    return float(np.linalg.norm(point - closest))


def segment_segment_distance(a0: np.ndarray, a1: np.ndarray, b0: np.ndarray, b1: np.ndarray) -> float:
    # Real-Time Collision Detection, closest points of two segments.
    u = a1 - a0
    v = b1 - b0
    w = a0 - b0
    a = float(u @ u)
    b = float(u @ v)
    c = float(v @ v)
    d = float(u @ w)
    e = float(v @ w)
    denom = a * c - b * b
    s_d = denom
    t_d = denom
    if denom < EPS:
        s_n = 0.0
        s_d = 1.0
        t_n = e
        t_d = c
    else:
        s_n = b * e - c * d
        t_n = a * e - b * d
        if s_n < 0.0:
            s_n = 0.0
            t_n = e
            t_d = c
        elif s_n > s_d:
            s_n = s_d
            t_n = e + b
            t_d = c
    if t_n < 0.0:
        t_n = 0.0
        if -d < 0.0:
            s_n = 0.0
        elif -d > a:
            s_n = s_d
        else:
            s_n = -d
            s_d = a
    elif t_n > t_d:
        t_n = t_d
        if -d + b < 0.0:
            s_n = 0.0
        elif -d + b > a:
            s_n = s_d
        else:
            s_n = -d + b
            s_d = a
    sc = 0.0 if abs(s_n) < EPS else s_n / s_d
    tc = 0.0 if abs(t_n) < EPS else t_n / t_d
    dp = w + sc * u - tc * v
    return float(np.linalg.norm(dp))


def point_triangle_distance(point: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> float:
    # Real-Time Collision Detection, closest point on triangle to point.
    ab = b - a
    ac = c - a
    ap = point - a
    d1 = float(ab @ ap)
    d2 = float(ac @ ap)
    if d1 <= 0.0 and d2 <= 0.0:
        return float(np.linalg.norm(point - a))

    bp = point - b
    d3 = float(ab @ bp)
    d4 = float(ac @ bp)
    if d3 >= 0.0 and d4 <= d3:
        return float(np.linalg.norm(point - b))

    vc = d1 * d4 - d3 * d2
    if vc <= 0.0 and d1 >= 0.0 and d3 <= 0.0:
        v = d1 / (d1 - d3)
        closest = a + v * ab
        return float(np.linalg.norm(point - closest))

    cp = point - c
    d5 = float(ab @ cp)
    d6 = float(ac @ cp)
    if d6 >= 0.0 and d5 <= d6:
        return float(np.linalg.norm(point - c))

    vb = d5 * d2 - d1 * d6
    if vb <= 0.0 and d2 >= 0.0 and d6 <= 0.0:
        w = d2 / (d2 - d6)
        closest = a + w * ac
        return float(np.linalg.norm(point - closest))

    va = d3 * d6 - d5 * d4
    if va <= 0.0 and (d4 - d3) >= 0.0 and (d5 - d6) >= 0.0:
        w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        closest = b + w * (c - b)
        return float(np.linalg.norm(point - closest))

    denom = 1.0 / (va + vb + vc)
    v = vb * denom
    w = vc * denom
    closest = a + ab * v + ac * w
    return float(np.linalg.norm(point - closest))


def segment_triangle_sampled_distance(a0: np.ndarray, a1: np.ndarray, t0: np.ndarray, t1: np.ndarray, t2: np.ndarray) -> float:
    # Conservative enough for diagnostics, but not an exact CAD predicate.
    candidates = [
        point_triangle_distance(a0, t0, t1, t2),
        point_triangle_distance(a1, t0, t1, t2),
        point_segment_distance(t0, a0, a1),
        point_segment_distance(t1, a0, a1),
        point_segment_distance(t2, a0, a1),
        segment_segment_distance(a0, a1, t0, t1),
        segment_segment_distance(a0, a1, t1, t2),
        segment_segment_distance(a0, a1, t2, t0),
    ]
    for fraction in (0.25, 0.5, 0.75):
        point = a0 + fraction * (a1 - a0)
        candidates.append(point_triangle_distance(point, t0, t1, t2))
    return min(candidates)


def segment_piece_surface_distance(a: np.ndarray, b: np.ndarray, vertices: list[np.ndarray], faces: list[tuple[int, int, int]]) -> float:
    return min(segment_triangle_sampled_distance(a, b, vertices[i], vertices[j], vertices[k]) for i, j, k in faces)


def cylinder_basis(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    axis = b - a
    norm = float(np.linalg.norm(axis))
    if norm <= EPS:
        raise RuntimeError("zero-length cylinder axis")
    w = axis / norm
    helper = np.asarray([1.0, 0.0, 0.0])
    if abs(float(w @ helper)) > 0.9:
        helper = np.asarray([0.0, 1.0, 0.0])
    u = np.cross(w, helper)
    u /= np.linalg.norm(u)
    v = np.cross(w, u)
    return u, v


def cylinder_obj_group(name: str, a: np.ndarray, b: np.ndarray, radius: float, start_index: int) -> tuple[list[str], int]:
    u, v = cylinder_basis(a, b)
    lines = [f"g {name}"]
    ring_a = []
    ring_b = []
    for i in range(CYLINDER_SEGMENTS):
        angle = 2.0 * math.pi * i / CYLINDER_SEGMENTS
        offset = radius * (math.cos(angle) * u + math.sin(angle) * v)
        ring_a.append(start_index + len(ring_a))
        point = a + offset
        lines.append(f"v {point[0]:.12f} {point[1]:.12f} {point[2]:.12f}")
    start_b = start_index + len(ring_a)
    for i in range(CYLINDER_SEGMENTS):
        angle = 2.0 * math.pi * i / CYLINDER_SEGMENTS
        offset = radius * (math.cos(angle) * u + math.sin(angle) * v)
        ring_b.append(start_b + len(ring_b))
        point = b + offset
        lines.append(f"v {point[0]:.12f} {point[1]:.12f} {point[2]:.12f}")
    center_a = start_index + 2 * CYLINDER_SEGMENTS
    center_b = center_a + 1
    lines.append(f"v {a[0]:.12f} {a[1]:.12f} {a[2]:.12f}")
    lines.append(f"v {b[0]:.12f} {b[1]:.12f} {b[2]:.12f}")
    for i in range(CYLINDER_SEGMENTS):
        j = (i + 1) % CYLINDER_SEGMENTS
        # OBJ indices are 1-based.
        aa = ring_a[i] + 1
        ab = ring_a[j] + 1
        ba = ring_b[i] + 1
        bb = ring_b[j] + 1
        lines.append(f"f {aa} {ba} {bb}")
        lines.append(f"f {aa} {bb} {ab}")
        lines.append(f"f {center_a + 1} {ab} {aa}")
        lines.append(f"f {center_b + 1} {ba} {bb}")
    return lines, start_index + 2 * CYLINDER_SEGMENTS + 2


def selected_candidate_ids(rw4e_report: dict[str, Any]) -> list[str]:
    ids = [item["candidate_id"] for item in rw4e_report["candidate_frontier"]]
    return list(dict.fromkeys(ids))


def candidate_by_id(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {candidate["candidate_id"]: candidate for candidate in payload["candidates"]}


def axis_world_points(
    axes: dict[tuple[str, str], dict[str, Any]],
    tree_id: str,
    hinge_id: str,
    transform: dict[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    axis = axes[(tree_id, hinge_id)]
    a = np.asarray(axis["axis_points"][0], dtype=float)
    b = np.asarray(axis["axis_points"][1], dtype=float)
    return transform_point(transform, a), transform_point(transform, b)


def build_doc(report: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in report["summary"].items()]
    candidate_rows = []
    for record in report["candidate_results"]:
        candidate_rows.append(
            [
                record["candidate_id"],
                record["status"],
                record["body_intrusion_summary"]["blocked_checks"],
                record["hinge_pair_overlap_summary"]["blocked_checks"],
                record["body_intrusion_summary"]["minimum_margin_model_units"],
                record["hinge_pair_overlap_summary"]["minimum_margin_model_units"],
            ]
        )
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4f CAD/Envelope Replay",
            "",
            "Status: frontier external-pin envelope geometry materialized; replay blocked by sampled hardware-envelope intrusions.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4f takes the RW4e candidate frontier and writes OBJ cylinder envelope",
            "geometry for selected-hinge external-pin envelopes on RW3 sample poses.",
            "It then checks each envelope against non-incident body pieces and against",
            "other selected-hinge envelopes.",
            "",
            "This is an envelope replay, not a CAD boolean or printability gate.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW2 mesh payload", report["precondition"]["rw2_mesh_payload"]],
                    ["RW3 kinematics adapter", report["precondition"]["rw3_kinematics_adapter"]],
                    ["RW4e candidate payload", report["precondition"]["rw4e_candidate_payload"]],
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
                ["Candidate", "Status", "Body blockers", "Hinge-pair blockers", "Min body margin", "Min hinge margin"],
                candidate_rows,
            ),
            "",
            "## Materialized Geometry",
            "",
            table(
                ["Artifact", "Path"],
                [["frontier external-pin envelope OBJ", report["materialized_geometry"]["frontier_envelope_obj"]]],
            ),
            "",
            "## Interpretation",
            "",
            "RW4f deliberately blocks RW5: every frontier candidate has sampled envelope",
            "intrusions before any CAD cutback/offset hardware design is introduced.  The",
            "next task is a hardware-interference mitigation pass, not printability.",
            "",
            "## Explicit Nonclaims",
            "",
            "- physical hingeability",
            "- finite-thickness clearance certification",
            "- selected-hinge hardware clearance certification",
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
    for path in (RW2_PATH, RW3_PATH, RW4E_REPORT_PATH, RW4E_PAYLOAD_PATH):
        if not path.exists():
            raise RuntimeError(f"missing source artifact: {path}")

    rw2 = load_json(RW2_PATH)
    rw3 = load_json(RW3_PATH)
    rw4e_report = load_json(RW4E_REPORT_PATH)
    rw4e_payload = load_json(RW4E_PAYLOAD_PATH)
    pieces = load_pieces(rw2)
    axes = load_axes(rw2)
    candidates = candidate_by_id(rw4e_payload)
    frontier_ids = selected_candidate_ids(rw4e_report)

    obj_lines = [
        "# S4 RW4f frontier external-pin envelope cylinders",
        "# envelope geometry only; not CAD solids, not printable hardware",
    ]
    obj_index = 0
    candidate_results = []

    for candidate_id in frontier_ids:
        candidate = candidates[candidate_id]
        scale = float(candidate["parameters"]["scale_mm_per_model_unit"])
        body_checks = []
        hinge_pair_checks = []
        max_axis_coherence = 0.0
        for tree in rw3["trees"]:
            tree_id = tree["tree_id"]
            tree_envelopes = [env for env in candidate["selected_hinge_external_pin_envelopes"] if env["tree_id"] == tree_id]
            for sample in tree["samples"]:
                theta = float(sample["theta_degrees"])
                transforms = sample["piece_transforms"]
                world_axes = []
                for env in tree_envelopes:
                    parent_piece = env["piece_pair"][0]
                    child_piece = env["piece_pair"][1]
                    parent_axis = axis_world_points(axes, tree_id, env["hinge_id"], transforms[parent_piece])
                    child_axis = axis_world_points(axes, tree_id, env["hinge_id"], transforms[child_piece])
                    coherence = max(float(np.linalg.norm(parent_axis[0] - child_axis[0])), float(np.linalg.norm(parent_axis[1] - child_axis[1])))
                    max_axis_coherence = max(max_axis_coherence, coherence)
                    radial_model = float(env["radial_envelope_mm"]) / scale
                    world_axes.append(
                        {
                            "env": env,
                            "axis_a": parent_axis[0],
                            "axis_b": parent_axis[1],
                            "radial_model": radial_model,
                        }
                    )
                    if theta in SNAPSHOT_THETAS:
                        group_name = f"{candidate_id}_{tree_id}_theta{int(theta):03d}_{env['hinge_id']}"
                        lines, obj_index = cylinder_obj_group(group_name, parent_axis[0], parent_axis[1], radial_model, obj_index)
                        obj_lines.extend(lines)

                    incident = set(env["piece_pair"])
                    for piece_id, piece in pieces.items():
                        if piece_id in incident:
                            continue
                        transformed_vertices = [transform_point(transforms[piece_id], vertex) for vertex in piece["vertices"]]
                        distance = segment_piece_surface_distance(parent_axis[0], parent_axis[1], transformed_vertices, piece["faces"])
                        margin = distance - radial_model
                        blocked = margin <= 0.0
                        body_checks.append(
                            {
                                "candidate_id": candidate_id,
                                "tree_id": tree_id,
                                "theta_degrees": theta,
                                "hinge_id": env["hinge_id"],
                                "hinge_pair": env["piece_pair"],
                                "nonincident_piece": piece_id,
                                "radial_envelope_model_units": round(radial_model, 12),
                                "sampled_axis_to_piece_surface_distance_model_units": round(distance, 12),
                                "margin_model_units": round(margin, 12),
                                "margin_mm": round(margin * scale, 9),
                                "blocked_by_sampled_envelope_intrusion": blocked,
                            }
                        )

                for left, right in itertools.combinations(world_axes, 2):
                    distance = segment_segment_distance(left["axis_a"], left["axis_b"], right["axis_a"], right["axis_b"])
                    margin = distance - (left["radial_model"] + right["radial_model"])
                    blocked = margin <= 0.0
                    hinge_pair_checks.append(
                        {
                            "candidate_id": candidate_id,
                            "tree_id": tree_id,
                            "theta_degrees": theta,
                            "left_hinge_id": left["env"]["hinge_id"],
                            "right_hinge_id": right["env"]["hinge_id"],
                            "axis_axis_distance_model_units": round(distance, 12),
                            "combined_radial_envelope_model_units": round(left["radial_model"] + right["radial_model"], 12),
                            "margin_model_units": round(margin, 12),
                            "margin_mm": round(margin * scale, 9),
                            "blocked_by_sampled_envelope_overlap": blocked,
                        }
                    )

        body_blockers = [record for record in body_checks if record["blocked_by_sampled_envelope_intrusion"]]
        hinge_blockers = [record for record in hinge_pair_checks if record["blocked_by_sampled_envelope_overlap"]]
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "status": "blocked_by_sampled_envelope_intrusions" if body_blockers or hinge_blockers else "sampled_envelope_replay_passed_not_cad_certified",
                "parameters": candidate["parameters"],
                "body_intrusion_summary": {
                    "total_checks": len(body_checks),
                    "blocked_checks": len(body_blockers),
                    "minimum_margin_model_units": min(record["margin_model_units"] for record in body_checks),
                    "minimum_margin_mm": min(record["margin_mm"] for record in body_checks),
                },
                "hinge_pair_overlap_summary": {
                    "total_checks": len(hinge_pair_checks),
                    "blocked_checks": len(hinge_blockers),
                    "minimum_margin_model_units": min(record["margin_model_units"] for record in hinge_pair_checks),
                    "minimum_margin_mm": min(record["margin_mm"] for record in hinge_pair_checks),
                },
                "max_axis_coherence_error_model_units": round(max_axis_coherence, 12),
                "body_intrusion_blockers": body_blockers,
                "hinge_pair_overlap_blockers": hinge_blockers,
            }
        )

    ENVELOPE_OBJ_PATH.parent.mkdir(parents=True, exist_ok=True)
    ENVELOPE_OBJ_PATH.write_text("\n".join(obj_lines) + "\n", encoding="utf-8", newline="\n")

    total_body_checks = sum(result["body_intrusion_summary"]["total_checks"] for result in candidate_results)
    total_body_blockers = sum(result["body_intrusion_summary"]["blocked_checks"] for result in candidate_results)
    total_hinge_checks = sum(result["hinge_pair_overlap_summary"]["total_checks"] for result in candidate_results)
    total_hinge_blockers = sum(result["hinge_pair_overlap_summary"]["blocked_checks"] for result in candidate_results)
    passed = [result for result in candidate_results if result["status"] == "sampled_envelope_replay_passed_not_cad_certified"]

    report = {
        "report_id": "S4-RW4F-CAD-ENVELOPE-REPLAY-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "frontier_envelope_geometry_materialized_blocked_before_rw5",
        "precondition": {
            "rw2_mesh_payload": rel(RW2_PATH),
            "rw3_kinematics_adapter": rel(RW3_PATH),
            "rw4e_report": rel(RW4E_REPORT_PATH),
            "rw4e_candidate_payload": rel(RW4E_PAYLOAD_PATH),
        },
        "scope": {
            "geometry_kind": "external_pin_cylinder_envelope_obj_for_frontier_candidates",
            "body_geometry_source": "RW2 exact body OBJ meshes",
            "motion_source": "RW3 sampled zero-thickness transforms",
            "replay_kind": "sampled_envelope_intrusion_check",
            "cad_boolean_status": "not_run",
            "finite_thickness_clearance_status": "blocked_not_certified",
            "printability_validation_status": "not_run",
        },
        "materialized_geometry": {
            "frontier_envelope_obj": rel(ENVELOPE_OBJ_PATH),
            "cylinder_segments": CYLINDER_SEGMENTS,
            "snapshot_theta_degrees": sorted(SNAPSHOT_THETAS),
        },
        "summary": {
            "frontier_candidate_count": len(frontier_ids),
            "sample_tree_count": len(rw3["trees"]),
            "rw3_sample_count_per_tree": [len(tree["samples"]) for tree in rw3["trees"]],
            "materialized_snapshot_theta_count": len(SNAPSHOT_THETAS),
            "nonincident_body_envelope_checks": total_body_checks,
            "nonincident_body_envelope_blockers": total_body_blockers,
            "selected_hinge_pair_envelope_checks": total_hinge_checks,
            "selected_hinge_pair_envelope_blockers": total_hinge_blockers,
            "candidates_passing_sampled_envelope_replay": len(passed),
            "rw5_unblocked": False,
            "blocker_kind": "selected_hinge_external_pin_envelope_intrusion_or_overlap",
        },
        "candidate_results": candidate_results,
        "acceptance": {
            "rw2_mesh_payload_present": RW2_PATH.exists(),
            "rw3_kinematics_adapter_present": RW3_PATH.exists(),
            "rw4e_payload_present": RW4E_PAYLOAD_PATH.exists(),
            "frontier_envelope_obj_written": ENVELOPE_OBJ_PATH.exists(),
            "frontier_candidates_audited": len(frontier_ids) > 0,
            "sampled_envelope_replay_run": total_body_checks > 0 and total_hinge_checks > 0,
            "all_frontier_candidates_pass_sampled_envelope_replay": len(passed) == len(candidate_results),
            "rw5_unblocked": False,
            "cad_boolean_validation_run": False,
            "finite_thickness_clearance_certified": False,
            "printability_validation_run": False,
            "report_says_no_physical_claim": True,
        },
        "next_task": (
            "RW4g design a hardware-interference mitigation model (offset pins, split bosses, or localized cutaways) "
            "for the RW4f blockers, then rerun the envelope replay before RW5."
        ),
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": rel(JSON_PATH),
                "envelope_obj": rel(ENVELOPE_OBJ_PATH),
                "summary": report["summary"],
                "next_task": report["next_task"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
