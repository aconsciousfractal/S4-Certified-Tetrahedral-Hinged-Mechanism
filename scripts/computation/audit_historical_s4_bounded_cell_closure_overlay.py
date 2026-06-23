"""Bounded-cell closure overlay for S4 representative trees.

This report reconciles the original bounded-cell first-pass ledger with all
later residual bounded-cell closure reports:

- first-pass clearance/orientation guard;
- shared-edge closure stacks;
- shared-face face-normal formula guard;
- shared-face edge-branch G1/G2/G3/G4 guards.

It is an overlay report only. It does not add a new local guard; it verifies
that existing finite ledgers cover the original 1536 all-free cells and 9216
pair-cells from the bounded-cell first-pass target.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_closure_overlay_report.json"
MAX_STORED_EXAMPLES = 48

SOURCE_REPORTS = {
    "first_pass": "bounded_cell_guard_first_pass_report.json",
    "shared_edge_direct": "bounded_cell_shared_edge_common_edge_overlay_report.json",
    "tree021_p1p2_margin": "bounded_cell_tree021_p1p2_margin_endgame_guard_report.json",
    "tree021_p0p3_closure": "bounded_cell_tree021_p0p3_closure_stack_report.json",
    "tree007_shared_edge_closure": "bounded_cell_tree007_shared_edge_closure_stack_report.json",
    "shared_face_inventory": "bounded_cell_residual_shared_face_inventory_report.json",
    "face_normal": "bounded_cell_face_normal_formula_guard_report.json",
    "g1": "bounded_cell_edge_branch_g1_fixed_axis_guard_report.json",
    "g2": "bounded_cell_edge_branch_g2_multi_axis_guard_report.json",
    "g3": "bounded_cell_edge_branch_g3_hybrid_guard_report.json",
    "g4": "bounded_cell_edge_branch_g4_adaptive_isolation_guard_report.json",
}

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def load_json(name: str) -> dict:
    with (RESULTS_DIR / name).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def pair_key(pair: list[str] | tuple[str, str]) -> str:
    return "-".join(pair)


def coverage_key(tree_id: str, pair: list[str] | tuple[str, str], cell_id: str) -> str:
    return f"{tree_id}|{pair_key(pair)}|{cell_id}"


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def reconstruct_first_pass_pair_cells() -> dict:
    case = first_pass.batch.build_case()
    component_report = first_pass.load_json(RESULTS_DIR / first_pass.SOURCE_COMPONENT_REPORT)
    source_by_tree = {
        audit["tree_id"]: audit
        for audit in component_report["representative_audits"]
    }
    signs_by_tree = first_pass.comp.certified_signs_by_tree()
    contacts_by_pair = first_pass.ray_guard.contact_by_pair(case)
    all_cells = first_pass.protocol.iter_cells()

    pair_records = []
    cells_by_tree = Counter()
    pair_count_by_tree = Counter()
    center_status_counts = Counter()
    cell_pair_keys = defaultdict(list)

    for tree_id in first_pass.TARGET_TREE_IDS:
        tree = first_pass.comp.find_tree(case, tree_id)
        signs = signs_by_tree[tree_id]
        paths_by_piece = first_pass.ray_guard.tree_paths_from_root(case, tree)
        hinge_by_pair = first_pass.selected_hinge_by_pair(case, tree)
        free_cells = first_pass.all_free_cells_for_tree(source_by_tree[tree_id], all_cells)
        cells_by_tree[tree_id] = len(free_cells)
        for cell in free_cells:
            audited = first_pass.audit_cell(
                case,
                tree,
                signs,
                cell,
                paths_by_piece,
                contacts_by_pair,
                hinge_by_pair,
            )
            center_status_counts[audited["center_sample_status"]] += 1
            cell_key = f"{tree_id}|{cell['cell_id']}"
            for record in audited["pair_records"]:
                key = coverage_key(tree_id, record["pair"], cell["cell_id"])
                compact = {
                    "key": key,
                    "tree_id": tree_id,
                    "cell_id": cell["cell_id"],
                    "pair": record["pair"],
                    "role": record["role"],
                    "first_pass_covered": bool(record["first_pass_covered"]),
                    "first_pass_method": record["coverage_method"],
                    "fallback_classes": record["fallback_classes"],
                    "guard_margin": round(float(record["guard_margin"]), 12),
                }
                pair_records.append(compact)
                cell_pair_keys[cell_key].append(key)
                pair_count_by_tree[tree_id] += 1

    return {
        "pair_records": pair_records,
        "cells_by_tree": dict(cells_by_tree),
        "pair_count_by_tree": dict(pair_count_by_tree),
        "center_status_counts": dict(center_status_counts),
        "cell_pair_keys": dict(cell_pair_keys),
    }


def certified_face_normal_keys(report: dict) -> dict[str, str]:
    output = {}
    for target in report["target_reports"]:
        tree_id = target["target"]["tree_id"]
        pair = target["target"]["pair"]
        for cell in target["cell_reports"]:
            if not cell["formula_certified"]:
                continue
            output[coverage_key(tree_id, pair, cell["cell_id"])] = "shared_face_face_normal_formula_guard"
    return output


def certified_edge_branch_route_keys(report: dict, route_name: str) -> dict[str, str]:
    output = {}
    for target in report["target_reports"]:
        tree_id = target["target"]["tree_id"]
        pair = target["target"]["pair"]
        for cell in target["cell_reports"]:
            if not cell["cell_certified"]:
                continue
            output[coverage_key(tree_id, pair, cell["cell_id"])] = route_name
    return output


def first_pass_uncovered_keys(records: list[dict], role: str | None = None) -> set[str]:
    return {
        record["key"]
        for record in records
        if not record["first_pass_covered"] and (role is None or record["role"] == role)
    }


def assert_count(label: str, actual: int, expected: int) -> None:
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected}, found {actual}")


def shared_edge_coverage(first_pass_records: list[dict], reports: dict[str, dict]) -> dict[str, str]:
    output = {}

    def cover_all(tree_id: str, pair: tuple[str, str], method: str, expected_count: int, failed_count: int) -> None:
        if failed_count != 0:
            raise AssertionError(f"{method} still has {failed_count} failed base pair-cells")
        keys = {
            record["key"]
            for record in first_pass_records
            if record["tree_id"] == tree_id
            and tuple(record["pair"]) == pair
            and record["role"] == "residual_shared_edge"
            and not record["first_pass_covered"]
        }
        assert_count(f"{method} key count", len(keys), expected_count)
        for key in keys:
            output[key] = method

    tree021_p1p2 = reports["tree021_p1p2_margin"]["summary_metrics"]
    cover_all(
        "TREE_021",
        ("P1", "P2"),
        "shared_edge_tree021_p1p2_margin_endgame_guard",
        int(tree021_p1p2["fully_covered_base_pair_cell_count_after_margin_guard"]),
        int(tree021_p1p2["zero_certified_base_pair_cell_count_after_margin_guard"]),
    )

    tree021_p0p3 = reports["tree021_p0p3_closure"]["summary_metrics"]
    cover_all(
        "TREE_021",
        ("P0", "P3"),
        "shared_edge_tree021_p0p3_closure_stack",
        int(tree021_p0p3["fully_covered_base_pair_cell_count_after_closure"]),
        int(tree021_p0p3["failed_base_pair_cell_count_after_closure"]),
    )

    tree007 = reports["tree007_shared_edge_closure"]
    for pair_report in tree007["pair_reports"]:
        pair = tuple(pair_report["target"]["pair"])
        metrics = pair_report["summary_metrics"]
        cover_all(
            "TREE_007",
            pair,
            f"shared_edge_tree007_{pair_key(pair).lower().replace('-', '')}_closure_stack",
            int(metrics["fully_covered_base_pair_cell_count_after_closure"]),
            int(metrics["failed_base_pair_cell_count_after_closure"]),
        )

    expected_total = int(reports["shared_edge_direct"]["summary_metrics"]["total_input_uncovered_shared_edge_pair_cell_count"])
    assert_count("shared-edge coverage total", len(output), expected_total)
    return output


def build_fallback_coverage(first_pass_records: list[dict], reports: dict[str, dict]) -> dict[str, str]:
    coverage = {}
    for key, method in shared_edge_coverage(first_pass_records, reports).items():
        coverage[key] = method
    for key, method in certified_face_normal_keys(reports["face_normal"]).items():
        if key in coverage:
            raise AssertionError(f"Duplicate fallback key: {key}")
        coverage[key] = method
    for report_key, route_name in [
        ("g1", "edge_branch_g1_fixed_axis_guard"),
        ("g2", "edge_branch_g2_multi_axis_guard"),
        ("g3", "edge_branch_g3_hybrid_guard"),
        ("g4", "edge_branch_g4_adaptive_isolation_guard"),
    ]:
        for key, method in certified_edge_branch_route_keys(reports[report_key], route_name).items():
            if key in coverage:
                raise AssertionError(f"Duplicate fallback key: {key}")
            coverage[key] = method
    return coverage


def summarize_overlay(records: list[dict], fallback_coverage: dict[str, str], cell_pair_keys: dict[str, list[str]]) -> dict:
    coverage_source_counts = Counter()
    role_counts = Counter()
    role_covered_counts = Counter()
    pair_counts = Counter()
    pair_covered_counts = Counter()
    tree_counts = Counter()
    tree_covered_counts = Counter()
    first_pass_method_counts = Counter()
    fallback_method_counts = Counter()
    uncovered = []
    examples = defaultdict(list)

    for record in records:
        tree_id = record["tree_id"]
        pair = pair_key(record["pair"])
        role = record["role"]
        tree_counts[tree_id] += 1
        role_counts[role] += 1
        pair_counts[f"{tree_id}:{pair}"] += 1

        if record["first_pass_covered"]:
            method = f"first_pass:{record['first_pass_method']}"
            covered = True
            first_pass_method_counts[record["first_pass_method"]] += 1
        elif record["key"] in fallback_coverage:
            method = fallback_coverage[record["key"]]
            covered = True
            fallback_method_counts[method] += 1
        else:
            method = "uncovered"
            covered = False
            uncovered.append(record)

        coverage_source_counts[method] += 1
        add_example(examples[method], record)
        if covered:
            tree_covered_counts[tree_id] += 1
            role_covered_counts[role] += 1
            pair_covered_counts[f"{tree_id}:{pair}"] += 1

    covered_keys = {
        record["key"]
        for record in records
        if record["first_pass_covered"] or record["key"] in fallback_coverage
    }
    fully_covered_cells = 0
    uncovered_cells = []
    for cell_key, keys in cell_pair_keys.items():
        if all(key in covered_keys for key in keys):
            fully_covered_cells += 1
        else:
            uncovered_cells.append(cell_key)

    pair_summaries = []
    for key in sorted(pair_counts):
        pair_summaries.append(
            {
                "tree_pair": key,
                "pair_cell_count": pair_counts[key],
                "covered_pair_cell_count": pair_covered_counts[key],
                "uncovered_pair_cell_count": pair_counts[key] - pair_covered_counts[key],
            }
        )

    return {
        "coverage_source_counts": dict(coverage_source_counts.most_common()),
        "first_pass_method_counts": dict(first_pass_method_counts.most_common()),
        "fallback_method_counts": dict(fallback_method_counts.most_common()),
        "role_counts": dict(role_counts.most_common()),
        "role_covered_counts": dict(role_covered_counts.most_common()),
        "tree_pair_summaries": pair_summaries,
        "tree_pair_cell_counts": dict(tree_counts.most_common()),
        "tree_covered_pair_cell_counts": dict(tree_covered_counts.most_common()),
        "fully_covered_cell_count": fully_covered_cells,
        "uncovered_cell_count": len(uncovered_cells),
        "uncovered_cells": uncovered_cells[:MAX_STORED_EXAMPLES],
        "uncovered_pair_cells": uncovered[:MAX_STORED_EXAMPLES],
        "examples": {key: value for key, value in examples.items()},
    }


def build_report() -> dict:
    reports = {name: load_json(filename) for name, filename in SOURCE_REPORTS.items()}
    first_pass_reconstructed = reconstruct_first_pass_pair_cells()
    first_pass_records = first_pass_reconstructed["pair_records"]
    fallback = build_fallback_coverage(first_pass_records, reports)
    overlay = summarize_overlay(first_pass_records, fallback, first_pass_reconstructed["cell_pair_keys"])

    first_pass_summary = reports["first_pass"]["summary_metrics"]
    total_pair_cells = len(first_pass_records)
    first_pass_covered = sum(1 for record in first_pass_records if record["first_pass_covered"])
    fallback_covered = len(fallback)
    final_covered = first_pass_covered + fallback_covered
    assert_count("first-pass reconstructed pair-cell count", total_pair_cells, int(first_pass_summary["total_pair_cell_count"]))
    assert_count("first-pass reconstructed covered pair-cell count", first_pass_covered, int(first_pass_summary["total_first_pass_covered_pair_cell_count"]))
    assert_count("fallback coverage count", fallback_covered, int(first_pass_summary["total_first_pass_uncovered_pair_cell_count"]))
    assert_count("final coverage count", final_covered, total_pair_cells)

    edge_branch_total = sum(
        int(reports[key]["summary_metrics"][metric])
        for key, metric in [
            ("g1", "g1_certified_cell_count"),
            ("g2", "g2_certified_cell_count"),
            ("g3", "g3_certified_cell_count"),
            ("g4", "g4_certified_cell_count"),
        ]
    )
    edge_branch_subcells = sum(
        int(reports[key]["summary_metrics"]["certified_subcell_count"])
        for key in ["g1", "g2", "g3", "g4"]
    )

    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_closure_overlay_completed",
        "source_reports": [
            f"results/{CASE_ID}/{filename}"
            for filename in SOURCE_REPORTS.values()
        ],
        "target": {
            "tree_ids": list(first_pass.TARGET_TREE_IDS),
            "description": "overlay reconciliation for original all-free bounded cells and pair-cells",
            "cell_count": int(first_pass_summary["total_candidate_cell_count"]),
            "pair_cell_count": int(first_pass_summary["total_pair_cell_count"]),
        },
        "summary_metrics": {
            "tree_count": len(first_pass.TARGET_TREE_IDS),
            "candidate_cell_count": int(first_pass_summary["total_candidate_cell_count"]),
            "center_sample_collision_free_cell_count": int(first_pass_summary["total_center_sample_collision_free_cell_count"]),
            "original_pair_cell_count": total_pair_cells,
            "first_pass_covered_pair_cell_count": first_pass_covered,
            "fallback_covered_pair_cell_count": fallback_covered,
            "final_covered_pair_cell_count": final_covered,
            "final_uncovered_pair_cell_count": total_pair_cells - final_covered,
            "final_fully_covered_cell_count": overlay["fully_covered_cell_count"],
            "final_uncovered_cell_count": overlay["uncovered_cell_count"],
            "bounded_cell_overlay_closed": final_covered == total_pair_cells and overlay["uncovered_cell_count"] == 0,
            "shared_edge_fallback_covered_pair_cell_count": int(reports["shared_edge_direct"]["summary_metrics"]["total_input_uncovered_shared_edge_pair_cell_count"]),
            "shared_face_face_normal_covered_pair_cell_count": int(reports["face_normal"]["summary_metrics"]["formula_certified_cell_count"]),
            "shared_face_edge_branch_covered_pair_cell_count": edge_branch_total,
            "shared_face_edge_branch_certified_subcell_count": edge_branch_subcells,
            "edge_branch_route_counts": {
                "G1": int(reports["g1"]["summary_metrics"]["g1_certified_cell_count"]),
                "G2": int(reports["g2"]["summary_metrics"]["g2_certified_cell_count"]),
                "G3": int(reports["g3"]["summary_metrics"]["g3_certified_cell_count"]),
                "G4": int(reports["g4"]["summary_metrics"]["g4_certified_cell_count"]),
            },
        },
        "breakdown": {
            "reconstructed_first_pass_cells_by_tree": first_pass_reconstructed["cells_by_tree"],
            "reconstructed_first_pass_pair_cells_by_tree": first_pass_reconstructed["pair_count_by_tree"],
            "reconstructed_center_status_counts": first_pass_reconstructed["center_status_counts"],
            **{
                key: value
                for key, value in overlay.items()
                if key not in {"examples", "uncovered_pair_cells", "uncovered_cells"}
            },
        },
        "examples": overlay["examples"],
        "uncovered_pair_cells": overlay["uncovered_pair_cells"],
        "uncovered_cells": overlay["uncovered_cells"],
        "limitations": [
            "This report is an overlay reconciliation of existing finite ledgers; it does not add a new local inequality or symbolic derivation.",
            "The overlay covers only the all-free bounded cells from the bounded-cell first-pass target.",
            "The domain starts at theta=0.5 degrees and does not cover theta=0.",
            "This does not certify dynamic connectedness between representatives, physical hinge thickness, offsets, CAD, mesh export, or printability.",
        ],
    }


def main() -> int:
    report = build_report()
    lib.write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "summary_metrics": report["summary_metrics"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
