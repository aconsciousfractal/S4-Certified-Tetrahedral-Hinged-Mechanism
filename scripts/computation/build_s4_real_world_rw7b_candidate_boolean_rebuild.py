#!/usr/bin/env python
"""Build RW7b selected-candidate boolean rebuild for S4.

RW7b executes the RW7 relief-box work order on the selected candidate using the
local trimesh + manifold3d boolean backend.  It produces candidate-only
boolean-rebuilt mesh OBJ artifacts and a validation report.

Scope boundary: this is a mesh boolean/rebuild gate for relief cutbacks only.
It does not design or boolean real hinge pin/boss/knuckle solids, does not
export STL/3MF, does not run a slicer, and does not validate a prototype.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from trimesh.creation import box
from trimesh import repair


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW7_PATH = RESULT_ROOT / "rw7_selected_candidate_cad_boolean_hardware_prep.json"
WORK_ORDER_PATH = RESULT_ROOT / "cad_boolean_prep" / "rw7_selected_candidate_work_order.json"
JSON_PATH = RESULT_ROOT / "rw7b_candidate_boolean_rebuild_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW7B_CANDIDATE_BOOLEAN_REBUILD.md"
REBUILD_DIR = RESULT_ROOT / "cad_boolean_rebuild"
COMBINED_OBJ_PATH = REBUILD_DIR / "rw7b_candidate_boolean_rebuilt_combined.obj"
MANIFEST_PATH = REBUILD_DIR / "rw7b_candidate_boolean_rebuild_manifest.json"

PIECE_IDS = ["P0", "P1", "P2", "P3"]
BOOLEAN_ENGINE = "manifold"

BLOCKED_CLAIMS = [
    "real hinge pin/boss/knuckle CAD validity",
    "direct printability",
    "STL/3MF export readiness",
    "G-code readiness",
    "fabrication readiness",
    "physical hingeability",
    "prototype validation",
]

OPEN_BLOCKERS = [
    "RW7b executes relief cutbacks only; real hinge hardware solids are still absent",
    "relief cutbacks are conservative axis-aligned boxes, not optimized manufacturable relief features",
    "hardware retention, insertion access, friction, wear, and material behavior remain untested",
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
    }


def cutter_from_operation(op: dict[str, Any]) -> trimesh.Trimesh:
    mn = op["proxy_box_min_model"]
    mx = op["proxy_box_max_model"]
    extent = [float(mx[i]) - float(mn[i]) for i in range(3)]
    center = [(float(mx[i]) + float(mn[i])) / 2.0 for i in range(3)]
    cutter = box(extents=extent)
    cutter.apply_translation(center)
    return cutter


def operations_by_piece(work_order: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    out = {piece_id: [] for piece_id in PIECE_IDS}
    for op in work_order["relief_boolean_work_order"]:
        for target in op["target_piece_operations"]:
            piece_id = target["piece_id"]
            op_copy = dict(op)
            op_copy["target_piece_id"] = piece_id
            op_copy["target_source_piece_obj"] = target["source_piece_obj"]
            out[piece_id].append(op_copy)
    return out


def export_obj(path: Path, mesh: trimesh.Trimesh, name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RW7b boolean-rebuilt mesh OBJ",
        "# relief booleans executed with trimesh + manifold3d",
        "# not STL/3MF, not slicer-ready, not prototype-validated",
        f"o {name}",
    ]
    for vertex in mesh.vertices:
        lines.append(f"v {vertex[0]:.12g} {vertex[1]:.12g} {vertex[2]:.12g}")
    for face in mesh.faces:
        a, b, c = [int(x) + 1 for x in face]
        lines.append(f"f {a} {b} {c}")
    write_text(path, "\n".join(lines))


def export_combined_obj(path: Path, piece_meshes: dict[str, trimesh.Trimesh]) -> None:
    lines = [
        "# RW7b combined boolean-rebuilt candidate OBJ",
        "# component groups are separate body pieces",
        "# relief booleans only; hardware solids absent",
    ]
    offset = 0
    for piece_id, mesh in piece_meshes.items():
        lines.append(f"g {piece_id}_rw7b_boolean_rebuilt")
        for vertex in mesh.vertices:
            lines.append(f"v {vertex[0]:.12g} {vertex[1]:.12g} {vertex[2]:.12g}")
        for face in mesh.faces:
            a, b, c = [int(x) + 1 + offset for x in face]
            lines.append(f"f {a} {b} {c}")
        offset += len(mesh.vertices)
    write_text(path, "\n".join(lines))


def run_piece_rebuild(piece_id: str, operations: list[dict[str, Any]]) -> tuple[trimesh.Trimesh, dict[str, Any], list[dict[str, Any]]]:
    if not operations:
        source_rel = f"results/{CASE_ID}/real_world/meshes/body_solids/{piece_id}.obj"
    else:
        source_rel = operations[0]["target_source_piece_obj"]
    source_path = ROOT / source_rel
    mesh = load_obj_min(source_path)
    initial_metrics = mesh_metrics(mesh)
    records = []
    current = mesh
    for sequence_index, op in enumerate(operations, start=1):
        before = mesh_metrics(current)
        cutter = cutter_from_operation(op)
        try:
            result = current.difference(cutter, engine=BOOLEAN_ENGINE)
            if isinstance(result, list):
                result = trimesh.util.concatenate(result)
            if result is None or len(result.faces) == 0:
                raise ValueError("boolean difference returned empty mesh")
            repair.fix_normals(result)
            after = mesh_metrics(result)
            ok = bool(after["watertight"] and after["is_volume"] and after["volume_model_units"] > 0.0)
            records.append({
                "piece_id": piece_id,
                "sequence_index": sequence_index,
                "operation_id": op["operation_id"],
                "tree_id": op["tree_id"],
                "route": op["route"],
                "boolean_engine": BOOLEAN_ENGINE,
                "status": "executed_valid_volume" if ok else "executed_but_invalid_volume",
                "before": before,
                "after": after,
                "volume_removed_model_units": float(before["volume_model_units"] - after["volume_model_units"]),
            })
            current = result
        except Exception as exc:
            records.append({
                "piece_id": piece_id,
                "sequence_index": sequence_index,
                "operation_id": op["operation_id"],
                "tree_id": op["tree_id"],
                "route": op["route"],
                "boolean_engine": BOOLEAN_ENGINE,
                "status": "boolean_failed",
                "error_type": type(exc).__name__,
                "error": str(exc),
                "before": before,
            })
    final_metrics = mesh_metrics(current)
    piece_path = REBUILD_DIR / f"{piece_id}_rw7b_boolean_rebuilt.obj"
    export_obj(piece_path, current, f"{piece_id}_rw7b_boolean_rebuilt")
    piece_result = {
        "piece_id": piece_id,
        "source_piece_obj": source_rel,
        "rebuilt_piece_obj": rel(piece_path),
        "operation_count": len(operations),
        "initial": initial_metrics,
        "final": final_metrics,
        "volume_removed_model_units": float(initial_metrics["volume_model_units"] - final_metrics["volume_model_units"]),
        "remaining_volume_fraction": float(final_metrics["volume_model_units"] / initial_metrics["volume_model_units"]),
        "all_piece_operations_executed_valid_volume": all(record["status"] == "executed_valid_volume" for record in records),
    }
    return current, piece_result, records


def build_doc(payload: dict[str, Any]) -> str:
    piece_rows = []
    for row in payload["piece_results"]:
        piece_rows.append([
            row["piece_id"],
            row["operation_count"],
            row["final"]["vertex_count"],
            row["final"]["face_count"],
            row["final"]["watertight"],
            row["final"]["is_volume"],
            round(row["remaining_volume_fraction"], 6),
            row["rebuilt_piece_obj"],
        ])
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    blocker_rows = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW7b candidate boolean rebuild

Status: {payload['status']}.

RW7b executes the RW7 relief-box work order for `{payload['selected_candidate_id']}` using `trimesh` with the `manifold3d` backend.  It writes boolean-rebuilt OBJ meshes for the four body pieces and a combined candidate OBJ.

## Outputs

| artifact | path |
| --- | --- |
| RW7b JSON report | `{rel(JSON_PATH)}` |
| RW7b manifest | `{rel(MANIFEST_PATH)}` |
| combined rebuilt OBJ | `{rel(COMBINED_OBJ_PATH)}` |

## Summary

| metric | value |
| --- | --- |
| selected candidate | `{payload['selected_candidate_id']}` |
| boolean engine | `{payload['boolean_engine']}` |
| manifold3d available | {payload['backend_capability']['manifold3d_available']} |
| planned subtractions | {payload['summary']['planned_boolean_subtraction_count']} |
| successful subtractions | {payload['summary']['successful_boolean_subtraction_count']} |
| all final pieces watertight | {payload['summary']['all_final_pieces_watertight']} |
| all final pieces valid volumes | {payload['summary']['all_final_pieces_valid_volumes']} |
| hardware solids present | {payload['summary']['hardware_solids_present']} |
| STL/3MF export run | {payload['summary']['stl_3mf_export_run']} |
| slicer run | {payload['summary']['slicer_gcode_run']} |

## Piece results

{table(['piece', 'cuts', 'verts', 'faces', 'watertight', 'valid volume', 'remaining volume fraction', 'OBJ'], piece_rows)}

The very small remaining volume fraction for some pieces is a physical-design warning: the box reliefs are conservative cutbacks, not optimized manufacturable features.

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Blockers still open

{table(['blocker'], blocker_rows)}

## Nonclaims

RW7b does not claim physical hingeability, direct printability, STL/3MF readiness, G-code readiness, fabrication readiness, or prototype validation.  It also does not yet create real hinge pin/boss/knuckle solids.

## Next task

RW7c should materialize real hinge hardware solids (pin, boss/knuckle, retention/insertion access) against the RW7b rebuilt bodies.  RW8 STL/3MF export should wait until RW7c passes.
"""


def main() -> None:
    rw7 = load_json(RW7_PATH)
    work_order = load_json(WORK_ORDER_PATH)
    selected_candidate_id = rw7["summary"]["selected_candidate_id"]
    ops = operations_by_piece(work_order)
    backend_capability = {
        "trimesh_version": getattr(trimesh, "__version__", "unknown"),
        "manifold3d_available": module_available("manifold3d"),
        "boolean_engine": BOOLEAN_ENGINE,
    }
    if not backend_capability["manifold3d_available"]:
        raise SystemExit("manifold3d is required for RW7b boolean rebuild")

    piece_meshes: dict[str, trimesh.Trimesh] = {}
    piece_results: list[dict[str, Any]] = []
    execution_records: list[dict[str, Any]] = []
    for piece_id in PIECE_IDS:
        mesh, piece_result, records = run_piece_rebuild(piece_id, ops[piece_id])
        piece_meshes[piece_id] = mesh
        piece_results.append(piece_result)
        execution_records.extend(records)

    export_combined_obj(COMBINED_OBJ_PATH, piece_meshes)
    successful = [record for record in execution_records if record["status"] == "executed_valid_volume"]
    planned_count = sum(len(items) for items in ops.values())
    all_final_watertight = all(row["final"]["watertight"] for row in piece_results)
    all_final_volumes = all(row["final"]["is_volume"] and row["final"]["volume_model_units"] > 0.0 for row in piece_results)
    payload: dict[str, Any] = {
        "report_id": "S4-RW7B-CANDIDATE-BOOLEAN-REBUILD-2026-06-22",
        "date": DATE,
        "case_id": CASE_ID,
        "status": "rw7b_relief_boolean_rebuild_completed_hardware_export_still_blocked",
        "selected_candidate_id": selected_candidate_id,
        "boolean_engine": BOOLEAN_ENGINE,
        "backend_capability": backend_capability,
        "precondition": {
            "rw7_report": rel(RW7_PATH),
            "rw7_work_order": rel(WORK_ORDER_PATH),
        },
        "summary": {
            "planned_boolean_subtraction_count": planned_count,
            "successful_boolean_subtraction_count": len(successful),
            "failed_boolean_subtraction_count": planned_count - len(successful),
            "all_final_pieces_watertight": all_final_watertight,
            "all_final_pieces_valid_volumes": all_final_volumes,
            "combined_rebuilt_obj_written": COMBINED_OBJ_PATH.exists(),
            "hardware_solids_present": False,
            "stl_3mf_export_run": False,
            "slicer_gcode_run": False,
            "static_coupon_printed_or_measured": False,
            "moving_prototype_printed_or_measured": False,
            "rw7c_hardware_solidization_unblocked": True,
        },
        "piece_results": piece_results,
        "boolean_execution_records": execution_records,
        "artifacts": {
            "json_report": rel(JSON_PATH),
            "manifest": rel(MANIFEST_PATH),
            "combined_rebuilt_obj": rel(COMBINED_OBJ_PATH),
            "piece_rebuilt_objs": [row["rebuilt_piece_obj"] for row in piece_results],
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": OPEN_BLOCKERS,
        "acceptance": {
            "rw7_work_order_present": WORK_ORDER_PATH.exists(),
            "manifold3d_backend_available": backend_capability["manifold3d_available"],
            "planned_boolean_subtraction_count_is_12": planned_count == 12,
            "all_planned_subtractions_executed_valid_volume": len(successful) == planned_count,
            "all_final_pieces_watertight": all_final_watertight,
            "all_final_pieces_valid_volumes": all_final_volumes,
            "combined_rebuilt_obj_written": COMBINED_OBJ_PATH.exists(),
            "hardware_solids_absent_and_blocked": True,
            "stl_3mf_export_not_run": True,
            "slicer_gcode_not_run": True,
            "prototype_validation_not_run": True,
            "rw7c_hardware_solidization_unblocked": True,
        },
        "next_task": "RW7c materialize real hinge hardware solids on the RW7b rebuilt bodies before STL/3MF export or slicer work.",
    }
    write_json(JSON_PATH, payload)
    write_json(MANIFEST_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "selected_candidate_id": selected_candidate_id,
        "successful_boolean_subtraction_count": len(successful),
        "planned_boolean_subtraction_count": planned_count,
        "all_final_pieces_watertight": all_final_watertight,
        "all_final_pieces_valid_volumes": all_final_volumes,
        "combined_rebuilt_obj": rel(COMBINED_OBJ_PATH),
        "next_task": payload["next_task"],
    }, indent=2))


if __name__ == "__main__":
    main()
