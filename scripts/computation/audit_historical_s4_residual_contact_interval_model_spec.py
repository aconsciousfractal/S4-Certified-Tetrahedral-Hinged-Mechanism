"""Residual-contact interval model specification for TREE_021 failures.

This script converts the residual-contact failure classification into a concrete
model plan. It is not a proof script: it records which interval models are now
well-posed by the classification data and in which order they should be built.
"""

from __future__ import annotations

import json
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "residual_contact_interval_model_spec_report.json"
CLASSIFICATION_REPORT = "residual_contact_failure_classification_report.json"

SCRIPT_PATH = Path(__file__).resolve()
RESULTS_DIR = SCRIPT_PATH.parents[1] / "results" / CASE_ID


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def pair_key(pair: list[str]) -> str:
    return "-".join(pair)


def model_for_pair(pair_report: dict) -> dict:
    key = pair_key(pair_report["pair"])
    role = pair_report["role"]
    uncovered = pair_report["uncovered_pair_segment_count"]
    uncovered_axes = pair_report["uncovered_axis_name_counts"]
    if key == "P0-P2" and role == "residual_shared_face":
        edge_edge = sum(count for axis, count in uncovered_axes.items() if axis.startswith("edge:"))
        face_normal = sum(count for axis, count in uncovered_axes.items() if "_face:" in axis)
        return {
            "pair": pair_report["pair"],
            "role": role,
            "priority": 1,
            "model_id": "TREE021_P0_P2_BRANCH_AWARE_SHARED_FACE_INTERVAL_MODEL",
            "model_status": "required_next",
            "uncovered_pair_segment_count": uncovered,
            "dominant_uncovered_axis_families": {
                "edge_edge_branches": edge_edge,
                "face_normal_branches": face_normal,
                "raw_axis_counts": uncovered_axes,
            },
            "local_geometry_summary": {
                "uncovered_source_edge_kind_counts": pair_report["uncovered_source_edge_kind_counts"],
                "uncovered_source_theta_pair_counts": pair_report["uncovered_source_theta_pair_counts"],
                "uncovered_source_radius_pair_counts": pair_report["uncovered_source_radius_pair_counts"],
                "guard_margin_interval": pair_report["guard_margin_interval"],
                "center_angle_intervals_by_hinge": pair_report["center_angle_intervals_by_hinge"],
            },
            "model_requirements": [
                "Track four observed midpoint separator branches instead of assuming the ray-line cubic branch remains active off-ray.",
                "For each branch, derive a signed gap expression or a rigorous lower-bound surrogate over a refined segment box in hinge-angle coordinates.",
                "Use branch coverage to decide whether segments can be certified directly or require further subdivision.",
            ],
        }
    if role == "residual_shared_edge":
        stable_common_edge = uncovered_axes == {"edge:M_AB-M_CD x M_AB-M_CD": uncovered}
        return {
            "pair": pair_report["pair"],
            "role": role,
            "priority": 2,
            "model_id": f"TREE021_{key.replace('-', '_')}_COMMON_EDGE_INTERVAL_MODEL",
            "model_status": "candidate_after_shared_face_gate",
            "uncovered_pair_segment_count": uncovered,
            "dominant_uncovered_axis_families": {
                "common_edge_axis_stable_on_uncovered_segments": stable_common_edge,
                "raw_axis_counts": uncovered_axes,
            },
            "local_geometry_summary": {
                "uncovered_source_edge_kind_counts": pair_report["uncovered_source_edge_kind_counts"],
                "uncovered_source_theta_pair_counts": pair_report["uncovered_source_theta_pair_counts"],
                "uncovered_source_radius_pair_counts": pair_report["uncovered_source_radius_pair_counts"],
                "guard_margin_interval": pair_report["guard_margin_interval"],
                "center_angle_intervals_by_hinge": pair_report["center_angle_intervals_by_hinge"],
            },
            "model_requirements": [
                "Use the stable common-edge separator edge:M_AB-M_CD x M_AB-M_CD observed on every uncovered segment for this pair.",
                "Generalize the ray-line shared-edge normalized-gap model to an interval lower bound over a 3-coordinate segment box.",
                "Apply after P0-P2 shared-face branches, because every failed segment pattern includes P0-P2 in the current probe.",
            ],
        }
    return {
        "pair": pair_report["pair"],
        "role": role,
        "priority": 99,
        "model_id": f"UNCLASSIFIED_{key}",
        "model_status": "unclassified",
        "uncovered_pair_segment_count": uncovered,
        "dominant_uncovered_axis_families": {"raw_axis_counts": uncovered_axes},
    }


def build_report() -> dict:
    classification = load_json(RESULTS_DIR / CLASSIFICATION_REPORT)
    pair_models = [model_for_pair(pair_report) for pair_report in classification["pair_reports"]]
    pair_models = sorted(pair_models, key=lambda item: (item["priority"], item["pair"]))
    p0p2_is_gate = all(
        pattern == "none" or pattern.startswith("P0-P2")
        for pattern in classification["failure_pattern_counts"]
    )
    return {
        "case_id": CASE_ID,
        "status": "residual_contact_interval_model_spec_completed",
        "source_reports": [
            f"results/{CASE_ID}/{CLASSIFICATION_REPORT}",
            f"results/{CASE_ID}/refined_edge_interval_guard_probe_report.json",
        ],
        "target_tree_id": classification["target_tree_id"],
        "summary_metrics": {
            "residual_pair_count": len(pair_models),
            "total_uncovered_pair_segment_count": classification["summary_metrics"]["total_residual_uncovered_pair_segment_count"],
            "p0_p2_shared_face_is_gate_for_all_failed_patterns": p0p2_is_gate,
            "p0_p2_uncovered_pair_segment_count": next(item["uncovered_pair_segment_count"] for item in pair_models if item["pair"] == ["P0", "P2"]),
            "residual_shared_edge_uncovered_pair_segment_count": sum(item["uncovered_pair_segment_count"] for item in pair_models if item["role"] == "residual_shared_edge"),
        },
        "failure_pattern_counts": classification["failure_pattern_counts"],
        "model_sequence": [
            "Build branch-aware interval lower bounds for TREE_021 P0-P2 residual shared-face branches.",
            "Re-run the refined-edge interval guard with the P0-P2 model overlay.",
            "Apply common-edge interval lower bounds to TREE_021 P0-P3 and P1-P2 residual shared-edge failures.",
            "Only after TREE_021 closes, mirror the protocol to TREE_007.",
        ],
        "pair_models": pair_models,
        "claim_boundary": [
            "This report specifies the residual-contact interval models to build; it does not certify the failed segments.",
            "The P0-P2 model must be branch-aware because midpoint separators split between edge-edge and face-normal branches off-ray.",
            "The shared-edge models are better posed because every uncovered shared-edge segment uses the same common-edge separator.",
        ],
    }


def main() -> int:
    report = build_report()
    write_json(RESULTS_DIR / REPORT_NAME, report)
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_file": str(RESULTS_DIR / REPORT_NAME),
                "status": report["status"],
                "summary_metrics": report["summary_metrics"],
                "model_sequence": report["model_sequence"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())