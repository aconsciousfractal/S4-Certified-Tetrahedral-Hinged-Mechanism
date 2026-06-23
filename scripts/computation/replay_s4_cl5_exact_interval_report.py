#!/usr/bin/env python
"""
Replay checker for S4 CL5 exact/interval report schema v1.

This is the first independent checker for the R21/R28 schema contract.  It is
deliberately conservative: it can validate synthetic B03-B08 reports and reject
malformed, unsupported-backend, diagnostic, and predicate-failing reports, but
it is not yet a generator for real S4 exact certificates.

Exit codes follow schemas/s4_cl5_exact_interval_report_schema_v1.yaml:

    0  replay passed and report is accepted
    1  replay failed predicate or margin
    2  malformed report or schema mismatch
    3  unsupported backend or operation
    4  diagnostic or nonclaim report only
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:  # pragma: no cover - local environment has PyYAML.
    yaml = None


EXIT_ACCEPTED = 0
EXIT_PREDICATE_FAILED = 1
EXIT_MALFORMED = 2
EXIT_UNSUPPORTED_BACKEND = 3
EXIT_DIAGNOSTIC = 4

EXPECTED_SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
EXPECTED_CASE_ID = "historical_s4_median_planes"
EXPECTED_POLICY_ID = "S4-CL5-EXACT-INTERVAL-ARITHMETIC-POLICY-2026-06-21"
EXPECTED_BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

REQUIRED_NONCLAIMS = {
    "no_physical_hingeability_claim",
    "no_global_s4_hingeability_claim",
    "no_dynamic_connectedness_claim",
    "no_theta_zero_positive_clearance_claim",
    "no_theorem_wrapper_promotion_claim",
}


class ReplayError(Exception):
    exit_code = EXIT_MALFORMED


class MalformedReport(ReplayError):
    exit_code = EXIT_MALFORMED


class UnsupportedBackend(ReplayError):
    exit_code = EXIT_UNSUPPORTED_BACKEND


class PredicateFailed(ReplayError):
    exit_code = EXIT_PREDICATE_FAILED


class DiagnosticReport(ReplayError):
    exit_code = EXIT_DIAGNOSTIC


@dataclass(frozen=True)
class RationalInterval:
    lo: Fraction
    hi: Fraction
    endpoint_semantics: str
    unit: str
    source_expr: str

    @property
    def strictly_positive(self) -> bool:
        return self.lo > 0


def load_mapping(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise MalformedReport(f"file not found: {path}")
    text = path.read_text(encoding="utf-8")
    suffix = path.suffix.lower()
    try:
        if suffix == ".json":
            obj = json.loads(text)
        elif suffix in {".yaml", ".yml"}:
            if yaml is None:
                raise MalformedReport("PyYAML is required to read YAML schema/report files")
            obj = yaml.safe_load(text)
        else:
            # Prefer YAML for extensionless fixtures because the schema is YAML.
            if yaml is None:
                obj = json.loads(text)
            else:
                obj = yaml.safe_load(text)
    except ReplayError:
        raise
    except Exception as exc:  # noqa: BLE001 - normalize parser exceptions.
        raise MalformedReport(f"cannot parse {path}: {exc}") from exc
    if not isinstance(obj, dict):
        raise MalformedReport(f"top-level object must be a mapping: {path}")
    return obj


def require_mapping(obj: Any, label: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        raise MalformedReport(f"{label} must be a mapping")
    return obj


def require_list(obj: Any, label: str) -> list[Any]:
    if not isinstance(obj, list):
        raise MalformedReport(f"{label} must be a list")
    return obj


def require_nonempty_string(obj: Any, label: str) -> str:
    if not isinstance(obj, str) or not obj:
        raise MalformedReport(f"{label} must be a nonempty string")
    return obj


def parse_endpoint(obj: Any, label: str) -> Fraction:
    data = require_mapping(obj, label)
    if set(data) != {"num", "den"}:
        raise MalformedReport(f"{label} must contain exactly num and den")
    num_raw = data["num"]
    den_raw = data["den"]
    if not isinstance(num_raw, str) or not isinstance(den_raw, str):
        raise MalformedReport(f"{label} endpoint values must be integer strings")
    try:
        num = int(num_raw, 10)
        den = int(den_raw, 10)
    except ValueError as exc:
        raise MalformedReport(f"{label} endpoint values must be base-10 integers") from exc
    if den <= 0:
        raise MalformedReport(f"{label} denominator must be positive")
    if math.gcd(num, den) != 1:
        raise MalformedReport(f"{label} fraction must be reduced")
    if num == 0 and den != 1:
        raise MalformedReport(f"{label} zero must be encoded as 0/1")
    return Fraction(num, den)


def parse_interval(obj: Any, schema: dict[str, Any], label: str) -> RationalInterval:
    data = require_mapping(obj, label)
    for field in ("lo", "hi", "endpoint_semantics", "unit", "source_expr"):
        if field not in data:
            raise MalformedReport(f"{label} missing interval field {field}")
    semantics = data["endpoint_semantics"]
    unit = data["unit"]
    allowed_semantics = set(schema["rational_interval"]["endpoint_semantics_allowed"])
    allowed_units = set(schema["rational_interval"]["unit_allowed"])
    if semantics not in allowed_semantics:
        raise MalformedReport(f"{label} endpoint_semantics not allowed: {semantics}")
    if unit not in allowed_units:
        raise MalformedReport(f"{label} unit not allowed: {unit}")
    source_expr = require_nonempty_string(data["source_expr"], f"{label}.source_expr")
    lo = parse_endpoint(data["lo"], f"{label}.lo")
    hi = parse_endpoint(data["hi"], f"{label}.hi")
    if lo > hi:
        raise MalformedReport(f"{label} has lo > hi")
    return RationalInterval(lo=lo, hi=hi, endpoint_semantics=semantics, unit=unit, source_expr=source_expr)


def endpoint(num: int, den: int = 1) -> dict[str, str]:
    frac = Fraction(num, den)
    return {"num": str(frac.numerator), "den": str(frac.denominator)}


def interval(lo: int, hi: int, unit: str = "signed_margin", expr: str = "synthetic") -> dict[str, Any]:
    return {
        "lo": endpoint(lo),
        "hi": endpoint(hi),
        "endpoint_semantics": "closed",
        "unit": unit,
        "source_expr": expr,
    }


def schema_contract(schema: dict[str, Any]) -> dict[str, Any]:
    if schema.get("schema_id") != EXPECTED_SCHEMA_ID:
        raise MalformedReport("schema_id mismatch in schema file")
    for field in (
        "required_top_level_fields",
        "accepted_backend_ids",
        "blocked_backend_ids",
        "predicate_ids",
        "route_extensions",
        "rational_interval",
    ):
        if field not in schema:
            raise MalformedReport(f"schema missing {field}")
    return schema


def validate_top_level(report: dict[str, Any], schema: dict[str, Any]) -> None:
    required = schema["required_top_level_fields"]
    missing = [field for field in required if field not in report]
    if missing:
        raise MalformedReport(f"report missing top-level fields: {', '.join(missing)}")
    if report["schema_id"] != schema["schema_id"]:
        raise MalformedReport("report schema_id does not match schema file")
    if report["case_id"] != schema["case_id"] or report["case_id"] != EXPECTED_CASE_ID:
        raise MalformedReport("case_id mismatch")
    if report["policy_id"] != schema["policy_id"] or report["policy_id"] != EXPECTED_POLICY_ID:
        raise MalformedReport("policy_id mismatch")
    if report["backend_lock_id"] != schema["backend_lock_id"] or report["backend_lock_id"] != EXPECTED_BACKEND_LOCK_ID:
        raise MalformedReport("backend_lock_id mismatch")
    if report["predicate_id"] not in schema["predicate_ids"]:
        raise MalformedReport(f"unregistered predicate_id: {report['predicate_id']}")
    require_nonempty_string(report["report_id"], "report_id")
    require_nonempty_string(report["report_kind"], "report_kind")
    require_nonempty_string(report["claim_level"], "claim_level")
    require_nonempty_string(report["generator_command"], "generator_command")
    require_nonempty_string(report["parent_key"], "parent_key")
    require_nonempty_string(report["domain_key"], "domain_key")
    require_list(report["source_ledger"], "source_ledger")
    require_mapping(report["input_intervals"], "input_intervals")
    require_mapping(report["branch_stability"], "branch_stability")
    require_mapping(report["ledger_reconstruction"], "ledger_reconstruction")
    require_mapping(report["replay_interface"], "replay_interface")
    require_list(report["nonclaim"], "nonclaim")


def validate_backends(report: dict[str, Any], schema: dict[str, Any]) -> None:
    accepted = set(schema["accepted_backend_ids"])
    blocked = set(schema["blocked_backend_ids"])
    allowed_ops = {
        backend_id: set(data.get("accepted_operations", []))
        for backend_id, data in schema["accepted_backend_ids"].items()
    }

    backend = report["rounding_backend"]
    if backend in blocked:
        raise UnsupportedBackend(f"rounding backend is blocked: {backend}")
    if backend not in accepted:
        raise UnsupportedBackend(f"rounding backend is not accepted: {backend}")

    operations = require_list(report["operation_enclosures"], "operation_enclosures")
    for idx, op in enumerate(operations):
        data = require_mapping(op, f"operation_enclosures[{idx}]")
        for field in schema["operation_enclosure"]["required"]:
            if field not in data:
                raise MalformedReport(f"operation_enclosures[{idx}] missing {field}")
        backend_id = data["backend_id"]
        operation = data["operation"]
        if backend_id in blocked:
            raise UnsupportedBackend(f"operation {data['op_id']} uses blocked backend {backend_id}")
        if backend_id not in accepted:
            raise UnsupportedBackend(f"operation {data['op_id']} uses unsupported backend {backend_id}")
        if operation not in allowed_ops[backend_id]:
            raise UnsupportedBackend(f"operation {operation} not allowed for backend {backend_id}")
        if backend_id == "fraction_interval_v1":
            parse_interval(data["output_interval"], schema, f"operation_enclosures[{idx}].output_interval")
        else:
            validate_symbolic_output(data, f"operation_enclosures[{idx}]")


def validate_symbolic_output(data: dict[str, Any], label: str) -> None:
    proof_rule = require_nonempty_string(data["proof_rule"], f"{label}.proof_rule")
    output = data["output_interval"]
    if not isinstance(output, dict):
        raise MalformedReport(f"{label}.output_interval must be a mapping for symbolic signs")
    if "symbolic_sign_margin" not in output and "sign_fact_list" not in output:
        raise MalformedReport(f"{label} symbolic output must include symbolic_sign_margin or sign_fact_list")
    if not proof_rule:
        raise MalformedReport(f"{label}.proof_rule is empty")


def validate_route_fields(report: dict[str, Any], schema: dict[str, Any]) -> dict[str, Any]:
    predicate_id = report["predicate_id"]
    route_schema = schema["route_extensions"][predicate_id]
    data = require_mapping(report.get("predicate_data"), "predicate_data")
    missing = [field for field in route_schema["required"] if field not in data]
    if missing:
        raise MalformedReport(f"predicate_data missing fields for {predicate_id}: {', '.join(missing)}")
    if predicate_id == "B07_EDGE_BRANCH_SUPPORT_COMPONENT_SOUNDNESS":
        if data["route"] not in route_schema["route_allowed"]:
            raise MalformedReport(f"B07 route not allowed: {data['route']}")
    return data


def status_is_accepted(obj: Any, label: str, accepted_values: set[str] | None = None) -> None:
    accepted_values = accepted_values or {"accepted"}
    data = require_mapping(obj, label)
    status = data.get("status")
    if status not in accepted_values:
        raise PredicateFailed(f"{label}.status is not accepted: {status}")


def require_string_list(obj: Any, label: str, *, nonempty: bool = False) -> list[str]:
    values = require_list(obj, label)
    if nonempty and not values:
        raise PredicateFailed(f"{label} must be nonempty")
    for idx, value in enumerate(values):
        require_nonempty_string(value, f"{label}[{idx}]")
    return values


def require_positive_interval(obj: Any, schema: dict[str, Any], label: str) -> RationalInterval:
    interval_value = parse_interval(obj, schema, label)
    if not interval_value.strictly_positive:
        raise PredicateFailed(f"{label}.lo must be strictly positive")
    return interval_value


def require_nonnegative_interval(obj: Any, schema: dict[str, Any], label: str) -> RationalInterval:
    interval_value = parse_interval(obj, schema, label)
    if interval_value.lo < 0:
        raise PredicateFailed(f"{label}.lo must be nonnegative")
    return interval_value


def intervals_same(a: RationalInterval, b: RationalInterval) -> bool:
    return (
        a.lo == b.lo
        and a.hi == b.hi
        and a.endpoint_semantics == b.endpoint_semantics
        and a.unit == b.unit
    )


def validate_b05_formula_shape(report: dict[str, Any], schema: dict[str, Any], data: dict[str, Any]) -> None:
    formula = data.get("formula_shape")
    if formula is None:
        if report.get("report_kind") == "b05_formula_shape_synthetic_fixture":
            raise MalformedReport("B05 formula-shape fixture missing predicate_data.formula_shape")
        return

    formula = require_mapping(formula, "predicate_data.formula_shape")
    for field in ("axis_nondegeneracy", "support_state", "component_motion_bounds", "exact_gap_formula"):
        if field not in formula:
            raise MalformedReport(f"predicate_data.formula_shape missing {field}")

    axis = require_mapping(formula["axis_nondegeneracy"], "predicate_data.formula_shape.axis_nondegeneracy")
    status_is_accepted(axis, "predicate_data.formula_shape.axis_nondegeneracy")
    require_nonempty_string(axis.get("axis_expression"), "predicate_data.formula_shape.axis_nondegeneracy.axis_expression")
    labels = set(require_string_list(axis.get("common_edge_labels"), "predicate_data.formula_shape.axis_nondegeneracy.common_edge_labels", nonempty=True))
    if labels != {"M_AB", "M_CD"}:
        raise PredicateFailed("B05 common_edge_labels must be exactly M_AB and M_CD")
    require_positive_interval(
        axis.get("axis_norm_lower_bound"),
        schema,
        "predicate_data.formula_shape.axis_nondegeneracy.axis_norm_lower_bound",
    )

    support = require_mapping(formula["support_state"], "predicate_data.formula_shape.support_state")
    status_is_accepted(support, "predicate_data.formula_shape.support_state")
    require_string_list(support.get("lower_support_labels"), "predicate_data.formula_shape.support_state.lower_support_labels", nonempty=True)
    require_string_list(support.get("upper_support_labels"), "predicate_data.formula_shape.support_state.upper_support_labels", nonempty=True)
    require_string_list(support.get("lower_non_support_labels"), "predicate_data.formula_shape.support_state.lower_non_support_labels")
    require_string_list(support.get("upper_non_support_labels"), "predicate_data.formula_shape.support_state.upper_non_support_labels")

    component = require_mapping(formula["component_motion_bounds"], "predicate_data.formula_shape.component_motion_bounds")
    for piece_field in ("lower_piece", "upper_piece"):
        piece = require_mapping(component.get(piece_field), f"predicate_data.formula_shape.component_motion_bounds.{piece_field}")
        interval_count = 0
        for key, value in piece.items():
            if isinstance(value, dict) and {"lo", "hi", "endpoint_semantics", "unit", "source_expr"} <= set(value):
                require_nonnegative_interval(
                    value,
                    schema,
                    f"predicate_data.formula_shape.component_motion_bounds.{piece_field}.{key}",
                )
                interval_count += 1
        if interval_count == 0:
            raise PredicateFailed(f"predicate_data.formula_shape.component_motion_bounds.{piece_field} has no interval bounds")
    rodrigues = require_mapping(component.get("rodrigues_terms"), "predicate_data.formula_shape.component_motion_bounds.rodrigues_terms")
    for field in ("A_term_rule", "B_term_rule", "bound_rule"):
        require_nonempty_string(rodrigues.get(field), f"predicate_data.formula_shape.component_motion_bounds.rodrigues_terms.{field}")

    exact_gap = require_mapping(formula["exact_gap_formula"], "predicate_data.formula_shape.exact_gap_formula")
    require_nonempty_string(exact_gap.get("source_identity_id"), "predicate_data.formula_shape.exact_gap_formula.source_identity_id")
    m_gap = require_positive_interval(exact_gap.get("M_gap"), schema, "predicate_data.formula_shape.exact_gap_formula.M_gap")
    require_positive_interval(exact_gap.get("M_L"), schema, "predicate_data.formula_shape.exact_gap_formula.M_L")
    require_positive_interval(exact_gap.get("M_U"), schema, "predicate_data.formula_shape.exact_gap_formula.M_U")
    route_gap = parse_interval(data["gap_interval"], schema, "predicate_data.gap_interval")
    top_margin = parse_interval(report["margin_interval"], schema, "margin_interval")
    if not intervals_same(m_gap, route_gap):
        raise PredicateFailed("B05 formula_shape M_gap must match predicate_data.gap_interval")
    if not intervals_same(m_gap, top_margin):
        raise PredicateFailed("B05 formula_shape M_gap must match top-level margin_interval")

    operation_ids = {
        require_mapping(op, "operation_enclosure").get("op_id")
        for op in require_list(report["operation_enclosures"], "operation_enclosures")
    }
    required_ops = {"op_axis_cross_product", "op_support_finite_extrema", "op_M_gap"}
    missing_ops = sorted(required_ops - operation_ids)
    if missing_ops:
        raise PredicateFailed(f"B05 formula-shape operation enclosures missing: {', '.join(missing_ops)}")


def validate_common_acceptance(report: dict[str, Any], schema: dict[str, Any]) -> None:
    parse_interval(report["margin_interval"], schema, "margin_interval")
    parse_interval(report["error_interval"], schema, "error_interval")
    status_is_accepted(report["branch_stability"], "branch_stability", {"accepted", "exhaustively_split"})
    status_is_accepted(report["ledger_reconstruction"], "ledger_reconstruction", {"accepted"})
    replay = require_mapping(report["replay_interface"], "replay_interface")
    if replay.get("checker") != "scripts/replay_s4_cl5_exact_interval_report.py":
        raise MalformedReport("replay_interface.checker mismatch")
    nonclaims = set(report["nonclaim"])
    missing = sorted(REQUIRED_NONCLAIMS - nonclaims)
    if missing:
        raise MalformedReport(f"missing required nonclaims: {', '.join(missing)}")


def validate_margin(report: dict[str, Any], schema: dict[str, Any]) -> None:
    margin = parse_interval(report["margin_interval"], schema, "margin_interval")
    error = parse_interval(report["error_interval"], schema, "error_interval")
    if margin.lo <= error.hi:
        raise PredicateFailed("margin_interval.lo must be strictly greater than error_interval.hi")


def validate_b08_overlay(report: dict[str, Any], schema: dict[str, Any], data: dict[str, Any]) -> None:
    child_keys = require_list(data["child_keys"], "predicate_data.child_keys")
    if not child_keys:
        raise PredicateFailed("B08 child_keys must be nonempty")
    intervals = require_list(data["exact_child_intervals"], "predicate_data.exact_child_intervals")
    if len(intervals) != len(child_keys):
        raise PredicateFailed("B08 child_keys and exact_child_intervals must have same length")
    for idx, child_interval in enumerate(intervals):
        parse_interval(child_interval, schema, f"predicate_data.exact_child_intervals[{idx}]")
    status_is_accepted(data["partition_certificate"], "predicate_data.partition_certificate")
    status_is_accepted(data["disjointness_certificate"], "predicate_data.disjointness_certificate")
    status_is_accepted(data["terminal_key_reconstruction"], "predicate_data.terminal_key_reconstruction")
    route_ids = set(require_list(data["route_predicate_ids"], "predicate_data.route_predicate_ids"))
    allowed = set(schema["predicate_ids"]) - {"B08_ADAPTIVE_OVERLAY_RECONSTRUCTION_SOUNDNESS"}
    if not route_ids or not route_ids <= allowed:
        raise PredicateFailed("B08 route_predicate_ids must reference B03-B07 predicate ids")
    excluded = set(require_list(data["excluded_scope"], "predicate_data.excluded_scope"))
    required_exclusions = {
        "theta_zero_positive_clearance",
        "dynamic_connectedness",
        "physical_hingeability",
        "theorem_wrapper_promotion",
    }
    missing = sorted(required_exclusions - excluded)
    if missing:
        raise MalformedReport(f"B08 excluded_scope missing: {', '.join(missing)}")


def replay_report(report: dict[str, Any], schema: dict[str, Any], strict: bool = False) -> int:
    schema = schema_contract(schema)
    validate_top_level(report, schema)
    validate_backends(report, schema)
    route_data = validate_route_fields(report, schema)
    validate_common_acceptance(report, schema)

    if report["accepted"] is not True:
        raise DiagnosticReport("report is diagnostic/nonclaim because accepted is not true")

    if report["predicate_id"] == "B08_ADAPTIVE_OVERLAY_RECONSTRUCTION_SOUNDNESS":
        validate_b08_overlay(report, schema, route_data)
    elif report["predicate_id"] == "B05_COMMON_EDGE_PROJECTION_SOUNDNESS":
        validate_b05_formula_shape(report, schema, route_data)
        validate_margin(report, schema)
    else:
        validate_margin(report, schema)

    if strict and report.get("failure_reason") not in ("", None):
        raise MalformedReport("accepted report must have empty failure_reason under --strict")
    return EXIT_ACCEPTED


def base_report(predicate_id: str, predicate_data: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_id": EXPECTED_SCHEMA_ID,
        "report_id": f"SYNTHETIC-{predicate_id}",
        "report_kind": "synthetic_fixture",
        "case_id": EXPECTED_CASE_ID,
        "policy_id": EXPECTED_POLICY_ID,
        "backend_lock_id": EXPECTED_BACKEND_LOCK_ID,
        "predicate_id": predicate_id,
        "claim_level": "exact_interval_report",
        "generator_command": "synthetic_fixture",
        "source_ledger": ["synthetic_fixture"],
        "parent_key": "SYNTHETIC_PARENT",
        "domain_key": "SYNTHETIC_DOMAIN",
        "input_intervals": {"theta": interval(0, 1, unit="degree", expr="theta")},
        "operation_enclosures": [
            {
                "op_id": "op_margin",
                "backend_id": "fraction_interval_v1",
                "operation": "add",
                "input_refs": ["synthetic"],
                "output_interval": interval(2, 3, expr="synthetic_margin"),
                "proof_rule": "synthetic_exact_fraction_interval",
            }
        ],
        "rounding_backend": "fraction_interval_v1",
        "margin_interval": interval(2, 3, expr="margin"),
        "error_interval": interval(0, 0, expr="error"),
        "branch_stability": {"status": "accepted", "rule": "synthetic"},
        "ledger_reconstruction": {"status": "accepted", "rule": "synthetic"},
        "replay_interface": {
            "checker": "scripts/replay_s4_cl5_exact_interval_report.py",
            "schema": "schemas/s4_cl5_exact_interval_report_schema_v1.yaml",
        },
        "accepted": True,
        "failure_reason": "",
        "nonclaim": sorted(REQUIRED_NONCLAIMS),
        "predicate_data": predicate_data,
    }


def synthetic_predicate_data(predicate_id: str) -> dict[str, Any]:
    common_interval = interval(2, 3, expr="route_margin")
    data_by_predicate = {
        "B03_STRICT_CONVEX_SAT": {
            "piece_pair": "P0-P1",
            "cell_or_segment_key": "synthetic_cell",
            "excluded_selected_hinge_contact": True,
            "axis_family": "synthetic_axis_family",
            "axis_id": "axis_0",
            "axis_nondegeneracy_interval": common_interval,
            "support_interval_left": common_interval,
            "support_interval_right": interval(0, 1, expr="support_right"),
            "separation_margin_interval": common_interval,
            "sat_axis_completeness_certificate": {"status": "accepted"},
        },
        "B04_SELECTED_HINGE_CONTACT_ORIENTATION": {
            "contact_id": "synthetic_contact",
            "hinge_axis": "AB",
            "signed_orientation_expression": "synthetic_positive_orientation",
            "angle_interval": interval(0, 1, unit="degree", expr="angle"),
            "opening_side_interval": common_interval,
            "branch_interval": interval(0, 1, expr="branch"),
            "boundary_contact_certificate": {"status": "accepted"},
            "no_positive_clearance_nonclaim": True,
        },
        "B05_COMMON_EDGE_PROJECTION_SOUNDNESS": {
            "common_edge_id": "M_AB",
            "projection_axis_or_coordinate": "synthetic_projection_axis",
            "projection_coordinate_intervals": [interval(0, 1, unit="projection", expr="projection")],
            "endpoint_case": "interior",
            "branch_validity": {"status": "accepted"},
            "gap_interval": common_interval,
            "parent_overlay_key": "synthetic_parent_overlay",
        },
        "B06_FACE_NORMAL_SUPPORT_GAP_SOUNDNESS": {
            "face_axis": "face_normal_0",
            "normal_validity_interval": common_interval,
            "raw_gap_formula_id": "synthetic_formula",
            "raw_gap_interval": common_interval,
            "support_extremality_intervals": [common_interval],
            "edge_branch_exclusion": {"status": "accepted"},
        },
        "B07_EDGE_BRANCH_SUPPORT_COMPONENT_SOUNDNESS": {
            "route": "G1",
            "candidate_axis_set": ["axis_0"],
            "axis_nondegeneracy": common_interval,
            "support_state": {"status": "accepted"},
            "support_component_intervals": [common_interval],
            "signed_component_margin_interval": common_interval,
            "branch_stability_evidence": {"status": "accepted"},
            "switch_domain_certificate": {"status": "accepted"},
            "parent_cell_key": "synthetic_parent_cell",
            "subcell_key": "synthetic_subcell",
        },
        "B08_ADAPTIVE_OVERLAY_RECONSTRUCTION_SOUNDNESS": {
            "parent_universe_id": "synthetic_parent_universe",
            "parent_key": "synthetic_parent",
            "child_keys": ["child_0", "child_1"],
            "exact_child_intervals": [
                interval(0, 1, unit="local_cell", expr="child_0"),
                interval(1, 2, unit="local_cell", expr="child_1"),
            ],
            "partition_certificate": {"status": "accepted"},
            "disjointness_certificate": {"status": "accepted"},
            "route_predicate_ids": [
                "B03_STRICT_CONVEX_SAT",
                "B07_EDGE_BRANCH_SUPPORT_COMPONENT_SOUNDNESS",
            ],
            "terminal_key_reconstruction": {"status": "accepted"},
            "excluded_scope": [
                "theta_zero_positive_clearance",
                "dynamic_connectedness",
                "physical_hingeability",
                "theorem_wrapper_promotion",
            ],
        },
    }
    return data_by_predicate[predicate_id]


def synthetic_fixtures(schema: dict[str, Any]) -> list[tuple[str, int, dict[str, Any]]]:
    fixtures: list[tuple[str, int, dict[str, Any]]] = []
    for predicate_id in schema["predicate_ids"]:
        fixtures.append((f"accepted_{predicate_id}", EXIT_ACCEPTED, base_report(predicate_id, synthetic_predicate_data(predicate_id))))

    malformed = base_report("B03_STRICT_CONVEX_SAT", synthetic_predicate_data("B03_STRICT_CONVEX_SAT"))
    malformed.pop("margin_interval")
    fixtures.append(("malformed_missing_margin", EXIT_MALFORMED, malformed))

    unsupported = base_report("B03_STRICT_CONVEX_SAT", synthetic_predicate_data("B03_STRICT_CONVEX_SAT"))
    unsupported["operation_enclosures"][0]["backend_id"] = "float64_numpy_scipy"
    fixtures.append(("unsupported_blocked_backend", EXIT_UNSUPPORTED_BACKEND, unsupported))

    diagnostic = base_report("B03_STRICT_CONVEX_SAT", synthetic_predicate_data("B03_STRICT_CONVEX_SAT"))
    diagnostic["accepted"] = False
    diagnostic["failure_reason"] = "synthetic diagnostic report"
    fixtures.append(("diagnostic_nonclaim", EXIT_DIAGNOSTIC, diagnostic))

    predicate_fail = base_report("B03_STRICT_CONVEX_SAT", synthetic_predicate_data("B03_STRICT_CONVEX_SAT"))
    predicate_fail["margin_interval"] = interval(0, 0, expr="zero_margin")
    fixtures.append(("predicate_fail_nonpositive_margin", EXIT_PREDICATE_FAILED, predicate_fail))

    b08_fail = base_report("B08_ADAPTIVE_OVERLAY_RECONSTRUCTION_SOUNDNESS", synthetic_predicate_data("B08_ADAPTIVE_OVERLAY_RECONSTRUCTION_SOUNDNESS"))
    b08_fail["predicate_data"]["disjointness_certificate"] = {"status": "failed"}
    fixtures.append(("predicate_fail_b08_disjointness", EXIT_PREDICATE_FAILED, b08_fail))
    return fixtures


def run_selftest(schema: dict[str, Any]) -> int:
    schema = schema_contract(schema)
    failures = []
    for name, expected, report in synthetic_fixtures(schema):
        try:
            got = replay_report(report, schema, strict=True)
        except ReplayError as exc:
            got = exc.exit_code
        status = "PASS" if got == expected else "FAIL"
        print(f"[{status}] {name}: expected={expected} got={got}")
        if got != expected:
            failures.append((name, expected, got))
    if failures:
        print(f"selftest failed: {len(failures)} fixture(s)", file=sys.stderr)
        return EXIT_PREDICATE_FAILED
    print("selftest passed")
    return EXIT_ACCEPTED


def write_fixtures(schema: dict[str, Any], out_dir: Path) -> int:
    schema = schema_contract(schema)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, expected, report in synthetic_fixtures(schema):
        path = out_dir / f"{name}.json"
        path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        manifest.append({"name": name, "expected_exit_code": expected, "path": str(path)})
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {len(manifest)} synthetic fixtures to {out_dir}")
    return EXIT_ACCEPTED


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Replay S4 CL5 exact/interval schema-v1 reports.")
    parser.add_argument("--report", type=Path, help="Report JSON/YAML file to replay.")
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("schemas/s4_cl5_exact_interval_report_schema_v1.yaml"),
        help="Schema YAML file.",
    )
    parser.add_argument("--strict", action="store_true", help="Reject accepted reports with a nonempty failure_reason.")
    parser.add_argument("--selftest", action="store_true", help="Run embedded synthetic B03-B08 replay fixtures.")
    parser.add_argument("--write-fixtures", type=Path, help="Write embedded synthetic fixtures to the given directory.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        schema = load_mapping(args.schema)
        if args.selftest:
            return run_selftest(schema)
        if args.write_fixtures:
            return write_fixtures(schema, args.write_fixtures)
        if not args.report:
            parser.error("--report is required unless --selftest or --write-fixtures is used")
        report = load_mapping(args.report)
        code = replay_report(report, schema, strict=args.strict)
        print("replay accepted")
        return code
    except ReplayError as exc:
        print(f"replay rejected: {exc}", file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
