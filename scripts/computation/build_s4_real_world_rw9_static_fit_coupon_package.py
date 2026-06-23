#!/usr/bin/env python
"""RW9 static fit coupon package for the body-preserving TREE_007 hinge set.

RW9 prepares a printable/measurable static coupon package for the corrected
RW7f/RW8g TREE_007 component set.  It does not claim that a coupon has been
printed, measured, or passed.  The output is a measurement-ready package:

* hole-sweep sleeves around the nominal RW7f hinge-hole diameter;
* printed-pin sweep rods around the nominal RW7f pin diameter;
* nominal outer/center knuckle coupons and a nominal pin reference;
* STL/3MF/OBJ artifacts, PrintabilityGate records, layer preview records;
* CSV/JSON measurement templates and acceptance protocol.

Physical validation remains blocked until the coupon is printed and measured.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from trimesh import repair

ROOT = Path(__file__).resolve().parents[1]
PAPP_ROOT = ROOT.parents[3] / "PAPP"
if str(PAPP_ROOT) not in sys.path:
    sys.path.insert(0, str(PAPP_ROOT))

from core.config.print_profiles import get_profile
from core.io.stl_writer import read_stl_info, write_stl
from core.io.threemf_writer import read_3mf_info, write_3mf
from core.slicer.layer_preview import slice_layers
from core.slicer.slicer_cli import detect_slicer, slice_mesh
from core.validation.printability_gate import PrintabilityGate

DATE = "2026-06-23"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW7F_PATH = RESULT_ROOT / "rw7f_body_preserving_rebuild_report.json"
RW8G_PATH = RESULT_ROOT / "rw8g_export_body_preserving_tree007_report.json"
RW8H_PATH = RESULT_ROOT / "rw8h_body_preserving_tree007_export_audit" / "body_preserving_tree007_export_integrity_audit.json"
OUT_DIR = RESULT_ROOT / "rw9_static_fit_coupon_body_preserving_tree007"
COMPONENT_DIR = OUT_DIR / "components"
MEASUREMENT_DIR = OUT_DIR / "measurement"
JSON_PATH = OUT_DIR / "rw9_static_fit_coupon_package_report.json"
MANIFEST_PATH = OUT_DIR / "rw9_static_fit_coupon_package_manifest.json"
DOC_PATH = ROOT / "docs" / "S4_RW9_STATIC_FIT_COUPON_PACKAGE.md"
PROFILE_KEY = "fdm"
SLICER_TIMEOUT_S = 120.0

COMMON_SLICER_COMMANDS = [
    "prusa-slicer", "prusaslicer", "PrusaSlicer", "CuraEngine", "curaengine",
    "OrcaSlicer", "orca-slicer", "bambu-studio",
]

BLOCKED_CLAIMS = [
    "static coupon validation",
    "fabrication readiness",
    "moving prototype validation",
    "physical hingeability",
    "public theorem promotion from physical evidence",
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


def clean_mesh(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    out = mesh.copy()
    try:
        out.update_faces(out.nondegenerate_faces())
    except Exception:
        pass
    try:
        out.update_faces(out.unique_faces())
    except Exception:
        pass
    try:
        out.remove_unreferenced_vertices()
    except Exception:
        pass
    try:
        out.merge_vertices()
    except Exception:
        pass
    try:
        repair.fix_winding(out)
        repair.fix_normals(out)
    except Exception:
        pass
    if out.volume < 0:
        out.invert()
    return out


def tube_along_x(*, outer_radius: float, inner_radius: float, length: float, sections: int = 96, center: tuple[float, float, float] = (0, 0, 0)) -> trimesh.Trimesh:
    if not (0 < inner_radius < outer_radius and length > 0):
        raise ValueError("invalid tube dimensions")
    cx, cy, cz = center
    xs = [cx - length / 2.0, cx + length / 2.0]
    vertices: list[list[float]] = []
    # order: left outer, right outer, left inner, right inner rings
    for x in xs:
        for radius in (outer_radius, inner_radius):
            for i in range(sections):
                ang = 2.0 * math.pi * i / sections
                vertices.append([x, cy + radius * math.cos(ang), cz + radius * math.sin(ang)])
    lo = 0
    ro = sections
    li = 2 * sections
    ri = 3 * sections
    faces: list[list[int]] = []
    for i in range(sections):
        j = (i + 1) % sections
        # outer cylinder
        faces.append([lo + i, ro + i, ro + j])
        faces.append([lo + i, ro + j, lo + j])
        # inner cylinder, reversed normal
        faces.append([li + i, ri + j, ri + i])
        faces.append([li + i, li + j, ri + j])
        # left annular cap
        faces.append([lo + i, lo + j, li + j])
        faces.append([lo + i, li + j, li + i])
        # right annular cap
        faces.append([ro + i, ri + i, ri + j])
        faces.append([ro + i, ri + j, ro + j])
    return clean_mesh(trimesh.Trimesh(vertices=np.asarray(vertices, dtype=float), faces=np.asarray(faces, dtype=int), process=False))


def cylinder_along_x(*, radius: float, length: float, sections: int = 96, center: tuple[float, float, float] = (0, 0, 0)) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(radius=radius, height=length, sections=sections)
    # default cylinder axis is z; rotate z -> x around y.
    rot = trimesh.transformations.rotation_matrix(math.pi / 2.0, [0, 1, 0])
    mesh.apply_transform(rot)
    mesh.apply_translation(center)
    return clean_mesh(mesh)


def concat(meshes: list[trimesh.Trimesh]) -> trimesh.Trimesh:
    return clean_mesh(trimesh.util.concatenate(meshes))


def mesh_arrays(mesh: trimesh.Trimesh) -> tuple[np.ndarray, list[list[int]]]:
    return np.asarray(mesh.vertices, dtype=float), np.asarray(mesh.faces, dtype=int).tolist()


def connected_components(mesh: trimesh.Trimesh) -> int | None:
    try:
        return len(mesh.split(only_watertight=False))
    except Exception:
        return None


def mesh_metrics(mesh: trimesh.Trimesh) -> dict[str, Any]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "connected_components": connected_components(mesh),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "euler_number": int(mesh.euler_number),
        "volume_mm3": float(mesh.volume),
        "surface_area_mm2": float(mesh.area),
        "bbox_min_mm": [float(x) for x in bounds[0]],
        "bbox_max_mm": [float(x) for x in bounds[1]],
        "size_mm": [float(x) for x in bounds[1] - bounds[0]],
    }


def print_gate_record(mesh: trimesh.Trimesh, max_components: int) -> dict[str, Any]:
    vertices, faces = mesh_arrays(mesh)
    gate = PrintabilityGate(
        "strict",
        max_components=max_components,
        euler_expected=int(mesh.euler_number),
        print_profile=get_profile(PROFILE_KEY),
        scale_mm=1.0,
        overhang_threshold_deg=45.0,
    )
    report = gate.check(vertices, faces)
    return {
        "passed": bool(report.passed),
        "mode": report.mode,
        "euler_expected": int(mesh.euler_number),
        "n_components": int(report.n_components),
        "winding_bfs_ok": bool(report.winding_bfs_ok),
        "errors": [{"code": i.code, "message": i.message} for i in report.errors],
        "warnings": [{"code": i.code, "message": i.message} for i in report.warnings],
        "summary": report.summary(),
    }


def layer_preview_record(mesh: trimesh.Trimesh, layer_height_mm: float) -> dict[str, Any]:
    vertices, faces = mesh_arrays(mesh)
    preview = slice_layers(vertices, faces, layer_height_mm)
    non_empty = [layer for layer in preview.layers if layer.n_segments > 0]
    return {
        "layer_height_mm": float(layer_height_mm),
        "n_layers": int(preview.n_layers),
        "non_empty_layers": int(preview.non_empty_layers),
        "first_non_empty_z_mm": float(non_empty[0].z) if non_empty else None,
        "last_non_empty_z_mm": float(non_empty[-1].z) if non_empty else None,
        "max_segments_in_layer": int(max((layer.n_segments for layer in preview.layers), default=0)),
        "bbox_min_mm": [float(x) for x in preview.bbox_min],
        "bbox_max_mm": [float(x) for x in preview.bbox_max],
        "passes_non_empty_preview": bool(preview.n_layers > 0 and preview.non_empty_layers > 0),
    }


def detect_slicers() -> dict[str, Any]:
    papp = detect_slicer()
    candidates = []
    for name in COMMON_SLICER_COMMANDS:
        found = shutil.which(name)
        if found:
            candidates.append({"command": name, "path": found})
    return {
        "papp_supported_slicer": None if papp is None else {"name": papp.name, "path": str(papp.path)},
        "path_candidates": candidates,
        "supported_slicer_detected": papp is not None,
    }


def export_component(component: dict[str, Any], profile: Any, slicer_info: Any | None) -> dict[str, Any]:
    mesh = component["mesh"]
    component_id = component["component_id"]
    max_components = int(component["max_components"])
    target_dir = COMPONENT_DIR / component_id
    stl_path = target_dir / f"{component_id}.stl"
    threemf_path = target_dir / f"{component_id}.3mf"
    obj_path = target_dir / f"{component_id}.obj"
    gcode_path = target_dir / f"{component_id}.gcode"
    vertices, faces = mesh_arrays(mesh)
    metadata = {
        "case_id": CASE_ID,
        "rw_stage": "RW9",
        "component_id": component_id,
        "role": component["role"],
    }
    write_stl(stl_path, vertices, faces, solid_name=component_id[:60], scale_mm=1.0)
    write_3mf(threemf_path, vertices, faces, unit="millimeter", object_name=component_id[:60], metadata=metadata, scale_mm=1.0)
    mesh.export(obj_path)
    stl_info = read_stl_info(stl_path)
    threemf_info = read_3mf_info(threemf_path)
    gate = print_gate_record(mesh, max_components=max_components)
    preview = layer_preview_record(mesh, float(profile.layer_height_mm))
    if slicer_info is None:
        external_slicer = {
            "attempted": False,
            "ok": False,
            "blocked_reason": "No supported PrusaSlicer/CuraEngine CLI detected on PATH",
        }
    else:
        result = slice_mesh(stl_path, output_path=gcode_path, slicer=slicer_info, timeout_s=SLICER_TIMEOUT_S)
        external_slicer = {
            "attempted": True,
            "ok": bool(result.ok),
            "slicer": result.slicer,
            "gcode_path": rel(result.gcode_path) if result.gcode_path else None,
            "layer_count": int(result.layer_count),
            "estimated_time_s": float(result.estimated_time_s),
            "filament_mm": float(result.filament_mm),
            "error": result.error,
        }
    return {
        "component_id": component_id,
        "role": component["role"],
        "description": component["description"],
        "parameters": component["parameters"],
        "max_components": max_components,
        "artifacts": {
            "stl": rel(stl_path),
            "threemf": rel(threemf_path),
            "obj": rel(obj_path),
            "gcode": external_slicer.get("gcode_path"),
        },
        "mesh_metrics": mesh_metrics(mesh),
        "stl_info": stl_info,
        "threemf_info": threemf_info,
        "printability_gate": gate,
        "layer_preview": preview,
        "external_slicer": external_slicer,
        "passes_package_preflight": bool(
            stl_path.exists()
            and threemf_path.exists()
            and obj_path.exists()
            and stl_info.get("valid_size")
            and threemf_info.get("n_triangles") == len(faces)
            and gate["passed"]
            and preview["passes_non_empty_preview"]
        ),
    }


def make_components(params: dict[str, float]) -> list[dict[str, Any]]:
    pin_radius = params["pin_radius_mm"]
    hole_radius = params["pin_hole_inner_radius_mm"]
    outer_radius = params["outer_boss_radius_mm"]
    knuckle_width = params["knuckle_width_mm"]
    axial_gap = params["axial_gap_mm"]
    nominal_pin_d = 2.0 * pin_radius
    nominal_hole_d = 2.0 * hole_radius

    hole_diameters = [round(nominal_hole_d + delta, 3) for delta in (-0.30, -0.15, 0.00, 0.15, 0.30)]
    pin_diameters = [round(nominal_pin_d + delta, 3) for delta in (-0.15, -0.075, 0.00, 0.075, 0.15)]

    hole_sleeves = []
    for idx, diameter in enumerate(hole_diameters):
        hole_sleeves.append(tube_along_x(
            outer_radius=outer_radius,
            inner_radius=diameter / 2.0,
            length=5.0,
            center=(idx * 10.0, 0.0, 0.0),
        ))
    pin_rods = []
    for idx, diameter in enumerate(pin_diameters):
        pin_rods.append(cylinder_along_x(
            radius=diameter / 2.0,
            length=18.0,
            center=(idx * 8.0, 0.0, 0.0),
        ))

    outer_center_span = knuckle_width + axial_gap + knuckle_width
    outer_pair = concat([
        tube_along_x(outer_radius=outer_radius, inner_radius=hole_radius, length=knuckle_width, center=(-outer_center_span / 2.0, 0.0, 0.0)),
        tube_along_x(outer_radius=outer_radius, inner_radius=hole_radius, length=knuckle_width, center=(outer_center_span / 2.0, 0.0, 0.0)),
    ])
    center_knuckle = tube_along_x(outer_radius=outer_radius, inner_radius=hole_radius, length=knuckle_width, center=(0.0, 0.0, 0.0))
    nominal_pin = cylinder_along_x(radius=pin_radius, length=2.0 * knuckle_width + axial_gap + 5.0, center=(0.0, 0.0, 0.0))

    return [
        {
            "component_id": "TREE_007_RW9_hole_sweep_sleeves",
            "role": "hole_diameter_sweep",
            "description": "Five standalone sleeve coupons with the RW7f outer boss radius and hole diameters around the nominal hinge-hole diameter.",
            "parameters": {"hole_diameters_mm": hole_diameters, "outer_diameter_mm": round(2.0 * outer_radius, 3), "sleeve_width_mm": 5.0},
            "mesh": concat(hole_sleeves),
            "max_components": len(hole_sleeves),
        },
        {
            "component_id": "TREE_007_RW9_pin_sweep_rods",
            "role": "printed_pin_diameter_sweep",
            "description": "Five printable pin rods around the nominal RW7f pin diameter; metal pin of nominal diameter may be tested against the same holes.",
            "parameters": {"pin_diameters_mm": pin_diameters, "rod_length_mm": 18.0},
            "mesh": concat(pin_rods),
            "max_components": len(pin_rods),
        },
        {
            "component_id": "TREE_007_RW9_nominal_outer_knuckle_pair",
            "role": "nominal_outer_knuckle_pair",
            "description": "Two nominal outer knuckle sleeves representing the fork side of a TREE_007 hinge; test with center knuckle and nominal pin.",
            "parameters": {"hole_diameter_mm": round(nominal_hole_d, 3), "outer_diameter_mm": round(2.0 * outer_radius, 3), "knuckle_width_mm": knuckle_width, "center_gap_mm": axial_gap},
            "mesh": outer_pair,
            "max_components": 2,
        },
        {
            "component_id": "TREE_007_RW9_nominal_center_knuckle",
            "role": "nominal_center_knuckle",
            "description": "Single nominal center knuckle sleeve for static assembly fit with the outer pair and nominal pin.",
            "parameters": {"hole_diameter_mm": round(nominal_hole_d, 3), "outer_diameter_mm": round(2.0 * outer_radius, 3), "knuckle_width_mm": knuckle_width},
            "mesh": center_knuckle,
            "max_components": 1,
        },
        {
            "component_id": "TREE_007_RW9_nominal_pin_reference",
            "role": "nominal_pin_reference",
            "description": "Printable nominal pin reference matching the RW7f pin radius; intended as a geometry reference, not a metal-pin substitution claim.",
            "parameters": {"pin_diameter_mm": round(nominal_pin_d, 3), "pin_length_mm": round(2.0 * knuckle_width + axial_gap + 5.0, 3)},
            "mesh": nominal_pin,
            "max_components": 1,
        },
    ]


def write_measurement_templates(params: dict[str, float], component_records: list[dict[str, Any]]) -> dict[str, str]:
    MEASUREMENT_DIR.mkdir(parents=True, exist_ok=True)
    csv_path = MEASUREMENT_DIR / "rw9_static_fit_measurement_template.csv"
    fields = [
        "record_id", "coupon_component", "feature_id", "nominal_mm", "measured_mm_1", "measured_mm_2", "measured_mm_3",
        "mean_measured_mm", "tool", "fit_with_nominal_pin", "fit_class", "notes",
    ]
    rows: list[dict[str, Any]] = []
    for record in component_records:
        role = record["role"]
        pars = record["parameters"]
        if role == "hole_diameter_sweep":
            for idx, value in enumerate(pars["hole_diameters_mm"]):
                rows.append({"record_id": f"H{idx}", "coupon_component": record["component_id"], "feature_id": f"hole_diameter_{idx}", "nominal_mm": value})
        elif role == "printed_pin_diameter_sweep":
            for idx, value in enumerate(pars["pin_diameters_mm"]):
                rows.append({"record_id": f"P{idx}", "coupon_component": record["component_id"], "feature_id": f"pin_diameter_{idx}", "nominal_mm": value})
        elif role in {"nominal_outer_knuckle_pair", "nominal_center_knuckle"}:
            rows.append({"record_id": f"K{len(rows)}", "coupon_component": record["component_id"], "feature_id": "hole_diameter", "nominal_mm": pars["hole_diameter_mm"]})
            rows.append({"record_id": f"K{len(rows)}", "coupon_component": record["component_id"], "feature_id": "knuckle_width", "nominal_mm": pars["knuckle_width_mm"]})
        elif role == "nominal_pin_reference":
            rows.append({"record_id": "NP0", "coupon_component": record["component_id"], "feature_id": "pin_diameter", "nominal_mm": pars["pin_diameter_mm"]})
    with csv_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            full = {field: "" for field in fields}
            full.update(row)
            writer.writerow(full)

    protocol = {
        "measurement_status": "pending_physical_print_and_measurement",
        "required_metadata": ["printer", "material", "nozzle_diameter_mm", "layer_height_mm", "orientation", "slicer", "temperature_settings", "measurement_tool"],
        "fit_class_values": ["too_tight_no_insert", "tight_insert", "sliding_fit", "loose_fit", "too_loose"],
        "nominal_rw7f_parameters_mm": params,
        "acceptance_rule_before_rw10": {
            "must_print_coupon": True,
            "must_measure_hole_and_pin_features": True,
            "must_identify_best_hole_pin_pair": True,
            "nominal_pair_required_outcome": "sliding_fit_or_documented_adjustment",
            "no_moving_prototype_claim_without_rw9_measurement": True,
        },
    }
    protocol_path = MEASUREMENT_DIR / "rw9_static_fit_measurement_protocol.json"
    write_json(protocol_path, protocol)
    return {"measurement_csv_template": rel(csv_path), "measurement_protocol_json": rel(protocol_path)}


def build_doc(payload: dict[str, Any]) -> str:
    component_rows = []
    for record in payload["component_records"]:
        component_rows.append([
            f"`{record['component_id']}`",
            record["role"],
            record["mesh_metrics"]["connected_components"],
            record["mesh_metrics"]["watertight"],
            record["mesh_metrics"]["is_volume"],
            record["printability_gate"]["passed"],
            record["layer_preview"]["passes_non_empty_preview"],
            record["artifacts"]["stl"],
        ])
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    blocker_rows = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW9 static fit coupon package

Status: `{payload['status']}`.

RW9 prepares a static coupon package for the corrected RW7f/RW8g TREE_007 hinge geometry.  This is a print-and-measure package, not a measured result.

## Inputs

| input | path/status |
| --- | --- |
| RW7f rebuild | `{payload['precondition']['rw7f_report']}` |
| RW8g export | `{payload['precondition']['rw8g_report']}` |
| RW8h audit | `{payload['precondition']['rw8h_report']}` |
| selected candidate | `{payload['selected_candidate_id']}` |

## Coupon parameters

| parameter | value |
| --- | --- |
| pin diameter | {payload['coupon_parameters_mm']['pin_diameter_mm']} mm |
| nominal hole diameter | {payload['coupon_parameters_mm']['hole_diameter_mm']} mm |
| nominal radial clearance | {payload['coupon_parameters_mm']['nominal_radial_clearance_mm']} mm |
| outer boss diameter | {payload['coupon_parameters_mm']['outer_boss_diameter_mm']} mm |
| knuckle width | {payload['coupon_parameters_mm']['knuckle_width_mm']} mm |
| center axial gap | {payload['coupon_parameters_mm']['axial_gap_mm']} mm |

## Component exports

{table(['component', 'role', 'components', 'watertight', 'volume', 'print gate', 'layer preview', 'STL'], component_rows)}

## Measurement artifacts

- CSV template: `{payload['measurement_artifacts']['measurement_csv_template']}`
- Protocol JSON: `{payload['measurement_artifacts']['measurement_protocol_json']}`

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Claim boundary

RW9 has not printed or measured anything.  It only prepares the coupon package and measurement protocol.  Static coupon validation, fabrication readiness, moving prototype validation, and physical hingeability remain blocked until physical measurements are entered and reviewed.

## Open blockers

{table(['blocker'], blocker_rows)}

## Next task

Print and measure the RW9 coupon package, fill the CSV measurement template, then run a RW9b measurement ingestion/report gate before any RW10 moving prototype work.
"""


def main() -> None:
    rw7f = load_json(RW7F_PATH)
    rw8g = load_json(RW8G_PATH)
    rw8h = load_json(RW8H_PATH)
    if not rw7f.get("summary", {}).get("body_preservation_passes"):
        raise RuntimeError("RW7f body preservation did not pass; refusing RW9")
    if not rw8g.get("summary", {}).get("all_component_exports_pass"):
        raise RuntimeError("RW8g component exports did not pass; refusing RW9")
    headline = rw8h.get("headline", {})
    if not headline.get("component_exports_all_clean_watertight_volumes"):
        raise RuntimeError("RW8h component integrity did not pass; refusing RW9")

    if OUT_DIR.exists():
        # Safety: only clean this exact generated output directory under RESULT_ROOT.
        resolved = OUT_DIR.resolve()
        if not resolved.is_relative_to(RESULT_ROOT.resolve()):
            raise RuntimeError(f"refusing to clean unexpected path: {resolved}")
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    dps = rw7f["design_parameter_summary"]
    params = {
        "pin_radius_mm": float(dps["pin_radius_mm"]),
        "pin_diameter_mm": round(2.0 * float(dps["pin_radius_mm"]), 3),
        "pin_hole_inner_radius_mm": float(dps["pin_hole_inner_radius_mm"]),
        "hole_diameter_mm": round(2.0 * float(dps["pin_hole_inner_radius_mm"]), 3),
        "nominal_radial_clearance_mm": float(dps["nominal_radial_pin_clearance_mm"]),
        "outer_boss_radius_mm": float(dps["outer_boss_radius_mm"]),
        "outer_boss_diameter_mm": round(2.0 * float(dps["outer_boss_radius_mm"]), 3),
        "knuckle_width_mm": 2.4,
        "axial_gap_mm": max(0.30, 2.0 * float(dps["nominal_radial_pin_clearance_mm"])),
    }
    profile = get_profile(PROFILE_KEY)
    slicer_detection = detect_slicers()
    papp_slicer = detect_slicer()

    components = make_components(params)
    component_records = [export_component(component, profile, papp_slicer) for component in components]
    measurement_artifacts = write_measurement_templates(params, component_records)
    all_preflight_pass = all(record["passes_package_preflight"] for record in component_records)
    external_slicer_available = bool(slicer_detection["supported_slicer_detected"])
    external_gcode_generated = any(record["external_slicer"].get("ok") for record in component_records)
    status = (
        "rw9_static_fit_coupon_package_exports_and_external_gcode_pass_measurement_pending"
        if all_preflight_pass and external_gcode_generated
        else "rw9_static_fit_coupon_package_exports_pass_external_slicer_cli_blocked_measurement_pending"
        if all_preflight_pass and not external_slicer_available
        else "rw9_static_fit_coupon_package_preflight_blocked"
    )
    payload: dict[str, Any] = {
        "report_id": "S4-RW9-STATIC-FIT-COUPON-PACKAGE-2026-06-23",
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "selected_candidate_id": rw7f["selected_candidate_id"],
        "precondition": {
            "rw7f_report": rel(RW7F_PATH),
            "rw7f_status": rw7f["status"],
            "rw8g_report": rel(RW8G_PATH),
            "rw8g_status": rw8g["status"],
            "rw8h_report": rel(RW8H_PATH),
            "rw8h_status": rw8h["status"],
        },
        "profile": profile.to_dict(),
        "coupon_parameters_mm": params,
        "slicer_detection": slicer_detection,
        "component_records": component_records,
        "measurement_artifacts": measurement_artifacts,
        "summary": {
            "coupon_component_count": len(component_records),
            "all_coupon_exports_pass": all_preflight_pass,
            "external_slicer_available": external_slicer_available,
            "external_gcode_generated": external_gcode_generated,
            "coupon_printed_or_measured": False,
            "static_coupon_validated": False,
            "rw10_moving_prototype_unblocked": False,
        },
        "artifacts": {
            "json_report": rel(JSON_PATH),
            "manifest": rel(MANIFEST_PATH),
            "component_root": rel(COMPONENT_DIR),
            "measurement_root": rel(MEASUREMENT_DIR),
            "doc": rel(DOC_PATH),
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": [
            "No physical coupon has been printed or measured",
            "No measurement CSV has been filled and ingested",
            "No supported slicer CLI was detected on PATH; G-code is blocked" if not external_slicer_available else "External slicer result must be reviewed before printing",
            "Material strength, anisotropy, friction, wear, and pin retention remain untested",
            "Moving prototype and physical hingeability remain blocked until after measured RW9 acceptance",
        ],
        "acceptance": {
            "rw7f_body_preservation_passed": bool(rw7f.get("summary", {}).get("body_preservation_passes")),
            "rw8g_component_exports_passed": bool(rw8g.get("summary", {}).get("all_component_exports_pass")),
            "rw8h_component_integrity_passed": bool(headline.get("component_exports_all_clean_watertight_volumes")),
            "coupon_component_exports_written": len(component_records),
            "all_coupon_component_preflights_pass": all_preflight_pass,
            "measurement_template_written": bool((ROOT / measurement_artifacts["measurement_csv_template"]).exists()),
            "measurement_protocol_written": bool((ROOT / measurement_artifacts["measurement_protocol_json"]).exists()),
            "physical_coupon_printed": False,
            "physical_measurements_recorded": False,
            "static_coupon_validated": False,
            "rw10_moving_prototype_unblocked": False,
        },
        "next_task": "RW9b print/measure/ingest the static fit coupon measurements; RW10 moving prototype remains blocked.",
    }
    write_json(JSON_PATH, payload)
    write_json(MANIFEST_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "coupon_component_count": payload["summary"]["coupon_component_count"],
        "all_coupon_exports_pass": payload["summary"]["all_coupon_exports_pass"],
        "external_slicer_available": payload["summary"]["external_slicer_available"],
        "static_coupon_validated": payload["summary"]["static_coupon_validated"],
        "json_report": payload["artifacts"]["json_report"],
        "measurement_csv_template": payload["measurement_artifacts"]["measurement_csv_template"],
    }, indent=2))


if __name__ == "__main__":
    main()
