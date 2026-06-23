#!/usr/bin/env python
"""
Attempt B05 g0 and support-competition seed isolation from R55 skeletons.

R56 consumes the R55 full-endpoint component-bound/margin skeleton records and
recomputes exact rational numerator intervals for:

* the center support gap candidate g0;
* the lower support-competition candidate c_L;
* the upper support-competition candidate c_U.

The extraction is deliberately strict.  A finite seed interval is marked ready
only when its lower endpoint is strictly positive.  If a side has no
non-support labels, the support-competition condition is recorded as vacuous,
but not counted as a positive finite interval.  Diagnostic finite floats are
not copied into accepted seed intervals.
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
MANIFEST_ID = "S4-CL5-B05-G0-SUPPORT-COMPETITION-SEED-ISOLATION-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_G0_SUPPORT_COMPETITION_SEED_ISOLATION"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R55_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_component_bound_margin_skeleton_reextract_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "g0_support_competition_seed_isolation"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_g0_support_competition_seed_isolation_manifest.json"
)

R42_MODULE_PATH = SCRIPT_PATH.with_name("build_s4_cl5_b05_rodrigues_interval_composition_backend.py")

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_positive_g0_center_gap_interval_claim_unless_record_says_ready",
    "no_positive_per_side_c_L_c_U_claim_unless_record_says_ready",
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
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(interval[1]),
        "lo": frac_obj(interval[0]),
        "source_expr": source_expr,
        "unit": unit,
    }


def vector_from_json(vector: dict[str, Any]) -> Vector:
    coords = vector.get("coordinates")
    if not isinstance(coords, list):
        raise TypeError("vector coordinates missing")
    return [R42.fraction_from_interval_json(coord) for coord in coords]


def load_manifest_records(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"records must be a list: {manifest_path}")
    return records


def projection_intervals(axis: Vector, package: dict[str, Any], labels: list[str]) -> list[dict[str, Any]]:
    out = []
    endpoints = package.get("endpoints") or {}
    for label in labels:
        if label not in endpoints:
            raise KeyError(f"endpoint label missing from package: {package.get('piece_id')} {label}")
        interval = R42.v_dot(axis, vector_from_json(endpoints[label]))
        out.append({
            "label": label,
            "projection_numerator_interval": interval_json(
                interval,
                unit="axis_dot_coordinate",
                source_expr=f"dot(axis_cross,{package.get('piece_id')}_{label})",
            ),
        })
    return out


def interval_from_projection(item: dict[str, Any]) -> Interval:
    return R42.fraction_from_interval_json(item["projection_numerator_interval"])


def max_enclosure(projections: list[dict[str, Any]], source_expr: str) -> dict[str, Any]:
    intervals = [interval_from_projection(item) for item in projections]
    return interval_json(
        (max(item[0] for item in intervals), max(item[1] for item in intervals)),
        unit="axis_dot_coordinate",
        source_expr=source_expr,
    )


def min_enclosure(projections: list[dict[str, Any]], source_expr: str) -> dict[str, Any]:
    intervals = [interval_from_projection(item) for item in projections]
    return interval_json(
        (min(item[0] for item in intervals), min(item[1] for item in intervals)),
        unit="axis_dot_coordinate",
        source_expr=source_expr,
    )


def positive_ready(interval: Interval) -> bool:
    return interval[0] > 0


def build_projection_summary(axis: Vector, package: dict[str, Any], labels: list[str], role: str) -> dict[str, Any]:
    projections = projection_intervals(axis, package, labels)
    return {
        "labels": labels,
        "max_projection_interval_enclosure": max_enclosure(
            projections,
            f"{role}_max_projection_interval_enclosure",
        ),
        "min_projection_interval_enclosure": min_enclosure(
            projections,
            f"{role}_min_projection_interval_enclosure",
        ),
        "piece_id": package.get("piece_id"),
        "projection_numerator_intervals_by_label": projections,
    }


def build_g0_attempt(axis: Vector, lower_pkg: dict[str, Any], upper_pkg: dict[str, Any],
                     lower_support: list[str], upper_support: list[str]) -> dict[str, Any]:
    lower = build_projection_summary(axis, lower_pkg, lower_support, "lower_support")
    upper = build_projection_summary(axis, upper_pkg, upper_support, "upper_support")
    gap = R42.i_sub(
        R42.fraction_from_interval_json(upper["min_projection_interval_enclosure"]),
        R42.fraction_from_interval_json(lower["max_projection_interval_enclosure"]),
    )
    ready = positive_ready(gap)
    blockers = [] if ready else ["g0_full_domain_projection_numerator_interval_not_strictly_positive"]
    return {
        "blockers": blockers,
        "g0_center_gap_interval_ready": ready,
        "lower_support_projection": lower,
        "raw_gap_numerator_interval": interval_json(
            gap,
            unit="axis_dot_coordinate",
            source_expr="min_upper_support_minus_max_lower_support_axis_numerator",
        ),
        "reason_not_g0": None if ready else (
            "R55/R54 full-domain projection interval contains zero or negative values; "
            "a tighter center/domain isolation is required before g0 can be promoted."
        ),
        "source_identity_id": SOURCE_IDENTITY_ID,
        "upper_support_projection": upper,
    }


def support_competition_attempt(axis: Vector, package: dict[str, Any], support: list[str],
                                non_support: list[str], side: str) -> dict[str, Any]:
    support_summary = build_projection_summary(axis, package, support, f"{side}_support")
    if not non_support:
        return {
            "blockers": [],
            "finite_interval_ready": False,
            "non_support_projection": None,
            "reason_not_finite_interval": "support competition is vacuous because the side has no non-support labels",
            "side": side,
            "support_competition_ready": True,
            "support_competition_vacuous": True,
            "support_projection": support_summary,
        }
    non_support_summary = build_projection_summary(axis, package, non_support, f"{side}_non_support")
    if side == "lower":
        # Lower support vertices must remain above lower non-support vertices.
        interval = R42.i_sub(
            R42.fraction_from_interval_json(support_summary["min_projection_interval_enclosure"]),
            R42.fraction_from_interval_json(non_support_summary["max_projection_interval_enclosure"]),
        )
        source_expr = "min_lower_support_minus_max_lower_non_support_axis_numerator"
    else:
        # Upper support vertices must remain below upper non-support vertices.
        interval = R42.i_sub(
            R42.fraction_from_interval_json(non_support_summary["min_projection_interval_enclosure"]),
            R42.fraction_from_interval_json(support_summary["max_projection_interval_enclosure"]),
        )
        source_expr = "min_upper_non_support_minus_max_upper_support_axis_numerator"
    ready = positive_ready(interval)
    return {
        "blockers": [] if ready else [
            f"{side}_support_competition_interval_not_strictly_positive"
        ],
        "finite_interval_ready": ready,
        "non_support_projection": non_support_summary,
        "reason_not_finite_interval": None if ready else (
            "full-domain support-competition numerator interval contains zero or negative values"
        ),
        "side": side,
        "support_competition_interval": interval_json(
            interval,
            unit="axis_dot_coordinate",
            source_expr=source_expr,
        ),
        "support_competition_ready": ready,
        "support_competition_vacuous": False,
        "support_projection": support_summary,
    }


def build_record(r55_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r55_path = ROOT / r55_summary["object_record"]
    r55 = read_json(r55_path)
    r54_path = ROOT / r55["input_r54_center_projection_non_support_endpoint_record"]
    r54 = read_json(r54_path)
    r42_path = ROOT / r54["input_r42_rodrigues_interval_record"]
    r42_record = read_json(r42_path)
    axis = vector_from_json(r42_record["axis_cross_product_interval"])
    packages = r54["full_endpoint_coordinate_interval_packages"]
    lower_pkg = packages["lower_piece"]
    upper_pkg = packages["upper_piece"]
    lower_piece = r55["component_bound_interval_reextract"]["lower_piece"]
    upper_piece = r55["component_bound_interval_reextract"]["upper_piece"]
    lower_support = [str(label) for label in lower_piece["support_labels"]]
    lower_non_support = [str(label) for label in lower_piece["non_support_labels"]]
    upper_support = [str(label) for label in upper_piece["support_labels"]]
    upper_non_support = [str(label) for label in upper_piece["non_support_labels"]]

    g0_attempt = build_g0_attempt(axis, lower_pkg, upper_pkg, lower_support, upper_support)
    lower_attempt = support_competition_attempt(
        axis,
        lower_pkg,
        lower_support,
        lower_non_support,
        "lower",
    )
    upper_attempt = support_competition_attempt(
        axis,
        upper_pkg,
        upper_support,
        upper_non_support,
        "upper",
    )
    lower_finite_ready = bool(lower_attempt["finite_interval_ready"])
    upper_finite_ready = bool(upper_attempt["finite_interval_ready"])
    lower_ready_or_vacuous = bool(lower_attempt["support_competition_ready"])
    upper_ready_or_vacuous = bool(upper_attempt["support_competition_ready"])
    diagnostic_positive = bool(r55.get("diagnostic_positive_signed_component_margin_candidate"))

    blockers = {
        "accepted_report_promotion_out_of_scope",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
        "tau_outward_error_interval_missing",
        "positive_M_gap_M_L_M_U_not_extracted",
        "diagnostic_float_seed_stats_not_fraction_intervals",
    }
    blockers.update(g0_attempt["blockers"])
    blockers.update(lower_attempt["blockers"])
    blockers.update(upper_attempt["blockers"])
    if not diagnostic_positive:
        blockers.add("diagnostic_signed_component_margin_nonpositive")
    if not (lower_finite_ready and upper_finite_ready):
        blockers.add("finite_per_side_c_L_c_U_support_competition_intervals_not_ready")

    if not diagnostic_positive:
        object_status = "g0_c_seed_isolation_blocked_diagnostic_nonpositive_margin"
    elif not g0_attempt["g0_center_gap_interval_ready"]:
        object_status = "g0_c_seed_isolation_blocked_full_domain_projection_contains_zero"
    elif not (lower_finite_ready and upper_finite_ready):
        object_status = "g0_c_seed_isolation_blocked_support_competition_contains_zero"
    else:
        object_status = "g0_c_seed_isolation_ready_tau_and_operation_enclosures_blocked"

    original_id = str(r55["original_report_id"])
    partition_index = int(r55["partition_index"])
    domain = str(r55["domain_family"])
    out_path = (
        out_dir
        / sanitize(domain)
        / sanitize(original_id)
        / f"partition_{partition_index:02d}_g0_support_competition_seed_isolation.json"
    )
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": bool(g0_attempt["g0_center_gap_interval_ready"]),
        "g0_seed_attempt": g0_attempt,
        "input_r42_rodrigues_interval_record": rel(r42_path),
        "input_r54_center_projection_non_support_endpoint_record": rel(r54_path),
        "input_r55_component_bound_margin_skeleton_record": rel(r55_path),
        "lower_support_competition_finite_interval_ready": lower_finite_ready,
        "lower_support_competition_ready_or_vacuous": lower_ready_or_vacuous,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-G0-SUPPORT-COMPETITION-SEED-ISOLATION-{sanitize(original_id).upper()}-"
            f"PART-{partition_index:02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r55.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": lower_finite_ready and upper_finite_ready,
        "per_side_support_competition_ready_or_vacuous": lower_ready_or_vacuous and upper_ready_or_vacuous,
        "piece_pair": r55.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "source_identity_id": SOURCE_IDENTITY_ID,
        "support_competition_seed_attempt": {
            "lower": lower_attempt,
            "upper": upper_attempt,
        },
        "support_signature": r55.get("support_signature"),
        "tau_outward_error_interval_ready": False,
        "tree_id": r55.get("tree_id"),
        "upper_support_competition_finite_interval_ready": upper_finite_ready,
        "upper_support_competition_ready_or_vacuous": upper_ready_or_vacuous,
    }
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": record["g0_center_gap_interval_ready"],
        "lower_support_competition_finite_interval_ready": lower_finite_ready,
        "lower_support_competition_ready_or_vacuous": lower_ready_or_vacuous,
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r55.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": record[
            "per_side_support_competition_intervals_ready"
        ],
        "per_side_support_competition_ready_or_vacuous": record[
            "per_side_support_competition_ready_or_vacuous"
        ],
        "piece_pair": r55.get("piece_pair"),
        "support_signature": r55.get("support_signature"),
        "tau_outward_error_interval_ready": False,
        "tree_id": r55.get("tree_id"),
        "upper_support_competition_finite_interval_ready": upper_finite_ready,
        "upper_support_competition_ready_or_vacuous": upper_ready_or_vacuous,
    }


def build_manifest(records: list[dict[str, Any]], r55_manifest: Path) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    domain_counts = Counter(record["domain_family"] for record in records)
    blocker_counts = Counter()
    lower_vacuous = 0
    upper_vacuous = 0
    both_vacuous = 0
    for summary in records:
        record = read_json(ROOT / summary["object_record"])
        blocker_counts.update(record["blockers"])
        lower = record["support_competition_seed_attempt"]["lower"]
        upper = record["support_competition_seed_attempt"]["upper"]
        lower_vacuous += bool(lower["support_competition_vacuous"])
        upper_vacuous += bool(upper["support_competition_vacuous"])
        both_vacuous += bool(lower["support_competition_vacuous"] and upper["support_competition_vacuous"])
    return {
        "accepted_real_b05_report_count": sum(1 for r in records if r["accepted_real_b05_report"]),
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_positive_signed_component_margin_candidate_count": sum(
            1 for r in records if r["diagnostic_positive_signed_component_margin_candidate"]
        ),
        "exact_M_gap_M_L_M_U_ready_count": sum(1 for r in records if r["exact_M_gap_M_L_M_U_ready"]),
        "formula_shape_contract_ready_count": sum(1 for r in records if r["formula_shape_contract_ready"]),
        "g0_center_gap_interval_ready_count": sum(1 for r in records if r["g0_center_gap_interval_ready"]),
        "input_r55_manifest": rel(r55_manifest),
        "lower_support_competition_finite_interval_ready_count": sum(
            1 for r in records if r["lower_support_competition_finite_interval_ready"]
        ),
        "lower_support_competition_vacuous_count": lower_vacuous,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": sum(1 for r in records if r["operation_enclosures_ready"]),
        "per_side_support_competition_intervals_ready_count": sum(
            1 for r in records if r["per_side_support_competition_intervals_ready"]
        ),
        "per_side_support_competition_ready_or_vacuous_count": sum(
            1 for r in records if r["per_side_support_competition_ready_or_vacuous"]
        ),
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": (
            "R57: tighten B05 center/support seed isolation beyond full-domain R55 intervals, "
            "for example by center-point replay, domain subdivision, or a sharper axis/orientation enclosure."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "support_competition_both_sides_vacuous_count": both_vacuous,
        "tau_outward_error_interval_ready_count": sum(
            1 for r in records if r["tau_outward_error_interval_ready"]
        ),
        "upper_support_competition_finite_interval_ready_count": sum(
            1 for r in records if r["upper_support_competition_finite_interval_ready"]
        ),
        "upper_support_competition_vacuous_count": upper_vacuous,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r55-manifest", default=DEFAULT_R55_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r55_manifest = ROOT / args.r55_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    records = [
        build_record(summary, out_dir)
        for summary in load_manifest_records(r55_manifest)
    ]
    manifest = build_manifest(records, r55_manifest)
    write_json_lf(manifest_path, manifest)

    print(f"input R55 records: {len(records)}")
    print(f"g0/support-competition seed records emitted: {manifest['object_record_count']}")
    print(f"g0 center gap intervals ready: {manifest['g0_center_gap_interval_ready_count']}")
    print(
        "lower support competition finite intervals ready: "
        f"{manifest['lower_support_competition_finite_interval_ready_count']}"
    )
    print(
        "upper support competition finite intervals ready: "
        f"{manifest['upper_support_competition_finite_interval_ready_count']}"
    )
    print(
        "per-side support competition finite intervals ready: "
        f"{manifest['per_side_support_competition_intervals_ready_count']}"
    )
    print(f"lower support competition vacuous: {manifest['lower_support_competition_vacuous_count']}")
    print(f"upper support competition vacuous: {manifest['upper_support_competition_vacuous_count']}")
    print(
        "per-side support competition ready-or-vacuous: "
        f"{manifest['per_side_support_competition_ready_or_vacuous_count']}"
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
