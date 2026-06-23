#!/usr/bin/env python
"""
Build the B05 trigonometric/fraction interval backend layer.

R41 consumes the R40 axis/endpoint transform manifest.  It does not promote
any real B05 report.  Its job is narrower: attach exact rational trigonometric
range objects to the selected-hinge transform paths, using the source report
theta domain and the selected dense-refinement signed ray.

For the current B05 records every source domain is

    1/2 <= theta_degrees <= 120.

The backend emits proof-rule-backed rational bounds for each signed hinge angle:

    sin(+theta) in [ 1/180, 1]
    sin(-theta) in [-1, -1/180]
    cos(theta)  in [-1/2, 1]
    1-cos(theta) in [1/64800, 3/2]

These are intentionally conservative.  They are enough to remove the generic
"hinge-angle trig backend missing" blocker, but they do not by themselves
propagate exact endpoint coordinates through Rodrigues compositions or prove a
positive lower bound for the cross-product axis norm.
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
MANIFEST_ID = "S4-CL5-B05-TRIG-FRACTION-INTERVAL-BACKEND-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_TRIG_FRACTION_INTERVAL_BACKEND"
BACKEND_ID = "b05_selected_hinge_trig_fraction_interval_v1"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R40_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_nondegeneracy_endpoint_transform_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "trig_fraction_interval_backend"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_trig_fraction_interval_backend_manifest.json"
)

SUPPORTED_THETA_LO = Fraction(1, 2)
SUPPORTED_THETA_HI = Fraction(120, 1)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_endpoint_coordinate_interval_claim",
    "no_exact_axis_norm_lower_bound_claim",
    "no_formula_shape_contract_ready_real_report_claim",
    "no_support_component_or_gap_margin_claim",
    "no_physical_hingeability_claim",
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


def interval_json(lo: Fraction, hi: Fraction, *, unit: str, source_expr: str) -> dict[str, Any]:
    return {
        "endpoint_semantics": "closed",
        "hi": {"den": str(hi.denominator), "num": str(hi.numerator)},
        "lo": {"den": str(lo.denominator), "num": str(lo.numerator)},
        "source_expr": source_expr,
        "unit": unit,
    }


def fraction_from_json(item: dict[str, Any]) -> Fraction:
    return Fraction(int(item["num"]), int(item["den"]))


def theta_interval(report: dict[str, Any]) -> dict[str, Any]:
    interval = report.get("input_intervals", {}).get("theta_degrees")
    if not isinstance(interval, dict):
        raise ValueError(f"missing theta_degrees in {report.get('report_id')}")
    return interval


def theta_bounds(report: dict[str, Any]) -> tuple[Fraction, Fraction]:
    interval = theta_interval(report)
    lo = fraction_from_json(interval["lo"])
    hi = fraction_from_json(interval["hi"])
    return lo, hi


def supported_domain(lo: Fraction, hi: Fraction) -> bool:
    return lo == SUPPORTED_THETA_LO and hi == SUPPORTED_THETA_HI


def collect_transform_steps(r40_record: dict[str, Any]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str, str]] = set()
    steps: list[dict[str, Any]] = []
    for item in r40_record.get("endpoint_transform_objects", {}).values():
        transform = item.get("transform_definition", {})
        for step in transform.get("steps", []) or []:
            key = (
                str(step.get("hinge_id")),
                str(step.get("from_piece")),
                str(step.get("to_piece")),
            )
            if key in seen:
                continue
            seen.add(key)
            steps.append(step)
    return steps


def signed_degree_interval(theta_lo: Fraction, theta_hi: Fraction, sign: int) -> dict[str, Any]:
    if sign >= 0:
        lo, hi = theta_lo, theta_hi
    else:
        lo, hi = -theta_hi, -theta_lo
    return interval_json(
        lo,
        hi,
        unit="degree",
        source_expr=f"signed_hinge_angle_sign_{sign}_times_theta_degrees",
    )


def trig_bounds_for_sign(sign: int) -> dict[str, Any]:
    if sign >= 0:
        sin_interval = interval_json(
            Fraction(1, 180),
            Fraction(1, 1),
            unit="dimensionless",
            source_expr="sin_positive_theta_bound_from_2x_over_pi",
        )
    else:
        sin_interval = interval_json(
            Fraction(-1, 1),
            Fraction(-1, 180),
            unit="dimensionless",
            source_expr="sin_negative_theta_bound_by_odd_symmetry",
        )
    return {
        "abs_sin_interval": interval_json(
            Fraction(1, 180),
            Fraction(1, 1),
            unit="dimensionless",
            source_expr="abs_sin_theta_bound_on_half_to_120_degrees",
        ),
        "cos_interval": interval_json(
            Fraction(-1, 2),
            Fraction(1, 1),
            unit="dimensionless",
            source_expr="cos_theta_bound_on_abs_theta_le_120_degrees",
        ),
        "one_minus_cos_interval": interval_json(
            Fraction(1, 64800),
            Fraction(3, 2),
            unit="dimensionless",
            source_expr="one_minus_cos_theta_bound_from_2x2_over_pi2",
        ),
        "sin_interval": sin_interval,
    }


def proof_rules(sign: int) -> list[str]:
    direction = "positive" if sign >= 0 else "negative"
    return [
        "source domain is 1/2 <= theta_degrees <= 120",
        "for 0 <= x <= pi/2, sin(x) >= 2x/pi, so sin(pi/360) >= 1/180",
        "for |x| <= 2pi/3, cos(x) >= -1/2 and cos(x) <= 1",
        "for 0 <= x <= pi, 1-cos(x) >= 2x^2/pi^2, so 1-cos(pi/360) >= 1/64800",
        f"sin sign interval adjusted by signed ray direction: {direction}",
    ]


def hinge_trig_object(
    step: dict[str, Any],
    *,
    sign: int,
    theta_lo: Fraction,
    theta_hi: Fraction,
    domain_ready: bool,
) -> dict[str, Any]:
    hinge_id = str(step.get("hinge_id"))
    if not domain_ready:
        return {
            "hinge_id": hinge_id,
            "status": "blocked_unsupported_theta_domain",
        }
    return {
        "axis_labels": step.get("axis_labels"),
        "backend_id": BACKEND_ID,
        "cos_symbol": f"cos({step.get('theta_symbol')})",
        "hinge_id": hinge_id,
        "one_minus_cos_symbol": f"1-cos({step.get('theta_symbol')})",
        "proof_rules": proof_rules(sign),
        "signed_degree_interval": signed_degree_interval(theta_lo, theta_hi, sign),
        "signed_ray_sign": sign,
        "sin_symbol": f"sin({step.get('theta_symbol')})",
        "status": "trig_fraction_intervals_emitted",
        "theta_symbol": step.get("theta_symbol"),
        "trig_intervals": trig_bounds_for_sign(sign),
    }


def tree_signs(r40_record: dict[str, Any]) -> dict[str, int]:
    source = r40_record.get("selected_hinge_tree_source", {}).get("source_path")
    if not isinstance(source, str):
        return {}
    data = read_json(ROOT / source)
    raw = data.get("dense_refinement", {}).get("sign_vector_by_hinge", {})
    if not isinstance(raw, dict):
        return {}
    return {str(k): int(v) for k, v in raw.items()}


def build_record(summary: dict[str, Any], *, out_dir: Path) -> dict[str, Any]:
    r40_path = ROOT / summary["object_record"]
    r40 = read_json(r40_path)
    original_path = ROOT / r40["original_report"]
    original = read_json(original_path)
    theta_lo, theta_hi = theta_bounds(original)
    domain_ready = supported_domain(theta_lo, theta_hi)
    signs = tree_signs(r40)
    steps = collect_transform_steps(r40)

    hinge_objects = []
    missing_signs = []
    for step in steps:
        hinge_id = str(step.get("hinge_id"))
        sign = signs.get(hinge_id)
        if sign is None:
            missing_signs.append(hinge_id)
            continue
        hinge_objects.append(
            hinge_trig_object(
                step,
                sign=sign,
                theta_lo=theta_lo,
                theta_hi=theta_hi,
                domain_ready=domain_ready,
            )
        )

    trig_ready = domain_ready and not missing_signs and len(hinge_objects) == len(steps)
    endpoint_interval_ready = False
    axis_bound_ready = False
    contract_ready = False

    blockers = [
        "endpoint_coordinate_interval_propagation_missing",
        "rodrigues_affine_interval_composition_missing",
        "positive_axis_norm_lower_bound_not_proved",
    ]
    if not domain_ready:
        blockers.append("unsupported_theta_domain_for_trig_fraction_backend")
    if missing_signs:
        blockers.append("selected_hinge_signed_ray_sign_missing")

    record = {
        "accepted_real_b05_report": False,
        "axis_nondegeneracy_contract_ready": contract_ready,
        "backend_id": BACKEND_ID,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers)),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "domain_family": r40["domain_family"],
        "endpoint_coordinate_interval_ready": endpoint_interval_ready,
        "hinge_trig_interval_objects": hinge_objects,
        "input_r40_axis_endpoint_record": rel(r40_path),
        "manifest_id": MANIFEST_ID,
        "missing_signed_ray_signs": sorted(missing_signs),
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-TRIG-FRACTION-{sanitize(r40['original_report_id'])}",
        "object_status": (
            "trig_fraction_intervals_emitted_endpoint_propagation_blocked"
            if trig_ready
            else "trig_fraction_interval_backend_blocked"
        ),
        "original_report": rel(original_path),
        "original_report_id": r40["original_report_id"],
        "piece_pair": r40["piece_pair"],
        "positive_axis_norm_lower_bound_ready": axis_bound_ready,
        "predicate_id": PREDICATE_ID,
        "signed_ray_signs_by_hinge": signs,
        "theta_degrees_interval": theta_interval(original),
        "theta_domain_supported": domain_ready,
        "tree_id": r40["tree_id"],
        "trig_fraction_interval_backend_ready": trig_ready,
        "used_transform_step_count": len(steps),
    }
    out_path = (
        out_dir
        / str(r40["domain_family"])
        / f"{sanitize(r40['original_report_id'])}_trig_fraction.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "axis_nondegeneracy_contract_ready": contract_ready,
        "blockers": record["blockers"],
        "domain_family": r40["domain_family"],
        "endpoint_coordinate_interval_ready": endpoint_interval_ready,
        "hinge_trig_interval_count": len(hinge_objects),
        "object_record": rel(out_path),
        "object_status": record["object_status"],
        "original_report": rel(original_path),
        "original_report_id": r40["original_report_id"],
        "piece_pair": r40["piece_pair"],
        "positive_axis_norm_lower_bound_ready": axis_bound_ready,
        "theta_domain_supported": domain_ready,
        "tree_id": r40["tree_id"],
        "trig_fraction_interval_backend_ready": trig_ready,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r40-manifest", default=DEFAULT_R40_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r40_manifest_path = ROOT / args.r40_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    r40 = read_json(r40_manifest_path)
    summaries = r40.get("records")
    if not isinstance(summaries, list):
        raise TypeError("R40 manifest records must be a list")

    records = [
        build_record(summary, out_dir=out_dir)
        for summary in summaries
        if isinstance(summary, dict)
    ]
    status_counts = Counter(item["object_status"] for item in records)
    blocker_counts = Counter(blocker for item in records for blocker in item["blockers"])
    domain_counts = Counter(item["domain_family"] for item in records)
    tree_counts = Counter(item["tree_id"] for item in records)

    trig_ready_count = sum(item["trig_fraction_interval_backend_ready"] for item in records)
    endpoint_ready_count = sum(item["endpoint_coordinate_interval_ready"] for item in records)
    axis_ready_count = sum(item["positive_axis_norm_lower_bound_ready"] for item in records)
    contract_ready_count = sum(item["axis_nondegeneracy_contract_ready"] for item in records)
    supported_domain_count = sum(item["theta_domain_supported"] for item in records)
    hinge_trig_count = sum(item["hinge_trig_interval_count"] for item in records)

    manifest = {
        "accepted_real_b05_report_count": 0,
        "axis_nondegeneracy_contract_ready_count": contract_ready_count,
        "backend_id": BACKEND_ID,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "endpoint_coordinate_interval_ready_count": endpoint_ready_count,
        "hinge_trig_interval_object_count": hinge_trig_count,
        "input_r40_manifest": rel(r40_manifest_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "positive_axis_norm_lower_bound_ready_count": axis_ready_count,
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "record_count_by_tree_id": dict(sorted(tree_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R42: implement Rodrigues affine interval composition for the R40 "
            "endpoint transform paths using the R41 trig/fraction bounds, then "
            "attempt positive interval lower bounds for ||n_ij||^2."
        ),
        "supported_theta_domain_count": supported_domain_count,
        "trig_fraction_interval_backend_ready_count": trig_ready_count,
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R40 records: {len(records)}")
    print(f"supported theta domains: {supported_domain_count}")
    print(f"hinge trig interval objects: {hinge_trig_count}")
    print(f"trig/fraction backend ready: {trig_ready_count}")
    print(f"endpoint coordinate intervals ready: {endpoint_ready_count}")
    print(f"positive axis norm lower bounds ready: {axis_ready_count}")
    print(f"axis-nondegeneracy contract ready: {contract_ready_count}")
    print(f"accepted real B05 reports: 0")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"blocker counts: {dict(sorted(blocker_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")

    if len(records) != len(summaries):
        return 1
    if trig_ready_count != len(records):
        return 1
    if endpoint_ready_count or axis_ready_count or contract_ready_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
