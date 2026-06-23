#!/usr/bin/env python
"""
Build B05 component-motion-bound object blueprints per support partition.

R48 consumes the R47 support-partition contract records and joins each
partition to the existing R39 formula bridge, R42 Rodrigues interval
composition, and R43 symbolic axis-norm lower-bound objects.

The result is intentionally a blueprint/blocker layer, not an accepted
component-bound extractor.  It records the exact support/non-support label
split required by the formula-shape contract, the source-locked Rodrigues
rules, the endpoint-coordinate coverage currently available from R42, and the
precise missing inputs before exact/outward-rounded component interval bounds
can be emitted.
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
MANIFEST_ID = "S4-CL5-B05-COMPONENT-MOTION-BOUND-OBJECTS-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_COMPONENT_MOTION_BOUND_OBJECT_BLUEPRINTS"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R47_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_partition_contract_records_manifest.json"
)
DEFAULT_R39_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_formula_backend_bridge_manifest.json"
)
DEFAULT_R42_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_rodrigues_interval_composition_manifest.json"
)
DEFAULT_R43_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_norm_symbolic_lower_bound_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "component_motion_bound_objects"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_component_motion_bound_objects_manifest.json"
)

PIECE_LABELS = {
    "P0": ["A", "M_AB", "C", "M_CD"],
    "P1": ["A", "M_AB", "D", "M_CD"],
    "P2": ["B", "M_AB", "C", "M_CD"],
    "P3": ["B", "M_AB", "D", "M_CD"],
}
COMMON_EDGE_LABELS = {"M_AB", "M_CD"}

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_component_motion_bound_claim",
    "no_outward_rounded_component_interval_claim",
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


def load_manifest_records(manifest_path: Path, record_key: str = "records") -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get(record_key) or []
    if not isinstance(records, list):
        raise TypeError(f"{record_key} must be a list: {manifest_path}")
    return records


def index_records_by_original_id(manifest_path: Path, *, list_key: str, path_key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for summary in load_manifest_records(manifest_path, list_key):
        if not isinstance(summary, dict):
            raise TypeError(f"manifest summary must be an object: {manifest_path}")
        original_id = str(summary["original_report_id"])
        record_path = ROOT / summary[path_key]
        out[original_id] = {
            "record": read_json(record_path),
            "record_path": rel(record_path),
            "summary": summary,
        }
    return out


def index_r39_bridge_records(manifest_path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for summary in load_manifest_records(manifest_path, "report_bridges"):
        original_id = str(summary["original_report_id"])
        record_path = ROOT / summary["bridge_record"]
        out[original_id] = {
            "record": read_json(record_path),
            "record_path": rel(record_path),
            "summary": summary,
        }
    return out


def endpoint_labels(rodrigues_record: dict[str, Any], piece_id: str) -> set[str]:
    intervals = rodrigues_record.get("endpoint_coordinate_intervals")
    if not isinstance(intervals, dict):
        return set()
    piece = intervals.get(piece_id)
    if not isinstance(piece, dict):
        return set()
    endpoints = piece.get("endpoints")
    if not isinstance(endpoints, dict):
        return set()
    return {str(label) for label in endpoints}


def label_split(piece_id: str, support_labels: list[str]) -> dict[str, Any]:
    all_labels = PIECE_LABELS.get(piece_id)
    if all_labels is None:
        raise ValueError(f"unknown piece id: {piece_id}")
    support = [str(label) for label in support_labels]
    non_support = [label for label in all_labels if label not in set(support)]
    return {
        "all_labels": all_labels,
        "non_support_labels": non_support,
        "support_labels": support,
    }


def required_bound_names(role: str) -> list[str]:
    if role == "lower_piece":
        return ["Delta_pos_L_support", "Delta_neg_L_support"]
    if role == "upper_piece":
        return ["Delta_pos_U_support", "Delta_neg_U_support"]
    raise ValueError(role)


def piece_bound_blueprint(
    *,
    role: str,
    piece_id: str,
    support_labels: list[str],
    rodrigues_record: dict[str, Any],
) -> dict[str, Any]:
    split = label_split(piece_id, support_labels)
    available = endpoint_labels(rodrigues_record, piece_id)
    missing_support = [label for label in split["support_labels"] if label not in available]
    missing_non_support = [label for label in split["non_support_labels"] if label not in available]
    support_common_only = set(split["support_labels"]) <= COMMON_EDGE_LABELS
    blockers = [
        "outward_rounded_component_projection_extractor_missing",
        "normalized_axis_interval_projection_unit_not_emitted",
    ]
    if missing_support:
        blockers.append("support_label_endpoint_coordinate_intervals_missing")
    if missing_non_support:
        blockers.append("non_support_label_endpoint_coordinate_intervals_missing_for_stability_M_L_M_U")
    return {
        "available_endpoint_coordinate_labels_from_R42": sorted(available),
        "blockers": blockers,
        "component_interval_bounds": {},
        "component_interval_bounds_ready": False,
        "missing_non_support_endpoint_coordinate_labels": missing_non_support,
        "missing_support_endpoint_coordinate_labels": missing_support,
        "non_support_labels": split["non_support_labels"],
        "piece_id": piece_id,
        "required_component_bound_names": required_bound_names(role),
        "role": role,
        "status": "blocked_component_interval_bounds_not_emitted",
        "support_labels": split["support_labels"],
        "support_labels_common_edge_only": support_common_only,
    }


def finite_component_bound_seed(record: dict[str, Any]) -> dict[str, Any]:
    evidence = record.get("finite_evidence_summary")
    if not isinstance(evidence, dict):
        return {"available": False}
    stats = evidence.get("finite_signed_component_bound_stats")
    if isinstance(stats, dict):
        return {
            "available": int(stats.get("count", 0) or 0) > 0,
            "finite_signed_component_bound_stats": stats,
            "semantics": "diagnostic_float_not_fraction_interval",
        }
    return {
        "available": "finite_signed_component_margin_stats" in evidence,
        "finite_signed_component_margin_stats": evidence.get("finite_signed_component_margin_stats"),
        "semantics": "diagnostic_float_not_fraction_interval",
    }


def rodrigues_terms_from_bridge(bridge_record: dict[str, Any]) -> dict[str, Any] | None:
    seed = bridge_record.get("formula_shape_symbolic_seed")
    if isinstance(seed, dict) and isinstance(seed.get("rodrigues_terms"), dict):
        return seed["rodrigues_terms"]
    fields = bridge_record.get("contract_field_status")
    if isinstance(fields, dict):
        status = fields.get("component_motion_bounds.rodrigues_terms")
        if isinstance(status, dict) and isinstance(status.get("emitted_value"), dict):
            return status["emitted_value"]
    return None


def build_component_record(
    *,
    partition_summary: dict[str, Any],
    partition_record: dict[str, Any],
    r39_index: dict[str, dict[str, Any]],
    r42_index: dict[str, dict[str, Any]],
    r43_index: dict[str, dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    original_id = str(partition_record["original_report_id"])
    r39 = r39_index.get(original_id)
    r42 = r42_index.get(original_id)
    r43 = r43_index.get(original_id)
    if r39 is None or r42 is None or r43 is None:
        missing = [
            name
            for name, item in [("R39", r39), ("R42", r42), ("R43", r43)]
            if item is None
        ]
        raise KeyError(f"missing source joins for {original_id}: {missing}")

    support = partition_record["support_state_candidate"]
    lower_piece = str(support["lower_piece"])
    upper_piece = str(support["upper_piece"])
    lower = piece_bound_blueprint(
        role="lower_piece",
        piece_id=lower_piece,
        support_labels=list(support["lower_support_labels"]),
        rodrigues_record=r42["record"],
    )
    upper = piece_bound_blueprint(
        role="upper_piece",
        piece_id=upper_piece,
        support_labels=list(support["upper_support_labels"]),
        rodrigues_record=r42["record"],
    )
    rodrigues_terms = rodrigues_terms_from_bridge(r39["record"])
    rodrigues_terms_ready = rodrigues_terms is not None
    axis_ready = bool(r43["record"].get("axis_nondegeneracy_contract_ready"))
    support_common_only = lower["support_labels_common_edge_only"] and upper["support_labels_common_edge_only"]

    blockers = [
        "component_interval_bounds_not_emitted",
        "outward_rounded_component_projection_extractor_missing",
        "formula_shape_real_report_not_emitted",
        "accepted_report_promotion_out_of_scope",
    ]
    if not support_common_only:
        blockers.append("support_partition_uses_outer_vertex_endpoint_intervals_not_available_from_R42")
    if not axis_ready:
        blockers.append("axis_nondegeneracy_contract_not_ready")
    if not rodrigues_terms_ready:
        blockers.append("rodrigues_terms_not_joined")

    component_blueprint = {
        "axis_nondegeneracy_contract": {
            "axis_norm_square_lower_bound": r43["record"].get("axis_norm_square_lower_bound"),
            "ready": axis_ready,
            "source_record": r43["record_path"],
        },
        "finite_component_bound_seed": finite_component_bound_seed(partition_record),
        "lower_piece": lower,
        "rodrigues_terms": {
            "ready": rodrigues_terms_ready,
            "source_record": r39["record_path"],
            "value": rodrigues_terms,
        },
        "support_state_for_formula_shape": {
            "lower_non_support_labels": lower["non_support_labels"],
            "lower_support_labels": lower["support_labels"],
            "status": "backend_blocked",
            "support_signature": partition_record["support_signature"],
            "upper_non_support_labels": upper["non_support_labels"],
            "upper_support_labels": upper["support_labels"],
        },
        "upper_piece": upper,
    }

    object_status = (
        "component_bound_blueprint_ready_interval_extractor_blocked"
        if support_common_only
        else "component_bound_blueprint_ready_outer_endpoint_propagation_blocked"
    )
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers + lower["blockers"] + upper["blockers"])),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_motion_bound_blueprint": component_blueprint,
        "component_motion_bound_blueprint_ready": True,
        "component_motion_bounds_ready": False,
        "domain_family": partition_record.get("domain_family"),
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "input_r39_formula_bridge_record": r39["record_path"],
        "input_r42_rodrigues_interval_record": r42["record_path"],
        "input_r43_axis_norm_record": r43["record_path"],
        "input_r47_support_partition_record": partition_summary["object_record"],
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-COMPONENT-MOTION-BOUND-OBJECT-{sanitize(original_id)}-"
            f"PART-{int(partition_record['partition_index']):02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": partition_record.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_record.get("partition_index"),
        "piece_pair": partition_record.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "support_partition_key": partition_record.get("support_partition_key"),
        "support_signature": partition_record.get("support_signature"),
        "support_uses_common_edge_labels_only": support_common_only,
        "tree_id": partition_record.get("tree_id"),
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / sanitize(original_id)
        / f"partition_{int(record['partition_index']):02d}_component_motion_bound_object.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "component_motion_bound_blueprint_ready": True,
        "component_motion_bounds_ready": False,
        "domain_family": record["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": record["original_report"],
        "original_report_id": original_id,
        "partition_index": record["partition_index"],
        "piece_pair": record["piece_pair"],
        "support_signature": record["support_signature"],
        "support_uses_common_edge_labels_only": support_common_only,
        "tree_id": record["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r47-manifest", default=DEFAULT_R47_MANIFEST.as_posix())
    parser.add_argument("--r39-manifest", default=DEFAULT_R39_MANIFEST.as_posix())
    parser.add_argument("--r42-manifest", default=DEFAULT_R42_MANIFEST.as_posix())
    parser.add_argument("--r43-manifest", default=DEFAULT_R43_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r47_path = ROOT / args.r47_manifest
    r39_path = ROOT / args.r39_manifest
    r42_path = ROOT / args.r42_manifest
    r43_path = ROOT / args.r43_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r39_index = index_r39_bridge_records(r39_path)
    r42_index = index_records_by_original_id(r42_path, list_key="records", path_key="object_record")
    r43_index = index_records_by_original_id(r43_path, list_key="records", path_key="object_record")
    r47_records = load_manifest_records(r47_path, "records")

    records: list[dict[str, Any]] = []
    for summary in r47_records:
        partition_record = read_json(ROOT / summary["object_record"])
        records.append(
            build_component_record(
                partition_summary=summary,
                partition_record=partition_record,
                r39_index=r39_index,
                r42_index=r42_index,
                r43_index=r43_index,
                out_dir=out_dir,
            )
        )

    status_counts = Counter(item["object_status"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)
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
        "common_edge_support_only_partition_count": sum(
            1 for item in records if item["support_uses_common_edge_labels_only"]
        ),
        "component_motion_bound_blueprint_ready_count": sum(
            1 for item in records if item["component_motion_bound_blueprint_ready"]
        ),
        "component_motion_bounds_ready_count": 0,
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "input_r39_manifest": rel(r39_path),
        "input_r42_manifest": rel(r42_path),
        "input_r43_manifest": rel(r43_path),
        "input_r47_manifest": rel(r47_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "outer_vertex_support_partition_count": sum(
            1 for item in records if not item["support_uses_common_edge_labels_only"]
        ),
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R49: implement the exact/outward-rounded component-bound extractor: "
            "propagate endpoint intervals for outer support labels where needed, "
            "emit normalized-axis projection component intervals, and keep "
            "M_gap/M_L/M_U extraction blocked until those intervals are ready."
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R47 records: {len(r47_records)}")
    print(f"component-bound blueprints emitted: {manifest['object_record_count']}")
    print(
        "common-edge-only support partitions: "
        f"{manifest['common_edge_support_only_partition_count']}"
    )
    print(
        "outer-vertex support partitions: "
        f"{manifest['outer_vertex_support_partition_count']}"
    )
    print(
        "component motion bound blueprints ready: "
        f"{manifest['component_motion_bound_blueprint_ready_count']}"
    )
    print(f"component motion bounds ready: {manifest['component_motion_bounds_ready_count']}")
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
