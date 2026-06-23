#!/usr/bin/env python
"""RW9d PrusaSlicer CLI preflight for the RW9c static-fit coupon.

RW9d verifies that an installed PrusaSlicer CLI can process the arranged RW9c
coupon plate and emit G-code artifacts.  This remains a generic slicer
preflight, not a printer-specific ready-to-print release: the real printer,
material, nozzle, and operator settings still have to be selected before
physical printing.

The script works around PrusaSlicer's Windows CLI write failure on project
paths containing spaces/apostrophes by slicing from a simple temporary path and
copying the resulting G-code back into the project results directory.
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
REPORT_ID = "S4-RW9D-PRUSASLICER-CLI-PREFLIGHT-2026-06-23"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW9C_REPORT = RESULT_ROOT / "rw9c_static_fit_print_handoff" / "rw9c_static_fit_print_handoff_report.json"
RW9C_STL = RESULT_ROOT / "rw9c_static_fit_print_handoff" / "print_plate" / "TREE_007_RW9C_static_fit_coupon_arranged_plate.stl"
OUT_DIR = RESULT_ROOT / "rw9d_prusaslicer_cli_preflight"
GCODE_DIR = OUT_DIR / "gcode"
JSON_PATH = OUT_DIR / "rw9d_prusaslicer_cli_preflight_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW9D_PRUSASLICER_CLI_PREFLIGHT.md"
TMP_DIR = Path("C:/tmp/s4_rw9d_prusaslicer_cli_preflight")
PRUSASLICER_EXE = Path("C:/Program Files/Prusa3D/PrusaSlicer/prusa-slicer-console.exe")

PROFILES = [
    {
        "profile_id": "generic_default",
        "description": "PrusaSlicer default CLI slicing, no project/printer profile supplied.",
        "extra_args": [],
        "claim": "diagnostic only; warning-prone for horizontal cylinders",
    },
    {
        "profile_id": "generic_support_brim",
        "description": "Generic CLI slicing with support material from build plate and 5 mm brim.",
        "extra_args": ["--support-material", "--support-material-buildplate-only", "--brim-width", "5", "--skirts", "2"],
        "claim": "preferred generic preflight artifact, still not printer-specific",
    },
]

BLOCKED_CLAIMS = [
    "printer-specific G-code approval",
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


def prusaslicer_version() -> str:
    proc = subprocess.run([str(PRUSASLICER_EXE), "--help"], capture_output=True, text=True, timeout=30)
    text = (proc.stdout or proc.stderr or "").splitlines()
    return text[0].strip() if text else "unknown"


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


def copy_to_temp() -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_stl = TMP_DIR / "rw9c_static_fit_coupon_arranged_plate.stl"
    shutil.copy2(RW9C_STL, temp_stl)
    return temp_stl


def run_slice(profile: dict[str, Any], temp_stl: Path) -> dict[str, Any]:
    GCODE_DIR.mkdir(parents=True, exist_ok=True)
    temp_gcode = TMP_DIR / f"{profile['profile_id']}.gcode"
    final_gcode = GCODE_DIR / f"TREE_007_RW9C_static_fit_coupon_arranged_plate.{profile['profile_id']}.gcode"
    if temp_gcode.exists():
        temp_gcode.unlink()
    cmd = [
        str(PRUSASLICER_EXE),
        "--export-gcode",
        str(temp_stl),
        "--output",
        str(temp_gcode),
        *profile["extra_args"],
        "--loglevel",
        "2",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180, cwd=str(TMP_DIR))
    ok = proc.returncode == 0 and temp_gcode.exists()
    if ok:
        shutil.copy2(temp_gcode, final_gcode)
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    combined = stdout + "\n" + stderr
    warnings = []
    for line in combined.splitlines():
        low = line.lower()
        if "warning" in low or "consider enabling" in low or "low bed adhesion" in low or "loose extrusions" in low:
            warnings.append(line.strip())
    metadata = parse_enriched_gcode_metadata(final_gcode) if ok else {"layer_count": 0, "estimated_time_s": 0.0, "filament_mm": 0.0}
    return {
        "profile_id": profile["profile_id"],
        "description": profile["description"],
        "claim": profile["claim"],
        "extra_args": profile["extra_args"],
        "ok": ok,
        "returncode": proc.returncode,
        "gcode_path": rel(final_gcode) if ok else None,
        "gcode_size_bytes": final_gcode.stat().st_size if ok else 0,
        "metadata": metadata,
        "warnings": warnings,
        "stdout_tail": stdout[-2000:],
        "stderr_tail": stderr[-2000:],
        "temp_workaround_used": True,
    }


def build_doc(payload: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in payload["summary"].items()]
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    run_rows = []
    for run in payload["slice_runs"]:
        run_rows.append([
            run["profile_id"],
            run["ok"],
            run["gcode_path"] or "",
            run["gcode_size_bytes"],
            run["metadata"].get("layer_count"),
            run["metadata"].get("estimated_time_s"),
            run["metadata"].get("filament_mm"),
            "; ".join(run["warnings"][:3]),
        ])
    blockers = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW9d PrusaSlicer CLI preflight

Status: `{payload['status']}`.

RW9d verifies that PrusaSlicer CLI can slice the RW9c arranged coupon plate and emit G-code artifacts.  This is not the final printer-specific G-code release: no real printer profile, material profile, nozzle profile, or operator acceptance has been supplied.

## Inputs

| input | path |
| --- | --- |
| RW9c report | `{payload['precondition']['rw9c_report']}` |
| arranged plate STL | `{payload['precondition']['rw9c_stl']}` |
| slicer executable | `{payload['slicer']['path']}` |

## Summary

{table(['field', 'value'], summary_rows)}

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Slice runs

{table(['profile', 'ok', 'gcode', 'bytes', 'layers', 'est sec', 'filament mm', 'warnings'], run_rows)}

## Practical interpretation

`generic_default` proves that the CLI can read and slice the plate, but it reports stability warnings for the horizontal cylindrical coupon bodies.  `generic_support_brim` is the better generic preflight because it enables build-plate supports and a 5 mm brim.  It is still not a replacement for choosing the real printer profile.

## Claim boundary

RW9d generates diagnostic G-code artifacts.  It does not validate physical fit, does not prove the coupon will print correctly on your machine, and does not unblock RW10.

## Open blockers

{table(['blocker'], blockers)}
"""


def main() -> None:
    rw9c = load_json(RW9C_REPORT)
    temp_stl = copy_to_temp()
    version = prusaslicer_version()
    slice_runs = [run_slice(profile, temp_stl) for profile in PROFILES]
    all_runs_ok = all(run["ok"] for run in slice_runs)
    support_run_ok = any(run["profile_id"] == "generic_support_brim" and run["ok"] for run in slice_runs)
    default_has_stability_warning = any(
        run["profile_id"] == "generic_default" and run["warnings"] for run in slice_runs
    )
    status = "rw9d_prusaslicer_cli_preflight_pass_generic_profile_physical_print_pending" if support_run_ok else "rw9d_prusaslicer_cli_preflight_failed"
    payload: dict[str, Any] = {
        "report_id": REPORT_ID,
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "precondition": {
            "rw9c_report": rel(RW9C_REPORT),
            "rw9c_status": rw9c["status"],
            "rw9c_stl": rel(RW9C_STL),
        },
        "slicer": {
            "name": "PrusaSlicer CLI",
            "version_banner": version,
            "path": str(PRUSASLICER_EXE),
            "installed": PRUSASLICER_EXE.exists(),
            "project_path_temp_workaround_required": True,
            "temp_work_dir": str(TMP_DIR),
        },
        "summary": {
            "slice_run_count": len(slice_runs),
            "all_slice_runs_ok": all_runs_ok,
            "generic_support_brim_ok": support_run_ok,
            "default_profile_reports_stability_warnings": default_has_stability_warning,
            "printer_specific_profile_supplied": False,
            "physical_coupon_printed_or_measured": False,
            "rw10_moving_prototype_unblocked": False,
        },
        "acceptance": {
            "rw9c_handoff_ready": rw9c["status"] == "rw9c_static_fit_print_handoff_ready_physical_print_pending",
            "prusaslicer_cli_installed": PRUSASLICER_EXE.exists(),
            "gcode_written_for_default_profile": any(run["profile_id"] == "generic_default" and run["ok"] for run in slice_runs),
            "gcode_written_for_support_brim_profile": support_run_ok,
            "claim_boundary_preserved": True,
            "rw10_unblocked": False,
        },
        "slice_runs": slice_runs,
        "artifacts": {
            "report_json": rel(JSON_PATH),
            "doc": rel(DOC_PATH),
            "gcode_dir": rel(GCODE_DIR),
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": [
            "Select the actual printer/nozzle/material profile in PrusaSlicer.",
            "Inspect/adjust support and brim settings for clean hole/rod measurement surfaces.",
            "Physically print the RW9c coupon plate.",
            "Measure the printed coupon and fill the RW9c measurement CSV.",
            "Rerun RW9b and require static_coupon_validated=true before RW10.",
        ],
        "next_task": "Use the support/brim G-code as a diagnostic starting point or reslice the RW9c plate with the real printer profile, then print and measure the coupon.",
    }
    write_json(JSON_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "support_brim_ok": support_run_ok,
        "gcode_dir": rel(GCODE_DIR),
        "rw10_unblocked": False,
    }, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
