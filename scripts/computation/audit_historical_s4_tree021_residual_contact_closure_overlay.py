"""TREE_021 residual-contact closure overlay.

This audit is an accounting overlay over the original TREE_021 residual-contact
pair-segment ledger. It combines the three completed evidence blocks:

- P0-P2 edge-branch workflow: 630 original pair-segments.
- P0-P2 face-normal formula guard: 435 original pair-segments.
- P0-P3/P1-P2 shared-edge common-edge guard: 890 original pair-segments.

The overlay does not recompute the geometric guards. It verifies that the source
reports cover the deterministic residual pair-record IDs reconstructed from the
original classification and then emits a closed 1955/1955 ledger.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree021_residual_contact_closure_overlay_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR_P0P2 = ("P0", "P2")
SHARED_EDGE_PAIRS = [("P0", "P3"), ("P1", "P2")]
COMMON_SHARED_EDGE_AXIS = "edge:M_AB-M_CD x M_AB-M_CD"
FACE_NORMAL_AXES = {"left_face:M_AB-C-M_CD", "right_face:M_AB-C-M_CD"}
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_tree021_residual_contact_reconciliation_ledger as recon  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def record_key(record: dict) -> tuple[str, str, str, str]:
    return (record["record_id"], record["segment_id"], record["pair_key"], record["best_axis_name"])


def face_report_keys(face_report: dict) -> set[tuple[str, str, str, str]]:
    keys = set()
    for item in face_report["segment_reports"]:
        if item.get("formula_certified"):
            keys.add((item["record_id"], item["segment_id"], item["pair_key"], item["axis_name"]))
    return keys


def reconstruct_records() -> tuple[list[dict], dict]:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    return recon.residual_pair_records(case, tree, source_audit, signs_by_tree)


def evidence_for_record(record: dict, face_keys: set[tuple[str, str, str, str]]) -> tuple[str, str, str | None]:
    pair = tuple(record["pair"])
    axis = record["best_axis_name"]
    if pair == TARGET_PAIR_P0P2 and axis in branch_probe.TARGET_BRANCHES:
        return "covered", "p0p2_edge_branch_workflow", None
    if pair == TARGET_PAIR_P0P2 and axis in FACE_NORMAL_AXES:
        if record_key(record) in face_keys:
            return "covered", "p0p2_face_normal_formula_guard", None
        return "uncovered", "p0p2_face_normal_formula_guard_missing_record", "face_record_key_not_found_or_not_certified"
    if pair in SHARED_EDGE_PAIRS and axis == COMMON_SHARED_EDGE_AXIS:
        return "covered", "tree021_shared_edge_common_edge_guard", None
    return "uncovered", "unexpected_residual_pair_or_axis", "no_matching_evidence_rule"


def compact_record(record: dict, status: str, method: str, reason: str | None) -> dict:
    return {
        "record_id": record["record_id"],
        "segment_id": record["segment_id"],
        "refined_segment_index": record["refined_segment_index"],
        "pair": record["pair"],
        "pair_key": record["pair_key"],
        "role": record["role"],
        "best_axis_name": record["best_axis_name"],
        "source_edge": record["source_edge"],
        "evidence_status": status,
        "evidence_method": method,
        "uncovered_reason": reason,
    }


def closure_ledger(records: list[dict], face_keys: set[tuple[str, str, str, str]]) -> dict:
    by_pair = defaultdict(Counter)
    by_method = Counter()
    by_axis = Counter()
    by_source_kind = Counter()
    by_theta_pair = Counter()
    uncovered_by_reason = Counter()
    examples = defaultdict(list)
    covered_records = []
    uncovered_records = []

    for record in records:
        status, method, reason = evidence_for_record(record, face_keys)
        item = compact_record(record, status, method, reason)
        by_pair[record["pair_key"]][status] += 1
        by_method[method] += 1
        by_axis[record["best_axis_name"]] += 1
        by_source_kind[record["source_edge"]["kind"]] += 1
        by_theta_pair[record["source_edge"]["theta_pair"]] += 1
        if status == "covered":
            covered_records.append(item)
            add_example(examples[method], item)
        else:
            uncovered_records.append(item)
            uncovered_by_reason[reason or "unknown"] += 1
            add_example(examples["uncovered"], item)

    segment_records = defaultdict(list)
    for item in covered_records + uncovered_records:
        segment_records[item["segment_id"]].append(item)

    segment_status_counts = Counter()
    segment_pattern_counts = Counter()
    segment_method_pattern_counts = Counter()
    for segment_id, items in segment_records.items():
        pair_pattern = " + ".join(sorted(item["pair_key"] for item in items))
        if all(item["evidence_status"] == "covered" for item in items):
            status = "fully_closed"
        else:
            status = "incomplete"
        segment_status_counts[status] += 1
        segment_pattern_counts[pair_pattern] += 1
        method_pattern = " + ".join(sorted(item["evidence_method"] for item in items))
        segment_method_pattern_counts[method_pattern] += 1

    return {
        "pair_segment_status_counts": {
            "covered": len(covered_records),
            "uncovered": len(uncovered_records),
        },
        "pair_segment_status_counts_by_pair": {pair: dict(counter.most_common()) for pair, counter in sorted(by_pair.items())},
        "evidence_method_counts": dict(by_method.most_common()),
        "axis_counts": dict(by_axis.most_common()),
        "source_edge_kind_counts": dict(by_source_kind.most_common()),
        "source_theta_pair_counts": dict(by_theta_pair.most_common()),
        "uncovered_reason_counts": dict(uncovered_by_reason.most_common()),
        "segment_status_counts": dict(segment_status_counts.most_common()),
        "segment_pattern_counts": dict(segment_pattern_counts.most_common()),
        "segment_method_pattern_counts": dict(segment_method_pattern_counts.most_common()),
        "examples": dict(examples),
    }


def consistency_checks(records: list[dict], ledger: dict, source_meta: dict, face_report: dict) -> dict:
    previous = load_json(RESULTS_DIR / "tree021_residual_contact_reconciliation_ledger_report.json")
    classification = load_json(RESULTS_DIR / "residual_contact_failure_classification_report.json")
    shared_edge = load_json(RESULTS_DIR / "tree021_shared_edge_common_edge_guard_report.json")

    reconstructed_face_keys = {
        record_key(record)
        for record in records
        if record["pair_key"] == "P0-P2" and record["best_axis_name"] in FACE_NORMAL_AXES
    }
    report_face_keys = face_report_keys(face_report)
    edge_branch_count = sum(
        1
        for record in records
        if record["pair_key"] == "P0-P2" and record["best_axis_name"] in branch_probe.TARGET_BRANCHES
    )
    shared_edge_count = sum(
        1
        for record in records
        if tuple(record["pair"]) in SHARED_EDGE_PAIRS and record["best_axis_name"] == COMMON_SHARED_EDGE_AXIS
    )

    return {
        "classification_total_matches_reconstruction": len(records) == classification["summary_metrics"]["total_residual_uncovered_pair_segment_count"],
        "source_failed_segment_count": source_meta["failed_refined_segment_count"],
        "previous_reconciliation_uncovered_pair_segment_count": previous["summary_metrics"]["outside_current_finite_evidence_pair_segment_count"],
        "previous_reconciliation_identified_face_normal_count": previous["summary_metrics"]["p0p2_face_normal_unresolved_pair_segment_count"],
        "face_report_input_count": face_report["summary_metrics"]["input_face_normal_pair_segment_count"],
        "face_report_certified_count": face_report["summary_metrics"]["formula_certified_pair_segment_count"],
        "face_report_uncovered_count": face_report["summary_metrics"]["formula_uncovered_pair_segment_count"],
        "face_report_keys_match_reconstructed_face_records": report_face_keys == reconstructed_face_keys,
        "face_report_key_symmetric_difference_count": len(report_face_keys ^ reconstructed_face_keys),
        "edge_branch_record_count": edge_branch_count,
        "edge_branch_matches_previous_reconciliation_count": edge_branch_count == previous["summary_metrics"]["p0p2_edge_branch_parent_pair_segment_count"],
        "shared_edge_record_count": shared_edge_count,
        "shared_edge_matches_guard_input_count": shared_edge_count == shared_edge["summary_metrics"]["input_shared_edge_pair_segment_count"],
        "shared_edge_guard_adaptive_completed": shared_edge["summary_metrics"]["adaptive_completed"],
        "all_pair_segments_covered_by_overlay": ledger["pair_segment_status_counts"]["covered"] == len(records) and ledger["pair_segment_status_counts"]["uncovered"] == 0,
    }


def build_report() -> dict:
    records, source_meta = reconstruct_records()
    face_report = load_json(RESULTS_DIR / "p0p2_face_normal_formula_guard_report.json")
    face_keys = face_report_keys(face_report)
    ledger = closure_ledger(records, face_keys)
    checks = consistency_checks(records, ledger, source_meta, face_report)

    covered = ledger["pair_segment_status_counts"]["covered"]
    uncovered = ledger["pair_segment_status_counts"]["uncovered"]
    segment_status = ledger["segment_status_counts"]

    return {
        "case_id": CASE_ID,
        "status": "tree021_residual_contact_closure_overlay_completed",
        "source_reports": [
            f"results/{CASE_ID}/residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/tree021_residual_contact_reconciliation_ledger_report.json",
            f"results/{CASE_ID}/p0p2_edge_branch_lower_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_same_branch_support_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_refinement_sensitivity_probe_report.json",
            f"results/{CASE_ID}/p0p2_theta_projection_component_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_targeted_endgame_guard_report.json",
            f"results/{CASE_ID}/p0p2_axis_switch_backlog_guard_report.json",
            f"results/{CASE_ID}/tree021_shared_edge_common_edge_guard_report.json",
            f"results/{CASE_ID}/p0p2_face_normal_formula_guard_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "summary_metrics": {
            "original_residual_pair_segment_count": len(records),
            "covered_pair_segment_count": covered,
            "uncovered_pair_segment_count": uncovered,
            "original_failed_refined_segment_count": source_meta["failed_refined_segment_count"],
            "fully_closed_failed_refined_segment_count": segment_status.get("fully_closed", 0),
            "incomplete_failed_refined_segment_count": segment_status.get("incomplete", 0),
            "p0p2_original_pair_segment_count": ledger["pair_segment_status_counts_by_pair"].get("P0-P2", {}).get("covered", 0),
            "p0p2_edge_branch_pair_segment_count": ledger["evidence_method_counts"].get("p0p2_edge_branch_workflow", 0),
            "p0p2_face_normal_pair_segment_count": ledger["evidence_method_counts"].get("p0p2_face_normal_formula_guard", 0),
            "shared_edge_pair_segment_count": ledger["evidence_method_counts"].get("tree021_shared_edge_common_edge_guard", 0),
            "tree021_residual_contacts_closed_by_overlay": covered == len(records) and uncovered == 0,
        },
        "source_ledger": source_meta,
        "closure_ledger": ledger,
        "consistency_checks": checks,
        "claim_boundary": [
            "This is a residual-contact pair-segment closure overlay for TREE_021 only.",
            "It closes the original 1955 TREE_021 residual pair-segment ledger by combining completed finite/formula reports; it is not a new geometric guard for each method.",
            "It does not by itself rewrite the refined-edge interval-guard report, certify TREE_007, theta=0, every continuous 3-parameter component cell, dynamic connectedness, physical hinge thickness, offsets, mesh export, or printability.",
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
                "evidence_method_counts": report["closure_ledger"]["evidence_method_counts"],
                "segment_status_counts": report["closure_ledger"]["segment_status_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())