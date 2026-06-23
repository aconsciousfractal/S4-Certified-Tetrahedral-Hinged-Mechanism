#!/usr/bin/env python
"""Build the A8.5 package-closure review for the S4 CL5 reviewer package."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
PACKAGE_ROOT = ROOT / "paper" / "s4_cl5_one_parameter_wrapper"
RESULT_ROOT = ROOT / "results" / "historical_s4_median_planes" / "exact_interval" / "papp_review"
DOC_PATH = ROOT / "docs" / "S4_CL5_A85_PACKAGE_CLOSURE_REVIEW.md"
JSON_PATH = RESULT_ROOT / "a85_package_closure_review.json"

REQUIRED_PACKAGE_FILES = [
    "README.md",
    "README_REVIEWER.md",
    "REPRODUCE.md",
    "CITATION.cff",
    "LICENSE",
    "LICENSE_NOTE.md",
    "PAPER_WORKSPACE_MANIFEST.json",
    "docs/CLAIM_LEDGER.md",
    "docs/EXPERIMENT_LEDGER.md",
    "docs/SOURCE_LOCK.md",
    "docs/NORMALIZATION_LOCK.md",
    "docs/PROOF_OBLIGATIONS.md",
    "docs/NEGATIVE_RESULTS_ATLAS.md",
    "docs/RED_TEAM_REPORT.md",
    "docs/PUBLIC_CLAIM_BOUNDARY.md",
    "docs/PAPER_TO_ENGINE_TRACEABILITY.md",
    "certified/a7d_one_parameter_theorem_wrapper_manifest.json",
    "results/a8_claim_ledger.json",
    "results/a8_experiment_ledger.json",
    "results/a8_red_team_report.json",
    "scripts/replay_s4_cl5_a8_package_gate.py",
]

WARNING_FIX_FILES = {
    "RT-1": "docs/SOURCE_LOCK.md",
    "RT-3": "docs/NORMALIZATION_LOCK.md",
    "RT-8": "REPRODUCE.md",
    "RT-10": "docs/PUBLIC_CLAIM_BOUNDARY.md",
    "RT-13a": "LICENSE_NOTE.md",
    "RT-13b": "CITATION.cff",
}

NONCLAIM_PATTERNS = [
    "not physical hingeability",
    "not a thickness/tolerance/CAD result",
    "not a public theorem release",
    "Do not say S4 is physically hingeable",
    "Do not say this proves a real mechanical device can be built",
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rel_exists(rel: str) -> bool:
    path = PACKAGE_ROOT / rel
    return path.exists() and path.stat().st_size > 0


def read_package_text(rel: str) -> str:
    return (PACKAGE_ROOT / rel).read_text(encoding="utf-8")


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(out)


def build_result() -> dict[str, Any]:
    manifest = load_json(PACKAGE_ROOT / "PAPER_WORKSPACE_MANIFEST.json")
    red = load_json(PACKAGE_ROOT / "results" / "a8_red_team_report.json")
    required_status = [{"path": rel, "present": rel_exists(rel)} for rel in REQUIRED_PACKAGE_FILES]
    warning_fixes = [
        {"red_team_item": item, "path": rel, "materialized": rel_exists(rel)}
        for item, rel in WARNING_FIX_FILES.items()
    ]

    readme = read_package_text("README.md")
    public_boundary = read_package_text("docs/PUBLIC_CLAIM_BOUNDARY.md")
    combined = readme + "\n" + public_boundary
    nonclaim_status = [
        {"pattern": pattern, "present": pattern in combined}
        for pattern in NONCLAIM_PATTERNS
    ]

    package_files_ready = all(item["present"] for item in required_status)
    warning_files_ready = all(item["materialized"] for item in warning_fixes)
    nonclaims_ready = all(item["present"] for item in nonclaim_status)
    no_hard_red_team_failures = red.get("status_counts", {}).get("fail", 0) == 0
    scaffold_ready = bool(manifest.get("package_scaffold_ready"))

    reviewer_package_ready = all(
        [
            package_files_ready,
            warning_files_ready,
            nonclaims_ready,
            no_hard_red_team_failures,
            scaffold_ready,
        ]
    )

    return {
        "review_id": "S4-CL5-A8.5-PACKAGE-CLOSURE-REVIEW-2026-06-22",
        "date": DATE,
        "package": "s4_cl5_one_parameter_wrapper",
        "package_root": PACKAGE_ROOT.as_posix(),
        "package_files_ready": package_files_ready,
        "warning_files_materialized": warning_files_ready,
        "nonclaims_visible": nonclaims_ready,
        "no_hard_red_team_failures": no_hard_red_team_failures,
        "scaffold_ready": scaffold_ready,
        "reviewer_package_ready": reviewer_package_ready,
        "public_export_ready": False,
        "claim_promotion_allowed": False,
        "physical_branch_unblocked_for_rw1_only": reviewer_package_ready,
        "required_package_files": required_status,
        "warning_fix_files": warning_fixes,
        "nonclaim_patterns": nonclaim_status,
        "red_team_status_counts": red.get("status_counts"),
        "guardrails": [
            "A8.5 closes only the internal reviewer package gate.",
            "A8.5 does not promote A7d to public theorem release.",
            "A8.5 does not prove physical hingeability.",
            "The physical branch may start only at RW1 physical source lock.",
            "No CAD, finite-thickness clearance, fabrication, or prototype claim is authorized.",
        ],
        "next_task": "Start RW1 physical source lock with symbolic/material/process fields before any CAD or printability claim.",
    }


def build_markdown(result: dict[str, Any]) -> str:
    file_rows = [
        [item["path"], "yes" if item["present"] else "NO"]
        for item in result["required_package_files"]
    ]
    warning_rows = [
        [item["red_team_item"], item["path"], "yes" if item["materialized"] else "NO"]
        for item in result["warning_fix_files"]
    ]
    nonclaim_rows = [
        [item["pattern"], "yes" if item["present"] else "NO"]
        for item in result["nonclaim_patterns"]
    ]
    return f"""# S4 CL5 A8.5 Package Closure Review

Status: {'reviewer package ready' if result['reviewer_package_ready'] else 'blocked'}
Date: {DATE}

## Scope

This review closes the A8 package-materialization gate for the internal
reviewer package:

`paper/s4_cl5_one_parameter_wrapper`

It does not promote the theorem to public release and does not start a physical
hingeability claim.  It only decides whether the package is coherent enough to
let the project move to RW1, the physical source-lock stage.

## Gate Summary

| Check | Result |
| --- | --- |
| package files ready | `{result['package_files_ready']}` |
| red-team warning files materialized | `{result['warning_files_materialized']}` |
| nonclaims visible | `{result['nonclaims_visible']}` |
| no hard A8 red-team failures | `{result['no_hard_red_team_failures']}` |
| scaffold ready | `{result['scaffold_ready']}` |
| reviewer package ready | `{result['reviewer_package_ready']}` |
| public export ready | `{result['public_export_ready']}` |
| claim promotion allowed | `{result['claim_promotion_allowed']}` |
| physical branch unblocked for RW1 only | `{result['physical_branch_unblocked_for_rw1_only']}` |

## Materialized Warning Fixes

{table(['Red-team item', 'Package file', 'Materialized'], warning_rows)}

## Required Package Files

{table(['Package file', 'Present'], file_rows)}

## Nonclaim Visibility Checks

{table(['Required nonclaim text/pattern', 'Present'], nonclaim_rows)}

## Decision

A8.5 is sufficient to start RW1 if and only if `reviewer_package_ready=True`.
The next permitted task is the physical source lock.  No physical CAD,
finite-thickness clearance, printability, fabrication, or prototype claim is
authorized by this review.

## Next Task

{result['next_task']}
"""


def main() -> int:
    result = build_result()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    DOC_PATH.write_text(build_markdown(result).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"reviewer_package_ready={result['reviewer_package_ready']}")
    print(f"physical_branch_unblocked_for_rw1_only={result['physical_branch_unblocked_for_rw1_only']}")
    print(f"public_export_ready={result['public_export_ready']}")
    print(f"claim_promotion_allowed={result['claim_promotion_allowed']}")
    print(f"wrote {DOC_PATH.relative_to(ROOT).as_posix()}")
    print(f"wrote {JSON_PATH.relative_to(ROOT).as_posix()}")
    return 0 if result["reviewer_package_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
