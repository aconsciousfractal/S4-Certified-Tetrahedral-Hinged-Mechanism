"""G2 multi-axis guard for S4 bounded-cell edge-branch cells.

The bounded-cell edge-branch guard plan assigns 371 cells to route G2:

- TREE_007 P2-P3: 140 cells
- TREE_021 P0-P2: 231 cells

These cells have an assigned center edge axis that remains separating at all
cell center/vertex samples, but the best named edge axis switches across those
samples. This audit uses the same projection-component support guard as the G1
fixed-axis report, but allows a finite edge-axis family on each subcell.

The guard order is tactical:

1. Try the assigned axis plus sampled best edge axes recorded by the classifier.
2. If that fails on a subcell, extend to all local named edge axes at the
   subcell center, sorted by center overlap.

This certifies only the G2 route. It does not cover G3 hybrid edge/face switch
cells or G4 nonseparating-axis cells.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_edge_branch_g2_multi_axis_guard_report.json"
SOURCE_CLASSIFIER_REPORT = "bounded_cell_edge_branch_stability_classifier_report.json"
SOURCE_GUARD_PLAN_REPORT = "bounded_cell_edge_branch_guard_plan_report.json"
SOURCE_G1_REPORT = "bounded_cell_edge_branch_g1_fixed_axis_guard_report.json"
G2_PROFILE = "assigned_separating_edge_axis_switch"
G2_ROUTE = "G2_multi_edge_axis_switch_guard"
SUBDIVISION = {
    "theta_splits": 16,
    "radial_splits": 2,
    "direction_splits": 2,
}
MAX_STORED_EXAMPLES = 36

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_bounded_cell_edge_branch_g1_fixed_axis_guard as g1  # noqa: E402

RESULTS_DIR = g1.RESULTS_DIR


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def sample_candidate_axes(record: dict) -> list[str]:
    axes = []
    for axis_name in [record["assigned_axis_name"], *record["best_axis_name_counts"].keys()]:
        if axis_name.startswith("edge:") and axis_name not in axes:
            axes.append(axis_name)
    return axes


def local_edge_axis_names(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    labels_by_piece: dict[str, list[str]],
    pair: tuple[str, str],
    subcell: dict,
) -> list[str]:
    center_vector = g1.subcell_center_angle_vector(tree, signs_by_hinge, subcell)
    center_degrees = g1.reps.degrees_from_vector(tree, center_vector)
    transforms = g1.ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = g1.lib.transform_pieces(case["pieces_by_id"], transforms)

    ranked = []
    for axis_name, axis in g1.classify.axis_records(
        transformed[pair[0]],
        transformed[pair[1]],
        labels_by_piece[pair[0]],
        labels_by_piece[pair[1]],
    ):
        if not axis_name.startswith("edge:"):
            continue
        norm = float(np.linalg.norm(axis))
        if norm <= g1.lib.TOL:
            continue
        unit = axis / norm
        left_values = [float(np.dot(vertex, unit)) for vertex in transformed[pair[0]]]
        right_values = [float(np.dot(vertex, unit)) for vertex in transformed[pair[1]]]
        overlap = min(max(left_values), max(right_values)) - max(min(left_values), min(right_values))
        ranked.append((float(overlap), axis_name))

    axes = []
    for _overlap, axis_name in sorted(ranked):
        if axis_name not in axes:
            axes.append(axis_name)
    return axes


def compact_attempt(result: dict, axis_name: str, stage: str, rank: int) -> dict:
    compact = {
        **result,
        "candidate_axis_name": axis_name,
        "candidate_stage": stage,
        "candidate_rank": rank,
    }
    return compact


def evaluate_subcell_with_candidates(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    record: dict,
    subcell: dict,
) -> dict:
    pair = tuple(record["pair"])
    tested_axes = []
    failures = []

    for rank, axis_name in enumerate(sample_candidate_axes(record), start=1):
        trial = {**record, "assigned_axis_name": axis_name}
        result = g1.evaluate_subcell(
            case,
            tree,
            signs_by_hinge,
            indices,
            labels_by_piece,
            paths_by_piece,
            trial,
            subcell,
        )
        tested_axes.append(axis_name)
        if result["certified"]:
            return {
                "certified": True,
                "attempt_count": len(tested_axes),
                "tested_axis_count": len(tested_axes),
                "source_candidate_axis_count": len(sample_candidate_axes(record)),
                "local_fallback_axis_count": 0,
                "accepted": compact_attempt(result, axis_name, "sample_candidate_family", rank),
                "failed_attempts": [],
            }
        failures.append(compact_attempt(result, axis_name, "sample_candidate_family", rank))

    local_axes = [
        axis_name
        for axis_name in local_edge_axis_names(case, tree, signs_by_hinge, labels_by_piece, pair, subcell)
        if axis_name not in tested_axes
    ]
    for local_rank, axis_name in enumerate(local_axes, start=1):
        trial = {**record, "assigned_axis_name": axis_name}
        result = g1.evaluate_subcell(
            case,
            tree,
            signs_by_hinge,
            indices,
            labels_by_piece,
            paths_by_piece,
            trial,
            subcell,
        )
        tested_axes.append(axis_name)
        if result["certified"]:
            return {
                "certified": True,
                "attempt_count": len(tested_axes),
                "tested_axis_count": len(tested_axes),
                "source_candidate_axis_count": len(sample_candidate_axes(record)),
                "local_fallback_axis_count": len(local_axes),
                "accepted": compact_attempt(result, axis_name, "local_edge_axis_fallback", local_rank),
                "failed_attempts": [],
            }
        failures.append(compact_attempt(result, axis_name, "local_edge_axis_fallback", local_rank))

    worst = min(
        failures,
        key=lambda item: (
            float("inf") if item.get("signed_component_margin") is None else -float(item["signed_component_margin"]),
            float("inf") if item.get("minimum_stability_margin") is None else -float(item["minimum_stability_margin"]),
        ),
    )
    return {
        "certified": False,
        "attempt_count": len(tested_axes),
        "tested_axis_count": len(tested_axes),
        "source_candidate_axis_count": len(sample_candidate_axes(record)),
        "local_fallback_axis_count": len(local_axes),
        "accepted": None,
        "best_failed_attempt": worst,
        "failed_attempts": failures[:8],
    }


def compact_cell_record(tree_id: str, record: dict, cell: dict, subcell_reports: list[dict]) -> dict:
    accepted = [item["accepted"] for item in subcell_reports if item["accepted"] is not None]
    failed = [item for item in subcell_reports if not item["certified"]]
    stage_counts = Counter(item["accepted"]["candidate_stage"] for item in subcell_reports if item["accepted"] is not None)
    accepted_axis_counts = Counter(item["accepted"]["candidate_axis_name"] for item in subcell_reports if item["accepted"] is not None)
    attempt_counts = Counter(item["attempt_count"] for item in subcell_reports)
    margins = [
        float(item["signed_component_margin"])
        for item in accepted
        if item.get("signed_component_margin") is not None
    ]
    stability_margins = [
        float(item["minimum_stability_margin"])
        for item in accepted
        if item.get("minimum_stability_margin") is not None
    ]
    gaps = [
        float(item["gap"])
        for item in accepted
        if item.get("gap") is not None
    ]
    max_deviations = [
        float(item["max_hinge_deviation_degrees"])
        for item in accepted
        if item.get("max_hinge_deviation_degrees") is not None
    ]
    worst = min(
        accepted,
        key=lambda item: (
            float("inf") if item.get("signed_component_margin") is None else float(item["signed_component_margin"]),
            float("inf") if item.get("minimum_stability_margin") is None else float(item["minimum_stability_margin"]),
        ),
    )
    return {
        "cell_id": record["cell_id"],
        "tree_id": tree_id,
        "pair": record["pair"],
        "kind": cell["kind"],
        "route": G2_ROUTE,
        "assigned_axis_name": record["assigned_axis_name"],
        "source_candidate_axes": sample_candidate_axes(record),
        "source_candidate_axis_count": len(sample_candidate_axes(record)),
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "sample_profile": record["sample_profile"],
        "source_sample_gap_interval": record["assigned_axis_gap_interval"],
        "source_best_axis_name_counts": record["best_axis_name_counts"],
        "subdivision": SUBDIVISION,
        "subcell_count": len(subcell_reports),
        "certified_subcell_count": len(accepted),
        "failed_subcell_count": len(failed),
        "cell_certified": len(failed) == 0,
        "sample_candidate_family_subcell_count": stage_counts.get("sample_candidate_family", 0),
        "local_edge_axis_fallback_subcell_count": stage_counts.get("local_edge_axis_fallback", 0),
        "minimum_gap": g1.rounded(min(gaps) if gaps else None, 15),
        "minimum_signed_component_margin": g1.rounded(min(margins) if margins else None, 15),
        "minimum_signed_stability_margin": g1.rounded(min(stability_margins) if stability_margins else None, 15),
        "maximum_subcell_hinge_deviation_degrees": g1.rounded(max(max_deviations) if max_deviations else None, 15),
        "accepted_axis_counts": dict(accepted_axis_counts.most_common()),
        "attempt_count_distribution": dict(attempt_counts.most_common()),
        "worst_subcell": worst,
        "failure_reason_counts": dict(Counter(item["best_failed_attempt"]["failure_reason"] for item in failed).most_common()),
    }


def g2_records_by_tree(classifier_report: dict) -> dict[str, list[dict]]:
    output = {}
    for target_report in classifier_report["target_reports"]:
        tree_id = target_report["target"]["tree_id"]
        output[tree_id] = [
            record
            for record in target_report["cell_reports"]
            if record["sample_profile"] == G2_PROFILE
        ]
    return output


def audit_target(
    case: dict,
    tree_id: str,
    records: list[dict],
    cell_by_id: dict[str, dict],
    signs_by_tree: dict[str, dict[str, int]],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
) -> dict:
    tree = g1.comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    paths_by_piece = g1.ray_guard.tree_paths_from_root(case, tree)

    cell_reports = []
    examples = defaultdict(list)
    source_candidate_counts = Counter()
    assigned_axis_counts = Counter()
    accepted_axis_counts = Counter()
    stage_counts = Counter()
    attempt_counts = Counter()
    kind_counts = Counter()
    signed_margins = []
    stability_margins = []
    gaps = []
    max_deviations = []

    for record in records:
        cell = cell_by_id[record["cell_id"]]
        subcell_reports = [
            evaluate_subcell_with_candidates(
                case,
                tree,
                signs,
                indices,
                labels_by_piece,
                paths_by_piece,
                record,
                subcell,
            )
            for subcell in g1.subdivide_cell(cell)
        ]
        compact = compact_cell_record(tree_id, record, cell, subcell_reports)
        cell_reports.append(compact)

        source_candidate_counts[compact["source_candidate_axis_count"]] += 1
        assigned_axis_counts[record["assigned_axis_name"]] += 1
        accepted_axis_counts.update(compact["accepted_axis_counts"])
        stage_counts["sample_candidate_family"] += compact["sample_candidate_family_subcell_count"]
        stage_counts["local_edge_axis_fallback"] += compact["local_edge_axis_fallback_subcell_count"]
        kind_counts[cell["kind"]] += 1
        for count, frequency in compact["attempt_count_distribution"].items():
            attempt_counts[int(count)] += int(frequency)
        if compact["local_edge_axis_fallback_subcell_count"] > 0:
            add_example(examples["cells_needing_local_edge_axis_fallback"], compact)
        else:
            add_example(examples["cells_certified_by_sample_candidate_family"], compact)
        if not compact["cell_certified"]:
            add_example(examples["uncovered_cells"], compact)
        if compact["minimum_signed_component_margin"] is not None:
            signed_margins.append(float(compact["minimum_signed_component_margin"]))
        if compact["minimum_signed_stability_margin"] is not None:
            stability_margins.append(float(compact["minimum_signed_stability_margin"]))
        if compact["minimum_gap"] is not None:
            gaps.append(float(compact["minimum_gap"]))
        if compact["maximum_subcell_hinge_deviation_degrees"] is not None:
            max_deviations.append(float(compact["maximum_subcell_hinge_deviation_degrees"]))

    certified_cells = sum(1 for item in cell_reports if item["cell_certified"])
    total_subcells = sum(item["subcell_count"] for item in cell_reports)
    certified_subcells = sum(item["certified_subcell_count"] for item in cell_reports)
    fallback_cells = sum(1 for item in cell_reports if item["local_edge_axis_fallback_subcell_count"] > 0)
    return {
        "target": {
            "tree_id": tree_id,
            "pair": records[0]["pair"] if records else None,
            "route": G2_ROUTE,
            "source_sample_profile": G2_PROFILE,
        },
        "summary_metrics": {
            "input_g2_cell_count": len(records),
            "g2_certified_cell_count": certified_cells,
            "g2_uncovered_cell_count": len(records) - certified_cells,
            "g2_all_input_cells_certified": certified_cells == len(records),
            "subcell_count": total_subcells,
            "certified_subcell_count": certified_subcells,
            "failed_subcell_count": total_subcells - certified_subcells,
            "sample_candidate_family_subcell_count": stage_counts.get("sample_candidate_family", 0),
            "local_edge_axis_fallback_subcell_count": stage_counts.get("local_edge_axis_fallback", 0),
            "cells_needing_local_edge_axis_fallback": fallback_cells,
            "cells_certified_by_sample_candidate_family_only": len(records) - fallback_cells,
            "minimum_signed_component_margin": g1.rounded(min(signed_margins) if signed_margins else None, 15),
            "minimum_signed_stability_margin": g1.rounded(min(stability_margins) if stability_margins else None, 15),
            "minimum_gap": g1.rounded(min(gaps) if gaps else None, 15),
            "maximum_subcell_hinge_deviation_degrees": g1.rounded(max(max_deviations) if max_deviations else None, 15),
        },
        "breakdown": {
            "source_candidate_axis_count_distribution_by_cell": dict(source_candidate_counts.most_common()),
            "assigned_axis_counts": dict(assigned_axis_counts.most_common()),
            "accepted_axis_counts": dict(accepted_axis_counts.most_common()),
            "coverage_stage_counts_by_subcell": dict(stage_counts.most_common()),
            "attempt_count_distribution_by_subcell": dict(attempt_counts.most_common()),
            "cell_kind_counts": dict(kind_counts.most_common()),
            "signed_component_margin_quantiles": g1.quantiles(signed_margins),
            "signed_stability_margin_quantiles": g1.quantiles(stability_margins),
            "gap_quantiles": g1.quantiles(gaps),
            "max_hinge_deviation_quantiles_degrees": g1.quantiles(max_deviations),
        },
        "examples": dict(examples),
        "cell_reports": cell_reports,
    }


def aggregate_summary(target_reports: list[dict]) -> dict:
    def total(metric: str) -> int:
        return sum(int(report["summary_metrics"][metric]) for report in target_reports)

    accepted_axis_counts = Counter()
    assigned_axis_counts = Counter()
    stage_counts = Counter()
    attempt_counts = Counter()
    kind_counts = Counter()
    source_candidate_counts = Counter()
    signed_margins = []
    stability_margins = []
    gaps = []
    max_deviations = []
    tree_counts = {}
    tree_certified_counts = {}
    tree_fallback_counts = {}
    for report in target_reports:
        tree_id = report["target"]["tree_id"]
        tree_counts[tree_id] = report["summary_metrics"]["input_g2_cell_count"]
        tree_certified_counts[tree_id] = report["summary_metrics"]["g2_certified_cell_count"]
        tree_fallback_counts[tree_id] = report["summary_metrics"]["cells_needing_local_edge_axis_fallback"]
        accepted_axis_counts.update(report["breakdown"]["accepted_axis_counts"])
        assigned_axis_counts.update(report["breakdown"]["assigned_axis_counts"])
        stage_counts.update(report["breakdown"]["coverage_stage_counts_by_subcell"])
        attempt_counts.update({int(k): v for k, v in report["breakdown"]["attempt_count_distribution_by_subcell"].items()})
        kind_counts.update(report["breakdown"]["cell_kind_counts"])
        source_candidate_counts.update({int(k): v for k, v in report["breakdown"]["source_candidate_axis_count_distribution_by_cell"].items()})
        signed_margins.extend(
            float(cell["minimum_signed_component_margin"])
            for cell in report["cell_reports"]
            if cell["minimum_signed_component_margin"] is not None
        )
        stability_margins.extend(
            float(cell["minimum_signed_stability_margin"])
            for cell in report["cell_reports"]
            if cell["minimum_signed_stability_margin"] is not None
        )
        gaps.extend(
            float(cell["minimum_gap"])
            for cell in report["cell_reports"]
            if cell["minimum_gap"] is not None
        )
        max_deviations.append(report["summary_metrics"]["maximum_subcell_hinge_deviation_degrees"])

    input_cells = total("input_g2_cell_count")
    certified_cells = total("g2_certified_cell_count")
    subcells = total("subcell_count")
    certified_subcells = total("certified_subcell_count")
    fallback_cells = total("cells_needing_local_edge_axis_fallback")
    return {
        "target_count": len(target_reports),
        "input_g2_cell_count": input_cells,
        "g2_certified_cell_count": certified_cells,
        "g2_uncovered_cell_count": input_cells - certified_cells,
        "g2_all_input_cells_certified": certified_cells == input_cells,
        "subdivision": SUBDIVISION,
        "subcell_count": subcells,
        "certified_subcell_count": certified_subcells,
        "failed_subcell_count": subcells - certified_subcells,
        "all_subcells_certified": certified_subcells == subcells,
        "sample_candidate_family_subcell_count": total("sample_candidate_family_subcell_count"),
        "local_edge_axis_fallback_subcell_count": total("local_edge_axis_fallback_subcell_count"),
        "cells_needing_local_edge_axis_fallback": fallback_cells,
        "cells_certified_by_sample_candidate_family_only": input_cells - fallback_cells,
        "tree_counts": tree_counts,
        "tree_certified_cell_counts": tree_certified_counts,
        "tree_local_fallback_cell_counts": tree_fallback_counts,
        "source_candidate_axis_count_distribution_by_cell": dict(source_candidate_counts.most_common()),
        "assigned_axis_counts": dict(assigned_axis_counts.most_common()),
        "accepted_axis_counts": dict(accepted_axis_counts.most_common()),
        "coverage_stage_counts_by_subcell": dict(stage_counts.most_common()),
        "attempt_count_distribution_by_subcell": dict(attempt_counts.most_common()),
        "cell_kind_counts": dict(kind_counts.most_common()),
        "minimum_signed_component_margin": g1.rounded(min(signed_margins) if signed_margins else None, 15),
        "minimum_signed_stability_margin": g1.rounded(min(stability_margins) if stability_margins else None, 15),
        "minimum_gap": g1.rounded(min(gaps) if gaps else None, 15),
        "maximum_subcell_hinge_deviation_degrees": g1.rounded(max(max_deviations) if max_deviations else None, 15),
    }


def build_report() -> dict:
    g1.SUBDIVISION.clear()
    g1.SUBDIVISION.update(SUBDIVISION)

    classifier_report = g1.load_json(RESULTS_DIR / SOURCE_CLASSIFIER_REPORT)
    guard_plan = g1.load_json(RESULTS_DIR / SOURCE_GUARD_PLAN_REPORT)
    expected_g2 = int(guard_plan["summary_metrics"]["route_counts"][G2_ROUTE])
    records_by_tree = g2_records_by_tree(classifier_report)
    input_g2 = sum(len(records) for records in records_by_tree.values())
    if input_g2 != expected_g2:
        raise AssertionError(f"Expected {expected_g2} G2 cells from guard plan, found {input_g2}")

    case = g1.batch.build_case()
    signs_by_tree = g1.comp.certified_signs_by_tree()
    indices = g1.classifier.label_indices(case)
    labels_by_piece = g1.classify.labels_by_piece(case)
    cell_by_id = {cell["cell_id"]: cell for cell in g1.protocol.iter_cells()}

    target_reports = [
        audit_target(case, tree_id, records_by_tree[tree_id], cell_by_id, signs_by_tree, indices, labels_by_piece)
        for tree_id in sorted(records_by_tree)
    ]
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_edge_branch_g2_multi_axis_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_CLASSIFIER_REPORT}",
            f"results/{CASE_ID}/{SOURCE_GUARD_PLAN_REPORT}",
            f"results/{CASE_ID}/{SOURCE_G1_REPORT}",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
        ],
        "target": {
            "description": "G2 multi-edge-axis switch guard for bounded-cell edge-branch records",
            "route": G2_ROUTE,
            "source_sample_profile": G2_PROFILE,
            "subdivision": SUBDIVISION,
            "guard_rule": "for every subcell, try the assigned/sample edge-axis family, then local edge axes ordered by center overlap, accepting the first axis with positive signed projection-component margin and stable support extrema",
            "displacement_safety_factor": g1.ray_guard.DISPLACEMENT_SAFETY_FACTOR,
        },
        "summary_metrics": aggregate_summary(target_reports),
        "target_reports": target_reports,
        "limitations": [
            "This report certifies only the 371 G2 edge-axis-switch bounded cells from the guard-plan report.",
            "The local-edge-axis fallback is used only after the assigned/sample edge-axis family fails on a subcell.",
            "The report does not certify the 180 G3 hybrid edge/face switch cells or the 22 G4 nonseparating-axis cells.",
            "This is finite numeric support-component evidence, not a symbolic formula derivation.",
            "This does not certify theta=0, the full continuous 3-parameter component, physical hinge thickness, offsets, CAD, mesh export, or printability.",
        ],
    }


def main() -> int:
    report = build_report()
    g1.lib.write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "summary_metrics": report["summary_metrics"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
