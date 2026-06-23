"""TREE_007 P2-P3 edge-edge branch refinement-sensitivity probe.

The support-bound probe left 1125 edge-branch leaf subsegments at max coordinate
delta 0.625 degrees. This script subdivides only those residual leaves and
reruns the combined guard at 0.3125 and 0.15625 max coordinate degrees:

    whole-piece branch lower-bound OR fixed-axis stable_support

This is a tactical sensitivity probe. It measures whether targeted subdivision
is still productive before introducing a P2-P3 projection-component formula.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_p2p3_edge_branch_refinement_sensitivity_probe_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIR = ("P2", "P3")
BASE_MAX_COORDINATE_DELTA_DEGREES = 0.625
REFINEMENT_THRESHOLDS = [0.3125, 0.15625]
MAX_STORED_EXAMPLES = 48

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_tree007_p2p3_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_tree007_p2p3_edge_branch_support_bound_probe as support_probe  # noqa: E402

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


def subdivide_vector_segment(left: np.ndarray, right: np.ndarray, max_coordinate_delta: float) -> list[tuple[np.ndarray, np.ndarray]]:
    delta = branch_probe.segment_delta(left, right)
    count = max(1, math.ceil(float(delta["max_coordinate_degrees"]) / max_coordinate_delta))
    subsegments = []
    previous = left
    for step in range(1, count + 1):
        t = float(step) / float(count)
        current = (1.0 - t) * left + t * right
        subsegments.append((previous, current))
        previous = current
    return subsegments


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
    context = branch_probe.midpoint_context(case, tree, indices, paths_by_piece, left, right, branch_name)
    relation = support_probe.axis_relation(context, branch_name)
    support = support_probe.evaluate_support_guard(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch_name, context)
    combined_certified = bool(context["branch_lower_bound_certified"] or support.get("stable_support_certified"))
    if combined_certified:
        reason = "covered"
    elif not support.get("separated_at_center"):
        reason = "not_separated_at_center"
    elif not support.get("extrema_stable"):
        reason = "support_margin_failed_and_extrema_unstable"
    else:
        reason = "support_margin_failed"
    return {
        "context": context,
        "axis_relation": relation,
        "support": support,
        "combined_certified": combined_certified,
        "remaining_reason": reason,
    }


def compact_record(base: dict, threshold: float | None, child_index: int | None, evaluation: dict) -> dict:
    context = evaluation["context"]
    support = evaluation["support"]
    return {
        "base_parent_segment_id": base["parent_segment_id"],
        "base_subsegment_index": base["base_subsegment_index"],
        "source_edge_index": base["source_edge_index"],
        "source_node_ids": base["source_node_ids"],
        "assigned_branch_name": base["assigned_branch_name"],
        "refinement_threshold_degrees": threshold,
        "child_subsegment_index": child_index,
        "axis_relation": evaluation["axis_relation"],
        "remaining_reason": evaluation["remaining_reason"],
        "delta": support.get("delta"),
        "center_angle_degrees_by_hinge": context.get("center_angle_degrees_by_hinge"),
        "best_axis_name": context.get("best_axis_name"),
        "branch_gap": context.get("branch_gap"),
        "whole_piece_guard_bound": context.get("guard_bound"),
        "whole_piece_margin": context.get("branch_lower_bound_margin"),
        "whole_piece_branch_certified": context.get("branch_lower_bound_certified"),
        "support_guard_bound": support.get("support_guard_bound"),
        "support_margin": support.get("support_margin"),
        "lower_stability_margin": support.get("lower_stability_margin"),
        "upper_stability_margin": support.get("upper_stability_margin"),
        "extrema_stable": support.get("extrema_stable"),
        "stable_support_certified": support.get("stable_support_certified"),
        "guard_improvement_factor": support.get("guard_improvement_factor"),
    }


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def residual_base_subsegments(
    case: dict,
    tree: dict,
    indices: dict,
    labels_by_piece: dict,
    paths_by_piece: dict,
    signs_by_tree: dict[str, dict[str, int]],
) -> tuple[list[dict], Counter]:
    parents = branch_probe.parent_branch_segments(case, tree, paths_by_piece, signs_by_tree)
    residuals = []
    base_counters = Counter()
    relation_counters = Counter()
    for parent in parents:
        branch = parent["assigned_branch_name"]
        for sub_index, (left, right) in enumerate(branch_probe.subdivide_segment(parent, BASE_MAX_COORDINATE_DELTA_DEGREES)):
            evaluation = evaluate_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            relation = evaluation["axis_relation"]
            relation_counters[relation] += 1
            if evaluation["context"]["branch_lower_bound_certified"]:
                base_counters["whole_piece_branch_certified"] += 1
                continue
            if evaluation["support"].get("stable_support_certified"):
                base_counters["stable_support_certified"] += 1
                continue
            base_counters[f"residual:{relation}:{evaluation['remaining_reason']}"] += 1
            residuals.append(
                {
                    "parent_segment_id": f"seg_{parent['refined_segment_index']:05d}",
                    "source_edge_index": parent["source_edge_index"],
                    "source_node_ids": parent["source_node_ids"],
                    "source_t_interval": parent["source_t_interval"],
                    "assigned_branch_name": branch,
                    "base_subsegment_index": sub_index,
                    "left_vector": left,
                    "right_vector": right,
                    "base_evaluation": evaluation,
                }
            )
    base_counters.update({f"axis_relation_total:{key}": value for key, value in relation_counters.items()})
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
        child_whole_piece = 0
        child_stable_support = 0
        child_remaining_by_reason = Counter()
        for child_index, (left, right) in enumerate(subdivide_vector_segment(base["left_vector"], base["right_vector"], threshold)):
            child_total += 1
            counters["refined_subsegment_count"] += 1
            assigned_branch_counts[branch] += 1
            evaluation = evaluate_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            context = evaluation["context"]
            support = evaluation["support"]
            relation = evaluation["axis_relation"]
            axis_relation_counts[relation] += 1
            best_axis_counts[context["best_axis_name"]] += 1
            if context.get("branch_gap") is not None:
                branch_gaps.append(float(context["branch_gap"]))
            if support.get("support_margin") is not None:
                support_margins.append(float(support["support_margin"]))
            if support.get("lower_stability_margin") is not None and support.get("upper_stability_margin") is not None:
                stability_margins.append(min(float(support["lower_stability_margin"]), float(support["upper_stability_margin"])))
            if support.get("guard_improvement_factor") is not None:
                improvement_factors.append(float(support["guard_improvement_factor"]))

            whole_piece = bool(context["branch_lower_bound_certified"])
            stable_support = bool(support.get("stable_support_certified"))
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
            if evaluation["combined_certified"]:
                counters["combined_certified_count"] += 1
                child_covered += 1
                continue

            reason = f"{relation}:{evaluation['remaining_reason']}"
            remaining_reason_counts[reason] += 1
            child_remaining_by_reason[reason] += 1
            if evaluation["remaining_reason"] == "support_margin_failed_and_extrema_unstable":
                counters["uncovered_unstable_count"] += 1
                add_example(examples["uncovered_unstable"], compact_record(base, threshold, child_index, evaluation))
            elif relation != "same_assigned_edge_branch":
                counters["uncovered_axis_switch_count"] += 1
                add_example(examples["uncovered_axis_switch"], compact_record(base, threshold, child_index, evaluation))
            else:
                counters["uncovered_same_branch_margin_count"] += 1
                add_example(examples["uncovered_same_branch_margin"], compact_record(base, threshold, child_index, evaluation))

        if child_covered == child_total:
            base_outcome_counts["fully_combined_certified_base_count"] += 1
        elif child_covered == 0:
            base_outcome_counts["zero_child_certified_base_count"] += 1
        else:
            base_outcome_counts["partially_combined_certified_base_count"] += 1
        if child_whole_piece:
            base_outcome_counts["base_with_whole_piece_certified_child_count"] += 1
        if child_stable_support:
            base_outcome_counts["base_with_stable_support_certified_child_count"] += 1
        for reason in child_remaining_by_reason:
            base_outcome_counts[f"base_with_uncovered:{reason}"] += 1

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
    best_threshold = max(
        threshold_reports,
        key=lambda item: item["summary_counts"].get("combined_certified_count", 0),
    )["max_coordinate_delta_degrees"] if threshold_reports else None
    best_combined = max(
        (item["summary_counts"].get("combined_certified_count", 0) for item in threshold_reports),
        default=0,
    )
    return {
        "case_id": CASE_ID,
        "status": "tree007_p2p3_edge_branch_refinement_sensitivity_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_support_bound_probe_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_lower_bound_probe_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_face",
            "branches": branch_probe.TARGET_BRANCHES,
        },
        "base_max_coordinate_delta_degrees": BASE_MAX_COORDINATE_DELTA_DEGREES,
        "refinement_thresholds_degrees": REFINEMENT_THRESHOLDS,
        "base_residual_selection_counts": dict(base_counters),
        "base_residual_count": len(residuals),
        "threshold_reports": threshold_reports,
        "summary_metrics": {
            "base_residual_count": len(residuals),
            "best_threshold_by_combined_coverage": best_threshold,
            "best_combined_certified_count": best_combined,
        },
        "limitations": [
            "This is finite numeric refinement-sensitivity evidence, not a symbolic projection-bound derivation.",
            "The probe starts only from TREE_007 P2-P3 edge-branch leaves left uncovered by lower-bound plus stable_support at 0.625 degrees.",
            "Face-normal parent branches left_face:B-M_AB-M_CD and right_face:B-M_AB-M_CD are outside this edge-branch report.",
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