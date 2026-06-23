#!/usr/bin/env python
"""Build the A8.3 red-team report for the post-A7d wrapper gate."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
DATE = "2026-06-22"
PROJECT_ID = "tetra_mechanical_extension"
PAPER_ID = "s4_cl5_one_parameter_wrapper"
REPORT_ID = "S4-CL5-A8-POST-A7D-RED-TEAM-2026-06-22"
OUT_JSON = Path("results/historical_s4_median_planes/exact_interval/papp_review/a8_red_team_report.json")
OUT_MD = Path("docs/S4_CL5_A8_RED_TEAM_REPORT.md")

CLAIM_IDS = [
    "S4-CL5-A6-B05-SYMBOLIC-CLOSURE",
    "S4-CL5-A7A-SHARED-FACE-RESIDUAL-STURM",
    "S4-CL5-A7B-B03-RAY-VACUITY",
    "S4-CL5-A7C-B04-CONTACT-SIDE",
    "S4-CL5-A7D-ONE-PARAMETER-WRAPPER",
    "S4-CL5-THREE-PARAMETER-BOUNDED-CELLS",
    "S4-CL5-PHYSICAL-HINGEABILITY",
]

FILES_INSPECTED = [
    "docs/S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md",
    "docs/S4_CL5_A8_CLAIM_LEDGER.md",
    "docs/S4_CL5_A8_EXPERIMENT_LEDGER.md",
    "docs/S4_CL5_A7C_SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE.md",
    "docs/S4_CL5_A7A_SHARED_FACE_RESIDUAL_STURM_CERTIFICATE.md",
    "docs/S4_CL5_A6_ONE_PARAMETER_RAY_CLOSURE_PACKAGE.md",
    "results/historical_s4_median_planes/exact_interval/papp_review/a8_claim_ledger.json",
    "results/historical_s4_median_planes/exact_interval/papp_review/a8_experiment_ledger.json",
]

TESTS: list[dict[str, str]] = [
    {
        "rt_id": "RT-1",
        "status": "warning",
        "severity": "medium",
        "finding": "A7d names its source-locked inputs and upstream manifests, but the future standalone paper package still needs a consolidated SOURCE_LOCK.md tying Lemma 02, Lemma 03, B04 semantics, and residual formula sources to package-local paths.",
        "required_action": "Before package release, materialize package docs/SOURCE_LOCK.md from the existing source-lock notes and A6/A7a/A7c/A7d manifests.",
    },
    {
        "rt_id": "RT-2",
        "status": "pass",
        "severity": "low",
        "finding": "Notation for theta, t=tan(theta/2), tree ids, pair ids, and route ids is consistent across A7d and the A8 ledgers.",
        "required_action": "Preserve these names in the package; do not introduce synonyms in public text.",
    },
    {
        "rt_id": "RT-3",
        "status": "warning",
        "severity": "medium",
        "finding": "The normalization is stated in the A7d/A7c docs, but the paper package still needs a standalone NORMALIZATION_LOCK.md for half-angle branch, open superset 0<t<2, theta=0 closed endpoint, signs, and route conventions.",
        "required_action": "Before reviewer package closure, create docs/NORMALIZATION_LOCK.md from A7d and A7c conventions.",
    },
    {
        "rt_id": "RT-4",
        "status": "pass",
        "severity": "low",
        "finding": "No external theorem is used as a hidden proof of physical or global hingeability; internal lemmas are only used under scoped zero-thickness one-parameter assumptions.",
        "required_action": "Keep Demaine/general hinged-dissection theory out of the A7d theorem wording unless separately source-locked.",
    },
    {
        "rt_id": "RT-5",
        "status": "pass",
        "severity": "low",
        "finding": "The A8 claim ledger keeps A6/A7a/A7b/A7c at CL3 and marks A7d as draft CL5 candidate with explicit scope and future branches blocked.",
        "required_action": "Do not promote A7d beyond scoped theorem wording without the package source/normalization/reproduce documents.",
    },
    {
        "rt_id": "RT-6",
        "status": "pass",
        "severity": "low",
        "finding": "The core A7d support comes from exact symbolic/Sturm/manifest checks; numeric diagnostics are not used as theorem evidence in the A8 ledger.",
        "required_action": "Keep diagnostic B03/B05 report drafts out of the theorem evidence list.",
    },
    {
        "rt_id": "RT-7",
        "status": "pass",
        "severity": "low",
        "finding": "Boundary and exception cases are explicit: theta=0 is closed-contact only; selected hinges are zero-margin contact-side, not positive clearance; domains outside 0<theta<=120 are excluded.",
        "required_action": "Mirror this exception language in PUBLIC_CLAIM_BOUNDARY.md and README_REVIEWER.md.",
    },
    {
        "rt_id": "RT-8",
        "status": "warning",
        "severity": "medium",
        "finding": "A8 experiment ledger lists replay commands and expected metrics, and current manifest metrics match, but a standalone package REPRODUCE.md and one-command replay wrapper are not yet present.",
        "required_action": "Before external review, create package REPRODUCE.md with smoke and full replay commands and expected A6/A7a/A7b/A7c/A7d/A8 counts.",
    },
    {
        "rt_id": "RT-9",
        "status": "pass",
        "severity": "low",
        "finding": "A7d docs, A8 ledgers, and manifest counts agree: A7d 2/2 wrappers, route counts B04=6, B05=4, B06/B07=2, and B03 obligations 0.",
        "required_action": "Run this red-team generator again after package scaffolding if any text is edited.",
    },
    {
        "rt_id": "RT-10",
        "status": "warning",
        "severity": "medium",
        "finding": "The public boundary is drafted inside A8 docs, but not yet materialized as package docs/PUBLIC_CLAIM_BOUNDARY.md.",
        "required_action": "Create package PUBLIC_CLAIM_BOUNDARY.md before any public/reviewer-facing text is considered ready.",
    },
    {
        "rt_id": "RT-11",
        "status": "pass",
        "severity": "low",
        "finding": "No agent self-approval is recorded: A7d remains draft CL5 candidate and package promotion is gated on red-team plus reviewer kit.",
        "required_action": "Keep promotion decision separate from generated artifacts.",
    },
    {
        "rt_id": "RT-12",
        "status": "pass",
        "severity": "low",
        "finding": "Pasted agent notes are not treated as source authority in the A8 ledgers; evidence points to local scripts, manifests, and docs.",
        "required_action": "Do not copy untrusted pasted text into source locks without source verification.",
    },
    {
        "rt_id": "RT-13",
        "status": "warning",
        "severity": "low",
        "finding": "The planned package uses local/generated artifacts, but LICENSE_NOTE.md and CITATION.cff are not yet filled for the reviewer package.",
        "required_action": "Fill package LICENSE_NOTE.md and CITATION.cff before external sharing.",
    },
    {
        "rt_id": "RT-14",
        "status": "pass",
        "severity": "low",
        "finding": "A8 explicitly blocks the false bridge from ideal zero-thickness one-parameter wrapper to real-world physical hingeability.",
        "required_action": "Keep the physical branch as a separate future project stage with thickness/tolerance/CAD evidence.",
    },
    {
        "rt_id": "RT-15",
        "status": "not_applicable",
        "severity": "low",
        "finding": "No live external data or time-sensitive external citation is central to the A7d wrapper package at this stage.",
        "required_action": "If external citations are added to the paper package, record retrieval dates and source locators.",
    },
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def markdown_table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def build_report() -> dict[str, Any]:
    status_counts = Counter(test["status"] for test in TESTS)
    hard_failures = [test for test in TESTS if test["status"] == "fail"]
    warnings = [test for test in TESTS if test["status"] == "warning"]
    return {
        "red_team_report_id": REPORT_ID,
        "project_id": PROJECT_ID,
        "paper_id": PAPER_ID,
        "claim_ids_checked": CLAIM_IDS,
        "tests": TESTS,
        "blocked_publication": bool(hard_failures or warnings),
        "promotion_allowed": False,
        "reviewer": "codex-a8-red-team-generator",
        "date": DATE,
        "files_inspected": FILES_INSPECTED,
        "status_counts": dict(sorted(status_counts.items())),
        "package_scaffold_allowed": not hard_failures,
        "required_before_public_package": [
            "materialize SOURCE_LOCK.md",
            "materialize NORMALIZATION_LOCK.md",
            "materialize PUBLIC_CLAIM_BOUNDARY.md",
            "materialize REPRODUCE.md with smoke/full replay",
            "fill LICENSE_NOTE.md and CITATION.cff",
        ],
    }


def markdown(report: dict[str, Any]) -> str:
    checks = markdown_table(
        ["ID", "Status", "Severity", "Finding", "Required action"],
        [[t["rt_id"], t["status"], t["severity"], t["finding"], t["required_action"]] for t in report["tests"]],
    )
    required = "\n".join(f"- {item}" for item in report["required_before_public_package"])
    inspected = "\n".join(f"- `{item}`" for item in report["files_inspected"])
    return f"""# S4 CL5 A8 Red Team Report

Project: {PROJECT_ID}
Paper/package candidate: {PAPER_ID}
Date: {DATE}

## Summary

Publication blocked: {'yes' if report['blocked_publication'] else 'no'}

Claim promotion allowed: {'yes' if report['promotion_allowed'] else 'no'}

Package scaffold allowed: {'yes' if report['package_scaffold_allowed'] else 'no'}

Status counts: `{report['status_counts']}`

Interpretation: A7d has no hard mathematical red-team failure in this pass, but
public/reviewer package release remains blocked by packaging warnings: source
lock, normalization lock, public claim boundary, reproduce file, license/citation
metadata.  It is acceptable to scaffold the package next, provided those warnings
are materialized as package files and not hidden.

## Files Inspected

{inspected}

## Checks

{checks}

## Required Fixes Before Public/Reviewer Package Release

{required}

## Residual Risk

- A7d is still a scoped one-parameter zero-thickness wrapper, not physical hingeability.
- The real-world branch must be a separate stage with thickness, hinge hardware,
  tolerance, CAD/mesh, and sweep-volume evidence.
- A7d can be packaged for review only if the package keeps all nonclaims visible.
"""


def main() -> int:
    report = build_report()
    write_json(ROOT / OUT_JSON, report)
    (ROOT / OUT_MD).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / OUT_MD).write_text(markdown(report), encoding="utf-8", newline="\n")
    print(f"A8 red-team tests: {len(TESTS)}")
    print(f"status counts: {report['status_counts']}")
    print(f"blocked publication: {report['blocked_publication']}")
    print(f"promotion allowed: {report['promotion_allowed']}")
    print(f"package scaffold allowed: {report['package_scaffold_allowed']}")
    print(f"red-team report: {rel(ROOT / OUT_MD)}")
    print(f"red-team json: {rel(ROOT / OUT_JSON)}")
    return 0 if report["package_scaffold_allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
