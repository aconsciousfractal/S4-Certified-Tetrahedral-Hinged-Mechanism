"""First-pass bounded cell guard for S4 representative component cells.

This audit targets the 768 all-vertices-free cylindrical wedge cells per
representative enumerated by the bounded cell-cover protocol spec.

It applies a conservative full-cell SAT displacement guard at the cell center
and a selected-hinge orientation guard for exact hinge contacts. Residual
contact pairs that remain uncovered are assigned explicit fallback classes from
the existing residual formula/guard library. Those fallback classes are not
applied here; they define the next local closure work.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_guard_first_pass_report.json"
SOURCE_COMPONENT_REPORT = "two_class_component_search_report.json"
SOURCE_PROTOCOL_REPORT = "bounded_cell_cover_protocol_spec_report.json"
TARGET_TREE_IDS = ["TREE_007", "TREE_021"]
MAX_STORED_CELLS = 80
ANGLE_TOLERANCE_DEGREES = 1.0e-10

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def direction_angle(direction_index: int) -> float:
    return 2.0 * math.pi * float(direction_index) / float(comp.DIRECTION_COUNT)


def sector_candidate_angles(direction_index: int, coefficient_cos: float, coefficient_sin: float) -> list[float]:
    start = direction_angle(direction_index)
    end = start + (2.0 * math.pi / float(comp.DIRECTION_COUNT))
    candidates = [start, end]
    amplitude = math.hypot(coefficient_cos, coefficient_sin)
    if amplitude <= lib.TOL:
        return candidates
    phase = math.atan2(coefficient_sin, coefficient_cos)
    for base in [phase, phase + math.pi]:
        for offset in range(-2, 4):
            candidate = base + 2.0 * math.pi * offset
            if start - 1.0e-12 <= candidate <= end + 1.0e-12:
                candidates.append(candidate)
    return sorted(set(round(value, 15) for value in candidates))


def offset_coordinate_range(
    e1_value: float,
    e2_value: float,
    radius_interval: list[float],
    direction_index: int,
) -> tuple[float, float]:
    candidates = sector_candidate_angles(direction_index, e1_value, e2_value)
    direction_values = [
        e1_value * math.cos(angle) + e2_value * math.sin(angle)
        for angle in candidates
    ]
    min_direction = min(direction_values)
    max_direction = max(direction_values)
    radius_left, radius_right = [float(value) for value in radius_interval]

    if min_direction < 0.0:
        offset_min = radius_right * min_direction
    else:
        offset_min = radius_left * min_direction
    if max_direction > 0.0:
        offset_max = radius_right * max_direction
    else:
        offset_max = radius_left * max_direction
    return float(offset_min), float(offset_max)


def theta_coordinate_range(sign: float, theta_interval: list[float]) -> tuple[float, float]:
    left, right = [float(value) for value in theta_interval]
    if sign >= 0.0:
        return left, right
    return -right, -left


def center_angle_vector(tree: dict, signs_by_hinge: dict[str, int], cell: dict) -> np.ndarray:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    e1, e2 = reps.transverse_basis(sign_vec)
    theta_left, theta_right = [float(value) for value in cell["theta_interval_degrees"]]
    radius_left, radius_right = [float(value) for value in cell["radial_interval_degrees"]]
    theta_center = (theta_left + theta_right) / 2.0
    radius_center = (radius_left + radius_right) / 2.0
    phi_center = direction_angle(int(cell["direction_index"])) + math.pi / float(comp.DIRECTION_COUNT)
    return sign_vec * theta_center + radius_center * (
        math.cos(phi_center) * e1 + math.sin(phi_center) * e2
    )


def angle_coordinate_intervals(tree: dict, signs_by_hinge: dict[str, int], cell: dict) -> dict[str, dict]:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    e1, e2 = reps.transverse_basis(sign_vec)
    center_vector = center_angle_vector(tree, signs_by_hinge, cell)
    output = {}
    for index, hinge_id in enumerate(tree["hinge_ids"]):
        theta_min, theta_max = theta_coordinate_range(sign_vec[index], cell["theta_interval_degrees"])
        offset_min, offset_max = offset_coordinate_range(
            float(e1[index]),
            float(e2[index]),
            cell["radial_interval_degrees"],
            int(cell["direction_index"]),
        )
        minimum = theta_min + offset_min
        maximum = theta_max + offset_max
        center = float(center_vector[index])
        max_deviation = max(abs(minimum - center), abs(maximum - center))
        output[hinge_id] = {
            "minimum_degrees": round(minimum, 12),
            "maximum_degrees": round(maximum, 12),
            "center_degrees": round(center, 12),
            "max_deviation_from_center_degrees": round(max_deviation, 12),
        }
    return output


def all_free_cells_for_tree(source_audit: dict, cells: list[dict]) -> list[dict]:
    free_ids = protocol.free_node_ids(source_audit)
    return [
        cell
        for cell in cells
        if all(node_id in free_ids for node_id in cell["vertex_node_ids"])
    ]


def selected_hinge_by_pair(case: dict, tree: dict) -> dict[tuple[str, str], dict]:
    output = {}
    for hinge_id in tree["hinge_ids"]:
        hinge = case["hinge_by_id"][hinge_id]
        output[tuple(sorted(hinge["pieces"]))] = hinge
    return output


def piece_displacement_bounds_for_cell(
    case: dict,
    tree: dict,
    transforms: dict[str, dict[str, np.ndarray]],
    transformed_pieces: dict[str, list[np.ndarray]],
    max_deviation_by_hinge: dict[str, float],
    paths_by_piece: dict[str, list[dict]],
) -> dict[str, float]:
    bounds = {}
    for piece_id, vertices in transformed_pieces.items():
        displacement = 0.0
        for hinge in paths_by_piece[piece_id]:
            hinge_id = hinge["hinge_id"]
            deviation_degrees = abs(float(max_deviation_by_hinge[hinge_id]))
            if deviation_degrees <= ANGLE_TOLERANCE_DEGREES:
                continue
            axis_side = hinge["pieces"][0]
            transform = transforms[axis_side]
            axis_a = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][0]])
            axis_b = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][1]])
            max_distance = max(ray_guard.point_line_distance(vertex, axis_a, axis_b) for vertex in vertices)
            displacement += 2.0 * max_distance * math.sin(math.radians(deviation_degrees) / 2.0)
        bounds[piece_id] = ray_guard.DISPLACEMENT_SAFETY_FACTOR * displacement
    return bounds


def selected_hinge_orientation_certificate(
    hinge: dict,
    coordinate_intervals: dict[str, dict],
    center_sample_status: str,
) -> dict:
    interval = coordinate_intervals[hinge["hinge_id"]]
    minimum = float(interval["minimum_degrees"])
    maximum = float(interval["maximum_degrees"])
    excludes_zero = minimum > 0.0 or maximum < 0.0
    within_half_turn = max(abs(minimum), abs(maximum)) < 180.0
    certified = center_sample_status == "collision_free" and excludes_zero and within_half_turn
    return {
        "method": "selected_hinge_contact_orientation_on_bounded_cell",
        "certified": certified,
        "hinge_id": hinge["hinge_id"],
        "signed_angle_interval_degrees": [round(minimum, 12), round(maximum, 12)],
        "angle_interval_excludes_zero": excludes_zero,
        "angle_interval_within_open_half_turn": within_half_turn,
        "center_sample_status": center_sample_status,
    }


def fallback_classes_for_pair(tree_id: str, pair: tuple[str, str], role: str) -> list[str]:
    pair_key = "-".join(pair)
    if role == "selected_hinge_contact":
        return ["selected_hinge_orientation_subdivision_if_interval_touches_zero"]
    if role == "residual_shared_edge":
        return [f"{tree_id.replace('_', '').lower()}_shared_edge_common_edge_guard"]
    if tree_id == "TREE_007" and pair_key == "P2-P3" and role == "residual_shared_face":
        return [
            "tree007_p2p3_edge_branch_workflow",
            "tree007_p2p3_face_normal_formula_guard",
        ]
    if tree_id == "TREE_021" and pair_key == "P0-P2" and role == "residual_shared_face":
        return [
            "tree021_p0p2_edge_branch_workflow",
            "tree021_p0p2_face_normal_formula_guard",
        ]
    if role.startswith("residual_"):
        return ["residual_formula_library_unmapped_for_this_cell_pair"]
    return ["adaptive_subdivision_or_tighter_clearance_guard"]


def compact_pair_record(record: dict) -> dict:
    return {
        "pair": record["pair"],
        "role": record["role"],
        "first_pass_covered": record["first_pass_covered"],
        "coverage_method": record["coverage_method"],
        "center_axis_overlap": round(record["center_axis_overlap"], 12),
        "guard_bound": round(record["guard_bound"], 12),
        "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
        "guard_margin": round(record["guard_margin"], 12),
        "fallback_classes": record["fallback_classes"],
        "orientation_certificate": record["orientation_certificate"],
    }


def compact_cell_record(cell: dict, pair_records: list[dict]) -> dict:
    return {
        "cell_id": cell["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "uncovered_pair_records": [
            compact_pair_record(record)
            for record in pair_records
            if not record["first_pass_covered"]
        ],
    }


def audit_cell(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    cell: dict,
    paths_by_piece: dict[str, list[dict]],
    contacts_by_pair: dict[tuple[str, str], dict],
    hinge_by_pair: dict[tuple[str, str], dict],
) -> dict:
    center_vector = center_angle_vector(tree, signs_by_hinge, cell)
    center_degrees = reps.degrees_from_vector(tree, center_vector)
    coordinate_intervals = angle_coordinate_intervals(tree, signs_by_hinge, cell)
    max_deviation_by_hinge = {
        hinge_id: float(record["max_deviation_from_center_degrees"])
        for hinge_id, record in coordinate_intervals.items()
    }

    transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    center_sample = lib.collision_report(transformed)
    displacement_bounds = piece_displacement_bounds_for_cell(
        case,
        tree,
        transforms,
        transformed,
        max_deviation_by_hinge,
        paths_by_piece,
    )

    pair_records = []
    for left, right in itertools.combinations(sorted(transformed), 2):
        pair = tuple(sorted((left, right)))
        role = ray_guard.pair_role(case, tree, pair, contacts_by_pair)
        best = ray_guard.best_center_separating_axis(transformed[left], transformed[right])
        guard_bound = displacement_bounds[left] + displacement_bounds[right] + ray_guard.SAT_TOLERANCE
        post_guard = best["center_axis_overlap"] + guard_bound
        guard_margin = ray_guard.SAT_TOLERANCE - post_guard
        clearance_certified = center_sample["status"] == "collision_free" and post_guard <= ray_guard.SAT_TOLERANCE
        orientation = None
        orientation_certified = False
        if role == "selected_hinge_contact":
            orientation = selected_hinge_orientation_certificate(
                hinge_by_pair[pair],
                coordinate_intervals,
                center_sample["status"],
            )
            orientation_certified = bool(orientation["certified"])

        first_pass_covered = bool(clearance_certified or orientation_certified)
        fallback_classes = [] if first_pass_covered else fallback_classes_for_pair(tree["tree_id"], pair, role)
        if clearance_certified:
            coverage_method = "clearance_full_cell_guard"
        elif orientation_certified:
            coverage_method = "selected_hinge_orientation_full_cell"
        elif role.startswith("residual_"):
            coverage_method = "residual_formula_fallback_required"
        else:
            coverage_method = "first_pass_uncovered"

        pair_records.append(
            {
                "pair": list(pair),
                "role": role,
                "first_pass_covered": first_pass_covered,
                "coverage_method": coverage_method,
                "center_axis_overlap": best["center_axis_overlap"],
                "guard_bound": guard_bound,
                "post_guard_overlap_bound": post_guard,
                "guard_margin": guard_margin,
                "fallback_classes": fallback_classes,
                "orientation_certificate": orientation,
            }
        )

    covered_count = sum(1 for record in pair_records if record["first_pass_covered"])
    fallback_classes = Counter(
        fallback
        for record in pair_records
        if not record["first_pass_covered"]
        for fallback in record["fallback_classes"]
    )
    return {
        "cell_id": cell["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "center_angle_degrees_by_hinge": {key: round(value, 12) for key, value in center_degrees.items()},
        "angle_coordinate_intervals_by_hinge": coordinate_intervals,
        "center_sample_status": center_sample["status"],
        "center_sample_collisions": center_sample["collisions"],
        "center_sample_minimum_axis_overlap_proxy": center_sample["minimum_axis_overlap_proxy"],
        "pair_count": len(pair_records),
        "first_pass_covered_pair_count": covered_count,
        "first_pass_uncovered_pair_count": len(pair_records) - covered_count,
        "first_pass_fully_covered": covered_count == len(pair_records),
        "fallback_class_counts": dict(sorted(fallback_classes.items())),
        "worst_pair_guard_margin": round(min(record["guard_margin"] for record in pair_records), 12),
        "pair_records": pair_records,
    }


def summarize_pairs(cells: list[dict]) -> list[dict]:
    summary: dict[tuple[str, str], dict] = {}
    for cell in cells:
        for record in cell["pair_records"]:
            pair = tuple(record["pair"])
            item = summary.setdefault(
                pair,
                {
                    "pair": list(pair),
                    "role": record["role"],
                    "cell_count": 0,
                    "covered_cell_count": 0,
                    "uncovered_cell_count": 0,
                    "coverage_method_counts": Counter(),
                    "fallback_class_counts": Counter(),
                    "minimum_guard_margin": None,
                    "first_uncovered_cell": None,
                },
            )
            item["cell_count"] += 1
            item["coverage_method_counts"][record["coverage_method"]] += 1
            if record["first_pass_covered"]:
                item["covered_cell_count"] += 1
            else:
                item["uncovered_cell_count"] += 1
                for fallback in record["fallback_classes"]:
                    item["fallback_class_counts"][fallback] += 1
                if item["first_uncovered_cell"] is None:
                    item["first_uncovered_cell"] = {
                        "cell_id": cell["cell_id"],
                        "theta_interval_degrees": cell["theta_interval_degrees"],
                        "radial_interval_degrees": cell["radial_interval_degrees"],
                        "direction_sector": cell["direction_sector"],
                        "guard_margin": round(record["guard_margin"], 12),
                        "fallback_classes": record["fallback_classes"],
                    }
            margin = float(record["guard_margin"])
            current = item["minimum_guard_margin"]
            item["minimum_guard_margin"] = margin if current is None else min(current, margin)

    output = []
    for item in summary.values():
        output.append(
            {
                "pair": item["pair"],
                "role": item["role"],
                "cell_count": item["cell_count"],
                "covered_cell_count": item["covered_cell_count"],
                "uncovered_cell_count": item["uncovered_cell_count"],
                "coverage_method_counts": dict(sorted(item["coverage_method_counts"].items())),
                "fallback_class_counts": dict(sorted(item["fallback_class_counts"].items())),
                "minimum_guard_margin": round(float(item["minimum_guard_margin"]), 12),
                "first_uncovered_cell": item["first_uncovered_cell"],
            }
        )
    return sorted(output, key=lambda item: item["pair"])


def audit_tree(case: dict, source_audit: dict, signs_by_tree: dict[str, dict[str, int]], all_cells: list[dict]) -> dict:
    tree_id = source_audit["tree_id"]
    tree = comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    target_cells = all_free_cells_for_tree(source_audit, all_cells)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    contacts_by_pair = ray_guard.contact_by_pair(case)
    hinge_by_pair = selected_hinge_by_pair(case, tree)
    audited_cells = [
        audit_cell(case, tree, signs, cell, paths_by_piece, contacts_by_pair, hinge_by_pair)
        for cell in target_cells
    ]

    coverage_methods = Counter(
        record["coverage_method"]
        for cell in audited_cells
        for record in cell["pair_records"]
    )
    uncovered_by_role = Counter(
        record["role"]
        for cell in audited_cells
        for record in cell["pair_records"]
        if not record["first_pass_covered"]
    )
    fallback_classes = Counter(
        fallback
        for cell in audited_cells
        for record in cell["pair_records"]
        if not record["first_pass_covered"]
        for fallback in record["fallback_classes"]
    )
    failed_cells = [cell for cell in audited_cells if not cell["first_pass_fully_covered"]]
    low_margin_cells = sorted(audited_cells, key=lambda item: item["worst_pair_guard_margin"])[:MAX_STORED_CELLS]
    pair_summary = summarize_pairs(audited_cells)

    return {
        "tree_id": tree_id,
        "class_id": source_audit["class_id"],
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs,
        "status": "bounded_cell_guard_first_pass_completed",
        "cell_guard_protocol": {
            "target_cells": "all-vertices-free cells from bounded_cell_cover_protocol_spec_report.json",
            "center_sample": "cylindrical wedge center in theta/radius/direction coordinates",
            "coordinate_interval_rule": "exact theta range plus conservative radial-sector extrema per hinge coordinate",
            "clearance_rule": "center separating-axis overlap plus full-cell local angular displacement bound must stay <= SAT tolerance",
            "selected_hinge_rule": "selected hinge angle interval must exclude zero and stay within an open half-turn",
            "residual_formula_policy": "existing residual formulas are assigned as fallback classes only; they are not applied in this first-pass guard",
            "sat_tolerance": ray_guard.SAT_TOLERANCE,
            "displacement_safety_factor": ray_guard.DISPLACEMENT_SAFETY_FACTOR,
        },
        "summary_metrics": {
            "candidate_cell_count": len(audited_cells),
            "center_sample_collision_free_cell_count": sum(
                1 for cell in audited_cells if cell["center_sample_status"] == "collision_free"
            ),
            "first_pass_fully_covered_cell_count": len(audited_cells) - len(failed_cells),
            "first_pass_uncovered_cell_count": len(failed_cells),
            "total_pair_cell_count": sum(cell["pair_count"] for cell in audited_cells),
            "first_pass_covered_pair_cell_count": sum(cell["first_pass_covered_pair_count"] for cell in audited_cells),
            "first_pass_uncovered_pair_cell_count": sum(cell["first_pass_uncovered_pair_count"] for cell in audited_cells),
            "minimum_worst_pair_guard_margin": min(cell["worst_pair_guard_margin"] for cell in audited_cells),
            "maximum_hinge_coordinate_deviation_degrees": max(
                interval["max_deviation_from_center_degrees"]
                for cell in audited_cells
                for interval in cell["angle_coordinate_intervals_by_hinge"].values()
            ),
            "bounded_cell_cover_certificate_completed": len(failed_cells) == 0,
        },
        "coverage_method_counts": dict(sorted(coverage_methods.items())),
        "uncovered_by_role": dict(sorted(uncovered_by_role.items())),
        "fallback_class_counts": dict(sorted(fallback_classes.items())),
        "pair_summary": pair_summary,
        "stored_uncovered_cells": [
            compact_cell_record(cell, cell["pair_records"])
            for cell in failed_cells[:MAX_STORED_CELLS]
        ],
        "stored_low_margin_cells": [
            {
                **{key: value for key, value in cell.items() if key != "pair_records"},
                "lowest_margin_pair_records": [
                    compact_pair_record(record)
                    for record in sorted(cell["pair_records"], key=lambda item: item["guard_margin"])[:3]
                ],
            }
            for cell in low_margin_cells
        ],
    }


def build_report() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / SOURCE_COMPONENT_REPORT)
    protocol_report = load_json(RESULTS_DIR / SOURCE_PROTOCOL_REPORT)
    signs_by_tree = comp.certified_signs_by_tree()
    source_by_tree = {audit["tree_id"]: audit for audit in component_report["representative_audits"]}
    all_cells = protocol.iter_cells()
    tree_reports = [
        audit_tree(case, source_by_tree[tree_id], signs_by_tree, all_cells)
        for tree_id in TARGET_TREE_IDS
    ]
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_guard_first_pass_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_PROTOCOL_REPORT}",
            f"results/{CASE_ID}/{SOURCE_COMPONENT_REPORT}",
            f"results/{CASE_ID}/tree007_residual_contact_closure_overlay_report.json",
            f"results/{CASE_ID}/tree021_residual_contact_closure_overlay_report.json",
        ],
        "target_tree_ids": TARGET_TREE_IDS,
        "source_protocol_summary_metrics": protocol_report["summary_metrics"],
        "summary_metrics": {
            "tree_count": len(tree_reports),
            "total_candidate_cell_count": sum(report["summary_metrics"]["candidate_cell_count"] for report in tree_reports),
            "total_center_sample_collision_free_cell_count": sum(
                report["summary_metrics"]["center_sample_collision_free_cell_count"] for report in tree_reports
            ),
            "total_first_pass_fully_covered_cell_count": sum(
                report["summary_metrics"]["first_pass_fully_covered_cell_count"] for report in tree_reports
            ),
            "total_first_pass_uncovered_cell_count": sum(
                report["summary_metrics"]["first_pass_uncovered_cell_count"] for report in tree_reports
            ),
            "total_pair_cell_count": sum(report["summary_metrics"]["total_pair_cell_count"] for report in tree_reports),
            "total_first_pass_covered_pair_cell_count": sum(
                report["summary_metrics"]["first_pass_covered_pair_cell_count"] for report in tree_reports
            ),
            "total_first_pass_uncovered_pair_cell_count": sum(
                report["summary_metrics"]["first_pass_uncovered_pair_cell_count"] for report in tree_reports
            ),
            "all_center_samples_collision_free": all(
                report["summary_metrics"]["center_sample_collision_free_cell_count"]
                == report["summary_metrics"]["candidate_cell_count"]
                for report in tree_reports
            ),
            "bounded_cell_cover_certificate_completed": all(
                report["summary_metrics"]["bounded_cell_cover_certificate_completed"]
                for report in tree_reports
            ),
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This is a first-pass bounded cell guard, not a complete continuous cell-cover certificate.",
            "Residual formula classes are assigned as next-step fallback classes but are not applied over full 3-parameter cells in this report.",
            "Cells with blocked sampled vertices are outside this first-pass target.",
            "The domain starts at theta=0.5 degrees and does not cover theta=0.",
            "The report does not certify dynamic connectedness between representatives, physical hinge thickness, offsets, mesh export, or printability.",
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
                    item["tree_id"]: item["summary_metrics"]
                    for item in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
