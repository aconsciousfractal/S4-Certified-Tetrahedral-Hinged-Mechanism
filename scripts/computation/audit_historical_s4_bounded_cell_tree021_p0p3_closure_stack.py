"""Closure stack for TREE_021 P0-P3 bounded-cell shared-edge cells.

The direct bounded-cell shared-edge overlay already certifies part of the
TREE_021 P0-P3 front. This script reconstructs that direct ledger, then
targets only the remaining P0-P3 failed pair-cells with the same finite local
guards used for the TREE_021 P1-P2 endgame:

1. common-edge projection-component box guard;
2. expanded-support guard for stability-only boxes;
3. bounded adaptive splitting for remaining margin obstructions.

This is finite adaptive evidence for one bounded-cell shared-edge target. It
does not close TREE_007, shared-face cells, theta=0, or physical printability.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_tree021_p0p3_closure_stack_report.json"
TARGET_TREE_ID = "TREE_021"
TARGET_PAIR = ("P0", "P3")
MAX_ADAPTIVE_ROUNDS = 4
MAX_STORED_EXAMPLES = 64

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_shared_edge_adaptive_probe as adaptive  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_endgame_failure_classifier as classifier  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_support_stability_endgame_guard as support_guard  # noqa: E402
import audit_historical_s4_bounded_cell_shared_edge_common_edge_overlay as direct_overlay  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_tree021_shared_edge_common_edge_guard as shared_edge  # noqa: E402

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


def patch_target_pair() -> None:
    adaptive.TARGET_PAIR = TARGET_PAIR


def context() -> dict:
    patch_target_pair()
    case = direct_overlay.batch.build_case()
    component_report = load_json(RESULTS_DIR / direct_overlay.SOURCE_COMPONENT_REPORT)
    source_audit = next(
        audit
        for audit in component_report["representative_audits"]
        if audit["tree_id"] == TARGET_TREE_ID
    )
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs = comp.certified_signs_by_tree()[TARGET_TREE_ID]
    return {
        "case": case,
        "source_audit": source_audit,
        "tree": tree,
        "signs": signs,
        "indices": shared_edge.label_indices(case),
        "labels_by_piece": classify.labels_by_piece(case),
        "paths_by_piece": ray_guard.tree_paths_from_root(case, tree),
        "contacts_by_pair": ray_guard.contact_by_pair(case),
        "hinge_by_pair": first_pass.selected_hinge_by_pair(case, tree),
        "all_cells": direct_overlay.all_free_cells_for_tree(
            source_audit,
            direct_overlay.protocol.iter_cells(),
        ),
    }


def source_direct_pair_counts() -> dict:
    direct_report = load_json(RESULTS_DIR / direct_overlay.REPORT_NAME)
    tree_report = next(
        report
        for report in direct_report["tree_reports"]
        if report["tree_id"] == TARGET_TREE_ID
    )
    pair_key = "-".join(TARGET_PAIR)
    return {
        "tree_summary_metrics": tree_report["summary_metrics"],
        "target_pair_result_counts": tree_report["result_counts_by_pair"].get(pair_key, {}),
    }


def target_direct_frontier(ctx: dict) -> dict:
    direct_certified_records = []
    direct_failed_boxes = []
    direct_result_counts = Counter()
    direct_failure_reason_counts = Counter()
    direct_category_counts = Counter()
    first_pass_target_count = 0

    for cell in ctx["all_cells"]:
        first_pass_cell = first_pass.audit_cell(
            ctx["case"],
            ctx["tree"],
            ctx["signs"],
            cell,
            ctx["paths_by_piece"],
            ctx["contacts_by_pair"],
            ctx["hinge_by_pair"],
        )
        first_pass_by_pair = {
            tuple(record["pair"]): record
            for record in first_pass_cell["pair_records"]
        }
        first_pass_record = first_pass_by_pair[TARGET_PAIR]
        if first_pass_record["role"] != "residual_shared_edge":
            continue
        if first_pass_record["first_pass_covered"]:
            continue

        first_pass_target_count += 1
        overlay = direct_overlay.common_edge_cell_guard(
            ctx["case"],
            ctx["tree"],
            ctx["signs"],
            ctx["indices"],
            ctx["labels_by_piece"],
            ctx["paths_by_piece"],
            cell,
            TARGET_PAIR,
        )
        key = "certified" if overlay["certified"] else f"failed:{overlay['failure_reason']}"
        direct_result_counts[key] += 1
        if overlay["certified"]:
            direct_certified_records.append(
                direct_overlay.compact_pair_cell(cell, TARGET_PAIR, first_pass_record, overlay)
            )
            continue

        direct_failure_reason_counts[str(overlay["failure_reason"])] += 1
        category = classifier.failure_category(overlay)
        direct_category_counts[category] += 1
        box = adaptive.original_box(cell)
        box.update(
            {
                "source_direct_box_id": cell["cell_id"],
                "source_direct_failure_reason": overlay["failure_reason"],
                "source_direct_failure_category": category,
                "source_first_pass_guard_margin": rounded(first_pass_record["guard_margin"]),
            }
        )
        direct_failed_boxes.append(box)

    return {
        "first_pass_target_pair_cell_count": first_pass_target_count,
        "direct_certified_records": direct_certified_records,
        "direct_failed_boxes": direct_failed_boxes,
        "direct_result_counts": dict(direct_result_counts.most_common()),
        "direct_failure_reason_counts": dict(direct_failure_reason_counts.most_common()),
        "direct_failure_category_counts": dict(direct_category_counts.most_common()),
    }


def width_record(ctx: dict, box: dict) -> dict[str, float]:
    widths = classifier.box_widths(box)
    widths["max_hinge_coordinate_deviation_degrees"] = adaptive.box_max_hinge_deviation(
        ctx["tree"],
        ctx["signs"],
        box,
    )
    return {key: rounded(value) for key, value in widths.items()}


def support_signature_for_guard(guard: dict) -> str:
    if guard.get("lower_expanded_support") is not None:
        return support_guard.expanded_support_signature(guard)
    return classifier.support_signature(guard)


def compact_leaf(ctx: dict, box: dict, guard: dict, round_index: int, method: str) -> dict:
    record = adaptive.compact_box(box, guard)
    record.update(
        {
            "round_index": round_index,
            "method": method,
            "source_direct_box_id": box.get("source_direct_box_id", box["base_cell_id"]),
            "source_direct_failure_reason": box.get("source_direct_failure_reason"),
            "source_direct_failure_category": box.get("source_direct_failure_category"),
            "recommended_split_dimension": box.get("recommended_split_dimension"),
            "support_signature": support_signature_for_guard(guard),
            "widths": width_record(ctx, box),
        }
    )
    if guard.get("lower_expanded_support") is not None:
        record.update(
            {
                "lower_expanded_support_labels": guard.get("lower_expanded_support", {}).get("expanded_support_labels"),
                "upper_expanded_support_labels": guard.get("upper_expanded_support", {}).get("expanded_support_labels"),
                "lower_promoted_label_count": guard.get("lower_expanded_support", {}).get("promoted_label_count"),
                "upper_promoted_label_count": guard.get("upper_expanded_support", {}).get("promoted_label_count"),
            }
        )
    return record


def split_failed_box(ctx: dict, box: dict) -> tuple[str, list[dict]]:
    dimension = adaptive.best_split_dimension(ctx["tree"], ctx["signs"], box)
    children = []
    for child in adaptive.split_box(box, dimension):
        child["source_direct_box_id"] = box.get("source_direct_box_id", box["base_cell_id"])
        child["source_direct_failure_reason"] = box.get("source_direct_failure_reason")
        child["source_direct_failure_category"] = box.get("source_direct_failure_category")
        children.append(child)
    return dimension, children


def evaluate_box(ctx: dict, box: dict) -> tuple[str, dict, str, str | None]:
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
        return "certified_common", guard, "common_edge_box_guard", None

    category = classifier.failure_category(guard)
    if category == "stability_only_signed_margin_nonnegative":
        expanded = support_guard.expanded_support_guard(ctx, box, guard)
        if expanded["certified"]:
            return "certified_expanded_support", expanded, "expanded_support_guard", category
        return f"failed_expanded:{expanded['failure_reason']}", expanded, "expanded_support_guard", category
    return f"failed:{category}", guard, "common_edge_box_guard", category


def audit_failed_frontier(ctx: dict, direct_failed_boxes: list[dict]) -> dict:
    current = list(direct_failed_boxes)
    levels = []
    examples = defaultdict(list)
    terminal_records = []
    terminal_by_source = defaultdict(Counter)
    terminal_by_base = defaultdict(Counter)
    cumulative_input_count = 0

    for round_index in range(MAX_ADAPTIVE_ROUNDS + 1):
        result_counts = Counter()
        category_counts = Counter()
        split_counts = Counter()
        source_outcomes = defaultdict(Counter)
        base_outcomes = defaultdict(Counter)
        signed_margins = []
        certified_margins = []
        failed_margins = []
        stability_margins = []
        widths_by_key = defaultdict(list)
        next_boxes = []

        for box in current:
            cumulative_input_count += 1
            key, guard, method, category = evaluate_box(ctx, box)
            result_counts[key] += 1
            source_id = box.get("source_direct_box_id", box["base_cell_id"])
            source_outcomes[source_id][key] += 1
            base_outcomes[box["base_cell_id"]][key] += 1

            if category is not None:
                category_counts[category] += 1

            if guard.get("signed_component_margin") is not None:
                margin = float(guard["signed_component_margin"])
                signed_margins.append(margin)
                if key.startswith("certified"):
                    certified_margins.append(margin)
                else:
                    failed_margins.append(margin)
            if guard.get("minimum_stability_margin") is not None:
                stability_margins.append(float(guard["minimum_stability_margin"]))
            for width_key, value in width_record(ctx, box).items():
                widths_by_key[width_key].append(float(value))

            if key.startswith("certified"):
                record = compact_leaf(ctx, box, guard, round_index, method)
                terminal_records.append(record)
                terminal_by_source[source_id]["certified"] += 1
                terminal_by_base[box["base_cell_id"]]["certified"] += 1
                add_example(examples["certified"], record)
                continue

            if round_index >= MAX_ADAPTIVE_ROUNDS:
                record = compact_leaf(ctx, box, guard, round_index, method)
                terminal_records.append(record)
                terminal_by_source[source_id]["failed"] += 1
                terminal_by_base[box["base_cell_id"]]["failed"] += 1
                add_example(examples["failed"], record)
                continue

            dimension, children = split_failed_box(ctx, box)
            split_counts[dimension] += 1
            next_boxes.extend(children)

        levels.append(
            {
                "round_index": round_index,
                "input_box_count": len(current),
                "result_counts": dict(result_counts.most_common()),
                "failure_category_counts": dict(category_counts.most_common()),
                "split_dimension_counts": dict(split_counts.most_common()),
                "next_box_count": len(next_boxes),
                "touched_source_direct_box_count": len(source_outcomes),
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
        )
        if not next_boxes:
            current = []
            break
        current = next_boxes

    source_count = len({box.get("source_direct_box_id", box["base_cell_id"]) for box in direct_failed_boxes})
    base_count = len({box["base_cell_id"] for box in direct_failed_boxes})
    fully_covered_sources = sum(1 for counter in terminal_by_source.values() if counter.get("failed", 0) == 0)
    fully_covered_bases = sum(1 for counter in terminal_by_base.values() if counter.get("failed", 0) == 0)
    certified_terminal_count = sum(1 for record in terminal_records if record["certified"])
    failed_terminal_count = len(terminal_records) - certified_terminal_count
    return {
        "max_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
        "adaptive_closed": failed_terminal_count == 0 and not current,
        "input_direct_failed_box_count": len(direct_failed_boxes),
        "input_direct_failed_source_box_count": source_count,
        "input_direct_failed_base_pair_cell_count": base_count,
        "cumulative_evaluated_box_count": cumulative_input_count,
        "replacement_terminal_leaf_count": len(terminal_records),
        "replacement_terminal_certified_leaf_count": certified_terminal_count,
        "replacement_terminal_failed_leaf_count": failed_terminal_count,
        "fully_covered_source_direct_box_count": fully_covered_sources,
        "failed_source_direct_box_count": source_count - fully_covered_sources,
        "fully_covered_direct_failed_base_pair_cell_count": fully_covered_bases,
        "failed_direct_failed_base_pair_cell_count": base_count - fully_covered_bases,
        "levels": levels,
        "terminal_records": terminal_records,
        "examples": dict(examples),
    }


def combined_ledger(direct_frontier: dict, closure_audit: dict) -> dict:
    direct_certified = len(direct_frontier["direct_certified_records"])
    direct_failed = len(direct_frontier["direct_failed_boxes"])
    replacement_total = int(closure_audit["replacement_terminal_leaf_count"])
    replacement_certified = int(closure_audit["replacement_terminal_certified_leaf_count"])
    replacement_failed = int(closure_audit["replacement_terminal_failed_leaf_count"])
    refined_total = direct_certified + replacement_total
    refined_certified = direct_certified + replacement_certified
    return {
        "direct_target_pair_cell_count": int(direct_frontier["first_pass_target_pair_cell_count"]),
        "direct_certified_pair_cell_count": direct_certified,
        "direct_failed_pair_cell_count": direct_failed,
        "direct_failed_base_pair_cell_count": len({box["base_cell_id"] for box in direct_frontier["direct_failed_boxes"]}),
        "refined_terminal_element_count_after_closure": refined_total,
        "refined_terminal_certified_element_count_after_closure": refined_certified,
        "refined_terminal_failed_element_count_after_closure": replacement_failed,
        "refined_terminal_coverage_fraction_after_closure": round(refined_certified / refined_total, 6) if refined_total else 0.0,
        "fully_covered_base_pair_cell_count_after_closure": direct_certified
        + int(closure_audit["fully_covered_direct_failed_base_pair_cell_count"]),
        "failed_base_pair_cell_count_after_closure": int(closure_audit["failed_direct_failed_base_pair_cell_count"]),
    }


def build_report() -> dict:
    ctx = context()
    direct_counts = source_direct_pair_counts()
    direct_frontier = target_direct_frontier(ctx)
    expected_counts = Counter(direct_counts["target_pair_result_counts"])
    actual_counts = Counter(direct_frontier["direct_result_counts"])
    if expected_counts and expected_counts != actual_counts:
        raise AssertionError(f"Direct P0-P3 counts mismatch: expected {expected_counts}, actual {actual_counts}")

    closure_audit = audit_failed_frontier(ctx, direct_frontier["direct_failed_boxes"])
    ledger = combined_ledger(direct_frontier, closure_audit)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_tree021_p0p3_closure_stack_completed",
        "source_reports": [
            f"results/{CASE_ID}/{direct_overlay.REPORT_NAME}",
            f"results/{CASE_ID}/{direct_overlay.SOURCE_FIRST_PASS_REPORT}",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
            f"results/{CASE_ID}/tree021_shared_edge_common_edge_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_tree021_p1p2_support_stability_endgame_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_tree021_p1p2_margin_endgame_guard_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_edge_closure_stack",
            "max_adaptive_rounds": MAX_ADAPTIVE_ROUNDS,
            "direct_overlay_reused": True,
            "expanded_support_guard_reused": True,
        },
        "source_direct_overlay_tree_summary": direct_counts["tree_summary_metrics"],
        "source_direct_overlay_target_pair_counts": direct_counts["target_pair_result_counts"],
        "summary_metrics": {
            **ledger,
            "adaptive_closed": closure_audit["adaptive_closed"],
            "max_round_reached": closure_audit["levels"][-1]["round_index"],
            "adaptive_cumulative_evaluated_box_count": closure_audit["cumulative_evaluated_box_count"],
            "replacement_terminal_leaf_count": closure_audit["replacement_terminal_leaf_count"],
            "replacement_terminal_certified_leaf_count": closure_audit["replacement_terminal_certified_leaf_count"],
            "replacement_terminal_failed_leaf_count": closure_audit["replacement_terminal_failed_leaf_count"],
            "fully_covered_source_direct_box_count": closure_audit["fully_covered_source_direct_box_count"],
            "failed_source_direct_box_count": closure_audit["failed_source_direct_box_count"],
            "direct_failure_reason_counts": direct_frontier["direct_failure_reason_counts"],
            "direct_failure_category_counts": direct_frontier["direct_failure_category_counts"],
        },
        "direct_frontier": {
            "first_pass_target_pair_cell_count": direct_frontier["first_pass_target_pair_cell_count"],
            "direct_result_counts": direct_frontier["direct_result_counts"],
            "direct_failure_reason_counts": direct_frontier["direct_failure_reason_counts"],
            "direct_failure_category_counts": direct_frontier["direct_failure_category_counts"],
            "direct_certified_records": direct_frontier["direct_certified_records"],
            "direct_failed_records": [
                adaptive.compact_box(box)
                for box in direct_frontier["direct_failed_boxes"]
            ],
        },
        "closure_audit": closure_audit,
        "limitations": [
            "This report targets only TREE_021 P0-P3 residual shared-edge bounded cells.",
            "Directly failed base pair-cells are replaced by certified adaptive leaves; refined terminal element count is therefore not the same as the direct target pair-cell count.",
            "The result does not cover TREE_007, TREE_021 P1-P2 beyond its separate report, residual shared-face pair-cells, theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
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
                "level_summaries": [
                    {
                        "round_index": level["round_index"],
                        "input_box_count": level["input_box_count"],
                        "result_counts": level["result_counts"],
                        "failure_category_counts": level["failure_category_counts"],
                        "split_dimension_counts": level["split_dimension_counts"],
                        "next_box_count": level["next_box_count"],
                    }
                    for level in report["closure_audit"]["levels"]
                ],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
