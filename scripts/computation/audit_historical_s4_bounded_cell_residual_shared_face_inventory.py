"""Bounded-cell residual shared-face inventory for S4 representatives.

The bounded-cell shared-edge front is now closed by separate closure-stack
reports. This diagnostic inventory returns to the first-pass bounded-cell guard
and classifies the remaining residual shared-face pair-cells:

- TREE_021 P0-P2
- TREE_007 P2-P3

For each first-pass-uncovered shared-face pair-cell, the script records the
named separating-axis family at the cell center. The classification is a routing
ledger only: it separates edge-branch cases from face-normal cases before any
full-cell formula guard is ported to the bounded-cell setting.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_residual_shared_face_inventory_report.json"
TARGETS = [
    {
        "tree_id": "TREE_021",
        "pair": ("P0", "P2"),
        "edge_branch_fallback": "tree021_p0p2_edge_branch_workflow",
        "face_normal_fallback": "tree021_p0p2_face_normal_formula_guard",
    },
    {
        "tree_id": "TREE_007",
        "pair": ("P2", "P3"),
        "edge_branch_fallback": "tree007_p2p3_edge_branch_workflow",
        "face_normal_fallback": "tree007_p2p3_face_normal_formula_guard",
    },
]
MAX_STORED_EXAMPLES_PER_AXIS = 8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

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
    if len(bucket) < MAX_STORED_EXAMPLES_PER_AXIS:
        bucket.append(record)


def target_key(target: dict) -> str:
    return f"{target['tree_id']}:{'-'.join(target['pair'])}"


def axis_category(axis_name: str) -> str:
    if axis_name.startswith("left_face:") or axis_name.startswith("right_face:"):
        return "face_normal"
    if axis_name.startswith("edge:"):
        return "edge_branch"
    return "other"


def cell_widths(cell: dict) -> dict[str, float]:
    theta_left, theta_right = [float(value) for value in cell["theta_interval_degrees"]]
    radial_left, radial_right = [float(value) for value in cell["radial_interval_degrees"]]
    return {
        "theta_width_degrees": theta_right - theta_left,
        "radial_width_degrees": radial_right - radial_left,
        "direction_sector_width": 1.0,
    }


def compact_record(cell: dict, pair_record: dict, best_axis: dict, category: str) -> dict:
    return {
        "cell_id": cell["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "pair": pair_record["pair"],
        "role": pair_record["role"],
        "axis_name": best_axis["axis_name"],
        "axis_category": category,
        "first_pass_guard_margin": rounded(pair_record["guard_margin"]),
        "first_pass_guard_bound": rounded(pair_record["guard_bound"]),
        "first_pass_post_guard_overlap_bound": rounded(pair_record["post_guard_overlap_bound"]),
        "center_axis_overlap_named": rounded(best_axis["center_axis_overlap"]),
        "fallback_classes": pair_record["fallback_classes"],
        "widths": {key: rounded(value) for key, value in cell_widths(cell).items()},
    }


def context() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / first_pass.SOURCE_COMPONENT_REPORT)
    source_by_tree = {audit["tree_id"]: audit for audit in component_report["representative_audits"]}
    return {
        "case": case,
        "source_by_tree": source_by_tree,
        "signs_by_tree": comp.certified_signs_by_tree(),
        "contacts_by_pair": ray_guard.contact_by_pair(case),
        "labels_by_piece": classify.labels_by_piece(case),
        "all_cells": protocol.iter_cells(),
    }


def first_pass_pair_summary(tree_report: dict, pair: tuple[str, str]) -> dict:
    for item in tree_report["pair_summary"]:
        if tuple(item["pair"]) == pair:
            return item
    raise KeyError(f"Missing first-pass pair summary for {'-'.join(pair)}")


def source_first_pass_summaries() -> dict[str, dict]:
    report = load_json(RESULTS_DIR / first_pass.REPORT_NAME)
    return {tree_report["tree_id"]: tree_report for tree_report in report["tree_reports"]}


def audit_target(ctx: dict, target: dict, source_first_pass: dict) -> dict:
    tree_id = target["tree_id"]
    pair = target["pair"]
    case = ctx["case"]
    tree = comp.find_tree(case, tree_id)
    signs = ctx["signs_by_tree"][tree_id]
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    hinge_by_pair = first_pass.selected_hinge_by_pair(case, tree)
    free_cells = first_pass.all_free_cells_for_tree(ctx["source_by_tree"][tree_id], ctx["all_cells"])

    axis_counts = Counter()
    category_counts = Counter()
    kind_counts = Counter()
    theta_interval_counts = Counter()
    radial_interval_counts = Counter()
    direction_sector_counts = Counter()
    fallback_counts = Counter()
    guard_margins = []
    guard_bounds = []
    post_guard_overlaps = []
    named_axis_overlaps = []
    width_values = defaultdict(list)
    examples_by_axis = defaultdict(list)
    records = []

    for cell in free_cells:
        audited = first_pass.audit_cell(
            case,
            tree,
            signs,
            cell,
            paths_by_piece,
            ctx["contacts_by_pair"],
            hinge_by_pair,
        )
        pair_record = next(record for record in audited["pair_records"] if tuple(record["pair"]) == pair)
        if pair_record["role"] != "residual_shared_face" or pair_record["first_pass_covered"]:
            continue

        transforms = ray_guard.transforms_for_degrees(case, tree, audited["center_angle_degrees_by_hinge"])
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        best_axis = classify.best_named_axis(
            transformed[pair[0]],
            transformed[pair[1]],
            ctx["labels_by_piece"][pair[0]],
            ctx["labels_by_piece"][pair[1]],
        )
        category = axis_category(best_axis["axis_name"])
        record = compact_record(cell, pair_record, best_axis, category)
        records.append(record)
        add_example(examples_by_axis[best_axis["axis_name"]], record)

        axis_counts[best_axis["axis_name"]] += 1
        category_counts[category] += 1
        kind_counts[cell["kind"]] += 1
        theta_interval_counts[str(cell["theta_interval_degrees"])] += 1
        radial_interval_counts[str(cell["radial_interval_degrees"])] += 1
        direction_sector_counts[str(cell["direction_sector"])] += 1
        fallback_counts.update(pair_record["fallback_classes"])
        guard_margins.append(float(pair_record["guard_margin"]))
        guard_bounds.append(float(pair_record["guard_bound"]))
        post_guard_overlaps.append(float(pair_record["post_guard_overlap_bound"]))
        named_axis_overlaps.append(float(best_axis["center_axis_overlap"]))
        for width_key, value in cell_widths(cell).items():
            width_values[width_key].append(float(value))

    fp_summary = first_pass_pair_summary(source_first_pass[tree_id], pair)
    expected_uncovered = int(fp_summary["uncovered_cell_count"])
    if len(records) != expected_uncovered:
        raise AssertionError(
            f"{tree_id} {'-'.join(pair)} expected {expected_uncovered} first-pass uncovered cells, "
            f"found {len(records)}"
        )

    face_count = category_counts.get("face_normal", 0)
    edge_count = category_counts.get("edge_branch", 0)
    other_count = category_counts.get("other", 0)
    return {
        "target": {
            "tree_id": tree_id,
            "pair": list(pair),
            "role": "residual_shared_face",
            "edge_branch_fallback": target["edge_branch_fallback"],
            "face_normal_fallback": target["face_normal_fallback"],
        },
        "source_first_pass_pair_summary": fp_summary,
        "summary_metrics": {
            "first_pass_uncovered_shared_face_cell_count": len(records),
            "center_axis_face_normal_cell_count": face_count,
            "center_axis_edge_branch_cell_count": edge_count,
            "center_axis_other_cell_count": other_count,
            "center_axis_classification_complete": other_count == 0 and len(records) == face_count + edge_count,
            "distinct_center_axis_count": len(axis_counts),
            "distinct_direction_sector_count": len(direction_sector_counts),
        },
        "breakdown": {
            "center_axis_category_counts": dict(category_counts.most_common()),
            "center_axis_name_counts": dict(axis_counts.most_common()),
            "cell_kind_counts": dict(kind_counts.most_common()),
            "theta_interval_counts": dict(theta_interval_counts.most_common()),
            "radial_interval_counts": dict(radial_interval_counts.most_common()),
            "fallback_class_counts": dict(fallback_counts.most_common()),
            "first_pass_guard_margin_quantiles": quantiles(guard_margins),
            "first_pass_guard_bound_quantiles": quantiles(guard_bounds),
            "first_pass_post_guard_overlap_bound_quantiles": quantiles(post_guard_overlaps),
            "named_center_axis_overlap_quantiles": quantiles(named_axis_overlaps),
            "width_quantiles": {
                key: quantiles(values)
                for key, values in sorted(width_values.items())
            },
        },
        "examples_by_axis": dict(examples_by_axis),
        "records": records,
    }


def aggregate_summary(target_reports: list[dict]) -> dict:
    def total(metric: str) -> int:
        return sum(int(report["summary_metrics"][metric]) for report in target_reports)

    category_counts = Counter()
    axis_counts = Counter()
    for report in target_reports:
        category_counts.update(report["breakdown"]["center_axis_category_counts"])
        axis_counts.update(report["breakdown"]["center_axis_name_counts"])
    total_cells = total("first_pass_uncovered_shared_face_cell_count")
    return {
        "target_count": len(target_reports),
        "first_pass_uncovered_shared_face_cell_count": total_cells,
        "center_axis_face_normal_cell_count": total("center_axis_face_normal_cell_count"),
        "center_axis_edge_branch_cell_count": total("center_axis_edge_branch_cell_count"),
        "center_axis_other_cell_count": total("center_axis_other_cell_count"),
        "center_axis_classification_complete": all(
            report["summary_metrics"]["center_axis_classification_complete"]
            for report in target_reports
        ),
        "center_axis_category_counts": dict(category_counts.most_common()),
        "top_center_axis_name_counts": dict(axis_counts.most_common(16)),
    }


def build_report() -> dict:
    ctx = context()
    first_pass_summaries = source_first_pass_summaries()
    target_reports = [
        audit_target(ctx, target, first_pass_summaries)
        for target in TARGETS
    ]
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_residual_shared_face_inventory_completed",
        "source_reports": [
            f"results/{CASE_ID}/{first_pass.REPORT_NAME}",
            f"results/{CASE_ID}/bounded_cell_shared_edge_common_edge_overlay_report.json",
            f"results/{CASE_ID}/bounded_cell_tree021_p1p2_margin_endgame_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_tree021_p0p3_closure_stack_report.json",
            f"results/{CASE_ID}/bounded_cell_tree007_shared_edge_closure_stack_report.json",
        ],
        "target": {
            "description": "first-pass-uncovered bounded-cell residual shared-face pair-cells after shared-edge closure",
            "targets": [
                {"tree_id": item["tree_id"], "pair": list(item["pair"])}
                for item in TARGETS
            ],
            "classification_method": "named center separating-axis family on each first-pass-uncovered shared-face bounded cell",
        },
        "summary_metrics": aggregate_summary(target_reports),
        "target_reports": target_reports,
        "limitations": [
            "This is a routing inventory/classifier only; it does not certify any residual shared-face bounded cell.",
            "Axis families are assigned from the named best separating axis at the bounded-cell center; full-cell formula guards still need separate interval proofs.",
            "The report covers only the all-vertices-free bounded cells from the current bounded-cell protocol and does not include blocked-vertex cells.",
            "The domain starts at theta=0.5 degrees and does not cover theta=0.",
            "The report does not certify dynamic class connection, physical hinge offsets/thickness, mesh export, or printability.",
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
                "target_summaries": {
                    target_key(item["target"]): item["summary_metrics"]
                    for item in report["target_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
