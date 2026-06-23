"""TREE_007 P2-P3 local-best-axis component diagnostic.

This diagnostic records why the existing P0-P2 targeted endgame guard should not
be blindly replayed for the TREE_007 P2-P3 residual shared-face backlog. It tests
that guard family on the 1064 P2-P3 residual pair-segments and on one tactical
0.625-degree subdivision level.
"""

from __future__ import annotations

from collections import Counter
import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "tree007_p2p3_local_best_axis_component_diagnostic_report.json"
TARGET_TREE_ID = "TREE_007"
TARGET_PAIR = ("P2", "P3")
TACTICAL_REFINEMENT_DELTA_DEGREES = 0.625
SAT_TOLERANCE = 1.0e-8
MAX_STORED_EXAMPLES = 24

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_refined_edge_interval_guard_probe as probe  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402
import audit_historical_s4_p0p2_edge_branch_lower_bound_probe as branch_probe  # noqa: E402
import audit_historical_s4_p0p2_refinement_sensitivity_probe as sensitivity  # noqa: E402
import audit_historical_s4_p0p2_targeted_endgame_guard as endgame  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def compact_child(child: dict) -> dict:
    return {
        "segment_id": child["segment_id"],
        "refined_segment_index": child["refined_segment_index"],
        "source_node_ids": child["source_node_ids"],
        "source_t_interval": child["source_t_interval"],
        "old_best_axis_name": child["old_best_axis_name"],
        "old_guard_margin": child["old_guard_margin"],
    }


def p2p3_residual_children(case: dict, tree: dict, labels_by_piece: dict, paths_by_piece: dict, signs_by_tree: dict[str, dict[str, int]]) -> list[dict]:
    component_report = probe.load_json(RESULTS_DIR / "two_class_component_search_report.json")
    source_audit = next(audit for audit in component_report["representative_audits"] if audit["tree_id"] == TARGET_TREE_ID)
    _tree, segments = probe.refined_segments_for_tree(case, source_audit, signs_by_tree)
    children = []
    for segment in segments:
        center = (segment["left_vector"] + segment["right_vector"]) / 2.0
        center_degrees = probe.degrees_from_vector(tree, center)
        left_degrees = probe.degrees_from_vector(tree, segment["left_vector"])
        right_degrees = probe.degrees_from_vector(tree, segment["right_vector"])
        delta_by_hinge = {hinge_id: right_degrees[hinge_id] - left_degrees[hinge_id] for hinge_id in tree["hinge_ids"]}
        transforms = ray_guard.transforms_for_degrees(case, tree, center_degrees)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        displacement_bounds = probe.piece_displacement_bounds_for_segment(case, tree, transforms, transformed, delta_by_hinge, paths_by_piece)
        best = classify.best_named_axis(transformed[TARGET_PAIR[0]], transformed[TARGET_PAIR[1]], labels_by_piece[TARGET_PAIR[0]], labels_by_piece[TARGET_PAIR[1]])
        guard_bound = displacement_bounds[TARGET_PAIR[0]] + displacement_bounds[TARGET_PAIR[1]] + SAT_TOLERANCE
        post_guard = best["center_axis_overlap"] + guard_bound
        if post_guard <= SAT_TOLERANCE:
            continue
        children.append(
            {
                "segment_id": f"seg_{segment['refined_segment_index']:05d}",
                "refined_segment_index": segment["refined_segment_index"],
                "source_node_ids": segment["source_node_ids"],
                "source_t_interval": segment["source_t_interval"],
                "left_vector": segment["left_vector"],
                "right_vector": segment["right_vector"],
                "old_best_axis_name": best["axis_name"],
                "old_guard_margin": round(SAT_TOLERANCE - post_guard, 12),
            }
        )
    return children


def evaluate_children(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, children: list[dict]) -> tuple[dict, list[dict]]:
    counts = Counter()
    failed = []
    examples = []
    original_target_pair = endgame.TARGET_PAIR
    try:
        endgame.TARGET_PAIR = TARGET_PAIR
        for child in children:
            guard = endgame.local_best_axis_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, child["left_vector"], child["right_vector"])
            key = "certified" if guard["certified"] else f"failed:{guard['failure_reason']}"
            counts[key] += 1
            if not guard["certified"]:
                failed.append(child)
                if len(examples) < MAX_STORED_EXAMPLES:
                    examples.append({**compact_child(child), "local_best_axis": guard.get("best_axis_name"), "failure_reason": guard.get("failure_reason")})
    finally:
        endgame.TARGET_PAIR = original_target_pair
    return {"result_counts": dict(counts.most_common()), "stored_failed_examples": examples}, failed


def evaluate_tactical_refinement(case: dict, tree: dict, indices: dict, labels_by_piece: dict, paths_by_piece: dict, children: list[dict]) -> dict:
    leaf_counts = Counter()
    child_outcomes = Counter()
    leaf_total = 0
    examples = []
    original_target_pair = endgame.TARGET_PAIR
    try:
        endgame.TARGET_PAIR = TARGET_PAIR
        for child in children:
            child_total = 0
            child_certified = 0
            for leaf_index, (left, right) in enumerate(sensitivity.subdivide_vector_segment(child["left_vector"], child["right_vector"], TACTICAL_REFINEMENT_DELTA_DEGREES)):
                child_total += 1
                leaf_total += 1
                guard = endgame.local_best_axis_component_guard(case, tree, indices, labels_by_piece, paths_by_piece, left, right)
                if guard["certified"]:
                    child_certified += 1
                    leaf_counts["certified"] += 1
                else:
                    key = f"failed:{guard['failure_reason']}"
                    leaf_counts[key] += 1
                    if len(examples) < MAX_STORED_EXAMPLES:
                        examples.append({**compact_child(child), "leaf_index": leaf_index, "local_best_axis": guard.get("best_axis_name"), "failure_reason": guard.get("failure_reason")})
            if child_certified == child_total:
                child_outcomes["fully_covered"] += 1
            elif child_certified == 0:
                child_outcomes["zero_leaf_covered"] += 1
            else:
                child_outcomes["partially_covered"] += 1
    finally:
        endgame.TARGET_PAIR = original_target_pair
    return {
        "threshold_degrees": TACTICAL_REFINEMENT_DELTA_DEGREES,
        "input_child_count": len(children),
        "leaf_subsegment_count": leaf_total,
        "leaf_result_counts": dict(leaf_counts.most_common()),
        "child_outcome_counts": dict(child_outcomes.most_common()),
        "stored_failed_leaf_examples": examples,
    }


def build_report() -> dict:
    case = batch.build_case()
    tree = comp.find_tree(case, TARGET_TREE_ID)
    signs_by_tree = comp.certified_signs_by_tree()
    labels_by_piece = classify.labels_by_piece(case)
    indices = branch_probe.label_indices(case)
    paths_by_piece = ray_guard.tree_paths_from_root(case, tree)
    children = p2p3_residual_children(case, tree, labels_by_piece, paths_by_piece, signs_by_tree)
    direct, failed = evaluate_children(case, tree, indices, labels_by_piece, paths_by_piece, children)
    tactical = evaluate_tactical_refinement(case, tree, indices, labels_by_piece, paths_by_piece, failed)
    return {
        "case_id": CASE_ID,
        "status": "tree007_p2p3_local_best_axis_component_diagnostic_completed",
        "source_reports": [
            f"results/{CASE_ID}/tree007_residual_contact_failure_classification_report.json",
            f"results/{CASE_ID}/tree007_refined_edge_interval_guard_probe_report.json",
        ],
        "target": {
            "tree_id": TARGET_TREE_ID,
            "pair": list(TARGET_PAIR),
            "role": "residual_shared_face",
        },
        "summary_metrics": {
            "input_p2p3_residual_pair_segment_count": len(children),
            "direct_local_best_certified_count": direct["result_counts"].get("certified", 0),
            "direct_local_best_failed_count": len(failed),
            "tactical_refinement_threshold_degrees": TACTICAL_REFINEMENT_DELTA_DEGREES,
            "tactical_leaf_subsegment_count": tactical["leaf_subsegment_count"],
            "tactical_certified_leaf_subsegment_count": tactical["leaf_result_counts"].get("certified", 0),
            "tactical_uncovered_leaf_subsegment_count": tactical["leaf_subsegment_count"] - tactical["leaf_result_counts"].get("certified", 0),
            "local_best_axis_component_family_rejected_for_p2p3": direct["result_counts"].get("failed:not_separated_at_center", 0) == len(children)
            and tactical["leaf_result_counts"].get("failed:not_separated_at_center", 0) == tactical["leaf_subsegment_count"],
        },
        "direct_local_best_axis_component_report": direct,
        "tactical_refinement_report": tactical,
        "limitations": [
            "This is a negative diagnostic for one guard family, not a certificate for P2-P3.",
            "Only the original P2-P3 residual pair-segments and one 0.625-degree tactical subdivision level are tested.",
            "The result indicates that the next P2-P3 guard should use a dedicated shared-face branch/formula workflow.",
        ],
    }


def main() -> int:
    report = build_report()
    lib.write_json(RESULTS_DIR / REPORT_NAME, report)
    print(json.dumps({"case_id": CASE_ID, "results_file": str(RESULTS_DIR / REPORT_NAME), "status": report["status"], "summary_metrics": report["summary_metrics"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())