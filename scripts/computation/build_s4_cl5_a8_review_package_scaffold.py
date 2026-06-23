#!/usr/bin/env python
"""Build the A8.4 paper/reviewer package scaffold."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
PACKAGE_ROOT = ROOT / "paper" / "s4_cl5_one_parameter_wrapper"
TEMPLATE_ROOT = ROOT.parents[3] / "PAPP" / "projects" / "PAPP v4" / "templates" / "paper_package"

A8_JSON_ROOT = ROOT / "results/historical_s4_median_planes/exact_interval/papp_review"
CERTIFIED_MANIFESTS = {
    "a6_b05_one_parameter_ray_closure_manifest.json": ROOT / "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/manifests/b05_a6_one_parameter_ray_closure_package_manifest.json",
    "a7a_shared_face_residual_sturm_manifest.json": ROOT / "results/historical_s4_median_planes/exact_interval/shared_face_residual/manifests/shared_face_a7a_residual_sturm_certificate_manifest.json",
    "a7b_b03_ray_vacuity_manifest.json": ROOT / "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/manifests/b03_a7b_ray_vacuity_certificate_manifest.json",
    "a7c_selected_hinge_contact_side_manifest.json": ROOT / "results/historical_s4_median_planes/exact_interval/b04_selected_hinge_contact_side/manifests/b04_a7c_selected_hinge_contact_side_certificate_manifest.json",
    "a7d_one_parameter_theorem_wrapper_manifest.json": ROOT / "results/historical_s4_median_planes/exact_interval/one_parameter_ray_theorem_wrapper/manifests/a7d_one_parameter_theorem_wrapper_manifest.json",
}
SOURCE_DOCS = {
    "S4_CL5_A6_ONE_PARAMETER_RAY_CLOSURE_PACKAGE.md": ROOT / "docs/S4_CL5_A6_ONE_PARAMETER_RAY_CLOSURE_PACKAGE.md",
    "S4_CL5_A7A_SHARED_FACE_RESIDUAL_STURM_CERTIFICATE.md": ROOT / "docs/S4_CL5_A7A_SHARED_FACE_RESIDUAL_STURM_CERTIFICATE.md",
    "S4_CL5_A7B_B03_RAY_VACUITY_CERTIFICATE.md": ROOT / "docs/S4_CL5_A7B_B03_RAY_VACUITY_CERTIFICATE.md",
    "S4_CL5_A7C_SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE.md": ROOT / "docs/S4_CL5_A7C_SELECTED_HINGE_CONTACT_SIDE_CERTIFICATE.md",
    "S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md": ROOT / "docs/S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md",
}

REQUIRED_FILES = [
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


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")


def copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(lines)


def make_readme() -> str:
    return f"""# S4 CL5 One-Parameter Wrapper Package

Status: internal reviewer scaffold, not public release.
Date: {DATE}

This package records the scoped zero-thickness one-parameter wrapper for the
catalogued S4 median-plane representatives `TREE_007` and `TREE_021`.

## Claim In One Sentence

For `TREE_007` and `TREE_021`, the A7d wrapper covers the closed endpoint
`theta=0` and all open one-parameter ray pair routes for `0<theta<=120` degrees
using the completed A6/A7a/A7b/A7c certificate layers.

## What This Is Not

This is not physical hingeability, not a thickness/tolerance/CAD result, not a
3-parameter bounded-cell closure, not dynamic connectedness between trees, and
not a public theorem release.

## Reviewer Entry

Start with `README_REVIEWER.md`, then read:

1. `docs/PUBLIC_CLAIM_BOUNDARY.md`
2. `docs/SOURCE_LOCK.md`
3. `docs/NORMALIZATION_LOCK.md`
4. `docs/CLAIM_LEDGER.md`
5. `docs/RED_TEAM_REPORT.md`
6. `REPRODUCE.md`

## Current Gate

A8.3 red-team has 15 checks: 9 pass, 5 warning, 1 not-applicable, 0 hard
failures.  Package scaffolding is allowed; publication and claim promotion are
blocked until human release review resolves license/citation and confirms the
package scope.
"""


def make_reviewer() -> str:
    return """# Reviewer Guide

Recommended review path:

1. Confirm the public boundary in `docs/PUBLIC_CLAIM_BOUNDARY.md`.
2. Check source and normalization locks in `docs/SOURCE_LOCK.md` and
   `docs/NORMALIZATION_LOCK.md`.
3. Read `docs/CLAIM_LEDGER.md` and `docs/EXPERIMENT_LEDGER.md`.
4. Inspect copied certified manifests in `certified/`.
5. Run the smoke replay:

```powershell
python scripts/replay_s4_cl5_a8_package_gate.py
```

From the source project root, the full replay is:

```powershell
python scripts/replay_s4_cl5_a8_package_gate.py --full
```

Do not quote the wrapper as physical hingeability or as public theorem release.
The package is an internal reviewer scaffold until the red-team warnings are
confirmed resolved by review.
"""


def make_reproduce() -> str:
    return """# Reproduce

Run from the S4 project root:

```powershell
python scripts/replay_s4_cl5_a8_package_gate.py
```

Expected smoke metrics:

```text
A7d wrappers closed: 2
A7d tree count: 2
A7d route counts: B04=6, B05=4, B06/B07=2
A8 experiments: 5
A8 claims: 7
A8 red-team tests: 15
A8 red-team hard failures: 0
package required files: present
```

Full regeneration gate:

```powershell
python scripts/replay_s4_cl5_a8_package_gate.py --full
```

The full gate regenerates A6, A7a, A7b, A7c, A7d, A8.1/A8.2 ledgers, A8.3
red-team, and this A8.4 package scaffold.  It is still scoped to the
zero-thickness one-parameter wrapper only.
"""


def make_source_lock() -> str:
    rows = [[name, path.as_posix()] for name, path in SOURCE_DOCS.items()]
    rows += [[name, path.as_posix()] for name, path in CERTIFIED_MANIFESTS.items()]
    return """# Source Lock

Locked object: S4 CL5 scoped zero-thickness one-parameter wrapper for
`TREE_007` and `TREE_021`.

Locked source statement:

- `theta=0` is the closed-contact endpoint.
- `0<theta<=120` degrees is the open one-parameter ray scope.
- `t=tan(theta/2)` is the half-angle coordinate.
- The exact sign certificates use the rational open superset `0<t<2`.
- A7d assembles A6/A7a/A7b/A7c route coverage for all 12 unordered pair routes.

Locked source artifacts:

""" + table(["Artifact", "Source path"], rows) + """

Excluded sources and claims:

- no physical hinge hardware, thickness, tolerance, CAD, or sweep-volume source;
- no 3-parameter bounded-cell source;
- no dynamic connectedness source between `TREE_007` and `TREE_021`;
- no accepted schema-v1 operation-enclosure report source.
"""


def make_normalization_lock() -> str:
    return """# Normalization Lock

## Parameters

- Angle variable: `theta`.
- Half-angle variable: `t = tan(theta/2)`.
- Open physical ray scope: `0 < theta <= 120 degrees`.
- Half-angle image: `0 < t <= sqrt(3)`.
- Certified rational open superset used by sign certificates: `0 < t < 2`.
- Closed endpoint: `theta = 0`, handled only as closed-contact endpoint.

## Route Names

- `B04_SELECTED_HINGE_CONTACT_SIDE`: selected-hinge contact-side orientation.
- `B05_COMMON_EDGE_PROJECTION`: common-edge/shared-edge projection layer.
- `B06_B07_SHARED_FACE_RESIDUAL`: shared-face residual formula-sign layer.
- `B03`: ordinary non-contact route; vacuous on this one-parameter ray.

## Forbidden Normalization Drift

- Do not treat selected-hinge B04 contact-side as positive clearance.
- Do not treat `theta=0` as covered by open-ray strict clearance.
- Do not replace `0<t<2` with a physical-domain claim outside the declared
  superset logic.
- Do not merge this wrapper with 3-parameter bounded cells or real-world
  hingeability.
"""


def make_public_boundary() -> str:
    return """# Public Claim Boundary

## Can Say Internally

- A7d is a scoped zero-thickness one-parameter theorem-wrapper candidate for
  `TREE_007` and `TREE_021`.
- The wrapper covers 12/12 unordered pair routes by A6/A7a/A7b/A7c layers.
- The A8 red-team found 0 hard failures and 5 packaging warnings.
- This package is a reviewer scaffold, not public release.

## Must Not Say

- Do not say S4 is physically hingeable.
- Do not say this proves a real mechanical device can be built.
- Do not say thickness, tolerance, CAD, sweep-volume, or hinge hardware has been
  solved.
- Do not say 3-parameter bounded cells are closed.
- Do not say `TREE_007` and `TREE_021` are dynamically connected by an open
  collision-free path.
- Do not say selected-hinge B04 pairs have positive clearance.
- Do not say this is a public theorem package until release review is complete.
"""


def make_proof_obligations() -> str:
    rows = [
        ["A6", "B05 symbolic one-parameter closure", "closed", "7/7 symbolic records"],
        ["A7a", "B06/B07 shared-face residual", "closed", "2/2 formula targets"],
        ["A7b", "B03 ray vacuity", "closed", "0 route-clean B03 obligations"],
        ["A7c", "B04 selected-hinge contact-side", "closed", "6/6 records"],
        ["A7d", "wrapper assembly", "closed in scope", "2/2 trees, 12/12 pair routes"],
        ["A8.3", "red-team", "reviewed", "0 hard failures, 5 warnings"],
        ["Physical branch", "real-world hingeability", "open", "requires thickness/tolerance/CAD/sweep evidence"],
        ["Bounded cells", "3-parameter bounded-cell generalization", "open", "separate branch"],
    ]
    return "# Proof Obligations\n\n" + table(["ID", "Obligation", "Status", "Evidence"], rows) + "\n"


def make_negative_atlas() -> str:
    return """# Negative Results Atlas

| Nonclaim | Reason |
| --- | --- |
| Physical hingeability | No thickness, hinge hardware, tolerance, CAD, or sweep-volume evidence in A7d. |
| 3-parameter bounded-cell closure | A7d is one-parameter only. |
| Dynamic connectedness | Shared closed endpoint is not an open collision-free path. |
| Positive selected-hinge clearance | B04 proves contact-side orientation, not positive clearance. |
| Accepted schema-v1 reports | A7d assembles symbolic/certificate layers, not accepted operation-enclosure reports. |
| Public theorem release | A8.3 permits scaffold only; release remains blocked by review metadata. |
"""


def make_traceability() -> str:
    rows = [
        ["Theorem-wrapper statement", "docs/S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md", "certified/source_docs/S4_CL5_A7D_ONE_PARAMETER_THEOREM_WRAPPER.md"],
        ["Claim ledger", "docs/S4_CL5_A8_CLAIM_LEDGER.md", "docs/CLAIM_LEDGER.md"],
        ["Experiment ledger", "docs/S4_CL5_A8_EXPERIMENT_LEDGER.md", "docs/EXPERIMENT_LEDGER.md"],
        ["Red-team", "docs/S4_CL5_A8_RED_TEAM_REPORT.md", "docs/RED_TEAM_REPORT.md"],
        ["Certified manifests", "results/.../manifests/*.json", "certified/*.json"],
        ["Replay gate", "scripts/replay_s4_cl5_a8_package_gate.py", "scripts/replay_s4_cl5_a8_package_gate.py"],
    ]
    return "# Paper To Engine Traceability\n\n" + table(["Claim surface", "Engine/source artifact", "Package artifact"], rows) + "\n"


def make_citation() -> str:
    return """cff-version: 1.2.0
message: "If you use this repository/package after public release, please cite the companion paper/repository. Public export remains blocked until the package-closure gate passes."
title: "S4 CL5 One-Parameter Mechanical Wrapper Package"
type: software
authors:
  - family-names: "Babanskyy"
    given-names: "Oleksiy"
version: "a8.4-internal-scaffold"
date-released: "2026-06-22"
year: 2026
license: MIT
repository-code: "https://github.com/aconsciousfractal/pending-s4-cl5-one-parameter-wrapper"
preferred-citation:
  type: article
  title: "S4 CL5 One-Parameter Mechanical Wrapper Package"
  authors:
    - family-names: "Babanskyy"
      given-names: "Oleksiy"
  year: 2026
"""


def make_license() -> str:
    return """MIT License

Copyright (c) 2026 Oleksiy Babanskyy

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

Paper text and future PDF artifacts, if added under `paper/`, should follow the
same public-paper convention used in related repositories: Creative Commons
Attribution 4.0 International (CC-BY-4.0), unless superseded by a later release
note.
"""


def make_license_note() -> str:
    return """# License Note

License/citation policy follows the public paper repositories under
`P:\\GitHub_puba`: code and package scripts use MIT; paper text and future PDF
artifacts should use CC-BY-4.0.  Public export is still blocked until the
package-closure review confirms repository URL, version, release date, and final
citation metadata.
"""


def make_manifest() -> dict[str, Any]:
    red = load_json(PACKAGE_ROOT / "results/a8_red_team_report.json")
    rows = []
    for rel in REQUIRED_FILES:
        path = PACKAGE_ROOT / rel
        exists = path.exists() or rel == "PAPER_WORKSPACE_MANIFEST.json"
        rows.append({"path": rel, "exists": exists, "size_bytes": path.stat().st_size if path.exists() else 0})
    return {
        "manifest_id": "S4-CL5-A8-PAPP-PACKAGE-SCAFFOLD-2026-06-22",
        "package": "s4_cl5_one_parameter_wrapper",
        "date": DATE,
        "template_source": TEMPLATE_ROOT.as_posix(),
        "public_export_ready": False,
        "claim_promotion_allowed": False,
        "package_scaffold_ready": all(row["exists"] for row in rows),
        "red_team_status_counts": red.get("status_counts"),
        "red_team_blocked_publication": red.get("blocked_publication"),
        "red_team_package_scaffold_allowed": red.get("package_scaffold_allowed"),
        "required_files": rows,
        "guardrails": [
            "one-parameter zero-thickness wrapper only",
            "not physical hingeability",
            "not 3-parameter bounded-cell closure",
            "not public release",
        ],
        "next_task": "Run package smoke replay and resolve human license/citation review before any publication or physical branch.",
    }


def main() -> int:
    for subdir in ["docs", "certified", "certified/source_docs", "paper", "scripts", "data", "results", "tests"]:
        (PACKAGE_ROOT / subdir).mkdir(parents=True, exist_ok=True)

    write(PACKAGE_ROOT / "README.md", make_readme())
    write(PACKAGE_ROOT / "README_REVIEWER.md", make_reviewer())
    write(PACKAGE_ROOT / "REPRODUCE.md", make_reproduce())
    write(PACKAGE_ROOT / "CITATION.cff", make_citation())
    write(PACKAGE_ROOT / "LICENSE", make_license())
    write(PACKAGE_ROOT / "LICENSE_NOTE.md", make_license_note())
    write(PACKAGE_ROOT / "docs/SOURCE_LOCK.md", make_source_lock())
    write(PACKAGE_ROOT / "docs/NORMALIZATION_LOCK.md", make_normalization_lock())
    write(PACKAGE_ROOT / "docs/PUBLIC_CLAIM_BOUNDARY.md", make_public_boundary())
    write(PACKAGE_ROOT / "docs/PROOF_OBLIGATIONS.md", make_proof_obligations())
    write(PACKAGE_ROOT / "docs/NEGATIVE_RESULTS_ATLAS.md", make_negative_atlas())
    write(PACKAGE_ROOT / "docs/PAPER_TO_ENGINE_TRACEABILITY.md", make_traceability())
    write(PACKAGE_ROOT / "paper/README.md", "# Manuscript Area\n\nNo public manuscript is included in A8.4.  This directory is reserved for a future paper draft.\n")
    write(PACKAGE_ROOT / "data/README.md", "# Data\n\nNo extra data payload is required beyond copied certified manifests and A8 JSON ledgers.\n")
    write(PACKAGE_ROOT / "tests/README.md", "# Tests\n\nUse `python scripts/replay_s4_cl5_a8_package_gate.py` from the source project root for the package smoke gate.\n")

    copy(ROOT / "docs/S4_CL5_A8_CLAIM_LEDGER.md", PACKAGE_ROOT / "docs/CLAIM_LEDGER.md")
    copy(ROOT / "docs/S4_CL5_A8_EXPERIMENT_LEDGER.md", PACKAGE_ROOT / "docs/EXPERIMENT_LEDGER.md")
    copy(ROOT / "docs/S4_CL5_A8_RED_TEAM_REPORT.md", PACKAGE_ROOT / "docs/RED_TEAM_REPORT.md")
    copy(A8_JSON_ROOT / "a8_claim_ledger.json", PACKAGE_ROOT / "results/a8_claim_ledger.json")
    copy(A8_JSON_ROOT / "a8_experiment_ledger.json", PACKAGE_ROOT / "results/a8_experiment_ledger.json")
    copy(A8_JSON_ROOT / "a8_red_team_report.json", PACKAGE_ROOT / "results/a8_red_team_report.json")
    copy(ROOT / "scripts/replay_s4_cl5_a8_package_gate.py", PACKAGE_ROOT / "scripts/replay_s4_cl5_a8_package_gate.py")

    for name, path in CERTIFIED_MANIFESTS.items():
        copy(path, PACKAGE_ROOT / "certified" / name)
    for name, path in SOURCE_DOCS.items():
        if path.exists():
            copy(path, PACKAGE_ROOT / "certified/source_docs" / name)

    manifest = make_manifest()
    write(PACKAGE_ROOT / "PAPER_WORKSPACE_MANIFEST.json", json.dumps(manifest, indent=2, sort_keys=True))
    print(f"package root: {PACKAGE_ROOT.relative_to(ROOT).as_posix()}")
    print(f"required files: {len(REQUIRED_FILES)}")
    print(f"package scaffold ready: {manifest['package_scaffold_ready']}")
    print(f"public export ready: {manifest['public_export_ready']}")
    print(f"claim promotion allowed: {manifest['claim_promotion_allowed']}")
    return 0 if manifest["package_scaffold_ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())