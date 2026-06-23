#!/usr/bin/env python
"""
Build A7a Weierstrass/Sturm sign certificates for residual shared-face targets.

A7a consumes the Lemma-06 residual shared-face formula-check report and certifies
that the source-locked unnormalized triple product

    ((1 - cos(theta)) * sin(theta)) / 4

is positive on the open one-parameter S4 ray domain.  With t=tan(theta/2), the
expression becomes

    t^3 / (1 + t^2)^2,

so positivity is certified by exact Sturm/root-counting on the rational
superset 0 < t < 2, which contains the audited ray domain 0 < t <= sqrt(3)
(theta <= 120 degrees).

This is a sign certificate for the residual shared-face formula route.  It does
not emit accepted schema-v1 reports, ordinary B03 clearance certificates,
selected-hinge B04 certificates, physical hingeability, 3-parameter bounded-cell
closure, or theorem promotion.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A7A-SHARED-FACE-RESIDUAL-STURM-CERTIFICATE-2026-06-22"
CLAIM_LEVEL = "SHARED_FACE_RESIDUAL_STURM_CERTIFICATE"
PREDICATE_ID = "B06_B07_SHARED_FACE_RESIDUAL_FORMULA_SIGN"

DEFAULT_SOURCE = Path("results/historical_s4_median_planes/residual_shared_face_formula_check_report.json")
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/shared_face_residual/"
    "a7a_shared_face_residual_sturm_certificate"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/shared_face_residual/"
    "manifests/shared_face_a7a_residual_sturm_certificate_manifest.json"
)

NONCLAIMS = [
    "no_b03_clearance_sat_certificate_claim",
    "no_b04_selected_hinge_contact_certificate_claim",
    "no_b06_b07_accepted_report_claim",
    "no_operation_enclosure_claim",
    "no_full_one_parameter_ray_theorem_claim",
    "no_three_parameter_bounded_cell_claim",
    "no_physical_hingeability_claim",
    "no_theorem_promotion_claim",
]

T = sp.symbols("t")
EPS = sp.symbols("eps", positive=True)


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
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def sanitize(value: Any) -> str:
    text = str(value)
    out: list[str] = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def sign_of_expr(expr: sp.Expr) -> int:
    expr = sp.simplify(expr)
    if expr == 0:
        return 0
    try:
        if bool(expr > 0):
            return 1
        if bool(expr < 0):
            return -1
    except TypeError:
        pass
    numeric = sp.N(expr, 80)
    if numeric > 0:
        return 1
    if numeric < 0:
        return -1
    return 0


def sign_from_eps_expansion(expr: sp.Expr, *, endpoint: sp.Rational, side: str) -> int:
    if side == "right":
        expanded = sp.expand(expr.subs(T, endpoint + EPS))
    elif side == "left":
        expanded = sp.expand(expr.subs(T, endpoint - EPS))
    else:
        raise ValueError(side)
    poly = sp.Poly(expanded, EPS, extension=True)
    if poly.is_zero:
        return 0
    for (_degree,), coeff in sorted(poly.terms(), key=lambda item: item[0][0]):
        if coeff != 0:
            return sign_of_expr(coeff)
    return 0


def variations(signs: list[int]) -> int:
    nonzero = [item for item in signs if item != 0]
    return sum(1 for left, right in zip(nonzero, nonzero[1:]) if left * right < 0)


def sturm_open_root_count(poly_expr: sp.Expr, lo: sp.Rational, hi: sp.Rational) -> dict[str, Any]:
    poly_expr = sp.factor(poly_expr)
    if poly_expr == 0:
        raise ValueError("zero polynomial has no finite Sturm certificate")
    if T not in poly_expr.free_symbols:
        return {
            "open_root_count": 0,
            "sturm_sequence": [str(poly_expr)],
            "signs_at_left_limit": [sign_of_expr(poly_expr)],
            "signs_at_right_limit": [sign_of_expr(poly_expr)],
            "variation_left": 0,
            "variation_right": 0,
        }
    sequence = [sp.factor(item) for item in sp.sturm(poly_expr, T)]
    signs_left = [sign_from_eps_expansion(item, endpoint=lo, side="right") for item in sequence]
    signs_right = [sign_from_eps_expansion(item, endpoint=hi, side="left") for item in sequence]
    var_left = variations(signs_left)
    var_right = variations(signs_right)
    return {
        "open_root_count": int(var_left - var_right),
        "sturm_sequence": [str(item) for item in sequence],
        "signs_at_left_limit": signs_left,
        "signs_at_right_limit": signs_right,
        "variation_left": var_left,
        "variation_right": var_right,
    }


def sign_certificate() -> dict[str, Any]:
    expr = sp.factor(T**3 / (1 + T**2)**2)
    num, den = sp.fraction(expr)
    num = sp.factor(num)
    den = sp.factor(den)
    lo = sp.Rational(0)
    hi = sp.Rational(2)
    sample = sp.Rational(1)
    num_cert = sturm_open_root_count(num, lo, hi)
    den_cert = sturm_open_root_count(den, lo, hi)
    sample_num = sign_of_expr(num.subs(T, sample))
    sample_den = sign_of_expr(den.subs(T, sample))
    positive = (
        num_cert["open_root_count"] == 0
        and den_cert["open_root_count"] == 0
        and sample_num > 0
        and sample_den > 0
    )
    return {
        "certificate_id": "a7a_shared_face_residual_triple_positive_on_open_ray_superset",
        "theta_expression": "((1 - cos(theta)) * sin(theta)) / 4 = sin(theta/2)^3 * cos(theta/2)",
        "weierstrass_substitution": "t = tan(theta/2)",
        "rational_expr": str(expr),
        "numerator": str(num),
        "denominator": str(den),
        "numerator_sturm": num_cert,
        "denominator_sturm": den_cert,
        "numerator_sample_sign": sample_num,
        "denominator_sample_sign": sample_den,
        "positive_on_open_interval": positive,
        "endpoint_roots_excluded": ["t=0 (theta=0 closed-contact endpoint excluded)"],
        "interval": {
            "name": "full_open_ray_rational_superset",
            "open_interval": True,
            "lo": "0",
            "hi": "2",
            "sample": "1",
            "contains_real_s4_ray_domain": "0 < t <= sqrt(3)",
            "theta_domain_degrees": "0 < theta <= 120",
        },
    }


def build_record(target: dict[str, Any], cert: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    if target.get("candidate_formula") != "unnormalized_triple_product = sin(theta/2)^3 * cos(theta/2)":
        raise ValueError(f"unexpected candidate formula for {target.get('target_id')}")
    if not cert["positive_on_open_interval"]:
        status = "a7a_shared_face_residual_formula_sign_blocked"
    else:
        status = "a7a_shared_face_residual_formula_positive_on_open_ray_superset"
    record = {
        "accepted_real_report": False,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "formula_check_status_from_source": target.get("status"),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"A7A-SHARED-FACE-STURM-{sanitize(target['target_id'])}",
        "object_status": status,
        "pair": target["pair"],
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": "A7b: build route-clean B03 clearance SAT Sturm certificates, while A7c handles selected-hinge contact-side orientation.",
        "residual_shared_face_target": {
            "target_id": target["target_id"],
            "tree_id": target["tree_id"],
            "left_piece": target["left_piece"],
            "right_piece": target["right_piece"],
            "left_edge_labels": target["left_edge_labels"],
            "right_edge_labels": target["right_edge_labels"],
            "separation_vector_labels": target["separation_vector_labels"],
        },
        "sign_certificate": cert,
        "source_formula_report_metrics": target.get("summary_metrics", {}),
        "symbolic_sign_certificate_ready": bool(cert["positive_on_open_interval"]),
        "tree_id": target["tree_id"],
    }
    out_path = out_dir / "records" / f"{sanitize(target['target_id'])}_a7a_shared_face_residual_sturm_certificate.json"
    write_json_lf(out_path, record)
    return {
        "accepted_real_report": False,
        "object_record": rel(out_path),
        "object_status": status,
        "pair": target["pair"],
        "positive_on_open_ray_superset": bool(cert["positive_on_open_interval"]),
        "target_id": target["target_id"],
        "tree_id": target["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = ROOT / args.source
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    source = read_json(source_path)
    targets = source.get("target_reports")
    if not isinstance(targets, list):
        raise TypeError("source report must expose target_reports list")
    cert = sign_certificate()
    emitted = [build_record(target, cert, out_dir) for target in targets]
    status_counts = Counter(item["object_status"] for item in emitted)
    positive_count = sum(1 for item in emitted if item["positive_on_open_ray_superset"])
    manifest = {
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(status_counts.items())),
        "positive_on_open_ray_superset_count": positive_count,
        "predicate_id": PREDICATE_ID,
        "record_count": len(emitted),
        "records": emitted,
        "recommended_next_task": "A7b: build route-clean B03 clearance SAT Sturm certificates, while A7c handles selected-hinge contact-side orientation.",
        "shared_sign_certificate": cert,
        "source_formula_report": rel(source_path),
        "source_summary_metrics": source.get("summary_metrics", {}),
    }
    write_json_lf(manifest_path, manifest)
    print(f"A7a records emitted: {len(emitted)}")
    print(f"shared-face residual formula positive: {positive_count}/{len(emitted)}")
    print(f"accepted real reports: 0")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
