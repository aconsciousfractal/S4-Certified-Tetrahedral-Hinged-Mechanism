#!/usr/bin/env python
"""
Build A7d one-parameter theorem-wrapper records for the S4 ray.

A7d assembles the completed one-parameter predicate layers:

* A6  closes the B05 residual shared-edge/common-edge layer;
* A7a closes the B06/B07 residual shared-face formula-sign layer;
* A7b proves the ray has no route-clean B03 ordinary non-contact obligations;
* A7c closes the B04 selected-hinge contact-side layer.

The wrapper verifies the pair-by-pair coverage for TREE_007 and TREE_021 and
emits scoped theorem-wrapper records.  It does not emit accepted schema-v1
reports, operation enclosures, bounded-cell closure, physical hingeability,
dynamic connectedness, or global S4 hingeability.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A7D-ONE-PARAMETER-THEOREM-WRAPPER-2026-06-22"
CLAIM_LEVEL = "ONE_PARAMETER_RAY_THEOREM_WRAPPER"
PREDICATE_ID = "S4_ONE_PARAMETER_ZERO_THICKNESS_RAY_WRAPPER"

DEFAULT_A6 = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a6_one_parameter_ray_closure_package_manifest.json"
)
DEFAULT_A7A = Path(
    "results/historical_s4_median_planes/exact_interval/shared_face_residual/"
    "manifests/shared_face_a7a_residual_sturm_certificate_manifest.json"
)
DEFAULT_A7B = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_a7b_ray_vacuity_certificate_manifest.json"
)
DEFAULT_A7C = Path(
    "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/"
    "manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/"
    "a7d_one_parameter_theorem_wrapper"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/"
    "manifests/a7d_one_parameter_theorem_wrapper_manifest.json"
)

PAIR_UNIVERSE = {
    ("P0", "P1"),
    ("P0", "P2"),
    ("P0", "P3"),
    ("P1", "P2"),
    ("P1", "P3"),
    ("P2", "P3"),
}

EXPECTED_TREE_LEDGER = {
    "TREE_007": {
        ("P0", "P1"): "B04_SELECTED_HINGE_CONTACT_SIDE",
        ("P0", "P2"): "B04_SELECTED_HINGE_CONTACT_SIDE",
        ("P0", "P3"): "B05_COMMON_EDGE_PROJECTION",
        ("P1", "P2"): "B05_COMMON_EDGE_PROJECTION",
        ("P1", "P3"): "B04_SELECTED_HINGE_CONTACT_SIDE",
        ("P2", "P3"): "B06_B07_SHARED_FACE_RESIDUAL",
    },
    "TREE_021": {
        ("P0", "P1"): "B04_SELECTED_HINGE_CONTACT_SIDE",
        ("P0", "P2"): "B06_B07_SHARED_FACE_RESIDUAL",
        ("P0", "P3"): "B05_COMMON_EDGE_PROJECTION",
        ("P1", "P2"): "B05_COMMON_EDGE_PROJECTION",
        ("P1", "P3"): "B04_SELECTED_HINGE_CONTACT_SIDE",
        ("P2", "P3"): "B04_SELECTED_HINGE_CONTACT_SIDE",
    },
}

NONCLAIMS = [
    "no_accepted_schema_v1_report_claim",
    "no_operation_enclosure_claim",
    "no_three_parameter_bounded_cell_claim",
    "no_physical_hingeability_claim",
    "no_dynamic_connectedness_between_representatives_claim",
    "no_global_s4_hingeability_claim",
    "no_positive_clearance_at_theta_zero_claim",
    "no_positive_clearance_for_selected_hinge_pairs_claim",
    "no_theorem_for_domains_outside_0_lt_theta_le_120_claim",
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


def pair_tuple(value: Any) -> tuple[str, str]:
    if isinstance(value, str):
        left, right = value.split("-")
        return tuple(sorted((left, right)))  # type: ignore[return-value]
    if isinstance(value, list) and len(value) == 2:
        return tuple(sorted((str(value[0]), str(value[1]))))  # type: ignore[return-value]
    if isinstance(value, tuple) and len(value) == 2:
        return tuple(sorted((str(value[0]), str(value[1]))))  # type: ignore[return-value]
    raise ValueError(f"bad pair: {value!r}")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def a6_b05_coverage(a6: dict[str, Any]) -> dict[tuple[str, tuple[str, str]], dict[str, Any]]:
    require(a6.get("one_parameter_symbolic_closed_count") == 7, "A6 does not close 7 symbolic records")
    coverage: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}
    for record in a6.get("records", []):
        require(record.get("one_parameter_symbolic_b05_closed") is True, "A6 record not closed")
        tree_id = record["tree_id"]
        pair = pair_tuple(record["piece_pair"])
        key = (tree_id, pair)
        # Keep the first source record for duplicate diagnostic origins; A7d
        # only needs one closed symbolic proof source per tree/pair.
        coverage.setdefault(key, record)
    return coverage


def a7a_shared_face_coverage(a7a: dict[str, Any]) -> dict[tuple[str, tuple[str, str]], dict[str, Any]]:
    require(a7a.get("positive_on_open_ray_superset_count") == 2, "A7a does not certify 2 shared-face targets")
    coverage: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}
    for record in a7a.get("records", []):
        require(record.get("positive_on_open_ray_superset") is True, "A7a record not positive")
        coverage[(record["tree_id"], pair_tuple(record["pair"]))] = record
    return coverage


def a7b_vacuity(a7b: dict[str, Any]) -> dict[str, Any]:
    require(a7b.get("sturm_obligation_count") == 0, "A7b has nonzero B03 Sturm obligations")
    require(a7b.get("pair_count") == 12, "A7b pair count is not 12")
    expected_routes = {
        "B04_SELECTED_HINGE_CONTACT_SIDE": 6,
        "B05_COMMON_EDGE_PROJECTION": 4,
        "B06_B07_SHARED_FACE_RESIDUAL": 2,
    }
    require(a7b.get("predicate_route_counts") == expected_routes, "A7b route counts changed")
    return {
        "b03_route_clean_pair_count": 0,
        "pair_count": a7b["pair_count"],
        "predicate_route_counts": a7b["predicate_route_counts"],
        "source_manifest_id": a7b.get("manifest_id"),
    }


def a7c_b04_coverage(a7c: dict[str, Any]) -> dict[tuple[str, tuple[str, str]], dict[str, Any]]:
    require(a7c.get("contact_side_certificate_count") == 6, "A7c does not certify 6 selected hinges")
    coverage: dict[tuple[str, tuple[str, str]], dict[str, Any]] = {}
    for record in a7c.get("records", []):
        require(record.get("contact_side_certified") is True, "A7c record not certified")
        coverage[(record["tree_id"], pair_tuple(record["pair"]))] = record
    return coverage


def source_for_pair(
    tree_id: str,
    pair: tuple[str, str],
    route: str,
    b04: dict[tuple[str, tuple[str, str]], dict[str, Any]],
    b05: dict[tuple[str, tuple[str, str]], dict[str, Any]],
    b06: dict[tuple[str, tuple[str, str]], dict[str, Any]],
) -> dict[str, Any]:
    key = (tree_id, pair)
    if route == "B04_SELECTED_HINGE_CONTACT_SIDE":
        source = b04.get(key)
    elif route == "B05_COMMON_EDGE_PROJECTION":
        source = b05.get(key)
    elif route == "B06_B07_SHARED_FACE_RESIDUAL":
        source = b06.get(key)
    else:
        raise ValueError(route)
    require(source is not None, f"missing source for {tree_id} {'-'.join(pair)} {route}")
    return source or {}


def build_tree_record(
    tree_id: str,
    b04: dict[tuple[str, tuple[str, str]], dict[str, Any]],
    b05: dict[tuple[str, tuple[str, str]], dict[str, Any]],
    b06: dict[tuple[str, tuple[str, str]], dict[str, Any]],
    a7b_summary: dict[str, Any],
    out_dir: Path,
) -> dict[str, Any]:
    expected = EXPECTED_TREE_LEDGER[tree_id]
    require(set(expected) == PAIR_UNIVERSE, f"pair universe mismatch for {tree_id}")
    pair_records: list[dict[str, Any]] = []
    for pair in sorted(PAIR_UNIVERSE):
        route = expected[pair]
        source = source_for_pair(tree_id, pair, route, b04, b05, b06)
        pair_records.append(
            {
                "pair": list(pair),
                "predicate_route": route,
                "source_object_record": source.get("object_record"),
                "source_object_status": source.get("object_status"),
                "wrapper_pair_certified": True,
            }
        )

    route_counts = Counter(item["predicate_route"] for item in pair_records)
    closed = len(pair_records) == 6 and all(item["wrapper_pair_certified"] for item in pair_records)
    record = {
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "closed_endpoint_clause": {
            "theta": "0",
            "source": "S4_LEMMA_02_CLOSED_ENDPOINT",
            "semantics": "closed-contact endpoint; no positive-clearance claim",
        },
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"A7D-ONE-PARAMETER-RAY-WRAPPER-{sanitize(tree_id)}",
        "object_status": (
            "a7d_one_parameter_ray_wrapper_closed"
            if closed
            else "a7d_one_parameter_ray_wrapper_blocked"
        ),
        "open_ray_clause": {
            "theta_domain": "0 < theta <= 120 degrees",
            "half_angle_domain": "0 < t <= sqrt(3)",
            "certified_open_superset": "0 < t < 2",
            "tree_id": tree_id,
        },
        "pair_count": len(pair_records),
        "pair_records": pair_records,
        "predicate_id": PREDICATE_ID,
        "predicate_route_counts": dict(sorted(route_counts.items())),
        "source_b03_vacuity": a7b_summary,
        "tree_id": tree_id,
        "wrapper_statement": (
            f"For {tree_id}, every unordered piece pair on the open one-parameter "
            "ray is routed to a completed A6/A7a/A7b/A7c certificate layer; "
            "theta=0 is handled separately as the catalogued closed-contact endpoint."
        ),
        "zero_thickness_one_parameter_wrapper_closed": closed,
    }
    path = out_dir / "records" / f"{sanitize(tree_id)}_a7d_one_parameter_theorem_wrapper.json"
    write_json_lf(path, record)
    return {
        "object_record": rel(path),
        "object_status": record["object_status"],
        "pair_count": len(pair_records),
        "predicate_route_counts": record["predicate_route_counts"],
        "tree_id": tree_id,
        "zero_thickness_one_parameter_wrapper_closed": closed,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a6", default=DEFAULT_A6.as_posix())
    parser.add_argument("--a7a", default=DEFAULT_A7A.as_posix())
    parser.add_argument("--a7b", default=DEFAULT_A7B.as_posix())
    parser.add_argument("--a7c", default=DEFAULT_A7C.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    a6_path = ROOT / args.a6
    a7a_path = ROOT / args.a7a
    a7b_path = ROOT / args.a7b
    a7c_path = ROOT / args.a7c
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    a6 = read_json(a6_path)
    a7a = read_json(a7a_path)
    a7b = read_json(a7b_path)
    a7c = read_json(a7c_path)
    b05 = a6_b05_coverage(a6)
    b06 = a7a_shared_face_coverage(a7a)
    b03_summary = a7b_vacuity(a7b)
    b04 = a7c_b04_coverage(a7c)

    tree_records = [
        build_tree_record(tree_id, b04, b05, b06, b03_summary, out_dir)
        for tree_id in sorted(EXPECTED_TREE_LEDGER)
    ]
    wrapper_closed_count = sum(1 for item in tree_records if item["zero_thickness_one_parameter_wrapper_closed"])
    route_counts: Counter[str] = Counter()
    for item in tree_records:
        route_counts.update(item["predicate_route_counts"])
    manifest = {
        "a6_b05_manifest": rel(a6_path),
        "a7a_shared_face_manifest": rel(a7a_path),
        "a7b_b03_vacuity_manifest": rel(a7b_path),
        "a7c_b04_contact_side_manifest": rel(a7c_path),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(Counter(item["object_status"] for item in tree_records).items())),
        "open_ray_domain": {
            "theta": "0 < theta <= 120 degrees",
            "half_angle": "0 < t <= sqrt(3)",
            "certified_open_superset": "0 < t < 2",
        },
        "predicate_id": PREDICATE_ID,
        "predicate_route_counts": dict(sorted(route_counts.items())),
        "recommended_next_task": "Post-A7d review/red-team of the scoped one-parameter wrapper; keep 3-parameter bounded cells and physical hingeability as later extensions.",
        "record_count": len(tree_records),
        "records": tree_records,
        "scoped_wrapper_statement": (
            "For the catalogued S4 median-plane pieces, TREE_007 and TREE_021 "
            "have a zero-thickness one-parameter ray wrapper on theta=0 plus "
            "0<theta<=120 degrees: theta=0 is the closed-contact endpoint, and "
            "all open-ray unordered piece pairs route to completed A6/A7a/A7b/A7c "
            "certificate layers."
        ),
        "tree_count": len(tree_records),
        "wrapper_closed_count": wrapper_closed_count,
    }
    write_json_lf(manifest_path, manifest)
    print(f"A7d tree wrapper records emitted: {len(tree_records)}")
    print(f"A7d wrappers closed: {wrapper_closed_count}/{len(tree_records)}")
    print(f"predicate route counts: {dict(sorted(route_counts.items()))}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")
    return 0 if wrapper_closed_count == len(tree_records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
