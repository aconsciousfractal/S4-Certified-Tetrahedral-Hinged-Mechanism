"""Classify TREE_021 P0-P2 residual bases after refinement sensitivity.

The refinement-sensitivity probe at 0.15625 degrees fully covered 693/1013
residual same-branch bases, leaving 287 zero-child-covered bases and 33 partial
bases. This audit recomputes that threshold and classifies the unresolved base
set by source edge, angle band, gap scale, support-margin scale, and stability.

It is diagnostic only: no new certification rule is introduced here.
"""

from __future__ import annotations

from collections import Counter
import json
import math
import re
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_residual_base_classification_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
TARGET_REFINEMENT_DELTA_DEGREES = 0.15625
MAX_STORED_EXAMPLES = 24

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID
NODE_RE = re.compile(r"^t(?P<t>[^:]+):r(?P<r>[^:]+):d(?P<d>.+)$")

GAP_BINS = [
    (1.0e-6, "<=1e-6"),
    (1.0e-5, "<=1e-5"),
    (1.0e-4, "<=1e-4"),
    (1.0e-3, "<=1e-3"),
    (1.0e-2, "<=1e-2"),
    (math.inf, ">1e-2"),
]

NEG_MARGIN_BINS = [
    (-1.0e-2, "<=-1e-2"),
    (-5.0e-3, "<=-5e-3"),
    (-1.0e-3, "<=-1e-3"),
    (-1.0e-4, "<=-1e-4"),
    (0.0, "<0"),
    (math.inf, ">=0"),
]

STABILITY_BINS = [
    (-1.0e-2, "<=-1e-2"),
    (-5.0e-3, "<=-5e-3"),
    (-1.0e-3, "<=-1e-3"),
    (-1.0e-4, "<=-1e-4"),
    (0.0, "<0"),
    (1.0e-3, "<=1e-3"),
    (math.inf, ">1e-3"),
]

ANGLE_BINS = [
    (5.0, "<=5deg"),
    (10.0, "<=10deg"),
    (15.0, "<=15deg"),
    (20.0, "<=20deg"),
    (25.0, "<=25deg"),
    (math.inf, ">25deg"),
]


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    if math.isinf(float(value)):
        return float(value)
    return round(float(value), digits)


def bin_value(value: float | None, bins: list[tuple[float, str]]) -> str:
    if value is None:
        return "none"
    for limit, label in bins:
        if value <= limit:
            return label
    return "unbinned"


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


def top_counter(counter: Counter, limit: int = 20) -> dict:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def parse_node_id(node_id: str) -> dict[str, str]:
    match = NODE_RE.match(node_id)
    if not match:
        return {"t": "?", "r": "?", "d": "?"}
    return match.groupdict()


def source_edge_descriptor(node_ids: list[str]) -> dict:
    left = parse_node_id(node_ids[0])
    right = parse_node_id(node_ids[1])
    changed = []
    if left["t"] != right["t"]:
        changed.append("theta")
    if left["r"] != right["r"]:
        changed.append("radius")
    if left["d"] != right["d"]:
        changed.append("direction")
    return {
        "kind": "+".join(changed) if changed else "same_node",
        "theta_pair": f"{left['t']}->{right['t']}",
        "radius_pair": f"{left['r']}->{right['r']}",
        "direction_pair": f"{left['d']}->{right['d']}",
        "node_pair": " -> ".join(node_ids),
    }


def max_abs_center_angle(evaluation: dict) -> float:
    values = evaluation["center_angle_degrees_by_hinge"].values()
    return max(abs(float(value)) for value in values)


def minimum_stability_margin(evaluation: dict) -> float | None:
    support = evaluation["support"]
    values = [support.get("lower_stability_margin"), support.get("upper_stability_margin")]
    values = [float(value) for value in values if value is not None]
    if not values:
        return None
    return min(values)


def base_reason(base_evaluation: dict) -> str:
    support = base_evaluation["support"]
    if base_evaluation["axis_relation"] != "same_assigned_edge_branch":
        return f"axis_switch:{base_evaluation['axis_relation']}"
    if not support.get("extrema_stable"):
        return "same_branch_support_margin_failed_and_extrema_unstable"
    return "same_branch_support_margin_failed"


def child_reason(evaluation: dict) -> str:
    support = evaluation["support"]
    relation = evaluation["axis_relation"]
    if evaluation["whole_piece_branch_certified"]:
        return "covered:whole_piece"
    if relation == "same_assigned_edge_branch" and support.get("stable_support_certified"):
        return "covered:stable_support"
    if relation != "same_assigned_edge_branch":
        return f"uncovered:axis_switch:{relation}"
    if not support.get("extrema_stable"):
        return "uncovered:same_branch_support_margin_failed_and_extrema_unstable"
    return "uncovered:same_branch_support_margin_failed"


def compact_base(base: dict, outcome: dict) -> dict:
    evaluation = base["base_evaluation"]
    support = evaluation["support"]
    source = source_edge_descriptor(base["source_node_ids"])
    stability = minimum_stability_margin(evaluation)
    angle = max_abs_center_angle(evaluation)
    return {
        "base_parent_segment_id": base["parent_segment_id"],
        "base_subsegment_index": base["base_subsegment_index"],
        "source_edge_index": base["source_edge_index"],
        "source_node_ids": base["source_node_ids"],
        "source_edge": source,
        "assigned_branch_name": base["assigned_branch_name"],
        "base_outcome": outcome["base_outcome"],
        "child_total": outcome["child_total"],
        "child_covered": outcome["child_covered"],
        "child_reason_counts": outcome["child_reason_counts"],
        "base_reason": base_reason(evaluation),
        "base_branch_gap": evaluation["branch_gap"],
        "base_support_margin": support.get("support_margin"),
        "base_minimum_stability_margin": rounded(stability),
        "base_max_abs_center_angle_degrees": rounded(angle, 8),
        "base_gap_bin": bin_value(evaluation["branch_gap"], GAP_BINS),
        "base_support_margin_bin": bin_value(support.get("support_margin"), NEG_MARGIN_BINS),
        "base_stability_bin": bin_value(stability, STABILITY_BINS),
        "base_angle_bin": bin_value(angle, ANGLE_BINS),
    }


def add_example(bucket: list[dict], item: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(item)


def evaluate_base_children(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, base: dict) -> dict:
    child_total = 0
    child_covered = 0
    reason_counts = Counter()
    for left, right in sensitivity.subdivide_vector_segment(base["left_vector"], base["right_vector"], TARGET_REFINEMENT_DELTA_DEGREES):
        child_total += 1
        evaluation = sensitivity.evaluate_segment(
            case,
            tree,
            indices,
            labels_by_piece,
            paths_by_piece,
            left,
            right,
            base["assigned_branch_name"],
        )
        reason = child_reason(evaluation)
        reason_counts[reason] += 1
        if reason.startswith("covered:"):
            child_covered += 1
    if child_covered == child_total:
        outcome = "fully_covered"
    elif child_covered == 0:
        outcome = "zero_child_covered"
    else:
        outcome = "partially_covered"
    return {
        "base_outcome": outcome,
        "child_total": child_total,
        "child_covered": child_covered,
        "child_reason_counts": dict(reason_counts.most_common()),
    }


def update_focus_stats(stats: dict, base_record: dict) -> None:
    outcome = base_record["base_outcome"]
    prefix = outcome
    stats[f"{prefix}_count"] += 1
    stats[f"{prefix}_by_assigned_branch"][base_record["assigned_branch_name"]] += 1
    stats[f"{prefix}_by_source_kind"][base_record["source_edge"]["kind"]] += 1
    stats[f"{prefix}_by_theta_pair"][base_record["source_edge"]["theta_pair"]] += 1
    stats[f"{prefix}_by_radius_pair"][base_record["source_edge"]["radius_pair"]] += 1
    stats[f"{prefix}_by_direction_pair"][base_record["source_edge"]["direction_pair"]] += 1
    stats[f"{prefix}_by_gap_bin"][base_record["base_gap_bin"]] += 1
    stats[f"{prefix}_by_support_margin_bin"][base_record["base_support_margin_bin"]] += 1
    stats[f"{prefix}_by_stability_bin"][base_record["base_stability_bin"]] += 1
    stats[f"{prefix}_by_angle_bin"][base_record["base_angle_bin"]] += 1
    stats[f"{prefix}_by_base_reason"][base_record["base_reason"]] += 1
    stats[f"{prefix}_by_source_node_pair"][base_record["source_edge"]["node_pair"]] += 1
    stats[f"{prefix}_gaps"].append(float(base_record["base_branch_gap"]))
    stats[f"{prefix}_support_margins"].append(float(base_record["base_support_margin"]))
    if base_record["base_minimum_stability_margin"] is not None:
        stats[f"{prefix}_stability_margins"].append(float(base_record["base_minimum_stability_margin"]))
    stats[f"{prefix}_angles"].append(float(base_record["base_max_abs_center_angle_degrees"]))
    for reason, count in base_record["child_reason_counts"].items():
        stats[f"{prefix}_child_reason_counts"][reason] += int(count)


def finalize_counter_maps(stats: dict, prefix: str) -> dict:
    return {
        "count": stats[f"{prefix}_count"],
        "by_assigned_branch": top_counter(stats[f"{prefix}_by_assigned_branch"]),
        "by_source_kind": top_counter(stats[f"{prefix}_by_source_kind"]),
        "by_theta_pair": top_counter(stats[f"{prefix}_by_theta_pair"]),
        "by_radius_pair": top_counter(stats[f"{prefix}_by_radius_pair"]),
        "by_direction_pair": top_counter(stats[f"{prefix}_by_direction_pair"]),
        "by_gap_bin": top_counter(stats[f"{prefix}_by_gap_bin"]),
        "by_support_margin_bin": top_counter(stats[f"{prefix}_by_support_margin_bin"]),
        "by_stability_bin": top_counter(stats[f"{prefix}_by_stability_bin"]),
        "by_angle_bin": top_counter(stats[f"{prefix}_by_angle_bin"]),
        "by_base_reason": top_counter(stats[f"{prefix}_by_base_reason"]),
        "by_source_node_pair_top20": top_counter(stats[f"{prefix}_by_source_node_pair"], 20),
        "child_reason_counts": top_counter(stats[f"{prefix}_child_reason_counts"]),
        "quantiles": {
            "base_branch_gap": quantiles(stats[f"{prefix}_gaps"]),
            "base_support_margin": quantiles(stats[f"{prefix}_support_margins"]),
            "base_minimum_stability_margin": quantiles(stats[f"{prefix}_stability_margins"]),
            "base_max_abs_center_angle_degrees": quantiles(stats[f"{prefix}_angles"]),
        },
    }


def build_report() -> dict:
    case = branch_probe.batch.build_case()
    tree = branch_probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = branch_probe.comp.certified_signs_by_tree()
    paths_by_piece = branch_probe.ray_guard.tree_paths_from_root(case, tree)
    indices = branch_probe.label_indices(case)
    labels_by_piece = branch_probe.classify.labels_by_piece(case)
    residuals, base_counters = sensitivity.residual_base_subsegments(case, tree, indices, labels_by_piece, paths_by_piece, signs_by_tree)

    outcome_counts = Counter()
    focus_child_reason_counts = Counter()
    stats = {}
    for prefix in ["zero_child_covered", "partially_covered"]:
        stats[f"{prefix}_count"] = 0
        for suffix in [
            "by_assigned_branch",
            "by_source_kind",
            "by_theta_pair",
            "by_radius_pair",
            "by_direction_pair",
            "by_gap_bin",
            "by_support_margin_bin",
            "by_stability_bin",
            "by_angle_bin",
            "by_base_reason",
            "by_source_node_pair",
            "child_reason_counts",
        ]:
            stats[f"{prefix}_{suffix}"] = Counter()
        for suffix in ["gaps", "support_margins", "stability_margins", "angles"]:
            stats[f"{prefix}_{suffix}"] = []

    examples = {
        "zero_child_covered": [],
        "partially_covered": [],
    }

    for base in residuals:
        outcome = evaluate_base_children(case, tree, indices, labels_by_piece, paths_by_piece, base)
        outcome_counts[outcome["base_outcome"]] += 1
        if outcome["base_outcome"] not in examples:
            continue
        record = compact_base(base, outcome)
        update_focus_stats(stats, record)
        add_example(examples[outcome["base_outcome"]], record)
        for reason, count in outcome["child_reason_counts"].items():
            focus_child_reason_counts[reason] += int(count)

    zero = finalize_counter_maps(stats, "zero_child_covered")
    partial = finalize_counter_maps(stats, "partially_covered")
    focus_count = zero["count"] + partial["count"]
    return {
        "case_id": CASE_ID,
        "status": "p0p2_residual_base_classification_completed",
        "source_report": f"results/{CASE_ID}/p0p2_refinement_sensitivity_probe_report.json",
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "target_refinement_delta_degrees": TARGET_REFINEMENT_DELTA_DEGREES,
        "base_residual_selection_counts": dict(base_counters),
        "base_outcome_counts": dict(outcome_counts.most_common()),
        "summary_metrics": {
            "base_residual_same_branch_count": len(residuals),
            "zero_child_covered_base_count": zero["count"],
            "partially_covered_base_count": partial["count"],
            "focus_unresolved_base_count": focus_count,
            "fully_covered_base_count": outcome_counts["fully_covered"],
        },
        "focus_child_reason_counts": dict(focus_child_reason_counts.most_common()),
        "zero_child_covered": zero,
        "partially_covered": partial,
        "examples": examples,
        "limitations": [
            "This is a diagnostic classification of unresolved bases after the 0.15625-degree refinement-sensitivity probe, not a new certificate.",
            "The report covers only the residual same-branch P0-P2 base subsegments selected by the previous stable-support guard.",
            "It does not cover the original P0-P2 axis-switch cases, residual shared-edge pairs, TREE_007, or physical hinge thickness/clearance.",
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
                "base_outcome_counts": report["base_outcome_counts"],
                "focus_child_reason_counts": report["focus_child_reason_counts"],
                "zero_child_top": {
                    "by_gap_bin": report["zero_child_covered"]["by_gap_bin"],
                    "by_angle_bin": report["zero_child_covered"]["by_angle_bin"],
                    "by_base_reason": report["zero_child_covered"]["by_base_reason"],
                },
                "partial_top": {
                    "by_gap_bin": report["partially_covered"]["by_gap_bin"],
                    "by_angle_bin": report["partially_covered"]["by_angle_bin"],
                    "by_base_reason": report["partially_covered"]["by_base_reason"],
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())