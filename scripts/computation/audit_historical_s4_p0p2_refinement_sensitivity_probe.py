"""TREE_021 P0-P2 same-branch refinement-sensitivity probe.

The same-branch support-bound probe left 1013 residual same-assigned edge-edge
subsegments at max coordinate delta 0.625 degrees. This script subdivides only
those residual subsegments and reruns the fixed-axis stable-support guard at
0.3125 and 0.15625 max coordinate degrees.

This is a tactical sensitivity probe: it estimates whether subdivision is still
productive before deriving a projection-component displacement formula.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_refinement_sensitivity_probe_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
BASE_MAX_COORDINATE_DELTA_DEGREES = 0.625
REFINEMENT_THRESHOLDS = [0.3125, 0.15625]
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 24

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_failure_classification as failure_classification  # noqa: E402
import audit_historical_s4_p0p2_same_branch_support_bound_probe as support_probe  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    if math.isinf(float(value)):
        return float(value)
    return round(float(value), digits)


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {key: None for key in ["min", "p05", "p10", "p25", "p50", "p75", "p90", "p95", "max"]}
    ordered = sorted(values)
    n = len(ordered)

    def q(percent: float) -> float:
        if n == 1:
            return ordered[0]
        position = percent * (n - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "min": rounded(ordered[0]),
        "p05": rounded(q(0.05)),
        "p10": rounded(q(0.10)),
        "p25": rounded(q(0.25)),
        "p50": rounded(q(0.50)),
        "p75": rounded(q(0.75)),
        "p90": rounded(q(0.90)),
        "p95": rounded(q(0.95)),
        "max": rounded(ordered[-1]),
    }


def vector_to_degrees(tree: dict, vector: np.ndarray) -> dict[str, float]:
    return {hinge_id: float(value) for hinge_id, value in zip(tree["hinge_ids"], vector)}


def subdivide_vector_segment(left: np.ndarray, right: np.ndarray, max_coordinate_delta: float) -> list[tuple[np.ndarray, np.ndarray]]:
    delta = branch_probe.segment_delta(left, right)
    count = max(1, math.ceil(delta["max_coordinate_degrees"] / max_coordinate_delta))
    subsegments = []
    previous = left
    for step in range(1, count + 1):
        t = float(step) / float(count)
        current = (1.0 - t) * left + t * right
        subsegments.append((previous, current))
        previous = current
    return subsegments


def piece_label_sets(labels_by_piece: dict[str, list[str]], piece_id: str, support_labels: list[str]) -> tuple[list[str], list[str]]:
    support = list(support_labels)
    support_set = set(support)
    non_support = [label for label in labels_by_piece[piece_id] if label not in support_set]
    return support, non_support


def support_guard_from_transformed(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    transforms: dict[str, dict[str, np.ndarray]],
    transformed: dict[str, list[np.ndarray]],
    delta_by_hinge: dict[str, float],
    branch_name: str,
    branch_gap: float,
) -> dict:
    unit = support_probe.branch_axis_unit(transformed, indices, branch_name)
    state = support_probe.support_state(transformed, labels_by_piece, unit)
    if not state["separated_at_center"]:
        return {
            **state,
            "support_only_certified": False,
            "stable_support_certified": False,
            "extrema_stable": False,
        }

    lower_support, lower_non_support = piece_label_sets(labels_by_piece, state["lower_piece"], state["lower_support_labels"])
    upper_support, upper_non_support = piece_label_sets(labels_by_piece, state["upper_piece"], state["upper_support_labels"])

    lower_support_bound = support_probe.displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        support_probe.vertices_for_labels(transformed, indices, state["lower_piece"], lower_support),
        state["lower_piece"],
    )
    upper_support_bound = support_probe.displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        support_probe.vertices_for_labels(transformed, indices, state["upper_piece"], upper_support),
        state["upper_piece"],
    )
    lower_non_support_bound = support_probe.displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        support_probe.vertices_for_labels(transformed, indices, state["lower_piece"], lower_non_support),
        state["lower_piece"],
    )
    upper_non_support_bound = support_probe.displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        support_probe.vertices_for_labels(transformed, indices, state["upper_piece"], upper_non_support),
        state["upper_piece"],
    )

    support_guard_bound = lower_support_bound + upper_support_bound + SAT_TOLERANCE
    support_margin = float(branch_gap) - support_guard_bound
    lower_stability_margin = float(state["lower_competition_margin"]) - lower_support_bound - lower_non_support_bound - SAT_TOLERANCE
    upper_stability_margin = float(state["upper_competition_margin"]) - upper_support_bound - upper_non_support_bound - SAT_TOLERANCE
    extrema_stable = lower_stability_margin >= 0.0 and upper_stability_margin >= 0.0
    support_only_certified = support_margin >= 0.0
    stable_support_certified = support_only_certified and extrema_stable

    return {
        **state,
        "support_guard_bound": rounded(support_guard_bound),
        "support_margin": rounded(support_margin),
        "lower_support_bound": rounded(lower_support_bound),
        "upper_support_bound": rounded(upper_support_bound),
        "lower_non_support_bound": rounded(lower_non_support_bound),
        "upper_non_support_bound": rounded(upper_non_support_bound),
        "lower_stability_margin": rounded(lower_stability_margin),
        "upper_stability_margin": rounded(upper_stability_margin),
        "minimum_stability_margin": rounded(min(lower_stability_margin, upper_stability_margin)),
        "extrema_stable": extrema_stable,
        "support_only_certified": support_only_certified,
        "stable_support_certified": stable_support_certified,
    }


def evaluate_segment(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    left: np.ndarray,
    right: np.ndarray,
    branch_name: str,
) -> dict:
    center = (left + right) / 2.0
    left_degrees = vector_to_degrees(tree, left)
    right_degrees = vector_to_degrees(tree, right)
    center_degrees = vector_to_degrees(tree, center)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = branch_probe.ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    branch_overlap = branch_probe.branch_overlap(transformed, indices, branch_name)
    branch_gap = branch_overlap["branch_gap"]
    if branch_gap is None:
        branch_gap = 0.0

    displacement = branch_probe.interval_probe.piece_displacement_bounds_for_segment(
        case,
        tree,
        transforms,
        transformed,
        delta_by_hinge,
        paths_by_piece,
    )
    whole_piece_guard_bound = displacement[TARGET_PAIR[0]] + displacement[TARGET_PAIR[1]] + SAT_TOLERANCE
    whole_piece_margin = float(branch_gap) - whole_piece_guard_bound

    best = branch_probe.classify.best_named_axis(
        transformed[TARGET_PAIR[0]],
        transformed[TARGET_PAIR[1]],
        labels_by_piece[TARGET_PAIR[0]],
        labels_by_piece[TARGET_PAIR[1]],
    )
    relation = failure_classification.axis_relation({"best_axis_name": best["axis_name"]}, branch_name)
    support = support_guard_from_transformed(
        case,
        tree,
        indices,
        labels_by_piece,
        paths_by_piece,
        transforms,
        transformed,
        delta_by_hinge,
        branch_name,
        float(branch_gap),
    )
    guard_improvement_factor = None
    if support.get("support_guard_bound") and support["support_guard_bound"] > 0.0:
        guard_improvement_factor = whole_piece_guard_bound / float(support["support_guard_bound"])

    return {
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "delta": branch_probe.segment_delta(left, right),
        "branch_name": branch_name,
        "best_axis_name": best["axis_name"],
        "axis_relation": relation,
        "branch_gap": rounded(branch_gap),
        "whole_piece_guard_bound": rounded(whole_piece_guard_bound),
        "whole_piece_margin": rounded(whole_piece_margin),
        "whole_piece_branch_certified": whole_piece_margin >= 0.0,
        "support": support,
        "guard_improvement_factor": rounded(guard_improvement_factor, 6),
    }


def compact_record(base: dict, threshold: float, child_index: int, eval_record: dict) -> dict:
    support = eval_record["support"]
    return {
        "base_parent_segment_id": base["parent_segment_id"],
        "base_subsegment_index": base["base_subsegment_index"],
        "source_edge_index": base["source_edge_index"],
        "source_node_ids": base["source_node_ids"],
        "assigned_branch_name": base["assigned_branch_name"],
        "refinement_threshold_degrees": threshold,
        "child_subsegment_index": child_index,
        "delta": eval_record["delta"],
        "center_angle_degrees_by_hinge": eval_record["center_angle_degrees_by_hinge"],
        "best_axis_name": eval_record["best_axis_name"],
        "axis_relation": eval_record["axis_relation"],
        "branch_gap": eval_record["branch_gap"],
        "whole_piece_guard_bound": eval_record["whole_piece_guard_bound"],
        "whole_piece_margin": eval_record["whole_piece_margin"],
        "whole_piece_branch_certified": eval_record["whole_piece_branch_certified"],
        "support_guard_bound": support.get("support_guard_bound"),
        "support_margin": support.get("support_margin"),
        "minimum_stability_margin": support.get("minimum_stability_margin"),
        "extrema_stable": support.get("extrema_stable"),
        "stable_support_certified": support.get("stable_support_certified"),
        "guard_improvement_factor": eval_record.get("guard_improvement_factor"),
    }


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def residual_base_subsegments(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]]) -> list[dict]:
    parents = branch_probe.parent_branch_segments(case, tree, indices, paths_by_piece, signs_by_tree)
    residuals = []
    base_counters = Counter()
    for parent in parents:
        branch = parent["assigned_branch_name"]
        for sub_index, (left, right) in enumerate(branch_probe.subdivide_segment(parent, BASE_MAX_COORDINATE_DELTA_DEGREES)):
            evaluation = evaluate_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            if evaluation["whole_piece_branch_certified"]:
                base_counters["whole_piece_certified"] += 1
                continue
            if evaluation["axis_relation"] != "same_assigned_edge_branch":
                base_counters[evaluation["axis_relation"]] += 1
                continue
            if evaluation["support"].get("stable_support_certified"):
                base_counters["stable_support_certified"] += 1
                continue
            base_counters["residual_same_branch"] += 1
            residuals.append(
                {
                    "parent_segment_id": f"seg_{parent['refined_segment_index']:05d}",
                    "source_edge_index": parent["source_edge_index"],
                    "source_node_ids": parent["source_node_ids"],
                    "assigned_branch_name": branch,
                    "base_subsegment_index": sub_index,
                    "left_vector": left,
                    "right_vector": right,
                    "base_evaluation": evaluation,
                }
            )
    return residuals, base_counters


def audit_threshold(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    residuals: list[dict],
    threshold: float,
) -> dict:
    counters = Counter()
    base_outcome_counts = Counter()
    assigned_branch_counts = Counter()
    axis_relation_counts = Counter()
    best_axis_counts = Counter()
    remaining_reason_counts = Counter()
    support_margins = []
    stability_margins = []
    branch_gaps = []
    improvement_factors = []
    examples = defaultdict(list)

    for base in residuals:
        branch = base["assigned_branch_name"]
        child_total = 0
        child_covered = 0
        child_axis_switch_uncovered = 0
        child_same_branch_margin_uncovered = 0
        child_same_branch_unstable_uncovered = 0
        child_whole_piece = 0
        child_stable_support = 0
        for child_index, (left, right) in enumerate(subdivide_vector_segment(base["left_vector"], base["right_vector"], threshold)):
            child_total += 1
            counters["refined_subsegment_count"] += 1
            assigned_branch_counts[branch] += 1
            evaluation = evaluate_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            support = evaluation["support"]
            relation = evaluation["axis_relation"]
            axis_relation_counts[relation] += 1
            best_axis_counts[evaluation["best_axis_name"]] += 1
            if evaluation["branch_gap"] is not None:
                branch_gaps.append(float(evaluation["branch_gap"]))
            if support.get("support_margin") is not None:
                support_margins.append(float(support["support_margin"]))
            if support.get("minimum_stability_margin") is not None:
                stability_margins.append(float(support["minimum_stability_margin"]))
            if evaluation.get("guard_improvement_factor") is not None:
                improvement_factors.append(float(evaluation["guard_improvement_factor"]))

            whole_piece = bool(evaluation["whole_piece_branch_certified"])
            stable_support = relation == "same_assigned_edge_branch" and bool(support.get("stable_support_certified"))
            if whole_piece:
                counters["whole_piece_branch_certified_count"] += 1
                child_whole_piece += 1
                add_example(examples["whole_piece_branch_certified"], compact_record(base, threshold, child_index, evaluation))
            if stable_support:
                counters["stable_support_certified_count"] += 1
                child_stable_support += 1
                add_example(examples["stable_support_certified"], compact_record(base, threshold, child_index, evaluation))
            if stable_support and not whole_piece:
                counters["stable_support_only_certified_count"] += 1
            if whole_piece or stable_support:
                counters["combined_certified_count"] += 1
                child_covered += 1
                continue

            if relation != "same_assigned_edge_branch":
                counters["uncovered_axis_switch_count"] += 1
                child_axis_switch_uncovered += 1
                remaining_reason_counts[f"axis_switch:{relation}"] += 1
                add_example(examples["uncovered_axis_switch"], compact_record(base, threshold, child_index, evaluation))
            elif not support.get("extrema_stable"):
                counters["uncovered_same_branch_unstable_count"] += 1
                child_same_branch_unstable_uncovered += 1
                remaining_reason_counts["same_branch_support_margin_failed_and_extrema_unstable"] += 1
                add_example(examples["uncovered_same_branch_unstable"], compact_record(base, threshold, child_index, evaluation))
            else:
                counters["uncovered_same_branch_margin_count"] += 1
                child_same_branch_margin_uncovered += 1
                remaining_reason_counts["same_branch_support_margin_failed"] += 1
                add_example(examples["uncovered_same_branch_margin"], compact_record(base, threshold, child_index, evaluation))

        if child_covered == child_total:
            base_outcome_counts["fully_combined_certified_base_count"] += 1
        elif child_covered == 0:
            base_outcome_counts["zero_child_certified_base_count"] += 1
        else:
            base_outcome_counts["partially_combined_certified_base_count"] += 1
        if child_axis_switch_uncovered:
            base_outcome_counts["base_with_uncovered_axis_switch_child_count"] += 1
        if child_same_branch_margin_uncovered:
            base_outcome_counts["base_with_uncovered_same_branch_margin_child_count"] += 1
        if child_same_branch_unstable_uncovered:
            base_outcome_counts["base_with_uncovered_same_branch_unstable_child_count"] += 1
        if child_whole_piece:
            base_outcome_counts["base_with_whole_piece_certified_child_count"] += 1
        if child_stable_support:
            base_outcome_counts["base_with_stable_support_certified_child_count"] += 1

    counters["combined_uncovered_count"] = counters["refined_subsegment_count"] - counters["combined_certified_count"]
    return {
        "max_coordinate_delta_degrees": threshold,
        "summary_counts": dict(counters),
        "base_outcome_counts": dict(base_outcome_counts),
        "assigned_branch_counts": dict(assigned_branch_counts.most_common()),
        "axis_relation_counts": dict(axis_relation_counts.most_common()),
        "best_axis_counts": dict(best_axis_counts.most_common()),
        "remaining_reason_counts": dict(remaining_reason_counts.most_common()),
        "quantiles": {
            "branch_gaps": quantiles(branch_gaps),
            "support_margins": quantiles(support_margins),
            "minimum_stability_margins": quantiles(stability_margins),
            "guard_improvement_factors": quantiles(improvement_factors),
        },
        "examples": dict(examples),
    }

def build_report() -> dict:
    case = branch_probe.batch.build_case()
    tree = branch_probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = branch_probe.comp.certified_signs_by_tree()
    paths_by_piece = branch_probe.ray_guard.tree_paths_from_root(case, tree)
    indices = branch_probe.label_indices(case)
    labels_by_piece = branch_probe.classify.labels_by_piece(case)
    residuals, base_counters = residual_base_subsegments(case, tree, indices, labels_by_piece, paths_by_piece, signs_by_tree)
    threshold_reports = [
        audit_threshold(case, tree, indices, labels_by_piece, paths_by_piece, residuals, threshold)
        for threshold in REFINEMENT_THRESHOLDS
    ]
    return {
        "case_id": CASE_ID,
        "status": "p0p2_refinement_sensitivity_probe_completed",
        "source_report": f"results/{CASE_ID}/p0p2_same_branch_support_bound_probe_report.json",
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "base_max_coordinate_delta_degrees": BASE_MAX_COORDINATE_DELTA_DEGREES,
        "refinement_thresholds_degrees": REFINEMENT_THRESHOLDS,
        "base_residual_selection_counts": dict(base_counters),
        "base_residual_same_branch_count": len(residuals),
        "threshold_reports": threshold_reports,
        "summary_metrics": {
            "base_residual_same_branch_count": len(residuals),
            "best_threshold_by_combined_coverage": max(
                threshold_reports,
                key=lambda item: item["summary_counts"].get("combined_certified_count", 0),
            )["max_coordinate_delta_degrees"] if threshold_reports else None,
            "best_combined_certified_count": max(
                (item["summary_counts"].get("combined_certified_count", 0) for item in threshold_reports),
                default=0,
            ),
        },
        "limitations": [
            "This is finite numeric refinement-sensitivity evidence, not a symbolic projection-bound derivation.",
            "The probe starts from the 1013 residual same-branch cases left by the stable-support guard at 0.625 degrees.",
            "Axis-switch children are recorded but not certified by the same-branch stable-support guard unless the whole-piece branch guard passes.",
            "The report does not cover P0-P2 face-normal switch cases from the previous classification, residual shared-edge pairs, TREE_007, or physical hinge thickness/clearance.",
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
                "base_residual_selection_counts": report["base_residual_selection_counts"],
                "threshold_summary": {
                    str(item["max_coordinate_delta_degrees"]): item["summary_counts"]
                    for item in report["threshold_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())