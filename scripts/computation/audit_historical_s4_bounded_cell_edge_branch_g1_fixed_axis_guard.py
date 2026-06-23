"""G1 fixed-axis guard for S4 bounded-cell edge-branch cells.

The bounded-cell edge-branch guard plan isolated 150 sample-stable G1 cells:

- TREE_007 P2-P3: 82 cells
- TREE_021 P0-P2: 68 cells

The coarse cells are too wide for the whole-piece displacement guard. This audit
therefore applies a fixed assigned-axis projection-component support guard on a
uniform 16 x 2 x 2 subdivision of each G1 cell. The separator axis is recomputed
at each subcell center from the assigned edge-edge branch. The proof condition is:

    signed support gap margin >= 0 and support extrema remain stable

This certifies only the G1 route from the edge-branch guard plan. It does not
cover the G2/G3/G4 edge-branch cells.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_edge_branch_g1_fixed_axis_guard_report.json"
SOURCE_CLASSIFIER_REPORT = "bounded_cell_edge_branch_stability_classifier_report.json"
SOURCE_GUARD_PLAN_REPORT = "bounded_cell_edge_branch_guard_plan_report.json"
G1_PROFILE = "assigned_edge_axis_sample_stable"
G1_ROUTE = "G1_fixed_assigned_axis_lower_bound_guard"
SUBDIVISION = {
    "theta_splits": 16,
    "radial_splits": 2,
    "direction_splits": 2,
}
SAT_TOLERANCE = 1.0e-8
SUPPORT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 36

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402
import audit_historical_s4_bounded_cell_edge_branch_stability_classifier as classifier  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

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
        "min": rounded(ordered[0], 15),
        "p05": rounded(q(0.05), 15),
        "p10": rounded(q(0.10), 15),
        "p25": rounded(q(0.25), 15),
        "p50": rounded(q(0.50), 15),
        "p75": rounded(q(0.75), 15),
        "p90": rounded(q(0.90), 15),
        "p95": rounded(q(0.95), 15),
        "max": rounded(ordered[-1], 15),
    }


def top_counter(counter: Counter, limit: int = 32) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def parse_edge_axis(axis_name: str) -> tuple[list[str], list[str]]:
    if not axis_name.startswith("edge:"):
        raise ValueError(f"Not an edge axis: {axis_name}")
    left_text, right_text = axis_name[len("edge:"):].split(" x ", 1)
    return left_text.split("-"), right_text.split("-")


def point(
    pieces: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    piece_id: str,
    label: str,
) -> np.ndarray:
    return pieces[piece_id][indices[piece_id][label]]


def assigned_axis_unit(
    pieces: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    pair: tuple[str, str],
    axis_name: str,
) -> np.ndarray | None:
    left_labels, right_labels = parse_edge_axis(axis_name)
    left_a = point(pieces, indices, pair[0], left_labels[0])
    left_b = point(pieces, indices, pair[0], left_labels[1])
    right_a = point(pieces, indices, pair[1], right_labels[0])
    right_b = point(pieces, indices, pair[1], right_labels[1])
    axis = np.cross(left_b - left_a, right_b - right_a)
    norm = float(np.linalg.norm(axis))
    if norm <= lib.TOL:
        return None
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
        return {
            "separated_at_center": False,
            "gap": rounded(max(0.0, -(min(left_max, right_max) - max(left_min, right_min))), 15),
        }

    lower_support, lower_extreme, lower_competition = extremum_labels(lower_values, "max")
    upper_support, upper_extreme, upper_competition = extremum_labels(upper_values, "min")
    return {
        "separated_at_center": True,
        "gap": float(gap),
        "lower_piece": lower_piece,
        "upper_piece": upper_piece,
        "lower_support_labels": lower_support,
        "upper_support_labels": upper_support,
        "lower_extreme_projection": lower_extreme,
        "upper_extreme_projection": upper_extreme,
        "lower_competition_margin": lower_competition,
        "upper_competition_margin": upper_competition,
    }


def piece_label_sets(
    labels_by_piece: dict[str, list[str]],
    piece_id: str,
    support_labels: list[str],
) -> tuple[list[str], list[str]]:
    support = list(support_labels)
    support_set = set(support)
    non_support = [label for label in labels_by_piece[piece_id] if label not in support_set]
    return support, non_support


def vertices_for_labels(
    transformed: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    piece_id: str,
    labels: list[str],
) -> list[np.ndarray]:
    return [transformed[piece_id][indices[piece_id][label]] for label in labels]


def unit_axis(axis_a: np.ndarray, axis_b: np.ndarray) -> np.ndarray:
    axis = axis_b - axis_a
    norm = float(np.linalg.norm(axis))
    if norm <= lib.TOL:
        raise ValueError("degenerate hinge axis")
    return axis / norm


def component_coefficients(
    separator_unit: np.ndarray,
    hinge_unit: np.ndarray,
    relative_vertex: np.ndarray,
) -> tuple[float, float]:
    a_term = float(np.dot(separator_unit, np.cross(hinge_unit, relative_vertex)))
    b_term = float(
        np.dot(separator_unit, hinge_unit) * np.dot(hinge_unit, relative_vertex)
        - np.dot(separator_unit, relative_vertex)
    )
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
    max_deviation_by_hinge: dict[str, float],
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
        half_width_radians = math.radians(abs(float(max_deviation_by_hinge[hinge_id])))
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
            hinge_worst = max(
                hinge_worst,
                component_term_bound(a_term, b_term, half_width_radians, direction),
            )
        displacement += hinge_worst
    return ray_guard.DISPLACEMENT_SAFETY_FACTOR * displacement


def direction_angle(direction_index: float) -> float:
    return 2.0 * math.pi * float(direction_index) / float(comp.DIRECTION_COUNT)


def sector_candidate_angles(
    phi_left: float,
    phi_right: float,
    coefficient_cos: float,
    coefficient_sin: float,
) -> list[float]:
    candidates = [phi_left, phi_right]
    amplitude = math.hypot(coefficient_cos, coefficient_sin)
    if amplitude <= lib.TOL:
        return candidates
    phase = math.atan2(coefficient_sin, coefficient_cos)
    for base in [phase, phase + math.pi]:
        for offset in range(-2, 5):
            candidate = base + 2.0 * math.pi * offset
            if phi_left - 1.0e-12 <= candidate <= phi_right + 1.0e-12:
                candidates.append(candidate)
    return sorted(set(round(value, 15) for value in candidates))


def theta_coordinate_range(sign: float, theta_interval: list[float]) -> tuple[float, float]:
    left, right = [float(value) for value in theta_interval]
    if sign >= 0.0:
        return left, right
    return -right, -left


def offset_coordinate_range(
    e1_value: float,
    e2_value: float,
    radius_interval: list[float],
    phi_interval: list[float],
) -> tuple[float, float]:
    candidates = sector_candidate_angles(phi_interval[0], phi_interval[1], e1_value, e2_value)
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


def subcell_center_angle_vector(tree: dict, signs_by_hinge: dict[str, int], subcell: dict) -> np.ndarray:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    e1, e2 = reps.transverse_basis(sign_vec)
    theta_center = sum(float(value) for value in subcell["theta_interval_degrees"]) / 2.0
    radius_center = sum(float(value) for value in subcell["radial_interval_degrees"]) / 2.0
    phi_center = sum(float(value) for value in subcell["phi_interval_radians"]) / 2.0
    return sign_vec * theta_center + radius_center * (
        math.cos(phi_center) * e1 + math.sin(phi_center) * e2
    )


def subcell_coordinate_intervals(
    tree: dict,
    signs_by_hinge: dict[str, int],
    subcell: dict,
) -> dict[str, dict]:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    e1, e2 = reps.transverse_basis(sign_vec)
    center_vector = subcell_center_angle_vector(tree, signs_by_hinge, subcell)
    output = {}
    for index, hinge_id in enumerate(tree["hinge_ids"]):
        theta_min, theta_max = theta_coordinate_range(sign_vec[index], subcell["theta_interval_degrees"])
        offset_min, offset_max = offset_coordinate_range(
            float(e1[index]),
            float(e2[index]),
            subcell["radial_interval_degrees"],
            subcell["phi_interval_radians"],
        )
        minimum = theta_min + offset_min
        maximum = theta_max + offset_max
        center = float(center_vector[index])
        max_deviation = max(abs(minimum - center), abs(maximum - center))
        output[hinge_id] = {
            "minimum_degrees": float(minimum),
            "maximum_degrees": float(maximum),
            "center_degrees": float(center),
            "max_deviation_from_center_degrees": float(max_deviation),
        }
    return output


def subdivide_cell(cell: dict) -> list[dict]:
    theta_left, theta_right = [float(value) for value in cell["theta_interval_degrees"]]
    radial_left, radial_right = [float(value) for value in cell["radial_interval_degrees"]]
    direction_index = int(cell["direction_index"])
    phi_left = direction_angle(direction_index)
    phi_right = direction_angle(direction_index + 1)
    theta_splits = int(SUBDIVISION["theta_splits"])
    radial_splits = int(SUBDIVISION["radial_splits"])
    direction_splits = int(SUBDIVISION["direction_splits"])
    subcells = []
    subcell_index = 0
    for theta_index in range(theta_splits):
        theta_a = theta_left + (theta_right - theta_left) * theta_index / theta_splits
        theta_b = theta_left + (theta_right - theta_left) * (theta_index + 1) / theta_splits
        for radial_index in range(radial_splits):
            radial_a = radial_left + (radial_right - radial_left) * radial_index / radial_splits
            radial_b = radial_left + (radial_right - radial_left) * (radial_index + 1) / radial_splits
            for direction_subindex in range(direction_splits):
                phi_a = phi_left + (phi_right - phi_left) * direction_subindex / direction_splits
                phi_b = phi_left + (phi_right - phi_left) * (direction_subindex + 1) / direction_splits
                subcells.append(
                    {
                        "subcell_index": subcell_index,
                        "theta_subindex": theta_index,
                        "radial_subindex": radial_index,
                        "direction_subindex": direction_subindex,
                        "theta_interval_degrees": [theta_a, theta_b],
                        "radial_interval_degrees": [radial_a, radial_b],
                        "phi_interval_radians": [phi_a, phi_b],
                    }
                )
                subcell_index += 1
    return subcells


def compact_interval(values: list[float], digits: int = 12) -> list[float]:
    return [rounded(float(values[0]), digits), rounded(float(values[1]), digits)]


def compact_subcell(subcell: dict) -> dict:
    return {
        "subcell_index": subcell["subcell_index"],
        "theta_subindex": subcell["theta_subindex"],
        "radial_subindex": subcell["radial_subindex"],
        "direction_subindex": subcell["direction_subindex"],
        "theta_interval_degrees": compact_interval(subcell["theta_interval_degrees"]),
        "radial_interval_degrees": compact_interval(subcell["radial_interval_degrees"]),
        "phi_interval_radians": compact_interval(subcell["phi_interval_radians"]),
    }


def evaluate_subcell(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    record: dict,
    subcell: dict,
) -> dict:
    pair = tuple(record["pair"])
    center_vector = subcell_center_angle_vector(tree, signs_by_hinge, subcell)
    center_degrees = reps.degrees_from_vector(tree, center_vector)
    coordinate_intervals = subcell_coordinate_intervals(tree, signs_by_hinge, subcell)
    max_deviation_by_hinge = {
        hinge_id: float(item["max_deviation_from_center_degrees"])
        for hinge_id, item in coordinate_intervals.items()
    }
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    separator_unit = assigned_axis_unit(transformed, indices, pair, record["assigned_axis_name"])
    if separator_unit is None:
        return {
            "certified": False,
            "failure_reason": "degenerate_assigned_axis",
            "subcell": compact_subcell(subcell),
        }

    state = support_state(transformed, labels_by_piece, pair, separator_unit)
    if not state["separated_at_center"]:
        return {
            "certified": False,
            "failure_reason": "not_separated_at_center",
            "subcell": compact_subcell(subcell),
            "gap": state.get("gap"),
        }

    lower_support, lower_non_support = piece_label_sets(
        labels_by_piece,
        state["lower_piece"],
        state["lower_support_labels"],
    )
    upper_support, upper_non_support = piece_label_sets(
        labels_by_piece,
        state["upper_piece"],
        state["upper_support_labels"],
    )

    lower_support_vertices = vertices_for_labels(transformed, indices, state["lower_piece"], lower_support)
    lower_non_support_vertices = vertices_for_labels(transformed, indices, state["lower_piece"], lower_non_support)
    upper_support_vertices = vertices_for_labels(transformed, indices, state["upper_piece"], upper_support)
    upper_non_support_vertices = vertices_for_labels(transformed, indices, state["upper_piece"], upper_non_support)

    lower_support_positive = component_displacement_bound_for_labels(
        case,
        transforms,
        max_deviation_by_hinge,
        paths_by_piece,
        lower_support_vertices,
        state["lower_piece"],
        separator_unit,
        "positive",
    )
    upper_support_negative = component_displacement_bound_for_labels(
        case,
        transforms,
        max_deviation_by_hinge,
        paths_by_piece,
        upper_support_vertices,
        state["upper_piece"],
        separator_unit,
        "negative",
    )
    lower_support_negative = component_displacement_bound_for_labels(
        case,
        transforms,
        max_deviation_by_hinge,
        paths_by_piece,
        lower_support_vertices,
        state["lower_piece"],
        separator_unit,
        "negative",
    )
    lower_non_support_positive = component_displacement_bound_for_labels(
        case,
        transforms,
        max_deviation_by_hinge,
        paths_by_piece,
        lower_non_support_vertices,
        state["lower_piece"],
        separator_unit,
        "positive",
    )
    upper_support_positive = component_displacement_bound_for_labels(
        case,
        transforms,
        max_deviation_by_hinge,
        paths_by_piece,
        upper_support_vertices,
        state["upper_piece"],
        separator_unit,
        "positive",
    )
    upper_non_support_negative = component_displacement_bound_for_labels(
        case,
        transforms,
        max_deviation_by_hinge,
        paths_by_piece,
        upper_non_support_vertices,
        state["upper_piece"],
        separator_unit,
        "negative",
    )

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
    signed_extrema_stable = lower_stability_margin >= 0.0 and upper_stability_margin >= 0.0
    certified = signed_component_margin >= 0.0 and signed_extrema_stable
    if certified:
        failure_reason = None
    elif not signed_extrema_stable:
        failure_reason = "support_extrema_stability_margin_failed"
    else:
        failure_reason = "signed_component_margin_failed"

    return {
        "certified": bool(certified),
        "failure_reason": failure_reason,
        "subcell": compact_subcell(subcell),
        "gap": rounded(float(state["gap"]), 15),
        "signed_component_bound": rounded(signed_component_bound, 15),
        "signed_component_margin": rounded(signed_component_margin, 15),
        "lower_stability_margin": rounded(lower_stability_margin, 15),
        "upper_stability_margin": rounded(upper_stability_margin, 15),
        "minimum_stability_margin": rounded(minimum_stability_margin, 15),
        "lower_piece": state["lower_piece"],
        "upper_piece": state["upper_piece"],
        "lower_support_labels": state["lower_support_labels"],
        "upper_support_labels": state["upper_support_labels"],
        "center_angle_degrees_by_hinge": {
            hinge_id: rounded(float(value), 8)
            for hinge_id, value in center_degrees.items()
        },
        "max_hinge_deviation_degrees": rounded(max(max_deviation_by_hinge.values()), 15),
    }


def choose_worst_subcell(results: list[dict]) -> dict:
    return min(
        results,
        key=lambda item: (
            float("inf") if item.get("signed_component_margin") is None else float(item["signed_component_margin"]),
            float("inf") if item.get("minimum_stability_margin") is None else float(item["minimum_stability_margin"]),
        ),
    )


def compact_cell_record(
    tree_id: str,
    record: dict,
    cell: dict,
    subcell_results: list[dict],
) -> dict:
    certified_results = [item for item in subcell_results if item["certified"]]
    failed_results = [item for item in subcell_results if not item["certified"]]
    margins = [
        float(item["signed_component_margin"])
        for item in subcell_results
        if item.get("signed_component_margin") is not None
    ]
    stability_margins = [
        float(item["minimum_stability_margin"])
        for item in subcell_results
        if item.get("minimum_stability_margin") is not None
    ]
    gaps = [
        float(item["gap"])
        for item in subcell_results
        if item.get("gap") is not None
    ]
    worst = choose_worst_subcell(subcell_results)
    return {
        "cell_id": record["cell_id"],
        "tree_id": tree_id,
        "pair": record["pair"],
        "kind": cell["kind"],
        "route": G1_ROUTE,
        "assigned_axis_name": record["assigned_axis_name"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "sample_profile": record["sample_profile"],
        "source_sample_gap_interval": record["assigned_axis_gap_interval"],
        "subdivision": SUBDIVISION,
        "subcell_count": len(subcell_results),
        "certified_subcell_count": len(certified_results),
        "failed_subcell_count": len(failed_results),
        "cell_certified": len(failed_results) == 0,
        "minimum_gap": rounded(min(gaps) if gaps else None, 15),
        "minimum_signed_component_margin": rounded(min(margins) if margins else None, 15),
        "minimum_signed_stability_margin": rounded(min(stability_margins) if stability_margins else None, 15),
        "worst_subcell": worst,
        "failure_reason_counts": dict(Counter(item["failure_reason"] for item in failed_results).most_common()),
    }


def g1_records_by_tree(classifier_report: dict) -> dict[str, list[dict]]:
    output = {}
    for target_report in classifier_report["target_reports"]:
        tree_id = target_report["target"]["tree_id"]
        records = [
            record
            for record in target_report["cell_reports"]
            if record["sample_profile"] == G1_PROFILE
        ]
        output[tree_id] = records
    return output


def audit_target(
    case: dict,
    tree_id: str,
    records: list[dict],
    cell_by_id: dict[str, dict],
    signs_by_tree: dict[str, dict[str, int]],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
) -> dict:
    tree = comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)

    cell_reports = []
    examples = defaultdict(list)
    axis_counts = Counter()
    kind_counts = Counter()
    failure_reason_counts = Counter()
    cell_failure_reason_counts = Counter()
    signed_margins = []
    stability_margins = []
    gaps = []
    max_deviations = []

    for record in records:
        cell = cell_by_id[record["cell_id"]]
        subcell_results = [
            evaluate_subcell(
                case,
                tree,
                signs,
                indices,
                labels_by_piece,
                paths_by_piece,
                record,
                subcell,
            )
            for subcell in subdivide_cell(cell)
        ]
        compact = compact_cell_record(tree_id, record, cell, subcell_results)
        cell_reports.append(compact)

        axis_counts[record["assigned_axis_name"]] += 1
        kind_counts[cell["kind"]] += 1
        if compact["cell_certified"]:
            add_example(examples["certified_cells"], compact)
        else:
            add_example(examples["uncovered_cells"], compact)
            for reason, count in compact["failure_reason_counts"].items():
                cell_failure_reason_counts[reason] += count
        for result in subcell_results:
            if result["failure_reason"] is not None:
                failure_reason_counts[result["failure_reason"]] += 1
            if result.get("signed_component_margin") is not None:
                signed_margins.append(float(result["signed_component_margin"]))
            if result.get("minimum_stability_margin") is not None:
                stability_margins.append(float(result["minimum_stability_margin"]))
            if result.get("gap") is not None:
                gaps.append(float(result["gap"]))
            if result.get("max_hinge_deviation_degrees") is not None:
                max_deviations.append(float(result["max_hinge_deviation_degrees"]))

    total_subcells = sum(item["subcell_count"] for item in cell_reports)
    certified_subcells = sum(item["certified_subcell_count"] for item in cell_reports)
    certified_cells = sum(1 for item in cell_reports if item["cell_certified"])
    return {
        "target": {
            "tree_id": tree_id,
            "pair": records[0]["pair"] if records else None,
            "route": G1_ROUTE,
            "source_sample_profile": G1_PROFILE,
        },
        "summary_metrics": {
            "input_g1_cell_count": len(records),
            "g1_certified_cell_count": certified_cells,
            "g1_uncovered_cell_count": len(records) - certified_cells,
            "g1_all_input_cells_certified": certified_cells == len(records),
            "subcell_count": total_subcells,
            "certified_subcell_count": certified_subcells,
            "failed_subcell_count": total_subcells - certified_subcells,
            "minimum_signed_component_margin": rounded(min(signed_margins) if signed_margins else None, 15),
            "minimum_signed_stability_margin": rounded(min(stability_margins) if stability_margins else None, 15),
            "minimum_gap": rounded(min(gaps) if gaps else None, 15),
            "maximum_subcell_hinge_deviation_degrees": rounded(max(max_deviations) if max_deviations else None, 15),
        },
        "breakdown": {
            "assigned_axis_counts": dict(axis_counts.most_common()),
            "cell_kind_counts": dict(kind_counts.most_common()),
            "subcell_failure_reason_counts": dict(failure_reason_counts.most_common()),
            "cell_failure_reason_counts": dict(cell_failure_reason_counts.most_common()),
            "signed_component_margin_quantiles": quantiles(signed_margins),
            "signed_stability_margin_quantiles": quantiles(stability_margins),
            "gap_quantiles": quantiles(gaps),
            "max_hinge_deviation_quantiles_degrees": quantiles(max_deviations),
        },
        "examples": dict(examples),
        "cell_reports": cell_reports,
    }


def aggregate_summary(target_reports: list[dict]) -> dict:
    def total(metric: str) -> int:
        return sum(int(report["summary_metrics"][metric]) for report in target_reports)

    axis_counts = Counter()
    kind_counts = Counter()
    failure_counts = Counter()
    signed_margins = []
    stability_margins = []
    gaps = []
    max_deviations = []
    tree_counts = {}
    tree_certified_counts = {}
    for report in target_reports:
        tree_id = report["target"]["tree_id"]
        tree_counts[tree_id] = report["summary_metrics"]["input_g1_cell_count"]
        tree_certified_counts[tree_id] = report["summary_metrics"]["g1_certified_cell_count"]
        axis_counts.update(report["breakdown"]["assigned_axis_counts"])
        kind_counts.update(report["breakdown"]["cell_kind_counts"])
        failure_counts.update(report["breakdown"]["subcell_failure_reason_counts"])
        signed_margins.extend(
            float(cell["minimum_signed_component_margin"])
            for cell in report["cell_reports"]
            if cell["minimum_signed_component_margin"] is not None
        )
        stability_margins.extend(
            float(cell["minimum_signed_stability_margin"])
            for cell in report["cell_reports"]
            if cell["minimum_signed_stability_margin"] is not None
        )
        gaps.extend(
            float(cell["minimum_gap"])
            for cell in report["cell_reports"]
            if cell["minimum_gap"] is not None
        )
        max_deviations.append(report["summary_metrics"]["maximum_subcell_hinge_deviation_degrees"])

    certified_cells = total("g1_certified_cell_count")
    input_cells = total("input_g1_cell_count")
    certified_subcells = total("certified_subcell_count")
    subcells = total("subcell_count")
    return {
        "target_count": len(target_reports),
        "input_g1_cell_count": input_cells,
        "g1_certified_cell_count": certified_cells,
        "g1_uncovered_cell_count": input_cells - certified_cells,
        "g1_all_input_cells_certified": certified_cells == input_cells,
        "subdivision": SUBDIVISION,
        "subcell_count": subcells,
        "certified_subcell_count": certified_subcells,
        "failed_subcell_count": subcells - certified_subcells,
        "all_subcells_certified": certified_subcells == subcells,
        "tree_counts": tree_counts,
        "tree_certified_cell_counts": tree_certified_counts,
        "assigned_axis_counts": dict(axis_counts.most_common()),
        "cell_kind_counts": dict(kind_counts.most_common()),
        "subcell_failure_reason_counts": dict(failure_counts.most_common()),
        "minimum_signed_component_margin": rounded(min(signed_margins) if signed_margins else None, 15),
        "minimum_signed_stability_margin": rounded(min(stability_margins) if stability_margins else None, 15),
        "minimum_gap": rounded(min(gaps) if gaps else None, 15),
        "maximum_subcell_hinge_deviation_degrees": rounded(max(max_deviations) if max_deviations else None, 15),
    }


def build_report() -> dict:
    classifier_report = load_json(RESULTS_DIR / SOURCE_CLASSIFIER_REPORT)
    guard_plan = load_json(RESULTS_DIR / SOURCE_GUARD_PLAN_REPORT)
    expected_g1 = int(guard_plan["summary_metrics"]["route_counts"][G1_ROUTE])
    records_by_tree = g1_records_by_tree(classifier_report)
    input_g1 = sum(len(records) for records in records_by_tree.values())
    if input_g1 != expected_g1:
        raise AssertionError(f"Expected {expected_g1} G1 cells from guard plan, found {input_g1}")

    case = batch.build_case()
    signs_by_tree = comp.certified_signs_by_tree()
    indices = classifier.label_indices(case)
    labels_by_piece = classify.labels_by_piece(case)
    cell_by_id = {cell["cell_id"]: cell for cell in protocol.iter_cells()}

    target_reports = [
        audit_target(case, tree_id, records_by_tree[tree_id], cell_by_id, signs_by_tree, indices, labels_by_piece)
        for tree_id in sorted(records_by_tree)
    ]
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_edge_branch_g1_fixed_axis_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_CLASSIFIER_REPORT}",
            f"results/{CASE_ID}/{SOURCE_GUARD_PLAN_REPORT}",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
        ],
        "target": {
            "description": "first executable G1 fixed assigned-axis guard for sample-stable bounded-cell edge-branch records",
            "route": G1_ROUTE,
            "source_sample_profile": G1_PROFILE,
            "subdivision": SUBDIVISION,
            "guard_rule": "for every subcell, recompute the assigned edge-edge separator at the subcell center and require positive signed projection-component gap margin plus stable support extrema",
            "sat_tolerance": SAT_TOLERANCE,
            "support_tolerance": SUPPORT_TOLERANCE,
            "displacement_safety_factor": ray_guard.DISPLACEMENT_SAFETY_FACTOR,
        },
        "summary_metrics": aggregate_summary(target_reports),
        "target_reports": target_reports,
        "limitations": [
            "This report certifies only the 150 G1 sample-stable edge-branch bounded cells from the guard-plan report.",
            "The original coarse G1 cells do not pass the whole-piece full-cell displacement guard; certification uses the recorded 16 x 2 x 2 subdivision.",
            "The report does not certify the 371 G2 edge-axis switch cells, 180 G3 hybrid edge/face switch cells, or 22 G4 nonseparating-axis cells.",
            "This is finite numeric support-component evidence, not a symbolic formula derivation.",
            "This does not certify theta=0, the full continuous 3-parameter component, physical hinge thickness, offsets, CAD, mesh export, or printability.",
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
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
