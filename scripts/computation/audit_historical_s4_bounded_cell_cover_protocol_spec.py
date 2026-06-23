"""Bounded 3-parameter cell-cover protocol spec for S4 representatives.

This audit does not certify continuous 3-parameter hingeability. It defines the
next certificate object after the completed refined-edge ledgers:

- cylindrical wedge cells in the sampled 3-parameter tube;
- a vertex-free inventory for TREE_007 and TREE_021; and
- the guard stack required to promote cells from finite samples to continuous
  cell coverage.

The domain is the existing component-search tube:

    angle vector = sign_vector * theta + radius * transverse_direction

with 10 theta stations, 7 radii, and 16 angular directions. Between consecutive
theta stations, consecutive radii, and adjacent direction sectors, this creates
864 cylindrical wedge cells per representative. Cells touching radius 0 are
triangular-prism-like core wedges; all other cells are annular wedge cells.
"""

from __future__ import annotations

from collections import Counter, defaultdict, deque
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_cover_protocol_spec_report.json"
SOURCE_COMPONENT_REPORT = "two_class_component_search_report.json"
SOURCE_BOUNDED_REPORT = "bounded_component_graph_certificate_report.json"
SOURCE_EDGE_REFINEMENT_REPORT = "bounded_component_edge_refinement_report.json"
TREE_OVERLAY_REPORTS = {
    "TREE_007": "tree007_refined_edge_interval_certificate_overlay_report.json",
    "TREE_021": "tree021_refined_edge_interval_certificate_overlay_report.json",
}
MAX_STORED_EXAMPLES = 48

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def all_node_ids() -> set[str]:
    return {node["node_id"] for node in comp.all_node_records()}


def free_node_ids(source_audit: dict) -> set[str]:
    blocked_ids = {node["node_id"] for node in source_audit["stored_blocked_nodes"]}
    expected_blocked = int(source_audit["summary_metrics"]["blocked_node_count"])
    if len(blocked_ids) != expected_blocked:
        raise RuntimeError(
            f"Source report did not store all blocked nodes for {source_audit['tree_id']}: "
            f"stored={len(blocked_ids)} expected={expected_blocked}"
        )
    return all_node_ids() - blocked_ids


def cell_id(theta_index: int, radial_band_index: int, direction_index: int) -> str:
    return f"theta{theta_index:02d}_radial{radial_band_index:02d}_dir{direction_index:02d}"


def direction_next(direction_index: int) -> int:
    return (direction_index + 1) % comp.DIRECTION_COUNT


def cell_vertices(theta_index: int, radial_band_index: int, direction_index: int) -> list[str]:
    theta_values = [theta_index, theta_index + 1]
    next_direction = direction_next(direction_index)
    if radial_band_index == 0:
        vertices = []
        for theta in theta_values:
            vertices.append(comp.node_key(theta, 0, None))
            vertices.append(comp.node_key(theta, 1, direction_index))
            vertices.append(comp.node_key(theta, 1, next_direction))
        return sorted(set(vertices))

    radius_values = [radial_band_index, radial_band_index + 1]
    vertices = []
    for theta in theta_values:
        for radius in radius_values:
            vertices.append(comp.node_key(theta, radius, direction_index))
            vertices.append(comp.node_key(theta, radius, next_direction))
    return sorted(set(vertices))


def iter_cells() -> list[dict]:
    cells = []
    for theta_index in range(len(comp.THETA_STATIONS_DEGREES) - 1):
        for radial_band_index in range(len(comp.RADII_DEGREES) - 1):
            for direction_index in range(comp.DIRECTION_COUNT):
                kind = "core_wedge" if radial_band_index == 0 else "annular_wedge"
                cells.append(
                    {
                        "cell_id": cell_id(theta_index, radial_band_index, direction_index),
                        "kind": kind,
                        "theta_interval_degrees": [
                            comp.THETA_STATIONS_DEGREES[theta_index],
                            comp.THETA_STATIONS_DEGREES[theta_index + 1],
                        ],
                        "radial_interval_degrees": [
                            comp.RADII_DEGREES[radial_band_index],
                            comp.RADII_DEGREES[radial_band_index + 1],
                        ],
                        "theta_index": theta_index,
                        "radial_band_index": radial_band_index,
                        "direction_index": direction_index,
                        "direction_sector": [
                            direction_index,
                            direction_next(direction_index),
                        ],
                        "vertex_node_ids": cell_vertices(theta_index, radial_band_index, direction_index),
                    }
                )
    return cells


def adjacent_cell_ids(cell: dict) -> list[str]:
    theta = int(cell["theta_index"])
    radial = int(cell["radial_band_index"])
    direction = int(cell["direction_index"])
    neighbors = []
    if theta > 0:
        neighbors.append(cell_id(theta - 1, radial, direction))
    if theta + 1 < len(comp.THETA_STATIONS_DEGREES) - 1:
        neighbors.append(cell_id(theta + 1, radial, direction))
    if radial > 0:
        neighbors.append(cell_id(theta, radial - 1, direction))
    if radial + 1 < len(comp.RADII_DEGREES) - 1:
        neighbors.append(cell_id(theta, radial + 1, direction))
    neighbors.append(cell_id(theta, radial, (direction - 1) % comp.DIRECTION_COUNT))
    neighbors.append(cell_id(theta, radial, (direction + 1) % comp.DIRECTION_COUNT))
    return neighbors


def connected_components_for_cells(all_free_cell_ids: set[str], cell_by_id: dict[str, dict]) -> list[list[str]]:
    seen = set()
    components = []
    for start in sorted(all_free_cell_ids):
        if start in seen:
            continue
        queue = deque([start])
        seen.add(start)
        component = []
        while queue:
            current = queue.popleft()
            component.append(current)
            for neighbor in adjacent_cell_ids(cell_by_id[current]):
                if neighbor not in all_free_cell_ids or neighbor in seen:
                    continue
                seen.add(neighbor)
                queue.append(neighbor)
        components.append(sorted(component))
    return sorted(components, key=len, reverse=True)


def compact_cell(cell: dict, free_ids: set[str]) -> dict:
    blocked_vertices = [node_id for node_id in cell["vertex_node_ids"] if node_id not in free_ids]
    return {
        "cell_id": cell["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "vertex_count": len(cell["vertex_node_ids"]),
        "blocked_vertex_count": len(blocked_vertices),
        "blocked_vertex_node_ids": blocked_vertices,
    }


def complete_ring_counts(cells: list[dict], all_free_cell_ids: set[str]) -> list[dict]:
    rows = []
    for theta_index in range(len(comp.THETA_STATIONS_DEGREES) - 1):
        for radial_band_index in range(len(comp.RADII_DEGREES) - 1):
            ids = {
                cell_id(theta_index, radial_band_index, direction)
                for direction in range(comp.DIRECTION_COUNT)
            }
            free_count = len(ids & all_free_cell_ids)
            rows.append(
                {
                    "theta_interval_degrees": [
                        comp.THETA_STATIONS_DEGREES[theta_index],
                        comp.THETA_STATIONS_DEGREES[theta_index + 1],
                    ],
                    "radial_interval_degrees": [
                        comp.RADII_DEGREES[radial_band_index],
                        comp.RADII_DEGREES[radial_band_index + 1],
                    ],
                    "radial_band_index": radial_band_index,
                    "all_direction_sector_count": comp.DIRECTION_COUNT,
                    "all_free_direction_sector_count": free_count,
                    "complete_angular_ring_by_vertex_status": free_count == comp.DIRECTION_COUNT,
                }
            )
    return rows


def tree_inventory(source_audit: dict, cells: list[dict]) -> dict:
    tree_id = source_audit["tree_id"]
    free_ids = free_node_ids(source_audit)
    cell_by_id = {cell["cell_id"]: cell for cell in cells}
    all_free_cells = []
    blocked_cells = []
    by_kind = defaultdict(Counter)
    by_theta = defaultdict(Counter)
    by_radial = defaultdict(Counter)
    examples = defaultdict(list)

    for cell in cells:
        blocked_vertices = [node_id for node_id in cell["vertex_node_ids"] if node_id not in free_ids]
        status = "all_vertices_free" if not blocked_vertices else "has_blocked_vertex"
        cell_key = cell["cell_id"]
        if status == "all_vertices_free":
            all_free_cells.append(cell_key)
        else:
            blocked_cells.append(cell_key)
        by_kind[cell["kind"]][status] += 1
        by_theta[str(cell["theta_interval_degrees"])][status] += 1
        by_radial[str(cell["radial_interval_degrees"])][status] += 1
        add_example(examples[status], compact_cell(cell, free_ids))

    all_free_ids = set(all_free_cells)
    components = connected_components_for_cells(all_free_ids, cell_by_id)
    ring_rows = complete_ring_counts(cells, all_free_ids)
    complete_ring_count = sum(1 for row in ring_rows if row["complete_angular_ring_by_vertex_status"])
    ray_core_complete_count = sum(
        1
        for row in ring_rows
        if row["radial_band_index"] == 0 and row["complete_angular_ring_by_vertex_status"]
    )

    return {
        "tree_id": tree_id,
        "class_id": source_audit["class_id"],
        "hinge_ids": source_audit["hinge_ids"],
        "ray_signs_by_hinge": source_audit["ray_signs_by_hinge"],
        "source_component_summary_metrics": source_audit["summary_metrics"],
        "cell_inventory": {
            "total_cell_count": len(cells),
            "all_vertices_free_cell_count": len(all_free_cells),
            "has_blocked_vertex_cell_count": len(blocked_cells),
            "core_wedge_cell_count": sum(1 for cell in cells if cell["kind"] == "core_wedge"),
            "annular_wedge_cell_count": sum(1 for cell in cells if cell["kind"] == "annular_wedge"),
            "complete_angular_ring_count": complete_ring_count,
            "ray_core_complete_angular_ring_count": ray_core_complete_count,
            "all_free_cell_component_count": len(components),
            "largest_all_free_cell_component_size": len(components[0]) if components else 0,
            "all_free_cells_single_face_adjacency_component": len(components) <= 1,
        },
        "breakdown": {
            "cell_status_by_kind": {key: dict(counter.most_common()) for key, counter in sorted(by_kind.items())},
            "cell_status_by_theta_interval": {key: dict(counter.most_common()) for key, counter in sorted(by_theta.items())},
            "cell_status_by_radial_interval": {key: dict(counter.most_common()) for key, counter in sorted(by_radial.items())},
            "complete_ring_rows": ring_rows,
            "all_free_cell_component_sizes_desc": [len(component) for component in components[:16]],
        },
        "examples": dict(examples),
    }


def overlay_status_by_tree() -> dict[str, dict]:
    output = {}
    for tree_id, report_name in TREE_OVERLAY_REPORTS.items():
        report = load_json(RESULTS_DIR / report_name)
        output[tree_id] = report["summary_metrics"]
    return output


def build_report() -> dict:
    component_report = load_json(RESULTS_DIR / SOURCE_COMPONENT_REPORT)
    bounded_report = load_json(RESULTS_DIR / SOURCE_BOUNDED_REPORT)
    edge_refinement_report = load_json(RESULTS_DIR / SOURCE_EDGE_REFINEMENT_REPORT)
    cells = iter_cells()
    tree_reports = [tree_inventory(audit, cells) for audit in component_report["representative_audits"]]
    overlay_status = overlay_status_by_tree()

    shape_keys = [
        json.dumps(report["cell_inventory"], sort_keys=True)
        for report in tree_reports
    ]
    all_shape_metrics_identical = len(set(shape_keys)) == 1

    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_cover_protocol_spec_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_COMPONENT_REPORT}",
            f"results/{CASE_ID}/{SOURCE_BOUNDED_REPORT}",
            f"results/{CASE_ID}/{SOURCE_EDGE_REFINEMENT_REPORT}",
            f"results/{CASE_ID}/tree007_refined_edge_interval_certificate_overlay_report.json",
            f"results/{CASE_ID}/tree021_refined_edge_interval_certificate_overlay_report.json",
        ],
        "domain_protocol": {
            "coordinate_model": "angle vector = sign_vector * theta + radius * transverse_direction",
            "theta_stations_degrees": comp.THETA_STATIONS_DEGREES,
            "radii_degrees": comp.RADII_DEGREES,
            "direction_count": comp.DIRECTION_COUNT,
            "cell_types": {
                "core_wedge": "theta interval x [0, first radius] x adjacent direction sector, with the radius-0 center collapsed",
                "annular_wedge": "theta interval x adjacent positive radii x adjacent direction sector",
            },
            "cell_count_per_representative": len(cells),
            "theta_zero_policy": "excluded; this protocol starts at theta=0.5 degrees and inherits the open-limit ray boundary separately",
        },
        "required_certificate_protocol": {
            "C0_domain_inventory": "enumerate cylindrical wedge cells and classify them by sampled vertex status",
            "C1_first_pass_cell_guard": "for every all-vertices-free cell, evaluate a center sample and apply conservative pairwise displacement/orientation guards over the full cell",
            "C2_residual_formula_library": "reuse the TREE_007/TREE_021 edge-branch, face-normal, shared-edge, and selected-hinge formulas where the clearance guard is structurally too conservative",
            "C3_adaptive_subdivision": "subdivide only uncovered cells in theta, radius, or direction coordinates and repeat the guard stack",
            "C4_connectivity_overlay": "verify that covered cells form a face-adjacent region connecting the representative ray corridor from theta=0.5 to theta=120",
            "C5_promotion_boundary": "only after C1-C4 close every required cell may the claim be promoted from sampled/refined-edge evidence to a bounded continuous 3-parameter component certificate",
        },
        "summary_metrics": {
            "representative_count": len(tree_reports),
            "cell_count_per_representative": len(cells),
            "total_cell_count": len(cells) * len(tree_reports),
            "all_shape_metrics_identical": all_shape_metrics_identical,
            "all_source_free_graphs_connected": bounded_report["summary_metrics"]["all_source_free_graphs_connected"],
            "all_spanning_tree_midpoints_collision_free": bounded_report["summary_metrics"]["all_spanning_tree_midpoints_collision_free"],
            "all_refined_edge_interior_samples_collision_free": edge_refinement_report["summary_metrics"]["all_interior_samples_collision_free"],
            "tree007_refined_edge_overlay_completed": overlay_status["TREE_007"]["tree007_refined_edge_interval_overlay_completed"],
            "tree021_refined_edge_overlay_completed": overlay_status["TREE_021"]["tree021_refined_edge_interval_overlay_completed"],
            "cell_cover_certificate_completed": False,
        },
        "tree_reports": tree_reports,
        "limitations": [
            "This report is a protocol specification and domain inventory, not a cell-cover certificate.",
            "A cell with all sampled vertices collision-free is not certified collision-free in its interior.",
            "Cells with blocked vertices are outside the first bounded free-cell target unless an adaptive or smaller domain is later defined.",
            "The protocol starts at theta=0.5 degrees and does not cover theta=0.",
            "It does not certify dynamic connectedness between TREE_007 and TREE_021, physical hinge offsets, thickness, mesh export, or printability.",
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
                "tree_cell_inventories": {
                    item["tree_id"]: item["cell_inventory"]
                    for item in report["tree_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
