#!/usr/bin/env python
"""Audit RW8f geometry regression for TREE_007 refined hardware.

This gate checks the external-review concern that RW7e/RW8d mesh-valid outputs
no longer preserve the closed tetrahedron body envelope. It compares the RW2
source body solids, the RW3 theta=0 snapshot, the RW7b boolean rebuilt pieces,
and the RW7e refined printed-body meshes.

RW8f is intentionally a blocking audit: mesh watertightness and component export
are insufficient if the body pieces no longer reconstruct the closed tetrahedron.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np
import trimesh
from trimesh import repair


ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
DOC_PATH = ROOT / "docs" / "S4_RW8F_TREE007_GEOMETRY_REGRESSION_AUDIT.md"
JSON_PATH = RESULT_ROOT / "rw8f_tree007_geometry_regression_audit_report.json"
SCALE_MM = 60.0
PIECE_IDS = ["P0", "P1", "P2", "P3"]

SOURCE_DIR = RESULT_ROOT / "meshes" / "body_solids"
KIN_THETA0_OBJ = RESULT_ROOT / "kinematics" / "snapshots" / "tree_007_theta_000000.obj"
SOURCE_COMBINED_OBJ = SOURCE_DIR / "s4_body_solids_combined.obj"
RW7B_DIR = RESULT_ROOT / "cad_boolean_rebuild"
RW7E_DIR = RESULT_ROOT / "cad_hardware_mechanical_refinement" / "TREE_007"
WORK_ORDER_PATH = RESULT_ROOT / "cad_boolean_prep" / "rw7_selected_candidate_work_order.json"

BLOCKING_RETENTION_THRESHOLD = 0.90
BBOX_X_MAX_TOLERANCE_MM = 0.25


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def load_obj_min(path: Path) -> trimesh.Trimesh:
    vertices: list[list[float]] = []
    faces: list[list[int]] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("v "):
            parts = line.split()
            vertices.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif line.startswith("f "):
            indices = [int(item.split("/")[0]) - 1 for item in line.split()[1:]]
            if len(indices) == 3:
                faces.append(indices)
            elif len(indices) > 3:
                for index in range(1, len(indices) - 1):
                    faces.append([indices[0], indices[index], indices[index + 1]])
    mesh = trimesh.Trimesh(vertices=np.asarray(vertices, dtype=float), faces=np.asarray(faces, dtype=int), process=True)
    repair.fix_normals(mesh)
    return mesh


def parse_obj_signature(path: Path) -> dict[str, Any]:
    vertices: list[tuple[float, float, float]] = []
    faces: list[tuple[int, ...]] = []
    groups: list[str] = []
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("v "):
            parts = line.split()
            vertices.append((float(parts[1]), float(parts[2]), float(parts[3])))
        elif line.startswith("f "):
            faces.append(tuple(int(item.split("/")[0]) for item in line.split()[1:]))
        elif line.startswith("g ") or line.startswith("o "):
            groups.append(line)
    normalized = "\n".join([repr(vertices), repr(faces)])
    return {
        "vertex_count": len(vertices),
        "face_count": len(faces),
        "groups_or_objects": groups,
        "vertices_faces_sha256": hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
    }


def mesh_metrics(path: Path) -> dict[str, Any]:
    mesh = load_obj_min(path)
    volume_model = abs(float(mesh.volume))
    bounds_min = mesh.bounds[0]
    bounds_max = mesh.bounds[1]
    return {
        "path": rel(path),
        "vertex_count": int(len(mesh.vertices)),
        "face_count": int(len(mesh.faces)),
        "watertight": bool(mesh.is_watertight),
        "is_volume": bool(mesh.is_volume),
        "volume_model": volume_model,
        "volume_mm3": volume_model * SCALE_MM ** 3,
        "bounds_min_model": [float(x) for x in bounds_min],
        "bounds_max_model": [float(x) for x in bounds_max],
        "bounds_min_mm": [float(x * SCALE_MM) for x in bounds_min],
        "bounds_max_mm": [float(x * SCALE_MM) for x in bounds_max],
    }


def piece_path(stage: str, piece_id: str) -> Path:
    if stage == "rw2_source":
        return SOURCE_DIR / f"{piece_id}.obj"
    if stage == "rw7b_boolean_rebuild":
        return RW7B_DIR / f"{piece_id}_rw7b_boolean_rebuilt.obj"
    if stage == "rw7e_refined_hardware":
        return RW7E_DIR / f"TREE_007_{piece_id}_printed_body_with_bosses.obj"
    raise KeyError(stage)


def load_relief_operations() -> list[dict[str, Any]]:
    work_order = json.loads(WORK_ORDER_PATH.read_text(encoding="utf-8"))
    operations = []
    for op in work_order.get("relief_boolean_work_order", []):
        if op.get("tree_id") != "TREE_007":
            continue
        targets = [target.get("piece_id") for target in op.get("target_piece_operations", [])]
        if not any(piece_id in {"P2", "P3"} for piece_id in targets):
            continue
        mn = [float(x) for x in op["proxy_box_min_model"]]
        mx = [float(x) for x in op["proxy_box_max_model"]]
        extent = [mx[i] - mn[i] for i in range(3)]
        operations.append({
            "operation_id": op.get("operation_id"),
            "operation_kind": op.get("operation_kind"),
            "piece_pair": op.get("piece_pair"),
            "targets": targets,
            "proxy_box_min_model": mn,
            "proxy_box_max_model": mx,
            "proxy_box_extent_model": extent,
            "proxy_box_min_mm": [x * SCALE_MM for x in mn],
            "proxy_box_max_mm": [x * SCALE_MM for x in mx],
            "proxy_box_extent_mm": [x * SCALE_MM for x in extent],
        })
    return operations


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def build_payload() -> dict[str, Any]:
    stage_metrics = {
        stage: {piece_id: mesh_metrics(piece_path(stage, piece_id)) for piece_id in PIECE_IDS}
        for stage in ["rw2_source", "rw7b_boolean_rebuild", "rw7e_refined_hardware"]
    }
    source_total_model = sum(stage_metrics["rw2_source"][piece_id]["volume_model"] for piece_id in PIECE_IDS)
    source_x_max_mm = max(stage_metrics["rw2_source"][piece_id]["bounds_max_mm"][0] for piece_id in PIECE_IDS)

    retention = {}
    for stage in ["rw7b_boolean_rebuild", "rw7e_refined_hardware"]:
        retention[stage] = {}
        for piece_id in PIECE_IDS:
            src = stage_metrics["rw2_source"][piece_id]["volume_model"]
            now = stage_metrics[stage][piece_id]["volume_model"]
            retention[stage][piece_id] = now / src

    combined_signature = parse_obj_signature(SOURCE_COMBINED_OBJ)
    theta0_signature = parse_obj_signature(KIN_THETA0_OBJ)
    source_and_theta0_same_raw_geometry = (
        combined_signature["vertices_faces_sha256"] == theta0_signature["vertices_faces_sha256"]
    )

    totals = {}
    for stage in ["rw2_source", "rw7b_boolean_rebuild", "rw7e_refined_hardware"]:
        total_model = sum(stage_metrics[stage][piece_id]["volume_model"] for piece_id in PIECE_IDS)
        x_max_mm = max(stage_metrics[stage][piece_id]["bounds_max_mm"][0] for piece_id in PIECE_IDS)
        totals[stage] = {
            "body_volume_model": total_model,
            "body_volume_mm3": total_model * SCALE_MM ** 3,
            "retention_vs_rw2_source": total_model / source_total_model,
            "max_x_mm": x_max_mm,
            "x_max_loss_mm_vs_source": source_x_max_mm - x_max_mm,
        }

    p2_p3_rw7b_destroyed = all(
        retention["rw7b_boolean_rebuild"][piece_id] < BLOCKING_RETENTION_THRESHOLD
        for piece_id in ["P2", "P3"]
    )
    p2_p3_rw7e_destroyed = all(
        retention["rw7e_refined_hardware"][piece_id] < BLOCKING_RETENTION_THRESHOLD
        for piece_id in ["P2", "P3"]
    )
    rw7e_loses_tetra_x_extent = totals["rw7e_refined_hardware"]["x_max_loss_mm_vs_source"] > BBOX_X_MAX_TOLERANCE_MM
    rw7e_preserves_closed_envelope = not (p2_p3_rw7e_destroyed or rw7e_loses_tetra_x_extent)

    acceptance = {
        "rw2_rw3_theta0_same_raw_vertices_faces": source_and_theta0_same_raw_geometry,
        "rw7b_preserves_piece_body_volumes": not p2_p3_rw7b_destroyed,
        "rw7e_preserves_closed_tetra_body_envelope": rw7e_preserves_closed_envelope,
        "p2_p3_regression_confirmed_before_hardware_union": p2_p3_rw7b_destroyed,
        "rw9_static_coupon_allowed": rw7e_preserves_closed_envelope,
    }

    status = (
        "rw8f_confirms_rw7b_body_regression_rw9_blocked"
        if not acceptance["rw9_static_coupon_allowed"]
        else "rw8f_passes_closed_body_envelope_gate"
    )

    return {
        "status": status,
        "date": "2026-06-23",
        "case_id": CASE_ID,
        "tree_id": "TREE_007",
        "scale_mm": SCALE_MM,
        "retention_threshold": BLOCKING_RETENTION_THRESHOLD,
        "bbox_x_max_tolerance_mm": BBOX_X_MAX_TOLERANCE_MM,
        "acceptance": acceptance,
        "stage_metrics": stage_metrics,
        "retention_vs_source": retention,
        "stage_totals": totals,
        "source_combined_signature": combined_signature,
        "theta0_signature": theta0_signature,
        "tree007_p2_p3_relief_operations": load_relief_operations(),
        "decision": {
            "rw9": "blocked",
            "reason": "RW7e/RW8d meshes are watertight/exportable but do not preserve the closed tetrahedron body envelope; P2/P3 are truncated in RW7b before hardware refinement.",
            "next_required_task": "RW7f body-preserving CAD rebuild from RW2/RW3 source solids with a pre-hardware envelope-preservation gate.",
        },
    }


def build_doc(payload: dict[str, Any]) -> str:
    rows = []
    for piece_id in PIECE_IDS:
        source = payload["stage_metrics"]["rw2_source"][piece_id]
        rw7b = payload["stage_metrics"]["rw7b_boolean_rebuild"][piece_id]
        rw7e = payload["stage_metrics"]["rw7e_refined_hardware"][piece_id]
        rows.append([
            piece_id,
            f"{source['volume_mm3']:.1f}",
            f"{rw7b['volume_mm3']:.1f}",
            f"{payload['retention_vs_source']['rw7b_boolean_rebuild'][piece_id] * 100:.2f}%",
            f"{rw7e['volume_mm3']:.1f}",
            f"{payload['retention_vs_source']['rw7e_refined_hardware'][piece_id] * 100:.2f}%",
            f"{rw7e['bounds_max_mm'][0]:.3f}",
        ])

    total_rows = []
    for stage, metrics in payload["stage_totals"].items():
        total_rows.append([
            stage,
            f"{metrics['body_volume_mm3']:.1f}",
            f"{metrics['retention_vs_rw2_source'] * 100:.2f}%",
            f"{metrics['max_x_mm']:.3f}",
            f"{metrics['x_max_loss_mm_vs_source']:.3f}",
        ])

    operation_rows = []
    for op in payload["tree007_p2_p3_relief_operations"]:
        operation_rows.append([
            op["operation_id"],
            op["piece_pair"],
            op["targets"],
            [round(x, 3) for x in op["proxy_box_min_mm"]],
            [round(x, 3) for x in op["proxy_box_max_mm"]],
            [round(x, 3) for x in op["proxy_box_extent_mm"]],
        ])

    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]

    return f"""# S4 RW8f TREE_007 geometry regression audit

Status: `{payload['status']}`.

RW8f was added after external review of the TREE_007 real-world package. The
review concern is confirmed: RW2/RW3 preserve the closed tetrahedron geometry,
but the RW7b boolean rebuild truncates P2/P3 before RW7e hardware refinement.
RW8d/RW8e mesh/export validity is therefore not sufficient for physical coupon
progress.

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Piece volume comparison

All volumes are reported at the 60 mm model scale.

{table(['piece', 'RW2 source mm3', 'RW7b mm3', 'RW7b retained', 'RW7e mm3', 'RW7e retained', 'RW7e max x mm'], rows)}

## Body totals

{table(['stage', 'body volume mm3', 'retained vs RW2', 'max x mm', 'x loss vs source mm'], total_rows)}

## Confirmed source sanity

`results/{CASE_ID}/real_world/meshes/body_solids/s4_body_solids_combined.obj`
and `results/{CASE_ID}/real_world/kinematics/snapshots/tree_007_theta_000000.obj`
have the same vertex/face SHA-256 hash:

```text
{payload['source_combined_signature']['vertices_faces_sha256']}
```

So the closed zero-thickness body and theta=0 kinematic snapshot agree. The
regression appears after that point.

## Suspect RW7 relief operations

{table(['operation', 'piece pair', 'targets', 'box min mm', 'box max mm', 'box extent mm'], operation_rows)}

The first listed operation cuts from about `x=29.2 mm` through the tetra vertex
region at `x=60 mm` and is applied directly to P2/P3. This is not a local hinge
clearance; it removes most of the P2/P3 body mass.

## Decision

RW9 static coupon fabrication is blocked. The next required task is `RW7f`:
rebuild the TREE_007 CAD body from RW2/RW3 source solids with a body-preserving
pre-hardware gate, then reapply hardware only after P0-P3 retain the closed
body envelope within an explicit tolerance.

Generated report: `{rel(JSON_PATH)}`.
"""


def main() -> None:
    payload = build_payload()
    write_json(JSON_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(f"status: {payload['status']}")
    print(f"report: {rel(JSON_PATH)}")
    print(f"doc: {rel(DOC_PATH)}")
    if not payload["acceptance"]["rw9_static_coupon_allowed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
