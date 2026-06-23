#!/usr/bin/env python
"""Build RW4 tier-1 collision/sweep evidence for the S4 real-world branch.

This is sampled zero-thickness collision/sweep evidence over the RW3
kinematics.  It records broad-phase AABB overlap, narrow-phase strict-convex
SAT overlap status, near-contact records, and sampled sweep envelopes.

It is not a finite-thickness clearance certificate, not a continuous collision
certificate, not CAD validation, not printability, and not a prototype claim.
"""

from __future__ import annotations

import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULTS_ROOT = ROOT / "results" / CASE_ID
RESULT_ROOT = RESULTS_ROOT / "real_world"
DOC_PATH = ROOT / "docs" / "S4_RW4_COLLISION_SWEEP_EVIDENCE.md"
JSON_PATH = RESULT_ROOT / "rw4_collision_sweep_report.json"
RW3_PATH = RESULT_ROOT / "rw3_kinematics_adapter_manifest.json"

THETA_START_DEGREES = 0.0
THETA_END_DEGREES = 120.0
THETA_STEP_DEGREES = 0.25
NEAR_CONTACT_AXIS_GAP_THRESHOLD = 1.0e-4
ROOT_PIECE = "P0"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
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


def theta_grid() -> list[float]:
    count = int(round((THETA_END_DEGREES - THETA_START_DEGREES) / THETA_STEP_DEGREES))
    return [round(THETA_START_DEGREES + i * THETA_STEP_DEGREES, 8) for i in range(count + 1)]


def find_tree(case: dict[str, Any], tree_id: str) -> dict[str, Any]:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"tree not found: {tree_id}")
    return tree


def signed_degrees(tree: dict[str, Any], signs_by_hinge: dict[str, int], theta_degrees: float) -> dict[str, float]:
    return {
        hinge_id: float(signs_by_hinge[hinge_id]) * float(theta_degrees)
        for hinge_id in tree["hinge_ids"]
    }


def transforms_for_sample(
    case: dict[str, Any],
    tree: dict[str, Any],
    signs_by_hinge: dict[str, int],
    theta_degrees: float,
) -> dict[str, dict[str, np.ndarray]]:
    degrees_by_hinge = signed_degrees(tree, signs_by_hinge, theta_degrees)
    angles = {hinge_id: math.radians(degrees) for hinge_id, degrees in degrees_by_hinge.items()}
    selected_hinges = batch.selected_hinges_for_tree(case, tree)
    return lib.transforms_for_hinge_tree(
        case["piece_ids"],
        selected_hinges,
        case["labels"],
        angles,
        root_piece=ROOT_PIECE,
    )


def selected_hinge_pairs(case: dict[str, Any], tree: dict[str, Any]) -> set[tuple[str, str]]:
    return {
        tuple(sorted(hinge["pieces"]))
        for hinge in batch.selected_hinges_for_tree(case, tree)
    }


def aabb(points: Sequence[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    arr = np.asarray(points, dtype=float)
    return arr.min(axis=0), arr.max(axis=0)


def aabb_overlaps(left: tuple[np.ndarray, np.ndarray], right: tuple[np.ndarray, np.ndarray], tol: float = 1.0e-12) -> bool:
    left_min, left_max = left
    right_min, right_max = right
    return bool(np.all(left_min <= right_max + tol) and np.all(right_min <= left_max + tol))


def axis_gap_proxy(minimum_axis_overlap_proxy: float | None) -> float | None:
    if minimum_axis_overlap_proxy is None:
        return None
    return max(0.0, -float(minimum_axis_overlap_proxy))


def pair_collision_records(
    transformed: dict[str, Sequence[np.ndarray]],
    selected_pairs: set[tuple[str, str]],
) -> list[dict[str, Any]]:
    records = []
    boxes = {piece_id: aabb(poly) for piece_id, poly in transformed.items()}
    for left, right in itertools.combinations(sorted(transformed), 2):
        pair = tuple(sorted((left, right)))
        has_overlap, min_overlap = lib.strict_interior_overlap(transformed[left], transformed[right])
        gap = axis_gap_proxy(min_overlap)
        records.append(
            {
                "pair": list(pair),
                "pair_role": "selected_hinge_pair" if pair in selected_pairs else "nonhinge_pair",
                "broad_phase_aabb_overlap": aabb_overlaps(boxes[left], boxes[right]),
                "narrow_phase_status": "blocked" if has_overlap else "separated_or_touching",
                "minimum_axis_overlap_proxy": round(float(min_overlap), 12),
                "axis_gap_proxy": round(float(gap), 12) if gap is not None else None,
                "near_contact": bool(gap is not None and gap <= NEAR_CONTACT_AXIS_GAP_THRESHOLD),
            }
        )
    return records


def min_gap(records: list[dict[str, Any]], role: str | None = None) -> float | None:
    values = [
        record["axis_gap_proxy"]
        for record in records
        if record["axis_gap_proxy"] is not None and (role is None or record["pair_role"] == role)
    ]
    return min(values) if values else None


def update_sweep_buffers(
    sweep_buffers: dict[str, list[np.ndarray]],
    transformed: dict[str, Sequence[np.ndarray]],
) -> None:
    for piece_id, poly in transformed.items():
        sweep_buffers.setdefault(piece_id, []).extend(np.asarray(point, dtype=float) for point in poly)


def sweep_summary(sweep_buffers: dict[str, list[np.ndarray]], initial_pieces: dict[str, Sequence[np.ndarray]]) -> dict[str, Any]:
    piece_records = []
    sweep_boxes: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for piece_id, points in sorted(sweep_buffers.items()):
        box = aabb(points)
        sweep_boxes[piece_id] = box
        initial = list(initial_pieces[piece_id])
        max_displacement = 0.0
        for point in points:
            max_displacement = max(max_displacement, min(float(np.linalg.norm(point - base)) for base in initial))
        piece_records.append(
            {
                "piece_id": piece_id,
                "sweep_aabb_min": [round(float(value), 12) for value in box[0]],
                "sweep_aabb_max": [round(float(value), 12) for value in box[1]],
                "sweep_aabb_diagonal": round(float(np.linalg.norm(box[1] - box[0])), 12),
                "max_sampled_vertex_displacement_to_initial_vertex_set": round(max_displacement, 12),
            }
        )

    pair_records = []
    for left, right in itertools.combinations(sorted(sweep_boxes), 2):
        pair_records.append(
            {
                "pair": [left, right],
                "sampled_sweep_aabb_overlap": aabb_overlaps(sweep_boxes[left], sweep_boxes[right]),
            }
        )
    return {"pieces": piece_records, "pair_sweep_aabb_overlaps": pair_records}


def sample_tree(case: dict[str, Any], tree: dict[str, Any], signs_by_hinge: dict[str, int]) -> dict[str, Any]:
    selected_pairs = selected_hinge_pairs(case, tree)
    grid = theta_grid()
    sample_summaries = []
    near_contact_records = []
    blocked_records = []
    sweep_buffers: dict[str, list[np.ndarray]] = {}
    initial_pieces: dict[str, Sequence[np.ndarray]] | None = None

    for theta in grid:
        transforms = transforms_for_sample(case, tree, signs_by_hinge, theta)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        if initial_pieces is None:
            initial_pieces = transformed
        update_sweep_buffers(sweep_buffers, transformed)
        pair_records = pair_collision_records(transformed, selected_pairs)
        near_records = [record for record in pair_records if record["near_contact"]]
        selected_near_records = [record for record in near_records if record["pair_role"] == "selected_hinge_pair"]
        nonhinge_near_records = [record for record in near_records if record["pair_role"] == "nonhinge_pair"]
        blocked = [record for record in pair_records if record["narrow_phase_status"] == "blocked"]
        if near_records:
            for record in near_records:
                near_contact_records.append({"theta_degrees": theta, **record})
        if blocked:
            for record in blocked:
                blocked_records.append({"theta_degrees": theta, **record})
        sample_summaries.append(
            {
                "theta_degrees": theta,
                "status": "blocked" if blocked else "collision_free",
                "broad_phase_aabb_overlap_pair_count": sum(1 for record in pair_records if record["broad_phase_aabb_overlap"]),
                "near_contact_pair_count": len(near_records),
                "selected_hinge_near_contact_pair_count": len(selected_near_records),
                "nonhinge_near_contact_pair_count": len(nonhinge_near_records),
                "minimum_axis_gap_proxy_all_pairs": min_gap(pair_records),
                "minimum_axis_gap_proxy_nonhinge_pairs": min_gap(pair_records, "nonhinge_pair"),
                "minimum_axis_gap_proxy_selected_hinge_pairs": min_gap(pair_records, "selected_hinge_pair"),
            }
        )

    segment_candidates = []
    nonhinge_segment_candidates = []
    for left, right in zip(sample_summaries, sample_summaries[1:]):
        if left["near_contact_pair_count"] or right["near_contact_pair_count"] or left["status"] != "collision_free" or right["status"] != "collision_free":
            segment_candidates.append(
                {
                    "theta_interval_degrees": [left["theta_degrees"], right["theta_degrees"]],
                    "reason": "near_contact_or_blocked_endpoint",
                    "left_near_contact_pair_count": left["near_contact_pair_count"],
                    "right_near_contact_pair_count": right["near_contact_pair_count"],
                    "left_status": left["status"],
                    "right_status": right["status"],
                }
            )
        if (
            left["nonhinge_near_contact_pair_count"]
            or right["nonhinge_near_contact_pair_count"]
            or left["status"] != "collision_free"
            or right["status"] != "collision_free"
        ):
            nonhinge_segment_candidates.append(
                {
                    "theta_interval_degrees": [left["theta_degrees"], right["theta_degrees"]],
                    "reason": "nonhinge_near_contact_or_blocked_endpoint",
                    "left_nonhinge_near_contact_pair_count": left["nonhinge_near_contact_pair_count"],
                    "right_nonhinge_near_contact_pair_count": right["nonhinge_near_contact_pair_count"],
                    "left_status": left["status"],
                    "right_status": right["status"],
                }
            )

    assert initial_pieces is not None
    return {
        "tree_id": tree["tree_id"],
        "hinge_ids": list(tree["hinge_ids"]),
        "sign_vector_by_hinge": signs_by_hinge,
        "selected_hinge_pairs": [list(pair) for pair in sorted(selected_pairs)],
        "sample_count": len(sample_summaries),
        "sample_grid_degrees": {
            "start": THETA_START_DEGREES,
            "end": THETA_END_DEGREES,
            "step": THETA_STEP_DEGREES,
        },
        "all_samples_collision_free": all(sample["status"] == "collision_free" for sample in sample_summaries),
        "blocked_record_count": len(blocked_records),
        "minimum_observed_axis_gap_proxy_all_pairs": min(
            sample["minimum_axis_gap_proxy_all_pairs"] for sample in sample_summaries if sample["minimum_axis_gap_proxy_all_pairs"] is not None
        ),
        "minimum_observed_axis_gap_proxy_nonhinge_pairs": min(
            sample["minimum_axis_gap_proxy_nonhinge_pairs"] for sample in sample_summaries if sample["minimum_axis_gap_proxy_nonhinge_pairs"] is not None
        ),
        "minimum_observed_axis_gap_proxy_selected_hinge_pairs": min(
            sample["minimum_axis_gap_proxy_selected_hinge_pairs"] for sample in sample_summaries if sample["minimum_axis_gap_proxy_selected_hinge_pairs"] is not None
        ),
        "near_contact_threshold": NEAR_CONTACT_AXIS_GAP_THRESHOLD,
        "near_contact_record_count": len(near_contact_records),
        "selected_hinge_near_contact_record_count": sum(
            1 for record in near_contact_records if record["pair_role"] == "selected_hinge_pair"
        ),
        "nonhinge_near_contact_record_count": sum(
            1 for record in near_contact_records if record["pair_role"] == "nonhinge_pair"
        ),
        "near_contact_records": near_contact_records,
        "tier2_candidate_segment_count": len(segment_candidates),
        "tier2_nonhinge_candidate_segment_count": len(nonhinge_segment_candidates),
        "tier2_candidate_segments": segment_candidates,
        "tier2_nonhinge_candidate_segments": nonhinge_segment_candidates,
        "sample_summaries": sample_summaries,
        "sampled_sweep_summary": sweep_summary(sweep_buffers, initial_pieces),
    }


def build_doc(report: dict[str, Any]) -> str:
    tree_rows = []
    for tree in report["trees"]:
        tree_rows.append(
            [
                tree["tree_id"],
                tree["sample_count"],
                tree["all_samples_collision_free"],
                tree["minimum_observed_axis_gap_proxy_all_pairs"],
                tree["minimum_observed_axis_gap_proxy_nonhinge_pairs"],
                tree["near_contact_record_count"],
                tree["nonhinge_near_contact_record_count"],
                tree["tier2_candidate_segment_count"],
                tree["tier2_nonhinge_candidate_segment_count"],
            ]
        )
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    near_rows = []
    for tree in report["trees"]:
        for record in tree["near_contact_records"][:20]:
            near_rows.append(
                [
                    tree["tree_id"],
                    record["theta_degrees"],
                    "-".join(record["pair"]),
                    record["pair_role"],
                    record["axis_gap_proxy"],
                    record["minimum_axis_overlap_proxy"],
                ]
            )
    sweep_rows = []
    for tree in report["trees"]:
        for piece in tree["sampled_sweep_summary"]["pieces"]:
            sweep_rows.append(
                [
                    tree["tree_id"],
                    piece["piece_id"],
                    piece["sweep_aabb_diagonal"],
                    piece["max_sampled_vertex_displacement_to_initial_vertex_set"],
                ]
            )

    return "\n".join(
        [
            "# S4 RW4 Collision/Sweep Evidence",
            "",
            "Status: sampled tier-1 collision/sweep evidence only.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4 samples the RW3 one-parameter kinematics for `TREE_007` and",
            "`TREE_021` on a recorded theta grid.  It records broad-phase AABB",
            "overlap, narrow-phase strict-convex SAT status, near-contact records,",
            "and sampled sweep AABB envelopes.",
            "",
            "The gap values are SAT axis-gap proxies from the existing zero-thickness",
            "tetrahedron model. They are useful for routing and diagnostics, but they",
            "are not Euclidean finite-thickness clearance certificates.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW3 kinematics adapter", str(RW3_PATH)],
                    ["kinematics/collision library", str(ROOT / "scripts" / "mechanical_audit_lib.py")],
                ],
            ),
            "",
            "## Tree Summary",
            "",
            table(
                [
                    "Tree",
                    "Samples",
                    "All collision free",
                    "Min gap proxy all",
                    "Min gap proxy nonhinge",
                    "Near records",
                    "Nonhinge near records",
                    "Tier-2 segments",
                    "Nonhinge tier-2 segments",
                ],
                tree_rows,
            ),
            "",
            "## Near-Contact Records",
            "",
            f"Threshold: `{NEAR_CONTACT_AXIS_GAP_THRESHOLD}` axis-gap proxy units.",
            "Only the first 20 records per tree are shown here; the JSON report contains the full ledger.",
            "",
            table(["Tree", "Theta", "Pair", "Role", "Gap proxy", "Min overlap proxy"], near_rows or [["none", "", "", "", "", ""]]),
            "",
            "## Sampled Sweep Envelope",
            "",
            table(["Tree", "Piece", "Sweep AABB diagonal", "Max sampled vertex displacement"], sweep_rows),
            "",
            "## Explicit Nonclaims",
            "",
            "- finite-thickness clearance",
            "- continuous collision-free sweep",
            "- hinge hardware clearance",
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
    if not RW3_PATH.exists():
        raise RuntimeError(f"missing RW3 manifest: {RW3_PATH}")
    rw3 = load_json(RW3_PATH)
    if rw3.get("status") != "kinematics_adapter_created_not_hardware_ready":
        raise RuntimeError(f"unexpected RW3 status: {rw3.get('status')}")

    case = batch.build_case()
    signs_by_tree = {tree["tree_id"]: {hinge: int(sign) for hinge, sign in tree["sign_vector_by_hinge"].items()} for tree in rw3["trees"]}
    tree_reports = []
    for tree_id in rw3["scope"]["target_trees"]:
        tree = find_tree(case, tree_id)
        signs = signs_by_tree[tree_id]
        if set(signs) != set(tree["hinge_ids"]):
            raise RuntimeError(f"sign vector does not match tree hinges: {tree_id}")
        tree_reports.append(sample_tree(case, tree, signs))

    total_samples = sum(tree["sample_count"] for tree in tree_reports)
    total_near = sum(tree["near_contact_record_count"] for tree in tree_reports)
    total_nonhinge_near = sum(tree["nonhinge_near_contact_record_count"] for tree in tree_reports)
    total_tier2 = sum(tree["tier2_candidate_segment_count"] for tree in tree_reports)
    total_nonhinge_tier2 = sum(tree["tier2_nonhinge_candidate_segment_count"] for tree in tree_reports)
    report = {
        "report_id": "S4-RW4-TIER1-COLLISION-SWEEP-EVIDENCE-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "sampled_collision_sweep_evidence_only_not_finite_thickness_certified",
        "precondition": {
            "rw3_manifest": rel(RW3_PATH),
            "rw3_status": rw3.get("status"),
        },
        "scope": {
            "evidence_tier": "tier_1_sampled_broad_and_narrow_phase",
            "theta_grid_degrees": {
                "start": THETA_START_DEGREES,
                "end": THETA_END_DEGREES,
                "step": THETA_STEP_DEGREES,
                "sample_count_per_tree": len(theta_grid()),
            },
            "near_contact_axis_gap_threshold": NEAR_CONTACT_AXIS_GAP_THRESHOLD,
            "collision_model": "zero_thickness_exact_tetrahedral_body_solids",
            "broad_phase": "sampled_AABB_overlap",
            "narrow_phase": "strict_convex_SAT_positive_volume_overlap",
            "continuous_collision_validation_status": "not_run",
            "finite_thickness_clearance_status": "not_certified",
            "hardware_geometry_status": "absent",
            "printability_validation_status": "not_run",
        },
        "summary": {
            "tree_count": len(tree_reports),
            "total_sample_count": total_samples,
            "total_near_contact_record_count": total_near,
            "total_nonhinge_near_contact_record_count": total_nonhinge_near,
            "total_tier2_candidate_segment_count": total_tier2,
            "total_nonhinge_tier2_candidate_segment_count": total_nonhinge_tier2,
            "all_samples_collision_free": all(tree["all_samples_collision_free"] for tree in tree_reports),
            "minimum_observed_axis_gap_proxy_all_pairs": min(tree["minimum_observed_axis_gap_proxy_all_pairs"] for tree in tree_reports),
            "minimum_observed_axis_gap_proxy_nonhinge_pairs": min(tree["minimum_observed_axis_gap_proxy_nonhinge_pairs"] for tree in tree_reports),
        },
        "trees": tree_reports,
        "acceptance": {
            "rw3_manifest_present": RW3_PATH.exists(),
            "rw3_status_locked": rw3.get("status") == "kinematics_adapter_created_not_hardware_ready",
            "sample_grid_recorded": True,
            "tree_count_is_2": len(tree_reports) == 2,
            "sample_count_per_tree": len(theta_grid()),
            "total_sample_count": total_samples,
            "all_sampled_narrow_phase_collision_free": all(tree["all_samples_collision_free"] for tree in tree_reports),
            "minimum_observed_clearance_proxy_recorded": all(
                tree["minimum_observed_axis_gap_proxy_all_pairs"] is not None for tree in tree_reports
            ),
            "near_misses_listed": total_near >= 0,
            "sampled_sweep_envelopes_recorded": all(
                len(tree["sampled_sweep_summary"]["pieces"]) == 4 for tree in tree_reports
            ),
            "report_says_sampled_evidence_only": True,
            "continuous_collision_validation_status": "not_run",
            "finite_thickness_clearance_status": "not_certified",
            "hardware_geometry_absent": True,
            "printability_validation_status": "not_run",
        },
        "next_task": "RW4b conservative interval/swept validation for the candidate near-contact segments, before RW5 printability/fabrication gates.",
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "report": rel(JSON_PATH), "summary": rel(DOC_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
