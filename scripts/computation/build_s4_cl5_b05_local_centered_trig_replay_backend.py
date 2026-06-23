"""
R58 B05 local centered trig replay backend.

This backend consumes the R57 centered-support seed tightening budget and
performs a real local geometric replay through the R40 symbolic transform
paths and the R42 Rodrigues interval arithmetic helpers.

Important claim boundary:
    The local trig intervals in this backend are diagnostic IEEE-754 sampled
    enclosures inflated and rationalized with a fixed decimal scale. They are
    intentionally NOT proof-locked. Positive g0/c_L/c_U outputs are therefore
    recorded as diagnostic local replay candidates only. The next task is to
    replace these trig enclosures with proof-locked rational/interval sine and
    cosine bounds, or with a certified subdivision source.
"""

from __future__ import annotations

from collections import Counter
from fractions import Fraction
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
R42_MODULE_PATH = SCRIPT_PATH.with_name(
    "build_s4_cl5_b05_rodrigues_interval_composition_backend.py"
)
INPUT_R57_MANIFEST = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_center_support_seed_tightening_budget_manifest.json"
)
OUTPUT_ROOT = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "local_centered_trig_replay"
)
MANIFEST_PATH = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_local_centered_trig_replay_manifest.json"
)

BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
MANIFEST_ID = "S4-CL5-B05-LOCAL-CENTERED-TRIG-REPLAY-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_LOCAL_CENTERED_TRIG_REPLAY_DIAGNOSTIC"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
CASE_ID = "historical_s4_median_planes"
TRIG_RULE_ID = "diagnostic_ieee754_centered_theta_subdomain_enclosure_v1"

FULL_THETA_LO_DEG = Fraction(1, 2)
FULL_THETA_HI_DEG = Fraction(120, 1)
CENTER_THETA_DEG = (FULL_THETA_LO_DEG + FULL_THETA_HI_DEG) / 2
SHRINK_FACTORS = [Fraction(1, 10), Fraction(1, 100), Fraction(1, 1000), Fraction(1, 10000)]
EPSILON = 1e-14
SCALE = 10**16

NONCLAIM = [
    "no_b05_accepted_true_report_claim",
    "no_positive_g0_center_gap_interval_claim_from_diagnostic_trig_replay",
    "no_positive_per_side_c_L_c_U_claim_from_diagnostic_trig_replay",
    "no_tau_outward_error_interval_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
    "no_formula_shape_real_report_claim",
    "no_theorem_promotion_claim",
    "no_proof_locked_trig_enclosure_claim",
]

spec = importlib.util.spec_from_file_location("r42_backend", R42_MODULE_PATH)
R42 = importlib.util.module_from_spec(spec)
sys.modules["r42_backend"] = R42
assert spec.loader is not None
spec.loader.exec_module(R42)

Interval = list[Fraction]
Vector = list[Interval]


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")


def rel(path: Path) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def frac_obj(x: Fraction) -> dict[str, str]:
    return {"num": str(x.numerator), "den": str(x.denominator)}


def interval_json(interval: Interval, *, unit: str, source_expr: str) -> dict[str, Any]:
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(interval[1]),
        "lo": frac_obj(interval[0]),
        "source_expr": source_expr,
        "unit": unit,
    }


def fraction_interval_from_float_bounds(lo: float, hi: float) -> Interval:
    lower = math.floor((lo - EPSILON) * SCALE)
    upper = math.ceil((hi + EPSILON) * SCALE)
    return [Fraction(lower, SCALE), Fraction(upper, SCALE)]


def extrema_on_degree_interval(fn, lo_deg: float, hi_deg: float, criticals: list[int]) -> tuple[float, float]:
    values = [fn(math.radians(lo_deg)), fn(math.radians(hi_deg))]
    for crit in criticals:
        if lo_deg <= crit <= hi_deg:
            values.append(fn(math.radians(crit)))
    return min(values), max(values)


def critical_points() -> tuple[list[int], list[int], list[int]]:
    sin_crit: list[int] = []
    cos_crit: list[int] = []
    one_minus_cos_crit: list[int] = []
    for k in range(-3, 4):
        sin_crit.extend([90 + 360 * k, -90 + 360 * k])
        cos_crit.extend([0 + 360 * k, 180 + 360 * k])
        one_minus_cos_crit.extend([0 + 360 * k, 180 + 360 * k])
    return sin_crit, cos_crit, one_minus_cos_crit


def local_theta_interval(sign: int, shrink: Fraction) -> tuple[Fraction, Fraction]:
    half_width = (FULL_THETA_HI_DEG - FULL_THETA_LO_DEG) * shrink / 2
    lo = CENTER_THETA_DEG - half_width
    hi = CENTER_THETA_DEG + half_width
    if sign < 0:
        return -hi, -lo
    return lo, hi


def local_trig_object(hinge_id: str, signed_ray_sign: int, shrink: Fraction) -> dict[str, Any]:
    lo_q, hi_q = local_theta_interval(signed_ray_sign, shrink)
    lo = float(lo_q)
    hi = float(hi_q)
    sin_crit, cos_crit, one_minus_cos_crit = critical_points()
    sin_lo, sin_hi = extrema_on_degree_interval(math.sin, lo, hi, sin_crit)
    cos_lo, cos_hi = extrema_on_degree_interval(math.cos, lo, hi, cos_crit)
    omc_lo, omc_hi = extrema_on_degree_interval(lambda t: 1.0 - math.cos(t), lo, hi, one_minus_cos_crit)
    sin_i = fraction_interval_from_float_bounds(sin_lo, sin_hi)
    cos_i = fraction_interval_from_float_bounds(cos_lo, cos_hi)
    omc_i = fraction_interval_from_float_bounds(omc_lo, omc_hi)
    return {
        "hinge_id": hinge_id,
        "local_theta_degrees_interval": interval_json(
            [lo_q, hi_q], unit="degree", source_expr="centered_signed_theta_subdomain"
        ),
        "proof_locked_trig_enclosure": False,
        "proof_rules": [
            TRIG_RULE_ID,
            "local theta interval is centered at the R41 full-domain midpoint 241/4 degrees",
            "math.sin/math.cos endpoints and critical points sampled in IEEE-754 double precision",
            "bounds inflated by 1e-14 and rationalized at denominator 10^16",
            "diagnostic only: not a proof-locked transcendental enclosure",
        ],
        "trig_intervals": {
            "cos_interval": interval_json(cos_i, unit="dimensionless", source_expr="diagnostic_local_cos"),
            "one_minus_cos_interval": interval_json(
                omc_i, unit="dimensionless", source_expr="diagnostic_local_one_minus_cos"
            ),
            "sin_interval": interval_json(sin_i, unit="dimensionless", source_expr="diagnostic_local_sin"),
        },
    }


def trig_map_from_r41(r41_path: Path, shrink: Fraction) -> dict[str, dict[str, Any]]:
    r41 = read_json(r41_path)
    out: dict[str, dict[str, Any]] = {}
    for item in r41.get("hinge_trig_interval_objects", []):
        hinge_id = str(item["hinge_id"])
        signed_ray_sign = int(item["signed_ray_sign"])
        out[hinge_id] = local_trig_object(hinge_id, signed_ray_sign, shrink)
    return out


def max_enclosure(intervals: list[Interval]) -> Interval:
    return [max(item[0] for item in intervals), max(item[1] for item in intervals)]


def min_enclosure(intervals: list[Interval]) -> Interval:
    return [min(item[0] for item in intervals), min(item[1] for item in intervals)]


def positive_ready(interval: Interval) -> bool:
    return interval[0] > 0


def midpoint(interval: Interval) -> Fraction:
    return (interval[0] + interval[1]) / 2


def neg_interval(interval: Interval) -> Interval:
    return [-interval[1], -interval[0]]


def axis_from_r42_record(r42_record: dict[str, Any]) -> Vector:
    return [
        R42.fraction_from_interval_json(coord)
        for coord in r42_record["axis_cross_product_interval"]["coordinates"]
    ]


def labels_from_non_support(side_attempt: dict[str, Any]) -> list[str]:
    non_support = side_attempt.get("non_support_projection")
    if not isinstance(non_support, dict):
        return []
    return [str(label) for label in non_support.get("labels", [])]


def projection_summary(axis: Vector, points: dict[str, Vector], labels: list[str], role: str) -> dict[str, Any]:
    projections = []
    intervals = []
    for label in labels:
        interval = R42.v_dot(axis, points[label])
        intervals.append(interval)
        projections.append({
            "label": label,
            "projection_numerator_interval": interval_json(
                interval,
                unit="axis_dot_coordinate",
                source_expr=f"diagnostic_local_dot(axis,{role}_{label})",
            ),
        })
    return {
        "labels": labels,
        "max_projection_interval_enclosure": interval_json(
            max_enclosure(intervals),
            unit="axis_dot_coordinate",
            source_expr=f"{role}_max_projection_interval_enclosure",
        ),
        "min_projection_interval_enclosure": interval_json(
            min_enclosure(intervals),
            unit="axis_dot_coordinate",
            source_expr=f"{role}_min_projection_interval_enclosure",
        ),
        "projection_numerator_intervals_by_label": projections,
    }


def build_piece_points(r40: dict[str, Any], piece: str, labels: list[str], trig_map: dict[str, dict[str, Any]]) -> dict[str, Vector]:
    steps = R42.transform_steps_for_piece(r40, piece)
    return {
        label: R42.apply_transform_path(label, steps, trig_map)
        for label in sorted(set(labels))
    }


def compute_for_shrink(r57: dict[str, Any], shrink: Fraction) -> dict[str, Any]:
    r56 = read_json(ROOT / r57["input_r56_g0_support_competition_seed_isolation_record"])
    r42_record = read_json(ROOT / r56["input_r42_rodrigues_interval_record"])
    r40 = read_json(ROOT / r42_record["input_r40_axis_endpoint_record"])
    trig_map = trig_map_from_r41(ROOT / r42_record["input_r41_trig_fraction_record"], shrink)

    lower_piece = str(r56["g0_seed_attempt"]["lower_support_projection"]["piece_id"])
    upper_piece = str(r56["g0_seed_attempt"]["upper_support_projection"]["piece_id"])
    lower_support = [str(label) for label in r56["g0_seed_attempt"]["lower_support_projection"]["labels"]]
    upper_support = [str(label) for label in r56["g0_seed_attempt"]["upper_support_projection"]["labels"]]
    lower_non_support = labels_from_non_support(r56["support_competition_seed_attempt"]["lower"])
    upper_non_support = labels_from_non_support(r56["support_competition_seed_attempt"]["upper"])

    lower_points = build_piece_points(r40, lower_piece, lower_support + lower_non_support, trig_map)
    upper_points = build_piece_points(r40, upper_piece, upper_support + upper_non_support, trig_map)

    if len(lower_support) >= 2 and len(upper_support) >= 2:
        lower_edge = R42.v_sub(lower_points[lower_support[1]], lower_points[lower_support[0]])
        upper_edge = R42.v_sub(upper_points[upper_support[1]], upper_points[upper_support[0]])
        axis = R42.v_cross(lower_edge, upper_edge)
        axis_source = "diagnostic_local_cross_of_replayed_common_support_edges"
    else:
        axis = axis_from_r42_record(r42_record)
        axis_source = "r42_full_domain_axis_fallback_for_single_support_label"

    lower_support_summary = projection_summary(axis, lower_points, lower_support, "lower_support")
    upper_support_summary = projection_summary(axis, upper_points, upper_support, "upper_support")
    raw_g0 = R42.i_sub(
        R42.fraction_from_interval_json(upper_support_summary["min_projection_interval_enclosure"]),
        R42.fraction_from_interval_json(lower_support_summary["max_projection_interval_enclosure"]),
    )

    orientation_multiplier = 1
    if midpoint(raw_g0) < 0:
        orientation_multiplier = -1
        axis = [neg_interval(coord) for coord in axis]
        lower_support_summary = projection_summary(axis, lower_points, lower_support, "lower_support")
        upper_support_summary = projection_summary(axis, upper_points, upper_support, "upper_support")
        raw_g0 = R42.i_sub(
            R42.fraction_from_interval_json(upper_support_summary["min_projection_interval_enclosure"]),
            R42.fraction_from_interval_json(lower_support_summary["max_projection_interval_enclosure"]),
        )

    lower_non_support_summary = None
    lower_competition_interval = None
    lower_ready_or_vacuous = True
    lower_finite_ready = False
    if lower_non_support:
        lower_non_support_summary = projection_summary(axis, lower_points, lower_non_support, "lower_non_support")
        lower_competition_interval = R42.i_sub(
            R42.fraction_from_interval_json(lower_support_summary["min_projection_interval_enclosure"]),
            R42.fraction_from_interval_json(lower_non_support_summary["max_projection_interval_enclosure"]),
        )
        lower_finite_ready = positive_ready(lower_competition_interval)
        lower_ready_or_vacuous = lower_finite_ready

    upper_non_support_summary = None
    upper_competition_interval = None
    upper_ready_or_vacuous = True
    upper_finite_ready = False
    if upper_non_support:
        upper_non_support_summary = projection_summary(axis, upper_points, upper_non_support, "upper_non_support")
        upper_competition_interval = R42.i_sub(
            R42.fraction_from_interval_json(upper_non_support_summary["min_projection_interval_enclosure"]),
            R42.fraction_from_interval_json(upper_support_summary["max_projection_interval_enclosure"]),
        )
        upper_finite_ready = positive_ready(upper_competition_interval)
        upper_ready_or_vacuous = upper_finite_ready

    g0_ready = positive_ready(raw_g0)
    all_ready_or_vacuous = g0_ready and lower_ready_or_vacuous and upper_ready_or_vacuous
    return {
        "axis_source": axis_source,
        "diagnostic_local_replay_all_finite_positive": all_ready_or_vacuous,
        "g0_positive": g0_ready,
        "local_theta_center_degrees": frac_obj(CENTER_THETA_DEG),
        "lower_support_competition_finite_positive": lower_finite_ready,
        "lower_support_competition_ready_or_vacuous": lower_ready_or_vacuous,
        "orientation_multiplier": orientation_multiplier,
        "proof_locked_trig_enclosure": False,
        "shrink_factor": frac_obj(shrink),
        "support_competition_seed_attempt": {
            "lower": {
                "finite_interval_ready": False,
                "diagnostic_finite_interval_positive": lower_finite_ready,
                "non_support_projection": lower_non_support_summary,
                "support_competition_interval": None if lower_competition_interval is None else interval_json(
                    lower_competition_interval,
                    unit="axis_dot_coordinate",
                    source_expr="diagnostic_min_lower_support_minus_max_lower_non_support",
                ),
                "support_competition_ready_or_vacuous": lower_ready_or_vacuous,
                "support_competition_vacuous": not lower_non_support,
                "support_projection": lower_support_summary,
            },
            "upper": {
                "finite_interval_ready": False,
                "diagnostic_finite_interval_positive": upper_finite_ready,
                "non_support_projection": upper_non_support_summary,
                "support_competition_interval": None if upper_competition_interval is None else interval_json(
                    upper_competition_interval,
                    unit="axis_dot_coordinate",
                    source_expr="diagnostic_min_upper_non_support_minus_max_upper_support",
                ),
                "support_competition_ready_or_vacuous": upper_ready_or_vacuous,
                "support_competition_vacuous": not upper_non_support,
                "support_projection": upper_support_summary,
            },
        },
        "raw_gap_numerator_interval": interval_json(
            raw_g0,
            unit="axis_dot_coordinate",
            source_expr="diagnostic_min_upper_support_minus_max_lower_support",
        ),
        "trig_rule_id": TRIG_RULE_ID,
        "upper_support_competition_finite_positive": upper_finite_ready,
        "upper_support_competition_ready_or_vacuous": upper_ready_or_vacuous,
    }


def build_record(r57_summary: dict[str, Any]) -> dict[str, Any]:
    r57_path = ROOT / r57_summary["object_record"]
    r57 = read_json(r57_path)
    diagnostic_positive = bool(r57["diagnostic_positive_signed_component_margin_candidate"])
    shrink_attempts: dict[str, Any] = {}
    blockers = {
        "accepted_report_promotion_out_of_scope",
        "operation_enclosures_missing",
        "tau_outward_error_interval_missing",
        "positive_M_gap_M_L_M_U_not_extracted",
        "formula_shape_real_report_not_emitted",
        "proof_locked_trig_enclosure_missing",
    }

    if diagnostic_positive:
        for shrink in SHRINK_FACTORS:
            key = f"1_over_{shrink.denominator}"
            shrink_attempts[key] = compute_for_shrink(r57, shrink)
    else:
        blockers.add("diagnostic_signed_component_margin_nonpositive")

    positive_keys = [
        key for key, attempt in shrink_attempts.items()
        if attempt["diagnostic_local_replay_all_finite_positive"]
    ]
    diagnostic_candidate_positive = bool(positive_keys)
    if not diagnostic_positive:
        object_status = "local_centered_trig_replay_blocked_diagnostic_nonpositive_margin"
    elif diagnostic_candidate_positive:
        object_status = "local_centered_trig_replay_candidate_positive_trig_proof_lock_required"
    else:
        object_status = "local_centered_trig_replay_blocked_no_centered_subdomain_positive_seed"
        blockers.add("centered_subdomain_positive_seed_not_found")

    record_rel_dir = Path(r57_summary["domain_family"]) / Path(r57_summary["original_report"]).stem
    record_path = OUTPUT_ROOT / record_rel_dir / f"partition_{int(r57_summary['partition_index']):02d}_local_centered_trig_replay.json"
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_local_replay_candidate_positive": diagnostic_candidate_positive,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": r57_summary["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": False,
        "input_r57_center_support_seed_tightening_budget_record": rel(r57_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIM,
        "object_id": "B05-LOCAL-CENTERED-TRIG-REPLAY-" + str(r57_summary["original_report_id"]).replace("-", "_") + f"-PART-{int(r57_summary['partition_index']):02d}",
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r57_summary["original_report"],
        "original_report_id": r57_summary["original_report_id"],
        "partition_index": r57_summary["partition_index"],
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r57_summary["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready": False,
        "recommended_next_task": (
            "R59: proof-lock the local trig enclosures (or replace them with certified theta "
            "subdivision) and rerun this replay to promote diagnostic positives."
        ),
        "shrink_attempts": shrink_attempts,
        "source_identity_id": "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22",
        "support_signature": r57_summary["support_signature"],
        "tau_outward_error_interval_ready": False,
        "tree_id": r57_summary["tree_id"],
    }
    write_json(record_path, record)
    summary = {
        "accepted_real_b05_report": False,
        "diagnostic_local_replay_candidate_positive": diagnostic_candidate_positive,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": r57_summary["domain_family"],
        "g0_center_gap_interval_ready": False,
        "object_record": rel(record_path),
        "object_status": object_status,
        "original_report": r57_summary["original_report"],
        "original_report_id": r57_summary["original_report_id"],
        "partition_index": r57_summary["partition_index"],
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r57_summary["piece_pair"],
        "proof_locked_positive_seed_ready": False,
        "support_signature": r57_summary["support_signature"],
        "tau_outward_error_interval_ready": False,
        "tree_id": r57_summary["tree_id"],
    }
    for shrink in SHRINK_FACTORS:
        key = f"1_over_{shrink.denominator}"
        attempt = shrink_attempts.get(key)
        summary[f"diagnostic_all_seed_positive_at_shrink_{key}"] = bool(
            attempt and attempt["diagnostic_local_replay_all_finite_positive"]
        )
        summary[f"diagnostic_g0_positive_at_shrink_{key}"] = bool(
            attempt and attempt["g0_positive"]
        )
    return summary


def build_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    shrink_counts = {}
    g0_counts = {}
    for shrink in SHRINK_FACTORS:
        key = f"1_over_{shrink.denominator}"
        shrink_counts[key] = sum(
            1 for record in records if record[f"diagnostic_all_seed_positive_at_shrink_{key}"]
        )
        g0_counts[key] = sum(
            1 for record in records if record[f"diagnostic_g0_positive_at_shrink_{key}"]
        )
    return {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": {
            "accepted_report_promotion_out_of_scope": len(records),
            "proof_locked_trig_enclosure_missing": len(records),
            "operation_enclosures_missing": len(records),
            "tau_outward_error_interval_missing": len(records),
            "positive_M_gap_M_L_M_U_not_extracted": len(records),
            "formula_shape_real_report_not_emitted": len(records),
        },
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_all_seed_positive_counts_by_shrink": shrink_counts,
        "diagnostic_g0_positive_counts_by_shrink": g0_counts,
        "diagnostic_local_replay_candidate_positive_count": sum(
            1 for record in records if record["diagnostic_local_replay_candidate_positive"]
        ),
        "diagnostic_positive_signed_component_margin_candidate_count": sum(
            1 for record in records if record["diagnostic_positive_signed_component_margin_candidate"]
        ),
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "g0_center_gap_interval_ready_count": 0,
        "input_r57_manifest": rel(INPUT_R57_MANIFEST),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIM,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "per_side_support_competition_intervals_ready_count": 0,
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready_count": 0,
        "recommended_next_task": (
            "R59: proof-lock local trig enclosures or certified theta subdivision, then promote "
            "diagnostic local replay positives to real g0/c_L/c_U seed intervals."
        ),
        "record_count_by_domain_family": dict(sorted(Counter(record["domain_family"] for record in records).items())),
        "records": records,
        "tau_outward_error_interval_ready_count": 0,
        "trig_rule_id": TRIG_RULE_ID,
    }


def main() -> None:
    r57_manifest = read_json(INPUT_R57_MANIFEST)
    records = [build_record(summary) for summary in r57_manifest["records"]]
    manifest = build_manifest(records)
    write_json(MANIFEST_PATH, manifest)
    print(f"input R57 records: {len(r57_manifest['records'])}")
    print(f"local centered trig replay records emitted: {len(records)}")
    print(
        "diagnostic positive signed-component candidates: "
        f"{manifest['diagnostic_positive_signed_component_margin_candidate_count']}"
    )
    print(
        "diagnostic local replay positive candidates: "
        f"{manifest['diagnostic_local_replay_candidate_positive_count']}"
    )
    print("diagnostic all-seed positive counts by shrink:")
    for key, value in manifest["diagnostic_all_seed_positive_counts_by_shrink"].items():
        print(f"  {key}: {value}")
    print("diagnostic g0 positive counts by shrink:")
    for key, value in manifest["diagnostic_g0_positive_counts_by_shrink"].items():
        print(f"  {key}: {value}")
    print(f"proof-locked positive seeds ready: {manifest['proof_locked_positive_seed_ready_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest written: {rel(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
