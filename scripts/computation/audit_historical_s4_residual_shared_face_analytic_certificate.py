"""Residual shared-face analytic certificate overlay for S4 representatives.

This script does not recompute all ray cells. It reads the contact-orientation
ledger and the residual shared-face formula-check report, then covers the two
critical residual shared-face pair-cells using the interval positivity of the
candidate formula

    sin(theta/2)^3 * cos(theta/2)

on 0.5 <= theta <= 120 degrees. The symbolic derivation is documented in the
companion summary/lemma; this script records the interval logic and resulting
ledger update.
"""

from __future__ import annotations

import json
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "residual_shared_face_analytic_certificate_report.json"
CONTACT_ORIENTATION_REPORT = "two_class_contact_orientation_report.json"
FORMULA_CHECK_REPORT = "residual_shared_face_formula_check_report.json"
THETA_INTERVAL_DEGREES = [0.5, 120.0]
ANALYTIC_TARGETS = {
    ("TREE_007", ("P2", "P3")): "TREE_007_P2_P3",
    ("TREE_021", ("P0", "P2")): "TREE_021_P0_P2",
}

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


def pair_tuple(record: dict) -> tuple[str, str]:
    return tuple(record["pair"])


def formula_target_by_id(formula_report: dict) -> dict[str, dict]:
    return {target["target_id"]: target for target in formula_report["target_reports"]}


def interval_positivity_certificate() -> dict:
    theta_left, theta_right = THETA_INTERVAL_DEGREES
    half_left = theta_left / 2.0
    half_right = theta_right / 2.0
    return {
        "theta_interval_degrees": THETA_INTERVAL_DEGREES,
        "half_theta_interval_degrees": [half_left, half_right],
        "sin_positive_reason": "0 < theta/2 on the certified interval",
        "cos_positive_reason": "theta/2 < 90 degrees on the certified interval",
        "formula": "sin(theta/2)^3 * cos(theta/2)",
        "formula_positive_on_interval": half_left > 0.0 and half_right < 90.0,
    }


def audit_tree(audit: dict, formula_targets: dict[str, dict], positivity: dict) -> dict:
    tree_id = audit["tree_id"]
    original = audit["summary_metrics"]
    covered_by_formula = []
    remaining_unresolved_cells = []
    remaining_unresolved_pair_cell_count = 0
    covered_pair_cell_count = original["covered_pair_cell_count"]

    for cell in audit["stored_unresolved_cells"]:
        remaining_records = []
        formula_records = []
        for record in cell["unresolved_pair_records"]:
            pair = pair_tuple(record)
            target_id = ANALYTIC_TARGETS.get((tree_id, pair))
            if target_id is None:
                remaining_records.append(record)
                continue
            target_report = formula_targets[target_id]
            certified = (
                positivity["formula_positive_on_interval"]
                and target_report["summary_metrics"]["all_formula_checks_within_tolerance"]
                and target_report["summary_metrics"]["all_triples_positive"]
            )
            if certified:
                formula_records.append(
                    {
                        "pair": list(pair),
                        "target_id": target_id,
                        "coverage_method": "residual_shared_face_analytic_formula",
                        "formula": "sin(theta/2)^3 * cos(theta/2)",
                        "theta_interval_degrees": cell["theta_interval_degrees"],
                    }
                )
                covered_pair_cell_count += 1
            else:
                remaining_records.append(record)
        if formula_records:
            covered_by_formula.append(
                {
                    "cell_id": cell["cell_id"],
                    "theta_interval_degrees": cell["theta_interval_degrees"],
                    "covered_pair_records": formula_records,
                }
            )
        if remaining_records:
            remaining_unresolved_pair_cell_count += len(remaining_records)
            remaining_unresolved_cells.append(
                {
                    "cell_id": cell["cell_id"],
                    "theta_interval_degrees": cell["theta_interval_degrees"],
                    "unresolved_pair_records": remaining_records,
                }
            )

    total_cells = original["cell_count"]
    fully_certified_cell_count = total_cells - len(remaining_unresolved_cells)
    return {
        "tree_id": tree_id,
        "status": "residual_shared_face_analytic_overlay_completed",
        "original_summary_metrics": original,
        "summary_metrics": {
            "cell_count": total_cells,
            "original_fully_composite_certified_cell_count": original["fully_composite_certified_cell_count"],
            "fully_composite_certified_cell_count_after_shared_face_formula": fully_certified_cell_count,
            "total_pair_cell_count": original["total_pair_cell_count"],
            "original_covered_pair_cell_count": original["covered_pair_cell_count"],
            "covered_pair_cell_count_after_shared_face_formula": covered_pair_cell_count,
            "covered_pair_cell_count_added_by_shared_face_formula": covered_pair_cell_count - original["covered_pair_cell_count"],
            "remaining_unresolved_pair_cell_count": remaining_unresolved_pair_cell_count,
            "remaining_unresolved_cell_count": len(remaining_unresolved_cells),
        },
        "stored_formula_covered_cells": covered_by_formula[:80],
        "stored_remaining_unresolved_cells": remaining_unresolved_cells[:80],
    }


def build_report() -> dict:
    contact_report = load_json(RESULTS_DIR / CONTACT_ORIENTATION_REPORT)
    formula_report = load_json(RESULTS_DIR / FORMULA_CHECK_REPORT)
    formula_targets = formula_target_by_id(formula_report)
    positivity = interval_positivity_certificate()
    tree_reports = [
        audit_tree(audit, formula_targets, positivity)
        for audit in contact_report["representative_audits"]
    ]
    return {
        "case_id": CASE_ID,
        "status": "residual_shared_face_analytic_certificate_completed",
        "source_reports": [
            f"results/{CASE_ID}/{CONTACT_ORIENTATION_REPORT}",
            f"results/{CASE_ID}/{FORMULA_CHECK_REPORT}",
        ],
        "analytic_formula_certificate": positivity,
        "summary_metrics": {
            "tree_count": len(tree_reports),
            "formula_check_all_targets_passed": formula_report["summary_metrics"]["all_targets_formula_checked"],
            "formula_positive_on_interval": positivity["formula_positive_on_interval"],
            "tree007_fully_certified_after_overlay": next(
                report["summary_metrics"]["remaining_unresolved_pair_cell_count"] == 0
                for report in tree_reports
                if report["tree_id"] == "TREE_007"
            ),
            "tree021_remaining_unresolved_pair_cell_count": next(
                report["summary_metrics"]["remaining_unresolved_pair_cell_count"]
                for report in tree_reports
                if report["tree_id"] == "TREE_021"
            ),
            "total_pair_cells_added_by_shared_face_formula": sum(
                report["summary_metrics"]["covered_pair_cell_count_added_by_shared_face_formula"]
                for report in tree_reports
            ),
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This report applies the documented formula lemma; it does not machine-derive the formula symbolically.",
            "It covers only the residual shared-face targets TREE_007 P2-P3 and TREE_021 P0-P2.",
            "The residual shared-edge target TREE_021 P1-P2 remains unresolved in two ray cells.",
            "The certificate covers ray cells from 0.5 to 120 degrees, not theta=0 and not the full cylindrical component graph.",
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