#!/usr/bin/env python
"""
Generate diagnostic B03 strict-convex SAT report skeletons.

R29 is intentionally diagnostic-only.  It maps existing finite S4 guard
ledgers into the locked schema-v1 B03 shape and proves only that the reports
are replayable as nonclaims (exit code 4).  It does not promote any finite
float SAT guard to an accepted exact/interval certificate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
POLICY_ID = "S4-CL5-EXACT-INTERVAL-ARITHMETIC-POLICY-2026-06-21"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
PREDICATE_ID = "B03_STRICT_CONVEX_SAT"
FAILURE_REASON = "diagnostic_only_existing_float_guard_not_exact_interval_proof"
REQUIRED_NONCLAIMS = [
    "no_dynamic_connectedness_claim",
    "no_global_s4_hingeability_claim",
    "no_physical_hingeability_claim",
    "no_theorem_wrapper_promotion_claim",
    "no_theta_zero_positive_clearance_claim",
]

RAY_LEDGER = Path("results/historical_s4_median_planes/two_class_ray_cell_guard_report.json")
BOUNDED_LEDGER = Path("results/historical_s4_median_planes/bounded_cell_guard_first_pass_report.json")
PLAN_DOC = Path("docs/S4_CL5_STRICT_CONVEX_SAT_EXACT_REPORT_IMPLEMENTATION_PLAN.md")


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


def endpoint(num: int, den: int = 1) -> dict[str, str]:
    frac = Fraction(num, den)
    return {"num": str(frac.numerator), "den": str(frac.denominator)}


def interval(
    lo_num: int,
    hi_num: int,
    *,
    lo_den: int = 1,
    hi_den: int = 1,
    unit: str = "signed_margin",
    expr: str,
) -> dict[str, Any]:
    lo = Fraction(lo_num, lo_den)
    hi = Fraction(hi_num, hi_den)
    if lo > hi:
        raise ValueError(f"invalid interval {lo} > {hi}")
    return {
        "endpoint_semantics": "closed",
        "lo": endpoint(lo.numerator, lo.denominator),
        "hi": endpoint(hi.numerator, hi.denominator),
        "source_expr": expr,
        "unit": unit,
    }


def sanitize(value: Any) -> str:
    text = str(value)
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def pair_key(pair: list[str]) -> str:
    return "-".join(pair)


def support_zero(expr: str) -> dict[str, Any]:
    return interval(0, 0, unit="support", expr=expr)


def margin_zero(expr: str) -> dict[str, Any]:
    return interval(0, 0, unit="signed_margin", expr=expr)


def theta_interval_for(domain_family: str) -> dict[str, Any]:
    if domain_family == "ray_nonhinge":
        return interval(1, 120, lo_den=2, unit="degree", expr="finite_ray_cell_theta_domain")
    return interval(1, 120, lo_den=2, unit="degree", expr="bounded_firstpass_theta_domain")


def source_ledger_list(source_report: Path) -> list[str]:
    return [
        rel(source_report),
        rel(PLAN_DOC),
        "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        "scripts/replay_s4_cl5_exact_interval_report.py",
    ]


def route_boundary(role: str, fallback_counts: dict[str, int] | None = None) -> dict[str, Any]:
    fallback_counts = fallback_counts or {}
    return {
        "selected_hinge_contact": role == "selected_hinge_contact",
        "residual_common_edge": role == "residual_shared_edge",
        "residual_face_normal": role == "residual_shared_face",
        "residual_edge_branch": bool(fallback_counts),
        "route_note": (
            "Only the clearance-covered subset is represented as a B03-shaped "
            "diagnostic skeleton; residual contact/fallback portions remain "
            "routed to B05/B06/B07 as specified by the B03 plan."
        ),
    }


def base_report(
    *,
    report_id: str,
    report_kind: str,
    generator_command: str,
    source_report: Path,
    parent_key: str,
    domain_key: str,
    predicate_data: dict[str, Any],
    domain_family: str,
) -> dict[str, Any]:
    return {
        "accepted": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "branch_stability": {
            "rule": "diagnostic_source_ledger_route_is_locked_no_exact_axis_branch_claim",
            "status": "accepted",
        },
        "case_id": CASE_ID,
        "claim_level": "exact_interval_report",
        "domain_key": domain_key,
        "error_interval": margin_zero("diagnostic_zero_error_placeholder"),
        "failure_reason": FAILURE_REASON,
        "generator_command": generator_command,
        "input_intervals": {
            "theta_degrees": theta_interval_for(domain_family),
        },
        "ledger_reconstruction": {
            "rule": "aggregate_pair_summary_reconstructed_from_named_source_ledger",
            "source_report": rel(source_report),
            "status": "accepted",
        },
        "margin_interval": margin_zero("diagnostic_zero_margin_placeholder"),
        "nonclaim": REQUIRED_NONCLAIMS,
        "operation_enclosures": [
            {
                "backend_id": "fraction_interval_v1",
                "input_refs": ["source_ledger_float_guard_margin_not_used_as_exact_margin"],
                "op_id": "op_diagnostic_margin_placeholder",
                "operation": "hull",
                "output_interval": margin_zero("diagnostic_zero_margin_placeholder"),
                "proof_rule": "diagnostic_placeholder_no_exact_interval_margin_claim",
            }
        ],
        "parent_key": parent_key,
        "policy_id": POLICY_ID,
        "predicate_data": predicate_data,
        "predicate_id": PREDICATE_ID,
        "replay_interface": {
            "checker": "scripts/replay_s4_cl5_exact_interval_report.py",
            "schema": "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        },
        "report_id": report_id,
        "report_kind": report_kind,
        "rounding_backend": "fraction_interval_v1",
        "schema_id": SCHEMA_ID,
        "source_ledger": source_ledger_list(source_report),
    }


def b03_predicate_data(
    *,
    tree_id: str,
    class_id: str,
    domain_family: str,
    pair_summary: dict[str, Any],
    certified_count: int,
    total_count: int,
) -> dict[str, Any]:
    pair = pair_summary["pair"]
    role = pair_summary["role"]
    fallback_counts = pair_summary.get("fallback_class_counts") or {}
    domain_expr = f"{tree_id}:{domain_family}:{pair_key(pair)}"
    return {
        "axis_family": "finite_float_sat_guard_diagnostic",
        "axis_id": "source_center_axis_or_full_cell_guard_axis",
        "axis_nondegeneracy_interval": interval(
            1,
            1,
            unit="dimensionless",
            expr=f"{domain_expr}:diagnostic_axis_nondegeneracy_placeholder",
        ),
        "cell_or_segment_key": (
            f"{tree_id}|{domain_family}|{pair_key(pair)}|"
            f"clearance_cells_{certified_count}_of_{total_count}"
        ),
        "diagnostic_source": {
            "certified_or_covered_clearance_cells": certified_count,
            "class_id": class_id,
            "minimum_float_guard_margin": pair_summary.get("minimum_guard_margin"),
            "minimum_float_overlap": pair_summary.get("minimum_center_axis_overlap"),
            "role": role,
            "total_cells": total_count,
            "tree_id": tree_id,
        },
        "excluded_selected_hinge_contact": role != "selected_hinge_contact",
        "piece_pair": pair_key(pair),
        "route_boundary": route_boundary(role, fallback_counts),
        "sat_axis_completeness_certificate": {
            "reason": FAILURE_REASON,
            "source_clearance_subset_only": True,
            "status": "diagnostic_only",
        },
        "separation_margin_interval": margin_zero(f"{domain_expr}:diagnostic_separation_margin"),
        "support_interval_left": support_zero(f"{domain_expr}:diagnostic_left_support"),
        "support_interval_right": support_zero(f"{domain_expr}:diagnostic_right_support"),
    }


def ray_entries(ray_report: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for audit in ray_report.get("representative_audits", []):
        tree_id = audit["tree_id"]
        class_id = audit["class_id"]
        for pair_summary in audit.get("pair_summary", []):
            role = pair_summary["role"]
            certified = int(pair_summary.get("certified_cell_count", 0))
            total = int(pair_summary.get("cell_count", 0))
            if role == "selected_hinge_contact" or certified <= 0:
                continue
            entries.append(
                {
                    "class_id": class_id,
                    "domain_family": "ray_nonhinge",
                    "pair_summary": pair_summary,
                    "source_family": "ray_nonhinge",
                    "tree_id": tree_id,
                    "certified_count": certified,
                    "total_count": total,
                }
            )
    return entries


def bounded_entries(bounded_report: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for tree in bounded_report.get("tree_reports", []):
        tree_id = tree["tree_id"]
        class_id = tree["class_id"]
        for pair_summary in tree.get("pair_summary", []):
            role = pair_summary["role"]
            counts = pair_summary.get("coverage_method_counts") or {}
            clearance = int(counts.get("clearance_full_cell_guard", 0))
            total = int(pair_summary.get("cell_count", 0))
            if role == "selected_hinge_contact" or clearance <= 0:
                continue
            entries.append(
                {
                    "class_id": class_id,
                    "domain_family": "bounded_firstpass",
                    "pair_summary": pair_summary,
                    "source_family": "bounded_firstpass",
                    "tree_id": tree_id,
                    "certified_count": clearance,
                    "total_count": total,
                }
            )
    return entries


def report_path(out_dir: Path, family: str, report_id: str) -> Path:
    return out_dir / family / f"{sanitize(report_id)}.json"


def build_reports(
    *,
    out_dir: Path,
    generator_command: str,
    max_per_family: int | None,
) -> list[dict[str, Any]]:
    ray_report = read_json(ROOT / RAY_LEDGER)
    bounded_report = read_json(ROOT / BOUNDED_LEDGER)
    sources = [
        ("ray_nonhinge", ROOT / RAY_LEDGER, ray_entries(ray_report)),
        ("bounded_firstpass", ROOT / BOUNDED_LEDGER, bounded_entries(bounded_report)),
    ]

    generated: list[dict[str, Any]] = []
    for family, source_report, entries in sources:
        if max_per_family is not None:
            entries = entries[:max_per_family]
        for index, entry in enumerate(entries):
            pair = pair_key(entry["pair_summary"]["pair"])
            report_id = (
                f"S4-CL5-B03-{family.upper()}-"
                f"{entry['tree_id']}-{pair}-DIAGNOSTIC-{index:03d}"
            )
            parent_key = f"{entry['tree_id']}|{family}|{pair}|source_ledger_pair_summary"
            domain_key = (
                f"{entry['tree_id']}|{family}|{pair}|"
                f"{entry['certified_count']}_of_{entry['total_count']}"
            )
            predicate_data = b03_predicate_data(
                tree_id=entry["tree_id"],
                class_id=entry["class_id"],
                domain_family=family,
                pair_summary=entry["pair_summary"],
                certified_count=entry["certified_count"],
                total_count=entry["total_count"],
            )
            report = base_report(
                report_id=report_id,
                report_kind="b03_strict_convex_sat_diagnostic_skeleton",
                generator_command=generator_command,
                source_report=source_report,
                parent_key=parent_key,
                domain_key=domain_key,
                predicate_data=predicate_data,
                domain_family=family,
            )
            path = report_path(out_dir, family, report_id)
            write_json_lf(path, report)
            generated.append({"family": family, "path": path, "report": report})
    return generated


def replay_report(checker: Path, schema: Path, report_path_value: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        rel(checker),
        "--schema",
        rel(schema),
        "--report",
        rel(report_path_value),
        "--strict",
    ]
    completed = subprocess.run(
        cmd,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return {
        "command": " ".join(cmd),
        "exit_code": completed.returncode,
        "report": rel(report_path_value),
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }


def write_manifest(
    *,
    out_dir: Path,
    generated: list[dict[str, Any]],
    replay_results: list[dict[str, Any]],
    no_replay: bool,
) -> Path:
    by_family = Counter(item["family"] for item in generated)
    exit_codes = Counter(str(result["exit_code"]) for result in replay_results)
    accepted_true = sum(1 for item in generated if item["report"].get("accepted") is True)
    selected_hinge_skipped = count_selected_hinge_skipped()
    manifest = {
        "accepted_true_count": accepted_true,
        "case_id": CASE_ID,
        "diagnostic_failure_reason": FAILURE_REASON,
        "expected_replay_exit_code": 4,
        "generated_report_count": len(generated),
        "generated_reports": [
            {
                "family": item["family"],
                "path": rel(item["path"]),
                "report_id": item["report"]["report_id"],
            }
            for item in generated
        ],
        "manifest_id": "S4-CL5-B03-STRICT-CONVEX-SAT-DIAGNOSTIC-MANIFEST-2026-06-21",
        "no_replay": no_replay,
        "nonclaim": REQUIRED_NONCLAIMS,
        "replay_exit_code_counts": dict(sorted(exit_codes.items())),
        "replay_results": replay_results,
        "report_count_by_family": dict(sorted(by_family.items())),
        "route_boundary": {
            "bounded_clearance_full_cell_guard_reports_are_diagnostic_only": True,
            "ray_nonhinge_certified_cell_reports_are_diagnostic_only": True,
            "selected_hinge_contact_pairs_skipped_for_B04": selected_hinge_skipped,
            "theorem_wrapper_promotion": False,
        },
        "schema_id": SCHEMA_ID,
        "source_ledgers": [rel(ROOT / RAY_LEDGER), rel(ROOT / BOUNDED_LEDGER)],
    }
    manifest_path = out_dir / "manifests" / "b03_strict_convex_sat_diagnostic_manifest.json"
    write_json_lf(manifest_path, manifest)
    return manifest_path


def count_selected_hinge_skipped() -> dict[str, int]:
    ray = read_json(ROOT / RAY_LEDGER)
    bounded = read_json(ROOT / BOUNDED_LEDGER)
    ray_count = sum(
        1
        for audit in ray.get("representative_audits", [])
        for pair in audit.get("pair_summary", [])
        if pair.get("role") == "selected_hinge_contact"
    )
    bounded_count = sum(
        1
        for tree in bounded.get("tree_reports", [])
        for pair in tree.get("pair_summary", [])
        if pair.get("role") == "selected_hinge_contact"
    )
    return {"bounded_firstpass": bounded_count, "ray_nonhinge": ray_count}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        default="results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat",
        help="Output directory for diagnostic B03 reports and manifest.",
    )
    parser.add_argument(
        "--schema",
        default="schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        help="Schema path passed to the replay checker.",
    )
    parser.add_argument(
        "--replay-checker",
        default="scripts/replay_s4_cl5_exact_interval_report.py",
        help="Replay checker path.",
    )
    parser.add_argument(
        "--max-per-family",
        type=int,
        default=None,
        help="Optional cap for development. Default emits all aggregate diagnostic reports.",
    )
    parser.add_argument("--no-replay", action="store_true", help="Emit reports without replaying them.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = (ROOT / args.out_dir).resolve()
    schema = (ROOT / args.schema).resolve()
    checker = (ROOT / args.replay_checker).resolve()
    generator_command = " ".join([Path(sys.argv[0]).as_posix(), *sys.argv[1:]])
    generated = build_reports(
        out_dir=out_dir,
        generator_command=generator_command,
        max_per_family=args.max_per_family,
    )
    replay_results: list[dict[str, Any]] = []
    if not args.no_replay:
        for item in generated:
            replay_results.append(replay_report(checker, schema, item["path"]))
    manifest_path = write_manifest(
        out_dir=out_dir,
        generated=generated,
        replay_results=replay_results,
        no_replay=args.no_replay,
    )

    unexpected = [
        result for result in replay_results
        if result["exit_code"] != 4
    ]
    accepted_true = [item for item in generated if item["report"].get("accepted") is True]
    print(f"generated reports: {len(generated)}")
    print(f"accepted true reports: {len(accepted_true)}")
    if replay_results:
        print(f"replay exit code counts: {dict(Counter(r['exit_code'] for r in replay_results))}")
    print(f"manifest: {rel(manifest_path)}")
    if unexpected or accepted_true:
        if unexpected:
            print("unexpected replay exits:")
            for result in unexpected:
                print(f"  {result['report']}: {result['exit_code']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
