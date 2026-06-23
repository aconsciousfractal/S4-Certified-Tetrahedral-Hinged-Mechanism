"""Dense refinement for the four all-ambient-edge S4 hinge trees."""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "ambient_edge_dense_refinement_report.json"
REPORT_DIR_NAME = "ambient_edge_dense_refinements"
TARGET_TREE_IDS = ["TREE_007", "TREE_009", "TREE_021", "TREE_093"]
DENSE_START_DEGREES = 0.0
DENSE_END_DEGREES = 120.0
DENSE_UNIFORM_STEP_DEGREES = 0.25
DENSE_CONTACT_BAND_THRESHOLD = 1.0e-3
DENSE_CONTACT_BAND_STEP_DEGREES = 0.03125
AMBIENT_EDGE_AXIS_BY_ID = {
    "H0_A_M_AB": {"ambient_edge": "AB", "half_axis_vertex": "A"},
    "H9_B_M_AB": {"ambient_edge": "AB", "half_axis_vertex": "B"},
    "H4_C_M_CD": {"ambient_edge": "CD", "half_axis_vertex": "C"},
    "H7_D_M_CD": {"ambient_edge": "CD", "half_axis_vertex": "D"},
}

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID
REPORTS_DIR = RESULTS_DIR / REPORT_DIR_NAME


def compact_sample(magnitude: float, sample: dict) -> dict:
    return {
        "magnitude_degrees": round(float(magnitude), 8),
        "status": sample["status"],
        "collisions": sample["collisions"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
    }


def find_tree(case: dict, tree_id: str) -> dict:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"Tree not found: {tree_id}")
    return tree


def dense_refine_tree(case: dict, tree: dict, sign_vector_by_hinge: dict[str, int]) -> dict:
    uniform_magnitudes = batch.degree_range(DENSE_START_DEGREES, DENSE_END_DEGREES, DENSE_UNIFORM_STEP_DEGREES)
    hinge_ids = tree["hinge_ids"]
    signs = tuple(int(sign_vector_by_hinge[hinge_id]) for hinge_id in hinge_ids)
    sample_cache: dict[float, dict] = {}

    for magnitude in uniform_magnitudes:
        signed_degrees = batch.signed_degrees_from_vector(hinge_ids, signs, magnitude)
        sample_cache[magnitude] = batch.evaluate_tree_configuration(case, tree, signed_degrees)

    contact_band_intervals = []
    for left, right in zip(uniform_magnitudes, uniform_magnitudes[1:]):
        left_sample = sample_cache[left]
        right_sample = sample_cache[right]
        left_proxy = left_sample["minimum_axis_overlap_proxy"] or 0.0
        right_proxy = right_sample["minimum_axis_overlap_proxy"] or 0.0
        left_near = abs(left_proxy) <= DENSE_CONTACT_BAND_THRESHOLD
        right_near = abs(right_proxy) <= DENSE_CONTACT_BAND_THRESHOLD
        if left_sample["status"] != "collision_free" or right_sample["status"] != "collision_free" or left_near or right_near:
            contact_band_intervals.append([left, right])
            for magnitude in batch.degree_range(left, right, DENSE_CONTACT_BAND_STEP_DEGREES):
                if magnitude not in sample_cache:
                    signed_degrees = batch.signed_degrees_from_vector(hinge_ids, signs, magnitude)
                    sample_cache[magnitude] = batch.evaluate_tree_configuration(case, tree, signed_degrees)

    all_magnitudes = sorted(sample_cache)
    all_samples = [(magnitude, sample_cache[magnitude]) for magnitude in all_magnitudes]
    blocked_samples = [(magnitude, sample) for magnitude, sample in all_samples if sample["status"] != "collision_free"]
    nonzero_samples = [(magnitude, sample) for magnitude, sample in all_samples if magnitude > 0.0]
    closest_nonzero = None
    if nonzero_samples:
        closest_nonzero = min(nonzero_samples, key=lambda item: abs(item[1]["minimum_axis_overlap_proxy"] or 0.0))
    largest_gap = max(round(right - left, 8) for left, right in zip(all_magnitudes, all_magnitudes[1:]))
    endpoint = (DENSE_END_DEGREES, sample_cache[DENSE_END_DEGREES])

    return {
        "status": "dense_refined_sampled_collision_free" if not blocked_samples else "blocked_on_dense_refinement",
        "sign_vector_by_hinge": sign_vector_by_hinge,
        "ray_interval_degrees": [DENSE_START_DEGREES, DENSE_END_DEGREES],
        "uniform_step_degrees": DENSE_UNIFORM_STEP_DEGREES,
        "contact_band_threshold": DENSE_CONTACT_BAND_THRESHOLD,
        "contact_band_step_degrees": DENSE_CONTACT_BAND_STEP_DEGREES,
        "contact_band_interval_count": len(contact_band_intervals),
        "contact_band_intervals_degrees": contact_band_intervals,
        "total_unique_sample_count": len(all_samples),
        "largest_gap_degrees_after_refinement": largest_gap,
        "blocked_sample_count": len(blocked_samples),
        "collision_free_sample_count": len(all_samples) - len(blocked_samples),
        "closest_nonzero_contact_sample": compact_sample(*closest_nonzero) if closest_nonzero else None,
        "endpoint_sample": compact_sample(*endpoint),
        "blocked_samples": [compact_sample(*item) for item in blocked_samples[:24]],
        "stored_samples": [compact_sample(*item) for item in all_samples[:: max(1, len(all_samples) // 80)]],
    }


def symmetry_signature(tree: dict) -> dict:
    ambient_axis_set = set(AMBIENT_EDGE_AXIS_BY_ID)
    used_axis_set = set(tree["hinge_ids"])
    missing = sorted(ambient_axis_set - used_axis_set)
    used_by_edge = {"AB": [], "CD": []}
    for hinge_id in tree["hinge_ids"]:
        metadata = AMBIENT_EDGE_AXIS_BY_ID[hinge_id]
        used_by_edge[metadata["ambient_edge"]].append(hinge_id)
    return {
        "ambient_edge_axis_universe": sorted(ambient_axis_set),
        "used_ambient_edge_axes": tree["hinge_ids"],
        "missing_ambient_edge_axis": missing[0] if len(missing) == 1 else missing,
        "missing_half_axis_vertex": AMBIENT_EDGE_AXIS_BY_ID[missing[0]]["half_axis_vertex"] if len(missing) == 1 else None,
        "used_axes_by_ambient_edge": used_by_edge,
        "structural_type": "three_of_four_half_axes_on_opposite_edges_AB_CD",
    }


def canonical_edge(edge: tuple[str, str]) -> tuple[str, str]:
    return tuple(sorted(edge))


def axis_id_for(vertex: str, edge: tuple[str, str]) -> str:
    edge = canonical_edge(edge)
    edge_name = "".join(edge)
    for hinge_id, metadata in AMBIENT_EDGE_AXIS_BY_ID.items():
        if metadata["half_axis_vertex"] == vertex and metadata["ambient_edge"] == edge_name:
            return hinge_id
    raise KeyError(f"No ambient-edge half-axis for vertex={vertex}, edge={edge}")


def opposite_edge_stabilizer_permutations() -> list[dict[str, str]]:
    vertices = ["A", "B", "C", "D"]
    target_pair = {canonical_edge(("A", "B")), canonical_edge(("C", "D"))}
    permutations = []
    for image_tuple in itertools.permutations(vertices):
        mapping = dict(zip(vertices, image_tuple))
        mapped_pair = {
            canonical_edge((mapping["A"], mapping["B"])),
            canonical_edge((mapping["C"], mapping["D"])),
        }
        if mapped_pair == target_pair:
            permutations.append(mapping)
    return permutations


def map_axis_id(hinge_id: str, permutation: dict[str, str]) -> str:
    metadata = AMBIENT_EDGE_AXIS_BY_ID[hinge_id]
    source_vertex = metadata["half_axis_vertex"]
    source_edge = tuple(metadata["ambient_edge"])
    mapped_vertex = permutation[source_vertex]
    mapped_edge = (permutation[source_edge[0]], permutation[source_edge[1]])
    return axis_id_for(mapped_vertex, mapped_edge)


def axis_set_orbit_check(tree_reports: list[dict]) -> dict:
    permutations = opposite_edge_stabilizer_permutations()
    tree_axis_sets = {
        report["tree_id"]: set(report["selected_tree"]["hinge_ids"])
        for report in tree_reports
    }
    base_tree_id = tree_reports[0]["tree_id"]
    base_axis_set = tree_axis_sets[base_tree_id]
    targets = {}
    for target_tree_id, target_axis_set in tree_axis_sets.items():
        match = None
        for permutation in permutations:
            mapped_axis_set = {map_axis_id(hinge_id, permutation) for hinge_id in base_axis_set}
            if mapped_axis_set == target_axis_set:
                match = {
                    "permutation": permutation,
                    "mapped_axis_set": sorted(mapped_axis_set),
                }
                break
        targets[target_tree_id] = match
    return {
        "group": "vertex permutations preserving unordered opposite-edge pair {AB, CD}",
        "permutation_count": len(permutations),
        "base_tree_id": base_tree_id,
        "all_targets_reached_from_base_axis_set": all(value is not None for value in targets.values()),
        "targets": targets,
        "certifies": "axis_set_orbit_only",
        "does_not_certify": "signed_ray_or_continuous_motion_equivalence",
    }


def tree_report(case: dict, tree_id: str, sign_vector_by_hinge: dict[str, int]) -> dict:
    tree = find_tree(case, tree_id)
    if tree["ambient_edge_axis_count"] != 3:
        raise RuntimeError(f"{tree_id} is not all-ambient-edge")
    selected_hinges = batch.selected_hinges_for_tree(case, tree)
    refinement = dense_refine_tree(case, tree, sign_vector_by_hinge)
    return {
        "case_id": CASE_ID,
        "tree_id": tree_id,
        "status": refinement["status"],
        "selected_tree": tree,
        "selected_hinges": selected_hinges,
        "symmetry_signature": symmetry_signature(tree),
        "dense_refinement": refinement,
        "limitations": [
            "This is a dense finite sampled audit, not a continuous interval certificate.",
            "All models are zero-thickness and omit physical hinge offsets, pin radii, clearances, mesh export, and printability gates.",
            "The symmetry comparison certifies only the hinge-axis-set orbit, not signed ray or continuous motion equivalence.",
        ],
    }


def comparison_report(tree_reports: list[dict]) -> dict:
    passing = [report for report in tree_reports if report["status"] == "dense_refined_sampled_collision_free"]
    signatures = [report["symmetry_signature"] for report in tree_reports]
    sample_counts = sorted({report["dense_refinement"]["total_unique_sample_count"] for report in tree_reports})
    contact_counts = sorted({report["dense_refinement"]["contact_band_interval_count"] for report in tree_reports})
    endpoint_proxies = {
        report["tree_id"]: report["dense_refinement"]["endpoint_sample"]["minimum_axis_overlap_proxy"]
        for report in tree_reports
    }
    axis_orbit = axis_set_orbit_check(tree_reports)
    return {
        "case_id": CASE_ID,
        "status": "ambient_edge_dense_refinement_completed" if len(passing) == len(tree_reports) else "ambient_edge_dense_refinement_has_blocks",
        "tree_ids": [report["tree_id"] for report in tree_reports],
        "dense_protocol": {
            "interval_degrees": [DENSE_START_DEGREES, DENSE_END_DEGREES],
            "uniform_step_degrees": DENSE_UNIFORM_STEP_DEGREES,
            "contact_band_threshold": DENSE_CONTACT_BAND_THRESHOLD,
            "contact_band_step_degrees": DENSE_CONTACT_BAND_STEP_DEGREES,
        },
        "summary_metrics": {
            "tested_tree_count": len(tree_reports),
            "dense_refined_sampled_collision_free_tree_count": len(passing),
            "sample_count_values": sample_counts,
            "contact_band_interval_count_values": contact_counts,
            "endpoint_minimum_axis_overlap_proxy_by_tree": endpoint_proxies,
        },
        "symmetry_comparison": {
            "structural_inference": "The four trees are the four choices of one missing half-axis from the ambient-edge-axis universe {A-M_AB, B-M_AB, C-M_CD, D-M_CD}.",
            "axis_set_orbit_check": axis_orbit,
            "likely_orbit": "The four hinge-axis sets are formally in one orbit under the vertex permutations preserving the unordered opposite-edge pair {AB, CD}.",
            "formal_status": "axis_sets_certified_same_orbit; signed_ray_equivalence_not_certified",
            "sign_patterns_by_tree": {
                report["tree_id"]: report["dense_refinement"]["sign_vector_by_hinge"]
                for report in tree_reports
            },
            "missing_half_axis_by_tree": {
                report["tree_id"]: report["symmetry_signature"]["missing_half_axis_vertex"]
                for report in tree_reports
            },
            "signatures": signatures,
        },
        "tree_reports": [
            {
                "tree_id": report["tree_id"],
                "status": report["status"],
                "hinge_ids": report["selected_tree"]["hinge_ids"],
                "ray_signs_by_hinge": report["dense_refinement"]["sign_vector_by_hinge"],
                "total_unique_sample_count": report["dense_refinement"]["total_unique_sample_count"],
                "contact_band_interval_count": report["dense_refinement"]["contact_band_interval_count"],
                "endpoint_sample": report["dense_refinement"]["endpoint_sample"],
                "symmetry_signature": report["symmetry_signature"],
            }
            for report in tree_reports
        ],
        "limitations": [
            "Dense sampled reports are stronger finite evidence than the batch ranking protocol, but still not interval certificates.",
            "The axis sets are certified in one symmetry orbit; signed ray and continuous motion equivalence are not certified by this script.",
            "No physical hinge offsets or printable clearances are modeled.",
        ],
    }


def main() -> int:
    case = batch.build_case()
    batch_report_path = RESULTS_DIR / "boundary_tree_batch_report.json"
    if not batch_report_path.exists():
        raise RuntimeError(f"Missing batch report: {batch_report_path}")
    with batch_report_path.open("r", encoding="utf-8") as handle:
        batch_report = json.load(handle)
    sign_vectors = {
        record["tree_id"]: record["refinement"]["first_refined_free_ray"]["sign_vector_by_hinge"]
        for record in batch_report["tree_records"]
        if record["tree_id"] in TARGET_TREE_IDS
    }
    missing = sorted(set(TARGET_TREE_IDS) - set(sign_vectors))
    if missing:
        raise RuntimeError(f"Missing sign vectors for: {missing}")

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    reports = []
    for tree_id in TARGET_TREE_IDS:
        report = tree_report(case, tree_id, sign_vectors[tree_id])
        reports.append(report)
        lib.write_json(REPORTS_DIR / f"{tree_id}_dense_refinement.json", report)

    comparison = comparison_report(reports)
    lib.write_json(RESULTS_DIR / REPORT_NAME, comparison)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": comparison["status"],
                "tested_tree_count": comparison["summary_metrics"]["tested_tree_count"],
                "passing_tree_count": comparison["summary_metrics"]["dense_refined_sampled_collision_free_tree_count"],
                "sample_count_values": comparison["summary_metrics"]["sample_count_values"],
                "contact_band_interval_count_values": comparison["summary_metrics"]["contact_band_interval_count_values"],
                "axis_sets_same_orbit": comparison["symmetry_comparison"]["axis_set_orbit_check"]["all_targets_reached_from_base_axis_set"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())