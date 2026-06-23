"""TREE_007 P2-P3 edge-edge projection-component bound probe.

This probe follows the P2-P3 edge-branch refinement-sensitivity report. It starts
from the 1125 residual 0.625-degree edge-branch leaves and evaluates their
0.15625-degree children. The previous support guard used a norm displacement
bound for support vertices; this probe replaces that term with a signed
component bound along the fixed branch separator axis.

This remains finite numeric evidence for the selected edge-branch workflow. It
does not cover the P2-P3 face-normal parent branches.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import re
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_p2p3_edge_branch_projection_component_bound_probe_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIR = ("P2", "P3")
TARGET_REFINEMENT_DELTA_DEGREES = 0.15625
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 48
NODE_RE = re.compile(r"^t(?P<t>[^:]+):r(?P<r>[^:]+):d(?P<d>.+)$")

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_tree007_p2p3_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_tree007_p2p3_edge_branch_refinement_sensitivity_probe as sensitivity  # noqa: E402
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


def top_counter(counter: Counter, limit: int = 24) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


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


def unit_axis(axis_a: np.ndarray, axis_b: np.ndarray) -> np.ndarray:
    axis = axis_b - axis_a
    norm = float(np.linalg.norm(axis))
    if norm <= lib.TOL:
        raise ValueError("degenerate hinge axis")
    return axis / norm


def component_coefficients(separator_unit: np.ndarray, hinge_unit: np.ndarray, relative_vertex: np.ndarray) -> tuple[float, float]:
    a_term = float(np.dot(separator_unit, np.cross(hinge_unit, relative_vertex)))
    b_term = float(np.dot(separator_unit, hinge_unit) * np.dot(hinge_unit, relative_vertex) - np.dot(separator_unit, relative_vertex))
    return a_term, b_term


def component_term_bound(a_term: float, b_term: float, half_width_radians: float, direction: str) -> float:
    sine = math.sin(half_width_radians)
    one_minus_cosine = 1.0 - math.cos(half_width_radians)
    if direction == "absolute":
        return abs(a_term) * sine + abs(b_term) * one_minus_cosine
    if direction == "positive":
        return abs(a_term) * sine + max(0.0, b_term) * one_minus_cosine
    if direction == "negative":
        return abs(a_term) * sine + max(0.0, -b_term) * one_minus_cosine
    raise ValueError(f"unsupported component-bound direction: {direction}")


def component_displacement_bound_for_labels(
    case: dict,
    transforms: dict[str, dict[str, np.ndarray]],
    delta_by_hinge: dict[str, float],
    paths_by_piece: dict[str, list[dict]],
    vertices: list[np.ndarray],
    piece_id: str,
    separator_unit: np.ndarray,
    direction: str,
) -> float:
    if not vertices:
        return 0.0
    displacement = 0.0
    for hinge in paths_by_piece[piece_id]:
        hinge_id = hinge["hinge_id"]
        half_width_radians = math.radians(abs(float(delta_by_hinge[hinge_id])) / 2.0)
        if half_width_radians <= 0.0:
            continue
        axis_side = hinge["pieces"][0]
        transform = transforms[axis_side]
        axis_a = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][0]])
        axis_b = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][1]])
        hinge_unit = unit_axis(axis_a, axis_b)
        hinge_worst = 0.0
        for vertex in vertices:
            a_term, b_term = component_coefficients(separator_unit, hinge_unit, vertex - axis_a)
            hinge_worst = max(hinge_worst, component_term_bound(a_term, b_term, half_width_radians, direction))
        displacement += hinge_worst
    return branch_probe.ray_guard.DISPLACEMENT_SAFETY_FACTOR * displacement


def vector_to_degrees(tree: dict, vector: np.ndarray) -> dict[str, float]:
    return {hinge_id: float(value) for hinge_id, value in zip(tree["hinge_ids"], vector)}


def component_support_guard_from_segment(
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

    separator_unit = support_probe.branch_axis_unit(transformed, indices, branch_name)
    state = support_probe.support_state(transformed, labels_by_piece, separator_unit)
    if not state["separated_at_center"]:
        return {
            **state,
            "branch_gap": rounded(branch_gap),
            "absolute_component_certified": False,
            "signed_component_certified": False,
            "signed_extrema_stable": False,
        }

    lower_support, lower_non_support = support_probe.piece_label_sets(labels_by_piece, state["lower_piece"], state["lower_support_labels"])
    upper_support, upper_non_support = support_probe.piece_label_sets(labels_by_piece, state["upper_piece"], state["upper_support_labels"])

    lower_support_vertices = support_probe.vertices_for_labels(transformed, indices, state["lower_piece"], lower_support)
    lower_non_support_vertices = support_probe.vertices_for_labels(transformed, indices, state["lower_piece"], lower_non_support)
    upper_support_vertices = support_probe.vertices_for_labels(transformed, indices, state["upper_piece"], upper_support)
    upper_non_support_vertices = support_probe.vertices_for_labels(transformed, indices, state["upper_piece"], upper_non_support)

    lower_support_absolute = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, lower_support_vertices, state["lower_piece"], separator_unit, "absolute"
    )
    upper_support_absolute = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, upper_support_vertices, state["upper_piece"], separator_unit, "absolute"
    )
    lower_support_positive = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, lower_support_vertices, state["lower_piece"], separator_unit, "positive"
    )
    upper_support_negative = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, upper_support_vertices, state["upper_piece"], separator_unit, "negative"
    )
    lower_support_negative = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, lower_support_vertices, state["lower_piece"], separator_unit, "negative"
    )
    lower_non_support_positive = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, lower_non_support_vertices, state["lower_piece"], separator_unit, "positive"
    )
    upper_support_positive = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, upper_support_vertices, state["upper_piece"], separator_unit, "positive"
    )
    upper_non_support_negative = component_displacement_bound_for_labels(
        case, transforms, delta_by_hinge, paths_by_piece, upper_non_support_vertices, state["upper_piece"], separator_unit, "negative"
    )

    absolute_component_bound = lower_support_absolute + upper_support_absolute + SAT_TOLERANCE
    signed_component_bound = lower_support_positive + upper_support_negative + SAT_TOLERANCE
    absolute_component_margin = float(branch_gap) - absolute_component_bound
    signed_component_margin = float(branch_gap) - signed_component_bound
    lower_signed_stability_margin = float(state["lower_competition_margin"]) - lower_support_negative - lower_non_support_positive - SAT_TOLERANCE
    upper_signed_stability_margin = float(state["upper_competition_margin"]) - upper_support_positive - upper_non_support_negative - SAT_TOLERANCE
    signed_extrema_stable = lower_signed_stability_margin >= 0.0 and upper_signed_stability_margin >= 0.0

    return {
        **state,
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "delta": branch_probe.segment_delta(left, right),
        "branch_gap": rounded(branch_gap),
        "absolute_component_bound": rounded(absolute_component_bound),
        "absolute_component_margin": rounded(absolute_component_margin),
        "signed_component_bound": rounded(signed_component_bound),
        "signed_component_margin": rounded(signed_component_margin),
        "lower_support_positive_bound": rounded(lower_support_positive),
        "upper_support_negative_bound": rounded(upper_support_negative),
        "lower_signed_stability_margin": rounded(lower_signed_stability_margin),
        "upper_signed_stability_margin": rounded(upper_signed_stability_margin),
        "minimum_signed_stability_margin": rounded(min(lower_signed_stability_margin, upper_signed_stability_margin)),
        "signed_extrema_stable": signed_extrema_stable,
        "absolute_component_certified": absolute_component_margin >= 0.0 and signed_extrema_stable,
        "signed_component_certified": signed_component_margin >= 0.0 and signed_extrema_stable,
    }


def old_child_reason(evaluation: dict) -> str:
    context = evaluation["context"]
    support = evaluation["support"]
    if context["branch_lower_bound_certified"]:
        return "covered:whole_piece"
    if support.get("stable_support_certified"):
        return "covered:stable_support"
    return f"uncovered:{evaluation['axis_relation']}:{evaluation['remaining_reason']}"


def projected_child_reason(evaluation: dict, component: dict) -> str:
    old_reason = old_child_reason(evaluation)
    if old_reason.startswith("covered:"):
        return old_reason
    if component.get("signed_component_certified"):
        return "covered:projection_component"
    if not component.get("signed_extrema_stable"):
        return f"uncovered:{evaluation['axis_relation']}:projection_component_stability_failed"
    return f"uncovered:{evaluation['axis_relation']}:projection_component_margin_failed"


def base_outcome(covered_count: int, total_count: int) -> str:
    if covered_count == total_count:
        return "fully_covered"
    if covered_count == 0:
        return "zero_child_covered"
    return "partially_covered"


def compact_child_record(base: dict, child_index: int, evaluation: dict, component: dict, old_reason: str, projected_reason: str) -> dict:
    context = evaluation["context"]
    support = evaluation["support"]
    return {
        "base_parent_segment_id": base["parent_segment_id"],
        "base_subsegment_index": base["base_subsegment_index"],
        "child_subsegment_index": child_index,
        "source_edge": source_edge_descriptor(base["source_node_ids"]),
        "source_node_ids": base["source_node_ids"],
        "assigned_branch_name": base["assigned_branch_name"],
        "old_reason": old_reason,
        "projected_reason": projected_reason,
        "center_angle_degrees_by_hinge": context["center_angle_degrees_by_hinge"],
        "axis_relation": evaluation["axis_relation"],
        "best_axis_name": context["best_axis_name"],
        "branch_gap": context["branch_gap"],
        "old_support_margin": support.get("support_margin"),
        "old_minimum_stability_margin": min(
            float(support["lower_stability_margin"]),
            float(support["upper_stability_margin"]),
        ) if support.get("lower_stability_margin") is not None and support.get("upper_stability_margin") is not None else None,
        "signed_component_bound": component.get("signed_component_bound"),
        "signed_component_margin": component.get("signed_component_margin"),
        "absolute_component_bound": component.get("absolute_component_bound"),
        "absolute_component_margin": component.get("absolute_component_margin"),
        "minimum_signed_stability_margin": component.get("minimum_signed_stability_margin"),
        "signed_extrema_stable": component.get("signed_extrema_stable"),
    }


def build_report() -> dict:
    case = branch_probe.batch.build_case()
    tree = branch_probe.comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = branch_probe.comp.certified_signs_by_tree()
    paths_by_piece = branch_probe.ray_guard.tree_paths_from_root(case, tree)
    indices = branch_probe.label_indices(case)
    labels_by_piece = branch_probe.classify.labels_by_piece(case)
    residuals, base_counters = sensitivity.residual_base_subsegments(case, tree, indices, labels_by_piece, paths_by_piece, signs_by_tree)

    old_child_reason_counts = Counter()
    projected_child_reason_counts = Counter()
    old_base_outcomes = Counter()
    projected_base_outcomes = Counter()
    focus_transition_counts = Counter()
    new_certified_source_kind_counts = Counter()
    new_certified_theta_pair_counts = Counter()
    new_certified_branch_counts = Counter()
    new_certified_axis_relation_counts = Counter()
    remaining_source_kind_counts = Counter()
    remaining_theta_pair_counts = Counter()
    remaining_branch_counts = Counter()
    remaining_reason_counts = Counter()
    remaining_axis_relation_counts = Counter()
    remaining_reason_theta_pair_counts = Counter()
    remaining_reason_branch_counts = Counter()

    signed_margins = []
    signed_bounds = []
    signed_stability_margins = []
    absolute_margins = []
    old_support_margins = []
    newly_certified_signed_margins = []
    remaining_signed_margins = []
    examples = defaultdict(list)

    child_total = 0
    old_certified_child_count = 0
    newly_signed_certified_child_count = 0
    newly_absolute_certified_child_count = 0

    for base in residuals:
        old_base_covered = 0
        projected_base_covered = 0
        base_child_total = 0
        branch = base["assigned_branch_name"]
        source = source_edge_descriptor(base["source_node_ids"])
        for child_index, (left, right) in enumerate(sensitivity.subdivide_vector_segment(base["left_vector"], base["right_vector"], TARGET_REFINEMENT_DELTA_DEGREES)):
            base_child_total += 1
            child_total += 1
            evaluation = sensitivity.evaluate_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            component = component_support_guard_from_segment(case, tree, indices, labels_by_piece, paths_by_piece, left, right, branch)
            old_reason = old_child_reason(evaluation)
            projected_reason = projected_child_reason(evaluation, component)
            old_child_reason_counts[old_reason] += 1
            projected_child_reason_counts[projected_reason] += 1

            old_covered = old_reason.startswith("covered:")
            projected_covered = projected_reason.startswith("covered:")
            if old_covered:
                old_base_covered += 1
                old_certified_child_count += 1
            if projected_covered:
                projected_base_covered += 1
            if (not old_covered) and projected_reason == "covered:projection_component":
                newly_signed_certified_child_count += 1
                new_certified_source_kind_counts[source["kind"]] += 1
                new_certified_theta_pair_counts[source["theta_pair"]] += 1
                new_certified_branch_counts[branch] += 1
                new_certified_axis_relation_counts[evaluation["axis_relation"]] += 1
                add_example(examples["newly_certified_by_projection_component"], compact_child_record(base, child_index, evaluation, component, old_reason, projected_reason))
            if (not old_covered) and component.get("absolute_component_certified"):
                newly_absolute_certified_child_count += 1
            if not projected_covered:
                remaining_source_kind_counts[source["kind"]] += 1
                remaining_theta_pair_counts[source["theta_pair"]] += 1
                remaining_branch_counts[branch] += 1
                remaining_reason_counts[projected_reason] += 1
                remaining_axis_relation_counts[evaluation["axis_relation"]] += 1
                remaining_reason_theta_pair_counts[f"{projected_reason} | {source['theta_pair']}"] += 1
                remaining_reason_branch_counts[f"{projected_reason} | {branch}"] += 1
                add_example(examples["remaining_uncovered_after_projection_component"], compact_child_record(base, child_index, evaluation, component, old_reason, projected_reason))

            if component.get("signed_component_margin") is not None:
                signed_margins.append(float(component["signed_component_margin"]))
                signed_bounds.append(float(component["signed_component_bound"]))
                absolute_margins.append(float(component["absolute_component_margin"]))
                if (not old_covered) and projected_reason == "covered:projection_component":
                    newly_certified_signed_margins.append(float(component["signed_component_margin"]))
                if not projected_covered:
                    remaining_signed_margins.append(float(component["signed_component_margin"]))
            if component.get("minimum_signed_stability_margin") is not None:
                signed_stability_margins.append(float(component["minimum_signed_stability_margin"]))
            if evaluation["support"].get("support_margin") is not None:
                old_support_margins.append(float(evaluation["support"]["support_margin"]))

        old_outcome = base_outcome(old_base_covered, base_child_total)
        projected_outcome = base_outcome(projected_base_covered, base_child_total)
        old_base_outcomes[old_outcome] += 1
        projected_base_outcomes[projected_outcome] += 1
        if old_outcome != "fully_covered":
            focus_transition_counts[f"{old_outcome}->{projected_outcome}"] += 1

    projected_certified_child_count = sum(
        count for reason, count in projected_child_reason_counts.items() if str(reason).startswith("covered:")
    )
    return {
        "case_id": CASE_ID,
        "status": "tree007_p2p3_edge_branch_projection_component_bound_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_refinement_sensitivity_probe_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_support_bound_probe_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_face",
            "branches": branch_probe.TARGET_BRANCHES,
            "refinement_delta_degrees": TARGET_REFINEMENT_DELTA_DEGREES,
        },
        "projection_component_formula": {
            "projection_displacement": "n dot (R_epsilon p - p) = A sin(epsilon) + B (1 - cos(epsilon))",
            "A": "n dot (u cross p)",
            "B": "(n dot u)(u dot p) - n dot p",
            "positive_bound": "abs(A) sin(h) + max(0, B) (1 - cos(h))",
            "negative_bound": "abs(A) sin(h) + max(0, -B) (1 - cos(h))",
            "interval": "abs(epsilon) <= h, with h = abs(delta_hinge_degrees) / 2 converted to radians",
            "safety_factor": branch_probe.ray_guard.DISPLACEMENT_SAFETY_FACTOR,
        },
        "base_residual_selection_counts": dict(base_counters),
        "summary_metrics": {
            "residual_base_count": len(residuals),
            "child_subsegment_count": child_total,
            "old_certified_child_count": old_certified_child_count,
            "newly_signed_component_certified_child_count": newly_signed_certified_child_count,
            "newly_absolute_component_certified_child_count": newly_absolute_certified_child_count,
            "projected_certified_child_count": projected_certified_child_count,
            "remaining_uncovered_child_count": child_total - projected_certified_child_count,
            "old_fully_covered_base_count": old_base_outcomes["fully_covered"],
            "projected_fully_covered_base_count": projected_base_outcomes["fully_covered"],
            "projected_partially_covered_base_count": projected_base_outcomes["partially_covered"],
            "projected_zero_child_covered_base_count": projected_base_outcomes["zero_child_covered"],
        },
        "old_child_reason_counts": dict(old_child_reason_counts.most_common()),
        "projected_child_reason_counts": dict(projected_child_reason_counts.most_common()),
        "old_base_outcome_counts": dict(old_base_outcomes.most_common()),
        "projected_base_outcome_counts": dict(projected_base_outcomes.most_common()),
        "focus_base_transition_counts": dict(focus_transition_counts.most_common()),
        "newly_signed_component_certified_breakdown": {
            "by_source_kind": top_counter(new_certified_source_kind_counts),
            "by_theta_pair": top_counter(new_certified_theta_pair_counts),
            "by_assigned_branch": top_counter(new_certified_branch_counts),
            "by_axis_relation": top_counter(new_certified_axis_relation_counts),
        },
        "remaining_uncovered_breakdown": {
            "by_projected_reason": top_counter(remaining_reason_counts),
            "by_axis_relation": top_counter(remaining_axis_relation_counts),
            "by_source_kind": top_counter(remaining_source_kind_counts),
            "by_theta_pair": top_counter(remaining_theta_pair_counts),
            "by_assigned_branch": top_counter(remaining_branch_counts),
            "by_projected_reason_and_theta_pair": top_counter(remaining_reason_theta_pair_counts),
            "by_projected_reason_and_assigned_branch": top_counter(remaining_reason_branch_counts),
        },
        "quantiles": {
            "old_support_margin_all_children": quantiles(old_support_margins),
            "signed_component_margin_all_children": quantiles(signed_margins),
            "absolute_component_margin_all_children": quantiles(absolute_margins),
            "signed_component_bound_all_children": quantiles(signed_bounds),
            "signed_stability_margin_all_children": quantiles(signed_stability_margins),
            "newly_certified_signed_component_margin": quantiles(newly_certified_signed_margins),
            "remaining_signed_component_margin": quantiles(remaining_signed_margins),
        },
        "examples": dict(examples),
        "limitations": [
            "This is a finite numeric projection-component probe, not a complete symbolic residual-contact certificate.",
            "The probe covers only the selected TREE_007 P2-P3 edge-edge branch workflow; P2-P3 face-normal parent branches remain outside this report.",
            "The fixed assigned branch axis is used even when the midpoint best axis switches; such children are recorded separately in the relation ledger.",
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
                "old_child_reason_counts": report["old_child_reason_counts"],
                "projected_child_reason_counts": report["projected_child_reason_counts"],
                "focus_base_transition_counts": report["focus_base_transition_counts"],
                "remaining_uncovered_breakdown": report["remaining_uncovered_breakdown"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())