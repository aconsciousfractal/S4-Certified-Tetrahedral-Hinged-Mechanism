"""TREE_007 P2-P3 edge-edge branch lower-bound probe.

This audit targets the two edge-edge separator branches in the TREE_007 P2-P3
residual shared-face backlog:

- edge:B-M_AB x B-M_CD
- edge:B-M_CD x B-M_AB

For each parent segment still uncovered by the TREE_007 refined-edge interval
guard and assigned to one of those branches, the script subdivides it to several
max-coordinate widths and applies a conservative branch-specific lower-bound
guard:

    branch_midpoint_gap - local_displacement_bound > 0

This is a finite lower-bound probe. It does not handle the P2-P3 face-normal
backlog and it is not a symbolic branch formula derivation.
"""

from __future__ import annotations

from collections import Counter
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_p2p3_edge_branch_lower_bound_probe_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIR = ("P2", "P3")
TARGET_BRANCHES = [
    "edge:B-M_AB x B-M_CD",
    "edge:B-M_CD x B-M_AB",
]
REFINEMENT_MAX_COORDINATE_DEGREES = [5.0, 2.5, 1.25, 0.625]
MAX_STORED_EXAMPLES = 60
SAT_TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as interval_probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def interval(values: list[float]) -> list[float | None]:
    if not values:
        return [None, None]
    return [rounded(min(values)), rounded(max(values))]


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
    if branch_name == "edge:B-M_AB x B-M_CD":
        return ["B", "M_AB"], ["B", "M_CD"]
    if branch_name == "edge:B-M_CD x B-M_AB":
        return ["B", "M_CD"], ["B", "M_AB"]
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
        "euclidean_degrees": rounded(float(np.linalg.norm(deltas))),
        "max_coordinate_degrees": rounded(float(np.max(np.abs(deltas)))),
    }


def source_segments(case: dict, signs_by_tree: dict[str, dict[str, int]]) -> list[dict]:
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    _tree, segments = interval_probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    return segments


def classification_p2p3_report() -> dict:
    report = load_json(RESULTS_DIR / "tree007_residual_contact_failure_classification_report.json")
    for pair_report in report["pair_reports"]:
        if tuple(pair_report["pair"]) == TARGET_PAIR:
            return pair_report
    raise RuntimeError("P2-P3 pair report not found in TREE_007 classification")


def parent_branch_segments(case: dict, tree: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]]) -> list[dict]:
    labels_by_piece = classify.labels_by_piece(case)
    output = []
    for segment in source_segments(case, signs_by_tree):
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
        output.append(
            {
                **segment,
                "assigned_branch_name": best["axis_name"],
                "parent_center_axis_overlap": best["center_axis_overlap"],
                "parent_guard_bound": guard_bound,
                "parent_guard_margin": SAT_TOLERANCE - post_guard,
            }
        )
    return output


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
        "axis_norm": rounded(overlap["axis_norm"]),
        "center_axis_overlap": rounded(center_axis_overlap),
        "branch_gap": rounded(overlap["branch_gap"]),
        "guard_bound": rounded(guard_bound),
        "branch_lower_bound_margin": rounded(branch_margin),
        "branch_lower_bound_certified": certified,
    }


def subdivide_segment(segment: dict, max_coordinate_delta: float) -> list[tuple[np.ndarray, np.ndarray]]:
    left = segment["left_vector"]
    right = segment["right_vector"]
    delta = segment_delta(left, right)
    count = max(1, math.ceil(float(delta["max_coordinate_degrees"]) / max_coordinate_delta))
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
        "source_t_interval": parent["source_t_interval"],
        "assigned_branch_name": parent["assigned_branch_name"],
        "parent_guard_margin": rounded(parent["parent_guard_margin"]),
        "subsegment_index": sub_index,
        "delta": delta,
        **context,
    }


def audit_threshold(case: dict, tree: dict, indices: dict, paths_by_piece: dict, parents: list[dict], max_coordinate_delta: float) -> dict:
    branch_counts = Counter()
    certified_by_branch = Counter()
    failed_by_branch = Counter()
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
            else:
                failed_by_branch[branch] += 1
                if len(stored_failures) < MAX_STORED_EXAMPLES:
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
        "branch_lower_bound_failed_by_branch": dict(failed_by_branch.most_common()),
        "branch_gap_interval": interval(gaps),
        "branch_lower_bound_margin_interval": interval(margins),
        "stored_certified_examples": stored_successes,
        "stored_failed_examples": stored_failures,
    }


def build_report() -> dict:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    indices = label_indices(case)
    parents = parent_branch_segments(case, tree, paths_by_piece, signs_by_tree)
    parent_branch_counts = Counter(parent["assigned_branch_name"] for parent in parents)
    classification_report = classification_p2p3_report()
    threshold_reports = [
        audit_threshold(case, tree, indices, paths_by_piece, parents, threshold)
        for threshold in REFINEMENT_MAX_COORDINATE_DEGREES
    ]
    max_certified = max((item["branch_lower_bound_certified_subsegment_count"] for item in threshold_reports), default=0)
    best_thresholds = [
        item["max_coordinate_delta_degrees"]
        for item in threshold_reports
        if item["branch_lower_bound_certified_subsegment_count"] == max_certified
    ]
    return {
        "case_id": CASE_ID,
        "status": "tree007_p2p3_edge_branch_lower_bound_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/tree007_residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/tree007_refined_edge_interval_guard_probe_report.json",
            f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_face",
            "branches": TARGET_BRANCHES,
        },
        "classification_uncovered_axis_name_counts": classification_report["uncovered_axis_name_counts"],
        "lower_bound_rule": "branch_gap_at_subsegment_midpoint - local_displacement_bound; pass when nonnegative",
        "summary_metrics": {
            "parent_uncovered_edge_branch_segment_count": len(parents),
            "parent_uncovered_edge_branch_counts": dict(parent_branch_counts.most_common()),
            "threshold_count": len(threshold_reports),
            "best_thresholds_by_certified_count": best_thresholds,
            "max_certified_subsegment_count": max_certified,
            "max_threshold_subsegment_count": max((item["subsegment_count"] for item in threshold_reports), default=0),
            "edge_branch_backlog_closed_by_probe": bool(threshold_reports)
            and any(item["branch_lower_bound_failed_subsegment_count"] == 0 for item in threshold_reports),
        },
        "threshold_reports": threshold_reports,
        "limitations": [
            "This is a conservative numeric lower-bound probe, not a symbolic branch formula derivation.",
            "Only original TREE_007 P2-P3 residual parent segments assigned to the two target edge-edge branches are included.",
            "The P2-P3 face-normal branches left_face:B-M_AB-M_CD and right_face:B-M_AB-M_CD are outside this report.",
            "Failing subsegments may still be collision-free; they only fail this midpoint branch lower-bound guard.",
            "The result does not certify theta=0, the full continuous 3-parameter component, physical hinge thickness, offsets, mesh export, or printability.",
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