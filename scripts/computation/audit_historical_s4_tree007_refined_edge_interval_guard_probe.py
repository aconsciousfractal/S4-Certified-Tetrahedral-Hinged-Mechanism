"""TREE_007 refined-edge interval-guard probe.

This is the TREE_007 mirror of the original TREE_021 refined-edge interval
probe. It reuses the shared refined-edge guard implementation but writes a
separate report so the TREE_021 baseline remains untouched.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_refined_edge_interval_guard_probe_report.json"
TARGET_TREE_ID = "TREE_007"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def build_report() -> dict:
    case = batch.build_case()
    component_report = probe.load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_by_tree = {audit["tree_id"]: audit for audit in component_report["representative_audits"]}
    signs_by_tree = comp.certified_signs_by_tree()
    tree_report = probe.audit_tree(case, source_by_tree[TARGET_TREE_ID], signs_by_tree)
    return {
        "case_id": CASE_ID,
        "status": "tree007_refined_edge_interval_guard_probe_completed",
        "source_reports": [
            f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "target_tree_ids": [TARGET_TREE_ID],
        "interval_guard_protocol": {
            "segment_source": "refined BFS spanning-tree segments with max coordinate delta <= 5 degrees",
            "sat_tolerance": probe.ray_guard.SAT_TOLERANCE,
            "displacement_safety_factor": probe.ray_guard.DISPLACEMENT_SAFETY_FACTOR,
            "clearance_rule": "center separating-axis overlap plus local angular displacement bound must stay <= SAT tolerance",
            "selected_hinge_rule": "selected hinge angle interval must exclude zero and stay within an open half-turn",
        },
        "summary_metrics": {
            "tree_count": 1,
            "total_refined_segment_count": tree_report["summary_metrics"]["refined_segment_count"],
            "total_fully_interval_guard_certified_segment_count": tree_report["summary_metrics"]["fully_interval_guard_certified_segment_count"],
            "total_failed_interval_guard_segment_count": tree_report["summary_metrics"]["failed_interval_guard_segment_count"],
            "total_uncovered_pair_segment_count": tree_report["summary_metrics"]["uncovered_pair_segment_count"],
        },
        "tree_reports": [tree_report],
        "limitations": [
            "This is a conservative interval-guard probe, not exact symbolic interval rotation arithmetic.",
            "Only TREE_007 is targeted in this mirror probe.",
            "Residual or near-contact pairs may fail this guard even when sampled subdivision points are collision-free.",
            "The result does not certify theta=0, the full continuous 3-parameter component, physical hinge thickness, offsets, mesh export, or printability.",
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
                "tree_summaries": {
                    item["tree_id"]: item["summary_metrics"] for item in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())