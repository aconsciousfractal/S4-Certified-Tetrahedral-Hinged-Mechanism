"""Contact-orientation overlay for two S4 ray-cell guards.

This audit reuses the ray-cell SAT clearance guard and adds a finite contact
orientation certificate for selected hinge-contact pairs. Residual contacts that
lack clearance remain unresolved and are reported explicitly.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "two_class_contact_orientation_report.json"
MAX_STORED_UNRESOLVED_CELLS = 80

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as guard  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def selected_hinge_by_pair(case: dict, tree: dict) -> dict[tuple[str, str], dict]:
    records = {}
    for hinge_id in tree["hinge_ids"]:
        hinge = case["hinge_by_id"][hinge_id]
        records[tuple(sorted(hinge["pieces"]))] = hinge
    return records


def signed_interval_for_hinge(cell: dict, sign: int) -> list[float]:
    left = float(sign) * float(cell["theta_left_degrees"])
    right = float(sign) * float(cell["theta_right_degrees"])
    return [round(min(left, right), 8), round(max(left, right), 8)]


def hinge_orientation_certificate(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    cell: dict,
    pair: tuple[str, str],
    hinge_by_pair: dict[tuple[str, str], dict],
    center_sample_status: str,
) -> dict:
    hinge = hinge_by_pair[pair]
    sign = int(signs_by_hinge[hinge["hinge_id"]])
    interval = signed_interval_for_hinge(cell, sign)
    excludes_zero = interval[0] > 0.0 or interval[1] < 0.0
    within_half_turn = max(abs(interval[0]), abs(interval[1])) < 180.0
    source_contact = next(
        contact for contact in case["contacts"] if contact["contact_id"] == hinge["source_contact"]
    )
    certified = center_sample_status == "collision_free" and excludes_zero and within_half_turn
    return {
        "method": "selected_hinge_contact_orientation",
        "certified": certified,
        "hinge_id": hinge["hinge_id"],
        "source_contact": hinge["source_contact"],
        "source_contact_type": source_contact["type"],
        "axis_labels": hinge["axis_labels"],
        "signed_angle_interval_degrees": interval,
        "angle_interval_excludes_zero": excludes_zero,
        "angle_interval_within_open_half_turn": within_half_turn,
        "center_sample_status": center_sample_status,
        "reason": (
            "hinge_angle_interval_has_constant_nonzero_opening_sign"
            if certified
            else "hinge_angle_interval_not_certifiable_by_orientation_protocol"
        ),
    }


def overlay_cell(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    paths_by_piece: dict[str, list[dict]],
    contacts_by_pair: dict[tuple[str, str], dict],
    hinge_by_pair: dict[tuple[str, str], dict],
    cell: dict,
) -> dict:
    base = guard.cell_guard_record(case, tree, signs_by_hinge, paths_by_piece, contacts_by_pair, cell)
    pair_records = []
    for record in base["pair_records"]:
        pair = tuple(record["pair"])
        orientation = None
        orientation_certified = False
        if record["role"] == "selected_hinge_contact":
            orientation = hinge_orientation_certificate(
                case,
                tree,
                signs_by_hinge,
                cell,
                pair,
                hinge_by_pair,
                base["center_sample_status"],
            )
            orientation_certified = orientation["certified"]

        covered = bool(record["certified"] or orientation_certified)
        if record["certified"]:
            coverage_method = "clearance_guard"
        elif orientation_certified:
            coverage_method = "selected_hinge_contact_orientation"
        elif record["role"].startswith("residual_"):
            coverage_method = "unresolved_residual_contact"
        else:
            coverage_method = "unresolved_clearance_guard_failure"

        pair_records.append(
            {
                "pair": list(pair),
                "role": record["role"],
                "clearance_certified": bool(record["certified"]),
                "orientation_certified": orientation_certified,
                "covered_by_composite_certificate": covered,
                "coverage_method": coverage_method,
                "center_axis_overlap": record["center_axis_overlap"],
                "guard_bound": record["guard_bound"],
                "post_guard_overlap_bound": record["post_guard_overlap_bound"],
                "orientation_certificate": orientation,
            }
        )

    covered_count = sum(1 for record in pair_records if record["covered_by_composite_certificate"])
    return {
        "cell_id": base["cell_id"],
        "theta_interval_degrees": [base["theta_left_degrees"], base["theta_right_degrees"]],
        "theta_center_degrees": base["theta_center_degrees"],
        "center_sample_status": base["center_sample_status"],
        "pair_count": len(pair_records),
        "covered_pair_count": covered_count,
        "uncovered_pair_count": len(pair_records) - covered_count,
        "fully_composite_certified": covered_count == len(pair_records),
        "pair_records": pair_records,
    }


def summarize_pairs(cells: list[dict]) -> list[dict]:
    summary: dict[tuple[str, str], dict] = {}
    for cell in cells:
        for record in cell["pair_records"]:
            pair = tuple(record["pair"])
            item = summary.setdefault(
                pair,
                {
                    "pair": pair,
                    "role": record["role"],
                    "cell_count": 0,
                    "clearance_certified_cell_count": 0,
                    "orientation_certified_cell_count": 0,
                    "covered_cell_count": 0,
                    "uncovered_cell_count": 0,
                    "coverage_methods": {},
                    "first_uncovered_cell": None,
                    "last_uncovered_cell": None,
                },
            )
            item["cell_count"] += 1
            if record["clearance_certified"]:
                item["clearance_certified_cell_count"] += 1
            if record["orientation_certified"]:
                item["orientation_certified_cell_count"] += 1
            method = record["coverage_method"]
            item["coverage_methods"][method] = item["coverage_methods"].get(method, 0) + 1
            if record["covered_by_composite_certificate"]:
                item["covered_cell_count"] += 1
            else:
                item["uncovered_cell_count"] += 1
                compact = {
                    "cell_id": cell["cell_id"],
                    "theta_interval_degrees": cell["theta_interval_degrees"],
                    "coverage_method": method,
                    "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
                }
                if item["first_uncovered_cell"] is None:
                    item["first_uncovered_cell"] = compact
                item["last_uncovered_cell"] = compact
    output = []
    for item in summary.values():
        output.append(
            {
                "pair": list(item["pair"]),
                "role": item["role"],
                "cell_count": item["cell_count"],
                "clearance_certified_cell_count": item["clearance_certified_cell_count"],
                "orientation_certified_cell_count": item["orientation_certified_cell_count"],
                "covered_cell_count": item["covered_cell_count"],
                "uncovered_cell_count": item["uncovered_cell_count"],
                "coverage_methods": item["coverage_methods"],
                "first_uncovered_cell": item["first_uncovered_cell"],
                "last_uncovered_cell": item["last_uncovered_cell"],
            }
        )
    return sorted(output, key=lambda item: item["pair"])


def audit_tree(case: dict, class_id: str, tree_id: str, signs_by_hinge: dict[str, int]) -> dict:
    tree = comp.find_tree(case, tree_id)
    paths = guard.tree_paths_from_root(case, tree)
    contacts = guard.contact_by_pair(case)
    hinges = selected_hinge_by_pair(case, tree)
    cells = [
        overlay_cell(case, tree, signs_by_hinge, paths, contacts, hinges, cell)
        for cell in guard.degree_cells(
            guard.RAY_CELL_START_DEGREES,
            guard.RAY_CELL_END_DEGREES,
            guard.RAY_CELL_STEP_DEGREES,
        )
    ]
    pair_summary = summarize_pairs(cells)
    total_pair_cells = sum(cell["pair_count"] for cell in cells)
    covered_pair_cells = sum(cell["covered_pair_count"] for cell in cells)
    selected_hinge_orientation = sum(
        1
        for cell in cells
        for record in cell["pair_records"]
        if record["orientation_certified"]
    )
    unresolved_residual = sum(
        1
        for cell in cells
        for record in cell["pair_records"]
        if record["coverage_method"] == "unresolved_residual_contact"
    )
    stored_unresolved = []
    for cell in cells:
        unresolved = [record for record in cell["pair_records"] if not record["covered_by_composite_certificate"]]
        if not unresolved:
            continue
        stored_unresolved.append(
            {
                "cell_id": cell["cell_id"],
                "theta_interval_degrees": cell["theta_interval_degrees"],
                "unresolved_pair_records": [
                    {
                        "pair": record["pair"],
                        "role": record["role"],
                        "coverage_method": record["coverage_method"],
                        "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
                    }
                    for record in unresolved
                ],
            }
        )
        if len(stored_unresolved) >= MAX_STORED_UNRESOLVED_CELLS:
            break

    return {
        "class_id": class_id,
        "tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs_by_hinge,
        "status": "contact_orientation_overlay_completed",
        "cell_protocol": {
            "theta_start_degrees": guard.RAY_CELL_START_DEGREES,
            "theta_end_degrees": guard.RAY_CELL_END_DEGREES,
            "theta_step_degrees": guard.RAY_CELL_STEP_DEGREES,
            "cell_count": len(cells),
            "orientation_rule": "selected hinge angle interval must exclude zero and stay within an open half-turn; midpoint sample must be collision-free",
        },
        "summary_metrics": {
            "cell_count": len(cells),
            "center_sample_collision_free_cell_count": sum(
                1 for cell in cells if cell["center_sample_status"] == "collision_free"
            ),
            "fully_composite_certified_cell_count": sum(
                1 for cell in cells if cell["fully_composite_certified"]
            ),
            "total_pair_cell_count": total_pair_cells,
            "covered_pair_cell_count": covered_pair_cells,
            "uncovered_pair_cell_count": total_pair_cells - covered_pair_cells,
            "selected_hinge_orientation_certified_pair_cell_count": selected_hinge_orientation,
            "unresolved_residual_contact_pair_cell_count": unresolved_residual,
        },
        "pair_summary": pair_summary,
        "stored_unresolved_cells": stored_unresolved,
    }


def build_report() -> dict:
    case = batch.build_case()
    signs_by_tree = comp.certified_signs_by_tree()
    audits = [
        audit_tree(case, class_id, tree_id, signs_by_tree[tree_id])
        for class_id, tree_id in comp.REPRESENTATIVES.items()
    ]
    return {
        "case_id": CASE_ID,
        "status": "two_class_contact_orientation_completed",
        "representatives": comp.REPRESENTATIVES,
        "summary_metrics": {
            "representative_count": len(audits),
            "all_center_samples_collision_free": all(
                audit["summary_metrics"]["center_sample_collision_free_cell_count"]
                == audit["summary_metrics"]["cell_count"]
                for audit in audits
            ),
            "all_selected_hinge_contacts_orientation_certified": all(
                all(
                    item["role"] != "selected_hinge_contact"
                    or item["orientation_certified_cell_count"] == item["cell_count"]
                    for item in audit["pair_summary"]
                )
                for audit in audits
            ),
            "all_cells_fully_composite_certified": all(
                audit["summary_metrics"]["fully_composite_certified_cell_count"]
                == audit["summary_metrics"]["cell_count"]
                for audit in audits
            ),
        },
        "representative_audits": audits,
        "limitations": [
            "This overlay certifies selected hinge-contact orientation under the finite ray-cell protocol; it is not a full symbolic contact proof.",
            "Residual contacts not selected as hinges remain unresolved when the clearance guard fails.",
            "The result covers ray cells from 0.5 to 120 degrees, not theta=0 and not the full cylindrical component graph.",
            "No physical hinge offsets, thickness, clearance, mesh export, or printability gate is modeled.",
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
                "tree_metrics": {
                    audit["tree_id"]: audit["summary_metrics"]
                    for audit in report["representative_audits"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())