"""Bounded-cell shared-edge common-edge overlay for S4 representatives.

This audit targets the residual shared-edge pair-cells left by the first-pass
bounded cell guard:

- TREE_007 P0-P3 and P1-P2.
- TREE_021 P0-P3 and P1-P2.

It lifts the refined-edge common-edge projection-component guard to full
cylindrical wedge cells by using the cell center plus conservative per-hinge
coordinate deviations. This is a direct bounded-cell overlay; it does not use
adaptive subdivision in this report.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_shared_edge_common_edge_overlay_report.json"
SOURCE_COMPONENT_REPORT = "two_class_component_search_report.json"
SOURCE_FIRST_PASS_REPORT = "bounded_cell_guard_first_pass_report.json"
TARGET_TREE_IDS = ["TREE_007", "TREE_021"]
TARGET_PAIRS = [("P0", "P3"), ("P1", "P2")]
MAX_STORED_EXAMPLES = 80
SAT_TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_p0p2_theta_projection_component_bound_probe as theta_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_tree021_shared_edge_common_edge_guard as shared_edge  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402

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


def all_free_cells_for_tree(source_audit: dict, cells: list[dict]) -> list[dict]:
    free_ids = protocol.free_node_ids(source_audit)
    return [
        cell
        for cell in cells
        if all(node_id in free_ids for node_id in cell["vertex_node_ids"])
    ]


def cell_angle_data(tree: dict, signs_by_hinge: dict[str, int], cell: dict) -> tuple[dict[str, float], dict[str, dict], dict[str, float]]:
    center_vector = first_pass.center_angle_vector(tree, signs_by_hinge, cell)
    center_degrees = reps.degrees_from_vector(tree, center_vector)
    intervals = first_pass.angle_coordinate_intervals(tree, signs_by_hinge, cell)
    delta_by_hinge = {
        hinge_id: 2.0 * float(record["max_deviation_from_center_degrees"])
        for hinge_id, record in intervals.items()
    }
    return center_degrees, intervals, delta_by_hinge


def vertices_for_labels(
    transformed: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    piece_id: str,
    labels: list[str],
) -> list[np.ndarray]:
    return [transformed[piece_id][indices[piece_id][label]] for label in labels]


def common_edge_cell_guard(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    cell: dict,
    pair: tuple[str, str],
) -> dict:
    center_degrees, intervals, delta_by_hinge = cell_angle_data(tree, signs_by_hinge, cell)
    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    center_status = lib.collision_report(transformed)["status"]
    unit, axis_norm = shared_edge.common_edge_axis_unit(transformed, indices, pair)
    if unit is None:
        return {
            "certified": False,
            "failure_reason": "degenerate_common_edge_axis",
            "center_sample_status": center_status,
            "axis_norm": rounded(axis_norm),
            "angle_coordinate_intervals_by_hinge": intervals,
        }

    state = shared_edge.support_state_for_pair(transformed, labels_by_piece, pair, unit)
    if not state["separated_at_center"]:
        return {
            "certified": False,
            "failure_reason": "not_separated_at_center",
            "center_sample_status": center_status,
            "axis_name": shared_edge.COMMON_EDGE_AXIS_NAME,
            "axis_norm": rounded(axis_norm),
            "gap": state.get("gap"),
            "angle_coordinate_intervals_by_hinge": intervals,
            "center_angle_degrees_by_hinge": {key: round(value, 12) for key, value in center_degrees.items()},
        }

    lower_support, lower_non_support = sensitivity.piece_label_sets(
        labels_by_piece,
        state["lower_piece"],
        state["lower_support_labels"],
    )
    upper_support, upper_non_support = sensitivity.piece_label_sets(
        labels_by_piece,
        state["upper_piece"],
        state["upper_support_labels"],
    )

    def component(labels: list[str], piece_id: str, direction: str) -> float:
        return theta_probe.component_displacement_bound_for_labels(
            case,
            transforms,
            delta_by_hinge,
            paths_by_piece,
            vertices_for_labels(transformed, indices, piece_id, labels),
            piece_id,
            unit,
            direction,
        )

    lower_support_positive = component(lower_support, state["lower_piece"], "positive")
    upper_support_negative = component(upper_support, state["upper_piece"], "negative")
    lower_support_negative = component(lower_support, state["lower_piece"], "negative")
    lower_non_support_positive = component(lower_non_support, state["lower_piece"], "positive")
    upper_support_positive = component(upper_support, state["upper_piece"], "positive")
    upper_non_support_negative = component(upper_non_support, state["upper_piece"], "negative")

    signed_component_bound = lower_support_positive + upper_support_negative + SAT_TOLERANCE
    signed_component_margin = float(state["gap"]) - signed_component_bound
    lower_stability_margin = (
        float(state["lower_competition_margin"])
        - lower_support_negative
        - lower_non_support_positive
        - SAT_TOLERANCE
    )
    upper_stability_margin = (
        float(state["upper_competition_margin"])
        - upper_support_positive
        - upper_non_support_negative
        - SAT_TOLERANCE
    )
    minimum_stability_margin = min(lower_stability_margin, upper_stability_margin)
    stable = lower_stability_margin >= 0.0 and upper_stability_margin >= 0.0
    certified = center_status == "collision_free" and signed_component_margin >= 0.0 and stable
    if certified:
        failure_reason = None
    elif center_status != "collision_free":
        failure_reason = "center_sample_blocked"
    elif not stable:
        failure_reason = "stability"
    else:
        failure_reason = "margin"

    return {
        "certified": certified,
        "failure_reason": failure_reason,
        "center_sample_status": center_status,
        "axis_name": shared_edge.COMMON_EDGE_AXIS_NAME,
        "axis_norm": rounded(axis_norm),
        "gap": rounded(float(state["gap"])),
        "signed_component_bound": rounded(signed_component_bound),
        "signed_component_margin": rounded(signed_component_margin),
        "minimum_stability_margin": rounded(minimum_stability_margin),
        "lower_piece": state["lower_piece"],
        "upper_piece": state["upper_piece"],
        "lower_support_labels": state["lower_support_labels"],
        "upper_support_labels": state["upper_support_labels"],
        "angle_coordinate_intervals_by_hinge": intervals,
        "center_angle_degrees_by_hinge": {key: round(value, 12) for key, value in center_degrees.items()},
        "max_hinge_coordinate_deviation_degrees": rounded(max(abs(value) for value in delta_by_hinge.values()) / 2.0),
    }


def compact_pair_cell(cell: dict, pair: tuple[str, str], first_pass_record: dict, overlay: dict) -> dict:
    return {
        "cell_id": cell["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "pair": list(pair),
        "first_pass_guard_margin": rounded(first_pass_record["guard_margin"]),
        "certified": overlay["certified"],
        "failure_reason": overlay["failure_reason"],
        "gap": overlay.get("gap"),
        "signed_component_bound": overlay.get("signed_component_bound"),
        "signed_component_margin": overlay.get("signed_component_margin"),
        "minimum_stability_margin": overlay.get("minimum_stability_margin"),
        "max_hinge_coordinate_deviation_degrees": overlay.get("max_hinge_coordinate_deviation_degrees"),
    }


def audit_tree(
    case: dict,
    source_audit: dict,
    signs_by_tree: dict[str, dict[str, int]],
    all_cells: list[dict],
) -> dict:
    tree_id = source_audit["tree_id"]
    tree = comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    target_cells = all_free_cells_for_tree(source_audit, all_cells)
    labels_by_piece = classify.labels_by_piece(case)
    indices = shared_edge.label_indices(case)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    contacts_by_pair = ray_guard.contact_by_pair(case)
    hinge_by_pair = first_pass.selected_hinge_by_pair(case, tree)

    result_counts = Counter()
    result_counts_by_pair = defaultdict(Counter)
    margin_values = []
    certified_margins = []
    failed_margins = []
    stability_values = []
    first_pass_targets = []
    examples = defaultdict(list)

    for cell in target_cells:
        first_pass_cell = first_pass.audit_cell(
            case,
            tree,
            signs,
            cell,
            paths_by_piece,
            contacts_by_pair,
            hinge_by_pair,
        )
        first_pass_by_pair = {
            tuple(record["pair"]): record
            for record in first_pass_cell["pair_records"]
        }
        for pair in TARGET_PAIRS:
            first_pass_record = first_pass_by_pair[pair]
            if first_pass_record["role"] != "residual_shared_edge":
                continue
            if first_pass_record["first_pass_covered"]:
                continue
            overlay = common_edge_cell_guard(
                case,
                tree,
                signs,
                indices,
                labels_by_piece,
                paths_by_piece,
                cell,
                pair,
            )
            key = "certified" if overlay["certified"] else f"failed:{overlay['failure_reason']}"
            result_counts[key] += 1
            pair_key = "-".join(pair)
            result_counts_by_pair[pair_key][key] += 1
            compact = compact_pair_cell(cell, pair, first_pass_record, overlay)
            first_pass_targets.append(compact)
            add_example(examples["certified" if overlay["certified"] else "failed"], compact)
            if overlay.get("signed_component_margin") is not None:
                value = float(overlay["signed_component_margin"])
                margin_values.append(value)
                if overlay["certified"]:
                    certified_margins.append(value)
                else:
                    failed_margins.append(value)
            if overlay.get("minimum_stability_margin") is not None:
                stability_values.append(float(overlay["minimum_stability_margin"]))

    input_count = len(first_pass_targets)
    certified_count = result_counts.get("certified", 0)
    return {
        "tree_id": tree_id,
        "class_id": source_audit["class_id"],
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs,
        "status": "bounded_cell_shared_edge_common_edge_overlay_completed",
        "summary_metrics": {
            "input_uncovered_shared_edge_pair_cell_count": input_count,
            "direct_common_edge_certified_pair_cell_count": certified_count,
            "direct_common_edge_uncovered_pair_cell_count": input_count - certified_count,
            "direct_overlay_closed": input_count == certified_count,
        },
        "result_counts": dict(result_counts.most_common()),
        "result_counts_by_pair": {pair: dict(counter.most_common()) for pair, counter in sorted(result_counts_by_pair.items())},
        "signed_component_margin_quantiles": quantiles(margin_values),
        "certified_signed_component_margin_quantiles": quantiles(certified_margins),
        "failed_signed_component_margin_quantiles": quantiles(failed_margins),
        "minimum_stability_margin_quantiles": quantiles(stability_values),
        "examples": dict(examples),
    }


def build_report() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / SOURCE_COMPONENT_REPORT)
    first_pass_report = load_json(RESULTS_DIR / SOURCE_FIRST_PASS_REPORT)
    signs_by_tree = comp.certified_signs_by_tree()
    source_by_tree = {audit["tree_id"]: audit for audit in component_report["representative_audits"]}
    all_cells = protocol.iter_cells()
    tree_reports = [
        audit_tree(case, source_by_tree[tree_id], signs_by_tree, all_cells)
        for tree_id in TARGET_TREE_IDS
    ]
    total_input = sum(report["summary_metrics"]["input_uncovered_shared_edge_pair_cell_count"] for report in tree_reports)
    total_certified = sum(report["summary_metrics"]["direct_common_edge_certified_pair_cell_count"] for report in tree_reports)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_shared_edge_common_edge_overlay_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_FIRST_PASS_REPORT}",
            f"results/{CASE_ID}/bounded_cell_cover_protocol_spec_report.json",
            f"results/{CASE_ID}/tree007_shared_edge_common_edge_guard_report.json",
            f"results/{CASE_ID}/tree021_shared_edge_common_edge_guard_report.json",
        ],
        "target": {
            "tree_ids": TARGET_TREE_IDS,
            "pairs": [list(pair) for pair in TARGET_PAIRS],
            "role": "residual_shared_edge",
            "common_edge_axis_name": shared_edge.COMMON_EDGE_AXIS_NAME,
            "adaptive_subdivision_used": False,
        },
        "source_first_pass_summary_metrics": first_pass_report["summary_metrics"],
        "summary_metrics": {
            "tree_count": len(tree_reports),
            "total_input_uncovered_shared_edge_pair_cell_count": total_input,
            "total_direct_common_edge_certified_pair_cell_count": total_certified,
            "total_direct_common_edge_uncovered_pair_cell_count": total_input - total_certified,
            "direct_shared_edge_overlay_closed": total_input == total_certified,
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This is a direct full-cell shared-edge common-edge overlay, not an adaptive subdivision closure.",
            "The guard uses conservative per-hinge coordinate deviations around each cell center.",
            "It targets only residual shared-edge pair-cells left by the first-pass bounded cell guard.",
            "Residual shared-face pair-cells, theta=0, dynamic class connection, physical hinge offsets/thickness, mesh export, and printability remain outside this report.",
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
                    report["tree_id"]: report["summary_metrics"]
                    for report in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
