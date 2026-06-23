"""Sampled motion audit for the S4 median-plane TREE_007 hinge graph."""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
TREE_ID = "TREE_007"
REPORT_NAME = "motion_report_tree007.json"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def build_case() -> dict:
    A, B, C, D = lib.regular_tetrahedron(edge_length=1.0)
    labels = lib.canonical_labels(A, B, C, D)
    pieces = lib.dissections.dissect_n4(A, B, C, D)
    piece_ids = [f"P{i}" for i in range(len(pieces))]
    pieces_by_id = dict(zip(piece_ids, pieces))
    piece_records = [lib.piece_record(piece_id, piece, labels) for piece_id, piece in pieces_by_id.items()]
    contacts = lib.extract_contacts(piece_records)
    hinges = lib.enumerate_candidate_hinges(contacts, labels, lib.ambient_faces(A, B, C, D))
    lib.augment_hinge_support(hinges, labels, lib.ambient_edges(A, B, C, D))
    hinge_trees = lib.enumerate_hinge_trees(piece_ids, hinges)
    selected_tree = next((tree for tree in hinge_trees if tree["tree_id"] == TREE_ID), None)
    if selected_tree is None:
        raise RuntimeError(f"{TREE_ID} not found in enumerated S4 hinge trees")
    hinge_by_id = {hinge["hinge_id"]: hinge for hinge in hinges}
    selected_hinges = [hinge_by_id[hinge_id] for hinge_id in selected_tree["hinge_ids"]]
    return {
        "labels": labels,
        "pieces_by_id": pieces_by_id,
        "piece_ids": piece_ids,
        "contacts": contacts,
        "hinges": hinges,
        "selected_tree": selected_tree,
        "selected_hinges": selected_hinges,
    }


def evaluate_configuration(case: dict, signed_degrees_by_hinge: dict[str, float]) -> dict:
    angles = {
        hinge_id: math.radians(float(degrees))
        for hinge_id, degrees in signed_degrees_by_hinge.items()
    }
    transforms = lib.transforms_for_hinge_tree(
        case["piece_ids"],
        case["selected_hinges"],
        case["labels"],
        angles,
        root_piece="P0",
    )
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    collision = lib.collision_report(transformed)
    return {
        "angle_degrees_by_hinge": {
            hinge["hinge_id"]: round(float(signed_degrees_by_hinge.get(hinge["hinge_id"], 0.0)), 6)
            for hinge in case["selected_hinges"]
        },
        "status": collision["status"],
        "collisions": collision["collisions"],
        "minimum_axis_overlap_proxy": collision["minimum_axis_overlap_proxy"],
    }


def ray_search(case: dict) -> list[dict]:
    sample_magnitudes = [0, 2, 5, 10, 15, 20, 30, 45, 60, 75, 90, 105, 120]
    hinge_ids = [hinge["hinge_id"] for hinge in case["selected_hinges"]]
    reports = []
    for sign_vector in itertools.product([1, -1], repeat=len(hinge_ids)):
        samples = []
        blocked_samples = []
        min_proxy = None
        for magnitude in sample_magnitudes:
            signed_degrees = {
                hinge_id: sign * magnitude
                for hinge_id, sign in zip(hinge_ids, sign_vector)
            }
            sample = evaluate_configuration(case, signed_degrees)
            samples.append(
                {
                    "magnitude_degrees": magnitude,
                    "angle_degrees_by_hinge": sample["angle_degrees_by_hinge"],
                    "status": sample["status"],
                    "collisions": sample["collisions"],
                    "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
                }
            )
            if sample["minimum_axis_overlap_proxy"] is not None:
                min_proxy = sample["minimum_axis_overlap_proxy"] if min_proxy is None else min(min_proxy, sample["minimum_axis_overlap_proxy"])
            if sample["status"] != "collision_free":
                blocked_samples.append(samples[-1])
        reports.append(
            {
                "sign_vector_by_hinge": dict(zip(hinge_ids, sign_vector)),
                "sample_magnitudes_degrees": sample_magnitudes,
                "status": "sampled_collision_free" if not blocked_samples else "blocked",
                "blocked_sample_count": len(blocked_samples),
                "first_blocked_sample": blocked_samples[0] if blocked_samples else None,
                "minimum_axis_overlap_proxy": min_proxy,
                "samples": samples,
            }
        )
    return reports


def grid_search(case: dict) -> dict:
    grid_degrees = [-60, -45, -30, -15, 0, 15, 30, 45, 60]
    hinge_ids = [hinge["hinge_id"] for hinge in case["selected_hinges"]]
    free_samples = []
    blocked_count = 0
    min_proxy = None
    for values in itertools.product(grid_degrees, repeat=len(hinge_ids)):
        if all(value == 0 for value in values):
            continue
        signed_degrees = dict(zip(hinge_ids, values))
        sample = evaluate_configuration(case, signed_degrees)
        if sample["minimum_axis_overlap_proxy"] is not None:
            min_proxy = sample["minimum_axis_overlap_proxy"] if min_proxy is None else min(min_proxy, sample["minimum_axis_overlap_proxy"])
        if sample["status"] == "collision_free":
            if len(free_samples) < 24:
                free_samples.append(sample)
        else:
            blocked_count += 1
    total = (len(grid_degrees) ** len(hinge_ids)) - 1
    return {
        "grid_degrees_per_hinge": grid_degrees,
        "total_nonzero_samples": total,
        "collision_free_sample_count": total - blocked_count,
        "blocked_sample_count": blocked_count,
        "stored_collision_free_samples": free_samples,
        "minimum_axis_overlap_proxy": min_proxy,
    }


def build_report() -> dict:
    case = build_case()
    zero_sample = evaluate_configuration(
        case,
        {hinge["hinge_id"]: 0.0 for hinge in case["selected_hinges"]},
    )
    ray_reports = ray_search(case)
    grid_report = grid_search(case)
    free_rays = [report for report in ray_reports if report["status"] == "sampled_collision_free"]

    if free_rays:
        status = "sampled_collision_free_ray_found"
    elif grid_report["collision_free_sample_count"] > 0:
        status = "sampled_free_configurations_found_no_ray"
    else:
        status = "blocked_on_sampled_search"

    return {
        "case_id": CASE_ID,
        "tree_id": TREE_ID,
        "status": status,
        "selected_tree": case["selected_tree"],
        "selected_hinges": case["selected_hinges"],
        "motion_model": {
            "root_piece": "P0",
            "parameter_count": len(case["selected_hinges"]),
            "angle_convention": "child piece rotates relative to parent about the listed axis-label order, propagated from root P0",
            "collision_method": "strict convex SAT; touching/contact is allowed, positive-volume interior overlap is blocked",
            "thickness_model": "zero_thickness",
        },
        "zero_configuration_check": zero_sample,
        "ray_search": {
            "ray_count": len(ray_reports),
            "sampled_collision_free_ray_count": len(free_rays),
            "first_sampled_collision_free_ray": free_rays[0] if free_rays else None,
            "rays": ray_reports,
        },
        "grid_search": grid_report,
        "limitations": [
            "This is a sampled zero-thickness rigid-body audit, not a proof of continuous path clearance.",
            "The report tests the selected TREE_007 only, not all 108 enumerated S4 hinge trees.",
            "No hinge thickness, pin radius, manufacturing clearance, or mesh export is modeled here.",
            "A sampled free ray is evidence for this finite audit only; it must not be stated as a theorem without stronger interval or analytic verification.",
        ],
    }


def main() -> int:
    report = build_report()
    lib.write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "tree_id": TREE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "sampled_collision_free_rays": report["ray_search"]["sampled_collision_free_ray_count"],
                "grid_collision_free_samples": report["grid_search"]["collision_free_sample_count"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())