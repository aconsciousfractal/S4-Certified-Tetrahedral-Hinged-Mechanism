"""Refine coarse edges in the bounded S4 component-graph certificate.

This audit subdivides every BFS spanning-tree edge from the bounded component
certificate until each refined segment has max hinge-coordinate delta at most
5 degrees. It samples all new subdivision points and verifies that they remain
collision-free.

This prepares the graph for a later interval-edge guard, but it is still finite
point sampling, not a continuous edge-segment certificate.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_component_edge_refinement_report.json"
SOURCE_BOUNDED_REPORT = "bounded_component_graph_certificate_report.json"
SOURCE_COMPONENT_REPORT = "two_class_component_search_report.json"
MAX_COORDINATE_DELTA_DEGREES = 5.0
MAX_STORED_RECORDS = 80

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def angle_vector(tree: dict, node: dict) -> np.ndarray:
    return np.array([float(node["angle_degrees_by_hinge"][hinge_id]) for hinge_id in tree["hinge_ids"]], dtype=float)


def vector_to_degrees(tree: dict, vector: np.ndarray) -> dict[str, float]:
    return {hinge_id: float(value) for hinge_id, value in zip(tree["hinge_ids"], vector)}


def sample_key(vector: np.ndarray) -> tuple[float, ...]:
    return tuple(round(float(value), 10) for value in vector)


def segment_delta(left: np.ndarray, right: np.ndarray) -> dict:
    deltas = right - left
    return {
        "euclidean_degrees": round(float(np.linalg.norm(deltas)), 12),
        "max_coordinate_degrees": round(float(np.max(np.abs(deltas))), 12),
    }


def compact_sample(tree: dict, vector: np.ndarray, sample: dict) -> dict:
    return {
        "angle_degrees_by_hinge": {hinge_id: round(float(value), 8) for hinge_id, value in zip(tree["hinge_ids"], vector)},
        "status": sample["status"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
        "collisions": sample["collisions"],
    }


def evaluate_cached(case: dict, tree: dict, vector: np.ndarray, cache: dict[tuple[float, ...], dict]) -> dict:
    key = sample_key(vector)
    if key not in cache:
        cache[key] = reps.evaluate(case, tree, vector_to_degrees(tree, vector))
    return cache[key]


def audit_tree(case: dict, source_audit: dict, signs_by_tree: dict[str, dict[str, int]]) -> dict:
    tree_id = source_audit["tree_id"]
    tree = comp.find_tree(case, tree_id)
    nodes_by_id = bounded.all_nodes_by_id(tree, signs_by_tree[tree_id])
    free_ids = bounded.free_node_ids_from_source(source_audit, nodes_by_id)
    edges = bounded.spanning_tree_edges(comp.node_key(0, 0, None), free_ids, nodes_by_id)

    cache: dict[tuple[float, ...], dict] = {}
    stored_refined_edges = []
    blocked_samples = []
    total_interior_samples = 0
    total_refined_segments = 0
    refined_edges_with_subdivision = 0
    max_original_coordinate_delta = 0.0
    max_refined_coordinate_delta = 0.0
    closest_abs_proxy = None
    min_proxy = None

    for edge_index, (left_id, right_id) in enumerate(edges):
        left = angle_vector(tree, nodes_by_id[left_id])
        right = angle_vector(tree, nodes_by_id[right_id])
        original_delta = segment_delta(left, right)
        max_original_coordinate_delta = max(max_original_coordinate_delta, original_delta["max_coordinate_degrees"])
        segment_count = max(1, math.ceil(original_delta["max_coordinate_degrees"] / MAX_COORDINATE_DELTA_DEGREES))
        if segment_count > 1:
            refined_edges_with_subdivision += 1
        total_refined_segments += segment_count
        previous = left
        stored_interior = []
        edge_blocked = []
        for step in range(1, segment_count):
            t = float(step) / float(segment_count)
            current = (1.0 - t) * left + t * right
            total_interior_samples += 1
            sample = evaluate_cached(case, tree, current, cache)
            proxy = sample["minimum_axis_overlap_proxy"]
            if proxy is not None:
                proxy = float(proxy)
                min_proxy = proxy if min_proxy is None else min(min_proxy, proxy)
                abs_proxy = abs(proxy)
                closest_abs_proxy = abs_proxy if closest_abs_proxy is None else min(closest_abs_proxy, abs_proxy)
            if len(stored_interior) < 6:
                stored_interior.append(compact_sample(tree, current, sample))
            if sample["status"] != "collision_free":
                edge_blocked.append(compact_sample(tree, current, sample))
            refined_delta = segment_delta(previous, current)
            max_refined_coordinate_delta = max(max_refined_coordinate_delta, refined_delta["max_coordinate_degrees"])
            previous = current
        refined_delta = segment_delta(previous, right)
        max_refined_coordinate_delta = max(max_refined_coordinate_delta, refined_delta["max_coordinate_degrees"])
        if edge_blocked:
            blocked_samples.extend(edge_blocked)
        if edge_index < MAX_STORED_RECORDS or edge_blocked or segment_count > 1:
            if len(stored_refined_edges) < MAX_STORED_RECORDS:
                stored_refined_edges.append(
                    {
                        "edge_index": edge_index,
                        "node_ids": [left_id, right_id],
                        "original_delta": original_delta,
                        "segment_count": segment_count,
                        "interior_sample_count": max(0, segment_count - 1),
                        "blocked_interior_sample_count": len(edge_blocked),
                        "stored_interior_samples": stored_interior,
                    }
                )

    all_collision_free = not blocked_samples
    return {
        "tree_id": tree_id,
        "class_id": source_audit["class_id"],
        "status": "bounded_component_edge_refinement_completed" if all_collision_free else "bounded_component_edge_refinement_failed",
        "summary_metrics": {
            "original_spanning_tree_edge_count": len(edges),
            "refined_edges_with_subdivision_count": refined_edges_with_subdivision,
            "refined_segment_count": total_refined_segments,
            "interior_sample_count": total_interior_samples,
            "unique_interior_sample_count": len(cache),
            "blocked_interior_sample_count": len(blocked_samples),
            "all_interior_samples_collision_free": all_collision_free,
            "max_original_coordinate_delta_degrees": round(max_original_coordinate_delta, 12),
            "max_refined_coordinate_delta_degrees": round(max_refined_coordinate_delta, 12),
            "target_max_coordinate_delta_degrees": MAX_COORDINATE_DELTA_DEGREES,
            "minimum_interior_axis_overlap_proxy": None if min_proxy is None else round(min_proxy, 12),
            "closest_abs_interior_axis_overlap_proxy": None if closest_abs_proxy is None else round(closest_abs_proxy, 12),
        },
        "stored_refined_edges": stored_refined_edges,
        "stored_blocked_samples": blocked_samples[:MAX_STORED_RECORDS],
    }


def build_report() -> dict:
    case = batch.build_case()
    bounded_report = bounded.load_json(RESULTS_DIR / SOURCE_BOUNDED_REPORT)
    component_report = bounded.load_json(RESULTS_DIR / SOURCE_COMPONENT_REPORT)
    signs_by_tree = comp.certified_signs_by_tree()
    bounded_tree_ids = {audit["tree_id"] for audit in bounded_report["tree_reports"]}
    source_by_tree = {
        audit["tree_id"]: audit
        for audit in component_report["representative_audits"]
        if audit["tree_id"] in bounded_tree_ids
    }
    tree_reports = [audit_tree(case, source_by_tree[tree_id], signs_by_tree) for tree_id in sorted(source_by_tree)]
    all_free = all(report["summary_metrics"]["all_interior_samples_collision_free"] for report in tree_reports)
    return {
        "case_id": CASE_ID,
        "status": "bounded_component_edge_refinement_completed" if all_free else "bounded_component_edge_refinement_incomplete",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_BOUNDED_REPORT}",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "refinement_protocol": {
            "edge_set": "BFS spanning tree from bounded_component_graph_certificate_report.json",
            "target_max_coordinate_delta_degrees": MAX_COORDINATE_DELTA_DEGREES,
            "sample_rule": "evaluate every newly inserted subdivision point; source endpoints are inherited from the bounded component graph certificate",
        },
        "summary_metrics": {
            "representative_count": len(tree_reports),
            "all_interior_samples_collision_free": all_free,
            "total_original_spanning_tree_edges": sum(report["summary_metrics"]["original_spanning_tree_edge_count"] for report in tree_reports),
            "total_refined_segments": sum(report["summary_metrics"]["refined_segment_count"] for report in tree_reports),
            "total_interior_samples": sum(report["summary_metrics"]["interior_sample_count"] for report in tree_reports),
            "total_unique_interior_samples": sum(report["summary_metrics"]["unique_interior_sample_count"] for report in tree_reports),
            "total_blocked_interior_samples": sum(report["summary_metrics"]["blocked_interior_sample_count"] for report in tree_reports),
            "max_refined_coordinate_delta_degrees": max(report["summary_metrics"]["max_refined_coordinate_delta_degrees"] for report in tree_reports),
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This is finite subdivision-point sampling, not an interval edge guard.",
            "Only the spanning-tree edges from the bounded component graph certificate are refined, not every free graph edge.",
            "Endpoints are inherited from the previous finite graph certificate; this audit samples newly inserted interior points only.",
            "The result prepares smaller segments for a later interval-guard audit but does not prove continuous edge safety.",
            "No physical hinge offsets, clearances, thickness, mesh export, or printability gates are modeled.",
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
                    report["tree_id"]: report["summary_metrics"] for report in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())