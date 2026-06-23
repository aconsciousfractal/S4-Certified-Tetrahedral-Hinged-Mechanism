"""Adaptive bounded-cell probe for TREE_021 P1-P2 shared-edge cells.

This audit starts from the direct bounded-cell shared-edge overlay, where
TREE_021 P1-P2 remained uncovered in all 768 candidate cells. It applies a
tactical adaptive subdivision to those cells only.

The subdivision is intentionally bounded: each failed cell is bisected along
the coordinate direction that most reduces the maximum hinge-coordinate
deviation of its children. This is a probe for the next closure strategy, not a
global cell-cover certificate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_tree021_p1p2_shared_edge_adaptive_probe_report.json"
SOURCE_COMPONENT_REPORT = "two_class_component_search_report.json"
SOURCE_DIRECT_OVERLAY_REPORT = "bounded_cell_shared_edge_common_edge_overlay_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P1", "P2")
MAX_DEPTH = 5
MAX_STORED_EXAMPLES = 80
SAT_TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_p0p2_theta_projection_component_bound_probe as theta_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_tree021_shared_edge_common_edge_guard as shared_edge  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402
import audit_historical_s4_bounded_cell_shared_edge_common_edge_overlay as direct_overlay  # noqa: E402

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


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def phi_interval_for_direction(direction_index: int) -> list[float]:
    left = 2.0 * math.pi * float(direction_index) / float(comp.DIRECTION_COUNT)
    right = 2.0 * math.pi * float(direction_index + 1) / float(comp.DIRECTION_COUNT)
    return [left, right]


def original_box(cell: dict) -> dict:
    return {
        "cell_id": cell["cell_id"],
        "base_cell_id": cell["cell_id"],
        "depth": 0,
        "split_history": [],
        "theta_interval_degrees": [float(value) for value in cell["theta_interval_degrees"]],
        "radial_interval_degrees": [float(value) for value in cell["radial_interval_degrees"]],
        "phi_interval_radians": phi_interval_for_direction(int(cell["direction_index"])),
        "kind": cell["kind"],
        "direction_sector": cell["direction_sector"],
    }


def all_tree021_boxes(source_audit: dict, cells: list[dict]) -> list[dict]:
    free_ids = protocol.free_node_ids(source_audit)
    return [
        original_box(cell)
        for cell in cells
        if all(node_id in free_ids for node_id in cell["vertex_node_ids"])
    ]


def sector_candidate_angles(phi_interval: list[float], coefficient_cos: float, coefficient_sin: float) -> list[float]:
    start, end = [float(value) for value in phi_interval]
    candidates = [start, end]
    amplitude = math.hypot(coefficient_cos, coefficient_sin)
    if amplitude <= lib.TOL:
        return candidates
    phase = math.atan2(coefficient_sin, coefficient_cos)
    for base in [phase, phase + math.pi]:
        low = math.floor((start - base) / (2.0 * math.pi)) - 1
        high = math.ceil((end - base) / (2.0 * math.pi)) + 1
        for offset in range(low, high + 1):
            candidate = base + 2.0 * math.pi * offset
            if start - 1.0e-12 <= candidate <= end + 1.0e-12:
                candidates.append(candidate)
    return sorted(set(round(value, 15) for value in candidates))


def offset_coordinate_range(
    e1_value: float,
    e2_value: float,
    radius_interval: list[float],
    phi_interval: list[float],
) -> tuple[float, float]:
    candidates = sector_candidate_angles(phi_interval, e1_value, e2_value)
    direction_values = [
        e1_value * math.cos(angle) + e2_value * math.sin(angle)
        for angle in candidates
    ]
    min_direction = min(direction_values)
    max_direction = max(direction_values)
    radius_left, radius_right = [float(value) for value in radius_interval]

    if min_direction < 0.0:
        offset_min = radius_right * min_direction
    else:
        offset_min = radius_left * min_direction
    if max_direction > 0.0:
        offset_max = radius_right * max_direction
    else:
        offset_max = radius_left * max_direction
    return float(offset_min), float(offset_max)


def theta_coordinate_range(sign: float, theta_interval: list[float]) -> tuple[float, float]:
    left, right = [float(value) for value in theta_interval]
    if sign >= 0.0:
        return left, right
    return -right, -left


def box_center_vector(tree: dict, signs_by_hinge: dict[str, int], box: dict) -> np.ndarray:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    e1, e2 = reps.transverse_basis(sign_vec)
    theta_center = sum(box["theta_interval_degrees"]) / 2.0
    radius_center = sum(box["radial_interval_degrees"]) / 2.0
    phi_center = sum(box["phi_interval_radians"]) / 2.0
    return sign_vec * theta_center + radius_center * (
        math.cos(phi_center) * e1 + math.sin(phi_center) * e2
    )


def box_angle_intervals(tree: dict, signs_by_hinge: dict[str, int], box: dict) -> dict[str, dict]:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    e1, e2 = reps.transverse_basis(sign_vec)
    center_vector = box_center_vector(tree, signs_by_hinge, box)
    output = {}
    for index, hinge_id in enumerate(tree["hinge_ids"]):
        theta_min, theta_max = theta_coordinate_range(sign_vec[index], box["theta_interval_degrees"])
        offset_min, offset_max = offset_coordinate_range(
            float(e1[index]),
            float(e2[index]),
            box["radial_interval_degrees"],
            box["phi_interval_radians"],
        )
        minimum = theta_min + offset_min
        maximum = theta_max + offset_max
        center = float(center_vector[index])
        max_deviation = max(abs(minimum - center), abs(maximum - center))
        output[hinge_id] = {
            "minimum_degrees": round(minimum, 12),
            "maximum_degrees": round(maximum, 12),
            "center_degrees": round(center, 12),
            "max_deviation_from_center_degrees": round(max_deviation, 12),
        }
    return output


def box_max_hinge_deviation(tree: dict, signs_by_hinge: dict[str, int], box: dict) -> float:
    intervals = box_angle_intervals(tree, signs_by_hinge, box)
    return max(float(item["max_deviation_from_center_degrees"]) for item in intervals.values())


def split_box(box: dict, dimension: str) -> list[dict]:
    if dimension == "theta":
        key = "theta_interval_degrees"
    elif dimension == "radius":
        key = "radial_interval_degrees"
    elif dimension == "phi":
        key = "phi_interval_radians"
    else:
        raise ValueError(f"Unknown split dimension: {dimension}")

    left, right = box[key]
    mid = (float(left) + float(right)) / 2.0
    children = []
    for child_index, interval in enumerate([[left, mid], [mid, right]]):
        child = dict(box)
        child[key] = interval
        child["depth"] = int(box["depth"]) + 1
        child["split_history"] = [*box["split_history"], dimension]
        child["cell_id"] = f"{box['cell_id']}_{dimension[0]}{child_index}"
        children.append(child)
    return children


def best_split_dimension(tree: dict, signs_by_hinge: dict[str, int], box: dict) -> str:
    candidates = {}
    for dimension in ["theta", "radius", "phi"]:
        children = split_box(box, dimension)
        candidates[dimension] = max(box_max_hinge_deviation(tree, signs_by_hinge, child) for child in children)
    return min(candidates, key=lambda key: (candidates[key], key))


def vertices_for_labels(
    transformed: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    piece_id: str,
    labels: list[str],
) -> list[np.ndarray]:
    return [transformed[piece_id][indices[piece_id][label]] for label in labels]


def common_edge_box_guard(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    box: dict,
) -> dict:
    center_vector = box_center_vector(tree, signs_by_hinge, box)
    center_degrees = reps.degrees_from_vector(tree, center_vector)
    intervals = box_angle_intervals(tree, signs_by_hinge, box)
    delta_by_hinge = {
        hinge_id: 2.0 * float(record["max_deviation_from_center_degrees"])
        for hinge_id, record in intervals.items()
    }
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    unit, axis_norm = shared_edge.common_edge_axis_unit(transformed, indices, TARGET_PAIR)
    if unit is None:
        return {
            "certified": False,
            "failure_reason": "degenerate_common_edge_axis",
            "axis_norm": rounded(axis_norm),
            "angle_coordinate_intervals_by_hinge": intervals,
        }

    state = shared_edge.support_state_for_pair(transformed, labels_by_piece, TARGET_PAIR, unit)
    if not state["separated_at_center"]:
        return {
            "certified": False,
            "failure_reason": "not_separated_at_center",
            "axis_name": shared_edge.COMMON_EDGE_AXIS_NAME,
            "axis_norm": rounded(axis_norm),
            "gap": state.get("gap"),
            "angle_coordinate_intervals_by_hinge": intervals,
            "center_angle_degrees_by_hinge": {key: round(value, 12) for key, value in center_degrees.items()},
        }

    lower_support, lower_non_support = sensitivity.piece_label_sets(
        labels_by_piece,
        state["lower_piece"],
        state["lower_support_labels"],
    )
    upper_support, upper_non_support = sensitivity.piece_label_sets(
        labels_by_piece,
        state["upper_piece"],
        state["upper_support_labels"],
    )

    def component(labels: list[str], piece_id: str, direction: str) -> float:
        return theta_probe.component_displacement_bound_for_labels(
            case,
            transforms,
            delta_by_hinge,
            paths_by_piece,
            vertices_for_labels(transformed, indices, piece_id, labels),
            piece_id,
            unit,
            direction,
        )

    lower_support_positive = component(lower_support, state["lower_piece"], "positive")
    upper_support_negative = component(upper_support, state["upper_piece"], "negative")
    lower_support_negative = component(lower_support, state["lower_piece"], "negative")
    lower_non_support_positive = component(lower_non_support, state["lower_piece"], "positive")
    upper_support_positive = component(upper_support, state["upper_piece"], "positive")
    upper_non_support_negative = component(upper_non_support, state["upper_piece"], "negative")

    signed_component_bound = lower_support_positive + upper_support_negative + SAT_TOLERANCE
    signed_component_margin = float(state["gap"]) - signed_component_bound
    lower_stability_margin = (
        float(state["lower_competition_margin"])
        - lower_support_negative
        - lower_non_support_positive
        - SAT_TOLERANCE
    )
    upper_stability_margin = (
        float(state["upper_competition_margin"])
        - upper_support_positive
        - upper_non_support_negative
        - SAT_TOLERANCE
    )
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
        "axis_name": shared_edge.COMMON_EDGE_AXIS_NAME,
        "axis_norm": rounded(axis_norm),
        "gap": rounded(float(state["gap"])),
        "signed_component_bound": rounded(signed_component_bound),
        "signed_component_margin": rounded(signed_component_margin),
        "minimum_stability_margin": rounded(minimum_stability_margin),
        "lower_piece": state["lower_piece"],
        "upper_piece": state["upper_piece"],
        "lower_support_labels": state["lower_support_labels"],
        "upper_support_labels": state["upper_support_labels"],
        "angle_coordinate_intervals_by_hinge": intervals,
        "center_angle_degrees_by_hinge": {key: round(value, 12) for key, value in center_degrees.items()},
        "max_hinge_coordinate_deviation_degrees": rounded(max(abs(value) for value in delta_by_hinge.values()) / 2.0),
    }


def compact_box(box: dict, guard: dict | None = None) -> dict:
    record = {
        "cell_id": box["cell_id"],
        "base_cell_id": box["base_cell_id"],
        "depth": box["depth"],
        "split_history": box["split_history"],
        "theta_interval_degrees": [round(float(value), 12) for value in box["theta_interval_degrees"]],
        "radial_interval_degrees": [round(float(value), 12) for value in box["radial_interval_degrees"]],
        "phi_interval_radians": [round(float(value), 12) for value in box["phi_interval_radians"]],
    }
    if guard is not None:
        record.update(
            {
                "certified": guard["certified"],
                "failure_reason": guard["failure_reason"],
                "gap": guard.get("gap"),
                "signed_component_bound": guard.get("signed_component_bound"),
                "signed_component_margin": guard.get("signed_component_margin"),
                "minimum_stability_margin": guard.get("minimum_stability_margin"),
                "max_hinge_coordinate_deviation_degrees": guard.get("max_hinge_coordinate_deviation_degrees"),
            }
        )
    return record


def audit_level(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    boxes: list[dict],
) -> tuple[dict, list[dict], list[dict]]:
    result_counts = Counter()
    split_counts = Counter()
    base_outcomes = defaultdict(Counter)
    margins = []
    failed_margins = []
    stability_values = []
    examples = defaultdict(list)
    remaining = []
    certified_boxes = []
    for box in boxes:
        guard = common_edge_box_guard(case, tree, signs_by_hinge, indices, labels_by_piece, paths_by_piece, box)
        key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
        result_counts[key] += 1
        base_outcomes[box["base_cell_id"]][key] += 1
        add_example(examples["certified" if guard["certified"] else "failed"], compact_box(box, guard))
        if guard.get("signed_component_margin") is not None:
            value = float(guard["signed_component_margin"])
            margins.append(value)
            if not guard["certified"]:
                failed_margins.append(value)
        if guard.get("minimum_stability_margin") is not None:
            stability_values.append(float(guard["minimum_stability_margin"]))
        if not guard["certified"]:
            split_dimension = best_split_dimension(tree, signs_by_hinge, box)
            split_counts[split_dimension] += 1
            remaining.append({**box, "recommended_split_dimension": split_dimension})
        else:
            certified_boxes.append(box)

    fully_covered_bases = sum(
        1
        for counter in base_outcomes.values()
        if sum(counter.values()) > 0 and sum(value for key, value in counter.items() if key != "certified") == 0
    )
    touched_bases = len(base_outcomes)
    report = {
        "input_box_count": len(boxes),
        "certified_box_count": result_counts.get("certified", 0),
        "failed_box_count": len(boxes) - result_counts.get("certified", 0),
        "touched_base_cell_count": touched_bases,
        "fully_covered_base_cell_count_at_this_level_only": fully_covered_bases,
        "result_counts": dict(result_counts.most_common()),
        "recommended_split_dimension_counts": dict(split_counts.most_common()),
        "signed_component_margin_quantiles": quantiles(margins),
        "failed_signed_component_margin_quantiles": quantiles(failed_margins),
        "minimum_stability_margin_quantiles": quantiles(stability_values),
        "examples": dict(examples),
    }
    return report, remaining, certified_boxes


def expand_remaining(tree: dict, signs_by_hinge: dict[str, int], remaining: list[dict]) -> list[dict]:
    children = []
    for box in remaining:
        dimension = box["recommended_split_dimension"]
        for child in split_box(box, dimension):
            children.append(child)
    return children


def build_report() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / SOURCE_COMPONENT_REPORT)
    direct_report = load_json(RESULTS_DIR / SOURCE_DIRECT_OVERLAY_REPORT)
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    signs = signs_by_tree[TARGET_TREE_ID]
    tree = comp.find_tree(case, TARGET_TREE_ID)
    labels_by_piece = classify.labels_by_piece(case)
    indices = shared_edge.label_indices(case)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    boxes = all_tree021_boxes(source_audit, protocol.iter_cells())

    level_reports = []
    current = boxes
    terminal_by_base: dict[str, Counter] = defaultdict(Counter)
    terminal_certified_box_count = 0
    terminal_failed_box_count = 0
    for depth in range(MAX_DEPTH + 1):
        level_report, remaining, certified_boxes = audit_level(case, tree, signs, indices, labels_by_piece, paths_by_piece, current)
        level_report["depth"] = depth
        level_reports.append(level_report)
        terminal_certified_box_count += len(certified_boxes)
        for box in certified_boxes:
            terminal_by_base[box["base_cell_id"]]["certified"] += 1
        if depth == MAX_DEPTH:
            terminal_failed_box_count = len(remaining)
            for box in remaining:
                terminal_by_base[box["base_cell_id"]]["failed"] += 1
            break
        current = expand_remaining(tree, signs, remaining)

    terminal_box_count = terminal_certified_box_count + terminal_failed_box_count
    fully_covered_base_count = sum(1 for counter in terminal_by_base.values() if counter.get("failed", 0) == 0)
    partially_covered_base_count = sum(1 for counter in terminal_by_base.values() if counter.get("failed", 0) > 0 and counter.get("certified", 0) > 0)
    zero_certified_base_count = sum(1 for counter in terminal_by_base.values() if counter.get("certified", 0) == 0)
    final_report = level_reports[-1]
    direct_tree = next(report for report in direct_report["tree_reports"] if report["tree_id"] == TARGET_TREE_ID)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_tree021_p1p2_shared_edge_adaptive_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_DIRECT_OVERLAY_REPORT}",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
            f"results/{CASE_ID}/tree021_shared_edge_common_edge_guard_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_edge",
            "max_depth": MAX_DEPTH,
            "split_policy": "bisect the coordinate dimension whose children minimize the maximum hinge-coordinate deviation",
        },
        "source_direct_overlay_tree_summary": direct_tree["summary_metrics"],
        "summary_metrics": {
            "base_pair_cell_count": len(boxes),
            "max_depth": MAX_DEPTH,
            "cumulative_evaluated_box_count": sum(level["input_box_count"] for level in level_reports),
            "terminal_box_count_at_max_depth": terminal_box_count,
            "terminal_certified_box_count_at_max_depth": terminal_certified_box_count,
            "terminal_failed_box_count_at_max_depth": terminal_failed_box_count,
            "terminal_box_coverage_fraction_at_max_depth": round(terminal_certified_box_count / terminal_box_count, 6) if terminal_box_count else 0.0,
            "fully_covered_base_pair_cell_count_at_max_depth": fully_covered_base_count,
            "partially_covered_base_pair_cell_count_at_max_depth": partially_covered_base_count,
            "zero_certified_base_pair_cell_count_at_max_depth": zero_certified_base_count,
            "adaptive_probe_closed_at_max_depth": terminal_failed_box_count == 0,
        },
        "level_reports": level_reports,
        "limitations": [
            "This is a bounded adaptive probe for TREE_021 P1-P2 only, not a closure of every residual shared-edge pair-cell.",
            "Base cells are split only up to the fixed max depth in this report.",
            "The result does not cover residual shared-face pair-cells, theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
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
                "level_summaries": [
                    {
                        "depth": level["depth"],
                        "input_box_count": level["input_box_count"],
                        "certified_box_count": level["certified_box_count"],
                        "failed_box_count": level["failed_box_count"],
                        "result_counts": level["result_counts"],
                        "recommended_split_dimension_counts": level["recommended_split_dimension_counts"],
                    }
                    for level in report["level_reports"]
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
