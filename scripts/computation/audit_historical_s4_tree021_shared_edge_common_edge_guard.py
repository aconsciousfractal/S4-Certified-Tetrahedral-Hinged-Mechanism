"""TREE_021 residual shared-edge common-edge guard.

This audit targets the residual shared-edge pair-segments left by the TREE_021
refined-edge interval guard:

- P0-P3: 329 uncovered pair-segments.
- P1-P2: 561 uncovered pair-segments.

Every uncovered midpoint uses the same named separator branch:
edge:M_AB-M_CD x M_AB-M_CD. The script replaces the old whole-piece radius
clearance bound with a support-extrema projection-component bound along that
common-edge separator, then uses adaptive refinement only for the pair-segments
that need smaller coordinate deltas.

This is finite adaptive evidence for the TREE_021 residual shared-edge backlog;
it is not a symbolic theorem and does not cover TREE_007 mirror transfer, the
closed theta=0 configuration, the full continuous component, or physical hinge
thickness/clearance.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree021_shared_edge_common_edge_guard_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIRS = [("P0", "P3"), ("P1", "P2")]
COMMON_EDGE_LABELS = ("M_AB", "M_CD")
COMMON_EDGE_AXIS_NAME = "edge:M_AB-M_CD x M_AB-M_CD"
SAT_TOLERANCE = 1.0e-8
SUPPORT_TOLERANCE = 1.0e-9
ADAPTIVE_THRESHOLDS_DEGREES = [
    0.25,
    0.125,
    0.0625,
    0.03125,
    0.015625,
    0.0078125,
]
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_p0p2_theta_projection_component_bound_probe as theta_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402

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


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def label_indices(case: dict) -> dict[str, dict[str, int]]:
    return {
        piece_id: {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(piece)
        }
        for piece_id, piece in case["pieces_by_id"].items()
    }


def point(transformed: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, label: str) -> np.ndarray:
    return transformed[piece_id][indices[piece_id][label]]


def common_edge_axis_unit(transformed: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], pair: tuple[str, str]) -> tuple[np.ndarray | None, float]:
    left, right = pair
    left_a = point(transformed, indices, left, COMMON_EDGE_LABELS[0])
    left_b = point(transformed, indices, left, COMMON_EDGE_LABELS[1])
    right_a = point(transformed, indices, right, COMMON_EDGE_LABELS[0])
    right_b = point(transformed, indices, right, COMMON_EDGE_LABELS[1])
    axis = np.cross(left_b - left_a, right_b - right_a)
    norm = float(np.linalg.norm(axis))
    if norm <= lib.TOL:
        return None, norm
    return axis / norm, norm


def projected_values(vertices: list[np.ndarray], labels: list[str], unit: np.ndarray) -> list[tuple[str, float]]:
    return [(label, float(np.dot(vertex, unit))) for label, vertex in zip(labels, vertices)]


def extremum_labels(values: list[tuple[str, float]], mode: str) -> tuple[list[str], float, float]:
    raw = [value for _label, value in values]
    if mode == "max":
        extreme = max(raw)
        support = [label for label, value in values if abs(value - extreme) <= SUPPORT_TOLERANCE]
        non_support = [value for label, value in values if label not in support]
        competition_margin = math.inf if not non_support else extreme - max(non_support)
        return support, extreme, competition_margin
    if mode == "min":
        extreme = min(raw)
        support = [label for label, value in values if abs(value - extreme) <= SUPPORT_TOLERANCE]
        non_support = [value for label, value in values if label not in support]
        competition_margin = math.inf if not non_support else min(non_support) - extreme
        return support, extreme, competition_margin
    raise ValueError(f"Unsupported extremum mode: {mode}")


def support_state_for_pair(
    transformed: dict[str, list[np.ndarray]],
    labels_by_piece: dict[str, list[str]],
    pair: tuple[str, str],
    unit: np.ndarray,
) -> dict:
    left_piece, right_piece = pair
    left_values = projected_values(transformed[left_piece], labels_by_piece[left_piece], unit)
    right_values = projected_values(transformed[right_piece], labels_by_piece[right_piece], unit)
    left_min = min(value for _label, value in left_values)
    left_max = max(value for _label, value in left_values)
    right_min = min(value for _label, value in right_values)
    right_max = max(value for _label, value in right_values)

    if left_max <= right_min:
        lower_piece = left_piece
        upper_piece = right_piece
        lower_values = left_values
        upper_values = right_values
        gap = right_min - left_max
    elif right_max <= left_min:
        lower_piece = right_piece
        upper_piece = left_piece
        lower_values = right_values
        upper_values = left_values
        gap = left_min - right_max
    else:
        gap = -(min(left_max, right_max) - max(left_min, right_min))
        return {"separated_at_center": False, "gap": rounded(max(0.0, gap))}

    lower_support, lower_extreme, lower_competition = extremum_labels(lower_values, "max")
    upper_support, upper_extreme, upper_competition = extremum_labels(upper_values, "min")
    return {
        "separated_at_center": True,
        "gap": rounded(gap),
        "lower_piece": lower_piece,
        "upper_piece": upper_piece,
        "lower_support_labels": lower_support,
        "upper_support_labels": upper_support,
        "lower_extreme_projection": rounded(lower_extreme),
        "upper_extreme_projection": rounded(upper_extreme),
        "lower_competition_margin": rounded(lower_competition),
        "upper_competition_margin": rounded(upper_competition),
    }


def vertices_for_labels(
    transformed: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    piece_id: str,
    labels: list[str],
) -> list[np.ndarray]:
    return [transformed[piece_id][indices[piece_id][label]] for label in labels]


def segment_delta(left: np.ndarray, right: np.ndarray) -> dict:
    delta = np.asarray(right, dtype=float) - np.asarray(left, dtype=float)
    return {
        "euclidean_degrees": rounded(float(np.linalg.norm(delta))),
        "max_coordinate_degrees": rounded(float(max(abs(value) for value in delta))),
    }


def vector_to_degrees(tree: dict, vector: np.ndarray) -> dict[str, float]:
    return {hinge_id: float(value) for hinge_id, value in zip(tree["hinge_ids"], vector)}


def old_clearance_guard_uncertified(
    case: dict,
    tree: dict,
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    left: np.ndarray,
    right: np.ndarray,
    pair: tuple[str, str],
) -> dict:
    center = (left + right) / 2.0
    left_degrees = vector_to_degrees(tree, left)
    right_degrees = vector_to_degrees(tree, right)
    center_degrees = vector_to_degrees(tree, center)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    best = classify.best_named_axis(transformed[pair[0]], transformed[pair[1]], labels_by_piece[pair[0]], labels_by_piece[pair[1]])
    displacement_bounds = probe.piece_displacement_bounds_for_segment(
        case,
        tree,
        transforms,
        transformed,
        delta_by_hinge,
        paths_by_piece,
    )
    guard_bound = displacement_bounds[pair[0]] + displacement_bounds[pair[1]] + SAT_TOLERANCE
    post_guard = best["center_axis_overlap"] + guard_bound
    return {
        "uncertified": post_guard > SAT_TOLERANCE,
        "best_axis_name": best["axis_name"],
        "center_axis_overlap": rounded(best["center_axis_overlap"]),
        "guard_bound": rounded(guard_bound),
        "post_guard_overlap_bound": rounded(post_guard),
        "guard_margin": rounded(SAT_TOLERANCE - post_guard),
    }


def common_edge_component_guard(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    left: np.ndarray,
    right: np.ndarray,
    pair: tuple[str, str],
) -> dict:
    center = (left + right) / 2.0
    left_degrees = vector_to_degrees(tree, left)
    right_degrees = vector_to_degrees(tree, right)
    center_degrees = vector_to_degrees(tree, center)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    unit, axis_norm = common_edge_axis_unit(transformed, indices, pair)
    if unit is None:
        return {
            "certified": False,
            "failure_reason": "degenerate_common_edge_axis",
            "axis_norm": rounded(axis_norm),
            "delta": segment_delta(left, right),
        }

    state = support_state_for_pair(transformed, labels_by_piece, pair, unit)
    if not state["separated_at_center"]:
        return {
            "certified": False,
            "failure_reason": "not_separated_at_center",
            "axis_name": COMMON_EDGE_AXIS_NAME,
            "axis_norm": rounded(axis_norm),
            "gap": state.get("gap"),
            "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
            "delta": segment_delta(left, right),
        }

    lower_support, lower_non_support = sensitivity.piece_label_sets(labels_by_piece, state["lower_piece"], state["lower_support_labels"])
    upper_support, upper_non_support = sensitivity.piece_label_sets(labels_by_piece, state["upper_piece"], state["upper_support_labels"])

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

    # The gap can close only if the lower maximum moves positive or the upper minimum moves negative.
    lower_support_positive = component(lower_support, state["lower_piece"], "positive")
    upper_support_negative = component(upper_support, state["upper_piece"], "negative")

    # Support/extrema stability mirrors the P0-P2 projection-component guard.
    lower_support_negative = component(lower_support, state["lower_piece"], "negative")
    lower_non_support_positive = component(lower_non_support, state["lower_piece"], "positive")
    upper_support_positive = component(upper_support, state["upper_piece"], "positive")
    upper_non_support_negative = component(upper_non_support, state["upper_piece"], "negative")

    signed_component_bound = lower_support_positive + upper_support_negative + SAT_TOLERANCE
    signed_component_margin = float(state["gap"]) - signed_component_bound
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
        "axis_name": COMMON_EDGE_AXIS_NAME,
        "axis_norm": rounded(axis_norm),
        "gap": rounded(float(state["gap"])),
        "signed_component_bound": rounded(signed_component_bound),
        "signed_component_margin": rounded(signed_component_margin),
        "minimum_stability_margin": rounded(minimum_stability_margin),
        "lower_piece": state["lower_piece"],
        "upper_piece": state["upper_piece"],
        "lower_support_labels": state["lower_support_labels"],
        "upper_support_labels": state["upper_support_labels"],
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "delta": segment_delta(left, right),
    }


def subdivide_vector_segment(left: np.ndarray, right: np.ndarray, threshold_degrees: float) -> list[tuple[np.ndarray, np.ndarray]]:
    delta = max(abs(float(a - b)) for a, b in zip(left, right))
    segment_count = max(1, math.ceil(delta / float(threshold_degrees)))
    output = []
    previous = left
    for step in range(1, segment_count + 1):
        t = float(step) / float(segment_count)
        current = (1.0 - t) * left + t * right
        output.append((previous, current))
        previous = current
    return output


def source_edge_descriptor(nodes_by_id: dict[str, dict], node_ids: list[str]) -> dict:
    return classify.source_edge_descriptor(nodes_by_id, node_ids)


def compact_child(child: dict) -> dict:
    return {
        "shared_edge_child_id": child["shared_edge_child_id"],
        "parent_segment_id": child["parent_segment_id"],
        "source_edge_index": child["source_edge_index"],
        "source_node_ids": child["source_node_ids"],
        "source_edge": child["source_edge"],
        "pair": list(child["pair"]),
        "previous_best_axis_name": child["previous_best_axis_name"],
        "previous_guard_margin": child["previous_guard_margin"],
    }


def compact_leaf(child: dict, leaf_index: int, guard: dict) -> dict:
    return {
        **compact_child(child),
        "leaf_index": leaf_index,
        "certified": guard["certified"],
        "failure_reason": guard["failure_reason"],
        "gap": guard.get("gap"),
        "signed_component_bound": guard.get("signed_component_bound"),
        "signed_component_margin": guard.get("signed_component_margin"),
        "minimum_stability_margin": guard.get("minimum_stability_margin"),
        "delta": guard.get("delta"),
        "center_angle_degrees_by_hinge": guard.get("center_angle_degrees_by_hinge"),
    }


def reconstruct_shared_edge_backlog(
    case: dict,
    tree: dict,
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    segments: list[dict],
    nodes_by_id: dict[str, dict],
) -> tuple[list[dict], dict]:
    children = []
    old_axis_counts = Counter()
    by_pair = Counter()
    by_source_kind = Counter()
    by_theta_pair = Counter()
    guard_margins = []
    for segment in segments:
        edge_info = source_edge_descriptor(nodes_by_id, segment["source_node_ids"])
        for pair in TARGET_PAIRS:
            old = old_clearance_guard_uncertified(
                case,
                tree,
                labels_by_piece,
                paths_by_piece,
                segment["left_vector"],
                segment["right_vector"],
                pair,
            )
            if not old["uncertified"]:
                continue
            old_axis_counts[old["best_axis_name"]] += 1
            by_pair["-".join(pair)] += 1
            by_source_kind[edge_info["kind"]] += 1
            by_theta_pair[edge_info["theta_pair"]] += 1
            guard_margins.append(float(old["guard_margin"]))
            children.append(
                {
                    "shared_edge_child_id": f"edge_{len(children):04d}",
                    "parent_segment_id": f"seg_{segment['refined_segment_index']:05d}",
                    "source_edge_index": segment["source_edge_index"],
                    "source_node_ids": segment["source_node_ids"],
                    "source_edge": edge_info,
                    "pair": pair,
                    "previous_best_axis_name": old["best_axis_name"],
                    "previous_guard_margin": old["guard_margin"],
                    "left_vector": segment["left_vector"],
                    "right_vector": segment["right_vector"],
                }
            )
    return children, {
        "input_shared_edge_pair_segment_count": len(children),
        "input_counts_by_pair": dict(by_pair.most_common()),
        "previous_best_axis_counts": dict(old_axis_counts.most_common()),
        "source_edge_kind_counts": dict(by_source_kind.most_common()),
        "source_theta_pair_counts": dict(by_theta_pair.most_common()),
        "previous_guard_margin_quantiles": quantiles(guard_margins),
    }


def audit_original_guard(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    children: list[dict],
) -> dict:
    result_counts = Counter()
    pair_counts = defaultdict(Counter)
    margins = []
    stability_margins = []
    examples = defaultdict(list)
    for child in children:
        guard = common_edge_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, child["left_vector"], child["right_vector"], child["pair"])
        key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
        result_counts[key] += 1
        pair_counts["-".join(child["pair"])][key] += 1
        if guard.get("signed_component_margin") is not None:
            margins.append(float(guard["signed_component_margin"]))
        if guard.get("minimum_stability_margin") is not None:
            stability_margins.append(float(guard["minimum_stability_margin"]))
        add_example(examples["certified" if guard["certified"] else "failed"], compact_leaf(child, 0, guard))
    return {
        "input_child_count": len(children),
        "result_counts": dict(result_counts.most_common()),
        "result_counts_by_pair": {pair: dict(counter.most_common()) for pair, counter in sorted(pair_counts.items())},
        "signed_component_margin_quantiles": quantiles(margins),
        "minimum_stability_margin_quantiles": quantiles(stability_margins),
        "examples": dict(examples),
    }


def audit_refinement_level(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    children: list[dict],
    threshold_degrees: float,
) -> dict:
    leaf_counts = Counter()
    child_outcomes = Counter()
    pair_child_outcomes = defaultdict(Counter)
    pair_leaf_counts = defaultdict(Counter)
    margins = []
    certified_margins = []
    failed_margins = []
    stability_margins = []
    child_reports = []
    examples = defaultdict(list)

    for child in children:
        leaf_total = 0
        leaf_certified = 0
        child_leaf_counts = Counter()
        child_margins = []
        for leaf_index, (left, right) in enumerate(subdivide_vector_segment(child["left_vector"], child["right_vector"], threshold_degrees)):
            leaf_total += 1
            guard = common_edge_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, left, right, child["pair"])
            key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
            leaf_counts[key] += 1
            pair_leaf_counts["-".join(child["pair"])][key] += 1
            child_leaf_counts[key] += 1
            if guard.get("signed_component_margin") is not None:
                value = float(guard["signed_component_margin"])
                margins.append(value)
                child_margins.append(value)
                if guard["certified"]:
                    certified_margins.append(value)
                else:
                    failed_margins.append(value)
            if guard.get("minimum_stability_margin") is not None:
                stability_margins.append(float(guard["minimum_stability_margin"]))
            if guard["certified"]:
                leaf_certified += 1
                add_example(examples["certified_leaves"], compact_leaf(child, leaf_index, guard))
            else:
                add_example(examples["failed_leaves"], compact_leaf(child, leaf_index, guard))

        if leaf_certified == leaf_total:
            outcome = "fully_covered"
        elif leaf_certified == 0:
            outcome = "zero_leaf_covered"
        else:
            outcome = "partially_covered"
        child_outcomes[outcome] += 1
        pair_child_outcomes["-".join(child["pair"])][outcome] += 1
        child_reports.append(
            {
                **compact_child(child),
                "leaf_total": leaf_total,
                "leaf_certified": leaf_certified,
                "outcome": outcome,
                "leaf_result_counts": dict(child_leaf_counts.most_common()),
                "signed_component_margin_interval": [
                    None if not child_margins else rounded(min(child_margins)),
                    None if not child_margins else rounded(max(child_margins)),
                ],
            }
        )

    return {
        "threshold_degrees": threshold_degrees,
        "input_child_count": len(children),
        "leaf_subsegment_count": sum(report["leaf_total"] for report in child_reports),
        "leaf_certified_count": sum(report["leaf_certified"] for report in child_reports),
        "leaf_uncovered_count": sum(report["leaf_total"] - report["leaf_certified"] for report in child_reports),
        "child_outcome_counts": dict(child_outcomes.most_common()),
        "child_outcome_counts_by_pair": {pair: dict(counter.most_common()) for pair, counter in sorted(pair_child_outcomes.items())},
        "leaf_result_counts": dict(leaf_counts.most_common()),
        "leaf_result_counts_by_pair": {pair: dict(counter.most_common()) for pair, counter in sorted(pair_leaf_counts.items())},
        "signed_component_margin_quantiles": quantiles(margins),
        "certified_signed_component_margin_quantiles": quantiles(certified_margins),
        "failed_signed_component_margin_quantiles": quantiles(failed_margins),
        "minimum_stability_margin_quantiles": quantiles(stability_margins),
        "child_reports": child_reports,
        "examples": dict(examples),
    }


def adaptive_ladder(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    children: list[dict],
) -> dict:
    remaining = children[:]
    levels = []
    first_cover_records = []
    first_cover_counts = Counter()
    for threshold in ADAPTIVE_THRESHOLDS_DEGREES:
        level = audit_refinement_level(case, tree, indices, labels_by_piece, paths_by_piece, remaining, threshold)
        levels.append(level)
        hard_ids = set()
        by_id = {child["shared_edge_child_id"]: child for child in remaining}
        for child_report in level["child_reports"]:
            child_id = child_report["shared_edge_child_id"]
            if child_report["outcome"] == "fully_covered":
                first_cover_counts[str(threshold)] += 1
                first_cover_records.append(
                    {
                        **compact_child(by_id[child_id]),
                        "covered_at_threshold_degrees": threshold,
                        "leaf_total": child_report["leaf_total"],
                        "leaf_certified": child_report["leaf_certified"],
                        "signed_component_margin_interval": child_report["signed_component_margin_interval"],
                    }
                )
            else:
                hard_ids.add(child_id)
        remaining = [child for child in remaining if child["shared_edge_child_id"] in hard_ids]
        if not remaining:
            break

    adaptive_leaf_count = sum(record["leaf_total"] for record in first_cover_records)
    adaptive_certified_leaf_count = sum(record["leaf_certified"] for record in first_cover_records)
    return {
        "adaptive_completed": not remaining,
        "adaptive_leaf_subsegment_count": adaptive_leaf_count,
        "adaptive_certified_leaf_subsegment_count": adaptive_certified_leaf_count,
        "adaptive_uncovered_leaf_subsegment_count": adaptive_leaf_count - adaptive_certified_leaf_count,
        "remaining_child_count": len(remaining),
        "first_cover_counts_by_threshold": dict(first_cover_counts),
        "first_cover_counts_by_pair": dict(Counter("-".join(record["pair"]) for record in first_cover_records).most_common()),
        "first_cover_records": first_cover_records,
        "remaining_children": [compact_child(child) for child in remaining],
        "level_reports": levels,
    }


def build_report() -> dict:
    case = batch.build_case()
    component_report = probe.load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    labels_by_piece = classify.labels_by_piece(case)
    indices = label_indices(case)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    nodes_by_id = probe.bounded.all_nodes_by_id(tree, signs_by_tree[TARGET_TREE_ID])
    _, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)

    children, reconstruction = reconstruct_shared_edge_backlog(case, tree, labels_by_piece, paths_by_piece, segments, nodes_by_id)
    original_guard = audit_original_guard(case, tree, indices, labels_by_piece, paths_by_piece, children)
    adaptive = adaptive_ladder(case, tree, indices, labels_by_piece, paths_by_piece, children)

    return {
        "case_id": CASE_ID,
        "status": "tree021_shared_edge_common_edge_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/refined_edge_interval_guard_probe_report.json",
            f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pairs": [list(pair) for pair in TARGET_PAIRS],
            "role": "residual_shared_edge",
            "common_edge_axis_name": COMMON_EDGE_AXIS_NAME,
            "adaptive_thresholds_degrees": ADAPTIVE_THRESHOLDS_DEGREES,
        },
        "summary_metrics": {
            "input_shared_edge_pair_segment_count": len(children),
            "input_p0_p3_pair_segment_count": reconstruction["input_counts_by_pair"].get("P0-P3", 0),
            "input_p1_p2_pair_segment_count": reconstruction["input_counts_by_pair"].get("P1-P2", 0),
            "direct_common_edge_certified_count": original_guard["result_counts"].get("certified", 0),
            "adaptive_completed": adaptive["adaptive_completed"],
            "adaptive_leaf_subsegment_count": adaptive["adaptive_leaf_subsegment_count"],
            "adaptive_certified_leaf_subsegment_count": adaptive["adaptive_certified_leaf_subsegment_count"],
            "adaptive_uncovered_leaf_subsegment_count": adaptive["adaptive_uncovered_leaf_subsegment_count"],
        },
        "reconstruction": reconstruction,
        "original_common_edge_guard_report": original_guard,
        "adaptive_summary": {
            key: value
            for key, value in adaptive.items()
            if key not in {"level_reports"}
        },
        "adaptive_level_reports": adaptive["level_reports"],
        "limitations": [
            "This is a finite adaptive guard for TREE_021 P0-P3/P1-P2 residual shared-edge pair-segments, not a symbolic theorem.",
            "The guard covers replacement leaves for the original shared-edge backlog by adaptive subdivision; it does not certify arbitrary continuous paths outside this finite ledger.",
            "TREE_007 mirror transfer, theta=0, the full continuous 3-parameter component, and physical hinge thickness/clearance remain outside this report.",
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
                "first_cover_counts_by_threshold": report["adaptive_summary"]["first_cover_counts_by_threshold"],
                "first_cover_counts_by_pair": report["adaptive_summary"]["first_cover_counts_by_pair"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())