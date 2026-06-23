"""TREE_021 P0-P2 same-branch support-bound probe.

The previous failure classification showed that the 0.625-degree P0-P2
edge-branch failures are dominated by same-assigned edge-edge branches. This
script probes a tighter fixed-axis guard for that dominant class.

For each same-branch failed subsegment, it uses the midpoint branch SAT axis,
identifies the projection-extremal support vertices, and compares two guards:

1. support_only: only the support vertices need to absorb motion along the fixed
   axis;
2. stable_support: support_only plus a stability check that non-support vertices
   cannot overtake the support extrema under their own local displacement bound.

The stable_support guard is still finite numeric engineering evidence. It is not
a symbolic formula and it does not cover axis-switch, face-normal, shared-edge,
TREE_007, or physical-thickness cases.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_same_branch_support_bound_probe_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
TARGET_MAX_COORDINATE_DELTA_DEGREES = 0.625
SUPPORT_TOLERANCE = 1.0e-8
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 24

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as probe  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_failure_classification as failure_classification  # noqa: E402

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


def branch_axis_unit(transformed: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], branch_name: str) -> np.ndarray:
    left_labels, right_labels = probe.branch_edges(branch_name)
    left_a = probe.point(transformed, indices, TARGET_PAIR[0], left_labels[0])
    left_b = probe.point(transformed, indices, TARGET_PAIR[0], left_labels[1])
    right_a = probe.point(transformed, indices, TARGET_PAIR[1], right_labels[0])
    right_b = probe.point(transformed, indices, TARGET_PAIR[1], right_labels[1])
    axis = np.cross(left_b - left_a, right_b - right_a)
    norm = float(np.linalg.norm(axis))
    if norm <= lib.TOL:
        raise ValueError(f"degenerate branch axis: {branch_name}")
    return axis / norm


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


def support_state(
    transformed: dict[str, list[np.ndarray]],
    labels_by_piece: dict[str, list[str]],
    unit: np.ndarray,
) -> dict:
    left_piece, right_piece = TARGET_PAIR
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
        lower_mode = "max"
        upper_mode = "min"
        gap = right_min - left_max
    elif right_max <= left_min:
        lower_piece = right_piece
        upper_piece = left_piece
        lower_values = right_values
        upper_values = left_values
        lower_mode = "max"
        upper_mode = "min"
        gap = left_min - right_max
    else:
        lower_piece = None
        upper_piece = None
        lower_values = []
        upper_values = []
        lower_mode = None
        upper_mode = None
        gap = -(
            min(left_max, right_max) - max(left_min, right_min)
        )

    if lower_piece is None or upper_piece is None:
        return {
            "separated_at_center": False,
            "gap": rounded(max(0.0, gap)),
        }

    lower_support, lower_extreme, lower_competition = extremum_labels(lower_values, lower_mode)
    upper_support, upper_extreme, upper_competition = extremum_labels(upper_values, upper_mode)
    return {
        "separated_at_center": True,
        "gap": rounded(gap),
        "lower_piece": lower_piece,
        "upper_piece": upper_piece,
        "lower_mode": lower_mode,
        "upper_mode": upper_mode,
        "lower_support_labels": lower_support,
        "upper_support_labels": upper_support,
        "lower_extreme_projection": rounded(lower_extreme),
        "upper_extreme_projection": rounded(upper_extreme),
        "lower_competition_margin": rounded(lower_competition),
        "upper_competition_margin": rounded(upper_competition),
    }


def vertices_for_labels(transformed: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, labels: list[str]) -> list[np.ndarray]:
    return [transformed[piece_id][indices[piece_id][label]] for label in labels]


def displacement_bound_for_labels(
    case: dict,
    transforms: dict[str, dict[str, np.ndarray]],
    delta_by_hinge: dict[str, float],
    paths_by_piece: dict[str, list[dict]],
    vertices: list[np.ndarray],
    piece_id: str,
) -> float:
    if not vertices:
        return 0.0
    displacement = 0.0
    for hinge in paths_by_piece[piece_id]:
        hinge_id = hinge["hinge_id"]
        half_angle_radians = math.radians(abs(float(delta_by_hinge[hinge_id])) / 2.0)
        if half_angle_radians <= 0.0:
            continue
        axis_side = hinge["pieces"][0]
        transform = transforms[axis_side]
        axis_a = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][0]])
        axis_b = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][1]])
        max_distance = max(probe.ray_guard.point_line_distance(vertex, axis_a, axis_b) for vertex in vertices)
        displacement += 2.0 * max_distance * math.sin(half_angle_radians / 2.0)
    return probe.ray_guard.DISPLACEMENT_SAFETY_FACTOR * displacement


def piece_label_sets(labels_by_piece: dict[str, list[str]], piece_id: str, support_labels: list[str]) -> tuple[list[str], list[str]]:
    support = list(support_labels)
    support_set = set(support)
    non_support = [label for label in labels_by_piece[piece_id] if label not in support_set]
    return support, non_support


def evaluate_support_guard(
    case: dict,
    tree: dict,
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    left: np.ndarray,
    right: np.ndarray,
    branch_name: str,
    original_context: dict,
) -> dict:
    center = (left + right) / 2.0
    left_degrees = vector_to_degrees(tree, left)
    right_degrees = vector_to_degrees(tree, right)
    center_degrees = vector_to_degrees(tree, center)
    delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
    transforms = probe.ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    unit = branch_axis_unit(transformed, indices, branch_name)
    state = support_state(transformed, labels_by_piece, unit)
    if not state["separated_at_center"]:
        return {
            **state,
            "support_only_certified": False,
            "stable_support_certified": False,
        }

    lower_support, lower_non_support = piece_label_sets(labels_by_piece, state["lower_piece"], state["lower_support_labels"])
    upper_support, upper_non_support = piece_label_sets(labels_by_piece, state["upper_piece"], state["upper_support_labels"])

    lower_support_bound = displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        vertices_for_labels(transformed, indices, state["lower_piece"], lower_support),
        state["lower_piece"],
    )
    upper_support_bound = displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        vertices_for_labels(transformed, indices, state["upper_piece"], upper_support),
        state["upper_piece"],
    )
    lower_non_support_bound = displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        vertices_for_labels(transformed, indices, state["lower_piece"], lower_non_support),
        state["lower_piece"],
    )
    upper_non_support_bound = displacement_bound_for_labels(
        case,
        transforms,
        delta_by_hinge,
        paths_by_piece,
        vertices_for_labels(transformed, indices, state["upper_piece"], upper_non_support),
        state["upper_piece"],
    )

    support_guard_bound = lower_support_bound + upper_support_bound + SAT_TOLERANCE
    support_margin = float(state["gap"]) - support_guard_bound
    lower_stability_margin = float(state["lower_competition_margin"]) - lower_support_bound - lower_non_support_bound - SAT_TOLERANCE
    upper_stability_margin = float(state["upper_competition_margin"]) - upper_support_bound - upper_non_support_bound - SAT_TOLERANCE
    extrema_stable = lower_stability_margin >= 0.0 and upper_stability_margin >= 0.0
    support_only_certified = support_margin >= 0.0
    stable_support_certified = support_only_certified and extrema_stable

    return {
        **state,
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "delta": probe.segment_delta(left, right),
        "original_branch_gap": original_context["branch_gap"],
        "original_guard_bound": original_context["guard_bound"],
        "original_margin": original_context["branch_lower_bound_margin"],
        "support_guard_bound": rounded(support_guard_bound),
        "support_margin": rounded(support_margin),
        "lower_support_bound": rounded(lower_support_bound),
        "upper_support_bound": rounded(upper_support_bound),
        "lower_non_support_bound": rounded(lower_non_support_bound),
        "upper_non_support_bound": rounded(upper_non_support_bound),
        "lower_stability_margin": rounded(lower_stability_margin),
        "upper_stability_margin": rounded(upper_stability_margin),
        "extrema_stable": extrema_stable,
        "support_only_certified": support_only_certified,
        "stable_support_certified": stable_support_certified,
        "guard_improvement_factor": rounded(original_context["guard_bound"] / support_guard_bound, 6) if support_guard_bound > 0.0 else None,
    }


def compact_record(parent: dict, sub_index: int, support: dict, relation: str) -> dict:
    return {
        "parent_segment_id": f"seg_{parent['refined_segment_index']:05d}",
        "source_edge_index": parent["source_edge_index"],
        "source_node_ids": parent["source_node_ids"],
        "assigned_branch_name": parent["assigned_branch_name"],
        "subsegment_index": sub_index,
        "axis_relation": relation,
        "center_angle_degrees_by_hinge": support.get("center_angle_degrees_by_hinge"),
        "delta": support.get("delta"),
        "gap": support.get("gap"),
        "lower_piece": support.get("lower_piece"),
        "upper_piece": support.get("upper_piece"),
        "lower_support_labels": support.get("lower_support_labels"),
        "upper_support_labels": support.get("upper_support_labels"),
        "lower_competition_margin": support.get("lower_competition_margin"),
        "upper_competition_margin": support.get("upper_competition_margin"),
        "original_guard_bound": support.get("original_guard_bound"),
        "support_guard_bound": support.get("support_guard_bound"),
        "support_margin": support.get("support_margin"),
        "lower_stability_margin": support.get("lower_stability_margin"),
        "upper_stability_margin": support.get("upper_stability_margin"),
        "extrema_stable": support.get("extrema_stable"),
        "support_only_certified": support.get("support_only_certified"),
        "stable_support_certified": support.get("stable_support_certified"),
        "guard_improvement_factor": support.get("guard_improvement_factor"),
    }


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def build_report() -> dict:
    case = probe.batch.build_case()
    tree = probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = probe.comp.certified_signs_by_tree()
    paths_by_piece = probe.ray_guard.tree_paths_from_root(case, tree)
    indices = probe.label_indices(case)
    labels_by_piece = probe.classify.labels_by_piece(case)
    parents = probe.parent_branch_segments(case, tree, indices, paths_by_piece, signs_by_tree)

    same_branch_failed_count = 0
    support_only_count = 0
    stable_count = 0
    stable_support_count = 0
    support_only_unstable_count = 0
    unstable_count = 0
    branch_counts = Counter()
    lower_upper_counts = Counter()
    support_label_counts = Counter()
    remaining_reason_counts = Counter()
    improvement_factors = []
    original_guards = []
    support_guards = []
    support_margins = []
    stability_margins = []

    stable_examples = []
    support_only_unstable_examples = []
    remaining_examples = []
    largest_improvement_examples = []

    for parent in parents:
        branch = parent["assigned_branch_name"]
        for sub_index, (left, right) in enumerate(probe.subdivide_segment(parent, TARGET_MAX_COORDINATE_DELTA_DEGREES)):
            context = probe.midpoint_context(case, tree, indices, paths_by_piece, left, right, branch)
            if context["branch_lower_bound_certified"]:
                continue
            relation = failure_classification.axis_relation(context, branch)
            if relation != "same_assigned_edge_branch":
                continue
            same_branch_failed_count += 1
            branch_counts[branch] += 1
            support = evaluate_support_guard(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch, context)
            record = compact_record(parent, sub_index, support, relation)

            if support.get("guard_improvement_factor") is not None:
                improvement_factors.append(float(support["guard_improvement_factor"]))
            if support.get("original_guard_bound") is not None:
                original_guards.append(float(support["original_guard_bound"]))
            if support.get("support_guard_bound") is not None:
                support_guards.append(float(support["support_guard_bound"]))
            if support.get("support_margin") is not None:
                support_margins.append(float(support["support_margin"]))
            if support.get("lower_stability_margin") is not None and support.get("upper_stability_margin") is not None:
                stability_margins.append(min(float(support["lower_stability_margin"]), float(support["upper_stability_margin"])))

            if support.get("separated_at_center"):
                lower_upper_counts[(support["lower_piece"], support["upper_piece"])] += 1
                support_label_counts[(tuple(support["lower_support_labels"]), tuple(support["upper_support_labels"]))] += 1
            if support.get("support_only_certified"):
                support_only_count += 1
            if support.get("extrema_stable"):
                stable_count += 1
            else:
                unstable_count += 1
            if support.get("stable_support_certified"):
                stable_support_count += 1
                add_example(stable_examples, record)
            elif support.get("support_only_certified"):
                support_only_unstable_count += 1
                add_example(support_only_unstable_examples, record)
                remaining_reason_counts["support_passed_but_extrema_unstable"] += 1
            else:
                add_example(remaining_examples, record)
                if not support.get("extrema_stable"):
                    remaining_reason_counts["support_margin_failed_and_extrema_unstable"] += 1
                else:
                    remaining_reason_counts["support_margin_failed"] += 1

            if record.get("guard_improvement_factor") is not None:
                largest_improvement_examples.append(record)
                largest_improvement_examples.sort(key=lambda item: item.get("guard_improvement_factor") or 0.0, reverse=True)
                del largest_improvement_examples[MAX_STORED_EXAMPLES:]

    return {
        "case_id": CASE_ID,
        "status": "p0p2_same_branch_support_bound_probe_completed",
        "source_report": f"results/{CASE_ID}/p0p2_edge_branch_failure_classification_report.json",
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "target_max_coordinate_delta_degrees": TARGET_MAX_COORDINATE_DELTA_DEGREES,
        "guard_rule": "fixed midpoint branch axis; support-only displacement plus support-extrema stability against non-support vertices",
        "summary_metrics": {
            "same_branch_failed_subsegment_count": same_branch_failed_count,
            "support_only_certified_count": support_only_count,
            "support_extrema_stable_count": stable_count,
            "stable_support_certified_count": stable_support_count,
            "support_only_certified_but_unstable_count": support_only_unstable_count,
            "unstable_support_extrema_count": unstable_count,
            "remaining_after_stable_support_count": same_branch_failed_count - stable_support_count,
        },
        "same_branch_failed_by_assigned_branch": dict(branch_counts.most_common()),
        "lower_upper_piece_counts": {f"{left}->{right}": count for (left, right), count in lower_upper_counts.most_common()},
        "support_label_pair_counts": {f"{list(lower)} | {list(upper)}": count for (lower, upper), count in support_label_counts.most_common()},
        "remaining_reason_counts": dict(remaining_reason_counts.most_common()),
        "quantiles": {
            "original_guard_bounds": quantiles(original_guards),
            "support_guard_bounds": quantiles(support_guards),
            "support_margins": quantiles(support_margins),
            "minimum_stability_margins": quantiles(stability_margins),
            "guard_improvement_factors": quantiles(improvement_factors),
        },
        "examples": {
            "stable_support_certified": stable_examples,
            "support_only_certified_but_unstable": support_only_unstable_examples,
            "remaining_after_stable_support": remaining_examples,
            "largest_guard_improvements": largest_improvement_examples,
        },
        "limitations": [
            "This is finite numeric support-bound evidence, not a symbolic branch formula derivation.",
            "The stable_support guard is a fixed-axis support-extrema guard; it does not cover axis-switch failures.",
            "The report covers only TREE_021 P0-P2 same-assigned edge-edge branch failures at max coordinate delta 0.625 degrees.",
            "Face-normal switches, other target-branch switches, residual shared-edge pairs, TREE_007, and physical hinge thickness/clearance remain outside this report.",
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
                "remaining_reason_counts": report["remaining_reason_counts"],
                "guard_improvement_quantiles": report["quantiles"]["guard_improvement_factors"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())