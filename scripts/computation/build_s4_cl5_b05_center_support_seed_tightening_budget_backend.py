#!/usr/bin/env python
"""
Build the B05 center/support seed tightening-budget backend.

R57 consumes the R56 g0/support-competition seed isolation records.  R56 proved
that full-domain projection intervals are too wide: every finite g0/c_L/c_U
attempt still contains zero.  This layer does not promote those attempts.
Instead, it quantifies the exact centered interval shrink needed after choosing
the orientation whose midpoint is positive.

For each finite seed interval [lo, hi], R57 forms the orientation-normalized
interval with nonnegative midpoint, computes

    midpoint = (lo + hi)/2,
    half_width = (hi - lo)/2,
    strict_positive_if_shrink_factor < midpoint / half_width.

It then tests a fixed rational shrink ladder 1/2, 1/5, 1/10, 1/100, 1/1000.
A positive result at, say, 1/100 means: if a later domain-subdivision or sharper
trig/axis replay can reduce the corresponding centered projection half-width to
1/100 of the R56 full-domain half-width, then the seed interval would be strictly
positive.  This is a quantitative next-step certificate, not a geometric
subdivision proof and not an accepted B05 report.
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
MANIFEST_ID = "S4-CL5-B05-CENTER-SUPPORT-SEED-TIGHTENING-BUDGET-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_CENTER_SUPPORT_SEED_TIGHTENING_BUDGET"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R56_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_g0_support_competition_seed_isolation_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "center_support_seed_tightening_budget"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_center_support_seed_tightening_budget_manifest.json"
)

SHRINK_LADDER = [
    Fraction(1, 2),
    Fraction(1, 5),
    Fraction(1, 10),
    Fraction(1, 100),
    Fraction(1, 1000),
]

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_geometric_domain_subdivision_certificate_claim",
    "no_positive_g0_center_gap_interval_claim_from_r57_budget_alone",
    "no_positive_per_side_c_L_c_U_claim_from_r57_budget_alone",
    "no_tau_outward_error_interval_claim",
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


def frac(value: dict[str, Any]) -> Fraction:
    return Fraction(int(value["num"]), int(value["den"]))


def frac_obj(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_from_json(data: dict[str, Any]) -> tuple[Fraction, Fraction]:
    return frac(data["lo"]), frac(data["hi"])


def interval_json(interval: tuple[Fraction, Fraction], *, unit: str, source_expr: str) -> dict[str, Any]:
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(interval[1]),
        "lo": frac_obj(interval[0]),
        "source_expr": source_expr,
        "unit": unit,
    }


def load_manifest_records(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"records must be a list: {manifest_path}")
    return records


def finite_seed_items(r56: dict[str, Any]) -> list[dict[str, Any]]:
    items = [
        {
            "kind": "g0_center_gap",
            "role": "center_gap",
            "side": None,
            "source_interval": r56["g0_seed_attempt"]["raw_gap_numerator_interval"],
        }
    ]
    for side in ["lower", "upper"]:
        attempt = r56["support_competition_seed_attempt"][side]
        if attempt.get("support_competition_vacuous"):
            items.append({
                "kind": f"{side}_support_competition",
                "role": "support_competition",
                "side": side,
                "support_competition_vacuous": True,
            })
            continue
        items.append({
            "kind": f"{side}_support_competition",
            "role": "support_competition",
            "side": side,
            "source_interval": attempt["support_competition_interval"],
            "support_competition_vacuous": False,
        })
    return items


def analyze_seed(item: dict[str, Any]) -> dict[str, Any]:
    if item.get("support_competition_vacuous"):
        return {
            "kind": item["kind"],
            "role": item["role"],
            "side": item.get("side"),
            "status": "vacuous_no_finite_seed_required",
            "support_competition_vacuous": True,
        }

    lo, hi = interval_from_json(item["source_interval"])
    midpoint = (lo + hi) / 2
    orientation_multiplier = Fraction(1)
    normalized_lo, normalized_hi = lo, hi
    if midpoint < 0:
        orientation_multiplier = Fraction(-1)
        normalized_lo, normalized_hi = -hi, -lo
        midpoint = -midpoint
    half_width = (normalized_hi - normalized_lo) / 2

    if midpoint <= 0:
        strict_bound: Fraction | None = None
        shrink_results = []
        status = "blocked_nonpositive_orientation_normalized_midpoint"
    elif half_width == 0:
        strict_bound = None
        shrink_results = []
        status = "already_strictly_positive_point_seed" if normalized_lo > 0 else "blocked_zero_width_nonpositive_seed"
    else:
        strict_bound = midpoint / half_width
        shrink_results = []
        status = "centered_shrink_budget_available"
        for factor in SHRINK_LADDER:
            candidate = (midpoint - factor * half_width, midpoint + factor * half_width)
            ready = candidate[0] > 0
            shrink_results.append({
                "candidate_centered_interval": interval_json(
                    candidate,
                    unit="axis_dot_coordinate",
                    source_expr=(
                        f"orientation_normalized_centered_shrink_{factor.numerator}_over_"
                        f"{factor.denominator}_{item['kind']}"
                    ),
                ),
                "positive_if_realized": ready,
                "shrink_factor": frac_obj(factor),
                "status": "strictly_positive" if ready else "still_contains_zero_or_negative",
            })

    smallest_ladder = None
    for result in shrink_results:
        if result["positive_if_realized"]:
            smallest_ladder = result["shrink_factor"]
            break

    return {
        "centered_shrink_ladder_results": shrink_results,
        "half_width": None if half_width is None else frac_obj(half_width),
        "kind": item["kind"],
        "midpoint": frac_obj(midpoint),
        "orientation_multiplier": frac_obj(orientation_multiplier),
        "orientation_rule": (
            "multiply seed inequality by -1 when the R56 full-domain midpoint is negative; "
            "this chooses the orientation whose midpoint is positive but does not prove a real-domain seed"
        ),
        "orientation_normalized_interval": interval_json(
            (normalized_lo, normalized_hi),
            unit="axis_dot_coordinate",
            source_expr=f"orientation_normalized_{item['kind']}_from_r56_full_domain_interval",
        ),
        "role": item["role"],
        "side": item.get("side"),
        "smallest_tested_shrink_factor_positive": smallest_ladder,
        "source_interval": item["source_interval"],
        "status": status,
        "strict_positive_shrink_factor_bound": None if strict_bound is None else frac_obj(strict_bound),
        "support_competition_vacuous": False,
    }


def fraction_from_obj_or_none(value: dict[str, str] | None) -> Fraction | None:
    if value is None:
        return None
    return Fraction(int(value["num"]), int(value["den"]))


def all_finite_positive_at(seeds: list[dict[str, Any]], factor: Fraction) -> bool:
    finite = [item for item in seeds if not item.get("support_competition_vacuous")]
    if not finite:
        return False
    for seed in finite:
        ok = False
        for result in seed.get("centered_shrink_ladder_results") or []:
            if fraction_from_obj_or_none(result["shrink_factor"]) == factor:
                ok = bool(result["positive_if_realized"])
                break
        if not ok:
            return False
    return True


def min_strict_bound(seeds: list[dict[str, Any]]) -> Fraction | None:
    bounds = []
    for seed in seeds:
        if seed.get("support_competition_vacuous"):
            continue
        value = fraction_from_obj_or_none(seed.get("strict_positive_shrink_factor_bound"))
        if value is not None:
            bounds.append(value)
    return min(bounds) if bounds else None


def build_record(summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r56_path = ROOT / summary["object_record"]
    r56 = read_json(r56_path)
    seeds = [analyze_seed(item) for item in finite_seed_items(r56)]
    diagnostic_positive = bool(r56.get("diagnostic_positive_signed_component_margin_candidate"))
    positive_at_1_10 = all_finite_positive_at(seeds, Fraction(1, 10))
    positive_at_1_100 = all_finite_positive_at(seeds, Fraction(1, 100))
    bound = min_strict_bound(seeds)

    blockers = {
        "accepted_report_promotion_out_of_scope",
        "geometric_domain_subdivision_certificate_missing",
        "tau_outward_error_interval_missing",
        "operation_enclosures_missing",
        "positive_M_gap_M_L_M_U_not_extracted",
    }
    if not diagnostic_positive:
        blockers.add("diagnostic_signed_component_margin_nonpositive")
    if not positive_at_1_100:
        blockers.add("centered_shrink_1_over_100_not_sufficient_for_all_finite_seeds")

    if not diagnostic_positive:
        object_status = "seed_tightening_budget_blocked_diagnostic_nonpositive_margin"
    elif positive_at_1_100:
        object_status = "seed_tightening_budget_ready_subdivision_certificate_required"
    else:
        object_status = "seed_tightening_budget_blocked_requires_stronger_than_1_over_100"

    original_id = str(r56["original_report_id"])
    partition_index = int(r56["partition_index"])
    domain = str(r56["domain_family"])
    out_path = (
        out_dir
        / sanitize(domain)
        / sanitize(original_id)
        / f"partition_{partition_index:02d}_center_support_seed_tightening_budget.json"
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
        "g0_center_gap_interval_ready": False,
        "input_r56_g0_support_competition_seed_isolation_record": rel(r56_path),
        "manifest_id": MANIFEST_ID,
        "min_strict_positive_shrink_factor_bound": None if bound is None else frac_obj(bound),
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-CENTER-SUPPORT-SEED-TIGHTENING-BUDGET-{sanitize(original_id).upper()}-"
            f"PART-{partition_index:02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r56.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r56.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "r56_object_status": r56.get("object_status"),
        "seed_tightening_budget": {
            "all_finite_seeds_positive_at_shrink_1_over_10": positive_at_1_10,
            "all_finite_seeds_positive_at_shrink_1_over_100": positive_at_1_100,
            "interpretation": (
                "Positive centered-shrink intervals are exact algebra on R56 intervals, but they are "
                "conditional on a later real geometric replay achieving the stated shrink factor."
            ),
            "seed_items": seeds,
            "shrink_ladder": [frac_obj(item) for item in SHRINK_LADDER],
        },
        "source_identity_id": SOURCE_IDENTITY_ID,
        "support_signature": r56.get("support_signature"),
        "tau_outward_error_interval_ready": False,
        "tree_id": r56.get("tree_id"),
    }
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "all_finite_seeds_positive_at_shrink_1_over_10": positive_at_1_10,
        "all_finite_seeds_positive_at_shrink_1_over_100": positive_at_1_100,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": False,
        "min_strict_positive_shrink_factor_bound": None if bound is None else frac_obj(bound),
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r56.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r56.get("piece_pair"),
        "support_signature": r56.get("support_signature"),
        "tau_outward_error_interval_ready": False,
        "tree_id": r56.get("tree_id"),
    }


def build_manifest(records: list[dict[str, Any]], r56_manifest: Path) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    domain_counts = Counter(record["domain_family"] for record in records)
    blocker_counts = Counter()
    bounds = []
    for summary in records:
        record = read_json(ROOT / summary["object_record"])
        blocker_counts.update(record["blockers"])
        value = fraction_from_obj_or_none(record.get("min_strict_positive_shrink_factor_bound"))
        if value is not None:
            bounds.append(value)
    return {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())) if blocker_counts else {},
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_positive_signed_component_margin_candidate_count": sum(
            1 for r in records if r["diagnostic_positive_signed_component_margin_candidate"]
        ),
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "g0_center_gap_interval_ready_count": 0,
        "input_r56_manifest": rel(r56_manifest),
        "manifest_id": MANIFEST_ID,
        "max_min_strict_positive_shrink_factor_bound": None if not bounds else frac_obj(max(bounds)),
        "min_min_strict_positive_shrink_factor_bound": None if not bounds else frac_obj(min(bounds)),
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "per_side_support_competition_intervals_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": (
            "R58: realize the R57 centered-shrink budget with a real geometric local replay: "
            "subdivide theta/domain or build sharper trig/axis endpoint intervals, then rerun g0/c_L/c_U."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "records_positive_at_shrink_1_over_10_count": sum(
            1 for r in records if r["all_finite_seeds_positive_at_shrink_1_over_10"]
        ),
        "records_positive_at_shrink_1_over_100_count": sum(
            1 for r in records if r["all_finite_seeds_positive_at_shrink_1_over_100"]
        ),
        "tau_outward_error_interval_ready_count": 0,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r56-manifest", default=DEFAULT_R56_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r56_manifest = ROOT / args.r56_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    summaries = load_manifest_records(r56_manifest)
    records = [build_record(summary, out_dir) for summary in summaries]
    manifest = build_manifest(records, r56_manifest)
    write_json_lf(manifest_path, manifest)

    print(f"input R56 records: {len(summaries)}")
    print(f"seed tightening-budget records emitted: {manifest['object_record_count']}")
    print(
        "diagnostic-positive signed-component candidates: "
        f"{manifest['diagnostic_positive_signed_component_margin_candidate_count']}"
    )
    print(
        "records positive at centered shrink 1/10: "
        f"{manifest['records_positive_at_shrink_1_over_10_count']}"
    )
    print(
        "records positive at centered shrink 1/100: "
        f"{manifest['records_positive_at_shrink_1_over_100_count']}"
    )
    print(f"g0 center gap intervals ready: {manifest['g0_center_gap_interval_ready_count']}")
    print(
        "per-side support competition intervals ready: "
        f"{manifest['per_side_support_competition_intervals_ready_count']}"
    )
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest written: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
