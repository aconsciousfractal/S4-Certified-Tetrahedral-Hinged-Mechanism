"""Adaptive and transverse sampled audits for two signed-ray S4 representatives.

Representatives:
- TREE_007 for signed class {TREE_007, TREE_009}
- TREE_021 for signed class {TREE_021, TREE_093}

This is still a finite sampled audit, not a continuous interval certificate.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "two_class_representative_audit_report.json"
REPRESENTATIVES = {
    "CLASS_A_TREE007_TREE009": "TREE_007",
    "CLASS_B_TREE021_TREE093": "TREE_021",
}
RAY_INTERVAL_DEGREES = [0.0, 120.0]
ADAPTIVE_GLOBAL_STEP_DEGREES = 0.5
ADAPTIVE_CONTACT_THRESHOLD = 1.0e-3
ADAPTIVE_MIN_STEP_DEGREES = 0.0078125
TRANSVERSE_THETA_STATIONS = [0.5, 1, 2, 5, 10, 20, 45, 75, 105, 120]
TRANSVERSE_RADII_DEGREES = [0.0625, 0.125, 0.25, 0.5, 1.0, 2.0, 5.0]
TRANSVERSE_DIRECTION_COUNT = 8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_dense_report() -> dict:
    return load_json(RESULTS_DIR / "ambient_edge_dense_refinement_report.json")


def load_signed_report() -> dict:
    return load_json(RESULTS_DIR / "signed_ray_symmetry_report.json")


def find_tree(case: dict, tree_id: str) -> dict:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"Tree not found: {tree_id}")
    return tree


def certified_signs_by_tree(dense_report: dict) -> dict[str, dict[str, int]]:
    return {
        record["tree_id"]: {hinge_id: int(sign) for hinge_id, sign in record["ray_signs_by_hinge"].items()}
        for record in dense_report["tree_reports"]
    }


def ordered_hinge_ids(tree: dict) -> list[str]:
    return list(tree["hinge_ids"])


def sign_vector(tree: dict, signs_by_hinge: dict[str, int]) -> np.ndarray:
    return np.array([float(signs_by_hinge[hinge_id]) for hinge_id in ordered_hinge_ids(tree)], dtype=float)


def degrees_from_vector(tree: dict, values: np.ndarray) -> dict[str, float]:
    return {
        hinge_id: float(value)
        for hinge_id, value in zip(ordered_hinge_ids(tree), values)
    }


def ray_degrees(tree: dict, signs_by_hinge: dict[str, int], theta_degrees: float) -> dict[str, float]:
    return {
        hinge_id: float(signs_by_hinge[hinge_id]) * float(theta_degrees)
        for hinge_id in ordered_hinge_ids(tree)
    }


def evaluate(case: dict, tree: dict, degrees_by_hinge: dict[str, float]) -> dict:
    sample = batch.evaluate_tree_configuration(case, tree, degrees_by_hinge)
    return {
        "status": sample["status"],
        "collisions": sample["collisions"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
    }


def compact_ray_sample(theta: float, sample: dict) -> dict:
    return {
        "theta_degrees": round(float(theta), 8),
        "status": sample["status"],
        "collisions": sample["collisions"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
    }


def adaptive_ray_audit(case: dict, tree: dict, signs_by_hinge: dict[str, int]) -> dict:
    start, end = RAY_INTERVAL_DEGREES
    global_points = batch.degree_range(start, end, ADAPTIVE_GLOBAL_STEP_DEGREES)
    sample_cache: dict[float, dict] = {}
    terminal_intervals = []
    refined_interval_count = 0

    def sample(theta: float) -> dict:
        theta = round(float(theta), 8)
        if theta not in sample_cache:
            sample_cache[theta] = evaluate(case, tree, ray_degrees(tree, signs_by_hinge, theta))
        return sample_cache[theta]

    def should_refine(left_theta: float, right_theta: float, mid_theta: float) -> bool:
        values = [sample(left_theta), sample(mid_theta), sample(right_theta)]
        if any(value["status"] != "collision_free" for value in values):
            return True
        return any(abs(value["minimum_axis_overlap_proxy"] or 0.0) <= ADAPTIVE_CONTACT_THRESHOLD for value in values)

    def refine(left_theta: float, right_theta: float) -> None:
        nonlocal refined_interval_count
        left_theta = round(float(left_theta), 8)
        right_theta = round(float(right_theta), 8)
        width = round(right_theta - left_theta, 8)
        mid_theta = round((left_theta + right_theta) / 2.0, 8)
        sample(left_theta)
        sample(mid_theta)
        sample(right_theta)
        if width <= ADAPTIVE_MIN_STEP_DEGREES or not should_refine(left_theta, right_theta, mid_theta):
            terminal_intervals.append([left_theta, right_theta])
            return
        refined_interval_count += 1
        refine(left_theta, mid_theta)
        refine(mid_theta, right_theta)

    for left, right in zip(global_points, global_points[1:]):
        refine(left, right)

    all_thetas = sorted(sample_cache)
    all_samples = [(theta, sample_cache[theta]) for theta in all_thetas]
    blocked = [(theta, item) for theta, item in all_samples if item["status"] != "collision_free"]
    nonzero = [(theta, item) for theta, item in all_samples if theta > 0.0]
    closest_nonzero = min(nonzero, key=lambda item: abs(item[1]["minimum_axis_overlap_proxy"] or 0.0)) if nonzero else None
    largest_gap = max(round(right - left, 8) for left, right in zip(all_thetas, all_thetas[1:]))
    near_contact_samples = [
        compact_ray_sample(theta, item)
        for theta, item in all_samples
        if abs(item["minimum_axis_overlap_proxy"] or 0.0) <= ADAPTIVE_CONTACT_THRESHOLD
    ]

    return {
        "status": "adaptive_sampled_collision_free" if not blocked else "blocked_on_adaptive_sampling",
        "ray_interval_degrees": RAY_INTERVAL_DEGREES,
        "global_step_degrees": ADAPTIVE_GLOBAL_STEP_DEGREES,
        "contact_threshold": ADAPTIVE_CONTACT_THRESHOLD,
        "minimum_step_degrees": ADAPTIVE_MIN_STEP_DEGREES,
        "total_unique_sample_count": len(all_samples),
        "terminal_interval_count": len(terminal_intervals),
        "refined_interval_count": refined_interval_count,
        "largest_gap_degrees": largest_gap,
        "blocked_sample_count": len(blocked),
        "collision_free_sample_count": len(all_samples) - len(blocked),
        "closest_nonzero_contact_sample": compact_ray_sample(*closest_nonzero) if closest_nonzero else None,
        "endpoint_sample": compact_ray_sample(end, sample_cache[end]),
        "stored_near_contact_samples": near_contact_samples[:80],
        "blocked_samples": [compact_ray_sample(theta, item) for theta, item in blocked[:24]],
    }


def transverse_basis(signs: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    unit = signs / np.linalg.norm(signs)
    trial = np.array([1.0, -1.0, 0.0], dtype=float)
    if abs(float(np.dot(unit, trial / np.linalg.norm(trial)))) > 0.95:
        trial = np.array([1.0, 0.0, -1.0], dtype=float)
    e1 = trial - float(np.dot(trial, unit)) * unit
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(unit, e1)
    e2 = e2 / np.linalg.norm(e2)
    return e1, e2


def transverse_offset_vectors(signs: np.ndarray, radius: float) -> list[np.ndarray]:
    e1, e2 = transverse_basis(signs)
    vectors = []
    for index in range(TRANSVERSE_DIRECTION_COUNT):
        angle = 2.0 * math.pi * index / TRANSVERSE_DIRECTION_COUNT
        vector = float(radius) * (math.cos(angle) * e1 + math.sin(angle) * e2)
        vectors.append(vector)
    return vectors


def transverse_perturbation_audit(case: dict, tree: dict, signs_by_hinge: dict[str, int]) -> dict:
    sign_vec = sign_vector(tree, signs_by_hinge)
    sample_records = []
    station_reports = []
    total_samples = 0
    blocked_samples = 0

    for theta in TRANSVERSE_THETA_STATIONS:
        base_vector = sign_vec * float(theta)
        radius_reports = []
        max_all_direction_free_radius = None
        first_blocked_radius = None
        for radius in TRANSVERSE_RADII_DEGREES:
            direction_reports = []
            radius_blocked = False
            for direction_index, offset in enumerate(transverse_offset_vectors(sign_vec, radius)):
                total_samples += 1
                degrees_by_hinge = degrees_from_vector(tree, base_vector + offset)
                sample = evaluate(case, tree, degrees_by_hinge)
                if sample["status"] != "collision_free":
                    blocked_samples += 1
                    radius_blocked = True
                direction_record = {
                    "direction_index": direction_index,
                    "angle_degrees_by_hinge": {key: round(value, 8) for key, value in degrees_by_hinge.items()},
                    "status": sample["status"],
                    "collisions": sample["collisions"],
                    "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
                }
                direction_reports.append(direction_record)
                if sample["status"] != "collision_free" and len(sample_records) < 24:
                    sample_records.append(
                        {
                            "theta_degrees": theta,
                            "radius_degrees": radius,
                            **direction_record,
                        }
                    )
            radius_reports.append(
                {
                    "radius_degrees": radius,
                    "all_directions_collision_free": not radius_blocked,
                    "blocked_direction_count": sum(1 for item in direction_reports if item["status"] != "collision_free"),
                    "stored_direction_reports": direction_reports[:TRANSVERSE_DIRECTION_COUNT],
                }
            )
            if not radius_blocked:
                max_all_direction_free_radius = radius
            elif first_blocked_radius is None:
                first_blocked_radius = radius
        station_reports.append(
            {
                "theta_degrees": theta,
                "max_all_direction_free_radius_degrees": max_all_direction_free_radius,
                "first_blocked_radius_degrees": first_blocked_radius,
                "radius_reports": radius_reports,
            }
        )

    positive_radii = [
        report["max_all_direction_free_radius_degrees"]
        for report in station_reports
        if report["max_all_direction_free_radius_degrees"] is not None
    ]
    return {
        "status": "transverse_samples_completed",
        "theta_stations_degrees": TRANSVERSE_THETA_STATIONS,
        "radii_degrees": TRANSVERSE_RADII_DEGREES,
        "direction_count_per_radius": TRANSVERSE_DIRECTION_COUNT,
        "total_sample_count": total_samples,
        "blocked_sample_count": blocked_samples,
        "collision_free_sample_count": total_samples - blocked_samples,
        "minimum_all_direction_free_radius_degrees": min(positive_radii) if positive_radii else None,
        "station_reports": station_reports,
        "stored_blocked_samples": sample_records,
    }


def representative_report(case: dict, class_id: str, tree_id: str, signs_by_tree: dict[str, dict[str, int]]) -> dict:
    tree = find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    return {
        "class_id": class_id,
        "representative_tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs,
        "adaptive_ray_audit": adaptive_ray_audit(case, tree, signs),
        "transverse_perturbation_audit": transverse_perturbation_audit(case, tree, signs),
    }


def build_report() -> dict:
    case = batch.build_case()
    dense_report = load_dense_report()
    signed_report = load_signed_report()
    signs_by_tree = certified_signs_by_tree(dense_report)
    representative_reports = [
        representative_report(case, class_id, tree_id, signs_by_tree)
        for class_id, tree_id in REPRESENTATIVES.items()
    ]
    all_adaptive_free = all(
        report["adaptive_ray_audit"]["status"] == "adaptive_sampled_collision_free"
        for report in representative_reports
    )
    transverse_counts = {
        report["representative_tree_id"]: {
            "total": report["transverse_perturbation_audit"]["total_sample_count"],
            "blocked": report["transverse_perturbation_audit"]["blocked_sample_count"],
            "minimum_all_direction_free_radius_degrees": report["transverse_perturbation_audit"]["minimum_all_direction_free_radius_degrees"],
        }
        for report in representative_reports
    }
    return {
        "case_id": CASE_ID,
        "status": "two_class_representative_audit_completed",
        "source_signed_ray_classes": signed_report["summary_metrics"]["signed_ray_orbit_classes_root_preserving"],
        "representatives": REPRESENTATIVES,
        "adaptive_protocol": {
            "ray_interval_degrees": RAY_INTERVAL_DEGREES,
            "global_step_degrees": ADAPTIVE_GLOBAL_STEP_DEGREES,
            "contact_threshold": ADAPTIVE_CONTACT_THRESHOLD,
            "minimum_step_degrees": ADAPTIVE_MIN_STEP_DEGREES,
        },
        "transverse_protocol": {
            "theta_stations_degrees": TRANSVERSE_THETA_STATIONS,
            "radii_degrees": TRANSVERSE_RADII_DEGREES,
            "direction_count_per_radius": TRANSVERSE_DIRECTION_COUNT,
            "basis": "two orthonormal directions perpendicular to the signed ray vector in hinge-angle space",
        },
        "summary_metrics": {
            "adaptive_ray_collision_free_for_all_representatives": all_adaptive_free,
            "transverse_counts_by_tree": transverse_counts,
        },
        "representative_reports": representative_reports,
        "limitations": [
            "This is an adaptive finite sampled audit, not a rigorous interval certificate.",
            "Transverse perturbations test a finite tube around each ray and do not prove connectedness or disconnectedness of signed classes.",
            "The two representatives live on different hinge graphs, so this report compares local behavior rather than constructing a direct path between classes.",
            "No physical hinge thickness, offsets, clearances, mesh export, or printability gate is modeled.",
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
                "adaptive_ray_collision_free_for_all_representatives": report["summary_metrics"]["adaptive_ray_collision_free_for_all_representatives"],
                "transverse_counts_by_tree": report["summary_metrics"]["transverse_counts_by_tree"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())