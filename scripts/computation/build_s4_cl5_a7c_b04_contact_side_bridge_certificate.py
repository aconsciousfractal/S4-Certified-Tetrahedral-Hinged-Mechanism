#!/usr/bin/env python
"""
Build the A7c/B04 contact-side bridge certificate for S4 selected hinges.

This script fills the semantic gap identified by the external red team:
A7c already proves a constant nonzero signed hinge angle on the one-parameter
open ray, but B04 also needs the local implication

    correct opening side + hinge-axis preservation => boundary hinge contact
    and no strict interior overlap for the selected shared-face pair.

The bridge is a local exact wedge certificate.  For every selected shared-face
hinge row, it checks in the normal cross-section around the oriented hinge
axis that:

1. the certified ray sign points to the child side of the shared face;
2. the parent apex is strictly on the opposite side;
3. the parent/child sector angle from the shared face is alpha with
   cos(alpha)=sqrt(6)/3 > 1/2, hence alpha < 60 degrees;
4. on the audited ray domain 0 < theta <= 120 degrees, the opened child sector
   remains strictly inside the child half-plane and cannot wrap around into
   the parent sector.

Together with Lemma 03 axis preservation, this proves that the selected pair
keeps only boundary hinge-axis contact and has no strict interior overlap in
the zero-thickness one-parameter model.  This is still not a positive SAT
clearance or physical hinge-thickness claim.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import sympy as sp

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]

CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A7C-B04-CONTACT-SIDE-BRIDGE-2026-06-23"
PREDICATE_ID = "B04_SELECTED_HINGE_CONTACT_SIDE_BRIDGE"
CLAIM_LEVEL = "LOCAL_EXACT_WEDGE_BRIDGE"

OUT_DIR = ROOT / "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/a7c_contact_side_bridge"
MANIFEST_PATH = ROOT / "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_contact_side_bridge_manifest.json"
DEFAULT_A7C_MANIFEST = ROOT / "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json"

NONCLAIMS = [
    "no_positive_sat_clearance_claim",
    "no_physical_hinge_thickness_claim",
    "no_mesh_or_cad_validation_claim",
    "no_three_parameter_bounded_cell_claim",
    "no_dynamic_connectedness_claim",
    "no_global_s4_hingeability_claim",
]

sqrt3 = sp.sqrt(3)
sqrt6 = sp.sqrt(6)
sqrt2 = sp.sqrt(2)
T = sp.symbols("t", positive=True)
COS_THETA = (1 - T**2) / (1 + T**2)
SIN_THETA_BASE = 2 * T / (1 + T**2)
POINTS = {
    "A": sp.Matrix([0, 0, 0]),
    "B": sp.Matrix([1, 0, 0]),
    "C": sp.Matrix([sp.Rational(1, 2), sqrt3 / 2, 0]),
    "D": sp.Matrix([sp.Rational(1, 2), sqrt3 / 6, sqrt6 / 3]),
}
POINTS["M_AB"] = (POINTS["A"] + POINTS["B"]) / 2
POINTS["M_CD"] = (POINTS["C"] + POINTS["D"]) / 2

PIECES = {
    "P0": ["A", "M_AB", "C", "M_CD"],
    "P1": ["A", "M_AB", "D", "M_CD"],
    "P2": ["B", "M_AB", "C", "M_CD"],
    "P3": ["B", "M_AB", "D", "M_CD"],
}

CONTACTS = {
    "C0": {"pair": ("P0", "P1"), "face": ["A", "M_AB", "M_CD"], "axis": ("A", "M_AB"), "hinge_id": "H0_A_M_AB"},
    "C1": {"pair": ("P0", "P2"), "face": ["C", "M_AB", "M_CD"], "axis": ("C", "M_CD"), "hinge_id": "H4_C_M_CD"},
    "C4": {"pair": ("P1", "P3"), "face": ["D", "M_AB", "M_CD"], "axis": ("D", "M_CD"), "hinge_id": "H7_D_M_CD"},
    "C5": {"pair": ("P2", "P3"), "face": ["B", "M_AB", "M_CD"], "axis": ("B", "M_AB"), "hinge_id": "H9_B_M_AB"},
}

CONTACT_BY_HINGE = {contact["hinge_id"]: contact_id for contact_id, contact in CONTACTS.items()}


def sign_of(expr: sp.Expr) -> int:
    value = sp.N(expr, 80)
    if value > 0:
        return 1
    if value < 0:
        return -1
    return 0


def sanitize(value: Any) -> str:
    text = str(value).lower()
    out = []
    for ch in text:
        out.append(ch if ch.isalnum() else "_")
    return "_".join("".join(out).split("_"))


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"expected JSON object: {path}")
    return data


def load_a7c_rows(manifest_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    manifest = read_json(manifest_path)
    if manifest.get("predicate_id") != "B04_SELECTED_HINGE_CONTACT_SIDE":
        raise ValueError("A7c manifest predicate_id mismatch")
    if manifest.get("contact_side_certificate_count") != manifest.get("record_count"):
        raise ValueError("A7c manifest is not fully certified")
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for item in manifest.get("records", []):
        if not item.get("contact_side_certified"):
            raise ValueError(f"A7c row is not certified: {item}")
        hinge_id = item.get("hinge_id")
        if hinge_id not in CONTACT_BY_HINGE:
            raise ValueError(f"A7c hinge is not a selected B04 bridge hinge: {hinge_id}")
        record_path = ROOT / item["object_record"]
        record = read_json(record_path)
        for key in ("tree_id", "hinge_id", "pair", "ray_sign"):
            if record.get(key) != item.get(key):
                raise ValueError(f"A7c manifest/record mismatch for {key}: {item}")
        if not record.get("sign_certificate", {}).get("constant_nonzero_sign_on_open_interval"):
            raise ValueError(f"A7c sign certificate is not constant nonzero: {record_path}")
        row_key = (str(item["tree_id"]), str(hinge_id))
        if row_key in seen:
            raise ValueError(f"duplicate A7c row: {row_key}")
        seen.add(row_key)
        contact_id = CONTACT_BY_HINGE[str(hinge_id)]
        source_pair = list(CONTACTS[contact_id]["pair"])
        if sorted(item["pair"]) != sorted(source_pair):
            raise ValueError(f"A7c pair does not match bridge contact pair: {item}")
        rows.append({
            "tree_id": item["tree_id"],
            "contact_id": contact_id,
            "ray_sign": int(item["ray_sign"]),
            "a7c_manifest_record": item,
            "a7c_object_record": record,
        })
    if manifest.get("record_count") != len(rows):
        raise ValueError("A7c manifest record_count mismatch")
    return manifest, rows


def derive_parent_child(contact_id: str, sigma: int) -> tuple[str, str]:
    contact = CONTACTS[contact_id]
    axis = contact["axis"]
    face = contact["face"]
    face_set = set(face)
    face_third = next(label for label in face if label not in axis)
    left, right = contact["pair"]
    left_apex = next(label for label in PIECES[left] if label not in face_set)
    right_apex = next(label for label in PIECES[right] if label not in face_set)
    left_side = sign_of(sigma * oriented_area(axis, face_third, left_apex))
    right_side = sign_of(sigma * oriented_area(axis, face_third, right_apex))
    if left_side < 0 and right_side > 0:
        return left, right
    if right_side < 0 and left_side > 0:
        return right, left
    raise ValueError(f"cannot derive parent/child side split for {contact_id}, sigma={sigma}")


def point_json(label: str) -> list[str]:
    return [str(sp.factor(coord)) for coord in POINTS[label]]


def oriented_area(axis: tuple[str, str], x_label: str, y_label: str) -> sp.Expr:
    a_label, b_label = axis
    a = POINTS[a_label]
    u = POINTS[b_label] - a
    x = POINTS[x_label] - a
    y = POINTS[y_label] - a
    return sp.factor(u.dot(x.cross(y)))


def perpendicular(axis: tuple[str, str], label: str) -> sp.Matrix:
    a_label, b_label = axis
    a = POINTS[a_label]
    u = POINTS[b_label] - a
    w = POINTS[label] - a
    return sp.simplify(w - u * (w.dot(u) / u.dot(u)))


def sector_cos(axis: tuple[str, str], x_label: str, y_label: str) -> sp.Expr:
    x = perpendicular(axis, x_label)
    y = perpendicular(axis, y_label)
    return sp.factor(x.dot(y) / sp.sqrt(x.dot(x) * y.dot(y)))


def rotate_about_axis_half_angle(axis: tuple[str, str], point: sp.Matrix, sigma: int) -> sp.Matrix:
    a_label, b_label = axis
    a = POINTS[a_label]
    u = POINTS[b_label] - a
    u = u / sp.sqrt(u.dot(u))
    w = point - a
    sin_theta = sigma * SIN_THETA_BASE
    return sp.simplify(a + w * COS_THETA + u.cross(w) * sin_theta + u * (u.dot(w)) * (1 - COS_THETA))


def oriented_area_point(axis: tuple[str, str], x_label: str, y: sp.Matrix) -> sp.Expr:
    a_label, b_label = axis
    a = POINTS[a_label]
    u = POINTS[b_label] - a
    x = POINTS[x_label] - a
    return sp.factor(u.dot(x.cross(y - a)))


def angular_half_turn_certificate() -> dict[str, Any]:
    cos_alpha = sqrt6 / 3
    cos_pi_over_3 = sp.Rational(1, 2)
    certified = bool(sp.simplify(cos_alpha - cos_pi_over_3) > 0)
    return {
        "theta_domain": "0 < theta <= 2*pi/3 (120 degrees)",
        "theta_max": "2*pi/3",
        "sector_cos_alpha": str(cos_alpha),
        "cos_pi_over_3": str(cos_pi_over_3),
        "cos_alpha_minus_cos_pi_over_3": str(sp.factor(cos_alpha - cos_pi_over_3)),
        "monotonicity_fact": "cos is strictly decreasing on [0, pi]",
        "sector_bound": "alpha < pi/3 because cos(alpha)=sqrt(6)/3 > 1/2",
        "half_turn_bound": "theta + alpha <= 2*pi/3 + alpha < pi",
        "theta_plus_sector_lt_pi": certified,
    }


def positive_child_apex_side_certificate(expr: sp.Expr) -> dict[str, Any]:
    num, den = sp.together(expr).as_numer_denom()
    num = sp.factor(num)
    den = sp.factor(den)
    roots = [sp.factor(root) for root in sp.solve(sp.Eq(num, 0), T)]
    positive_roots_outside_domain = all(bool(sp.simplify(root - sqrt3) > 0) for root in roots)
    return {
        "numerator": str(num),
        "denominator": str(den),
        "positive_numerator_roots": [str(root) for root in roots],
        "denominator_positive_on_domain": str(den),
        "positive_root_condition": "all positive numerator roots are > sqrt(3), the audited upper endpoint for t",
        "positive_on_0_t_sqrt3": (
            positive_roots_outside_domain
            and sign_of(expr.subs(T, sp.Rational(1))) > 0
            and sign_of(expr.subs(T, sqrt3)) > 0
        ),
    }


def bridge_record(row: dict[str, Any]) -> dict[str, Any]:
    contact = CONTACTS[row["contact_id"]]
    axis = contact["axis"]
    face = contact["face"]
    face_set = set(face)
    face_third = next(label for label in face if label not in axis)
    sigma = int(row["ray_sign"])
    parent_piece, child_piece = derive_parent_child(row["contact_id"], sigma)
    parent_apex = next(label for label in PIECES[parent_piece] if label not in face_set)
    child_apex = next(label for label in PIECES[child_piece] if label not in face_set)

    parent_raw = oriented_area(axis, face_third, parent_apex)
    child_raw = oriented_area(axis, face_third, child_apex)
    signed_parent = sp.factor(sigma * parent_raw)
    signed_child = sp.factor(sigma * child_raw)
    parent_cos = sector_cos(axis, face_third, parent_apex)
    child_cos = sector_cos(axis, face_third, child_apex)
    rotated_face = rotate_about_axis_half_angle(axis, POINTS[face_third], sigma)
    rotated_child_apex = rotate_about_axis_half_angle(axis, POINTS[child_apex], sigma)
    rotated_face_side = sp.factor(sigma * oriented_area_point(axis, face_third, rotated_face))
    rotated_child_apex_side = sp.factor(sigma * oriented_area_point(axis, face_third, rotated_child_apex))
    child_apex_side_certificate = positive_child_apex_side_certificate(rotated_child_apex_side)
    angular_certificate = angular_half_turn_certificate()

    checks = {
        "ray_sign_matches_child_side": sign_of(signed_child) > 0,
        "parent_is_opposite_side": sign_of(signed_parent) < 0,
        "parent_sector_cos_expected": sp.simplify(parent_cos - sqrt6 / 3) == 0,
        "child_sector_cos_expected": sp.simplify(child_cos - sqrt6 / 3) == 0,
        "sector_angle_lt_60_degrees": bool(sp.simplify(sqrt6 / 3 - sp.Rational(1, 2)) > 0),
        "ray_domain_plus_sector_stays_below_half_turn": angular_certificate["theta_plus_sector_lt_pi"],
        "rotated_face_strictly_on_child_side": sp.simplify(rotated_face_side - T / (2 * (T**2 + 1))) == 0,
        "rotated_child_apex_strictly_on_child_side": child_apex_side_certificate["positive_on_0_t_sqrt3"],
    }
    accepted = all(checks.values())
    return {
        "accepted_bridge_record": accepted,
        "axis": {
            "endpoint_labels": list(axis),
            "endpoint_coordinates": [point_json(axis[0]), point_json(axis[1])],
            "oriented_axis_convention": f"{axis[0]} -> {axis[1]}",
        },
        "case_id": CASE_ID,
        "checks": checks,
        "child_piece": child_piece,
        "claim_level": CLAIM_LEVEL,
        "contact_id": row["contact_id"],
        "face_third_vertex": face_third,
        "hinge_id": contact["hinge_id"],
        "local_wedge_values": {
            "oriented_area_face_to_parent_apex": str(parent_raw),
            "oriented_area_face_to_child_apex": str(child_raw),
            "ray_signed_parent_side": str(signed_parent),
            "ray_signed_child_side": str(signed_child),
            "parent_sector_cos": str(parent_cos),
            "child_sector_cos": str(child_cos),
            "sector_angle_bound": "alpha < 60 degrees because cos(alpha)=sqrt(6)/3 > 1/2",
            "ray_domain_bound": "0 < theta <= 120 degrees; therefore theta + alpha < 180 degrees",
            "angular_half_turn_certificate": angular_certificate,
            "rotated_face_side_under_t_tan_half_theta": str(rotated_face_side),
            "rotated_child_apex_side_under_t_tan_half_theta": str(rotated_child_apex_side),
            "rotated_child_apex_side_certificate": child_apex_side_certificate,
        },
        "manifest_id": MANIFEST_ID,
        "nonclaims": NONCLAIMS,
        "pair": list(contact["pair"]),
        "parent_piece": parent_piece,
        "predicate_id": PREDICATE_ID,
        "proof_conclusion": (
            "With Lemma 03 axis preservation, the selected child piece opens into its own side "
            "of the source contact face.  The original contact plane separates the parent "
            "from the opened child except along the hinge axis, so the selected pair has "
            "boundary hinge contact and no strict interior overlap on 0 < theta <= 120 degrees."
            if accepted else "bridge checks failed"
        ),
        "ray_sign": sigma,
        "source_a7c_manifest_record": row["a7c_manifest_record"],
        "source_a7c_object_record_id": row["a7c_object_record"].get("object_id"),
        "source_contact_face": face,
        "tree_id": row["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a7c-manifest", default=DEFAULT_A7C_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=MANIFEST_PATH.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    a7c_manifest_path = Path(args.a7c_manifest)
    if not a7c_manifest_path.is_absolute():
        a7c_manifest_path = ROOT / a7c_manifest_path
    out_dir = Path(args.out_dir)
    if not out_dir.is_absolute():
        out_dir = ROOT / out_dir
    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path

    a7c_manifest, rows = load_a7c_rows(a7c_manifest_path)
    records = []
    for row in rows:
        record = bridge_record(row)
        record_path = out_dir / "records" / f"{sanitize(row['tree_id'])}_{sanitize(record['hinge_id'])}_a7c_b04_bridge.json"
        write_json(record_path, record)
        records.append({
            "accepted_bridge_record": record["accepted_bridge_record"],
            "contact_id": record["contact_id"],
            "hinge_id": record["hinge_id"],
            "object_record": rel(record_path),
            "pair": record["pair"],
            "ray_sign": record["ray_sign"],
            "source_a7c_record": record["source_a7c_manifest_record"].get("object_record"),
            "tree_id": record["tree_id"],
        })

    accepted_count = sum(1 for item in records if item["accepted_bridge_record"])
    manifest = {
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaims": NONCLAIMS,
        "predicate_id": PREDICATE_ID,
        "record_count": len(records),
        "accepted_bridge_record_count": accepted_count,
        "records": records,
        "source_a7c_manifest": rel(a7c_manifest_path),
        "source_a7c_manifest_id": a7c_manifest.get("manifest_id"),
        "source_a7c_record_count": a7c_manifest.get("record_count"),
        "source_bridge_row_policy": "bridge rows are consumed from A7c manifest records; tree_id, hinge_id, pair, and ray_sign are asserted against each A7c object record",
        "bridge_lemma_summary": {
            "local_model": "normal cross-section wedge about selected hinge axis",
            "exact_side_fact": "ray sign equals child side; parent apex is on the opposite side",
            "exact_angle_fact": "cos(alpha)=sqrt(6)/3 > 1/2, hence alpha < 60 degrees",
            "domain_fact": "0 < theta <= 120 degrees, hence theta + alpha < 180 degrees",
            "geometric_implication": "original contact plane separates parent and opened child except on hinge axis",
        },
        "source_dependencies": [
            "docs/S4_LEMMA_00_DEFINITIONS_AND_NOTATION_LOCK.md",
            "docs/S4_LEMMA_02_CLOSED_ENDPOINT.md",
            "docs/S4_LEMMA_03_KINEMATICS_AND_SIGNS.md",
            "docs/S4_CL5_A7C_SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE.md",
            "docs/S4_CL5_SELECTED_HINGE_CONTACT_ORIENTATION_REVIEW.md",
        ],
    }
    write_json(manifest_path, manifest)
    print(f"A7c/B04 bridge records accepted: {accepted_count}/{len(records)}")
    print(f"manifest: {rel(manifest_path)}")
    return 0 if accepted_count == len(records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
