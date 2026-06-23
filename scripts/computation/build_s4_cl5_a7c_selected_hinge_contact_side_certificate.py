#!/usr/bin/env python
"""
Build A7c selected-hinge B04 contact-side certificates for the S4 ray.

A7c closes the one-parameter selected-hinge contact-side layer.  Selected
hinges are zero-margin boundary contacts, so this is not a B03 positive SAT
clearance certificate.  The exact one-variable fact is:

    d_h(theta) = s_h * theta,  s_h in {+1,-1}

and under the Weierstrass half-angle parameter t = tan(theta/2), the signed
orientation has the same sign as s_h * t.  On the rational open superset
0 < t < 2, this expression has no interior root and has constant sign; the
same interval lies inside one open half-turn.  It contains the audited S4 ray
domain 0 < t <= sqrt(3), i.e. 0 < theta <= 120 degrees.

The emitted records combine that exact sign certificate with the source-locked
Lemma 02 closed endpoint, Lemma 03 hinge-axis preservation, and the B04 review's
local contact-side semantics.  They do not emit accepted schema-v1 reports,
positive-clearance claims, bounded-cell claims, operation enclosures, physical
hingeability claims, or theorem promotion.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

import sympy as sp


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402


CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A7C-SELECTED-HINGE-CONTACT-SIDE-CERTIFICATE-2026-06-22"
CLAIM_LEVEL = "SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE"
PREDICATE_ID = "B04_SELECTED_HINGE_CONTACT_SIDE"

DEFAULT_SOURCE = Path("results/historical_s4_median_planes/two_class_contact_orientation_report.json")
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/"
    "a7c_selected_hinge_contact_side_certificate"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/"
    "manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json"
)

NONCLAIMS = [
    "no_b03_positive_clearance_claim",
    "no_b04_accepted_schema_v1_report_claim",
    "no_bounded_cell_b04_claim",
    "no_non_hinge_contact_claim",
    "no_residual_contact_claim",
    "no_operation_enclosure_claim",
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
            "signs_at_left_limit": [sign_of_expr(poly_expr)],
            "signs_at_right_limit": [sign_of_expr(poly_expr)],
            "sturm_sequence": [str(poly_expr)],
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
        "signs_at_left_limit": signs_left,
        "signs_at_right_limit": signs_right,
        "sturm_sequence": [str(item) for item in sequence],
        "variation_left": var_left,
        "variation_right": var_right,
    }


def sign_certificate(sign: int) -> dict[str, Any]:
    if sign not in {-1, 1}:
        raise ValueError(f"unexpected sign: {sign}")
    expr = sp.factor(sign * T)
    lo = sp.Rational(0)
    hi = sp.Rational(2)
    sample = sp.Rational(1)
    cert = sturm_open_root_count(expr, lo, hi)
    sample_sign = sign_of_expr(expr.subs(T, sample))
    expected = sign
    certified = cert["open_root_count"] == 0 and sample_sign == expected
    return {
        "certificate_id": f"a7c_selected_hinge_signed_orientation_{'positive' if sign > 0 else 'negative'}",
        "signed_ray_formula": f"d_h(theta) = {sign} * theta",
        "weierstrass_substitution": "t = tan(theta/2)",
        "signed_orientation_polynomial": str(expr),
        "orientation_sturm": cert,
        "sample_t": str(sample),
        "sample_sign": sample_sign,
        "expected_sign": expected,
        "constant_nonzero_sign_on_open_interval": certified,
        "endpoint_roots_excluded": ["t=0 (theta=0 closed-contact endpoint excluded)"],
        "open_half_turn_certificate": {
            "open_interval": "0 < t < 2",
            "theta_relation": "theta = 2*atan(t)",
            "half_turn_reason": "0 < t < 2 implies 0 < theta < 2*atan(2) < pi",
            "contains_real_s4_ray_domain": "0 < t <= sqrt(3)",
            "theta_domain_degrees": "0 < theta <= 120",
        },
    }


def selected_pair_summaries(audit: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for item in audit.get("pair_summary", []):
        if item.get("role") == "selected_hinge_contact":
            out[tuple(item["pair"])] = item
    return out


def build_record(
    *,
    class_id: str,
    tree_id: str,
    hinge: dict[str, Any],
    contact: dict[str, Any],
    sign: int,
    pair_summary: dict[str, Any],
    cert: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    pair = list(hinge["pieces"])
    certified = (
        cert["constant_nonzero_sign_on_open_interval"]
        and pair_summary.get("orientation_certified_cell_count") == pair_summary.get("cell_count")
        and contact.get("type") == "shared_face"
    )
    record = {
        "accepted_real_report": False,
        "axis_labels": hinge.get("axis_labels"),
        "axis_length": hinge.get("axis_length"),
        "axis_points": hinge.get("axis_points"),
        "axis_support": hinge.get("axis_support"),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "class_id": class_id,
        "contact_side_semantics": {
            "closed_endpoint_contact_source": "S4_LEMMA_02_CLOSED_ENDPOINT",
            "hinge_axis_preservation_source": "S4_LEMMA_03_KINEMATICS_AND_SIGNS",
            "local_contact_side_review_source": "S4_CL5_SELECTED_HINGE_CONTACT_ORIENTATION_REVIEW",
            "meaning": (
                "opening on the package-approved signed side gives boundary hinge contact "
                "for the selected shared-face route, not positive SAT clearance"
            ),
        },
        "hinge_id": hinge["hinge_id"],
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"A7C-B04-{sanitize(tree_id)}-{sanitize(hinge['hinge_id'])}",
        "object_status": (
            "a7c_selected_hinge_contact_side_certified_on_open_ray_superset"
            if certified
            else "a7c_selected_hinge_contact_side_blocked"
        ),
        "pair": pair,
        "predicate_id": PREDICATE_ID,
        "ray_sign": sign,
        "ray_sign_source": "S4_LEMMA_03_KINEMATICS_AND_SIGNS and two_class_contact_orientation_report",
        "selected_pair_source_summary": pair_summary,
        "sign_certificate": cert,
        "source_contact": contact["contact_id"],
        "source_contact_type": contact["type"],
        "tree_id": tree_id,
    }
    path = out_dir / "records" / f"{sanitize(tree_id)}_{sanitize(hinge['hinge_id'])}_a7c_b04_contact_side.json"
    write_json_lf(path, record)
    return {
        "contact_side_certified": certified,
        "hinge_id": hinge["hinge_id"],
        "object_record": rel(path),
        "object_status": record["object_status"],
        "pair": pair,
        "ray_sign": sign,
        "tree_id": tree_id,
    }


def build_records(source: dict[str, Any], out_dir: Path) -> list[dict[str, Any]]:
    if not source.get("summary_metrics", {}).get("all_selected_hinge_contacts_orientation_certified"):
        raise ValueError("source finite overlay does not certify all selected hinge contacts")

    case = batch.build_case()
    contacts_by_id = {item["contact_id"]: item for item in case["contacts"]}
    emitted: list[dict[str, Any]] = []
    for audit in source.get("representative_audits", []):
        class_id = audit["class_id"]
        tree_id = audit["tree_id"]
        pair_summaries = selected_pair_summaries(audit)
        signs = {hinge_id: int(sign) for hinge_id, sign in audit["ray_signs_by_hinge"].items()}
        tree = comp.find_tree(case, tree_id)
        for hinge_id in tree["hinge_ids"]:
            hinge = case["hinge_by_id"][hinge_id]
            pair_key = tuple(hinge["pieces"])
            if pair_key not in pair_summaries:
                raise ValueError(f"selected hinge pair missing from source summary: {tree_id} {pair_key}")
            sign = signs[hinge_id]
            contact = contacts_by_id[hinge["source_contact"]]
            cert = sign_certificate(sign)
            emitted.append(
                build_record(
                    class_id=class_id,
                    tree_id=tree_id,
                    hinge=hinge,
                    contact=contact,
                    sign=sign,
                    pair_summary=pair_summaries[pair_key],
                    cert=cert,
                    out_dir=out_dir,
                )
            )
    return emitted


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
    emitted = build_records(source, out_dir)

    sign_counts = Counter(str(item["ray_sign"]) for item in emitted)
    status_counts = Counter(item["object_status"] for item in emitted)
    certified_count = sum(1 for item in emitted if item["contact_side_certified"])
    manifest = {
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "contact_side_certificate_count": certified_count,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(status_counts.items())),
        "predicate_id": PREDICATE_ID,
        "ray_domain": {
            "audited_domain": "0 < theta <= 120 degrees",
            "audited_half_angle_domain": "0 < t <= sqrt(3)",
            "certified_open_superset": "0 < t < 2",
            "closed_endpoint": "theta=0 handled by Lemma 02, excluded from open sign certificates",
        },
        "recommended_next_task": ("Post-A7d review/red-team of the scoped one-parameter wrapper; " "keep three-parameter bounded cells and physical hingeability as later extensions."),
        "record_count": len(emitted),
        "records": emitted,
        "ray_sign_counts": dict(sorted(sign_counts.items())),
        "source_contact_orientation_report": rel(source_path),
        "source_summary_metrics": source.get("summary_metrics", {}),
    }
    write_json_lf(manifest_path, manifest)
    print(f"A7c selected-hinge records emitted: {len(emitted)}")
    print(f"A7c contact-side certificates: {certified_count}/{len(emitted)}")
    print(f"ray sign counts: {dict(sorted(sign_counts.items()))}")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")
    return 0 if certified_count == len(emitted) else 2


if __name__ == "__main__":
    raise SystemExit(main())
