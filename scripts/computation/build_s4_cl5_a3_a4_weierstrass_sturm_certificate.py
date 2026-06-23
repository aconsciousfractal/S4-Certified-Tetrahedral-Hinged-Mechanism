#!/usr/bin/env python
"""
Build A3/A4 Weierstrass/Sturm sign certificates for the A2 B05 pilots.

This consumes the A2 symbolic common-edge pilot records.  It proves, with exact
Sturm root counts on rational t-intervals, the uniform positivity of the A2
common-edge raw gap, axis norm square, and normalized gap square on the open
ray domain (theta in (0, 120 degrees], represented by t=tan(theta/2)).

It also audits the support-switch inequalities induced by the A2 projection
charts.  The support signature M_AB/M_CD is certified only on the near branch
0 < t < 1 (theta in (0, 90 degrees)); every current record has a support switch
root at t=1 for one of its competition inequalities.  Therefore this remains a
sign certificate plus support-switch audit, not a full B05 proof and not an
accepted report.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A3-A4-WEIERSTRASS-STURM-SIGN-CERTIFICATE-2026-06-22"
CLAIM_LEVEL = "WEIERSTRASS_STURM_SIGN_CERTIFICATE"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"

DEFAULT_A2_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a2_symbolic_ray_model_pilot_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "a3_a4_weierstrass_sturm_certificate"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a3_a4_weierstrass_sturm_certificate_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_full_domain_support_stability_claim",
    "no_operation_enclosure_claim",
    "no_full_b05_proof_claim",
    "no_physical_hingeability_claim",
    "no_theorem_promotion_claim",
]

T = sp.symbols("t")
S = sp.symbols("s")
C = sp.symbols("c")
EPS = sp.symbols("eps", positive=True)
LOCAL = {"s": S, "c": C, "t": T, "sqrt": sp.sqrt}
WEIERSTRASS_SUBS = {
    S: 2 * T / (1 + T * T),
    C: (1 - T * T) / (1 + T * T),
}
SUPPORT_RE = re.compile(r"lower=(P\d)\[([^\]]*)\]\|upper=(P\d)\[([^\]]*)\]")


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


def sympify_expr(expr: str) -> sp.Expr:
    return sp.sympify(expr, locals=LOCAL)


def weierstrass(expr: sp.Expr) -> tuple[sp.Expr, sp.Expr, sp.Expr]:
    rational = sp.factor(sp.together(expr.subs(WEIERSTRASS_SUBS)))
    num, den = sp.fraction(rational)
    return sp.factor(rational), sp.factor(num), sp.factor(den)


def sign_of_expr(expr: sp.Expr) -> int:
    expr = sp.simplify(expr)
    if expr == 0:
        return 0
    if bool(expr > 0):
        return 1
    if bool(expr < 0):
        return -1
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
    for (degree,), coeff in sorted(poly.terms(), key=lambda item: item[0][0]):
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
    sturm_sequence = [sp.factor(item) for item in sp.sturm(poly_expr, T)]
    signs_left = [sign_from_eps_expansion(item, endpoint=lo, side="right") for item in sturm_sequence]
    signs_right = [sign_from_eps_expansion(item, endpoint=hi, side="left") for item in sturm_sequence]
    var_left = variations(signs_left)
    var_right = variations(signs_right)
    return {
        "open_root_count": int(var_left - var_right),
        "sturm_sequence": [str(item) for item in sturm_sequence],
        "signs_at_left_limit": signs_left,
        "signs_at_right_limit": signs_right,
        "variation_left": var_left,
        "variation_right": var_right,
    }


def sign_certificate_for_rational(
    *,
    name: str,
    expr: sp.Expr,
    interval_name: str,
    lo: sp.Rational,
    hi: sp.Rational,
    sample: sp.Rational,
) -> dict[str, Any]:
    rational, num, den = weierstrass(expr)
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
        "certificate_id": name,
        "denominator": str(den),
        "denominator_sample_sign": sample_den,
        "denominator_sturm": den_cert,
        "interval": {
            "hi": str(hi),
            "lo": str(lo),
            "name": interval_name,
            "open_interval": True,
            "sample": str(sample),
        },
        "numerator": str(num),
        "numerator_sample_sign": sample_num,
        "numerator_sturm": num_cert,
        "positive_on_open_interval": positive,
        "rational_expr": str(rational),
    }


def parse_support_signature(signature: str) -> tuple[str, list[str], str, list[str]]:
    match = SUPPORT_RE.fullmatch(signature)
    if not match:
        raise ValueError(f"unexpected support signature: {signature}")
    lower_piece, lower_labels, upper_piece, upper_labels = match.groups()
    return (
        lower_piece,
        [label for label in lower_labels.split(",") if label],
        upper_piece,
        [label for label in upper_labels.split(",") if label],
    )


def competition_exprs(record: dict[str, Any]) -> list[dict[str, Any]]:
    lower_piece, lower_support, upper_piece, upper_support = parse_support_signature(
        str(record["common_edge_support_signature"])
    )
    table = record["projection_table_on_n_ij"]
    out = []
    for piece, support_labels, side in [
        (lower_piece, lower_support, "lower_max_support"),
        (upper_piece, upper_support, "upper_min_support"),
    ]:
        all_labels = sorted(table[piece])
        nonsupport = [label for label in all_labels if label not in support_labels]
        for support_label in support_labels:
            support_projection = sympify_expr(table[piece][support_label])
            for nonsupport_label in nonsupport:
                nonsupport_projection = sympify_expr(table[piece][nonsupport_label])
                if side == "lower_max_support":
                    trig_expr = sp.factor(support_projection - nonsupport_projection)
                    semantic = "support_projection_minus_nonsupport_projection_positive"
                else:
                    trig_expr = sp.factor(nonsupport_projection - support_projection)
                    semantic = "nonsupport_projection_minus_support_projection_positive"
                out.append({
                    "piece": piece,
                    "semantic": semantic,
                    "side": side,
                    "support_label": support_label,
                    "nonsupport_label": nonsupport_label,
                    "trig_expr": trig_expr,
                })
    return out


def support_condition_certificate(condition: dict[str, Any]) -> dict[str, Any]:
    trig_expr = condition["trig_expr"]
    rational, num, den = weierstrass(trig_expr)
    near = sign_certificate_for_rational(
        name="support_condition_near_branch_t_open_0_1",
        expr=trig_expr,
        interval_name="near_branch_t_in_(0,1)_theta_in_(0,90deg)",
        lo=sp.Rational(0),
        hi=sp.Rational(1),
        sample=sp.Rational(1, 2),
    )
    post = sign_certificate_for_rational(
        name="support_condition_post_switch_t_open_1_2_superset",
        expr=trig_expr,
        interval_name="post_switch_probe_t_in_(1,2)",
        lo=sp.Rational(1),
        hi=sp.Rational(2),
        sample=sp.Rational(3, 2),
    )
    endpoint_roots = []
    for endpoint in [sp.Rational(0), sp.Rational(1), sp.Rational(2)]:
        if sp.simplify(num.subs(T, endpoint)) == 0:
            endpoint_roots.append(str(endpoint))
    out = dict(condition)
    out.update({
        "endpoint_roots_in_audit_grid": endpoint_roots,
        "near_branch_positive": near["positive_on_open_interval"],
        "near_branch_sturm_certificate": near,
        "post_switch_positive": post["positive_on_open_interval"],
        "post_switch_sample_sign": post["numerator_sample_sign"] * post["denominator_sample_sign"],
        "post_switch_sturm_certificate": post,
        "rational_expr": str(rational),
        "weierstrass_denominator": str(den),
        "weierstrass_numerator": str(num),
        "trig_expr": str(trig_expr),
    })
    return out


def build_record(summary: dict[str, Any], global_certs: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    pilot_path = ROOT / summary["object_record"]
    pilot = read_json(pilot_path)
    support_conditions = [support_condition_certificate(item) for item in competition_exprs(pilot)]
    all_near = all(item["near_branch_positive"] for item in support_conditions)
    all_post = all(item["post_switch_positive"] for item in support_conditions)
    has_switch_at_1 = any("1" in item["endpoint_roots_in_audit_grid"] for item in support_conditions)
    if all_near and has_switch_at_1:
        status = "a3_a4_gap_axis_certified_support_near_branch_only_switch_at_t_1"
    elif all_near:
        status = "a3_a4_gap_axis_certified_support_near_branch_only"
    else:
        status = "a3_a4_gap_axis_certified_support_near_branch_blocked"
    record = {
        "accepted_real_b05_report": False,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "full_domain_gap_axis_positive": bool(
            global_certs["raw_common_edge_gap"]["positive_on_open_interval"]
            and global_certs["axis_norm_square"]["positive_on_open_interval"]
            and global_certs["normalized_gap_square"]["positive_on_open_interval"]
        ),
        "full_domain_support_signature_positive": all_post and all_near and not has_switch_at_1,
        "global_sign_certificates_ref": "manifest.global_sign_certificates",
        "input_a2_pilot_record": rel(pilot_path),
        "manifest_id": MANIFEST_ID,
        "near_branch_support_signature_positive": all_near,
        "nonclaim": NONCLAIMS,
        "object_id": f"A3-A4-STURM-{sanitize(summary['original_report_id'])}",
        "object_status": status,
        "original_report_id": summary["original_report_id"],
        "piece_pair": summary["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": "A5: partition at t=1 or replace the current support signature with the correct post-switch signature, then repeat the support-switch audit.",
        "support_signature": summary["common_edge_support_signature"],
        "support_switch_audit": {
            "certified_near_branch_t_interval": "0 < t < 1",
            "full_ray_t_domain": "0 < t <= sqrt(3)",
            "post_switch_probe_interval": "1 < t < 2 (superset contains the post-switch part of the S4 ray domain)",
            "support_conditions": support_conditions,
            "switch_root_t_1_detected": has_switch_at_1,
            "switch_theta_degrees": 90 if has_switch_at_1 else None,
        },
        "symbolic_sign_certificate_ready": True,
        "tree_id": summary["tree_id"],
    }
    out_path = out_dir / "records" / summary["domain_family"] / f"{sanitize(summary['original_report_id'])}_a3_a4_sturm_certificate.json"
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "full_domain_gap_axis_positive": record["full_domain_gap_axis_positive"],
        "full_domain_support_signature_positive": record["full_domain_support_signature_positive"],
        "near_branch_support_signature_positive": record["near_branch_support_signature_positive"],
        "object_record": rel(out_path),
        "object_status": status,
        "original_report_id": summary["original_report_id"],
        "piece_pair": summary["piece_pair"],
        "support_signature": summary["common_edge_support_signature"],
        "switch_root_t_1_detected": has_switch_at_1,
        "tree_id": summary["tree_id"],
    }


def global_sign_certificates() -> dict[str, Any]:
    raw_gap = sp.sqrt(2) * S * S / 4
    axis_norm_square = S * S * (2 - S * S) / 4
    normalized_gap_square = S * S / (2 * (2 - S * S))
    return {
        "axis_norm_square": sign_certificate_for_rational(
            name="axis_norm_square_full_ray_open_domain_superset",
            expr=axis_norm_square,
            interval_name="full_ray_open_t_domain_superset_(0,2)_contains_(0,sqrt(3)]",
            lo=sp.Rational(0),
            hi=sp.Rational(2),
            sample=sp.Rational(1),
        ),
        "normalized_gap_square": sign_certificate_for_rational(
            name="normalized_gap_square_full_ray_open_domain_superset",
            expr=normalized_gap_square,
            interval_name="full_ray_open_t_domain_superset_(0,2)_contains_(0,sqrt(3)]",
            lo=sp.Rational(0),
            hi=sp.Rational(2),
            sample=sp.Rational(1),
        ),
        "raw_common_edge_gap": sign_certificate_for_rational(
            name="raw_common_edge_gap_full_ray_open_domain_superset",
            expr=raw_gap,
            interval_name="full_ray_open_t_domain_superset_(0,2)_contains_(0,sqrt(3)]",
            lo=sp.Rational(0),
            hi=sp.Rational(2),
            sample=sp.Rational(1),
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a2-manifest", default=DEFAULT_A2_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    a2_manifest_path = ROOT / args.a2_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    a2 = read_json(a2_manifest_path)
    records = a2.get("records")
    if not isinstance(records, list):
        raise TypeError("A2 manifest must expose records list")
    global_certs = global_sign_certificates()
    emitted = [build_record(item, global_certs, out_dir) for item in records]
    status_counts = Counter(item["object_status"] for item in emitted)
    support_full_count = sum(1 for item in emitted if item["full_domain_support_signature_positive"])
    support_near_count = sum(1 for item in emitted if item["near_branch_support_signature_positive"])
    switch_count = sum(1 for item in emitted if item["switch_root_t_1_detected"])
    manifest = {
        "accepted_real_b05_report_count": 0,
        "a2_manifest": rel(a2_manifest_path),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "global_sign_certificates": global_certs,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(status_counts.items())),
        "predicate_id": PREDICATE_ID,
        "record_count": len(emitted),
        "records": emitted,
        "recommended_next_task": "A5: split the one-parameter ray at t=1 (theta=90 degrees) or derive post-switch support signatures; then certify support stability on each branch.",
        "support_full_domain_positive_count": support_full_count,
        "support_near_branch_positive_count": support_near_count,
        "support_switch_root_t_1_count": switch_count,
        "weierstrass_domain_notes": {
            "full_ray_theta_domain_degrees": "0 < theta <= 120",
            "full_ray_t_domain": "0 < t <= sqrt(3)",
            "sturm_full_domain_superset": "0 < t < 2",
            "support_near_branch": "0 < t < 1, i.e. 0 < theta < 90 degrees",
        },
    }
    write_json_lf(manifest_path, manifest)
    print(f"A3/A4 records emitted: {len(emitted)}")
    print(f"gap/axis full-domain certificates: {all(c['positive_on_open_interval'] for c in global_certs.values())}")
    print(f"near-branch support signatures certified: {support_near_count}/{len(emitted)}")
    print(f"full-domain support signatures certified: {support_full_count}/{len(emitted)}")
    print(f"support switch root t=1 detected: {switch_count}/{len(emitted)}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
