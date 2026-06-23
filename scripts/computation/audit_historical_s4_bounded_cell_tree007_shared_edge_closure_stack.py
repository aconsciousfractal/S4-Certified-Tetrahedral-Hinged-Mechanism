"""Closure stack for TREE_007 bounded-cell shared-edge cells.

This report ports the bounded-cell shared-edge closure stack to the two
TREE_007 residual shared-edge targets left by the direct overlay:

- P0-P3
- P1-P2

For each pair, the script keeps direct common-edge certifications from the
bounded-cell overlay and replaces only directly failed pair-cells by certified
adaptive leaves. The local stack is the same one used for TREE_021 P0-P3:
common-edge box guard, expanded-support guard for stability-only obstructions,
and bounded local adaptive splitting for the remaining margin obstructions.
"""

from __future__ import annotations

from collections import Counter
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_tree007_shared_edge_closure_stack_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIRS = [("P0", "P3"), ("P1", "P2")]
MAX_ADAPTIVE_ROUNDS = 4

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p0p3_closure_stack as closure  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_shared_edge_adaptive_probe as adaptive  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def configure(pair: tuple[str, str]) -> None:
    closure.TARGET_TREE_ID = TARGET_TREE_ID
    closure.TARGET_PAIR = pair
    closure.MAX_ADAPTIVE_ROUNDS = MAX_ADAPTIVE_ROUNDS
    adaptive.TARGET_PAIR = pair


def context() -> dict:
    configure(TARGET_PAIRS[0])
    return closure.context()


def counter_from(mapping: dict) -> Counter:
    return Counter({key: int(value) for key, value in mapping.items()})


def compact_failed_records(frontier: dict) -> list[dict]:
    return [
        closure.adaptive.compact_box(box)
        for box in frontier["direct_failed_boxes"]
    ]


def audit_pair(ctx: dict, pair: tuple[str, str]) -> dict:
    configure(pair)
    source_direct_counts = closure.source_direct_pair_counts()
    frontier = closure.target_direct_frontier(ctx)
    expected_counts = counter_from(source_direct_counts["target_pair_result_counts"])
    actual_counts = counter_from(frontier["direct_result_counts"])
    if expected_counts and expected_counts != actual_counts:
        raise AssertionError(
            f"Direct {TARGET_TREE_ID} {'-'.join(pair)} counts mismatch: "
            f"expected {expected_counts}, actual {actual_counts}"
        )

    audit = closure.audit_failed_frontier(ctx, frontier["direct_failed_boxes"])
    ledger = closure.combined_ledger(frontier, audit)
    return {
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(pair),
            "role": "residual_shared_edge_closure_stack",
            "max_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
        },
        "source_direct_overlay_target_pair_counts": source_direct_counts["target_pair_result_counts"],
        "summary_metrics": {
            **ledger,
            "adaptive_closed": audit["adaptive_closed"],
            "max_round_reached": audit["levels"][-1]["round_index"],
            "adaptive_cumulative_evaluated_box_count": audit["cumulative_evaluated_box_count"],
            "replacement_terminal_leaf_count": audit["replacement_terminal_leaf_count"],
            "replacement_terminal_certified_leaf_count": audit["replacement_terminal_certified_leaf_count"],
            "replacement_terminal_failed_leaf_count": audit["replacement_terminal_failed_leaf_count"],
            "fully_covered_source_direct_box_count": audit["fully_covered_source_direct_box_count"],
            "failed_source_direct_box_count": audit["failed_source_direct_box_count"],
            "direct_failure_reason_counts": frontier["direct_failure_reason_counts"],
            "direct_failure_category_counts": frontier["direct_failure_category_counts"],
        },
        "direct_frontier": {
            "first_pass_target_pair_cell_count": frontier["first_pass_target_pair_cell_count"],
            "direct_result_counts": frontier["direct_result_counts"],
            "direct_failure_reason_counts": frontier["direct_failure_reason_counts"],
            "direct_failure_category_counts": frontier["direct_failure_category_counts"],
            "direct_certified_records": frontier["direct_certified_records"],
            "direct_failed_records": compact_failed_records(frontier),
        },
        "closure_audit": audit,
    }


def sum_counter(pair_reports: list[dict], key: str) -> dict:
    total = Counter()
    for report in pair_reports:
        total.update(report["summary_metrics"].get(key, {}))
    return dict(total.most_common())


def aggregate_summary(pair_reports: list[dict]) -> dict:
    def total(metric: str) -> int:
        return sum(int(report["summary_metrics"][metric]) for report in pair_reports)

    refined_total = total("refined_terminal_element_count_after_closure")
    refined_certified = total("refined_terminal_certified_element_count_after_closure")
    return {
        "target_pair_count": len(pair_reports),
        "direct_target_pair_cell_count": total("direct_target_pair_cell_count"),
        "direct_certified_pair_cell_count": total("direct_certified_pair_cell_count"),
        "direct_failed_pair_cell_count": total("direct_failed_pair_cell_count"),
        "direct_failed_base_pair_cell_count": total("direct_failed_base_pair_cell_count"),
        "all_pairs_adaptive_closed": all(report["summary_metrics"]["adaptive_closed"] for report in pair_reports),
        "max_round_reached": max(int(report["summary_metrics"]["max_round_reached"]) for report in pair_reports),
        "adaptive_cumulative_evaluated_box_count": total("adaptive_cumulative_evaluated_box_count"),
        "replacement_terminal_leaf_count": total("replacement_terminal_leaf_count"),
        "replacement_terminal_certified_leaf_count": total("replacement_terminal_certified_leaf_count"),
        "replacement_terminal_failed_leaf_count": total("replacement_terminal_failed_leaf_count"),
        "refined_terminal_element_count_after_closure": refined_total,
        "refined_terminal_certified_element_count_after_closure": refined_certified,
        "refined_terminal_failed_element_count_after_closure": total("refined_terminal_failed_element_count_after_closure"),
        "refined_terminal_coverage_fraction_after_closure": round(refined_certified / refined_total, 6) if refined_total else 0.0,
        "fully_covered_base_pair_cell_count_after_closure": total("fully_covered_base_pair_cell_count_after_closure"),
        "failed_base_pair_cell_count_after_closure": total("failed_base_pair_cell_count_after_closure"),
        "direct_failure_reason_counts": sum_counter(pair_reports, "direct_failure_reason_counts"),
        "direct_failure_category_counts": sum_counter(pair_reports, "direct_failure_category_counts"),
    }


def build_report() -> dict:
    ctx = context()
    pair_reports = [audit_pair(ctx, pair) for pair in TARGET_PAIRS]
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_tree007_shared_edge_closure_stack_completed",
        "source_reports": [
            f"results/{CASE_ID}/bounded_cell_shared_edge_common_edge_overlay_report.json",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
            f"results/{CASE_ID}/tree007_shared_edge_common_edge_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_tree021_p0p3_closure_stack_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pairs": [list(pair) for pair in TARGET_PAIRS],
            "role": "residual_shared_edge_closure_stack",
            "max_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
            "direct_overlay_reused": True,
            "expanded_support_guard_reused": True,
        },
        "summary_metrics": aggregate_summary(pair_reports),
        "pair_reports": pair_reports,
        "limitations": [
            "This report targets only TREE_007 residual shared-edge bounded cells for P0-P3 and P1-P2.",
            "Directly failed base pair-cells are replaced by certified adaptive leaves; refined terminal element count is therefore not the same as direct target pair-cell count.",
            "Together with the separate TREE_021 P0-P3 and P1-P2 reports, this closes the bounded-cell shared-edge front, but residual shared-face bounded cells remain outside this report.",
            "The result does not cover theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
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
                "pair_level_summaries": {
                    "-".join(pair_report["target"]["pair"]): [
                        {
                            "round_index": level["round_index"],
                            "input_box_count": level["input_box_count"],
                            "result_counts": level["result_counts"],
                            "failure_category_counts": level["failure_category_counts"],
                            "split_dimension_counts": level["split_dimension_counts"],
                            "next_box_count": level["next_box_count"],
                        }
                        for level in pair_report["closure_audit"]["levels"]
                    ]
                    for pair_report in report["pair_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
