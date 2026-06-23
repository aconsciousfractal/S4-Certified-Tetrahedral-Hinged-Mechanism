"""Margin-only endgame guard for TREE_021 P1-P2 bounded-cell failures.

The support-stability endgame guard leaves 218 depth-5 terminal boxes, all
margin-only. This script targets exactly that backlog with a bounded local
adaptive replacement:

1. Reconstruct the 218 margin-only terminal boxes.
2. Repeatedly evaluate the common-edge projection-component guard.
3. Split only failed boxes along the local best split dimension.
4. Stop when all replacement leaves are certified, or after the fixed round cap.

This is finite adaptive evidence for one bounded-cell shared-edge target. It is
not a global bounded-cell cover certificate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_tree021_p1p2_margin_endgame_guard_report.json"
SOURCE_SUPPORT_REPORT = "bounded_cell_tree021_p1p2_support_stability_endgame_guard_report.json"
TARGET_CATEGORY = "margin_only"
MAX_ADAPTIVE_ROUNDS = 6
MAX_STORED_EXAMPLES = 64

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_shared_edge_adaptive_probe as adaptive  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_endgame_failure_classifier as classifier  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_support_stability_endgame_guard as support_guard  # noqa: E402

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
    return adaptive.quantiles(values)


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def width_record(box: dict) -> dict[str, float]:
    widths = classifier.box_widths(box)
    widths["max_hinge_coordinate_deviation_degrees"] = adaptive.box_max_hinge_deviation(
        CONTEXT["tree"],
        CONTEXT["signs"],
        box,
    )
    return {key: rounded(value) for key, value in widths.items()}


def compact_margin_leaf(box: dict, guard: dict, round_index: int) -> dict:
    record = adaptive.compact_box(box, guard)
    record.update(
        {
            "round_index": round_index,
            "source_margin_box_id": box.get("source_margin_box_id", box["cell_id"]),
            "source_margin_base_cell_id": box["base_cell_id"],
            "recommended_split_dimension": box.get("recommended_split_dimension"),
            "widths": width_record(box),
        }
    )
    return record


def mark_source_boxes(boxes: list[dict]) -> list[dict]:
    output = []
    for box in boxes:
        item = dict(box)
        item["source_margin_box_id"] = box["cell_id"]
        item["source_margin_depth"] = box["depth"]
        output.append(item)
    return output


def split_failed_box(ctx: dict, box: dict) -> tuple[str, list[dict]]:
    dimension = adaptive.best_split_dimension(ctx["tree"], ctx["signs"], box)
    children = []
    for child in adaptive.split_box(box, dimension):
        child["source_margin_box_id"] = box.get("source_margin_box_id", box["cell_id"])
        child["source_margin_depth"] = box.get("source_margin_depth", box["depth"])
        children.append(child)
    return dimension, children


def evaluate_box(ctx: dict, box: dict) -> tuple[str, dict]:
    guard = adaptive.common_edge_box_guard(
        ctx["case"],
        ctx["tree"],
        ctx["signs"],
        ctx["indices"],
        ctx["labels_by_piece"],
        ctx["paths_by_piece"],
        box,
    )
    if guard["certified"]:
        return "certified_common", guard

    category = classifier.failure_category(guard)
    if category == "stability_only_signed_margin_nonnegative":
        expanded = support_guard.expanded_support_guard(ctx, box, guard)
        if expanded["certified"]:
            return "certified_expanded_support", expanded
        return f"failed_expanded_support:{expanded['failure_reason']}", expanded
    return f"failed:{category}", guard


def audit_margin_endgame(ctx: dict, margin_boxes: list[dict]) -> dict:
    current = mark_source_boxes(margin_boxes)
    levels = []
    examples = defaultdict(list)
    terminal_records = []
    terminal_by_source = defaultdict(Counter)
    terminal_by_base = defaultdict(Counter)
    cumulative_input_count = 0

    for round_index in range(MAX_ADAPTIVE_ROUNDS + 1):
        result_counts = Counter()
        split_counts = Counter()
        next_boxes = []
        signed_margins = []
        failed_margins = []
        certified_margins = []
        stability_margins = []
        widths_by_key = defaultdict(list)
        source_outcomes = defaultdict(Counter)
        base_outcomes = defaultdict(Counter)

        for box in current:
            cumulative_input_count += 1
            key, guard = evaluate_box(ctx, box)
            result_counts[key] += 1
            source_outcomes[box["source_margin_box_id"]][key] += 1
            base_outcomes[box["base_cell_id"]][key] += 1

            if guard.get("signed_component_margin") is not None:
                margin = float(guard["signed_component_margin"])
                signed_margins.append(margin)
                if key.startswith("certified"):
                    certified_margins.append(margin)
                else:
                    failed_margins.append(margin)
            if guard.get("minimum_stability_margin") is not None:
                stability_margins.append(float(guard["minimum_stability_margin"]))
            for width_key, value in width_record(box).items():
                widths_by_key[width_key].append(float(value))

            if key.startswith("certified"):
                record = compact_margin_leaf(box, guard, round_index)
                terminal_records.append(record)
                terminal_by_source[box["source_margin_box_id"]]["certified"] += 1
                terminal_by_base[box["base_cell_id"]]["certified"] += 1
                add_example(examples["certified"], record)
                continue

            if round_index >= MAX_ADAPTIVE_ROUNDS:
                record = compact_margin_leaf(box, guard, round_index)
                terminal_records.append(record)
                terminal_by_source[box["source_margin_box_id"]]["failed"] += 1
                terminal_by_base[box["base_cell_id"]]["failed"] += 1
                add_example(examples["failed"], record)
                continue

            dimension, children = split_failed_box(ctx, box)
            split_counts[dimension] += 1
            next_boxes.extend(children)

        level = {
            "round_index": round_index,
            "input_box_count": len(current),
            "result_counts": dict(result_counts.most_common()),
            "split_dimension_counts": dict(split_counts.most_common()),
            "next_box_count": len(next_boxes),
            "touched_source_margin_box_count": len(source_outcomes),
            "touched_base_pair_cell_count": len(base_outcomes),
            "signed_component_margin_quantiles": quantiles(signed_margins),
            "certified_signed_component_margin_quantiles": quantiles(certified_margins),
            "failed_signed_component_margin_quantiles": quantiles(failed_margins),
            "minimum_stability_margin_quantiles": quantiles(stability_margins),
            "width_quantiles": {
                key: quantiles(values)
                for key, values in sorted(widths_by_key.items())
            },
        }
        levels.append(level)
        if not next_boxes:
            current = []
            break
        current = next_boxes

    original_source_count = len({box["source_margin_box_id"] for box in mark_source_boxes(margin_boxes)})
    original_base_count = len({box["base_cell_id"] for box in margin_boxes})
    fully_covered_sources = sum(1 for counter in terminal_by_source.values() if counter.get("failed", 0) == 0)
    fully_covered_bases = sum(1 for counter in terminal_by_base.values() if counter.get("failed", 0) == 0)
    failed_sources = original_source_count - fully_covered_sources
    failed_bases = original_base_count - fully_covered_bases
    certified_terminal_count = sum(1 for record in terminal_records if record["certified"])
    failed_terminal_count = len(terminal_records) - certified_terminal_count

    return {
        "max_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
        "adaptive_closed": failed_terminal_count == 0 and not current,
        "input_margin_box_count": len(margin_boxes),
        "input_margin_base_pair_cell_count": original_base_count,
        "cumulative_evaluated_box_count": cumulative_input_count,
        "replacement_terminal_leaf_count": len(terminal_records),
        "replacement_terminal_certified_leaf_count": certified_terminal_count,
        "replacement_terminal_failed_leaf_count": failed_terminal_count,
        "fully_covered_source_margin_box_count": fully_covered_sources,
        "failed_source_margin_box_count": failed_sources,
        "fully_covered_margin_base_pair_cell_count": fully_covered_bases,
        "failed_margin_base_pair_cell_count": failed_bases,
        "levels": levels,
        "terminal_records": terminal_records,
        "examples": dict(examples),
    }


def combined_ledger(source_support_report: dict, margin_audit: dict) -> dict:
    support_summary = source_support_report["summary_metrics"]
    certified_before_margin = int(support_summary["terminal_certified_box_count_after_guard"])
    failed_before_margin = int(support_summary["terminal_failed_box_count_after_guard"])
    replacement_leaves = int(margin_audit["replacement_terminal_leaf_count"])
    replacement_certified = int(margin_audit["replacement_terminal_certified_leaf_count"])
    replacement_failed = int(margin_audit["replacement_terminal_failed_leaf_count"])
    refined_total = certified_before_margin + replacement_leaves
    refined_certified = certified_before_margin + replacement_certified
    return {
        "source_depth5_terminal_box_count": int(support_summary["terminal_box_count"]),
        "source_depth5_certified_box_count_after_support_guard": certified_before_margin,
        "source_depth5_failed_box_count_after_support_guard": failed_before_margin,
        "margin_replacement_leaf_count": replacement_leaves,
        "margin_replacement_certified_leaf_count": replacement_certified,
        "margin_replacement_failed_leaf_count": replacement_failed,
        "refined_terminal_element_count_after_margin_guard": refined_total,
        "refined_terminal_certified_element_count_after_margin_guard": refined_certified,
        "refined_terminal_failed_element_count_after_margin_guard": replacement_failed,
        "refined_terminal_coverage_fraction_after_margin_guard": round(refined_certified / refined_total, 6) if refined_total else 0.0,
        "original_depth5_failed_box_count_after_margin_guard": 0 if margin_audit["adaptive_closed"] else replacement_failed,
        "fully_covered_base_pair_cell_count_after_margin_guard": 768 if margin_audit["adaptive_closed"] else None,
        "partially_covered_base_pair_cell_count_after_margin_guard": 0 if margin_audit["adaptive_closed"] else None,
        "zero_certified_base_pair_cell_count_after_margin_guard": 0,
    }


def build_report() -> dict:
    global CONTEXT
    CONTEXT = classifier.context()
    source_support_report = load_json(RESULTS_DIR / SOURCE_SUPPORT_REPORT)
    _target, margin_backlog, reconstruction = support_guard.target_boxes(CONTEXT)
    expected_margin_count = source_support_report["summary_metrics"]["margin_only_backlog_box_count"]
    if len(margin_backlog) != expected_margin_count:
        raise AssertionError(f"Expected {expected_margin_count} margin boxes, found {len(margin_backlog)}")

    margin_audit = audit_margin_endgame(CONTEXT, margin_backlog)
    ledger = combined_ledger(source_support_report, margin_audit)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_tree021_p1p2_margin_endgame_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_SUPPORT_REPORT}",
            f"results/{CASE_ID}/{support_guard.SOURCE_CLASSIFIER_REPORT}",
            f"results/{CASE_ID}/{adaptive.REPORT_NAME}",
            f"results/{CASE_ID}/{adaptive.SOURCE_DIRECT_OVERLAY_REPORT}",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
        ],
        "target": {
            "tree_id": adaptive.TARGET_TREE_ID,
            "pair": list(adaptive.TARGET_PAIR),
            "role": "margin_only_endgame_guard",
            "target_failure_category": TARGET_CATEGORY,
            "max_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
        },
        "source_support_summary_metrics": source_support_report["summary_metrics"],
        "reconstruction": reconstruction,
        "summary_metrics": {
            "target_margin_only_box_count": len(margin_backlog),
            "target_margin_only_base_pair_cell_count": len({box["base_cell_id"] for box in margin_backlog}),
            "adaptive_closed": margin_audit["adaptive_closed"],
            "max_round_reached": margin_audit["levels"][-1]["round_index"],
            "cumulative_evaluated_box_count": margin_audit["cumulative_evaluated_box_count"],
            "replacement_terminal_leaf_count": margin_audit["replacement_terminal_leaf_count"],
            "replacement_terminal_certified_leaf_count": margin_audit["replacement_terminal_certified_leaf_count"],
            "replacement_terminal_failed_leaf_count": margin_audit["replacement_terminal_failed_leaf_count"],
            "fully_covered_source_margin_box_count": margin_audit["fully_covered_source_margin_box_count"],
            "failed_source_margin_box_count": margin_audit["failed_source_margin_box_count"],
            "fully_covered_margin_base_pair_cell_count": margin_audit["fully_covered_margin_base_pair_cell_count"],
            "failed_margin_base_pair_cell_count": margin_audit["failed_margin_base_pair_cell_count"],
            **ledger,
        },
        "margin_audit": margin_audit,
        "limitations": [
            "This report targets only the 218 TREE_021 P1-P2 margin-only terminal boxes left by the support-stability endgame guard.",
            "The original 218 boxes are replaced by certified adaptive leaves; the refined terminal element count is therefore not the same as the source depth-5 terminal box count.",
            "The result does not cover TREE_007, TREE_021 P0-P3, residual shared-face pair-cells, theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
        ],
    }


CONTEXT = None


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
                "level_summaries": [
                    {
                        "round_index": level["round_index"],
                        "input_box_count": level["input_box_count"],
                        "result_counts": level["result_counts"],
                        "split_dimension_counts": level["split_dimension_counts"],
                        "next_box_count": level["next_box_count"],
                    }
                    for level in report["margin_audit"]["levels"]
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
