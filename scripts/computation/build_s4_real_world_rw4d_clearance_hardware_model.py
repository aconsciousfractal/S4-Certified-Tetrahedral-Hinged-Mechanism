#!/usr/bin/env python
"""Build RW4d clearance/relief and selected-hinge hardware model for S4.

RW4d consumes RW4c's residual blocker routing and the RW1 physical source lock.
It converts the remaining zero-thickness guard deficits into a parametric
clearance/relief budget over the exploratory RW1 scale/clearance grid, and it
records an external-pin envelope grid for the selected hinge axes.

This is a model and routing artifact only.  It does not generate CAD geometry,
does not subtract reliefs, does not validate finite-thickness collision, does
not certify printability, and does not validate a prototype.
"""

from __future__ import annotations

from collections import defaultdict
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW1_PATH = RESULT_ROOT / "rw1_physical_source_lock.json"
RW2_PATH = RESULT_ROOT / "rw2_mesh_payload_manifest.json"
RW4C_PATH = RESULT_ROOT / "rw4c_blocker_reduction_report.json"
JSON_PATH = RESULT_ROOT / "rw4d_clearance_hardware_model_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4D_CLEARANCE_HARDWARE_MODEL.md"
ROOT_PIECE = "P0"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import mechanical_audit_lib as lib  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lib.json_ready(payload), indent=2) + "\n", encoding="utf-8", newline="\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def param_grid(rw1: dict[str, Any], key: str) -> list[float]:
    return [float(value) for value in rw1["parameter_lock"][key]["grid"]]


def deficit_from_margin(guard_margin: float) -> float:
    return max(0.0, -float(guard_margin))


def group_face_reliefs(tree_report: dict[str, Any], scale_grid: list[float], clearance_grid: list[float]) -> list[dict[str, Any]]:
    records_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in tree_report["face_blocker_records"]:
        records_by_pair[tuple(record["pair"])].append(record)

    groups = []
    bands_by_pair = {tuple(band["pair"]): band for band in tree_report["face_clearance_bands"]}
    for pair, records in sorted(records_by_pair.items()):
        required_model = max(deficit_from_margin(record["guard_margin"]) for record in records)
        band = bands_by_pair[pair]
        groups.append(
            clearance_group(
                group_id=f"{tree_report['tree_id']}_{'-'.join(pair)}_shared_face_relief",
                tree_id=tree_report["tree_id"],
                pair=list(pair),
                route="shared_face_relief_cutback_required",
                theta_domain=band["theta_band_degrees"],
                source_blocker_count=len(records),
                required_model_clearance=required_model,
                scale_grid=scale_grid,
                clearance_grid=clearance_grid,
                notes=[
                    "Residual shared-face contact cannot be cleared by the zero-thickness interval guard.",
                    "CAD must introduce a relief/cutback or assembly clearance on this non-hinge interface.",
                ],
            )
        )
    return groups


def group_edge_reliefs(tree_report: dict[str, Any], scale_grid: list[float], clearance_grid: list[float]) -> list[dict[str, Any]]:
    micro_by_pair: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    source_count_by_pair: dict[tuple[str, str], int] = defaultdict(int)
    for record in tree_report["edge_adaptive_records"]:
        pair = tuple(record["source"]["pair"])
        source_count_by_pair[pair] += 1
        for micro in record["residual_micro_intervals"]:
            micro_by_pair[pair].append(micro)

    groups = []
    for pair, micros in sorted(micro_by_pair.items()):
        required_model = max(deficit_from_margin(micro["guard_margin"]) for micro in micros)
        left = min(float(micro["theta_interval_degrees"][0]) for micro in micros)
        right = max(float(micro["theta_interval_degrees"][1]) for micro in micros)
        groups.append(
            clearance_group(
                group_id=f"{tree_report['tree_id']}_{'-'.join(pair)}_near_zero_edge_relief",
                tree_id=tree_report["tree_id"],
                pair=list(pair),
                route="near_zero_shared_edge_chamfer_or_start_gap_required",
                theta_domain=[round(left, 12), round(right, 12)],
                source_blocker_count=source_count_by_pair[pair],
                required_model_clearance=required_model,
                scale_grid=scale_grid,
                clearance_grid=clearance_grid,
                notes=[
                    "Adaptive subdivision certified the rest of the coarse edge interval.",
                    "Only near-zero micro-intervals remain; a tiny chamfer/start-gap relief is the appropriate next model.",
                ],
            )
        )
    return groups


def clearance_group(
    group_id: str,
    tree_id: str,
    pair: list[str],
    route: str,
    theta_domain: list[float],
    source_blocker_count: int,
    required_model_clearance: float,
    scale_grid: list[float],
    clearance_grid: list[float],
    notes: list[str],
) -> dict[str, Any]:
    required_by_scale = {
        str(int(scale) if scale.is_integer() else scale): round(required_model_clearance * scale, 9)
        for scale in scale_grid
    }
    cells = []
    covering_by_scale: dict[str, list[float]] = defaultdict(list)
    for scale, clearance in itertools.product(scale_grid, clearance_grid):
        model_clearance = clearance / scale
        margin = model_clearance - required_model_clearance
        covers = margin >= -1.0e-15
        scale_key = str(int(scale) if scale.is_integer() else scale)
        if covers:
            covering_by_scale[scale_key].append(clearance)
        cells.append(
            {
                "scale_mm_per_model_unit": scale,
                "clearance_mm": clearance,
                "clearance_model_units": round(model_clearance, 12),
                "required_model_clearance": round(required_model_clearance, 12),
                "clearance_margin_model_units": round(margin, 12),
                "covers_guard_deficit": covers,
            }
        )
    return {
        "group_id": group_id,
        "tree_id": tree_id,
        "pair": pair,
        "route": route,
        "theta_domain_degrees": theta_domain,
        "source_blocker_count": source_blocker_count,
        "required_model_clearance": round(required_model_clearance, 12),
        "required_clearance_mm_by_scale": required_by_scale,
        "covering_clearance_mm_by_scale": {key: values for key, values in sorted(covering_by_scale.items())},
        "clearance_grid_cells": cells,
        "notes": notes,
    }


def find_tree(case: dict[str, Any], tree_id: str) -> dict[str, Any]:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"tree not found: {tree_id}")
    return tree


def selected_hinge_hardware_records(
    case: dict[str, Any],
    target_tree_ids: list[str],
    scale_grid: list[float],
    clearance_grid: list[float],
    pin_grid: list[float],
    boss_grid: list[float],
) -> list[dict[str, Any]]:
    records = []
    for tree_id in target_tree_ids:
        tree = find_tree(case, tree_id)
        for hinge in batch.selected_hinges_for_tree(case, tree):
            axis_a = np.asarray(case["labels"][hinge["axis_labels"][0]], dtype=float)
            axis_b = np.asarray(case["labels"][hinge["axis_labels"][1]], dtype=float)
            axis_length_model = float(np.linalg.norm(axis_b - axis_a))
            envelope_grid = []
            for scale, clearance, pin_radius, boss_width in itertools.product(scale_grid, clearance_grid, pin_grid, boss_grid):
                axis_length_mm = axis_length_model * scale
                radial_envelope_mm = pin_radius + clearance + boss_width
                envelope_grid.append(
                    {
                        "scale_mm_per_model_unit": scale,
                        "axis_length_mm": round(axis_length_mm, 9),
                        "clearance_mm": clearance,
                        "pin_radius_mm": pin_radius,
                        "boss_width_mm": boss_width,
                        "radial_envelope_mm": round(radial_envelope_mm, 9),
                        "diameter_to_axis_length_ratio": round((2.0 * radial_envelope_mm) / axis_length_mm, 12) if axis_length_mm > 0 else None,
                    }
                )
            records.append(
                {
                    "tree_id": tree_id,
                    "hinge_id": hinge["hinge_id"],
                    "piece_pair": list(hinge["pieces"]),
                    "axis_labels": list(hinge["axis_labels"]),
                    "axis_support": hinge.get("axis_support", "ambient_edge_subsegment"),
                    "axis_length_model_units": round(axis_length_model, 12),
                    "axis_length_mm_by_scale": {
                        str(int(scale) if scale.is_integer() else scale): round(axis_length_model * scale, 9)
                        for scale in scale_grid
                    },
                    "external_pin_model_status": "placeholder_envelope_only_not_cad_validated",
                    "envelope_grid_count": len(envelope_grid),
                    "minimum_radial_envelope_mm": min(item["radial_envelope_mm"] for item in envelope_grid),
                    "maximum_radial_envelope_mm": max(item["radial_envelope_mm"] for item in envelope_grid),
                    "maximum_diameter_to_axis_length_ratio": max(item["diameter_to_axis_length_ratio"] for item in envelope_grid if item["diameter_to_axis_length_ratio"] is not None),
                    "envelope_grid_examples": envelope_grid[:12],
                }
            )
    return records


def build_doc(report: dict[str, Any]) -> str:
    group_rows = []
    for group in report["clearance_relief_groups"]:
        group_rows.append(
            [
                group["group_id"],
                group["route"],
                group["theta_domain_degrees"],
                group["source_blocker_count"],
                group["required_model_clearance"],
                group["required_clearance_mm_by_scale"],
                group["covering_clearance_mm_by_scale"],
            ]
        )
    hinge_rows = []
    for record in report["selected_hinge_hardware"]:
        hinge_rows.append(
            [
                record["tree_id"],
                record["hinge_id"],
                "-".join(record["piece_pair"]),
                "-".join(record["axis_labels"]),
                record["axis_length_model_units"],
                record["axis_length_mm_by_scale"],
                record["minimum_radial_envelope_mm"],
                record["maximum_radial_envelope_mm"],
            ]
        )
    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4d Clearance/Hardware Model",
            "",
            "Status: parametric clearance/relief and external-pin envelope model; not CAD validated.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4d converts RW4c's residual blocker ledger into two physical-model inputs:",
            "clearance/relief budgets for residual non-hinge contacts, and external-pin",
            "envelope budgets for the selected hinge axes.  It does not write modified CAD",
            "or prove finite-thickness motion.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW1 source lock", rel(RW1_PATH)],
                    ["RW2 mesh payload", rel(RW2_PATH)],
                    ["RW4c blocker reduction", rel(RW4C_PATH)],
                ],
            ),
            "",
            "## Parameter Grid",
            "",
            table(
                ["Parameter", "Values"],
                [[key, value] for key, value in report["parameter_grid"].items()],
            ),
            "",
            "## Summary",
            "",
            table(["Metric", "Value"], [[key, value] for key, value in report["summary"].items()]),
            "",
            "## Clearance/Relief Groups",
            "",
            table(
                ["Group", "Route", "Theta domain", "Blockers", "Required model clearance", "Required mm by scale", "Covering grid clearances"],
                group_rows,
            ),
            "",
            "## Selected-Hinge External-Pin Envelope",
            "",
            table(
                ["Tree", "Hinge", "Pair", "Axis", "Length model", "Length mm by scale", "Min radial envelope mm", "Max radial envelope mm"],
                hinge_rows,
            ),
            "",
            "## Interpretation",
            "",
            "The RW1 clearance grid has nominal cells that cover the guard-deficit budget,",
            "but this is not yet a physical proof: RW4e must materialize relief/hardware",
            "geometry or an equivalent envelope model and re-run collision/clearance checks.",
            "",
            "## Explicit Nonclaims",
            "",
            "- physical hingeability",
            "- finite-thickness clearance",
            "- selected-hinge hardware clearance",
            "- CAD validity",
            "- printability",
            "- fabrication readiness",
            "- prototype validation",
            "",
            "## Acceptance",
            "",
            table(["Check", "Value"], acceptance_rows),
            "",
            "## Next Task",
            "",
            report["next_task"],
            "",
        ]
    )


def main() -> int:
    if not RW1_PATH.exists():
        raise RuntimeError(f"missing RW1 source lock: {RW1_PATH}")
    if not RW4C_PATH.exists():
        raise RuntimeError(f"missing RW4c report: {RW4C_PATH}")
    rw1 = load_json(RW1_PATH)
    rw2 = load_json(RW2_PATH) if RW2_PATH.exists() else {}
    rw4c = load_json(RW4C_PATH)
    case = batch.build_case()

    scale_grid = param_grid(rw1, "scale_mm")
    clearance_grid = param_grid(rw1, "clearance_policy")
    pin_grid = param_grid(rw1, "hinge_axis_radius_mm")
    boss_grid = param_grid(rw1, "shell_or_boss_thickness_mm")

    clearance_groups = []
    for tree_report in rw4c["trees"]:
        clearance_groups.extend(group_face_reliefs(tree_report, scale_grid, clearance_grid))
        clearance_groups.extend(group_edge_reliefs(tree_report, scale_grid, clearance_grid))

    max_required_model = max(group["required_model_clearance"] for group in clearance_groups)
    covering_scale_clearance_cells = []
    for scale, clearance in itertools.product(scale_grid, clearance_grid):
        if clearance / scale >= max_required_model - 1.0e-15:
            covering_scale_clearance_cells.append(
                {
                    "scale_mm_per_model_unit": scale,
                    "clearance_mm": clearance,
                    "clearance_model_units": round(clearance / scale, 12),
                    "margin_model_units": round(clearance / scale - max_required_model, 12),
                }
            )

    target_tree_ids = [tree["tree_id"] for tree in rw4c["trees"]]
    hardware_records = selected_hinge_hardware_records(case, target_tree_ids, scale_grid, clearance_grid, pin_grid, boss_grid)
    full_grid_candidate_count = len(covering_scale_clearance_cells) * len(pin_grid) * len(boss_grid)

    report = {
        "report_id": "S4-RW4D-CLEARANCE-HARDWARE-MODEL-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "clearance_hardware_model_created_not_cad_validated",
        "precondition": {
            "rw1_source_lock": rel(RW1_PATH),
            "rw1_status": rw1.get("status"),
            "rw2_mesh_payload": rel(RW2_PATH) if RW2_PATH.exists() else None,
            "rw4c_blocker_reduction": rel(RW4C_PATH),
            "rw4c_status": rw4c.get("status"),
        },
        "scope": {
            "model_kind": "parametric_clearance_relief_and_external_pin_envelope",
            "body_geometry_source": "exact_body_solids_from_rw2_no_relief_subtracted_yet",
            "relief_geometry_status": "not_materialized",
            "hardware_geometry_status": "external_pin_envelope_only_not_cad",
            "finite_thickness_clearance_status": "not_certified",
            "printability_validation_status": "not_run",
        },
        "parameter_grid": {
            "scale_mm": scale_grid,
            "clearance_policy_mm": clearance_grid,
            "hinge_axis_radius_mm": pin_grid,
            "shell_or_boss_thickness_mm": boss_grid,
        },
        "summary": {
            "clearance_relief_group_count": len(clearance_groups),
            "shared_face_relief_group_count": sum(1 for group in clearance_groups if group["route"] == "shared_face_relief_cutback_required"),
            "near_zero_edge_relief_group_count": sum(1 for group in clearance_groups if group["route"] == "near_zero_shared_edge_chamfer_or_start_gap_required"),
            "maximum_required_model_clearance": round(max_required_model, 12),
            "minimum_required_clearance_mm_by_scale": {
                str(int(scale) if scale.is_integer() else scale): round(max_required_model * scale, 9)
                for scale in scale_grid
            },
            "covering_scale_clearance_cell_count": len(covering_scale_clearance_cells),
            "full_parameter_grid_candidate_count_before_cad": full_grid_candidate_count,
            "selected_hinge_axis_count": len(hardware_records),
            "all_selected_hinge_axes_positive_length": all(record["axis_length_model_units"] > 0 for record in hardware_records),
            "clearance_model_required_before_rw5": True,
        },
        "covering_scale_clearance_cells": covering_scale_clearance_cells,
        "clearance_relief_groups": clearance_groups,
        "selected_hinge_hardware": hardware_records,
        "acceptance": {
            "rw1_source_lock_present": RW1_PATH.exists(),
            "rw4c_report_present": RW4C_PATH.exists(),
            "all_rw4c_remaining_blockers_mapped_to_relief_groups": len(clearance_groups) > 0,
            "at_least_one_clearance_scale_cell_covers_all_guard_deficits": len(covering_scale_clearance_cells) > 0,
            "selected_hinge_hardware_grid_enumerated": len(hardware_records) > 0,
            "all_selected_hinge_axes_positive_length": all(record["axis_length_model_units"] > 0 for record in hardware_records),
            "cad_geometry_written": False,
            "finite_thickness_clearance_certified": False,
            "printability_validation_run": False,
            "report_says_no_physical_claim": True,
        },
        "next_task": "RW4e materialize relief/hardware candidate payloads or equivalent envelope checks, then rerun clearance before RW5 printability/fabrication gates.",
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "report": rel(JSON_PATH), "summary": rel(DOC_PATH), "totals": report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
