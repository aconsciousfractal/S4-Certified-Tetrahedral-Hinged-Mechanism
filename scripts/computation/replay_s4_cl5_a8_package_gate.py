#!/usr/bin/env python
"""Replay gate for the S4 CL5 A8 paper/reviewer package."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

THIS = Path(__file__).resolve()
if (THIS.parents[1] / "PAPER_WORKSPACE_MANIFEST.json").exists():
    PACKAGE_ROOT = THIS.parents[1]
    SOURCE_ROOT = THIS.parents[3]
else:
    SOURCE_ROOT = THIS.parents[1]
    PACKAGE_ROOT = SOURCE_ROOT / "paper" / "s4_cl5_one_parameter_wrapper"

FULL_REPLAY_COMMANDS = [
    [sys.executable, "scripts/build_s4_cl5_a6_one_parameter_ray_closure_package.py"],
    [sys.executable, "scripts/build_s4_cl5_a7a_shared_face_residual_sturm_certificate.py"],
    [sys.executable, "scripts/build_s4_cl5_a7b_b03_ray_vacuity_certificate.py"],
    [sys.executable, "scripts/build_s4_cl5_a7c_selected_hinge_contact_side_certificate.py"],
    [sys.executable, "scripts/build_s4_cl5_a7d_one_parameter_theorem_wrapper.py"],
    [sys.executable, "scripts/build_s4_cl5_a8_review_ledgers.py"],
    [sys.executable, "scripts/build_s4_cl5_a8_red_team_report.py"],
    [sys.executable, "scripts/build_s4_cl5_a8_review_package_scaffold.py"],
]

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
]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def check(name: str, condition: bool, detail: str = "") -> bool:
    mark = "PASS" if condition else "FAIL"
    suffix = f" - {detail}" if detail else ""
    print(f"[{mark}] {name}{suffix}")
    return condition


def smoke() -> int:
    ok = True
    a7d = load_json(
        SOURCE_ROOT
        / "results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/manifests/a7d_one_parameter_theorem_wrapper_manifest.json"
    )
    red = load_json(
        SOURCE_ROOT
        / "results/historical_s4_median_planes/exact_interval/papp_review/a8_red_team_report.json"
    )
    exp = load_json(
        SOURCE_ROOT
        / "results/historical_s4_median_planes/exact_interval/papp_review/a8_experiment_ledger.json"
    )
    claims = load_json(
        SOURCE_ROOT
        / "results/historical_s4_median_planes/exact_interval/papp_review/a8_claim_ledger.json"
    )
    ok &= check("A7d wrappers closed", a7d.get("wrapper_closed_count") == 2, str(a7d.get("wrapper_closed_count")))
    ok &= check("A7d tree count", a7d.get("tree_count") == 2, str(a7d.get("tree_count")))
    ok &= check(
        "A7d route counts",
        a7d.get("predicate_route_counts")
        == {
            "B04_SELECTED_HINGE_CONTACT_SIDE": 6,
            "B05_COMMON_EDGE_PROJECTION": 4,
            "B06_B07_SHARED_FACE_RESIDUAL": 2,
        },
        str(a7d.get("predicate_route_counts")),
    )
    ok &= check("A8 experiments", len(exp.get("experiments", [])) == 5, str(len(exp.get("experiments", []))))
    ok &= check("A8 claims", len(claims.get("claims", [])) == 7, str(len(claims.get("claims", []))))
    ok &= check("A8 red-team test count", len(red.get("tests", [])) == 15, str(len(red.get("tests", []))))
    ok &= check("A8 red-team no hard failures", red.get("status_counts", {}).get("fail", 0) == 0, str(red.get("status_counts")))
    ok &= check("A8 red-team package scaffold allowed", bool(red.get("package_scaffold_allowed")), str(red.get("package_scaffold_allowed")))
    missing = [rel for rel in REQUIRED_PACKAGE_FILES if not (PACKAGE_ROOT / rel).exists()]
    ok &= check("package required files", not missing, ", ".join(missing))
    if ok:
        print("smoke_status=PASS")
        return 0
    print("smoke_status=FAIL")
    return 1


def full() -> int:
    for command in FULL_REPLAY_COMMANDS:
        print("RUN", " ".join(command))
        completed = subprocess.run(command, cwd=SOURCE_ROOT)
        if completed.returncode != 0:
            print(f"full_replay_failed command={' '.join(command)} exit={completed.returncode}")
            return completed.returncode
    return smoke()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="Regenerate A6/A7a/A7b/A7c/A7d/A8 artifacts before smoke checks.")
    args = parser.parse_args()
    return full() if args.full else smoke()


if __name__ == "__main__":
    raise SystemExit(main())