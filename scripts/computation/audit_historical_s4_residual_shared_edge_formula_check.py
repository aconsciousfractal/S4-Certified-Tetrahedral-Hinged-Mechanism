"""Residual shared-edge separator formula check for S4 representatives.

This is a finite numerical formula check, not a symbolic proof. It verifies that
all four residual shared-edge targets use the same common-edge separator and
that the near-zero normalized separating gap matches the candidate expression
sin(theta) / sqrt(2 * (1 + cos(theta)^2)) on selected bridge probes.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "residual_shared_edge_formula_check_report.json"
THETA_PROBES_DEGREES = [0.03125, 0.0625, 0.125, 0.25, 0.5]
FORMULA_TOLERANCE = 1.0e-12
COMMON_EDGE_LABELS = ["M_AB", "M_CD"]
TARGETS = [
    {"target_id": "TREE_007_P0_P3", "tree_id": "TREE_007", "pair": ["P0", "P3"]},
    {"target_id": "TREE_007_P1_P2", "tree_id": "TREE_007", "pair": ["P1", "P2"]},
    {"target_id": "TREE_021_P0_P3", "tree_id": "TREE_021", "pair": ["P0", "P3"]},
    {"target_id": "TREE_021_P1_P2", "tree_id": "TREE_021", "pair": ["P1", "P2"]},
]

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def label_index(case: dict) -> dict[str, dict[str, int]]:
    return {
        piece_id: {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(piece)
        }
        for piece_id, piece in case["pieces_by_id"].items()
    }


def transformed_pieces(case: dict, tree: dict, signs_by_hinge: dict[str, int], theta_degrees: float) -> dict[str, list[np.ndarray]]:
    degrees_by_hinge = reps.ray_degrees(tree, signs_by_hinge, theta_degrees)
    angles = {hinge_id: math.radians(degrees) for hinge_id, degrees in degrees_by_hinge.items()}
    transforms = lib.transforms_for_hinge_tree(
        case["piece_ids"],
        batch.selected_hinges_for_tree(case, tree),
        case["labels"],
        angles,
        root_piece="P0",
    )
    return lib.transform_pieces(case["pieces_by_id"], transforms)


def point(pieces: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, label: str) -> np.ndarray:
    return pieces[piece_id][indices[piece_id][label]]


def candidate_formula(theta_degrees: float) -> float:
    theta = math.radians(theta_degrees)
    return math.sin(theta) / math.sqrt(2.0 * (1.0 + math.cos(theta) ** 2))


def sample_target(case: dict, indices: dict, signs_by_tree: dict, target: dict, theta_degrees: float) -> dict:
    tree = comp.find_tree(case, target["tree_id"])
    left_piece, right_piece = target["pair"]
    pieces = transformed_pieces(case, tree, signs_by_tree[target["tree_id"]], theta_degrees)
    left_a = point(pieces, indices, left_piece, COMMON_EDGE_LABELS[0])
    left_b = point(pieces, indices, left_piece, COMMON_EDGE_LABELS[1])
    right_a = point(pieces, indices, right_piece, COMMON_EDGE_LABELS[0])
    right_b = point(pieces, indices, right_piece, COMMON_EDGE_LABELS[1])
    axis = np.cross(left_b - left_a, right_b - right_a)
    axis_norm = float(np.linalg.norm(axis))
    unit = axis / axis_norm
    left_values = [float(np.dot(vertex, unit)) for vertex in pieces[left_piece]]
    right_values = [float(np.dot(vertex, unit)) for vertex in pieces[right_piece]]
    overlap = min(max(left_values), max(right_values)) - max(min(left_values), min(right_values))
    normalized_gap = max(0.0, -float(overlap))
    formula = candidate_formula(theta_degrees)
    error = normalized_gap - formula
    return {
        "theta_degrees": theta_degrees,
        "axis_norm": round(axis_norm, 15),
        "center_axis_overlap": round(float(overlap), 15),
        "normalized_gap": round(normalized_gap, 15),
        "candidate_formula_value": round(formula, 15),
        "formula_error": round(error, 18),
        "formula_abs_error": round(abs(error), 18),
        "gap_positive": normalized_gap > 0.0,
        "formula_check_within_tolerance": abs(error) <= FORMULA_TOLERANCE,
    }


def audit_target(case: dict, indices: dict, signs_by_tree: dict, target: dict) -> dict:
    samples = [sample_target(case, indices, signs_by_tree, target, theta) for theta in THETA_PROBES_DEGREES]
    return {
        **target,
        "status": "residual_shared_edge_formula_check_completed",
        "common_edge_separator": "edge:M_AB-M_CD x M_AB-M_CD",
        "candidate_formula": "normalized_gap = sin(theta) / sqrt(2 * (1 + cos(theta)^2))",
        "theta_probe_degrees": THETA_PROBES_DEGREES,
        "summary_metrics": {
            "sample_count": len(samples),
            "all_formula_checks_within_tolerance": all(sample["formula_check_within_tolerance"] for sample in samples),
            "max_formula_abs_error": max(sample["formula_abs_error"] for sample in samples),
            "all_gaps_positive": all(sample["gap_positive"] for sample in samples),
            "minimum_axis_norm": min(sample["axis_norm"] for sample in samples),
            "minimum_normalized_gap": min(sample["normalized_gap"] for sample in samples),
        },
        "samples": samples,
    }


def build_report() -> dict:
    case = batch.build_case()
    indices = label_index(case)
    signs_by_tree = comp.certified_signs_by_tree()
    target_reports = [audit_target(case, indices, signs_by_tree, target) for target in TARGETS]
    return {
        "case_id": CASE_ID,
        "status": "residual_shared_edge_formula_check_completed",
        "source_report": "results/historical_s4_median_planes/near_zero_gap_inventory_report.json",
        "formula_tolerance": FORMULA_TOLERANCE,
        "summary_metrics": {
            "target_count": len(target_reports),
            "all_targets_formula_checked": all(
                report["summary_metrics"]["all_formula_checks_within_tolerance"] for report in target_reports
            ),
            "all_sampled_gaps_positive": all(
                report["summary_metrics"]["all_gaps_positive"] for report in target_reports
            ),
            "max_formula_abs_error": max(
                report["summary_metrics"]["max_formula_abs_error"] for report in target_reports
            ),
        },
        "target_reports": target_reports,
        "limitations": [
            "This is a finite numerical formula check, not a symbolic derivation.",
            "The check covers selected bridge probes for 0 < theta <= 0.5 degrees, not every theta in the interval.",
            "The formula is for the normalized SAT clearance gap, not an unnormalized triple product.",
            "The result supports the near-zero bridge lemma; the existing ray-cell certificate covers 0.5 <= theta <= 120 degrees.",
            "The result does not by itself complete the full 3-parameter component graph.",
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
                "target_summaries": {
                    report["target_id"]: report["summary_metrics"] for report in report["target_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())