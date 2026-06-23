"""Expanded-support endgame guard for TREE_021 P1-P2 bounded-cell failures.

The depth-5 failure classifier found 775 terminal boxes whose signed separation
margin is already nonnegative and whose only obstruction is support-extrema
stability. This script targets exactly those boxes.

For each box, it promotes any non-support vertex that cannot be proven unable
to overtake the current support extremum into an expanded support candidate set.
It then certifies separation with the expanded support set and a residual
stability check for the remaining non-support vertices.

This is a finite interval guard for the selected stability-only endgame boxes.
It does not address the 218 margin-only terminal boxes.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_tree021_p1p2_support_stability_endgame_guard_report.json"
SOURCE_CLASSIFIER_REPORT = "bounded_cell_tree021_p1p2_endgame_failure_classifier_report.json"
TARGET_CATEGORY = "stability_only_signed_margin_nonnegative"
MAX_STORED_EXAMPLES = 64
SAT_TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_p0p2_theta_projection_component_bound_probe as theta_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_shared_edge_adaptive_probe as adaptive  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_endgame_failure_classifier as classifier  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    if math.isinf(float(value)):
        return float(value)
    return round(float(value), digits)


def quantiles(values: list[float]) -> dict[str, float | None]:
    return adaptive.quantiles(values)


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def label_projection_map(
    transformed: dict[str, list[np.ndarray]],
    labels_by_piece: dict[str, list[str]],
    piece_id: str,
    unit: np.ndarray,
) -> dict[str, float]:
    return {
        label: float(np.dot(vertex, unit))
        for label, vertex in zip(labels_by_piece[piece_id], transformed[piece_id])
    }


def guard_context(ctx: dict, box: dict) -> dict:
    center_vector = adaptive.box_center_vector(ctx["tree"], ctx["signs"], box)
    center_degrees = adaptive.reps.degrees_from_vector(ctx["tree"], center_vector)
    intervals = adaptive.box_angle_intervals(ctx["tree"], ctx["signs"], box)
    delta_by_hinge = {
        hinge_id: 2.0 * float(record["max_deviation_from_center_degrees"])
        for hinge_id, record in intervals.items()
    }
    transforms = adaptive.ray_guard.transforms_for_degrees(ctx["case"], ctx["tree"], center_degrees)
    transformed = lib.transform_pieces(ctx["case"]["pieces_by_id"], transforms)
    unit, axis_norm = adaptive.shared_edge.common_edge_axis_unit(
        transformed,
        ctx["indices"],
        adaptive.TARGET_PAIR,
    )
    if unit is None:
        return {
            "valid": False,
            "failure_reason": "degenerate_common_edge_axis",
            "axis_norm": rounded(axis_norm),
            "angle_coordinate_intervals_by_hinge": intervals,
        }
    state = adaptive.shared_edge.support_state_for_pair(
        transformed,
        ctx["labels_by_piece"],
        adaptive.TARGET_PAIR,
        unit,
    )
    return {
        "valid": bool(state["separated_at_center"]),
        "failure_reason": None if state["separated_at_center"] else "not_separated_at_center",
        "axis_norm": rounded(axis_norm),
        "unit": unit,
        "state": state,
        "transforms": transforms,
        "transformed": transformed,
        "delta_by_hinge": delta_by_hinge,
        "angle_coordinate_intervals_by_hinge": intervals,
        "center_angle_degrees_by_hinge": {key: round(value, 12) for key, value in center_degrees.items()},
    }


def vertices_for_labels(
    transformed: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    piece_id: str,
    labels: list[str],
) -> list[np.ndarray]:
    return [transformed[piece_id][indices[piece_id][label]] for label in labels]


def component(
    ctx: dict,
    gctx: dict,
    piece_id: str,
    labels: list[str],
    direction: str,
) -> float:
    return theta_probe.component_displacement_bound_for_labels(
        ctx["case"],
        gctx["transforms"],
        gctx["delta_by_hinge"],
        ctx["paths_by_piece"],
        vertices_for_labels(gctx["transformed"], ctx["indices"], piece_id, labels),
        piece_id,
        gctx["unit"],
        direction,
    )


def component_per_label(
    ctx: dict,
    gctx: dict,
    piece_id: str,
    labels: list[str],
    direction: str,
) -> dict[str, float]:
    return {label: component(ctx, gctx, piece_id, [label], direction) for label in labels}


def expand_lower_support(ctx: dict, gctx: dict) -> dict:
    state = gctx["state"]
    piece_id = state["lower_piece"]
    labels = list(ctx["labels_by_piece"][piece_id])
    projections = label_projection_map(gctx["transformed"], ctx["labels_by_piece"], piece_id, gctx["unit"])
    extreme = float(state["lower_extreme_projection"])
    positive_bounds = component_per_label(ctx, gctx, piece_id, labels, "positive")
    support = set(state["lower_support_labels"])
    iterations = []

    changed = True
    while changed:
        changed = False
        support_labels = sorted(support)
        support_negative = component(ctx, gctx, piece_id, support_labels, "negative")
        promoted = []
        for label in labels:
            if label in support:
                continue
            center_gap = extreme - projections[label]
            margin = center_gap - support_negative - positive_bounds[label] - SAT_TOLERANCE
            if margin < 0.0:
                support.add(label)
                promoted.append(
                    {
                        "label": label,
                        "center_gap": rounded(center_gap),
                        "positive_bound": rounded(positive_bounds[label]),
                        "promotion_margin": rounded(margin),
                    }
                )
                changed = True
        iterations.append(
            {
                "support_labels_before": support_labels,
                "support_negative_bound": rounded(support_negative),
                "promoted": promoted,
            }
        )

    support_labels = sorted(support)
    support_negative = component(ctx, gctx, piece_id, support_labels, "negative")
    support_positive = component(ctx, gctx, piece_id, support_labels, "positive")
    non_support = [label for label in labels if label not in support]
    residual_margins = []
    for label in non_support:
        center_gap = extreme - projections[label]
        residual_margins.append(center_gap - support_negative - positive_bounds[label] - SAT_TOLERANCE)
    return {
        "piece_id": piece_id,
        "mode": "max",
        "original_support_labels": list(state["lower_support_labels"]),
        "expanded_support_labels": support_labels,
        "non_support_labels": non_support,
        "support_positive_bound": rounded(support_positive),
        "support_negative_bound": rounded(support_negative),
        "minimum_residual_stability_margin": rounded(min(residual_margins)) if residual_margins else float("inf"),
        "promoted_label_count": len(support_labels) - len(state["lower_support_labels"]),
        "iterations": iterations,
    }


def expand_upper_support(ctx: dict, gctx: dict) -> dict:
    state = gctx["state"]
    piece_id = state["upper_piece"]
    labels = list(ctx["labels_by_piece"][piece_id])
    projections = label_projection_map(gctx["transformed"], ctx["labels_by_piece"], piece_id, gctx["unit"])
    extreme = float(state["upper_extreme_projection"])
    negative_bounds = component_per_label(ctx, gctx, piece_id, labels, "negative")
    support = set(state["upper_support_labels"])
    iterations = []

    changed = True
    while changed:
        changed = False
        support_labels = sorted(support)
        support_positive = component(ctx, gctx, piece_id, support_labels, "positive")
        promoted = []
        for label in labels:
            if label in support:
                continue
            center_gap = projections[label] - extreme
            margin = center_gap - support_positive - negative_bounds[label] - SAT_TOLERANCE
            if margin < 0.0:
                support.add(label)
                promoted.append(
                    {
                        "label": label,
                        "center_gap": rounded(center_gap),
                        "negative_bound": rounded(negative_bounds[label]),
                        "promotion_margin": rounded(margin),
                    }
                )
                changed = True
        iterations.append(
            {
                "support_labels_before": support_labels,
                "support_positive_bound": rounded(support_positive),
                "promoted": promoted,
            }
        )

    support_labels = sorted(support)
    support_positive = component(ctx, gctx, piece_id, support_labels, "positive")
    support_negative = component(ctx, gctx, piece_id, support_labels, "negative")
    non_support = [label for label in labels if label not in support]
    residual_margins = []
    for label in non_support:
        center_gap = projections[label] - extreme
        residual_margins.append(center_gap - support_positive - negative_bounds[label] - SAT_TOLERANCE)
    return {
        "piece_id": piece_id,
        "mode": "min",
        "original_support_labels": list(state["upper_support_labels"]),
        "expanded_support_labels": support_labels,
        "non_support_labels": non_support,
        "support_positive_bound": rounded(support_positive),
        "support_negative_bound": rounded(support_negative),
        "minimum_residual_stability_margin": rounded(min(residual_margins)) if residual_margins else float("inf"),
        "promoted_label_count": len(support_labels) - len(state["upper_support_labels"]),
        "iterations": iterations,
    }


def expanded_support_guard(ctx: dict, box: dict, current_guard: dict) -> dict:
    gctx = guard_context(ctx, box)
    if not gctx["valid"]:
        return {
            "certified": False,
            "failure_reason": gctx["failure_reason"],
            "axis_norm": gctx.get("axis_norm"),
        }

    lower = expand_lower_support(ctx, gctx)
    upper = expand_upper_support(ctx, gctx)
    gap = float(gctx["state"]["gap"])
    signed_component_bound = (
        float(lower["support_positive_bound"])
        + float(upper["support_negative_bound"])
        + SAT_TOLERANCE
    )
    signed_component_margin = gap - signed_component_bound
    minimum_stability_margin = min(
        float(lower["minimum_residual_stability_margin"]),
        float(upper["minimum_residual_stability_margin"]),
    )
    certified = signed_component_margin >= 0.0 and minimum_stability_margin >= 0.0
    if certified:
        failure_reason = None
    elif signed_component_margin < 0.0:
        failure_reason = "expanded_support_margin"
    else:
        failure_reason = "expanded_support_stability"

    return {
        "certified": certified,
        "failure_reason": failure_reason,
        "axis_name": adaptive.shared_edge.COMMON_EDGE_AXIS_NAME,
        "axis_norm": gctx["axis_norm"],
        "gap": rounded(gap),
        "signed_component_bound": rounded(signed_component_bound),
        "signed_component_margin": rounded(signed_component_margin),
        "minimum_stability_margin": rounded(minimum_stability_margin),
        "lower_piece": gctx["state"]["lower_piece"],
        "upper_piece": gctx["state"]["upper_piece"],
        "lower_expanded_support": lower,
        "upper_expanded_support": upper,
        "current_signed_component_margin": current_guard.get("signed_component_margin"),
        "current_minimum_stability_margin": current_guard.get("minimum_stability_margin"),
        "angle_coordinate_intervals_by_hinge": gctx["angle_coordinate_intervals_by_hinge"],
        "center_angle_degrees_by_hinge": gctx["center_angle_degrees_by_hinge"],
        "max_hinge_coordinate_deviation_degrees": rounded(
            adaptive.box_max_hinge_deviation(ctx["tree"], ctx["signs"], box)
        ),
    }


def expanded_support_signature(guard: dict) -> str:
    lower = guard.get("lower_expanded_support", {})
    upper = guard.get("upper_expanded_support", {})
    lower_labels = ",".join(str(label) for label in lower.get("expanded_support_labels", []))
    upper_labels = ",".join(str(label) for label in upper.get("expanded_support_labels", []))
    return (
        f"lower={guard.get('lower_piece')}[{lower_labels}]"
        f"|upper={guard.get('upper_piece')}[{upper_labels}]"
    )

def compact_box_record(box: dict, guard: dict, current_guard: dict | None = None) -> dict:
    record = adaptive.compact_box(box, guard)
    record.update(
        {
            "recommended_split_dimension": box.get("recommended_split_dimension"),
            "support_signature": expanded_support_signature(guard),
            "lower_expanded_support_labels": guard.get("lower_expanded_support", {}).get("expanded_support_labels"),
            "upper_expanded_support_labels": guard.get("upper_expanded_support", {}).get("expanded_support_labels"),
            "lower_promoted_label_count": guard.get("lower_expanded_support", {}).get("promoted_label_count"),
            "upper_promoted_label_count": guard.get("upper_expanded_support", {}).get("promoted_label_count"),
        }
    )
    if current_guard is not None:
        record["current_minimum_stability_margin"] = current_guard.get("minimum_stability_margin")
        record["current_signed_component_margin"] = current_guard.get("signed_component_margin")
    return record


def target_boxes(ctx: dict) -> tuple[list[dict], list[dict], dict]:
    failed_boxes, level_trace = classifier.reconstruct_failed_terminal_boxes(ctx)
    target = []
    margin_backlog = []
    category_counts = Counter()
    for box in failed_boxes:
        current_guard = adaptive.common_edge_box_guard(
            ctx["case"],
            ctx["tree"],
            ctx["signs"],
            ctx["indices"],
            ctx["labels_by_piece"],
            ctx["paths_by_piece"],
            box,
        )
        category = classifier.failure_category(current_guard)
        category_counts[category] += 1
        record = {**box, "current_guard": current_guard, "failure_category": category}
        if category == TARGET_CATEGORY:
            target.append(record)
        else:
            margin_backlog.append(record)
    return target, margin_backlog, {
        "reconstructed_failed_box_count": len(failed_boxes),
        "reconstructed_category_counts": dict(category_counts.most_common()),
        "reconstructed_level_trace": level_trace,
    }


def audit_target_boxes(ctx: dict, boxes: list[dict]) -> dict:
    result_counts = Counter()
    support_expansion_counts = Counter()
    split_counts = Counter()
    support_signature_counts = Counter()
    base_outcomes: dict[str, Counter] = defaultdict(Counter)
    examples = defaultdict(list)
    signed_margins = []
    current_stability_margins = []
    expanded_stability_margins = []
    promoted_counts = []

    certified_records = []
    failed_records = []
    for box in boxes:
        current_guard = box["current_guard"]
        guard = expanded_support_guard(ctx, box, current_guard)
        key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
        result_counts[key] += 1
        split_counts[str(box.get("recommended_split_dimension"))] += 1
        support_signature_counts[expanded_support_signature(guard)] += 1
        base_outcomes[box["base_cell_id"]][key] += 1
        lower_promoted = int(guard.get("lower_expanded_support", {}).get("promoted_label_count", 0) or 0)
        upper_promoted = int(guard.get("upper_expanded_support", {}).get("promoted_label_count", 0) or 0)
        support_expansion_counts[f"lower+{lower_promoted}|upper+{upper_promoted}"] += 1
        promoted_counts.append(lower_promoted + upper_promoted)
        if guard.get("signed_component_margin") is not None:
            signed_margins.append(float(guard["signed_component_margin"]))
        if current_guard.get("minimum_stability_margin") is not None:
            current_stability_margins.append(float(current_guard["minimum_stability_margin"]))
        if guard.get("minimum_stability_margin") is not None and not math.isinf(float(guard["minimum_stability_margin"])):
            expanded_stability_margins.append(float(guard["minimum_stability_margin"]))
        record = compact_box_record(box, guard, current_guard)
        if guard["certified"]:
            certified_records.append(record)
            add_example(examples["certified"], record)
        else:
            failed_records.append(record)
            add_example(examples["failed"], record)

    fully_covered_target_bases = sum(
        1
        for counter in base_outcomes.values()
        if sum(value for key, value in counter.items() if key != "certified") == 0
    )
    return {
        "target_box_count": len(boxes),
        "result_counts": dict(result_counts.most_common()),
        "certified_box_count": result_counts.get("certified", 0),
        "failed_box_count": len(boxes) - result_counts.get("certified", 0),
        "target_base_cell_count": len(base_outcomes),
        "fully_covered_target_base_cell_count": fully_covered_target_bases,
        "support_expansion_counts": dict(support_expansion_counts.most_common()),
        "recommended_split_dimension_counts": dict(split_counts.most_common()),
        "support_signature_counts": dict(support_signature_counts.most_common()),
        "expanded_signed_component_margin_quantiles": quantiles(signed_margins),
        "current_minimum_stability_margin_quantiles": quantiles(current_stability_margins),
        "expanded_minimum_stability_margin_quantiles": quantiles(expanded_stability_margins),
        "total_promoted_label_count_quantiles": quantiles([float(value) for value in promoted_counts]),
        "certified_records": certified_records,
        "failed_records": failed_records,
        "examples": dict(examples),
    }


def combined_ledger_metrics(ctx: dict, target_audit: dict, margin_backlog: list[dict]) -> dict:
    adaptive_report = load_json(RESULTS_DIR / adaptive.REPORT_NAME)
    source = adaptive_report["summary_metrics"]
    remaining_failed_by_base = Counter()
    for box in margin_backlog:
        remaining_failed_by_base[box["base_cell_id"]] += 1
    for record in target_audit["failed_records"]:
        remaining_failed_by_base[record["base_cell_id"]] += 1

    base_count = len({box["base_cell_id"] for box in ctx["boxes"]})
    terminal_certified = (
        int(source["terminal_certified_box_count_at_max_depth"])
        + int(target_audit["certified_box_count"])
    )
    terminal_failed = (
        int(source["terminal_failed_box_count_at_max_depth"])
        - int(target_audit["certified_box_count"])
    )
    terminal_total = int(source["terminal_box_count_at_max_depth"])
    return {
        "terminal_box_count": terminal_total,
        "terminal_certified_box_count_after_guard": terminal_certified,
        "terminal_failed_box_count_after_guard": terminal_failed,
        "terminal_box_coverage_fraction_after_guard": round(terminal_certified / terminal_total, 6),
        "remaining_failed_terminal_box_count": terminal_failed,
        "remaining_margin_only_box_count": len(margin_backlog),
        "remaining_stability_box_count": int(target_audit["failed_box_count"]),
        "fully_covered_base_pair_cell_count_after_guard": base_count - len(remaining_failed_by_base),
        "partially_covered_base_pair_cell_count_after_guard": len(remaining_failed_by_base),
        "zero_certified_base_pair_cell_count_after_guard": 0,
        "remaining_failed_base_pair_cell_count": len(remaining_failed_by_base),
    }


def build_report() -> dict:
    ctx = classifier.context()
    source_classifier = load_json(RESULTS_DIR / SOURCE_CLASSIFIER_REPORT)
    target, margin_backlog, reconstruction = target_boxes(ctx)
    expected_target = source_classifier["summary_metrics"]["failure_category_counts"][TARGET_CATEGORY]
    if len(target) != expected_target:
        raise AssertionError(f"Expected {expected_target} target boxes, found {len(target)}")

    target_audit = audit_target_boxes(ctx, target)
    ledger = combined_ledger_metrics(ctx, target_audit, margin_backlog)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_tree021_p1p2_support_stability_endgame_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_CLASSIFIER_REPORT}",
            f"results/{CASE_ID}/{adaptive.REPORT_NAME}",
            f"results/{CASE_ID}/{adaptive.SOURCE_DIRECT_OVERLAY_REPORT}",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
        ],
        "target": {
            "tree_id": adaptive.TARGET_TREE_ID,
            "pair": list(adaptive.TARGET_PAIR),
            "role": "support_stability_endgame_guard",
            "target_failure_category": TARGET_CATEGORY,
        },
        "source_classifier_summary_metrics": source_classifier["summary_metrics"],
        "reconstruction": reconstruction,
        "summary_metrics": {
            "target_stability_only_box_count": len(target),
            "target_stability_only_certified_count": target_audit["certified_box_count"],
            "target_stability_only_failed_count": target_audit["failed_box_count"],
            "margin_only_backlog_box_count": len(margin_backlog),
            **ledger,
        },
        "target_audit": target_audit,
        "limitations": [
            "This report targets only the stability-only terminal boxes identified by the depth-5 classifier.",
            "The expanded-support guard does not certify the margin-only terminal boxes.",
            "The result does not close TREE_021 P1-P2 unless the remaining margin-only backlog is also handled.",
            "The result does not cover TREE_007, TREE_021 P0-P3, residual shared-face pair-cells, theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
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
                "target_result_counts": report["target_audit"]["result_counts"],
                "support_expansion_counts": report["target_audit"]["support_expansion_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
