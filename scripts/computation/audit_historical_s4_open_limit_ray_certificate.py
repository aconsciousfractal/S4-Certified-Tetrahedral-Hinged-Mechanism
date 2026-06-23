"""Open-limit ray certificate ledger for S4 representatives.

This report combines two ingredients:

1. the completed finite ray-cell certificate on 0.5 <= theta <= 120 degrees;
2. a near-zero bridge on 0 < theta <= 0.5 degrees using the selected-hinge
   orientation rule, the residual shared-face cubic formula, and the residual
   shared-edge normalized-gap formula.

It is a ledger/interval-logic report. It does not recompute all cells and does
not certify theta = 0, physical hinge thickness, or the full 3-parameter graph.
"""

from __future__ import annotations

import json
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "open_limit_ray_certificate_report.json"
FINITE_CERTIFICATE_REPORT = "tree021_residual_edge_targeted_guard_report.json"
FACE_FORMULA_REPORT = "residual_shared_face_formula_check_report.json"
EDGE_FORMULA_REPORT = "residual_shared_edge_formula_check_report.json"
NEAR_ZERO_INVENTORY_REPORT = "near_zero_gap_inventory_report.json"
CONTACT_ORIENTATION_REPORT = "two_class_contact_orientation_report.json"
BRIDGE_INTERVAL_DEGREES = {"left": 0.0, "left_open": True, "right": 0.5, "right_closed": True}
FINITE_INTERVAL_DEGREES = {"left": 0.5, "left_closed": True, "right": 120.0, "right_closed": True}
REPRESENTATIVES = ["TREE_007", "TREE_021"]

SCRIPT_PATH = Path(__file__).resolve()
RESULTS_DIR = SCRIPT_PATH.parents[1] / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def bridge_formula_certificates(face_report: dict, edge_report: dict, contact_report: dict) -> dict:
    bridge_right = BRIDGE_INTERVAL_DEGREES["right"]
    half_right = bridge_right / 2.0
    selected_hinge_orientation = {
        "method": "selected_hinge_contact_orientation",
        "interval": "0 < theta <= 0.5 degrees",
        "reason": "signed hinge angles keep constant nonzero sign on the open bridge and remain within an open half-turn",
        "certified_by_source_report": contact_report["summary_metrics"]["all_selected_hinge_contacts_orientation_certified"],
    }
    shared_face = {
        "method": "residual_shared_face_cubic_formula",
        "formula": "sin(theta/2)^3 * cos(theta/2)",
        "interval": "0 < theta <= 0.5 degrees",
        "positive_on_bridge": half_right > 0.0 and half_right < 90.0,
        "formula_check_all_targets_passed": face_report["summary_metrics"]["all_targets_formula_checked"],
        "all_sampled_triples_positive": face_report["summary_metrics"]["all_sampled_triples_positive"],
    }
    shared_edge = {
        "method": "residual_shared_edge_near_zero_formula",
        "formula": "normalized_gap = sin(theta) / sqrt(2 * (1 + cos(theta)^2))",
        "interval": "0 < theta <= 0.5 degrees",
        "positive_on_bridge": True,
        "positive_reason": "sin(theta) > 0 on the open bridge and the denominator is strictly positive",
        "formula_check_all_targets_passed": edge_report["summary_metrics"]["all_targets_formula_checked"],
        "all_sampled_gaps_positive": edge_report["summary_metrics"]["all_sampled_gaps_positive"],
    }
    return {
        "selected_hinge_orientation": selected_hinge_orientation,
        "residual_shared_face": shared_face,
        "residual_shared_edge": shared_edge,
        "bridge_certified": (
            selected_hinge_orientation["certified_by_source_report"]
            and shared_face["positive_on_bridge"]
            and shared_face["formula_check_all_targets_passed"]
            and shared_face["all_sampled_triples_positive"]
            and shared_edge["positive_on_bridge"]
            and shared_edge["formula_check_all_targets_passed"]
            and shared_edge["all_sampled_gaps_positive"]
        ),
    }


def inventory_by_tree(inventory_report: dict) -> dict[str, dict]:
    output = {}
    for tree in inventory_report["tree_reports"]:
        residual_edges = []
        residual_faces = []
        selected_hinges = []
        for record in tree["pair_records"]:
            item = {
                "pair": record["pair"],
                "role": record["role"],
                "axis_names": record["axis_names"],
                "estimated_order": record["near_zero_order_fit"]["estimated_order"],
            }
            if record["role"] == "selected_hinge_contact":
                selected_hinges.append(item)
            elif record["role"] == "residual_shared_edge":
                residual_edges.append(item)
            elif record["role"] == "residual_shared_face":
                residual_faces.append(item)
        output[tree["tree_id"]] = {
            "selected_hinge_contacts": selected_hinges,
            "residual_shared_edge_targets": residual_edges,
            "residual_shared_face_targets": residual_faces,
            "expected_bridge_shape_confirmed": len(selected_hinges) == 3 and len(residual_edges) == 2 and len(residual_faces) == 1,
        }
    return output


def finite_tree_summaries(face_certificate_report: dict, finite_certificate_report: dict) -> dict[str, dict]:
    summaries = {}
    for tree in face_certificate_report["tree_reports"]:
        if tree["tree_id"] == "TREE_007":
            summaries["TREE_007"] = {
                "source": "residual_shared_face_analytic_certificate_report.json",
                "finite_interval_degrees": FINITE_INTERVAL_DEGREES,
                "ray_cells_covered": tree["summary_metrics"]["fully_composite_certified_cell_count_after_shared_face_formula"],
                "ray_cell_count": tree["summary_metrics"]["cell_count"],
                "pair_cells_covered": tree["summary_metrics"]["covered_pair_cell_count_after_shared_face_formula"],
                "pair_cell_count": tree["summary_metrics"]["total_pair_cell_count"],
                "remaining_unresolved_pair_cells": tree["summary_metrics"]["remaining_unresolved_pair_cell_count"],
            }
    tree021 = finite_certificate_report["tree021_summary_after_targeted_guard"]
    summaries["TREE_021"] = {
        "source": "tree021_residual_edge_targeted_guard_report.json",
        "finite_interval_degrees": FINITE_INTERVAL_DEGREES,
        "ray_cells_covered": tree021["fully_composite_certified_cell_count_after_targeted_guard"],
        "ray_cell_count": tree021["cell_count"],
        "pair_cells_covered": tree021["covered_pair_cell_count_after_targeted_guard"],
        "pair_cell_count": tree021["total_pair_cell_count"],
        "remaining_unresolved_pair_cells": tree021["remaining_unresolved_pair_cell_count_after_targeted_guard"],
    }
    return summaries


def build_report() -> dict:
    finite_report = load_json(RESULTS_DIR / FINITE_CERTIFICATE_REPORT)
    face_report = load_json(RESULTS_DIR / FACE_FORMULA_REPORT)
    edge_report = load_json(RESULTS_DIR / EDGE_FORMULA_REPORT)
    inventory_report = load_json(RESULTS_DIR / NEAR_ZERO_INVENTORY_REPORT)
    contact_report = load_json(RESULTS_DIR / CONTACT_ORIENTATION_REPORT)
    face_certificate_report = load_json(RESULTS_DIR / "residual_shared_face_analytic_certificate_report.json")

    bridge = bridge_formula_certificates(face_report, edge_report, contact_report)
    inventory = inventory_by_tree(inventory_report)
    finite_summaries = finite_tree_summaries(face_certificate_report, finite_report)
    finite_completed = finite_report["summary_metrics"]["all_representative_ray_cells_fully_certified_after_targeted_guard"]
    inventory_confirmed = all(inventory[tree_id]["expected_bridge_shape_confirmed"] for tree_id in REPRESENTATIVES)
    per_tree = []
    for tree_id in REPRESENTATIVES:
        finite = finite_summaries[tree_id]
        bridge_ok = bridge["bridge_certified"] and inventory[tree_id]["expected_bridge_shape_confirmed"]
        per_tree.append(
            {
                "tree_id": tree_id,
                "status": "open_limit_representative_ray_certified" if finite_completed and bridge_ok else "open_limit_representative_ray_not_certified",
                "bridge_interval_degrees": BRIDGE_INTERVAL_DEGREES,
                "finite_interval_degrees": FINITE_INTERVAL_DEGREES,
                "bridge_inventory": inventory[tree_id],
                "finite_summary": finite,
                "open_limit_interval_degrees": "0 < theta <= 120",
                "theta_zero_status": "excluded_closed_configuration",
            }
        )

    open_limit_completed = finite_completed and bridge["bridge_certified"] and inventory_confirmed
    return {
        "case_id": CASE_ID,
        "status": "open_limit_ray_certificate_completed" if open_limit_completed else "open_limit_ray_certificate_incomplete",
        "source_reports": [
            f"results/{CASE_ID}/{FINITE_CERTIFICATE_REPORT}",
            f"results/{CASE_ID}/residual_shared_face_analytic_certificate_report.json",
            f"results/{CASE_ID}/{FACE_FORMULA_REPORT}",
            f"results/{CASE_ID}/{EDGE_FORMULA_REPORT}",
            f"results/{CASE_ID}/{NEAR_ZERO_INVENTORY_REPORT}",
            f"results/{CASE_ID}/{CONTACT_ORIENTATION_REPORT}",
        ],
        "summary_metrics": {
            "representative_count": len(REPRESENTATIVES),
            "finite_certificate_completed_on_0_5_to_120": finite_completed,
            "near_zero_bridge_certified_on_0_to_0_5_open_left": bridge["bridge_certified"],
            "near_zero_inventory_shape_confirmed": inventory_confirmed,
            "open_limit_representative_ray_certificate_completed": open_limit_completed,
        },
        "bridge_certificate": bridge,
        "tree_reports": per_tree,
        "limitations": [
            "The certificate covers only the two representative signed-ray classes TREE_007 and TREE_021.",
            "The certificate covers 0 < theta <= 120 degrees; theta = 0 is excluded as the closed contact configuration.",
            "The report applies documented formula lemmas and source ledgers; it does not machine-derive the formulas symbolically.",
            "The certificate is zero-thickness and does not prove physical printability or hinge clearances with thickness.",
            "The certificate does not cover the full 3-parameter cylindrical component graph or dynamic connectedness between signed-ray classes.",
        ],
    }


def main() -> int:
    report = build_report()
    write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "summary_metrics": report["summary_metrics"],
                "tree_status": {tree["tree_id"]: tree["status"] for tree in report["tree_reports"]},
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())