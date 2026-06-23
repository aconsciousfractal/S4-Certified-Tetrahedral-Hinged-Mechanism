#!/usr/bin/env python
"""
Build B05 geometric seed arithmetic operand records.

R53 consumes the R52 exact-seed replay source-audit records.  It does not copy
diagnostic ledger min/max values into exact seeds.  Instead it joins the exact
geometric operands that already exist in the backend chain:

* R42 common-edge endpoint/vector/cross-product interval objects;
* R43 symbolic positive common-edge axis-norm lower bound;
* R49/R50 support component-bound interval inputs for M_gap.

The backend records which operands are now available for an exact seed replay
and which terms remain blocked.  In particular, g0, c_L, c_U, tau, and
non-support component terms are still not emitted as outward-rounded geometric
seed intervals.
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
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-GEOMETRIC-SEED-ARITHMETIC-OPERANDS-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_GEOMETRIC_SEED_ARITHMETIC_OPERANDS"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R52_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_exact_seed_replay_source_audit_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "geometric_seed_arithmetic_backend"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_geometric_seed_arithmetic_backend_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_g0_center_gap_interval_claim",
    "no_exact_c_L_c_U_support_competition_interval_claim",
    "no_tau_outward_error_interval_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
    "no_formula_shape_real_report_claim",
    "no_theorem_promotion_claim",
]

COMMON_EDGE_LABELS = ["M_AB", "M_CD"]


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


def sanitize(value: Any) -> str:
    text = str(value)
    out: list[str] = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def load_manifest_records(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"records must be a list: {manifest_path}")
    return records


def frac_obj(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_frac(interval: dict[str, Any]) -> tuple[Fraction, Fraction]:
    return (
        Fraction(int(interval["lo"]["num"]), int(interval["lo"]["den"])),
        Fraction(int(interval["hi"]["num"]), int(interval["hi"]["den"])),
    )


def interval_width(interval: dict[str, Any]) -> Fraction:
    lo, hi = interval_frac(interval)
    return hi - lo


def vector_coordinate_widths(vector: dict[str, Any]) -> list[dict[str, Any]]:
    coords = vector.get("coordinates") or []
    order = vector.get("coordinate_order") or []
    widths = []
    for axis, coord in zip(order, coords):
        width = abs(interval_width(coord))
        widths.append({
            "axis": str(axis),
            "interval_width": frac_obj(width),
            "source_expr": coord.get("source_expr"),
        })
    return widths


def endpoint_coverage(r42_record: dict[str, Any], piece_id: str, labels: list[str]) -> dict[str, Any]:
    intervals = r42_record.get("endpoint_coordinate_intervals")
    piece = intervals.get(piece_id) if isinstance(intervals, dict) else None
    endpoints = piece.get("endpoints") if isinstance(piece, dict) else None
    endpoints = endpoints if isinstance(endpoints, dict) else {}
    missing = [label for label in labels if label not in endpoints]
    return {
        "available": not missing and bool(labels),
        "available_labels": [label for label in labels if label in endpoints],
        "missing_labels": missing,
        "piece_id": piece_id,
        "requested_labels": labels,
    }


def common_edge_operand_package(
    r42_record: dict[str, Any],
    r43_record: dict[str, Any],
    lower_piece: str,
    upper_piece: str,
) -> dict[str, Any]:
    edge_vectors = r42_record.get("edge_vector_intervals")
    axis_cross = r42_record.get("axis_cross_product_interval")
    axis_norm_interval = r43_record.get("axis_norm_square_interval")
    lower_edge = edge_vectors.get(lower_piece) if isinstance(edge_vectors, dict) else None
    upper_edge = edge_vectors.get(upper_piece) if isinstance(edge_vectors, dict) else None
    axis_ready = (
        isinstance(axis_cross, dict)
        and isinstance(axis_norm_interval, dict)
        and bool(r43_record.get("positive_axis_norm_lower_bound_ready"))
    )
    package = {
        "axis_cross_product_interval": axis_cross,
        "axis_cross_product_interval_coordinate_widths": (
            vector_coordinate_widths(axis_cross) if isinstance(axis_cross, dict) else []
        ),
        "axis_nondegeneracy_source": {
            "axis_norm_square_interval": axis_norm_interval,
            "positive_axis_norm_lower_bound_ready": bool(
                r43_record.get("positive_axis_norm_lower_bound_ready")
            ),
            "source_claim_level": r43_record.get("claim_level"),
            "source_object_status": r43_record.get("object_status"),
        },
        "axis_operand_ready_for_future_normalization": axis_ready,
        "lower_common_edge_vector_interval": lower_edge,
        "lower_common_edge_vector_interval_coordinate_widths": (
            vector_coordinate_widths(lower_edge) if isinstance(lower_edge, dict) else []
        ),
        "upper_common_edge_vector_interval": upper_edge,
        "upper_common_edge_vector_interval_coordinate_widths": (
            vector_coordinate_widths(upper_edge) if isinstance(upper_edge, dict) else []
        ),
    }
    return package


def piece_ids_from_signature(signature: str) -> tuple[str | None, str | None]:
    try:
        lower_part, upper_part = signature.split("|")
        lower_piece = lower_part.split("=")[1].split("[")[0]
        upper_piece = upper_part.split("=")[1].split("[")[0]
        return lower_piece, upper_piece
    except Exception:
        return None, None


def load_chain(r52_record: dict[str, Any]) -> dict[str, Any]:
    r50_path = ROOT / r52_record["input_r50_m_gap_m_l_m_u_attempt_record"]
    r50 = read_json(r50_path)
    r49_path_value = r50.get("input_r49_component_bound_interval_record")
    if not isinstance(r49_path_value, str):
        return {"r50_path": r50_path, "r50": r50}
    r49_path = ROOT / r49_path_value
    r49 = read_json(r49_path)
    r48_path = ROOT / r49["input_r48_component_motion_bound_object_record"]
    r48 = read_json(r48_path)
    r42_path = ROOT / r48["input_r42_rodrigues_interval_record"]
    r43_path = ROOT / r48["input_r43_axis_norm_record"]
    return {
        "r42": read_json(r42_path),
        "r42_path": r42_path,
        "r43": read_json(r43_path),
        "r43_path": r43_path,
        "r48": r48,
        "r48_path": r48_path,
        "r49": r49,
        "r49_path": r49_path,
        "r50": r50,
        "r50_path": r50_path,
    }


def support_component_inputs(skeleton: dict[str, Any]) -> dict[str, Any]:
    inputs = skeleton.get("component_interval_inputs")
    if not isinstance(inputs, dict):
        return {"available": False, "blocker": "component_interval_inputs_missing"}
    lower = inputs.get("lower_piece")
    upper = inputs.get("upper_piece")
    ready = isinstance(lower, dict) and isinstance(upper, dict)
    return {
        "available": ready,
        "blocker": None if ready else "support_component_interval_inputs_missing",
        "lower_piece": lower,
        "upper_piece": upper,
        "rodrigues_terms": inputs.get("rodrigues_terms"),
    }


def non_support_status(skeleton: dict[str, Any]) -> dict[str, Any]:
    requirements = skeleton.get("non_support_requirements")
    missing: list[str] = []
    by_role: dict[str, Any] = {}
    if isinstance(requirements, dict):
        for role in ["lower_piece", "upper_piece"]:
            item = requirements.get(role)
            if not isinstance(item, dict):
                continue
            role_missing = [str(label) for label in item.get("missing_non_support_endpoint_coordinate_labels") or []]
            missing.extend(role_missing)
            by_role[role] = {
                "missing_non_support_endpoint_coordinate_labels": role_missing,
                "non_support_labels": item.get("non_support_labels") or [],
                "piece_id": item.get("piece_id"),
                "support_labels": item.get("support_labels") or [],
            }
    return {
        "available": bool(requirements),
        "by_role": by_role,
        "missing_non_support_endpoint_coordinate_labels": sorted(set(missing)),
        "non_support_endpoint_coordinate_intervals_ready": not missing and bool(requirements),
    }


def build_record(r52_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r52_path = ROOT / r52_summary["object_record"]
    r52 = read_json(r52_path)
    chain = load_chain(r52)
    r50 = chain["r50"]
    skeleton = r50.get("exact_gap_formula_skeleton")
    formula_ready = isinstance(skeleton, dict) and bool(r52.get("diagnostic_rational_seed_hulls_ready"))
    signature = str(r52_summary.get("support_signature") or r52.get("support_signature"))
    lower_piece, upper_piece = piece_ids_from_signature(signature)
    diagnostic_positive = bool(r52_summary.get("diagnostic_positive_signed_component_candidate"))

    blockers = {
        "accepted_report_promotion_out_of_scope",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
    }
    operand_package: dict[str, Any] = {
        "available": False,
        "blocker": "formula_skeleton_or_r52_seed_hulls_missing",
    }
    support_endpoint_ready = False
    axis_operand_ready = False
    support_component_ready = False
    non_support_ready = False

    if formula_ready and lower_piece and upper_piece and all(k in chain for k in ["r42", "r43"]):
        r42 = chain["r42"]
        r43 = chain["r43"]
        lower_support = endpoint_coverage(r42, lower_piece, COMMON_EDGE_LABELS)
        upper_support = endpoint_coverage(r42, upper_piece, COMMON_EDGE_LABELS)
        support_endpoint_ready = lower_support["available"] and upper_support["available"]
        common_edge = common_edge_operand_package(r42, r43, lower_piece, upper_piece)
        axis_operand_ready = bool(common_edge["axis_operand_ready_for_future_normalization"])
        support_component = support_component_inputs(skeleton)
        support_component_ready = bool(support_component["available"])
        non_support = non_support_status(skeleton)
        non_support_ready = bool(non_support["non_support_endpoint_coordinate_intervals_ready"])
        operand_package = {
            "available": True,
            "axis_and_common_edge_operands": common_edge,
            "input_r42_rodrigues_interval_record": rel(chain["r42_path"]),
            "input_r43_axis_norm_record": rel(chain["r43_path"]),
            "input_r49_component_bound_interval_record": rel(chain["r49_path"]),
            "lower_support_endpoint_coverage": lower_support,
            "non_support_endpoint_coverage": non_support,
            "source_identity_id": SOURCE_IDENTITY_ID,
            "support_component_interval_inputs": support_component,
            "upper_support_endpoint_coverage": upper_support,
        }
        if not support_endpoint_ready:
            blockers.add("support_endpoint_coordinate_intervals_missing")
        if not axis_operand_ready:
            blockers.add("axis_cross_product_or_axis_lower_bound_missing")
        if not support_component_ready:
            blockers.add("support_component_interval_inputs_missing")
        if not non_support_ready:
            blockers.add("non_support_endpoint_coordinate_intervals_missing_for_M_L_M_U")
    else:
        blockers.add("formula_skeleton_or_r52_seed_hulls_missing")

    blockers.update({
        "g0_center_gap_requires_center_separator_projection_replay",
        "per_side_c_L_c_U_support_competition_replay_missing",
        "tau_outward_error_interval_missing",
        "exact_seed_intervals_not_emitted",
        "positive_M_gap_M_L_M_U_not_extracted",
    })
    if not diagnostic_positive:
        blockers.add("diagnostic_signed_component_margin_nonpositive_or_missing")

    if not formula_ready:
        object_status = "geometric_seed_arithmetic_blocked_formula_skeleton_missing"
    elif not diagnostic_positive:
        object_status = "geometric_seed_arithmetic_blocked_diagnostic_nonpositive_margin"
    elif support_endpoint_ready and axis_operand_ready and support_component_ready:
        object_status = "geometric_seed_arithmetic_operands_ready_seed_intervals_blocked"
    else:
        object_status = "geometric_seed_arithmetic_operands_incomplete"

    original_id = str(r52_summary["original_report_id"])
    partition_index = int(r52_summary["partition_index"])
    domain = str(r52_summary["domain_family"])
    record_dir = out_dir / sanitize(domain) / sanitize(original_id)
    record_path = record_dir / f"partition_{partition_index:02d}_geometric_seed_arithmetic.json"
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "common_edge_axis_operand_ready": axis_operand_ready,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_seed_intervals_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": False,
        "geometric_seed_arithmetic_operands": operand_package,
        "input_r50_m_gap_m_l_m_u_attempt_record": rel(chain["r50_path"]),
        "input_r52_exact_seed_replay_source_audit_record": rel(r52_path),
        "manifest_id": MANIFEST_ID,
        "non_support_endpoint_coordinate_intervals_ready": non_support_ready,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"S4-CL5-B05-GEOMETRIC-SEED-ARITHMETIC-"
            f"{sanitize(original_id).upper()}-PARTITION-{partition_index:02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r52_summary.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r52_summary.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "support_component_interval_inputs_ready": support_component_ready,
        "support_endpoint_coordinate_intervals_ready": support_endpoint_ready,
        "support_signature": signature,
        "tau_outward_error_interval_ready": False,
        "tree_id": r52_summary.get("tree_id"),
    }
    write_json_lf(record_path, record)
    return {
        "accepted_real_b05_report": False,
        "common_edge_axis_operand_ready": axis_operand_ready,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_seed_intervals_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": False,
        "non_support_endpoint_coordinate_intervals_ready": non_support_ready,
        "object_record": rel(record_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r52_summary.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r52_summary.get("piece_pair"),
        "support_component_interval_inputs_ready": support_component_ready,
        "support_endpoint_coordinate_intervals_ready": support_endpoint_ready,
        "support_signature": signature,
        "tau_outward_error_interval_ready": False,
        "tree_id": r52_summary.get("tree_id"),
    }


def build_manifest(records: list[dict[str, Any]], r52_manifest: Path) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    domain_counts = Counter(record["domain_family"] for record in records)
    return {
        "accepted_real_b05_report_count": sum(1 for r in records if r["accepted_real_b05_report"]),
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "common_edge_axis_operand_ready_count": sum(1 for r in records if r["common_edge_axis_operand_ready"]),
        "diagnostic_positive_signed_component_candidate_count": sum(
            1 for r in records if r["diagnostic_positive_signed_component_candidate"]
        ),
        "exact_M_gap_M_L_M_U_ready_count": sum(1 for r in records if r["exact_M_gap_M_L_M_U_ready"]),
        "exact_seed_intervals_ready_count": sum(1 for r in records if r["exact_seed_intervals_ready"]),
        "formula_shape_contract_ready_count": sum(1 for r in records if r["formula_shape_contract_ready"]),
        "g0_center_gap_interval_ready_count": sum(1 for r in records if r["g0_center_gap_interval_ready"]),
        "input_r52_manifest": rel(r52_manifest),
        "manifest_id": MANIFEST_ID,
        "non_support_endpoint_coordinate_intervals_ready_count": sum(
            1 for r in records if r["non_support_endpoint_coordinate_intervals_ready"]
        ),
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": sum(1 for r in records if r["operation_enclosures_ready"]),
        "per_side_support_competition_intervals_ready_count": sum(
            1 for r in records if r["per_side_support_competition_intervals_ready"]
        ),
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": (
            "Use the R53 operand records to implement center-separator projection "
            "replay for g0 and endpoint propagation for A/B/C/D non-support labels."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "support_component_interval_inputs_ready_count": sum(
            1 for r in records if r["support_component_interval_inputs_ready"]
        ),
        "support_endpoint_coordinate_intervals_ready_count": sum(
            1 for r in records if r["support_endpoint_coordinate_intervals_ready"]
        ),
        "tau_outward_error_interval_ready_count": sum(
            1 for r in records if r["tau_outward_error_interval_ready"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r52-manifest", type=Path, default=DEFAULT_R52_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    r52_manifest = ROOT / args.r52_manifest
    out_dir = ROOT / args.out_dir
    records = [build_record(record, out_dir) for record in load_manifest_records(r52_manifest)]
    manifest = build_manifest(records, r52_manifest)
    write_json_lf(ROOT / args.manifest, manifest)

    print(f"input R52 records: {len(records)}")
    print(f"geometric seed arithmetic records emitted: {len(records)}")
    print(f"support endpoint coordinate intervals ready: {manifest['support_endpoint_coordinate_intervals_ready_count']}")
    print(f"common-edge axis operands ready: {manifest['common_edge_axis_operand_ready_count']}")
    print(f"support component interval inputs ready: {manifest['support_component_interval_inputs_ready_count']}")
    print(f"g0 center gap intervals ready: {manifest['g0_center_gap_interval_ready_count']}")
    print(f"per-side support competition intervals ready: {manifest['per_side_support_competition_intervals_ready_count']}")
    print(f"non-support endpoint coordinate intervals ready: {manifest['non_support_endpoint_coordinate_intervals_ready_count']}")
    print(f"tau outward error intervals ready: {manifest['tau_outward_error_interval_ready_count']}")
    print(f"exact seed intervals ready: {manifest['exact_seed_intervals_ready_count']}")
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(ROOT / args.manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
