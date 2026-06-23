#!/usr/bin/env python
"""
Build B05 rational seed interval extractor audit records.

R51 consumes the R50 M_gap/M_L/M_U formula-skeleton attempt records.  It tries
one level deeper than R50: each diagnostic float seed statistic is converted to
an exact rational JSON-number hull so the record clearly separates

* diagnostic rational hulls recoverable from current JSON sources; from
* exact/outward-rounded seed intervals still missing for replayable reports.

This backend intentionally does not promote B05 reports.  A JSON-number hull of
a diagnostic float is not an exact geometric seed interval: it is a precise
record of the current source value and a blocker pointing at the required exact
support/gap replay backend.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-RATIONAL-SEED-INTERVAL-EXTRACTOR-AUDIT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_RATIONAL_SEED_INTERVAL_EXTRACTOR_AUDIT"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R50_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_m_gap_m_l_m_u_interval_extractor_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "rational_seed_interval_extractor"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_rational_seed_interval_extractor_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_exact_geometric_seed_interval_claim",
    "no_operation_enclosure_claim",
    "no_formula_shape_real_report_claim",
    "no_theorem_promotion_claim",
]

STAT_TO_SEED = {
    "finite_gap_stats": "g0_center_gap_diagnostic_hull",
    "finite_minimum_stability_margin_stats": "support_competition_combined_diagnostic_hull",
    "finite_signed_component_bound_stats": "signed_component_bound_diagnostic_hull",
    "finite_signed_component_margin_stats": "signed_component_margin_diagnostic_hull",
}


class SourceShapeError(RuntimeError):
    pass


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
    data = read_json(manifest_path)
    records = data.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"records must be a list: {manifest_path}")
    return records


def decimal_fraction(value: Any) -> Fraction | None:
    if value is None:
        return None
    dec = Decimal(str(value))
    return Fraction(dec)


def frac_obj(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_obj(lo: Fraction, hi: Fraction, *, source_expr: str, unit: str) -> dict[str, Any]:
    if hi < lo:
        raise ValueError(f"invalid interval {lo}..{hi}")
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(hi),
        "lo": frac_obj(lo),
        "source_expr": source_expr,
        "unit": unit,
    }


def diagnostic_hull_from_stats(name: str, stats: Any) -> dict[str, Any] | None:
    if not isinstance(stats, dict):
        return None
    lo = decimal_fraction(stats.get("min"))
    hi = decimal_fraction(stats.get("max"))
    if lo is None or hi is None:
        return {
            "available": False,
            "blocker": "diagnostic_stat_min_or_max_missing",
            "source_stat": name,
        }
    return {
        "available": True,
        "count": stats.get("count"),
        "finite_float_semantics": stats.get("finite_float_semantics"),
        "hull_interval": interval_obj(
            lo,
            hi,
            source_expr=f"{name}:json_decimal_rational_hull(min,max)",
            unit="diagnostic_margin",
        ),
        "nonfinite_count": stats.get("nonfinite_count"),
        "ready_for_exact_formula": False,
        "source_stat": name,
        "status": "diagnostic_json_number_rational_hull_not_outward_rounded_exact_seed",
    }


def diagnostic_seed_hulls(record: dict[str, Any]) -> dict[str, Any]:
    skeleton = record.get("exact_gap_formula_skeleton")
    if not isinstance(skeleton, dict):
        return {}
    stats = skeleton.get("diagnostic_float_seed_stats")
    if not isinstance(stats, dict):
        return {}
    out: dict[str, Any] = {}
    for stat_name, seed_name in STAT_TO_SEED.items():
        hull = diagnostic_hull_from_stats(stat_name, stats.get(stat_name))
        if hull is not None:
            out[seed_name] = hull
    return out


def source_audit(record: dict[str, Any]) -> dict[str, Any]:
    join = record.get("margin_source_join")
    if not isinstance(join, dict):
        return {"available": False, "blocker": "margin_source_join_missing"}
    source_path_value = join.get("input_support_source_record")
    source_record: dict[str, Any] | None = None
    if isinstance(source_path_value, str):
        source_path = ROOT / source_path_value
        if source_path.exists():
            source_record = read_json(source_path)
    matched = join.get("matched_support_partition_stats")
    source_ledgers = source_record.get("source_ledgers_scanned") if isinstance(source_record, dict) else None
    blockers = source_record.get("blockers") if isinstance(source_record, dict) else None
    return {
        "available": source_record is not None,
        "input_support_source_backend": join.get("input_support_source_backend"),
        "input_support_source_record": source_path_value,
        "matched_support_partition_count": join.get("matched_support_partition_count"),
        "source_blockers": blockers if isinstance(blockers, list) else [],
        "source_claim_level": source_record.get("claim_level") if isinstance(source_record, dict) else None,
        "source_ledgers_scanned": source_ledgers if isinstance(source_ledgers, list) else [],
        "source_object_status": source_record.get("object_status") if isinstance(source_record, dict) else None,
        "support_partition_count": matched.get("count") if isinstance(matched, dict) else None,
        "support_partition_stats_are_aggregate_only": isinstance(matched, dict),
    }


def non_support_audit(record: dict[str, Any]) -> dict[str, Any]:
    skeleton = record.get("exact_gap_formula_skeleton")
    if not isinstance(skeleton, dict):
        return {"available": False, "missing_non_support_endpoint_coordinate_labels": []}
    req = skeleton.get("non_support_requirements")
    if not isinstance(req, dict):
        return {"available": False, "missing_non_support_endpoint_coordinate_labels": []}
    labels: list[str] = []
    by_role: dict[str, Any] = {}
    for role in ["lower_piece", "upper_piece"]:
        item = req.get(role)
        if not isinstance(item, dict):
            continue
        missing = [str(label) for label in item.get("missing_non_support_endpoint_coordinate_labels") or []]
        labels.extend(missing)
        by_role[role] = {
            "missing_non_support_endpoint_coordinate_labels": missing,
            "non_support_labels": item.get("non_support_labels") or [],
            "piece_id": item.get("piece_id"),
            "support_labels": item.get("support_labels") or [],
        }
    return {
        "available": True,
        "by_role": by_role,
        "missing_non_support_endpoint_coordinate_labels": sorted(set(labels)),
        "ready": False,
        "status": "non_support_endpoint_coordinate_intervals_missing_for_M_L_M_U",
    }


def candidate_signed_component_margin_min(record: dict[str, Any]) -> Fraction | None:
    hulls = diagnostic_seed_hulls(record)
    item = hulls.get("signed_component_margin_diagnostic_hull")
    if not isinstance(item, dict) or not item.get("available"):
        return None
    interval = item.get("hull_interval")
    if not isinstance(interval, dict):
        return None
    lo = interval.get("lo")
    if not isinstance(lo, dict):
        return None
    return Fraction(int(lo["num"]), int(lo["den"]))


def exact_seed_requirements(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "c_L_lower_support_competition_margin_interval": {
            "ready": False,
            "blocker": "per_side_lower_support_competition_replay_interval_missing",
        },
        "c_U_upper_support_competition_margin_interval": {
            "ready": False,
            "blocker": "per_side_upper_support_competition_replay_interval_missing",
        },
        "g0_center_gap_interval": {
            "ready": False,
            "blocker": "center_gap_replay_interval_missing",
        },
        "lower_non_support_component_bounds": {
            "ready": False,
            "blocker": "lower_non_support_endpoint_coordinate_intervals_missing",
        },
        "tau_outward_error_interval": {
            "ready": False,
            "blocker": "tau_outward_error_interval_missing",
        },
        "upper_non_support_component_bounds": {
            "ready": False,
            "blocker": "upper_non_support_endpoint_coordinate_intervals_missing",
        },
    }


def build_seed_record(summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r50_path = ROOT / summary["object_record"]
    r50 = read_json(r50_path)
    skeleton_ready = bool(r50.get("margin_formula_skeleton_ready"))
    hulls = diagnostic_seed_hulls(r50) if skeleton_ready else {}
    hulls_ready = bool(skeleton_ready and hulls)
    signed_min = candidate_signed_component_margin_min(r50) if skeleton_ready else None
    diagnostic_positive = signed_min is not None and signed_min > 0
    diagnostic_nonpositive = signed_min is not None and signed_min <= 0

    blockers = [
        "accepted_report_promotion_out_of_scope",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
        "diagnostic_json_number_hulls_not_outward_rounded_exact_intervals",
        "source_ledgers_store_float_diagnostics_not_fraction_intervals",
        "exact_center_gap_interval_replay_missing",
        "exact_support_competition_margin_replay_missing",
        "per_side_support_competition_margin_split_missing",
        "tau_outward_error_interval_missing",
        "non_support_endpoint_coordinate_intervals_missing_for_M_L_M_U",
    ]
    if not skeleton_ready:
        blockers.append("R50_formula_skeleton_missing")
    if diagnostic_nonpositive:
        blockers.append("diagnostic_signed_component_margin_nonpositive")

    if skeleton_ready and diagnostic_nonpositive:
        object_status = "rational_seed_interval_extractor_blocked_diagnostic_nonpositive_margin"
    elif skeleton_ready:
        object_status = "rational_seed_interval_extractor_diagnostic_hulls_ready_exact_seed_replay_blocked"
    else:
        object_status = "rational_seed_interval_extractor_blocked_formula_skeleton_missing"

    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers)),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "diagnostic_rational_seed_hulls": hulls,
        "diagnostic_rational_seed_hulls_ready": hulls_ready,
        "domain_family": r50.get("domain_family"),
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_seed_intervals_ready": False,
        "formula_shape_contract_ready": False,
        "input_r50_m_gap_m_l_m_u_attempt_record": rel(r50_path),
        "manifest_id": MANIFEST_ID,
        "non_support_endpoint_audit": non_support_audit(r50),
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-RATIONAL-SEED-INTERVAL-{sanitize(r50['original_report_id'])}-"
            f"PART-{int(r50['partition_index']):02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r50.get("original_report"),
        "original_report_id": r50.get("original_report_id"),
        "partition_index": r50.get("partition_index"),
        "piece_pair": r50.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "r35_source_identity_id": SOURCE_IDENTITY_ID,
        "required_exact_seed_intervals": exact_seed_requirements(r50),
        "source_seed_audit": source_audit(r50),
        "support_signature": r50.get("support_signature"),
        "tree_id": r50.get("tree_id"),
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / sanitize(record["original_report_id"])
        / f"partition_{int(record['partition_index']):02d}_rational_seed_interval_audit.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "diagnostic_rational_seed_hulls_ready": hulls_ready,
        "domain_family": record["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_seed_intervals_ready": False,
        "formula_shape_contract_ready": False,
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": record["original_report"],
        "original_report_id": record["original_report_id"],
        "partition_index": record["partition_index"],
        "piece_pair": record["piece_pair"],
        "support_signature": record["support_signature"],
        "tree_id": record["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r50-manifest", default=DEFAULT_R50_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r50_manifest = ROOT / args.r50_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    records = [build_seed_record(summary, out_dir) for summary in load_manifest_records(r50_manifest)]
    status_counts = Counter(item["object_status"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)
    blocker_counts = Counter()
    for item in records:
        record = read_json(ROOT / item["object_record"])
        blocker_counts.update(record["blockers"])

    hull_ready = sum(1 for item in records if item["diagnostic_rational_seed_hulls_ready"])
    exact_seed_ready = sum(1 for item in records if item["exact_seed_intervals_ready"])
    exact_margin_ready = sum(1 for item in records if item["exact_M_gap_M_L_M_U_ready"])
    diagnostic_positive = sum(
        1 for item in records
        if item["diagnostic_rational_seed_hulls_ready"]
        and item["diagnostic_positive_signed_component_candidate"]
    )
    diagnostic_nonpositive = sum(
        1 for item in records
        if item["diagnostic_rational_seed_hulls_ready"]
        and not item["diagnostic_positive_signed_component_candidate"]
    )
    manifest = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_nonpositive_signed_component_candidate_count": diagnostic_nonpositive,
        "diagnostic_positive_signed_component_candidate_count": diagnostic_positive,
        "diagnostic_rational_seed_hulls_ready_count": hull_ready,
        "exact_M_gap_M_L_M_U_ready_count": exact_margin_ready,
        "exact_seed_intervals_ready_count": exact_seed_ready,
        "formula_shape_contract_ready_count": 0,
        "input_r50_manifest": rel(r50_manifest),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R52: build exact support/gap seed replay from source ledgers so g0, "
            "c_L, c_U, tau, and non-support component terms are outward-rounded "
            "geometric intervals rather than diagnostic JSON-number hulls."
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R50 records: {len(records)}")
    print(f"rational seed audit records emitted: {manifest['object_record_count']}")
    print(f"diagnostic rational seed hulls ready: {hull_ready}")
    print(f"diagnostic positive signed-component candidates: {diagnostic_positive}")
    print(f"diagnostic nonpositive signed-component candidates: {diagnostic_nonpositive}")
    print(f"exact seed intervals ready: {exact_seed_ready}")
    print(f"exact M_gap/M_L/M_U ready: {exact_margin_ready}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())