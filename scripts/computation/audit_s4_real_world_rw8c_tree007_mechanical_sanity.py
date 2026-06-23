#!/usr/bin/env python
"""RW8c mechanical/visual sanity audit for the TREE_007 hardware export.

RW8 proves that the TREE_007 component exports are clean mesh artifacts.  This
script answers a different question: whether the current exported object is a
credible final physical prototype candidate.

The answer is intentionally stricter than RW8.  A design can be watertight,
exportable, and still be rejected as a final object because its hinge clearances,
knuckle widths, pin retention, or viewer/fabrication presentation are not good
enough.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-23"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW7_PATH = RESULT_ROOT / "rw7_selected_candidate_cad_boolean_hardware_prep.json"
RW7D_PATH = RESULT_ROOT / "rw7d_hinge_connectivity_repair_report.json"
RW8_PATH = RESULT_ROOT / "rw8_export_slicer_preflight_report.json"
TREE_AUDIT_PATH = RESULT_ROOT / "tree007_export_audit" / "tree007_export_integrity_audit.json"
JSON_PATH = RESULT_ROOT / "rw8c_tree007_mechanical_sanity_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW8C_TREE007_MECHANICAL_SANITY.md"

REPORT_ID = "S4-RW8C-TREE007-MECHANICAL-SANITY-2026-06-23"


THRESHOLDS = {
    "radial_clearance_mm": {
        "target_min": 0.20,
        "target_max": 0.40,
        "critical_max": 0.45,
        "rationale": "FDM-friendly removable pin fit; larger clearance becomes visibly sloppy.",
    },
    "boss_axial_width_mm": {
        "target_min": 2.40,
        "critical_min": 2.00,
        "rationale": "Knuckle sleeve should have enough axial bearing area and printable strength.",
    },
    "boss_wall_thickness_mm": {
        "target_min": 1.50,
        "critical_min": 1.20,
        "rationale": "Around the pin hole, 1.2 mm is roughly a minimum wall, not a robust final value.",
    },
    "web_penetration_mm": {
        "target_min": 1.80,
        "critical_min": 1.20,
        "rationale": "Connector web must key into the body strongly enough for handling.",
    },
    "web_tube_overlap_mm": {
        "target_min": 0.05,
        "critical_min": 0.01,
        "rationale": "Tiny overlap may pass boolean connectivity but is visually and mechanically fragile.",
    },
    "active_axis_length_mm": {
        "target_min": 18.00,
        "critical_min": 15.00,
        "rationale": "There must be enough useful hinge length after endpoint setbacks.",
    },
}


BLOCKED_CLAIMS = [
    "final physical prototype readiness",
    "physical hingeability",
    "pin retention correctness",
    "print orientation/support correctness",
    "G-code readiness",
    "measured static coupon validation",
    "measured moving prototype validation",
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


def variant(report: dict[str, Any], tree_id: str) -> dict[str, Any]:
    for item in report.get("variant_results", []):
        if item.get("tree_id") == tree_id:
            return item
    raise KeyError(tree_id)


def tree_rows(rw7: dict[str, Any], tree_id: str) -> list[dict[str, Any]]:
    return [row for row in rw7.get("hardware_work_order", []) if row.get("tree_id") == tree_id]


def eval_min(value: float, target_min: float, critical_min: float) -> tuple[str, str]:
    if value < critical_min:
        return "FAIL", f"{value:.3f} < critical minimum {critical_min:.3f}"
    if value < target_min:
        return "WARN", f"{value:.3f} below target {target_min:.3f}"
    return "PASS", f"{value:.3f} >= target {target_min:.3f}"


def eval_max(value: float, target_max: float, critical_max: float) -> tuple[str, str]:
    if value > critical_max:
        return "FAIL", f"{value:.3f} > critical maximum {critical_max:.3f}"
    if value > target_max:
        return "WARN", f"{value:.3f} above target {target_max:.3f}"
    return "PASS", f"{value:.3f} <= target {target_max:.3f}"


def main() -> None:
    rw7 = load_json(RW7_PATH)
    rw7d = load_json(RW7D_PATH)
    rw8 = load_json(RW8_PATH)
    tree_audit = load_json(TREE_AUDIT_PATH)

    tree_id = "TREE_007"
    rows = tree_rows(rw7, tree_id)
    if len(rows) != 3:
        raise SystemExit(f"expected three TREE_007 hinge rows, found {len(rows)}")
    variant(rw7d, tree_id)  # explicit precondition check
    params = dict(rw7d.get("design_parameter_summary", {}))
    selected_params = rw7.get("selected_candidate", {}).get("parameters", {})

    pin_radius_mm = float(params["pin_radius_mm"])
    pin_diameter_mm = 2.0 * pin_radius_mm
    clearance_mm = float(params["nominal_radial_pin_clearance_mm"])
    hole_inner_radius_mm = float(params["pin_hole_inner_radius_mm"])
    outer_radius_mm = float(params["outer_boss_radius_mm"])
    boss_wall_thickness_mm = outer_radius_mm - hole_inner_radius_mm
    boss_width_mm = float(selected_params.get("boss_width_mm", rows[0].get("boss_width_mm")))
    web_penetration_mm = float(params["web_penetration_mm"])
    web_tube_overlap_mm = float(params["web_tube_overlap_mm"])
    axis_offset_mm = float(params["axis_offset_mm"])
    active_axis_lengths = [float(row["active_axis_length_mm"]) for row in rows]
    min_axis_length_mm = min(active_axis_lengths)
    endpoint_setback_mm = min(float(row["endpoint_setback_mm"]) for row in rows)
    pin_retention_design_present = all("no_retention" not in str(row.get("geometry_status", "")) for row in rows)

    component_mesh_pass = bool(rw8.get("summary", {}).get("all_component_exports_pass"))
    component_export_count = int(rw8.get("summary", {}).get("component_export_count", 0))
    assembly_preview_role = tree_audit.get("assembly_preview_audit", {}).get("fabrication_role")
    assembly_preview_fabrication_file = bool(assembly_preview_role != "assembly_preview_not_fabrication_file")
    assembly_preview_watertight = bool(tree_audit.get("assembly_preview_audit", {}).get("stl_metrics", {}).get("cleaned", {}).get("watertight"))
    assembly_preview_components = int(tree_audit.get("assembly_preview_audit", {}).get("stl_metrics", {}).get("cleaned", {}).get("connected_components", -1))

    checks: list[dict[str, Any]] = []

    def add_check(name: str, value: Any, status: str, detail: str, recommendation: str, critical: bool = False) -> None:
        checks.append({
            "name": name,
            "value": value,
            "status": status,
            "detail": detail,
            "recommendation": recommendation,
            "critical": bool(critical),
        })

    status, detail = eval_max(clearance_mm, THRESHOLDS["radial_clearance_mm"]["target_max"], THRESHOLDS["radial_clearance_mm"]["critical_max"])
    add_check(
        "nominal radial pin clearance",
        clearance_mm,
        status,
        detail,
        "Reduce radial clearance to roughly 0.25-0.35 mm for the next printable-hinge variant.",
        critical=True,
    )

    status, detail = eval_min(boss_width_mm, THRESHOLDS["boss_axial_width_mm"]["target_min"], THRESHOLDS["boss_axial_width_mm"]["critical_min"])
    add_check(
        "boss/knuckle axial width",
        boss_width_mm,
        status,
        detail,
        "Increase knuckle width to at least 2.4 mm; 3.0 mm is the robust follow-up target.",
        critical=True,
    )

    status, detail = eval_min(boss_wall_thickness_mm, THRESHOLDS["boss_wall_thickness_mm"]["target_min"], THRESHOLDS["boss_wall_thickness_mm"]["critical_min"])
    add_check(
        "boss wall thickness around pin hole",
        boss_wall_thickness_mm,
        status,
        detail,
        "Use a larger outer boss radius after tightening clearance, targeting >= 1.5 mm wall.",
        critical=status == "FAIL",
    )

    status, detail = eval_min(web_penetration_mm, THRESHOLDS["web_penetration_mm"]["target_min"], THRESHOLDS["web_penetration_mm"]["critical_min"])
    add_check(
        "connector web body penetration",
        web_penetration_mm,
        status,
        detail,
        "Raise web penetration toward 1.8-2.0 mm and re-run piece connectivity/overlap checks.",
        critical=status == "FAIL",
    )

    status, detail = eval_min(web_tube_overlap_mm, THRESHOLDS["web_tube_overlap_mm"]["target_min"], THRESHOLDS["web_tube_overlap_mm"]["critical_min"])
    add_check(
        "connector web overlap into tube",
        web_tube_overlap_mm,
        status,
        detail,
        "Use a real union overlap, around 0.05-0.10 mm, while preserving pin clearance.",
        critical=status == "FAIL",
    )

    status, detail = eval_min(min_axis_length_mm, THRESHOLDS["active_axis_length_mm"]["target_min"], THRESHOLDS["active_axis_length_mm"]["critical_min"])
    add_check(
        "minimum active hinge axis length",
        min_axis_length_mm,
        status,
        detail,
        "Keep endpoint setbacks but verify wider knuckles still fit on the active axis.",
        critical=status == "FAIL",
    )

    add_check(
        "component export mesh integrity",
        {"component_export_count": component_export_count, "all_component_exports_pass": component_mesh_pass},
        "PASS" if component_mesh_pass and component_export_count == 7 else "FAIL",
        "RW8 component files are the trustworthy fabrication candidates; the mesh issue is not the blocker." if component_mesh_pass else "Component export integrity failed.",
        "Keep separate component exports as the source of truth; do not judge by the diagnostic assembly preview alone.",
        critical=not component_mesh_pass,
    )

    add_check(
        "assembly preview suitability",
        {"fabrication_file": assembly_preview_fabrication_file, "watertight": assembly_preview_watertight, "clean_connected_components": assembly_preview_components},
        "FAIL" if not assembly_preview_fabrication_file else "WARN",
        "The combined assembly preview is diagnostic only and is not watertight; viewers may display it misleadingly.",
        "Use grouped inspection OBJ plus separate component STL/3MF exports; create a final viewer bundle after redesign.",
        critical=True,
    )

    add_check(
        "pin retention design",
        pin_retention_design_present,
        "PASS" if pin_retention_design_present else "FAIL",
        "The hardware work order explicitly remains no-retention/spec-only for the pins." if not pin_retention_design_present else "Retention geometry present.",
        "Add an explicit retaining feature: end collars, press caps, clip groove, or documented off-the-shelf fastener stack.",
        critical=True,
    )

    critical_fails = [check for check in checks if check["critical"] and check["status"] == "FAIL"]
    warnings = [check for check in checks if check["status"] == "WARN"]
    mesh_clean_but_not_final = bool(component_mesh_pass and critical_fails)

    proposed_rw7e_compact = {
        "pin_radius_mm": 1.25,
        "pin_diameter_mm": 2.50,
        "nominal_radial_pin_clearance_mm": 0.30,
        "pin_hole_inner_radius_mm": 1.55,
        "outer_boss_radius_mm": 3.40,
        "boss_wall_thickness_mm": 1.85,
        "boss_width_mm": 2.40,
        "web_penetration_mm": 1.80,
        "web_tube_overlap_mm": 0.08,
        "expected_axis_offset_mm": 3.80,
        "note": "Compact refinement: similar external envelope, much tighter fit and wider knuckles.",
    }
    proposed_rw7e_robust = {
        "pin_radius_mm": 1.50,
        "pin_diameter_mm": 3.00,
        "nominal_radial_pin_clearance_mm": 0.35,
        "pin_hole_inner_radius_mm": 1.85,
        "outer_boss_radius_mm": 4.00,
        "boss_wall_thickness_mm": 2.15,
        "boss_width_mm": 3.00,
        "web_penetration_mm": 2.20,
        "web_tube_overlap_mm": 0.10,
        "expected_axis_offset_mm": 4.35,
        "note": "Robust fallback if compact hinge still looks weak or prints poorly.",
    }

    payload = {
        "report_id": REPORT_ID,
        "date": DATE,
        "case_id": CASE_ID,
        "tree_id": tree_id,
        "status": "rw8c_tree007_current_design_rejected_for_final_prototype_refinement_required" if critical_fails else "rw8c_tree007_current_design_mechanical_sanity_pass",
        "decision": {
            "component_mesh_integrity_passes": component_mesh_pass,
            "final_prototype_ready": not bool(critical_fails),
            "mesh_clean_but_not_final": mesh_clean_but_not_final,
            "critical_fail_count": len(critical_fails),
            "warning_count": len(warnings),
        },
        "current_design_metrics_mm": {
            "pin_radius_mm": pin_radius_mm,
            "pin_diameter_mm": pin_diameter_mm,
            "pin_hole_inner_radius_mm": hole_inner_radius_mm,
            "nominal_radial_pin_clearance_mm": clearance_mm,
            "outer_boss_radius_mm": outer_radius_mm,
            "boss_wall_thickness_mm": boss_wall_thickness_mm,
            "boss_width_mm": boss_width_mm,
            "web_penetration_mm": web_penetration_mm,
            "web_tube_overlap_mm": web_tube_overlap_mm,
            "axis_offset_mm": axis_offset_mm,
            "minimum_active_axis_length_mm": min_axis_length_mm,
            "endpoint_setback_mm": endpoint_setback_mm,
        },
        "checks": checks,
        "thresholds": THRESHOLDS,
        "proposed_next_variants": {
            "rw7e_compact_refinement_first": proposed_rw7e_compact,
            "rw7e_robust_fallback": proposed_rw7e_robust,
        },
        "preconditions": {
            "rw7_selected_candidate": rel(RW7_PATH),
            "rw7d_connectivity_repair_report": rel(RW7D_PATH),
            "rw8_export_slicer_preflight_report": rel(RW8_PATH),
            "tree007_export_integrity_audit": rel(TREE_AUDIT_PATH),
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "next_task": "RW7e should generate a TREE_007 mechanical refinement with tighter clearance, wider knuckles, stronger web overlap, and explicit pin-retention placeholders before RW9 coupon work.",
    }

    write_json(JSON_PATH, payload)

    check_rows = [
        [check["name"], check["status"], check["value"], check["detail"], check["recommendation"]]
        for check in checks
    ]
    metric_rows = [[key, f"{value:.3f}" if isinstance(value, float) else value] for key, value in payload["current_design_metrics_mm"].items()]
    proposal_rows = [[key, value] for key, value in proposed_rw7e_compact.items()]

    doc = f"""# S4 RW8c TREE_007 mechanical sanity audit

Status: `{payload['status']}`.

RW8 proved that the separate TREE_007 component exports are clean mesh artifacts.
RW8c applies a stricter question: is the current object good enough to be the
final physical prototype candidate?  The answer is no.  The current TREE_007 is
complete enough to inspect, but it is not good enough to send forward as the
best final object.

## Decision

| field | value |
| --- | --- |
| component mesh integrity passes | {payload['decision']['component_mesh_integrity_passes']} |
| final prototype ready | {payload['decision']['final_prototype_ready']} |
| mesh clean but not final | {payload['decision']['mesh_clean_but_not_final']} |
| critical fails | {payload['decision']['critical_fail_count']} |
| warnings | {payload['decision']['warning_count']} |

## Current metrics

{table(['metric', 'value mm'], metric_rows)}

## Gate checks

{table(['check', 'status', 'value', 'detail', 'recommendation'], check_rows)}

## Interpretation

The screenshots are consistent with the current CAD baseline: four printed body
pieces, three external hinge axes, removable pin cylinders, and boss/knuckle
rings.  The object is not missing a whole hidden component, but the hinge design
is visibly and mechanically provisional.

The concrete blockers are:

- radial pin clearance is `0.8 mm`, far too loose for a serious small hinge;
- boss/knuckle width is `1.2 mm`, too thin for a robust bearing sleeve;
- there is no explicit pin retention design;
- the combined assembly preview is diagnostic and non-watertight, so viewers
  can make the object look broken or incomplete;
- several dimensions are minimum/marginal values rather than final design
  values.

## Proposed next variant: RW7e compact refinement

{table(['parameter', 'value'], proposal_rows)}

RW7e should keep the TREE_007 kinematic layout but regenerate the hinge hardware
with the compact refinement first.  If that still looks weak or fails mesh and
clearance checks, the robust fallback should be tried before any physical coupon
or prototype work.

## Nonclaims

RW8c does not claim final physical prototype readiness, physical hingeability,
pin retention correctness, print orientation/support correctness, G-code
readiness, measured static coupon validation, or measured moving prototype
validation.

## Artifacts

| artifact | path |
| --- | --- |
| RW8c JSON report | `{rel(JSON_PATH)}` |
"""
    write_text(DOC_PATH, doc)

    print(f"status: {payload['status']}")
    print(f"critical fails: {len(critical_fails)}")
    for check in critical_fails:
        print(f"  FAIL {check['name']}: {check['detail']}")
    print(f"warnings: {len(warnings)}")
    print(f"json: {JSON_PATH}")
    print(f"doc: {DOC_PATH}")


if __name__ == "__main__":
    main()
