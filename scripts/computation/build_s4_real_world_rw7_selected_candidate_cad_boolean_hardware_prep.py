#!/usr/bin/env python
"""Build RW7 selected-candidate CAD boolean / hardware prep package.

RW7 consumes the RW6-selected candidate and produces a candidate-only work
order for the first real CAD/prototype step:

* map each relief proxy box to concrete target piece OBJ files;
* map each selected hinge envelope to RW2 axis placeholder coordinates;
* compute setback-shortened active hardware axes;
* write a candidate-only diagnostic OBJ containing the body solids plus the
  relief boxes that must be converted to real boolean subtractions.

RW7 intentionally does not execute boolean subtraction, mesh repair, STL/3MF
export, slicer preview, or any physical prototype validation.  The local PAPP
boolean wrapper is recorded as available only at the thin wrapper level; no
robust backend is assumed.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HAN_ROOT = ROOT.parents[5]
PAPP_ROOT = HAN_ROOT / "FRAMEWORK" / "04-SOFTWARE" / "PAPP"
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW2_PATH = RESULT_ROOT / "rw2_mesh_payload_manifest.json"
RW4E_PAYLOAD_PATH = RESULT_ROOT / "relief_hardware_candidates" / "rw4e_candidate_payloads.json"
RW4H_PATH = RESULT_ROOT / "rw4h_combined_cad_mesh_proxy_report.json"
RW5_PATH = RESULT_ROOT / "rw5_printability_fabrication_preflight_report.json"
RW6_PATH = RESULT_ROOT / "rw6_physical_red_team_package.json"
JSON_PATH = RESULT_ROOT / "rw7_selected_candidate_cad_boolean_hardware_prep.json"
DOC_PATH = ROOT / "docs" / "S4_RW7_SELECTED_CANDIDATE_CAD_BOOLEAN_HARDWARE_PREP.md"
PREP_DIR = RESULT_ROOT / "cad_boolean_prep"
PROXY_OBJ_PATH = PREP_DIR / "rw7_selected_candidate_boolean_prep_proxy.obj"
WORK_ORDER_PATH = PREP_DIR / "rw7_selected_candidate_work_order.json"

BOOLEAN_BLOCKERS = [
    "relief boxes are diagnostic proxy boxes, not boolean-subtracted CAD features",
    "real hinge pin/boss/knuckle solids are not yet modelled",
    "robust local boolean backend is unavailable or unverified",
    "mesh repair and winding normalization have not been run on a boolean result",
    "STL/3MF export has not been run",
    "slicer/layer preview and G-code have not been run",
    "static fit coupon and moving prototype have not been printed or measured",
]

BLOCKED_CLAIMS = [
    "CAD boolean validity",
    "direct printability",
    "STL/3MF export readiness",
    "G-code readiness",
    "fabrication readiness",
    "physical hingeability",
    "prototype validation",
]

ALLOWED_CLAIMS = [
    "RW7 creates a candidate-only CAD boolean and hardware work order for the RW6-selected candidate.",
    "RW7 maps each relief proxy and each selected hinge envelope to concrete upstream evidence records.",
    "RW7 writes a diagnostic OBJ for review only; it is not a printable CAD artifact.",
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


def get_candidate_id(rw6: dict[str, Any], rw5: dict[str, Any]) -> str:
    candidate = rw6.get("recommended_frontier_candidate", {}).get("candidate_id")
    if candidate:
        return str(candidate)
    candidate = rw5.get("summary", {}).get("recommended_rw6_frontier_candidate")
    if candidate:
        return str(candidate)
    raise ValueError("No selected candidate found in RW6/RW5")


def candidate_by_id(candidates: list[dict[str, Any]], candidate_id: str) -> dict[str, Any]:
    for candidate in candidates:
        if candidate.get("candidate_id") == candidate_id:
            return candidate
    raise KeyError(candidate_id)


def piece_obj_map(rw2: dict[str, Any]) -> dict[str, str]:
    out = {}
    for item in rw2["exports"]["piece_objs"]:
        out[item["piece_id"]] = item["path"]
    return out


def hinge_axis_index(rw2: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    for tree in rw2["hinge_axis_payload"]["trees"]:
        for hinge in tree["hinges"]:
            out[(tree["tree_id"], hinge["hinge_id"])] = hinge
    return out


def vec_sub(a: list[float], b: list[float]) -> list[float]:
    return [float(x) - float(y) for x, y in zip(a, b)]


def vec_add(a: list[float], b: list[float]) -> list[float]:
    return [float(x) + float(y) for x, y in zip(a, b)]


def vec_scale(a: list[float], s: float) -> list[float]:
    return [float(x) * s for x in a]


def to_mm(point: list[float], scale: float) -> list[float]:
    return [round(float(x) * scale, 9) for x in point]


def extent_mm(extent: list[float], scale: float) -> list[float]:
    return [round(float(x) * scale, 9) for x in extent]


def module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def papp_boolean_capability() -> dict[str, Any]:
    wrapper_path = PAPP_ROOT / "core" / "mesh_ops" / "boolean_ops.py"
    backend_modules = ["manifold3d", "bpy", "open3d", "cadquery", "solid2"]
    available_backends = [name for name in backend_modules if module_available(name)]
    return {
        "papp_root": str(PAPP_ROOT),
        "boolean_wrapper_path": str(wrapper_path),
        "papp_boolean_wrapper_present": wrapper_path.exists(),
        "trimesh_available": module_available("trimesh"),
        "robust_boolean_backend_modules_checked": backend_modules,
        "robust_boolean_backend_modules_available": available_backends,
        "robust_boolean_backend_available": bool(available_backends),
        "rw7_boolean_execution_policy": "not_executed_in_rw7_work_order_only",
    }


def count_obj_vertices(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.startswith("v "))


def box_obj_lines(name: str, box_min: list[float], box_max: list[float], vertex_offset: int) -> tuple[list[str], int]:
    x0, y0, z0 = [float(v) for v in box_min]
    x1, y1, z1 = [float(v) for v in box_max]
    verts = [
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1),
    ]
    faces = [
        (1, 2, 3), (1, 3, 4),
        (5, 8, 7), (5, 7, 6),
        (1, 5, 6), (1, 6, 2),
        (2, 6, 7), (2, 7, 3),
        (3, 7, 8), (3, 8, 4),
        (4, 8, 5), (4, 5, 1),
    ]
    safe_name = name.replace(" ", "_").replace("/", "_")
    lines = [f"g {safe_name}"]
    for x, y, z in verts:
        lines.append(f"v {x:.12g} {y:.12g} {z:.12g}")
    for a, b, c in faces:
        lines.append(f"f {a + vertex_offset} {b + vertex_offset} {c + vertex_offset}")
    return lines, vertex_offset + len(verts)


def write_candidate_proxy_obj(combined_obj_rel: str, relief_records: list[dict[str, Any]]) -> None:
    source = ROOT / combined_obj_rel
    body_text = source.read_text(encoding="utf-8").rstrip() + "\n"
    vertex_offset = count_obj_vertices(body_text)
    lines = [
        "# RW7 selected-candidate boolean prep proxy",
        "# Body solids copied from RW2 combined OBJ.",
        "# Relief boxes are diagnostic subtraction targets only; they are not boolean results.",
        body_text,
    ]
    for record in relief_records:
        group_name = "RW7_relief_box_" + record["operation_id"]
        box_lines, vertex_offset = box_obj_lines(group_name, record["proxy_box_min"], record["proxy_box_max"], vertex_offset)
        lines.extend(box_lines)
    write_text(PROXY_OBJ_PATH, "\n".join(lines))


def build_relief_work_order(
    selected_h: dict[str, Any],
    selected_e: dict[str, Any],
    piece_paths: dict[str, str],
    scale: float,
) -> list[dict[str, Any]]:
    e_ops = {op["operation_id"]: op for op in selected_e["relief_operations"]}
    rows = []
    for index, record in enumerate(selected_h["relief_proxy_records"], start=1):
        op = e_ops.get(record["operation_id"], {})
        targets = []
        for piece_id in record["piece_pair"]:
            targets.append({
                "piece_id": piece_id,
                "source_piece_obj": piece_paths.get(piece_id),
                "planned_operation": "mesh_difference(piece, relief_box)",
                "execution_status": "planned_not_executed",
            })
        rows.append({
            "index": index,
            "operation_id": record["operation_id"],
            "tree_id": record["tree_id"],
            "piece_pair": record["piece_pair"],
            "route": record["route"],
            "operation_kind": record["operation_kind"],
            "theta_domain_degrees": record["theta_domain_degrees"],
            "source_blocker_count": op.get("source_blocker_count"),
            "default_target_policy": "paired_piece_subtractions_for_review_not_final_design_choice",
            "target_piece_operations": targets,
            "proxy_shape": record["proxy_shape"],
            "proxy_box_min_model": record["proxy_box_min"],
            "proxy_box_max_model": record["proxy_box_max"],
            "proxy_box_extent_model": record["proxy_box_extent"],
            "proxy_box_extent_mm": extent_mm(record["proxy_box_extent"], scale),
            "proxy_box_volume_model_units": record["proxy_box_volume_model_units"],
            "support_point_count": record["support_point_count"],
            "support_span_model_units": record["support_span_model_units"],
            "applied_clearance_mm": record["applied_clearance_mm"],
            "applied_clearance_model_units": record["applied_clearance_model_units"],
            "clearance_margin_model_units": record["clearance_margin_model_units"],
            "clearance_margin_mm": round(float(record["clearance_margin_model_units"]) * scale, 9),
            "covers_guard_deficit": record["covers_guard_deficit"],
            "positive_proxy_volume": record["positive_proxy_volume"],
            "geometry_status": "rw7_work_order_only_not_boolean_subtracted",
        })
    return rows


def build_hardware_work_order(
    selected_e: dict[str, Any],
    axes: dict[tuple[str, str], dict[str, Any]],
    scale: float,
    setback_fraction: float,
    shortened_fraction: float,
) -> list[dict[str, Any]]:
    rows = []
    for index, env in enumerate(selected_e["selected_hinge_external_pin_envelopes"], start=1):
        axis = axes.get((env["tree_id"], env["hinge_id"]))
        if axis is None:
            axis_points = None
            active_points = None
            active_points_mm = None
            axis_points_mm = None
        else:
            axis_points = axis["axis_points"]
            start, end = axis_points
            delta = vec_sub(end, start)
            active_start = vec_add(start, vec_scale(delta, setback_fraction))
            active_end = vec_add(end, vec_scale(delta, -setback_fraction))
            active_points = [active_start, active_end]
            axis_points_mm = [to_mm(start, scale), to_mm(end, scale)]
            active_points_mm = [to_mm(active_start, scale), to_mm(active_end, scale)]
        axis_length_mm = float(env["axis_length_mm"])
        endpoint_setback_mm = round(axis_length_mm * setback_fraction, 9)
        rows.append({
            "index": index,
            "tree_id": env["tree_id"],
            "hinge_id": env["hinge_id"],
            "piece_pair": env["piece_pair"],
            "axis_labels": env["axis_labels"],
            "axis_support": env["axis_support"],
            "source_axis_placeholder_found": axis is not None,
            "source_axis_placeholder_only": bool(axis.get("axis_placeholder_only", False)) if axis else None,
            "axis_points_model": axis_points,
            "axis_points_mm": axis_points_mm,
            "endpoint_setback_fraction": setback_fraction,
            "endpoint_setback_mm": endpoint_setback_mm,
            "shortened_length_fraction": shortened_fraction,
            "active_axis_points_model": active_points,
            "active_axis_points_mm": active_points_mm,
            "axis_length_model_units": env["axis_length_model_units"],
            "axis_length_mm": axis_length_mm,
            "active_axis_length_mm": round(axis_length_mm * shortened_fraction, 9),
            "pin_radius_mm": env["pin_radius_mm"],
            "pin_diameter_mm": round(float(env["pin_radius_mm"]) * 2.0, 9),
            "boss_width_mm": env["boss_width_mm"],
            "clearance_mm": env["clearance_mm"],
            "radial_envelope_mm": env["radial_envelope_mm"],
            "diameter_to_axis_length_ratio": env["diameter_to_axis_length_ratio"],
            "required_cad_features": [
                "pin cylinder on active axis",
                "external boss or knuckle envelope on incident pieces",
                "real retention/assembly access geometry",
                "piece-specific relief from boolean work order",
            ],
            "geometry_status": "hardware_spec_only_no_cad_solid_no_retention_design",
        })
    return rows


def build_doc(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    params = payload["selected_candidate"]["parameters"]
    relief_rows = []
    for row in payload["relief_boolean_work_order"]:
        relief_rows.append([
            row["operation_id"],
            "-".join(row["piece_pair"]),
            row["route"],
            row["applied_clearance_mm"],
            row["clearance_margin_mm"],
            row["geometry_status"],
        ])
    hardware_rows = []
    for row in payload["hardware_work_order"]:
        hardware_rows.append([
            row["tree_id"],
            row["hinge_id"],
            "-".join(row["piece_pair"]),
            row["axis_length_mm"],
            row["endpoint_setback_mm"],
            row["active_axis_length_mm"],
            row["pin_diameter_mm"],
            row["geometry_status"],
        ])
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    blocker_rows = [[item] for item in payload["boolean_and_prototype_blockers"]]
    return f"""# S4 RW7 selected-candidate CAD boolean / hardware prep

Status: {payload['status']}.

RW7 is a candidate-only preparation gate for `{summary['selected_candidate_id']}`.  It turns the RW6 route into concrete work records for CAD boolean reliefs and real hinge hardware, but it does not execute CAD booleans or claim printability.

## Selected candidate

| field | value |
| --- | --- |
| candidate | `{summary['selected_candidate_id']}` |
| scale | {params['scale_mm_per_model_unit']} mm/model-unit |
| clearance | {params['clearance_mm']} mm |
| pin radius | {params['pin_radius_mm']} mm |
| boss width | {params['boss_width_mm']} mm |
| minimum passing setback | {payload['selected_candidate']['minimum_passing_setback_fraction']} |
| shortened axis fraction | {payload['selected_candidate']['shortened_length_fraction']} |

## Outputs

| artifact | path |
| --- | --- |
| RW7 JSON report | `{rel(JSON_PATH)}` |
| candidate-only work order | `{rel(WORK_ORDER_PATH)}` |
| diagnostic OBJ proxy | `{rel(PROXY_OBJ_PATH)}` |

The OBJ is diagnostic only: it contains the RW2 body solids plus the six relief boxes that must become real boolean subtractions.

## Relief boolean work order

{table(['operation', 'piece pair', 'route', 'clearance mm', 'margin mm', 'status'], relief_rows)}

Planned boolean subtractions: {summary['planned_boolean_subtraction_count']} ({summary['relief_operation_count']} relief boxes, paired-piece review policy).  None were executed in RW7.

## Hardware work order

{table(['tree', 'hinge', 'piece pair', 'axis mm', 'setback mm', 'active mm', 'pin dia mm', 'status'], hardware_rows)}

Every hardware row is still a spec, not a CAD solid.  Pin cylinders, boss/knuckle features, retention, insertion access, material behavior, friction, and wear remain open.

## project-local boolean capability

| field | value |
| --- | --- |
| project-local boolean wrapper present | {payload['papp_boolean_capability']['papp_boolean_wrapper_present']} |
| trimesh available | {payload['papp_boolean_capability']['trimesh_available']} |
| robust backend available | {payload['papp_boolean_capability']['robust_boolean_backend_available']} |
| available robust backend modules | {payload['papp_boolean_capability']['robust_boolean_backend_modules_available']} |
| RW7 execution policy | {payload['papp_boolean_capability']['rw7_boolean_execution_policy']} |

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Blockers still open

{table(['blocker'], blocker_rows)}

## Nonclaims

RW7 does not claim CAD boolean validity, direct printability, STL/3MF readiness, G-code readiness, fabrication readiness, physical hingeability, or prototype validation.

## Next task

RW7b should execute the candidate-only boolean/rebuild step with a real robust CAD/mesh backend, repair winding/manifold issues, and produce an exportable candidate mesh.  Only after that should RW8 run STL/3MF export and slicer/layer preview.
"""


def main() -> None:
    rw2 = load_json(RW2_PATH)
    rw4e = load_json(RW4E_PAYLOAD_PATH)
    rw4h = load_json(RW4H_PATH)
    rw5 = load_json(RW5_PATH)
    rw6 = load_json(RW6_PATH)

    selected_id = get_candidate_id(rw6, rw5)
    selected_e = candidate_by_id(rw4e["candidates"], selected_id)
    selected_h = candidate_by_id(rw4h["candidate_results"], selected_id)
    scale = float(selected_e["parameters"]["scale_mm_per_model_unit"])
    piece_paths = piece_obj_map(rw2)
    axes = hinge_axis_index(rw2)

    relief_work_order = build_relief_work_order(selected_h, selected_e, piece_paths, scale)
    hardware_work_order = build_hardware_work_order(
        selected_e,
        axes,
        scale,
        float(selected_h["minimum_passing_setback_fraction"]),
        float(selected_h["shortened_length_fraction"]),
    )

    write_candidate_proxy_obj(rw2["exports"]["combined_obj"], selected_h["relief_proxy_records"])

    planned_boolean_subtractions = sum(len(row["target_piece_operations"]) for row in relief_work_order)
    hardware_axis_points_found = all(row["source_axis_placeholder_found"] for row in hardware_work_order)
    all_relief_positive = all(row["positive_proxy_volume"] for row in relief_work_order)
    all_relief_mapped = all(
        all(target["source_piece_obj"] for target in row["target_piece_operations"])
        for row in relief_work_order
    )
    min_margin_mm = min(row["clearance_margin_mm"] for row in relief_work_order)
    min_active_axis_mm = min(row["active_axis_length_mm"] for row in hardware_work_order)

    payload: dict[str, Any] = {
        "report_id": "S4-RW7-SELECTED-CANDIDATE-CAD-BOOLEAN-HARDWARE-PREP-2026-06-22",
        "date": DATE,
        "case_id": CASE_ID,
        "status": "rw7_selected_candidate_work_order_created_boolean_execution_blocked",
        "precondition": {
            "rw6_report": rel(RW6_PATH),
            "rw5_report": rel(RW5_PATH),
            "selected_candidate_from_rw6": selected_id,
        },
        "selected_candidate": {
            "candidate_id": selected_id,
            "status_rw4e": selected_e["status"],
            "status_rw4h": selected_h["status"],
            "parameters": selected_e["parameters"],
            "minimum_passing_setback_fraction": selected_h["minimum_passing_setback_fraction"],
            "shortened_length_fraction": selected_h["shortened_length_fraction"],
            "clearance_replay": selected_e["clearance_replay"],
            "hardware_envelope_summary": selected_e["hardware_envelope_summary"],
        },
        "summary": {
            "selected_candidate_id": selected_id,
            "candidate_only_scope": True,
            "relief_operation_count": len(relief_work_order),
            "planned_boolean_subtraction_count": planned_boolean_subtractions,
            "hardware_axis_count": len(hardware_work_order),
            "all_hardware_axes_mapped_to_rw2_placeholders": hardware_axis_points_found,
            "all_relief_boxes_positive_volume": all_relief_positive,
            "all_relief_operations_mapped_to_piece_objs": all_relief_mapped,
            "minimum_relief_clearance_margin_mm": min_margin_mm,
            "minimum_active_axis_length_mm": min_active_axis_mm,
            "diagnostic_proxy_obj_written": PROXY_OBJ_PATH.exists(),
            "cad_boolean_operations_executed": False,
            "cad_boolean_validity": False,
            "stl_3mf_export_ready": False,
            "slicer_gcode_ready": False,
            "physical_prototype_validated": False,
            "rw7b_boolean_execution_unblocked": True,
        },
        "relief_boolean_work_order": relief_work_order,
        "hardware_work_order": hardware_work_order,
        "papp_boolean_capability": papp_boolean_capability(),
        "artifacts": {
            "json_report": rel(JSON_PATH),
            "candidate_work_order_json": rel(WORK_ORDER_PATH),
            "diagnostic_proxy_obj": rel(PROXY_OBJ_PATH),
            "source_combined_body_obj": rw2["exports"]["combined_obj"],
        },
        "allowed_claims": ALLOWED_CLAIMS,
        "blocked_claims": BLOCKED_CLAIMS,
        "boolean_and_prototype_blockers": BOOLEAN_BLOCKERS,
        "acceptance": {
            "rw6_report_present": RW6_PATH.exists(),
            "selected_candidate_matches_rw6": selected_id == rw6["recommended_frontier_candidate"]["candidate_id"],
            "candidate_only_scope": True,
            "rw4e_candidate_record_found": selected_e["candidate_id"] == selected_id,
            "rw4h_candidate_record_found": selected_h["candidate_id"] == selected_id,
            "relief_work_order_count_is_6": len(relief_work_order) == 6,
            "planned_boolean_subtraction_count_is_12": planned_boolean_subtractions == 12,
            "hardware_axis_count_is_6": len(hardware_work_order) == 6,
            "all_hardware_axes_have_rw2_axis_points": hardware_axis_points_found,
            "all_relief_boxes_positive_volume": all_relief_positive,
            "all_relief_operations_mapped_to_piece_objs": all_relief_mapped,
            "candidate_only_proxy_obj_written": PROXY_OBJ_PATH.exists(),
            "cad_boolean_operations_executed": False,
            "cad_boolean_validity_claim_blocked": True,
            "direct_fabrication_claim_blocked": True,
            "rw7b_boolean_execution_unblocked": True,
        },
        "next_task": "RW7b execute candidate-only CAD boolean/rebuild with robust backend, then mesh repair and export gate before slicer/prototype work.",
    }

    write_json(JSON_PATH, payload)
    write_json(WORK_ORDER_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "selected_candidate_id": selected_id,
        "relief_operation_count": len(relief_work_order),
        "planned_boolean_subtraction_count": planned_boolean_subtractions,
        "hardware_axis_count": len(hardware_work_order),
        "diagnostic_proxy_obj": rel(PROXY_OBJ_PATH),
        "cad_boolean_operations_executed": False,
        "rw7b_boolean_execution_unblocked": True,
    }, indent=2))


if __name__ == "__main__":
    main()
