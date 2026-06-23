#!/usr/bin/env python
"""Build RW7d hinge connectivity repair variants for S4.

RW7d consumes the RW7 hardware work order and RW7b boolean-rebuilt body pieces.
It creates one hardware-solidization variant per hinge tree (TREE_007 and
TREE_021), because the two tree hinge sets are alternative mechanical layouts,
not a single six-hinge prototype.

For each tree variant RW7d creates:

* offset removable pin cylinders;
* printable boss/knuckle sleeve tubes with connector webs;
* piece-wise boolean unions of body + owned sleeve/web solids;
* pin/body, piece/piece, and pin/pin intersection checks;
* OBJ artifacts for printed pieces, pins, and combined assemblies.

Scope boundary: RW7d is a CAD/mesh solidization and clearance gate. It does
not export STL/3MF, does not run a slicer, does not print a coupon, and does
not validate physical hingeability.
"""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from trimesh import repair
from trimesh.creation import cylinder


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW7_PATH = RESULT_ROOT / "rw7_selected_candidate_cad_boolean_hardware_prep.json"
RW7B_PATH = RESULT_ROOT / "rw7b_candidate_boolean_rebuild_report.json"
JSON_PATH = RESULT_ROOT / "rw7d_hinge_connectivity_repair_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW7C_HINGE_HARDWARE_SOLIDIZATION.md"
OUT_DIR = RESULT_ROOT / "cad_hardware_connectivity_repair"
MANIFEST_PATH = OUT_DIR / "rw7d_hinge_connectivity_repair_manifest.json"

PIECE_IDS = ["P0", "P1", "P2", "P3"]
SECTIONS = 32
BOOLEAN_ENGINE = "manifold"
INTERSECTION_TOL_MODEL_VOLUME = 1e-10

# Regular tetrahedron centroid in the RW2 coordinate frame.  This is used only
# to choose an external offset direction away from the tetrahedral body.
TETRA_CENTROID = np.array([0.5, 0.288675134595, 0.204124145232], dtype=float)

BLOCKED_CLAIMS = [
    "physical hingeability",
    "direct printability",
    "STL/3MF export readiness",
    "G-code readiness",
    "fabrication readiness",
    "static coupon validation",
    "moving prototype validation",
]

OPEN_BLOCKERS = [
    "RW7d hardware geometry is a baseline printable hinge layout, not an optimized mechanical design",
    "material strength, anisotropy, friction, wear, and pin retention are untested",
    "pin insertion/removal and assembly sequence are not physically tested",
    "STL/3MF export and slicer/layer preview have not been run",
    "static fit coupon and moving prototype have not been printed or measured",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def as_np(point: list[float]) -> np.ndarray:
    return np.asarray(point, dtype=float)


def unit(vec: np.ndarray) -> np.ndarray:
    norm = float(np.linalg.norm(vec))
    if norm <= 0.0:
        raise ValueError("zero vector")
    return vec / norm


def fallback_perp(u: np.ndarray) -> np.ndarray:
    trial = np.array([1.0, 0.0, 0.0])
    if abs(float(np.dot(trial, u))) > 0.85:
        trial = np.array([0.0, 1.0, 0.0])
    return unit(trial - float(np.dot(trial, u)) * u)


def external_basis(start: np.ndarray, end: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    u = unit(end - start)
    mid = 0.5 * (start + end)
    raw = mid - TETRA_CENTROID
    v = raw - float(np.dot(raw, u)) * u
    if np.linalg.norm(v) < 1e-9:
        v = fallback_perp(u)
    else:
        v = unit(v)
    w = unit(np.cross(u, v))
    return u, v, w


def load_obj_min(path: Path) -> trimesh.Trimesh:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("v "):
            vertices.append([float(value) for value in line.split()[1:4]])
        elif line.startswith("f "):
            faces.append([int(item.split("/")[0]) - 1 for item in line.split()[1:4]])
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=float), faces=np.asarray(faces, dtype=int), process=True)
    repair.fix_normals(mesh)
    return mesh


def mesh_metrics(mesh: trimesh.Trimesh) -> dict[str, Any]:
    return {
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "euler_number": int(mesh.euler_number),
        "volume_model_units": float(mesh.volume),
        "surface_area_model_units": float(mesh.area),
        "bounds_min_model": [float(x) for x in mesh.bounds[0]],
        "bounds_max_model": [float(x) for x in mesh.bounds[1]],
        "connected_component_count": int(len(mesh.split(only_watertight=False))),
    }


def solid_cylinder_between(start: np.ndarray, end: np.ndarray, radius: float, sections: int = SECTIONS) -> trimesh.Trimesh:
    mesh = cylinder(radius=radius, segment=np.vstack([start, end]), sections=sections)
    repair.fix_normals(mesh)
    return mesh


def tube_between(start: np.ndarray, end: np.ndarray, inner_radius: float, outer_radius: float, sections: int = SECTIONS) -> trimesh.Trimesh:
    u, v, w = external_basis(start, end)
    vertices: list[np.ndarray] = []
    for center, radius in [(start, outer_radius), (end, outer_radius), (start, inner_radius), (end, inner_radius)]:
        for i in range(sections):
            angle = 2.0 * math.pi * i / sections
            vertices.append(center + radius * (math.cos(angle) * v + math.sin(angle) * w))
    os0, oe0, is0, ie0 = 0, sections, 2 * sections, 3 * sections
    faces: list[list[int]] = []
    for i in range(sections):
        j = (i + 1) % sections
        os_i, os_j = os0 + i, os0 + j
        oe_i, oe_j = oe0 + i, oe0 + j
        is_i, is_j = is0 + i, is0 + j
        ie_i, ie_j = ie0 + i, ie0 + j
        faces += [
            [os_i, os_j, oe_j], [os_i, oe_j, oe_i],
            [is_i, ie_j, is_j], [is_i, ie_i, ie_j],
            [os_i, is_j, os_j], [os_i, is_i, is_j],
            [oe_i, oe_j, ie_j], [oe_i, ie_j, ie_i],
        ]
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=float), faces=np.asarray(faces, dtype=int), process=True)
    repair.fix_normals(mesh)
    return mesh


def web_prism(base_start: np.ndarray, base_end: np.ndarray, v: np.ndarray, w: np.ndarray, radial_min: float, radial_max: float, w_min: float, w_max: float) -> trimesh.Trimesh:
    vertices = []
    for base in [base_start, base_end]:
        for radial in [radial_min, radial_max]:
            for side in [w_min, w_max]:
                vertices.append(base + radial * v + side * w)
    faces = [
        [0, 1, 3], [0, 3, 2],
        [4, 6, 7], [4, 7, 5],
        [0, 4, 5], [0, 5, 1],
        [2, 3, 7], [2, 7, 6],
        [0, 2, 6], [0, 6, 4],
        [1, 5, 7], [1, 7, 3],
    ]
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=float), faces=np.asarray(faces, dtype=int), process=True)
    repair.fix_normals(mesh)
    return mesh


def union_meshes(base: trimesh.Trimesh, additions: list[trimesh.Trimesh]) -> tuple[trimesh.Trimesh, list[dict[str, Any]]]:
    current = base
    records = []
    for index, part in enumerate(additions, start=1):
        before = mesh_metrics(current)
        try:
            result = current.union(part, engine=BOOLEAN_ENGINE)
            if isinstance(result, list):
                result = trimesh.util.concatenate(result)
            if result is None or len(result.faces) == 0:
                raise ValueError("union returned empty mesh")
            repair.fix_normals(result)
            after = mesh_metrics(result)
            ok = bool(after["watertight"] and after["is_volume"] and after["volume_model_units"] > 0.0)
            records.append({"index": index, "status": "union_valid_volume" if ok else "union_invalid_volume", "before": before, "after": after})
            current = result
        except Exception as exc:
            records.append({"index": index, "status": "union_failed", "error_type": type(exc).__name__, "error": str(exc), "before": before})
    return current, records


def intersection_volume(a: trimesh.Trimesh, b: trimesh.Trimesh) -> tuple[float | None, str | None]:
    try:
        result = a.intersection(b, engine=BOOLEAN_ENGINE)
        if result is None or not hasattr(result, "faces") or len(result.faces) == 0:
            return 0.0, None
        repair.fix_normals(result)
        return abs(float(result.volume)), None
    except Exception as exc:
        # Manifold may report an empty/invalid intersection as an exception.
        return None, f"{type(exc).__name__}: {exc}"


def export_obj(path: Path, groups: list[tuple[str, trimesh.Trimesh]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RW7d hinge connectivity repair OBJ",
        "# CAD/mesh draft; not STL/3MF, not slicer-ready, not prototype-validated",
    ]
    offset = 0
    for name, mesh in groups:
        lines.append(f"g {name}")
        for vertex in mesh.vertices:
            lines.append(f"v {vertex[0]:.12g} {vertex[1]:.12g} {vertex[2]:.12g}")
        for face in mesh.faces:
            a, b, c = [int(x) + 1 + offset for x in face]
            lines.append(f"f {a} {b} {c}")
        offset += len(mesh.vertices)
    write_text(path, "\n".join(lines))


def hardware_segments(row: dict[str, Any]) -> list[dict[str, Any]]:
    start = as_np(row["active_axis_points_model"][0])
    end = as_np(row["active_axis_points_model"][1])
    u, v, w = external_basis(start, end)
    length = float(np.linalg.norm(end - start))
    sleeve_len = float(row["boss_width_mm"]) / float(row["axis_length_mm"] / row["axis_length_model_units"])
    # Equivalent to boss_width_mm / scale_mm_per_model_unit, but local to the row.
    if sleeve_len <= 0.0 or length <= 4.0 * sleeve_len:
        raise ValueError(f"invalid sleeve length for {row['tree_id']} {row['hinge_id']}")
    piece_a, piece_b = row["piece_pair"]
    return [
        {"owner_piece": piece_a, "role": "outer_knuckle_start", "t0": 0.0, "t1": sleeve_len},
        {"owner_piece": piece_a, "role": "outer_knuckle_end", "t0": length - sleeve_len, "t1": length},
        {"owner_piece": piece_b, "role": "center_knuckle", "t0": 0.5 * length - 0.5 * sleeve_len, "t1": 0.5 * length + 0.5 * sleeve_len},
    ]


def build_tree_variant(tree_id: str, hardware_rows: list[dict[str, Any]], rebuilt_bodies: dict[str, trimesh.Trimesh], scale: float) -> dict[str, Any]:
    variant_dir = OUT_DIR / tree_id
    pin_radius = float(hardware_rows[0]["pin_radius_mm"]) / scale
    clearance = float(hardware_rows[0]["clearance_mm"]) / scale
    inner_radius = pin_radius + clearance
    outer_radius = float(hardware_rows[0]["radial_envelope_mm"]) / scale
    web_half_width = float(hardware_rows[0]["boss_width_mm"]) / (2.0 * scale)
    web_penetration = 0.02  # model units = 1.20 mm at the current scale; reinforces body-boss connectivity.
    web_tube_overlap = min(0.0002, 0.1 * clearance)
    offset_distance = outer_radius + clearance
    min_pin_clearance_mm = (inner_radius - web_tube_overlap - pin_radius) * scale

    additions_by_piece: dict[str, list[trimesh.Trimesh]] = {piece_id: [] for piece_id in PIECE_IDS}
    piece_centroids = {piece_id: rebuilt_bodies[piece_id].center_mass for piece_id in PIECE_IDS}
    hardware_component_records: list[dict[str, Any]] = []
    pin_meshes: list[tuple[str, trimesh.Trimesh, dict[str, Any]]] = []

    for row in hardware_rows:
        base_start = as_np(row["active_axis_points_model"][0])
        base_end = as_np(row["active_axis_points_model"][1])
        u, v, w = external_basis(base_start, base_end)
        axis_len = float(np.linalg.norm(base_end - base_start))
        offset_start = base_start + offset_distance * v
        offset_end = base_end + offset_distance * v
        pin_mesh = solid_cylinder_between(offset_start, offset_end, pin_radius)
        pin_name = f"{tree_id}_{row['hinge_id']}_removable_pin"
        pin_meshes.append((pin_name, pin_mesh, row))
        hardware_component_records.append({
            "tree_id": tree_id,
            "hinge_id": row["hinge_id"],
            "component": pin_name,
            "component_kind": "removable_pin_cylinder",
            "owner_piece": None,
            "axis_offset_model_units": offset_distance,
            "axis_offset_mm": offset_distance * scale,
            "pin_radius_mm": row["pin_radius_mm"],
            "active_axis_length_mm": row["active_axis_length_mm"],
            "mesh_metrics": mesh_metrics(pin_mesh),
        })
        for segment in hardware_segments(row):
            seg_start_base = base_start + u * segment["t0"]
            seg_end_base = base_start + u * segment["t1"]
            seg_start_offset = seg_start_base + offset_distance * v
            seg_end_offset = seg_end_base + offset_distance * v
            sleeve = tube_between(seg_start_offset, seg_end_offset, inner_radius, outer_radius)
            owner = segment["owner_piece"]
            seg_mid = 0.5 * (seg_start_base + seg_end_base)
            owner_side = float(np.dot(piece_centroids[owner] - seg_mid, w))
            side_sign = 1.0 if owner_side >= 0.0 else -1.0
            w_min = 0.0 if side_sign > 0.0 else -2.0 * web_half_width
            w_max = 2.0 * web_half_width if side_sign > 0.0 else 0.0
            web = web_prism(
                seg_start_base,
                seg_end_base,
                v,
                w,
                -web_penetration,
                offset_distance - inner_radius + web_tube_overlap,
                w_min,
                w_max,
            )
            additions_by_piece[owner].extend([sleeve, web])
            for kind, mesh in [("boss_knuckle_sleeve_tube", sleeve), ("connector_web", web)]:
                hardware_component_records.append({
                    "tree_id": tree_id,
                    "hinge_id": row["hinge_id"],
                    "component": f"{tree_id}_{row['hinge_id']}_{owner}_{segment['role']}_{kind}",
                    "component_kind": kind,
                    "owner_piece": owner,
                    "role": segment["role"],
                    "nominal_inner_radius_mm": inner_radius * scale,
                    "outer_radius_mm": outer_radius * scale,
                    "minimum_pin_clearance_after_web_overlap_mm": min_pin_clearance_mm,
                    "owner_side_w_interval_model_units": [w_min, w_max] if kind == "connector_web" else None,
                    "mesh_metrics": mesh_metrics(mesh),
                })

    printed_piece_meshes: dict[str, trimesh.Trimesh] = {}
    piece_results: list[dict[str, Any]] = []
    union_records: list[dict[str, Any]] = []
    for piece_id in PIECE_IDS:
        mesh, records = union_meshes(rebuilt_bodies[piece_id], additions_by_piece[piece_id])
        printed_piece_meshes[piece_id] = mesh
        piece_path = variant_dir / f"{tree_id}_{piece_id}_printed_body_with_bosses.obj"
        export_obj(piece_path, [(f"{tree_id}_{piece_id}_printed_body_with_bosses", mesh)])
        for record in records:
            record.update({"tree_id": tree_id, "piece_id": piece_id})
        union_records.extend(records)
        piece_results.append({
            "tree_id": tree_id,
            "piece_id": piece_id,
            "owned_hardware_component_count": len(additions_by_piece[piece_id]),
            "printed_piece_obj": rel(piece_path),
            "mesh_metrics": mesh_metrics(mesh),
            "all_unions_valid_volume": all(record["status"] == "union_valid_volume" for record in records),
        })

    # Export pins and combined assembly.
    pin_path = variant_dir / f"{tree_id}_removable_pins.obj"
    export_obj(pin_path, [(name, mesh) for name, mesh, _ in pin_meshes])
    combined_groups: list[tuple[str, trimesh.Trimesh]] = []
    combined_groups.extend((f"{tree_id}_{piece_id}_printed_piece", printed_piece_meshes[piece_id]) for piece_id in PIECE_IDS)
    combined_groups.extend((name, mesh) for name, mesh, _ in pin_meshes)
    combined_path = variant_dir / f"{tree_id}_hardware_assembly_candidate.obj"
    export_obj(combined_path, combined_groups)

    piece_pair_intersections = []
    for i, piece_a in enumerate(PIECE_IDS):
        for piece_b in PIECE_IDS[i + 1:]:
            volume, error = intersection_volume(printed_piece_meshes[piece_a], printed_piece_meshes[piece_b])
            piece_pair_intersections.append({
                "piece_pair": [piece_a, piece_b],
                "intersection_volume_model_units": volume,
                "intersection_error": error,
                "passes_zero_positive_volume_overlap": (volume is not None and volume <= INTERSECTION_TOL_MODEL_VOLUME),
            })

    pin_body_intersections = []
    for pin_name, pin_mesh, row in pin_meshes:
        for piece_id, body_mesh in printed_piece_meshes.items():
            volume, error = intersection_volume(pin_mesh, body_mesh)
            pin_body_intersections.append({
                "pin": pin_name,
                "hinge_id": row["hinge_id"],
                "piece_id": piece_id,
                "intersection_volume_model_units": volume,
                "intersection_error": error,
                "passes_pin_body_clearance": (volume is not None and volume <= INTERSECTION_TOL_MODEL_VOLUME),
            })

    pin_pin_intersections = []
    for i, (name_a, mesh_a, _) in enumerate(pin_meshes):
        for name_b, mesh_b, _ in pin_meshes[i + 1:]:
            volume, error = intersection_volume(mesh_a, mesh_b)
            pin_pin_intersections.append({
                "pin_pair": [name_a, name_b],
                "intersection_volume_model_units": volume,
                "intersection_error": error,
                "passes_pin_pin_clearance": (volume is not None and volume <= INTERSECTION_TOL_MODEL_VOLUME),
            })

    all_printed_pieces_valid = all(row["mesh_metrics"]["watertight"] and row["mesh_metrics"]["is_volume"] for row in piece_results)
    all_printed_pieces_single_component = all(row["mesh_metrics"]["connected_component_count"] == 1 for row in piece_results)
    all_unions_valid = all(row["all_unions_valid_volume"] for row in piece_results)
    all_piece_pair_clear = all(row["passes_zero_positive_volume_overlap"] for row in piece_pair_intersections)
    all_pin_body_clear = all(row["passes_pin_body_clearance"] for row in pin_body_intersections)
    all_pin_pin_clear = all(row["passes_pin_pin_clearance"] for row in pin_pin_intersections)
    variant_passes = all([all_printed_pieces_valid, all_printed_pieces_single_component, all_unions_valid, all_piece_pair_clear, all_pin_body_clear, all_pin_pin_clear])
    return {
        "tree_id": tree_id,
        "status": "hinge_connectivity_repair_variant_passes_mesh_clearance_connectivity_checks" if variant_passes else "hinge_connectivity_repair_variant_blocked_by_mesh_clearance_or_connectivity_checks",
        "design_parameters": {
            "scale_mm_per_model_unit": scale,
            "pin_radius_mm": pin_radius * scale,
            "pin_hole_inner_radius_mm": inner_radius * scale,
            "nominal_radial_pin_clearance_mm": clearance * scale,
            "minimum_pin_clearance_after_web_overlap_mm": min_pin_clearance_mm,
            "outer_boss_radius_mm": outer_radius * scale,
            "axis_offset_mm": offset_distance * scale,
            "web_penetration_mm": web_penetration * scale,
            "web_tube_overlap_mm": web_tube_overlap * scale,
            "knuckle_pattern": "first_piece_outer_start_and_end_second_piece_center",
        },
        "summary": {
            "printed_piece_count": len(piece_results),
            "pin_count": len(pin_meshes),
            "hardware_component_count": len(hardware_component_records),
            "all_printed_pieces_watertight_valid_volumes": all_printed_pieces_valid,
            "all_printed_pieces_single_connected_components": all_printed_pieces_single_component,
            "all_hardware_unions_valid_volumes": all_unions_valid,
            "all_piece_pair_positive_volume_overlaps_clear": all_piece_pair_clear,
            "all_pin_body_positive_volume_overlaps_clear": all_pin_body_clear,
            "all_pin_pin_positive_volume_overlaps_clear": all_pin_pin_clear,
            "variant_passes_mesh_clearance_checks": variant_passes,
        },
        "artifacts": {
            "pin_obj": rel(pin_path),
            "combined_assembly_obj": rel(combined_path),
            "printed_piece_objs": [row["printed_piece_obj"] for row in piece_results],
        },
        "piece_results": piece_results,
        "hardware_component_records": hardware_component_records,
        "union_records": union_records,
        "piece_pair_intersections": piece_pair_intersections,
        "pin_body_intersections": pin_body_intersections,
        "pin_pin_intersections": pin_pin_intersections,
    }


def build_doc(payload: dict[str, Any]) -> str:
    variant_rows = []
    for variant in payload["variant_results"]:
        variant_rows.append([
            variant["tree_id"],
            variant["summary"]["pin_count"],
            variant["summary"]["hardware_component_count"],
            variant["summary"]["all_printed_pieces_watertight_valid_volumes"],
            variant["summary"]["all_piece_pair_positive_volume_overlaps_clear"],
            variant["summary"]["all_pin_body_positive_volume_overlaps_clear"],
            variant["summary"]["variant_passes_mesh_clearance_checks"],
            variant["artifacts"]["combined_assembly_obj"],
        ])
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    blocker_rows = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW7d hinge connectivity repair

Status: {payload['status']}.

RW7d materializes baseline hinge hardware solids for the selected candidate `{payload['selected_candidate_id']}` on top of the RW7b boolean-rebuilt body pieces.  It creates separate variants for `TREE_007` and `TREE_021`; these are alternative hinge layouts, not a single six-hinge assembly.

## Outputs

| artifact | path |
| --- | --- |
| RW7d JSON report | `{rel(JSON_PATH)}` |
| RW7d manifest | `{rel(MANIFEST_PATH)}` |

## Variant summary

{table(['variant', 'pins', 'hardware components', 'pieces valid', 'piece overlaps clear', 'pin/body clear', 'variant passes', 'assembly OBJ'], variant_rows)}

## Geometry model

Each variant uses offset removable pin cylinders plus printable boss/knuckle sleeve tubes and connector webs.  The boss pattern is `first_piece_outer_start_and_end_second_piece_center`; it is a baseline printable hinge layout, not an optimized mechanical design.

Key parameters:

| field | value |
| --- | --- |
| pin radius | {payload['design_parameter_summary']['pin_radius_mm']} mm |
| pin hole inner radius | {payload['design_parameter_summary']['pin_hole_inner_radius_mm']} mm |
| nominal radial clearance | {payload['design_parameter_summary']['nominal_radial_pin_clearance_mm']} mm |
| minimum clearance after web overlap | {payload['design_parameter_summary']['minimum_pin_clearance_after_web_overlap_mm']} mm |
| outer boss radius | {payload['design_parameter_summary']['outer_boss_radius_mm']} mm |
| axis offset | {payload['design_parameter_summary']['axis_offset_mm']} mm |

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Blockers still open

{table(['blocker'], blocker_rows)}

## Nonclaims

RW7d does not claim physical hingeability, direct printability, STL/3MF readiness, G-code readiness, fabrication readiness, static coupon validation, or moving prototype validation.

## Next task

RW8 may export the passing RW7d variant assemblies to STL/3MF and run slicer/layer preview.  A physical claim still remains blocked until RW9/RW10 measurements.
"""


def main() -> None:
    rw7 = load_json(RW7_PATH)
    rw7b = load_json(RW7B_PATH)
    selected_candidate_id = rw7["summary"]["selected_candidate_id"]
    if not module_available("manifold3d"):
        raise SystemExit("manifold3d is required for RW7d hardware solidization")
    scale = float(rw7["selected_candidate"]["parameters"]["scale_mm_per_model_unit"])

    rebuilt_bodies = {}
    for piece in rw7b["piece_results"]:
        rebuilt_bodies[piece["piece_id"]] = load_obj_min(ROOT / piece["rebuilt_piece_obj"])

    rows_by_tree: dict[str, list[dict[str, Any]]] = {}
    for row in rw7["hardware_work_order"]:
        rows_by_tree.setdefault(row["tree_id"], []).append(row)
    variant_results = [build_tree_variant(tree_id, rows_by_tree[tree_id], rebuilt_bodies, scale) for tree_id in sorted(rows_by_tree)]
    all_variants_pass = all(v["summary"]["variant_passes_mesh_clearance_checks"] for v in variant_results)
    first_params = variant_results[0]["design_parameters"]
    payload: dict[str, Any] = {
        "report_id": "S4-RW7C-HINGE-HARDWARE-SOLIDIZATION-2026-06-22",
        "date": DATE,
        "case_id": CASE_ID,
        "status": "rw7d_hinge_connectivity_repair_variants_pass_mesh_checks_export_gate_unblocked" if all_variants_pass else "rw7d_hinge_connectivity_repair_variants_blocked_by_mesh_or_connectivity_checks",
        "selected_candidate_id": selected_candidate_id,
        "precondition": {
            "rw7_report": rel(RW7_PATH),
            "rw7b_report": rel(RW7B_PATH),
        },
        "backend_capability": {
            "trimesh_version": getattr(trimesh, "__version__", "unknown"),
            "manifold3d_available": module_available("manifold3d"),
            "boolean_engine": BOOLEAN_ENGINE,
        },
        "design_parameter_summary": first_params,
        "summary": {
            "variant_count": len(variant_results),
            "passing_variant_count": sum(1 for v in variant_results if v["summary"]["variant_passes_mesh_clearance_checks"]),
            "all_variants_pass_mesh_clearance_checks": all_variants_pass,
            "stl_3mf_export_run": False,
            "slicer_gcode_run": False,
            "static_coupon_printed_or_measured": False,
            "moving_prototype_printed_or_measured": False,
            "rw8_export_and_slicer_unblocked": all_variants_pass,
        },
        "variant_results": variant_results,
        "artifacts": {
            "json_report": rel(JSON_PATH),
            "manifest": rel(MANIFEST_PATH),
            "variant_assembly_objs": [v["artifacts"]["combined_assembly_obj"] for v in variant_results],
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": ["RW7d increased connector-web penetration to repair body-boss connectivity; mechanical strength remains untested"] + OPEN_BLOCKERS,
        "acceptance": {
            "rw7_report_present": RW7_PATH.exists(),
            "rw7b_report_present": RW7B_PATH.exists(),
            "manifold3d_backend_available": module_available("manifold3d"),
            "two_tree_variants_created": len(variant_results) == 2,
            "all_variants_have_three_pins": all(v["summary"]["pin_count"] == 3 for v in variant_results),
            "all_printed_pieces_watertight_valid_volumes": all(v["summary"]["all_printed_pieces_watertight_valid_volumes"] for v in variant_results),
            "all_printed_pieces_single_connected_components": all(v["summary"]["all_printed_pieces_single_connected_components"] for v in variant_results),
            "all_hardware_unions_valid_volumes": all(v["summary"]["all_hardware_unions_valid_volumes"] for v in variant_results),
            "all_piece_pair_positive_volume_overlaps_clear": all(v["summary"]["all_piece_pair_positive_volume_overlaps_clear"] for v in variant_results),
            "all_pin_body_positive_volume_overlaps_clear": all(v["summary"]["all_pin_body_positive_volume_overlaps_clear"] for v in variant_results),
            "all_pin_pin_positive_volume_overlaps_clear": all(v["summary"]["all_pin_pin_positive_volume_overlaps_clear"] for v in variant_results),
            "stl_3mf_export_not_run": True,
            "slicer_gcode_not_run": True,
            "prototype_validation_not_run": True,
            "rw8_export_and_slicer_unblocked": all_variants_pass,
        },
        "next_task": "RW8 export passing RW7d connectivity-repaired variant assemblies to STL/3MF and run slicer/layer preview; physical claims remain blocked until coupon/prototype measurements.",
    }
    write_json(JSON_PATH, payload)
    write_json(MANIFEST_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "selected_candidate_id": selected_candidate_id,
        "variant_count": payload["summary"]["variant_count"],
        "passing_variant_count": payload["summary"]["passing_variant_count"],
        "rw8_export_and_slicer_unblocked": payload["summary"]["rw8_export_and_slicer_unblocked"],
        "variant_assembly_objs": payload["artifacts"]["variant_assembly_objs"],
    }, indent=2))


if __name__ == "__main__":
    main()
