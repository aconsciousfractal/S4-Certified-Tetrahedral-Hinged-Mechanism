#!/usr/bin/env python
"""
Build B05 center-projection and non-support endpoint operand records.

R54 consumes the R53 geometric seed arithmetic operand records.  It replays the
R42 Rodrigues interval-composition backend on the full local S4 endpoint label
set needed by each support partition, instead of only the common-edge labels
M_AB and M_CD.  This makes A/B/C/D endpoint coordinate interval packages
available for later component-bound and support-stability extraction.

It also emits a center-projection numerator interval attempt from the available
common-edge axis and full endpoint intervals.  That attempt is intentionally not
promoted to an exact positive g0 interval: the current full-domain interval
contains zero/has unresolved orientation in the real records, so center-gap
acceptance remains blocked.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-CENTER-PROJECTION-NON-SUPPORT-ENDPOINT-BACKEND-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_CENTER_PROJECTION_NON_SUPPORT_ENDPOINT_BACKEND"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R53_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_geometric_seed_arithmetic_backend_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "center_projection_non_support_endpoint_backend"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_center_projection_non_support_endpoint_backend_manifest.json"
)

R42_MODULE_PATH = SCRIPT_PATH.with_name("build_s4_cl5_b05_rodrigues_interval_composition_backend.py")
PIECE_LABELS = {
    "P0": ["A", "M_AB", "C", "M_CD"],
    "P1": ["A", "M_AB", "D", "M_CD"],
    "P2": ["B", "M_AB", "C", "M_CD"],
    "P3": ["B", "M_AB", "D", "M_CD"],
}

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_positive_g0_center_gap_interval_claim",
    "no_per_side_c_L_c_U_support_competition_interval_claim",
    "no_tau_outward_error_interval_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
    "no_formula_shape_real_report_claim",
    "no_theorem_promotion_claim",
]


def load_r42_backend():
    spec = importlib.util.spec_from_file_location("b05_r42_rodrigues_backend", R42_MODULE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import R42 backend: {R42_MODULE_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R42 = load_r42_backend()
Interval = tuple[Fraction, Fraction]
Vector = list[Interval]


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


def frac_obj(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_json(interval: Interval, *, unit: str, source_expr: str) -> dict[str, Any]:
    lo, hi = interval
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(hi),
        "lo": frac_obj(lo),
        "source_expr": source_expr,
        "unit": unit,
    }


def vector_from_json(vector: dict[str, Any]) -> Vector:
    coords = vector.get("coordinates")
    if not isinstance(coords, list):
        raise TypeError("vector coordinates missing")
    return [R42.fraction_from_interval_json(coord) for coord in coords]


def coordinate_width(coord_interval: dict[str, Any]) -> Fraction:
    lo, hi = R42.fraction_from_interval_json(coord_interval)
    return hi - lo


def endpoint_l1_diameter(endpoint: dict[str, Any]) -> dict[str, Any]:
    coords = endpoint.get("coordinates") or []
    order = endpoint.get("coordinate_order") or []
    total = Fraction(0)
    widths = []
    for axis, coord in zip(order, coords):
        width = abs(coordinate_width(coord))
        total += width
        widths.append({
            "axis": str(axis),
            "interval_width": frac_obj(width),
            "source_expr": coord.get("source_expr"),
        })
    return {
        "coordinate_l1_diameter_bound": frac_obj(total),
        "coordinate_widths": widths,
        "source_rule": "|u dot (x-y)| <= ||x-y||_1 for unit projection direction u",
    }


def load_manifest_records(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"records must be a list: {manifest_path}")
    return records


def load_chain(r53_record: dict[str, Any]) -> dict[str, Any]:
    r50_path = ROOT / r53_record["input_r50_m_gap_m_l_m_u_attempt_record"]
    r50 = read_json(r50_path)
    r49_path = ROOT / r50["input_r49_component_bound_interval_record"]
    r49 = read_json(r49_path)
    r48_path = ROOT / r49["input_r48_component_motion_bound_object_record"]
    r48 = read_json(r48_path)
    r42_path = ROOT / r48["input_r42_rodrigues_interval_record"]
    r43_path = ROOT / r48["input_r43_axis_norm_record"]
    r42 = read_json(r42_path)
    r43 = read_json(r43_path)
    r40_path = ROOT / r42["input_r40_axis_endpoint_record"]
    r41_path = ROOT / r42["input_r41_trig_fraction_record"]
    return {
        "r40": read_json(r40_path),
        "r40_path": r40_path,
        "r41": read_json(r41_path),
        "r41_path": r41_path,
        "r42": r42,
        "r42_path": r42_path,
        "r43": r43,
        "r43_path": r43_path,
        "r48": r48,
        "r48_path": r48_path,
        "r49": r49,
        "r49_path": r49_path,
        "r50": r50,
        "r50_path": r50_path,
    }


def piece_blueprint(r48_record: dict[str, Any], role: str) -> dict[str, Any]:
    blueprint = r48_record.get("component_motion_bound_blueprint")
    if not isinstance(blueprint, dict):
        return {}
    item = blueprint.get(role)
    return item if isinstance(item, dict) else {}


def replay_full_endpoint_package(
    *,
    r40_record: dict[str, Any],
    r41_record: dict[str, Any],
    piece_id: str,
) -> dict[str, Any]:
    labels = PIECE_LABELS[piece_id]
    steps = R42.transform_steps_for_piece(r40_record, piece_id)
    trig_map = R42.trig_by_hinge(r41_record)
    endpoints: dict[str, Any] = {}
    diameters: dict[str, Any] = {}
    for label in labels:
        vector = R42.apply_transform_path(label, steps, trig_map)
        endpoints[label] = R42.vector_json(
            vector,
            source_expr=f"{piece_id}_{label}_r54_full_endpoint_rodrigues_interval",
        )
        diameters[label] = endpoint_l1_diameter(endpoints[label])
    return {
        "all_piece_labels": labels,
        "endpoints": endpoints,
        "endpoint_coordinate_l1_diameter_bounds": diameters,
        "full_endpoint_coordinate_intervals_ready": True,
        "piece_id": piece_id,
        "source_status": "full_piece_endpoint_coordinate_intervals_emitted",
        "transform_step_count": len(steps),
    }


def coverage(piece_package: dict[str, Any], labels: list[str]) -> dict[str, Any]:
    endpoints = piece_package.get("endpoints") or {}
    missing = [label for label in labels if label not in endpoints]
    return {
        "available": not missing,
        "available_labels": [label for label in labels if label in endpoints],
        "missing_labels": missing,
        "piece_id": piece_package.get("piece_id"),
        "requested_labels": labels,
    }


def projection_summary(axis: Vector, endpoint_package: dict[str, Any], labels: list[str]) -> dict[str, Any]:
    projections = []
    for label in labels:
        endpoint = endpoint_package["endpoints"][label]
        value = R42.v_dot(axis, vector_from_json(endpoint))
        projections.append({
            "label": label,
            "projection_numerator_interval": interval_json(
                value,
                unit="axis_dot_coordinate",
                source_expr=f"dot(axis_cross,{endpoint_package['piece_id']}_{label})",
            ),
        })
    los = [R42.fraction_from_interval_json(p["projection_numerator_interval"])[0] for p in projections]
    his = [R42.fraction_from_interval_json(p["projection_numerator_interval"])[1] for p in projections]
    return {
        "projection_numerator_intervals_by_label": projections,
        "max_projection_interval_enclosure": interval_json(
            (max(los), max(his)),
            unit="axis_dot_coordinate",
            source_expr="max_support_projection_interval_enclosure",
        ),
        "min_projection_interval_enclosure": interval_json(
            (min(los), min(his)),
            unit="axis_dot_coordinate",
            source_expr="min_support_projection_interval_enclosure",
        ),
    }


def center_projection_attempt(
    *,
    r42_record: dict[str, Any],
    lower_package: dict[str, Any],
    upper_package: dict[str, Any],
    lower_support_labels: list[str],
    upper_support_labels: list[str],
) -> dict[str, Any]:
    axis = vector_from_json(r42_record["axis_cross_product_interval"])
    lower = projection_summary(axis, lower_package, lower_support_labels)
    upper = projection_summary(axis, upper_package, upper_support_labels)
    upper_min = R42.fraction_from_interval_json(upper["min_projection_interval_enclosure"])
    lower_max = R42.fraction_from_interval_json(lower["max_projection_interval_enclosure"])
    raw_gap = R42.i_sub(upper_min, lower_max)
    flipped_gap = R42.i_neg(raw_gap)
    if raw_gap[0] > 0:
        orientation_status = "raw_axis_orientation_positive"
        oriented = raw_gap
    elif raw_gap[1] < 0:
        orientation_status = "flipped_axis_orientation_positive"
        oriented = flipped_gap
    else:
        orientation_status = "blocked_interval_contains_zero_or_orientation_not_isolated"
        oriented = raw_gap
    return {
        "axis_source": "R42_axis_cross_product_interval",
        "center_projection_numerator_interval_ready": True,
        "g0_center_gap_interval_ready": False,
        "lower_support_projection": lower,
        "orientation_status": orientation_status,
        "oriented_gap_numerator_interval": interval_json(
            oriented,
            unit="axis_dot_coordinate",
            source_expr="oriented_min_upper_support_minus_max_lower_support_axis_numerator",
        ),
        "raw_gap_numerator_interval": interval_json(
            raw_gap,
            unit="axis_dot_coordinate",
            source_expr="min_upper_support_minus_max_lower_support_axis_numerator",
        ),
        "reason_not_g0": (
            "full-domain projection numerator is an interval operand only; current real records do not isolate "
            "a positive center support gap or accepted unit-axis normalization/orientation enclosure"
        ),
        "source_identity_id": SOURCE_IDENTITY_ID,
        "upper_support_projection": upper,
    }


def build_record(r53_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r53_path = ROOT / r53_summary["object_record"]
    r53 = read_json(r53_path)
    chain = load_chain(r53)
    r48 = chain["r48"]
    r50 = chain["r50"]
    lower_bp = piece_blueprint(r48, "lower_piece")
    upper_bp = piece_blueprint(r48, "upper_piece")
    lower_piece = str(lower_bp.get("piece_id"))
    upper_piece = str(upper_bp.get("piece_id"))
    if lower_piece not in PIECE_LABELS or upper_piece not in PIECE_LABELS:
        raise ValueError(f"unexpected piece ids: {lower_piece}, {upper_piece}")

    lower_support = [str(label) for label in lower_bp.get("support_labels") or []]
    upper_support = [str(label) for label in upper_bp.get("support_labels") or []]
    lower_non_support = [str(label) for label in lower_bp.get("non_support_labels") or []]
    upper_non_support = [str(label) for label in upper_bp.get("non_support_labels") or []]

    lower_package = replay_full_endpoint_package(
        r40_record=chain["r40"],
        r41_record=chain["r41"],
        piece_id=lower_piece,
    )
    upper_package = replay_full_endpoint_package(
        r40_record=chain["r40"],
        r41_record=chain["r41"],
        piece_id=upper_piece,
    )
    lower_support_coverage = coverage(lower_package, lower_support)
    upper_support_coverage = coverage(upper_package, upper_support)
    lower_non_support_coverage = coverage(lower_package, lower_non_support)
    upper_non_support_coverage = coverage(upper_package, upper_non_support)
    support_ready = lower_support_coverage["available"] and upper_support_coverage["available"]
    non_support_ready = lower_non_support_coverage["available"] and upper_non_support_coverage["available"]
    full_endpoint_ready = support_ready and non_support_ready

    projection_attempt = center_projection_attempt(
        r42_record=chain["r42"],
        lower_package=lower_package,
        upper_package=upper_package,
        lower_support_labels=lower_support,
        upper_support_labels=upper_support,
    )
    center_projection_ready = bool(projection_attempt["center_projection_numerator_interval_ready"])
    formula_ready = isinstance(r50.get("exact_gap_formula_skeleton"), dict)
    diagnostic_positive = bool(r53_summary.get("diagnostic_positive_signed_component_candidate"))
    component_reextract_ready = full_endpoint_ready

    blockers = {
        "accepted_report_promotion_out_of_scope",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
        "g0_center_gap_interval_not_promoted_from_full_domain_projection_attempt",
        "per_side_c_L_c_U_support_competition_reextract_missing",
        "tau_outward_error_interval_missing",
        "positive_M_gap_M_L_M_U_not_extracted",
    }
    if not formula_ready:
        blockers.add("formula_skeleton_missing_until_component_bounds_are_reextracted")
    if not diagnostic_positive:
        blockers.add("diagnostic_signed_component_margin_nonpositive_or_missing")
    if not support_ready:
        blockers.add("support_endpoint_coordinate_intervals_still_missing")
    if not non_support_ready:
        blockers.add("non_support_endpoint_coordinate_intervals_still_missing")
    if projection_attempt["orientation_status"] == "blocked_interval_contains_zero_or_orientation_not_isolated":
        blockers.add("center_projection_full_domain_interval_contains_zero_or_orientation_not_isolated")

    if not formula_ready and component_reextract_ready:
        object_status = "center_projection_non_support_endpoint_ready_component_reextract_required"
    elif not diagnostic_positive:
        object_status = "center_projection_non_support_endpoint_ready_diagnostic_nonpositive_margin"
    elif full_endpoint_ready and center_projection_ready:
        object_status = "center_projection_non_support_endpoint_ready_g0_blocked"
    else:
        object_status = "center_projection_non_support_endpoint_incomplete"

    original_id = str(r53["original_report_id"])
    partition_index = int(r53["partition_index"])
    domain = str(r53["domain_family"])
    out_path = (
        out_dir
        / sanitize(domain)
        / sanitize(original_id)
        / f"partition_{partition_index:02d}_center_projection_non_support_endpoint.json"
    )
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "center_projection_attempt": projection_attempt,
        "center_projection_numerator_interval_ready": center_projection_ready,
        "claim_level": CLAIM_LEVEL,
        "component_bound_reextract_ready_from_full_endpoints": component_reextract_ready,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "full_endpoint_coordinate_interval_packages": {
            "lower_piece": lower_package,
            "upper_piece": upper_package,
        },
        "full_endpoint_coordinate_intervals_ready": full_endpoint_ready,
        "g0_center_gap_interval_ready": False,
        "input_r40_axis_endpoint_record": rel(chain["r40_path"]),
        "input_r41_trig_fraction_record": rel(chain["r41_path"]),
        "input_r42_rodrigues_interval_record": rel(chain["r42_path"]),
        "input_r43_axis_norm_record": rel(chain["r43_path"]),
        "input_r48_component_motion_bound_object_record": rel(chain["r48_path"]),
        "input_r49_component_bound_interval_record": rel(chain["r49_path"]),
        "input_r50_m_gap_m_l_m_u_attempt_record": rel(chain["r50_path"]),
        "input_r53_geometric_seed_arithmetic_record": rel(r53_path),
        "manifest_id": MANIFEST_ID,
        "non_support_endpoint_coordinate_intervals_ready": non_support_ready,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"S4-CL5-B05-CENTER-PROJECTION-NON-SUPPORT-ENDPOINT-"
            f"{sanitize(original_id).upper()}-PARTITION-{partition_index:02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r53.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r53.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "source_identity_id": SOURCE_IDENTITY_ID,
        "support_endpoint_coordinate_intervals_ready": support_ready,
        "support_non_support_coverage": {
            "lower_non_support_endpoint_coverage": lower_non_support_coverage,
            "lower_support_endpoint_coverage": lower_support_coverage,
            "upper_non_support_endpoint_coverage": upper_non_support_coverage,
            "upper_support_endpoint_coverage": upper_support_coverage,
        },
        "support_signature": r53.get("support_signature"),
        "tau_outward_error_interval_ready": False,
        "tree_id": r53.get("tree_id"),
    }
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "center_projection_numerator_interval_ready": center_projection_ready,
        "component_bound_reextract_ready_from_full_endpoints": component_reextract_ready,
        "diagnostic_positive_signed_component_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "full_endpoint_coordinate_intervals_ready": full_endpoint_ready,
        "g0_center_gap_interval_ready": False,
        "non_support_endpoint_coordinate_intervals_ready": non_support_ready,
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r53.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r53.get("piece_pair"),
        "support_endpoint_coordinate_intervals_ready": support_ready,
        "support_signature": r53.get("support_signature"),
        "tau_outward_error_interval_ready": False,
        "tree_id": r53.get("tree_id"),
    }


def build_manifest(records: list[dict[str, Any]], r53_manifest: Path) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    domain_counts = Counter(record["domain_family"] for record in records)
    return {
        "accepted_real_b05_report_count": sum(1 for r in records if r["accepted_real_b05_report"]),
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "center_projection_numerator_interval_ready_count": sum(
            1 for r in records if r["center_projection_numerator_interval_ready"]
        ),
        "claim_level": CLAIM_LEVEL,
        "component_bound_reextract_ready_from_full_endpoints_count": sum(
            1 for r in records if r["component_bound_reextract_ready_from_full_endpoints"]
        ),
        "diagnostic_positive_signed_component_candidate_count": sum(
            1 for r in records if r["diagnostic_positive_signed_component_candidate"]
        ),
        "exact_M_gap_M_L_M_U_ready_count": sum(1 for r in records if r["exact_M_gap_M_L_M_U_ready"]),
        "formula_shape_contract_ready_count": sum(1 for r in records if r["formula_shape_contract_ready"]),
        "full_endpoint_coordinate_intervals_ready_count": sum(
            1 for r in records if r["full_endpoint_coordinate_intervals_ready"]
        ),
        "g0_center_gap_interval_ready_count": sum(1 for r in records if r["g0_center_gap_interval_ready"]),
        "input_r53_manifest": rel(r53_manifest),
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
            "Consume R54 full endpoint records to re-run component-bound extraction for all 23 "
            "support partitions, then rebuild M_gap/M_L/M_U formula skeletons."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "support_endpoint_coordinate_intervals_ready_count": sum(
            1 for r in records if r["support_endpoint_coordinate_intervals_ready"]
        ),
        "tau_outward_error_interval_ready_count": sum(1 for r in records if r["tau_outward_error_interval_ready"]),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r53-manifest", type=Path, default=DEFAULT_R53_MANIFEST)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    args = parser.parse_args(argv)

    r53_manifest = ROOT / args.r53_manifest
    out_dir = ROOT / args.out_dir
    records = [build_record(summary, out_dir) for summary in load_manifest_records(r53_manifest)]
    manifest = build_manifest(records, r53_manifest)
    write_json_lf(ROOT / args.manifest, manifest)

    print(f"input R53 records: {len(records)}")
    print(f"center projection/non-support endpoint records emitted: {len(records)}")
    print(f"full endpoint coordinate intervals ready: {manifest['full_endpoint_coordinate_intervals_ready_count']}")
    print(f"support endpoint coordinate intervals ready: {manifest['support_endpoint_coordinate_intervals_ready_count']}")
    print(f"non-support endpoint coordinate intervals ready: {manifest['non_support_endpoint_coordinate_intervals_ready_count']}")
    print(f"center projection numerator intervals ready: {manifest['center_projection_numerator_interval_ready_count']}")
    print(f"component-bound reextract candidates ready: {manifest['component_bound_reextract_ready_from_full_endpoints_count']}")
    print(f"g0 center gap intervals ready: {manifest['g0_center_gap_interval_ready_count']}")
    print(f"per-side support competition intervals ready: {manifest['per_side_support_competition_intervals_ready_count']}")
    print(f"tau outward error intervals ready: {manifest['tau_outward_error_interval_ready_count']}")
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(ROOT / args.manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
