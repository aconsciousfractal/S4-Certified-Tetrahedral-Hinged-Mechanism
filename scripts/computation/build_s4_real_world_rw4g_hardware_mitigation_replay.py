#!/usr/bin/env python
"""Build RW4g hardware-interference mitigation replay for S4.

RW4g consumes RW4f's blocking frontier replay and tests a simple mitigation
family: segmented external-pin/boss envelopes with endpoint setback along each
selected hinge axis.  The model answers one narrow question:

    How much axis-end setback is needed before the sampled envelope replay no
    longer intrudes into non-incident body pieces or other selected-hinge
    envelopes?

This is still not printable CAD.  The output is an envelope mitigation replay
and OBJ proxy only.  It does not subtract body reliefs, does not design real
hinge knuckles, does not validate strength or assembly, and does not certify
finite-thickness physical hingeability.
"""

from __future__ import annotations

import itertools
import json
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
RW4F_PATH = RESULT_ROOT / "rw4f_cad_envelope_replay_report.json"
ENVELOPE_DIR = RESULT_ROOT / "cad_envelope_replay"
MITIGATED_OBJ_PATH = ENVELOPE_DIR / "rw4g_segmented_external_pin_envelopes.obj"
JSON_PATH = RESULT_ROOT / "rw4g_hardware_mitigation_replay_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4G_HARDWARE_MITIGATION_REPLAY.md"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import build_s4_real_world_rw4f_cad_envelope_replay as rw4f  # noqa: E402
import mechanical_audit_lib as lib  # noqa: E402


SETBACK_FRACTION_GRID = [
    0.02,
    0.04,
    0.06,
    0.08,
    0.10,
    0.12,
    0.15,
    0.18,
    0.20,
    0.25,
    0.30,
    0.35,
    0.40,
    0.45,
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


def shorten_axis(a: np.ndarray, b: np.ndarray, setback_model: float) -> tuple[np.ndarray, np.ndarray] | None:
    axis = b - a
    length = float(np.linalg.norm(axis))
    if length <= rw4f.EPS or 2.0 * setback_model >= length:
        return None
    direction = axis / length
    return a + direction * setback_model, b - direction * setback_model


def selected_candidate_ids(rw4e_report: dict[str, Any]) -> list[str]:
    return [record["candidate_id"] for record in rw4e_report["candidate_frontier"]]


def replay_candidate_with_setback(
    candidate: dict[str, Any],
    setback_fraction: float,
    rw2: dict[str, Any],
    rw3: dict[str, Any],
    pieces: dict[str, dict[str, Any]],
    axes: dict[tuple[str, str], dict[str, Any]],
) -> dict[str, Any]:
    scale = float(candidate["parameters"]["scale_mm_per_model_unit"])
    body_checks = []
    hinge_pair_checks = []
    axis_lengths = []
    shortened_length_fractions = []
    for tree in rw3["trees"]:
        tree_id = tree["tree_id"]
        tree_envelopes = [env for env in candidate["selected_hinge_external_pin_envelopes"] if env["tree_id"] == tree_id]
        for sample in tree["samples"]:
            transforms = sample["piece_transforms"]
            world_axes = []
            for env in tree_envelopes:
                parent_piece = env["piece_pair"][0]
                axis_a, axis_b = rw4f.axis_world_points(axes, tree_id, env["hinge_id"], transforms[parent_piece])
                axis_length = float(np.linalg.norm(axis_b - axis_a))
                setback_model = setback_fraction * axis_length
                shortened = shorten_axis(axis_a, axis_b, setback_model)
                if shortened is None:
                    return {
                        "valid_segment": False,
                        "reason": "setback_removes_axis",
                    }
                short_a, short_b = shortened
                axis_lengths.append(axis_length)
                shortened_length_fractions.append(float(np.linalg.norm(short_b - short_a)) / axis_length)
                radial_model = float(env["radial_envelope_mm"]) / scale
                world_axes.append(
                    {
                        "env": env,
                        "axis_a": short_a,
                        "axis_b": short_b,
                        "radial_model": radial_model,
                    }
                )

                incident = set(env["piece_pair"])
                for piece_id, piece in pieces.items():
                    if piece_id in incident:
                        continue
                    transformed_vertices = [rw4f.transform_point(transforms[piece_id], vertex) for vertex in piece["vertices"]]
                    distance = rw4f.segment_piece_surface_distance(short_a, short_b, transformed_vertices, piece["faces"])
                    margin = distance - radial_model
                    body_checks.append(
                        {
                            "tree_id": tree_id,
                            "theta_degrees": float(sample["theta_degrees"]),
                            "hinge_id": env["hinge_id"],
                            "nonincident_piece": piece_id,
                            "radial_envelope_model_units": round(radial_model, 12),
                            "setback_model_units": round(setback_model, 12),
                            "sampled_axis_to_piece_surface_distance_model_units": round(distance, 12),
                            "margin_model_units": round(margin, 12),
                            "margin_mm": round(margin * scale, 9),
                            "blocked": margin <= 0.0,
                        }
                    )

            for left, right in itertools.combinations(world_axes, 2):
                distance = rw4f.segment_segment_distance(left["axis_a"], left["axis_b"], right["axis_a"], right["axis_b"])
                margin = distance - (left["radial_model"] + right["radial_model"])
                hinge_pair_checks.append(
                    {
                        "tree_id": tree_id,
                        "theta_degrees": float(sample["theta_degrees"]),
                        "left_hinge_id": left["env"]["hinge_id"],
                        "right_hinge_id": right["env"]["hinge_id"],
                        "axis_axis_distance_model_units": round(distance, 12),
                        "combined_radial_envelope_model_units": round(left["radial_model"] + right["radial_model"], 12),
                        "margin_model_units": round(margin, 12),
                        "margin_mm": round(margin * scale, 9),
                        "blocked": margin <= 0.0,
                    }
                )

    body_blockers = [record for record in body_checks if record["blocked"]]
    hinge_blockers = [record for record in hinge_pair_checks if record["blocked"]]
    return {
        "valid_segment": True,
        "setback_fraction": setback_fraction,
        "setback_mm_by_axis": round(setback_fraction * min(axis_lengths) * scale, 9),
        "shortened_length_fraction": round(min(shortened_length_fractions), 12),
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
        "passed_sampled_envelope_replay": len(body_blockers) == 0 and len(hinge_blockers) == 0,
        "body_intrusion_blockers": body_blockers,
        "hinge_pair_overlap_blockers": hinge_blockers,
    }


def materialize_candidate_obj(
    obj_lines: list[str],
    start_index: int,
    candidate: dict[str, Any],
    setback_fraction: float,
    rw2: dict[str, Any],
    rw3: dict[str, Any],
    axes: dict[tuple[str, str], dict[str, Any]],
) -> int:
    scale = float(candidate["parameters"]["scale_mm_per_model_unit"])
    for tree in rw3["trees"]:
        tree_id = tree["tree_id"]
        tree_envelopes = [env for env in candidate["selected_hinge_external_pin_envelopes"] if env["tree_id"] == tree_id]
        for sample in tree["samples"]:
            theta = float(sample["theta_degrees"])
            if theta not in rw4f.SNAPSHOT_THETAS:
                continue
            transforms = sample["piece_transforms"]
            for env in tree_envelopes:
                parent_piece = env["piece_pair"][0]
                axis_a, axis_b = rw4f.axis_world_points(axes, tree_id, env["hinge_id"], transforms[parent_piece])
                length = float(np.linalg.norm(axis_b - axis_a))
                shortened = shorten_axis(axis_a, axis_b, setback_fraction * length)
                if shortened is None:
                    continue
                short_a, short_b = shortened
                radial_model = float(env["radial_envelope_mm"]) / scale
                group_name = f"{candidate['candidate_id']}_setback{int(round(setback_fraction * 1000)):03d}_{tree_id}_theta{int(theta):03d}_{env['hinge_id']}"
                lines, start_index = rw4f.cylinder_obj_group(group_name, short_a, short_b, radial_model, start_index)
                obj_lines.extend(lines)
    return start_index


def build_doc(report: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in report["summary"].items()]
    result_rows = []
    for result in report["candidate_results"]:
        result_rows.append(
            [
                result["candidate_id"],
                result["status"],
                result["minimum_passing_setback_fraction"],
                result["setback_mm_by_axis"],
                result["shortened_length_fraction"],
                result["passing_body_min_margin_model_units"],
                result["passing_hinge_min_margin_model_units"],
            ]
        )
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4g Hardware-Mitigation Replay",
            "",
            "Status: segmented external-pin endpoint-setback mitigation passes sampled envelope replay; not CAD/printability validated.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4g tests the first hardware-interference mitigation family for the RW4f",
            "blockers: external-pin/boss envelopes are shortened along each hinge axis by",
            "a symmetric endpoint setback.  The resulting segmented envelope is replayed",
            "against non-incident body pieces and other selected-hinge envelopes.",
            "",
            "This is still only an envelope model.  It does not design a real hinge knuckle",
            "layout, subtract body cutaways, validate CAD booleans, prove strength, or run",
            "printability checks.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW2 mesh payload", report["precondition"]["rw2_mesh_payload"]],
                    ["RW3 kinematics adapter", report["precondition"]["rw3_kinematics_adapter"]],
                    ["RW4e candidate payload", report["precondition"]["rw4e_candidate_payload"]],
                    ["RW4f blocked replay", report["precondition"]["rw4f_cad_envelope_replay"]],
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
                ["Candidate", "Status", "Setback fraction", "Setback mm", "Remaining axis length", "Body min margin", "Hinge min margin"],
                result_rows,
            ),
            "",
            "## Materialized Geometry",
            "",
            table(
                ["Artifact", "Path"],
                [["segmented external-pin envelope OBJ", report["materialized_geometry"]["segmented_envelope_obj"]]],
            ),
            "",
            "## Interpretation",
            "",
            "Endpoint setback fixes the RW4f sampled envelope blockers for this frontier,",
            "but it does not yet unblock RW5.  A future step must turn the envelope into",
            "explicit CAD/mesh operations, including body relief/cutaways and manufacturable",
            "hinge hardware.",
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
    for path in (RW2_PATH, RW3_PATH, RW4E_REPORT_PATH, RW4E_PAYLOAD_PATH, RW4F_PATH):
        if not path.exists():
            raise RuntimeError(f"missing source artifact: {path}")

    rw2 = load_json(RW2_PATH)
    rw3 = load_json(RW3_PATH)
    rw4e_report = load_json(RW4E_REPORT_PATH)
    rw4e_payload = load_json(RW4E_PAYLOAD_PATH)
    rw4f_report = load_json(RW4F_PATH)
    pieces = rw4f.load_pieces(rw2)
    axes = rw4f.load_axes(rw2)
    candidates = rw4f.candidate_by_id(rw4e_payload)
    frontier_ids = selected_candidate_ids(rw4e_report)

    candidate_results = []
    obj_lines = [
        "# S4 RW4g segmented external-pin endpoint-setback envelope cylinders",
        "# mitigation envelope only; not CAD solids, not printable hardware",
    ]
    obj_index = 0

    for candidate_id in frontier_ids:
        candidate = candidates[candidate_id]
        attempts = []
        passing = None
        for setback_fraction in SETBACK_FRACTION_GRID:
            attempt = replay_candidate_with_setback(candidate, setback_fraction, rw2, rw3, pieces, axes)
            attempt["setback_fraction"] = setback_fraction
            attempts.append(attempt)
            if attempt.get("passed_sampled_envelope_replay"):
                passing = attempt
                break
        if passing is not None:
            obj_index = materialize_candidate_obj(obj_lines, obj_index, candidate, passing["setback_fraction"], rw2, rw3, axes)
            status = "segmented_endpoint_setback_passes_sampled_envelope_replay"
        else:
            status = "blocked_after_endpoint_setback_grid"
        candidate_results.append(
            {
                "candidate_id": candidate_id,
                "status": status,
                "parameters": candidate["parameters"],
                "minimum_passing_setback_fraction": passing["setback_fraction"] if passing is not None else None,
                "setback_mm_by_axis": passing["setback_mm_by_axis"] if passing is not None else None,
                "shortened_length_fraction": passing["shortened_length_fraction"] if passing is not None else None,
                "passing_body_min_margin_model_units": passing["body_intrusion_summary"]["minimum_margin_model_units"] if passing is not None else None,
                "passing_hinge_min_margin_model_units": passing["hinge_pair_overlap_summary"]["minimum_margin_model_units"] if passing is not None else None,
                "attempt_count": len(attempts),
                "attempts": attempts,
            }
        )

    MITIGATED_OBJ_PATH.parent.mkdir(parents=True, exist_ok=True)
    MITIGATED_OBJ_PATH.write_text("\n".join(obj_lines) + "\n", encoding="utf-8", newline="\n")

    passed = [record for record in candidate_results if record["status"] == "segmented_endpoint_setback_passes_sampled_envelope_replay"]
    max_setback_fraction = max(record["minimum_passing_setback_fraction"] for record in passed) if passed else None
    min_remaining_fraction = min(record["shortened_length_fraction"] for record in passed) if passed else None
    min_body_margin = min(record["passing_body_min_margin_model_units"] for record in passed) if passed else None
    min_hinge_margin = min(record["passing_hinge_min_margin_model_units"] for record in passed) if passed else None

    report = {
        "report_id": "S4-RW4G-HARDWARE-MITIGATION-REPLAY-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "segmented_endpoint_setback_envelope_replay_passed_not_cad_validated",
        "precondition": {
            "rw2_mesh_payload": rel(RW2_PATH),
            "rw3_kinematics_adapter": rel(RW3_PATH),
            "rw4e_candidate_payload": rel(RW4E_PAYLOAD_PATH),
            "rw4f_cad_envelope_replay": rel(RW4F_PATH),
            "rw4f_status": rw4f_report.get("status"),
        },
        "mitigation_family": {
            "name": "segmented_external_pin_endpoint_setback",
            "description": "Shorten external-pin/boss envelope cylinders symmetrically away from both endpoints of each selected hinge axis.",
            "setback_fraction_grid": SETBACK_FRACTION_GRID,
            "cad_status": "envelope_proxy_only_no_boolean_operations",
            "assembly_status": "not_validated",
        },
        "materialized_geometry": {
            "segmented_envelope_obj": rel(MITIGATED_OBJ_PATH),
            "cylinder_segments": rw4f.CYLINDER_SEGMENTS,
            "snapshot_theta_degrees": sorted(rw4f.SNAPSHOT_THETAS),
        },
        "summary": {
            "frontier_candidate_count": len(frontier_ids),
            "candidates_passing_after_setback": len(passed),
            "candidates_still_blocked": len(candidate_results) - len(passed),
            "maximum_required_setback_fraction": max_setback_fraction,
            "minimum_remaining_axis_length_fraction": min_remaining_fraction,
            "minimum_passing_body_margin_model_units": min_body_margin,
            "minimum_passing_hinge_margin_model_units": min_hinge_margin,
            "rw4f_blockers_mitigated_in_sampled_envelope_replay": len(passed) == len(candidate_results),
            "rw5_unblocked": False,
        },
        "candidate_results": candidate_results,
        "acceptance": {
            "rw4f_report_present": RW4F_PATH.exists(),
            "mitigated_envelope_obj_written": MITIGATED_OBJ_PATH.exists(),
            "all_frontier_candidates_replayed": len(candidate_results) == len(frontier_ids),
            "all_frontier_candidates_pass_segmented_envelope_replay": len(passed) == len(candidate_results),
            "cad_boolean_validation_run": False,
            "body_relief_geometry_materialized": False,
            "finite_thickness_clearance_certified": False,
            "printability_validation_run": False,
            "rw5_unblocked": False,
            "report_says_no_physical_claim": True,
        },
        "next_task": (
            "RW4h materialize a combined CAD/mesh proxy for body relief cutaways plus segmented hinge envelopes, "
            "then rerun mesh/envelope validity checks before RW5."
        ),
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "report": rel(JSON_PATH),
                "segmented_envelope_obj": rel(MITIGATED_OBJ_PATH),
                "summary": report["summary"],
                "next_task": report["next_task"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
