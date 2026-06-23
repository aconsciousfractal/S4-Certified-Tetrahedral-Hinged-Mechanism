"""TREE_021 P0-P2 targeted endgame guard.

This audit follows the theta projection-component bound probe. It targets only
the 53 child subsegments that remain uncovered after the previous 3999/4052
child coverage on the residual same-branch P0-P2 base set.

The endgame guard uses the locally best named SAT axis at each subcell midpoint
and applies the same projection-component support/extrema bound used by the
theta projection probe. It is adaptive:

1. Try the local best-axis component guard on the original 53 children.
2. Refine all 53 to max coordinate delta 0.01953125 degrees.
3. Refine only the remaining hard children to max coordinate delta
   0.001220703125 degrees.

This is finite numeric evidence for the selected residual same-branch workflow;
it does not cover the original 0.625-degree axis-switch failures that were
excluded before the 1013-base residual set was formed.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_targeted_endgame_guard_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
SOURCE_REFINEMENT_DELTA_DEGREES = 0.15625
BROAD_LOCAL_REFINEMENT_DELTA_DEGREES = 0.01953125
HARD_LOCAL_REFINEMENT_DELTA_DEGREES = 0.001220703125
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as failure_classification  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402
import audit_historical_s4_p0p2_residual_base_classification as base_classification  # noqa: E402
import audit_historical_s4_p0p2_same_branch_support_bound_probe as support_probe  # noqa: E402
import audit_historical_s4_p0p2_theta_projection_component_bound_probe as theta_probe  # noqa: E402

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


def top_counter(counter: Counter, limit: int = 24) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def best_named_axis_with_unit(poly_a: list[np.ndarray], poly_b: list[np.ndarray], labels_a: list[str], labels_b: list[str]) -> dict:
    best = None
    for name, axis in failure_classification.axis_records(poly_a, poly_b, labels_a, labels_b):
        norm = float(np.linalg.norm(axis))
        if norm <= lib.TOL:
            continue
        unit = axis / norm
        a_values = [float(np.dot(vertex, unit)) for vertex in poly_a]
        b_values = [float(np.dot(vertex, unit)) for vertex in poly_b]
        overlap = min(max(a_values), max(b_values)) - max(min(a_values), min(b_values))
        if best is None or overlap < best["center_axis_overlap"]:
            best = {"axis_name": name, "center_axis_overlap": float(overlap), "unit": unit}
    if best is None:
        raise RuntimeError("No named SAT axis found")
    return best


def local_best_axis_component_guard(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    left: np.ndarray,
    right: np.ndarray,
) -> dict:
    center = (left + right) / 2.0
    left_degrees = theta_probe.vector_to_degrees(tree, left)
    right_degrees = theta_probe.vector_to_degrees(tree, right)
    center_degrees = theta_probe.vector_to_degrees(tree, center)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = branch_probe.ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    best = best_named_axis_with_unit(
        transformed[TARGET_PAIR[0]],
        transformed[TARGET_PAIR[1]],
        labels_by_piece[TARGET_PAIR[0]],
        labels_by_piece[TARGET_PAIR[1]],
    )
    unit = best["unit"]
    state = support_probe.support_state(transformed, labels_by_piece, unit)
    if not state["separated_at_center"]:
        return {
            "certified": False,
            "failure_reason": "not_separated_at_center",
            "best_axis_name": best["axis_name"],
            "center_axis_overlap": rounded(best["center_axis_overlap"]),
            "gap": state.get("gap"),
            "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
            "delta": branch_probe.segment_delta(left, right),
        }

    lower_support, lower_non_support = sensitivity.piece_label_sets(labels_by_piece, state["lower_piece"], state["lower_support_labels"])
    upper_support, upper_non_support = sensitivity.piece_label_sets(labels_by_piece, state["upper_piece"], state["upper_support_labels"])

    def vertices(piece_id: str, labels: list[str]) -> list[np.ndarray]:
        return theta_probe.vertices_for_labels(transformed, indices, piece_id, labels)

    lower_support_positive = theta_probe.component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, vertices(state["lower_piece"], lower_support), state["lower_piece"], unit, "positive"
    )
    upper_support_negative = theta_probe.component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, vertices(state["upper_piece"], upper_support), state["upper_piece"], unit, "negative"
    )
    lower_support_negative = theta_probe.component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, vertices(state["lower_piece"], lower_support), state["lower_piece"], unit, "negative"
    )
    lower_non_support_positive = theta_probe.component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, vertices(state["lower_piece"], lower_non_support), state["lower_piece"], unit, "positive"
    )
    upper_support_positive = theta_probe.component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, vertices(state["upper_piece"], upper_support), state["upper_piece"], unit, "positive"
    )
    upper_non_support_negative = theta_probe.component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, vertices(state["upper_piece"], upper_non_support), state["upper_piece"], unit, "negative"
    )

    gap = float(state["gap"])
    signed_component_bound = lower_support_positive + upper_support_negative + SAT_TOLERANCE
    signed_component_margin = gap - signed_component_bound
    lower_stability_margin = float(state["lower_competition_margin"]) - lower_support_negative - lower_non_support_positive - SAT_TOLERANCE
    upper_stability_margin = float(state["upper_competition_margin"]) - upper_support_positive - upper_non_support_negative - SAT_TOLERANCE
    minimum_stability_margin = min(lower_stability_margin, upper_stability_margin)
    stable = lower_stability_margin >= 0.0 and upper_stability_margin >= 0.0
    certified = signed_component_margin >= 0.0 and stable
    if certified:
        failure_reason = None
    elif not stable:
        failure_reason = "stability"
    else:
        failure_reason = "margin"

    return {
        "certified": certified,
        "failure_reason": failure_reason,
        "best_axis_name": best["axis_name"],
        "center_axis_overlap": rounded(best["center_axis_overlap"]),
        "gap": rounded(gap),
        "signed_component_bound": rounded(signed_component_bound),
        "signed_component_margin": rounded(signed_component_margin),
        "minimum_stability_margin": rounded(minimum_stability_margin),
        "lower_piece": state["lower_piece"],
        "upper_piece": state["upper_piece"],
        "lower_support_labels": state["lower_support_labels"],
        "upper_support_labels": state["upper_support_labels"],
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "delta": branch_probe.segment_delta(left, right),
    }


def projected_remaining_children(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]]) -> tuple[list[dict], dict]:
    residuals, base_counters = sensitivity.residual_base_subsegments(case, tree, indices, labels_by_piece, paths_by_piece, signs_by_tree)
    children = []
    projected_reason_counts = Counter()
    for base in residuals:
        branch = base["assigned_branch_name"]
        for child_index, (left, right) in enumerate(sensitivity.subdivide_vector_segment(base["left_vector"], base["right_vector"], SOURCE_REFINEMENT_DELTA_DEGREES)):
            evaluation = sensitivity.evaluate_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            component = theta_probe.component_support_guard_from_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            projected_reason = theta_probe.projected_child_reason(evaluation, component)
            projected_reason_counts[projected_reason] += 1
            if projected_reason.startswith("covered:"):
                continue
            children.append(
                {
                    "residual_child_id": f"rem_{len(children):03d}",
                    "base_parent_segment_id": base["parent_segment_id"],
                    "base_subsegment_index": base["base_subsegment_index"],
                    "child_subsegment_index": child_index,
                    "source_node_ids": base["source_node_ids"],
                    "source_edge": base_classification.source_edge_descriptor(base["source_node_ids"]),
                    "assigned_branch_name": branch,
                    "previous_projected_reason": projected_reason,
                    "previous_best_axis_name": evaluation["best_axis_name"],
                    "left_vector": left,
                    "right_vector": right,
                }
            )
    return children, {"base_counters": dict(base_counters), "projected_reason_counts": dict(projected_reason_counts.most_common())}


def compact_child(child: dict) -> dict:
    return {
        "residual_child_id": child["residual_child_id"],
        "base_parent_segment_id": child["base_parent_segment_id"],
        "base_subsegment_index": child["base_subsegment_index"],
        "child_subsegment_index": child["child_subsegment_index"],
        "source_edge": child["source_edge"],
        "assigned_branch_name": child["assigned_branch_name"],
        "previous_projected_reason": child["previous_projected_reason"],
        "previous_best_axis_name": child["previous_best_axis_name"],
    }


def compact_leaf(child: dict, leaf_index: int, guard: dict) -> dict:
    return {
        **compact_child(child),
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


def audit_original_children(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, children: list[dict]) -> dict:
    counts = Counter()
    by_previous_reason = Counter()
    axis_counts = Counter()
    margins = []
    examples = defaultdict(list)
    for child in children:
        guard = local_best_axis_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, child["left_vector"], child["right_vector"])
        axis_counts[guard["best_axis_name"]] += 1
        key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
        counts[key] += 1
        by_previous_reason[f"{child['previous_projected_reason']} -> {key}"] += 1
        if guard.get("signed_component_margin") is not None:
            margins.append(float(guard["signed_component_margin"]))
        if guard["certified"]:
            add_example(examples["certified"], compact_leaf(child, 0, guard))
        else:
            add_example(examples["failed"], compact_leaf(child, 0, guard))
    return {
        "residual_child_count": len(children),
        "result_counts": dict(counts.most_common()),
        "by_previous_reason": dict(by_previous_reason.most_common()),
        "best_axis_counts": dict(axis_counts.most_common()),
        "signed_component_margin_quantiles": quantiles(margins),
        "examples": dict(examples),
    }


def audit_refined_children(
    case: dict,
    tree: dict,
    indices: dict,
    labels_by_piece: dict,
    paths_by_piece: dict,
    children: list[dict],
    threshold: float,
) -> dict:
    leaf_counts = Counter()
    original_outcome_counts = Counter()
    failure_counts = Counter()
    failure_by_previous_reason = Counter()
    best_axis_counts = Counter()
    margins = []
    certified_margins = []
    failed_margins = []
    examples = defaultdict(list)
    child_reports = []

    for child in children:
        leaf_total = 0
        leaf_certified = 0
        child_failure_counts = Counter()
        child_best_axis_counts = Counter()
        child_margin_values = []
        for leaf_index, (left, right) in enumerate(sensitivity.subdivide_vector_segment(child["left_vector"], child["right_vector"], threshold)):
            leaf_total += 1
            guard = local_best_axis_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, left, right)
            best_axis_counts[guard["best_axis_name"]] += 1
            child_best_axis_counts[guard["best_axis_name"]] += 1
            if guard.get("signed_component_margin") is not None:
                value = float(guard["signed_component_margin"])
                margins.append(value)
                child_margin_values.append(value)
                if guard["certified"]:
                    certified_margins.append(value)
                else:
                    failed_margins.append(value)
            if guard["certified"]:
                leaf_certified += 1
                leaf_counts["certified"] += 1
                add_example(examples["certified_leaves"], compact_leaf(child, leaf_index, guard))
            else:
                key = f"failed:{guard['failure_reason']}"
                leaf_counts[key] += 1
                failure_counts[guard["failure_reason"]] += 1
                failure_by_previous_reason[f"{child['previous_projected_reason']} -> {guard['failure_reason']}"] += 1
                child_failure_counts[guard["failure_reason"]] += 1
                add_example(examples["failed_leaves"], compact_leaf(child, leaf_index, guard))
        if leaf_certified == leaf_total:
            outcome = "fully_covered"
        elif leaf_certified == 0:
            outcome = "zero_leaf_covered"
        else:
            outcome = "partially_covered"
        original_outcome_counts[outcome] += 1
        child_reports.append(
            {
                **compact_child(child),
                "leaf_total": leaf_total,
                "leaf_certified": leaf_certified,
                "outcome": outcome,
                "failure_counts": dict(child_failure_counts.most_common()),
                "best_axis_counts": dict(child_best_axis_counts.most_common()),
                "signed_component_margin_interval": [
                    None if not child_margin_values else rounded(min(child_margin_values)),
                    None if not child_margin_values else rounded(max(child_margin_values)),
                ],
            }
        )

    return {
        "threshold_degrees": threshold,
        "original_child_count": len(children),
        "leaf_subsegment_count": sum(report["leaf_total"] for report in child_reports),
        "leaf_certified_count": sum(report["leaf_certified"] for report in child_reports),
        "leaf_uncovered_count": sum(report["leaf_total"] - report["leaf_certified"] for report in child_reports),
        "original_child_outcome_counts": dict(original_outcome_counts.most_common()),
        "leaf_result_counts": dict(leaf_counts.most_common()),
        "failure_reason_counts": dict(failure_counts.most_common()),
        "failure_by_previous_reason": dict(failure_by_previous_reason.most_common()),
        "best_axis_counts": dict(best_axis_counts.most_common()),
        "signed_component_margin_quantiles": quantiles(margins),
        "certified_signed_component_margin_quantiles": quantiles(certified_margins),
        "failed_signed_component_margin_quantiles": quantiles(failed_margins),
        "child_reports": child_reports,
        "examples": dict(examples),
    }


def hard_children_from_refinement(children: list[dict], refinement_report: dict) -> list[dict]:
    hard_ids = {
        report["residual_child_id"]
        for report in refinement_report["child_reports"]
        if report["outcome"] != "fully_covered"
    }
    return [child for child in children if child["residual_child_id"] in hard_ids]


def build_report() -> dict:
    case = branch_probe.batch.build_case()
    tree = branch_probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = branch_probe.comp.certified_signs_by_tree()
    paths_by_piece = branch_probe.ray_guard.tree_paths_from_root(case, tree)
    indices = branch_probe.label_indices(case)
    labels_by_piece = branch_probe.classify.labels_by_piece(case)

    children, selection_context = projected_remaining_children(case, tree, indices, labels_by_piece, paths_by_piece, signs_by_tree)
    original_report = audit_original_children(case, tree, indices, labels_by_piece, paths_by_piece, children)
    broad_report = audit_refined_children(case, tree, indices, labels_by_piece, paths_by_piece, children, BROAD_LOCAL_REFINEMENT_DELTA_DEGREES)
    hard_children = hard_children_from_refinement(children, broad_report)
    hard_report = audit_refined_children(case, tree, indices, labels_by_piece, paths_by_piece, hard_children, HARD_LOCAL_REFINEMENT_DELTA_DEGREES)

    broad_full_ids = {
        report["residual_child_id"]
        for report in broad_report["child_reports"]
        if report["outcome"] == "fully_covered"
    }
    broad_full_leaf_count = sum(
        report["leaf_total"] for report in broad_report["child_reports"] if report["residual_child_id"] in broad_full_ids
    )
    adaptive_leaf_count = broad_full_leaf_count + hard_report["leaf_subsegment_count"]
    adaptive_certified_leaf_count = broad_full_leaf_count + hard_report["leaf_certified_count"]
    all_hard_covered = hard_report["leaf_uncovered_count"] == 0 and len(hard_children) == hard_report["original_child_outcome_counts"].get("fully_covered", 0)
    adaptive_completed = len(broad_full_ids) + len(hard_children) == len(children) and all_hard_covered

    return {
        "case_id": CASE_ID,
        "status": "p0p2_targeted_endgame_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/p0p2_theta_projection_component_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_residual_base_classification_report.json",
            f"results/{CASE_ID}/p0p2_refinement_sensitivity_probe_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "selection_context": selection_context,
        "local_best_axis_rule": "At each subcell midpoint choose the named SAT axis with minimum overlap for P0-P2, then apply the signed projection-component support/extrema guard on that local axis.",
        "thresholds": {
            "source_remaining_child_delta_degrees": SOURCE_REFINEMENT_DELTA_DEGREES,
            "broad_local_refinement_delta_degrees": BROAD_LOCAL_REFINEMENT_DELTA_DEGREES,
            "hard_local_refinement_delta_degrees": HARD_LOCAL_REFINEMENT_DELTA_DEGREES,
        },
        "summary_metrics": {
            "input_remaining_child_count": len(children),
            "original_local_best_axis_certified_child_count": original_report["result_counts"].get("certified", 0),
            "broad_refinement_fully_covered_child_count": broad_report["original_child_outcome_counts"].get("fully_covered", 0),
            "broad_refinement_hard_child_count": len(hard_children),
            "hard_refinement_fully_covered_child_count": hard_report["original_child_outcome_counts"].get("fully_covered", 0),
            "adaptive_leaf_subsegment_count": adaptive_leaf_count,
            "adaptive_certified_leaf_subsegment_count": adaptive_certified_leaf_count,
            "adaptive_uncovered_leaf_subsegment_count": adaptive_leaf_count - adaptive_certified_leaf_count,
            "targeted_endgame_completed": adaptive_completed,
            "prior_projected_certified_child_count": 3999,
            "coarse_child_count_after_endgame": 4052 if adaptive_completed else None,
        },
        "remaining_child_breakdown": {
            "by_previous_projected_reason": top_counter(Counter(child["previous_projected_reason"] for child in children)),
            "by_source_kind": top_counter(Counter(child["source_edge"]["kind"] for child in children)),
            "by_theta_pair": top_counter(Counter(child["source_edge"]["theta_pair"] for child in children)),
            "by_assigned_branch": top_counter(Counter(child["assigned_branch_name"] for child in children)),
        },
        "original_local_best_axis_report": original_report,
        "broad_refinement_report": broad_report,
        "hard_children_after_broad_refinement": [compact_child(child) for child in hard_children],
        "hard_refinement_report": hard_report,
        "limitations": [
            "This is a finite adaptive guard for the 53 children left by the previous theta projection-component probe, not a symbolic theorem.",
            "It completes the selected 1013-base residual same-branch workflow only after replacing hard child cells by finer subcells.",
            "It does not cover the original 0.625-degree P0-P2 axis-switch failures that were excluded before forming the 1013 residual same-branch base set.",
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
                "remaining_child_breakdown": report["remaining_child_breakdown"],
                "original_local_best_axis_counts": report["original_local_best_axis_report"]["result_counts"],
                "broad_refinement_outcomes": report["broad_refinement_report"]["original_child_outcome_counts"],
                "hard_refinement_outcomes": report["hard_refinement_report"]["original_child_outcome_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())