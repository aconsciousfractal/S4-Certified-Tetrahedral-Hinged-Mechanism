#!/usr/bin/env python
"""Build RW1 physical source-lock artifacts for the S4 real-world branch."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
DOC_PATH = ROOT / "docs" / "S4_RW1_PHYSICAL_SOURCE_LOCK.md"
JSON_PATH = RESULT_ROOT / "rw1_physical_source_lock.json"

GEOMETRY_PATH = ROOT / "results" / CASE_ID / "geometry_payload.json"
HINGE_TREE_PATH = ROOT / "results" / CASE_ID / "hinge_tree_report.json"
A85_PATH = (
    ROOT
    / "results"
    / CASE_ID
    / "exact_interval"
    / "papp_review"
    / "a85_package_closure_review.json"
)

FIRST_TREE = "TREE_007"
SECOND_TREE = "TREE_021"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(out)


def find_tree(report: dict[str, Any], tree_id: str) -> dict[str, Any]:
    for tree in report["trees"]:
        if tree["tree_id"] == tree_id:
            return tree
    raise KeyError(tree_id)


def build_lock() -> dict[str, Any]:
    geometry = load_json(GEOMETRY_PATH)
    hinge_tree_report = load_json(HINGE_TREE_PATH)
    a85 = load_json(A85_PATH)
    first_tree = find_tree(hinge_tree_report, FIRST_TREE)
    second_tree = find_tree(hinge_tree_report, SECOND_TREE)
    return {
        "lock_id": "S4-RW1-PHYSICAL-SOURCE-LOCK-2026-06-22",
        "date": DATE,
        "status": "source_lock_created_not_fabrication_ready",
        "case_id": CASE_ID,
        "precondition": {
            "a85_package_closure_review": A85_PATH.as_posix(),
            "a85_reviewer_package_ready": bool(a85.get("reviewer_package_ready")),
            "a85_public_export_ready": bool(a85.get("public_export_ready")),
            "a85_claim_promotion_allowed": bool(a85.get("claim_promotion_allowed")),
            "rw1_only_unblocked": bool(a85.get("physical_branch_unblocked_for_rw1_only")),
        },
        "tree_ids": [FIRST_TREE, SECOND_TREE],
        "first_tree_to_test": FIRST_TREE,
        "second_tree_to_replay": SECOND_TREE,
        "motion_domain": {
            "closed_endpoint": "theta = 0",
            "open_domain": "0 < theta <= 120 degrees",
            "half_angle_coordinate": "t = tan(theta/2)",
            "open_certificate_superset": "0 < t < 2",
            "source": "A7d one-parameter wrapper and A8.5 package closure",
        },
        "piece_geometry_source": {
            "kind": "exact_s4_median_plane_payload",
            "source_path": GEOMETRY_PATH.as_posix(),
            "source_constructor": geometry.get("source_constructor"),
            "ambient_edge_length_model_units": geometry.get("ambient", {}).get("edge_length"),
            "piece_count": geometry.get("checks", {}).get("piece_count"),
            "congruent_edge_spectra": geometry.get("checks", {}).get("congruent_edge_spectra"),
            "physical_scale_mapping": "one model unit maps to scale_mm millimetres",
        },
        "hinge_tree_source": {
            "source_path": HINGE_TREE_PATH.as_posix(),
            "first_tree": first_tree,
            "second_tree": second_tree,
        },
        "physical_model": {
            "hinge_model_family": "external_pin",
            "primary_start_model": "external_pin",
            "deferred_hinge_families": ["attached_knuckle", "flexure", "print_in_place"],
            "body_geometry_policy": "exact piece solids first; hinge hardware external/placeholder until RW2",
            "exterior_policy": "not exterior-preserving at RW1; external bosses or brackets may protrude in later CAD candidates",
        },
        "parameter_lock": {
            "scale_mm": {
                "status": "exploratory_grid_not_universal",
                "unit": "mm per model unit",
                "symbol": "S_mm",
                "grid": [60, 80, 100],
            },
            "material": {
                "status": "candidate_not_validated",
                "first_candidate": "PLA",
                "alternate_candidates": ["PETG", "PA12", "SLA tough resin"],
            },
            "process": {
                "status": "candidate_not_validated",
                "first_candidate": "FDM",
                "alternate_candidates": ["SLA", "SLS"],
            },
            "clearance_policy": {
                "status": "exploratory_grid_not_universal",
                "unit": "mm",
                "symbol": "c_clear_mm",
                "grid": [0.2, 0.3, 0.5, 0.8],
            },
            "hinge_axis_radius_mm": {
                "status": "exploratory_grid_not_universal",
                "unit": "mm",
                "symbol": "r_pin_mm",
                "grid": [1.0, 1.5, 2.0],
            },
            "shell_or_boss_thickness_mm": {
                "status": "exploratory_grid_not_universal",
                "unit": "mm",
                "symbol": "w_boss_mm",
                "grid": [1.2, 1.6, 2.0, 2.4],
            },
        },
        "manufacturing_assumptions": [
            "Process-specific tolerances are unknown until a printer/process is selected.",
            "Clearance grid values are exploratory inputs, not certified safe clearances.",
            "External pins are preferred first to avoid print-in-place hinge coupling.",
            "RW1 does not place hinge bosses, cutbacks, pins, or fasteners.",
            "RW2 must keep exact body solids separate from optional hinge hardware features.",
        ],
        "excluded_claims": [
            "physical hingeability",
            "finite-thickness clearance",
            "CAD validity",
            "printability",
            "fabrication readiness",
            "prototype success",
            "universal tolerance values",
            "public theorem or release promotion",
        ],
        "acceptance": {
            "all_parameters_have_units_or_unknown_markers": True,
            "numeric_values_are_marked_exploratory": True,
            "first_tree_named": FIRST_TREE,
            "second_tree_named": SECOND_TREE,
            "cad_blocked_until_rw2": True,
        },
        "next_task": "RW2 mesh/CAD payload adapter: export exact body solids and named hinge-axis placeholders, without adding hardware geometry until this lock is reviewed.",
    }


def build_doc(lock: dict[str, Any]) -> str:
    p = lock["parameter_lock"]
    parameter_rows = [
        [name, data["status"], data.get("unit", ""), data.get("symbol", ""), data.get("grid", data.get("first_candidate", ""))]
        for name, data in p.items()
    ]
    first = lock["hinge_tree_source"]["first_tree"]
    second = lock["hinge_tree_source"]["second_tree"]
    tree_rows = [
        [
            first["tree_id"],
            ", ".join(first["hinge_ids"]),
            ", ".join("".join(axis) for axis in first["axis_labels"]),
            "first test",
        ],
        [
            second["tree_id"],
            ", ".join(second["hinge_ids"]),
            ", ".join("".join(axis) for axis in second["axis_labels"]),
            "second replay",
        ],
    ]
    return f"""# S4 RW1 Physical Source Lock

Status: source lock created; not fabrication ready.
Date: {DATE}

## Scope

RW1 opens only the physical evidence branch input contract.  It does not create
CAD, does not certify finite-thickness clearance, does not certify printability,
and does not claim a physical prototype.

The precondition is A8.5 package closure:

```text
a85 reviewer package ready: {lock['precondition']['a85_reviewer_package_ready']}
public export ready: {lock['precondition']['a85_public_export_ready']}
claim promotion allowed: {lock['precondition']['a85_claim_promotion_allowed']}
RW1-only physical branch unblocked: {lock['precondition']['rw1_only_unblocked']}
```

## Locked Case

| Field | Value |
| --- | --- |
| case id | `{lock['case_id']}` |
| tree ids | `{', '.join(lock['tree_ids'])}` |
| first tree to test | `{lock['first_tree_to_test']}` |
| second tree to replay | `{lock['second_tree_to_replay']}` |
| closed endpoint | `{lock['motion_domain']['closed_endpoint']}` |
| open domain | `{lock['motion_domain']['open_domain']}` |
| half-angle coordinate | `{lock['motion_domain']['half_angle_coordinate']}` |
| certificate superset | `{lock['motion_domain']['open_certificate_superset']}` |

## Geometry Source

| Field | Value |
| --- | --- |
| geometry kind | `{lock['piece_geometry_source']['kind']}` |
| source path | `{lock['piece_geometry_source']['source_path']}` |
| source constructor | `{lock['piece_geometry_source']['source_constructor']}` |
| model edge length | `{lock['piece_geometry_source']['ambient_edge_length_model_units']}` |
| physical scale mapping | `{lock['piece_geometry_source']['physical_scale_mapping']}` |

## Hinge Trees

{table(['Tree', 'Hinges', 'Axis labels', 'Role'], tree_rows)}

## Physical Model Decision

| Field | Value |
| --- | --- |
| hinge model family | `{lock['physical_model']['hinge_model_family']}` |
| primary start model | `{lock['physical_model']['primary_start_model']}` |
| deferred families | `{', '.join(lock['physical_model']['deferred_hinge_families'])}` |
| body geometry policy | `{lock['physical_model']['body_geometry_policy']}` |
| exterior policy | `{lock['physical_model']['exterior_policy']}` |

## Parameter Lock

{table(['Parameter', 'Status', 'Unit', 'Symbol', 'Value/Grid'], parameter_rows)}

The numeric grids are exploratory inputs.  They are not universal tolerance
claims and are not fabrication recommendations.

## Manufacturing Assumptions

{chr(10).join('- ' + item for item in lock['manufacturing_assumptions'])}

## Excluded Claims

{chr(10).join('- ' + item for item in lock['excluded_claims'])}

## Acceptance

| Check | Value |
| --- | --- |
| all parameters have units or unknown markers | `{lock['acceptance']['all_parameters_have_units_or_unknown_markers']}` |
| numeric values marked exploratory | `{lock['acceptance']['numeric_values_are_marked_exploratory']}` |
| first tree named | `{lock['acceptance']['first_tree_named']}` |
| second tree named | `{lock['acceptance']['second_tree_named']}` |
| CAD blocked until RW2 | `{lock['acceptance']['cad_blocked_until_rw2']}` |

## Next Task

{lock['next_task']}
"""


def main() -> int:
    lock = build_lock()
    RESULT_ROOT.mkdir(parents=True, exist_ok=True)
    JSON_PATH.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    DOC_PATH.write_text(build_doc(lock).rstrip() + "\n", encoding="utf-8", newline="\n")
    print(f"rw1_source_lock_created=True")
    print(f"first_tree={FIRST_TREE}")
    print(f"second_tree={SECOND_TREE}")
    print(f"hinge_model_family={lock['physical_model']['hinge_model_family']}")
    print(f"wrote {DOC_PATH.relative_to(ROOT).as_posix()}")
    print(f"wrote {JSON_PATH.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
