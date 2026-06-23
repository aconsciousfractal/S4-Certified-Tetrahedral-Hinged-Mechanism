"""Targeted guard for the last TREE_021 residual shared-edge pair.

The previous residual shared-face analytic overlay left only two unresolved
pair-cells: TREE_021 P1-P2 on theta intervals 0.5..0.75 and 0.75..1.0. This
script covers that small interval with fixed 0.05-degree clearance subcells.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree021_residual_edge_targeted_guard_report.json"
SOURCE_REPORT = "residual_shared_face_analytic_certificate_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P1", "P2")
TARGET_INTERVAL_DEGREES = [0.5, 1.0]
TARGET_SUBCELL_STEP_DEGREES = 0.05

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as guard  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def subcells(start: float, end: float, step: float) -> list[dict]:
    cells = []
    left = float(start)
    index = 0
    while left < end - 1.0e-12:
        right = min(float(end), left + float(step))
        cells.append(
            {
                "cell_id": f"tree021_p1p2_subcell_{index:03d}",
                "theta_left_degrees": round(left, 10),
                "theta_right_degrees": round(right, 10),
                "theta_center_degrees": round((left + right) / 2.0, 10),
                "theta_half_width_degrees": round((right - left) / 2.0, 10),
            }
        )
        left = right
        index += 1
    return cells


def target_pair_record(cell: dict) -> dict:
    case = target_pair_record.case
    tree = target_pair_record.tree
    signs = target_pair_record.signs
    paths = target_pair_record.paths
    contacts = target_pair_record.contacts
    record = guard.cell_guard_record(case, tree, signs, paths, contacts, cell)
    for pair_record in record["pair_records"]:
        if tuple(pair_record["pair"]) == TARGET_PAIR:
            return pair_record
    raise RuntimeError(f"Target pair not found: {TARGET_PAIR}")


def original_remaining(source_report: dict) -> dict:
    tree_report = next(report for report in source_report["tree_reports"] if report["tree_id"] == TARGET_TREE_ID)
    remaining = tree_report["stored_remaining_unresolved_cells"]
    target_remaining = []
    for cell in remaining:
        for record in cell["unresolved_pair_records"]:
            if tuple(record["pair"]) == TARGET_PAIR:
                target_remaining.append(
                    {
                        "cell_id": cell["cell_id"],
                        "theta_interval_degrees": cell["theta_interval_degrees"],
                        "pair": list(TARGET_PAIR),
                        "role": record["role"],
                    }
                )
    return {
        "tree_summary_before_targeted_guard": tree_report["summary_metrics"],
        "target_remaining_parent_pair_cells": target_remaining,
    }


def build_report() -> dict:
    source = load_json(RESULTS_DIR / SOURCE_REPORT)
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    target_pair_record.case = case
    target_pair_record.tree = tree
    target_pair_record.signs = signs_by_tree[TARGET_TREE_ID]
    target_pair_record.paths = guard.tree_paths_from_root(case, tree)
    target_pair_record.contacts = guard.contact_by_pair(case)

    original = original_remaining(source)
    subcell_records = []
    for cell in subcells(TARGET_INTERVAL_DEGREES[0], TARGET_INTERVAL_DEGREES[1], TARGET_SUBCELL_STEP_DEGREES):
        pair_record = target_pair_record(cell)
        subcell_records.append(
            {
                "cell_id": cell["cell_id"],
                "theta_interval_degrees": [cell["theta_left_degrees"], cell["theta_right_degrees"]],
                "theta_center_degrees": cell["theta_center_degrees"],
                "clearance_certified": bool(pair_record["certified"]),
                "center_axis_overlap": round(float(pair_record["center_axis_overlap"]), 15),
                "guard_bound": round(float(pair_record["guard_bound"]), 15),
                "post_guard_overlap_bound": round(float(pair_record["post_guard_overlap_bound"]), 15),
            }
        )

    all_subcells_certified = all(record["clearance_certified"] for record in subcell_records)
    parent_pair_cells_covered = len(original["target_remaining_parent_pair_cells"]) if all_subcells_certified else 0
    before = original["tree_summary_before_targeted_guard"]
    tree021_after = {
        "cell_count": before["cell_count"],
        "fully_composite_certified_cell_count_after_targeted_guard": before["cell_count"] if all_subcells_certified else before["fully_composite_certified_cell_count_after_shared_face_formula"],
        "total_pair_cell_count": before["total_pair_cell_count"],
        "covered_pair_cell_count_after_targeted_guard": before["covered_pair_cell_count_after_shared_face_formula"] + parent_pair_cells_covered,
        "covered_pair_cell_count_added_by_targeted_guard": parent_pair_cells_covered,
        "remaining_unresolved_pair_cell_count_after_targeted_guard": before["remaining_unresolved_pair_cell_count"] - parent_pair_cells_covered,
    }

    return {
        "case_id": CASE_ID,
        "status": "tree021_residual_edge_targeted_guard_completed",
        "source_report": f"results/{CASE_ID}/{SOURCE_REPORT}",
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_edge",
            "target_interval_degrees": TARGET_INTERVAL_DEGREES,
            "subcell_step_degrees": TARGET_SUBCELL_STEP_DEGREES,
        },
        "summary_metrics": {
            "subcell_count": len(subcell_records),
            "all_subcells_clearance_certified": all_subcells_certified,
            "covered_parent_pair_cell_count_added": parent_pair_cells_covered,
            "tree021_remaining_unresolved_pair_cell_count_after_targeted_guard": tree021_after["remaining_unresolved_pair_cell_count_after_targeted_guard"],
            "tree021_fully_certified_after_targeted_guard": tree021_after["remaining_unresolved_pair_cell_count_after_targeted_guard"] == 0,
            "all_representative_ray_cells_fully_certified_after_targeted_guard": (
                source["summary_metrics"]["tree007_fully_certified_after_overlay"]
                and tree021_after["remaining_unresolved_pair_cell_count_after_targeted_guard"] == 0
            ),
        },
        "original_remaining": original,
        "tree021_summary_after_targeted_guard": tree021_after,
        "subcell_records": subcell_records,
        "limitations": [
            "This is a targeted finite clearance guard for TREE_021 P1-P2 on theta 0.5..1.0 only.",
            "The result completes the representative ray-cell ledger from 0.5 to 120 degrees; it does not cover theta=0.",
            "The result does not certify the full cylindrical component graph or physical hinge clearances.",
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
                "tree021_summary_after_targeted_guard": report["tree021_summary_after_targeted_guard"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())