"""TREE_007 residual-contact failure classification.

This is the TREE_007 mirror classification for the refined-edge interval guard.
It reuses the shared residual-contact classifier after setting the target tree,
then rewrites the claim-boundary text so the report does not inherit TREE_021
wording.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_residual_contact_failure_classification_report.json"
TARGET_TREE_ID = "TREE_007"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def build_report() -> dict:
    original_target = classify.TARGET_TREE_ID
    original_report_name = classify.REPORT_NAME
    try:
        classify.TARGET_TREE_ID = TARGET_TREE_ID
        classify.REPORT_NAME = REPORT_NAME
        report = classify.build_report()
    finally:
        classify.TARGET_TREE_ID = original_target
        classify.REPORT_NAME = original_report_name

    report["status"] = "tree007_residual_contact_failure_classification_completed"
    report["source_reports"] = [
        f"results/{CASE_ID}/tree007_refined_edge_interval_guard_probe_report.json",
        f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
        f"results/{CASE_ID}/two_class_component_search_report.json",
    ]
    report["model_implications"] = [
        "For TREE_007, the residual shared-face gate is P2-P3 rather than TREE_021 P0-P2.",
        "The residual shared-edge pairs remain P0-P3 and P1-P2, but their counts and source-edge distribution must be audited separately from TREE_021.",
        "This classification is diagnostic: it identifies the residual-contact backlog for a TREE_007 mirror overlay, but it does not certify the failed residual-contact segments.",
    ]
    report["limitations"] = [
        "This classification recomputes residual-pair guard data only for TREE_007 refined spanning-tree segments.",
        "It is diagnostic and does not certify the failed residual-contact segments.",
        "It does not prove transfer from TREE_021 and does not cover every free graph edge.",
        "No physical hinge offsets, thickness, mesh export, or printability gates are modeled.",
    ]
    return report


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
                "failure_pattern_counts": report["failure_pattern_counts"],
                "pair_counts": {
                    "-".join(item["pair"]): {
                        "role": item["role"],
                        "uncovered": item["uncovered_pair_segment_count"],
                        "certified": item["clearance_certified_pair_segment_count"],
                    }
                    for item in report["pair_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())