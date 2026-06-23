#!/usr/bin/env python
"""
Build B05 support-partitioned contract records.

R47 consumes the R45 support finite-extrema extractor and the R46 missing
support seed reconstruction.  It emits one contract record per finite support
partition.  This is the report granularity required before exact component
motion bounds and M_gap/M_L/M_U intervals can be extracted.

The generated records are still backend contracts.  They carry finite support
labels and diagnostic float summaries, but they do not claim exact support
finite-extrema enclosures, component bounds, positive M_gap/M_L/M_U intervals,
operation enclosures, or accepted B05 reports.
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
MANIFEST_ID = "S4-CL5-B05-SUPPORT-PARTITION-CONTRACT-RECORDS-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_SUPPORT_PARTITION_CONTRACT_RECORDS"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R45_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_finite_extrema_extractor_manifest.json"
)
DEFAULT_R46_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_missing_support_seed_reconstruction_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "support_partition_contract_records"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_partition_contract_records_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_support_finite_extrema_claim",
    "no_exact_component_motion_bound_claim",
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


def partition_signature(partition: dict[str, Any]) -> str:
    signature = partition.get("signature") or partition.get("support_signature")
    if not isinstance(signature, str) or not signature:
        raise ValueError(f"partition missing support signature: {partition}")
    return signature


def partition_count(partition: dict[str, Any]) -> int:
    for key in ["count", "source_margin_box_count", "inherited_terminal_leaf_count"]:
        value = partition.get(key)
        if isinstance(value, int):
            return value
    return 0


def finite_evidence_summary(partition: dict[str, Any]) -> dict[str, Any]:
    keys = [
        "count",
        "source_margin_box_count",
        "inherited_terminal_leaf_count",
        "terminal_leaf_certified_counts",
        "expanded_support_label_variants",
        "finite_gap_stats",
        "finite_minimum_stability_margin_stats",
        "finite_signed_component_bound_stats",
        "finite_signed_component_margin_stats",
        "source_margin_box_ids_sample",
        "terminal_leaf_ids_sample",
    ]
    return {key: partition[key] for key in keys if key in partition}


def support_state_candidate(partition: dict[str, Any], signature: str) -> dict[str, Any]:
    return {
        "candidate_semantics": "finite_support_partition_signature_only_not_exact_enclosure",
        "lower_piece": partition.get("lower_piece"),
        "lower_support_labels": list(partition.get("lower_support_labels") or []),
        "status": "backend_blocked",
        "support_signature": signature,
        "upper_piece": partition.get("upper_piece"),
        "upper_support_labels": list(partition.get("upper_support_labels") or []),
    }


def source_ledgers(record: dict[str, Any]) -> list[str]:
    ledgers = record.get("source_ledgers_scanned")
    if isinstance(ledgers, list):
        return [str(item) for item in ledgers]
    reconstruction = record.get("reconstruction_source")
    if isinstance(reconstruction, dict):
        out = []
        source_margin = reconstruction.get("source_margin_report")
        if isinstance(source_margin, str):
            out.append(source_margin)
        source_script = reconstruction.get("source_classifier_script")
        if isinstance(source_script, str):
            out.append(source_script)
        return out
    return []


def build_partition_record(
    *,
    source_backend: str,
    source_summary: dict[str, Any],
    source_record: dict[str, Any],
    partition: dict[str, Any],
    partition_index: int,
    out_dir: Path,
) -> dict[str, Any]:
    signature = partition_signature(partition)
    original_report_id = str(source_record["original_report_id"])
    partition_key = (
        f"{source_record.get('tree_id')}|{source_record.get('piece_pair')}|"
        f"{source_record.get('domain_family')}|support_partition_{partition_index:02d}|{signature}"
    )
    status = "support_partition_contract_ready_component_gap_extractors_blocked"
    blockers = [
        "finite_support_partition_is_diagnostic_seed_not_exact_enclosure",
        "exact_component_motion_bounds_not_extracted",
        "positive_M_gap_M_L_M_U_not_extracted",
        "operation_enclosures_missing",
        "formula_shape_real_report_not_emitted",
        "accepted_report_promotion_out_of_scope",
    ]
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": blockers,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_motion_bounds_ready": False,
        "domain_family": source_record.get("domain_family"),
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_support_labels_ready": False,
        "finite_evidence_summary": finite_evidence_summary(partition),
        "formula_shape_contract_ready": False,
        "input_support_source_record": source_summary["object_record"],
        "input_support_source_backend": source_backend,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-SUPPORT-PARTITION-CONTRACT-{sanitize(original_report_id)}-"
            f"PART-{partition_index:02d}"
        ),
        "object_status": status,
        "operation_enclosures_ready": False,
        "original_report": source_record.get("original_report"),
        "original_report_id": original_report_id,
        "partition_index": partition_index,
        "piece_pair": source_record.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "source_ledgers": source_ledgers(source_record),
        "support_partition_contract_ready": True,
        "support_partition_count": partition_count(partition),
        "support_partition_key": partition_key,
        "support_state_candidate": support_state_candidate(partition, signature),
        "support_state_partition_candidate_ready": True,
        "support_signature": signature,
        "tree_id": source_record.get("tree_id"),
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / sanitize(original_report_id)
        / f"partition_{partition_index:02d}_{sanitize(signature)}.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "component_motion_bounds_ready": False,
        "domain_family": record["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_support_labels_ready": False,
        "formula_shape_contract_ready": False,
        "object_record": rel(out_path),
        "object_status": status,
        "operation_enclosures_ready": False,
        "original_report": record["original_report"],
        "original_report_id": original_report_id,
        "partition_index": partition_index,
        "piece_pair": record["piece_pair"],
        "source_backend": source_backend,
        "support_partition_contract_ready": True,
        "support_partition_count": record["support_partition_count"],
        "support_signature": signature,
        "tree_id": record["tree_id"],
    }


def load_source_records(manifest_path: Path) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    manifest = read_json(manifest_path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"manifest records must be a list: {manifest_path}")
    out = []
    for summary in records:
        if not isinstance(summary, dict):
            raise TypeError(f"manifest record summary must be an object: {manifest_path}")
        record_path = ROOT / summary["object_record"]
        out.append((summary, read_json(record_path)))
    return out


def build_records(
    *,
    r45_path: Path,
    r46_path: Path,
    out_dir: Path,
) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for summary, record in load_source_records(r45_path):
        partitions = record.get("support_partition_inventory")
        if not isinstance(partitions, list):
            raise TypeError("R45 support_partition_inventory must be a list")
        if not partitions:
            continue
        for index, partition in enumerate(partitions):
            records.append(
                build_partition_record(
                    source_backend="R45_support_finite_extrema_extractor",
                    source_summary=summary,
                    source_record=record,
                    partition=partition,
                    partition_index=index,
                    out_dir=out_dir,
                )
            )

    for summary, record in load_source_records(r46_path):
        partitions = record.get("support_partition_inventory")
        if not isinstance(partitions, list):
            raise TypeError("R46 support_partition_inventory must be a list")
        if not record.get("support_seed_reconstructed"):
            continue
        for index, partition in enumerate(partitions):
            records.append(
                build_partition_record(
                    source_backend="R46_missing_support_seed_reconstruction",
                    source_summary=summary,
                    source_record=record,
                    partition=partition,
                    partition_index=index,
                    out_dir=out_dir,
                )
            )

    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r45-manifest", default=DEFAULT_R45_MANIFEST.as_posix())
    parser.add_argument("--r46-manifest", default=DEFAULT_R46_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r45_path = ROOT / args.r45_manifest
    r46_path = ROOT / args.r46_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    records = build_records(r45_path=r45_path, r46_path=r46_path, out_dir=out_dir)
    status_counts = Counter(item["object_status"] for item in records)
    source_backend_counts = Counter(item["source_backend"] for item in records)
    partition_count_by_original_report = Counter(item["original_report_id"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)

    manifest = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_motion_bounds_ready_count": 0,
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "exact_support_labels_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "input_r45_manifest": rel(r45_path),
        "input_r46_manifest": rel(r46_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "partition_count_by_original_report": dict(sorted(partition_count_by_original_report.items())),
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "record_count_by_source_backend": dict(sorted(source_backend_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R48: extract exact/outward-rounded component motion bound objects per "
            "B05 support-partition contract before M_gap/M_L/M_U interval extraction."
        ),
        "support_partition_contract_ready_count": sum(
            1 for item in records if item["support_partition_contract_ready"]
        ),
        "support_partition_record_count": len(records),
        "support_partition_total_finite_seed_count": sum(
            int(item["support_partition_count"]) for item in records
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R45 manifest: {rel(r45_path)}")
    print(f"input R46 manifest: {rel(r46_path)}")
    print(f"support partition records emitted: {manifest['support_partition_record_count']}")
    print(
        "support partition records by source backend: "
        f"{manifest['record_count_by_source_backend']}"
    )
    print(
        "support partition records by domain family: "
        f"{manifest['record_count_by_domain_family']}"
    )
    print(
        "support partition finite seed count total: "
        f"{manifest['support_partition_total_finite_seed_count']}"
    )
    print(
        "support partition contracts ready: "
        f"{manifest['support_partition_contract_ready_count']}"
    )
    print(f"exact support labels ready: {manifest['exact_support_labels_ready_count']}")
    print(
        "component motion bounds ready: "
        f"{manifest['component_motion_bounds_ready_count']}"
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
