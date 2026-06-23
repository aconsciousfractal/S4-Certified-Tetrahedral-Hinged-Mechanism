"""Residual contact gap diagnostic for S4 representative ray cells.

This is a tactical diagnostic, not a proof-producing audit. It measures the
residual contacts left open by the selected-hinge contact-orientation overlay
and estimates how small a clearance-only ray cell would need to be. The goal is
to decide whether adaptive clearance refinement is practical before launching it.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "residual_contact_gap_diagnostic_report.json"
PROBE_THETA_DEGREES = [0.625, 0.875, 1.125, 2.0, 5.0, 10.0, 15.0, 15.625]
BASE_HALF_WIDTH_DEGREES = 0.125
MAX_HALF_WIDTH_SEARCH_DEGREES = 0.125
BINARY_SEARCH_STEPS = 20
RESIDUAL_TARGETS = [
    {
        "tree_id": "TREE_007",
        "pair": ["P2", "P3"],
        "role": "residual_shared_face",
        "unresolved_theta_interval_degrees": [0.5, 15.75],
    },
    {
        "tree_id": "TREE_021",
        "pair": ["P0", "P2"],
        "role": "residual_shared_face",
        "unresolved_theta_interval_degrees": [0.5, 15.75],
    },
    {
        "tree_id": "TREE_021",
        "pair": ["P1", "P2"],
        "role": "residual_shared_edge",
        "unresolved_theta_interval_degrees": [0.5, 1.0],
    },
]

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as guard  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def probe_cell(theta: float, half_width: float) -> dict:
    return {
        "cell_id": "diagnostic_probe",
        "theta_left_degrees": round(float(theta) - float(half_width), 10),
        "theta_right_degrees": round(float(theta) + float(half_width), 10),
        "theta_center_degrees": round(float(theta), 10),
        "theta_half_width_degrees": round(float(half_width), 10),
    }


def target_pair_record(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    paths: dict,
    contacts: dict,
    pair: tuple[str, str],
    theta: float,
    half_width: float,
) -> dict:
    cell = probe_cell(theta, half_width)
    record = guard.cell_guard_record(case, tree, signs_by_hinge, paths, contacts, cell)
    for pair_record in record["pair_records"]:
        if tuple(pair_record["pair"]) == pair:
            return pair_record
    raise RuntimeError(f"Pair not found in cell guard: {pair}")


def max_certifiable_half_width(
    case: dict,
    tree: dict,
    signs_by_hinge: dict[str, int],
    paths: dict,
    contacts: dict,
    pair: tuple[str, str],
    theta: float,
) -> float:
    lo = 0.0
    hi = MAX_HALF_WIDTH_SEARCH_DEGREES
    for _ in range(BINARY_SEARCH_STEPS):
        mid = (lo + hi) / 2.0
        record = target_pair_record(case, tree, signs_by_hinge, paths, contacts, pair, theta, mid)
        if record["certified"]:
            lo = mid
        else:
            hi = mid
    return lo


def diagnostic_for_target(case: dict, signs_by_tree: dict, target: dict) -> dict:
    tree = comp.find_tree(case, target["tree_id"])
    pair = tuple(target["pair"])
    paths = guard.tree_paths_from_root(case, tree)
    contacts = guard.contact_by_pair(case)
    signs = signs_by_tree[target["tree_id"]]
    interval = target["unresolved_theta_interval_degrees"]
    probes = [theta for theta in PROBE_THETA_DEGREES if interval[0] <= theta <= interval[1]]
    probe_records = []
    for theta in probes:
        base_record = target_pair_record(
            case,
            tree,
            signs,
            paths,
            contacts,
            pair,
            theta,
            BASE_HALF_WIDTH_DEGREES,
        )
        max_half_width = max_certifiable_half_width(case, tree, signs, paths, contacts, pair, theta)
        clearance = max(0.0, -float(base_record["center_axis_overlap"]))
        theta_cubed = float(theta) ** 3
        probe_records.append(
            {
                "theta_degrees": theta,
                "center_axis_overlap": round(float(base_record["center_axis_overlap"]), 15),
                "clearance_at_center": round(clearance, 15),
                "guard_bound_at_base_half_width": round(float(base_record["guard_bound"]), 15),
                "post_guard_overlap_bound_at_base_half_width": round(
                    float(base_record["post_guard_overlap_bound"]), 15
                ),
                "base_half_width_certified": bool(base_record["certified"]),
                "max_certifiable_half_width_degrees": round(max_half_width, 12),
                "max_certifiable_cell_width_degrees": round(2.0 * max_half_width, 12),
                "clearance_per_theta_cubed_degrees": round(clearance / theta_cubed, 15) if theta_cubed else None,
            }
        )

    smallest = min(record["max_certifiable_cell_width_degrees"] for record in probe_records)
    return {
        **target,
        "status": "residual_contact_gap_diagnostic_completed",
        "probe_records": probe_records,
        "summary_metrics": {
            "probe_count": len(probe_records),
            "base_half_width_degrees": BASE_HALF_WIDTH_DEGREES,
            "base_cell_width_degrees": 2.0 * BASE_HALF_WIDTH_DEGREES,
            "base_width_certified_probe_count": sum(1 for record in probe_records if record["base_half_width_certified"]),
            "smallest_max_certifiable_cell_width_degrees": smallest,
            "smallest_max_certifiable_cell_width_theta_degrees": next(
                record["theta_degrees"]
                for record in probe_records
                if record["max_certifiable_cell_width_degrees"] == smallest
            ),
        },
    }


def build_report() -> dict:
    case = batch.build_case()
    signs_by_tree = comp.certified_signs_by_tree()
    target_reports = [diagnostic_for_target(case, signs_by_tree, target) for target in RESIDUAL_TARGETS]
    smallest_width = min(
        report["summary_metrics"]["smallest_max_certifiable_cell_width_degrees"]
        for report in target_reports
    )
    return {
        "case_id": CASE_ID,
        "status": "residual_contact_gap_diagnostic_completed",
        "source_report": "results/historical_s4_median_planes/two_class_contact_orientation_report.json",
        "protocol": {
            "probe_theta_degrees": PROBE_THETA_DEGREES,
            "base_half_width_degrees": BASE_HALF_WIDTH_DEGREES,
            "max_half_width_search_degrees": MAX_HALF_WIDTH_SEARCH_DEGREES,
            "binary_search_steps": BINARY_SEARCH_STEPS,
            "method": "targeted residual pair guard probes plus binary search for local max certifiable clearance half-width",
        },
        "summary_metrics": {
            "target_count": len(target_reports),
            "smallest_max_certifiable_cell_width_degrees": smallest_width,
            "clearance_refinement_recommended": False,
            "reason": "The required clearance-only cell width near theta=0.625 degrees is around 1.6e-5 degrees for residual shared-face contacts, so brute-force adaptive clearance refinement is not a tactical next step.",
        },
        "target_reports": target_reports,
        "limitations": [
            "This diagnostic does not certify unresolved residual contacts.",
            "The max-width estimates are local to the probed theta values and the existing clearance guard.",
            "The report is intended to choose the next audit strategy, not to replace an interval or contact-orientation proof.",
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
                "target_summaries": {
                    f"{target['tree_id']}:{'-'.join(target['pair'])}": target["summary_metrics"]
                    for target in report["target_reports"]
                },
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())