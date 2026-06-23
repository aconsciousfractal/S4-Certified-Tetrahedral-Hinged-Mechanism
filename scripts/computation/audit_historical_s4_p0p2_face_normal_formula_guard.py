"""TREE_021 P0-P2 face-normal formula guard.

This audit closes the P0-P2 face-normal backlog identified by the TREE_021
residual-contact reconciliation ledger. The ordinary clearance/displacement
bound is too conservative here because the shared-face gap is cubic/near-zero
near the closed end. For the two observed face-normal branches, the support gap
reduces to simple trigonometric factors over each refined spanning-tree segment.

Let the TREE_021 hinge coordinates be:

- a = H0_A_M_AB
- b = H7_D_M_CD
- c = H9_B_M_AB

For the assigned face-normal support gap, using unnormalized face normals:

- left_face:M_AB-C-M_CD  gap = (cos(c) - 1) * sin(b) / 4
- right_face:M_AB-C-M_CD gap = (cos(a) - 1) * sin(b) / 4

On all 435 input records, b stays in (-90, 0) degrees and the active a/c
coordinate stays in (0, 90) degrees. Therefore sin(b) < 0 and cos(x) - 1 < 0,
so the branch support gap is positive throughout each segment. The same interval
conditions also keep the support vertices extremal for the recorded face branch.

The script records the formula ledger and checks the formula numerically against
direct transformed geometry at each segment endpoint and midpoint. It does not
use sympy at runtime and does not claim a full 3-parameter component theorem.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "p0p2_face_normal_formula_guard_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P2")
LEFT_FACE_AXIS = "left_face:M_AB-C-M_CD"
RIGHT_FACE_AXIS = "right_face:M_AB-C-M_CD"
TARGET_FACE_AXES = {LEFT_FACE_AXIS, RIGHT_FACE_AXIS}
H0 = "H0_A_M_AB"
H7 = "H7_D_M_CD"
H9 = "H9_B_M_AB"
FORMULA_TOLERANCE = 1.0e-12
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_tree021_residual_contact_reconciliation_ledger as recon  # noqa: E402

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


def top_counter(counter: Counter, limit: int = 24) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def interval_for_hinge(tree: dict, segment: dict, hinge_id: str) -> list[float]:
    left = probe.degrees_from_vector(tree, segment["left_vector"])
    right = probe.degrees_from_vector(tree, segment["right_vector"])
    return [min(float(left[hinge_id]), float(right[hinge_id])), max(float(left[hinge_id]), float(right[hinge_id]))]


def angle_intervals(tree: dict, segment: dict) -> dict[str, list[float]]:
    return {hinge_id: interval_for_hinge(tree, segment, hinge_id) for hinge_id in tree["hinge_ids"]}


def negative_acute(interval_degrees: list[float]) -> bool:
    return interval_degrees[0] > -90.0 and interval_degrees[1] < 0.0


def positive_acute(interval_degrees: list[float]) -> bool:
    return interval_degrees[0] > 0.0 and interval_degrees[1] < 90.0


def min_minus_sin_negative_acute(interval_degrees: list[float]) -> float:
    # On (-90, 0), -sin(x) is positive and smallest nearest zero.
    return -math.sin(math.radians(interval_degrees[1]))


def min_sin_positive_acute(interval_degrees: list[float]) -> float:
    return math.sin(math.radians(interval_degrees[0]))


def min_cos_positive_acute(interval_degrees: list[float]) -> float:
    return math.cos(math.radians(interval_degrees[1]))


def min_one_minus_cos_positive_acute(interval_degrees: list[float]) -> float:
    return 1.0 - math.cos(math.radians(interval_degrees[0]))


def min_cos_negative_acute(interval_degrees: list[float]) -> float:
    # The interval is negative; the most negative endpoint has the largest absolute value.
    return math.cos(math.radians(interval_degrees[0]))


def active_hinge_for_axis(axis_name: str) -> str:
    if axis_name == LEFT_FACE_AXIS:
        return H9
    if axis_name == RIGHT_FACE_AXIS:
        return H0
    raise ValueError(f"Unsupported face axis: {axis_name}")


def formula_value(axis_name: str, degrees_by_hinge: dict[str, float]) -> float:
    b = math.radians(float(degrees_by_hinge[H7]))
    x_hinge = active_hinge_for_axis(axis_name)
    x = math.radians(float(degrees_by_hinge[x_hinge]))
    return (math.cos(x) - 1.0) * math.sin(b) / 4.0


def formula_lower_bounds(axis_name: str, intervals: dict[str, list[float]]) -> dict:
    b_interval = intervals[H7]
    x_hinge = active_hinge_for_axis(axis_name)
    x_interval = intervals[x_hinge]
    b_rule = negative_acute(b_interval)
    x_rule = positive_acute(x_interval)

    if not (b_rule and x_rule):
        return {
            "formula_sign_certified": False,
            "support_sign_certified": False,
            "active_hinge": x_hinge,
            "reason": "angle_interval_outside_required_open_quadrants",
        }

    minus_sin_b = min_minus_sin_negative_acute(b_interval)
    sin_x = min_sin_positive_acute(x_interval)
    cos_x = min_cos_positive_acute(x_interval)
    one_minus_cos_x = min_one_minus_cos_positive_acute(x_interval)
    cos_b = min_cos_negative_acute(b_interval)

    raw_gap_lower = minus_sin_b * one_minus_cos_x / 4.0
    if axis_name == LEFT_FACE_AXIS:
        support_bounds = {
            "left_P2_M_AB_minus_M_CD": minus_sin_b * cos_x / 4.0,
            "left_P2_C_minus_M_CD": math.sqrt(2.0) * minus_sin_b * sin_x / 8.0,
            "left_P2_B_minus_M_CD": (2.0 * minus_sin_b * cos_x + math.sqrt(2.0) * cos_b) / 8.0,
        }
    else:
        support_bounds = {
            "right_P0_M_CD_minus_M_AB": minus_sin_b * cos_x / 4.0,
            "right_P0_M_CD_minus_C": math.sqrt(2.0) * minus_sin_b * sin_x / 8.0,
            "right_P0_M_CD_minus_A": (2.0 * minus_sin_b * cos_x + math.sqrt(2.0) * cos_b) / 8.0,
            "right_P2_B_minus_face": math.sqrt(2.0) / 8.0,
        }

    support_min = min(support_bounds.values())
    return {
        "formula_sign_certified": raw_gap_lower > 0.0,
        "support_sign_certified": support_min > 0.0,
        "active_hinge": x_hinge,
        "b_interval_degrees": [rounded(b_interval[0], 8), rounded(b_interval[1], 8)],
        "active_hinge_interval_degrees": [rounded(x_interval[0], 8), rounded(x_interval[1], 8)],
        "raw_gap_lower_bound": rounded(raw_gap_lower),
        "support_lower_bounds": {key: rounded(value) for key, value in support_bounds.items()},
        "minimum_support_lower_bound": rounded(support_min),
        "sign_rules": {
            "H7_D_M_CD_inside_negative_acute_interval": b_rule,
            f"{x_hinge}_inside_positive_acute_interval": x_rule,
        },
    }


def point(pieces: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, label: str) -> np.ndarray:
    return pieces[piece_id][indices[piece_id][label]]


def direct_raw_gap(case: dict, tree: dict, indices: dict, axis_name: str, vector: np.ndarray) -> float:
    degrees = probe.degrees_from_vector(tree, vector)
    transforms = ray_guard.transforms_for_degrees(case, tree, degrees)
    pieces = lib.transform_pieces(case["pieces_by_id"], transforms)
    if axis_name == LEFT_FACE_AXIS:
        axis = np.cross(
            point(pieces, indices, "P0", "C") - point(pieces, indices, "P0", "M_AB"),
            point(pieces, indices, "P0", "M_CD") - point(pieces, indices, "P0", "M_AB"),
        )
    elif axis_name == RIGHT_FACE_AXIS:
        axis = np.cross(
            point(pieces, indices, "P2", "C") - point(pieces, indices, "P2", "M_AB"),
            point(pieces, indices, "P2", "M_CD") - point(pieces, indices, "P2", "M_AB"),
        )
    else:
        raise ValueError(f"Unsupported face axis: {axis_name}")
    return float(np.dot(point(pieces, indices, "P2", "M_CD") - point(pieces, indices, "P0", "M_CD"), axis))


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
        "pair_key": record["pair_key"],
        "axis_name": record["best_axis_name"],
        "source_edge": record["source_edge"],
        "formula_certified": certified,
        "active_hinge": bounds.get("active_hinge"),
        "b_interval_degrees": bounds.get("b_interval_degrees"),
        "active_hinge_interval_degrees": bounds.get("active_hinge_interval_degrees"),
        "raw_gap_lower_bound": bounds.get("raw_gap_lower_bound"),
        "minimum_support_lower_bound": bounds.get("minimum_support_lower_bound"),
        "formula_check_max_abs_error": formula_check["max_abs_error"],
    }


def reconstruct_inputs(case: dict, tree: dict, signs_by_tree: dict[str, dict[str, int]]) -> tuple[list[dict], dict[int, dict], dict]:
    component_report = recon.load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    _tree, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    records, source_meta = recon.residual_pair_records(case, tree, source_audit, signs_by_tree)
    face_records = [
        record
        for record in records
        if record["pair_key"] == "P0-P2" and record["best_axis_name"] in TARGET_FACE_AXES
    ]
    return face_records, {segment["refined_segment_index"]: segment for segment in segments}, source_meta


def build_report() -> dict:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    indices = branch_probe.label_indices(case)
    face_records, segments_by_index, source_meta = reconstruct_inputs(case, tree, signs_by_tree)

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
        segment = segments_by_index[record["refined_segment_index"]]
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
        "status": "p0p2_face_normal_formula_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/tree021_residual_contact_reconciliation_ledger_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "target_pair": list(TARGET_PAIR),
        "target_axes": sorted(TARGET_FACE_AXES),
        "formula_guard": {
            "hinge_coordinate_names": {"a": H0, "b": H7, "c": H9},
            "left_face_raw_gap_formula": "(cos(c) - 1) * sin(b) / 4",
            "right_face_raw_gap_formula": "(cos(a) - 1) * sin(b) / 4",
            "required_angle_intervals_degrees": {
                H7: "(-90, 0)",
                H0: "(0, 90) when active for right_face",
                H9: "(0, 90) when active for left_face",
            },
            "support_lower_bound_formulas": {
                "left_face": [
                    "P2.M_AB - P2.M_CD = -sin(b) * cos(c) / 4",
                    "P2.C - P2.M_CD = -sqrt(2) * sin(b) * sin(c) / 8",
                    "P2.B - P2.M_CD = (-2 * sin(b) * cos(c) + sqrt(2) * cos(b)) / 8",
                ],
                "right_face": [
                    "P0.M_CD - P0.M_AB = -sin(b) * cos(a) / 4",
                    "P0.M_CD - P0.C = -sqrt(2) * sin(a) * sin(b) / 8",
                    "P0.M_CD - P0.A = (-2 * sin(b) * cos(a) + sqrt(2) * cos(b)) / 8",
                    "P2.B - P2.face = sqrt(2) / 8",
                ],
            },
            "formula_tolerance": FORMULA_TOLERANCE,
        },
        "source_reconstruction": source_meta,
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
            "This covers only the 435 TREE_021 P0-P2 face-normal residual pair-segments identified by the reconciliation ledger.",
            "The formulas are recorded as local analytic reductions and checked numerically against direct geometry at endpoints and midpoints; the script does not machine-derive them with a CAS at runtime.",
            "This report does not by itself update the original 1955 residual-contact reconciliation ledger; a closure overlay should combine it with the existing edge-branch and shared-edge evidence.",
            "It does not cover TREE_007 mirror transfer, theta=0, every continuous 3-parameter component cell, dynamic connectedness, physical hinge thickness, offsets, mesh export, or printability.",
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
                "source_edge_kind_counts": report["breakdown"]["source_edge_kind_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())