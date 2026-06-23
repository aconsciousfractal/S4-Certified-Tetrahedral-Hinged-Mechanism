#!/usr/bin/env python
"""Build RW4c targeted blocker reduction for S4 real-world branch.

RW4c consumes RW4b's 89 interval-guard blockers and separates them into two
routes:

* residual_shared_edge blockers: run bounded adaptive subdivision with the same
  zero-thickness center-SAT plus displacement guard, so non-problematic parts of
  the coarse interval are certified and only near-zero micro-intervals remain;
* residual_shared_face blockers: classify as structural clearance/model blockers
  instead of subdividing.  The RW4b guard fails because the residual contact is a
  face-class contact manifold, so this route needs a physical clearance/relief
  model rather than more generic sampling.

This is still a routing/certification artifact only.  It is not physical
hingeability, finite-thickness clearance, CAD validity, printability,
fabrication readiness, or prototype validation.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW4B_PATH = RESULT_ROOT / "rw4b_interval_sweep_validation_report.json"
JSON_PATH = RESULT_ROOT / "rw4c_blocker_reduction_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4C_BLOCKER_REDUCTION.md"
ROOT_PIECE = "P0"
MAX_EDGE_ADAPTIVE_DEPTH = 8
MAX_STORED_EXAMPLES = 24

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import build_s4_real_world_rw4b_interval_sweep_validation as rw4b  # noqa: E402
import mechanical_audit_lib as lib  # noqa: E402


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lib.json_ready(payload), indent=2) + "\n", encoding="utf-8", newline="\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def compact_source_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "segment_index": record["segment_index"],
        "theta_interval_degrees": record["theta_interval_degrees"],
        "pair": record["pair"],
        "role": record["role"],
        "guard_margin": record["guard_margin"],
        "post_guard_overlap_bound": record["post_guard_overlap_bound"],
        "reason": record["reason"],
    }


def merge_intervals(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[tuple[str, str], list[list[float]]] = defaultdict(list)
    for record in records:
        by_pair[tuple(record["pair"])].append([float(record["theta_interval_degrees"][0]), float(record["theta_interval_degrees"][1])])

    merged = []
    for pair, intervals in sorted(by_pair.items()):
        intervals = sorted(intervals)
        bands = []
        for left, right in intervals:
            if not bands or abs(left - bands[-1][1]) > 1.0e-10:
                bands.append([left, right])
            else:
                bands[-1][1] = max(bands[-1][1], right)
        for band in bands:
            merged.append(
                {
                    "pair": list(pair),
                    "theta_band_degrees": [round(band[0], 12), round(band[1], 12)],
                    "width_degrees": round(band[1] - band[0], 12),
                    "source_interval_count": sum(
                        1
                        for left, right in intervals
                        if left >= band[0] - 1.0e-10 and right <= band[1] + 1.0e-10
                    ),
                }
            )
    return merged


def adaptive_edge_reduction(
    case: dict[str, Any],
    tree: dict[str, Any],
    signs: dict[str, int],
    paths_by_piece: dict[str, list[dict]],
    contacts_by_pair: dict[tuple[str, str], dict],
    source_record: dict[str, Any],
) -> dict[str, Any]:
    pair = tuple(source_record["pair"])
    stack = [(float(source_record["theta_interval_degrees"][0]), float(source_record["theta_interval_degrees"][1]), 0)]
    certified_children = []
    residual_children = []
    visited_child_count = 0

    while stack:
        left, right, depth = stack.pop()
        visited_child_count += 1
        evaluation = rw4b.evaluate_pair_interval(case, tree, signs, paths_by_piece, contacts_by_pair, pair, left, right)
        if evaluation["certified"]:
            certified_children.append(evaluation)
            continue
        if depth >= MAX_EDGE_ADAPTIVE_DEPTH:
            residual_children.append(evaluation)
            continue
        center = (left + right) / 2.0
        stack.append((center, right, depth + 1))
        stack.append((left, center, depth + 1))

    residual_widths = [child["theta_interval_degrees"][1] - child["theta_interval_degrees"][0] for child in residual_children]
    certified_width = sum(child["theta_interval_degrees"][1] - child["theta_interval_degrees"][0] for child in certified_children)
    residual_width = sum(residual_widths)
    return {
        "source": compact_source_record(source_record),
        "adaptive_depth": MAX_EDGE_ADAPTIVE_DEPTH,
        "visited_child_interval_count": visited_child_count,
        "certified_child_interval_count": len(certified_children),
        "residual_child_interval_count": len(residual_children),
        "source_interval_resolved": len(residual_children) == 0,
        "certified_width_degrees": round(certified_width, 12),
        "residual_width_degrees": round(residual_width, 12),
        "max_residual_width_degrees": round(max(residual_widths), 12) if residual_widths else 0.0,
        "residual_micro_intervals": [
            {
                "theta_interval_degrees": child["theta_interval_degrees"],
                "guard_margin": child["guard_margin"],
                "post_guard_overlap_bound": child["post_guard_overlap_bound"],
            }
            for child in residual_children
        ],
        "first_certified_children": [
            {
                "theta_interval_degrees": child["theta_interval_degrees"],
                "guard_margin": child["guard_margin"],
            }
            for child in certified_children[:MAX_STORED_EXAMPLES]
        ],
    }


def audit_tree(case: dict[str, Any], tree_report: dict[str, Any]) -> dict[str, Any]:
    tree = rw4b.find_tree(case, tree_report["tree_id"])
    signs = {hinge_id: int(sign) for hinge_id, sign in tree_report["sign_vector_by_hinge"].items()}
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree, root_piece=ROOT_PIECE)
    contacts_by_pair = ray_guard.contact_by_pair(case)

    blocked = tree_report["blocked_pair_records"]
    edge_blockers = [record for record in blocked if record["role"] == "residual_shared_edge"]
    face_blockers = [record for record in blocked if record["role"] == "residual_shared_face"]
    other_blockers = [record for record in blocked if record["role"] not in {"residual_shared_edge", "residual_shared_face"}]

    edge_records = [adaptive_edge_reduction(case, tree, signs, paths_by_piece, contacts_by_pair, record) for record in edge_blockers]
    edge_resolved = [record for record in edge_records if record["source_interval_resolved"]]
    edge_unresolved = [record for record in edge_records if not record["source_interval_resolved"]]
    edge_residual_micro_count = sum(record["residual_child_interval_count"] for record in edge_records)
    edge_certified_child_count = sum(record["certified_child_interval_count"] for record in edge_records)
    edge_residual_widths = [
        micro["theta_interval_degrees"][1] - micro["theta_interval_degrees"][0]
        for record in edge_records
        for micro in record["residual_micro_intervals"]
    ]

    return {
        "tree_id": tree_report["tree_id"],
        "input_blocker_pair_record_count": len(blocked),
        "residual_shared_face_blocker_count": len(face_blockers),
        "residual_shared_edge_blocker_count": len(edge_blockers),
        "other_blocker_count": len(other_blockers),
        "edge_source_records_resolved_count": len(edge_resolved),
        "edge_source_records_with_residual_micro_intervals_count": len(edge_unresolved),
        "edge_certified_child_interval_count": edge_certified_child_count,
        "edge_residual_micro_interval_count": edge_residual_micro_count,
        "edge_max_residual_micro_interval_width_degrees": round(max(edge_residual_widths), 12) if edge_residual_widths else 0.0,
        "remaining_original_blocker_record_count": len(face_blockers) + len(edge_unresolved) + len(other_blockers),
        "face_clearance_bands": merge_intervals(face_blockers),
        "edge_adaptive_records": edge_records,
        "face_blocker_records": [compact_source_record(record) for record in face_blockers],
        "other_blocker_records": [compact_source_record(record) for record in other_blockers],
    }


def build_doc(report: dict[str, Any]) -> str:
    tree_rows = []
    face_rows = []
    edge_rows = []
    for tree in report["trees"]:
        tree_rows.append(
            [
                tree["tree_id"],
                tree["input_blocker_pair_record_count"],
                tree["residual_shared_face_blocker_count"],
                tree["residual_shared_edge_blocker_count"],
                tree["edge_source_records_resolved_count"],
                tree["edge_residual_micro_interval_count"],
                tree["remaining_original_blocker_record_count"],
            ]
        )
        for band in tree["face_clearance_bands"]:
            face_rows.append([tree["tree_id"], "-".join(band["pair"]), band["theta_band_degrees"], band["source_interval_count"]])
        for record in tree["edge_adaptive_records"]:
            edge_rows.append(
                [
                    tree["tree_id"],
                    "-".join(record["source"]["pair"]),
                    record["source"]["theta_interval_degrees"],
                    record["source_interval_resolved"],
                    record["certified_child_interval_count"],
                    record["residual_child_interval_count"],
                    record["max_residual_width_degrees"],
                ]
            )

    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4c Blocker Reduction",
            "",
            "Status: targeted blocker reduction and routing after RW4b.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4c consumes RW4b's interval-guard blockers.  It adaptively subdivides",
            "only `residual_shared_edge` blockers and routes `residual_shared_face`",
            "blockers to the physical clearance/relief model instead of more generic",
            "sampling.",
            "",
            "## Source",
            "",
            table([["Source", "Path"]][0], [["RW4b interval ledger", rel(RW4B_PATH)]]),
            "",
            "## Summary",
            "",
            table(
                ["Metric", "Value"],
                [[key, value] for key, value in report["summary"].items()],
            ),
            "",
            "## Tree Summary",
            "",
            table(
                ["Tree", "Input blockers", "Face blockers", "Edge blockers", "Edge source records resolved", "Edge residual micro-intervals", "Remaining original blockers"],
                tree_rows,
            ),
            "",
            "## Shared-Face Clearance Bands",
            "",
            table(["Tree", "Pair", "Theta band", "Source intervals"], face_rows),
            "",
            "## Shared-Edge Adaptive Reduction",
            "",
            table(["Tree", "Pair", "Source interval", "Resolved", "Certified children", "Residual micro-intervals", "Max residual width"], edge_rows),
            "",
            "## Interpretation",
            "",
            "The edge blockers are mostly reduced to certified children plus a few",
            "near-zero micro-intervals.  The face blockers remain structural clearance",
            "blockers: they are residual face-class contacts in the zero-thickness source",
            "model, so the next step must introduce explicit clearance/relief or hardware",
            "geometry before any printability/fabrication gate.",
            "",
            "## Explicit Nonclaims",
            "",
            "- physical hingeability",
            "- finite-thickness clearance",
            "- selected-hinge hardware clearance",
            "- CAD validity",
            "- printability",
            "- fabrication readiness",
            "- prototype validation",
            "",
            "## Acceptance",
            "",
            table(["Check", "Value"], acceptance_rows),
            "",
            "## Next Task",
            "",
            report["next_task"],
            "",
        ]
    )


def main() -> int:
    if not RW4B_PATH.exists():
        raise RuntimeError(f"missing RW4b report: {RW4B_PATH}")
    rw4b_report = load_json(RW4B_PATH)
    case = batch.build_case()
    tree_reports = [audit_tree(case, tree) for tree in rw4b_report["trees"]]

    total_input = sum(tree["input_blocker_pair_record_count"] for tree in tree_reports)
    total_face = sum(tree["residual_shared_face_blocker_count"] for tree in tree_reports)
    total_edge = sum(tree["residual_shared_edge_blocker_count"] for tree in tree_reports)
    total_other = sum(tree["other_blocker_count"] for tree in tree_reports)
    total_edge_resolved = sum(tree["edge_source_records_resolved_count"] for tree in tree_reports)
    total_edge_unresolved = sum(tree["edge_source_records_with_residual_micro_intervals_count"] for tree in tree_reports)
    total_edge_certified_children = sum(tree["edge_certified_child_interval_count"] for tree in tree_reports)
    total_edge_residual_micro = sum(tree["edge_residual_micro_interval_count"] for tree in tree_reports)
    total_remaining_original = sum(tree["remaining_original_blocker_record_count"] for tree in tree_reports)
    max_edge_width = max((tree["edge_max_residual_micro_interval_width_degrees"] for tree in tree_reports), default=0.0)

    report = {
        "report_id": "S4-RW4C-BLOCKER-REDUCTION-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "targeted_blocker_reduction_completed_clearance_model_required",
        "precondition": {
            "rw4b_report": rel(RW4B_PATH),
            "rw4b_status": rw4b_report.get("status"),
        },
        "scope": {
            "input": "RW4b blocked non-hinge interval pair records",
            "edge_route": "adaptive zero-thickness interval subdivision",
            "face_route": "structural clearance/relief model required",
            "edge_adaptive_depth": MAX_EDGE_ADAPTIVE_DEPTH,
            "edge_micro_interval_width_degrees": round(0.25 / (2 ** MAX_EDGE_ADAPTIVE_DEPTH), 12),
            "finite_thickness_clearance_status": "not_certified",
            "hardware_geometry_status": "not_modelled",
            "printability_validation_status": "not_run",
        },
        "summary": {
            "input_blocker_pair_record_count": total_input,
            "residual_shared_face_blocker_count": total_face,
            "residual_shared_edge_blocker_count": total_edge,
            "other_blocker_count": total_other,
            "edge_source_records_resolved_count": total_edge_resolved,
            "edge_source_records_with_residual_micro_intervals_count": total_edge_unresolved,
            "edge_certified_child_interval_count": total_edge_certified_children,
            "edge_residual_micro_interval_count": total_edge_residual_micro,
            "edge_max_residual_micro_interval_width_degrees": max_edge_width,
            "remaining_original_blocker_record_count": total_remaining_original,
            "clearance_model_required": True,
        },
        "trees": tree_reports,
        "acceptance": {
            "rw4b_report_present": RW4B_PATH.exists(),
            "rw4b_blocker_count_matched": total_input == rw4b_report["summary"]["total_blocked_pair_segment_count"],
            "all_blockers_routed": total_input == total_face + total_edge + total_other,
            "shared_edge_blockers_adaptively_processed": total_edge > 0 and total_edge == total_edge_resolved + total_edge_unresolved,
            "shared_face_blockers_classified_as_clearance_model_required": total_face > 0,
            "other_blocker_count_zero": total_other == 0,
            "report_says_no_finite_thickness_or_hardware_claim": True,
        },
        "next_task": "RW4d clearance/relief and selected-hinge hardware model for the shared-face bands and near-zero shared-edge micro-intervals before RW5.",
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "report": rel(JSON_PATH), "summary": rel(DOC_PATH), "totals": report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
