"""Finite component-search graph for two S4 signed-ray representatives.

This audit samples a cylindrical graph around each representative ray in the
3-parameter hinge-angle space. It is a graph-level finite search, not a proof of
continuous connectedness.
"""

from __future__ import annotations

from collections import deque
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "two_class_component_search_report.json"
REPRESENTATIVES = {
    "CLASS_A_TREE007_TREE009": "TREE_007",
    "CLASS_B_TREE021_TREE093": "TREE_021",
}
THETA_STATIONS_DEGREES = [0.5, 1, 2, 5, 10, 20, 45, 75, 105, 120]
RADII_DEGREES = [0.0, 0.125, 0.25, 0.5, 1.0, 2.0, 5.0]
DIRECTION_COUNT = 16
MAX_STORED_NODES = 96

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def certified_signs_by_tree() -> dict[str, dict[str, int]]:
    dense_report = load_json(RESULTS_DIR / "ambient_edge_dense_refinement_report.json")
    return {
        record["tree_id"]: {hinge_id: int(sign) for hinge_id, sign in record["ray_signs_by_hinge"].items()}
        for record in dense_report["tree_reports"]
    }


def find_tree(case: dict, tree_id: str) -> dict:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"Tree not found: {tree_id}")
    return tree


def node_key(theta_index: int, radius_index: int, direction_index: int | None) -> str:
    direction_token = "C" if direction_index is None else str(direction_index)
    return f"t{theta_index}:r{radius_index}:d{direction_token}"


def node_record(theta_index: int, radius_index: int, direction_index: int | None) -> dict:
    return {
        "node_id": node_key(theta_index, radius_index, direction_index),
        "theta_index": theta_index,
        "theta_degrees": THETA_STATIONS_DEGREES[theta_index],
        "radius_index": radius_index,
        "radius_degrees": RADII_DEGREES[radius_index],
        "direction_index": direction_index,
    }


def all_node_records() -> list[dict]:
    records = []
    for theta_index in range(len(THETA_STATIONS_DEGREES)):
        records.append(node_record(theta_index, 0, None))
        for radius_index in range(1, len(RADII_DEGREES)):
            for direction_index in range(DIRECTION_COUNT):
                records.append(node_record(theta_index, radius_index, direction_index))
    return records


def offset_for_node(sign_vec: np.ndarray, node: dict) -> np.ndarray:
    radius = float(node["radius_degrees"])
    if radius == 0.0:
        return np.zeros(3)
    e1, e2 = reps.transverse_basis(sign_vec)
    angle = 2.0 * math.pi * int(node["direction_index"]) / DIRECTION_COUNT
    return radius * (math.cos(angle) * e1 + math.sin(angle) * e2)


def evaluate_node(case: dict, tree: dict, signs_by_hinge: dict[str, int], node: dict) -> dict:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    base_vector = sign_vec * float(node["theta_degrees"])
    degrees_by_hinge = reps.degrees_from_vector(tree, base_vector + offset_for_node(sign_vec, node))
    sample = reps.evaluate(case, tree, degrees_by_hinge)
    return {
        **node,
        "angle_degrees_by_hinge": {key: round(value, 8) for key, value in degrees_by_hinge.items()},
        "status": sample["status"],
        "collisions": sample["collisions"],
        "minimum_axis_overlap_proxy": sample["minimum_axis_overlap_proxy"],
    }


def neighbor_ids(node: dict) -> list[str]:
    theta_index = int(node["theta_index"])
    radius_index = int(node["radius_index"])
    direction_index = node["direction_index"]
    neighbors = []

    for next_theta in [theta_index - 1, theta_index + 1]:
        if 0 <= next_theta < len(THETA_STATIONS_DEGREES):
            neighbors.append(node_key(next_theta, radius_index, direction_index))

    if radius_index == 0:
        for direction in range(DIRECTION_COUNT):
            neighbors.append(node_key(theta_index, 1, direction))
        return neighbors

    if radius_index == 1:
        neighbors.append(node_key(theta_index, 0, None))
    else:
        neighbors.append(node_key(theta_index, radius_index - 1, direction_index))
    if radius_index + 1 < len(RADII_DEGREES):
        neighbors.append(node_key(theta_index, radius_index + 1, direction_index))

    left_direction = (int(direction_index) - 1) % DIRECTION_COUNT
    right_direction = (int(direction_index) + 1) % DIRECTION_COUNT
    neighbors.append(node_key(theta_index, radius_index, left_direction))
    neighbors.append(node_key(theta_index, radius_index, right_direction))
    return neighbors


def connected_components(free_node_ids: set[str], nodes_by_id: dict[str, dict]) -> tuple[dict[str, int], list[list[str]]]:
    component_by_node = {}
    components = []
    for start in sorted(free_node_ids):
        if start in component_by_node:
            continue
        component_index = len(components)
        queue = deque([start])
        component = []
        component_by_node[start] = component_index
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in neighbor_ids(nodes_by_id[current]):
                if neighbor not in free_node_ids or neighbor in component_by_node:
                    continue
                component_by_node[neighbor] = component_index
                queue.append(neighbor)
        components.append(sorted(component))
    return component_by_node, components


def radius_profile_for_component(component_ids: set[str], nodes_by_id: dict[str, dict]) -> list[dict]:
    profile = []
    for theta_index, theta in enumerate(THETA_STATIONS_DEGREES):
        max_any = None
        max_all = None
        for radius_index, radius in enumerate(RADII_DEGREES):
            if radius_index == 0:
                node_ids = [node_key(theta_index, 0, None)]
            else:
                node_ids = [node_key(theta_index, radius_index, direction) for direction in range(DIRECTION_COUNT)]
            present_count = sum(1 for node_id in node_ids if node_id in component_ids)
            if present_count > 0:
                max_any = radius
            if present_count == len(node_ids):
                max_all = radius
        profile.append(
            {
                "theta_degrees": theta,
                "max_any_direction_radius_in_component_degrees": max_any,
                "max_all_direction_radius_in_component_degrees": max_all,
            }
        )
    return profile


def graph_audit_for_tree(case: dict, class_id: str, tree_id: str, signs_by_hinge: dict[str, int]) -> dict:
    tree = find_tree(case, tree_id)
    evaluated_nodes = [evaluate_node(case, tree, signs_by_hinge, node) for node in all_node_records()]
    nodes_by_id = {node["node_id"]: node for node in evaluated_nodes}
    free_node_ids = {node["node_id"] for node in evaluated_nodes if node["status"] == "collision_free"}
    blocked_nodes = [node for node in evaluated_nodes if node["status"] != "collision_free"]
    component_by_node, components = connected_components(free_node_ids, nodes_by_id)
    components_sorted = sorted(components, key=len, reverse=True)

    ray_node_ids = [node_key(theta_index, 0, None) for theta_index in range(len(THETA_STATIONS_DEGREES))]
    ray_component_indices = sorted({component_by_node.get(node_id) for node_id in ray_node_ids if node_id in component_by_node})
    ray_component_index = ray_component_indices[0] if len(ray_component_indices) == 1 else None
    ray_component_ids = set(components[ray_component_index]) if ray_component_index is not None else set()
    start_node = ray_node_ids[0]
    endpoint_node = ray_node_ids[-1]

    component_sizes = sorted([len(component) for component in components], reverse=True)
    return {
        "class_id": class_id,
        "tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "ray_signs_by_hinge": signs_by_hinge,
        "status": "component_graph_completed",
        "node_protocol": {
            "theta_stations_degrees": THETA_STATIONS_DEGREES,
            "radii_degrees": RADII_DEGREES,
            "direction_count": DIRECTION_COUNT,
            "node_count": len(evaluated_nodes),
        },
        "summary_metrics": {
            "free_node_count": len(free_node_ids),
            "blocked_node_count": len(blocked_nodes),
            "component_count": len(components),
            "component_sizes_desc": component_sizes[:12],
            "largest_component_size": component_sizes[0] if component_sizes else 0,
            "all_ray_nodes_free": all(node_id in free_node_ids for node_id in ray_node_ids),
            "all_ray_nodes_same_component": len(ray_component_indices) == 1,
            "start_to_endpoint_connected_in_sample_graph": (
                start_node in component_by_node
                and endpoint_node in component_by_node
                and component_by_node[start_node] == component_by_node[endpoint_node]
            ),
            "ray_component_size": len(ray_component_ids),
            "ray_component_fraction_of_free_nodes": round(len(ray_component_ids) / len(free_node_ids), 6) if free_node_ids else 0.0,
        },
        "ray_component_radius_profile": radius_profile_for_component(ray_component_ids, nodes_by_id),
        "stored_blocked_nodes": blocked_nodes[:MAX_STORED_NODES],
        "stored_ray_component_nodes": [nodes_by_id[node_id] for node_id in sorted(ray_component_ids)[:MAX_STORED_NODES]],
    }


def build_report() -> dict:
    case = batch.build_case()
    signs_by_tree = certified_signs_by_tree()
    audits = [
        graph_audit_for_tree(case, class_id, tree_id, signs_by_tree[tree_id])
        for class_id, tree_id in REPRESENTATIVES.items()
    ]
    matching_shape = len({json.dumps(audit["summary_metrics"], sort_keys=True) for audit in audits}) == 1
    return {
        "case_id": CASE_ID,
        "status": "two_class_component_search_completed",
        "representatives": REPRESENTATIVES,
        "graph_protocol": {
            "theta_stations_degrees": THETA_STATIONS_DEGREES,
            "radii_degrees": RADII_DEGREES,
            "direction_count": DIRECTION_COUNT,
            "edge_rule": "adjacent theta stations, adjacent radii, and adjacent angular directions on each radial ring",
        },
        "summary_metrics": {
            "representative_count": len(audits),
            "all_start_to_endpoint_connected_in_sample_graph": all(
                audit["summary_metrics"]["start_to_endpoint_connected_in_sample_graph"] for audit in audits
            ),
            "all_ray_nodes_same_component": all(
                audit["summary_metrics"]["all_ray_nodes_same_component"] for audit in audits
            ),
            "component_summary_metrics_identical": matching_shape,
        },
        "representative_audits": audits,
        "limitations": [
            "This is a finite sample graph in angle space, not a proof of continuous connectedness.",
            "Edges only connect sampled nodes; no cell-level interval SAT bound is used here.",
            "The two representatives belong to different hinge graphs, so this compares local component evidence rather than building a direct path between classes.",
            "No physical hinge offsets, clearances, mesh export, or printability gates are modeled.",
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
                "all_start_to_endpoint_connected_in_sample_graph": report["summary_metrics"]["all_start_to_endpoint_connected_in_sample_graph"],
                "component_summary_metrics_identical": report["summary_metrics"]["component_summary_metrics_identical"],
                "tree_metrics": {
                    audit["tree_id"]: audit["summary_metrics"] for audit in report["representative_audits"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())