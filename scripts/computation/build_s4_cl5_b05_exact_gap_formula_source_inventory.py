#!/usr/bin/env python
"""
Build the B05 exact-gap formula source inventory.

R36 consumes the R34 B05 source-layer manifest and the R35 derivation
source-lock.  Its job is deliberately narrower than report generation: it
classifies the seven real B05 diagnostic reports by the formula objects now
known from R35, the exact/backend objects still missing, and the synthetic
fixture coverage available before any real B05 report may be promoted.

This script does not promote reports and does not rewrite diagnostics.  The
expected real-report outcome is still 0 accepted S4 B05 reports.
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
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
INVENTORY_ID = "S4-CL5-B05-EXACT-GAP-FORMULA-SOURCE-INVENTORY-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_EXACT_GAP_FORMULA_SOURCE_INVENTORY"

DEFAULT_R34_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_common_edge_projection_exact_gap_source_layer_manifest.json"
)
DEFAULT_DERIVATION = Path("docs/S4_CL5_B05_COMMON_EDGE_EXACT_GAP_DERIVATION.md")
DEFAULT_SYNTHETIC_ACCEPTED_FIXTURE = Path(
    "results/historical_s4_median_planes/exact_interval/fixtures/synthetic/"
    "accepted_B05_COMMON_EDGE_PROJECTION_SOUNDNESS.json"
)
DEFAULT_OUT = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_exact_gap_formula_source_inventory_manifest.json"
)
REPLAY_CHECKER = Path("scripts/replay_s4_cl5_exact_interval_report.py")
SCHEMA = Path("schemas/s4_cl5_exact_interval_report_schema_v1.yaml")

FORMULA_OBJECTS = [
    "residual_shared_edge_universe",
    "common_edge_labels",
    "separator_axis_formula",
    "axis_nondegeneracy_lower_bound",
    "exact_transform_endpoint_coordinates",
    "center_support_labels",
    "one_hinge_rodrigues_component_formula",
    "trig_component_bounds",
    "component_motion_bounds",
    "signed_gap_margin",
    "support_stability_margins",
    "operation_enclosure_trace",
    "adaptive_parent_reconstruction",
]

SOURCE_LOCK_AVAILABLE = {
    "residual_shared_edge_universe",
    "common_edge_labels",
    "separator_axis_formula",
    "one_hinge_rodrigues_component_formula",
    "trig_component_bounds",
    "signed_gap_margin",
    "support_stability_margins",
}

REPORT_PRESENT_BUT_DIAGNOSTIC = {
    "separator_axis_formula",
    "signed_gap_margin",
    "operation_enclosure_trace",
    "adaptive_parent_reconstruction",
}

BACKEND_REQUIRED = {
    "axis_nondegeneracy_lower_bound",
    "exact_transform_endpoint_coordinates",
    "center_support_labels",
    "trig_component_bounds",
    "component_motion_bounds",
    "signed_gap_margin",
    "support_stability_margins",
    "operation_enclosure_trace",
    "adaptive_parent_reconstruction",
}

TRIG_BACKEND_BLOCKERS = [
    "sin_h_interval_not_emitted_by_accepted_r21_backend",
    "one_minus_cos_h_interval_not_emitted_by_accepted_r21_backend",
    "general_trig_interval_v1_is_blocked_by_schema_lock",
    "no_named_symbolic_trig_sign_rule_for_current_b05_domains",
]

SCHEMA_REPORT_SHAPE_BLOCKERS = [
    "projection_axis_or_coordinate_is_string_not_structured_axis_object",
    "axis_norm_lower_bound_field_not_populated",
    "support_state_fields_not_populated",
    "component_motion_bound_fields_not_populated",
    "support_stability_margin_fields_not_populated",
    "operation_enclosures_use_diagnostic_placeholder_rule",
    "branch_validity_status_is_diagnostic_only",
]

REAL_REPORT_NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_common_edge_gap_claim",
    "no_finite_common_edge_ledger_as_exact_gap_claim",
    "no_theorem_wrapper_promotion_claim",
    "no_physical_hingeability_claim",
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
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def file_has_text(path: Path, required: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(item in text for item in required)


def source_decisions(r34_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    decisions = r34_manifest.get("source_decisions") or []
    if not isinstance(decisions, list):
        raise TypeError("R34 manifest source_decisions must be a list")
    return [item for item in decisions if isinstance(item, dict)]


def replay_fixture(path: Path, checker: Path, schema: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "expected_exit_code": 0,
            "path": rel(path),
            "replay_exit_code": None,
            "replay_status": "missing",
        }
    cmd = [
        sys.executable,
        rel(checker),
        "--schema",
        rel(schema),
        "--report",
        rel(path),
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
        "exists": True,
        "expected_exit_code": 0,
        "path": rel(path),
        "replay_exit_code": completed.returncode,
        "replay_status": "replay_passed" if completed.returncode == 0 else "replay_failed",
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }


def formula_object_inventory(decision: dict[str, Any]) -> dict[str, dict[str, Any]]:
    inventory: dict[str, dict[str, Any]] = {}
    for name in FORMULA_OBJECTS:
        source_locked = name in SOURCE_LOCK_AVAILABLE
        report_diagnostic = name in REPORT_PRESENT_BUT_DIAGNOSTIC
        backend_required = name in BACKEND_REQUIRED
        if name in {"residual_shared_edge_universe", "common_edge_labels"}:
            status = "available_from_source_ledger_and_r35"
        elif source_locked and not report_diagnostic and not backend_required:
            status = "available_from_r35_source_lock"
        elif source_locked and report_diagnostic:
            status = "formula_locked_but_report_field_is_diagnostic"
        elif source_locked and backend_required:
            status = "formula_locked_but_backend_object_missing"
        elif backend_required:
            status = "backend_object_missing"
        else:
            status = "unknown"
        inventory[name] = {
            "backend_required": backend_required,
            "report_diagnostic_or_placeholder": report_diagnostic,
            "source_locked_by_r35": source_locked,
            "status": status,
        }

    checks = decision.get("exact_source_checks") or {}
    if checks.get("exact_backend") is True:
        inventory["operation_enclosure_trace"]["rounding_backend_field"] = "fraction_interval_v1"
    if decision.get("finite_source_ledger_count", 0):
        inventory["residual_shared_edge_universe"]["finite_source_ledger_count"] = decision[
            "finite_source_ledger_count"
        ]
    inventory["signed_gap_margin"]["gap_interval_is_diagnostic_zero_placeholder"] = bool(
        decision.get("gap_interval_is_diagnostic_zero_placeholder")
    )
    inventory["adaptive_parent_reconstruction"]["parent_overlay_key_present_in_report"] = True
    return inventory


def classify_formula_report(decision: dict[str, Any]) -> dict[str, Any]:
    object_inventory = formula_object_inventory(decision)
    missing_backend = sorted(
        name
        for name, data in object_inventory.items()
        if data["status"] in {
            "backend_object_missing",
            "formula_locked_but_backend_object_missing",
            "formula_locked_but_report_field_is_diagnostic",
        }
    )
    formula_source_locked_count = sum(
        1 for data in object_inventory.values() if data["source_locked_by_r35"]
    )
    report_shape_ready = not any(
        reason in set(decision.get("blocked_reasons") or [])
        for reason in {
            "branch_validity_not_accepted",
            "gap_interval_is_diagnostic_zero_placeholder",
            "operation_enclosures_are_diagnostic_placeholders",
            "projection_coordinate_intervals_are_diagnostic_or_missing",
        }
    )
    can_promote_real_report = (
        decision.get("candidate_exact_gap_ready") is True
        and report_shape_ready
        and not missing_backend
    )
    return {
        "accepted_true": bool(decision.get("accepted_true")),
        "blocked_reasons_from_r34": decision.get("blocked_reasons") or [],
        "can_promote_real_b05_report": can_promote_real_report,
        "domain_family": decision.get("domain_family"),
        "formula_object_inventory": object_inventory,
        "formula_source_locked_count": formula_source_locked_count,
        "missing_backend_or_exact_objects": missing_backend,
        "piece_pair": decision.get("piece_pair"),
        "recommended_engine_step": "emit_exact_formula_objects_not_real_report_promotion",
        "report": decision.get("report"),
        "report_id": decision.get("report_id"),
        "report_shape_ready": report_shape_ready,
        "source_status": "formula_source_locked_backend_blocked",
        "tree_id": decision.get("tree_id"),
    }


def fixture_inventory(fixture_replay: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": "existing_minimal_accepted_b05_fixture",
            "claim_boundary": "synthetic_only_not_real_s4_b05_report",
            "expected_replay_exit_code": 0,
            "fixture_path": fixture_replay["path"],
            "readiness": (
                "ready_and_replay_passed"
                if fixture_replay.get("replay_exit_code") == 0
                else "blocked_or_missing"
            ),
            "replay_exit_code": fixture_replay.get("replay_exit_code"),
        },
        {
            "candidate_id": "formula_shape_accepted_b05_fixture",
            "claim_boundary": "synthetic_only_should_exercise_axis_support_component_gap_fields",
            "readiness": "recommended_next_fixture_not_emitted_by_r36",
            "required_formula_objects": [
                "axis_norm_lower_bound",
                "support_state_fields",
                "component_motion_bounds",
                "M_gap",
                "M_L",
                "M_U",
            ],
        },
        {
            "candidate_id": "zero_gap_rejected_b05_fixture",
            "claim_boundary": "synthetic_rejection_for_gap_interval_lo_not_gt_error_hi",
            "readiness": "recommended_next_fixture_not_emitted_by_r36",
            "expected_replay_exit_code": 1,
        },
        {
            "candidate_id": "blocked_trig_backend_b05_fixture",
            "claim_boundary": "synthetic_rejection_for_general_trig_interval_v1_or_float_backend",
            "readiness": "recommended_next_fixture_not_emitted_by_r36",
            "expected_replay_exit_code": 3,
        },
        {
            "candidate_id": "diagnostic_placeholder_b05_fixture",
            "claim_boundary": "real_r33_diagnostics_already_cover_exit_code_4",
            "readiness": "covered_by_existing_real_diagnostic_reports",
            "expected_replay_exit_code": 4,
        },
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r34-manifest", default=DEFAULT_R34_MANIFEST.as_posix())
    parser.add_argument("--derivation", default=DEFAULT_DERIVATION.as_posix())
    parser.add_argument("--synthetic-fixture", default=DEFAULT_SYNTHETIC_ACCEPTED_FIXTURE.as_posix())
    parser.add_argument("--schema", default=SCHEMA.as_posix())
    parser.add_argument("--replay-checker", default=REPLAY_CHECKER.as_posix())
    parser.add_argument("--out", default=DEFAULT_OUT.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r34_path = ROOT / args.r34_manifest
    derivation_path = ROOT / args.derivation
    fixture_path = ROOT / args.synthetic_fixture
    schema_path = ROOT / args.schema
    checker_path = ROOT / args.replay_checker
    out_path = ROOT / args.out

    r34_manifest = read_json(r34_path)
    derivation_source_locked = file_has_text(
        derivation_path,
        [
            "u dot (R_epsilon(v) - v)",
            "M_gap = g0 - Delta_pos(L,S_L) - Delta_neg(U,S_U) - tau",
            "M_L = c_L - Delta_neg(L,S_L) - Delta_pos(L,N_L) - tau",
            "M_U = c_U - Delta_pos(U,S_U) - Delta_neg(U,N_U) - tau",
        ],
    )
    decisions = source_decisions(r34_manifest)
    report_inventory = [classify_formula_report(decision) for decision in decisions]
    fixture_replay = replay_fixture(fixture_path, checker_path, schema_path)

    missing_counts = Counter(
        item for report in report_inventory for item in report["missing_backend_or_exact_objects"]
    )
    formula_status_counts = Counter(
        data["status"]
        for report in report_inventory
        for data in report["formula_object_inventory"].values()
    )
    domain_counts = Counter(report["domain_family"] for report in report_inventory)

    real_promotable = [report for report in report_inventory if report["can_promote_real_b05_report"]]
    output = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "derivation_source_lock": {
            "formula_terms_found": derivation_source_locked,
            "path": rel(derivation_path),
            "source_lock_status": "present" if derivation_source_locked else "missing_or_incomplete",
        },
        "formula_object_status_counts": dict(sorted(formula_status_counts.items())),
        "input_report_count": len(report_inventory),
        "manifest_id": INVENTORY_ID,
        "missing_backend_or_exact_object_counts": dict(sorted(missing_counts.items())),
        "nonclaim": REAL_REPORT_NONCLAIMS,
        "predicate_id": PREDICATE_ID,
        "real_report_promotable_count": len(real_promotable),
        "report_count_by_domain_family": dict(sorted(domain_counts.items())),
        "report_formula_inventory": report_inventory,
        "r34_source_layer_manifest": rel(r34_path),
        "schema_id": SCHEMA_ID,
        "schema_report_shape_blockers": SCHEMA_REPORT_SHAPE_BLOCKERS,
        "synthetic_fixture_inventory": fixture_inventory(fixture_replay),
        "synthetic_fixture_replay": fixture_replay,
        "trig_backend_blockers": TRIG_BACKEND_BLOCKERS,
        "inventory_status": (
            "formula_source_locked_real_reports_backend_blocked"
            if derivation_source_locked and not real_promotable
            else "inventory_requires_attention"
        ),
        "recommended_next_task": (
            "R40: implement the B05 exact axis-nondegeneracy and endpoint-transform "
            "object emitter, because R39 shows every real B05 bridge record is blocked "
            "before support/component/gap margins by missing exact axis norm and "
            "endpoint transform objects."
        ),
    }
    write_json_lf(out_path, output)

    print(f"input reports: {len(report_inventory)}")
    print(f"derivation source lock present: {derivation_source_locked}")
    print(f"real B05 reports promotable: {len(real_promotable)}")
    print(f"accepted real B05 reports: 0")
    print(f"synthetic accepted B05 fixture replay: {fixture_replay.get('replay_exit_code')}")
    print(f"missing exact/backend object counts: {dict(sorted(missing_counts.items()))}")
    print(f"manifest: {rel(out_path)}")
    if not derivation_source_locked:
        return 1
    if fixture_replay.get("replay_exit_code") not in {0, None}:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
