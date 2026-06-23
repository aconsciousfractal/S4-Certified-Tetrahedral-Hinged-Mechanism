"""Batch sampled motion audit for boundary-only S4 hinge trees.

This script ranks the 32 boundary-only connected 3-hinge trees from the S4
median-plane enumeration. It uses the same zero-thickness rigid-body convention
as the TREE_007 scripts, but a lighter refinement protocol for breadth.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "boundary_tree_batch_report.json"
RAY_SAMPLE_MAGNITUDES = [0, 2, 5, 10, 15, 20, 30, 45, 60, 75, 90, 105, 120]
REFINE_START_DEGREES = 0.0
REFINE_END_DEGREES = 120.0
REFINE_UNIFORM_STEP_DEGREES = 1.0
REFINE_CONTACT_BAND_THRESHOLD = 1.0e-3
REFINE_CONTACT_BAND_STEP_DEGREES = 0.125
MAX_STORED_TREE_RECORDS = 64

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
    return {
        "labels": labels,
        "pieces_by_id": pieces_by_id,
        "piece_ids": piece_ids,
        "contacts": contacts,
        "hinges": hinges,
        "hinge_by_id": {hinge["hinge_id"]: hinge for hinge in hinges},
        "hinge_trees": hinge_trees,
    }


def selected_hinges_for_tree(case: dict, tree: dict) -> list[dict]:
    return [case["hinge_by_id"][hinge_id] for hinge_id in tree["hinge_ids"]]


def evaluate_tree_configuration(case: dict, tree: dict, signed_degrees_by_hinge: dict[str, float]) -> dict:
    selected_hinges = selected_hinges_for_tree(case, tree)
    angles = {
        hinge_id: math.radians(float(degrees))
        for hinge_id, degrees in signed_degrees_by_hinge.items()
    }
    transforms = lib.transforms_for_hinge_tree(
        case["piece_ids"],
        selected_hinges,
        case["labels"],
        angles,
        root_piece="P0",
    )
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    collision = lib.collision_report(transformed)
    return {
        "status": collision["status"],
        "collisions": collision["collisions"],
        "minimum_axis_overlap_proxy": collision["minimum_axis_overlap_proxy"],
    }


def signed_degrees_from_vector(hinge_ids: list[str], sign_vector: tuple[int, ...], magnitude: float) -> dict[str, float]:
    return {
        hinge_id: sign * float(magnitude)
        for hinge_id, sign in zip(hinge_ids, sign_vector)
    }


def compact_sample(magnitude: float, sample: dict) -> dict:
    return {
        "magnitude_degrees": round(float(magnitude), 8),
        "status": sample["status"],
        "collisions": sample["collisions"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
    }


def ray_search_for_tree(case: dict, tree: dict) -> dict:
    hinge_ids = tree["hinge_ids"]
    ray_reports = []
    for sign_vector in itertools.product([1, -1], repeat=len(hinge_ids)):
        blocked_samples = []
        stored_samples = []
        min_proxy = None
        endpoint_sample = None
        for magnitude in RAY_SAMPLE_MAGNITUDES:
            signed_degrees = signed_degrees_from_vector(hinge_ids, sign_vector, magnitude)
            sample = evaluate_tree_configuration(case, tree, signed_degrees)
            compact = compact_sample(magnitude, sample)
            stored_samples.append(compact)
            endpoint_sample = compact
            if sample["minimum_axis_overlap_proxy"] is not None:
                min_proxy = sample["minimum_axis_overlap_proxy"] if min_proxy is None else min(min_proxy, sample["minimum_axis_overlap_proxy"])
            if sample["status"] != "collision_free":
                blocked_samples.append(compact)
        ray_reports.append(
            {
                "sign_vector_by_hinge": dict(zip(hinge_ids, sign_vector)),
                "status": "sampled_collision_free" if not blocked_samples else "blocked",
                "blocked_sample_count": len(blocked_samples),
                "first_blocked_sample": blocked_samples[0] if blocked_samples else None,
                "endpoint_sample": endpoint_sample,
                "minimum_axis_overlap_proxy": min_proxy,
                "samples": stored_samples,
            }
        )
    free_rays = [ray for ray in ray_reports if ray["status"] == "sampled_collision_free"]
    return {
        "ray_count": len(ray_reports),
        "sample_magnitudes_degrees": RAY_SAMPLE_MAGNITUDES,
        "sampled_collision_free_ray_count": len(free_rays),
        "free_rays": free_rays,
        "rays": ray_reports,
    }


def degree_range(start: float, end: float, step: float) -> list[float]:
    count = int(round((end - start) / step))
    values = [round(start + index * step, 8) for index in range(count + 1)]
    if values[-1] < end:
        values.append(round(end, 8))
    return values


def refine_ray_for_tree(case: dict, tree: dict, sign_vector_by_hinge: dict[str, int]) -> dict:
    uniform_magnitudes = degree_range(REFINE_START_DEGREES, REFINE_END_DEGREES, REFINE_UNIFORM_STEP_DEGREES)
    hinge_ids = tree["hinge_ids"]
    signs = tuple(int(sign_vector_by_hinge[hinge_id]) for hinge_id in hinge_ids)
    sample_cache: dict[float, dict] = {}

    for magnitude in uniform_magnitudes:
        signed_degrees = signed_degrees_from_vector(hinge_ids, signs, magnitude)
        sample_cache[magnitude] = evaluate_tree_configuration(case, tree, signed_degrees)

    contact_band_intervals = []
    for left, right in zip(uniform_magnitudes, uniform_magnitudes[1:]):
        left_sample = sample_cache[left]
        right_sample = sample_cache[right]
        left_proxy = left_sample["minimum_axis_overlap_proxy"] or 0.0
        right_proxy = right_sample["minimum_axis_overlap_proxy"] or 0.0
        left_near = abs(left_proxy) <= REFINE_CONTACT_BAND_THRESHOLD
        right_near = abs(right_proxy) <= REFINE_CONTACT_BAND_THRESHOLD
        if left_sample["status"] != "collision_free" or right_sample["status"] != "collision_free" or left_near or right_near:
            contact_band_intervals.append([left, right])
            for magnitude in degree_range(left, right, REFINE_CONTACT_BAND_STEP_DEGREES):
                if magnitude not in sample_cache:
                    signed_degrees = signed_degrees_from_vector(hinge_ids, signs, magnitude)
                    sample_cache[magnitude] = evaluate_tree_configuration(case, tree, signed_degrees)

    all_magnitudes = sorted(sample_cache)
    all_samples = [(magnitude, sample_cache[magnitude]) for magnitude in all_magnitudes]
    blocked_samples = [(magnitude, sample) for magnitude, sample in all_samples if sample["status"] != "collision_free"]
    nonzero_samples = [(magnitude, sample) for magnitude, sample in all_samples if magnitude > 0.0]
    closest_nonzero = None
    if nonzero_samples:
        closest_nonzero = min(nonzero_samples, key=lambda item: abs(item[1]["minimum_axis_overlap_proxy"] or 0.0))
    largest_gap = max(round(right - left, 8) for left, right in zip(all_magnitudes, all_magnitudes[1:]))
    endpoint = (REFINE_END_DEGREES, sample_cache[REFINE_END_DEGREES])

    return {
        "status": "refined_sampled_collision_free" if not blocked_samples else "blocked_on_refined_sampling",
        "sign_vector_by_hinge": sign_vector_by_hinge,
        "ray_interval_degrees": [REFINE_START_DEGREES, REFINE_END_DEGREES],
        "uniform_step_degrees": REFINE_UNIFORM_STEP_DEGREES,
        "contact_band_threshold": REFINE_CONTACT_BAND_THRESHOLD,
        "contact_band_step_degrees": REFINE_CONTACT_BAND_STEP_DEGREES,
        "contact_band_interval_count": len(contact_band_intervals),
        "contact_band_intervals_degrees": contact_band_intervals[:40],
        "total_unique_sample_count": len(all_samples),
        "largest_gap_degrees_after_refinement": largest_gap,
        "blocked_sample_count": len(blocked_samples),
        "closest_nonzero_contact_sample": compact_sample(*closest_nonzero) if closest_nonzero else None,
        "endpoint_sample": compact_sample(*endpoint),
        "first_blocked_sample": compact_sample(*blocked_samples[0]) if blocked_samples else None,
    }


def refine_free_rays_for_tree(case: dict, tree: dict, free_rays: list[dict]) -> dict | None:
    if not free_rays:
        return None
    attempts = []
    for ray in free_rays:
        result = refine_ray_for_tree(case, tree, ray["sign_vector_by_hinge"])
        attempts.append(result)
        if result["status"] == "refined_sampled_collision_free":
            break
    return {
        "attempt_count": len(attempts),
        "status": attempts[-1]["status"],
        "first_refined_free_ray": next((attempt for attempt in attempts if attempt["status"] == "refined_sampled_collision_free"), None),
        "attempts": attempts,
    }


def classify_tree(tree: dict, ray_search: dict, refinement: dict | None) -> str:
    if ray_search["sampled_collision_free_ray_count"] == 0:
        return "no_sampled_free_ray"
    if refinement and refinement["first_refined_free_ray"]:
        return "refined_free_ray_found"
    return "coarse_free_ray_found_refinement_blocked"


def tree_record(case: dict, tree: dict) -> dict:
    ray_search = ray_search_for_tree(case, tree)
    refinement = refine_free_rays_for_tree(case, tree, ray_search["free_rays"])
    status = classify_tree(tree, ray_search, refinement)
    selected_hinges = selected_hinges_for_tree(case, tree)
    ambient_face_axis_count = sum(1 for support in tree["axis_supports"] if support == "ambient_face_segment")
    refined = refinement["first_refined_free_ray"] if refinement else None
    ranking_key = [
        0 if status == "refined_free_ray_found" else 1,
        -ray_search["sampled_collision_free_ray_count"],
        -tree["ambient_edge_axis_count"],
        ambient_face_axis_count,
        refined["contact_band_interval_count"] if refined else 999,
        tree["rank"],
    ]
    return {
        "tree_id": tree["tree_id"],
        "status": status,
        "tree_rank_from_enumeration": tree["rank"],
        "hinge_ids": tree["hinge_ids"],
        "piece_edges": tree["piece_edges"],
        "axis_labels": tree["axis_labels"],
        "axis_supports": tree["axis_supports"],
        "ambient_edge_axis_count": tree["ambient_edge_axis_count"],
        "ambient_face_axis_count": ambient_face_axis_count,
        "selected_hinges": selected_hinges,
        "sampled_collision_free_ray_count": ray_search["sampled_collision_free_ray_count"],
        "first_free_ray": ray_search["free_rays"][0] if ray_search["free_rays"] else None,
        "refinement": refinement,
        "ranking_key": ranking_key,
    }


def build_report() -> dict:
    case = build_case()
    boundary_trees = [tree for tree in case["hinge_trees"] if tree["internal_axis_count"] == 0]
    records = [tree_record(case, tree) for tree in boundary_trees]
    records.sort(key=lambda record: tuple(record["ranking_key"]))
    for index, record in enumerate(records):
        record["batch_rank"] = index + 1

    refined_records = [record for record in records if record["status"] == "refined_free_ray_found"]
    coarse_only_records = [record for record in records if record["status"] == "coarse_free_ray_found_refinement_blocked"]
    blocked_records = [record for record in records if record["status"] == "no_sampled_free_ray"]
    all_ambient_edge_records = [record for record in records if record["ambient_edge_axis_count"] == 3]

    return {
        "case_id": CASE_ID,
        "status": "boundary_tree_batch_completed",
        "scope": {
            "total_hinge_tree_count": len(case["hinge_trees"]),
            "boundary_only_tree_count": len(boundary_trees),
            "tested_tree_count": len(records),
            "filter": "internal_axis_count == 0",
        },
        "sampling_protocol": {
            "ray_sample_magnitudes_degrees": RAY_SAMPLE_MAGNITUDES,
            "ray_count_per_tree": 8,
            "refinement": {
                "applies_to": "first sampled free ray, or next free ray if a refinement attempt blocks",
                "uniform_step_degrees": REFINE_UNIFORM_STEP_DEGREES,
                "contact_band_threshold": REFINE_CONTACT_BAND_THRESHOLD,
                "contact_band_step_degrees": REFINE_CONTACT_BAND_STEP_DEGREES,
                "interval_degrees": [REFINE_START_DEGREES, REFINE_END_DEGREES],
            },
            "note": "This is a batch-ranking refinement, lighter than the dedicated TREE_007 refinement report.",
        },
        "summary_metrics": {
            "refined_free_ray_tree_count": len(refined_records),
            "coarse_free_ray_refinement_blocked_tree_count": len(coarse_only_records),
            "no_sampled_free_ray_tree_count": len(blocked_records),
            "all_ambient_edge_tree_count": len(all_ambient_edge_records),
            "all_ambient_edge_refined_free_ray_tree_count": sum(1 for record in all_ambient_edge_records if record["status"] == "refined_free_ray_found"),
        },
        "top_ranked_trees": records[:MAX_STORED_TREE_RECORDS],
        "tree_records": records,
        "limitations": [
            "This is a sampled zero-thickness batch audit, not a continuous proof of hingeability.",
            "Only boundary-only trees are tested here; trees with internal axes are intentionally excluded.",
            "The batch refinement protocol is lighter than the dedicated TREE_007 0.25-degree / 0.03125-degree refinement.",
            "No hinge thickness, pin radius, manufacturing clearance, mesh export, or printability gate is modeled.",
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
                "tested_tree_count": report["scope"]["tested_tree_count"],
                "refined_free_ray_tree_count": report["summary_metrics"]["refined_free_ray_tree_count"],
                "no_sampled_free_ray_tree_count": report["summary_metrics"]["no_sampled_free_ray_tree_count"],
                "top_tree": report["top_ranked_trees"][0]["tree_id"] if report["top_ranked_trees"] else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())