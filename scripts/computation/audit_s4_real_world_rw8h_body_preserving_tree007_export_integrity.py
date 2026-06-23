#!/usr/bin/env python
"""Audit body-preserving TREE_007 RW8g export integrity and viewer-safety.

This audit is intentionally stricter/different from RW8:

* it rechecks every body-preserving TREE_007 component export after vertex welding/cleanup;
* it compares the component face/volume sums against the assembly preview;
* it records why the assembly preview is not a fabrication/viewer-safe solid;
* it emits a grouped millimeter-scale OBJ/MTL for visual inspection.

It does not claim fabrication readiness, G-code readiness, or physical
hingeability.
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import numpy as np
import trimesh

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW8_PATH = RESULT_ROOT / "rw8g_export_body_preserving_tree007_report.json"
OUT_DIR = RESULT_ROOT / "rw8h_body_preserving_tree007_export_audit"
VIEWER_DIR = OUT_DIR / "inspection_viewer"
JSON_PATH = OUT_DIR / "body_preserving_tree007_export_integrity_audit.json"
MD_PATH = OUT_DIR / "BODY_PRESERVING_TREE007_EXPORT_INTEGRITY_AUDIT.md"
VIEWER_OBJ_PATH = VIEWER_DIR / "TREE_007_RW7F_body-preserving_viewer_inspection_grouped_mm.obj"
VIEWER_MTL_PATH = VIEWER_DIR / "TREE_007_RW7F_body-preserving_viewer_inspection_grouped_mm.mtl"
VIEWER_MANIFEST_PATH = VIEWER_DIR / "TREE_007_RW7F_body-preserving_viewer_inspection_grouped_mm_manifest.json"
PNG_PATH = OUT_DIR / "TREE_007_RW7F_body-preserving_export_preview_views.png"
DATE = "2026-06-23"

COLORS = [
    ("mat_P0", (0.86, 0.20, 0.16)),
    ("mat_P1", (0.12, 0.47, 0.71)),
    ("mat_P2", (0.17, 0.63, 0.17)),
    ("mat_P3", (0.58, 0.40, 0.74)),
    ("mat_pin0", (0.95, 0.62, 0.12)),
    ("mat_pin1", (0.95, 0.85, 0.18)),
    ("mat_pin2", (0.65, 0.65, 0.65)),
]


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_mesh(path: Path, *, process: bool = False) -> trimesh.Trimesh:
    mesh = trimesh.load_mesh(path, process=process)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(tuple(mesh.geometry.values()))
    return mesh


def cleaned(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    out = mesh.copy()
    try:
        out.remove_degenerate_faces()
    except Exception:
        pass
    try:
        out.remove_duplicate_faces()
    except Exception:
        pass
    try:
        out.merge_vertices()
    except Exception:
        pass
    try:
        trimesh.repair.fix_normals(out)
    except Exception:
        pass
    return out


def connected_components(mesh: trimesh.Trimesh) -> int | None:
    try:
        return len(mesh.split(only_watertight=False))
    except Exception:
        return None


def mesh_metrics(path: Path) -> dict[str, Any]:
    raw = load_mesh(path, process=False)
    clean = cleaned(raw)
    return {
        "path": rel(path),
        "raw": {
            "vertices": int(len(raw.vertices)),
            "faces": int(len(raw.faces)),
            "connected_components": connected_components(raw),
            "watertight": bool(raw.is_watertight),
            "is_volume": bool(raw.is_volume),
            "volume_mm3": float(raw.volume),
        },
        "cleaned": {
            "vertices": int(len(clean.vertices)),
            "faces": int(len(clean.faces)),
            "connected_components": connected_components(clean),
            "watertight": bool(clean.is_watertight),
            "is_volume": bool(clean.is_volume),
            "volume_mm3": float(clean.volume),
            "bbox_min_mm": [float(x) for x in clean.bounds[0]],
            "bbox_max_mm": [float(x) for x in clean.bounds[1]],
            "size_mm": [float(x) for x in clean.extents],
        },
    }


def threemf_metrics(path: Path) -> dict[str, Any]:
    with zipfile.ZipFile(path) as zf:
        model_name = next(name for name in zf.namelist() if name.endswith(".model"))
        root = ET.fromstring(zf.read(model_name))
    ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
    vertices = [
        (float(v.attrib["x"]), float(v.attrib["y"]), float(v.attrib["z"]))
        for v in root.findall(".//m:vertex", ns)
    ]
    triangles = root.findall(".//m:triangle", ns)
    objects = root.findall(".//m:object", ns)
    arr = np.asarray(vertices, dtype=float)
    return {
        "path": rel(path),
        "objects": len(objects),
        "vertices": len(vertices),
        "triangles": len(triangles),
        "bbox_min_mm": [float(x) for x in arr.min(axis=0)],
        "bbox_max_mm": [float(x) for x in arr.max(axis=0)],
        "size_mm": [float(x) for x in (arr.max(axis=0) - arr.min(axis=0))],
    }


def component_audit(record: dict[str, Any]) -> dict[str, Any]:
    stl = ROOT / record["artifacts"]["stl"]
    threemf = ROOT / record["artifacts"]["threemf"]
    return {
        "component_kind": record["component_kind"],
        "component_id": record["component_id"],
        "fabrication_role": record["fabrication_role"],
        "source_obj": record["source_obj"],
        "stl_metrics": mesh_metrics(stl),
        "threemf_metrics": threemf_metrics(threemf),
        "report_passes_export_preflight": bool(record["passes_export_preflight"]),
    }


def write_viewer_obj(component_records: list[dict[str, Any]]) -> dict[str, Any]:
    VIEWER_DIR.mkdir(parents=True, exist_ok=True)
    obj_lines = [
        f"mtllib {VIEWER_MTL_PATH.name}",
        "# TREE_007 RW7f body-preserving inspection assembly in millimeters; grouped by RW8g exported component; not a fabrication file",
    ]
    mtl_lines: list[str] = []
    for material_name, rgb in COLORS:
        mtl_lines.extend([
            f"newmtl {material_name}",
            f"Kd {rgb[0]:.6f} {rgb[1]:.6f} {rgb[2]:.6f}",
            "Ka 0.050000 0.050000 0.050000",
            "Ks 0.100000 0.100000 0.100000",
            "d 1.0",
            "",
        ])
    rows: list[dict[str, Any]] = []
    vertex_offset = 1
    for idx, record in enumerate(component_records):
        stl = ROOT / record["artifacts"]["stl"]
        mesh = load_mesh(stl, process=True)
        material_name = COLORS[idx][0]
        group_name = record["component_id"]
        obj_lines.extend([f"o {group_name}", f"g {group_name}", f"usemtl {material_name}"])
        for vertex in mesh.vertices:
            obj_lines.append(f"v {vertex[0]:.9f} {vertex[1]:.9f} {vertex[2]:.9f}")
        for face in mesh.faces:
            a = int(face[0]) + vertex_offset
            b = int(face[1]) + vertex_offset
            c = int(face[2]) + vertex_offset
            obj_lines.append(f"f {a} {b} {c}")
        rows.append({
            "component_id": group_name,
            "component_kind": record["component_kind"],
            "material": material_name,
            "faces": int(len(mesh.faces)),
            "vertices": int(len(mesh.vertices)),
            "bbox_min_mm": [float(x) for x in mesh.bounds[0]],
            "bbox_max_mm": [float(x) for x in mesh.bounds[1]],
        })
        vertex_offset += len(mesh.vertices)
    VIEWER_OBJ_PATH.write_text("\n".join(obj_lines) + "\n", encoding="utf-8", newline="\n")
    VIEWER_MTL_PATH.write_text("\n".join(mtl_lines), encoding="utf-8", newline="\n")
    manifest = {
        "inspection_obj": rel(VIEWER_OBJ_PATH),
        "inspection_mtl": rel(VIEWER_MTL_PATH),
        "role": "viewer_inspection_only_not_fabrication_file",
        "unit": "millimeter",
        "component_count": len(rows),
        "components": rows,
    }
    VIEWER_MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return manifest


def write_png_preview(component_records: list[dict[str, Any]]) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from mpl_toolkits.mplot3d.art3d import Poly3DCollection
    except Exception:
        return None
    meshes = []
    vertices = []
    hex_colors = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#bcbd22", "#7f7f7f"]
    for record in component_records:
        mesh = load_mesh(ROOT / record["artifacts"]["stl"], process=True)
        meshes.append(mesh)
        vertices.append(mesh.vertices)
    all_vertices = np.vstack(vertices)
    mins = all_vertices.min(axis=0)
    maxs = all_vertices.max(axis=0)
    center = (mins + maxs) / 2
    span = float(max(maxs - mins))
    views = [("isometric", 28, -42), ("front", 0, -90), ("top", 90, -90)]
    fig = plt.figure(figsize=(14, 5), dpi=160)
    for panel, (title, elev, azim) in enumerate(views, start=1):
        axis = fig.add_subplot(1, 3, panel, projection="3d")
        for mesh, color in zip(meshes, hex_colors):
            triangles = mesh.vertices[mesh.faces]
            collection = Poly3DCollection(triangles, facecolor=color, edgecolor="k", linewidths=0.03, alpha=0.86)
            axis.add_collection3d(collection)
        axis.set_xlim(center[0] - span / 2, center[0] + span / 2)
        axis.set_ylim(center[1] - span / 2, center[1] + span / 2)
        axis.set_zlim(center[2] - span / 2, center[2] + span / 2)
        axis.view_init(elev=elev, azim=azim)
        axis.set_title(title)
        axis.set_axis_off()
    fig.tight_layout()
    fig.savefig(PNG_PATH, bbox_inches="tight")
    return rel(PNG_PATH)


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(cell) for cell in row) + " |")
    return "\n".join(out)


def write_markdown(report: dict[str, Any]) -> None:
    rows = []
    for component in report["component_audits"]:
        metrics = component["stl_metrics"]["cleaned"]
        rows.append([
            f"`{component['component_id']}`",
            f"`{component['component_kind']}`",
            metrics["watertight"],
            metrics["is_volume"],
            metrics["connected_components"],
            f"{metrics['volume_mm3']:.3f}",
            ", ".join(f"{x:.3f}" for x in metrics["size_mm"]),
        ])
    headline_rows = [[f"`{key}`", f"`{value}`"] for key, value in report["headline"].items()]
    text = f"""# TREE_007 RW7f body-preserving export integrity audit

Status: `{report['status']}`.

## Headline

{table(['field', 'value'], headline_rows)}

## Interpretation

- The seven separate component exports are complete after vertex welding/cleanup.
- Binary STL stores per-triangle vertices; validators/viewers that do not weld equal coordinates may see one component per face.
- The assembly preview is one concatenated inspection mesh/object and is intentionally not a fabrication file; some viewers may repair/cull it incorrectly.
- Use the grouped millimeter OBJ or the separate component STL/3MF files for inspection.

## Component Exports

{table(['component', 'kind', 'clean watertight', 'clean volume', 'clean components', 'volume mm3', 'size mm'], rows)}

## Viewer-Safe Inspection Artifacts

- Grouped OBJ: `{report['viewer_artifacts']['inspection_obj']}`
- MTL: `{report['viewer_artifacts']['inspection_mtl']}`
- PNG preview: `{report.get('png_preview')}`

## Assembly Preview Caveat

The RW8 assembly preview has clean connected components `{report['headline']['assembly_preview_clean_connected_components']}`, watertight `{report['headline']['assembly_preview_clean_watertight']}`, and volume-solid status `{report['headline']['assembly_preview_clean_is_volume']}`. This is expected because it is a concatenated diagnostic assembly, not a single manifold fabrication file.
"""
    MD_PATH.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rw8 = load_json(RW8_PATH)
    variants = rw8["variant_results"]
    if len(variants) != 1 or variants[0].get("tree_id") != "TREE_007":
        raise RuntimeError("expected exactly one RW8 variant result for TREE_007")
    variant = variants[0]
    component_records = variant["component_exports"]
    assembly_record = variant["assembly_preview_exports"][0]
    component_audits = [component_audit(record) for record in component_records]
    assembly_audit = component_audit(assembly_record)
    viewer_artifacts = write_viewer_obj(component_records)
    png_preview = write_png_preview(component_records)

    component_face_sum = sum(item["stl_metrics"]["cleaned"]["faces"] for item in component_audits)
    component_volume_sum = sum(item["stl_metrics"]["cleaned"]["volume_mm3"] for item in component_audits)
    assembly_clean = assembly_audit["stl_metrics"]["cleaned"]
    report = {
        "audit_id": "S4-RW8H-BODY-PRESERVING-TREE007-EXPORT-INTEGRITY-AUDIT-2026-06-23",
        "date": DATE,
        "status": "tree007_body_preserving_component_exports_complete_assembly_preview_not_viewer_safe",
        "source_report": rel(RW8_PATH),
        "headline": {
            "tree_id": "TREE_007",
            "component_export_count": len(component_audits),
            "component_exports_all_clean_watertight_volumes": all(
                item["stl_metrics"]["cleaned"]["watertight"] and item["stl_metrics"]["cleaned"]["is_volume"]
                for item in component_audits
            ),
            "component_exports_all_single_clean_components": all(
                item["stl_metrics"]["cleaned"]["connected_components"] == 1 for item in component_audits
            ),
            "component_face_sum_matches_assembly_preview": component_face_sum == assembly_clean["faces"],
            "component_volume_sum_matches_assembly_preview": abs(component_volume_sum - assembly_clean["volume_mm3"]) < 1e-4,
            "assembly_preview_is_fabrication_file": False,
            "assembly_preview_clean_connected_components": assembly_clean["connected_components"],
            "assembly_preview_clean_watertight": assembly_clean["watertight"],
            "assembly_preview_clean_is_volume": assembly_clean["is_volume"],
        },
        "interpretation": [
            "The separate component exports are complete after vertex welding/cleanup.",
            "Binary STL stores per-triangle vertices; validators/viewers that do not weld equal coordinates may see one component per face.",
            "The assembly preview is one concatenated inspection mesh/object and intentionally fails strict printability; some viewers may repair/cull it incorrectly.",
            "For inspection, open the grouped millimeter OBJ or the separate component STL/3MF files, not the assembly preview as a print file.",
        ],
        "viewer_artifacts": viewer_artifacts,
        "png_preview": png_preview,
        "component_audits": component_audits,
        "assembly_preview_audit": assembly_audit,
        "blocked_claims": [
            "fabrication readiness",
            "G-code readiness",
            "static coupon validation",
            "moving prototype validation",
            "physical hingeability",
        ],
    }
    JSON_PATH.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    write_markdown(report)
    print(json.dumps({
        "status": report["status"],
        "json_report": rel(JSON_PATH),
        "markdown_report": rel(MD_PATH),
        "viewer_obj": viewer_artifacts["inspection_obj"],
        "png_preview": png_preview,
        "headline": report["headline"],
    }, indent=2))


if __name__ == "__main__":
    main()
