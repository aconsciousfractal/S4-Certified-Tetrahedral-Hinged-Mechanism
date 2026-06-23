"""TREE_021 residual-contact reconciliation ledger.

This audit reconciles existing finite reports against the original TREE_021
residual-contact classification ledger:

- 1955 uncovered residual pair-segments.
- 1065 P0-P2 residual shared-face pair-segments.
- 329 P0-P3 residual shared-edge pair-segments.
- 561 P1-P2 residual shared-edge pair-segments.

The ledger maps the P0-P2 edge-branch workflow and the shared-edge common-edge
guard back to the original pair-segment accounting. It is deliberately an
accounting/reporting audit: it identifies what is covered by existing finite
evidence and what remains outside that evidence.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree021_residual_contact_reconciliation_ledger_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR_P0P2 = ("P0", "P2")
SHARED_EDGE_PAIRS = [("P0", "P3"), ("P1", "P2")]
COMMON_SHARED_EDGE_AXIS = "edge:M_AB-M_CD x M_AB-M_CD"
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
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    if math.isinf(float(value)):
        return float(value)
    return round(float(value), digits)


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {key: None for key in ["min", "p05", "p10", "p25", "p50", "p75", "p90", "p95", "max"]}
    ordered = sorted(values)
    n = len(ordered)

    def q(percent: float) -> float:
        if n == 1:
            return ordered[0]
        position = percent * (n - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "min": rounded(ordered[0]),
        "p05": rounded(q(0.05)),
        "p10": rounded(q(0.10)),
        "p25": rounded(q(0.25)),
        "p50": rounded(q(0.50)),
        "p75": rounded(q(0.75)),
        "p90": rounded(q(0.90)),
        "p95": rounded(q(0.95)),
        "max": rounded(ordered[-1]),
    }


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def compact_source_edge(nodes_by_id: dict[str, dict], node_ids: list[str]) -> dict:
    return classify.source_edge_descriptor(nodes_by_id, node_ids)


def pair_key(pair: tuple[str, str]) -> str:
    return "-".join(pair)


def residual_pair_records(case: dict, tree: dict, source_audit: dict, signs_by_tree: dict[str, dict[str, int]]) -> tuple[list[dict], dict]:
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
        source_edge = compact_source_edge(nodes_by_id, segment["source_node_ids"])
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
                "record_id": f"res_{len(records):04d}",
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

    for segment_records in segment_to_records.values():
        pattern = " + ".join(sorted(record["pair_key"] for record in segment_records))
        segment_patterns[pattern] += 1

    return records, {
        "refined_segment_count": len(segments),
        "failed_refined_segment_count": len(segment_to_records),
        "original_failure_pattern_counts": dict(segment_patterns.most_common()),
    }


def evidence_for_record(record: dict) -> tuple[str, str | None]:
    pair = tuple(record["pair"])
    axis = record["best_axis_name"]
    if pair == TARGET_PAIR_P0P2:
        if axis in branch_probe.TARGET_BRANCHES:
            return "covered", "p0p2_edge_branch_workflow"
        return "outside_current_finite_evidence", "p0p2_face_normal_branch_unresolved"
    if pair in SHARED_EDGE_PAIRS and axis == COMMON_SHARED_EDGE_AXIS:
        return "covered", "tree021_shared_edge_common_edge_guard"
    return "outside_current_finite_evidence", "unexpected_residual_pair_or_axis"


def evidence_ledger(records: list[dict]) -> dict:
    by_pair = defaultdict(Counter)
    by_method = Counter()
    by_unresolved_axis = Counter()
    by_unresolved_source_kind = Counter()
    by_unresolved_theta_pair = Counter()
    by_covered_source_kind = Counter()
    by_covered_theta_pair = Counter()
    covered_records = []
    unresolved_records = []
    examples = defaultdict(list)

    for record in records:
        status, method = evidence_for_record(record)
        record_with_status = {**record, "evidence_status": status, "evidence_method": method}
        by_pair[record["pair_key"]][status] += 1
        by_method[method] += 1
        if status == "covered":
            covered_records.append(record_with_status)
            by_covered_source_kind[record["source_edge"]["kind"]] += 1
            by_covered_theta_pair[record["source_edge"]["theta_pair"]] += 1
            add_example(examples["covered"], record_with_status)
        else:
            unresolved_records.append(record_with_status)
            by_unresolved_axis[record["best_axis_name"]] += 1
            by_unresolved_source_kind[record["source_edge"]["kind"]] += 1
            by_unresolved_theta_pair[record["source_edge"]["theta_pair"]] += 1
            add_example(examples["unresolved"], record_with_status)

    segment_records = defaultdict(list)
    for record in covered_records + unresolved_records:
        segment_records[record["segment_id"]].append(record)

    segment_status_counts = Counter()
    covered_segment_patterns = Counter()
    unresolved_segment_patterns = Counter()
    for segment_id, items in segment_records.items():
        pattern = " + ".join(sorted(item["pair_key"] for item in items))
        if all(item["evidence_status"] == "covered" for item in items):
            segment_status_counts["fully_covered"] += 1
            covered_segment_patterns[pattern] += 1
        else:
            segment_status_counts["unresolved"] += 1
            unresolved_segment_patterns[pattern] += 1

    return {
        "pair_segment_status_counts": {
            "covered": len(covered_records),
            "outside_current_finite_evidence": len(unresolved_records),
        },
        "pair_segment_status_counts_by_pair": {pair: dict(counter.most_common()) for pair, counter in sorted(by_pair.items())},
        "evidence_method_counts": dict(by_method.most_common()),
        "covered_source_edge_kind_counts": dict(by_covered_source_kind.most_common()),
        "covered_source_theta_pair_counts": dict(by_covered_theta_pair.most_common()),
        "unresolved_axis_counts": dict(by_unresolved_axis.most_common()),
        "unresolved_source_edge_kind_counts": dict(by_unresolved_source_kind.most_common()),
        "unresolved_source_theta_pair_counts": dict(by_unresolved_theta_pair.most_common()),
        "segment_status_counts": dict(segment_status_counts.most_common()),
        "covered_segment_pattern_counts": dict(covered_segment_patterns.most_common()),
        "unresolved_segment_pattern_counts": dict(unresolved_segment_patterns.most_common()),
        "examples": dict(examples),
    }


def report_consistency_checks(case: dict, tree: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]], records: list[dict], ledger: dict) -> dict:
    classification = load_json(RESULTS_DIR / "residual_contact_failure_classification_report.json")
    lower = load_json(RESULTS_DIR / "p0p2_edge_branch_lower_bound_probe_report.json")
    failure = load_json(RESULTS_DIR / "p0p2_edge_branch_failure_classification_report.json")
    support = load_json(RESULTS_DIR / "p0p2_same_branch_support_bound_probe_report.json")
    targeted = load_json(RESULTS_DIR / "p0p2_targeted_endgame_guard_report.json")
    axis_switch = load_json(RESULTS_DIR / "p0p2_axis_switch_backlog_guard_report.json")
    shared_edge = load_json(RESULTS_DIR / "tree021_shared_edge_common_edge_guard_report.json")

    indices = branch_probe.label_indices(case)
    parents = branch_probe.parent_branch_segments(case, tree, indices, paths_by_piece, signs_by_tree)
    parent_ids = {f"seg_{parent['refined_segment_index']:05d}" for parent in parents}
    p0p2_edge_ids = {
        record["segment_id"]
        for record in records
        if record["pair_key"] == "P0-P2" and record["best_axis_name"] in branch_probe.TARGET_BRANCHES
    }

    threshold_0625 = next(item for item in lower["threshold_reports"] if item["max_coordinate_delta_degrees"] == 0.625)
    p0p2_branch_subsegment_total = int(threshold_0625["subsegment_count"])
    branch_workflow_base_covered_sum = (
        int(threshold_0625["branch_lower_bound_certified_subsegment_count"])
        + int(support["summary_metrics"]["stable_support_certified_count"])
        + int(support["summary_metrics"]["remaining_after_stable_support_count"])
        + int(axis_switch["summary_metrics"]["input_axis_switch_child_count"])
    )

    source_pair_counts = Counter(record["pair_key"] for record in records)
    expected_pair_counts = {
        "P0-P2": next(report["uncovered_pair_segment_count"] for report in classification["pair_reports"] if report["pair"] == ["P0", "P2"]),
        "P0-P3": next(report["uncovered_pair_segment_count"] for report in classification["pair_reports"] if report["pair"] == ["P0", "P3"]),
        "P1-P2": next(report["uncovered_pair_segment_count"] for report in classification["pair_reports"] if report["pair"] == ["P1", "P2"]),
    }

    return {
        "classification_pair_segment_count_matches": len(records) == classification["summary_metrics"]["total_residual_uncovered_pair_segment_count"],
        "classification_pair_counts_expected": expected_pair_counts,
        "classification_pair_counts_reconstructed": dict(source_pair_counts.most_common()),
        "p0p2_edge_branch_parent_ids_match_reconstructed_records": parent_ids == p0p2_edge_ids,
        "p0p2_edge_branch_parent_segment_count": len(parent_ids),
        "p0p2_edge_branch_parent_id_symmetric_difference_count": len(parent_ids ^ p0p2_edge_ids),
        "p0p2_branch_subsegment_ledger": {
            "subsegments_at_0_625_degrees": p0p2_branch_subsegment_total,
            "covered_by_initial_branch_lower_bound": threshold_0625["branch_lower_bound_certified_subsegment_count"],
            "covered_by_same_branch_support_bound": support["summary_metrics"]["stable_support_certified_count"],
            "covered_by_same_branch_refinement_theta_projection_endgame_base_count": support["summary_metrics"]["remaining_after_stable_support_count"],
            "covered_by_axis_switch_backlog_guard_base_count": axis_switch["summary_metrics"]["input_axis_switch_child_count"],
            "base_coverage_sum": branch_workflow_base_covered_sum,
            "base_coverage_sum_matches_subsegment_count": branch_workflow_base_covered_sum == p0p2_branch_subsegment_total,
            "targeted_endgame_completed": targeted["summary_metrics"]["targeted_endgame_completed"],
            "axis_switch_adaptive_completed": axis_switch["summary_metrics"]["adaptive_completed"],
        },
        "shared_edge_guard_input_matches_reconstructed_records": (
            shared_edge["summary_metrics"]["input_shared_edge_pair_segment_count"]
            == ledger["evidence_method_counts"].get("tree021_shared_edge_common_edge_guard", 0)
        ),
        "shared_edge_guard_adaptive_completed": shared_edge["summary_metrics"]["adaptive_completed"],
        "all_current_evidence_reports_completed": all(
            [
                targeted["summary_metrics"]["targeted_endgame_completed"],
                axis_switch["summary_metrics"]["adaptive_completed"],
                shared_edge["summary_metrics"]["adaptive_completed"],
                branch_workflow_base_covered_sum == p0p2_branch_subsegment_total,
                parent_ids == p0p2_edge_ids,
            ]
        ),
    }


def build_report() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)

    records, source_ledger = residual_pair_records(case, tree, source_audit, signs_by_tree)
    ledger = evidence_ledger(records)
    checks = report_consistency_checks(case, tree, paths_by_piece, signs_by_tree, records, ledger)

    covered_pair_segments = ledger["pair_segment_status_counts"]["covered"]
    unresolved_pair_segments = ledger["pair_segment_status_counts"]["outside_current_finite_evidence"]
    segment_status = ledger["segment_status_counts"]

    return {
        "case_id": CASE_ID,
        "status": "tree021_residual_contact_reconciliation_ledger_completed",
        "source_reports": [
            f"results/{CASE_ID}/residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/p0p2_edge_branch_lower_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_edge_branch_failure_classification_report.json",
            f"results/{CASE_ID}/p0p2_same_branch_support_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_refinement_sensitivity_probe_report.json",
            f"results/{CASE_ID}/p0p2_theta_projection_component_bound_probe_report.json",
            f"results/{CASE_ID}/p0p2_targeted_endgame_guard_report.json",
            f"results/{CASE_ID}/p0p2_axis_switch_backlog_guard_report.json",
            f"results/{CASE_ID}/tree021_shared_edge_common_edge_guard_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "summary_metrics": {
            "original_residual_pair_segment_count": len(records),
            "original_failed_refined_segment_count": source_ledger["failed_refined_segment_count"],
            "covered_by_current_finite_evidence_pair_segment_count": covered_pair_segments,
            "outside_current_finite_evidence_pair_segment_count": unresolved_pair_segments,
            "fully_covered_failed_refined_segment_count": segment_status.get("fully_covered", 0),
            "unresolved_failed_refined_segment_count": segment_status.get("unresolved", 0),
            "p0p2_original_pair_segment_count": checks["classification_pair_counts_reconstructed"].get("P0-P2", 0),
            "p0p2_edge_branch_parent_pair_segment_count": checks["p0p2_edge_branch_parent_segment_count"],
            "p0p2_face_normal_unresolved_pair_segment_count": ledger["pair_segment_status_counts_by_pair"].get("P0-P2", {}).get("outside_current_finite_evidence", 0),
            "shared_edge_original_pair_segment_count": checks["classification_pair_counts_reconstructed"].get("P0-P3", 0) + checks["classification_pair_counts_reconstructed"].get("P1-P2", 0),
            "shared_edge_covered_pair_segment_count": ledger["evidence_method_counts"].get("tree021_shared_edge_common_edge_guard", 0),
            "tree021_residual_contact_fully_reconciled": unresolved_pair_segments == 0,
        },
        "source_ledger": source_ledger,
        "evidence_ledger": ledger,
        "consistency_checks": checks,
        "claim_boundary": [
            "This ledger reconciles current finite evidence against the original TREE_021 residual pair-segment accounting.",
            "It identifies 435 P0-P2 face-normal residual pair-segments outside current finite evidence.",
            "It does not certify the unresolved face-normal pair-segments, TREE_007 mirror transfer, theta=0, the full continuous component, or physical hinge thickness/clearance.",
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
                "unresolved_axis_counts": report["evidence_ledger"]["unresolved_axis_counts"],
                "unresolved_segment_pattern_counts": report["evidence_ledger"]["unresolved_segment_pattern_counts"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())