#!/usr/bin/env python
"""
Extract conservative B05 component-bound interval envelopes per support partition.

R49 consumes the R48 component-motion-bound blueprint records.  For support
partitions whose support labels are already covered by the R42 Rodrigues
endpoint-coordinate intervals, it emits checker-shaped lower/upper component
interval maps with rational nonnegative bounds.  The bound used here is a
conservative coordinate-diameter projection envelope: for a unit projection
axis u and an endpoint coordinate interval box X, the projection variation is
bounded by the L1 coordinate diameter of X.

This is still not an accepted B05 report layer.  It does not emit M_gap/M_L/M_U,
operation enclosures, or real formula_shape reports.  Partitions whose support
labels require outer vertices A/B/C/D remain blocked until endpoint-coordinate
propagation exists for those labels.
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
MANIFEST_ID = "S4-CL5-B05-COMPONENT-BOUND-INTERVAL-EXTRACTOR-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_COMPONENT_BOUND_INTERVAL_EXTRACTOR"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
BOUND_RULE_ID = "R49-L1-COORDINATE-DIAMETER-PROJECTION-ENVELOPE"

DEFAULT_R48_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_component_motion_bound_objects_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "component_bound_interval_extractor"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_component_bound_interval_extractor_manifest.json"
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


def load_manifest_records(manifest_path: Path, record_key: str = "records") -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get(record_key) or []
    if not isinstance(records, list):
        raise TypeError(f"{record_key} must be a list: {manifest_path}")
    return records


def frac(value: dict[str, Any]) -> Fraction:
    return Fraction(int(value["num"]), int(value["den"]))


def frac_obj(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_obj(*, lo: Fraction, hi: Fraction, unit: str, source_expr: str) -> dict[str, Any]:
    if lo < 0 or hi < lo:
        raise ValueError(f"invalid nonnegative interval: {lo}..{hi}")
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(hi),
        "lo": frac_obj(lo),
        "source_expr": source_expr,
        "unit": unit,
    }


def coordinate_width(coord_interval: dict[str, Any]) -> Fraction:
    return frac(coord_interval["hi"]) - frac(coord_interval["lo"])


def endpoint_l1_diameter(endpoint: dict[str, Any]) -> tuple[Fraction, list[dict[str, Any]]]:
    coords = endpoint.get("coordinates")
    order = endpoint.get("coordinate_order")
    if not isinstance(coords, list) or not isinstance(order, list):
        raise TypeError("endpoint coordinate interval has wrong shape")
    widths: list[dict[str, Any]] = []
    total = Fraction(0)
    for axis, coord in zip(order, coords):
        width = abs(coordinate_width(coord))
        total += width
        widths.append({
            "axis": str(axis),
            "interval_width": frac_obj(width),
            "source_expr": coord.get("source_expr"),
        })
    return total, widths


def piece_endpoint_map(r42_record: dict[str, Any], piece_id: str) -> dict[str, Any]:
    intervals = r42_record.get("endpoint_coordinate_intervals")
    if not isinstance(intervals, dict):
        return {}
    piece = intervals.get(piece_id)
    if not isinstance(piece, dict):
        return {}
    endpoints = piece.get("endpoints")
    if not isinstance(endpoints, dict):
        return {}
    return endpoints


def build_piece_bounds(piece_blueprint: dict[str, Any], r42_record: dict[str, Any]) -> dict[str, Any]:
    piece_id = str(piece_blueprint["piece_id"])
    role = str(piece_blueprint["role"])
    support_labels = [str(label) for label in piece_blueprint.get("support_labels") or []]
    required_names = [str(name) for name in piece_blueprint.get("required_component_bound_names") or []]
    endpoints = piece_endpoint_map(r42_record, piece_id)
    missing_support = [label for label in support_labels if label not in endpoints]
    label_diameters = []
    max_diameter = Fraction(0)
    for label in support_labels:
        if label not in endpoints:
            continue
        diameter, widths = endpoint_l1_diameter(endpoints[label])
        if diameter > max_diameter:
            max_diameter = diameter
        label_diameters.append({
            "coordinate_l1_diameter_bound": frac_obj(diameter),
            "coordinate_widths": widths,
            "label": label,
            "source_rule": "|u dot (x-x0)| <= ||x-x0||_1 for unit projection direction u",
        })

    ready = bool(required_names) and not missing_support and bool(support_labels)
    interval_bounds = {}
    if ready:
        for name in required_names:
            interval_bounds[name] = interval_obj(
                lo=Fraction(0),
                hi=max_diameter,
                unit="projection",
                source_expr=(
                    f"{name}:max_endpoint_L1_coordinate_diameter_envelope"
                    f"({piece_id};{','.join(support_labels)})"
                ),
            )

    blockers = []
    if missing_support:
        blockers.append("support_label_endpoint_coordinate_intervals_missing")
    if not ready:
        blockers.append("component_interval_bounds_not_emitted")

    checker_shape_piece = dict(interval_bounds)
    checker_shape_piece["piece_id"] = piece_id
    checker_shape_piece["support_labels"] = support_labels
    checker_shape_piece["bound_rule_id"] = BOUND_RULE_ID

    return {
        "blockers": blockers,
        "checker_shape_piece": checker_shape_piece,
        "component_interval_bounds": interval_bounds,
        "component_interval_bounds_ready": ready,
        "label_coordinate_diameter_bounds": label_diameters,
        "max_coordinate_l1_diameter_bound": frac_obj(max_diameter),
        "missing_support_endpoint_coordinate_labels": missing_support,
        "piece_id": piece_id,
        "required_component_bound_names": required_names,
        "role": role,
        "source_endpoint_interval_piece_available": bool(endpoints),
        "support_labels": support_labels,
    }


def rodrigues_terms_from_blueprint(r48_record: dict[str, Any]) -> dict[str, Any] | None:
    blueprint = r48_record.get("component_motion_bound_blueprint")
    if not isinstance(blueprint, dict):
        return None
    terms = blueprint.get("rodrigues_terms")
    if isinstance(terms, dict) and isinstance(terms.get("value"), dict):
        return terms["value"]
    return None


def build_interval_record(r48_summary: dict[str, Any], r48_record: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    blueprint = r48_record["component_motion_bound_blueprint"]
    r42_path = ROOT / r48_record["input_r42_rodrigues_interval_record"]
    r42_record = read_json(r42_path)
    lower = build_piece_bounds(blueprint["lower_piece"], r42_record)
    upper = build_piece_bounds(blueprint["upper_piece"], r42_record)
    rodrigues_terms = rodrigues_terms_from_blueprint(r48_record)
    rodrigues_ready = rodrigues_terms is not None
    component_ready = (
        lower["component_interval_bounds_ready"]
        and upper["component_interval_bounds_ready"]
        and rodrigues_ready
    )
    missing_non_support = []
    for role in ["lower_piece", "upper_piece"]:
        part = blueprint.get(role, {})
        if isinstance(part, dict):
            missing_non_support.extend(part.get("missing_non_support_endpoint_coordinate_labels") or [])

    blockers = [
        "exact_M_gap_M_L_M_U_interval_extractor_missing",
        "operation_enclosures_missing",
        "formula_shape_real_report_not_emitted",
        "accepted_report_promotion_out_of_scope",
    ]
    blockers.extend(lower["blockers"])
    blockers.extend(upper["blockers"])
    if missing_non_support:
        blockers.append("non_support_label_endpoint_coordinate_intervals_missing_for_stability_M_L_M_U")
    if not rodrigues_ready:
        blockers.append("rodrigues_terms_not_joined")

    object_status = (
        "component_bound_interval_envelopes_ready_M_gap_extractor_blocked"
        if component_ready
        else "component_bound_interval_envelopes_blocked_outer_endpoint_propagation_required"
    )
    component_motion_bounds_candidate = {
        "bound_rule_id": BOUND_RULE_ID,
        "bound_rule_semantics": (
            "Conservative rational projection envelope from endpoint coordinate interval L1 diameters; "
            "not an accepted report without operation enclosures and M_gap/M_L/M_U intervals."
        ),
        "lower_piece": lower["checker_shape_piece"],
        "rodrigues_terms": rodrigues_terms,
        "upper_piece": upper["checker_shape_piece"],
    }
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers)),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_bound_interval_envelope_ready": component_ready,
        "component_bound_interval_extraction": {
            "bound_rule_id": BOUND_RULE_ID,
            "lower_piece": lower,
            "upper_piece": upper,
        },
        "component_motion_bounds_candidate": component_motion_bounds_candidate,
        "component_motion_bounds_ready": component_ready,
        "domain_family": r48_record.get("domain_family"),
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "input_r42_rodrigues_interval_record": rel(r42_path),
        "input_r48_component_motion_bound_object_record": r48_summary["object_record"],
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-COMPONENT-BOUND-INTERVAL-{sanitize(r48_record['original_report_id'])}-"
            f"PART-{int(r48_record['partition_index']):02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r48_record.get("original_report"),
        "original_report_id": r48_record.get("original_report_id"),
        "partition_index": r48_record.get("partition_index"),
        "piece_pair": r48_record.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "support_signature": r48_record.get("support_signature"),
        "support_uses_common_edge_labels_only": r48_record.get("support_uses_common_edge_labels_only"),
        "tree_id": r48_record.get("tree_id"),
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / sanitize(record["original_report_id"])
        / f"partition_{int(record['partition_index']):02d}_component_bound_interval.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "component_bound_interval_envelope_ready": component_ready,
        "component_motion_bounds_ready": component_ready,
        "domain_family": record["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
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
    parser.add_argument("--r48-manifest", default=DEFAULT_R48_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r48_path = ROOT / args.r48_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    records: list[dict[str, Any]] = []
    for summary in load_manifest_records(r48_path, "records"):
        r48_record = read_json(ROOT / summary["object_record"])
        records.append(build_interval_record(summary, r48_record, out_dir))

    status_counts = Counter(item["object_status"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)
    blocker_counts = Counter()
    missing_support_labels = Counter()
    for item in records:
        record = read_json(ROOT / item["object_record"])
        blocker_counts.update(record["blockers"])
        for role in ["lower_piece", "upper_piece"]:
            missing = record["component_bound_interval_extraction"][role][
                "missing_support_endpoint_coordinate_labels"
            ]
            missing_support_labels.update(missing)

    ready_count = sum(1 for item in records if item["component_motion_bounds_ready"])
    manifest = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "component_bound_interval_envelope_ready_count": ready_count,
        "component_motion_bounds_ready_count": ready_count,
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "input_r48_manifest": rel(r48_path),
        "manifest_id": MANIFEST_ID,
        "missing_support_endpoint_label_counts": dict(sorted(missing_support_labels.items())),
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "outer_endpoint_propagation_blocked_count": sum(
            1 for item in records if not item["component_motion_bounds_ready"]
        ),
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R50: extract positive B05 M_gap/M_L/M_U interval margins from R49 "
            "component-bound interval envelopes where available, while keeping outer-endpoint "
            "partitions and operation-enclosure promotion blocked."
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R48 records: {len(records)}")
    print(f"component-bound interval records emitted: {manifest['object_record_count']}")
    print(
        "component-bound interval envelopes ready: "
        f"{manifest['component_bound_interval_envelope_ready_count']}"
    )
    print(f"component motion bounds ready: {manifest['component_motion_bounds_ready_count']}")
    print(
        "outer endpoint propagation blocked records: "
        f"{manifest['outer_endpoint_propagation_blocked_count']}"
    )
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"missing support endpoint label counts: {manifest['missing_support_endpoint_label_counts']}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())