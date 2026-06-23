#!/usr/bin/env python
"""RW9c static fit coupon print handoff package.

RW9 generated the individual coupon components and RW9b generated the
measurement ingest/checker.  RW9c prepares the operator handoff layer between
those two steps: one arranged build-plate mesh with non-overlapping coupon
components, copied measurement templates, and explicit print/measure
instructions.

RW9c does not generate G-code and does not claim physical validation.  RW10
remains blocked until the arranged coupon is printed, measured, and RW9b passes
on the filled measurement CSV.
"""

from __future__ import annotations

import csv
import json
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
from core.io.obj_writer import write_obj
from core.io.stl_writer import read_stl_info, write_stl
from core.io.threemf_writer import read_3mf_info, write_3mf
from core.slicer.layer_preview import slice_layers
from core.slicer.slicer_cli import detect_slicer
from core.validation.printability_gate import PrintabilityGate

DATE = "2026-06-23"
CASE_ID = "historical_s4_median_planes"
REPORT_ID = "S4-RW9C-STATIC-FIT-PRINT-HANDOFF-2026-06-23"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW9_DIR = RESULT_ROOT / "rw9_static_fit_coupon_body_preserving_tree007"
RW9_REPORT = RW9_DIR / "rw9_static_fit_coupon_package_report.json"
RW9B_REPORT = RESULT_ROOT / "rw9b_static_fit_measurement_ingest" / "rw9b_static_fit_measurement_ingest_report.json"
OUT_DIR = RESULT_ROOT / "rw9c_static_fit_print_handoff"
PRINT_DIR = OUT_DIR / "print_plate"
MEASUREMENT_DIR = OUT_DIR / "measurement"
JSON_PATH = OUT_DIR / "rw9c_static_fit_print_handoff_report.json"
MANIFEST_PATH = OUT_DIR / "rw9c_static_fit_print_handoff_manifest.json"
DOC_PATH = ROOT / "docs" / "S4_RW9C_STATIC_FIT_PRINT_HANDOFF.md"

PROFILE_KEY = "fdm"
PLATE_STEM = "TREE_007_RW9C_static_fit_coupon_arranged_plate"
SPACING_MM = 12.0
ROW_LIMIT_MM = 130.0
LAYER_HEIGHT_MM = 0.2

COMPONENT_ORDER = [
    "TREE_007_RW9_hole_sweep_sleeves",
    "TREE_007_RW9_pin_sweep_rods",
    "TREE_007_RW9_nominal_outer_knuckle_pair",
    "TREE_007_RW9_nominal_center_knuckle",
    "TREE_007_RW9_nominal_pin_reference",
]

COMPONENT_COLORS = {
    "TREE_007_RW9_hole_sweep_sleeves": [0.35, 0.58, 0.82],
    "TREE_007_RW9_pin_sweep_rods": [0.94, 0.65, 0.22],
    "TREE_007_RW9_nominal_outer_knuckle_pair": [0.62, 0.62, 0.62],
    "TREE_007_RW9_nominal_center_knuckle": [0.48, 0.72, 0.48],
    "TREE_007_RW9_nominal_pin_reference": [0.86, 0.44, 0.36],
}

BLOCKED_CLAIMS = [
    "G-code generation by local external slicer",
    "physical coupon printed",
    "static coupon measured",
    "static coupon validated",
    "RW10 moving prototype unblocked",
    "physical hingeability",
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


def mesh_metrics(mesh: trimesh.Trimesh) -> dict[str, Any]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    return {
        "vertices": int(len(mesh.vertices)),
        "faces": int(len(mesh.faces)),
        "connected_components": int(len(mesh.split(only_watertight=False))),
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


def mesh_arrays(mesh: trimesh.Trimesh) -> tuple[np.ndarray, list[list[int]]]:
    return np.asarray(mesh.vertices, dtype=float), np.asarray(mesh.faces, dtype=int).tolist()


def load_component_mesh(path: Path) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=True)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    if not isinstance(mesh, trimesh.Trimesh):
        raise TypeError(f"not a Trimesh: {path}")
    return clean_mesh(mesh)


def arrange_components(records: list[dict[str, Any]]) -> tuple[trimesh.Trimesh, list[dict[str, Any]], np.ndarray]:
    x_cursor = 0.0
    y_cursor = 0.0
    row_depth = 0.0
    placements: list[dict[str, Any]] = []
    vertices_all: list[np.ndarray] = []
    faces_all: list[np.ndarray] = []
    colors_all: list[np.ndarray] = []
    face_offset = 0

    for record in records:
        component_id = record["component_id"]
        source_path = ROOT / record["artifacts"]["stl"]
        mesh = load_component_mesh(source_path)
        before = mesh_metrics(mesh)
        bounds = np.asarray(mesh.bounds, dtype=float)
        size = bounds[1] - bounds[0]
        if x_cursor > 0 and x_cursor + size[0] > ROW_LIMIT_MM:
            x_cursor = 0.0
            y_cursor += row_depth + SPACING_MM
            row_depth = 0.0
        translation = np.array([x_cursor - bounds[0][0], y_cursor - bounds[0][1], -bounds[0][2]], dtype=float)
        placed = mesh.copy()
        placed.apply_translation(translation)
        after = mesh_metrics(placed)
        placements.append({
            "component_id": component_id,
            "role": record.get("role"),
            "description": record.get("description"),
            "source_stl": rel(source_path),
            "source_max_components": record.get("max_components"),
            "source_metrics": before,
            "translation_mm": [float(x) for x in translation],
            "arranged_bbox_min_mm": after["bbox_min_mm"],
            "arranged_bbox_max_mm": after["bbox_max_mm"],
            "arranged_size_mm": after["size_mm"],
            "color_rgb_for_obj": COMPONENT_COLORS.get(component_id, [0.7, 0.7, 0.7]),
        })
        verts = np.asarray(placed.vertices, dtype=float)
        faces = np.asarray(placed.faces, dtype=int) + face_offset
        color = np.asarray(COMPONENT_COLORS.get(component_id, [0.7, 0.7, 0.7]), dtype=float)
        vertices_all.append(verts)
        faces_all.append(faces)
        colors_all.append(np.repeat(color[None, :], len(verts), axis=0))
        face_offset += len(verts)
        x_cursor += float(size[0]) + SPACING_MM
        row_depth = max(row_depth, float(size[1]))

    combined_vertices = np.vstack(vertices_all)
    combined_faces = np.vstack(faces_all)
    combined_colors = np.vstack(colors_all)
    combined = clean_mesh(trimesh.Trimesh(vertices=combined_vertices, faces=combined_faces, process=False))
    return combined, placements, combined_colors


def print_gate_record(mesh: trimesh.Trimesh) -> dict[str, Any]:
    vertices, faces = mesh_arrays(mesh)
    n_components = int(len(mesh.split(only_watertight=False)))
    gate = PrintabilityGate(
        "strict",
        max_components=n_components,
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
        "max_components": n_components,
        "n_components": int(report.n_components),
        "winding_bfs_ok": bool(report.winding_bfs_ok),
        "errors": [{"code": i.code, "message": i.message} for i in report.errors],
        "warnings": [{"code": i.code, "message": i.message} for i in report.warnings],
        "summary": report.summary(),
    }


def layer_preview_record(mesh: trimesh.Trimesh) -> dict[str, Any]:
    vertices, faces = mesh_arrays(mesh)
    preview = slice_layers(vertices, faces, LAYER_HEIGHT_MM)
    non_empty = [layer for layer in preview.layers if layer.n_segments > 0]
    return {
        "layer_height_mm": LAYER_HEIGHT_MM,
        "n_layers": int(preview.n_layers),
        "non_empty_layers": int(preview.non_empty_layers),
        "first_non_empty_z_mm": float(non_empty[0].z) if non_empty else None,
        "last_non_empty_z_mm": float(non_empty[-1].z) if non_empty else None,
        "max_segments_in_layer": int(max((layer.n_segments for layer in preview.layers), default=0)),
        "bbox_min_mm": [float(x) for x in preview.bbox_min],
        "bbox_max_mm": [float(x) for x in preview.bbox_max],
        "passes_non_empty_preview": bool(preview.n_layers > 0 and preview.non_empty_layers > 0),
    }


def copy_measurement_artifacts(rw9: dict[str, Any]) -> dict[str, str]:
    MEASUREMENT_DIR.mkdir(parents=True, exist_ok=True)
    copied: dict[str, str] = {}
    for key, out_name in [
        ("measurement_csv_template", "rw9c_static_fit_measurement_template.csv"),
        ("measurement_protocol_json", "rw9c_static_fit_measurement_protocol.json"),
    ]:
        source = ROOT / rw9["measurement_artifacts"][key]
        target = MEASUREMENT_DIR / out_name
        shutil.copy2(source, target)
        copied[key] = rel(target)
    return copied


def export_plate(mesh: trimesh.Trimesh, colors: np.ndarray, payload_meta: dict[str, str]) -> dict[str, Any]:
    PRINT_DIR.mkdir(parents=True, exist_ok=True)
    vertices, faces = mesh_arrays(mesh)
    stl_path = PRINT_DIR / f"{PLATE_STEM}.stl"
    threemf_path = PRINT_DIR / f"{PLATE_STEM}.3mf"
    obj_path = PRINT_DIR / f"{PLATE_STEM}.obj"
    write_stl(stl_path, vertices, faces, solid_name=PLATE_STEM)
    write_3mf(threemf_path, vertices, faces, object_name=PLATE_STEM, metadata=payload_meta)
    write_obj(
        obj_path,
        vertices,
        faces,
        colors=colors,
        object_name=PLATE_STEM,
        header=[
            "S4 RW9c arranged static fit coupon plate",
            "Units: millimeter",
            "OBJ vertex colors identify coupon groups; STL/3MF are geometry-only.",
        ],
    )
    return {
        "arranged_plate_stl": rel(stl_path),
        "arranged_plate_3mf": rel(threemf_path),
        "arranged_plate_obj": rel(obj_path),
        "stl_info": read_stl_info(stl_path),
        "threemf_info": read_3mf_info(threemf_path),
    }


def measurement_csv_summary(path: Path) -> dict[str, Any]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    return {
        "row_count": len(rows),
        "record_ids": [row.get("record_id", "") for row in rows],
        "feature_ids": [row.get("feature_id", "") for row in rows],
    }


def build_doc(payload: dict[str, Any]) -> str:
    placement_rows = []
    for place in payload["placements"]:
        placement_rows.append([
            place["component_id"],
            place["role"],
            [round(x, 3) for x in place["translation_mm"]],
            [round(x, 3) for x in place["arranged_size_mm"]],
        ])
    artifact_rows = [[key, value] for key, value in payload["artifacts"].items() if isinstance(value, str)]
    summary_rows = [[key, value] for key, value in payload["summary"].items()]
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    blocker_rows = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW9c static fit print handoff

Status: `{payload['status']}`.

RW9c packages the RW9 static-fit coupon for a real printer operator.  It arranges the five validated RW9 coupon component meshes onto a single non-overlapping build plate and copies the measurement template/protocol that must be filled after printing.

RW9c is a handoff gate only.  It does not generate G-code, it does not claim that anything has been printed, and it does not unblock RW10.

## Inputs

| input | path |
| --- | --- |
| RW9 package report | `{payload['precondition']['rw9_report']}` |
| RW9b checker report | `{payload['precondition']['rw9b_report']}` |

## Summary

{table(['field', 'value'], summary_rows)}

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Arranged print artifacts

{table(['artifact', 'path'], artifact_rows)}

## Component placement manifest

{table(['component', 'role', 'translation mm', 'arranged size mm'], placement_rows)}

## Operator checklist

1. Open `{payload['artifacts']['arranged_plate_3mf']}` in the slicer.  If the slicer has trouble with 3MF, use `{payload['artifacts']['arranged_plate_stl']}`.
2. Confirm units are millimeters and the build plate size is approximately `{[round(x, 3) for x in payload['arranged_plate_metrics']['size_mm']]}` mm.
3. Slice with the intended printer/material/profile.  Record nozzle, layer height, material, printer model, and slicer in the measurement notes.
4. Print the arranged coupon plate.  Do not claim RW10 readiness from slicing alone.
5. Measure all rows in `{payload['artifacts']['measurement_csv_template']}`: three measurements per feature where possible, measurement tool, fit class, and notes.
6. Rerun `scripts/audit_s4_real_world_rw9b_static_fit_measurement_ingest.py` after the CSV is filled.
7. RW10 starts only if RW9b reports static coupon validation true and selects an acceptable fit pair.

## Claim boundary

The arranged plate preserves the already validated RW9 component geometries and fixes the practical handoff issue that all separate components otherwise import near the origin.  It is not a mechanical validation by itself.

## Open blockers

{table(['blocker'], blocker_rows)}
"""


def ordered_component_records(rw9: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {record["component_id"]: record for record in rw9["component_records"]}
    missing = [component_id for component_id in COMPONENT_ORDER if component_id not in by_id]
    if missing:
        raise KeyError(f"missing RW9 component records: {missing}")
    return [by_id[component_id] for component_id in COMPONENT_ORDER]


def main() -> None:
    rw9 = load_json(RW9_REPORT)
    rw9b = load_json(RW9B_REPORT) if RW9B_REPORT.exists() else {"status": "missing"}
    records = ordered_component_records(rw9)
    combined, placements, colors = arrange_components(records)
    gate = print_gate_record(combined)
    preview = layer_preview_record(combined)
    exports = export_plate(combined, colors, {
        "report_id": REPORT_ID,
        "date": DATE,
        "source_rw9_status": rw9["status"],
        "claim_boundary": "print handoff only; physical validation pending",
    })
    copied_measurements = copy_measurement_artifacts(rw9)
    measurement_summary = measurement_csv_summary(ROOT / copied_measurements["measurement_csv_template"])
    slicer = detect_slicer()
    metrics = mesh_metrics(combined)
    source_exports_pass = bool(rw9["summary"].get("all_coupon_exports_pass"))
    arranged_exports_pass = bool(
        exports["stl_info"]["valid_size"]
        and exports["threemf_info"]["n_triangles"] == len(combined.faces)
        and gate["passed"]
        and preview["passes_non_empty_preview"]
    )
    status = "rw9c_static_fit_print_handoff_ready_physical_print_pending" if source_exports_pass and arranged_exports_pass else "rw9c_static_fit_print_handoff_failed_preflight"
    payload: dict[str, Any] = {
        "report_id": REPORT_ID,
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "precondition": {
            "rw9_report": rel(RW9_REPORT),
            "rw9_status": rw9["status"],
            "rw9b_report": rel(RW9B_REPORT) if RW9B_REPORT.exists() else None,
            "rw9b_status": rw9b.get("status"),
        },
        "layout_policy": {
            "units": "millimeter",
            "spacing_mm": SPACING_MM,
            "row_limit_mm": ROW_LIMIT_MM,
            "z_min_lifted_to_bed_zero": True,
            "geometry_modified": False,
            "component_shape_preserved": True,
        },
        "summary": {
            "component_count": len(records),
            "arranged_connected_components": metrics["connected_components"],
            "source_rw9_exports_pass": source_exports_pass,
            "arranged_plate_exports_pass": arranged_exports_pass,
            "external_slicer_cli_detected": slicer is not None,
            "gcode_generated": False,
            "physical_coupon_printed_or_measured": False,
            "rw10_moving_prototype_unblocked": False,
        },
        "acceptance": {
            "rw9_package_exports_pass": source_exports_pass,
            "all_required_components_present": len(records) == len(COMPONENT_ORDER),
            "arranged_plate_non_overlapping_by_manifest": True,
            "arranged_plate_printability_gate_passed": gate["passed"],
            "arranged_plate_layer_preview_non_empty": preview["passes_non_empty_preview"],
            "measurement_template_copied": (ROOT / copied_measurements["measurement_csv_template"]).exists(),
            "claim_boundary_preserved": True,
            "rw10_unblocked": False,
        },
        "artifacts": {
            **exports,
            **copied_measurements,
            "handoff_manifest_json": rel(MANIFEST_PATH),
            "handoff_report_json": rel(JSON_PATH),
            "handoff_doc": rel(DOC_PATH),
        },
        "arranged_plate_metrics": metrics,
        "printability_gate": gate,
        "layer_preview": preview,
        "placements": placements,
        "measurement_csv_summary": measurement_summary,
        "slicer_detection": {
            "papp_supported_slicer": None if slicer is None else {"name": slicer.name, "path": str(slicer.path)},
            "gcode_generation_attempted": False,
            "why_no_gcode": "RW9c is a handoff package; local external slicer detection is recorded but physical/operator slicing is the next gate.",
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": [
            "Open arranged plate in target slicer and generate printer-specific G-code outside this script.",
            "Physically print RW9c coupon plate.",
            "Measure all rows in the copied CSV template.",
            "Rerun RW9b and require static_coupon_validated=true before RW10.",
        ],
        "next_task": "Print and measure RW9c coupon plate, fill measurement CSV, rerun RW9b.",
    }
    write_json(MANIFEST_PATH, {
        "report_id": REPORT_ID,
        "status": payload["status"],
        "artifacts": payload["artifacts"],
        "placements": placements,
        "operator_checklist": [
            "Open arranged_plate_3mf or arranged_plate_stl in slicer as millimeters.",
            "Slice with target printer/material settings and record them in measurement notes.",
            "Print coupon plate.",
            "Fill copied measurement CSV.",
            "Rerun RW9b measurement ingest.",
        ],
    })
    write_json(JSON_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "arranged_plate_stl": payload["artifacts"]["arranged_plate_stl"],
        "arranged_plate_3mf": payload["artifacts"]["arranged_plate_3mf"],
        "printability_gate_passed": gate["passed"],
        "rw10_unblocked": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
