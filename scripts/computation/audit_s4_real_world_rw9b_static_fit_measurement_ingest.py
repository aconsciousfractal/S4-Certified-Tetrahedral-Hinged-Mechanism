#!/usr/bin/env python
"""RW9b static fit coupon measurement ingest/checker.

RW9b ingests the RW9 measurement CSV after physical coupon printing and
measurement.  With the initial blank template, the expected status is pending:
no static coupon validation, no fabrication readiness, and no RW10 moving
prototype unblock.
"""

from __future__ import annotations

import csv
import json
import statistics
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CASE_ID = "historical_s4_median_planes"
DATE = "2026-06-23"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW9_PATH = RESULT_ROOT / "rw9_static_fit_coupon_body_preserving_tree007" / "rw9_static_fit_coupon_package_report.json"
OUT_DIR = RESULT_ROOT / "rw9b_static_fit_measurement_ingest"
JSON_PATH = OUT_DIR / "rw9b_static_fit_measurement_ingest_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW9B_STATIC_FIT_MEASUREMENT_INGEST.md"

REQUIRED_FIELDS = [
    "record_id", "coupon_component", "feature_id", "nominal_mm",
    "measured_mm_1", "measured_mm_2", "measured_mm_3", "mean_measured_mm",
    "tool", "fit_with_nominal_pin", "fit_class", "notes",
]

FIT_CLASSES = [
    "too_tight_no_insert",
    "tight_insert",
    "sliding_fit",
    "loose_fit",
    "too_loose",
]

BLOCKED_CLAIMS = [
    "static coupon validation",
    "fabrication readiness",
    "moving prototype validation",
    "physical hingeability",
    "public theorem promotion from physical evidence",
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


def parse_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def load_measurements(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        fields = reader.fieldnames or []
        rows = [dict(row) for row in reader]
    missing = [field for field in REQUIRED_FIELDS if field not in fields]
    return rows, missing


def summarize_row(row: dict[str, str]) -> dict[str, Any]:
    values = [parse_float(row.get(key)) for key in ("measured_mm_1", "measured_mm_2", "measured_mm_3")]
    measured_values = [value for value in values if value is not None]
    explicit_mean = parse_float(row.get("mean_measured_mm"))
    computed_mean = statistics.fmean(measured_values) if measured_values else explicit_mean
    nominal = parse_float(row.get("nominal_mm"))
    fit_class = (row.get("fit_class") or "").strip()
    tool = (row.get("tool") or "").strip()
    notes = (row.get("notes") or "").strip()
    has_any_data = bool(measured_values or explicit_mean is not None or fit_class or tool or notes or (row.get("fit_with_nominal_pin") or "").strip())
    errors = []
    if nominal is None:
        errors.append("nominal_mm_missing_or_invalid")
    if fit_class and fit_class not in FIT_CLASSES:
        errors.append("invalid_fit_class")
    if measured_values and explicit_mean is not None and abs(statistics.fmean(measured_values) - explicit_mean) > 0.03:
        errors.append("mean_measured_mm_differs_from_replicate_mean_gt_0_03mm")
    if measured_values and not tool:
        errors.append("measurement_tool_missing")
    row_complete = bool(computed_mean is not None and tool and not errors)
    return {
        "record_id": row.get("record_id", ""),
        "coupon_component": row.get("coupon_component", ""),
        "feature_id": row.get("feature_id", ""),
        "nominal_mm": nominal,
        "measured_values_mm": measured_values,
        "mean_measured_mm": computed_mean,
        "deviation_from_nominal_mm": None if nominal is None or computed_mean is None else computed_mean - nominal,
        "tool": tool,
        "fit_with_nominal_pin": (row.get("fit_with_nominal_pin") or "").strip(),
        "fit_class": fit_class,
        "notes": notes,
        "has_any_physical_data": has_any_data,
        "row_complete": row_complete,
        "errors": errors,
    }


def feature_groups(rows: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups = {
        "hole_sweep": [],
        "pin_sweep": [],
        "nominal_knuckles": [],
        "nominal_pin": [],
        "other": [],
    }
    for row in rows:
        feature = row["feature_id"]
        if feature.startswith("hole_diameter_"):
            groups["hole_sweep"].append(row)
        elif feature.startswith("pin_diameter_"):
            groups["pin_sweep"].append(row)
        elif row["coupon_component"].endswith("nominal_pin_reference"):
            groups["nominal_pin"].append(row)
        elif row["coupon_component"].endswith("nominal_outer_knuckle_pair") or row["coupon_component"].endswith("nominal_center_knuckle"):
            groups["nominal_knuckles"].append(row)
        else:
            groups["other"].append(row)
    return groups


def estimate_fit_candidates(groups: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    candidates = []
    hole_rows = [row for row in groups["hole_sweep"] if row["mean_measured_mm"] is not None]
    pin_rows = [row for row in groups["pin_sweep"] if row["mean_measured_mm"] is not None]
    for hole in hole_rows:
        for pin in pin_rows:
            clearance = hole["mean_measured_mm"] - pin["mean_measured_mm"]
            score = abs(clearance - 0.6)  # RW7f nominal diametral clearance: 3.10 - 2.50 = 0.60 mm.
            candidates.append({
                "hole_record_id": hole["record_id"],
                "pin_record_id": pin["record_id"],
                "hole_mean_mm": hole["mean_measured_mm"],
                "pin_mean_mm": pin["mean_measured_mm"],
                "diametral_clearance_mm": clearance,
                "clearance_error_from_nominal_mm": score,
            })
    return sorted(candidates, key=lambda item: item["clearance_error_from_nominal_mm"])


def build_doc(payload: dict[str, Any]) -> str:
    summary_rows = [[key, value] for key, value in payload["summary"].items()]
    acceptance_rows = [[key, value] for key, value in payload["acceptance"].items()]
    row_rows = []
    for row in payload["row_summaries"]:
        row_rows.append([
            row["record_id"],
            row["feature_id"],
            row["nominal_mm"],
            row["mean_measured_mm"],
            row["tool"] or "",
            row["fit_class"] or "",
            row["row_complete"],
            ", ".join(row["errors"]),
        ])
    blockers = [[item] for item in payload["open_blockers"]]
    return f"""# S4 RW9b static fit measurement ingest

Status: `{payload['status']}`.

RW9b ingests physical measurement data for the RW9 coupon.  The current run reads the measurement CSV and reports whether physical validation can proceed.  Blank template rows are expected to produce `pending_physical_data`, not a pass.

## Inputs

| input | path |
| --- | --- |
| RW9 package report | `{payload['precondition']['rw9_report']}` |
| measurement CSV | `{payload['precondition']['measurement_csv']}` |
| measurement protocol | `{payload['precondition']['measurement_protocol']}` |

## Summary

{table(['field', 'value'], summary_rows)}

## Acceptance

{table(['check', 'value'], acceptance_rows)}

## Row summaries

{table(['record', 'feature', 'nominal mm', 'mean measured mm', 'tool', 'fit class', 'complete', 'errors'], row_rows)}

## Best measured clearance candidates

`{payload['best_measured_clearance_candidates'][:5]}`

## Claim boundary

RW9b does not validate the coupon unless physical measurements are present, complete, and identify an acceptable fit.  Fabrication readiness, RW10 moving prototype, and physical hingeability remain blocked in the current status.

## Open blockers

{table(['blocker'], blockers)}

## Next task

Print the RW9 coupon package, measure the features listed in the CSV, enter the values and fit classes, then rerun this RW9b script.
"""


def main() -> None:
    rw9 = load_json(RW9_PATH)
    csv_path = ROOT / rw9["measurement_artifacts"]["measurement_csv_template"]
    protocol_path = ROOT / rw9["measurement_artifacts"]["measurement_protocol_json"]
    protocol = load_json(protocol_path)
    raw_rows, missing_fields = load_measurements(csv_path)
    row_summaries = [summarize_row(row) for row in raw_rows]
    groups = feature_groups(row_summaries)
    best_candidates = estimate_fit_candidates(groups)
    rows_with_data = [row for row in row_summaries if row["has_any_physical_data"]]
    rows_complete = [row for row in row_summaries if row["row_complete"]]
    row_errors = [err for row in row_summaries for err in row["errors"]]

    required_group_counts = {
        "hole_sweep": 5,
        "pin_sweep": 5,
        "nominal_knuckles": 4,
        "nominal_pin": 1,
    }
    group_presence = {key: len(groups[key]) for key in required_group_counts}
    required_groups_present = all(group_presence[key] == expected for key, expected in required_group_counts.items())
    any_physical_data = bool(rows_with_data)
    complete_physical_measurements = (
        not missing_fields
        and required_groups_present
        and len(rows_complete) == len(row_summaries)
        and not row_errors
    )
    fit_rows = [row for row in row_summaries if row["fit_class"]]
    sliding_fit_rows = [row for row in fit_rows if row["fit_class"] == "sliding_fit"]
    best_pair_identified = bool(best_candidates and any_physical_data)
    documented_adjustment = any("adjust" in row["notes"].lower() or "adjusted" in row["notes"].lower() for row in row_summaries)
    static_coupon_validated = bool(
        complete_physical_measurements
        and best_pair_identified
        and (sliding_fit_rows or documented_adjustment)
    )
    status = (
        "rw9b_static_fit_measurement_validated_rw10_unblocked"
        if static_coupon_validated
        else "rw9b_static_fit_measurement_ingest_incomplete_or_failed_rw10_blocked"
        if any_physical_data
        else "rw9b_static_fit_measurement_ingest_pending_physical_data_rw10_blocked"
    )
    payload: dict[str, Any] = {
        "report_id": "S4-RW9B-STATIC-FIT-MEASUREMENT-INGEST-2026-06-23",
        "date": DATE,
        "case_id": CASE_ID,
        "status": status,
        "precondition": {
            "rw9_report": rel(RW9_PATH),
            "rw9_status": rw9["status"],
            "measurement_csv": rel(csv_path),
            "measurement_protocol": rel(protocol_path),
        },
        "protocol_acceptance_rule": protocol.get("acceptance_rule_before_rw10", {}),
        "summary": {
            "measurement_rows_total": len(row_summaries),
            "rows_with_any_physical_data": len(rows_with_data),
            "rows_complete": len(rows_complete),
            "missing_csv_fields": missing_fields,
            "required_groups_present": required_groups_present,
            "row_error_count": len(row_errors),
            "fit_class_rows": len(fit_rows),
            "sliding_fit_rows": len(sliding_fit_rows),
            "best_measured_clearance_candidates": len(best_candidates),
            "static_coupon_validated": static_coupon_validated,
            "rw10_moving_prototype_unblocked": static_coupon_validated,
        },
        "group_presence": group_presence,
        "row_summaries": row_summaries,
        "best_measured_clearance_candidates": best_candidates[:10],
        "artifacts": {
            "json_report": rel(JSON_PATH),
            "markdown_report": rel(DOC_PATH),
        },
        "blocked_claims": BLOCKED_CLAIMS,
        "open_blockers": [
            "No physical measurement data found in the CSV" if not any_physical_data else "Physical measurement data is incomplete or not yet accepted",
            "No best measured hole/pin pair can be accepted" if not best_pair_identified else "Best measured hole/pin pair requires review",
            "No sliding-fit row or documented adjustment found" if not sliding_fit_rows and not documented_adjustment else "Sliding-fit/documented adjustment present but full acceptance still requires complete data",
            "RW10 moving prototype remains blocked" if not static_coupon_validated else "RW10 can proceed only with the accepted RW9b measured parameters",
        ],
        "acceptance": {
            "rw9_package_report_present": RW9_PATH.exists(),
            "measurement_csv_present": csv_path.exists(),
            "measurement_protocol_present": protocol_path.exists(),
            "csv_schema_complete": not missing_fields,
            "required_feature_groups_present": required_groups_present,
            "physical_measurements_present": any_physical_data,
            "physical_measurements_complete": complete_physical_measurements,
            "valid_fit_classes_or_blank": not any(err == "invalid_fit_class" for err in row_errors),
            "best_hole_pin_pair_identified": best_pair_identified,
            "sliding_fit_or_documented_adjustment": bool(sliding_fit_rows or documented_adjustment),
            "static_coupon_validated": static_coupon_validated,
            "rw10_moving_prototype_unblocked": static_coupon_validated,
        },
        "next_task": "Print and measure the RW9 coupon, fill the measurement CSV, then rerun RW9b; RW10 remains blocked until RW9b validates measured data.",
    }
    write_json(JSON_PATH, payload)
    write_text(DOC_PATH, build_doc(payload))
    print(json.dumps({
        "status": payload["status"],
        "rows_total": payload["summary"]["measurement_rows_total"],
        "rows_with_any_physical_data": payload["summary"]["rows_with_any_physical_data"],
        "static_coupon_validated": payload["summary"]["static_coupon_validated"],
        "rw10_moving_prototype_unblocked": payload["summary"]["rw10_moving_prototype_unblocked"],
        "json_report": payload["artifacts"]["json_report"],
    }, indent=2))


if __name__ == "__main__":
    main()
