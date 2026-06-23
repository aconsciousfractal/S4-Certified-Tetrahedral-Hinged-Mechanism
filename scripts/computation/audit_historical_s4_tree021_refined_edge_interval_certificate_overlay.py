"""TREE_021 refined-edge interval certificate overlay.

This audit promotes the TREE_021 refined-edge interval guard from a partial
probe to a complete refined-edge ledger by combining:

- the 1463 refined segments already fully certified by the original interval
  guard; and
- the 1065 failed refined segments closed by the residual-contact closure
  overlay.

It is an overlay/accounting certificate for the 2528 refined BFS spanning-tree
segments. It does not recompute every local SAT interval guard and does not claim
a continuous full 3-parameter component theorem.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree021_refined_edge_interval_certificate_overlay_report.json"
TARGET_TREE_ID = "TREE_021"
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_tree021_residual_contact_reconciliation_ledger as recon  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def segment_id(segment: dict) -> str:
    return f"seg_{segment['refined_segment_index']:05d}"


def reconstruct_segments_and_residuals() -> tuple[list[dict], list[dict], dict, dict]:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    _tree, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    residual_records, residual_source_meta = recon.residual_pair_records(case, tree, source_audit, signs_by_tree)
    nodes_by_id = bounded.all_nodes_by_id(tree, signs_by_tree[TARGET_TREE_ID])
    return segments, residual_records, residual_source_meta, nodes_by_id


def compact_source_edge(nodes_by_id: dict[str, dict], node_ids: list[str]) -> dict:
    return classify.source_edge_descriptor(nodes_by_id, node_ids)


def compact_segment(segment: dict, nodes_by_id: dict[str, dict], status: str, method: str, residual_pair_count: int) -> dict:
    return {
        "segment_id": segment_id(segment),
        "refined_segment_index": segment["refined_segment_index"],
        "source_edge_index": segment["source_edge_index"],
        "source_node_ids": segment["source_node_ids"],
        "source_edge": compact_source_edge(nodes_by_id, segment["source_node_ids"]),
        "segment_index_within_source_edge": segment["segment_index_within_source_edge"],
        "source_edge_segment_count": segment["source_edge_segment_count"],
        "source_t_interval": segment["source_t_interval"],
        "delta": segment["delta"],
        "certificate_status": status,
        "certificate_method": method,
        "residual_pair_segment_count": residual_pair_count,
    }


def build_segment_ledger(segments: list[dict], residual_records: list[dict], nodes_by_id: dict[str, dict]) -> dict:
    residual_by_segment = defaultdict(list)
    for record in residual_records:
        residual_by_segment[record["segment_id"]].append(record)

    segment_reports = []
    status_counts = Counter()
    method_counts = Counter()
    residual_pattern_counts = Counter()
    source_kind_by_method = defaultdict(Counter)
    examples = defaultdict(list)

    for segment in segments:
        sid = segment_id(segment)
        residuals = residual_by_segment.get(sid, [])
        if residuals:
            status = "certified_by_overlay"
            method = "residual_contact_closure_overlay"
            residual_pattern = " + ".join(sorted(record["pair_key"] for record in residuals))
            residual_pattern_counts[residual_pattern] += 1
        else:
            status = "certified_by_original_probe"
            method = "original_refined_edge_interval_guard"
        item = compact_segment(segment, nodes_by_id, status, method, len(residuals))
        segment_reports.append(item)
        status_counts[status] += 1
        method_counts[method] += 1
        source_kind_by_method[method][item["source_edge"]["kind"]] += 1
        add_example(examples[method], item)

    return {
        "segment_status_counts": dict(status_counts.most_common()),
        "segment_certificate_method_counts": dict(method_counts.most_common()),
        "residual_segment_pattern_counts": dict(residual_pattern_counts.most_common()),
        "source_edge_kind_counts_by_method": {
            method: dict(counter.most_common()) for method, counter in sorted(source_kind_by_method.items())
        },
        "examples": dict(examples),
        "segment_reports": segment_reports,
    }


def consistency_checks(segments: list[dict], residual_records: list[dict], residual_source_meta: dict, segment_ledger: dict) -> dict:
    refined = load_json(RESULTS_DIR / "refined_edge_interval_guard_probe_report.json")
    closure = load_json(RESULTS_DIR / "tree021_residual_contact_closure_overlay_report.json")
    tree_report = next(report for report in refined["tree_reports"] if report["tree_id"] == TARGET_TREE_ID)
    refined_metrics = tree_report["summary_metrics"]
    refined_global = refined["summary_metrics"]
    residual_segment_ids = {record["segment_id"] for record in residual_records}
    all_segment_ids = {segment_id(segment) for segment in segments}

    original_certified = segment_ledger["segment_certificate_method_counts"].get("original_refined_edge_interval_guard", 0)
    residual_closed = segment_ledger["segment_certificate_method_counts"].get("residual_contact_closure_overlay", 0)
    combined_pair_count = int(refined_metrics["covered_pair_segment_count"]) + int(closure["summary_metrics"]["covered_pair_segment_count"])

    return {
        "reconstructed_refined_segment_count": len(segments),
        "reconstructed_residual_failed_segment_count": len(residual_segment_ids),
        "residual_pair_segment_count_reconstructed": len(residual_records),
        "segment_ids_partition_without_overlap_or_gap": len(all_segment_ids) == original_certified + residual_closed,
        "residual_segment_count_matches_refined_probe_failed_count": len(residual_segment_ids) == refined_metrics["failed_interval_guard_segment_count"],
        "original_certified_count_matches_refined_probe": original_certified == refined_metrics["fully_interval_guard_certified_segment_count"],
        "residual_closed_count_matches_closure_overlay": residual_closed == closure["summary_metrics"]["fully_closed_failed_refined_segment_count"],
        "residual_pair_count_matches_refined_probe_uncovered_pair_count": len(residual_records) == refined_metrics["uncovered_pair_segment_count"],
        "residual_pair_count_matches_closure_overlay": len(residual_records) == closure["summary_metrics"]["covered_pair_segment_count"],
        "combined_pair_segment_count": combined_pair_count,
        "combined_pair_segment_count_matches_total": combined_pair_count == refined_metrics["total_pair_segment_count"],
        "all_refined_segments_certified_by_overlay": original_certified + residual_closed == len(segments),
        "all_pair_segments_certified_by_overlay": combined_pair_count == refined_metrics["total_pair_segment_count"],
        "refined_probe_tree_metrics": refined_metrics,
        "refined_probe_global_metrics": refined_global,
        "residual_closure_metrics": closure["summary_metrics"],
        "residual_source_meta": residual_source_meta,
    }


def build_report() -> dict:
    segments, residual_records, residual_source_meta, nodes_by_id = reconstruct_segments_and_residuals()
    segment_ledger = build_segment_ledger(segments, residual_records, nodes_by_id)
    checks = consistency_checks(segments, residual_records, residual_source_meta, segment_ledger)

    original_count = segment_ledger["segment_certificate_method_counts"].get("original_refined_edge_interval_guard", 0)
    residual_count = segment_ledger["segment_certificate_method_counts"].get("residual_contact_closure_overlay", 0)

    return {
        "case_id": CASE_ID,
        "status": "tree021_refined_edge_interval_certificate_overlay_completed",
        "source_reports": [
            f"results/{CASE_ID}/refined_edge_interval_guard_probe_report.json",
            f"results/{CASE_ID}/tree021_residual_contact_closure_overlay_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "summary_metrics": {
            "refined_segment_count": len(segments),
            "original_interval_guard_certified_segment_count": original_count,
            "residual_contact_closure_segment_count": residual_count,
            "certified_refined_segment_count": original_count + residual_count,
            "uncertified_refined_segment_count": len(segments) - original_count - residual_count,
            "total_pair_segment_count": checks["refined_probe_tree_metrics"]["total_pair_segment_count"],
            "original_probe_covered_pair_segment_count": checks["refined_probe_tree_metrics"]["covered_pair_segment_count"],
            "residual_closure_pair_segment_count": checks["residual_closure_metrics"]["covered_pair_segment_count"],
            "combined_certified_pair_segment_count": checks["combined_pair_segment_count"],
            "uncertified_pair_segment_count": checks["refined_probe_tree_metrics"]["total_pair_segment_count"] - checks["combined_pair_segment_count"],
            "tree021_refined_edge_interval_overlay_completed": checks["all_refined_segments_certified_by_overlay"] and checks["all_pair_segments_certified_by_overlay"],
        },
        "segment_ledger": segment_ledger,
        "consistency_checks": checks,
        "claim_boundary": [
            "This is a TREE_021 refined-edge overlay over the 2528 refined BFS spanning-tree segments.",
            "It combines the original interval-guard-certified segments with the residual-contact closure overlay; it does not recompute every guard from scratch.",
            "It does not certify TREE_007, theta=0, every continuous 3-parameter component cell, dynamic connectedness, physical hinge thickness, offsets, mesh export, or printability.",
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
                "segment_certificate_method_counts": report["segment_ledger"]["segment_certificate_method_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())