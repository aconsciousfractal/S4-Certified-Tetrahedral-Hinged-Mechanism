"""Bounded component-graph certificate for S4 representatives.

This audit promotes the existing finite component-search graph by extracting a
spanning tree of the sampled free component and checking the midpoint of every
spanning-tree edge in the 3-parameter hinge-angle space.

It is still a finite bounded graph certificate. It does not certify every point
on every edge segment, every free graph edge, or the full continuous component.
"""

from __future__ import annotations

from collections import deque
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_component_graph_certificate_report.json"
SOURCE_COMPONENT_REPORT = "two_class_component_search_report.json"
MAX_STORED_EDGE_RECORDS = 80

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def node_angles(tree: dict, signs_by_hinge: dict[str, int], node: dict) -> dict[str, float]:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    base_vector = sign_vec * float(node["theta_degrees"])
    values = base_vector + comp.offset_for_node(sign_vec, node)
    return reps.degrees_from_vector(tree, values)


def all_nodes_by_id(tree: dict, signs_by_hinge: dict[str, int]) -> dict[str, dict]:
    output = {}
    for node in comp.all_node_records():
        output[node["node_id"]] = {
            **node,
            "angle_degrees_by_hinge": {
                key: round(value, 8)
                for key, value in node_angles(tree, signs_by_hinge, node).items()
            },
        }
    return output


def free_node_ids_from_source(source_audit: dict, nodes_by_id: dict[str, dict]) -> set[str]:
    blocked_ids = {node["node_id"] for node in source_audit["stored_blocked_nodes"]}
    expected_blocked = int(source_audit["summary_metrics"]["blocked_node_count"])
    if len(blocked_ids) != expected_blocked:
        raise RuntimeError(
            f"Source report did not store all blocked nodes for {source_audit['tree_id']}: "
            f"stored={len(blocked_ids)} expected={expected_blocked}"
        )
    return set(nodes_by_id) - blocked_ids


def spanning_tree_edges(start_id: str, free_ids: set[str], nodes_by_id: dict[str, dict]) -> list[tuple[str, str]]:
    seen = {start_id}
    queue: deque[str] = deque([start_id])
    edges: list[tuple[str, str]] = []
    while queue:
        current = queue.popleft()
        for neighbor in sorted(comp.neighbor_ids(nodes_by_id[current])):
            if neighbor not in free_ids or neighbor in seen:
                continue
            seen.add(neighbor)
            queue.append(neighbor)
            edges.append((current, neighbor))
    if seen != free_ids:
        missing = sorted(free_ids - seen)[:12]
        raise RuntimeError(f"Free graph is not connected from {start_id}; first missing nodes: {missing}")
    return edges


def midpoint_degrees(tree: dict, left: dict, right: dict) -> dict[str, float]:
    return {
        hinge_id: (float(left["angle_degrees_by_hinge"][hinge_id]) + float(right["angle_degrees_by_hinge"][hinge_id])) / 2.0
        for hinge_id in tree["hinge_ids"]
    }


def edge_length_degrees(tree: dict, left: dict, right: dict) -> dict:
    deltas = [
        float(right["angle_degrees_by_hinge"][hinge_id]) - float(left["angle_degrees_by_hinge"][hinge_id])
        for hinge_id in tree["hinge_ids"]
    ]
    return {
        "euclidean_degrees": round(float(np.linalg.norm(np.array(deltas, dtype=float))), 12),
        "max_coordinate_degrees": round(max(abs(delta) for delta in deltas), 12),
    }


def compact_edge_record(edge_id: str, left_id: str, right_id: str, left: dict, right: dict, midpoint: dict, sample: dict, length: dict) -> dict:
    return {
        "edge_id": edge_id,
        "node_ids": [left_id, right_id],
        "left_node": {
            "theta_degrees": left["theta_degrees"],
            "radius_degrees": left["radius_degrees"],
            "direction_index": left["direction_index"],
        },
        "right_node": {
            "theta_degrees": right["theta_degrees"],
            "radius_degrees": right["radius_degrees"],
            "direction_index": right["direction_index"],
        },
        "midpoint_angle_degrees_by_hinge": {key: round(value, 8) for key, value in midpoint.items()},
        "edge_length": length,
        "midpoint_status": sample["status"],
        "midpoint_minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
        "midpoint_collisions": sample["collisions"],
    }


def audit_tree(case: dict, source_audit: dict, signs_by_tree: dict[str, dict[str, int]]) -> dict:
    tree_id = source_audit["tree_id"]
    tree = comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    nodes_by_id = all_nodes_by_id(tree, signs)
    free_ids = free_node_ids_from_source(source_audit, nodes_by_id)
    start_id = comp.node_key(0, 0, None)
    edges = spanning_tree_edges(start_id, free_ids, nodes_by_id)

    blocked_midpoints = []
    stored_edges = []
    min_proxy = None
    closest_abs_proxy = None
    max_euclidean = 0.0
    max_coordinate = 0.0
    for index, (left_id, right_id) in enumerate(edges):
        left = nodes_by_id[left_id]
        right = nodes_by_id[right_id]
        midpoint = midpoint_degrees(tree, left, right)
        sample = reps.evaluate(case, tree, midpoint)
        length = edge_length_degrees(tree, left, right)
        max_euclidean = max(max_euclidean, float(length["euclidean_degrees"]))
        max_coordinate = max(max_coordinate, float(length["max_coordinate_degrees"]))
        proxy = sample["minimum_axis_overlap_proxy"]
        if proxy is not None:
            proxy = float(proxy)
            min_proxy = proxy if min_proxy is None else min(min_proxy, proxy)
            abs_proxy = abs(proxy)
            closest_abs_proxy = abs_proxy if closest_abs_proxy is None else min(closest_abs_proxy, abs_proxy)
        edge_id = f"{tree_id}_span_edge_{index:04d}"
        compact = None
        if index < MAX_STORED_EDGE_RECORDS or sample["status"] != "collision_free":
            compact = compact_edge_record(edge_id, left_id, right_id, left, right, midpoint, sample, length)
        if compact is not None and index < MAX_STORED_EDGE_RECORDS:
            stored_edges.append(compact)
        if sample["status"] != "collision_free":
            blocked_midpoints.append(compact or compact_edge_record(edge_id, left_id, right_id, left, right, midpoint, sample, length))

    all_midpoints_free = not blocked_midpoints
    ray_node_ids = [comp.node_key(theta_index, 0, None) for theta_index in range(len(comp.THETA_STATIONS_DEGREES))]
    return {
        "class_id": source_audit["class_id"],
        "tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs,
        "status": "bounded_spanning_tree_midpoint_certificate_completed" if all_midpoints_free else "bounded_spanning_tree_midpoint_certificate_failed",
        "source_component_summary_metrics": source_audit["summary_metrics"],
        "bounded_graph_protocol": {
            "theta_stations_degrees": comp.THETA_STATIONS_DEGREES,
            "radii_degrees": comp.RADII_DEGREES,
            "direction_count": comp.DIRECTION_COUNT,
            "start_node_id": start_id,
            "edge_set": "BFS spanning tree of the sampled free component",
            "edge_guard": "collision check at the arithmetic midpoint in hinge-angle coordinates",
        },
        "summary_metrics": {
            "node_count": len(nodes_by_id),
            "free_node_count": len(free_ids),
            "blocked_node_count": len(nodes_by_id) - len(free_ids),
            "spanning_tree_edge_count": len(edges),
            "expected_spanning_tree_edge_count": len(free_ids) - 1,
            "all_free_nodes_reached_by_spanning_tree": len(edges) == len(free_ids) - 1,
            "all_spanning_tree_midpoints_collision_free": all_midpoints_free,
            "blocked_midpoint_count": len(blocked_midpoints),
            "ray_nodes_in_free_spanning_component": all(node_id in free_ids for node_id in ray_node_ids),
            "max_spanning_edge_euclidean_length_degrees": round(max_euclidean, 12),
            "max_spanning_edge_coordinate_delta_degrees": round(max_coordinate, 12),
            "minimum_midpoint_axis_overlap_proxy": None if min_proxy is None else round(min_proxy, 12),
            "closest_abs_midpoint_axis_overlap_proxy": None if closest_abs_proxy is None else round(closest_abs_proxy, 12),
        },
        "stored_spanning_tree_edge_midpoints": stored_edges,
        "stored_blocked_midpoints": blocked_midpoints[:MAX_STORED_EDGE_RECORDS],
    }


def build_report() -> dict:
    case = batch.build_case()
    source_report = load_json(RESULTS_DIR / SOURCE_COMPONENT_REPORT)
    signs_by_tree = comp.certified_signs_by_tree()
    tree_reports = [audit_tree(case, audit, signs_by_tree) for audit in source_report["representative_audits"]]
    return {
        "case_id": CASE_ID,
        "status": "bounded_component_graph_certificate_completed" if all(
            report["summary_metrics"]["all_spanning_tree_midpoints_collision_free"] for report in tree_reports
        ) else "bounded_component_graph_certificate_incomplete",
        "source_reports": [f"results/{CASE_ID}/{SOURCE_COMPONENT_REPORT}"],
        "summary_metrics": {
            "representative_count": len(tree_reports),
            "all_source_free_graphs_connected": all(
                report["source_component_summary_metrics"]["component_count"] == 1 for report in tree_reports
            ),
            "all_spanning_tree_midpoints_collision_free": all(
                report["summary_metrics"]["all_spanning_tree_midpoints_collision_free"] for report in tree_reports
            ),
            "total_spanning_tree_edges_checked": sum(
                report["summary_metrics"]["spanning_tree_edge_count"] for report in tree_reports
            ),
            "total_blocked_midpoints": sum(
                report["summary_metrics"]["blocked_midpoint_count"] for report in tree_reports
            ),
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This is a finite bounded graph certificate, not a continuous 3-parameter component proof.",
            "Only a BFS spanning tree of the sampled free component is midpoint-checked; not every free graph edge is part of the certificate.",
            "A midpoint collision-free check does not certify the whole straight segment between two sampled nodes.",
            "The certificate does not connect TREE_007 to TREE_021; they remain representatives of different hinge-tree classes.",
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