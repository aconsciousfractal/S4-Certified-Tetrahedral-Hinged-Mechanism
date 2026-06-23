#!/usr/bin/env python
"""
Generate diagnostic B05 common-edge projection report skeletons.

R33 consumes the R32 residual-route source-layer manifest and emits real
schema-v1 B05-shaped diagnostics for the seven residual shared-edge records.
These reports are intentionally nonclaims: they cite the existing common-edge
source ledgers, expose the B05 route fields required by the locked schema, and
replay with exit code 4 until a route-specific exact/symbolic B05 proof layer
exists.
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
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
FAILURE_REASON = "diagnostic_only_existing_common_edge_ledgers_not_exact_b05_report"
REQUIRED_NONCLAIMS = [
    "no_dynamic_connectedness_claim",
    "no_global_s4_hingeability_claim",
    "no_physical_hingeability_claim",
    "no_theorem_wrapper_promotion_claim",
    "no_theta_zero_positive_clearance_claim",
]

DEFAULT_SOURCE_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/residual_routes/"
    "manifests/residual_route_exact_source_layer_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection"
)
DEFAULT_MANIFEST = DEFAULT_OUT_DIR / "manifests/b05_common_edge_projection_diagnostic_manifest.json"
REPLAY_CHECKER = Path("scripts/replay_s4_cl5_exact_interval_report.py")
SCHEMA = Path("schemas/s4_cl5_exact_interval_report_schema_v1.yaml")
PLAN_DOC = Path("docs/S4_CL5_COMMON_EDGE_PROJECTION_EXACT_REPORT_IMPLEMENTATION_PLAN.md")


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
    unit: str,
    expr: str,
) -> dict[str, Any]:
    lo = Fraction(lo_num, lo_den)
    hi = Fraction(hi_num, hi_den)
    if lo > hi:
        raise ValueError(f"invalid interval {lo} > {hi}")
    return {
        "endpoint_semantics": "closed",
        "hi": endpoint(hi.numerator, hi.denominator),
        "lo": endpoint(lo.numerator, lo.denominator),
        "source_expr": expr,
        "unit": unit,
    }


def margin_zero(expr: str) -> dict[str, Any]:
    return interval(0, 0, unit="signed_margin", expr=expr)


def projection_zero(expr: str) -> dict[str, Any]:
    return interval(0, 0, unit="projection", expr=expr)


def theta_interval_for(domain_family: str) -> dict[str, Any]:
    if domain_family == "ray_nonhinge":
        return interval(1, 120, lo_den=2, unit="degree", expr="finite_ray_cell_theta_domain")
    return interval(1, 120, lo_den=2, unit="degree", expr="bounded_firstpass_theta_domain")


def sanitize(value: Any) -> str:
    text = str(value)
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def source_ledger_list(route_record: dict[str, Any], source_manifest: Path) -> list[str]:
    ledgers = [item["path"] for item in route_record.get("source_ledgers", []) if item.get("exists")]
    ledgers.extend(
        [
            rel(source_manifest),
            rel(PLAN_DOC),
            "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
            "scripts/replay_s4_cl5_exact_interval_report.py",
        ]
    )
    # Preserve order while removing duplicates.
    return list(dict.fromkeys(ledgers))


def b05_predicate_data(route_record: dict[str, Any]) -> dict[str, Any]:
    tree_id = route_record["tree_id"]
    pair = route_record["piece_pair"]
    domain_family = route_record["domain_family"]
    domain_expr = f"{tree_id}:{domain_family}:{pair}:B05_common_edge"
    return {
        "branch_validity": {
            "reason": FAILURE_REASON,
            "status": "diagnostic_only",
        },
        "common_edge_id": "M_AB-M_CD",
        "diagnostic_source": {
            "candidate_route": route_record["candidate_route"],
            "domain_family": domain_family,
            "piece_pair": pair,
            "route_status": route_record["route_status"],
            "source_blockers": route_record["source_blockers"],
            "source_report": route_record["source_report"],
            "source_report_id": route_record["source_report_id"],
            "tree_id": tree_id,
        },
        "endpoint_case": "residual_shared_edge_common_edge_contact",
        "gap_interval": margin_zero(f"{domain_expr}:diagnostic_gap_placeholder"),
        "parent_overlay_key": (
            f"{tree_id}|{domain_family}|{pair}|"
            "residual_common_edge_source_layer"
        ),
        "projection_axis_or_coordinate": "edge:M_AB-M_CD x M_AB-M_CD",
        "projection_coordinate_intervals": [
            projection_zero(f"{domain_expr}:diagnostic_common_edge_projection_placeholder")
        ],
        "route_boundary": {
            "positive_clearance_sat": False,
            "residual_common_edge": True,
            "residual_shared_face": False,
            "selected_hinge_contact": False,
        },
    }


def base_report(
    *,
    report_id: str,
    generator_command: str,
    route_record: dict[str, Any],
    source_manifest: Path,
) -> dict[str, Any]:
    tree_id = route_record["tree_id"]
    pair = route_record["piece_pair"]
    domain_family = route_record["domain_family"]
    return {
        "accepted": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "branch_stability": {
            "rule": "diagnostic_b05_source_route_locked_no_exact_common_edge_branch_claim",
            "status": "accepted",
        },
        "case_id": CASE_ID,
        "claim_level": "exact_interval_report",
        "domain_key": f"{tree_id}|{domain_family}|{pair}|b05_common_edge_diagnostic",
        "error_interval": margin_zero("diagnostic_zero_error_placeholder"),
        "failure_reason": FAILURE_REASON,
        "generator_command": generator_command,
        "input_intervals": {
            "theta_degrees": theta_interval_for(domain_family),
        },
        "ledger_reconstruction": {
            "rule": "residual_route_record_reconstructed_from_r32_source_layer_manifest",
            "source_manifest": rel(source_manifest),
            "status": "accepted",
        },
        "margin_interval": margin_zero("diagnostic_zero_margin_placeholder"),
        "nonclaim": REQUIRED_NONCLAIMS,
        "operation_enclosures": [
            {
                "backend_id": "fraction_interval_v1",
                "input_refs": ["source_common_edge_ledger_not_used_as_exact_b05_gap"],
                "op_id": "op_diagnostic_b05_gap_placeholder",
                "operation": "hull",
                "output_interval": margin_zero("diagnostic_zero_margin_placeholder"),
                "proof_rule": "diagnostic_placeholder_no_exact_b05_gap_claim",
            }
        ],
        "parent_key": f"{tree_id}|{domain_family}|{pair}|r32_residual_route_record",
        "policy_id": POLICY_ID,
        "predicate_data": b05_predicate_data(route_record),
        "predicate_id": PREDICATE_ID,
        "replay_interface": {
            "checker": "scripts/replay_s4_cl5_exact_interval_report.py",
            "schema": "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        },
        "report_id": report_id,
        "report_kind": "b05_common_edge_projection_diagnostic_skeleton",
        "rounding_backend": "fraction_interval_v1",
        "schema_id": SCHEMA_ID,
        "source_ledger": source_ledger_list(route_record, source_manifest),
    }


def b05_records(source_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    records = [
        item
        for item in source_manifest.get("residual_route_records", [])
        if item.get("candidate_route") == PREDICATE_ID
    ]
    return sorted(
        records,
        key=lambda item: (item.get("domain_family", ""), item.get("tree_id", ""), item.get("piece_pair", "")),
    )


def report_path(out_dir: Path, route_record: dict[str, Any], report_id: str) -> Path:
    return out_dir / route_record["domain_family"] / f"{sanitize(report_id)}.json"


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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", default=DEFAULT_SOURCE_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    parser.add_argument("--schema", default=SCHEMA.as_posix())
    parser.add_argument("--replay-checker", default=REPLAY_CHECKER.as_posix())
    parser.add_argument("--no-replay", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_manifest_path = ROOT / args.source_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    schema_path = ROOT / args.schema
    checker_path = ROOT / args.replay_checker
    source_manifest = read_json(source_manifest_path)
    records = b05_records(source_manifest)

    generated = []
    for index, record in enumerate(records):
        pair = record["piece_pair"]
        report_id = (
            f"S4-CL5-B05-COMMON_EDGE-{record['domain_family'].upper()}-"
            f"{record['tree_id']}-{pair}-DIAGNOSTIC-{index:03d}"
        )
        report = base_report(
            report_id=report_id,
            generator_command="scripts/generate_s4_cl5_b05_common_edge_projection_reports.py",
            route_record=record,
            source_manifest=source_manifest_path,
        )
        path = report_path(out_dir, record, report_id)
        write_json_lf(path, report)
        generated.append(
            {
                "domain_family": record["domain_family"],
                "path": rel(path),
                "piece_pair": pair,
                "report_id": report_id,
                "tree_id": record["tree_id"],
            }
        )

    replay_results = []
    if not args.no_replay:
        for item in generated:
            replay_results.append(replay_report(checker_path, schema_path, ROOT / item["path"]))

    replay_counts = Counter(str(item["exit_code"]) for item in replay_results)
    manifest = {
        "accepted_true_count": 0,
        "case_id": CASE_ID,
        "diagnostic_failure_reason": FAILURE_REASON,
        "expected_replay_exit_code": 4,
        "generated_report_count": len(generated),
        "generated_reports": generated,
        "input_source_manifest": rel(source_manifest_path),
        "manifest_id": "S4-CL5-B05-COMMON-EDGE-PROJECTION-DIAGNOSTIC-MANIFEST-2026-06-22",
        "no_replay": args.no_replay,
        "nonclaim": REQUIRED_NONCLAIMS,
        "predicate_id": PREDICATE_ID,
        "report_count_by_domain_family": dict(Counter(item["domain_family"] for item in generated)),
        "replay_exit_code_counts": dict(sorted(replay_counts.items())),
        "replay_results": replay_results,
        "route_boundary": {
            "b05_common_edge_reports_are_diagnostic_only": True,
            "b06_b07_shared_face_records_excluded": source_manifest.get("route_counts", {}).get(
                "B06_B07_SHARED_FACE_SPLIT_REQUIRED", 0
            ),
            "theorem_wrapper_promotion": False,
        },
        "schema_id": SCHEMA_ID,
        "source_ledgers_are_not_exact_reports": True,
    }
    write_json_lf(manifest_path, manifest)

    print(f"generated reports: {len(generated)}")
    print(f"accepted true reports: 0")
    print(f"replay exit code counts: {dict(Counter(item['exit_code'] for item in replay_results))}")
    print(f"manifest: {rel(manifest_path)}")

    unexpected = [item for item in replay_results if item["exit_code"] != 4]
    if unexpected:
        print("unexpected replay exits for diagnostic B05 reports:")
        for item in unexpected:
            print(f"  {item['report']}: {item['exit_code']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
