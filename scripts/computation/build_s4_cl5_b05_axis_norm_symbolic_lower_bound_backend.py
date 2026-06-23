#!/usr/bin/env python
"""
Build the B05 common-edge axis norm symbolic lower-bound backend.

R43 consumes the R40 endpoint transform paths, the R41 trig/fraction interval
objects, and the R42 Rodrigues interval-composition records.  It removes the
main R42 overestimation by keeping the shared angle dependency symbolic:

    s = sin(theta), c = cos(theta), c^2 + s^2 = 1.

For every real-source B05 record the common-edge axis norm square reduces to

    ||e_i x e_j||^2 = s^2 * (2 - s^2) / 4.

Together with the R41 bound |sin(theta)| >= 1/180 and |sin(theta)| <= 1, this
gives the uniform positive lower bound 1/129600.

This proves the axis-nondegeneracy sub-contract only.  It does not emit support
labels, component motion bounds, M_gap/M_L/M_U margins, operation enclosures,
or accepted B05 reports.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any

import sympy as sp


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-AXIS-NORM-SYMBOLIC-LOWER-BOUND-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_AXIS_NORM_SYMBOLIC_LOWER_BOUND"
BACKEND_ID = "b05_common_edge_axis_norm_symbolic_lower_bound_v1"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R40_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_nondegeneracy_endpoint_transform_manifest.json"
)
DEFAULT_R41_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_trig_fraction_interval_backend_manifest.json"
)
DEFAULT_R42_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_rodrigues_interval_composition_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "axis_norm_symbolic_lower_bound"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_norm_symbolic_lower_bound_manifest.json"
)

COMMON_EDGE_LABELS = ["M_AB", "M_CD"]
EXPECTED_FACTOR = "sin_theta^2*(2-sin_theta^2)/4"
LOWER_BOUND = Fraction(1, 129600)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_support_component_or_gap_margin_claim",
    "no_operation_enclosure_claim",
    "no_physical_hingeability_claim",
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


def fraction_json(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_json(lo: Fraction, hi: Fraction, *, unit: str, source_expr: str) -> dict[str, Any]:
    return {
        "endpoint_semantics": "closed",
        "hi": fraction_json(hi),
        "lo": fraction_json(lo),
        "source_expr": source_expr,
        "unit": unit,
    }


def fraction_from_interval_json(data: dict[str, Any]) -> tuple[Fraction, Fraction]:
    lo = Fraction(int(data["lo"]["num"]), int(data["lo"]["den"]))
    hi = Fraction(int(data["hi"]["num"]), int(data["hi"]["den"]))
    return lo, hi


S, C = sp.symbols("s c")
SQRT3 = sp.sqrt(3)
SQRT6 = sp.sqrt(6)

AMBIENT = {
    "A": sp.Matrix([0, 0, 0]),
    "B": sp.Matrix([1, 0, 0]),
    "C": sp.Matrix([sp.Rational(1, 2), SQRT3 / 2, 0]),
    "D": sp.Matrix([sp.Rational(1, 2), SQRT3 / 6, SQRT6 / 3]),
    "M_AB": sp.Matrix([sp.Rational(1, 2), 0, 0]),
    "M_CD": sp.Matrix([sp.Rational(1, 2), SQRT3 / 3, SQRT6 / 6]),
}


def v_cross(a: sp.Matrix, b: sp.Matrix) -> sp.Matrix:
    return sp.Matrix([
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ])


def rotate_point(point: sp.Matrix, p0: sp.Matrix, unit_axis: sp.Matrix, sign: int) -> sp.Matrix:
    signed_sin = sign * S
    v = point - p0
    return sp.simplify(
        p0
        + v * C
        + v_cross(unit_axis, v) * signed_sin
        + unit_axis * (unit_axis.dot(v)) * (1 - C)
    )


def apply_transform_path(label: str, steps: list[dict[str, Any]], signs: dict[str, int]) -> sp.Matrix:
    coords = {key: value for key, value in AMBIENT.items()}
    for step in steps:
        old = {key: value for key, value in coords.items()}
        axis_a, axis_b = step["axis_labels"]
        p0 = old[str(axis_a)]
        p1 = old[str(axis_b)]
        unit_axis = sp.simplify(2 * (p1 - p0))
        sign = signs[str(step["hinge_id"])]
        coords = {
            key: rotate_point(value, p0, unit_axis, sign)
            for key, value in old.items()
        }
    return coords[label]


def transform_steps_for_piece(r40_record: dict[str, Any], piece: str) -> list[dict[str, Any]]:
    transform = (
        r40_record.get("endpoint_transform_objects", {})
        .get(piece, {})
        .get("transform_definition", {})
    )
    steps = transform.get("steps", []) or []
    return [step for step in steps if isinstance(step, dict)]


def reduce_trig_identity(expr: sp.Expr) -> sp.Expr:
    poly = sp.Poly(sp.expand(expr), C, S, extension=[SQRT3, SQRT6])
    relation = sp.Poly(C * C + S * S - 1, C, S, extension=[SQRT3, SQRT6])
    return sp.factor(poly.rem(relation).as_expr())


def norm_square(vector: sp.Matrix) -> sp.Expr:
    return sp.expand(sum(item * item for item in vector))


def symbolic_axis_norm_factor(r40_record: dict[str, Any], signs: dict[str, int]) -> sp.Expr:
    pair = str(r40_record["piece_pair"]).split("-")
    if len(pair) != 2:
        raise ValueError(f"unexpected piece pair: {r40_record['piece_pair']}")
    edge_vectors = []
    for piece in pair:
        steps = transform_steps_for_piece(r40_record, piece)
        m_cd = apply_transform_path("M_CD", steps, signs)
        m_ab = apply_transform_path("M_AB", steps, signs)
        edge_vectors.append(sp.simplify(m_cd - m_ab))
    axis = v_cross(edge_vectors[0], edge_vectors[1])
    return reduce_trig_identity(norm_square(axis))


def trig_signs_and_bounds(r41_record: dict[str, Any]) -> tuple[dict[str, int], Fraction, Fraction]:
    signs: dict[str, int] = {}
    abs_sin_lowers = []
    abs_sin_uppers = []
    for item in r41_record.get("hinge_trig_interval_objects", []):
        if not isinstance(item, dict):
            continue
        signs[str(item["hinge_id"])] = int(item["signed_ray_sign"])
        abs_sin = item["trig_intervals"]["abs_sin_interval"]
        lo, hi = fraction_from_interval_json(abs_sin)
        abs_sin_lowers.append(lo)
        abs_sin_uppers.append(hi)
    if not abs_sin_lowers:
        raise ValueError("missing R41 abs-sin bounds")
    return signs, min(abs_sin_lowers), max(abs_sin_uppers)


def build_record(
    r40_summary: dict[str, Any],
    r41_by_report_id: dict[str, dict[str, Any]],
    r42_by_report_id: dict[str, dict[str, Any]],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    r40_path = ROOT / r40_summary["object_record"]
    r40 = read_json(r40_path)
    report_id = str(r40["original_report_id"])
    r41_summary = r41_by_report_id[report_id]
    r42_summary = r42_by_report_id[report_id]
    r41_path = ROOT / r41_summary["object_record"]
    r42_path = ROOT / r42_summary["object_record"]
    r41 = read_json(r41_path)

    signs, abs_sin_lb, abs_sin_ub = trig_signs_and_bounds(r41)
    factor = symbolic_axis_norm_factor(r40, signs)
    expected = S * S * (2 - S * S) / 4
    if sp.simplify(factor - expected) != 0:
        raise ValueError(f"unexpected symbolic factor for {report_id}: {sp.factor(factor)}")
    if abs_sin_lb <= 0 or abs_sin_ub > 1:
        raise ValueError(f"bad R41 abs-sin bounds for {report_id}: {abs_sin_lb}, {abs_sin_ub}")

    lower_bound = abs_sin_lb * abs_sin_lb * (2 - abs_sin_ub * abs_sin_ub) / 4
    if lower_bound <= 0:
        raise ValueError(f"non-positive axis lower bound for {report_id}: {lower_bound}")

    record = {
        "accepted_real_b05_report": False,
        "axis_nondegeneracy_contract_ready": True,
        "axis_norm_square_interval": interval_json(
            lower_bound,
            Fraction(1, 2),
            unit="squared_coordinate",
            source_expr="sin_theta_squared_times_two_minus_sin_theta_squared_over_four",
        ),
        "axis_norm_square_symbolic_factor": {
            "canonical_expr": EXPECTED_FACTOR,
            "computed_expr": str(sp.factor(factor)),
            "trig_relation_used": "cos(theta)^2 + sin(theta)^2 = 1",
        },
        "backend_id": BACKEND_ID,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": [
            "support_component_gap_margins_not_checked",
            "operation_enclosures_not_checked",
            "accepted_report_promotion_out_of_scope",
        ],
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "domain_family": r40["domain_family"],
        "input_r40_axis_endpoint_record": rel(r40_path),
        "input_r41_trig_fraction_record": rel(r41_path),
        "input_r42_rodrigues_interval_record": rel(r42_path),
        "lower_bound_proof": {
            "abs_sin_lower_bound": fraction_json(abs_sin_lb),
            "abs_sin_upper_bound": fraction_json(abs_sin_ub),
            "lower_bound": fraction_json(lower_bound),
            "rules": [
                "R43 symbolic reduction gives ||e_i x e_j||^2 = sin(theta)^2*(2-sin(theta)^2)/4",
                "R41 gives |sin(theta)| >= 1/180 on the source theta domain",
                "R41 gives |sin(theta)| <= 1 on the source theta domain",
                "therefore ||e_i x e_j||^2 >= (1/180)^2*(2-1)/4 = 1/129600",
            ],
        },
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-AXIS-NORM-LOWER-BOUND-{sanitize(report_id)}",
        "object_status": "positive_axis_norm_symbolic_lower_bound_ready",
        "original_report": r40["original_report"],
        "original_report_id": report_id,
        "piece_pair": r40["piece_pair"],
        "positive_axis_norm_lower_bound_ready": True,
        "predicate_id": PREDICATE_ID,
        "symbolic_axis_norm_lower_bound_ready": True,
        "tree_id": r40["tree_id"],
    }
    out_path = (
        out_dir
        / str(r40["domain_family"])
        / f"{sanitize(report_id)}_axis_norm_symbolic_lower_bound.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "axis_nondegeneracy_contract_ready": True,
        "axis_norm_square_lower_bound": fraction_json(lower_bound),
        "blockers": record["blockers"],
        "domain_family": r40["domain_family"],
        "object_record": rel(out_path),
        "object_status": record["object_status"],
        "original_report": r40["original_report"],
        "original_report_id": report_id,
        "piece_pair": r40["piece_pair"],
        "positive_axis_norm_lower_bound_ready": True,
        "symbolic_axis_norm_lower_bound_ready": True,
        "tree_id": r40["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r40-manifest", default=DEFAULT_R40_MANIFEST.as_posix())
    parser.add_argument("--r41-manifest", default=DEFAULT_R41_MANIFEST.as_posix())
    parser.add_argument("--r42-manifest", default=DEFAULT_R42_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r40_manifest_path = ROOT / args.r40_manifest
    r41_manifest_path = ROOT / args.r41_manifest
    r42_manifest_path = ROOT / args.r42_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r40 = read_json(r40_manifest_path)
    r41 = read_json(r41_manifest_path)
    r42 = read_json(r42_manifest_path)
    r40_records = r40.get("records")
    r41_records = r41.get("records")
    r42_records = r42.get("records")
    if not all(isinstance(records, list) for records in [r40_records, r41_records, r42_records]):
        raise TypeError("R40/R41/R42 manifests must expose records lists")

    r41_by_report_id = {str(item["original_report_id"]): item for item in r41_records if isinstance(item, dict)}
    r42_by_report_id = {str(item["original_report_id"]): item for item in r42_records if isinstance(item, dict)}
    records = [
        build_record(item, r41_by_report_id, r42_by_report_id, out_dir=out_dir)
        for item in r40_records
        if isinstance(item, dict)
    ]

    status_counts = Counter(item["object_status"] for item in records)
    blocker_counts = Counter(blocker for item in records for blocker in item["blockers"])
    domain_counts = Counter(item["domain_family"] for item in records)
    tree_counts = Counter(item["tree_id"] for item in records)

    lower_bound_ready_count = sum(item["positive_axis_norm_lower_bound_ready"] for item in records)
    contract_ready_count = sum(item["axis_nondegeneracy_contract_ready"] for item in records)
    symbolic_ready_count = sum(item["symbolic_axis_norm_lower_bound_ready"] for item in records)

    manifest = {
        "accepted_real_b05_report_count": 0,
        "axis_nondegeneracy_contract_ready_count": contract_ready_count,
        "backend_id": BACKEND_ID,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "input_r40_manifest": rel(r40_manifest_path),
        "input_r41_manifest": rel(r41_manifest_path),
        "input_r42_manifest": rel(r42_manifest_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "positive_axis_norm_lower_bound_ready_count": lower_bound_ready_count,
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "record_count_by_tree_id": dict(sorted(tree_counts.items())),
        "records": records,
        "recommended_next_task": (
            "R44: implement B05 support labels, component motion bounds, "
            "and M_gap/M_L/M_U interval margins using the now-ready axis "
            "nondegeneracy contract."
        ),
        "symbolic_axis_norm_lower_bound_ready_count": symbolic_ready_count,
        "uniform_axis_norm_square_lower_bound": fraction_json(LOWER_BOUND),
        "uniform_symbolic_factor": EXPECTED_FACTOR,
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R40 records: {len(records)}")
    print(f"symbolic axis norm lower bounds ready: {symbolic_ready_count}")
    print(f"positive axis norm lower bounds ready: {lower_bound_ready_count}")
    print(f"axis-nondegeneracy contract ready: {contract_ready_count}")
    print(f"accepted real B05 reports: 0")
    print(f"uniform lower bound: {LOWER_BOUND}")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"blocker counts: {dict(sorted(blocker_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")

    if len(records) != len(r40_records):
        return 1
    if symbolic_ready_count != len(records) or lower_bound_ready_count != len(records):
        return 1
    if contract_ready_count != len(records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
