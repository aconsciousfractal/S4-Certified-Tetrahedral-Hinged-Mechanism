#!/usr/bin/env python
"""Build RW4b conservative interval/swept validation for S4 real-world branch.

RW4b promotes RW4's sampled near-contact routing into a conservative interval
ledger for the non-hinge candidate segments.  It uses the existing S4 ray-cell
clearance guard:

    center SAT overlap + endpoint-motion bound + SAT tolerance <= tolerance

A passing record is a sufficient zero-thickness non-hinge clearance certificate
for that pair/interval.  A failing record is only a blocker: it means the guard
is too weak and the segment must be routed to a richer exact, hardware-aware, or
clearance model.  This is not a finite-thickness, CAD, printability, or physical
prototype claim.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import itertools
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
RW3_PATH = RESULT_ROOT / "rw3_kinematics_adapter_manifest.json"
RW4_PATH = RESULT_ROOT / "rw4_collision_sweep_report.json"
JSON_PATH = RESULT_ROOT / "rw4b_interval_sweep_validation_report.json"
DOC_PATH = ROOT / "docs" / "S4_RW4B_INTERVAL_SWEEP_VALIDATION.md"
ROOT_PIECE = "P0"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
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


def find_tree(case: dict[str, Any], tree_id: str) -> dict[str, Any]:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"tree not found: {tree_id}")
    return tree


def signed_degrees(tree: dict[str, Any], signs_by_hinge: dict[str, int], theta_degrees: float) -> dict[str, float]:
    return {
        hinge_id: float(signs_by_hinge[hinge_id]) * float(theta_degrees)
        for hinge_id in tree["hinge_ids"]
    }


def selected_hinge_pairs(case: dict[str, Any], tree: dict[str, Any]) -> set[tuple[str, str]]:
    return {tuple(sorted(hinge["pieces"])) for hinge in batch.selected_hinges_for_tree(case, tree)}


def nonhinge_pairs(case: dict[str, Any], tree: dict[str, Any]) -> list[tuple[str, str]]:
    selected = selected_hinge_pairs(case, tree)
    return [
        tuple(sorted(pair))
        for pair in itertools.combinations(sorted(case["piece_ids"]), 2)
        if tuple(sorted(pair)) not in selected
    ]


def compact_interval(segment: dict[str, Any]) -> tuple[float, float]:
    left, right = segment["theta_interval_degrees"]
    return round(float(left), 8), round(float(right), 8)


def evaluate_pair_interval(
    case: dict[str, Any],
    tree: dict[str, Any],
    signs_by_hinge: dict[str, int],
    paths_by_piece: dict[str, list[dict]],
    contacts_by_pair: dict[tuple[str, str], dict],
    pair: tuple[str, str],
    left_degrees: float,
    right_degrees: float,
) -> dict[str, Any]:
    center_degrees = (left_degrees + right_degrees) / 2.0
    half_width_degrees = (right_degrees - left_degrees) / 2.0
    degrees_by_hinge = signed_degrees(tree, signs_by_hinge, center_degrees)
    transforms = ray_guard.transforms_for_degrees(case, tree, degrees_by_hinge)
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    displacement_bounds = ray_guard.piece_displacement_bounds(
        case,
        tree,
        transforms,
        transformed,
        half_width_degrees,
        paths_by_piece,
    )
    sample_status = lib.collision_report(transformed)["status"]
    left_piece, right_piece = pair
    best = ray_guard.best_center_separating_axis(transformed[left_piece], transformed[right_piece])
    guard_bound = displacement_bounds[left_piece] + displacement_bounds[right_piece] + ray_guard.SAT_TOLERANCE
    post_guard = best["center_axis_overlap"] + guard_bound
    certified = sample_status == "collision_free" and post_guard <= ray_guard.SAT_TOLERANCE
    role = ray_guard.pair_role(case, tree, pair, contacts_by_pair)
    if certified:
        reason = "clearance_guard_passed"
    elif sample_status != "collision_free":
        reason = "center_sample_not_collision_free"
    elif role.startswith("residual_"):
        reason = "residual_contact_or_near_contact_has_insufficient_interval_margin"
    else:
        reason = "nonhinge_pair_has_insufficient_interval_margin"
    return {
        "pair": list(pair),
        "role": role,
        "theta_interval_degrees": [round(left_degrees, 8), round(right_degrees, 8)],
        "theta_center_degrees": round(center_degrees, 8),
        "theta_half_width_degrees": round(half_width_degrees, 8),
        "center_sample_status": sample_status,
        "certified": certified,
        "center_axis_overlap": round(float(best["center_axis_overlap"]), 15),
        "guard_bound": round(float(guard_bound), 15),
        "post_guard_overlap_bound": round(float(post_guard), 15),
        "guard_margin": round(float(ray_guard.SAT_TOLERANCE - post_guard), 15),
        "left_displacement_bound": round(float(displacement_bounds[left_piece]), 15),
        "right_displacement_bound": round(float(displacement_bounds[right_piece]), 15),
        "reason": reason,
    }


def pair_key(record: dict[str, Any]) -> tuple[str, str]:
    return tuple(record["pair"])


def summarize_pair_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    for record in records:
        key = pair_key(record)
        item = by_pair.setdefault(
            key,
            {
                "pair": list(key),
                "role": record["role"],
                "pair_segment_count": 0,
                "certified_pair_segment_count": 0,
                "blocked_pair_segment_count": 0,
                "minimum_guard_margin": None,
                "maximum_post_guard_overlap_bound": None,
                "first_blocked_interval": None,
            },
        )
        item["pair_segment_count"] += 1
        if record["certified"]:
            item["certified_pair_segment_count"] += 1
        else:
            item["blocked_pair_segment_count"] += 1
            if item["first_blocked_interval"] is None:
                item["first_blocked_interval"] = record["theta_interval_degrees"]
        margin = float(record["guard_margin"])
        post_guard = float(record["post_guard_overlap_bound"])
        if item["minimum_guard_margin"] is None or margin < item["minimum_guard_margin"]:
            item["minimum_guard_margin"] = margin
        if item["maximum_post_guard_overlap_bound"] is None or post_guard > item["maximum_post_guard_overlap_bound"]:
            item["maximum_post_guard_overlap_bound"] = post_guard
    return sorted(by_pair.values(), key=lambda item: (item["pair"][0], item["pair"][1]))


def audit_tree(case: dict[str, Any], rw4_tree: dict[str, Any]) -> dict[str, Any]:
    tree = find_tree(case, rw4_tree["tree_id"])
    signs = {hinge_id: int(sign) for hinge_id, sign in rw4_tree["sign_vector_by_hinge"].items()}
    if set(signs) != set(tree["hinge_ids"]):
        raise RuntimeError(f"sign vector does not match tree hinges: {tree['tree_id']}")
    candidate_segments = rw4_tree["tier2_nonhinge_candidate_segments"]
    expected_count = int(rw4_tree["tier2_nonhinge_candidate_segment_count"])
    if len(candidate_segments) != expected_count:
        raise RuntimeError(
            f"RW4 candidate ledger is truncated for {tree['tree_id']}: "
            f"stored={len(candidate_segments)} expected={expected_count}. Re-run RW4 after removing segment preview truncation."
        )

    paths_by_piece = ray_guard.tree_paths_from_root(case, tree, root_piece=ROOT_PIECE)
    contacts_by_pair = ray_guard.contact_by_pair(case)
    pairs = nonhinge_pairs(case, tree)

    segment_records = []
    pair_records = []
    for segment_index, segment in enumerate(candidate_segments):
        left, right = compact_interval(segment)
        records = [
            evaluate_pair_interval(case, tree, signs, paths_by_piece, contacts_by_pair, pair, left, right)
            for pair in pairs
        ]
        pair_records.extend({"segment_index": segment_index, **record} for record in records)
        certified = all(record["certified"] for record in records)
        blocker_reasons = Counter(record["reason"] for record in records if not record["certified"])
        segment_records.append(
            {
                "segment_index": segment_index,
                "theta_interval_degrees": [left, right],
                "certified_all_nonhinge_pairs": certified,
                "certified_pair_count": sum(1 for record in records if record["certified"]),
                "blocked_pair_count": sum(1 for record in records if not record["certified"]),
                "blocker_reasons": dict(sorted(blocker_reasons.items())),
            }
        )

    blocked_pair_records = [record for record in pair_records if not record["certified"]]
    blocker_reason_counts = Counter(record["reason"] for record in blocked_pair_records)
    blocked_segments = [record for record in segment_records if not record["certified_all_nonhinge_pairs"]]
    certified_segments = [record for record in segment_records if record["certified_all_nonhinge_pairs"]]
    pair_summary = summarize_pair_records(pair_records)
    return {
        "tree_id": tree["tree_id"],
        "hinge_ids": list(tree["hinge_ids"]),
        "sign_vector_by_hinge": signs,
        "nonhinge_pairs_audited": [list(pair) for pair in pairs],
        "candidate_segment_count": len(candidate_segments),
        "pair_segment_count": len(pair_records),
        "certified_pair_segment_count": sum(1 for record in pair_records if record["certified"]),
        "blocked_pair_segment_count": len(blocked_pair_records),
        "certified_segment_count": len(certified_segments),
        "blocked_segment_count": len(blocked_segments),
        "all_candidate_segments_certified_for_nonhinge_pairs": not blocked_segments,
        "blocker_reason_counts": dict(sorted(blocker_reason_counts.items())),
        "minimum_guard_margin": min(float(record["guard_margin"]) for record in pair_records),
        "maximum_post_guard_overlap_bound": max(float(record["post_guard_overlap_bound"]) for record in pair_records),
        "pair_summary": pair_summary,
        "segment_records": segment_records,
        "blocked_pair_records": sorted(
            blocked_pair_records,
            key=lambda record: (record["tree_id"] if "tree_id" in record else "", record["segment_index"], record["pair"]),
        ),
    }


def build_doc(report: dict[str, Any]) -> str:
    tree_rows = []
    pair_rows = []
    blocker_rows = []
    for tree in report["trees"]:
        tree_rows.append(
            [
                tree["tree_id"],
                tree["candidate_segment_count"],
                tree["pair_segment_count"],
                tree["certified_pair_segment_count"],
                tree["blocked_pair_segment_count"],
                tree["certified_segment_count"],
                tree["blocked_segment_count"],
                tree["minimum_guard_margin"],
            ]
        )
        for pair in tree["pair_summary"]:
            pair_rows.append(
                [
                    tree["tree_id"],
                    "-".join(pair["pair"]),
                    pair["role"],
                    pair["pair_segment_count"],
                    pair["certified_pair_segment_count"],
                    pair["blocked_pair_segment_count"],
                    pair["first_blocked_interval"],
                ]
            )
        for record in tree["blocked_pair_records"][:20]:
            blocker_rows.append(
                [
                    tree["tree_id"],
                    record["segment_index"],
                    record["theta_interval_degrees"],
                    "-".join(record["pair"]),
                    record["role"],
                    record["guard_margin"],
                    record["reason"],
                ]
            )

    acceptance_rows = [[key, value] for key, value in report["acceptance"].items()]
    return "\n".join(
        [
            "# S4 RW4b Interval/Swept Validation",
            "",
            "Status: conservative interval guard routing for RW4 non-hinge near-contact segments.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW4b audits the complete RW4 non-hinge tier-2 candidate segment ledger.",
            "Each pair/segment is tested with the existing center-sample SAT axis plus",
            "a conservative displacement bound over the theta interval.",
            "",
            "A pass is a sufficient zero-thickness interval clearance certificate for",
            "that non-hinge pair.  A fail is only a routed blocker: the current guard is",
            "too weak for that interval and must be handled by RW4c or a richer hardware",
            "clearance model.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW3 kinematics", rel(RW3_PATH)],
                    ["RW4 sampled candidate ledger", rel(RW4_PATH)],
                    ["interval guard implementation", "scripts/audit_historical_s4_two_class_ray_cell_guard.py"],
                ],
            ),
            "",
            "## Guard Model",
            "",
            table(
                ["Parameter", "Value"],
                [
                    ["SAT tolerance", ray_guard.SAT_TOLERANCE],
                    ["displacement safety factor", ray_guard.DISPLACEMENT_SAFETY_FACTOR],
                    ["certification inequality", "center_axis_overlap + motion_bound + tolerance <= tolerance"],
                    ["audited scope", "non-hinge pairs only on RW4 non-hinge tier-2 intervals"],
                ],
            ),
            "",
            "## Tree Summary",
            "",
            table(
                [
                    "Tree",
                    "Candidate segments",
                    "Pair-segments",
                    "Certified pair-segments",
                    "Blocked pair-segments",
                    "Certified segments",
                    "Blocked segments",
                    "Min guard margin",
                ],
                tree_rows,
            ),
            "",
            "## Pair Summary",
            "",
            table(
                ["Tree", "Pair", "Role", "Pair-segments", "Certified", "Blocked", "First blocked interval"],
                pair_rows,
            ),
            "",
            "## First Blockers",
            "",
            table(
                ["Tree", "Segment", "Theta interval", "Pair", "Role", "Guard margin", "Reason"],
                blocker_rows or [["none", "", "", "", "", "", ""]],
            ),
            "",
            "## Explicit Nonclaims",
            "",
            "- finite-thickness clearance",
            "- continuous collision-free sweep for all geometry",
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
    if not RW3_PATH.exists():
        raise RuntimeError(f"missing RW3 manifest: {RW3_PATH}")
    if not RW4_PATH.exists():
        raise RuntimeError(f"missing RW4 report: {RW4_PATH}")
    rw3 = load_json(RW3_PATH)
    rw4 = load_json(RW4_PATH)
    case = batch.build_case()

    tree_reports = [audit_tree(case, rw4_tree) for rw4_tree in rw4["trees"]]
    total_candidate_segments = sum(tree["candidate_segment_count"] for tree in tree_reports)
    total_pair_segments = sum(tree["pair_segment_count"] for tree in tree_reports)
    total_certified_pair_segments = sum(tree["certified_pair_segment_count"] for tree in tree_reports)
    total_blocked_pair_segments = sum(tree["blocked_pair_segment_count"] for tree in tree_reports)
    total_certified_segments = sum(tree["certified_segment_count"] for tree in tree_reports)
    total_blocked_segments = sum(tree["blocked_segment_count"] for tree in tree_reports)
    blocker_reasons = Counter()
    for tree in tree_reports:
        blocker_reasons.update(tree["blocker_reason_counts"])

    fully_certified = total_blocked_pair_segments == 0
    report = {
        "report_id": "S4-RW4B-INTERVAL-SWEEP-VALIDATION-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": (
            "conservative_interval_nonhinge_clearance_certified_not_hardware_ready"
            if fully_certified
            else "conservative_interval_guard_routing_completed_not_full_clearance_certified"
        ),
        "precondition": {
            "rw3_manifest": rel(RW3_PATH),
            "rw3_status": rw3.get("status"),
            "rw4_report": rel(RW4_PATH),
            "rw4_status": rw4.get("status"),
        },
        "scope": {
            "evidence_tier": "tier_2_conservative_interval_guard_for_rw4_nonhinge_candidates",
            "collision_model": "zero_thickness_exact_tetrahedral_body_solids",
            "guard_model": "center_sat_axis_plus_piece_displacement_bounds",
            "finite_thickness_clearance_status": "not_certified",
            "selected_hinge_hardware_clearance_status": "not_run",
            "printability_validation_status": "not_run",
        },
        "summary": {
            "tree_count": len(tree_reports),
            "total_candidate_segment_count": total_candidate_segments,
            "total_pair_segment_count": total_pair_segments,
            "total_certified_pair_segment_count": total_certified_pair_segments,
            "total_blocked_pair_segment_count": total_blocked_pair_segments,
            "total_certified_segment_count": total_certified_segments,
            "total_blocked_segment_count": total_blocked_segments,
            "all_nonhinge_candidate_segments_interval_certified": fully_certified,
            "blocker_reason_counts": dict(sorted(blocker_reasons.items())),
        },
        "trees": tree_reports,
        "acceptance": {
            "rw3_manifest_present": RW3_PATH.exists(),
            "rw4_report_present": RW4_PATH.exists(),
            "rw4_candidate_ledgers_complete": all(
                len(tree["tier2_nonhinge_candidate_segments"]) == tree["tier2_nonhinge_candidate_segment_count"]
                for tree in rw4["trees"]
            ),
            "tree_count_is_2": len(tree_reports) == 2,
            "candidate_segment_count_matches_rw4": total_candidate_segments == rw4["summary"]["total_nonhinge_tier2_candidate_segment_count"],
            "interval_pair_records_written": total_pair_segments > 0,
            "conservative_guard_pass_records_count": total_certified_pair_segments,
            "conservative_guard_blocker_records_count": total_blocked_pair_segments,
            "full_nonhinge_interval_clearance_certified": fully_certified,
            "report_says_not_finite_thickness_or_hardware_ready": True,
        },
        "next_task": (
            "RW4c targeted blocker reduction for the uncertified non-hinge interval records, then selected-hinge hardware/clearance modelling before RW5."
            if not fully_certified
            else "RW4c selected-hinge hardware/clearance modelling before RW5 printability/fabrication gates."
        ),
    }

    write_json(JSON_PATH, report)
    DOC_PATH.write_text(build_doc(report), encoding="utf-8", newline="\n")
    print(json.dumps({"status": report["status"], "report": rel(JSON_PATH), "summary": rel(DOC_PATH), "totals": report["summary"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
