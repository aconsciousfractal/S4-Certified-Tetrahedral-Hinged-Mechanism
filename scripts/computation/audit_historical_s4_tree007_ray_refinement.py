"""Refine the sampled free ray for S4 TREE_007.

This is a stronger finite replay than the first TREE_007 motion report, but it
is still not an interval proof. The target ray is the discovered sign pattern:
H0_A_M_AB = +theta, H4_C_M_CD = +theta, H7_D_M_CD = -theta.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
TREE_ID = "TREE_007"
REPORT_NAME = "motion_report_tree007_ray_refinement.json"
RAY_SIGNS = {
    "H0_A_M_AB": 1,
    "H4_C_M_CD": 1,
    "H7_D_M_CD": -1,
}
RAY_START_DEGREES = 0.0
RAY_END_DEGREES = 120.0
UNIFORM_STEP_DEGREES = 0.25
CONTACT_BAND_THRESHOLD = 1.0e-3
CONTACT_BAND_STEP_DEGREES = 0.03125

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_tree007_motion as base_motion  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def ray_angles(magnitude_degrees: float) -> dict[str, float]:
    return {
        hinge_id: sign * float(magnitude_degrees)
        for hinge_id, sign in RAY_SIGNS.items()
    }


def pairwise_collision_report(transformed_pieces: dict) -> dict:
    pair_reports = []
    blocked_pairs = []
    minimum_axis_overlap_proxy = None
    closest_to_contact_proxy = None
    closest_to_contact_pair = None

    piece_ids = sorted(transformed_pieces)
    for left_index, left in enumerate(piece_ids):
        for right in piece_ids[left_index + 1 :]:
            has_overlap, min_overlap = lib.strict_interior_overlap(transformed_pieces[left], transformed_pieces[right])
            rounded_overlap = round(float(min_overlap), 12)
            pair_report = {
                "pieces": [left, right],
                "status": "blocked" if has_overlap else "collision_free",
                "min_axis_overlap": rounded_overlap,
            }
            pair_reports.append(pair_report)
            if minimum_axis_overlap_proxy is None or rounded_overlap < minimum_axis_overlap_proxy:
                minimum_axis_overlap_proxy = rounded_overlap
            if closest_to_contact_proxy is None or abs(rounded_overlap) < abs(closest_to_contact_proxy):
                closest_to_contact_proxy = rounded_overlap
                closest_to_contact_pair = [left, right]
            if has_overlap:
                blocked_pairs.append(pair_report)

    return {
        "status": "collision_free" if not blocked_pairs else "blocked",
        "blocked_pairs": blocked_pairs,
        "pair_reports": pair_reports,
        "minimum_axis_overlap_proxy": minimum_axis_overlap_proxy,
        "closest_to_contact_proxy": closest_to_contact_proxy,
        "closest_to_contact_pair": closest_to_contact_pair,
    }


def evaluate_magnitude(case: dict, magnitude_degrees: float) -> dict:
    signed_degrees = ray_angles(magnitude_degrees)
    angles = {
        hinge_id: math.radians(float(degrees))
        for hinge_id, degrees in signed_degrees.items()
    }
    transforms = lib.transforms_for_hinge_tree(
        case["piece_ids"],
        case["selected_hinges"],
        case["labels"],
        angles,
        root_piece="P0",
    )
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    collision = pairwise_collision_report(transformed)
    return {
        "magnitude_degrees": round(float(magnitude_degrees), 8),
        "angle_degrees_by_hinge": {
            hinge_id: round(float(degrees), 8)
            for hinge_id, degrees in signed_degrees.items()
        },
        "status": collision["status"],
        "blocked_pairs": collision["blocked_pairs"],
        "minimum_axis_overlap_proxy": collision["minimum_axis_overlap_proxy"],
        "closest_to_contact_proxy": collision["closest_to_contact_proxy"],
        "closest_to_contact_pair": collision["closest_to_contact_pair"],
        "pair_reports": collision["pair_reports"],
    }


def degree_range(start: float, end: float, step: float) -> list[float]:
    count = int(round((end - start) / step))
    values = [round(start + index * step, 8) for index in range(count + 1)]
    if values[-1] < end:
        values.append(round(end, 8))
    return values


def compact_sample(sample: dict) -> dict:
    return {
        "magnitude_degrees": sample["magnitude_degrees"],
        "status": sample["status"],
        "blocked_pairs": sample["blocked_pairs"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
        "closest_to_contact_proxy": sample["closest_to_contact_proxy"],
        "closest_to_contact_pair": sample["closest_to_contact_pair"],
    }


def build_report() -> dict:
    case = base_motion.build_case()
    uniform_magnitudes = degree_range(RAY_START_DEGREES, RAY_END_DEGREES, UNIFORM_STEP_DEGREES)
    sample_cache: dict[float, dict] = {}

    for magnitude in uniform_magnitudes:
        sample_cache[magnitude] = evaluate_magnitude(case, magnitude)

    contact_band_intervals = []
    for left, right in zip(uniform_magnitudes, uniform_magnitudes[1:]):
        left_sample = sample_cache[left]
        right_sample = sample_cache[right]
        left_near = abs(left_sample["minimum_axis_overlap_proxy"] or 0.0) <= CONTACT_BAND_THRESHOLD
        right_near = abs(right_sample["minimum_axis_overlap_proxy"] or 0.0) <= CONTACT_BAND_THRESHOLD
        if left_sample["status"] != "collision_free" or right_sample["status"] != "collision_free" or left_near or right_near:
            contact_band_intervals.append([left, right])
            for magnitude in degree_range(left, right, CONTACT_BAND_STEP_DEGREES):
                if magnitude not in sample_cache:
                    sample_cache[magnitude] = evaluate_magnitude(case, magnitude)

    all_magnitudes = sorted(sample_cache)
    all_samples = [sample_cache[magnitude] for magnitude in all_magnitudes]
    blocked_samples = [sample for sample in all_samples if sample["status"] != "collision_free"]
    nonzero_samples = [sample for sample in all_samples if sample["magnitude_degrees"] > 0.0]
    closest_nonzero = None
    if nonzero_samples:
        closest_nonzero = min(nonzero_samples, key=lambda sample: abs(sample["minimum_axis_overlap_proxy"] or 0.0))
    largest_gap = max(
        round(right - left, 8)
        for left, right in zip(all_magnitudes, all_magnitudes[1:])
    )

    status = "refined_sampled_collision_free" if not blocked_samples else "blocked_on_refined_sampling"

    return {
        "case_id": CASE_ID,
        "tree_id": TREE_ID,
        "status": status,
        "ray_signs_by_hinge": RAY_SIGNS,
        "ray_interval_degrees": [RAY_START_DEGREES, RAY_END_DEGREES],
        "sampling_protocol": {
            "uniform_step_degrees": UNIFORM_STEP_DEGREES,
            "uniform_sample_count": len(uniform_magnitudes),
            "contact_band_threshold": CONTACT_BAND_THRESHOLD,
            "contact_band_step_degrees": CONTACT_BAND_STEP_DEGREES,
            "contact_band_interval_count": len(contact_band_intervals),
            "contact_band_intervals_degrees": contact_band_intervals,
            "total_unique_sample_count": len(all_samples),
            "largest_gap_degrees_after_refinement": largest_gap,
        },
        "summary_metrics": {
            "blocked_sample_count": len(blocked_samples),
            "collision_free_sample_count": len(all_samples) - len(blocked_samples),
            "closest_nonzero_contact_sample": compact_sample(closest_nonzero) if closest_nonzero else None,
            "endpoint_sample": compact_sample(sample_cache[RAY_END_DEGREES]),
        },
        "blocked_samples": [compact_sample(sample) for sample in blocked_samples[:24]],
        "stored_samples": [compact_sample(sample) for sample in all_samples[:: max(1, len(all_samples) // 80)]],
        "limitations": [
            "This is a refined finite sampled audit, not a continuous interval certificate.",
            "The contact-band refinement densifies the sampled ray near small SAT-separation proxies but does not bound every unsampled angle analytically.",
            "The model remains zero-thickness: no hinge pins, offsets, clearances, or mesh printability are included.",
            "The supported claim is limited to the sampled ray and must not be promoted to a theorem without interval or analytic verification.",
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
                "total_unique_sample_count": report["sampling_protocol"]["total_unique_sample_count"],
                "blocked_sample_count": report["summary_metrics"]["blocked_sample_count"],
                "largest_gap_degrees_after_refinement": report["sampling_protocol"]["largest_gap_degrees_after_refinement"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())