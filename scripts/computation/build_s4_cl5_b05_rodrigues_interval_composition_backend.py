#!/usr/bin/env python
"""
Build the B05 Rodrigues affine interval-composition backend layer.

R42 consumes:

* R40 selected-hinge endpoint transform paths;
* R41 signed-hinge trigonometric fraction intervals.

It propagates rational interval coordinates through each Rodrigues transform
path for the common endpoints M_AB and M_CD on both pieces of every B05 pair.
It then attempts the common-edge axis lower-bound check by interval arithmetic:

    n_ij = (F_i(M_CD)-F_i(M_AB)) x (F_j(M_CD)-F_j(M_AB)).

The backend is intentionally conservative and does not promote any real B05
report.  If interval overestimation keeps 0 in the cross-product coordinates,
the record stays blocked with an explicit lower-bound blocker.
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
MANIFEST_ID = "S4-CL5-B05-RODRIGUES-INTERVAL-COMPOSITION-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_RODRIGUES_INTERVAL_COMPOSITION"
BACKEND_ID = "b05_rodrigues_affine_interval_composition_v1"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R40_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_nondegeneracy_endpoint_transform_manifest.json"
)
DEFAULT_R41_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_trig_fraction_interval_backend_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "rodrigues_interval_composition"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_rodrigues_interval_composition_manifest.json"
)

COMMON_EDGE_LABELS = ["M_AB", "M_CD"]
AMBIENT_LABELS = ["A", "B", "C", "D", "M_AB", "M_CD"]
QUANT_DEN = 10**12

SQRT3 = (Fraction(1732050807568877, 10**15), Fraction(1732050807568878, 10**15))
SQRT6 = (Fraction(2449489742783178, 10**15), Fraction(2449489742783179, 10**15))

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_axis_norm_lower_bound_claim_unless_record_says_ready",
    "no_formula_shape_contract_ready_real_report_claim",
    "no_support_component_or_gap_margin_claim",
    "no_physical_hingeability_claim",
]


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


def floor_fraction(value: Fraction, den: int = QUANT_DEN) -> Fraction:
    return Fraction(value.numerator * den // value.denominator, den)


def ceil_fraction(value: Fraction, den: int = QUANT_DEN) -> Fraction:
    return Fraction(-((-value.numerator * den) // value.denominator), den)


def q_interval(interval: Interval) -> Interval:
    lo, hi = interval
    if lo > hi:
        raise ValueError(f"bad interval: {interval}")
    return (floor_fraction(lo), ceil_fraction(hi))


def i_const(value: Fraction | int) -> Interval:
    item = Fraction(value)
    return (item, item)


def i_add(a: Interval, b: Interval) -> Interval:
    return q_interval((a[0] + b[0], a[1] + b[1]))


def i_sub(a: Interval, b: Interval) -> Interval:
    return q_interval((a[0] - b[1], a[1] - b[0]))


def i_neg(a: Interval) -> Interval:
    return (-a[1], -a[0])


def i_mul(a: Interval, b: Interval) -> Interval:
    vals = [a[0] * b[0], a[0] * b[1], a[1] * b[0], a[1] * b[1]]
    return q_interval((min(vals), max(vals)))


def i_square(a: Interval) -> Interval:
    if a[0] <= 0 <= a[1]:
        return q_interval((Fraction(0), max(a[0] * a[0], a[1] * a[1])))
    vals = [a[0] * a[0], a[1] * a[1]]
    return q_interval((min(vals), max(vals)))


def v_add(a: Vector, b: Vector) -> Vector:
    return [i_add(x, y) for x, y in zip(a, b)]


def v_sub(a: Vector, b: Vector) -> Vector:
    return [i_sub(x, y) for x, y in zip(a, b)]


def v_scale(k: Interval, v: Vector) -> Vector:
    return [i_mul(k, item) for item in v]


def v_dot(a: Vector, b: Vector) -> Interval:
    total = i_const(0)
    for x, y in zip(a, b):
        total = i_add(total, i_mul(x, y))
    return total


def v_cross(a: Vector, b: Vector) -> Vector:
    return [
        i_sub(i_mul(a[1], b[2]), i_mul(a[2], b[1])),
        i_sub(i_mul(a[2], b[0]), i_mul(a[0], b[2])),
        i_sub(i_mul(a[0], b[1]), i_mul(a[1], b[0])),
    ]


def fraction_from_interval_json(data: dict[str, Any]) -> Interval:
    lo = Fraction(int(data["lo"]["num"]), int(data["lo"]["den"]))
    hi = Fraction(int(data["hi"]["num"]), int(data["hi"]["den"]))
    return (lo, hi)


def interval_json(interval: Interval, *, unit: str, source_expr: str) -> dict[str, Any]:
    lo, hi = interval
    return {
        "endpoint_semantics": "closed",
        "hi": {"den": str(hi.denominator), "num": str(hi.numerator)},
        "lo": {"den": str(lo.denominator), "num": str(lo.numerator)},
        "source_expr": source_expr,
        "unit": unit,
    }


def vector_json(vector: Vector, *, source_expr: str) -> dict[str, Any]:
    return {
        "coordinate_order": ["x", "y", "z"],
        "coordinates": [
            interval_json(item, unit="coordinate", source_expr=f"{source_expr}_{axis}")
            for item, axis in zip(vector, ["x", "y", "z"])
        ],
    }


def ambient_coordinates() -> dict[str, Vector]:
    sqrt3 = SQRT3
    sqrt6 = SQRT6
    zero = i_const(0)
    half = i_const(Fraction(1, 2))
    one = i_const(1)
    return {
        "A": [zero, zero, zero],
        "B": [one, zero, zero],
        "C": [half, q_interval((sqrt3[0] / 2, sqrt3[1] / 2)), zero],
        "D": [
            half,
            q_interval((sqrt3[0] / 6, sqrt3[1] / 6)),
            q_interval((sqrt6[0] / 3, sqrt6[1] / 3)),
        ],
        "M_AB": [half, zero, zero],
        "M_CD": [
            half,
            q_interval((sqrt3[0] / 3, sqrt3[1] / 3)),
            q_interval((sqrt6[0] / 6, sqrt6[1] / 6)),
        ],
    }


def trig_by_hinge(r41_record: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out = {}
    for item in r41_record.get("hinge_trig_interval_objects", []):
        if isinstance(item, dict):
            out[str(item.get("hinge_id"))] = item
    return out


def rotate_point(point: Vector, p0: Vector, unit_axis: Vector, trig: dict[str, Any]) -> Vector:
    intervals = trig["trig_intervals"]
    sin_i = fraction_from_interval_json(intervals["sin_interval"])
    cos_i = fraction_from_interval_json(intervals["cos_interval"])
    one_minus_cos_i = fraction_from_interval_json(intervals["one_minus_cos_interval"])
    v = v_sub(point, p0)
    term_cos = v_scale(cos_i, v)
    term_sin = v_scale(sin_i, v_cross(unit_axis, v))
    term_omc = v_scale(i_mul(v_dot(unit_axis, v), one_minus_cos_i), unit_axis)
    return v_add(p0, v_add(term_cos, v_add(term_sin, term_omc)))


def apply_transform_path(label: str, steps: list[dict[str, Any]], trig_map: dict[str, dict[str, Any]]) -> Vector:
    coords = ambient_coordinates()
    for step in steps:
        hinge_id = str(step["hinge_id"])
        trig = trig_map[hinge_id]
        axis_a, axis_b = step["axis_labels"]
        old = {key: [coord for coord in value] for key, value in coords.items()}
        p0 = old[str(axis_a)]
        p1 = old[str(axis_b)]
        # All selected B05 axes are half-edge axes of length 1/2, so 2*(p1-p0)
        # contains the exact unit axis after applying the parent isometry.
        unit_axis = v_scale(i_const(2), v_sub(p1, p0))
        coords = {
            key: rotate_point(value, p0, unit_axis, trig)
            for key, value in old.items()
        }
    return coords[label]


def norm_square_interval(vector: Vector) -> Interval:
    total = i_const(0)
    for item in vector:
        total = i_add(total, i_square(item))
    return total


def transform_steps_for_piece(r40_record: dict[str, Any], piece: str) -> list[dict[str, Any]]:
    transform = (
        r40_record.get("endpoint_transform_objects", {})
        .get(piece, {})
        .get("transform_definition", {})
    )
    steps = transform.get("steps", []) or []
    return [step for step in steps if isinstance(step, dict)]


def build_record(
    r40_summary: dict[str, Any],
    r41_by_report_id: dict[str, dict[str, Any]],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    r40_path = ROOT / r40_summary["object_record"]
    r40 = read_json(r40_path)
    report_id = str(r40["original_report_id"])
    r41_summary = r41_by_report_id[report_id]
    r41_path = ROOT / r41_summary["object_record"]
    r41 = read_json(r41_path)
    trig_map = trig_by_hinge(r41)
    pair = str(r40["piece_pair"]).split("-")
    if len(pair) != 2:
        raise ValueError(f"unexpected piece pair: {r40['piece_pair']}")

    endpoint_intervals: dict[str, dict[str, Any]] = {}
    endpoint_vectors: dict[str, dict[str, Vector]] = {}
    for piece in pair:
        steps = transform_steps_for_piece(r40, piece)
        endpoint_vectors[piece] = {}
        endpoint_intervals[piece] = {
            "piece": piece,
            "source_status": "endpoint_coordinate_intervals_emitted",
            "transform_step_count": len(steps),
            "endpoints": {},
        }
        for label in COMMON_EDGE_LABELS:
            vec = apply_transform_path(label, steps, trig_map)
            endpoint_vectors[piece][label] = vec
            endpoint_intervals[piece]["endpoints"][label] = vector_json(
                vec,
                source_expr=f"{piece}_{label}_rodrigues_interval",
            )

    e_left = v_sub(endpoint_vectors[pair[0]]["M_CD"], endpoint_vectors[pair[0]]["M_AB"])
    e_right = v_sub(endpoint_vectors[pair[1]]["M_CD"], endpoint_vectors[pair[1]]["M_AB"])
    cross = v_cross(e_left, e_right)
    norm_sq = norm_square_interval(cross)
    axis_bound_ready = norm_sq[0] > 0

    blockers = []
    if not axis_bound_ready:
        blockers.extend([
            "positive_axis_norm_lower_bound_not_proved",
            "interval_overestimation_axis_norm_square_lower_bound_zero",
        ])

    endpoint_ready = True
    contract_ready = endpoint_ready and axis_bound_ready
    record = {
        "accepted_real_b05_report": False,
        "ambient_coordinate_interval_backend": {
            "coordinate_labels": AMBIENT_LABELS,
            "quantization_denominator": str(QUANT_DEN),
            "sqrt3_interval": interval_json(SQRT3, unit="coordinate", source_expr="sqrt3_decimal_rational_enclosure"),
            "sqrt6_interval": interval_json(SQRT6, unit="coordinate", source_expr="sqrt6_decimal_rational_enclosure"),
            "status": "ambient_coordinates_enclosed_by_rational_intervals",
        },
        "axis_cross_product_interval": vector_json(cross, source_expr="common_edge_axis_cross_product"),
        "axis_nondegeneracy_contract_ready": contract_ready,
        "axis_norm_square_interval": interval_json(norm_sq, unit="squared_coordinate", source_expr="sum_of_axis_cross_product_coordinate_squares"),
        "backend_id": BACKEND_ID,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(set(blockers)),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "domain_family": r40["domain_family"],
        "edge_vector_intervals": {
            pair[0]: vector_json(e_left, source_expr=f"{pair[0]}_common_edge_vector"),
            pair[1]: vector_json(e_right, source_expr=f"{pair[1]}_common_edge_vector"),
        },
        "endpoint_coordinate_interval_ready": endpoint_ready,
        "endpoint_coordinate_intervals": endpoint_intervals,
        "input_r40_axis_endpoint_record": rel(r40_path),
        "input_r41_trig_fraction_record": rel(r41_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-RODRIGUES-COMPOSITION-{sanitize(report_id)}",
        "object_status": (
            "endpoint_coordinate_intervals_emitted_axis_lower_bound_ready"
            if axis_bound_ready
            else "endpoint_coordinate_intervals_emitted_axis_lower_bound_blocked"
        ),
        "original_report": r40["original_report"],
        "original_report_id": report_id,
        "piece_pair": r40["piece_pair"],
        "positive_axis_norm_lower_bound_ready": axis_bound_ready,
        "predicate_id": PREDICATE_ID,
        "rodrigues_interval_composition_ready": True,
        "tree_id": r40["tree_id"],
    }
    out_path = (
        out_dir
        / str(r40["domain_family"])
        / f"{sanitize(report_id)}_rodrigues_interval.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "axis_nondegeneracy_contract_ready": contract_ready,
        "axis_norm_square_lower_bound": {
            "den": str(norm_sq[0].denominator),
            "num": str(norm_sq[0].numerator),
        },
        "blockers": record["blockers"],
        "domain_family": r40["domain_family"],
        "endpoint_coordinate_interval_ready": endpoint_ready,
        "object_record": rel(out_path),
        "object_status": record["object_status"],
        "original_report": r40["original_report"],
        "original_report_id": report_id,
        "piece_pair": r40["piece_pair"],
        "positive_axis_norm_lower_bound_ready": axis_bound_ready,
        "rodrigues_interval_composition_ready": True,
        "tree_id": r40["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r40-manifest", default=DEFAULT_R40_MANIFEST.as_posix())
    parser.add_argument("--r41-manifest", default=DEFAULT_R41_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r40_manifest_path = ROOT / args.r40_manifest
    r41_manifest_path = ROOT / args.r41_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r40 = read_json(r40_manifest_path)
    r41 = read_json(r41_manifest_path)
    r40_records = r40.get("records")
    r41_records = r41.get("records")
    if not isinstance(r40_records, list) or not isinstance(r41_records, list):
        raise TypeError("R40/R41 manifests must expose records lists")
    r41_by_report_id = {
        str(item["original_report_id"]): item
        for item in r41_records
        if isinstance(item, dict)
    }

    records = [
        build_record(item, r41_by_report_id, out_dir=out_dir)
        for item in r40_records
        if isinstance(item, dict)
    ]
    status_counts = Counter(item["object_status"] for item in records)
    blocker_counts = Counter(blocker for item in records for blocker in item["blockers"])
    domain_counts = Counter(item["domain_family"] for item in records)
    tree_counts = Counter(item["tree_id"] for item in records)

    composition_ready_count = sum(item["rodrigues_interval_composition_ready"] for item in records)
    endpoint_ready_count = sum(item["endpoint_coordinate_interval_ready"] for item in records)
    axis_ready_count = sum(item["positive_axis_norm_lower_bound_ready"] for item in records)
    contract_ready_count = sum(item["axis_nondegeneracy_contract_ready"] for item in records)

    manifest = {
        "accepted_real_b05_report_count": 0,
        "axis_nondegeneracy_contract_ready_count": contract_ready_count,
        "backend_id": BACKEND_ID,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "endpoint_coordinate_interval_ready_count": endpoint_ready_count,
        "input_r40_manifest": rel(r40_manifest_path),
        "input_r41_manifest": rel(r41_manifest_path),
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
            "R43: sharpen the common-edge axis norm lower-bound backend, either "
            "by branch-splitting the Rodrigues intervals or by symbolic axis "
            "norm factorization, before support/component/gap margins."
        ),
        "rodrigues_interval_composition_ready_count": composition_ready_count,
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R40 records: {len(records)}")
    print(f"Rodrigues interval composition ready: {composition_ready_count}")
    print(f"endpoint coordinate intervals ready: {endpoint_ready_count}")
    print(f"positive axis norm lower bounds ready: {axis_ready_count}")
    print(f"axis-nondegeneracy contract ready: {contract_ready_count}")
    print(f"accepted real B05 reports: 0")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"blocker counts: {dict(sorted(blocker_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")

    if len(records) != len(r40_records):
        return 1
    if composition_ready_count != len(records) or endpoint_ready_count != len(records):
        return 1
    if contract_ready_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
