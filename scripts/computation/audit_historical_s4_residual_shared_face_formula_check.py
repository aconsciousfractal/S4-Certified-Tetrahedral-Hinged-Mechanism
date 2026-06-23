"""Residual shared-face separator formula check for S4 representatives.

This is a finite numerical formula check, not a symbolic proof. It verifies that
both remaining residual shared-face targets use the same edge-edge separator and
that the unnormalized separating triple product matches the candidate expression
sin(theta/2)^3 * cos(theta/2) at selected theta values.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "residual_shared_face_formula_check_report.json"
THETA_PROBES_DEGREES = [0.5, 0.625, 1.0, 2.0, 5.0, 10.0, 15.0, 15.625, 20.0, 45.0, 75.0, 120.0]
FORMULA_TOLERANCE = 1.0e-12
TARGETS = [
    {
        "target_id": "TREE_007_P2_P3",
        "tree_id": "TREE_007",
        "pair": ["P2", "P3"],
        "left_piece": "P2",
        "right_piece": "P3",
        "left_edge_labels": ["B", "M_CD"],
        "right_edge_labels": ["B", "M_AB"],
        "separation_vector_labels": {"from": ["P2", "M_AB"], "to": ["P3", "B"]},
    },
    {
        "target_id": "TREE_021_P0_P2",
        "tree_id": "TREE_021",
        "pair": ["P0", "P2"],
        "left_piece": "P0",
        "right_piece": "P2",
        "left_edge_labels": ["M_AB", "C"],
        "right_edge_labels": ["C", "M_CD"],
        "separation_vector_labels": {"from": ["P0", "M_CD"], "to": ["P2", "C"]},
    },
]

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def label_index(case: dict) -> dict[str, dict[str, int]]:
    output = {}
    for piece_id, vertices in case["pieces_by_id"].items():
        output[piece_id] = {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(vertices)
        }
    return output


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
    half = math.radians(theta_degrees) / 2.0
    return (math.sin(half) ** 3) * math.cos(half)


def sample_target(case: dict, indices: dict, signs_by_tree: dict, target: dict, theta_degrees: float) -> dict:
    tree = comp.find_tree(case, target["tree_id"])
    pieces = transformed_pieces(case, tree, signs_by_tree[target["tree_id"]], theta_degrees)
    left_a = point(pieces, indices, target["left_piece"], target["left_edge_labels"][0])
    left_b = point(pieces, indices, target["left_piece"], target["left_edge_labels"][1])
    right_a = point(pieces, indices, target["right_piece"], target["right_edge_labels"][0])
    right_b = point(pieces, indices, target["right_piece"], target["right_edge_labels"][1])
    from_piece, from_label = target["separation_vector_labels"]["from"]
    to_piece, to_label = target["separation_vector_labels"]["to"]
    separation = point(pieces, indices, to_piece, to_label) - point(pieces, indices, from_piece, from_label)
    axis = np.cross(left_b - left_a, right_b - right_a)
    axis_norm = float(np.linalg.norm(axis))
    triple = float(np.dot(separation, axis))
    normalized_gap = triple / axis_norm
    formula = candidate_formula(theta_degrees)
    error = triple - formula
    return {
        "theta_degrees": theta_degrees,
        "axis_norm": round(axis_norm, 15),
        "unnormalized_triple_product": round(triple, 15),
        "candidate_formula_value": round(formula, 15),
        "formula_error": round(error, 18),
        "formula_abs_error": round(abs(error), 18),
        "normalized_gap": round(normalized_gap, 15),
        "triple_positive": triple > 0.0,
        "formula_check_within_tolerance": abs(error) <= FORMULA_TOLERANCE,
    }


def audit_target(case: dict, indices: dict, signs_by_tree: dict, target: dict) -> dict:
    samples = [sample_target(case, indices, signs_by_tree, target, theta) for theta in THETA_PROBES_DEGREES]
    return {
        **target,
        "status": "residual_shared_face_formula_check_completed",
        "candidate_formula": "unnormalized_triple_product = sin(theta/2)^3 * cos(theta/2)",
        "theta_probe_degrees": THETA_PROBES_DEGREES,
        "summary_metrics": {
            "sample_count": len(samples),
            "all_formula_checks_within_tolerance": all(sample["formula_check_within_tolerance"] for sample in samples),
            "max_formula_abs_error": max(sample["formula_abs_error"] for sample in samples),
            "all_triples_positive": all(sample["triple_positive"] for sample in samples),
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
        "status": "residual_shared_face_formula_check_completed",
        "source_report": "results/historical_s4_median_planes/residual_contact_gap_diagnostic_report.json",
        "formula_tolerance": FORMULA_TOLERANCE,
        "summary_metrics": {
            "target_count": len(target_reports),
            "all_targets_formula_checked": all(
                report["summary_metrics"]["all_formula_checks_within_tolerance"] for report in target_reports
            ),
            "all_sampled_triples_positive": all(
                report["summary_metrics"]["all_triples_positive"] for report in target_reports
            ),
            "max_formula_abs_error": max(
                report["summary_metrics"]["max_formula_abs_error"] for report in target_reports
            ),
        },
        "target_reports": target_reports,
        "limitations": [
            "This is a finite numerical formula check, not a symbolic derivation.",
            "The check covers selected theta probes, not every theta in the interval.",
            "The result supports the next manual lemma for residual shared-face orientation; it does not by itself complete the ray-cell certificate.",
            "The residual shared-edge target TREE_021 P1-P2 is not handled by this shared-face formula check.",
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