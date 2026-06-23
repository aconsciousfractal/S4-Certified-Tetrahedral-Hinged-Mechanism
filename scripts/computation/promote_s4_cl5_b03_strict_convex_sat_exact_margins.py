#!/usr/bin/env python
"""
Conservative promotion gate for B03 strict-convex SAT diagnostics.

R30 does not invent exact margins.  It inspects the R29 diagnostic B03 report
skeletons and promotes none unless a report already contains replayable exact
or source-locked symbolic margin evidence.  With the current finite float guard
ledgers, every report must remain diagnostic/nonclaim.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
DIAGNOSTIC_REASON = "diagnostic_only_existing_float_guard_not_exact_interval_proof"
BLOCK_REASON = "blocked_no_replayable_exact_or_symbolic_b03_margin_source"
REPLAY_CHECKER = Path("scripts/replay_s4_cl5_exact_interval_report.py")
SCHEMA = Path("schemas/s4_cl5_exact_interval_report_schema_v1.yaml")
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_strict_convex_sat_diagnostic_manifest.json"
)
DEFAULT_OUT = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_strict_convex_sat_exact_margin_promotion_gate_manifest.json"
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


def is_zero_placeholder_interval(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    lo = value.get("lo") or {}
    hi = value.get("hi") or {}
    return (
        lo.get("num") == "0"
        and lo.get("den") == "1"
        and hi.get("num") == "0"
        and hi.get("den") == "1"
        and "diagnostic" in str(value.get("source_expr", ""))
    )


def replay(report_path: Path, checker: Path, schema: Path) -> dict[str, Any]:
    cmd = [
        sys.executable,
        rel(checker),
        "--schema",
        rel(schema),
        "--report",
        rel(report_path),
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
        "report": rel(report_path),
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }


def promotion_decision(report: dict[str, Any]) -> dict[str, Any]:
    reasons: list[str] = []
    data = report.get("predicate_data") or {}
    operations = report.get("operation_enclosures") or []

    if report.get("accepted") is not False:
        reasons.append("source_report_not_currently_diagnostic_false")
    if report.get("failure_reason") != DIAGNOSTIC_REASON:
        reasons.append("source_report_failure_reason_not_r29_diagnostic_reason")
    if data.get("axis_family") == "finite_float_sat_guard_diagnostic":
        reasons.append("axis_family_is_finite_float_diagnostic_not_exact")
    cert = data.get("sat_axis_completeness_certificate") or {}
    if cert.get("status") != "accepted":
        reasons.append("sat_axis_certificate_not_accepted_exact_or_symbolic")
    if is_zero_placeholder_interval(data.get("support_interval_left")):
        reasons.append("left_support_interval_is_diagnostic_zero_placeholder")
    if is_zero_placeholder_interval(data.get("support_interval_right")):
        reasons.append("right_support_interval_is_diagnostic_zero_placeholder")
    if is_zero_placeholder_interval(data.get("separation_margin_interval")):
        reasons.append("separation_margin_interval_is_diagnostic_zero_placeholder")
    if is_zero_placeholder_interval(report.get("margin_interval")):
        reasons.append("top_level_margin_interval_is_diagnostic_zero_placeholder")
    if any("diagnostic_placeholder" in str(op.get("proof_rule", "")) for op in operations if isinstance(op, dict)):
        reasons.append("operation_enclosure_uses_diagnostic_placeholder_proof_rule")
    if not any(
        isinstance(op, dict)
        and op.get("backend_id") in {"fraction_interval_v1", "symbolic_sign_v1"}
        and "diagnostic" not in str(op.get("proof_rule", ""))
        for op in operations
    ):
        reasons.append("no_non_diagnostic_fraction_or_symbolic_operation_enclosure")

    promotable = not reasons and report.get("accepted") is True
    return {
        "blocked_reasons": sorted(set(reasons)) or ["not_promoted_by_conservative_gate"],
        "promotion_status": "promotable_existing_accepted_report" if promotable else BLOCK_REASON,
        "would_set_accepted_true": bool(promotable),
    }


def load_report_paths(manifest: dict[str, Any]) -> list[Path]:
    reports = manifest.get("generated_reports") or []
    out: list[Path] = []
    for item in reports:
        if not isinstance(item, dict) or "path" not in item:
            raise ValueError("manifest generated_reports entry missing path")
        out.append(ROOT / item["path"])
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    parser.add_argument("--out", default=DEFAULT_OUT.as_posix())
    parser.add_argument("--schema", default=SCHEMA.as_posix())
    parser.add_argument("--replay-checker", default=REPLAY_CHECKER.as_posix())
    parser.add_argument(
        "--fail-if-any-promoted",
        action="store_true",
        help="Fail if any report is promotable. Useful while this gate is expected to remain diagnostic-only.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest_path = ROOT / args.manifest
    out_path = ROOT / args.out
    schema = ROOT / args.schema
    checker = ROOT / args.replay_checker

    manifest = read_json(manifest_path)
    report_paths = load_report_paths(manifest)
    decisions = []
    replay_results = []
    for report_path in report_paths:
        report = read_json(report_path)
        decision = promotion_decision(report)
        replay_result = replay(report_path, checker, schema)
        decisions.append(
            {
                "accepted_before": report.get("accepted"),
                "accepted_after": report.get("accepted"),
                "decision": decision,
                "failure_reason_after": report.get("failure_reason"),
                "predicate_id": report.get("predicate_id"),
                "report": rel(report_path),
                "report_id": report.get("report_id"),
            }
        )
        replay_results.append(replay_result)

    promoted = [d for d in decisions if d["decision"]["would_set_accepted_true"]]
    blocked = [d for d in decisions if not d["decision"]["would_set_accepted_true"]]
    replay_counts = Counter(str(r["exit_code"]) for r in replay_results)
    output = {
        "case_id": CASE_ID,
        "diagnostic_manifest": rel(manifest_path),
        "expected_replay_exit_for_unpromoted_reports": 4,
        "gate_id": "S4-CL5-B03-STRICT-CONVEX-SAT-EXACT-MARGIN-PROMOTION-GATE-2026-06-21",
        "input_report_count": len(report_paths),
        "nonclaim": manifest.get("nonclaim", []),
        "promotion_blocked_count": len(blocked),
        "promotion_decisions": decisions,
        "promotion_status": "no_reports_promoted_current_sources_are_diagnostic_only" if not promoted else "promoted_existing_accepted_reports_present",
        "promoted_count": len(promoted),
        "replay_exit_code_counts": dict(sorted(replay_counts.items())),
        "replay_results": replay_results,
        "schema_id": SCHEMA_ID,
    }
    write_json_lf(out_path, output)

    print(f"input reports: {len(report_paths)}")
    print(f"promoted reports: {len(promoted)}")
    print(f"blocked reports: {len(blocked)}")
    print(f"replay exit code counts: {dict(Counter(r['exit_code'] for r in replay_results))}")
    print(f"manifest: {rel(out_path)}")

    unexpected_replay = [r for r in replay_results if r["exit_code"] != 4]
    if unexpected_replay:
        print("unexpected replay exits for unpromoted diagnostics:")
        for result in unexpected_replay:
            print(f"  {result['report']}: {result['exit_code']}")
        return 1
    if args.fail_if_any_promoted and promoted:
        print("unexpected promotable report under diagnostic-only source assumptions")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
