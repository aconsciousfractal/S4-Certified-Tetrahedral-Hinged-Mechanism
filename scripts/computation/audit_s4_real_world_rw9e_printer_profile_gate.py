#!/usr/bin/env python
"""RW9e printer-specific profile gate for RW9c/RW9d coupon printing.

RW9d proved that PrusaSlicer CLI can emit diagnostic generic G-code for the
RW9c coupon.  RW9e prevents that generic G-code from being mistaken for a
printer-specific print release.  It creates/validates an operator profile
intake JSON and only generates a printer-specific G-code when real printer,
nozzle, material, slicer profile/config, and operator approval are supplied.

With the default empty template, the correct result is blocked.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAPP_ROOT = ROOT.parents[3] / "PAPP"
if str(PAPP_ROOT) not in sys.path:
    sys.path.insert(0, str(PAPP_ROOT))

from core.slicer.slicer_cli import _parse_gcode_metadata

DATE = "2026-06-23"
CASE_ID = "historical_s4_median_planes"
REPORT_ID = "S4-RW9E-PRINTER-PROFILE-GATE-2026-06-23"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW9C_REPORT = RESULT_ROOT / "rw9c_static_fit_print_handoff" / "rw9c_static_fit_print_handoff_report.json"
RW9C_STL = RESULT_ROOT / "rw9c_static_fit_print_handoff" / "print_plate" / "TREE_007_RW9C_static_fit_coupon_arranged_plate.stl"
RW9D_REPORT = RESULT_ROOT / "rw9d_prusaslicer_cli_preflight" / "rw9d_prusaslicer_cli_preflight_report.json"
OUT_DIR = RESULT_ROOT / "rw9e_printer_profile_gate"
PROFILE_PATH = OUT_DIR / "rw9e_printer_profile_template.json"
GCODE_DIR = OUT_DIR / "gcode"
JSON_PATH = OUT_DIR / "rw9e_printer_profile_gate_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW9E_PRINTER_PROFILE_GATE.md"
TMP_DIR = Path("C:/tmp/s4_rw9e_printer_profile_gate")
PRUSASLICER_EXE = Path("C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe")

REQUIRED_POINTER_FIELDS = [
    ("printer", "model"),
    ("printer", "build_plate_mm"),
    ("nozzle", "diameter_mm"),
    ("material", "type"),
    ("material", "diameter_mm"),
    ("slicer", "engine"),
    ("operator", "approved_for_coupon_print"),
]

BLOCKED_CLAIMS = [
    "printer-specific G-code approval without filled profile",
    "physical coupon printed",
    "static coupon measured",
    "static coupon validated",
    "RW10 moving prototype unblocked",
    "physical hingeability",
]


def default_profile_template() -> dict[str, Any]:
    return {
        "profile_status": "draft_unfilled",
        "printer": {
            "model": "",
            "build_plate_mm": [],
            "firmware_or_gcode_flavor": "",
            "notes": "",
        },
        "nozzle": {
            "diameter_mm": None,
        },
        "material": {
            "type": "",
            "brand_or_line": "",
            "diameter_mm": 1.75,
            "first_layer_temperature_c": None,
            "temperature_c": None,
            "first_layer_bed_temperature_c": None,
            "bed_temperature_c": None,
        },
        "slicer": {
            "engine": "PrusaSlicer",
            "config_file_path": "",
            "printer_profile": "",
            "print_profile": "",
            "filament_profile": "",
            "extra_cli_args": ["--support-material", "--support-material-buildplate-only", "--brim-width", "5", "--skirts", "2"],
        },
        "coupon_print_decision": {
            "use_support_brim": True,
            "operator_accepts_support_cleanup_effect_on_measurements": False,
            "do_not_print_generic_rw9d_gcode_without_review": True,
        },
        "operator": {
            "name_or_initials": "",
            "approval_date": "",
            "approved_for_coupon_print": False,
        },
    }


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


def get_nested(data: dict[str, Any], path: tuple[str, str]) -> Any:
    return data.get(path[0], {}).get(path[1])


def missing_required_fields(profile: dict[str, Any]) -> list[str]:
    missing = []
    for path in REQUIRED_POINTER_FIELDS:
        value = get_nested(profile, path)
        if value in (None, "", [], False):
            missing.append(".".join(path))
    if not profile.get("coupon_print_decision", {}).get("operator_accepts_support_cleanup_effect_on_measurements"):
        missing.append("coupon_print_decision.operator_accepts_support_cleanup_effect_on_measurements")
    slicer = profile.get("slicer", {})
    has_config_path = bool(str(slicer.get("config_file_path", "")).strip())
    has_named_profiles = bool(str(slicer.get("printer_profile", "")).strip() and str(slicer.get("print_profile", "")).strip() and str(slicer.get("filament_profile", "")).strip())
    if not (has_config_path or has_named_profiles):
        missing.append("slicer.config_file_path OR slicer printer/print/filament profile names")
    return missing


def profile_paths(profile: dict[str, Any]) -> dict[str, Any]:
    slicer = profile.get("slicer", {})
    config_text = str(slicer.get("config_file_path", "")).strip()
    config_path = Path(config_text) if config_text else None
    if config_path is not None and not config_path.is_absolute():
        config_path = ROOT / config_path
    return {
        "config_file_path": None if config_path is None else str(config_path),
        "config_file_exists": False if config_path is None else config_path.is_file(),
    }


def temp_copy_stl() -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_stl = TMP_DIR / "rw9c_plate.stl"
    shutil.copy2(RW9C_STL, temp_stl)
    return temp_stl


def parse_enriched_gcode_metadata(path: Path) -> dict[str, Any]:
    metadata = _parse_gcode_metadata(path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return metadata
    layer_changes = sum(1 for line in text.splitlines() if line.strip().upper() == ";LAYER_CHANGE")
    if metadata.get("layer_count", 0) == 0 and layer_changes:
        metadata["layer_count"] = layer_changes
        metadata["layer_count_source"] = ";LAYER_CHANGE comment count"
    else:
        metadata["layer_count_source"] = "layer parser"
    return metadata


def build_slicer_args(profile: dict[str, Any]) -> list[str]:
    slicer = profile.get("slicer", {})
    args: list[str] = []
    config_path = str(slicer.get("config_file_path", "")).strip()
    if config_path:
        cp = Path(config_path)
        if not cp.is_absolute():
            cp = ROOT / cp
        args += ["--load", str(cp)]
    for key, flag in [("printer_profile", "--printer-profile"), ("print_profile", "--print-profile"), ("filament_profile", "--material-profile")]:
        value = str(slicer.get(key, "")).strip()
        if value:
            args += [flag, value]
    args += [str(x) for x in slicer.get("extra_cli_args", [])]
    material = profile.get("material", {})
    for key, flag in [
        ("first_layer_temperature_c", "--first-layer-temperature"),
        ("temperature_c", "--temperature"),
        ("first_layer_bed_temperature_c", "--first-layer-bed-temperature"),
        ("bed_temperature_c", "--bed-temperature"),
    ]:
        value = material.get(key)
        if value is not None:
            args += [flag, str(value)]
    nozzle = profile.get("nozzle", {}).get("diameter_mm")
    if nozzle is not None:
        args += ["--nozzle-diameter", str(nozzle)]
    return args


def run_printer_specific_slice(profile: dict[str, Any]) -> dict[str, Any]:
    GCODE_DIR.mkdir(parents=True, exist_ok=True)
    temp_stl = temp_copy_stl()
    temp_gcode = TMP_DIR / "printer_specific_rw9c_coupon.gcode"
    final_gcode = GCODE_DIR / "TREE_007_RW9C_static_fit_coupon_arranged_plate.printer_specific.gcode"
    if temp_gcode.exists():
        temp_gcode.unlink()
    cmd = [str(PRUSASLICER_EXE), "--export-gcode", str(temp_stl), "--output", str(temp_gcode), *build_slicer_args(profile), "--loglevel", "2"]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=240, cwd=str(TMP_DIR))
    ok = proc.returncode == 0 and temp_gcode.exists()
    if ok:
        shutil.copy2(temp_gcode, final_gcode)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    warnings = []
    for line in (stdout + "\n" + stderr).splitlines():
        low = line.lower()
        if "warning" in low or "low bed adhesion" in low or "loose extrusions" in low or "consider enabling" in low:
            warnings.append(line.strip())
    return {
        "attempted": True,
        "ok": ok,
        "returncode": proc.returncode,
        "gcode_path": rel(final_gcode) if ok else None,
        "gcode_size_bytes": final_gcode.stat().st_size if ok else 0,
        "metadata": parse_enriched_gcode_metadata(final_gcode) if ok else {"layer_count": 0, "estimated_time_s": 0.0, "filament_mm": 0.0},
        "warnings": warnings,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "command_without_exe": cmd[1:],
    }


def build_doc(payload: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in payload["summary"].items()]
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    missing_rows = [[item] for item in payload["missing_profile_fields"]]
    blockers = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW9e printer profile gate

Status: `{payload['status']}`.

RW9e is the safety gate between generic PrusaSlicer G-code and a real coupon print.  It requires a real printer/nozzle/material/profile decision before producing or approving printer-specific G-code.

## Inputs

| input | path |
| --- | --- |
| RW9c report | `{payload['precondition']['rw9c_report']}` |
| RW9d report | `{payload['precondition']['rw9d_report']}` |
| profile template | `{payload['artifacts']['profile_template_json']}` |

## Summary

{table(['field', 'value'], summary_rows)}

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Missing profile fields

{table(['missing field'], missing_rows) if missing_rows else 'No missing profile fields.'}

## Printer-specific slice attempt

`{payload['printer_specific_slice']}`

## How to unblock

Fill `{payload['artifacts']['profile_template_json']}` with the real printer, nozzle, material, slicer config/profile, and operator approval.  Then rerun this script.  If it passes, inspect the generated printer-specific G-code in the slicer before printing.

## Claim boundary

RW9e does not validate the physical coupon.  It only prevents generic G-code from becoming an accidental print claim.

## Open blockers

{table(['blocker'], blockers)}
"""


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    if not PROFILE_PATH.exists():
        write_json(PROFILE_PATH, default_profile_template())
    profile = load_json(PROFILE_PATH)
    rw9c = load_json(RW9C_REPORT)
    rw9d = load_json(RW9D_REPORT)
    missing = missing_required_fields(profile)
    path_info = profile_paths(profile)
    ready_for_slice = not missing and PRUSASLICER_EXE.exists() and rw9d["summary"].get("generic_support_brim_ok")
    slice_result = {"attempted": False, "reason": "blocked_missing_profile_fields"}
    if ready_for_slice:
        slice_result = run_printer_specific_slice(profile)
    status = "rw9e_printer_profile_gate_pass_printer_specific_gcode_pending_physical_print" if slice_result.get("ok") else "rw9e_printer_profile_gate_blocked_profile_or_operator_approval_missing"
    payload: dict[str, Any] = {
        "report_id": REPORT_ID,
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "precondition": {
            "rw9c_report": rel(RW9C_REPORT),
            "rw9c_status": rw9c["status"],
            "rw9d_report": rel(RW9D_REPORT),
            "rw9d_status": rw9d["status"],
        },
        "profile_path_checks": path_info,
        "missing_profile_fields": missing,
        "summary": {
            "profile_template_exists": PROFILE_PATH.exists(),
            "missing_profile_field_count": len(missing),
            "prusaslicer_cli_installed": PRUSASLICER_EXE.exists(),
            "rw9d_generic_support_brim_ok": bool(rw9d["summary"].get("generic_support_brim_ok")),
            "printer_specific_slice_attempted": bool(slice_result.get("attempted")),
            "printer_specific_gcode_written": bool(slice_result.get("ok")),
            "physical_coupon_printed_or_measured": False,
            "rw10_moving_prototype_unblocked": False,
        },
        "acceptance": {
            "rw9c_handoff_ready": rw9c["status"] == "rw9c_static_fit_print_handoff_ready_physical_print_pending",
            "rw9d_generic_slicer_preflight_passed": rw9d["status"] == "rw9d_prusaslicer_cli_preflight_pass_generic_profile_physical_print_pending",
            "real_printer_profile_supplied": not missing,
            "operator_approved_coupon_print": bool(profile.get("operator", {}).get("approved_for_coupon_print")),
            "printer_specific_gcode_ready": bool(slice_result.get("ok")),
            "claim_boundary_preserved": True,
            "rw10_unblocked": False,
        },
        "printer_specific_slice": slice_result,
        "artifacts": {
            "profile_template_json": rel(PROFILE_PATH),
            "report_json": rel(JSON_PATH),
            "doc": rel(DOC_PATH),
            "gcode_dir": rel(GCODE_DIR),
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": [
            "Fill RW9e printer profile template with real printer/nozzle/material/profile details.",
            "Approve support/brim cleanup impact on measurement surfaces, or choose a different slicing strategy.",
            "Generate and inspect printer-specific G-code.",
            "Physically print and measure the RW9c coupon.",
            "Rerun RW9b and require static_coupon_validated=true before RW10.",
        ],
        "next_task": "Fill RW9e printer profile template, rerun RW9e, then print/measure the coupon if printer-specific G-code passes.",
    }
    write_json(JSON_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "missing_profile_field_count": len(missing),
        "profile_template": rel(PROFILE_PATH),
        "rw10_unblocked": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
