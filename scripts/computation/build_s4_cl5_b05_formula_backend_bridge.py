#!/usr/bin/env python
"""
Build the B05 real formula backend bridge.

R39 consumes the R36 formula inventory and the R38 schema/checker contract.
It attempts to materialize the real-source B05 formula objects needed by the
checker-enforced `predicate_data.formula_shape` contract, but it does not
promote any real S4 B05 report.

The output is a bridge manifest plus one per-report bridge record.  Each record
separates source-locked symbolic seeds that can already be emitted from the
positive interval objects that are still backend/proof blocked.
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
MANIFEST_ID = "S4-CL5-B05-FORMULA-BACKEND-BRIDGE-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_FORMULA_BACKEND_BRIDGE"
R35_SOURCE_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R36_INVENTORY = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_exact_gap_formula_source_inventory_manifest.json"
)
DEFAULT_R37_FIXTURE_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/fixtures/synthetic/"
    "b05_formula_shape/b05_formula_shape_fixture_manifest.json"
)
DEFAULT_DECISION = Path("docs/S4_CL5_B05_FORMULA_SHAPE_CONTRACT_DECISION.md")
DEFAULT_DERIVATION = Path("docs/S4_CL5_B05_COMMON_EDGE_EXACT_GAP_DERIVATION.md")
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "formula_backend_bridge"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_formula_backend_bridge_manifest.json"
)
REPLAY_CHECKER = Path("scripts/replay_s4_cl5_exact_interval_report.py")
SCHEMA = Path("schemas/s4_cl5_exact_interval_report_schema_v1.yaml")

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_common_edge_gap_claim",
    "no_formula_shape_contract_ready_real_report_claim",
    "no_backend_implementation_claim",
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


def sanitize(value: Any) -> str:
    text = str(value)
    out = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def file_has_text(path: Path, required: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    return all(item in text for item in required)


def replay_report(path: Path, checker: Path, schema: Path, *, no_replay: bool) -> dict[str, Any]:
    if no_replay:
        return {
            "path": rel(path),
            "replay_exit_code": None,
            "replay_status": "not_run",
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
        "path": rel(path),
        "replay_exit_code": completed.returncode,
        "replay_status": "expected_diagnostic" if completed.returncode == 4 else "unexpected",
        "stderr": completed.stderr.strip(),
        "stdout": completed.stdout.strip(),
    }


def source_locked_terms_available(derivation_path: Path, decision_path: Path) -> dict[str, bool]:
    return {
        "r35_derivation_formula_terms": file_has_text(
            derivation_path,
            [
                "n_ij(q) = e_i(q) x e_j(q)",
                "u dot (R_epsilon(v) - v)",
                "M_gap = g0 - Delta_pos(L,S_L) - Delta_neg(U,S_U) - tau",
                "M_L = c_L - Delta_neg(L,S_L) - Delta_pos(L,N_L) - tau",
                "M_U = c_U - Delta_pos(U,S_U) - Delta_neg(U,N_U) - tau",
            ],
        ),
        "r38_contract_terms": file_has_text(
            decision_path,
            [
                "axis_nondegeneracy",
                "support_state",
                "component_motion_bounds",
                "exact_gap_formula",
                "operation_enclosures",
            ],
        ),
    }


def report_path_from_inventory(item: dict[str, Any]) -> Path:
    report = item.get("report")
    if not isinstance(report, str) or not report:
        raise ValueError(f"inventory item missing report path: {item.get('report_id')}")
    return ROOT / report


def field_status(status: str, *, emitted_value: Any = None, blockers: list[str] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {"status": status}
    if emitted_value is not None:
        out["emitted_value"] = emitted_value
    if blockers:
        out["blockers"] = blockers
    return out


def common_edge_labels(report: dict[str, Any]) -> list[str]:
    edge_id = report.get("predicate_data", {}).get("common_edge_id")
    if edge_id == "M_AB-M_CD":
        return ["M_AB", "M_CD"]
    return []


def required_ops_present(report: dict[str, Any]) -> dict[str, Any]:
    operation_ids = [
        op.get("op_id")
        for op in report.get("operation_enclosures", [])
        if isinstance(op, dict)
    ]
    required = ["op_axis_cross_product", "op_support_finite_extrema", "op_M_gap"]
    missing = sorted(set(required) - set(operation_ids))
    return {
        "existing_operation_ids": operation_ids,
        "missing_required_operation_ids": missing,
        "ready": not missing,
    }


def bridge_record(
    item: dict[str, Any],
    *,
    out_dir: Path,
    checker: Path,
    schema: Path,
    no_replay: bool,
) -> dict[str, Any]:
    report_path = report_path_from_inventory(item)
    report = read_json(report_path)
    labels = common_edge_labels(report)
    ops = required_ops_present(report)

    blocked_reasons = sorted(set(item.get("blocked_reasons_from_r34") or []))
    missing_objects = sorted(set(item.get("missing_backend_or_exact_objects") or []))
    all_blockers = sorted(set(blocked_reasons + missing_objects))

    axis_expression = (
        "n_ij = (F_i(M_CD)-F_i(M_AB)) x (F_j(M_CD)-F_j(M_AB))"
    )
    rodrigues_terms = {
        "A_term_rule": "A = u dot (w x (v-o))",
        "B_term_rule": "B = (u dot w)(w dot (v-o)) - u dot (v-o)",
        "bound_rule": "D_pos/D_neg from R35 source lock",
    }
    seed = {
        "axis_expression": axis_expression,
        "common_edge_labels": labels,
        "parent_overlay_key": report.get("predicate_data", {}).get("parent_overlay_key"),
        "rodrigues_terms": rodrigues_terms,
        "source_identity_id": R35_SOURCE_ID,
    }

    contract_fields = {
        "axis_nondegeneracy.axis_expression": field_status(
            "emitted_source_locked_symbolic_seed",
            emitted_value=axis_expression,
        ),
        "axis_nondegeneracy.common_edge_labels": field_status(
            "emitted_from_report_and_r35_universe" if labels == ["M_AB", "M_CD"] else "blocked",
            emitted_value=labels,
            blockers=[] if labels == ["M_AB", "M_CD"] else ["common_edge_labels_not_M_AB_M_CD"],
        ),
        "axis_nondegeneracy.axis_norm_lower_bound": field_status(
            "blocked_positive_interval_not_emitted",
            blockers=[
                "axis_nondegeneracy_lower_bound",
                "exact_transform_endpoint_coordinates",
                "floating_cross_product_axis_not_accepted_as_exact_branch_proof",
            ],
        ),
        "support_state.lower_support_labels": field_status(
            "blocked_support_labels_not_emitted",
            blockers=["center_support_labels", "support_stability_margins"],
        ),
        "support_state.upper_support_labels": field_status(
            "blocked_support_labels_not_emitted",
            blockers=["center_support_labels", "support_stability_margins"],
        ),
        "support_state.lower_non_support_labels": field_status(
            "blocked_support_labels_not_emitted",
            blockers=["center_support_labels", "support_stability_margins"],
        ),
        "support_state.upper_non_support_labels": field_status(
            "blocked_support_labels_not_emitted",
            blockers=["center_support_labels", "support_stability_margins"],
        ),
        "component_motion_bounds.rodrigues_terms": field_status(
            "emitted_source_locked_symbolic_seed",
            emitted_value=rodrigues_terms,
        ),
        "component_motion_bounds.lower_piece_interval_bounds": field_status(
            "blocked_interval_bounds_not_emitted",
            blockers=[
                "component_motion_bounds",
                "trig_component_bounds",
                "exact_transform_endpoint_coordinates",
            ],
        ),
        "component_motion_bounds.upper_piece_interval_bounds": field_status(
            "blocked_interval_bounds_not_emitted",
            blockers=[
                "component_motion_bounds",
                "trig_component_bounds",
                "exact_transform_endpoint_coordinates",
            ],
        ),
        "exact_gap_formula.source_identity_id": field_status(
            "emitted_source_locked_symbolic_seed",
            emitted_value=R35_SOURCE_ID,
        ),
        "exact_gap_formula.M_gap": field_status(
            "blocked_positive_interval_not_emitted",
            blockers=[
                "signed_gap_margin",
                "gap_interval_is_diagnostic_zero_placeholder",
                "no_strictly_positive_exact_gap_interval",
            ],
        ),
        "exact_gap_formula.M_L": field_status(
            "blocked_positive_interval_not_emitted",
            blockers=["support_stability_margins", "center_support_labels"],
        ),
        "exact_gap_formula.M_U": field_status(
            "blocked_positive_interval_not_emitted",
            blockers=["support_stability_margins", "center_support_labels"],
        ),
        "operation_enclosures.required_ops": field_status(
            "blocked_required_ops_not_emitted",
            emitted_value=ops["existing_operation_ids"],
            blockers=ops["missing_required_operation_ids"],
        ),
    }

    field_ready = {
        key: value["status"].startswith("emitted")
        for key, value in contract_fields.items()
    }
    checker_ready = all(field_ready.values())
    original_replay = replay_report(report_path, checker, schema, no_replay=no_replay)

    bridge = {
        "accepted_real_b05_report": False,
        "all_blockers": all_blockers,
        "blocked_reasons_from_r34": blocked_reasons,
        "bridge_id": f"B05-FORMULA-BRIDGE-{sanitize(item.get('report_id'))}",
        "bridge_status": (
            "formula_shape_contract_ready"
            if checker_ready
            else "symbolic_seed_emitted_backend_blocked"
        ),
        "case_id": CASE_ID,
        "contract_field_ready": field_ready,
        "contract_field_status": contract_fields,
        "domain_family": item.get("domain_family"),
        "formula_shape_candidate_for_schema_report": None,
        "formula_shape_candidate_reason": (
            "not_emitted_because_positive_interval_objects_are_missing"
            if not checker_ready
            else "ready_for_candidate_report_generation"
        ),
        "formula_shape_contract_ready": checker_ready,
        "formula_shape_symbolic_seed": seed,
        "missing_backend_or_exact_objects": missing_objects,
        "original_report": rel(report_path),
        "original_report_accepted": bool(report.get("accepted")),
        "original_report_id": report.get("report_id"),
        "original_replay": original_replay,
        "piece_pair": item.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "tree_id": item.get("tree_id"),
    }
    out_path = out_dir / str(item.get("domain_family")) / f"{sanitize(item.get('report_id'))}_bridge.json"
    write_json_lf(out_path, bridge)
    return {
        "accepted_real_b05_report": False,
        "bridge_record": rel(out_path),
        "bridge_status": bridge["bridge_status"],
        "contract_field_ready": field_ready,
        "domain_family": item.get("domain_family"),
        "formula_shape_contract_ready": checker_ready,
        "missing_backend_or_exact_objects": missing_objects,
        "original_report": rel(report_path),
        "original_report_id": report.get("report_id"),
        "original_replay_exit_code": original_replay["replay_exit_code"],
        "piece_pair": item.get("piece_pair"),
        "tree_id": item.get("tree_id"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r36-inventory", default=DEFAULT_R36_INVENTORY.as_posix())
    parser.add_argument("--r37-fixture-manifest", default=DEFAULT_R37_FIXTURE_MANIFEST.as_posix())
    parser.add_argument("--decision", default=DEFAULT_DECISION.as_posix())
    parser.add_argument("--derivation", default=DEFAULT_DERIVATION.as_posix())
    parser.add_argument("--schema", default=SCHEMA.as_posix())
    parser.add_argument("--replay-checker", default=REPLAY_CHECKER.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    parser.add_argument("--no-replay", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r36_path = ROOT / args.r36_inventory
    r37_path = ROOT / args.r37_fixture_manifest
    decision_path = ROOT / args.decision
    derivation_path = ROOT / args.derivation
    schema_path = ROOT / args.schema
    checker_path = ROOT / args.replay_checker
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r36 = read_json(r36_path)
    r37 = read_json(r37_path)
    source_terms = source_locked_terms_available(derivation_path, decision_path)
    items = r36.get("report_formula_inventory") or []
    if not isinstance(items, list):
        raise TypeError("R36 report_formula_inventory must be a list")

    bridges = [
        bridge_record(
            item,
            out_dir=out_dir,
            checker=checker_path,
            schema=schema_path,
            no_replay=args.no_replay,
        )
        for item in items
    ]

    bridge_status_counts = Counter(item["bridge_status"] for item in bridges)
    domain_counts = Counter(item["domain_family"] for item in bridges)
    field_ready_counts = Counter()
    field_blocked_counts = Counter()
    missing_counts = Counter(
        blocker for item in bridges for blocker in item["missing_backend_or_exact_objects"]
    )
    replay_counts = Counter(str(item["original_replay_exit_code"]) for item in bridges)
    for item in bridges:
        for field, ready in item["contract_field_ready"].items():
            if ready:
                field_ready_counts[field] += 1
            else:
                field_blocked_counts[field] += 1

    ready = [item for item in bridges if item["formula_shape_contract_ready"]]
    manifest = {
        "accepted_real_b05_report_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "bridge_record_count": len(bridges),
        "bridge_status": (
            "all_real_reports_still_backend_blocked"
            if not ready and all(source_terms.values())
            else "requires_attention"
        ),
        "bridge_status_counts": dict(sorted(bridge_status_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "contract_blocked_field_counts": dict(sorted(field_blocked_counts.items())),
        "contract_ready_field_counts": dict(sorted(field_ready_counts.items())),
        "formula_shape_contract_ready_count": len(ready),
        "input_r36_inventory": rel(r36_path),
        "input_r37_fixture_manifest": rel(r37_path),
        "manifest_id": MANIFEST_ID,
        "missing_backend_or_exact_object_counts": dict(sorted(missing_counts.items())),
        "nonclaim": NONCLAIMS,
        "original_report_replay_exit_code_counts": dict(sorted(replay_counts.items())),
        "predicate_id": PREDICATE_ID,
        "real_report_promotable_count_from_r36": r36.get("real_report_promotable_count"),
        "report_count_by_domain_family": dict(sorted(domain_counts.items())),
        "report_bridges": bridges,
        "schema_id": SCHEMA_ID,
        "source_locked_terms": source_terms,
        "synthetic_formula_shape_fixture_status": {
            "manifest": rel(r37_path),
            "replay_mismatches": r37.get("replay_mismatches"),
            "status": r37.get("status"),
        },
        "recommended_next_task": (
            "R40: implement the B05 exact axis-nondegeneracy and endpoint-transform "
            "object emitter first, because every real B05 bridge record is blocked "
            "before support/component/gap margins by missing exact axis norm and "
            "endpoint transform objects."
        ),
    }
    write_json_lf(manifest_path, manifest)

    print(f"input reports: {len(bridges)}")
    print(f"formula-shape contract ready: {len(ready)}")
    print(f"accepted real B05 reports: 0")
    print(f"bridge status counts: {dict(sorted(bridge_status_counts.items()))}")
    print(f"missing exact/backend object counts: {dict(sorted(missing_counts.items()))}")
    print(f"original replay exit code counts: {dict(sorted(replay_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")

    if not all(source_terms.values()):
        return 1
    if ready:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
