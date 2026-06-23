"""Classify depth-5 TREE_021 P1-P2 bounded-cell adaptive failures.

The preceding adaptive probe left 993 terminal boxes uncovered at depth 5.
This script reconstructs that exact terminal frontier, recomputes the
common-edge guard on the failed boxes, and separates margin failures from
support-stability failures. It is diagnostic only: it does not certify any new
box and does not extend the max-depth ledger.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_tree021_p1p2_endgame_failure_classifier_report.json"
SOURCE_ADAPTIVE_REPORT = "bounded_cell_tree021_p1p2_shared_edge_adaptive_probe_report.json"
MAX_STORED_EXAMPLES = 48

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_tree021_shared_edge_common_edge_guard as shared_edge  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_shared_edge_adaptive_probe as adaptive  # noqa: E402

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


def context() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / adaptive.SOURCE_COMPONENT_REPORT)
    source_audit = next(
        audit
        for audit in component_report["representative_audits"]
        if audit["tree_id"] == adaptive.TARGET_TREE_ID
    )
    tree = comp.find_tree(case, adaptive.TARGET_TREE_ID)
    signs = comp.certified_signs_by_tree()[adaptive.TARGET_TREE_ID]
    return {
        "case": case,
        "tree": tree,
        "signs": signs,
        "indices": shared_edge.label_indices(case),
        "labels_by_piece": classify.labels_by_piece(case),
        "paths_by_piece": ray_guard.tree_paths_from_root(case, tree),
        "boxes": adaptive.all_tree021_boxes(source_audit, adaptive.protocol.iter_cells()),
    }


def reconstruct_failed_terminal_boxes(ctx: dict) -> tuple[list[dict], list[dict]]:
    current = ctx["boxes"]
    level_trace = []
    for depth in range(adaptive.MAX_DEPTH + 1):
        level_report, remaining, certified_boxes = adaptive.audit_level(
            ctx["case"],
            ctx["tree"],
            ctx["signs"],
            ctx["indices"],
            ctx["labels_by_piece"],
            ctx["paths_by_piece"],
            current,
        )
        level_trace.append(
            {
                "depth": depth,
                "input_box_count": level_report["input_box_count"],
                "certified_box_count": level_report["certified_box_count"],
                "failed_box_count": level_report["failed_box_count"],
                "result_counts": level_report["result_counts"],
                "recommended_split_dimension_counts": level_report["recommended_split_dimension_counts"],
                "certified_terminal_box_count_at_this_depth": len(certified_boxes),
            }
        )
        if depth == adaptive.MAX_DEPTH:
            return remaining, level_trace
        current = adaptive.expand_remaining(ctx["tree"], ctx["signs"], remaining)
    raise RuntimeError("Unreachable depth reconstruction state.")


def box_widths(box: dict) -> dict[str, float]:
    theta_left, theta_right = [float(value) for value in box["theta_interval_degrees"]]
    radius_left, radius_right = [float(value) for value in box["radial_interval_degrees"]]
    phi_left, phi_right = [float(value) for value in box["phi_interval_radians"]]
    return {
        "theta_width_degrees": theta_right - theta_left,
        "radial_width_degrees": radius_right - radius_left,
        "phi_width_degrees": math.degrees(phi_right - phi_left),
    }


def support_signature(guard: dict) -> str:
    lower_labels = ",".join(str(label) for label in guard.get("lower_support_labels", []))
    upper_labels = ",".join(str(label) for label in guard.get("upper_support_labels", []))
    return (
        f"lower={guard.get('lower_piece')}[{lower_labels}]"
        f"|upper={guard.get('upper_piece')}[{upper_labels}]"
    )


def failure_category(guard: dict) -> str:
    reason = guard.get("failure_reason")
    if reason == "margin":
        return "margin_only"
    if reason == "stability":
        signed_margin = guard.get("signed_component_margin")
        if signed_margin is None:
            return "stability_without_signed_margin"
        if float(signed_margin) >= 0.0:
            return "stability_only_signed_margin_nonnegative"
        return "stability_and_margin_negative"
    return f"other_{reason}"


def compact_record(box: dict, guard: dict, category: str) -> dict:
    record = adaptive.compact_box(box, guard)
    record.update(
        {
            "failure_category": category,
            "recommended_split_dimension": box.get("recommended_split_dimension"),
            "support_signature": support_signature(guard),
        }
    )
    return record


def classify_terminal_failures(ctx: dict, failed_boxes: list[dict]) -> dict:
    category_counts = Counter()
    reason_counts = Counter()
    split_counts = Counter()
    split_history_counts = Counter()
    support_counts = Counter()
    base_failure_counts: dict[str, Counter] = defaultdict(Counter)
    examples: dict[str, list[dict]] = defaultdict(list)
    records = []

    theta_widths = []
    radial_widths = []
    phi_widths = []
    max_hinge_deviations = []
    signed_margins = []
    margin_only_signed_margins = []
    stability_signed_margins = []
    stability_margins = []
    gap_values = []
    signed_bounds = []

    for box in failed_boxes:
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
            raise AssertionError(f"Reconstructed failed box is now certified: {box['cell_id']}")

        category = failure_category(guard)
        reason_counts[str(guard.get("failure_reason"))] += 1
        category_counts[category] += 1
        split_counts[str(box.get("recommended_split_dimension"))] += 1
        split_history_counts[">".join(box.get("split_history", [])) or "(none)"] += 1
        support_counts[support_signature(guard)] += 1
        base_failure_counts[box["base_cell_id"]][category] += 1

        widths = box_widths(box)
        theta_widths.append(widths["theta_width_degrees"])
        radial_widths.append(widths["radial_width_degrees"])
        phi_widths.append(widths["phi_width_degrees"])
        if guard.get("max_hinge_coordinate_deviation_degrees") is not None:
            max_hinge_deviations.append(float(guard["max_hinge_coordinate_deviation_degrees"]))
        if guard.get("signed_component_margin") is not None:
            signed_margin = float(guard["signed_component_margin"])
            signed_margins.append(signed_margin)
            if category == "margin_only":
                margin_only_signed_margins.append(signed_margin)
            if category.startswith("stability"):
                stability_signed_margins.append(signed_margin)
        if guard.get("minimum_stability_margin") is not None and category.startswith("stability"):
            stability_margins.append(float(guard["minimum_stability_margin"]))
        if guard.get("gap") is not None:
            gap_values.append(float(guard["gap"]))
        if guard.get("signed_component_bound") is not None:
            signed_bounds.append(float(guard["signed_component_bound"]))

        record = compact_record(box, guard, category)
        records.append(record)
        add_example(examples[category], record)

    base_category_presence = Counter()
    base_single_category_counts = Counter()
    for counter in base_failure_counts.values():
        present = [category for category, count in counter.items() if count > 0]
        for category in present:
            base_category_presence[category] += 1
        if len(present) == 1:
            base_single_category_counts[present[0]] += 1
        else:
            base_single_category_counts["mixed"] += 1

    worst_margin_examples = sorted(
        records,
        key=lambda record: (
            float(record["signed_component_margin"])
            if record.get("signed_component_margin") is not None
            else float("inf")
        ),
    )[:MAX_STORED_EXAMPLES]
    worst_stability_examples = sorted(
        [
            record
            for record in records
            if record.get("minimum_stability_margin") is not None
        ],
        key=lambda record: float(record["minimum_stability_margin"]),
    )[:MAX_STORED_EXAMPLES]

    return {
        "terminal_failed_box_count": len(failed_boxes),
        "failure_reason_counts": dict(reason_counts.most_common()),
        "failure_category_counts": dict(category_counts.most_common()),
        "recommended_split_dimension_counts": dict(split_counts.most_common()),
        "split_history_counts": dict(split_history_counts.most_common()),
        "support_signature_counts": dict(support_counts.most_common()),
        "base_failure_summary": {
            "base_with_terminal_failures_count": len(base_failure_counts),
            "base_category_presence_counts": dict(base_category_presence.most_common()),
            "base_single_category_counts": dict(base_single_category_counts.most_common()),
        },
        "width_quantiles": {
            "theta_width_degrees": quantiles(theta_widths),
            "radial_width_degrees": quantiles(radial_widths),
            "phi_width_degrees": quantiles(phi_widths),
            "max_hinge_coordinate_deviation_degrees": quantiles(max_hinge_deviations),
        },
        "guard_value_quantiles": {
            "signed_component_margin_all_failures": quantiles(signed_margins),
            "signed_component_margin_margin_only": quantiles(margin_only_signed_margins),
            "signed_component_margin_stability_failures": quantiles(stability_signed_margins),
            "minimum_stability_margin_stability_failures": quantiles(stability_margins),
            "gap": quantiles(gap_values),
            "signed_component_bound": quantiles(signed_bounds),
        },
        "examples": dict(examples),
        "worst_margin_examples": worst_margin_examples,
        "worst_stability_examples": worst_stability_examples,
    }


def recommendation(classification: dict) -> dict:
    counts = Counter(classification["failure_category_counts"])
    stability_nonnegative = counts.get("stability_only_signed_margin_nonnegative", 0)
    stability_negative = counts.get("stability_and_margin_negative", 0)
    margin_only = counts.get("margin_only", 0)
    stability_total = stability_nonnegative + stability_negative + counts.get("stability_without_signed_margin", 0)

    if stability_nonnegative >= max(stability_negative, margin_only):
        primary = "support_stability_endgame_guard"
        rationale = (
            "Most or many residual boxes have nonnegative signed separation margin and fail because the "
            "support labels are not stable over the whole box."
        )
    elif margin_only > stability_total:
        primary = "margin_guard_or_refinement"
        rationale = "Margin-only failures dominate the terminal frontier."
    else:
        primary = "mixed_stability_and_margin_split"
        rationale = "The terminal frontier is mixed enough that support stability and margin must be handled together."

    return {
        "primary_next_step": primary,
        "rationale": rationale,
        "do_not_claim": [
            "No terminal failed box is certified by this diagnostic.",
            "The report does not close TREE_021 P1-P2.",
            "The report does not close the bounded-cell shared-edge front.",
        ],
    }


def build_report() -> dict:
    ctx = context()
    source_adaptive_report = load_json(RESULTS_DIR / SOURCE_ADAPTIVE_REPORT)
    failed_boxes, level_trace = reconstruct_failed_terminal_boxes(ctx)
    expected_failed = source_adaptive_report["summary_metrics"]["terminal_failed_box_count_at_max_depth"]
    if len(failed_boxes) != expected_failed:
        raise AssertionError(f"Expected {expected_failed} terminal failed boxes, found {len(failed_boxes)}")

    classification = classify_terminal_failures(ctx, failed_boxes)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_tree021_p1p2_endgame_failure_classifier_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_ADAPTIVE_REPORT}",
            f"results/{CASE_ID}/{adaptive.SOURCE_DIRECT_OVERLAY_REPORT}",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
            f"results/{CASE_ID}/tree021_shared_edge_common_edge_guard_report.json",
        ],
        "target": {
            "tree_id": adaptive.TARGET_TREE_ID,
            "pair": list(adaptive.TARGET_PAIR),
            "role": "depth_5_terminal_failure_classification",
            "max_depth": adaptive.MAX_DEPTH,
        },
        "source_adaptive_summary_metrics": source_adaptive_report["summary_metrics"],
        "reconstructed_level_trace": level_trace,
        "summary_metrics": {
            "base_pair_cell_count": len(ctx["boxes"]),
            "max_depth": adaptive.MAX_DEPTH,
            "terminal_failed_box_count_classified": classification["terminal_failed_box_count"],
            "failure_reason_counts": classification["failure_reason_counts"],
            "failure_category_counts": classification["failure_category_counts"],
            "recommended_split_dimension_counts": classification["recommended_split_dimension_counts"],
            "base_failure_summary": classification["base_failure_summary"],
        },
        "classification": classification,
        "recommendation": recommendation(classification),
        "limitations": [
            "This is a diagnostic classifier for the already-failed depth-5 terminal boxes.",
            "No failed box is certified by this report.",
            "The classifier does not refine beyond depth 5.",
            "The result does not cover TREE_007, TREE_021 P0-P3, residual shared-face pair-cells, theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
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
                "recommendation": report["recommendation"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
