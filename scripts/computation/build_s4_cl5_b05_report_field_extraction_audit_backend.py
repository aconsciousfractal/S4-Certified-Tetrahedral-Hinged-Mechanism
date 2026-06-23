#!/usr/bin/env python
"""
R60 B05 report-field extraction/audit backend.

This backend consumes the R59 local Taylor-trig proof-locked replay records.
It extracts checker-shaped B05 report-field candidates from the 10 proof-locked
local seeds while keeping accepted reports at zero until the operation-enclosure
audit is complete.

The key no-false-positive split is:

* 10 records have proof-locked local g0/M_gap candidates;
* 6 of those also have finite lower and upper support-competition intervals,
  so M_L/M_U and formula-shape candidate fields can be emitted;
* 4 records have an upper support side that is vacuous, which is logically
  usable for separation but is not yet representable by the current R38 checker
  contract, which requires positive finite M_U.  They are kept as partial
  candidates with an explicit vacuous-side bridge blocker.
"""

from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]

INPUT_R59_MANIFEST = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_local_taylor_trig_proof_locked_replay_manifest.json"
)
INPUT_R43_MANIFEST = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_norm_symbolic_lower_bound_manifest.json"
)
OUTPUT_ROOT = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "report_field_extraction_audit"
)
MANIFEST_PATH = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_report_field_extraction_audit_manifest.json"
)

BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
MANIFEST_ID = "S4-CL5-B05-REPORT-FIELD-EXTRACTION-AUDIT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_REPORT_FIELD_EXTRACTION_AUDIT"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
CASE_ID = "historical_s4_median_planes"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_operation_enclosure_ready_claim",
    "no_tau_outward_error_interval_claim",
    "no_vacuous_support_checker_semantics_claim",
    "no_physical_hingeability_claim",
    "no_theorem_promotion_claim",
]


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


def interval_zero(unit: str = "signed_margin", expr: str = "zero") -> dict[str, Any]:
    return {
        "endpoint_semantics": "closed",
        "hi": {"num": "0", "den": "1"},
        "lo": {"num": "0", "den": "1"},
        "source_expr": expr,
        "unit": unit,
    }


def load_manifest_records(path: Path) -> list[dict[str, Any]]:
    manifest = read_json(path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"manifest records must be a list: {path}")
    return records


def index_r43_records() -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for summary in load_manifest_records(INPUT_R43_MANIFEST):
        if not isinstance(summary, dict):
            continue
        original_id = str(summary.get("original_report_id"))
        rec_path = ROOT / str(summary.get("object_record"))
        out[original_id] = {"summary": summary, "record": read_json(rec_path), "record_path": rel(rec_path)}
    return out


def selected_attempt(r59_record: dict[str, Any]) -> tuple[str | None, dict[str, Any] | None]:
    keys = r59_record.get("proof_locked_positive_shrink_keys") or []
    if not keys:
        return None, None
    key = str(keys[0])
    return key, r59_record.get("shrink_attempts", {}).get(key)


def side_labels(side: dict[str, Any], field: str) -> list[str]:
    projection = side.get(field)
    if not isinstance(projection, dict):
        return []
    return [str(x) for x in projection.get("labels", [])]


def component_motion_bounds_from_r55(r55_record: dict[str, Any]) -> dict[str, Any]:
    reextract = r55_record.get("component_bound_interval_reextract") or {}
    candidate = r55_record.get("component_motion_bounds_candidate") or {}
    lower = ((reextract.get("lower_piece") or {}).get("checker_shape_piece") or {})
    upper = ((reextract.get("upper_piece") or {}).get("checker_shape_piece") or {})
    return {
        "lower_piece": lower,
        "upper_piece": upper,
        "rodrigues_terms": candidate.get("rodrigues_terms") or {
            "A_term_rule": "A = u dot (w x (v-o))",
            "B_term_rule": "B = (u dot w)(w dot (v-o)) - u dot (v-o)",
            "bound_rule": "D_pos/D_neg from R35 source lock",
        },
    }


def formula_shape_candidate(
    *,
    r43_record: dict[str, Any],
    attempt: dict[str, Any],
    r55_record: dict[str, Any],
    m_gap: dict[str, Any],
    m_l: dict[str, Any],
    m_u: dict[str, Any],
) -> dict[str, Any]:
    lower = attempt["support_competition_seed_attempt"]["lower"]
    upper = attempt["support_competition_seed_attempt"]["upper"]
    return {
        "axis_nondegeneracy": {
            "axis_expression": "n_ij = (F_i(M_CD)-F_i(M_AB)) x (F_j(M_CD)-F_j(M_AB))",
            "axis_norm_lower_bound": r43_record["axis_norm_square_interval"],
            "axis_norm_source_note": "R43 gives a positive axis-norm-square interval; checker currently only requires a positive interval object here.",
            "common_edge_labels": ["M_AB", "M_CD"],
            "status": "accepted",
        },
        "component_motion_bounds": component_motion_bounds_from_r55(r55_record),
        "exact_gap_formula": {
            "M_L": m_l,
            "M_U": m_u,
            "M_gap": m_gap,
            "source_identity_id": SOURCE_IDENTITY_ID,
        },
        "support_state": {
            "lower_non_support_labels": side_labels(lower, "non_support_projection"),
            "lower_support_labels": side_labels(lower, "support_projection"),
            "status": "accepted",
            "upper_non_support_labels": side_labels(upper, "non_support_projection"),
            "upper_support_labels": side_labels(upper, "support_projection"),
        },
    }


def operation_candidates(
    *,
    r43_path: str | None,
    r59_path: str,
    r55_path: str | None,
    axis_interval: dict[str, Any] | None,
    m_gap: dict[str, Any] | None,
    m_l: dict[str, Any] | None,
    m_u: dict[str, Any] | None,
    finite_pair_ready: bool,
) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    if axis_interval is not None:
        ops.append({
            "backend_id": "b05_common_edge_axis_norm_symbolic_lower_bound_v1",
            "input_refs": [r43_path] if r43_path else [],
            "op_id": "op_axis_cross_product",
            "operation": "symbolic_axis_norm_square_lower_bound",
            "output_interval": axis_interval,
            "proof_rule": "R43 symbolic common-edge axis norm lower bound",
            "ready_for_checker_contract": True,
        })
    if m_l is not None and m_u is not None:
        ops.append({
            "backend_id": "b05_local_taylor_trig_proof_locked_replay_v1",
            "input_refs": [r59_path],
            "op_id": "op_support_finite_extrema",
            "operation": "finite_support_non_support_projection_competition",
            "output_intervals": {"M_L_candidate": m_l, "M_U_candidate": m_u},
            "proof_rule": "R59 local Taylor trig proof-locked support competition intervals",
            "ready_for_checker_contract": finite_pair_ready,
        })
    if m_gap is not None:
        ops.append({
            "backend_id": "b05_local_taylor_trig_proof_locked_replay_v1",
            "input_refs": [r59_path, r55_path] if r55_path else [r59_path],
            "op_id": "op_M_gap",
            "operation": "local_projection_gap_field_candidate",
            "output_interval": m_gap,
            "proof_rule": "R59 proof-locked local replay gap numerator candidate; R60 still audits formula/report-field alignment",
            "ready_for_checker_contract": finite_pair_ready,
        })
    return ops


def build_record(r59_summary: dict[str, Any], r43_by_original: dict[str, dict[str, Any]]) -> dict[str, Any]:
    r59_path = ROOT / r59_summary["object_record"]
    r59 = read_json(r59_path)
    proof_positive = bool(r59.get("proof_locked_positive_seed_ready"))
    chosen_key, attempt = selected_attempt(r59)
    blockers = {
        "accepted_report_promotion_out_of_scope",
        "operation_enclosure_global_replay_audit_missing",
        "tau_outward_error_interval_not_extracted_as_report_field",
    }

    r57_path = ROOT / r59["input_r57_center_support_seed_tightening_budget_record"]
    r57 = read_json(r57_path)
    r56_path = ROOT / r57["input_r56_g0_support_competition_seed_isolation_record"]
    r56 = read_json(r56_path)
    r55_path = ROOT / r56["input_r55_component_bound_margin_skeleton_record"]
    r55 = read_json(r55_path)
    r43 = r43_by_original.get(str(r59["original_report_id"]))

    m_gap = None
    m_l = None
    m_u = None
    lower_vacuous = False
    upper_vacuous = False
    finite_pair_ready = False
    formula_candidate = None
    report_candidate = None
    op_candidates: list[dict[str, Any]] = []

    if not proof_positive or attempt is None:
        if r59.get("object_status") == "local_taylor_trig_replay_blocked_diagnostic_nonpositive_margin":
            object_status = "report_field_extraction_blocked_diagnostic_nonpositive_margin"
            blockers.add("diagnostic_signed_component_margin_nonpositive")
        else:
            object_status = "report_field_extraction_blocked_no_proof_locked_positive_seed"
            blockers.add("proof_locked_positive_local_seed_missing")
    else:
        lower = attempt["support_competition_seed_attempt"]["lower"]
        upper = attempt["support_competition_seed_attempt"]["upper"]
        m_gap = attempt["raw_gap_numerator_interval"]
        lower_vacuous = bool(lower.get("support_competition_vacuous"))
        upper_vacuous = bool(upper.get("support_competition_vacuous"))
        m_l = lower.get("support_competition_interval")
        m_u = upper.get("support_competition_interval")
        finite_pair_ready = bool(lower.get("finite_interval_ready") and upper.get("finite_interval_ready") and m_l and m_u)
        axis_interval = r43["record"]["axis_norm_square_interval"] if r43 else None
        op_candidates = operation_candidates(
            r43_path=r43["record_path"] if r43 else None,
            r59_path=rel(r59_path),
            r55_path=rel(r55_path),
            axis_interval=axis_interval,
            m_gap=m_gap,
            m_l=m_l,
            m_u=m_u,
            finite_pair_ready=finite_pair_ready,
        )
        if not r43:
            blockers.add("axis_nondegeneracy_r43_record_missing")
        if finite_pair_ready and r43:
            formula_candidate = formula_shape_candidate(
                r43_record=r43["record"], attempt=attempt, r55_record=r55, m_gap=m_gap, m_l=m_l, m_u=m_u
            )
            report_candidate = {
                "branch_validity": {"status": "accepted"},
                "common_edge_id": "M_AB-M_CD",
                "endpoint_case": "local_taylor_trig_positive_gap_seed",
                "formula_shape": formula_candidate,
                "gap_interval": m_gap,
                "margin_interval": m_gap,
                "parent_overlay_key": f"{r59['original_report_id']}:partition_{int(r59['partition_index']):02d}:{chosen_key}",
                "projection_axis_or_coordinate": "n_ij = e_i x e_j, oriented by R59 local replay midpoint sign",
                "projection_coordinate_intervals": [
                    attempt["support_competition_seed_attempt"]["lower"]["support_projection"]["max_projection_interval_enclosure"],
                    attempt["support_competition_seed_attempt"]["upper"]["support_projection"]["min_projection_interval_enclosure"],
                ],
            }
            object_status = "report_field_candidate_ready_operation_audit_blocked"
        else:
            object_status = "report_field_candidate_partial_vacuous_or_missing_side_bridge_blocked"
            if lower_vacuous or upper_vacuous:
                blockers.add("vacuous_support_competition_requires_schema_or_semantic_bridge_for_M_L_M_U")
            if not m_l:
                blockers.add("finite_M_L_candidate_missing")
            if not m_u:
                blockers.add("finite_M_U_candidate_missing")
            if not r43:
                blockers.add("formula_shape_axis_nondegeneracy_missing")

    record_rel_dir = Path(str(r59_summary["domain_family"])) / Path(str(r59_summary["original_report"])).stem
    out_path = OUTPUT_ROOT / record_rel_dir / f"partition_{int(r59_summary['partition_index']):02d}_report_field_extraction_audit.json"
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_local_replay_candidate_positive": bool(r59.get("diagnostic_local_replay_candidate_positive")),
        "domain_family": r59_summary["domain_family"],
        "exact_M_gap_M_L_M_U_field_candidate_ready": finite_pair_ready,
        "formula_shape_contract_candidate_ready": bool(formula_candidate),
        "g0_M_gap_field_candidate_ready": bool(proof_positive and m_gap is not None),
        "input_r55_component_bound_margin_skeleton_record": rel(r55_path),
        "input_r56_g0_support_competition_seed_isolation_record": rel(r56_path),
        "input_r57_center_support_seed_tightening_budget_record": rel(r57_path),
        "input_r59_local_taylor_trig_proof_locked_replay_record": rel(r59_path),
        "input_r43_axis_norm_symbolic_lower_bound_record": r43["record_path"] if r43 else None,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": "B05-REPORT-FIELD-EXTRACTION-AUDIT-" + sanitize(r59_summary["original_report_id"]) + f"-PART-{int(r59_summary['partition_index']):02d}",
        "object_status": object_status,
        "operation_enclosure_candidates": op_candidates,
        "operation_enclosure_required_ids_present_as_candidates": {op.get("op_id") for op in op_candidates} >= {"op_axis_cross_product", "op_support_finite_extrema", "op_M_gap"},
        "operation_enclosures_ready": False,
        "original_report": r59_summary["original_report"],
        "original_report_id": r59_summary["original_report_id"],
        "partition_index": r59_summary["partition_index"],
        "per_side_finite_M_L_M_U_candidates_ready": finite_pair_ready,
        "piece_pair": r59_summary["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready": proof_positive,
        "report_field_candidate": report_candidate,
        "selected_positive_shrink_key": chosen_key,
        "source_identity_id": SOURCE_IDENTITY_ID,
        "support_signature": r59_summary["support_signature"],
        "vacuous_support_competition": {"lower": lower_vacuous, "upper": upper_vacuous},
        "tree_id": r59_summary["tree_id"],
    }
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "domain_family": record["domain_family"],
        "exact_M_gap_M_L_M_U_field_candidate_ready": record["exact_M_gap_M_L_M_U_field_candidate_ready"],
        "formula_shape_contract_candidate_ready": record["formula_shape_contract_candidate_ready"],
        "g0_M_gap_field_candidate_ready": record["g0_M_gap_field_candidate_ready"],
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosure_required_ids_present_as_candidates": record["operation_enclosure_required_ids_present_as_candidates"],
        "operation_enclosures_ready": False,
        "original_report": record["original_report"],
        "original_report_id": record["original_report_id"],
        "partition_index": record["partition_index"],
        "per_side_finite_M_L_M_U_candidates_ready": finite_pair_ready,
        "piece_pair": record["piece_pair"],
        "proof_locked_positive_seed_ready": proof_positive,
        "support_signature": record["support_signature"],
        "tree_id": record["tree_id"],
        "vacuous_support_competition": record["vacuous_support_competition"],
    }


def build_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    return {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "exact_M_gap_M_L_M_U_field_candidate_ready_count": sum(1 for r in records if r["exact_M_gap_M_L_M_U_field_candidate_ready"]),
        "formula_shape_contract_candidate_ready_count": sum(1 for r in records if r["formula_shape_contract_candidate_ready"]),
        "g0_M_gap_field_candidate_ready_count": sum(1 for r in records if r["g0_M_gap_field_candidate_ready"]),
        "input_r59_manifest": rel(INPUT_R59_MANIFEST),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosure_required_ids_present_as_candidates_count": sum(1 for r in records if r["operation_enclosure_required_ids_present_as_candidates"]),
        "operation_enclosures_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready_count": sum(1 for r in records if r["proof_locked_positive_seed_ready"]),
        "record_count_by_domain_family": dict(sorted(Counter(record["domain_family"] for record in records).items())),
        "records": records,
        "recommended_next_task": "R61: turn the 6 finite formula-shape candidates into blocked schema-v1 report drafts and run the B05 checker/audit loop, or extend checker semantics for the 4 vacuous-side candidates.",
        "vacuous_support_competition_count": sum(1 for r in records if r["vacuous_support_competition"]["lower"] or r["vacuous_support_competition"]["upper"]),
    }


def main() -> None:
    r43_by_original = index_r43_records()
    r59_records = load_manifest_records(INPUT_R59_MANIFEST)
    records = [build_record(summary, r43_by_original) for summary in r59_records]
    manifest = build_manifest(records)
    write_json_lf(MANIFEST_PATH, manifest)
    print(f"input R59 records: {len(r59_records)}")
    print(f"R60 report-field/audit records emitted: {len(records)}")
    print(f"proof-locked positive seeds consumed: {manifest['proof_locked_positive_seed_ready_count']}")
    print(f"g0/M_gap field candidates ready: {manifest['g0_M_gap_field_candidate_ready_count']}")
    print(f"finite M_gap/M_L/M_U candidates ready: {manifest['exact_M_gap_M_L_M_U_field_candidate_ready_count']}")
    print(f"formula-shape contract candidates ready: {manifest['formula_shape_contract_candidate_ready_count']}")
    print(f"required operation ids present as candidates: {manifest['operation_enclosure_required_ids_present_as_candidates_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest written: {rel(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
