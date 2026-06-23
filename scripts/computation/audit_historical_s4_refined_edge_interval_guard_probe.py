"""Interval-guard probe for refined bounded component edges.

This first probe targets TREE_021 refined spanning-tree segments. It applies the
same conservative local-displacement SAT guard used by the ray-cell certificate,
generalized from one scalar ray parameter to a 3-coordinate hinge-angle segment.

The result is expected to be diagnostic: if all pairs on a segment pass, the
segment is interval-guard certified by this conservative protocol; otherwise the
report records which pair/role defeated the guard.
"""

from __future__ import annotations

from collections import Counter
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "refined_edge_interval_guard_probe_report.json"
TARGET_TREE_IDS = ["TREE_021"]
MAX_COORDINATE_DELTA_DEGREES = 5.0
MAX_STORED_FAILED_SEGMENTS = 80
MAX_STORED_LOW_MARGIN_SEGMENTS = 40

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402
import audit_historical_s4_bounded_component_edge_refinement as refinement  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def selected_hinge_by_pair(case: dict, tree: dict) -> dict[tuple[str, str], dict]:
    output = {}
    for hinge_id in tree["hinge_ids"]:
        hinge = case["hinge_by_id"][hinge_id]
        output[tuple(sorted(hinge["pieces"]))] = hinge
    return output


def refined_segments_for_tree(case: dict, source_audit: dict, signs_by_tree: dict[str, dict[str, int]]) -> tuple[dict, list[dict]]:
    tree = comp.find_tree(case, source_audit["tree_id"])
    nodes_by_id = bounded.all_nodes_by_id(tree, signs_by_tree[source_audit["tree_id"]])
    free_ids = bounded.free_node_ids_from_source(source_audit, nodes_by_id)
    edges = bounded.spanning_tree_edges(comp.node_key(0, 0, None), free_ids, nodes_by_id)
    segments = []
    for edge_index, (left_id, right_id) in enumerate(edges):
        left = refinement.angle_vector(tree, nodes_by_id[left_id])
        right = refinement.angle_vector(tree, nodes_by_id[right_id])
        original_delta = refinement.segment_delta(left, right)
        segment_count = max(1, math.ceil(original_delta["max_coordinate_degrees"] / MAX_COORDINATE_DELTA_DEGREES))
        previous = left
        previous_t = 0.0
        for step in range(1, segment_count + 1):
            current_t = float(step) / float(segment_count)
            current = (1.0 - current_t) * left + current_t * right
            segments.append(
                {
                    "source_edge_index": edge_index,
                    "source_node_ids": [left_id, right_id],
                    "refined_segment_index": len(segments),
                    "segment_index_within_source_edge": step - 1,
                    "source_edge_segment_count": segment_count,
                    "source_t_interval": [round(previous_t, 8), round(current_t, 8)],
                    "left_vector": previous,
                    "right_vector": current,
                    "delta": refinement.segment_delta(previous, current),
                }
            )
            previous = current
            previous_t = current_t
    return tree, segments


def degrees_from_vector(tree: dict, vector: np.ndarray) -> dict[str, float]:
    return {hinge_id: float(value) for hinge_id, value in zip(tree["hinge_ids"], vector)}


def piece_displacement_bounds_for_segment(
    case: dict,
    tree: dict,
    transforms: dict[str, dict[str, np.ndarray]],
    transformed_pieces: dict[str, list[np.ndarray]],
    delta_by_hinge: dict[str, float],
    paths_by_piece: dict[str, list[dict]],
) -> dict[str, float]:
    bounds = {}
    for piece_id, vertices in transformed_pieces.items():
        displacement = 0.0
        for hinge in paths_by_piece[piece_id]:
            hinge_id = hinge["hinge_id"]
            half_angle_radians = math.radians(abs(float(delta_by_hinge[hinge_id])) / 2.0)
            if half_angle_radians <= 0.0:
                continue
            axis_side = hinge["pieces"][0]
            transform = transforms[axis_side]
            axis_a = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][0]])
            axis_b = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][1]])
            max_distance = max(ray_guard.point_line_distance(vertex, axis_a, axis_b) for vertex in vertices)
            displacement += 2.0 * max_distance * math.sin(half_angle_radians / 2.0)
        bounds[piece_id] = ray_guard.DISPLACEMENT_SAFETY_FACTOR * displacement
    return bounds


def hinge_interval(left_degrees: dict[str, float], right_degrees: dict[str, float], hinge_id: str) -> list[float]:
    left = float(left_degrees[hinge_id])
    right = float(right_degrees[hinge_id])
    return [round(min(left, right), 8), round(max(left, right), 8)]


def selected_hinge_orientation_certificate(
    hinge: dict,
    left_degrees: dict[str, float],
    right_degrees: dict[str, float],
    center_sample_status: str,
) -> dict:
    interval = hinge_interval(left_degrees, right_degrees, hinge["hinge_id"])
    excludes_zero = interval[0] > 0.0 or interval[1] < 0.0
    within_half_turn = max(abs(interval[0]), abs(interval[1])) < 180.0
    certified = center_sample_status == "collision_free" and excludes_zero and within_half_turn
    return {
        "method": "selected_hinge_contact_orientation_on_edge_segment",
        "certified": certified,
        "hinge_id": hinge["hinge_id"],
        "signed_angle_interval_degrees": interval,
        "angle_interval_excludes_zero": excludes_zero,
        "angle_interval_within_open_half_turn": within_half_turn,
        "center_sample_status": center_sample_status,
    }


def compact_pair_record(record: dict) -> dict:
    return {
        "pair": record["pair"],
        "role": record["role"],
        "coverage_method": record["coverage_method"],
        "covered": record["covered"],
        "center_axis_overlap": round(record["center_axis_overlap"], 12),
        "guard_bound": round(record["guard_bound"], 12),
        "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
        "guard_margin": round(record["guard_margin"], 12),
        "orientation_certificate": record["orientation_certificate"],
    }


def audit_segment(
    case: dict,
    tree: dict,
    segment: dict,
    paths_by_piece: dict[str, list[dict]],
    contacts_by_pair: dict[tuple[str, str], dict],
    hinge_by_pair: dict[tuple[str, str], dict],
) -> dict:
    left_vector = segment["left_vector"]
    right_vector = segment["right_vector"]
    center_vector = (left_vector + right_vector) / 2.0
    left_degrees = degrees_from_vector(tree, left_vector)
    right_degrees = degrees_from_vector(tree, right_vector)
    center_degrees = degrees_from_vector(tree, center_vector)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    sample_status = lib.collision_report(transformed)["status"]
    displacement_bounds = piece_displacement_bounds_for_segment(
        case,
        tree,
        transforms,
        transformed,
        delta_by_hinge,
        paths_by_piece,
    )

    pair_records = []
    for left, right in itertools.combinations(sorted(transformed), 2):
        pair = tuple(sorted((left, right)))
        role = ray_guard.pair_role(case, tree, pair, contacts_by_pair)
        best = ray_guard.best_center_separating_axis(transformed[left], transformed[right])
        guard_bound = displacement_bounds[left] + displacement_bounds[right] + ray_guard.SAT_TOLERANCE
        post_guard = best["center_axis_overlap"] + guard_bound
        clearance_certified = sample_status == "collision_free" and post_guard <= ray_guard.SAT_TOLERANCE
        orientation = None
        orientation_certified = False
        if role == "selected_hinge_contact":
            orientation = selected_hinge_orientation_certificate(hinge_by_pair[pair], left_degrees, right_degrees, sample_status)
            orientation_certified = orientation["certified"]
        covered = bool(clearance_certified or orientation_certified)
        if clearance_certified:
            method = "clearance_interval_guard"
        elif orientation_certified:
            method = "selected_hinge_contact_orientation"
        elif role.startswith("residual_"):
            method = "unresolved_residual_contact_or_near_contact"
        else:
            method = "insufficient_clearance_interval_margin"
        pair_records.append(
            {
                "pair": list(pair),
                "role": role,
                "coverage_method": method,
                "covered": covered,
                "center_axis_overlap": best["center_axis_overlap"],
                "guard_bound": guard_bound,
                "post_guard_overlap_bound": post_guard,
                "guard_margin": ray_guard.SAT_TOLERANCE - post_guard,
                "orientation_certificate": orientation,
            }
        )

    covered_pair_count = sum(1 for record in pair_records if record["covered"])
    worst_margin = min(record["guard_margin"] for record in pair_records)
    return {
        "segment_id": f"seg_{segment['refined_segment_index']:05d}",
        "source_edge_index": segment["source_edge_index"],
        "source_node_ids": segment["source_node_ids"],
        "segment_index_within_source_edge": segment["segment_index_within_source_edge"],
        "source_edge_segment_count": segment["source_edge_segment_count"],
        "source_t_interval": segment["source_t_interval"],
        "delta": segment["delta"],
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "center_sample_status": sample_status,
        "pair_count": len(pair_records),
        "covered_pair_count": covered_pair_count,
        "uncovered_pair_count": len(pair_records) - covered_pair_count,
        "fully_interval_guard_certified": covered_pair_count == len(pair_records),
        "worst_pair_guard_margin": round(worst_margin, 12),
        "pair_records": pair_records,
    }


def audit_tree(case: dict, source_audit: dict, signs_by_tree: dict[str, dict[str, int]]) -> dict:
    tree, segments = refined_segments_for_tree(case, source_audit, signs_by_tree)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    contacts_by_pair = ray_guard.contact_by_pair(case)
    hinge_by_pair = selected_hinge_by_pair(case, tree)
    audited_segments = [audit_segment(case, tree, segment, paths_by_piece, contacts_by_pair, hinge_by_pair) for segment in segments]
    failed = [segment for segment in audited_segments if not segment["fully_interval_guard_certified"]]
    coverage_methods = Counter(
        record["coverage_method"]
        for segment in audited_segments
        for record in segment["pair_records"]
    )
    uncovered_by_role = Counter(
        record["role"]
        for segment in audited_segments
        for record in segment["pair_records"]
        if not record["covered"]
    )
    low_margin = sorted(audited_segments, key=lambda item: item["worst_pair_guard_margin"])[:MAX_STORED_LOW_MARGIN_SEGMENTS]
    return {
        "tree_id": source_audit["tree_id"],
        "class_id": source_audit["class_id"],
        "status": "refined_edge_interval_guard_probe_completed",
        "summary_metrics": {
            "refined_segment_count": len(audited_segments),
            "center_sample_collision_free_segment_count": sum(1 for item in audited_segments if item["center_sample_status"] == "collision_free"),
            "fully_interval_guard_certified_segment_count": len(audited_segments) - len(failed),
            "failed_interval_guard_segment_count": len(failed),
            "total_pair_segment_count": sum(item["pair_count"] for item in audited_segments),
            "covered_pair_segment_count": sum(item["covered_pair_count"] for item in audited_segments),
            "uncovered_pair_segment_count": sum(item["uncovered_pair_count"] for item in audited_segments),
            "minimum_worst_pair_guard_margin": min(item["worst_pair_guard_margin"] for item in audited_segments),
            "maximum_segment_coordinate_delta_degrees": max(item["delta"]["max_coordinate_degrees"] for item in audited_segments),
        },
        "coverage_methods": dict(sorted(coverage_methods.items())),
        "uncovered_by_role": dict(sorted(uncovered_by_role.items())),
        "stored_failed_segments": [
            {
                **{key: value for key, value in segment.items() if key != "pair_records"},
                "uncovered_pair_records": [compact_pair_record(record) for record in segment["pair_records"] if not record["covered"]],
            }
            for segment in failed[:MAX_STORED_FAILED_SEGMENTS]
        ],
        "stored_low_margin_segments": [
            {
                **{key: value for key, value in segment.items() if key != "pair_records"},
                "lowest_margin_pair_records": [
                    compact_pair_record(record)
                    for record in sorted(segment["pair_records"], key=lambda item: item["guard_margin"])[:3]
                ],
            }
            for segment in low_margin
        ],
    }


def build_report() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    signs_by_tree = comp.certified_signs_by_tree()
    source_by_tree = {audit["tree_id"]: audit for audit in component_report["representative_audits"]}
    tree_reports = [audit_tree(case, source_by_tree[tree_id], signs_by_tree) for tree_id in TARGET_TREE_IDS]
    return {
        "case_id": CASE_ID,
        "status": "refined_edge_interval_guard_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "target_tree_ids": TARGET_TREE_IDS,
        "interval_guard_protocol": {
            "segment_source": "refined BFS spanning-tree segments with max coordinate delta <= 5 degrees",
            "sat_tolerance": ray_guard.SAT_TOLERANCE,
            "displacement_safety_factor": ray_guard.DISPLACEMENT_SAFETY_FACTOR,
            "clearance_rule": "center separating-axis overlap plus local angular displacement bound must stay <= SAT tolerance",
            "selected_hinge_rule": "selected hinge angle interval must exclude zero and stay within an open half-turn",
        },
        "summary_metrics": {
            "tree_count": len(tree_reports),
            "total_refined_segment_count": sum(report["summary_metrics"]["refined_segment_count"] for report in tree_reports),
            "total_fully_interval_guard_certified_segment_count": sum(report["summary_metrics"]["fully_interval_guard_certified_segment_count"] for report in tree_reports),
            "total_failed_interval_guard_segment_count": sum(report["summary_metrics"]["failed_interval_guard_segment_count"] for report in tree_reports),
            "total_uncovered_pair_segment_count": sum(report["summary_metrics"]["uncovered_pair_segment_count"] for report in tree_reports),
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This is a conservative interval-guard probe, not exact symbolic interval rotation arithmetic.",
            "Only TREE_021 is targeted in this first probe.",
            "Residual or near-contact pairs may fail this guard even when sampled subdivision points are collision-free.",
            "The result does not cover physical hinge thickness, offsets, mesh export, or printability.",
        ],
    }


def main() -> int:
    report = build_report()
    lib.write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "summary_metrics": report["summary_metrics"],
                "tree_summaries": {
                    report["tree_id"]: report["summary_metrics"] for report in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())