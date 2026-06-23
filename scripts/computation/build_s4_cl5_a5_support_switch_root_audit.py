#!/usr/bin/env python
"""
Build A5 support/branch switch-root audit for the A2/A3-A4 B05 pilots.

A3/A4 proved that the A2 common-edge gap and axis are positive on the open ray
but that the A2 common-edge support signature only holds on 0 < t < 1.  A5
splits at the exact switch root t=1, keeps the A2 support signature on the near
branch, derives the post-switch support signature from the exact projection
chart, and certifies the post-switch support and projection gap on 1 < t < 7/4
(a rational superset containing the S4 post-switch ray branch 1 < t <= sqrt(3)).

This remains an algebraic support-switch audit.  It does not emit accepted B05
reports, operation enclosures, or theorem promotion.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A5-SUPPORT-SWITCH-ROOT-AUDIT-2026-06-22"
CLAIM_LEVEL = "SUPPORT_SWITCH_ROOT_AUDIT"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"

DEFAULT_A3_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a3_a4_weierstrass_sturm_certificate_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "a5_support_switch_root_audit"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a5_support_switch_root_audit_manifest.json"
)
A3_SCRIPT = Path("scripts/build_s4_cl5_a3_a4_weierstrass_sturm_certificate.py")

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_operation_enclosure_claim",
    "no_full_b05_report_proof_claim",
    "no_physical_hingeability_claim",
    "no_theorem_promotion_claim",
]


def load_helper():
    spec = importlib.util.spec_from_file_location("a3_a4_sturm", ROOT / A3_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import helper: {A3_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A3 = load_helper()
T = A3.T


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
    return A3.sanitize(value)


def projection_expr(table: dict[str, Any], piece: str, label: str) -> sp.Expr:
    return A3.sympify_expr(str(table[piece][label]))


def value_at_sample(expr: sp.Expr, sample: sp.Rational) -> sp.Expr:
    rational, _num, _den = A3.weierstrass(expr)
    return sp.simplify(rational.subs(T, sample))


def sign_cert(name: str, expr: sp.Expr, lo: sp.Rational, hi: sp.Rational, sample: sp.Rational) -> dict[str, Any]:
    return A3.sign_certificate_for_rational(
        name=name,
        expr=expr,
        interval_name=f"t_in_({lo},{hi})",
        lo=lo,
        hi=hi,
        sample=sample,
    )


def extrema_labels(table: dict[str, Any], piece: str, mode: str, sample: sp.Rational) -> list[str]:
    values = []
    for label in sorted(table[piece]):
        expr = projection_expr(table, piece, label)
        values.append((label, value_at_sample(expr, sample)))
    target = max(v for _label, v in values) if mode == "max" else min(v for _label, v in values)
    return [label for label, value in values if sp.simplify(value - target) == 0]


def support_competition_certs(
    table: dict[str, Any],
    *,
    piece: str,
    support_labels: list[str],
    side: str,
    lo: sp.Rational,
    hi: sp.Rational,
    sample: sp.Rational,
) -> list[dict[str, Any]]:
    all_labels = sorted(table[piece])
    nonsupport = [label for label in all_labels if label not in support_labels]
    out = []
    for support_label in support_labels:
        support = projection_expr(table, piece, support_label)
        for nonsupport_label in nonsupport:
            other = projection_expr(table, piece, nonsupport_label)
            if side == "lower_max_support":
                expr = sp.factor(support - other)
                semantic = "support_projection_minus_nonsupport_projection_positive"
            elif side == "upper_min_support":
                expr = sp.factor(other - support)
                semantic = "nonsupport_projection_minus_support_projection_positive"
            else:
                raise ValueError(side)
            cert = sign_cert(
                f"{side}_{piece}_{support_label}_vs_{nonsupport_label}",
                expr,
                lo,
                hi,
                sample,
            )
            rational, num, den = A3.weierstrass(expr)
            out.append({
                "denominator": str(den),
                "nonsupport_label": nonsupport_label,
                "numerator": str(num),
                "piece": piece,
                "positive_on_branch": cert["positive_on_open_interval"],
                "rational_expr": str(rational),
                "semantic": semantic,
                "side": side,
                "sturm_certificate": cert,
                "support_label": support_label,
                "trig_expr": str(expr),
            })
    return out


def branch_gap_cert(
    table: dict[str, Any],
    *,
    lower_piece: str,
    lower_support_labels: list[str],
    upper_piece: str,
    upper_support_labels: list[str],
    lo: sp.Rational,
    hi: sp.Rational,
    sample: sp.Rational,
) -> dict[str, Any]:
    # The support labels tied on an edge have identical projection expressions;
    # using the first label is therefore enough for the branch gap expression.
    lower = projection_expr(table, lower_piece, lower_support_labels[0])
    upper = projection_expr(table, upper_piece, upper_support_labels[0])
    expr = sp.factor(upper - lower)
    cert = sign_cert("branch_projection_gap", expr, lo, hi, sample)
    rational, num, den = A3.weierstrass(expr)
    return {
        "denominator": str(den),
        "numerator": str(num),
        "positive_on_branch": cert["positive_on_open_interval"],
        "rational_expr": str(rational),
        "sturm_certificate": cert,
        "trig_expr": str(expr),
    }


def signature(piece_lower: str, lower_labels: list[str], piece_upper: str, upper_labels: list[str]) -> str:
    return (
        f"lower={piece_lower}[{','.join(lower_labels)}]"
        f"|upper={piece_upper}[{','.join(upper_labels)}]"
    )


def build_record(summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    a3_record_path = ROOT / summary["object_record"]
    a3_record = read_json(a3_record_path)
    a2_record_path = ROOT / a3_record["input_a2_pilot_record"]
    a2_record = read_json(a2_record_path)
    table = a2_record["projection_table_on_n_ij"]
    lower_piece = str(a2_record["lower_piece"])
    upper_piece = str(a2_record["upper_piece"])

    near_lower_labels = list(a2_record["lower_support_labels"])
    near_upper_labels = list(a2_record["upper_support_labels"])
    post_lower_labels = extrema_labels(table, lower_piece, "max", sp.Rational(3, 2))
    post_upper_labels = extrema_labels(table, upper_piece, "min", sp.Rational(3, 2))

    post_competition = []
    post_competition += support_competition_certs(
        table,
        piece=lower_piece,
        support_labels=post_lower_labels,
        side="lower_max_support",
        lo=sp.Rational(1),
        hi=sp.Rational(7, 4),
        sample=sp.Rational(3, 2),
    )
    post_competition += support_competition_certs(
        table,
        piece=upper_piece,
        support_labels=post_upper_labels,
        side="upper_min_support",
        lo=sp.Rational(1),
        hi=sp.Rational(7, 4),
        sample=sp.Rational(3, 2),
    )
    post_gap = branch_gap_cert(
        table,
        lower_piece=lower_piece,
        lower_support_labels=post_lower_labels,
        upper_piece=upper_piece,
        upper_support_labels=post_upper_labels,
        lo=sp.Rational(1),
        hi=sp.Rational(7, 4),
        sample=sp.Rational(3, 2),
    )
    post_support_positive = all(item["positive_on_branch"] for item in post_competition)
    post_gap_positive = bool(post_gap["positive_on_branch"])
    near_support_positive = bool(a3_record["near_branch_support_signature_positive"])
    full_gap_axis_positive = bool(a3_record["full_domain_gap_axis_positive"])
    branchwise_ready = bool(
        full_gap_axis_positive
        and near_support_positive
        and post_support_positive
        and post_gap_positive
    )
    status = (
        "a5_branchwise_support_switch_audit_ready_for_one_parameter_closure"
        if branchwise_ready
        else "a5_branchwise_support_switch_audit_blocked"
    )
    record = {
        "accepted_real_b05_report": False,
        "branchwise_support_gap_axis_certificate_ready": branchwise_ready,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "full_domain_gap_axis_positive_from_a3_a4": full_gap_axis_positive,
        "input_a2_pilot_record": rel(a2_record_path),
        "input_a3_a4_record": rel(a3_record_path),
        "manifest_id": MANIFEST_ID,
        "near_branch": {
            "branch_interval": "0 < t < 1",
            "gap_axis_positive_from_a3_a4": full_gap_axis_positive,
            "support_signature": signature(lower_piece, near_lower_labels, upper_piece, near_upper_labels),
            "support_signature_positive_from_a3_a4": near_support_positive,
        },
        "nonclaim": NONCLAIMS,
        "object_id": f"A5-SUPPORT-SWITCH-{sanitize(summary['original_report_id'])}",
        "object_status": status,
        "original_report_id": summary["original_report_id"],
        "piece_pair": summary["piece_pair"],
        "post_switch_branch": {
            "branch_interval": "1 < t < 7/4 (rational superset of 1 < t <= sqrt(3))",
            "derived_support_signature": signature(lower_piece, post_lower_labels, upper_piece, post_upper_labels),
            "projection_gap_certificate": post_gap,
            "projection_gap_positive": post_gap_positive,
            "support_competition_certificates": post_competition,
            "support_signature_positive": post_support_positive,
        },
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": "A6: package the two certified support branches plus the A3/A4 gap/axis certificates into a one-parameter ray closure non-overlap certificate.",
        "switch_root": {
            "t": "1",
            "theta_degrees": 90,
            "source": "A3/A4 support competition endpoint-root audit",
        },
        "tree_id": summary["tree_id"],
    }
    out_path = out_dir / "records" / f"{sanitize(summary['original_report_id'])}_a5_support_switch_audit.json"
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "branchwise_support_gap_axis_certificate_ready": branchwise_ready,
        "derived_post_switch_support_signature": record["post_switch_branch"]["derived_support_signature"],
        "near_support_signature": record["near_branch"]["support_signature"],
        "object_record": rel(out_path),
        "object_status": status,
        "original_report_id": summary["original_report_id"],
        "piece_pair": summary["piece_pair"],
        "post_projection_gap_positive": post_gap_positive,
        "post_support_signature_positive": post_support_positive,
        "tree_id": summary["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a3-manifest", default=DEFAULT_A3_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    a3_manifest_path = ROOT / args.a3_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    a3_manifest = read_json(a3_manifest_path)
    records = a3_manifest.get("records")
    if not isinstance(records, list):
        raise TypeError("A3/A4 manifest must expose records list")
    emitted = [build_record(item, out_dir) for item in records]
    status_counts = Counter(item["object_status"] for item in emitted)
    post_signature_counts = Counter(item["derived_post_switch_support_signature"] for item in emitted)
    ready_count = sum(1 for item in emitted if item["branchwise_support_gap_axis_certificate_ready"])
    manifest = {
        "accepted_real_b05_report_count": 0,
        "a3_a4_manifest": rel(a3_manifest_path),
        "branchwise_ready_count": ready_count,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(status_counts.items())),
        "post_switch_support_signature_counts": dict(sorted(post_signature_counts.items())),
        "predicate_id": PREDICATE_ID,
        "record_count": len(emitted),
        "records": emitted,
        "recommended_next_task": "A6: package A3/A4 and A5 branchwise certificates into a one-parameter ray closure certificate; accepted reports and operation enclosures remain out of scope.",
        "switch_root": {"t": "1", "theta_degrees": 90},
    }
    write_json_lf(manifest_path, manifest)
    print(f"A5 records emitted: {len(emitted)}")
    print(f"branchwise support/gap/axis ready: {ready_count}/{len(emitted)}")
    print(f"post-switch support signatures: {dict(sorted(post_signature_counts.items()))}")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
