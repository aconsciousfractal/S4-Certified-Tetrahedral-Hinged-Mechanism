"""TREE_007 residual-contact closure overlay.

This audit is an accounting overlay over the TREE_007 residual-contact
pair-segment ledger. It combines the three completed evidence blocks:

- P2-P3 edge-branch workflow: 629 original pair-segments.
- P2-P3 face-normal formula guard: 435 original pair-segments.
- P0-P3/P1-P2 shared-edge common-edge guard: 661 original pair-segments.

The overlay does not recompute the geometric guards. It reconstructs the
deterministic residual pair-records from the TREE_007 classification criterion
and verifies that the source reports cover the full 1725/1725 residual ledger.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_residual_contact_closure_overlay_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIR_P2P3 = ("P2", "P3")
SHARED_EDGE_PAIRS = [("P0", "P3"), ("P1", "P2")]
COMMON_SHARED_EDGE_AXIS = "edge:M_AB-M_CD x M_AB-M_CD"
EDGE_BRANCH_AXES = {"edge:B-M_AB x B-M_CD", "edge:B-M_CD x B-M_AB"}
FACE_NORMAL_AXES = {"left_face:B-M_AB-M_CD", "right_face:B-M_AB-M_CD"}
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    return round(float(value), digits)


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def pair_key(pair: tuple[str, str]) -> str:
    return "-".join(pair)


def record_key(record: dict) -> tuple[str, str, str]:
    return (record["segment_id"], record["pair_key"], record["best_axis_name"])


def face_report_keys(face_report: dict) -> set[tuple[str, str, str]]:
    keys = set()
    for item in face_report["segment_reports"]:
        if item.get("formula_certified"):
            keys.add((item["segment_id"], item["pair_key"], item["axis_name"]))
    return keys


def reconstruct_records() -> tuple[list[dict], dict]:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)

    labels_by_piece = classify.labels_by_piece(case)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    nodes_by_id = bounded.all_nodes_by_id(tree, signs_by_tree[TARGET_TREE_ID])
    _tree, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    residual_pairs = classify.residual_pairs_for_tree(case, tree)

    records = []
    segment_patterns = Counter()
    segment_to_records = defaultdict(list)
    for segment in segments:
        center = (segment["left_vector"] + segment["right_vector"]) / 2.0
        center_degrees = probe.degrees_from_vector(tree, center)
        left_degrees = probe.degrees_from_vector(tree, segment["left_vector"])
        right_degrees = probe.degrees_from_vector(tree, segment["right_vector"])
        delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
        transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        displacement_bounds = probe.piece_displacement_bounds_for_segment(
            case,
            tree,
            transforms,
            transformed,
            delta_by_hinge,
            paths_by_piece,
        )
        source_edge = classify.source_edge_descriptor(nodes_by_id, segment["source_node_ids"])
        segment_id = f"seg_{segment['refined_segment_index']:05d}"
        for pair, role in residual_pairs:
            left, right = pair
            best = classify.best_named_axis(transformed[left], transformed[right], labels_by_piece[left], labels_by_piece[right])
            guard_bound = displacement_bounds[left] + displacement_bounds[right] + SAT_TOLERANCE
            post_guard = best["center_axis_overlap"] + guard_bound
            guard_margin = SAT_TOLERANCE - post_guard
            if post_guard <= SAT_TOLERANCE:
                continue
            record = {
                "record_id": f"tree007_res_{len(records):04d}",
                "segment_id": segment_id,
                "refined_segment_index": segment["refined_segment_index"],
                "source_edge_index": segment["source_edge_index"],
                "source_node_ids": segment["source_node_ids"],
                "source_edge": source_edge,
                "source_t_interval": segment["source_t_interval"],
                "delta": segment["delta"],
                "pair": list(pair),
                "pair_key": pair_key(pair),
                "role": role,
                "best_axis_name": best["axis_name"],
                "center_axis_overlap": rounded(best["center_axis_overlap"]),
                "guard_bound": rounded(guard_bound),
                "post_guard_overlap_bound": rounded(post_guard),
                "guard_margin": rounded(guard_margin),
            }
            records.append(record)
            segment_to_records[segment_id].append(record)

    for items in segment_to_records.values():
        pattern = " + ".join(sorted(item["pair_key"] for item in items))
        segment_patterns[pattern] += 1

    return records, {
        "refined_segment_count": len(segments),
        "failed_refined_segment_count": len(segment_to_records),
        "original_failure_pattern_counts": dict(segment_patterns.most_common()),
    }


def evidence_for_record(record: dict, face_keys: set[tuple[str, str, str]]) -> tuple[str, str, str | None]:
    pair = tuple(record["pair"])
    axis = record["best_axis_name"]
    if pair == TARGET_PAIR_P2P3 and axis in EDGE_BRANCH_AXES:
        return "covered", "tree007_p2p3_edge_branch_workflow", None
    if pair == TARGET_PAIR_P2P3 and axis in FACE_NORMAL_AXES:
        if record_key(record) in face_keys:
            return "covered", "tree007_p2p3_face_normal_formula_guard", None
        return "uncovered", "tree007_p2p3_face_normal_formula_guard_missing_record", "face_record_key_not_found_or_not_certified"
    if pair in SHARED_EDGE_PAIRS and axis == COMMON_SHARED_EDGE_AXIS:
        return "covered", "tree007_shared_edge_common_edge_guard", None
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


def closure_ledger(records: list[dict], face_keys: set[tuple[str, str, str]]) -> dict:
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
    for items in segment_records.values():
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
    classification = load_json(RESULTS_DIR / "tree007_residual_contact_failure_classification_report.json")
    refined = load_json(RESULTS_DIR / "tree007_refined_edge_interval_guard_probe_report.json")
    shared_edge = load_json(RESULTS_DIR / "tree007_shared_edge_common_edge_guard_report.json")
    lower = load_json(RESULTS_DIR / "tree007_p2p3_edge_branch_lower_bound_probe_report.json")
    support = load_json(RESULTS_DIR / "tree007_p2p3_edge_branch_support_bound_probe_report.json")
    projection = load_json(RESULTS_DIR / "tree007_p2p3_edge_branch_projection_component_bound_probe_report.json")
    endgame = load_json(RESULTS_DIR / "tree007_p2p3_edge_branch_targeted_endgame_guard_report.json")
    tree_report = next(report for report in refined["tree_reports"] if report["tree_id"] == TARGET_TREE_ID)

    face_keys_reconstructed = {
        record_key(record)
        for record in records
        if record["pair_key"] == "P2-P3" and record["best_axis_name"] in FACE_NORMAL_AXES
    }
    face_keys_report = face_report_keys(face_report)
    edge_branch_count = sum(
        1
        for record in records
        if record["pair_key"] == "P2-P3" and record["best_axis_name"] in EDGE_BRANCH_AXES
    )
    shared_edge_count = sum(
        1
        for record in records
        if tuple(record["pair"]) in SHARED_EDGE_PAIRS and record["best_axis_name"] == COMMON_SHARED_EDGE_AXIS
    )
    source_pair_counts = Counter(record["pair_key"] for record in records)
    expected_pair_counts = {
        "-".join(report["pair"]): report["uncovered_pair_segment_count"]
        for report in classification["pair_reports"]
    }
    threshold_0625 = next(item for item in lower["threshold_reports"] if item["max_coordinate_delta_degrees"] == 0.625)

    return {
        "classification_total_matches_reconstruction": len(records) == classification["summary_metrics"]["total_residual_uncovered_pair_segment_count"],
        "pair_counts_match_classification": dict(source_pair_counts) == expected_pair_counts,
        "source_failed_segment_count": source_meta["failed_refined_segment_count"],
        "failed_segment_count_matches_refined_probe": source_meta["failed_refined_segment_count"] == tree_report["summary_metrics"]["failed_interval_guard_segment_count"],
        "edge_branch_record_count": edge_branch_count,
        "edge_branch_count_matches_lower_bound_input": edge_branch_count == lower["summary_metrics"]["parent_uncovered_edge_branch_segment_count"],
        "edge_branch_threshold_0625_subsegment_count": threshold_0625["subsegment_count"],
        "edge_branch_support_input_matches_threshold": support["summary_metrics"]["edge_branch_subsegment_count"] == threshold_0625["subsegment_count"],
        "edge_branch_projection_input_matches_support_residual": projection["summary_metrics"]["residual_base_count"] == support["summary_metrics"]["combined_edge_branch_uncovered_count"],
        "edge_branch_endgame_input_matches_projection_remaining": endgame["summary_metrics"]["input_remaining_child_count"] == projection["summary_metrics"]["remaining_uncovered_child_count"],
        "edge_branch_endgame_completed": endgame["summary_metrics"]["targeted_endgame_completed"],
        "edge_branch_endgame_uncovered_leaf_count": endgame["summary_metrics"]["adaptive_uncovered_leaf_subsegment_count"],
        "face_normal_record_count": len(face_keys_reconstructed),
        "face_report_input_count": face_report["summary_metrics"]["input_face_normal_pair_segment_count"],
        "face_report_certified_count": face_report["summary_metrics"]["formula_certified_pair_segment_count"],
        "face_report_uncovered_count": face_report["summary_metrics"]["formula_uncovered_pair_segment_count"],
        "face_report_keys_match_reconstructed_face_records": face_keys_report == face_keys_reconstructed,
        "face_report_key_symmetric_difference_count": len(face_keys_report ^ face_keys_reconstructed),
        "shared_edge_record_count": shared_edge_count,
        "shared_edge_matches_guard_input_count": shared_edge_count == shared_edge["summary_metrics"]["input_shared_edge_pair_segment_count"],
        "shared_edge_guard_adaptive_completed": shared_edge["summary_metrics"]["adaptive_completed"],
        "all_pair_segments_covered_by_overlay": ledger["pair_segment_status_counts"]["covered"] == len(records) and ledger["pair_segment_status_counts"]["uncovered"] == 0,
    }


def build_report() -> dict:
    records, source_meta = reconstruct_records()
    face_report = load_json(RESULTS_DIR / "tree007_p2p3_face_normal_formula_guard_report.json")
    face_keys = face_report_keys(face_report)
    ledger = closure_ledger(records, face_keys)
    checks = consistency_checks(records, ledger, source_meta, face_report)

    covered = ledger["pair_segment_status_counts"]["covered"]
    uncovered = ledger["pair_segment_status_counts"]["uncovered"]
    segment_status = ledger["segment_status_counts"]

    return {
        "case_id": CASE_ID,
        "status": "tree007_residual_contact_closure_overlay_completed",
        "source_reports": [
            f"results/{CASE_ID}/tree007_residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/tree007_shared_edge_common_edge_guard_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_lower_bound_probe_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_support_bound_probe_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_refinement_sensitivity_probe_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_projection_component_bound_probe_report.json",
            f"results/{CASE_ID}/tree007_p2p3_edge_branch_targeted_endgame_guard_report.json",
            f"results/{CASE_ID}/tree007_p2p3_face_normal_formula_guard_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "summary_metrics": {
            "original_residual_pair_segment_count": len(records),
            "covered_pair_segment_count": covered,
            "uncovered_pair_segment_count": uncovered,
            "original_failed_refined_segment_count": source_meta["failed_refined_segment_count"],
            "fully_closed_failed_refined_segment_count": segment_status.get("fully_closed", 0),
            "incomplete_failed_refined_segment_count": segment_status.get("incomplete", 0),
            "p2p3_original_pair_segment_count": ledger["pair_segment_status_counts_by_pair"].get("P2-P3", {}).get("covered", 0),
            "p2p3_edge_branch_pair_segment_count": ledger["evidence_method_counts"].get("tree007_p2p3_edge_branch_workflow", 0),
            "p2p3_face_normal_pair_segment_count": ledger["evidence_method_counts"].get("tree007_p2p3_face_normal_formula_guard", 0),
            "shared_edge_pair_segment_count": ledger["evidence_method_counts"].get("tree007_shared_edge_common_edge_guard", 0),
            "tree007_residual_contacts_closed_by_overlay": covered == len(records) and uncovered == 0,
        },
        "source_ledger": source_meta,
        "closure_ledger": ledger,
        "consistency_checks": checks,
        "claim_boundary": [
            "This is a residual-contact pair-segment closure overlay for TREE_007 only.",
            "It closes the original 1725 TREE_007 residual pair-segment ledger by combining completed finite/formula reports; it is not a new geometric guard for each method.",
            "It does not certify theta=0, every continuous 3-parameter component cell, dynamic connectedness, physical hinge thickness, offsets, mesh export, or printability.",
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
