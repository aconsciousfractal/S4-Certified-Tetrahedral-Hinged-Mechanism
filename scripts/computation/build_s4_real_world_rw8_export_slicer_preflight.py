#!/usr/bin/env python
"""RW8 STL/3MF export and slicer preflight for S4 real-world variants.

RW8 consumes the passing RW7d connectivity-repaired variant when available, otherwise the RW7c hardware-solidization variants and produces
millimeter-scaled STL/3MF exports plus layer-preview evidence.  It keeps a
strict boundary between:

* component exports that are plausible print inputs after later slicer/coupon
  gates;
* assembly-preview exports, useful for inspection but not a fabrication claim;
* external G-code slicing, which is attempted only when a supported slicer CLI
  is available on PATH.

Scope boundary: RW8 is an export/preflight gate.  It does not print a coupon,
does not measure fit, does not validate motion, and does not claim physical
hingeability or fabrication readiness.
"""

from __future__ import annotations

import json
import re
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

DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW7C_PATH = RESULT_ROOT / "rw7c_hinge_hardware_solidization_report.json"
RW7D_PATH = RESULT_ROOT / "rw7d_hinge_connectivity_repair_report.json"
JSON_PATH = RESULT_ROOT / "rw8_export_slicer_preflight_report.json"
OUT_DIR = RESULT_ROOT / "export_slicer_preflight"
MANIFEST_PATH = OUT_DIR / "rw8_export_slicer_preflight_manifest.json"
DOC_PATH = ROOT / "docs" / "S4_RW8_EXPORT_SLICER_PREFLIGHT.md"

PROFILE_KEY = "fdm"
ASSEMBLY_MAX_COMPONENTS = 12
SLICER_TIMEOUT_S = 120.0

BLOCKED_CLAIMS_ALWAYS = [
    "physical hingeability",
    "fabrication readiness",
    "static coupon validation",
    "moving prototype validation",
    "public theorem promotion from physical evidence",
]

OPEN_BLOCKERS_BASE = [
    "external slicer/G-code may be unavailable or unvalidated",
    "material strength, anisotropy, friction, wear, and pin retention are untested",
    "pin insertion/removal and assembly sequence are not physically tested",
    "static fit coupon has not been printed or measured",
    "moving prototype has not been printed or measured",
]

COMMON_SLICER_COMMANDS = [
    "prusa-slicer",
    "prusaslicer",
    "PrusaSlicer",
    "CuraEngine",
    "curaengine",
    "OrcaSlicer",
    "orca-slicer",
    "bambu-studio",
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


def safe_name(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9_.-]+", "_", value.strip())
    return text.strip("_") or "component"


def load_obj_groups(path: Path) -> list[dict[str, Any]]:
    vertices: list[list[float]] = []
    group_faces: dict[str, list[list[int]]] = {}
    order: list[str] = []
    current = path.stem
    order.append(current)
    group_faces[current] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("g ") or line.startswith("o "):
            current = safe_name(line.split(maxsplit=1)[1])
            if current not in group_faces:
                group_faces[current] = []
                order.append(current)
            continue
        if line.startswith("v "):
            parts = line.split()
            vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
            continue
        if line.startswith("f "):
            idx = [int(token.split("/")[0]) - 1 for token in line.split()[1:]]
            if len(idx) < 3:
                continue
            for i in range(1, len(idx) - 1):
                group_faces[current].append([idx[0], idx[i], idx[i + 1]])
    records: list[dict[str, Any]] = []
    global_vertices = np.asarray(vertices, dtype=float)
    for name in order:
        faces = group_faces.get(name, [])
        if not faces:
            continue
        used = sorted({int(v) for face in faces for v in face})
        remap = {old: new for new, old in enumerate(used)}
        local_vertices = global_vertices[used]
        local_faces = [[remap[int(v)] for v in face] for face in faces]
        mesh = trimesh.Trimesh(vertices=local_vertices, faces=np.asarray(local_faces, dtype=int), process=False)
        mesh = clean_mesh_for_export(mesh)
        records.append({"name": name, "vertices": np.asarray(mesh.vertices, dtype=float), "faces": np.asarray(mesh.faces, dtype=int).tolist(), "mesh": mesh})
    return records


def clean_mesh_for_export(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    cleaned = mesh.copy()
    try:
        mask = cleaned.nondegenerate_faces()
        cleaned.update_faces(mask)
    except Exception:
        pass
    try:
        unique = cleaned.unique_faces()
        cleaned.update_faces(unique)
    except Exception:
        pass
    try:
        cleaned.remove_unreferenced_vertices()
    except Exception:
        pass
    try:
        cleaned.merge_vertices()
    except Exception:
        pass
    try:
        repair.fix_winding(cleaned)
    except Exception:
        pass
    try:
        repair.fix_normals(cleaned)
    except Exception:
        pass
    try:
        repair.fill_holes(cleaned)
    except Exception:
        pass
    return cleaned


def mesh_arrays(mesh: trimesh.Trimesh) -> tuple[np.ndarray, list[list[int]]]:
    return np.asarray(mesh.vertices, dtype=float), np.asarray(mesh.faces, dtype=int).tolist()


def mesh_metrics(mesh: trimesh.Trimesh, scale_mm: float) -> dict[str, Any]:
    bounds = np.asarray(mesh.bounds, dtype=float)
    size = (bounds[1] - bounds[0]) * scale_mm
    return {
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "winding_consistent": bool(mesh.is_winding_consistent),
        "is_volume": bool(mesh.is_volume),
        "euler_number": int(mesh.euler_number),
        "volume_model_units": float(mesh.volume),
        "surface_area_model_units": float(mesh.area),
        "volume_mm3": float(mesh.volume * scale_mm ** 3),
        "surface_area_mm2": float(mesh.area * scale_mm ** 2),
        "bounds_min_model": [float(x) for x in bounds[0]],
        "bounds_max_model": [float(x) for x in bounds[1]],
        "bounds_min_mm": [float(x) for x in bounds[0] * scale_mm],
        "bounds_max_mm": [float(x) for x in bounds[1] * scale_mm],
        "size_mm": [float(x) for x in size],
    }


def print_gate_record(mesh: trimesh.Trimesh, scale_mm: float, max_components: int) -> dict[str, Any]:
    vertices, faces = mesh_arrays(mesh)
    vertices_mm = vertices * scale_mm
    euler_expected = int(mesh.euler_number)
    gate = PrintabilityGate(
        "strict",
        max_components=max_components,
        euler_expected=euler_expected,
        print_profile=get_profile(PROFILE_KEY),
        scale_mm=1.0,
        overhang_threshold_deg=45.0,
    )
    report = gate.check(vertices_mm, faces)
    return {
        "passed": bool(report.passed),
        "mode": report.mode,
        "euler_expected": euler_expected,
        "n_components": int(report.n_components),
        "winding_bfs_ok": bool(report.winding_bfs_ok),
        "errors": [{"code": i.code, "message": i.message} for i in report.errors],
        "warnings": [{"code": i.code, "message": i.message} for i in report.warnings],
        "summary": report.summary(),
    }


def layer_preview_record(mesh: trimesh.Trimesh, scale_mm: float, layer_height_mm: float) -> dict[str, Any]:
    vertices, faces = mesh_arrays(mesh)
    vertices_mm = vertices * scale_mm
    preview = slice_layers(vertices_mm, faces, layer_height_mm)
    non_empty = [layer for layer in preview.layers if layer.n_segments > 0]
    max_segments = max((layer.n_segments for layer in preview.layers), default=0)
    return {
        "layer_height_mm": float(layer_height_mm),
        "n_layers": int(preview.n_layers),
        "non_empty_layers": int(preview.non_empty_layers),
        "first_non_empty_z_mm": float(non_empty[0].z) if non_empty else None,
        "last_non_empty_z_mm": float(non_empty[-1].z) if non_empty else None,
        "max_segments_in_layer": int(max_segments),
        "bbox_min_mm": [float(x) for x in preview.bbox_min],
        "bbox_max_mm": [float(x) for x in preview.bbox_max],
        "passes_non_empty_preview": bool(preview.n_layers > 0 and preview.non_empty_layers > 0),
    }


def detect_slicers() -> dict[str, Any]:
    papp = detect_slicer()
    commands = []
    for name in COMMON_SLICER_COMMANDS:
        found = shutil.which(name)
        if found:
            commands.append({"command": name, "path": found})
    return {
        "papp_supported_slicer": None if papp is None else {"name": papp.name, "path": str(papp.path)},
        "path_candidates": commands,
        "supported_slicer_detected": papp is not None,
    }


def export_one(
    *,
    tree_id: str,
    component_kind: str,
    component_id: str,
    source_obj: str,
    mesh: trimesh.Trimesh,
    scale_mm: float,
    layer_height_mm: float,
    slicer_info: Any | None,
    max_components: int = 1,
    fabrication_role: str = "print_component",
) -> dict[str, Any]:
    name = safe_name(component_id)
    target_dir = OUT_DIR / tree_id / component_kind
    stl_path = target_dir / f"{name}.stl"
    threemf_path = target_dir / f"{name}.3mf"
    gcode_path = target_dir / f"{name}.gcode"
    vertices, faces = mesh_arrays(mesh)
    metadata = {
        "case_id": CASE_ID,
        "tree_id": tree_id,
        "component_kind": component_kind,
        "component_id": component_id,
        "source_obj": source_obj,
        "rw_stage": "RW8",
        "fabrication_role": fabrication_role,
    }
    write_stl(stl_path, vertices, faces, solid_name=name[:60], scale_mm=scale_mm)
    write_3mf(
        threemf_path,
        vertices,
        faces,
        unit="millimeter",
        object_name=name[:60],
        metadata=metadata,
        scale_mm=scale_mm,
    )
    stl_info = read_stl_info(stl_path)
    threemf_info = read_3mf_info(threemf_path)
    stl_mesh = trimesh.load_mesh(stl_path, process=False)
    if isinstance(stl_mesh, trimesh.Scene):
        stl_mesh = trimesh.util.concatenate(tuple(stl_mesh.geometry.values()))
    stl_mesh = clean_mesh_for_export(stl_mesh)
    gate = print_gate_record(mesh, scale_mm, max_components=max_components)
    preview = layer_preview_record(mesh, scale_mm, layer_height_mm)
    slice_result: dict[str, Any]
    if slicer_info is None:
        slice_result = {
            "attempted": False,
            "ok": False,
            "blocked_reason": "No supported PrusaSlicer/CuraEngine CLI detected on PATH",
        }
    else:
        result = slice_mesh(stl_path, output_path=gcode_path, slicer=slicer_info, timeout_s=SLICER_TIMEOUT_S)
        slice_result = {
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
        "tree_id": tree_id,
        "component_kind": component_kind,
        "component_id": component_id,
        "fabrication_role": fabrication_role,
        "source_obj": source_obj,
        "artifacts": {
            "stl": rel(stl_path),
            "threemf": rel(threemf_path),
            "gcode": slice_result.get("gcode_path"),
        },
        "source_mesh_metrics_model": mesh_metrics(mesh, scale_mm),
        "stl_reimport_metrics_mm": mesh_metrics(stl_mesh, 1.0),
        "stl_info": stl_info,
        "threemf_info": threemf_info,
        "printability_gate": gate,
        "layer_preview": preview,
        "external_slicer": slice_result,
        "passes_export_preflight": bool(
            stl_path.exists()
            and threemf_path.exists()
            and stl_info.get("valid_size")
            and threemf_info.get("n_triangles") == len(faces)
            and bool(stl_mesh.is_watertight)
            and bool(stl_mesh.is_volume)
            and gate["passed"]
            and preview["passes_non_empty_preview"]
        ),
    }


def build_doc(payload: dict[str, Any]) -> str:
    variant_rows = []
    for variant in payload["variant_results"]:
        variant_rows.append([
            variant["tree_id"],
            variant["summary"]["component_exports"],
            variant["summary"]["assembly_preview_exports"],
            variant["summary"]["all_component_exports_pass"],
            variant["summary"]["all_component_layer_previews_pass"],
            variant["summary"]["external_gcode_generated"],
            variant["artifacts"]["variant_export_dir"],
        ])
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    blocker_rows = [[item] for item in payload["open_blockers"]]
    slicer = payload["slicer_detection"]
    return f"""# S4 RW8 export and slicer preflight

Status: {payload['status']}.

RW8 exports the passing source hardware variant(s) to millimeter-scaled STL/3MF artifacts and runs layer-preview checks.  The export uses the local STL writer, stdlib 3MF writer, printability gate, and pure-Python layer preview.  External G-code slicing is attempted only if a supported PrusaSlicer/CuraEngine CLI is detected.

## Outputs

| artifact | path |
| --- | --- |
| RW8 JSON report | `{rel(JSON_PATH)}` |
| RW8 manifest | `{rel(MANIFEST_PATH)}` |
| export root | `{rel(OUT_DIR)}` |

## Variant summary

{table(['variant', 'component exports', 'assembly previews', 'component exports pass', 'layer previews pass', 'external G-code generated', 'export dir'], variant_rows)}

## Slicer detection

| field | value |
| --- | --- |
| PAPP supported slicer | {slicer['papp_supported_slicer']} |
| PATH candidates | {slicer['path_candidates']} |
| supported slicer detected | {slicer['supported_slicer_detected']} |

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Claim boundary

RW8 does not claim physical hingeability or fabrication readiness.  Passing component STL/3MF export and layer preview only means the selected component meshes are exportable and inspectable in a print-oriented format; assembly-preview exports are diagnostic and are not fabrication files.  Coupon and moving-prototype evidence are still required.

## Blockers still open

{table(['blocker'], blocker_rows)}

## Next task

RW9 should select one exported variant/component set, run a static fit coupon plan, and record measured pin/boss/hole tolerances before any moving prototype claim.
"""


def clean_export_dir() -> None:
    out = OUT_DIR.resolve()
    result_root = RESULT_ROOT.resolve()
    if not out.is_relative_to(result_root):
        raise RuntimeError(f"refusing to clean export path outside result root: {out}")
    if not OUT_DIR.exists():
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        return
    for child in OUT_DIR.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def main() -> None:
    clean_export_dir()
    source_path = RW7D_PATH if RW7D_PATH.exists() else RW7C_PATH
    source_stage = "RW7d" if source_path == RW7D_PATH else "RW7c"
    rw7c = load_json(source_path)
    profile = get_profile(PROFILE_KEY)
    scale_mm = float(rw7c["design_parameter_summary"]["scale_mm_per_model_unit"])
    layer_height_mm = float(profile.layer_height_mm)
    slicer_detection = detect_slicers()
    papp_slicer = detect_slicer()

    source_variants = rw7c["variant_results"]
    passing_source_variants = [
        v for v in source_variants
        if v.get("summary", {}).get("variant_passes_mesh_clearance_checks")
        or v.get("summary", {}).get("variant_passes_mesh_clearance_connectivity_checks")
    ]
    blocked_source_variants = [v for v in source_variants if v not in passing_source_variants]
    variant_results: list[dict[str, Any]] = []
    all_export_records: list[dict[str, Any]] = []
    for variant in passing_source_variants:
        tree_id = variant["tree_id"]
        component_records: list[dict[str, Any]] = []
        assembly_records: list[dict[str, Any]] = []
        for source_rel in variant["artifacts"]["printed_piece_objs"]:
            source = ROOT / source_rel
            groups = load_obj_groups(source)
            if len(groups) != 1:
                raise ValueError(f"expected one group in printed piece OBJ: {source_rel}")
            piece_match = re.search(r"_(P\d)_", source.name)
            piece_id = piece_match.group(1) if piece_match else groups[0]["name"]
            component_records.append(export_one(
                tree_id=tree_id,
                component_kind="printed_pieces",
                component_id=f"{tree_id}_{piece_id}_printed_body_with_bosses",
                source_obj=source_rel,
                mesh=groups[0]["mesh"],
                scale_mm=scale_mm,
                layer_height_mm=layer_height_mm,
                slicer_info=papp_slicer,
                max_components=1,
                fabrication_role="primary_print_component",
            ))
        pin_source_rel = variant["artifacts"]["pin_obj"]
        for group in load_obj_groups(ROOT / pin_source_rel):
            component_records.append(export_one(
                tree_id=tree_id,
                component_kind="removable_pin_references",
                component_id=group["name"],
                source_obj=pin_source_rel,
                mesh=group["mesh"],
                scale_mm=scale_mm,
                layer_height_mm=layer_height_mm,
                slicer_info=papp_slicer,
                max_components=1,
                fabrication_role="optional_printed_pin_or_metal_pin_reference",
            ))
        assembly_source_rel = variant["artifacts"]["combined_assembly_obj"]
        assembly_groups = load_obj_groups(ROOT / assembly_source_rel)
        assembly_mesh = trimesh.util.concatenate([g["mesh"] for g in assembly_groups])
        assembly_mesh = clean_mesh_for_export(assembly_mesh)
        assembly_records.append(export_one(
            tree_id=tree_id,
            component_kind="assembly_preview",
            component_id=f"{tree_id}_full_hardware_assembly_preview_not_fabrication_file",
            source_obj=assembly_source_rel,
            mesh=assembly_mesh,
            scale_mm=scale_mm,
            layer_height_mm=layer_height_mm,
            slicer_info=None,
            max_components=ASSEMBLY_MAX_COMPONENTS,
            fabrication_role="assembly_preview_not_fabrication_file",
        ))
        variant_summary = {
            "component_exports": len(component_records),
            "assembly_preview_exports": len(assembly_records),
            "all_component_exports_pass": all(r["passes_export_preflight"] for r in component_records),
            "all_component_layer_previews_pass": all(r["layer_preview"]["passes_non_empty_preview"] for r in component_records),
            "all_assembly_preview_exports_pass": all(r["passes_export_preflight"] for r in assembly_records),
            "external_gcode_generated": any(r["external_slicer"].get("ok") for r in component_records),
            "external_gcode_attempted": any(r["external_slicer"].get("attempted") for r in component_records),
        }
        variant_payload = {
            "tree_id": tree_id,
            "status": "rw8_variant_exports_and_layer_preview_pass" if variant_summary["all_component_exports_pass"] else "rw8_variant_export_preflight_blocked",
            "summary": variant_summary,
            "artifacts": {"variant_export_dir": rel(OUT_DIR / tree_id)},
            "component_exports": component_records,
            "assembly_preview_exports": assembly_records,
        }
        variant_results.append(variant_payload)
        all_export_records.extend(component_records)
        all_export_records.extend(assembly_records)

    all_component_records = [record for variant in variant_results for record in variant["component_exports"]]
    all_assembly_records = [record for variant in variant_results for record in variant["assembly_preview_exports"]]
    component_exports_pass = all(record["passes_export_preflight"] for record in all_component_records)
    assembly_exports_pass = all(record["passes_export_preflight"] for record in all_assembly_records)
    external_slicer_available = bool(slicer_detection["supported_slicer_detected"])
    external_gcode_generated = any(record["external_slicer"].get("ok") for record in all_component_records)
    status = (
        "rw8_component_exports_layer_preview_and_external_gcode_pass_coupon_gate_unblocked"
        if component_exports_pass and external_gcode_generated
        else "rw8_component_exports_and_papp_layer_preview_pass_external_slicer_cli_blocked"
        if component_exports_pass and not external_slicer_available
        else "rw8_component_export_preflight_blocked"
    )
    open_blockers = list(OPEN_BLOCKERS_BASE)
    if blocked_source_variants:
        open_blockers.insert(0, "Some source CAD variants remain blocked and are not exported by RW8: " + ", ".join(v.get("tree_id", "unknown") for v in blocked_source_variants))
    if not external_slicer_available:
        open_blockers.insert(0, "No supported PrusaSlicer/CuraEngine CLI was detected on PATH; G-code/layer-by-slicer preview is blocked")
    payload: dict[str, Any] = {
        "report_id": "S4-RW8-EXPORT-SLICER-PREFLIGHT-2026-06-22",
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "selected_candidate_id": rw7c["selected_candidate_id"],
        "precondition": {"source_cad_stage": source_stage, "source_cad_report": rel(source_path)},
        "profile": profile.to_dict(),
        "scale_mm_per_model_unit": scale_mm,
        "slicer_detection": slicer_detection,
        "summary": {
            "source_variant_count": len(source_variants),
            "source_passing_variant_count": len(passing_source_variants),
            "source_blocked_variant_count": len(blocked_source_variants),
            "variant_count": len(variant_results),
            "component_export_count": len(all_component_records),
            "assembly_preview_export_count": len(all_assembly_records),
            "stl_export_count": len(all_export_records),
            "threemf_export_count": len(all_export_records),
            "all_component_exports_pass": component_exports_pass,
            "all_assembly_preview_exports_pass": assembly_exports_pass,
            "external_slicer_available": external_slicer_available,
            "external_gcode_generated": external_gcode_generated,
            "static_coupon_printed_or_measured": False,
            "moving_prototype_printed_or_measured": False,
            "fabrication_ready": False,
            "physical_hingeability_claim_ready": False,
            "rw9_static_coupon_unblocked": component_exports_pass,
        },
        "source_blocked_variants": [
            {
                "tree_id": v.get("tree_id"),
                "status": v.get("status"),
                "summary": v.get("summary", {}),
            }
            for v in blocked_source_variants
        ],
        "variant_results": variant_results,
        "artifacts": {
            "json_report": rel(JSON_PATH),
            "manifest": rel(MANIFEST_PATH),
            "export_root": rel(OUT_DIR),
        },
        "blocked_claims": BLOCKED_CLAIMS_ALWAYS,
        "open_blockers": open_blockers,
        "acceptance": {
            "source_cad_report_present": source_path.exists(),
            "at_least_one_passing_source_variant_processed": len(variant_results) >= 1,
            "all_passing_source_variants_processed": len(variant_results) == len(passing_source_variants),
            "component_exports_written": len(all_component_records),
            "assembly_preview_exports_written": len(all_assembly_records),
            "all_component_stl_and_3mf_written": all(Path(ROOT / r["artifacts"]["stl"]).exists() and Path(ROOT / r["artifacts"]["threemf"]).exists() for r in all_component_records),
            "all_component_stl_reimports_valid_volume": all(r["stl_reimport_metrics_mm"]["watertight"] and r["stl_reimport_metrics_mm"]["is_volume"] for r in all_component_records),
            "all_component_printability_gates_pass": all(r["printability_gate"]["passed"] for r in all_component_records),
            "all_component_layer_previews_non_empty": all(r["layer_preview"]["passes_non_empty_preview"] for r in all_component_records),
            "all_assembly_preview_exports_pass": assembly_exports_pass,
            "external_slicer_cli_detected": external_slicer_available,
            "external_gcode_generated": external_gcode_generated,
            "static_coupon_not_run": True,
            "moving_prototype_not_run": True,
            "physical_claims_still_blocked": True,
        },
        "next_task": "RW9 static fit coupon plan/print/measurement using the RW8 exported passing variant; physical hingeability remains blocked until RW10 moving prototype measurements.",
    }
    write_json(JSON_PATH, payload)
    write_json(MANIFEST_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "component_export_count": payload["summary"]["component_export_count"],
        "assembly_preview_export_count": payload["summary"]["assembly_preview_export_count"],
        "all_component_exports_pass": payload["summary"]["all_component_exports_pass"],
        "external_slicer_available": payload["summary"]["external_slicer_available"],
        "rw9_static_coupon_unblocked": payload["summary"]["rw9_static_coupon_unblocked"],
        "json_report": payload["artifacts"]["json_report"],
    }, indent=2))


if __name__ == "__main__":
    main()
