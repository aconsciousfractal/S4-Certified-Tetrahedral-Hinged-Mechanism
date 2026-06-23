#!/usr/bin/env python
"""
Build the B05 common-edge projection exact-gap source-layer inventory.

R34 consumes the R33 diagnostic B05 report manifest.  R33 created seven
schema-v1 B05-shaped reports for residual common-edge candidates, but each
report is intentionally accepted=false and still carries diagnostic zero
placeholders for the common-edge projection/gap evidence.

This script does not promote reports.  It audits whether any generated B05
report has a route-specific exact source suitable for a future accepted
B05-FI/B05-SS report:

* accepted fraction-interval or symbolic-sign backend evidence;
* non-diagnostic branch validity;
* non-diagnostic projection coordinate intervals;
* a strictly positive exact/symbolic gap interval;
* operation enclosures whose proof rule is not a diagnostic placeholder.

The current expected outcome is 0 exact-gap source-ready reports.  That is a
feature: it records the next real blocker instead of letting finite/common-edge
ledgers masquerade as accepted exact B05 gap reports.
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
SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
SOURCE_LAYER_ID = "S4-CL5-B05-COMMON-EDGE-PROJECTION-EXACT-GAP-SOURCE-LAYER-2026-06-22"

DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_common_edge_projection_diagnostic_manifest.json"
)
DEFAULT_OUT = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_common_edge_projection_exact_gap_source_layer_manifest.json"
)


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


def endpoint_fraction(value: Any) -> Fraction | None:
    if not isinstance(value, dict):
        return None
    try:
        return Fraction(int(value["num"]), int(value["den"]))
    except Exception:
        return None


def interval_bounds(value: Any) -> tuple[Fraction | None, Fraction | None]:
    if not isinstance(value, dict):
        return (None, None)
    return (endpoint_fraction(value.get("lo")), endpoint_fraction(value.get("hi")))


def interval_is_strictly_positive(value: Any) -> bool:
    lo, _ = interval_bounds(value)
    return lo is not None and lo > 0


def interval_is_zero_placeholder(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    lo, hi = interval_bounds(value)
    source_expr = str(value.get("source_expr", "")).lower()
    return lo == 0 and hi == 0 and "diagnostic" in source_expr


def interval_is_diagnostic(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    return "diagnostic" in str(value.get("source_expr", "")).lower()


def load_report_paths(manifest: dict[str, Any]) -> list[Path]:
    reports = manifest.get("generated_reports") or []
    out: list[Path] = []
    for item in reports:
        if not isinstance(item, dict) or "path" not in item:
            raise ValueError("manifest generated_reports entry missing path")
        out.append(ROOT / item["path"])
    return out


def operation_enclosures_are_exact(report: dict[str, Any]) -> bool:
    operations = report.get("operation_enclosures") or []
    if not operations:
        return False
    for op in operations:
        if not isinstance(op, dict):
            return False
        proof_rule = str(op.get("proof_rule", "")).lower()
        if "diagnostic" in proof_rule or "placeholder" in proof_rule:
            return False
        if op.get("backend_id") not in {"fraction_interval_v1", "symbolic_sign_v1"}:
            return False
    return True


def classify_report(report_path: Path, report: dict[str, Any]) -> dict[str, Any]:
    pdata = report.get("predicate_data") or {}
    diag = pdata.get("diagnostic_source") or {}
    projection_intervals = pdata.get("projection_coordinate_intervals") or []
    gap_interval = pdata.get("gap_interval")
    margin_interval = report.get("margin_interval")
    branch_validity = pdata.get("branch_validity") or {}

    predicate_ok = report.get("predicate_id") == PREDICATE_ID
    accepted_true = report.get("accepted") is True
    branch_accepted = branch_validity.get("status") == "accepted"
    projection_exact = bool(projection_intervals) and all(
        isinstance(item, dict) and not interval_is_diagnostic(item)
        for item in projection_intervals
    )
    gap_positive = interval_is_strictly_positive(gap_interval) or interval_is_strictly_positive(margin_interval)
    gap_diagnostic = interval_is_zero_placeholder(gap_interval) or interval_is_zero_placeholder(margin_interval)
    operation_exact = operation_enclosures_are_exact(report)
    exact_backend = report.get("rounding_backend") in {"fraction_interval_v1", "symbolic_sign_v1"}

    source_ledgers = report.get("source_ledger") or []
    finite_ledgers = [
        item for item in source_ledgers
        if isinstance(item, str)
        and item.startswith("results/")
        and "/exact_interval/" not in item
    ]

    blockers: list[str] = []
    if not predicate_ok:
        blockers.append("wrong_or_missing_b05_predicate_id")
    if not accepted_true:
        blockers.append("report_accepted_false")
    if not branch_accepted:
        blockers.append("branch_validity_not_accepted")
    if not projection_exact:
        blockers.append("projection_coordinate_intervals_are_diagnostic_or_missing")
    if gap_diagnostic:
        blockers.append("gap_interval_is_diagnostic_zero_placeholder")
    if not gap_positive:
        blockers.append("no_strictly_positive_exact_gap_interval")
    if not operation_exact:
        blockers.append("operation_enclosures_are_diagnostic_placeholders")
    if finite_ledgers:
        blockers.append("source_ledgers_are_finite_common_edge_ledgers_not_b05_exact_gap_sources")
    if not exact_backend:
        blockers.append("rounding_backend_missing_or_not_locked_exact_backend")

    exact_gap_ready = (
        predicate_ok
        and branch_accepted
        and projection_exact
        and gap_positive
        and operation_exact
        and exact_backend
    )
    if exact_gap_ready:
        source_status = "source_ready_b05_exact_gap"
    else:
        source_status = "blocked_missing_b05_exact_gap_source"

    return {
        "accepted_true": accepted_true,
        "blocked_reasons": sorted(set(blockers)),
        "branch_validity_status": branch_validity.get("status"),
        "candidate_exact_gap_ready": exact_gap_ready,
        "diagnostic_failure_reason": report.get("failure_reason"),
        "domain_family": diag.get("domain_family") or Path(report_path).parent.name,
        "exact_source_checks": {
            "branch_accepted": branch_accepted,
            "exact_backend": exact_backend,
            "gap_positive": gap_positive,
            "operation_exact": operation_exact,
            "predicate_ok": predicate_ok,
            "projection_exact": projection_exact,
        },
        "finite_source_ledger_count": len(finite_ledgers),
        "gap_interval_is_diagnostic_zero_placeholder": gap_diagnostic,
        "piece_pair": diag.get("piece_pair"),
        "predicate_id": report.get("predicate_id"),
        "projection_interval_count": len(projection_intervals),
        "report": rel(report_path),
        "report_id": report.get("report_id"),
        "source_status": source_status,
        "tree_id": diag.get("tree_id"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    parser.add_argument("--out", default=DEFAULT_OUT.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = ROOT / args.manifest
    out_path = ROOT / args.out
    manifest = read_json(manifest_path)
    report_paths = load_report_paths(manifest)
    decisions = [classify_report(path, read_json(path)) for path in report_paths]

    exact_ready = [item for item in decisions if item["candidate_exact_gap_ready"]]
    blocker_counts = Counter(reason for item in decisions for reason in item["blocked_reasons"])
    status_counts = Counter(item["source_status"] for item in decisions)
    domain_counts = Counter(item["domain_family"] for item in decisions)
    pair_counts = Counter(item["piece_pair"] for item in decisions)

    output = {
        "accepted_true_count": sum(1 for item in decisions if item["accepted_true"]),
        "backend_lock_id": BACKEND_LOCK_ID,
        "b05_exact_gap_source_ready_count": len(exact_ready),
        "case_id": CASE_ID,
        "diagnostic_manifest": rel(manifest_path),
        "input_report_count": len(decisions),
        "manifest_id": SOURCE_LAYER_ID,
        "nonclaim": [
            "no_b05_accepted_true_report_claim",
            "no_exact_common_edge_gap_claim",
            "no_finite_common_edge_ledger_as_exact_gap_claim",
            "no_theorem_wrapper_promotion_claim",
            "no_physical_hingeability_claim",
        ],
        "predicate_id": PREDICATE_ID,
        "report_count_by_domain_family": dict(sorted(domain_counts.items())),
        "report_count_by_piece_pair": dict(sorted(pair_counts.items())),
        "schema_id": SCHEMA_ID,
        "source_blocker_counts": dict(sorted(blocker_counts.items())),
        "source_decisions": decisions,
        "source_layer_status": (
            "no_current_b05_diagnostic_report_has_exact_gap_source"
            if not exact_ready
            else "some_b05_reports_have_candidate_exact_gap_sources"
        ),
        "source_status_counts": dict(sorted(status_counts.items())),
        "recommended_next_task": (
            "R35: derive or source-lock the B05 common-edge projection exact-gap evidence, "
            "then replace diagnostic projection/gap placeholders with fraction_interval_v1 or symbolic_sign_v1 proof objects."
        ),
    }
    write_json_lf(out_path, output)

    print(f"input reports: {len(decisions)}")
    print(f"B05 exact-gap source-ready reports: {len(exact_ready)}")
    print(f"accepted true reports: {output['accepted_true_count']}")
    print(f"source status counts: {dict(sorted(status_counts.items()))}")
    print(f"source blocker counts: {dict(sorted(blocker_counts.items()))}")
    print(f"manifest: {rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
