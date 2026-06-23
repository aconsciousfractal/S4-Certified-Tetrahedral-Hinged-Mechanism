#!/usr/bin/env python
"""
Build the S4 CL5 residual-route exact source-layer split.

R32 consumes the R31 B03 source-layer manifest.  R31 proved that the current
11 B03-shaped diagnostics are not route-clean B03 strict-clearance targets:
they are residual shared-edge/shared-face candidates.  This script routes those
records to the correct exact-report families and source ledgers:

* B05 common-edge projection for residual shared-edge candidates;
* B06/B07 shared-face split for residual shared-face candidates.

This is still a source inventory, not an accepted exact report generator.  It
keeps accepted/report-ready counts at zero until a route-specific schema-v1
report exists and replays through the locked checker.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
SCHEMA_ID = "S4-CL5-EXACT-INTERVAL-REPORT-SCHEMA-v1"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_LAYER_ID = "S4-CL5-RESIDUAL-ROUTE-EXACT-SOURCE-LAYER-2026-06-22"

DEFAULT_R31_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b03_strict_convex_sat/"
    "manifests/b03_strict_convex_sat_exact_margin_source_layer_manifest.json"
)
DEFAULT_OUT = Path(
    "results/historical_s4_median_planes/exact_interval/residual_routes/"
    "manifests/residual_route_exact_source_layer_manifest.json"
)

RESULTS_ROOT = Path("results/historical_s4_median_planes")

B05_DOCS = [
    "docs/S4_CL5_COMMON_EDGE_PROJECTION_EXACT_REPORT_IMPLEMENTATION_PLAN.md",
    "docs/S4_CL5_COMMON_EDGE_PROJECTION_SOUNDNESS_REVIEW.md",
]
B06_DOCS = [
    "docs/S4_CL5_FACE_NORMAL_SUPPORT_GAP_EXACT_REPORT_IMPLEMENTATION_PLAN.md",
    "docs/S4_CL5_FACE_NORMAL_SUPPORT_GAP_SOUNDNESS_REVIEW.md",
]
B07_DOCS = [
    "docs/S4_CL5_EDGE_BRANCH_SUPPORT_COMPONENT_EXACT_REPORT_IMPLEMENTATION_PLAN.md",
    "docs/S4_CL5_EDGE_BRANCH_SUPPORT_COMPONENT_SOUNDNESS_REVIEW.md",
]

B05_PAIR_SOURCES = {
    ("TREE_007", "P0-P3"): [
        "tree007_shared_edge_common_edge_guard_report.json",
        "bounded_cell_shared_edge_common_edge_overlay_report.json",
        "bounded_cell_tree007_shared_edge_closure_stack_report.json",
    ],
    ("TREE_007", "P1-P2"): [
        "tree007_shared_edge_common_edge_guard_report.json",
        "bounded_cell_shared_edge_common_edge_overlay_report.json",
        "bounded_cell_tree007_shared_edge_closure_stack_report.json",
    ],
    ("TREE_021", "P0-P3"): [
        "tree021_shared_edge_common_edge_guard_report.json",
        "bounded_cell_shared_edge_common_edge_overlay_report.json",
        "bounded_cell_tree021_p0p3_closure_stack_report.json",
    ],
    ("TREE_021", "P1-P2"): [
        "tree021_shared_edge_common_edge_guard_report.json",
        "bounded_cell_shared_edge_common_edge_overlay_report.json",
        "bounded_cell_tree021_p1p2_margin_endgame_guard_report.json",
    ],
}

B06_PAIR_SOURCES = {
    ("TREE_007", "P2-P3"): [
        "tree007_p2p3_face_normal_formula_guard_report.json",
        "bounded_cell_residual_shared_face_inventory_report.json",
        "bounded_cell_face_normal_formula_guard_report.json",
    ],
    ("TREE_021", "P0-P2"): [
        "p0p2_face_normal_formula_guard_report.json",
        "bounded_cell_residual_shared_face_inventory_report.json",
        "bounded_cell_face_normal_formula_guard_report.json",
    ],
}

B07_PAIR_SOURCES = {
    ("TREE_007", "P2-P3"): [
        "bounded_cell_residual_shared_face_inventory_report.json",
        "bounded_cell_edge_branch_guard_plan_report.json",
        "bounded_cell_edge_branch_g1_fixed_axis_guard_report.json",
        "bounded_cell_edge_branch_g2_multi_axis_guard_report.json",
        "bounded_cell_edge_branch_g3_hybrid_guard_report.json",
        "bounded_cell_edge_branch_g4_adaptive_isolation_guard_report.json",
    ],
    ("TREE_021", "P0-P2"): [
        "bounded_cell_residual_shared_face_inventory_report.json",
        "bounded_cell_edge_branch_guard_plan_report.json",
        "bounded_cell_edge_branch_g1_fixed_axis_guard_report.json",
        "bounded_cell_edge_branch_g2_multi_axis_guard_report.json",
        "bounded_cell_edge_branch_g3_hybrid_guard_report.json",
        "bounded_cell_edge_branch_g4_adaptive_isolation_guard_report.json",
    ],
}


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def result_path(name: str) -> Path:
    return ROOT / RESULTS_ROOT / name


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


def compact_summary(summary: Any) -> dict[str, Any]:
    if not isinstance(summary, dict):
        return {}
    # Keep the route inventory useful without copying large nested reports.
    out: dict[str, Any] = {}
    for key, value in summary.items():
        if isinstance(value, (str, int, float, bool)) or value is None:
            out[key] = value
        elif isinstance(value, dict) and all(isinstance(v, (str, int, float, bool)) for v in value.values()):
            out[key] = value
    return out


def source_record(name: str) -> dict[str, Any]:
    path = result_path(name)
    if not path.exists():
        return {
            "exists": False,
            "path": rel(path),
            "status": "missing",
            "summary_metrics": {},
        }
    data = read_json(path)
    return {
        "exists": True,
        "path": rel(path),
        "status": data.get("status"),
        "summary_metrics": compact_summary(data.get("summary_metrics") or data.get("summary")),
    }


def domain_family_from_report_path(report_path: str) -> str:
    parent = Path(report_path).parent.name
    if parent in {"ray_nonhinge", "bounded_firstpass"}:
        return parent
    return "unknown"


def b05_route(decision: dict[str, Any]) -> dict[str, Any]:
    tree = decision["tree_id"]
    pair = decision["piece_pair"]
    source_names = B05_PAIR_SOURCES.get((tree, pair), [])
    sources = [source_record(name) for name in source_names]
    return {
        "candidate_exact_report_ready": False,
        "candidate_route": "B05_COMMON_EDGE_PROJECTION_SOUNDNESS",
        "domain_family": domain_family_from_report_path(decision["report"]),
        "missing_source_count": sum(not item["exists"] for item in sources),
        "piece_pair": pair,
        "required_docs": B05_DOCS,
        "route_status": "source_ledgers_available_but_no_schema_v1_b05_report_yet",
        "source_blockers": [
            "no_route_specific_schema_v1_b05_report",
            "finite_or_formula_ledger_not_replayed_as_fraction_interval_or_symbolic_sign_report",
            "accepted_true_must_remain_false_until_b05_replay_exists",
        ],
        "source_ledgers": sources,
        "source_report": decision["report"],
        "source_report_id": decision["report_id"],
        "tree_id": tree,
    }


def shared_face_route(decision: dict[str, Any]) -> dict[str, Any]:
    tree = decision["tree_id"]
    pair = decision["piece_pair"]
    b06_sources = [source_record(name) for name in B06_PAIR_SOURCES.get((tree, pair), [])]
    b07_sources = [source_record(name) for name in B07_PAIR_SOURCES.get((tree, pair), [])]
    return {
        "candidate_exact_report_ready": False,
        "candidate_route": "B06_B07_SHARED_FACE_SPLIT_REQUIRED",
        "domain_family": domain_family_from_report_path(decision["report"]),
        "missing_source_count": sum(not item["exists"] for item in b06_sources + b07_sources),
        "piece_pair": pair,
        "required_docs": B06_DOCS + B07_DOCS,
        "route_status": "source_ledgers_available_but_report_level_aggregate_must_split_to_b06_and_b07",
        "source_blockers": [
            "no_route_specific_schema_v1_b06_or_b07_report",
            "report_level_shared_face_aggregate_not_split_into_face_normal_and_edge_branch_subdomains",
            "finite_or_formula_ledger_not_replayed_as_fraction_interval_or_symbolic_sign_report",
            "accepted_true_must_remain_false_until_b06_b07_replay_exists",
        ],
        "source_ledgers_b06": b06_sources,
        "source_ledgers_b07": b07_sources,
        "source_report": decision["report"],
        "source_report_id": decision["report_id"],
        "tree_id": tree,
    }


def route_decision(decision: dict[str, Any]) -> dict[str, Any]:
    targets = decision.get("primary_route_targets") or []
    if "B05_common_edge_projection" in targets:
        return b05_route(decision)
    if "B06_or_B07_shared_face_split_required" in targets:
        return shared_face_route(decision)
    return {
        "candidate_exact_report_ready": False,
        "candidate_route": "UNROUTED",
        "missing_source_count": 0,
        "piece_pair": decision.get("piece_pair"),
        "route_status": "no_residual_route_target_found",
        "source_blockers": ["r31_decision_has_no_b05_b06_b07_target"],
        "source_report": decision.get("report"),
        "source_report_id": decision.get("report_id"),
        "tree_id": decision.get("tree_id"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r31-manifest", default=DEFAULT_R31_MANIFEST.as_posix())
    parser.add_argument("--out", default=DEFAULT_OUT.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r31_path = ROOT / args.r31_manifest
    out_path = ROOT / args.out
    r31 = read_json(r31_path)
    decisions = r31.get("source_decisions") or []
    if not isinstance(decisions, list):
        raise TypeError("R31 manifest source_decisions must be a list")

    routes = [route_decision(item) for item in decisions]
    route_counts = Counter(item["candidate_route"] for item in routes)
    status_counts = Counter(item["route_status"] for item in routes)
    blocker_counts = Counter(blocker for item in routes for blocker in item.get("source_blockers", []))
    missing_source_count = sum(item.get("missing_source_count", 0) for item in routes)
    exact_ready_count = sum(1 for item in routes if item.get("candidate_exact_report_ready"))

    output = {
        "accepted_true_count": 0,
        "backend_lock_id": BACKEND_LOCK_ID,
        "case_id": CASE_ID,
        "candidate_exact_report_ready_count": exact_ready_count,
        "input_r31_manifest": rel(r31_path),
        "input_r31_report_count": len(decisions),
        "manifest_id": SOURCE_LAYER_ID,
        "missing_source_ledger_count": missing_source_count,
        "nonclaim": [
            "no_b05_b06_b07_accepted_true_report_claim",
            "no_exact_residual_margin_claim",
            "no_finite_or_formula_ledger_as_schema_v1_replay_claim",
            "no_theorem_wrapper_promotion_claim",
            "no_physical_hingeability_claim",
        ],
        "predicate_route_families": [
            "B05_COMMON_EDGE_PROJECTION_SOUNDNESS",
            "B06_FACE_NORMAL_SUPPORT_GAP_SOUNDNESS",
            "B07_EDGE_BRANCH_SUPPORT_COMPONENT_SOUNDNESS",
        ],
        "recommended_next_task": (
            "R33: implement a B05 common-edge projection diagnostic exact-report writer first, because R32 routes "
            "7 of the 11 residual candidates to B05 and all required B05 source ledgers are present."
        ),
        "residual_route_records": routes,
        "route_counts": dict(sorted(route_counts.items())),
        "route_source_layer_status": (
            "all_r31_residual_candidates_have_source_ledgers_but_no_route_specific_schema_v1_reports"
            if missing_source_count == 0 and exact_ready_count == 0
            else "residual_source_layer_requires_attention"
        ),
        "schema_id": SCHEMA_ID,
        "source_blocker_counts": dict(sorted(blocker_counts.items())),
        "source_status_counts": dict(sorted(status_counts.items())),
    }
    write_json_lf(out_path, output)

    print(f"input R31 records: {len(decisions)}")
    print(f"route counts: {dict(sorted(route_counts.items()))}")
    print(f"missing source ledgers: {missing_source_count}")
    print(f"candidate exact-ready reports: {exact_ready_count}")
    print(f"manifest: {rel(out_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
