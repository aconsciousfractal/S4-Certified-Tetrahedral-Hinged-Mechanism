#!/usr/bin/env python
"""
Build the B05 support finite-extrema extractor backend.

R45 consumes the R44 support/component/gap contract manifest.  It extracts the
finite support signatures that actually match each B05 piece pair, parses the
lower/upper support label sets, and records whether a single report-level
support_state can be emitted.

The current answer is intentionally conservative: the finite ledgers contain
multiple support signatures for the same piece pair, so a single uniform
support_state per real B05 report would be unsound.  This backend therefore
emits a support-partition inventory and precise blockers, not accepted report
fields and not op_support_finite_extrema enclosures.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-SUPPORT-FINITE-EXTREMA-EXTRACTOR-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_SUPPORT_FINITE_EXTREMA_EXTRACTOR"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R44_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_component_gap_margin_contract_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "support_finite_extrema_extractor"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_finite_extrema_extractor_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_uniform_report_level_support_state_claim",
    "no_exact_support_finite_extrema_claim",
    "no_op_support_finite_extrema_enclosure_claim",
    "no_exact_component_motion_bound_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_theorem_promotion_claim",
]

SUPPORT_SIGNATURE_RE = re.compile(r"lower=([^\[]+)\[([^\]]*)\]\|upper=([^\[]+)\[([^\]]*)\]")


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


def parse_labels(text: str) -> list[str]:
    return [item for item in text.split(",") if item]


def parse_support_signature(signature: str) -> dict[str, Any] | None:
    match = SUPPORT_SIGNATURE_RE.fullmatch(signature)
    if not match:
        return None
    return {
        "lower_piece": match.group(1),
        "lower_support_labels": parse_labels(match.group(2)),
        "upper_piece": match.group(3),
        "upper_support_labels": parse_labels(match.group(4)),
    }


def finite_float_stats(values: list[float]) -> dict[str, Any]:
    finite_values = [value for value in values if math.isfinite(value)]
    nonfinite_count = len(values) - len(finite_values)
    if not finite_values:
        return {
            "count": len(values),
            "finite_float_semantics": "no_finite_values",
            "max": None,
            "min": None,
            "nonfinite_count": nonfinite_count,
        }
    return {
        "count": len(values),
        "finite_float_semantics": "diagnostic_float_not_fraction_interval",
        "max": max(finite_values),
        "min": min(finite_values),
        "nonfinite_count": nonfinite_count,
    }


def support_entries(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = read_json(path)
    entries: list[dict[str, Any]] = []

    def walk(value: Any, context: dict[str, Any]) -> None:
        if isinstance(value, dict):
            next_context = dict(context)
            for key in [
                "cell_id",
                "base_cell_id",
                "source_margin_box_id",
                "source_margin_base_cell_id",
                "status",
                "failure_reason",
                "method",
            ]:
                item = value.get(key)
                if item is not None and not isinstance(item, (dict, list)):
                    next_context[key] = item
            signature = value.get("support_signature")
            if isinstance(signature, str):
                parsed = parse_support_signature(signature)
                entries.append({
                    "context": next_context,
                    "finite_gap": value.get("gap"),
                    "finite_minimum_stability_margin": value.get("minimum_stability_margin"),
                    "finite_signed_component_bound": value.get("signed_component_bound"),
                    "finite_signed_component_margin": value.get("signed_component_margin"),
                    "ledger": rel(path),
                    "lower_expanded_support_labels": value.get("lower_expanded_support_labels"),
                    "parsed": parsed,
                    "signature": signature,
                    "upper_expanded_support_labels": value.get("upper_expanded_support_labels"),
                })
            for child in value.values():
                walk(child, next_context)
        elif isinstance(value, list):
            for child in value:
                walk(child, context)

    walk(data, {})
    return entries


def piece_pair_set(piece_pair: str) -> set[str]:
    return {part for part in str(piece_pair).split("-") if part}


def matches_piece_pair(entry: dict[str, Any], piece_pair: str) -> bool:
    parsed = entry.get("parsed")
    if not isinstance(parsed, dict):
        return False
    return {parsed["lower_piece"], parsed["upper_piece"]} == piece_pair_set(piece_pair)


def tuple_or_empty(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value)


def partition_inventory(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_signature: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in entries:
        by_signature[entry["signature"]].append(entry)

    out: list[dict[str, Any]] = []
    for signature, items in sorted(by_signature.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        parsed = items[0]["parsed"]
        expanded_counter = Counter(
            (
                tuple_or_empty(item.get("lower_expanded_support_labels")),
                tuple_or_empty(item.get("upper_expanded_support_labels")),
            )
            for item in items
            if item.get("lower_expanded_support_labels") is not None
            or item.get("upper_expanded_support_labels") is not None
        )
        stability_values = [
            float(item["finite_minimum_stability_margin"])
            for item in items
            if item.get("finite_minimum_stability_margin") is not None
        ]
        gap_values = [
            float(item["finite_gap"])
            for item in items
            if item.get("finite_gap") is not None
        ]
        margin_values = [
            float(item["finite_signed_component_margin"])
            for item in items
            if item.get("finite_signed_component_margin") is not None
        ]
        out.append({
            "count": len(items),
            "expanded_support_label_variants": [
                {
                    "count": count,
                    "lower_expanded_support_labels": list(lower),
                    "upper_expanded_support_labels": list(upper),
                }
                for (lower, upper), count in expanded_counter.most_common()
            ],
            "finite_gap_stats": finite_float_stats(gap_values),
            "finite_minimum_stability_margin_stats": finite_float_stats(stability_values),
            "finite_signed_component_margin_stats": finite_float_stats(margin_values),
            "lower_piece": parsed["lower_piece"],
            "lower_support_labels": parsed["lower_support_labels"],
            "signature": signature,
            "upper_piece": parsed["upper_piece"],
            "upper_support_labels": parsed["upper_support_labels"],
        })
    return out


def label_union(partitions: list[dict[str, Any]], key: str) -> list[str]:
    labels: set[str] = set()
    for item in partitions:
        labels.update(str(label) for label in item[key])
    return sorted(labels)


def label_intersection(partitions: list[dict[str, Any]], key: str) -> list[str]:
    if not partitions:
        return []
    common = set(str(label) for label in partitions[0][key])
    for item in partitions[1:]:
        common &= set(str(label) for label in item[key])
    return sorted(common)


def operation_enclosure_status(partitions: list[dict[str, Any]]) -> dict[str, Any]:
    if not partitions:
        return {
            "blockers": ["no_matching_support_signature_for_piece_pair"],
            "op_id": "op_support_finite_extrema",
            "ready": False,
            "status": "blocked_no_support_seed",
        }
    return {
        "blockers": [
            "finite_support_margins_are_diagnostic_float_not_fraction_interval",
            "support_extrema_not_replayed_by_exact_backend",
            "support_partitioned_report_generation_required",
        ],
        "op_id": "op_support_finite_extrema",
        "ready": False,
        "status": "finite_partition_seed_extracted_operation_enclosure_blocked",
    }


def build_record(
    r44_summary: dict[str, Any],
    *,
    entry_cache: dict[str, list[dict[str, Any]]],
    out_dir: Path,
) -> dict[str, Any]:
    r44_path = ROOT / r44_summary["object_record"]
    r44 = read_json(r44_path)
    piece_pair = str(r44["piece_pair"])
    matching_entries: list[dict[str, Any]] = []
    source_ledgers = [
        item["ledger"]
        for item in r44.get("finite_source_ledger_summaries", [])
        if isinstance(item, dict) and isinstance(item.get("ledger"), str)
    ]
    for ledger in source_ledgers:
        ledger_path = ROOT / ledger
        if ledger not in entry_cache:
            entry_cache[ledger] = support_entries(ledger_path)
        matching_entries.extend(
            entry for entry in entry_cache[ledger] if matches_piece_pair(entry, piece_pair)
        )

    partitions = partition_inventory(matching_entries)
    unique_count = len(partitions)
    total_count = sum(item["count"] for item in partitions)
    uniform_candidate_ready = unique_count == 1
    exact_support_state_ready = False
    if not partitions:
        status = "blocked_no_matching_support_signature_for_piece_pair"
        blockers = [
            "no_matching_support_signature_for_piece_pair",
            "support_seed_gap_must_be_reconstructed_from_component_margin_ledger",
            "formula_shape_report_not_emitted",
            "accepted_report_promotion_out_of_scope",
        ]
    elif uniform_candidate_ready:
        status = "single_finite_support_signature_extracted_exact_enclosure_blocked"
        blockers = [
            "finite_support_margins_are_diagnostic_float_not_fraction_interval",
            "op_support_finite_extrema_missing",
            "formula_shape_report_not_emitted",
            "accepted_report_promotion_out_of_scope",
        ]
    else:
        status = "support_partitions_extracted_report_level_support_state_blocked"
        blockers = [
            "support_signature_not_uniform_across_record",
            "support_partitioned_report_generation_required",
            "finite_support_margins_are_diagnostic_float_not_fraction_interval",
            "op_support_finite_extrema_missing",
            "formula_shape_report_not_emitted",
            "accepted_report_promotion_out_of_scope",
        ]

    support_state_candidate = None
    if uniform_candidate_ready:
        only = partitions[0]
        support_state_candidate = {
            "candidate_semantics": "finite_signature_only_not_exact_enclosure",
            "lower_support_labels": only["lower_support_labels"],
            "status": "backend_blocked",
            "upper_support_labels": only["upper_support_labels"],
        }

    operation_status = operation_enclosure_status(partitions)
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers + operation_status["blockers"])),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "domain_family": r44.get("domain_family"),
        "exact_support_labels_ready": exact_support_state_ready,
        "finite_matching_support_signature_count": total_count,
        "formula_shape_contract_ready": False,
        "input_r44_contract_record": rel(r44_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-SUPPORT-FINITE-EXTREMA-{sanitize(r44['original_report_id'])}",
        "object_status": status,
        "op_support_finite_extrema": operation_status,
        "original_report": r44.get("original_report"),
        "original_report_id": r44.get("original_report_id"),
        "piece_pair": piece_pair,
        "predicate_id": PREDICATE_ID,
        "source_ledgers_scanned": source_ledgers,
        "support_label_intersections": {
            "lower_support_labels": label_intersection(partitions, "lower_support_labels"),
            "upper_support_labels": label_intersection(partitions, "upper_support_labels"),
        },
        "support_label_unions": {
            "lower_support_labels": label_union(partitions, "lower_support_labels"),
            "upper_support_labels": label_union(partitions, "upper_support_labels"),
        },
        "support_partition_inventory": partitions,
        "support_state_candidate": support_state_candidate,
        "support_state_uniform_candidate_ready": uniform_candidate_ready,
        "tree_id": r44.get("tree_id"),
        "unique_support_partition_count": unique_count,
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / f"{sanitize(record['original_report_id'])}_support_finite_extrema.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "domain_family": record["domain_family"],
        "exact_support_labels_ready": exact_support_state_ready,
        "finite_matching_support_signature_count": total_count,
        "formula_shape_contract_ready": False,
        "object_record": rel(out_path),
        "object_status": status,
        "op_support_finite_extrema_ready": False,
        "original_report": record["original_report"],
        "original_report_id": record["original_report_id"],
        "piece_pair": piece_pair,
        "support_state_uniform_candidate_ready": uniform_candidate_ready,
        "tree_id": record["tree_id"],
        "unique_support_partition_count": unique_count,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r44-manifest", default=DEFAULT_R44_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r44_path = ROOT / args.r44_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    r44 = read_json(r44_path)
    records_in = r44.get("records") or []
    if not isinstance(records_in, list):
        raise TypeError("R44 records must be a list")

    entry_cache: dict[str, list[dict[str, Any]]] = {}
    records = [
        build_record(item, entry_cache=entry_cache, out_dir=out_dir)
        for item in records_in
    ]

    status_counts = Counter(item["object_status"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)
    unique_partition_counts = Counter(str(item["unique_support_partition_count"]) for item in records)
    blocker_counts = Counter()
    for item in records:
        record = read_json(ROOT / item["object_record"])
        blocker_counts.update(record["blockers"])

    manifest = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "exact_support_labels_ready_count": sum(
            1 for item in records if item["exact_support_labels_ready"]
        ),
        "formula_shape_contract_ready_count": 0,
        "input_r44_manifest": rel(r44_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "op_support_finite_extrema_ready_count": sum(
            1 for item in records if item["op_support_finite_extrema_ready"]
        ),
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R46: build support-partitioned B05 contract records, or reconstruct "
            "missing TREE_021 P1-P2 ray-nonhinge support seeds, before attempting "
            "component-bound and M_gap interval extraction."
        ),
        "support_matching_signature_count_total": sum(
            item["finite_matching_support_signature_count"] for item in records
        ),
        "support_partition_count_distribution": dict(sorted(unique_partition_counts.items())),
        "support_partitioned_records_count": sum(
            1 for item in records if item["unique_support_partition_count"] > 1
        ),
        "support_seed_missing_records_count": sum(
            1 for item in records if item["unique_support_partition_count"] == 0
        ),
        "support_state_uniform_candidate_ready_count": sum(
            1 for item in records if item["support_state_uniform_candidate_ready"]
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R44 records: {len(records)}")
    print(
        "matching finite support signatures: "
        f"{manifest['support_matching_signature_count_total']}"
    )
    print(
        "support partition count distribution: "
        f"{manifest['support_partition_count_distribution']}"
    )
    print(f"support-partitioned records: {manifest['support_partitioned_records_count']}")
    print(f"support seed missing records: {manifest['support_seed_missing_records_count']}")
    print(
        "uniform report-level support candidates ready: "
        f"{manifest['support_state_uniform_candidate_ready_count']}"
    )
    print(f"exact support labels ready: {manifest['exact_support_labels_ready_count']}")
    print(
        "op_support_finite_extrema ready: "
        f"{manifest['op_support_finite_extrema_ready_count']}"
    )
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")

    if len(records) != len(records_in):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
