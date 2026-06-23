#!/usr/bin/env python
"""
Build B05 exact-seed replay source-audit records.

R52 consumes the R51 rational seed interval audit records and checks whether
their diagnostic seed hulls can be traced back to the underlying R45/R46 source
partition inventories and, where available, raw source-ledger entries.

This backend intentionally does not promote B05 reports.  Matching raw source
entries still carry finite diagnostic float semantics, not exact geometric
seed intervals and not outward-rounded arithmetic enclosures.  The value of
this layer is to make the next blocker precise: the source seeds are traceable,
but a real exact/outward-rounded replay backend is still missing.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-EXACT-SEED-REPLAY-SOURCE-AUDIT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_EXACT_SEED_REPLAY_SOURCE_AUDIT"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R51_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_rational_seed_interval_extractor_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "exact_seed_replay_source_audit"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_exact_seed_replay_source_audit_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_geometric_seed_interval_claim",
    "no_outward_rounded_seed_replay_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
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

RAW_FIELD_TO_STAT = {
    "gap": "finite_gap_stats",
    "minimum_stability_margin": "finite_minimum_stability_margin_stats",
    "signed_component_bound": "finite_signed_component_bound_stats",
    "signed_component_margin": "finite_signed_component_margin_stats",
}


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
    if isinstance(value, float) and not math.isfinite(value):
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


def diagnostic_seed_hulls_from_stats(stats: Any) -> dict[str, Any]:
    if not isinstance(stats, dict):
        return {}
    out: dict[str, Any] = {}
    for stat_name, seed_name in STAT_TO_SEED.items():
        hull = diagnostic_hull_from_stats(stat_name, stats.get(stat_name))
        if hull is not None:
            out[seed_name] = hull
    return out


def json_stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def source_partition_stats_from_r50(r50_record: dict[str, Any]) -> dict[str, Any] | None:
    join = r50_record.get("margin_source_join")
    if not isinstance(join, dict):
        return None
    stats = join.get("matched_support_partition_stats")
    return stats if isinstance(stats, dict) else None


def source_record_from_r50(r50_record: dict[str, Any]) -> dict[str, Any] | None:
    join = r50_record.get("margin_source_join")
    if not isinstance(join, dict):
        return None
    value = join.get("input_support_source_record")
    if not isinstance(value, str):
        return None
    path = ROOT / value
    if not path.exists():
        return None
    return read_json(path)


def source_record_path_from_r50(r50_record: dict[str, Any]) -> str | None:
    join = r50_record.get("margin_source_join")
    if not isinstance(join, dict):
        return None
    value = join.get("input_support_source_record")
    return value if isinstance(value, str) else None


def is_finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def raw_entries_with_signature(data: Any, signature: str) -> list[tuple[tuple[Any, ...], dict[str, Any]]]:
    found: list[tuple[tuple[Any, ...], dict[str, Any]]] = []
    stack: list[tuple[tuple[Any, ...], Any]] = [((), data)]
    while stack:
        path, item = stack.pop()
        if isinstance(item, dict):
            if item.get("support_signature") == signature:
                found.append((path, item))
            for key, value in item.items():
                stack.append((path + (key,), value))
        elif isinstance(item, list):
            for idx, value in enumerate(item):
                stack.append((path + (idx,), value))
    return found


def bucket_key(path: tuple[Any, ...]) -> str:
    if len(path) >= 2:
        prefix = path[:2]
    else:
        prefix = path
    return "/".join(str(part) for part in prefix)


def finite_stats(values: list[Any]) -> dict[str, Any]:
    finite = [value for value in values if is_finite_number(value)]
    if not finite:
        return {
            "count": 0,
            "finite_float_semantics": "no_finite_values",
            "max": None,
            "min": None,
            "nonfinite_count": len(values),
        }
    return {
        "count": len(finite),
        "finite_float_semantics": "diagnostic_float_not_fraction_interval",
        "max": max(finite),
        "min": min(finite),
        "nonfinite_count": len(values) - len(finite),
    }


def raw_bucket_stats(entries: list[tuple[tuple[Any, ...], dict[str, Any]]]) -> dict[str, Any]:
    stats: dict[str, Any] = {}
    for raw_field, stat_name in RAW_FIELD_TO_STAT.items():
        values = [entry.get(raw_field) for _, entry in entries if raw_field in entry]
        if values:
            stats[stat_name] = finite_stats(values)
    return stats


def stat_minmax_fraction_pair(stats: dict[str, Any]) -> tuple[Fraction | None, Fraction | None]:
    return decimal_fraction(stats.get("min")), decimal_fraction(stats.get("max"))


def stats_match_expected(raw_stats: dict[str, Any], expected: dict[str, Any]) -> bool:
    for stat_name, expected_stats in expected.items():
        if stat_name not in STAT_TO_SEED:
            continue
        if not isinstance(expected_stats, dict):
            continue
        if expected_stats.get("min") is None or expected_stats.get("max") is None:
            continue
        candidate = raw_stats.get(stat_name)
        if not isinstance(candidate, dict):
            return False
        if candidate.get("count") != expected_stats.get("count"):
            return False
        if stat_minmax_fraction_pair(candidate) != stat_minmax_fraction_pair(expected_stats):
            return False
    return True


def raw_ledger_trace(signature: str, source_ledgers: list[str], expected_stats: dict[str, Any] | None) -> dict[str, Any]:
    buckets: list[dict[str, Any]] = []
    total_entries = 0
    exact_match = False
    for ledger_value in source_ledgers:
        ledger_path = ROOT / ledger_value
        if not ledger_path.exists():
            buckets.append({
                "source_ledger": ledger_value,
                "status": "source_ledger_missing",
            })
            continue
        data = read_json(ledger_path)
        entries = raw_entries_with_signature(data, signature)
        total_entries += len(entries)
        grouped: dict[str, list[tuple[tuple[Any, ...], dict[str, Any]]]] = defaultdict(list)
        for path, entry in entries:
            grouped[bucket_key(path)].append((path, entry))
        for key, group_entries in sorted(grouped.items(), key=lambda item: item[0]):
            stats = raw_bucket_stats(group_entries)
            match = bool(expected_stats) and stats_match_expected(stats, expected_stats)
            exact_match = exact_match or match
            samples = []
            for raw_path, entry in group_entries[:3]:
                sample: dict[str, Any] = {
                    "path": "/".join(str(part) for part in raw_path),
                }
                for field in [
                    "gap",
                    "minimum_stability_margin",
                    "signed_component_bound",
                    "signed_component_margin",
                    "lower_expanded_support_labels",
                    "upper_expanded_support_labels",
                ]:
                    if field in entry:
                        sample[field] = entry[field]
                samples.append(sample)
            buckets.append({
                "bucket_path_prefix": key,
                "raw_matching_support_signature_count": len(group_entries),
                "source_ledger": ledger_value,
                "stats_match_expected_partition_stats": match,
                "finite_stats": stats,
                "samples": samples,
            })
    matched = [bucket for bucket in buckets if bucket.get("stats_match_expected_partition_stats")]
    return {
        "available": bool(total_entries),
        "expected_partition_stats_available": isinstance(expected_stats, dict),
        "exact_partition_bucket_matched": exact_match,
        "matching_bucket_count": len(matched),
        "raw_matching_support_signature_total_count": total_entries,
        "source_values_semantics": "diagnostic_float_not_fraction_interval",
        "status": (
            "raw_source_partition_bucket_matched_float_diagnostic_only"
            if exact_match
            else "raw_source_partition_bucket_not_matched_or_missing"
        ),
        "buckets": buckets,
    }


def support_inventory_trace(
    r50_record: dict[str, Any],
    source_record: dict[str, Any] | None,
    signature: str,
    expected_stats: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(source_record, dict):
        return {"available": False, "blocker": "input_support_source_record_missing"}
    inventory = source_record.get("support_partition_inventory")
    if not isinstance(inventory, list):
        return {"available": False, "blocker": "support_partition_inventory_missing"}
    matches = [
        item for item in inventory
        if isinstance(item, dict)
        and str(item.get("signature") or item.get("support_signature")) == signature
    ]
    stats_match = False
    if expected_stats is not None:
        expected_hulls = diagnostic_seed_hulls_from_stats(expected_stats)
        for item in matches:
            item_hulls = diagnostic_seed_hulls_from_stats(item)
            if json_stable(item_hulls) == json_stable(expected_hulls):
                stats_match = True
                break
    return {
        "available": True,
        "input_support_source_backend": (
            r50_record.get("margin_source_join", {}).get("input_support_source_backend")
            if isinstance(r50_record.get("margin_source_join"), dict)
            else None
        ),
        "input_support_source_record": source_record_path_from_r50(r50_record),
        "matched_inventory_item_count": len(matches),
        "source_claim_level": source_record.get("claim_level"),
        "source_object_status": source_record.get("object_status"),
        "source_partition_stats_match_r50": stats_match,
        "matched_inventory_items": matches[:3],
    }


def signed_component_margin_min_from_hulls(hulls: dict[str, Any]) -> Fraction | None:
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


def default_required_exact_seed_intervals(r51_record: dict[str, Any]) -> dict[str, Any]:
    value = r51_record.get("required_exact_seed_intervals")
    if isinstance(value, dict):
        return value
    return {
        "c_L_lower_support_competition_margin_interval": {
            "blocker": "per_side_lower_support_competition_replay_interval_missing",
            "ready": False,
        },
        "c_U_upper_support_competition_margin_interval": {
            "blocker": "per_side_upper_support_competition_replay_interval_missing",
            "ready": False,
        },
        "g0_center_gap_interval": {
            "blocker": "center_gap_replay_interval_missing",
            "ready": False,
        },
        "lower_non_support_component_bounds": {
            "blocker": "lower_non_support_endpoint_coordinate_intervals_missing",
            "ready": False,
        },
        "tau_outward_error_interval": {
            "blocker": "tau_outward_error_interval_missing",
            "ready": False,
        },
        "upper_non_support_component_bounds": {
            "blocker": "upper_non_support_endpoint_coordinate_intervals_missing",
            "ready": False,
        },
    }


def build_audit_record(r51_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r51_path = ROOT / r51_summary["object_record"]
    r51_record = read_json(r51_path)
    r50_path = ROOT / r51_record["input_r50_m_gap_m_l_m_u_attempt_record"]
    r50_record = read_json(r50_path)
    source_record = source_record_from_r50(r50_record)
    signature = str(r51_summary.get("support_signature") or r51_record.get("support_signature"))
    formula_ready = bool(r51_summary.get("diagnostic_rational_seed_hulls_ready"))
    expected_stats = source_partition_stats_from_r50(r50_record) if formula_ready else None
    source_hulls = diagnostic_seed_hulls_from_stats(expected_stats) if formula_ready else {}
    r51_hulls = r51_record.get("diagnostic_rational_seed_hulls")
    if not isinstance(r51_hulls, dict):
        r51_hulls = {}
    hulls_match = formula_ready and json_stable(r51_hulls) == json_stable(source_hulls)

    source_seed_audit = r51_record.get("source_seed_audit")
    if not isinstance(source_seed_audit, dict):
        source_seed_audit = {}
    source_ledgers = source_seed_audit.get("source_ledgers_scanned")
    if not isinstance(source_ledgers, list):
        source_ledgers = []

    inventory_trace = (
        support_inventory_trace(r50_record, source_record, signature, expected_stats)
        if formula_ready
        else {
            "available": False,
            "blocker": "formula_skeleton_or_r51_diagnostic_hulls_missing",
            "not_attempted": True,
        }
    )
    raw_trace = (
        raw_ledger_trace(signature, source_ledgers, expected_stats)
        if source_ledgers and r51_summary.get("diagnostic_rational_seed_hulls_ready")
        else {
            "available": False,
            "exact_partition_bucket_matched": False,
            "raw_matching_support_signature_total_count": 0,
            "source_values_semantics": "diagnostic_float_not_fraction_interval",
            "status": "raw_source_ledger_trace_not_available_for_record",
            "buckets": [],
        }
    )

    signed_min = signed_component_margin_min_from_hulls(source_hulls)
    diagnostic_positive = signed_min is not None and signed_min > 0
    raw_bucket_matched = bool(raw_trace.get("exact_partition_bucket_matched"))
    inventory_matched = bool(inventory_trace.get("source_partition_stats_match_r50"))

    blockers = set(str(item) for item in r51_record.get("blockers") or [])
    blockers.update({
        "accepted_report_promotion_out_of_scope",
        "exact_geometric_seed_interval_replay_missing",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
        "outward_rounded_seed_arithmetic_backend_missing",
        "source_values_are_finite_diagnostic_floats_not_fraction_intervals",
    })
    if not formula_ready:
        blockers.add("formula_skeleton_or_diagnostic_hulls_missing")
    if formula_ready and not raw_bucket_matched:
        blockers.add("raw_source_partition_bucket_not_matched_or_missing")
    if raw_bucket_matched:
        blockers.add("raw_source_partition_bucket_matched_but_float_diagnostic_only")
    if not source_ledgers:
        blockers.add("raw_source_ledgers_not_available_for_reconstructed_or_blocked_seed")
    if not diagnostic_positive:
        blockers.add("diagnostic_signed_component_margin_nonpositive_or_missing")
    if not inventory_matched:
        blockers.add("source_partition_inventory_not_matched_to_r50_stats")

    if not formula_ready:
        object_status = "exact_seed_replay_source_audit_blocked_formula_skeleton_missing"
    elif not diagnostic_positive:
        object_status = "exact_seed_replay_source_audit_blocked_diagnostic_nonpositive_margin"
    elif raw_bucket_matched:
        object_status = "exact_seed_replay_source_audit_raw_trace_matched_float_only_exact_replay_blocked"
    elif inventory_matched:
        object_status = "exact_seed_replay_source_audit_partition_inventory_matched_float_only_exact_replay_blocked"
    else:
        object_status = "exact_seed_replay_source_audit_blocked_source_trace_unmatched"

    original_id = str(r51_summary["original_report_id"])
    partition_index = int(r51_summary["partition_index"])
    domain = str(r51_summary["domain_family"])
    record_dir = out_dir / sanitize(domain) / sanitize(original_id)
    record_path = record_dir / f"partition_{partition_index:02d}_exact_seed_replay_source_audit.json"

    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "diagnostic_rational_seed_hulls_from_source_partition_stats": source_hulls,
        "diagnostic_rational_seed_hulls_match_r51": hulls_match,
        "diagnostic_rational_seed_hulls_ready": bool(source_hulls),
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_seed_intervals_ready": False,
        "formula_shape_contract_ready": False,
        "input_r50_m_gap_m_l_m_u_attempt_record": rel(r50_path),
        "input_r51_rational_seed_audit_record": rel(r51_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"S4-CL5-B05-EXACT-SEED-REPLAY-SOURCE-AUDIT-"
            f"{sanitize(original_id).upper()}-PARTITION-{partition_index:02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r51_summary.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "piece_pair": r51_summary.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "r35_source_identity_id": SOURCE_IDENTITY_ID,
        "raw_source_partition_bucket_matched": raw_bucket_matched,
        "required_exact_seed_intervals": default_required_exact_seed_intervals(r51_record),
        "source_partition_inventory_matched": inventory_matched,
        "source_replay_audit": {
            "current_promotion_decision": "blocked",
            "reason": (
                "source seeds are traceable but finite diagnostic floats; exact "
                "outward-rounded geometric replay is still missing"
            ),
            "r45_or_r46_source_partition_inventory_trace": inventory_trace,
            "r51_hulls_match_source_partition_hulls": hulls_match,
            "raw_source_ledger_trace": raw_trace,
        },
        "support_signature": signature,
        "tree_id": r51_summary.get("tree_id"),
    }
    write_json_lf(record_path, record)
    summary = {
        "accepted_real_b05_report": False,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "diagnostic_rational_seed_hulls_match_r51": hulls_match,
        "diagnostic_rational_seed_hulls_ready": bool(source_hulls),
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_seed_intervals_ready": False,
        "formula_shape_contract_ready": False,
        "object_record": rel(record_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r51_summary.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "piece_pair": r51_summary.get("piece_pair"),
        "raw_source_partition_bucket_matched": raw_bucket_matched,
        "source_partition_inventory_matched": inventory_matched,
        "support_signature": signature,
        "tree_id": r51_summary.get("tree_id"),
    }
    return summary


def build_manifest(records: list[dict[str, Any]], r51_manifest: Path) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    domain_counts = Counter(record["domain_family"] for record in records)
    return {
        "accepted_real_b05_report_count": sum(1 for r in records if r["accepted_real_b05_report"]),
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_positive_signed_component_candidate_count": sum(
            1 for r in records if r["diagnostic_positive_signed_component_candidate"]
        ),
        "diagnostic_rational_seed_hulls_match_r51_count": sum(
            1 for r in records if r["diagnostic_rational_seed_hulls_match_r51"]
        ),
        "diagnostic_rational_seed_hulls_ready_count": sum(
            1 for r in records if r["diagnostic_rational_seed_hulls_ready"]
        ),
        "exact_M_gap_M_L_M_U_ready_count": sum(1 for r in records if r["exact_M_gap_M_L_M_U_ready"]),
        "exact_seed_intervals_ready_count": sum(1 for r in records if r["exact_seed_intervals_ready"]),
        "formula_shape_contract_ready_count": sum(1 for r in records if r["formula_shape_contract_ready"]),
        "input_r51_manifest": rel(r51_manifest),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": sum(1 for r in records if r["operation_enclosures_ready"]),
        "predicate_id": PREDICATE_ID,
        "raw_source_partition_bucket_matched_count": sum(
            1 for r in records if r["raw_source_partition_bucket_matched"]
        ),
        "recommended_next_task": (
            "Build the exact/outward-rounded geometric seed arithmetic backend for "
            "B05 g0/c_L/c_U/tau/non-support component intervals, using the R52 "
            "source traces as diagnostics only."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "source_partition_inventory_matched_count": sum(
            1 for r in records if r["source_partition_inventory_matched"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r51-manifest", type=Path, default=DEFAULT_R51_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    r51_manifest = ROOT / args.r51_manifest
    out_dir = ROOT / args.out_dir
    records = [
        build_audit_record(record, out_dir)
        for record in load_manifest_records(r51_manifest)
    ]
    manifest = build_manifest(records, r51_manifest)
    write_json_lf(ROOT / args.manifest, manifest)

    print(f"input R51 records: {len(records)}")
    print(f"exact seed replay source-audit records emitted: {len(records)}")
    print(
        "source partition inventory matched: "
        f"{manifest['source_partition_inventory_matched_count']}"
    )
    print(
        "raw source partition bucket matched: "
        f"{manifest['raw_source_partition_bucket_matched_count']}"
    )
    print(
        "diagnostic rational seed hulls ready: "
        f"{manifest['diagnostic_rational_seed_hulls_ready_count']}"
    )
    print(
        "diagnostic hulls match R51: "
        f"{manifest['diagnostic_rational_seed_hulls_match_r51_count']}"
    )
    print(
        "diagnostic positive signed-component candidates: "
        f"{manifest['diagnostic_positive_signed_component_candidate_count']}"
    )
    print(f"exact seed intervals ready: {manifest['exact_seed_intervals_ready_count']}")
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(ROOT / args.manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
