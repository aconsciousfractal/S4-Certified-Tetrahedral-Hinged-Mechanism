"""
R59 B05 local Taylor trig proof-locked replay backend.

This backend consumes the R58 local centered trig replay manifest.  It keeps
R58's geometric replay structure (R40 endpoint transform paths, R42 Rodrigues
interval arithmetic, R56 support/non-support competition layout), but replaces
R58's diagnostic IEEE trig enclosures with proof-locked rational Taylor
intervals:

* pi is enclosed by Machin's formula
      pi = 16 atan(1/5) - 4 atan(1/239)
  using alternating-series rational remainders;
* degrees are converted to radians by exact rational interval multiplication;
* sin/cos are enclosed by Maclaurin interval polynomials plus an absolute
  next-term remainder bound on the local theta subdomain;
* every emitted trig endpoint is outward-quantized to a fixed rational grid.

Claim boundary: this promotes only record-local positive g0/support seed
intervals.  It still does not emit accepted B05 reports, tau intervals,
M_gap/M_L/M_U exact report fields, or theorem-level promotion.
"""

from __future__ import annotations

from collections import Counter
from copy import deepcopy
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
R58_MODULE_PATH = SCRIPT_PATH.with_name("build_s4_cl5_b05_local_centered_trig_replay_backend.py")

INPUT_R58_MANIFEST = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_local_centered_trig_replay_manifest.json"
)
OUTPUT_ROOT = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "local_taylor_trig_proof_locked_replay"
)
MANIFEST_PATH = ROOT / (
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_local_taylor_trig_proof_locked_replay_manifest.json"
)

BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
MANIFEST_ID = "S4-CL5-B05-LOCAL-TAYLOR-TRIG-PROOF-LOCKED-REPLAY-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_LOCAL_TAYLOR_TRIG_REPLAY_PROOF_LOCKED_SEEDS"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
CASE_ID = "historical_s4_median_planes"
TRIG_RULE_ID = "proof_locked_machin_taylor_outward_rational_trig_v1"

PI_TERMS = 24
TAYLOR_N = 12
OUTWARD_QUANT_DENOMINATOR = 10**24

NONCLAIM = [
    "no_b05_accepted_true_report_claim",
    "no_tau_outward_error_interval_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_formula_shape_real_report_claim",
    "no_theorem_promotion_claim",
    "no_global_operation_enclosure_audit_claim",
]

spec = importlib.util.spec_from_file_location("r58_backend", R58_MODULE_PATH)
R58 = importlib.util.module_from_spec(spec)
sys.modules["r58_backend"] = R58
assert spec.loader is not None
spec.loader.exec_module(R58)

Interval = list[Fraction]


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


def floor_to_grid(value: Fraction, denominator: int = OUTWARD_QUANT_DENOMINATOR) -> Fraction:
    return Fraction((value.numerator * denominator) // value.denominator, denominator)


def ceil_to_grid(value: Fraction, denominator: int = OUTWARD_QUANT_DENOMINATOR) -> Fraction:
    return Fraction(-((-value.numerator * denominator) // value.denominator), denominator)


def quant_interval(lo: Fraction, hi: Fraction) -> Interval:
    if lo > hi:
        lo, hi = hi, lo
    return [floor_to_grid(lo), ceil_to_grid(hi)]


def i_add(a: Interval, b: Interval) -> Interval:
    return [a[0] + b[0], a[1] + b[1]]


def i_sub(a: Interval, b: Interval) -> Interval:
    return [a[0] - b[1], a[1] - b[0]]


def i_scale(a: Interval, k: Fraction) -> Interval:
    vals = [a[0] * k, a[1] * k]
    return [min(vals), max(vals)]


def i_mul(a: Interval, b: Interval) -> Interval:
    vals = [a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1]]
    return [min(vals), max(vals)]


def i_pow(a: Interval, n: int) -> Interval:
    out = [Fraction(1), Fraction(1)]
    for _ in range(n):
        out = i_mul(out, a)
    return out


def abs_bound(a: Interval) -> Fraction:
    return max(abs(a[0]), abs(a[1]))


def atan_inv_interval(inv: int, terms: int = PI_TERMS) -> Interval:
    x = Fraction(1, inv)
    partial = Fraction(0)
    for k in range(terms):
        term = x ** (2 * k + 1) / (2 * k + 1)
        partial = partial + term if k % 2 == 0 else partial - term
    remainder = x ** (2 * terms + 1) / (2 * terms + 1)
    if terms % 2 == 0:
        return [partial, partial + remainder]
    return [partial - remainder, partial]


def pi_interval() -> Interval:
    atan_1_5 = atan_inv_interval(5)
    atan_1_239 = atan_inv_interval(239)
    pi_over_4 = i_sub(i_scale(atan_1_5, Fraction(4)), atan_1_239)
    return quant_interval(4 * pi_over_4[0], 4 * pi_over_4[1])


PI_INTERVAL = pi_interval()


def degree_to_radian_interval(deg: Interval) -> Interval:
    vals = [
        deg[0] * PI_INTERVAL[0] / 180,
        deg[0] * PI_INTERVAL[1] / 180,
        deg[1] * PI_INTERVAL[0] / 180,
        deg[1] * PI_INTERVAL[1] / 180,
    ]
    return quant_interval(min(vals), max(vals))


def sin_interval(rad: Interval, n: int = TAYLOR_N) -> Interval:
    out = [Fraction(0), Fraction(0)]
    for k in range(n + 1):
        power = 2 * k + 1
        term = i_scale(i_pow(rad, power), Fraction((-1) ** k, math.factorial(power)))
        out = i_add(out, term)
    remainder_power = 2 * n + 3
    remainder = abs_bound(rad) ** remainder_power / math.factorial(remainder_power)
    return quant_interval(out[0] - remainder, out[1] + remainder)


def cos_interval(rad: Interval, n: int = TAYLOR_N) -> Interval:
    out = [Fraction(0), Fraction(0)]
    for k in range(n + 1):
        power = 2 * k
        term = i_scale(i_pow(rad, power), Fraction((-1) ** k, math.factorial(power)))
        out = i_add(out, term)
    remainder_power = 2 * n + 2
    remainder = abs_bound(rad) ** remainder_power / math.factorial(remainder_power)
    return quant_interval(out[0] - remainder, out[1] + remainder)


def proof_locked_local_trig_object(hinge_id: str, signed_ray_sign: int, shrink: Fraction) -> dict[str, Any]:
    lo_deg, hi_deg = R58.local_theta_interval(signed_ray_sign, shrink)
    degree_interval = [lo_deg, hi_deg]
    radian_interval = degree_to_radian_interval(degree_interval)
    sin_i = sin_interval(radian_interval)
    cos_i = cos_interval(radian_interval)
    one_minus_cos_i = quant_interval(Fraction(1) - cos_i[1], Fraction(1) - cos_i[0])
    return {
        "hinge_id": hinge_id,
        "local_theta_degrees_interval": R58.interval_json(
            degree_interval, unit="degree", source_expr="centered_signed_theta_subdomain"
        ),
        "local_theta_radians_interval": R58.interval_json(
            radian_interval, unit="radian", source_expr="outward_machin_pi_times_degree_interval_over_180"
        ),
        "proof_locked_trig_enclosure": True,
        "proof_rules": [
            TRIG_RULE_ID,
            f"pi enclosure: Machin formula 16*atan(1/5)-4*atan(1/239), terms={PI_TERMS}",
            f"sin/cos enclosure: Maclaurin interval polynomial plus next-term remainder, n={TAYLOR_N}",
            f"emitted endpoints outward-quantized to denominator {OUTWARD_QUANT_DENOMINATOR}",
        ],
        "trig_intervals": {
            "cos_interval": R58.interval_json(
                cos_i, unit="dimensionless", source_expr="proof_locked_local_cos_taylor"
            ),
            "one_minus_cos_interval": R58.interval_json(
                one_minus_cos_i,
                unit="dimensionless",
                source_expr="proof_locked_local_one_minus_cos_taylor",
            ),
            "sin_interval": R58.interval_json(
                sin_i, unit="dimensionless", source_expr="proof_locked_local_sin_taylor"
            ),
        },
    }


def patch_attempt(value: Any) -> Any:
    if isinstance(value, dict):
        patched: dict[str, Any] = {}
        for key, item in value.items():
            new_key = key
            if key == "diagnostic_local_replay_all_finite_positive":
                new_key = "proof_locked_local_replay_all_finite_positive"
            elif key == "diagnostic_finite_interval_positive":
                new_key = "proof_locked_finite_interval_positive"
            patched[new_key] = patch_attempt(item)
        if "source_expr" in patched and isinstance(patched["source_expr"], str):
            patched["source_expr"] = (
                patched["source_expr"]
                .replace("diagnostic_local", "proof_locked_local_taylor")
                .replace("diagnostic_min", "proof_locked_min")
            )
        return patched
    if isinstance(value, list):
        return [patch_attempt(item) for item in value]
    return value


def compute_for_shrink(r57: dict[str, Any], shrink: Fraction) -> dict[str, Any]:
    attempt = patch_attempt(R58.compute_for_shrink(r57, shrink))
    attempt["proof_locked_trig_enclosure"] = True
    attempt["trig_rule_id"] = TRIG_RULE_ID
    attempt["pi_interval"] = R58.interval_json(
        PI_INTERVAL, unit="radian", source_expr="machin_pi_interval_outward_quantized"
    )
    attempt["taylor_parameters"] = {
        "machin_atan_terms": PI_TERMS,
        "sin_cos_taylor_n": TAYLOR_N,
        "outward_quant_denominator": str(OUTWARD_QUANT_DENOMINATOR),
    }
    return attempt


def attempt_all_positive(attempt: dict[str, Any]) -> bool:
    return bool(attempt["proof_locked_local_replay_all_finite_positive"])


def attempt_support_intervals_ready(attempt: dict[str, Any]) -> bool:
    lower = attempt["support_competition_seed_attempt"]["lower"]
    upper = attempt["support_competition_seed_attempt"]["upper"]
    return bool(lower["finite_interval_ready"] and upper["finite_interval_ready"])


def mark_finite_ready(attempt: dict[str, Any]) -> None:
    for side in ["lower", "upper"]:
        side_obj = attempt["support_competition_seed_attempt"][side]
        if side_obj.get("support_competition_interval") is not None:
            side_obj["finite_interval_ready"] = bool(side_obj.get("proof_locked_finite_interval_positive"))


def build_record(r58_summary: dict[str, Any]) -> dict[str, Any]:
    r58_path = ROOT / r58_summary["object_record"]
    r58_record = read_json(r58_path)
    r57_path = ROOT / r58_record["input_r57_center_support_seed_tightening_budget_record"]
    r57 = read_json(r57_path)
    diagnostic_positive = bool(r58_record["diagnostic_positive_signed_component_margin_candidate"])
    shrink_attempts: dict[str, Any] = {}
    blockers = {
        "accepted_report_promotion_out_of_scope",
        "tau_outward_error_interval_missing",
        "positive_M_gap_M_L_M_U_not_extracted",
        "formula_shape_real_report_not_emitted",
        "global_operation_enclosure_audit_missing",
    }

    if diagnostic_positive:
        for shrink in R58.SHRINK_FACTORS:
            key = f"1_over_{shrink.denominator}"
            attempt = compute_for_shrink(r57, shrink)
            mark_finite_ready(attempt)
            shrink_attempts[key] = attempt
    else:
        blockers.add("diagnostic_signed_component_margin_nonpositive")

    positive_keys = [key for key, attempt in shrink_attempts.items() if attempt_all_positive(attempt)]
    proof_positive = bool(positive_keys)
    chosen_key = positive_keys[0] if positive_keys else None
    chosen_attempt = shrink_attempts[chosen_key] if chosen_key else None
    per_side_intervals_ready = bool(chosen_attempt and attempt_support_intervals_ready(chosen_attempt))

    if not diagnostic_positive:
        object_status = "local_taylor_trig_replay_blocked_diagnostic_nonpositive_margin"
    elif proof_positive:
        object_status = "local_taylor_trig_replay_proof_locked_positive_seed_ready"
    else:
        object_status = "local_taylor_trig_replay_blocked_no_centered_subdomain_positive_seed"
        blockers.add("centered_subdomain_positive_seed_not_found")

    record_rel_dir = Path(r58_summary["domain_family"]) / Path(r58_summary["original_report"]).stem
    record_path = OUTPUT_ROOT / record_rel_dir / (
        f"partition_{int(r58_summary['partition_index']):02d}_local_taylor_trig_proof_locked_replay.json"
    )
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "diagnostic_local_replay_candidate_positive": bool(r58_record["diagnostic_local_replay_candidate_positive"]),
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": r58_summary["domain_family"],
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "g0_center_gap_interval_ready": proof_positive,
        "input_r58_local_centered_trig_replay_record": rel(r58_path),
        "input_r57_center_support_seed_tightening_budget_record": rel(r57_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIM,
        "object_id": "B05-LOCAL-TAYLOR-TRIG-PROOF-LOCKED-REPLAY-"
        + str(r58_summary["original_report_id"]).replace("-", "_")
        + f"-PART-{int(r58_summary['partition_index']):02d}",
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r58_summary["original_report"],
        "original_report_id": r58_summary["original_report_id"],
        "partition_index": r58_summary["partition_index"],
        "per_side_support_competition_intervals_ready": per_side_intervals_ready,
        "per_side_support_competition_ready_or_vacuous": proof_positive,
        "piece_pair": r58_summary["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "proof_locked_positive_seed_ready": proof_positive,
        "proof_locked_positive_shrink_keys": positive_keys,
        "recommended_next_task": (
            "R60: extract exact M_gap/M_L/M_U report fields and operation-enclosure audit "
            "for the 10 proof-locked local seed records."
        ),
        "shrink_attempts": shrink_attempts,
        "source_identity_id": "S4-CL5-B05-COMMON-EDGE-LOCAL-TAYLOR-TRIG-PROOF-LOCK-2026-06-22",
        "support_signature": r58_summary["support_signature"],
        "tau_outward_error_interval_ready": False,
        "tree_id": r58_summary["tree_id"],
        "trig_rule_id": TRIG_RULE_ID,
    }
    write_json(record_path, record)

    summary = {
        "accepted_real_b05_report": False,
        "diagnostic_local_replay_candidate_positive": bool(r58_record["diagnostic_local_replay_candidate_positive"]),
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": r58_summary["domain_family"],
        "g0_center_gap_interval_ready": proof_positive,
        "object_record": rel(record_path),
        "object_status": object_status,
        "original_report": r58_summary["original_report"],
        "original_report_id": r58_summary["original_report_id"],
        "partition_index": r58_summary["partition_index"],
        "per_side_support_competition_intervals_ready": per_side_intervals_ready,
        "per_side_support_competition_ready_or_vacuous": proof_positive,
        "piece_pair": r58_summary["piece_pair"],
        "proof_locked_positive_seed_ready": proof_positive,
        "proof_locked_positive_shrink_keys": positive_keys,
        "support_signature": r58_summary["support_signature"],
        "tau_outward_error_interval_ready": False,
        "tree_id": r58_summary["tree_id"],
    }
    for shrink in R58.SHRINK_FACTORS:
        key = f"1_over_{shrink.denominator}"
        attempt = shrink_attempts.get(key)
        summary[f"proof_locked_all_seed_positive_at_shrink_{key}"] = bool(
            attempt and attempt_all_positive(attempt)
        )
        summary[f"proof_locked_g0_positive_at_shrink_{key}"] = bool(
            attempt and attempt["g0_positive"]
        )
    return summary


def build_manifest(records: list[dict[str, Any]]) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    shrink_counts = {}
    g0_counts = {}
    for shrink in R58.SHRINK_FACTORS:
        key = f"1_over_{shrink.denominator}"
        shrink_counts[key] = sum(
            1 for record in records if record[f"proof_locked_all_seed_positive_at_shrink_{key}"]
        )
        g0_counts[key] = sum(
            1 for record in records if record[f"proof_locked_g0_positive_at_shrink_{key}"]
        )
    return {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": {
            "accepted_report_promotion_out_of_scope": len(records),
            "tau_outward_error_interval_missing": len(records),
            "positive_M_gap_M_L_M_U_not_extracted": len(records),
            "formula_shape_real_report_not_emitted": len(records),
            "global_operation_enclosure_audit_missing": len(records),
        },
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "exact_M_gap_M_L_M_U_ready_count": 0,
        "formula_shape_contract_ready_count": 0,
        "g0_center_gap_interval_ready_count": sum(1 for record in records if record["g0_center_gap_interval_ready"]),
        "input_r58_manifest": rel(INPUT_R58_MANIFEST),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIM,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": 0,
        "per_side_support_competition_intervals_ready_count": sum(
            1 for record in records if record["per_side_support_competition_intervals_ready"]
        ),
        "per_side_support_competition_ready_or_vacuous_count": sum(
            1 for record in records if record["per_side_support_competition_ready_or_vacuous"]
        ),
        "predicate_id": PREDICATE_ID,
        "proof_locked_all_seed_positive_counts_by_shrink": shrink_counts,
        "proof_locked_g0_positive_counts_by_shrink": g0_counts,
        "proof_locked_positive_seed_ready_count": sum(
            1 for record in records if record["proof_locked_positive_seed_ready"]
        ),
        "recommended_next_task": (
            "R60: extract exact M_gap/M_L/M_U report fields and operation-enclosure audit "
            "for proof-locked local Taylor trig seed records."
        ),
        "record_count_by_domain_family": dict(sorted(Counter(record["domain_family"] for record in records).items())),
        "records": records,
        "tau_outward_error_interval_ready_count": 0,
        "taylor_parameters": {
            "machin_atan_terms": PI_TERMS,
            "sin_cos_taylor_n": TAYLOR_N,
            "outward_quant_denominator": str(OUTWARD_QUANT_DENOMINATOR),
            "pi_interval": R58.interval_json(
                PI_INTERVAL, unit="radian", source_expr="machin_pi_interval_outward_quantized"
            ),
        },
        "trig_rule_id": TRIG_RULE_ID,
    }


def main() -> None:
    R58.local_trig_object = proof_locked_local_trig_object
    R58.TRIG_RULE_ID = TRIG_RULE_ID
    r58_manifest = read_json(INPUT_R58_MANIFEST)
    records = [build_record(summary) for summary in r58_manifest["records"]]
    manifest = build_manifest(records)
    write_json(MANIFEST_PATH, manifest)
    print(f"input R58 records: {len(r58_manifest['records'])}")
    print(f"local Taylor trig proof-locked replay records emitted: {len(records)}")
    print(f"proof-locked positive seeds ready: {manifest['proof_locked_positive_seed_ready_count']}")
    print("proof-locked all-seed positive counts by shrink:")
    for key, value in manifest["proof_locked_all_seed_positive_counts_by_shrink"].items():
        print(f"  {key}: {value}")
    print("proof-locked g0 positive counts by shrink:")
    for key, value in manifest["proof_locked_g0_positive_counts_by_shrink"].items():
        print(f"  {key}: {value}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest written: {rel(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
