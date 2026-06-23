#!/usr/bin/env python
"""RW10 digital final prototype package for external fabrication review.

RW10 is rescoped away from a measured moving prototype because no local printer
or physical measurement loop is available.  It packages the corrected,
body-preserving TREE_007 fabrication components, hashes them, separates
fabrication files from inspection-only files, and records the exact claim
boundary.

No physical hingeability, printer-specific print readiness, or measured coupon
validation is claimed by this script.
"""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-23"
CASE_ID = "historical_s4_median_planes"
REPORT_ID = "S4-RW10-DIGITAL-FINAL-PROTOTYPE-PACKAGE-2026-06-23"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW7F_REPORT = RESULT_ROOT / "rw7f_body_preserving_rebuild_report.json"
RW8G_REPORT = RESULT_ROOT / "rw8g_export_body_preserving_tree007_report.json"
RW8H_REPORT = RESULT_ROOT / "rw8h_body_preserving_tree007_export_audit" / "body_preserving_tree007_export_integrity_audit.json"
RW9E_REPORT = RESULT_ROOT / "rw9e_printer_profile_gate" / "rw9e_printer_profile_gate_report.json"
OUT_DIR = RESULT_ROOT / "rw10_digital_final_prototype_package"
FAB_DIR = OUT_DIR / "fabrication_files"
INSPECTION_DIR = OUT_DIR / "inspection_only"
JSON_PATH = OUT_DIR / "rw10_digital_final_prototype_package_report.json"
MANIFEST_PATH = OUT_DIR / "rw10_digital_final_prototype_manifest.json"
REQUEST_PATH = OUT_DIR / "RW10_EXTERNAL_FABRICATION_REQUEST.md"
DOC_PATH = ROOT / "docs" / "S4_RW10_DIGITAL_FINAL_PROTOTYPE_PACKAGE.md"

FABRICABLE_KINDS = {"printed_pieces", "removable_pin_references"}
PRIMARY_PRINT_COMPONENTS = {"primary_print_component"}
PIN_REFERENCE_ROLE = "optional_printed_pin_or_metal_pin_reference"

BLOCKED_CLAIMS = [
    "local physical prototype exists",
    "measured coupon validation",
    "printer-specific G-code approved",
    "moving hingeability measured",
    "physical hingeability theorem",
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


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def copy_artifact(source_rel: str, target_dir: Path) -> dict[str, Any]:
    source = ROOT / source_rel
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return {
        "source": rel(source),
        "target": rel(target),
        "bytes": target.stat().st_size,
        "sha256": sha256(target),
    }


def component_records(rw8g: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    variants = rw8g.get("variant_results", [])
    if len(variants) != 1:
        raise ValueError(f"expected exactly one RW8g variant, found {len(variants)}")
    variant = variants[0]
    fabricable = []
    inspection = []
    for record in variant.get("component_exports", []):
        if record.get("component_kind") in FABRICABLE_KINDS and record.get("passes_export_preflight"):
            fabricable.append(record)
    for record in variant.get("assembly_preview_exports", []):
        inspection.append(record)
    return fabricable, inspection


def package_fabricable_components(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packaged = []
    for record in records:
        role = record.get("fabrication_role", "unknown")
        kind = record.get("component_kind", "unknown")
        subdir = FAB_DIR / kind / record["component_id"]
        artifacts = {}
        for ext_key in ("stl", "threemf"):
            src = record.get("artifacts", {}).get(ext_key)
            if src:
                artifacts[ext_key] = copy_artifact(src, subdir)
        packaged.append({
            "component_id": record["component_id"],
            "component_kind": kind,
            "fabrication_role": role,
            "passes_export_preflight": bool(record.get("passes_export_preflight")),
            "printability_gate_passed": bool(record.get("printability_gate", {}).get("passed")),
            "layer_preview_passed": bool(record.get("layer_preview", {}).get("passes_non_empty_preview")),
            "artifact_copies": artifacts,
            "source_mesh_metrics_model": record.get("source_mesh_metrics_model", {}),
        })
    return packaged


def package_inspection_files(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    packaged = []
    for record in records:
        subdir = INSPECTION_DIR / record["component_id"]
        artifacts = {}
        for ext_key in ("stl", "threemf"):
            src = record.get("artifacts", {}).get(ext_key)
            if src:
                artifacts[ext_key] = copy_artifact(src, subdir)
        packaged.append({
            "component_id": record["component_id"],
            "component_kind": record.get("component_kind"),
            "fabrication_role": record.get("fabrication_role"),
            "passes_export_preflight": bool(record.get("passes_export_preflight")),
            "why_inspection_only": "assembly preview is not a fabrication file and may fail manifold/winding checks",
            "artifact_copies": artifacts,
        })
    return packaged


def bom_guidance(rw7f: dict[str, Any], packaged_components: list[dict[str, Any]]) -> dict[str, Any]:
    params = rw7f.get("design_parameter_summary", {})
    printed = [c for c in packaged_components if c["fabrication_role"] in PRIMARY_PRINT_COMPONENTS]
    pins = [c for c in packaged_components if c["fabrication_role"] == PIN_REFERENCE_ROLE]
    pin_diameter = 2.0 * float(params.get("pin_radius_mm", 1.25))
    hole_diameter = 2.0 * float(params.get("pin_hole_inner_radius_mm", 1.55))
    return {
        "printed_body_components": [c["component_id"] for c in printed],
        "pin_reference_components": [c["component_id"] for c in pins],
        "preferred_physical_pin_strategy": "external metal/dowel pins should be considered before printed pins for a real prototype, because diameter tolerance and wear are more reliable than FDM printed rods",
        "nominal_pin_diameter_mm": pin_diameter,
        "nominal_hole_diameter_mm": hole_diameter,
        "nominal_diametral_clearance_mm": hole_diameter - pin_diameter,
        "nominal_radial_clearance_mm": float(params.get("nominal_radial_pin_clearance_mm", 0.3)),
        "pin_count_reference": len(pins),
        "physical_note": "pin length, retention, and final fit must be reviewed by the external fabricator; this package does not validate actual printed dimensions",
    }


def build_external_request(payload: dict[str, Any]) -> str:
    rows = []
    for c in payload["fabrication_components"]:
        stl = c["artifact_copies"].get("stl", {}).get("target", "")
        mf = c["artifact_copies"].get("threemf", {}).get("target", "")
        rows.append([c["component_id"], c["component_kind"], c["fabrication_role"], stl, mf])
    return f"""# RW10 external fabrication request

This package is a digital fabrication candidate for the S4 TREE_007 body-preserving prototype.  It is not a physically validated prototype.

## Fabrication files

{table(['component', 'kind', 'role', 'STL', '3MF'], rows)}

## Suggested fabrication interpretation

- Print the four `printed_pieces` components as the primary body+boss pieces.
- Treat the three `removable_pin_references` as geometry references for the hinge pins.
- Prefer commercial/metal pins near `{payload['bom_guidance']['nominal_pin_diameter_mm']}` mm if available and if the fabricator confirms fit strategy.
- Do not print the assembly preview as a fabrication part; it is inspection-only.

## Required post-fabrication checks

1. Measure actual hole diameters and pin diameters.
2. Verify hinge insertion and rotation manually.
3. Report any needed clearance change.
4. Do not claim physical hingeability until measured motion is documented.
"""


def build_doc(payload: dict[str, Any]) -> str:
    summary_rows = [[k, v] for k, v in payload["summary"].items()]
    acceptance_rows = [[k, v] for k, v in payload["acceptance"].items()]
    component_rows = []
    for c in payload["fabrication_components"]:
        component_rows.append([
            c["component_id"],
            c["component_kind"],
            c["fabrication_role"],
            c["printability_gate_passed"],
            c["layer_preview_passed"],
        ])
    blockers = [[b] for b in payload["open_blockers"]]
    return f"""# S4 RW10 digital final prototype package

Status: `{payload['status']}`.

RW10 is rescoped as a digital final prototype package for external fabrication review.  It packages the corrected TREE_007 body-preserving fabrication components and records the nonclaim boundary.

## Summary

{table(['field', 'value'], summary_rows)}

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Fabrication components

{table(['component', 'kind', 'role', 'print gate', 'layer preview'], component_rows)}

## BOM guidance

```json
{json.dumps(payload['bom_guidance'], indent=2, sort_keys=True)}
```

## Main artifacts

| artifact | path |
| --- | --- |
| manifest | `{payload['artifacts']['manifest_json']}` |
| report | `{payload['artifacts']['report_json']}` |
| external fabrication request | `{payload['artifacts']['external_fabrication_request_md']}` |
| fabrication files dir | `{payload['artifacts']['fabrication_files_dir']}` |
| inspection-only dir | `{payload['artifacts']['inspection_only_dir']}` |

## Claim boundary

This package is digitally checked and traceable.  It is not a physical validation.  It does not claim actual printed tolerances, successful assembly, or measured hinge motion.

## Open blockers

{table(['blocker'], blockers)}
"""


def main() -> None:
    rw7f = load_json(RW7F_REPORT)
    rw8g = load_json(RW8G_REPORT)
    rw8h = load_json(RW8H_REPORT)
    rw9e = load_json(RW9E_REPORT)
    fabricable, inspection = component_records(rw8g)
    packaged_components = package_fabricable_components(fabricable)
    packaged_inspection = package_inspection_files(inspection)
    all_fabricable_pass = bool(packaged_components) and all(c["passes_export_preflight"] and c["printability_gate_passed"] and c["layer_preview_passed"] for c in packaged_components)
    has_four_bodies = sum(1 for c in packaged_components if c["component_kind"] == "printed_pieces") == 4
    has_pin_refs = sum(1 for c in packaged_components if c["component_kind"] == "removable_pin_references") == 3
    status = "rw10_digital_final_prototype_package_ready_external_fabrication_review_no_physical_claim" if all_fabricable_pass and has_four_bodies and has_pin_refs else "rw10_digital_final_prototype_package_failed_digital_gate"
    payload: dict[str, Any] = {
        "report_id": REPORT_ID,
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "precondition": {
            "rw7f_report": rel(RW7F_REPORT),
            "rw7f_status": rw7f["status"],
            "rw8g_report": rel(RW8G_REPORT),
            "rw8g_status": rw8g["status"],
            "rw8h_report": rel(RW8H_REPORT),
            "rw8h_status": rw8h["status"],
            "rw9e_report": rel(RW9E_REPORT),
            "rw9e_status": rw9e["status"],
        },
        "scope": {
            "target": "digital final prototype package for external fabrication review",
            "local_physical_validation_available": False,
            "printer_specific_profile_available": False,
            "physical_claim_promoted": False,
        },
        "summary": {
            "fabrication_component_count": len(packaged_components),
            "printed_body_component_count": sum(1 for c in packaged_components if c["component_kind"] == "printed_pieces"),
            "pin_reference_component_count": sum(1 for c in packaged_components if c["component_kind"] == "removable_pin_references"),
            "inspection_only_component_count": len(packaged_inspection),
            "all_fabrication_components_pass_export_preflight": all_fabricable_pass,
            "body_preservation_passed_rw7f": bool(rw7f["summary"].get("body_preservation_passes")),
            "rw8g_all_component_exports_pass": bool(rw8g["summary"].get("all_component_exports_pass")),
            "rw9e_printer_profile_gate_currently_blocked": rw9e["status"].startswith("rw9e_printer_profile_gate_blocked"),
            "external_fabrication_review_ready": status.startswith("rw10_digital_final"),
            "physical_hingeability_claim_ready": False,
        },
        "acceptance": {
            "rw7f_body_preservation_passed": bool(rw7f["summary"].get("body_preservation_passes")),
            "rw8g_component_exports_passed": bool(rw8g["summary"].get("all_component_exports_pass")),
            "four_primary_printed_body_components_present": has_four_bodies,
            "three_pin_reference_components_present": has_pin_refs,
            "all_packaged_fabrication_components_have_hashes": all(bool(c["artifact_copies"].get("stl", {}).get("sha256")) for c in packaged_components),
            "assembly_preview_separated_as_inspection_only": bool(packaged_inspection),
            "claim_boundary_preserved": True,
            "physical_claim_promoted": False,
        },
        "bom_guidance": bom_guidance(rw7f, packaged_components),
        "fabrication_components": packaged_components,
        "inspection_only_components": packaged_inspection,
        "artifacts": {
            "manifest_json": rel(MANIFEST_PATH),
            "report_json": rel(JSON_PATH),
            "external_fabrication_request_md": rel(REQUEST_PATH),
            "doc": rel(DOC_PATH),
            "fabrication_files_dir": rel(FAB_DIR),
            "inspection_only_dir": rel(INSPECTION_DIR),
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": [
            "External fabricator/printer profile not selected.",
            "No local physical coupon or prototype measurement exists.",
            "Pin material, exact retained length, and assembly workflow require external review.",
            "Measured hinge insertion/rotation remains unvalidated.",
        ],
        "next_task": "Send RW10 package to external fabrication review or create tolerance-variant digital packages before external fabrication.",
    }
    write_json(MANIFEST_PATH, {
        "report_id": REPORT_ID,
        "status": payload["status"],
        "fabrication_components": packaged_components,
        "inspection_only_components": packaged_inspection,
        "bom_guidance": payload["bom_guidance"],
        "claim_boundary": "digital fabrication package only; no physical validation claim",
    })
    write_json(JSON_PATH, payload)
    write_text(REQUEST_PATH, build_external_request(payload))
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "fabrication_component_count": len(packaged_components),
        "fabrication_files_dir": rel(FAB_DIR),
        "physical_claim_promoted": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
