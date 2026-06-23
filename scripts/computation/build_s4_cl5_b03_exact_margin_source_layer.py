#!/usr/bin/env python
"""
Build the B03 strict-convex SAT exact-margin source-layer inventory.

R31 does not promote reports.  It audits the R29 B03-shaped diagnostic reports
and classifies whether each report has the two things required before B03-FI or
B03-SS can exist:

* a route-clean B03 clearance target, not a selected-hinge or residual fallback
  target;
* replayable exact rational or source-locked symbolic axis/support/margin
  evidence.

The current R29 reports intentionally fail that test: they are finite
float-guard diagnostics, and all 11 current candidates are residual
shared-edge/shared-face route-out cases rather than route-clean B03 clearance
cases.  This script records that boundary explicitly so the next task can move
to the right exact-report family instead of trying to promote placeholders.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
PREDICATE_ID = "B03_STRICT_CONVEX_SAT"
SOURCE_LAYER_ID = "S4-CL5-B03-STRICT-CONVEX-SAT-EXACT-MARGIN-SOURCE-LAYER-2026-06-21"

DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_strict_convex_sat_diagnostic_manifest.json"
)
DEFAULT_OUT = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_strict_convex_sat_exact_margin_source_layer_manifest.json"
)


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"expected JSON object: {path}")
    return data


def write_json_lf(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def endpoint_fraction(value: dict[str, Any]) -> Fraction | None:
    try:
        return Fraction(int(value["num"]), int(value["den"]))
    except Exception:
        return None


def interval_lo(value: Any) -> Fraction | None:
    if not isinstance(value, dict):
        return None
    lo = value.get("lo")
    if not isinstance(lo, dict):
        return None
    return endpoint_fraction(lo)


def interval_is_strictly_positive(value: Any) -> bool:
    lo = interval_lo(value)
    return lo is not None and lo > 0


def is_diagnostic_placeholder_interval(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    source_expr = str(value.get("source_expr", ""))
    lo = value.get("lo") or {}
    hi = value.get("hi") or {}
    return (
        "diagnostic" in source_expr
        and lo.get("num") == "0"
        and lo.get("den") == "1"
        and hi.get("num") == "0"
        and hi.get("den") == "1"
    )


def load_report_paths(manifest: dict[str, Any]) -> list[Path]:
    reports = manifest.get("generated_reports") or []
    out: list[Path] = []
    for item in reports:
        if not isinstance(item, dict) or "path" not in item:
            raise ValueError("manifest generated_reports entry missing path")
        out.append(ROOT / item["path"])
    return out


def primary_route_targets(report: dict[str, Any]) -> list[str]:
    data = report.get("predicate_data") or {}
    source = data.get("diagnostic_source") or {}
    route = data.get("route_boundary") or {}
    role = source.get("role")
    targets: list[str] = []
    if route.get("selected_hinge_contact") or role == "selected_hinge_contact":
        targets.append("B04_selected_hinge_contact")
    if route.get("residual_common_edge") or role == "residual_shared_edge":
        targets.append("B05_common_edge_projection")
    if route.get("residual_face_normal") or role == "residual_shared_face":
        targets.append("B06_or_B07_shared_face_split_required")
    return sorted(set(targets))


def raw_route_flags(report: dict[str, Any]) -> list[str]:
    route = ((report.get("predicate_data") or {}).get("route_boundary") or {})
    flags = []
    for key in [
        "selected_hinge_contact",
        "residual_common_edge",
        "residual_face_normal",
        "residual_edge_branch",
    ]:
        if route.get(key):
            flags.append(key)
    return flags


def classify_axis(report: dict[str, Any]) -> dict[str, Any]:
    data = report.get("predicate_data") or {}
    family = data.get("axis_family")
    if family in {"named_axis", "face_normal", "edge_cross"}:
        axis_class = "potential_fraction_interval_axis_if_exact_definition_exists"
        exact_axis_available = bool(data.get("axis", {}).get("exact_definition") or data.get("exact_definition"))
    elif family == "symbolic_axis":
        axis_class = "potential_symbolic_sign_axis_if_source_identity_exists"
        exact_axis_available = bool(data.get("axis", {}).get("exact_definition") or data.get("exact_definition"))
    elif family == "finite_float_sat_guard_diagnostic":
        axis_class = "finite_float_center_axis_or_full_cell_guard_diagnostic"
        exact_axis_available = False
    else:
        axis_class = "unknown_or_unhandled_axis_family"
        exact_axis_available = False
    return {
        "axis_family": family,
        "axis_id": data.get("axis_id"),
        "axis_source_class": axis_class,
        "exact_axis_available": exact_axis_available,
    }


def classify_report(report_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    data = report.get("predicate_data") or {}
    source = data.get("diagnostic_source") or {}
    route_targets = primary_route_targets(report)
    axis = classify_axis(report)

    support_placeholders = [
        key
        for key in ["support_interval_left", "support_interval_right"]
        if is_diagnostic_placeholder_interval(data.get(key))
    ]
    margin_placeholders = [
        key
        for key in ["separation_margin_interval", "margin_interval"]
        if is_diagnostic_placeholder_interval(data.get(key) if key != "margin_interval" else report.get(key))
    ]

    exact_supports_available = not support_placeholders and bool(
        data.get("support_interval_left") and data.get("support_interval_right")
    )
    positive_margin_available = interval_is_strictly_positive(data.get("separation_margin_interval")) or interval_is_strictly_positive(
        report.get("margin_interval")
    )
    b03_route_clean = not route_targets and not raw_route_flags(report)
    b03_fi_ready = (
        b03_route_clean
        and axis["exact_axis_available"]
        and axis["axis_source_class"].startswith("potential_fraction_interval_axis")
        and exact_supports_available
        and positive_margin_available
    )
    b03_ss_ready = (
        b03_route_clean
        and axis["exact_axis_available"]
        and axis["axis_source_class"].startswith("potential_symbolic_sign_axis")
        and positive_margin_available
    )

    blockers: list[str] = []
    if not b03_route_clean:
        blockers.append("route_boundary_not_clean_b03_clearance")
    if not axis["exact_axis_available"]:
        blockers.append("no_exact_or_symbolic_axis_source")
    if axis["axis_source_class"] == "finite_float_center_axis_or_full_cell_guard_diagnostic":
        blockers.append("axis_is_finite_float_diagnostic")
    if support_placeholders:
        blockers.append("support_intervals_are_diagnostic_placeholders")
    if margin_placeholders:
        blockers.append("margin_intervals_are_diagnostic_placeholders")
    if not positive_margin_available:
        blockers.append("no_positive_exact_margin_interval")

    if b03_fi_ready:
        status = "source_ready_b03_fraction_interval"
    elif b03_ss_ready:
        status = "source_ready_b03_symbolic_sign"
    elif route_targets:
        status = "route_out_before_b03_exact_margin_source"
    else:
        status = "blocked_missing_b03_fi_or_b03_ss_source"

    return {
        "axis": axis,
        "b03_fraction_interval_ready": b03_fi_ready,
        "b03_route_clean": b03_route_clean,
        "b03_symbolic_sign_ready": b03_ss_ready,
        "blocked_reasons": sorted(set(blockers)),
        "diagnostic_float_guard": {
            "certified_or_covered_clearance_cells": source.get("certified_or_covered_clearance_cells"),
            "minimum_float_guard_margin": source.get("minimum_float_guard_margin"),
            "minimum_float_overlap": source.get("minimum_float_overlap"),
            "role": source.get("role"),
            "total_cells": source.get("total_cells"),
        },
        "piece_pair": data.get("piece_pair"),
        "primary_route_targets": route_targets,
        "raw_route_flags": raw_route_flags(report),
        "report": rel(report_path),
        "report_id": report.get("report_id"),
        "source_status": status,
        "support_margin_source": {
            "exact_supports_available": exact_supports_available,
            "margin_placeholders": margin_placeholders,
            "positive_margin_available": positive_margin_available,
            "support_placeholders": support_placeholders,
        },
        "tree_id": source.get("tree_id"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    parser.add_argument("--out", default=DEFAULT_OUT.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = ROOT / args.manifest
    out_path = ROOT / args.out
    manifest = read_json(manifest_path)
    decisions = []
    for report_path in load_report_paths(manifest):
        decisions.append(classify_report(report_path, read_json(report_path)))

    route_counts = Counter(target for item in decisions for target in item["primary_route_targets"])
    raw_route_flag_counts = Counter(flag for item in decisions for flag in item["raw_route_flags"])
    blocker_counts = Counter(reason for item in decisions for reason in item["blocked_reasons"])
    status_counts = Counter(item["source_status"] for item in decisions)
    family_counts = Counter((Path(item["report"]).parent.name) for item in decisions)
    source_ready = [
        item
        for item in decisions
        if item["b03_fraction_interval_ready"] or item["b03_symbolic_sign_ready"]
    ]
    route_clean = [item for item in decisions if item["b03_route_clean"]]

    output = {
        "backend_lock_id": BACKEND_LOCK_ID,
        "b03_route_clean_count": len(route_clean),
        "case_id": CASE_ID,
        "diagnostic_manifest": rel(manifest_path),
        "family_counts": dict(sorted(family_counts.items())),
        "input_report_count": len(decisions),
        "manifest_id": SOURCE_LAYER_ID,
        "nonclaim": [
            "no_b03_accepted_true_report_claim",
            "no_exact_sat_margin_claim",
            "no_float_guard_as_exact_margin_claim",
            "no_theorem_wrapper_promotion_claim",
            "no_physical_hingeability_claim",
        ],
        "predicate_id": PREDICATE_ID,
        "primary_route_out_counts": dict(sorted(route_counts.items())),
        "raw_route_flag_counts": dict(sorted(raw_route_flag_counts.items())),
        "schema_id": SCHEMA_ID,
        "source_blocker_counts": dict(sorted(blocker_counts.items())),
        "source_decisions": decisions,
        "source_layer_status": (
            "no_current_report_has_route_clean_b03_fi_or_b03_ss_margin_source"
            if not source_ready
            else "some_reports_have_candidate_b03_exact_margin_sources"
        ),
        "source_ready_count": len(source_ready),
        "source_status_counts": dict(sorted(status_counts.items())),
        "source_summary": {
            "b03_fraction_interval_ready_count": sum(item["b03_fraction_interval_ready"] for item in decisions),
            "b03_route_clean_count": len(route_clean),
            "b03_symbolic_sign_ready_count": sum(item["b03_symbolic_sign_ready"] for item in decisions),
            "route_out_before_b03_count": sum(
                item["source_status"] == "route_out_before_b03_exact_margin_source"
                for item in decisions
            ),
        },
        "recommended_next_task": (
            "R32: stop treating the current 11 residual shared-edge/shared-face diagnostics as B03 promotion "
            "candidates; build the corresponding B05 common-edge and B06/B07 shared-face exact/source layers, "
            "or create a new route-clean B03 clearance source before any B03 exact-margin report is attempted."
        ),
    }
    write_json_lf(out_path, output)

    print(f"input reports: {len(decisions)}")
    print(f"B03 route-clean reports: {len(route_clean)}")
    print(f"B03 FI/SS source-ready reports: {len(source_ready)}")
    print(f"primary route-out counts: {dict(sorted(route_counts.items()))}")
    print(f"source status counts: {dict(sorted(status_counts.items()))}")
    print(f"manifest: {rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
