"""Ray-cell SAT guard for two S4 signed-ray representatives.

This audit adds a conservative cell-level guard around the already sampled
representative rays. It certifies only pair/cell combinations with a positive
separating-axis margin large enough to absorb a local angular displacement
bound. Pairs that remain in exact hinge/contact are reported separately because
clearance-only SAT guards cannot certify zero-margin contact cells.
"""

from __future__ import annotations

from collections import deque
import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "two_class_ray_cell_guard_report.json"
REPRESENTATIVES = {
    "CLASS_A_TREE007_TREE009": "TREE_007",
    "CLASS_B_TREE021_TREE093": "TREE_021",
}
RAY_CELL_START_DEGREES = 0.5
RAY_CELL_END_DEGREES = 120.0
RAY_CELL_STEP_DEGREES = 0.25
SAT_TOLERANCE = 1.0e-8
DISPLACEMENT_SAFETY_FACTOR = 1.25
MAX_STORED_CELLS = 48

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def degree_cells(start: float, end: float, step: float) -> list[dict]:
    cells = []
    left = float(start)
    index = 0
    while left < end - 1.0e-12:
        right = min(float(end), left + float(step))
        cells.append(
            {
                "cell_id": f"ray_cell_{index:04d}",
                "theta_left_degrees": round(left, 8),
                "theta_right_degrees": round(right, 8),
                "theta_center_degrees": round((left + right) / 2.0, 8),
                "theta_half_width_degrees": round((right - left) / 2.0, 8),
            }
        )
        left = right
        index += 1
    return cells


def selected_hinges(case: dict, tree: dict) -> list[dict]:
    return batch.selected_hinges_for_tree(case, tree)


def tree_paths_from_root(case: dict, tree: dict, root_piece: str = "P0") -> dict[str, list[dict]]:
    adjacency: dict[str, list[tuple[str, dict]]] = {piece_id: [] for piece_id in case["piece_ids"]}
    for hinge in selected_hinges(case, tree):
        left, right = hinge["pieces"]
        adjacency[left].append((right, hinge))
        adjacency[right].append((left, hinge))

    parent: dict[str, str | None] = {root_piece: None}
    parent_hinge: dict[str, dict] = {}
    queue: deque[str] = deque([root_piece])
    while queue:
        current = queue.popleft()
        for child, hinge in adjacency[current]:
            if child in parent:
                continue
            parent[child] = current
            parent_hinge[child] = hinge
            queue.append(child)

    paths = {}
    for piece_id in case["piece_ids"]:
        path = []
        current = piece_id
        while current != root_piece:
            path.append(parent_hinge[current])
            current = parent[current]
        paths[piece_id] = list(reversed(path))
    return paths


def transforms_for_degrees(case: dict, tree: dict, degrees_by_hinge: dict[str, float]) -> dict[str, dict[str, np.ndarray]]:
    angles = {hinge_id: math.radians(float(degrees)) for hinge_id, degrees in degrees_by_hinge.items()}
    return lib.transforms_for_hinge_tree(
        case["piece_ids"],
        selected_hinges(case, tree),
        case["labels"],
        angles,
        root_piece="P0",
    )


def point_line_distance(point: np.ndarray, axis_a: np.ndarray, axis_b: np.ndarray) -> float:
    axis = axis_b - axis_a
    return float(np.linalg.norm(np.cross(point - axis_a, axis)) / np.linalg.norm(axis))


def piece_displacement_bounds(
    case: dict,
    tree: dict,
    transforms: dict[str, dict[str, np.ndarray]],
    transformed_pieces: dict[str, list[np.ndarray]],
    theta_half_width_degrees: float,
    paths_by_piece: dict[str, list[dict]],
) -> dict[str, float]:
    half_angle_radians = math.radians(float(theta_half_width_degrees))
    bounds = {}
    for piece_id, vertices in transformed_pieces.items():
        displacement = 0.0
        for hinge in paths_by_piece[piece_id]:
            # The two incident pieces share the same transformed hinge axis. Use
            # the first side as a stable way to place that axis in world space.
            axis_side = hinge["pieces"][0]
            transform = transforms[axis_side]
            axis_a = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][0]])
            axis_b = lib.apply_transform_to_point(transform, case["labels"][hinge["axis_labels"][1]])
            max_distance = max(point_line_distance(vertex, axis_a, axis_b) for vertex in vertices)
            displacement += 2.0 * max_distance * math.sin(half_angle_radians / 2.0)
        bounds[piece_id] = DISPLACEMENT_SAFETY_FACTOR * displacement
    return bounds


def best_center_separating_axis(poly_a: list[np.ndarray], poly_b: list[np.ndarray]) -> dict:
    best = None
    for axis in lib.sat_axes(poly_a, poly_b):
        norm = np.linalg.norm(axis)
        if norm <= lib.TOL:
            continue
        unit = axis / norm
        a_values = [float(np.dot(vertex, unit)) for vertex in poly_a]
        b_values = [float(np.dot(vertex, unit)) for vertex in poly_b]
        overlap = min(max(a_values), max(b_values)) - max(min(a_values), min(b_values))
        if best is None or overlap < best["center_axis_overlap"]:
            best = {
                "center_axis_overlap": float(overlap),
                "axis": unit,
            }
    if best is None:
        raise RuntimeError("No SAT axis available for tetrahedron pair")
    return best


def contact_by_pair(case: dict) -> dict[tuple[str, str], dict]:
    records = {}
    for contact in case["contacts"]:
        pair = tuple(sorted(contact["pieces"]))
        records[pair] = contact
    return records


def pair_role(case: dict, tree: dict, pair: tuple[str, str], contacts_by_pair: dict[tuple[str, str], dict]) -> str:
    hinge_pairs = {tuple(sorted(case["hinge_by_id"][hinge_id]["pieces"])) for hinge_id in tree["hinge_ids"]}
    if pair in hinge_pairs:
        return "selected_hinge_contact"
    if pair in contacts_by_pair:
        return f"residual_{contacts_by_pair[pair]['type']}"
    return "non_contact_pair"


def compact_pair_record(record: dict) -> dict:
    return {
        "pair": list(record["pair"]),
        "role": record["role"],
        "certified": record["certified"],
        "center_axis_overlap": round(record["center_axis_overlap"], 12),
        "guard_bound": round(record["guard_bound"], 12),
        "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
        "reason": record["reason"],
    }


def cell_guard_record(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    paths_by_piece: dict[str, list[dict]],
    contacts_by_pair: dict[tuple[str, str], dict],
    cell: dict,
) -> dict:
    degrees_by_hinge = reps.ray_degrees(tree, signs_by_hinge, cell["theta_center_degrees"])
    transforms = transforms_for_degrees(case, tree, degrees_by_hinge)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    displacement_bounds = piece_displacement_bounds(
        case,
        tree,
        transforms,
        transformed,
        cell["theta_half_width_degrees"],
        paths_by_piece,
    )
    sample_status = lib.collision_report(transformed)["status"]

    pair_records = []
    for left, right in itertools.combinations(sorted(transformed), 2):
        pair = tuple(sorted((left, right)))
        best = best_center_separating_axis(transformed[left], transformed[right])
        guard = displacement_bounds[left] + displacement_bounds[right] + SAT_TOLERANCE
        post_guard = best["center_axis_overlap"] + guard
        certified = sample_status == "collision_free" and post_guard <= SAT_TOLERANCE
        role = pair_role(case, tree, pair, contacts_by_pair)
        if certified:
            reason = "clearance_guard_passed"
        elif role == "selected_hinge_contact":
            reason = "selected_hinge_contact_has_zero_or_insufficient_clearance_margin"
        elif role.startswith("residual_"):
            reason = "residual_contact_or_near_contact_has_zero_or_insufficient_clearance_margin"
        else:
            reason = "insufficient_clearance_margin"
        pair_records.append(
            {
                "pair": pair,
                "role": role,
                "certified": certified,
                "center_axis_overlap": best["center_axis_overlap"],
                "guard_bound": guard,
                "post_guard_overlap_bound": post_guard,
                "reason": reason,
            }
        )

    non_hinge_records = [record for record in pair_records if record["role"] != "selected_hinge_contact"]
    certified_count = sum(1 for record in pair_records if record["certified"])
    return {
        **cell,
        "center_sample_status": sample_status,
        "pair_count": len(pair_records),
        "certified_pair_count": certified_count,
        "uncertified_pair_count": len(pair_records) - certified_count,
        "fully_clearance_certified": certified_count == len(pair_records),
        "all_non_hinge_pairs_clearance_certified": all(record["certified"] for record in non_hinge_records),
        "pair_records": pair_records,
    }


def summarize_pair_records(cells: list[dict]) -> list[dict]:
    summary: dict[tuple[str, str], dict] = {}
    for cell in cells:
        for record in cell["pair_records"]:
            pair = record["pair"]
            item = summary.setdefault(
                pair,
                {
                    "pair": pair,
                    "role": record["role"],
                    "cell_count": 0,
                    "certified_cell_count": 0,
                    "uncertified_cell_count": 0,
                    "minimum_center_axis_overlap": None,
                    "maximum_post_guard_overlap_bound": None,
                    "first_uncertified_cell": None,
                    "last_uncertified_cell": None,
                },
            )
            item["cell_count"] += 1
            if record["certified"]:
                item["certified_cell_count"] += 1
            else:
                item["uncertified_cell_count"] += 1
                compact = {
                    "cell_id": cell["cell_id"],
                    "theta_interval_degrees": [cell["theta_left_degrees"], cell["theta_right_degrees"]],
                    "reason": record["reason"],
                    "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
                }
                if item["first_uncertified_cell"] is None:
                    item["first_uncertified_cell"] = compact
                item["last_uncertified_cell"] = compact
            overlap = record["center_axis_overlap"]
            post_guard = record["post_guard_overlap_bound"]
            current_min = item["minimum_center_axis_overlap"]
            current_max = item["maximum_post_guard_overlap_bound"]
            item["minimum_center_axis_overlap"] = overlap if current_min is None else min(current_min, overlap)
            item["maximum_post_guard_overlap_bound"] = post_guard if current_max is None else max(current_max, post_guard)
    output = []
    for item in summary.values():
        output.append(
            {
                "pair": list(item["pair"]),
                "role": item["role"],
                "cell_count": item["cell_count"],
                "certified_cell_count": item["certified_cell_count"],
                "uncertified_cell_count": item["uncertified_cell_count"],
                "minimum_center_axis_overlap": round(item["minimum_center_axis_overlap"], 12),
                "maximum_post_guard_overlap_bound": round(item["maximum_post_guard_overlap_bound"], 12),
                "first_uncertified_cell": item["first_uncertified_cell"],
                "last_uncertified_cell": item["last_uncertified_cell"],
            }
        )
    return sorted(output, key=lambda item: item["pair"])


def audit_tree(case: dict, class_id: str, tree_id: str, signs_by_hinge: dict[str, int]) -> dict:
    tree = comp.find_tree(case, tree_id)
    paths = tree_paths_from_root(case, tree)
    contacts = contact_by_pair(case)
    cells = [
        cell_guard_record(case, tree, signs_by_hinge, paths, contacts, cell)
        for cell in degree_cells(RAY_CELL_START_DEGREES, RAY_CELL_END_DEGREES, RAY_CELL_STEP_DEGREES)
    ]
    pair_summary = summarize_pair_records(cells)
    full_cells = [cell for cell in cells if cell["fully_clearance_certified"]]
    non_hinge_cells = [cell for cell in cells if cell["all_non_hinge_pairs_clearance_certified"]]
    total_pair_cells = sum(cell["pair_count"] for cell in cells)
    certified_pair_cells = sum(cell["certified_pair_count"] for cell in cells)
    selected_hinge_pair_cells = sum(
        1
        for cell in cells
        for record in cell["pair_records"]
        if record["role"] == "selected_hinge_contact"
    )
    selected_hinge_certified = sum(
        1
        for cell in cells
        for record in cell["pair_records"]
        if record["role"] == "selected_hinge_contact" and record["certified"]
    )
    non_hinge_pair_cells = total_pair_cells - selected_hinge_pair_cells
    non_hinge_certified = certified_pair_cells - selected_hinge_certified

    stored_uncertified = []
    for cell in cells:
        if cell["uncertified_pair_count"] == 0:
            continue
        stored_uncertified.append(
            {
                "cell_id": cell["cell_id"],
                "theta_interval_degrees": [cell["theta_left_degrees"], cell["theta_right_degrees"]],
                "uncertified_pair_records": [
                    compact_pair_record(record)
                    for record in cell["pair_records"]
                    if not record["certified"]
                ],
            }
        )
        if len(stored_uncertified) >= MAX_STORED_CELLS:
            break

    return {
        "class_id": class_id,
        "tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs_by_hinge,
        "status": "ray_cell_guard_completed",
        "cell_protocol": {
            "theta_start_degrees": RAY_CELL_START_DEGREES,
            "theta_end_degrees": RAY_CELL_END_DEGREES,
            "theta_step_degrees": RAY_CELL_STEP_DEGREES,
            "cell_count": len(cells),
            "sat_tolerance": SAT_TOLERANCE,
            "displacement_safety_factor": DISPLACEMENT_SAFETY_FACTOR,
            "guard_rule": "center separating-axis overlap plus local angular displacement bound must stay <= SAT tolerance",
        },
        "summary_metrics": {
            "cell_count": len(cells),
            "center_sample_collision_free_cell_count": sum(
                1 for cell in cells if cell["center_sample_status"] == "collision_free"
            ),
            "full_clearance_certified_cell_count": len(full_cells),
            "all_non_hinge_pairs_clearance_certified_cell_count": len(non_hinge_cells),
            "total_pair_cell_count": total_pair_cells,
            "certified_pair_cell_count": certified_pair_cells,
            "uncertified_pair_cell_count": total_pair_cells - certified_pair_cells,
            "selected_hinge_pair_cell_count": selected_hinge_pair_cells,
            "selected_hinge_certified_pair_cell_count": selected_hinge_certified,
            "non_hinge_pair_cell_count": non_hinge_pair_cells,
            "non_hinge_certified_pair_cell_count": non_hinge_certified,
            "non_hinge_uncertified_pair_cell_count": non_hinge_pair_cells - non_hinge_certified,
        },
        "pair_summary": pair_summary,
        "stored_uncertified_cells": stored_uncertified,
    }


def build_report() -> dict:
    case = batch.build_case()
    signs_by_tree = comp.certified_signs_by_tree()
    audits = [
        audit_tree(case, class_id, tree_id, signs_by_tree[tree_id])
        for class_id, tree_id in REPRESENTATIVES.items()
    ]
    return {
        "case_id": CASE_ID,
        "status": "two_class_ray_cell_guard_completed",
        "representatives": REPRESENTATIVES,
        "global_protocol": {
            "theta_start_degrees": RAY_CELL_START_DEGREES,
            "theta_end_degrees": RAY_CELL_END_DEGREES,
            "theta_step_degrees": RAY_CELL_STEP_DEGREES,
            "sat_tolerance": SAT_TOLERANCE,
            "displacement_safety_factor": DISPLACEMENT_SAFETY_FACTOR,
        },
        "summary_metrics": {
            "representative_count": len(audits),
            "all_center_samples_collision_free": all(
                audit["summary_metrics"]["center_sample_collision_free_cell_count"]
                == audit["summary_metrics"]["cell_count"]
                for audit in audits
            ),
            "any_full_clearance_certified_cells": any(
                audit["summary_metrics"]["full_clearance_certified_cell_count"] > 0
                for audit in audits
            ),
            "all_non_hinge_pairs_have_some_clearance_certification": all(
                all(
                    item["role"] == "selected_hinge_contact" or item["certified_cell_count"] > 0
                    for item in audit["pair_summary"]
                )
                for audit in audits
            ),
        },
        "representative_audits": audits,
        "limitations": [
            "This is a finite ray-cell guard, not a full interval-arithmetic SAT proof.",
            "The guard certifies only pairs with positive separating-axis clearance; exact hinge/contact pairs remain intentionally uncertified by this method.",
            "The displacement bound is local to each ray cell and uses a safety factor; it is a conservative engineering guard, not symbolic interval rotation arithmetic.",
            "The audit covers cells along the signed ray from 0.5 to 120 degrees, not the full cylindrical component graph and not the closed theta=0 contact configuration.",
            "No physical hinge offsets, thickness, clearance, mesh export, or printability gate is modeled.",
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
                "tree_metrics": {
                    audit["tree_id"]: audit["summary_metrics"]
                    for audit in report["representative_audits"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())