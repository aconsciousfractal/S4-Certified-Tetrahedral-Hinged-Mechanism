"""TREE_007 P2-P3 face-normal formula guard.

This audit closes the face-normal subset that remains after the TREE_007
P2-P3 edge-branch closure. It targets only the two observed P2-P3 face-normal
branches:

- left_face:B-M_AB-M_CD
- right_face:B-M_AB-M_CD

Let the TREE_007 hinge coordinates be:

- a = H0_A_M_AB
- b = H4_C_M_CD
- c = H7_D_M_CD

For the assigned unnormalized face-normal support gap:

- left_face:B-M_AB-M_CD  gap = (1 - cos(c)) * sin(a) / 4
- right_face:B-M_AB-M_CD gap = (1 - cos(b)) * sin(a) / 4

On the targeted records, a stays in (0, 90) degrees; c stays in (-90, 0)
for the left-face branch; and b stays in (0, 90) for the right-face branch.
These interval facts certify positive raw gap and positive support-extremality
margins for each parent segment.

The script records the formula ledger and checks the formulas numerically
against direct transformed geometry at each segment endpoint and midpoint. It
does not use sympy at runtime and does not claim a full continuous
3-parameter component theorem.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_p2p3_face_normal_formula_guard_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIR = ("P2", "P3")
LEFT_FACE_AXIS = "left_face:B-M_AB-M_CD"
RIGHT_FACE_AXIS = "right_face:B-M_AB-M_CD"
TARGET_FACE_AXES = {LEFT_FACE_AXIS, RIGHT_FACE_AXIS}
H0 = "H0_A_M_AB"
H4 = "H4_C_M_CD"
H7 = "H7_D_M_CD"
FORMULA_TOLERANCE = 1.0e-12
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 48

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_tree007_p2p3_edge_branch_lower_bound_probe as edge_branch  # noqa: E402

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


def label_indices(case: dict) -> dict[str, dict[str, int]]:
    return {
        piece_id: {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(piece)
        }
        for piece_id, piece in case["pieces_by_id"].items()
    }


def point(pieces: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, label: str) -> np.ndarray:
    return pieces[piece_id][indices[piece_id][label]]


def interval_for_hinge(tree: dict, segment: dict, hinge_id: str) -> list[float]:
    left = probe.degrees_from_vector(tree, segment["left_vector"])
    right = probe.degrees_from_vector(tree, segment["right_vector"])
    return [min(float(left[hinge_id]), float(right[hinge_id])), max(float(left[hinge_id]), float(right[hinge_id]))]


def angle_intervals(tree: dict, segment: dict) -> dict[str, list[float]]:
    return {hinge_id: interval_for_hinge(tree, segment, hinge_id) for hinge_id in tree["hinge_ids"]}


def positive_acute(interval_degrees: list[float]) -> bool:
    return interval_degrees[0] > 0.0 and interval_degrees[1] < 90.0


def negative_acute(interval_degrees: list[float]) -> bool:
    return interval_degrees[0] > -90.0 and interval_degrees[1] < 0.0


def min_sin_positive_acute(interval_degrees: list[float]) -> float:
    return math.sin(math.radians(interval_degrees[0]))


def min_cos_positive_acute(interval_degrees: list[float]) -> float:
    return math.cos(math.radians(interval_degrees[1]))


def min_one_minus_cos_positive_acute(interval_degrees: list[float]) -> float:
    return 1.0 - math.cos(math.radians(interval_degrees[0]))


def min_minus_sin_negative_acute(interval_degrees: list[float]) -> float:
    # On (-90, 0), -sin(x) is positive and smallest nearest zero.
    return -math.sin(math.radians(interval_degrees[1]))


def min_cos_negative_acute(interval_degrees: list[float]) -> float:
    # The most negative endpoint has the largest absolute angle and smallest cosine.
    return math.cos(math.radians(interval_degrees[0]))


def min_one_minus_cos_negative_acute(interval_degrees: list[float]) -> float:
    # On (-90, 0), 1 - cos(x) is positive and smallest nearest zero.
    return 1.0 - math.cos(math.radians(interval_degrees[1]))


def formula_value(axis_name: str, degrees_by_hinge: dict[str, float]) -> float:
    a = math.radians(float(degrees_by_hinge[H0]))
    if axis_name == LEFT_FACE_AXIS:
        c = math.radians(float(degrees_by_hinge[H7]))
        return (1.0 - math.cos(c)) * math.sin(a) / 4.0
    if axis_name == RIGHT_FACE_AXIS:
        b = math.radians(float(degrees_by_hinge[H4]))
        return (1.0 - math.cos(b)) * math.sin(a) / 4.0
    raise ValueError(f"Unsupported face axis: {axis_name}")


def formula_lower_bounds(axis_name: str, intervals: dict[str, list[float]]) -> dict:
    a_interval = intervals[H0]
    b_interval = intervals[H4]
    c_interval = intervals[H7]
    a_rule = positive_acute(a_interval)
    b_rule = positive_acute(b_interval)
    c_rule = negative_acute(c_interval)

    if axis_name == LEFT_FACE_AXIS:
        if not (a_rule and c_rule):
            return {
                "formula_sign_certified": False,
                "support_sign_certified": False,
                "active_hinge": H7,
                "reason": "angle_interval_outside_required_open_quadrants",
                "sign_rules": {
                    f"{H0}_inside_positive_acute_interval": a_rule,
                    f"{H7}_inside_negative_acute_interval": c_rule,
                },
            }
        sin_a = min_sin_positive_acute(a_interval)
        cos_a = min_cos_positive_acute(a_interval)
        minus_sin_c = min_minus_sin_negative_acute(c_interval)
        cos_c = min_cos_negative_acute(c_interval)
        one_minus_cos_c = min_one_minus_cos_negative_acute(c_interval)
        raw_gap_lower = sin_a * one_minus_cos_c / 4.0
        support_bounds = {
            "left_lower_P3_M_AB_minus_B": math.sqrt(2.0) * sin_a * minus_sin_c / 8.0,
            "left_lower_P3_M_AB_minus_M_CD": sin_a * cos_c / 4.0,
            "left_lower_P3_M_AB_minus_D": (2.0 * sin_a * cos_c + math.sqrt(2.0) * cos_a) / 8.0,
            "left_upper_P2_C_minus_M_AB": math.sqrt(2.0) / 8.0,
        }
        sign_rules = {
            f"{H0}_inside_positive_acute_interval": a_rule,
            f"{H7}_inside_negative_acute_interval": c_rule,
        }
        active_hinge = H7
    elif axis_name == RIGHT_FACE_AXIS:
        if not (a_rule and b_rule):
            return {
                "formula_sign_certified": False,
                "support_sign_certified": False,
                "active_hinge": H4,
                "reason": "angle_interval_outside_required_open_quadrants",
                "sign_rules": {
                    f"{H0}_inside_positive_acute_interval": a_rule,
                    f"{H4}_inside_positive_acute_interval": b_rule,
                },
            }
        sin_a = min_sin_positive_acute(a_interval)
        cos_a = min_cos_positive_acute(a_interval)
        sin_b = min_sin_positive_acute(b_interval)
        cos_b = min_cos_positive_acute(b_interval)
        one_minus_cos_b = min_one_minus_cos_positive_acute(b_interval)
        raw_gap_lower = sin_a * one_minus_cos_b / 4.0
        support_bounds = {
            "right_lower_P3_B_minus_D": math.sqrt(2.0) / 8.0,
            "right_upper_P2_B_minus_M_AB": math.sqrt(2.0) * sin_a * sin_b / 8.0,
            "right_upper_P2_M_CD_minus_M_AB": sin_a * cos_b / 4.0,
            "right_upper_P2_C_minus_M_AB": (2.0 * sin_a * cos_b + math.sqrt(2.0) * cos_a) / 8.0,
        }
        sign_rules = {
            f"{H0}_inside_positive_acute_interval": a_rule,
            f"{H4}_inside_positive_acute_interval": b_rule,
        }
        active_hinge = H4
    else:
        raise ValueError(f"Unsupported face axis: {axis_name}")

    support_min = min(support_bounds.values())
    return {
        "formula_sign_certified": raw_gap_lower > 0.0,
        "support_sign_certified": support_min > 0.0,
        "active_hinge": active_hinge,
        "angle_intervals_degrees": {
            hinge_id: [rounded(interval[0], 8), rounded(interval[1], 8)]
            for hinge_id, interval in intervals.items()
        },
        "raw_gap_lower_bound": rounded(raw_gap_lower),
        "support_lower_bounds": {key: rounded(value) for key, value in support_bounds.items()},
        "minimum_support_lower_bound": rounded(support_min),
        "sign_rules": sign_rules,
    }


def direct_raw_gap(case: dict, tree: dict, indices: dict[str, dict[str, int]], axis_name: str, vector: np.ndarray) -> float:
    degrees = probe.degrees_from_vector(tree, vector)
    transforms = ray_guard.transforms_for_degrees(case, tree, degrees)
    pieces = lib.transform_pieces(case["pieces_by_id"], transforms)
    if axis_name == LEFT_FACE_AXIS:
        axis = np.cross(
            point(pieces, indices, "P2", "M_AB") - point(pieces, indices, "P2", "B"),
            point(pieces, indices, "P2", "M_CD") - point(pieces, indices, "P2", "B"),
        )
    elif axis_name == RIGHT_FACE_AXIS:
        axis = np.cross(
            point(pieces, indices, "P3", "M_AB") - point(pieces, indices, "P3", "B"),
            point(pieces, indices, "P3", "M_CD") - point(pieces, indices, "P3", "B"),
        )
    else:
        raise ValueError(f"Unsupported face axis: {axis_name}")
    return float(np.dot(point(pieces, indices, "P2", "M_AB") - point(pieces, indices, "P3", "M_AB"), axis))


def formula_check_for_segment(case: dict, tree: dict, indices: dict, segment: dict, axis_name: str) -> dict:
    checks = []
    for sample_name, vector in [
        ("left_endpoint", segment["left_vector"]),
        ("midpoint", (segment["left_vector"] + segment["right_vector"]) / 2.0),
        ("right_endpoint", segment["right_vector"]),
    ]:
        degrees = probe.degrees_from_vector(tree, vector)
        formula = formula_value(axis_name, degrees)
        direct = direct_raw_gap(case, tree, indices, axis_name, vector)
        error = formula - direct
        checks.append(
            {
                "sample": sample_name,
                "formula_value": rounded(formula, 15),
                "direct_raw_gap": rounded(direct, 15),
                "absolute_error": rounded(abs(error), 18),
                "within_tolerance": abs(error) <= FORMULA_TOLERANCE,
            }
        )
    return {
        "sample_count": len(checks),
        "max_abs_error": max(item["absolute_error"] for item in checks),
        "all_within_tolerance": all(item["within_tolerance"] for item in checks),
        "samples": checks,
    }


def compact_record(record: dict, bounds: dict, formula_check: dict, certified: bool) -> dict:
    return {
        "record_id": record["record_id"],
        "segment_id": record["segment_id"],
        "refined_segment_index": record["refined_segment_index"],
        "source_edge_index": record["source_edge_index"],
        "source_node_ids": record["source_node_ids"],
        "source_edge": record["source_edge"],
        "source_t_interval": record["source_t_interval"],
        "pair_key": record["pair_key"],
        "axis_name": record["best_axis_name"],
        "center_axis_overlap": rounded(record["center_axis_overlap"]),
        "guard_bound": rounded(record["guard_bound"]),
        "post_guard_overlap_bound": rounded(record["post_guard_overlap_bound"]),
        "guard_margin": rounded(record["guard_margin"]),
        "formula_certified": certified,
        "active_hinge": bounds.get("active_hinge"),
        "angle_intervals_degrees": bounds.get("angle_intervals_degrees"),
        "raw_gap_lower_bound": bounds.get("raw_gap_lower_bound"),
        "minimum_support_lower_bound": bounds.get("minimum_support_lower_bound"),
        "formula_check_max_abs_error": formula_check["max_abs_error"],
    }


def reconstruct_inputs(case: dict, tree: dict, signs_by_tree: dict[str, dict[str, int]]) -> tuple[list[dict], dict]:
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    labels = classify.labels_by_piece(case)
    nodes_by_id = bounded.all_nodes_by_id(tree, signs_by_tree[TARGET_TREE_ID])
    _tree, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)

    records = []
    all_uncovered_axis_counts = Counter()
    for segment in segments:
        center_vector = (segment["left_vector"] + segment["right_vector"]) / 2.0
        center_degrees = probe.degrees_from_vector(tree, center_vector)
        left_degrees = probe.degrees_from_vector(tree, segment["left_vector"])
        right_degrees = probe.degrees_from_vector(tree, segment["right_vector"])
        delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
        transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        displacement_bounds = probe.piece_displacement_bounds_for_segment(
            case,
            tree,
            transforms,
            transformed,
            delta_by_hinge,
            paths_by_piece,
        )
        best = classify.best_named_axis(
            transformed[TARGET_PAIR[0]],
            transformed[TARGET_PAIR[1]],
            labels[TARGET_PAIR[0]],
            labels[TARGET_PAIR[1]],
        )
        guard_bound = displacement_bounds[TARGET_PAIR[0]] + displacement_bounds[TARGET_PAIR[1]] + SAT_TOLERANCE
        post_guard = best["center_axis_overlap"] + guard_bound
        if post_guard <= SAT_TOLERANCE:
            continue
        all_uncovered_axis_counts[best["axis_name"]] += 1
        if best["axis_name"] not in TARGET_FACE_AXES:
            continue
        record_index = len(records)
        records.append(
            {
                "record_id": f"tree007_p2p3_face_{record_index:05d}",
                "segment_id": f"seg_{segment['refined_segment_index']:05d}",
                "refined_segment_index": segment["refined_segment_index"],
                "source_edge_index": segment["source_edge_index"],
                "source_node_ids": segment["source_node_ids"],
                "source_edge": classify.source_edge_descriptor(nodes_by_id, segment["source_node_ids"]),
                "source_t_interval": segment["source_t_interval"],
                "delta": segment["delta"],
                "pair_key": "-".join(TARGET_PAIR),
                "role": "residual_shared_face",
                "best_axis_name": best["axis_name"],
                "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
                "center_axis_overlap": best["center_axis_overlap"],
                "guard_bound": guard_bound,
                "post_guard_overlap_bound": post_guard,
                "guard_margin": SAT_TOLERANCE - post_guard,
                "left_vector": segment["left_vector"],
                "right_vector": segment["right_vector"],
            }
        )

    source_meta = {
        "source_refined_segment_count": len(segments),
        "reconstructed_p2p3_uncovered_pair_segment_count": sum(all_uncovered_axis_counts.values()),
        "reconstructed_p2p3_uncovered_axis_counts": dict(all_uncovered_axis_counts.most_common()),
    }
    return records, source_meta


def classification_expected_counts() -> dict:
    report = load_json(RESULTS_DIR / "tree007_residual_contact_failure_classification_report.json")
    pair_report = next(item for item in report["pair_reports"] if tuple(item["pair"]) == TARGET_PAIR)
    return {
        "classification_p2p3_uncovered_pair_segment_count": pair_report["uncovered_pair_segment_count"],
        "classification_p2p3_uncovered_axis_counts": pair_report["uncovered_axis_name_counts"],
    }


def build_report() -> dict:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    indices = label_indices(case)
    face_records, source_meta = reconstruct_inputs(case, tree, signs_by_tree)
    expected = classification_expected_counts()

    axis_counts = Counter()
    source_kind_counts = Counter()
    theta_pair_counts = Counter()
    active_hinge_counts = Counter()
    result_counts = Counter()
    examples = defaultdict(list)
    segment_reports = []
    raw_gap_lower_bounds = []
    support_lower_bounds = []
    formula_errors = []
    global_angle_intervals = defaultdict(list)

    for record in face_records:
        segment = {"left_vector": record["left_vector"], "right_vector": record["right_vector"]}
        axis_name = record["best_axis_name"]
        intervals = angle_intervals(tree, segment)
        bounds = formula_lower_bounds(axis_name, intervals)
        formula_check = formula_check_for_segment(case, tree, indices, segment, axis_name)
        certified = bool(
            bounds.get("formula_sign_certified")
            and bounds.get("support_sign_certified")
            and formula_check["all_within_tolerance"]
        )
        axis_counts[axis_name] += 1
        source_kind_counts[record["source_edge"]["kind"]] += 1
        theta_pair_counts[record["source_edge"]["theta_pair"]] += 1
        active_hinge_counts[bounds.get("active_hinge")] += 1
        result_counts["certified" if certified else "uncovered"] += 1
        if bounds.get("raw_gap_lower_bound") is not None:
            raw_gap_lower_bounds.append(float(bounds["raw_gap_lower_bound"]))
        if bounds.get("minimum_support_lower_bound") is not None:
            support_lower_bounds.append(float(bounds["minimum_support_lower_bound"]))
        formula_errors.append(float(formula_check["max_abs_error"]))
        for hinge_id, interval in intervals.items():
            global_angle_intervals[hinge_id].extend(interval)
        compact = compact_record(record, bounds, formula_check, certified)
        segment_reports.append(compact)
        add_example(examples["certified" if certified else "uncovered"], compact)

    certified_count = result_counts.get("certified", 0)
    uncovered_count = result_counts.get("uncovered", 0)
    return {
        "case_id": CASE_ID,
        "status": "tree007_p2p3_face_normal_formula_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/tree007_residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_targeted_endgame_guard_report.json",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "target_axes": sorted(TARGET_FACE_AXES),
        "formula_guard": {
            "hinge_coordinate_names": {"a": H0, "b": H4, "c": H7},
            "left_face_raw_gap_formula": "(1 - cos(c)) * sin(a) / 4",
            "right_face_raw_gap_formula": "(1 - cos(b)) * sin(a) / 4",
            "required_angle_intervals_degrees": {
                H0: "(0, 90)",
                H4: "(0, 90) when active for right_face",
                H7: "(-90, 0) when active for left_face",
            },
            "support_lower_bound_formulas": {
                "left_face": [
                    "P3.M_AB - P3.B = -sqrt(2) * sin(a) * sin(c) / 8",
                    "P3.M_AB - P3.M_CD = sin(a) * cos(c) / 4",
                    "P3.M_AB - P3.D = (2 * sin(a) * cos(c) + sqrt(2) * cos(a)) / 8",
                    "P2.C - P2.M_AB = sqrt(2) / 8",
                ],
                "right_face": [
                    "P3.B - P3.D = sqrt(2) / 8",
                    "P2.B - P2.M_AB = sqrt(2) * sin(a) * sin(b) / 8",
                    "P2.M_CD - P2.M_AB = sin(a) * cos(b) / 4",
                    "P2.C - P2.M_AB = (2 * sin(a) * cos(b) + sqrt(2) * cos(a)) / 8",
                ],
            },
            "formula_tolerance": FORMULA_TOLERANCE,
        },
        "source_reconstruction": {**source_meta, **expected},
        "summary_metrics": {
            "input_face_normal_pair_segment_count": len(face_records),
            "left_face_pair_segment_count": axis_counts.get(LEFT_FACE_AXIS, 0),
            "right_face_pair_segment_count": axis_counts.get(RIGHT_FACE_AXIS, 0),
            "formula_certified_pair_segment_count": certified_count,
            "formula_uncovered_pair_segment_count": uncovered_count,
            "all_input_pair_segments_formula_certified": certified_count == len(face_records) and uncovered_count == 0,
            "minimum_raw_gap_lower_bound": rounded(min(raw_gap_lower_bounds) if raw_gap_lower_bounds else None, 15),
            "minimum_support_lower_bound": rounded(min(support_lower_bounds) if support_lower_bounds else None, 15),
            "maximum_formula_check_abs_error": rounded(max(formula_errors) if formula_errors else None, 18),
            "formula_check_all_samples_within_tolerance": all(error <= FORMULA_TOLERANCE for error in formula_errors),
        },
        "breakdown": {
            "axis_counts": dict(axis_counts.most_common()),
            "source_edge_kind_counts": dict(source_kind_counts.most_common()),
            "source_theta_pair_counts": dict(theta_pair_counts.most_common()),
            "active_hinge_counts": dict(active_hinge_counts.most_common()),
            "global_angle_intervals_degrees": {
                hinge_id: [rounded(min(values), 8), rounded(max(values), 8)]
                for hinge_id, values in sorted(global_angle_intervals.items())
            },
            "raw_gap_lower_bound_quantiles": quantiles(raw_gap_lower_bounds),
            "support_lower_bound_quantiles": quantiles(support_lower_bounds),
            "formula_check_abs_error_quantiles": quantiles(formula_errors),
        },
        "examples": dict(examples),
        "segment_reports": segment_reports,
        "limitations": [
            "This covers only TREE_007 P2-P3 face-normal residual pair-segments identified by reconstruction from the classification guard.",
            "The formulas are recorded as local analytic reductions and checked numerically against direct geometry at endpoints and midpoints; the script does not machine-derive them with a CAS at runtime.",
            "This report does not by itself update the TREE_007 closure overlay; it must be combined with the existing shared-edge and edge-branch evidence.",
            "It does not cover theta=0, every continuous 3-parameter component cell, dynamic connectedness, physical hinge thickness, offsets, mesh export, or printability.",
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
                "axis_counts": report["breakdown"]["axis_counts"],
                "source_reconstruction": report["source_reconstruction"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
