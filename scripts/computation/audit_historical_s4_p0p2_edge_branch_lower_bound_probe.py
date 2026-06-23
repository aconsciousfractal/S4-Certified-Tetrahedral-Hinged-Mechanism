"""TREE_021 P0-P2 edge-edge branch lower-bound probe.

This audit targets the two dominant edge-edge separator branches observed for
uncovered TREE_021 P0-P2 residual shared-face failures:

- edge:M_AB-C x C-M_CD
- edge:C-M_CD x M_AB-C

For each parent segment assigned to one of those branches, the script subdivides
it to several max-coordinate widths and applies a conservative branch-specific
lower-bound guard:

    branch_midpoint_gap - local_displacement_bound > 0

This is a lower-bound probe, not a symbolic derivation. Passing subsegments are
certified by the same engineering displacement-bound discipline used elsewhere;
failing subsegments require either further subdivision or symbolic branch bounds.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_edge_branch_lower_bound_probe_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
TARGET_BRANCHES = [
    "edge:M_AB-C x C-M_CD",
    "edge:C-M_CD x M_AB-C",
]
REFINEMENT_MAX_COORDINATE_DEGREES = [5.0, 2.5, 1.25, 0.625]
BASE_MAX_COORDINATE_DELTA_DEGREES = 5.0
MAX_STORED_EXAMPLES = 60
SAT_TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402
import audit_historical_s4_bounded_component_edge_refinement as refinement  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as interval_probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def label_indices(case: dict) -> dict[str, dict[str, int]]:
    return {
        piece_id: {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(piece)
        }
        for piece_id, piece in case["pieces_by_id"].items()
    }


def point(pieces: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, label: str) -> np.ndarray:
    return pieces[piece_id][indices[piece_id][label]]


def branch_edges(branch_name: str) -> tuple[list[str], list[str]]:
    if branch_name == "edge:M_AB-C x C-M_CD":
        return ["M_AB", "C"], ["C", "M_CD"]
    if branch_name == "edge:C-M_CD x M_AB-C":
        return ["C", "M_CD"], ["M_AB", "C"]
    raise ValueError(f"Unsupported branch: {branch_name}")


def branch_overlap(
    pieces: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    branch_name: str,
) -> dict:
    left_labels, right_labels = branch_edges(branch_name)
    left_a = point(pieces, indices, TARGET_PAIR[0], left_labels[0])
    left_b = point(pieces, indices, TARGET_PAIR[0], left_labels[1])
    right_a = point(pieces, indices, TARGET_PAIR[1], right_labels[0])
    right_b = point(pieces, indices, TARGET_PAIR[1], right_labels[1])
    axis = np.cross(left_b - left_a, right_b - right_a)
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm <= lib.TOL:
        return {
            "axis_norm": axis_norm,
            "center_axis_overlap": None,
            "branch_gap": None,
        }
    unit = axis / axis_norm
    left_values = [float(np.dot(vertex, unit)) for vertex in pieces[TARGET_PAIR[0]]]
    right_values = [float(np.dot(vertex, unit)) for vertex in pieces[TARGET_PAIR[1]]]
    overlap = min(max(left_values), max(right_values)) - max(min(left_values), min(right_values))
    return {
        "axis_norm": axis_norm,
        "center_axis_overlap": float(overlap),
        "branch_gap": max(0.0, -float(overlap)),
    }


def vector_to_degrees(tree: dict, vector: np.ndarray) -> dict[str, float]:
    return {hinge_id: float(value) for hinge_id, value in zip(tree["hinge_ids"], vector)}


def segment_delta(left: np.ndarray, right: np.ndarray) -> dict:
    deltas = right - left
    return {
        "euclidean_degrees": round(float(np.linalg.norm(deltas)), 12),
        "max_coordinate_degrees": round(float(np.max(np.abs(deltas))), 12),
    }


def midpoint_context(case: dict, tree: dict, indices: dict, paths_by_piece: dict, left: np.ndarray, right: np.ndarray, branch_name: str) -> dict:
    center = (left + right) / 2.0
    left_degrees = vector_to_degrees(tree, left)
    right_degrees = vector_to_degrees(tree, right)
    center_degrees = vector_to_degrees(tree, center)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    displacement = interval_probe.piece_displacement_bounds_for_segment(
        case,
        tree,
        transforms,
        transformed,
        delta_by_hinge,
        paths_by_piece,
    )
    overlap = branch_overlap(transformed, indices, branch_name)
    guard_bound = displacement[TARGET_PAIR[0]] + displacement[TARGET_PAIR[1]] + SAT_TOLERANCE
    center_axis_overlap = overlap["center_axis_overlap"]
    if center_axis_overlap is None:
        branch_margin = None
        certified = False
    else:
        branch_margin = (-center_axis_overlap) - guard_bound
        certified = branch_margin >= 0.0
    labels_by_piece = classify.labels_by_piece(case)
    best = classify.best_named_axis(
        transformed[TARGET_PAIR[0]],
        transformed[TARGET_PAIR[1]],
        labels_by_piece[TARGET_PAIR[0]],
        labels_by_piece[TARGET_PAIR[1]],
    )
    return {
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "branch_name": branch_name,
        "best_axis_name": best["axis_name"],
        "best_axis_is_assigned_branch": best["axis_name"] == branch_name,
        "best_axis_in_target_branch_family": best["axis_name"] in TARGET_BRANCHES,
        "axis_norm": None if overlap["axis_norm"] is None else round(overlap["axis_norm"], 12),
        "center_axis_overlap": None if center_axis_overlap is None else round(center_axis_overlap, 12),
        "branch_gap": None if overlap["branch_gap"] is None else round(overlap["branch_gap"], 12),
        "guard_bound": round(guard_bound, 12),
        "branch_lower_bound_margin": None if branch_margin is None else round(branch_margin, 12),
        "branch_lower_bound_certified": certified,
    }


def source_segments(case: dict, tree: dict, signs_by_tree: dict[str, dict[str, int]]) -> list[dict]:
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    _tree, segments = interval_probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    return segments


def parent_branch_segments(case: dict, tree: dict, indices: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]]) -> list[dict]:
    labels_by_piece = classify.labels_by_piece(case)
    output = []
    for segment in source_segments(case, tree, signs_by_tree):
        center = (segment["left_vector"] + segment["right_vector"]) / 2.0
        center_degrees = vector_to_degrees(tree, center)
        left_degrees = vector_to_degrees(tree, segment["left_vector"])
        right_degrees = vector_to_degrees(tree, segment["right_vector"])
        delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
        transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        best = classify.best_named_axis(
            transformed[TARGET_PAIR[0]],
            transformed[TARGET_PAIR[1]],
            labels_by_piece[TARGET_PAIR[0]],
            labels_by_piece[TARGET_PAIR[1]],
        )
        if best["axis_name"] not in TARGET_BRANCHES:
            continue
        displacement = interval_probe.piece_displacement_bounds_for_segment(
            case,
            tree,
            transforms,
            transformed,
            delta_by_hinge,
            paths_by_piece,
        )
        guard_bound = displacement[TARGET_PAIR[0]] + displacement[TARGET_PAIR[1]] + SAT_TOLERANCE
        post_guard = best["center_axis_overlap"] + guard_bound
        if post_guard <= SAT_TOLERANCE:
            continue
        output.append({**segment, "assigned_branch_name": best["axis_name"], "parent_center_axis_overlap": best["center_axis_overlap"]})
    return output


def subdivide_segment(segment: dict, max_coordinate_delta: float) -> list[tuple[np.ndarray, np.ndarray]]:
    left = segment["left_vector"]
    right = segment["right_vector"]
    delta = segment_delta(left, right)
    count = max(1, math.ceil(delta["max_coordinate_degrees"] / max_coordinate_delta))
    subsegments = []
    previous = left
    for step in range(1, count + 1):
        t = float(step) / float(count)
        current = (1.0 - t) * left + t * right
        subsegments.append((previous, current))
        previous = current
    return subsegments


def compact_example(parent: dict, sub_index: int, left: np.ndarray, right: np.ndarray, context: dict, delta: dict) -> dict:
    return {
        "parent_segment_id": f"seg_{parent['refined_segment_index']:05d}",
        "source_edge_index": parent["source_edge_index"],
        "source_node_ids": parent["source_node_ids"],
        "assigned_branch_name": parent["assigned_branch_name"],
        "subsegment_index": sub_index,
        "delta": delta,
        **context,
    }


def audit_threshold(case: dict, tree: dict, indices: dict, paths_by_piece: dict, parents: list[dict], max_coordinate_delta: float) -> dict:
    branch_counts = Counter()
    certified_by_branch = Counter()
    best_axis_counts = Counter()
    positive_gap_count = 0
    certified_count = 0
    subsegment_count = 0
    margins = []
    gaps = []
    stored_failures = []
    stored_successes = []
    for parent in parents:
        for sub_index, (left, right) in enumerate(subdivide_segment(parent, max_coordinate_delta)):
            subsegment_count += 1
            branch = parent["assigned_branch_name"]
            branch_counts[branch] += 1
            delta = segment_delta(left, right)
            context = midpoint_context(case, tree, indices, paths_by_piece, left, right, branch)
            best_axis_counts[context["best_axis_name"]] += 1
            if context["branch_gap"] is not None:
                gaps.append(context["branch_gap"])
                if context["branch_gap"] > 0.0:
                    positive_gap_count += 1
            if context["branch_lower_bound_margin"] is not None:
                margins.append(context["branch_lower_bound_margin"])
            if context["branch_lower_bound_certified"]:
                certified_count += 1
                certified_by_branch[branch] += 1
                if len(stored_successes) < MAX_STORED_EXAMPLES:
                    stored_successes.append(compact_example(parent, sub_index, left, right, context, delta))
            elif len(stored_failures) < MAX_STORED_EXAMPLES:
                stored_failures.append(compact_example(parent, sub_index, left, right, context, delta))
    return {
        "max_coordinate_delta_degrees": max_coordinate_delta,
        "parent_segment_count": len(parents),
        "subsegment_count": subsegment_count,
        "branch_assignment_counts": dict(branch_counts.most_common()),
        "best_axis_counts_at_subsegment_midpoints": dict(best_axis_counts.most_common()),
        "positive_branch_gap_subsegment_count": positive_gap_count,
        "branch_lower_bound_certified_subsegment_count": certified_count,
        "branch_lower_bound_failed_subsegment_count": subsegment_count - certified_count,
        "branch_lower_bound_certified_by_branch": dict(certified_by_branch.most_common()),
        "branch_gap_interval": [None, None] if not gaps else [round(min(gaps), 12), round(max(gaps), 12)],
        "branch_lower_bound_margin_interval": [None, None] if not margins else [round(min(margins), 12), round(max(margins), 12)],
        "stored_certified_examples": stored_successes,
        "stored_failed_examples": stored_failures,
    }


def build_report() -> dict:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    indices = label_indices(case)
    parents = parent_branch_segments(case, tree, indices, paths_by_piece, signs_by_tree)
    threshold_reports = [audit_threshold(case, tree, indices, paths_by_piece, parents, threshold) for threshold in REFINEMENT_MAX_COORDINATE_DEGREES]
    return {
        "case_id": CASE_ID,
        "status": "p0p2_edge_branch_lower_bound_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/refined_edge_interval_guard_probe_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "target_branches": TARGET_BRANCHES,
        "lower_bound_rule": "branch_gap_at_subsegment_midpoint - local_displacement_bound; pass when positive",
        "summary_metrics": {
            "parent_uncovered_edge_branch_segment_count": len(parents),
            "threshold_count": len(threshold_reports),
            "best_threshold_by_certified_count": max(threshold_reports, key=lambda item: item["branch_lower_bound_certified_subsegment_count"])["max_coordinate_delta_degrees"] if threshold_reports else None,
            "max_certified_subsegment_count": max((item["branch_lower_bound_certified_subsegment_count"] for item in threshold_reports), default=0),
        },
        "threshold_reports": threshold_reports,
        "limitations": [
            "This is a conservative numeric lower-bound probe, not a symbolic branch formula derivation.",
            "Only parent segments whose P0-P2 midpoint best separator is one of the two target edge-edge branches are included.",
            "The lower bound uses a midpoint branch separator and a local displacement bound; failing subsegments may still be collision-free.",
            "Face-normal P0-P2 branches and residual shared-edge pairs are not handled by this report.",
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
                "threshold_summary": {
                    str(item["max_coordinate_delta_degrees"]): {
                        "subsegments": item["subsegment_count"],
                        "positive_gap": item["positive_branch_gap_subsegment_count"],
                        "certified": item["branch_lower_bound_certified_subsegment_count"],
                        "failed": item["branch_lower_bound_failed_subsegment_count"],
                    }
                    for item in report["threshold_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())