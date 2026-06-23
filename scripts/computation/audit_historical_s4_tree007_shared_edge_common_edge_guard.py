"""TREE_007 residual shared-edge common-edge guard.

Mirror of the TREE_021 common-edge guard for TREE_007. It targets the residual
shared-edge pairs P0-P3 and P1-P2 after the TREE_007 refined-edge interval
probe. The shared-edge axis family is the same M_AB-M_CD common-edge branch,
but the ledger is recomputed for TREE_007 and written separately.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_shared_edge_common_edge_guard_report.json"
TARGET_TREE_ID = "TREE_007"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_tree021_shared_edge_common_edge_guard as shared_edge  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def build_report() -> dict:
    original_target = shared_edge.TARGET_TREE_ID
    original_report_name = shared_edge.REPORT_NAME
    try:
        shared_edge.TARGET_TREE_ID = TARGET_TREE_ID
        shared_edge.REPORT_NAME = REPORT_NAME
        report = shared_edge.build_report()
    finally:
        shared_edge.TARGET_TREE_ID = original_target
        shared_edge.REPORT_NAME = original_report_name

    report["status"] = "tree007_shared_edge_common_edge_guard_completed"
    report["source_reports"] = [
        f"results/{CASE_ID}/tree007_residual_contact_failure_classification_report.json",
        f"results/{CASE_ID}/tree007_refined_edge_interval_guard_probe_report.json",
        f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
        f"results/{CASE_ID}/two_class_component_search_report.json",
    ]
    report["limitations"] = [
        "This is a finite adaptive guard for TREE_007 P0-P3/P1-P2 residual shared-edge pair-segments, not a symbolic theorem.",
        "The guard covers replacement leaves for the original TREE_007 shared-edge backlog by adaptive subdivision; it does not certify arbitrary continuous paths outside this finite ledger.",
        "TREE_021 evidence is not imported; theta=0, the full continuous 3-parameter component, and physical hinge thickness/clearance remain outside this report.",
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
                "first_cover_counts_by_threshold": report["adaptive_summary"]["first_cover_counts_by_threshold"],
                "first_cover_counts_by_pair": report["adaptive_summary"]["first_cover_counts_by_pair"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())