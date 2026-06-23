"""Classify TREE_021 P0-P2 edge-branch lower-bound failures.

This audit follows the first P0-P2 edge-branch lower-bound probe and focuses on
its best threshold, max coordinate delta 0.625 degrees. It does not attempt a
new certificate. It separates failed subsegments by:

- assigned edge-edge branch;
- midpoint best-axis relation;
- branch-gap scale;
- hinge-angle scale;
- source component-graph edge.

The result is meant to choose the next model-building step tactically.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_edge_branch_failure_classification_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
TARGET_MAX_COORDINATE_DELTA_DEGREES = 0.625
MAX_STORED_EXAMPLES_PER_BUCKET = 20

GAP_BINS = [
    (1.0e-6, "<=1e-6"),
    (1.0e-5, "<=1e-5"),
    (1.0e-4, "<=1e-4"),
    (1.0e-3, "<=1e-3"),
    (1.0e-2, "<=1e-2"),
    (math.inf, ">1e-2"),
]

DEFICIT_BINS = [
    (1.0e-4, "<=1e-4"),
    (1.0e-3, "<=1e-3"),
    (1.0e-2, "<=1e-2"),
    (5.0e-2, "<=5e-2"),
    (math.inf, ">5e-2"),
]

ANGLE_BINS = [
    (1.0, "<=1deg"),
    (2.0, "<=2deg"),
    (5.0, "<=5deg"),
    (10.0, "<=10deg"),
    (20.0, "<=20deg"),
    (math.inf, ">20deg"),
]

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as probe  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
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
        return {key: None for key in ["min", "p01", "p05", "p10", "p25", "p50", "p75", "p90", "p95", "p99", "max"]}
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
        "p01": rounded(q(0.01)),
        "p05": rounded(q(0.05)),
        "p10": rounded(q(0.10)),
        "p25": rounded(q(0.25)),
        "p50": rounded(q(0.50)),
        "p75": rounded(q(0.75)),
        "p90": rounded(q(0.90)),
        "p95": rounded(q(0.95)),
        "p99": rounded(q(0.99)),
        "max": rounded(ordered[-1]),
    }


def axis_relation(context: dict, assigned_branch: str) -> str:
    best = context["best_axis_name"]
    if best == assigned_branch:
        return "same_assigned_edge_branch"
    if best in probe.TARGET_BRANCHES:
        return "other_target_edge_branch"
    if best.startswith("left_face:") or best.startswith("right_face:"):
        return "face_normal_switch"
    return "other_axis_switch"


def max_abs_angle(context: dict) -> float:
    angles = context["center_angle_degrees_by_hinge"].values()
    return max(abs(float(value)) for value in angles)


def source_key(parent: dict) -> str:
    return " -> ".join(parent["source_node_ids"])


def compact_record(parent: dict, sub_index: int, left: np.ndarray, right: np.ndarray, context: dict, relation: str) -> dict:
    branch_gap = context["branch_gap"]
    guard_bound = context["guard_bound"]
    margin = context["branch_lower_bound_margin"]
    deficit = None if margin is None else max(0.0, -float(margin))
    ratio = None
    if branch_gap is not None and branch_gap > 0.0 and guard_bound is not None:
        ratio = float(guard_bound) / float(branch_gap)
    return {
        "parent_segment_id": f"seg_{parent['refined_segment_index']:05d}",
        "source_edge_index": parent["source_edge_index"],
        "source_node_ids": parent["source_node_ids"],
        "assigned_branch_name": parent["assigned_branch_name"],
        "subsegment_index": sub_index,
        "delta": probe.segment_delta(left, right),
        "center_angle_degrees_by_hinge": context["center_angle_degrees_by_hinge"],
        "max_abs_center_angle_degrees": rounded(max_abs_angle(context), 8),
        "best_axis_name": context["best_axis_name"],
        "axis_relation": relation,
        "branch_gap": rounded(branch_gap),
        "guard_bound": rounded(guard_bound),
        "branch_lower_bound_margin": rounded(margin),
        "margin_deficit": rounded(deficit),
        "guard_to_gap_ratio": rounded(ratio, 6),
        "gap_bin": bin_value(branch_gap, GAP_BINS),
        "deficit_bin": bin_value(deficit, DEFICIT_BINS),
        "angle_bin": bin_value(max_abs_angle(context), ANGLE_BINS),
    }


def add_example(bucket: dict[str, list[dict]], key: str, record: dict) -> None:
    if len(bucket[key]) < MAX_STORED_EXAMPLES_PER_BUCKET:
        bucket[key].append(record)


def top_counter(counter: Counter, limit: int = 20) -> dict:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def classify_failures() -> dict:
    case = probe.batch.build_case()
    tree = probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = probe.comp.certified_signs_by_tree()
    paths_by_piece = probe.ray_guard.tree_paths_from_root(case, tree)
    indices = probe.label_indices(case)
    parents = probe.parent_branch_segments(case, tree, indices, paths_by_piece, signs_by_tree)

    total_subsegments = 0
    certified_count = 0
    failed_records: list[dict] = []
    failed_by_assigned_branch = Counter()
    failed_by_best_axis = Counter()
    failed_by_axis_relation = Counter()
    failed_by_gap_bin = Counter()
    failed_by_deficit_bin = Counter()
    failed_by_angle_bin = Counter()
    failed_by_source_edge_index = Counter()
    failed_by_source_node_pair = Counter()
    failed_by_relation_gap = Counter()
    failed_by_relation_angle = Counter()
    failed_by_relation_deficit = Counter()
    examples_by_relation: dict[str, list[dict]] = defaultdict(list)
    examples_by_gap_bin: dict[str, list[dict]] = defaultdict(list)
    examples_by_angle_bin: dict[str, list[dict]] = defaultdict(list)

    all_gaps: list[float] = []
    failed_gaps: list[float] = []
    failed_deficits: list[float] = []
    failed_ratios: list[float] = []
    failed_angles: list[float] = []

    for parent in parents:
        branch = parent["assigned_branch_name"]
        for sub_index, (left, right) in enumerate(probe.subdivide_segment(parent, TARGET_MAX_COORDINATE_DELTA_DEGREES)):
            total_subsegments += 1
            context = probe.midpoint_context(case, tree, indices, paths_by_piece, left, right, branch)
            gap = context["branch_gap"]
            if gap is not None:
                all_gaps.append(float(gap))
            if context["branch_lower_bound_certified"]:
                certified_count += 1
                continue

            relation = axis_relation(context, branch)
            record = compact_record(parent, sub_index, left, right, context, relation)
            failed_records.append(record)

            failed_by_assigned_branch[branch] += 1
            failed_by_best_axis[context["best_axis_name"]] += 1
            failed_by_axis_relation[relation] += 1
            failed_by_gap_bin[record["gap_bin"]] += 1
            failed_by_deficit_bin[record["deficit_bin"]] += 1
            failed_by_angle_bin[record["angle_bin"]] += 1
            failed_by_source_edge_index[parent["source_edge_index"]] += 1
            failed_by_source_node_pair[source_key(parent)] += 1
            failed_by_relation_gap[(relation, record["gap_bin"])] += 1
            failed_by_relation_angle[(relation, record["angle_bin"])] += 1
            failed_by_relation_deficit[(relation, record["deficit_bin"])] += 1
            add_example(examples_by_relation, relation, record)
            add_example(examples_by_gap_bin, record["gap_bin"], record)
            add_example(examples_by_angle_bin, record["angle_bin"], record)

            if record["branch_gap"] is not None:
                failed_gaps.append(float(record["branch_gap"]))
            if record["margin_deficit"] is not None:
                failed_deficits.append(float(record["margin_deficit"]))
            if record["guard_to_gap_ratio"] is not None:
                failed_ratios.append(float(record["guard_to_gap_ratio"]))
            failed_angles.append(float(record["max_abs_center_angle_degrees"]))

    closest_to_certification = sorted(
        failed_records,
        key=lambda item: (math.inf if item["margin_deficit"] is None else item["margin_deficit"]),
    )[:MAX_STORED_EXAMPLES_PER_BUCKET]
    largest_deficits = sorted(
        failed_records,
        key=lambda item: (-math.inf if item["margin_deficit"] is None else item["margin_deficit"]),
        reverse=True,
    )[:MAX_STORED_EXAMPLES_PER_BUCKET]
    minimum_gap_failures = sorted(
        failed_records,
        key=lambda item: (math.inf if item["branch_gap"] is None else item["branch_gap"]),
    )[:MAX_STORED_EXAMPLES_PER_BUCKET]

    relation_gap_table = {
        f"{relation} | {gap_bin}": int(count)
        for (relation, gap_bin), count in failed_by_relation_gap.most_common()
    }
    relation_angle_table = {
        f"{relation} | {angle_bin}": int(count)
        for (relation, angle_bin), count in failed_by_relation_angle.most_common()
    }
    relation_deficit_table = {
        f"{relation} | {deficit_bin}": int(count)
        for (relation, deficit_bin), count in failed_by_relation_deficit.most_common()
    }

    dominant_relation = failed_by_axis_relation.most_common(1)[0][0] if failed_by_axis_relation else None
    near_minimum_gap_count = sum(
        count for label, count in failed_by_gap_bin.items() if label in {"<=1e-6", "<=1e-5", "<=1e-4", "<=1e-3"}
    )
    axis_switch_count = sum(
        count for relation, count in failed_by_axis_relation.items() if relation != "same_assigned_edge_branch"
    )

    return {
        "case_id": CASE_ID,
        "status": "p0p2_edge_branch_failure_classification_completed",
        "source_report": f"results/{CASE_ID}/p0p2_edge_branch_lower_bound_probe_report.json",
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "target_max_coordinate_delta_degrees": TARGET_MAX_COORDINATE_DELTA_DEGREES,
        "summary_metrics": {
            "parent_uncovered_edge_branch_segment_count": len(parents),
            "subsegment_count": total_subsegments,
            "certified_subsegment_count": certified_count,
            "failed_subsegment_count": len(failed_records),
            "dominant_axis_relation": dominant_relation,
            "near_minimum_gap_failed_count_gap_le_1e_minus_3": near_minimum_gap_count,
            "axis_switch_failed_count": axis_switch_count,
        },
        "failed_by_assigned_branch": top_counter(failed_by_assigned_branch),
        "failed_by_best_axis": top_counter(failed_by_best_axis),
        "failed_by_axis_relation": top_counter(failed_by_axis_relation),
        "failed_by_gap_bin": top_counter(failed_by_gap_bin),
        "failed_by_deficit_bin": top_counter(failed_by_deficit_bin),
        "failed_by_angle_bin": top_counter(failed_by_angle_bin),
        "failed_by_relation_gap_bin": relation_gap_table,
        "failed_by_relation_angle_bin": relation_angle_table,
        "failed_by_relation_deficit_bin": relation_deficit_table,
        "failed_by_source_edge_index_top20": top_counter(failed_by_source_edge_index),
        "failed_by_source_node_pair_top20": top_counter(failed_by_source_node_pair),
        "quantiles": {
            "all_branch_gaps": quantiles(all_gaps),
            "failed_branch_gaps": quantiles(failed_gaps),
            "failed_margin_deficits": quantiles(failed_deficits),
            "failed_guard_to_gap_ratios": quantiles(failed_ratios),
            "failed_max_abs_center_angles_degrees": quantiles(failed_angles),
        },
        "examples": {
            "by_axis_relation": dict(examples_by_relation),
            "by_gap_bin": dict(examples_by_gap_bin),
            "by_angle_bin": dict(examples_by_angle_bin),
            "minimum_gap_failures": minimum_gap_failures,
            "closest_to_certification": closest_to_certification,
            "largest_margin_deficits": largest_deficits,
        },
        "limitations": [
            "This is a finite diagnostic classification of the 0.625-degree failed subsegments, not a new certificate.",
            "Failure of the conservative lower-bound guard does not imply collision.",
            "The report still covers only TREE_021 P0-P2 parent segments assigned to the two target edge-edge branches.",
            "Face-normal branches, residual shared-edge pairs, TREE_007, and the full continuous 3-parameter component remain outside this report.",
        ],
    }


def main() -> int:
    report = classify_failures()
    lib.write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "summary_metrics": report["summary_metrics"],
                "failed_by_axis_relation": report["failed_by_axis_relation"],
                "failed_by_gap_bin": report["failed_by_gap_bin"],
                "failed_by_angle_bin": report["failed_by_angle_bin"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())