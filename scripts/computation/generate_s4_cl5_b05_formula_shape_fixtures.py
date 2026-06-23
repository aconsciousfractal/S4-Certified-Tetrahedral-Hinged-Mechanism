#!/usr/bin/env python
"""
Generate B05 formula-shape synthetic fixtures.

R37 extends the synthetic B05 coverage beyond the minimal R28 fixture.  These
fixtures exercise the source-locked formula shape from R35/R36: common-edge
axis norm, support state, one-sided component bounds, M_gap, M_L, M_U, and
operation-enclosure trace fields.

The fixtures are synthetic only.  They do not promote any real S4 B05 report.
They replay through the existing schema-v1 checker using current checker
semantics; extra formula-shape fields are recorded for engine contract
development and are not yet a full semantic validator.
"""

from __future__ import annotations

import argparse
import copy
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
MANIFEST_ID = "S4-CL5-B05-FORMULA-SHAPE-SYNTHETIC-FIXTURE-SUITE-2026-06-22"

DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/fixtures/synthetic/"
    "b05_formula_shape"
)
DEFAULT_MANIFEST = DEFAULT_OUT_DIR / "b05_formula_shape_fixture_manifest.json"
DEFAULT_R36_INVENTORY = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_exact_gap_formula_source_inventory_manifest.json"
)
REPLAY_CHECKER = Path("scripts/replay_s4_cl5_exact_interval_report.py")
SCHEMA = Path("schemas/s4_cl5_exact_interval_report_schema_v1.yaml")

REQUIRED_NONCLAIMS = [
    "no_dynamic_connectedness_claim",
    "no_global_s4_hingeability_claim",
    "no_physical_hingeability_claim",
    "no_theorem_wrapper_promotion_claim",
    "no_theta_zero_positive_clearance_claim",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


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
    expr: str = "synthetic",
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


def write_json_lf(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"expected JSON object: {path}")
    return data


def formula_shape(
    *,
    axis_norm: dict[str, Any] | None = None,
    gap: dict[str, Any] | None = None,
    lower_stability: dict[str, Any] | None = None,
    upper_stability: dict[str, Any] | None = None,
    support_status: str = "accepted",
) -> dict[str, Any]:
    axis_norm = axis_norm or interval(2, 3, unit="projection", expr="synthetic_axis_norm_lower_bound")
    gap = gap or interval(2, 3, unit="signed_margin", expr="M_gap")
    lower_stability = lower_stability or interval(1, 2, unit="signed_margin", expr="M_L")
    upper_stability = upper_stability or interval(1, 2, unit="signed_margin", expr="M_U")
    return {
        "axis_nondegeneracy": {
            "axis_expression": "n_ij = (F_i(M_CD)-F_i(M_AB)) x (F_j(M_CD)-F_j(M_AB))",
            "axis_norm_lower_bound": axis_norm,
            "common_edge_labels": ["M_AB", "M_CD"],
            "status": "accepted" if axis_norm["lo"]["num"] != "0" else "failed",
        },
        "component_motion_bounds": {
            "lower_piece": {
                "Delta_pos_L_support": interval(1, 4, hi_den=4, unit="projection", expr="Delta_pos(L,S_L)"),
                "Delta_neg_L_support": interval(0, 1, hi_den=4, unit="projection", expr="Delta_neg(L,S_L)"),
            },
            "upper_piece": {
                "Delta_pos_U_support": interval(0, 1, hi_den=4, unit="projection", expr="Delta_pos(U,S_U)"),
                "Delta_neg_U_support": interval(1, 4, hi_den=4, unit="projection", expr="Delta_neg(U,S_U)"),
            },
            "rodrigues_terms": {
                "A_term_rule": "A = u dot (w x (v-o))",
                "B_term_rule": "B = (u dot w)(w dot (v-o)) - u dot (v-o)",
                "bound_rule": "D_pos/D_neg from R35 source lock",
            },
        },
        "exact_gap_formula": {
            "M_L": lower_stability,
            "M_U": upper_stability,
            "M_gap": gap,
            "source_identity_id": "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22",
        },
        "support_state": {
            "lower_non_support_labels": ["v_L2"],
            "lower_support_labels": ["v_L0", "v_L1"],
            "status": support_status,
            "upper_non_support_labels": ["v_U2"],
            "upper_support_labels": ["v_U0", "v_U1"],
        },
    }


def operation_enclosures(*, blocked_trig: bool = False, gap: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    gap = gap or interval(2, 3, unit="signed_margin", expr="M_gap")
    operations = [
        {
            "backend_id": "fraction_interval_v1",
            "input_refs": ["synthetic_e_i", "synthetic_e_j"],
            "op_id": "op_axis_cross_product",
            "operation": "cross_product_polynomial_components",
            "output_interval": interval(2, 3, unit="projection", expr="axis_norm_lower_bound"),
            "proof_rule": "synthetic_axis_nondegeneracy_interval",
        },
        {
            "backend_id": "fraction_interval_v1",
            "input_refs": ["synthetic_support_vertices"],
            "op_id": "op_support_finite_extrema",
            "operation": "finite_min",
            "output_interval": interval(1, 2, unit="projection", expr="support_competition_margin"),
            "proof_rule": "synthetic_support_state_stability",
        },
        {
            "backend_id": "fraction_interval_v1",
            "input_refs": ["Delta_pos_L", "Delta_neg_U", "g0"],
            "op_id": "op_M_gap",
            "operation": "subtract",
            "output_interval": gap,
            "proof_rule": "synthetic_R35_M_gap_rule",
        },
    ]
    if blocked_trig:
        operations.insert(
            0,
            {
                "backend_id": "general_trig_interval_v1",
                "input_refs": ["h"],
                "op_id": "op_blocked_sin_h",
                "operation": "sin",
                "output_interval": interval(0, 1, unit="dimensionless", expr="blocked_sin_h"),
                "proof_rule": "blocked_backend_fixture",
            },
        )
    return operations


def base_report(report_id: str, *, gap: dict[str, Any] | None = None) -> dict[str, Any]:
    gap = gap or interval(2, 3, unit="signed_margin", expr="M_gap")
    return {
        "accepted": True,
        "backend_lock_id": BACKEND_LOCK_ID,
        "branch_stability": {
            "rule": "synthetic_formula_shape_branch_stability",
            "status": "accepted",
        },
        "case_id": CASE_ID,
        "claim_level": "exact_interval_report",
        "domain_key": f"{report_id}:synthetic_domain",
        "error_interval": interval(0, 0, unit="signed_margin", expr="zero_error"),
        "failure_reason": "",
        "generator_command": "scripts/generate_s4_cl5_b05_formula_shape_fixtures.py",
        "input_intervals": {
            "theta_degrees": interval(0, 1, unit="degree", expr="synthetic_theta_domain"),
        },
        "ledger_reconstruction": {
            "rule": "synthetic_formula_shape_fixture",
            "status": "accepted",
        },
        "margin_interval": gap,
        "nonclaim": REQUIRED_NONCLAIMS,
        "operation_enclosures": operation_enclosures(gap=gap),
        "parent_key": "SYNTHETIC_B05_FORMULA_SHAPE_PARENT",
        "policy_id": POLICY_ID,
        "predicate_data": {
            "branch_validity": {"status": "accepted"},
            "common_edge_id": "M_AB-M_CD",
            "endpoint_case": "interior_positive_gap",
            "formula_shape": formula_shape(gap=gap),
            "gap_interval": gap,
            "parent_overlay_key": "synthetic_b05_formula_shape_parent_overlay",
            "projection_axis_or_coordinate": "n_ij = e_i x e_j",
            "projection_coordinate_intervals": [
                interval(0, 1, unit="projection", expr="lower_projection_support"),
                interval(2, 3, unit="projection", expr="upper_projection_support"),
            ],
        },
        "predicate_id": PREDICATE_ID,
        "replay_interface": {
            "checker": "scripts/replay_s4_cl5_exact_interval_report.py",
            "schema": "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        },
        "report_id": report_id,
        "report_kind": "b05_formula_shape_synthetic_fixture",
        "rounding_backend": "fraction_interval_v1",
        "schema_id": SCHEMA_ID,
        "source_ledger": [
            "docs/S4_CL5_B05_COMMON_EDGE_EXACT_GAP_DERIVATION.md",
            "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/manifests/b05_exact_gap_formula_source_inventory_manifest.json",
        ],
    }


def fixture_specs() -> list[tuple[str, int, dict[str, Any]]]:
    accepted = base_report("SYNTHETIC-B05-FORMULA-SHAPE-ACCEPTED")

    zero_gap = base_report(
        "SYNTHETIC-B05-FORMULA-SHAPE-ZERO-GAP-REJECTED",
        gap=interval(0, 0, unit="signed_margin", expr="M_gap_zero"),
    )

    degenerate_axis = base_report("SYNTHETIC-B05-FORMULA-SHAPE-DEGENERATE-AXIS-REJECTED")
    zero_axis = interval(0, 0, unit="projection", expr="axis_norm_zero")
    degenerate_axis["branch_stability"] = {
        "rule": "synthetic_axis_nondegeneracy_required",
        "status": "failed",
    }
    degenerate_axis["predicate_data"]["formula_shape"] = formula_shape(axis_norm=zero_axis)

    blocked_trig = base_report("SYNTHETIC-B05-FORMULA-SHAPE-BLOCKED-TRIG-BACKEND")
    blocked_trig["operation_enclosures"] = operation_enclosures(blocked_trig=True)

    unstable_support = base_report("SYNTHETIC-B05-FORMULA-SHAPE-UNSTABLE-SUPPORT-REJECTED")
    unstable_support["branch_stability"] = {
        "rule": "synthetic_support_state_stability_required",
        "status": "failed",
    }
    unstable_support["predicate_data"]["branch_validity"] = {"status": "failed"}
    unstable_support["predicate_data"]["formula_shape"] = formula_shape(support_status="failed")

    diagnostic = base_report("SYNTHETIC-B05-FORMULA-SHAPE-DIAGNOSTIC-NONCLAIM")
    diagnostic["accepted"] = False
    diagnostic["failure_reason"] = "synthetic_formula_shape_diagnostic_nonclaim"

    return [
        ("accepted_formula_shape_fraction_interval", 0, accepted),
        ("rejected_zero_gap", 1, zero_gap),
        ("rejected_degenerate_axis", 1, degenerate_axis),
        ("rejected_blocked_trig_backend", 3, blocked_trig),
        ("rejected_unstable_support_state", 1, unstable_support),
        ("diagnostic_nonclaim", 4, diagnostic),
    ]


def replay_report(path: Path, checker: Path, schema: Path) -> dict[str, Any]:
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
        "exit_code": completed.returncode,
        "report": rel(path),
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }


def sanitize(text: str) -> str:
    return "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    parser.add_argument("--r36-inventory", default=DEFAULT_R36_INVENTORY.as_posix())
    parser.add_argument("--schema", default=SCHEMA.as_posix())
    parser.add_argument("--replay-checker", default=REPLAY_CHECKER.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest
    r36_path = ROOT / args.r36_inventory
    schema_path = ROOT / args.schema
    checker_path = ROOT / args.replay_checker
    r36_inventory = read_json(r36_path)

    generated = []
    replay_results = []
    for fixture_id, expected_exit, report in fixture_specs():
        path = out_dir / f"{sanitize(fixture_id)}.json"
        write_json_lf(path, report)
        replay = replay_report(path, checker_path, schema_path)
        replay_results.append({**replay, "fixture_id": fixture_id, "expected_exit_code": expected_exit})
        generated.append(
            {
                "expected_exit_code": expected_exit,
                "fixture_id": fixture_id,
                "path": rel(path),
                "report_id": report["report_id"],
            }
        )

    mismatches = [
        item for item in replay_results
        if item["exit_code"] != item["expected_exit_code"]
    ]
    exit_counts = Counter(str(item["exit_code"]) for item in replay_results)
    expected_counts = Counter(str(item["expected_exit_code"]) for item in replay_results)
    manifest = {
        "accepted_real_b05_report_count": 0,
        "case_id": CASE_ID,
        "fixture_count": len(generated),
        "fixture_manifest_id": MANIFEST_ID,
        "formula_shape_semantic_boundary": (
            "current replay validates schema/minimal B05 margin semantics; extra R35 formula-shape "
            "fields are synthetic engine-contract fields and are not yet a full semantic validator"
        ),
        "generated_fixtures": generated,
        "input_r36_inventory": rel(r36_path),
        "nonclaim": [
            "no_real_s4_b05_accepted_report_claim",
            "no_b05_exact_backend_implementation_claim",
            "no_common_edge_gap_proof_claim",
            "no_theorem_wrapper_promotion_claim",
            "no_physical_hingeability_claim",
        ],
        "predicate_id": PREDICATE_ID,
        "real_report_promotable_count_from_r36": r36_inventory.get("real_report_promotable_count"),
        "replay_exit_code_counts": dict(sorted(exit_counts.items())),
        "replay_expected_exit_code_counts": dict(sorted(expected_counts.items())),
        "replay_mismatches": mismatches,
        "replay_results": replay_results,
        "schema_id": SCHEMA_ID,
        "status": "passed" if not mismatches else "failed",
        "recommended_next_task": (
            "R40: implement the B05 exact axis-nondegeneracy and endpoint-transform "
            "object emitter, because R39 shows every real B05 bridge record is blocked "
            "before support/component/gap margins by missing exact axis norm and "
            "endpoint transform objects."
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"fixtures generated: {len(generated)}")
    print(f"replay exit code counts: {dict(sorted(exit_counts.items()))}")
    print(f"replay mismatches: {len(mismatches)}")
    print(f"real accepted B05 reports: 0")
    print(f"manifest: {rel(manifest_path)}")
    if mismatches:
        for item in mismatches:
            print(
                f"mismatch {item['fixture_id']}: expected {item['expected_exit_code']} "
                f"got {item['exit_code']}"
            )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
