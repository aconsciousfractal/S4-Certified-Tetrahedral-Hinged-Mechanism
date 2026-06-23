#!/usr/bin/env python
"""
Build A7b B03 one-parameter ray vacuity certificate.

A7b is scoped to the one-parameter theorem spine after A7a.  It must not reuse
the old bounded-cell or diagnostic B03 surface.  On the one-parameter ray for
the two representative trees, every unordered piece pair is already routed to a
non-B03 predicate:

* selected hinge contact -> B04;
* residual shared edge -> B05;
* residual shared face -> B06/B07.

Therefore there are no route-clean ordinary non-contact B03 pairs on the
one-parameter ray, and the B03 Sturm-obligation count is zero.  This is a
vacuity/routing certificate, not an accepted B03 report and not a theorem
wrapper.
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
MANIFEST_ID = "S4-CL5-A7B-B03-RAY-VACUITY-CERTIFICATE-2026-06-22"
CLAIM_LEVEL = "B03_RAY_VACUITY_CERTIFICATE"
PREDICATE_ID = "B03_STRICT_CONVEX_SAT"

DEFAULT_SOURCE = Path("results/historical_s4_median_planes/two_class_ray_cell_guard_report.json")
DEFAULT_OUT = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "a7b_b03_ray_vacuity_certificate"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_a7b_ray_vacuity_certificate_manifest.json"
)

ROLE_TO_ROUTE = {
    "selected_hinge_contact": "B04_SELECTED_HINGE_CONTACT_SIDE",
    "residual_shared_edge": "B05_COMMON_EDGE_PROJECTION",
    "residual_shared_face": "B06_B07_SHARED_FACE_RESIDUAL",
    "ordinary_non_contact": "B03_STRICT_CONVEX_SAT",
}

NONCLAIMS = [
    "no_b03_positive_margin_report_claim",
    "no_b03_accepted_schema_v1_report_claim",
    "no_bounded_cell_b03_claim",
    "no_selected_hinge_clearance_claim",
    "no_residual_contact_clearance_claim",
    "no_operation_enclosure_claim",
    "no_three_parameter_bounded_cell_claim",
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


def pair_key(pair: list[str]) -> str:
    return "-".join(pair)


def classify_pair(tree_id: str, class_id: str, pair_summary: dict[str, Any]) -> dict[str, Any]:
    pair = pair_summary["pair"]
    role = pair_summary["role"]
    route = ROLE_TO_ROUTE.get(role, "UNKNOWN_ROUTE")
    b03_route_clean = route == "B03_STRICT_CONVEX_SAT"
    return {
        "b03_route_clean": b03_route_clean,
        "b03_sturm_obligation": b03_route_clean,
        "cell_count": pair_summary.get("cell_count"),
        "certified_cell_count": pair_summary.get("certified_cell_count"),
        "class_id": class_id,
        "object_status": (
            "a7b_b03_route_clean_obligation"
            if b03_route_clean
            else "a7b_non_b03_pair_routed_out"
        ),
        "pair": pair,
        "pair_key": pair_key(pair),
        "predicate_route": route,
        "role": role,
        "tree_id": tree_id,
    }


def build_records(source: dict[str, Any], out_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for audit in source.get("representative_audits", []):
        tree_id = audit["tree_id"]
        class_id = audit["class_id"]
        items = [
            classify_pair(tree_id, class_id, pair_summary)
            for pair_summary in audit.get("pair_summary", [])
        ]
        role_counts = Counter(item["role"] for item in items)
        route_counts = Counter(item["predicate_route"] for item in items)
        b03_count = sum(1 for item in items if item["b03_route_clean"])
        record = {
            "case_id": CASE_ID,
            "claim_level": CLAIM_LEVEL,
            "class_id": class_id,
            "manifest_id": MANIFEST_ID,
            "nonclaim": NONCLAIMS,
            "object_id": f"A7B-B03-RAY-VACUITY-{sanitize(tree_id)}",
            "object_status": (
                "a7b_b03_ray_layer_vacuous"
                if b03_count == 0
                else "a7b_b03_route_clean_pairs_found"
            ),
            "pair_count": len(items),
            "pair_records": items,
            "predicate_id": PREDICATE_ID,
            "predicate_route_counts": dict(sorted(route_counts.items())),
            "role_counts": dict(sorted(role_counts.items())),
            "sturm_obligation_count": b03_count,
            "tree_id": tree_id,
        }
        path = out_dir / "records" / f"{sanitize(tree_id)}_a7b_b03_ray_vacuity_certificate.json"
        write_json_lf(path, record)
        records.append({
            "b03_route_clean_pair_count": b03_count,
            "object_record": rel(path),
            "object_status": record["object_status"],
            "pair_count": len(items),
            "tree_id": tree_id,
        })
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=DEFAULT_SOURCE.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_path = ROOT / args.source
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    source = read_json(source_path)
    emitted = build_records(source, out_dir)
    total_pairs = sum(item["pair_count"] for item in emitted)
    total_b03 = sum(item["b03_route_clean_pair_count"] for item in emitted)

    # Recompute aggregate role/route counts from emitted records to keep the
    # manifest reviewer-readable without needing to open each object.
    role_counts: Counter[str] = Counter()
    route_counts: Counter[str] = Counter()
    for item in emitted:
        record = read_json(ROOT / item["object_record"])
        role_counts.update(record["role_counts"])
        route_counts.update(record["predicate_route_counts"])

    manifest = {
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(Counter(item["object_status"] for item in emitted).items())),
        "pair_count": total_pairs,
        "predicate_id": PREDICATE_ID,
        "predicate_route_counts": dict(sorted(route_counts.items())),
        "recommended_next_task": ("Post-A7d review/red-team of the scoped one-parameter wrapper; " "keep three-parameter bounded cells and physical hingeability as later extensions."),
        "record_count": len(emitted),
        "records": emitted,
        "role_counts": dict(sorted(role_counts.items())),
        "source_ray_guard_report": rel(source_path),
        "source_summary_metrics": source.get("summary_metrics", {}),
        "sturm_obligation_count": total_b03,
        "vacuity_certificate": {
            "b03_route_clean_pair_count": total_b03,
            "one_parameter_ray_b03_layer_vacuous": total_b03 == 0,
            "reason": "all one-parameter representative ray pairs route to B04, B05, or B06/B07",
        },
    }
    write_json_lf(manifest_path, manifest)
    print(f"A7b tree records emitted: {len(emitted)}")
    print(f"one-parameter pair records: {total_pairs}")
    print(f"B03 route-clean pairs: {total_b03}")
    print(f"B03 Sturm obligations: {total_b03}")
    print(f"role counts: {dict(sorted(role_counts.items()))}")
    print(f"predicate route counts: {dict(sorted(route_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")
    return 0 if total_b03 == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())

