#!/usr/bin/env python
"""
Build B05 M_gap/M_L/M_U interval-extractor attempt records.

R50 consumes the R49 component-bound interval extractor records.  It joins each
support partition back to its finite support/gap source stats and emits the
exact formula skeleton for M_gap, M_L, and M_U where component bounds are ready.

This backend intentionally does not promote any B05 report.  The current source
layer only provides diagnostic float finite gap/stability/margin stats, not
accepted rational or outward-rounded intervals for g0, c_L, c_U, tau, or
non-support component bounds.  Therefore every exact M_gap/M_L/M_U interval
remains blocked; the value of this layer is making that blocker explicit and
record-local.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-M-GAP-M-L-M-U-INTERVAL-EXTRACTOR-ATTEMPT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_M_GAP_M_L_M_U_INTERVAL_EXTRACTOR_ATTEMPT"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R49_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_component_bound_interval_extractor_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "m_gap_m_l_m_u_interval_extractor"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_m_gap_m_l_m_u_interval_extractor_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
    "no_formula_shape_real_report_claim",
    "no_theorem_promotion_claim",
]


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


def finite_stats_semantics(stats: Any) -> str | None:
    if not isinstance(stats, dict):
        return None
    value = stats.get("finite_float_semantics")
    return str(value) if value is not None else None


def join_support_partition_stats(r49_record: dict[str, Any]) -> dict[str, Any]:
    r48_path = ROOT / r49_record["input_r48_component_motion_bound_object_record"]
    r48_record = read_json(r48_path)
    r47_path = ROOT / r48_record["input_r47_support_partition_record"]
    r47_record = read_json(r47_path)
    source_path = ROOT / r47_record["input_support_source_record"]
    source_record = read_json(source_path)
    signature = str(r49_record["support_signature"])
    inventory = source_record.get("support_partition_inventory") or []
    if not isinstance(inventory, list):
        inventory = []
    matches = [
        item for item in inventory
        if isinstance(item, dict)
        and str(item.get("signature") or item.get("support_signature")) == signature
    ]
    matched = matches[0] if matches else None
    return {
        "input_r47_support_partition_record": rel(r47_path),
        "input_support_source_backend": r47_record.get("input_support_source_backend"),
        "input_support_source_record": rel(source_path),
        "matched_support_partition_count": len(matches),
        "matched_support_partition_stats": matched,
        "support_source_claim_level": source_record.get("claim_level"),
        "support_source_object_status": source_record.get("object_status"),
    }


def component_interval_inputs(r49_record: dict[str, Any]) -> dict[str, Any]:
    candidate = r49_record.get("component_motion_bounds_candidate") or {}
    if not isinstance(candidate, dict):
        candidate = {}
    return {
        "bound_rule_id": candidate.get("bound_rule_id"),
        "lower_piece": candidate.get("lower_piece"),
        "upper_piece": candidate.get("upper_piece"),
        "rodrigues_terms": candidate.get("rodrigues_terms"),
    }


def non_support_labels_from_r48(r49_record: dict[str, Any]) -> dict[str, Any]:
    r48_record = read_json(ROOT / r49_record["input_r48_component_motion_bound_object_record"])
    blueprint = r48_record.get("component_motion_bound_blueprint") or {}
    out: dict[str, Any] = {}
    for role in ["lower_piece", "upper_piece"]:
        piece = blueprint.get(role) if isinstance(blueprint, dict) else None
        if not isinstance(piece, dict):
            out[role] = {}
            continue
        out[role] = {
            "piece_id": piece.get("piece_id"),
            "support_labels": piece.get("support_labels") or [],
            "non_support_labels": piece.get("non_support_labels") or [],
            "missing_non_support_endpoint_coordinate_labels": (
                piece.get("missing_non_support_endpoint_coordinate_labels") or []
            ),
        }
    return out


def build_formula_skeleton(r49_record: dict[str, Any], joined_stats: dict[str, Any]) -> dict[str, Any]:
    stats = joined_stats.get("matched_support_partition_stats")
    diagnostic_inputs: dict[str, Any] = {}
    if isinstance(stats, dict):
        for field in [
            "finite_gap_stats",
            "finite_minimum_stability_margin_stats",
            "finite_signed_component_bound_stats",
            "finite_signed_component_margin_stats",
        ]:
            if field in stats:
                diagnostic_inputs[field] = stats[field]
    non_support = non_support_labels_from_r48(r49_record)
    return {
        "source_identity_id": SOURCE_IDENTITY_ID,
        "formulae": {
            "M_gap": "g0 - Delta_pos(L,S_L) - Delta_neg(U,S_U) - tau",
            "M_L": "c_L - Delta_neg(L,S_L) - Delta_pos(L,N_L) - tau",
            "M_U": "c_U - Delta_pos(U,S_U) - Delta_neg(U,N_U) - tau",
        },
        "component_interval_inputs": component_interval_inputs(r49_record),
        "diagnostic_float_seed_stats": diagnostic_inputs,
        "non_support_requirements": non_support,
        "exact_seed_requirements": {
            "g0_center_gap_interval_ready": False,
            "lower_support_competition_margin_interval_ready": False,
            "upper_support_competition_margin_interval_ready": False,
            "tau_outward_error_interval_ready": False,
            "lower_non_support_component_bounds_ready": False,
            "upper_non_support_component_bounds_ready": False,
        },
    }


def diagnostic_signed_margin_min(joined_stats: dict[str, Any]) -> float | None:
    stats = joined_stats.get("matched_support_partition_stats")
    if not isinstance(stats, dict):
        return None
    margin = stats.get("finite_signed_component_margin_stats")
    if not isinstance(margin, dict):
        return None
    value = margin.get("min")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def build_margin_record(r49_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r49_path = ROOT / r49_summary["object_record"]
    r49_record = read_json(r49_path)
    component_ready = bool(r49_record.get("component_motion_bounds_ready"))
    joined_stats = join_support_partition_stats(r49_record)
    skeleton_ready = component_ready and joined_stats["matched_support_partition_count"] == 1
    signed_min = diagnostic_signed_margin_min(joined_stats)
    diagnostic_positive = signed_min is not None and signed_min > 0

    blockers = [
        "accepted_report_promotion_out_of_scope",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
        "exact_center_gap_interval_missing",
        "exact_support_competition_margin_intervals_missing",
        "tau_outward_error_interval_missing",
        "non_support_component_bounds_missing_for_M_L_M_U",
        "diagnostic_float_seed_stats_not_fraction_intervals",
    ]
    if not component_ready:
        blockers.append("component_bound_interval_envelopes_not_ready")
    if joined_stats["matched_support_partition_count"] != 1:
        blockers.append("support_partition_diagnostic_stats_not_joined")
    if signed_min is not None and signed_min <= 0:
        blockers.append("diagnostic_signed_component_margin_nonpositive")

    object_status = (
        "M_gap_M_L_M_U_formula_skeleton_ready_exact_seed_intervals_blocked"
        if skeleton_ready
        else "M_gap_M_L_M_U_blocked_component_bounds_or_support_stats_missing"
    )
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers)),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_bound_interval_envelope_ready": component_ready,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": r49_record.get("domain_family"),
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_gap_formula_skeleton": build_formula_skeleton(r49_record, joined_stats) if skeleton_ready else None,
        "formula_shape_contract_ready": False,
        "input_r49_component_bound_interval_record": rel(r49_path),
        "manifest_id": MANIFEST_ID,
        "margin_formula_skeleton_ready": skeleton_ready,
        "margin_source_join": joined_stats,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-M-GAP-M-L-M-U-INTERVAL-{sanitize(r49_record['original_report_id'])}-"
            f"PART-{int(r49_record['partition_index']):02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r49_record.get("original_report"),
        "original_report_id": r49_record.get("original_report_id"),
        "partition_index": r49_record.get("partition_index"),
        "piece_pair": r49_record.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "support_signature": r49_record.get("support_signature"),
        "tree_id": r49_record.get("tree_id"),
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / sanitize(record["original_report_id"])
        / f"partition_{int(record['partition_index']):02d}_m_gap_m_l_m_u_attempt.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "component_bound_interval_envelope_ready": component_ready,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": record["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "margin_formula_skeleton_ready": skeleton_ready,
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
    parser.add_argument("--r49-manifest", default=DEFAULT_R49_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r49_manifest = ROOT / args.r49_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    records = [build_margin_record(summary, out_dir) for summary in load_manifest_records(r49_manifest)]
    status_counts = Counter(item["object_status"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)
    blocker_counts = Counter()
    diagnostic_positive = 0
    diagnostic_nonpositive = 0
    for item in records:
        record = read_json(ROOT / item["object_record"])
        blocker_counts.update(record["blockers"])
        if item["margin_formula_skeleton_ready"]:
            if item["diagnostic_positive_signed_component_margin_candidate"]:
                diagnostic_positive += 1
            else:
                diagnostic_nonpositive += 1

    skeleton_ready = sum(1 for item in records if item["margin_formula_skeleton_ready"])
    component_ready = sum(1 for item in records if item["component_bound_interval_envelope_ready"])
    manifest = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_bound_interval_envelope_ready_count": component_ready,
        "diagnostic_nonpositive_signed_component_margin_candidate_count": diagnostic_nonpositive,
        "diagnostic_positive_signed_component_margin_candidate_count": diagnostic_positive,
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "exact_center_gap_interval_ready_count": 0,
        "exact_support_competition_margin_intervals_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "input_r49_manifest": rel(r49_manifest),
        "manifest_id": MANIFEST_ID,
        "margin_formula_skeleton_ready_count": skeleton_ready,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R51: emit rational/outward-rounded center-gap and support-competition "
            "seed intervals for the seven R50 formula skeletons, or prove they cannot "
            "be promoted; endpoint propagation for A/B/C/D remains a separate blocker."
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R49 records: {len(records)}")
    print(f"M_gap/M_L/M_U attempt records emitted: {manifest['object_record_count']}")
    print(f"component-bound envelopes ready: {component_ready}")
    print(f"margin formula skeletons ready: {skeleton_ready}")
    print(f"diagnostic positive signed-component candidates: {diagnostic_positive}")
    print(f"diagnostic nonpositive signed-component candidates: {diagnostic_nonpositive}")
    print(f"exact center gap intervals ready: {manifest['exact_center_gap_interval_ready_count']}")
    print(
        "exact support competition margin intervals ready: "
        f"{manifest['exact_support_competition_margin_intervals_ready_count']}"
    )
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())