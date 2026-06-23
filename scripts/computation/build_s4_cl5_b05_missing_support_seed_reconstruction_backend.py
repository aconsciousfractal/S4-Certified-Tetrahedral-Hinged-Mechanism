#!/usr/bin/env python
"""
Reconstruct the missing B05 TREE_021 P1-P2 finite support seed.

R45 could not find a support signature for the TREE_021 P1-P2 ray-nonhinge
B05 record because the direct R44 ledger chain points at the margin endgame
report.  That report stores source margin boxes and refined terminal leaves,
but not the support_signature field.  The support seed is recoverable by
replaying the exact same depth-5 failure classifier used by the margin
endgame, then joining the margin report's source_margin_box_id values back to
the reconstructed classifier boxes.

This backend is deliberately conservative.  It reconstructs a finite support
seed and records the join evidence; it does not emit exact support extrema,
component motion intervals, M_gap/M_L/M_U intervals, operation enclosures, or
accepted B05 reports.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_bounded_cell_tree021_p1p2_endgame_failure_classifier as classifier  # noqa: E402
import audit_historical_s4_bounded_cell_tree021_p1p2_shared_edge_adaptive_probe as adaptive  # noqa: E402


CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-MISSING-SUPPORT-SEED-RECONSTRUCTION-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_MISSING_SUPPORT_SEED_RECONSTRUCTION"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R45_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_finite_extrema_extractor_manifest.json"
)
DEFAULT_MARGIN_REPORT = Path(
    "results/historical_s4_median_planes/"
    "bounded_cell_tree021_p1p2_margin_endgame_guard_report.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "missing_support_seed_reconstruction"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_missing_support_seed_reconstruction_manifest.json"
)

TARGET_TREE_ID = "TREE_021"
TARGET_PIECE_PAIR = "P1-P2"
TARGET_DOMAIN = "ray_nonhinge"

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_support_label_claim",
    "no_exact_support_finite_extrema_claim",
    "no_exact_component_motion_bound_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
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


def finite_float_stats(values: list[Any]) -> dict[str, Any]:
    finite_values: list[float] = []
    nonfinite_count = 0
    for value in values:
        if value is None:
            continue
        numeric = float(value)
        if math.isfinite(numeric):
            finite_values.append(numeric)
        else:
            nonfinite_count += 1
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


def support_seed_from_guard(box: dict[str, Any], guard: dict[str, Any]) -> dict[str, Any]:
    signature = classifier.support_signature(guard)
    return {
        "base_cell_id": box.get("base_cell_id"),
        "cell_id": box.get("cell_id"),
        "failure_category": classifier.failure_category(guard),
        "finite_gap": guard.get("gap"),
        "finite_minimum_stability_margin": guard.get("minimum_stability_margin"),
        "finite_signed_component_bound": guard.get("signed_component_bound"),
        "finite_signed_component_margin": guard.get("signed_component_margin"),
        "lower_piece": guard.get("lower_piece"),
        "lower_support_labels": list(guard.get("lower_support_labels", [])),
        "recommended_split_dimension": box.get("recommended_split_dimension"),
        "support_signature": signature,
        "upper_piece": guard.get("upper_piece"),
        "upper_support_labels": list(guard.get("upper_support_labels", [])),
    }


def reconstruct_classifier_seed_map(source_ids: set[str]) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    ctx = classifier.context()
    failed_boxes, level_trace = classifier.reconstruct_failed_terminal_boxes(ctx)
    seeds: dict[str, dict[str, Any]] = {}
    category_counts = Counter()
    signature_counts = Counter()
    for box in failed_boxes:
        cell_id = str(box.get("cell_id"))
        if cell_id not in source_ids:
            continue
        guard = adaptive.common_edge_box_guard(
            ctx["case"],
            ctx["tree"],
            ctx["signs"],
            ctx["indices"],
            ctx["labels_by_piece"],
            ctx["paths_by_piece"],
            box,
        )
        seed = support_seed_from_guard(box, guard)
        seeds[cell_id] = seed
        category_counts[str(seed["failure_category"])] += 1
        signature_counts[str(seed["support_signature"])] += 1

    diagnostics = {
        "classifier_failed_box_count": len(failed_boxes),
        "classifier_level_trace": level_trace,
        "matched_source_margin_box_count": len(seeds),
        "missing_source_margin_box_count": len(source_ids - set(seeds)),
        "missing_source_margin_box_ids": sorted(source_ids - set(seeds))[:32],
        "source_failure_category_counts": dict(sorted(category_counts.items())),
        "source_support_signature_counts": dict(sorted(signature_counts.items())),
    }
    return seeds, diagnostics


def terminal_leaf_inventory(margin_report: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    terminal_records = margin_report.get("margin_audit", {}).get("terminal_records", [])
    if not isinstance(terminal_records, list):
        raise TypeError("margin_audit.terminal_records must be a list")
    source_ids = [
        str(record.get("source_margin_box_id"))
        for record in terminal_records
        if record.get("source_margin_box_id") is not None
    ]
    certified_counter = Counter(str(record.get("certified")) for record in terminal_records)
    diagnostics = {
        "replacement_terminal_leaf_count": len(terminal_records),
        "replacement_terminal_leaf_certified_counts": dict(sorted(certified_counter.items())),
        "source_margin_box_count": len(set(source_ids)),
    }
    return terminal_records, diagnostics


def partition_inventory(
    source_seeds: dict[str, dict[str, Any]],
    terminal_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    leaves_by_source = defaultdict(list)
    for record in terminal_records:
        source_id = record.get("source_margin_box_id")
        if source_id is not None:
            leaves_by_source[str(source_id)].append(record)

    by_signature: dict[str, dict[str, Any]] = {}
    for source_id, seed in source_seeds.items():
        signature = str(seed["support_signature"])
        bucket = by_signature.setdefault(
            signature,
            {
                "finite_gap_values": [],
                "finite_minimum_stability_margin_values": [],
                "finite_signed_component_bound_values": [],
                "finite_signed_component_margin_values": [],
                "lower_piece": seed["lower_piece"],
                "lower_support_labels": seed["lower_support_labels"],
                "source_margin_box_ids": [],
                "support_signature": signature,
                "terminal_leaf_certified_counts": Counter(),
                "terminal_leaf_ids_sample": [],
                "upper_piece": seed["upper_piece"],
                "upper_support_labels": seed["upper_support_labels"],
            },
        )
        bucket["source_margin_box_ids"].append(source_id)
        for key, value_key in [
            ("finite_gap_values", "finite_gap"),
            ("finite_minimum_stability_margin_values", "finite_minimum_stability_margin"),
            ("finite_signed_component_bound_values", "finite_signed_component_bound"),
            ("finite_signed_component_margin_values", "finite_signed_component_margin"),
        ]:
            bucket[key].append(seed.get(value_key))
        for leaf in leaves_by_source.get(source_id, []):
            bucket["terminal_leaf_certified_counts"][str(leaf.get("certified"))] += 1
            if len(bucket["terminal_leaf_ids_sample"]) < 16:
                bucket["terminal_leaf_ids_sample"].append(leaf.get("cell_id"))

    out: list[dict[str, Any]] = []
    for signature, bucket in sorted(by_signature.items(), key=lambda kv: (-len(kv[1]["source_margin_box_ids"]), kv[0])):
        source_ids = sorted(bucket["source_margin_box_ids"])
        leaf_count = sum(bucket["terminal_leaf_certified_counts"].values())
        out.append({
            "finite_gap_stats": finite_float_stats(bucket["finite_gap_values"]),
            "finite_minimum_stability_margin_stats": finite_float_stats(
                bucket["finite_minimum_stability_margin_values"]
            ),
            "finite_signed_component_bound_stats": finite_float_stats(
                bucket["finite_signed_component_bound_values"]
            ),
            "finite_signed_component_margin_stats": finite_float_stats(
                bucket["finite_signed_component_margin_values"]
            ),
            "inherited_terminal_leaf_count": leaf_count,
            "lower_piece": bucket["lower_piece"],
            "lower_support_labels": bucket["lower_support_labels"],
            "source_margin_box_count": len(source_ids),
            "source_margin_box_ids_sample": source_ids[:32],
            "support_signature": signature,
            "terminal_leaf_certified_counts": dict(sorted(bucket["terminal_leaf_certified_counts"].items())),
            "terminal_leaf_ids_sample": bucket["terminal_leaf_ids_sample"],
            "upper_piece": bucket["upper_piece"],
            "upper_support_labels": bucket["upper_support_labels"],
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


def build_record(
    r45_summary: dict[str, Any],
    *,
    margin_report_path: Path,
    out_dir: Path,
) -> dict[str, Any]:
    r45_record_path = ROOT / r45_summary["object_record"]
    r45_record = read_json(r45_record_path)
    margin_report = read_json(margin_report_path)
    terminal_records, terminal_diagnostics = terminal_leaf_inventory(margin_report)
    source_ids = {
        str(record["source_margin_box_id"])
        for record in terminal_records
        if record.get("source_margin_box_id") is not None
    }
    source_seeds, classifier_diagnostics = reconstruct_classifier_seed_map(source_ids)
    partitions = partition_inventory(source_seeds, terminal_records)
    unique_partition_count = len(partitions)
    all_sources_matched = classifier_diagnostics["missing_source_margin_box_count"] == 0

    if not partitions:
        status = "blocked_no_reconstructable_support_seed"
        blockers = [
            "no_reconstructable_classifier_support_seed",
            "support_extrema_not_replayed_by_exact_backend",
            "accepted_report_promotion_out_of_scope",
        ]
    else:
        status = "missing_support_seed_reconstructed_from_classifier_margin_source_boxes"
        blockers = [
            "reconstructed_support_seed_is_finite_classifier_guard_not_exact_interval",
            "support_extrema_not_replayed_by_exact_backend",
            "component_motion_bounds_not_extracted",
            "positive_M_gap_M_L_M_U_not_extracted",
            "operation_enclosure_missing",
            "accepted_report_promotion_out_of_scope",
        ]
        if not all_sources_matched:
            blockers.append("some_source_margin_box_ids_not_reconstructed")
        if unique_partition_count != 1:
            blockers.append("support_partitioned_report_generation_required")

    support_state_candidate = None
    if unique_partition_count == 1:
        only = partitions[0]
        support_state_candidate = {
            "candidate_semantics": "finite_classifier_signature_only_not_exact_enclosure",
            "lower_piece": only["lower_piece"],
            "lower_support_labels": only["lower_support_labels"],
            "status": "backend_blocked",
            "support_signature": only["support_signature"],
            "upper_piece": only["upper_piece"],
            "upper_support_labels": only["upper_support_labels"],
        }

    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers)),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "classifier_reconstruction_diagnostics": classifier_diagnostics,
        "domain_family": r45_record.get("domain_family"),
        "exact_support_labels_ready": False,
        "formula_shape_contract_ready": False,
        "input_r45_support_finite_extrema_record": rel(r45_record_path),
        "manifest_id": MANIFEST_ID,
        "margin_report": rel(margin_report_path),
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-MISSING-SUPPORT-SEED-RECONSTRUCTION-{sanitize(r45_record['original_report_id'])}",
        "object_status": status,
        "op_support_finite_extrema": {
            "blockers": [
                "finite_classifier_support_seed_not_exact_support_extrema_enclosure",
                "support_extrema_not_replayed_by_exact_backend",
            ],
            "op_id": "op_support_finite_extrema",
            "ready": False,
            "status": "finite_support_seed_reconstructed_operation_enclosure_blocked",
        },
        "original_report": r45_record.get("original_report"),
        "original_report_id": r45_record.get("original_report_id"),
        "piece_pair": r45_record.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "reconstruction_source": {
            "join_key": "margin_audit.terminal_records[*].source_margin_box_id == reconstructed_classifier_box.cell_id",
            "source_classifier_script": "scripts/audit_historical_s4_bounded_cell_tree021_p1p2_endgame_failure_classifier.py",
            "source_margin_report": rel(margin_report_path),
        },
        "support_label_intersections": {
            "lower_support_labels": label_intersection(partitions, "lower_support_labels"),
            "upper_support_labels": label_intersection(partitions, "upper_support_labels"),
        },
        "support_label_unions": {
            "lower_support_labels": label_union(partitions, "lower_support_labels"),
            "upper_support_labels": label_union(partitions, "upper_support_labels"),
        },
        "support_partition_inventory": partitions,
        "support_seed_reconstructed": bool(partitions and all_sources_matched),
        "support_state_candidate": support_state_candidate,
        "support_state_uniform_candidate_ready": unique_partition_count == 1,
        "terminal_leaf_diagnostics": terminal_diagnostics,
        "tree_id": r45_record.get("tree_id"),
        "unique_support_partition_count": unique_partition_count,
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / f"{sanitize(record['original_report_id'])}_missing_support_seed_reconstruction.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "domain_family": record["domain_family"],
        "exact_support_labels_ready": False,
        "object_record": rel(out_path),
        "object_status": status,
        "original_report": record["original_report"],
        "original_report_id": record["original_report_id"],
        "piece_pair": record["piece_pair"],
        "source_margin_box_count": terminal_diagnostics["source_margin_box_count"],
        "support_seed_reconstructed": record["support_seed_reconstructed"],
        "support_state_uniform_candidate_ready": record["support_state_uniform_candidate_ready"],
        "terminal_leaf_count": terminal_diagnostics["replacement_terminal_leaf_count"],
        "tree_id": record["tree_id"],
        "unique_support_partition_count": unique_partition_count,
    }


def is_target_missing_seed_record(summary: dict[str, Any]) -> bool:
    return (
        summary.get("tree_id") == TARGET_TREE_ID
        and summary.get("piece_pair") == TARGET_PIECE_PAIR
        and summary.get("domain_family") == TARGET_DOMAIN
        and int(summary.get("unique_support_partition_count", -1)) == 0
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r45-manifest", default=DEFAULT_R45_MANIFEST.as_posix())
    parser.add_argument("--margin-report", default=DEFAULT_MARGIN_REPORT.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r45_path = ROOT / args.r45_manifest
    margin_path = ROOT / args.margin_report
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r45_manifest = read_json(r45_path)
    r45_records = r45_manifest.get("records") or []
    if not isinstance(r45_records, list):
        raise TypeError("R45 records must be a list")
    targets = [item for item in r45_records if is_target_missing_seed_record(item)]
    records = [
        build_record(item, margin_report_path=margin_path, out_dir=out_dir)
        for item in targets
    ]

    status_counts = Counter(item["object_status"] for item in records)
    partition_counts = Counter(str(item["unique_support_partition_count"]) for item in records)
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
        "exact_support_labels_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "input_r45_manifest": rel(r45_path),
        "manifest_id": MANIFEST_ID,
        "missing_seed_target_count": len(targets),
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "op_support_finite_extrema_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "records": records,
        "recommended_next_task": (
            "R47: build support-partitioned B05 contract records using R45 plus "
            "this reconstructed TREE_021 P1-P2 support seed before component-bound "
            "and M_gap interval extraction."
        ),
        "reconstructed_support_seed_count": sum(
            1 for item in records if item["support_seed_reconstructed"]
        ),
        "support_partition_count_distribution": dict(sorted(partition_counts.items())),
        "support_state_uniform_candidate_ready_count": sum(
            1 for item in records if item["support_state_uniform_candidate_ready"]
        ),
        "target": {
            "domain_family": TARGET_DOMAIN,
            "piece_pair": TARGET_PIECE_PAIR,
            "tree_id": TARGET_TREE_ID,
        },
        "terminal_leaf_count_total": sum(item["terminal_leaf_count"] for item in records),
        "source_margin_box_count_total": sum(item["source_margin_box_count"] for item in records),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R45 records: {len(r45_records)}")
    print(f"missing seed targets: {manifest['missing_seed_target_count']}")
    print(f"reconstructed support seeds: {manifest['reconstructed_support_seed_count']}")
    print(f"source margin boxes joined: {manifest['source_margin_box_count_total']}")
    print(f"terminal leaves inheriting support seed: {manifest['terminal_leaf_count_total']}")
    print(
        "support partition count distribution: "
        f"{manifest['support_partition_count_distribution']}"
    )
    print(
        "uniform support-state candidates ready: "
        f"{manifest['support_state_uniform_candidate_ready_count']}"
    )
    print(f"exact support labels ready: {manifest['exact_support_labels_ready_count']}")
    print(
        "op_support_finite_extrema ready: "
        f"{manifest['op_support_finite_extrema_ready_count']}"
    )
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")

    if len(records) != len(targets):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
