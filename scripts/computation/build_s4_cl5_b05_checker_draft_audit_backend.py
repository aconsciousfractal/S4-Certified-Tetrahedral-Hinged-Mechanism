#!/usr/bin/env python
"""
R61 B05 checker-draft/audit backend.

This backend consumes the R60 report-field extraction/audit records.  It does
not promote any real B05 report.  Its purpose is narrower:

* emit schema-v1 checker draft reports for the six finite R60 formula-shape
  candidates;
* normalize R60 diagnostic units into the current checker vocabulary
  (`projection` and `signed_margin`);
* replay every emitted draft through the independent checker and require the
  diagnostic/nonclaim exit code 4;
* route the four proof-locked vacuous-side candidates to a separate checker
  semantics / finite-witness bridge.

The generated draft reports intentionally set ``accepted`` to ``false``.
Therefore the checker validates top-level shape, accepted backends, route
presence, margin/error interval syntax, branch/ledger status, and nonclaims,
then exits as a diagnostic report before accepting any B05 predicate.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]

INPUT_R60_MANIFEST = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_report_field_extraction_audit_manifest.json"
)
OUTPUT_ROOT = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "checker_draft_audit"
)
MANIFEST_PATH = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_checker_draft_audit_manifest.json"
)
CHECKER = ROOT / "scripts/replay_s4_cl5_exact_interval_report.py"
SCHEMA = ROOT / "schemas/s4_cl5_exact_interval_report_schema_v1.yaml"

SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
CASE_ID = "historical_s4_median_planes"
POLICY_ID = "S4-CL5-EXACT-INTERVAL-ARITHMETIC-POLICY-2026-06-21"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
MANIFEST_ID = "S4-CL5-B05-CHECKER-DRAFT-AUDIT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_CHECKER_DRAFT_AUDIT"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"

EXPECTED_DIAGNOSTIC_EXIT = 4

REQUIRED_NONCLAIMS = [
    "no_physical_hingeability_claim",
    "no_global_s4_hingeability_claim",
    "no_dynamic_connectedness_claim",
    "no_theta_zero_positive_clearance_claim",
    "no_theorem_wrapper_promotion_claim",
]
R61_NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_operation_enclosure_semantic_acceptance_claim",
    "no_tau_outward_error_interval_claim",
    "no_vacuous_support_checker_semantics_claim",
]
NONCLAIMS = REQUIRED_NONCLAIMS + R61_NONCLAIMS


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


def rel(path: Path) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def sanitize(value: Any) -> str:
    text = str(value)
    out: list[str] = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def endpoint_from_fraction(value: Fraction) -> dict[str, str]:
    return {"num": str(value.numerator), "den": str(value.denominator)}


def parse_endpoint(endpoint: dict[str, Any]) -> Fraction:
    return Fraction(int(str(endpoint["num"]), 10), int(str(endpoint["den"]), 10))


def parse_interval_bounds(interval: dict[str, Any]) -> tuple[Fraction, Fraction]:
    return parse_endpoint(interval["lo"]), parse_endpoint(interval["hi"])


def normalize_interval(interval: dict[str, Any], *, unit: str, source_note: str | None = None) -> dict[str, Any]:
    lo, hi = parse_interval_bounds(interval)
    source_expr = str(interval.get("source_expr", "R61_normalized_interval"))
    old_unit = str(interval.get("unit", "unknown"))
    if source_note:
        source_expr = f"{source_expr}; {source_note}"
    if old_unit != unit:
        source_expr = f"{source_expr}; R61_unit_normalized_from_{old_unit}_to_{unit}"
    return {
        "endpoint_semantics": str(interval.get("endpoint_semantics", "closed")),
        "hi": endpoint_from_fraction(hi),
        "lo": endpoint_from_fraction(lo),
        "source_expr": source_expr,
        "unit": unit,
    }


def zero_interval(unit: str = "signed_margin") -> dict[str, Any]:
    return {
        "endpoint_semantics": "closed",
        "hi": {"num": "0", "den": "1"},
        "lo": {"num": "0", "den": "1"},
        "source_expr": "R61_zero_error_interval_for_diagnostic_draft",
        "unit": unit,
    }


def finite_min_enclosure(left: dict[str, Any], right: dict[str, Any], *, unit: str) -> dict[str, Any]:
    left_lo, left_hi = parse_interval_bounds(left)
    right_lo, right_hi = parse_interval_bounds(right)
    return {
        "endpoint_semantics": "closed",
        "hi": endpoint_from_fraction(min(left_hi, right_hi)),
        "lo": endpoint_from_fraction(min(left_lo, right_lo)),
        "source_expr": "R61_finite_min_enclosure_of_R60_M_L_candidate_and_M_U_candidate",
        "unit": unit,
    }


def normalize_formula_shape(candidate: dict[str, Any]) -> dict[str, Any]:
    formula = json.loads(json.dumps(candidate["formula_shape"]))
    axis = formula["axis_nondegeneracy"]
    axis["axis_norm_lower_bound"] = normalize_interval(
        axis["axis_norm_lower_bound"],
        unit="projection",
        source_note="checker draft syntax normalization; accepted=false",
    )
    exact_gap = formula["exact_gap_formula"]
    exact_gap["M_gap"] = normalize_interval(exact_gap["M_gap"], unit="signed_margin")
    exact_gap["M_L"] = normalize_interval(exact_gap["M_L"], unit="signed_margin")
    exact_gap["M_U"] = normalize_interval(exact_gap["M_U"], unit="signed_margin")
    for piece_name in ("lower_piece", "upper_piece"):
        piece = formula["component_motion_bounds"].get(piece_name, {})
        for key, value in list(piece.items()):
            if isinstance(value, dict) and {"lo", "hi", "endpoint_semantics", "unit", "source_expr"} <= set(value):
                piece[key] = normalize_interval(value, unit="projection")
    return formula


def normalize_predicate_data(candidate: dict[str, Any]) -> dict[str, Any]:
    gap = normalize_interval(candidate["gap_interval"], unit="signed_margin")
    projection_intervals = [
        normalize_interval(interval, unit="projection")
        for interval in candidate["projection_coordinate_intervals"]
    ]
    return {
        "branch_validity": candidate["branch_validity"],
        "common_edge_id": candidate["common_edge_id"],
        "endpoint_case": candidate["endpoint_case"],
        "formula_shape": normalize_formula_shape(candidate),
        "gap_interval": gap,
        "parent_overlay_key": candidate["parent_overlay_key"],
        "projection_axis_or_coordinate": candidate["projection_axis_or_coordinate"],
        "projection_coordinate_intervals": projection_intervals,
    }


def translate_operation_enclosures(r60_record: dict[str, Any], predicate_data: dict[str, Any]) -> list[dict[str, Any]]:
    by_id = {op["op_id"]: op for op in r60_record.get("operation_enclosure_candidates", [])}
    axis = by_id["op_axis_cross_product"]
    support = by_id["op_support_finite_extrema"]
    gap = by_id["op_M_gap"]
    support_outputs = support["output_intervals"]
    support_min = finite_min_enclosure(
        support_outputs["M_L_candidate"],
        support_outputs["M_U_candidate"],
        unit="signed_margin",
    )
    return [
        {
            "backend_id": "fraction_interval_v1",
            "input_refs": axis.get("input_refs", []),
            "op_id": "op_axis_cross_product",
            "operation": "cross_product_polynomial_components",
            "output_interval": normalize_interval(
                axis["output_interval"],
                unit="projection",
                source_note="R61 checker-draft syntax projection of axis-norm lower bound; accepted=false",
            ),
            "proof_rule": "R61 draft translation of R43 symbolic axis-norm-square lower-bound candidate",
        },
        {
            "backend_id": "fraction_interval_v1",
            "input_refs": support.get("input_refs", []),
            "op_id": "op_support_finite_extrema",
            "operation": "finite_min",
            "output_interval": support_min,
            "proof_rule": "R61 draft finite_min enclosure over R60 finite M_L/M_U support competition candidates",
        },
        {
            "backend_id": "fraction_interval_v1",
            "input_refs": gap.get("input_refs", []),
            "op_id": "op_M_gap",
            "operation": "subtract",
            "output_interval": predicate_data["gap_interval"],
            "proof_rule": "R61 draft translation of R60 proof-locked local M_gap candidate",
        },
    ]


def source_ledger_for(r60_record: dict[str, Any], r60_record_path: str) -> list[str]:
    ledger = [
        r60_record_path,
        "docs/S4_CL5_B05_COMMON_EDGE_EXACT_GAP_DERIVATION.md",
        "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        "scripts/replay_s4_cl5_exact_interval_report.py",
    ]
    for key, value in sorted(r60_record.items()):
        if key.startswith("input_") and isinstance(value, str) and value:
            ledger.append(value)
    original = r60_record.get("original_report")
    if isinstance(original, str) and original:
        ledger.append(original)
    return list(dict.fromkeys(ledger))


def draft_report_path(summary: dict[str, Any]) -> Path:
    rel_dir = Path(str(summary["domain_family"])) / Path(str(summary["original_report"])).stem
    return OUTPUT_ROOT / rel_dir / f"partition_{int(summary['partition_index']):02d}_b05_checker_draft_report.json"


def audit_record_path(summary: dict[str, Any]) -> Path:
    rel_dir = Path(str(summary["domain_family"])) / Path(str(summary["original_report"])).stem
    return OUTPUT_ROOT / rel_dir / f"partition_{int(summary['partition_index']):02d}_checker_draft_audit.json"


def build_draft_report(summary: dict[str, Any], r60_record: dict[str, Any], r60_record_path: str) -> dict[str, Any]:
    predicate_data = normalize_predicate_data(r60_record["report_field_candidate"])
    report_id = (
        "S4-CL5-B05-CHECKER-DRAFT-"
        + sanitize(summary["original_report_id"]).upper()
        + f"-PART-{int(summary['partition_index']):02d}"
    )
    return {
        "accepted": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "branch_stability": {
            "rule": "R61 uses R60 accepted branch_validity for a diagnostic checker draft only",
            "status": "accepted",
        },
        "case_id": CASE_ID,
        "claim_level": "exact_interval_diagnostic_draft",
        "domain_key": f"{summary['original_report_id']}:partition_{int(summary['partition_index']):02d}:R61_checker_draft",
        "error_interval": zero_interval(),
        "failure_reason": "R61 checker draft only: operation-enclosure semantic audit and tau/error envelope are not complete",
        "generator_command": "scripts/build_s4_cl5_b05_checker_draft_audit_backend.py",
        "input_intervals": {
            "selected_positive_shrink_key": r60_record.get("selected_positive_shrink_key"),
            "support_signature": r60_record.get("support_signature"),
        },
        "ledger_reconstruction": {
            "rule": "R61 draft joins R60 report-field extraction with checker schema and replay contract",
            "status": "accepted",
        },
        "margin_interval": predicate_data["gap_interval"],
        "nonclaim": NONCLAIMS,
        "operation_enclosures": translate_operation_enclosures(r60_record, predicate_data),
        "parent_key": str(summary["original_report_id"]),
        "policy_id": POLICY_ID,
        "predicate_data": predicate_data,
        "predicate_id": PREDICATE_ID,
        "replay_interface": {
            "checker": "scripts/replay_s4_cl5_exact_interval_report.py",
            "schema": "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        },
        "report_id": report_id,
        "report_kind": "b05_real_candidate_checker_draft",
        "rounding_backend": "fraction_interval_v1",
        "schema_id": SCHEMA_ID,
        "source_ledger": source_ledger_for(r60_record, r60_record_path),
    }


def replay_draft(path: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        rel(CHECKER),
        "--report",
        rel(path),
        "--schema",
        rel(SCHEMA),
        "--strict",
    ]
    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, check=False)
    return {
        "command": " ".join(cmd),
        "exit_code": proc.returncode,
        "stderr": proc.stderr.strip(),
        "stdout": proc.stdout.strip(),
    }


def route_status(summary: dict[str, Any]) -> str:
    status = str(summary["object_status"])
    if status == "report_field_candidate_partial_vacuous_or_missing_side_bridge_blocked":
        return "vacuous_side_candidate_routed_to_checker_semantics_bridge"
    if status == "report_field_extraction_blocked_diagnostic_nonpositive_margin":
        return "checker_draft_blocked_diagnostic_nonpositive_margin"
    return "checker_draft_blocked_no_proof_locked_positive_seed"


def build_record(summary: dict[str, Any]) -> dict[str, Any]:
    r60_record_path = str(summary["object_record"])
    r60_record = read_json(ROOT / r60_record_path)
    finite = bool(summary.get("formula_shape_contract_candidate_ready"))
    emitted = False
    draft_rel: str | None = None
    replay: dict[str, Any] | None = None
    object_status = route_status(summary)
    blockers = set(r60_record.get("blockers", []))
    blockers.add("accepted_report_promotion_out_of_scope")

    if finite:
        draft_path = draft_report_path(summary)
        draft = build_draft_report(summary, r60_record, r60_record_path)
        write_json_lf(draft_path, draft)
        replay = replay_draft(draft_path)
        emitted = True
        draft_rel = rel(draft_path)
        if replay["exit_code"] == EXPECTED_DIAGNOSTIC_EXIT:
            object_status = "checker_draft_replays_as_diagnostic_nonclaim"
        else:
            object_status = "checker_draft_replay_unexpected_exit_blocked"
            blockers.add("checker_draft_exit_code_mismatch")
    elif summary["object_status"] == "report_field_candidate_partial_vacuous_or_missing_side_bridge_blocked":
        blockers.add("vacuous_support_competition_requires_checker_semantics_or_finite_witness_bridge")

    audit_path = audit_record_path(summary)
    checker_exit = replay["exit_code"] if replay else None
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "checker_draft_report": draft_rel,
        "checker_draft_report_emitted": emitted,
        "checker_expected_exit_code": EXPECTED_DIAGNOSTIC_EXIT if emitted else None,
        "checker_exit_code": checker_exit,
        "checker_exit_matches_expected": bool(emitted and checker_exit == EXPECTED_DIAGNOSTIC_EXIT),
        "checker_replay": replay,
        "claim_level": CLAIM_LEVEL,
        "domain_family": summary["domain_family"],
        "formula_shape_contract_candidate_ready": bool(summary.get("formula_shape_contract_candidate_ready")),
        "input_r60_report_field_extraction_audit_record": r60_record_path,
        "manifest_id": MANIFEST_ID,
        "object_id": "B05-CHECKER-DRAFT-AUDIT-" + sanitize(summary["original_report_id"]) + f"-PART-{int(summary['partition_index']):02d}",
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": summary["original_report"],
        "original_report_id": summary["original_report_id"],
        "partition_index": summary["partition_index"],
        "piece_pair": summary["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready": bool(summary.get("proof_locked_positive_seed_ready")),
        "recommended_next_task": (
            "R62: complete operation-enclosure semantic audit for diagnostic drafts"
            if emitted else
            "R62: add finite-witness/checker-semantics bridge for vacuous-side candidates"
            if object_status == "vacuous_side_candidate_routed_to_checker_semantics_bridge" else
            "No R62 action until a proof-locked positive seed exists"
        ),
        "support_signature": summary["support_signature"],
        "tree_id": summary["tree_id"],
        "vacuous_side_semantics_bridge_required": (
            object_status == "vacuous_side_candidate_routed_to_checker_semantics_bridge"
        ),
        "vacuous_support_competition": summary["vacuous_support_competition"],
    }
    write_json_lf(audit_path, record)
    return {
        "accepted_real_b05_report": False,
        "checker_draft_report": draft_rel,
        "checker_draft_report_emitted": emitted,
        "checker_exit_code": checker_exit,
        "checker_exit_matches_expected": record["checker_exit_matches_expected"],
        "domain_family": record["domain_family"],
        "formula_shape_contract_candidate_ready": record["formula_shape_contract_candidate_ready"],
        "object_record": rel(audit_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": record["original_report"],
        "original_report_id": record["original_report_id"],
        "partition_index": record["partition_index"],
        "piece_pair": record["piece_pair"],
        "proof_locked_positive_seed_ready": record["proof_locked_positive_seed_ready"],
        "support_signature": record["support_signature"],
        "tree_id": record["tree_id"],
        "vacuous_side_semantics_bridge_required": record["vacuous_side_semantics_bridge_required"],
        "vacuous_support_competition": record["vacuous_support_competition"],
    }


def build_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    exit_counts = Counter(
        str(record["checker_exit_code"])
        for record in records
        if record["checker_exit_code"] is not None
    )
    status_counts = Counter(record["object_status"] for record in records)
    emitted = [record for record in records if record["checker_draft_report_emitted"]]
    return {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "checker_draft_report_count": len(emitted),
        "checker_exit_code_counts": dict(sorted(exit_counts.items())),
        "checker_exit_mismatch_count": sum(1 for record in emitted if not record["checker_exit_matches_expected"]),
        "claim_level": CLAIM_LEVEL,
        "finite_formula_shape_candidate_count": sum(1 for record in records if record["formula_shape_contract_candidate_ready"]),
        "input_r60_manifest": rel(INPUT_R60_MANIFEST),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready_count": sum(1 for record in records if record["proof_locked_positive_seed_ready"]),
        "record_count_by_domain_family": dict(sorted(Counter(record["domain_family"] for record in records).items())),
        "records": records,
        "recommended_next_task": "R62: audit operation-enclosure semantics for the 6 replay-clean diagnostic drafts, then add a finite-witness/checker-semantics bridge for the 4 vacuous-side candidates.",
        "vacuous_side_semantics_bridge_required_count": sum(1 for record in records if record["vacuous_side_semantics_bridge_required"]),
    }


def main() -> None:
    manifest = read_json(INPUT_R60_MANIFEST)
    summaries = manifest.get("records") or []
    if not isinstance(summaries, list):
        raise TypeError(f"manifest records must be a list: {INPUT_R60_MANIFEST}")
    records = [build_record(summary) for summary in summaries]
    out_manifest = build_manifest(records)
    write_json_lf(MANIFEST_PATH, out_manifest)
    print(f"input R60 records: {len(summaries)}")
    print(f"R61 checker/audit records emitted: {len(records)}")
    print(f"finite formula-shape candidates consumed: {out_manifest['finite_formula_shape_candidate_count']}")
    print(f"checker draft reports emitted: {out_manifest['checker_draft_report_count']}")
    print(f"checker exit code counts: {out_manifest['checker_exit_code_counts']}")
    print(f"checker exit mismatches: {out_manifest['checker_exit_mismatch_count']}")
    print(f"vacuous-side bridge routes: {out_manifest['vacuous_side_semantics_bridge_required_count']}")
    print(f"operation enclosures ready: {out_manifest['operation_enclosures_ready_count']}")
    print(f"accepted real B05 reports: {out_manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {out_manifest['object_status_counts']}")
    print(f"manifest written: {rel(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
