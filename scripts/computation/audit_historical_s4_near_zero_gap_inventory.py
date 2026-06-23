"""Near-zero gap inventory for S4 representative rays.

This diagnostic inventories all piece-pair separating gaps near theta -> 0+ for
TREE_007 and TREE_021. It is intentionally small and non-adaptive: a few theta
probes, all pair roles, best named SAT axis, and an estimated gap order.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "near_zero_gap_inventory_report.json"
REPRESENTATIVES = ["TREE_007", "TREE_021"]
THETA_PROBES_DEGREES = [0.03125, 0.0625, 0.125, 0.25, 0.5, 1.0, 2.0]
ORDER_FIT_MAX_THETA_DEGREES = 0.5

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID
FACES = list(itertools.combinations(range(4), 3))
EDGES = list(itertools.combinations(range(4), 2))


def label_index(case: dict) -> dict[str, dict[str, int]]:
    return {
        piece_id: {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(piece)
        }
        for piece_id, piece in case["pieces_by_id"].items()
    }


def vertex_labels(case: dict) -> dict[str, list[str]]:
    return {
        piece_id: [lib.label_for(vertex, case["labels"]) for vertex in piece]
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


def axis_records(poly_a: list[np.ndarray], poly_b: list[np.ndarray], labels_a: list[str], labels_b: list[str]) -> list[tuple[str, np.ndarray]]:
    records = []
    for side, poly, labels in [("left", poly_a, labels_a), ("right", poly_b, labels_b)]:
        for face in FACES:
            pts = [poly[index] for index in face]
            axis = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            if np.linalg.norm(axis) > lib.TOL:
                records.append((f"{side}_face:{'-'.join(labels[index] for index in face)}", axis))
    for edge_a in EDGES:
        vector_a = poly_a[edge_a[1]] - poly_a[edge_a[0]]
        for edge_b in EDGES:
            vector_b = poly_b[edge_b[1]] - poly_b[edge_b[0]]
            axis = np.cross(vector_a, vector_b)
            if np.linalg.norm(axis) > lib.TOL:
                records.append(
                    (
                        f"edge:{labels_a[edge_a[0]]}-{labels_a[edge_a[1]]} x {labels_b[edge_b[0]]}-{labels_b[edge_b[1]]}",
                        axis,
                    )
                )
    return records


def best_axis(poly_a: list[np.ndarray], poly_b: list[np.ndarray], labels_a: list[str], labels_b: list[str]) -> dict:
    best = None
    for name, axis in axis_records(poly_a, poly_b, labels_a, labels_b):
        unit = axis / np.linalg.norm(axis)
        a_values = [float(np.dot(vertex, unit)) for vertex in poly_a]
        b_values = [float(np.dot(vertex, unit)) for vertex in poly_b]
        overlap = min(max(a_values), max(b_values)) - max(min(a_values), min(b_values))
        if best is None or overlap < best["center_axis_overlap"]:
            best = {
                "axis_name": name,
                "center_axis_overlap": float(overlap),
                "clearance_gap": max(0.0, -float(overlap)),
                "axis_unit": [round(float(value), 12) for value in unit],
            }
    if best is None:
        raise RuntimeError("No SAT axis found")
    return best


def contacts_by_pair(case: dict) -> dict[tuple[str, str], dict]:
    return {tuple(sorted(contact["pieces"])): contact for contact in case["contacts"]}


def role_for_pair(case: dict, tree: dict, pair: tuple[str, str], contacts: dict[tuple[str, str], dict]) -> str:
    hinge_pairs = {tuple(sorted(case["hinge_by_id"][hinge_id]["pieces"])) for hinge_id in tree["hinge_ids"]}
    if pair in hinge_pairs:
        return "selected_hinge_contact"
    if pair in contacts:
        return f"residual_{contacts[pair]['type']}"
    return "non_contact_pair"


def estimate_order(samples: list[dict]) -> dict:
    points = [
        (math.log(float(sample["theta_degrees"])), math.log(float(sample["clearance_gap"])))
        for sample in samples
        if sample["theta_degrees"] <= ORDER_FIT_MAX_THETA_DEGREES and sample["clearance_gap"] > 1.0e-14
    ]
    if len(points) < 2:
        return {"estimated_order": None, "fit_point_count": len(points)}
    xs = np.array([point[0] for point in points], dtype=float)
    ys = np.array([point[1] for point in points], dtype=float)
    slope, intercept = np.polyfit(xs, ys, 1)
    return {
        "estimated_order": round(float(slope), 6),
        "log_intercept": round(float(intercept), 12),
        "fit_point_count": len(points),
    }


def audit_tree(case: dict, labels_by_piece: dict[str, list[str]], tree_id: str, signs_by_hinge: dict[str, int]) -> dict:
    tree = comp.find_tree(case, tree_id)
    contacts = contacts_by_pair(case)
    pair_records = []
    for pair in itertools.combinations(sorted(case["piece_ids"]), 2):
        role = role_for_pair(case, tree, pair, contacts)
        samples = []
        for theta in THETA_PROBES_DEGREES:
            pieces = transformed_pieces(case, tree, signs_by_hinge, theta)
            best = best_axis(pieces[pair[0]], pieces[pair[1]], labels_by_piece[pair[0]], labels_by_piece[pair[1]])
            samples.append(
                {
                    "theta_degrees": theta,
                    "axis_name": best["axis_name"],
                    "center_axis_overlap": round(best["center_axis_overlap"], 15),
                    "clearance_gap": round(best["clearance_gap"], 15),
                }
            )
        axis_names = sorted({sample["axis_name"] for sample in samples})
        fit = estimate_order(samples)
        pair_records.append(
            {
                "pair": list(pair),
                "role": role,
                "axis_name_count": len(axis_names),
                "axis_names": axis_names,
                "minimum_probe_gap": min(sample["clearance_gap"] for sample in samples),
                "maximum_probe_gap": max(sample["clearance_gap"] for sample in samples),
                "near_zero_order_fit": fit,
                "samples": samples,
            }
        )
    non_hinge = [record for record in pair_records if record["role"] != "selected_hinge_contact"]
    analytic_targets = [
        record for record in non_hinge
        if (record["near_zero_order_fit"]["estimated_order"] or 0.0) >= 2.5
    ]
    linear_targets = [
        record for record in non_hinge
        if record["near_zero_order_fit"]["estimated_order"] is not None
        and record["near_zero_order_fit"]["estimated_order"] < 2.5
    ]
    return {
        "tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs_by_hinge,
        "status": "near_zero_gap_inventory_completed",
        "summary_metrics": {
            "pair_count": len(pair_records),
            "selected_hinge_contact_pair_count": sum(1 for record in pair_records if record["role"] == "selected_hinge_contact"),
            "non_hinge_pair_count": len(non_hinge),
            "near_zero_cubic_or_higher_target_count": len(analytic_targets),
            "near_zero_lower_order_target_count": len(linear_targets),
        },
        "pair_records": pair_records,
    }


def build_report() -> dict:
    case = batch.build_case()
    labels_by_piece = vertex_labels(case)
    signs_by_tree = comp.certified_signs_by_tree()
    tree_reports = [audit_tree(case, labels_by_piece, tree_id, signs_by_tree[tree_id]) for tree_id in REPRESENTATIVES]
    return {
        "case_id": CASE_ID,
        "status": "near_zero_gap_inventory_completed",
        "theta_probe_degrees": THETA_PROBES_DEGREES,
        "order_fit_max_theta_degrees": ORDER_FIT_MAX_THETA_DEGREES,
        "summary_metrics": {
            "tree_count": len(tree_reports),
            "all_tree_reports_completed": all(report["status"] == "near_zero_gap_inventory_completed" for report in tree_reports),
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This is a finite near-zero diagnostic, not a proof for theta -> 0+.",
            "Estimated orders are log-log fits over selected theta probes.",
            "Axis-name stability is sampled and does not by itself certify a symbolic separator.",
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
                "tree_summaries": {
                    tree["tree_id"]: tree["summary_metrics"] for tree in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())