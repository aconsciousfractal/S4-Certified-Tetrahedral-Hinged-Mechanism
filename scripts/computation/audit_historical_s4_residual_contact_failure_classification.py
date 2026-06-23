"""Classify TREE_021 residual-contact failures from the refined-edge guard probe.

The interval-guard probe showed that all remaining uncovered pair-segments are
residual shared-face/shared-edge contacts. This script recomputes only those
residual pairs for TREE_021 and aggregates failures by pair, source-edge local
geometry, and midpoint SAT-axis family.
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
REPORT_NAME = "residual_contact_failure_classification_report.json"
TARGET_TREE_ID = "TREE_021"
MAX_COORDINATE_DELTA_DEGREES = 5.0
MAX_STORED_EXAMPLES_PER_PAIR = 24
SAT_TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_component_graph_certificate as bounded  # noqa: E402
import audit_historical_s4_bounded_component_edge_refinement as refinement  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID
FACES = list(itertools.combinations(range(4), 3))
EDGES = list(itertools.combinations(range(4), 2))


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def labels_by_piece(case: dict) -> dict[str, list[str]]:
    return {
        piece_id: [lib.label_for(vertex, case["labels"]) for vertex in piece]
        for piece_id, piece in case["pieces_by_id"].items()
    }


def axis_records(poly_a: list[np.ndarray], poly_b: list[np.ndarray], labels_a: list[str], labels_b: list[str]) -> list[tuple[str, np.ndarray]]:
    records = []
    for side, poly, labels in [("left", poly_a, labels_a), ("right", poly_b, labels_b)]:
        for face in FACES:
            pts = [poly[index] for index in face]
            axis = np.cross(pts[1] - pts[0], pts[2] - pts[0])
            if np.linalg.norm(axis) > lib.TOL:
                records.append((f"{side}_face:{'-'.join(labels[index] for index in face)}", axis))
    for edge_a in EDGES:
        vector_a = poly_a[edge_a[1]] - poly_a[edge_a[0]]
        for edge_b in EDGES:
            vector_b = poly_b[edge_b[1]] - poly_b[edge_b[0]]
            axis = np.cross(vector_a, vector_b)
            if np.linalg.norm(axis) > lib.TOL:
                records.append(
                    (
                        f"edge:{labels_a[edge_a[0]]}-{labels_a[edge_a[1]]} x {labels_b[edge_b[0]]}-{labels_b[edge_b[1]]}",
                        axis,
                    )
                )
    return records


def best_named_axis(poly_a: list[np.ndarray], poly_b: list[np.ndarray], labels_a: list[str], labels_b: list[str]) -> dict:
    best = None
    for name, axis in axis_records(poly_a, poly_b, labels_a, labels_b):
        unit = axis / np.linalg.norm(axis)
        a_values = [float(np.dot(vertex, unit)) for vertex in poly_a]
        b_values = [float(np.dot(vertex, unit)) for vertex in poly_b]
        overlap = min(max(a_values), max(b_values)) - max(min(a_values), min(b_values))
        if best is None or overlap < best["center_axis_overlap"]:
            best = {"axis_name": name, "center_axis_overlap": float(overlap)}
    if best is None:
        raise RuntimeError("No named SAT axis found")
    return best


def node_kind(left_node: dict, right_node: dict) -> str:
    changed = []
    if left_node["theta_index"] != right_node["theta_index"]:
        changed.append("theta")
    if left_node["radius_index"] != right_node["radius_index"]:
        changed.append("radius")
    if left_node["direction_index"] != right_node["direction_index"]:
        changed.append("direction")
    return "+".join(changed) if changed else "same_node"


def node_descriptor(node: dict) -> str:
    direction = "C" if node["direction_index"] is None else str(node["direction_index"])
    return f"t{node['theta_degrees']}:r{node['radius_degrees']}:d{direction}"


def source_edge_descriptor(nodes_by_id: dict[str, dict], node_ids: list[str]) -> dict:
    left = nodes_by_id[node_ids[0]]
    right = nodes_by_id[node_ids[1]]
    return {
        "kind": node_kind(left, right),
        "left": node_descriptor(left),
        "right": node_descriptor(right),
        "theta_pair": f"{left['theta_degrees']}->{right['theta_degrees']}",
        "radius_pair": f"{left['radius_degrees']}->{right['radius_degrees']}",
        "direction_pair": f"{left['direction_index']}->{right['direction_index']}",
    }


def residual_pairs_for_tree(case: dict, tree: dict) -> list[tuple[tuple[str, str], str]]:
    contacts_by_pair = ray_guard.contact_by_pair(case)
    hinge_pairs = {tuple(sorted(case["hinge_by_id"][hinge_id]["pieces"])) for hinge_id in tree["hinge_ids"]}
    output = []
    for pair, contact in sorted(contacts_by_pair.items()):
        if pair in hinge_pairs:
            continue
        role = f"residual_{contact['type']}"
        output.append((pair, role))
    return output


def interval(values: list[float]) -> list[float | None]:
    if not values:
        return [None, None]
    return [round(min(values), 8), round(max(values), 8)]


def compact_example(segment: dict, edge_info: dict, center_degrees: dict[str, float], record: dict) -> dict:
    return {
        "segment_id": f"seg_{segment['refined_segment_index']:05d}",
        "source_edge_index": segment["source_edge_index"],
        "source_node_ids": segment["source_node_ids"],
        "source_edge": edge_info,
        "source_t_interval": segment["source_t_interval"],
        "delta": segment["delta"],
        "center_angle_degrees_by_hinge": {key: round(value, 8) for key, value in center_degrees.items()},
        "pair": list(record["pair"]),
        "role": record["role"],
        "best_axis_name": record["best_axis_name"],
        "center_axis_overlap": round(record["center_axis_overlap"], 12),
        "guard_bound": round(record["guard_bound"], 12),
        "post_guard_overlap_bound": round(record["post_guard_overlap_bound"], 12),
        "guard_margin": round(record["guard_margin"], 12),
    }


def update_pair_stats(stats: dict, segment: dict, edge_info: dict, center_degrees: dict[str, float], record: dict) -> None:
    stats["pair_segment_count"] += 1
    stats["axis_name_counts"][record["best_axis_name"]] += 1
    stats["source_edge_kind_counts"][edge_info["kind"]] += 1
    stats["source_theta_pair_counts"][edge_info["theta_pair"]] += 1
    stats["source_radius_pair_counts"][edge_info["radius_pair"]] += 1
    stats["source_direction_pair_counts"][edge_info["direction_pair"]] += 1
    stats["center_axis_overlaps"].append(record["center_axis_overlap"])
    stats["guard_bounds"].append(record["guard_bound"])
    stats["guard_margins"].append(record["guard_margin"])
    for hinge_id, value in center_degrees.items():
        stats["center_angles_by_hinge"][hinge_id].append(float(value))
    if record["clearance_certified"]:
        stats["clearance_certified_pair_segment_count"] += 1
    else:
        stats["uncovered_pair_segment_count"] += 1
        stats["uncovered_axis_name_counts"][record["best_axis_name"]] += 1
        stats["uncovered_source_edge_kind_counts"][edge_info["kind"]] += 1
        stats["uncovered_source_theta_pair_counts"][edge_info["theta_pair"]] += 1
        stats["uncovered_source_radius_pair_counts"][edge_info["radius_pair"]] += 1
        stats["uncovered_source_direction_pair_counts"][edge_info["direction_pair"]] += 1
        if len(stats["stored_uncovered_examples"]) < MAX_STORED_EXAMPLES_PER_PAIR:
            stats["stored_uncovered_examples"].append(compact_example(segment, edge_info, center_degrees, record))
        worst = stats.get("worst_uncovered_example")
        if worst is None or record["guard_margin"] < worst["guard_margin"]:
            stats["worst_uncovered_example"] = compact_example(segment, edge_info, center_degrees, record)


def finalize_pair_stats(pair: tuple[str, str], role: str, stats: dict) -> dict:
    return {
        "pair": list(pair),
        "role": role,
        "pair_segment_count": stats["pair_segment_count"],
        "clearance_certified_pair_segment_count": stats["clearance_certified_pair_segment_count"],
        "uncovered_pair_segment_count": stats["uncovered_pair_segment_count"],
        "axis_name_counts": dict(stats["axis_name_counts"].most_common()),
        "source_edge_kind_counts": dict(stats["source_edge_kind_counts"].most_common()),
        "source_theta_pair_counts": dict(stats["source_theta_pair_counts"].most_common()),
        "source_radius_pair_counts": dict(stats["source_radius_pair_counts"].most_common()),
        "source_direction_pair_counts": dict(stats["source_direction_pair_counts"].most_common()),
        "uncovered_axis_name_counts": dict(stats["uncovered_axis_name_counts"].most_common()),
        "uncovered_source_edge_kind_counts": dict(stats["uncovered_source_edge_kind_counts"].most_common()),
        "uncovered_source_theta_pair_counts": dict(stats["uncovered_source_theta_pair_counts"].most_common()),
        "uncovered_source_radius_pair_counts": dict(stats["uncovered_source_radius_pair_counts"].most_common()),
        "uncovered_source_direction_pair_counts": dict(stats["uncovered_source_direction_pair_counts"].most_common()),
        "center_axis_overlap_interval": interval(stats["center_axis_overlaps"]),
        "guard_bound_interval": interval(stats["guard_bounds"]),
        "guard_margin_interval": interval(stats["guard_margins"]),
        "center_angle_intervals_by_hinge": {
            hinge_id: interval(values) for hinge_id, values in sorted(stats["center_angles_by_hinge"].items())
        },
        "stored_uncovered_examples": stats["stored_uncovered_examples"],
        "worst_uncovered_example": stats.get("worst_uncovered_example"),
    }


def build_report() -> dict:
    case = batch.build_case()
    component_report = load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    labels = labels_by_piece(case)
    nodes_by_id = bounded.all_nodes_by_id(tree, signs_by_tree[TARGET_TREE_ID])
    _, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    residual_pairs = residual_pairs_for_tree(case, tree)

    pair_stats = {
        pair: {
            "pair_segment_count": 0,
            "clearance_certified_pair_segment_count": 0,
            "uncovered_pair_segment_count": 0,
            "axis_name_counts": Counter(),
            "source_edge_kind_counts": Counter(),
            "source_theta_pair_counts": Counter(),
            "source_radius_pair_counts": Counter(),
            "source_direction_pair_counts": Counter(),
            "uncovered_axis_name_counts": Counter(),
            "uncovered_source_edge_kind_counts": Counter(),
            "uncovered_source_theta_pair_counts": Counter(),
            "uncovered_source_radius_pair_counts": Counter(),
            "uncovered_source_direction_pair_counts": Counter(),
            "center_axis_overlaps": [],
            "guard_bounds": [],
            "guard_margins": [],
            "center_angles_by_hinge": defaultdict(list),
            "stored_uncovered_examples": [],
        }
        for pair, _role in residual_pairs
    }
    failure_patterns = Counter()

    for segment in segments:
        center_vector = (segment["left_vector"] + segment["right_vector"]) / 2.0
        center_degrees = probe.degrees_from_vector(tree, center_vector)
        left_degrees = probe.degrees_from_vector(tree, segment["left_vector"])
        right_degrees = probe.degrees_from_vector(tree, segment["right_vector"])
        delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
        transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        displacement_bounds = probe.piece_displacement_bounds_for_segment(
            case,
            tree,
            transforms,
            transformed,
            delta_by_hinge,
            paths_by_piece,
        )
        edge_info = source_edge_descriptor(nodes_by_id, segment["source_node_ids"])
        uncovered_pairs = []
        for pair, role in residual_pairs:
            left, right = pair
            best = best_named_axis(transformed[left], transformed[right], labels[left], labels[right])
            guard_bound = displacement_bounds[left] + displacement_bounds[right] + SAT_TOLERANCE
            post_guard = best["center_axis_overlap"] + guard_bound
            guard_margin = SAT_TOLERANCE - post_guard
            record = {
                "pair": pair,
                "role": role,
                "best_axis_name": best["axis_name"],
                "center_axis_overlap": best["center_axis_overlap"],
                "guard_bound": guard_bound,
                "post_guard_overlap_bound": post_guard,
                "guard_margin": guard_margin,
                "clearance_certified": post_guard <= SAT_TOLERANCE,
            }
            update_pair_stats(pair_stats[pair], segment, edge_info, center_degrees, record)
            if not record["clearance_certified"]:
                uncovered_pairs.append("-".join(pair))
        if uncovered_pairs:
            failure_patterns[" + ".join(uncovered_pairs)] += 1
        else:
            failure_patterns["none"] += 1

    pair_reports = [finalize_pair_stats(pair, role, pair_stats[pair]) for pair, role in residual_pairs]
    return {
        "case_id": CASE_ID,
        "status": "residual_contact_failure_classification_completed",
        "source_reports": [
            f"results/{CASE_ID}/refined_edge_interval_guard_probe_report.json",
            f"results/{CASE_ID}/bounded_component_edge_refinement_report.json",
            f"results/{CASE_ID}/two_class_component_search_report.json",
        ],
        "target_tree_id": TARGET_TREE_ID,
        "summary_metrics": {
            "refined_segment_count": len(segments),
            "residual_pair_count": len(residual_pairs),
            "residual_pair_segment_count": len(segments) * len(residual_pairs),
            "total_residual_uncovered_pair_segment_count": sum(report["uncovered_pair_segment_count"] for report in pair_reports),
            "total_residual_clearance_certified_pair_segment_count": sum(report["clearance_certified_pair_segment_count"] for report in pair_reports),
        },
        "failure_pattern_counts": dict(failure_patterns.most_common()),
        "pair_reports": pair_reports,
        "model_implications": [
            "Residual shared-face failures should be handled before residual shared-edge failures because every failed segment includes P0-P2 in this TREE_021 probe.",
            "The midpoint SAT-axis family reported here identifies which separator branches need interval tracking off the representative ray.",
            "Clearance-only displacement guards are too conservative for the residual contacts; a branch-aware residual-contact interval model is required.",
        ],
        "limitations": [
            "This classification recomputes residual-pair guard data only for TREE_021 refined spanning-tree segments.",
            "It is diagnostic and does not certify the failed residual-contact segments.",
            "It does not cover TREE_007 or every free graph edge.",
            "No physical hinge offsets, thickness, mesh export, or printability gates are modeled.",
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
                "failure_pattern_counts": report["failure_pattern_counts"],
                "pair_counts": {
                    "-".join(report["pair"]): {
                        "role": report["role"],
                        "uncovered": report["uncovered_pair_segment_count"],
                        "certified": report["clearance_certified_pair_segment_count"],
                    }
                    for report in report["pair_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())