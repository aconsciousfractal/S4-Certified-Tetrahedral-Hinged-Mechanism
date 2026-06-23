#!/usr/bin/env python
"""
Build A6 one-parameter ray closure package over the A2/A3-A4/A5 B05 records.

A6 is a packaging layer.  It does not create accepted B05 schema reports and it
does not prove operation enclosures.  It verifies that each current B05 symbolic
record has:

  * A3/A4 global gap/axis positivity on the open one-parameter ray domain;
  * A3/A4 near-branch support stability on 0 < t < 1;
  * A5 post-switch support stability and projection gap on 1 < t < 7/4;
  * the A5 branchwise-ready status.

If all records satisfy those checks, A6 emits a symbolic one-parameter closure
certificate for the seven B05 common-edge records only.
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
MANIFEST_ID = "S4-CL5-A6-ONE-PARAMETER-RAY-CLOSURE-PACKAGE-2026-06-22"
CLAIM_LEVEL = "ONE_PARAMETER_RAY_CLOSURE_PACKAGE"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"

DEFAULT_A3_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a3_a4_weierstrass_sturm_certificate_manifest.json"
)
DEFAULT_A5_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a5_support_switch_root_audit_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "a6_one_parameter_ray_closure_package"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a6_one_parameter_ray_closure_package_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_operation_enclosure_claim",
    "no_schema_v1_report_promotion_claim",
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


def index_records(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in manifest.get("records", []):
        if not isinstance(item, dict):
            continue
        out[str(item["original_report_id"])] = item
    return out


def build_record(a3_summary: dict[str, Any], a5_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    report_id = str(a3_summary["original_report_id"])
    a3_path = ROOT / a3_summary["object_record"]
    a5_path = ROOT / a5_summary["object_record"]
    a3 = read_json(a3_path)
    a5 = read_json(a5_path)

    checks = {
        "a3_full_domain_gap_axis_positive": bool(a3["full_domain_gap_axis_positive"]),
        "a3_near_branch_support_positive": bool(a3["near_branch_support_signature_positive"]),
        "a5_branchwise_ready": bool(a5["branchwise_support_gap_axis_certificate_ready"]),
        "a5_post_switch_support_positive": bool(a5["post_switch_branch"]["support_signature_positive"]),
        "a5_post_switch_gap_positive": bool(a5["post_switch_branch"]["projection_gap_positive"]),
        "same_report_id": report_id == str(a5_summary["original_report_id"]),
    }
    closed = all(checks.values())
    status = (
        "a6_symbolic_one_parameter_ray_closed"
        if closed else "a6_symbolic_one_parameter_ray_closure_blocked"
    )
    record = {
        "accepted_real_b05_report": False,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "closure_checks": checks,
        "input_a3_a4_record": rel(a3_path),
        "input_a5_record": rel(a5_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"A6-ONE-PARAMETER-RAY-CLOSURE-{sanitize(report_id)}",
        "object_status": status,
        "one_parameter_symbolic_b05_closed": closed,
        "original_report_id": report_id,
        "piece_pair": a3_summary["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "proof_outline": [
            "A3/A4 proves raw common-edge gap, axis norm square, and normalized gap square positive on the open ray domain.",
            "A3/A4 proves the A2 common-edge support signature on 0<t<1.",
            "A5 splits at t=1 and proves derived post-switch support signatures and projection gaps on 1<t<7/4.",
            "The interval 1<t<7/4 contains the S4 post-switch branch 1<t<=sqrt(3).",
            "Therefore this symbolic B05 common-edge record is closed on the one-parameter ray, modulo the stated nonclaims.",
        ],
        "recommended_next_task": "A7: decide whether to generalize this symbolic closure to three-parameter bounded cells or keep a scoped one-parameter theorem boundary.",
        "support_branch_summary": {
            "near_branch_signature": a5["near_branch"]["support_signature"],
            "near_branch_interval": a5["near_branch"]["branch_interval"],
            "post_switch_signature": a5["post_switch_branch"]["derived_support_signature"],
            "post_switch_interval": a5["post_switch_branch"]["branch_interval"],
            "switch_root": a5["switch_root"],
        },
        "tree_id": a3_summary["tree_id"],
    }
    out_path = out_dir / "records" / f"{sanitize(report_id)}_a6_one_parameter_ray_closure.json"
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "object_record": rel(out_path),
        "object_status": status,
        "one_parameter_symbolic_b05_closed": closed,
        "original_report_id": report_id,
        "piece_pair": a3_summary["piece_pair"],
        "post_switch_signature": record["support_branch_summary"]["post_switch_signature"],
        "tree_id": a3_summary["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--a3-manifest", default=DEFAULT_A3_MANIFEST.as_posix())
    parser.add_argument("--a5-manifest", default=DEFAULT_A5_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    a3_manifest_path = ROOT / args.a3_manifest
    a5_manifest_path = ROOT / args.a5_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    a3_manifest = read_json(a3_manifest_path)
    a5_manifest = read_json(a5_manifest_path)
    a3_records = index_records(a3_manifest)
    a5_records = index_records(a5_manifest)
    missing_a5 = sorted(set(a3_records) - set(a5_records))
    extra_a5 = sorted(set(a5_records) - set(a3_records))
    if missing_a5 or extra_a5:
        raise SystemExit(f"A3/A5 record mismatch missing={missing_a5} extra={extra_a5}")
    emitted = [build_record(a3_records[key], a5_records[key], out_dir) for key in sorted(a3_records)]
    status_counts = Counter(item["object_status"] for item in emitted)
    post_signature_counts = Counter(item["post_switch_signature"] for item in emitted)
    closed_count = sum(1 for item in emitted if item["one_parameter_symbolic_b05_closed"])
    manifest = {
        "a3_a4_manifest": rel(a3_manifest_path),
        "a5_manifest": rel(a5_manifest_path),
        "accepted_real_b05_report_count": 0,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(status_counts.items())),
        "one_parameter_symbolic_closed_count": closed_count,
        "post_switch_support_signature_counts": dict(sorted(post_signature_counts.items())),
        "predicate_id": PREDICATE_ID,
        "record_count": len(emitted),
        "records": emitted,
        "recommended_next_task": "A7: decide whether to attempt three-parameter bounded-cell generalization or formalize a scoped one-parameter theorem boundary.",
    }
    write_json_lf(manifest_path, manifest)
    print(f"A6 records emitted: {len(emitted)}")
    print(f"one-parameter symbolic B05 closed: {closed_count}/{len(emitted)}")
    print(f"accepted real B05 reports: 0")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
