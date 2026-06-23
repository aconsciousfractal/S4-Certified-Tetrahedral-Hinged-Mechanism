"""TREE_021 P0-P2 original axis-switch backlog guard.

This audit returns to the 116 P0-P2 axis-switch failures from the 0.625-degree
edge-branch failure classification. Those failures were intentionally excluded
before the 1013 residual same-branch base workflow was formed.

The guard uses the same locally best named SAT axis and signed projection-
component support/extrema rule used by the targeted endgame guard. It applies an
adaptive refinement ladder to the 116 backlog children and records the first
level at which each child is fully covered.

This is finite adaptive evidence for the original P0-P2 axis-switch backlog; it
is not a symbolic theorem and does not cover P0-P3/P1-P2 shared-edge residuals.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_axis_switch_backlog_guard_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
SOURCE_MAX_COORDINATE_DELTA_DEGREES = 0.625
ADAPTIVE_THRESHOLDS_DEGREES = [
    0.3125,
    0.15625,
    0.078125,
    0.0390625,
    0.01953125,
    0.009765625,
    0.0048828125,
    0.00244140625,
    0.001220703125,
]
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_failure_classification as failure_classification  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402
import audit_historical_s4_p0p2_residual_base_classification as base_classification  # noqa: E402
import audit_historical_s4_p0p2_targeted_endgame_guard as endgame_guard  # noqa: E402

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


def top_counter(counter: Counter, limit: int = 30) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def add_example(bucket: list[dict], item: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(item)


def compact_backlog_child(child: dict) -> dict:
    return {
        "backlog_child_id": child["backlog_child_id"],
        "parent_segment_id": child["parent_segment_id"],
        "source_edge_index": child["source_edge_index"],
        "source_node_ids": child["source_node_ids"],
        "source_edge": child["source_edge"],
        "assigned_branch_name": child["assigned_branch_name"],
        "subsegment_index": child["subsegment_index"],
        "axis_relation": child["axis_relation"],
        "previous_best_axis_name": child["previous_best_axis_name"],
        "previous_branch_gap": child["previous_branch_gap"],
        "previous_margin_deficit": child["previous_margin_deficit"],
    }


def compact_leaf(child: dict, leaf_index: int, guard: dict) -> dict:
    return {
        **compact_backlog_child(child),
        "leaf_index": leaf_index,
        "certified": guard["certified"],
        "failure_reason": guard["failure_reason"],
        "best_axis_name": guard["best_axis_name"],
        "gap": guard.get("gap"),
        "signed_component_bound": guard.get("signed_component_bound"),
        "signed_component_margin": guard.get("signed_component_margin"),
        "minimum_stability_margin": guard.get("minimum_stability_margin"),
        "delta": guard.get("delta"),
        "center_angle_degrees_by_hinge": guard.get("center_angle_degrees_by_hinge"),
    }


def reconstruct_axis_switch_backlog(case: dict, tree: dict, indices: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]]) -> tuple[list[dict], dict]:
    parents = branch_probe.parent_branch_segments(case, tree, indices, paths_by_piece, signs_by_tree)
    backlog = []
    failed_relation_counts = Counter()
    certified_count = 0
    failed_count = 0
    for parent in parents:
        branch = parent["assigned_branch_name"]
        for sub_index, (left, right) in enumerate(branch_probe.subdivide_segment(parent, SOURCE_MAX_COORDINATE_DELTA_DEGREES)):
            context = branch_probe.midpoint_context(case, tree, indices, paths_by_piece, left, right, branch)
            if context["branch_lower_bound_certified"]:
                certified_count += 1
                continue
            failed_count += 1
            relation = failure_classification.axis_relation(context, branch)
            failed_relation_counts[relation] += 1
            if relation == "same_assigned_edge_branch":
                continue
            margin = context["branch_lower_bound_margin"]
            backlog.append(
                {
                    "backlog_child_id": f"axis_{len(backlog):03d}",
                    "parent_segment_id": f"seg_{parent['refined_segment_index']:05d}",
                    "source_edge_index": parent["source_edge_index"],
                    "source_node_ids": parent["source_node_ids"],
                    "source_edge": base_classification.source_edge_descriptor(parent["source_node_ids"]),
                    "assigned_branch_name": branch,
                    "subsegment_index": sub_index,
                    "axis_relation": relation,
                    "previous_best_axis_name": context["best_axis_name"],
                    "previous_branch_gap": context["branch_gap"],
                    "previous_margin_deficit": None if margin is None else rounded(max(0.0, -float(margin))),
                    "left_vector": left,
                    "right_vector": right,
                }
            )
    return backlog, {
        "parent_segment_count": len(parents),
        "source_subsegment_count": certified_count + failed_count,
        "source_certified_subsegment_count": certified_count,
        "source_failed_subsegment_count": failed_count,
        "source_failed_relation_counts": dict(failed_relation_counts.most_common()),
    }


def audit_original_guard(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, backlog: list[dict]) -> dict:
    result_counts = Counter()
    by_relation = Counter()
    by_theta_pair = Counter()
    best_axis_counts = Counter()
    margins = []
    examples = defaultdict(list)
    for child in backlog:
        guard = endgame_guard.local_best_axis_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, child["left_vector"], child["right_vector"])
        key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
        result_counts[key] += 1
        by_relation[f"{child['axis_relation']} -> {key}"] += 1
        by_theta_pair[f"{child['source_edge']['theta_pair']} -> {key}"] += 1
        best_axis_counts[guard["best_axis_name"]] += 1
        if guard.get("signed_component_margin") is not None:
            margins.append(float(guard["signed_component_margin"]))
        if guard["certified"]:
            add_example(examples["certified"], compact_leaf(child, 0, guard))
        else:
            add_example(examples["failed"], compact_leaf(child, 0, guard))
    return {
        "input_child_count": len(backlog),
        "result_counts": dict(result_counts.most_common()),
        "by_axis_relation": dict(by_relation.most_common()),
        "by_theta_pair": dict(by_theta_pair.most_common()),
        "best_axis_counts": dict(best_axis_counts.most_common()),
        "signed_component_margin_quantiles": quantiles(margins),
        "examples": dict(examples),
    }


def audit_refinement_level(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, children: list[dict], threshold: float) -> dict:
    leaf_counts = Counter()
    child_outcomes = Counter()
    failure_counts = Counter()
    failure_by_relation_theta_axis = Counter()
    best_axis_counts = Counter()
    margins = []
    certified_margins = []
    failed_margins = []
    examples = defaultdict(list)
    child_reports = []

    for child in children:
        leaf_total = 0
        leaf_certified = 0
        child_failures = Counter()
        child_best_axes = Counter()
        child_margins = []
        for leaf_index, (left, right) in enumerate(sensitivity.subdivide_vector_segment(child["left_vector"], child["right_vector"], threshold)):
            leaf_total += 1
            guard = endgame_guard.local_best_axis_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, left, right)
            best_axis_counts[guard["best_axis_name"]] += 1
            child_best_axes[guard["best_axis_name"]] += 1
            if guard.get("signed_component_margin") is not None:
                value = float(guard["signed_component_margin"])
                margins.append(value)
                child_margins.append(value)
                if guard["certified"]:
                    certified_margins.append(value)
                else:
                    failed_margins.append(value)
            if guard["certified"]:
                leaf_certified += 1
                leaf_counts["certified"] += 1
                add_example(examples["certified_leaves"], compact_leaf(child, leaf_index, guard))
            else:
                reason = guard["failure_reason"]
                leaf_counts[f"failed:{reason}"] += 1
                failure_counts[reason] += 1
                child_failures[reason] += 1
                failure_by_relation_theta_axis[(child["axis_relation"], child["source_edge"]["theta_pair"], reason, guard["best_axis_name"])] += 1
                add_example(examples["failed_leaves"], compact_leaf(child, leaf_index, guard))
        if leaf_certified == leaf_total:
            outcome = "fully_covered"
        elif leaf_certified == 0:
            outcome = "zero_leaf_covered"
        else:
            outcome = "partially_covered"
        child_outcomes[outcome] += 1
        child_reports.append(
            {
                **compact_backlog_child(child),
                "leaf_total": leaf_total,
                "leaf_certified": leaf_certified,
                "outcome": outcome,
                "failure_counts": dict(child_failures.most_common()),
                "best_axis_counts": dict(child_best_axes.most_common()),
                "signed_component_margin_interval": [
                    None if not child_margins else rounded(min(child_margins)),
                    None if not child_margins else rounded(max(child_margins)),
                ],
            }
        )

    return {
        "threshold_degrees": threshold,
        "input_child_count": len(children),
        "leaf_subsegment_count": sum(report["leaf_total"] for report in child_reports),
        "leaf_certified_count": sum(report["leaf_certified"] for report in child_reports),
        "leaf_uncovered_count": sum(report["leaf_total"] - report["leaf_certified"] for report in child_reports),
        "child_outcome_counts": dict(child_outcomes.most_common()),
        "leaf_result_counts": dict(leaf_counts.most_common()),
        "failure_reason_counts": dict(failure_counts.most_common()),
        "failure_by_relation_theta_axis": {
            f"{relation} | {theta_pair} | {reason} | {axis}": int(count)
            for (relation, theta_pair, reason, axis), count in failure_by_relation_theta_axis.most_common(30)
        },
        "best_axis_counts": dict(best_axis_counts.most_common()),
        "signed_component_margin_quantiles": quantiles(margins),
        "certified_signed_component_margin_quantiles": quantiles(certified_margins),
        "failed_signed_component_margin_quantiles": quantiles(failed_margins),
        "child_reports": child_reports,
        "examples": dict(examples),
    }


def hard_children(children: list[dict], level_report: dict) -> list[dict]:
    hard_ids = {report["backlog_child_id"] for report in level_report["child_reports"] if report["outcome"] != "fully_covered"}
    return [child for child in children if child["backlog_child_id"] in hard_ids]


def adaptive_ladder(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, backlog: list[dict]) -> tuple[list[dict], dict]:
    remaining = list(backlog)
    level_reports = []
    first_cover_records = []
    adaptive_leaf_count = 0
    adaptive_certified_leaf_count = 0

    for threshold in ADAPTIVE_THRESHOLDS_DEGREES:
        if not remaining:
            break
        report = audit_refinement_level(case, tree, indices, labels_by_piece, paths_by_piece, remaining, threshold)
        level_reports.append(report)
        current_by_id = {child["backlog_child_id"]: child for child in remaining}
        next_remaining_ids = set()
        for child_report in report["child_reports"]:
            child = current_by_id[child_report["backlog_child_id"]]
            if child_report["outcome"] == "fully_covered":
                adaptive_leaf_count += int(child_report["leaf_total"])
                adaptive_certified_leaf_count += int(child_report["leaf_certified"])
                first_cover_records.append(
                    {
                        **compact_backlog_child(child),
                        "covered_at_threshold_degrees": threshold,
                        "leaf_total": child_report["leaf_total"],
                        "leaf_certified": child_report["leaf_certified"],
                        "best_axis_counts": child_report["best_axis_counts"],
                        "signed_component_margin_interval": child_report["signed_component_margin_interval"],
                    }
                )
            else:
                next_remaining_ids.add(child_report["backlog_child_id"])
        remaining = [child for child in remaining if child["backlog_child_id"] in next_remaining_ids]

    return level_reports, {
        "adaptive_completed": not remaining,
        "adaptive_leaf_subsegment_count": adaptive_leaf_count,
        "adaptive_certified_leaf_subsegment_count": adaptive_certified_leaf_count,
        "adaptive_uncovered_leaf_subsegment_count": adaptive_leaf_count - adaptive_certified_leaf_count,
        "first_cover_counts_by_threshold": top_counter(Counter(str(record["covered_at_threshold_degrees"]) for record in first_cover_records)),
        "first_cover_records": first_cover_records,
        "remaining_after_ladder": [compact_backlog_child(child) for child in remaining],
    }


def build_report() -> dict:
    case = branch_probe.batch.build_case()
    tree = branch_probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = branch_probe.comp.certified_signs_by_tree()
    paths_by_piece = branch_probe.ray_guard.tree_paths_from_root(case, tree)
    indices = branch_probe.label_indices(case)
    labels_by_piece = branch_probe.classify.labels_by_piece(case)

    backlog, reconstruction = reconstruct_axis_switch_backlog(case, tree, indices, paths_by_piece, signs_by_tree)
    original_report = audit_original_guard(case, tree, indices, labels_by_piece, paths_by_piece, backlog)
    level_reports, adaptive = adaptive_ladder(case, tree, indices, labels_by_piece, paths_by_piece, backlog)

    return {
        "case_id": CASE_ID,
        "status": "p0p2_axis_switch_backlog_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/p0p2_edge_branch_failure_classification_report.json",
            f"results/{CASE_ID}/p0p2_edge_branch_lower_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_targeted_endgame_guard_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "source_max_coordinate_delta_degrees": SOURCE_MAX_COORDINATE_DELTA_DEGREES,
        "adaptive_thresholds_degrees": ADAPTIVE_THRESHOLDS_DEGREES,
        "reconstruction": reconstruction,
        "summary_metrics": {
            "input_axis_switch_child_count": len(backlog),
            "input_face_normal_switch_count": sum(1 for child in backlog if child["axis_relation"] == "face_normal_switch"),
            "input_other_target_edge_branch_count": sum(1 for child in backlog if child["axis_relation"] == "other_target_edge_branch"),
            "original_local_best_axis_certified_count": original_report["result_counts"].get("certified", 0),
            "adaptive_completed": adaptive["adaptive_completed"],
            "adaptive_leaf_subsegment_count": adaptive["adaptive_leaf_subsegment_count"],
            "adaptive_certified_leaf_subsegment_count": adaptive["adaptive_certified_leaf_subsegment_count"],
            "adaptive_uncovered_leaf_subsegment_count": adaptive["adaptive_uncovered_leaf_subsegment_count"],
        },
        "input_breakdown": {
            "by_axis_relation": top_counter(Counter(child["axis_relation"] for child in backlog)),
            "by_theta_pair": top_counter(Counter(child["source_edge"]["theta_pair"] for child in backlog)),
            "by_assigned_branch": top_counter(Counter(child["assigned_branch_name"] for child in backlog)),
            "by_previous_best_axis": top_counter(Counter(child["previous_best_axis_name"] for child in backlog)),
        },
        "original_local_best_axis_report": original_report,
        "adaptive_level_reports": level_reports,
        "adaptive_summary": adaptive,
        "limitations": [
            "This is a finite adaptive guard for the 116 P0-P2 axis-switch failures from the 0.625-degree edge-branch failure classification, not a symbolic theorem.",
            "The adaptive ledger covers the original axis-switch backlog by replacing hard child cells with finer certified leaves.",
            "It does not cover P0-P3/P1-P2 shared-edge residual contacts, TREE_007 mirror transfer, theta=0, the full continuous 3-parameter component, or physical hinge thickness.",
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
                "input_breakdown": report["input_breakdown"],
                "first_cover_counts_by_threshold": report["adaptive_summary"]["first_cover_counts_by_threshold"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())