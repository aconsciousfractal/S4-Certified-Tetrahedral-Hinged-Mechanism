"""G3 hybrid edge/face guard for S4 bounded-cell edge-branch cells.

The bounded-cell edge-branch guard plan assigns 180 cells to route G3:

- TREE_007 P2-P3: 90 cells
- TREE_021 P0-P2: 90 cells

These cells have an assigned edge axis that remains separating at all sampled
cell center/vertices, but sampled best axes include face-normal or mixed
switches. This audit tries the G2 multi-edge-axis support-component guard first
and uses the bounded-cell face-normal formula guard only on subcells still
uncovered by edge axes.

This certifies only the G3 route. It does not cover G4 nonseparating-axis cells.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_edge_branch_g3_hybrid_guard_report.json"
SOURCE_CLASSIFIER_REPORT = "bounded_cell_edge_branch_stability_classifier_report.json"
SOURCE_GUARD_PLAN_REPORT = "bounded_cell_edge_branch_guard_plan_report.json"
SOURCE_G1_REPORT = "bounded_cell_edge_branch_g1_fixed_axis_guard_report.json"
SOURCE_G2_REPORT = "bounded_cell_edge_branch_g2_multi_axis_guard_report.json"
SOURCE_FACE_NORMAL_REPORT = "bounded_cell_face_normal_formula_guard_report.json"
G3_PROFILE = "assigned_separating_face_normal_or_mixed_switch"
G3_ROUTE = "G3_hybrid_edge_face_axis_switch_guard"
SUBDIVISION = {
    "theta_splits": 16,
    "radial_splits": 2,
    "direction_splits": 2,
}
MAX_STORED_EXAMPLES = 36

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_bounded_cell_edge_branch_g1_fixed_axis_guard as g1  # noqa: E402
import audit_historical_s4_bounded_cell_edge_branch_g2_multi_axis_guard as g2  # noqa: E402
import audit_historical_s4_p0p2_face_normal_formula_guard as tree021_face  # noqa: E402
import audit_historical_s4_tree007_p2p3_face_normal_formula_guard as tree007_face  # noqa: E402

RESULTS_DIR = g1.RESULTS_DIR

TARGET_CONFIG = {
    "TREE_007": {
        "formula_module": tree007_face,
        "expected_face_axes": {tree007_face.LEFT_FACE_AXIS, tree007_face.RIGHT_FACE_AXIS},
        "source_formula_report": "tree007_p2p3_face_normal_formula_guard_report.json",
    },
    "TREE_021": {
        "formula_module": tree021_face,
        "expected_face_axes": {tree021_face.LEFT_FACE_AXIS, tree021_face.RIGHT_FACE_AXIS},
        "source_formula_report": "p0p2_face_normal_formula_guard_report.json",
    },
}


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def g3_records_by_tree(classifier_report: dict) -> dict[str, list[dict]]:
    output = {}
    for target_report in classifier_report["target_reports"]:
        tree_id = target_report["target"]["tree_id"]
        output[tree_id] = [
            record
            for record in target_report["cell_reports"]
            if record["sample_profile"] == G3_PROFILE
        ]
    return output


def subcell_interval_lists(tree: dict, signs_by_hinge: dict[str, int], subcell: dict) -> dict[str, list[float]]:
    intervals = g1.subcell_coordinate_intervals(tree, signs_by_hinge, subcell)
    return {
        hinge_id: [float(record["minimum_degrees"]), float(record["maximum_degrees"])]
        for hinge_id, record in intervals.items()
    }


def face_candidate_axes(tree_id: str, record: dict) -> list[str]:
    expected = TARGET_CONFIG[tree_id]["expected_face_axes"]
    axes = []
    for axis_name in record["best_axis_name_counts"]:
        if axis_name in expected and axis_name not in axes:
            axes.append(axis_name)
    for axis_name in sorted(expected):
        if axis_name not in axes:
            axes.append(axis_name)
    return axes


def compact_face_attempt(axis_name: str, bounds: dict, subcell: dict, rank: int) -> dict:
    return {
        "certified": bool(bounds.get("formula_sign_certified") and bounds.get("support_sign_certified")),
        "failure_reason": None
        if bool(bounds.get("formula_sign_certified") and bounds.get("support_sign_certified"))
        else "face_normal_formula_or_support_sign_failed",
        "candidate_axis_name": axis_name,
        "candidate_stage": "face_normal_formula_fallback",
        "candidate_rank": rank,
        "subcell": g1.compact_subcell(subcell),
        "active_hinge": bounds.get("active_hinge"),
        "raw_gap_lower_bound": bounds.get("raw_gap_lower_bound"),
        "minimum_support_lower_bound": bounds.get("minimum_support_lower_bound"),
        "formula_sign_certified": bool(bounds.get("formula_sign_certified")),
        "support_sign_certified": bool(bounds.get("support_sign_certified")),
    }


def evaluate_subcell_with_hybrid_candidates(
    case: dict,
    tree: dict,
    tree_id: str,
    signs_by_hinge: dict[str, int],
    indices: dict[str, dict[str, int]],
    labels_by_piece: dict[str, list[str]],
    paths_by_piece: dict[str, list[dict]],
    record: dict,
    subcell: dict,
) -> dict:
    edge = g2.evaluate_subcell_with_candidates(
        case,
        tree,
        signs_by_hinge,
        indices,
        labels_by_piece,
        paths_by_piece,
        record,
        subcell,
    )
    if edge["certified"]:
        return {
            "certified": True,
            "guard_family": "edge_axis_support_component",
            "accepted": edge["accepted"],
            "edge_attempt_count": edge["attempt_count"],
            "face_attempt_count": 0,
        }

    intervals = subcell_interval_lists(tree, signs_by_hinge, subcell)
    formula_module = TARGET_CONFIG[tree_id]["formula_module"]
    face_failures = []
    for rank, axis_name in enumerate(face_candidate_axes(tree_id, record), start=1):
        bounds = formula_module.formula_lower_bounds(axis_name, intervals)
        attempt = compact_face_attempt(axis_name, bounds, subcell, rank)
        if attempt["certified"]:
            return {
                "certified": True,
                "guard_family": "face_normal_formula",
                "accepted": attempt,
                "edge_attempt_count": edge["attempt_count"],
                "face_attempt_count": rank,
                "edge_best_failed_attempt": edge["best_failed_attempt"],
            }
        face_failures.append(attempt)

    return {
        "certified": False,
        "guard_family": None,
        "accepted": None,
        "edge_attempt_count": edge["attempt_count"],
        "face_attempt_count": len(face_failures),
        "edge_best_failed_attempt": edge["best_failed_attempt"],
        "face_failed_attempts": face_failures,
    }


def compact_cell_record(tree_id: str, record: dict, cell: dict, subcell_reports: list[dict]) -> dict:
    accepted = [item["accepted"] for item in subcell_reports if item["accepted"] is not None]
    failed = [item for item in subcell_reports if not item["certified"]]
    stage_counts = Counter(item["accepted"]["candidate_stage"] for item in subcell_reports if item["accepted"] is not None)
    accepted_axis_counts = Counter(item["accepted"]["candidate_axis_name"] for item in subcell_reports if item["accepted"] is not None)
    edge_margins = [
        float(item["signed_component_margin"])
        for item in accepted
        if item.get("signed_component_margin") is not None
    ]
    edge_stability_margins = [
        float(item["minimum_stability_margin"])
        for item in accepted
        if item.get("minimum_stability_margin") is not None
    ]
    face_raw_bounds = [
        float(item["raw_gap_lower_bound"])
        for item in accepted
        if item.get("raw_gap_lower_bound") is not None
    ]
    face_support_bounds = [
        float(item["minimum_support_lower_bound"])
        for item in accepted
        if item.get("minimum_support_lower_bound") is not None
    ]
    edge_attempt_counts = Counter(item["edge_attempt_count"] for item in subcell_reports)
    face_attempt_counts = Counter(item["face_attempt_count"] for item in subcell_reports)
    worst_edge = min(
        [item for item in accepted if item.get("signed_component_margin") is not None],
        key=lambda item: float(item["signed_component_margin"]),
        default=None,
    )
    worst_face = min(
        [item for item in accepted if item.get("minimum_support_lower_bound") is not None],
        key=lambda item: float(item["minimum_support_lower_bound"]),
        default=None,
    )
    return {
        "cell_id": record["cell_id"],
        "tree_id": tree_id,
        "pair": record["pair"],
        "kind": cell["kind"],
        "route": G3_ROUTE,
        "assigned_axis_name": record["assigned_axis_name"],
        "source_candidate_axes": g2.sample_candidate_axes(record),
        "face_candidate_axes": face_candidate_axes(tree_id, record),
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
        "face_normal_formula_fallback_subcell_count": stage_counts.get("face_normal_formula_fallback", 0),
        "minimum_edge_signed_component_margin": g1.rounded(min(edge_margins) if edge_margins else None, 15),
        "minimum_edge_signed_stability_margin": g1.rounded(min(edge_stability_margins) if edge_stability_margins else None, 15),
        "minimum_face_raw_gap_lower_bound": g1.rounded(min(face_raw_bounds) if face_raw_bounds else None, 15),
        "minimum_face_support_lower_bound": g1.rounded(min(face_support_bounds) if face_support_bounds else None, 15),
        "accepted_axis_counts": dict(accepted_axis_counts.most_common()),
        "edge_attempt_count_distribution": dict(edge_attempt_counts.most_common()),
        "face_attempt_count_distribution": dict(face_attempt_counts.most_common()),
        "worst_edge_subcell": worst_edge,
        "worst_face_subcell": worst_face,
        "failure_reason_counts": dict(Counter(item.get("edge_best_failed_attempt", {}).get("failure_reason") for item in failed).most_common()),
    }


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
    assigned_axis_counts = Counter()
    accepted_axis_counts = Counter()
    stage_counts = Counter()
    kind_counts = Counter()
    edge_margins = []
    edge_stability_margins = []
    face_raw_bounds = []
    face_support_bounds = []

    for record in records:
        cell = cell_by_id[record["cell_id"]]
        subcell_reports = [
            evaluate_subcell_with_hybrid_candidates(
                case,
                tree,
                tree_id,
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

        assigned_axis_counts[record["assigned_axis_name"]] += 1
        accepted_axis_counts.update(compact["accepted_axis_counts"])
        stage_counts["sample_candidate_family"] += compact["sample_candidate_family_subcell_count"]
        stage_counts["local_edge_axis_fallback"] += compact["local_edge_axis_fallback_subcell_count"]
        stage_counts["face_normal_formula_fallback"] += compact["face_normal_formula_fallback_subcell_count"]
        kind_counts[cell["kind"]] += 1
        if compact["face_normal_formula_fallback_subcell_count"] > 0:
            add_example(examples["cells_needing_face_normal_formula_fallback"], compact)
        elif compact["local_edge_axis_fallback_subcell_count"] > 0:
            add_example(examples["cells_needing_local_edge_axis_fallback"], compact)
        else:
            add_example(examples["cells_certified_by_sample_candidate_family"], compact)
        if not compact["cell_certified"]:
            add_example(examples["uncovered_cells"], compact)
        if compact["minimum_edge_signed_component_margin"] is not None:
            edge_margins.append(float(compact["minimum_edge_signed_component_margin"]))
        if compact["minimum_edge_signed_stability_margin"] is not None:
            edge_stability_margins.append(float(compact["minimum_edge_signed_stability_margin"]))
        if compact["minimum_face_raw_gap_lower_bound"] is not None:
            face_raw_bounds.append(float(compact["minimum_face_raw_gap_lower_bound"]))
        if compact["minimum_face_support_lower_bound"] is not None:
            face_support_bounds.append(float(compact["minimum_face_support_lower_bound"]))

    certified_cells = sum(1 for item in cell_reports if item["cell_certified"])
    total_subcells = sum(item["subcell_count"] for item in cell_reports)
    certified_subcells = sum(item["certified_subcell_count"] for item in cell_reports)
    face_fallback_cells = sum(1 for item in cell_reports if item["face_normal_formula_fallback_subcell_count"] > 0)
    local_edge_fallback_cells = sum(1 for item in cell_reports if item["local_edge_axis_fallback_subcell_count"] > 0)
    return {
        "target": {
            "tree_id": tree_id,
            "pair": records[0]["pair"] if records else None,
            "route": G3_ROUTE,
            "source_sample_profile": G3_PROFILE,
            "source_formula_report": TARGET_CONFIG[tree_id]["source_formula_report"],
        },
        "summary_metrics": {
            "input_g3_cell_count": len(records),
            "g3_certified_cell_count": certified_cells,
            "g3_uncovered_cell_count": len(records) - certified_cells,
            "g3_all_input_cells_certified": certified_cells == len(records),
            "subcell_count": total_subcells,
            "certified_subcell_count": certified_subcells,
            "failed_subcell_count": total_subcells - certified_subcells,
            "sample_candidate_family_subcell_count": stage_counts.get("sample_candidate_family", 0),
            "local_edge_axis_fallback_subcell_count": stage_counts.get("local_edge_axis_fallback", 0),
            "face_normal_formula_fallback_subcell_count": stage_counts.get("face_normal_formula_fallback", 0),
            "cells_needing_local_edge_axis_fallback": local_edge_fallback_cells,
            "cells_needing_face_normal_formula_fallback": face_fallback_cells,
            "minimum_edge_signed_component_margin": g1.rounded(min(edge_margins) if edge_margins else None, 15),
            "minimum_edge_signed_stability_margin": g1.rounded(min(edge_stability_margins) if edge_stability_margins else None, 15),
            "minimum_face_raw_gap_lower_bound": g1.rounded(min(face_raw_bounds) if face_raw_bounds else None, 15),
            "minimum_face_support_lower_bound": g1.rounded(min(face_support_bounds) if face_support_bounds else None, 15),
        },
        "breakdown": {
            "assigned_axis_counts": dict(assigned_axis_counts.most_common()),
            "accepted_axis_counts": dict(accepted_axis_counts.most_common()),
            "coverage_stage_counts_by_subcell": dict(stage_counts.most_common()),
            "cell_kind_counts": dict(kind_counts.most_common()),
            "edge_signed_component_margin_quantiles": g1.quantiles(edge_margins),
            "edge_signed_stability_margin_quantiles": g1.quantiles(edge_stability_margins),
            "face_raw_gap_lower_bound_quantiles": g1.quantiles(face_raw_bounds),
            "face_support_lower_bound_quantiles": g1.quantiles(face_support_bounds),
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
    kind_counts = Counter()
    edge_margins = []
    edge_stability_margins = []
    face_raw_bounds = []
    face_support_bounds = []
    tree_counts = {}
    tree_certified_counts = {}
    tree_face_fallback_counts = {}
    for report in target_reports:
        tree_id = report["target"]["tree_id"]
        tree_counts[tree_id] = report["summary_metrics"]["input_g3_cell_count"]
        tree_certified_counts[tree_id] = report["summary_metrics"]["g3_certified_cell_count"]
        tree_face_fallback_counts[tree_id] = report["summary_metrics"]["cells_needing_face_normal_formula_fallback"]
        accepted_axis_counts.update(report["breakdown"]["accepted_axis_counts"])
        assigned_axis_counts.update(report["breakdown"]["assigned_axis_counts"])
        stage_counts.update(report["breakdown"]["coverage_stage_counts_by_subcell"])
        kind_counts.update(report["breakdown"]["cell_kind_counts"])
        edge_margins.extend(
            float(cell["minimum_edge_signed_component_margin"])
            for cell in report["cell_reports"]
            if cell["minimum_edge_signed_component_margin"] is not None
        )
        edge_stability_margins.extend(
            float(cell["minimum_edge_signed_stability_margin"])
            for cell in report["cell_reports"]
            if cell["minimum_edge_signed_stability_margin"] is not None
        )
        face_raw_bounds.extend(
            float(cell["minimum_face_raw_gap_lower_bound"])
            for cell in report["cell_reports"]
            if cell["minimum_face_raw_gap_lower_bound"] is not None
        )
        face_support_bounds.extend(
            float(cell["minimum_face_support_lower_bound"])
            for cell in report["cell_reports"]
            if cell["minimum_face_support_lower_bound"] is not None
        )

    input_cells = total("input_g3_cell_count")
    certified_cells = total("g3_certified_cell_count")
    subcells = total("subcell_count")
    certified_subcells = total("certified_subcell_count")
    return {
        "target_count": len(target_reports),
        "input_g3_cell_count": input_cells,
        "g3_certified_cell_count": certified_cells,
        "g3_uncovered_cell_count": input_cells - certified_cells,
        "g3_all_input_cells_certified": certified_cells == input_cells,
        "subdivision": SUBDIVISION,
        "subcell_count": subcells,
        "certified_subcell_count": certified_subcells,
        "failed_subcell_count": subcells - certified_subcells,
        "all_subcells_certified": certified_subcells == subcells,
        "sample_candidate_family_subcell_count": total("sample_candidate_family_subcell_count"),
        "local_edge_axis_fallback_subcell_count": total("local_edge_axis_fallback_subcell_count"),
        "face_normal_formula_fallback_subcell_count": total("face_normal_formula_fallback_subcell_count"),
        "cells_needing_local_edge_axis_fallback": total("cells_needing_local_edge_axis_fallback"),
        "cells_needing_face_normal_formula_fallback": total("cells_needing_face_normal_formula_fallback"),
        "tree_counts": tree_counts,
        "tree_certified_cell_counts": tree_certified_counts,
        "tree_face_fallback_cell_counts": tree_face_fallback_counts,
        "assigned_axis_counts": dict(assigned_axis_counts.most_common()),
        "accepted_axis_counts": dict(accepted_axis_counts.most_common()),
        "coverage_stage_counts_by_subcell": dict(stage_counts.most_common()),
        "cell_kind_counts": dict(kind_counts.most_common()),
        "minimum_edge_signed_component_margin": g1.rounded(min(edge_margins) if edge_margins else None, 15),
        "minimum_edge_signed_stability_margin": g1.rounded(min(edge_stability_margins) if edge_stability_margins else None, 15),
        "minimum_face_raw_gap_lower_bound": g1.rounded(min(face_raw_bounds) if face_raw_bounds else None, 15),
        "minimum_face_support_lower_bound": g1.rounded(min(face_support_bounds) if face_support_bounds else None, 15),
    }


def build_report() -> dict:
    g1.SUBDIVISION.clear()
    g1.SUBDIVISION.update(SUBDIVISION)

    classifier_report = g1.load_json(RESULTS_DIR / SOURCE_CLASSIFIER_REPORT)
    guard_plan = g1.load_json(RESULTS_DIR / SOURCE_GUARD_PLAN_REPORT)
    expected_g3 = int(guard_plan["summary_metrics"]["route_counts"][G3_ROUTE])
    records_by_tree = g3_records_by_tree(classifier_report)
    input_g3 = sum(len(records) for records in records_by_tree.values())
    if input_g3 != expected_g3:
        raise AssertionError(f"Expected {expected_g3} G3 cells from guard plan, found {input_g3}")

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
        "status": "bounded_cell_edge_branch_g3_hybrid_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_CLASSIFIER_REPORT}",
            f"results/{CASE_ID}/{SOURCE_GUARD_PLAN_REPORT}",
            f"results/{CASE_ID}/{SOURCE_G1_REPORT}",
            f"results/{CASE_ID}/{SOURCE_G2_REPORT}",
            f"results/{CASE_ID}/{SOURCE_FACE_NORMAL_REPORT}",
            f"results/{CASE_ID}/tree007_p2p3_face_normal_formula_guard_report.json",
            f"results/{CASE_ID}/p0p2_face_normal_formula_guard_report.json",
        ],
        "target": {
            "description": "G3 hybrid edge/face switch guard for bounded-cell edge-branch records",
            "route": G3_ROUTE,
            "source_sample_profile": G3_PROFILE,
            "subdivision": SUBDIVISION,
            "guard_rule": "for every subcell, try the G2 multi-edge-axis support-component guard first; if edge axes fail, apply the target face-normal formula lower-bound guard over the subcell hinge-coordinate intervals",
            "displacement_safety_factor": g1.ray_guard.DISPLACEMENT_SAFETY_FACTOR,
        },
        "summary_metrics": aggregate_summary(target_reports),
        "target_reports": target_reports,
        "limitations": [
            "This report certifies only the 180 G3 hybrid edge/face switch bounded cells from the guard-plan report.",
            "Face-normal formulas are used only after edge-axis support-component candidates fail on a subcell.",
            "The report does not certify the 22 G4 nonseparating-axis cells.",
            "This is finite numeric support-component and formula evidence, not a symbolic derivation.",
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
