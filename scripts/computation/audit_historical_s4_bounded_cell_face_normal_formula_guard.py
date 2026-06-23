"""Bounded-cell face-normal formula guard for S4 representatives.

This audit ports the existing TREE_021 P0-P2 and TREE_007 P2-P3 face-normal
support-gap formulas from refined 1D residual pair-segments to full bounded
3-parameter cells.

Input is the bounded-cell residual shared-face inventory. Only records already
classified as face-normal at the bounded-cell center are targeted:

- TREE_021 P0-P2: left/right face M_AB-C-M_CD
- TREE_007 P2-P3: left/right face B-M_AB-M_CD

For each bounded cell, the script computes interval enclosures for every hinge
coordinate over the full cylindrical wedge cell. It then applies the historical
face-normal formula lower-bound routines to those intervals and numerically
checks the formula against direct transformed geometry at the cell center and
all sampled cell vertices. This is a finite formula ledger for the face-normal
pair-cells only; it does not close the remaining edge-branch cells or promote a
full continuous 3-parameter component certificate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_face_normal_formula_guard_report.json"
SOURCE_INVENTORY_REPORT = "bounded_cell_residual_shared_face_inventory_report.json"
FORMULA_TOLERANCE = 1.0e-12
MAX_STORED_EXAMPLES = 32

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402
import audit_historical_s4_p0p2_face_normal_formula_guard as tree021_face  # noqa: E402
import audit_historical_s4_tree007_p2p3_face_normal_formula_guard as tree007_face  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID

TARGETS = {
    "TREE_021": {
        "pair": ("P0", "P2"),
        "formula_module": tree021_face,
        "indices_factory": tree021_face.branch_probe.label_indices,
        "expected_axes": {tree021_face.LEFT_FACE_AXIS, tree021_face.RIGHT_FACE_AXIS},
        "source_formula_report": "p0p2_face_normal_formula_guard_report.json",
    },
    "TREE_007": {
        "pair": ("P2", "P3"),
        "formula_module": tree007_face,
        "indices_factory": tree007_face.label_indices,
        "expected_axes": {tree007_face.LEFT_FACE_AXIS, tree007_face.RIGHT_FACE_AXIS},
        "source_formula_report": "tree007_p2p3_face_normal_formula_guard_report.json",
    },
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    if math.isinf(float(value)):
        return float(value)
    return round(float(value), digits)


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {key: None for key in ["min", "p05", "p10", "p25", "p50", "p75", "p90", "p95", "max"]}
    ordered = sorted(values)
    n = len(ordered)

    def q(percent: float) -> float:
        if n == 1:
            return ordered[0]
        position = percent * (n - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "min": rounded(ordered[0], 15),
        "p05": rounded(q(0.05), 15),
        "p10": rounded(q(0.10), 15),
        "p25": rounded(q(0.25), 15),
        "p50": rounded(q(0.50), 15),
        "p75": rounded(q(0.75), 15),
        "p90": rounded(q(0.90), 15),
        "p95": rounded(q(0.95), 15),
        "max": rounded(ordered[-1], 15),
    }


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def top_counter(counter: Counter, limit: int = 32) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def cell_widths(cell: dict) -> dict[str, float]:
    theta_left, theta_right = [float(value) for value in cell["theta_interval_degrees"]]
    radial_left, radial_right = [float(value) for value in cell["radial_interval_degrees"]]
    return {
        "theta_width_degrees": theta_right - theta_left,
        "radial_width_degrees": radial_right - radial_left,
        "direction_sector_width": 1.0,
    }


def interval_lists(tree: dict, signs_by_hinge: dict[str, int], cell: dict) -> dict[str, list[float]]:
    intervals = first_pass.angle_coordinate_intervals(tree, signs_by_hinge, cell)
    return {
        hinge_id: [float(record["minimum_degrees"]), float(record["maximum_degrees"])]
        for hinge_id, record in intervals.items()
    }


def compact_intervals(intervals: dict[str, list[float]]) -> dict[str, list[float]]:
    return {
        hinge_id: [rounded(values[0], 10), rounded(values[1], 10)]
        for hinge_id, values in sorted(intervals.items())
    }


def angle_vector_for_node(tree: dict, signs_by_hinge: dict[str, int], node: dict) -> np.ndarray:
    sign_vec = reps.sign_vector(tree, signs_by_hinge)
    base_vector = sign_vec * float(node["theta_degrees"])
    return base_vector + comp.offset_for_node(sign_vec, node)


def sample_vectors_for_cell(
    tree: dict,
    signs_by_hinge: dict[str, int],
    cell: dict,
    nodes_by_id: dict[str, dict],
) -> list[tuple[str, np.ndarray]]:
    samples = [("cell_center", first_pass.center_angle_vector(tree, signs_by_hinge, cell))]
    for node_id in cell["vertex_node_ids"]:
        samples.append((f"vertex:{node_id}", angle_vector_for_node(tree, signs_by_hinge, nodes_by_id[node_id])))
    return samples


def formula_check_for_cell(
    case: dict,
    tree: dict,
    formula_module,
    indices: dict,
    axis_name: str,
    samples: list[tuple[str, np.ndarray]],
) -> dict:
    checks = []
    for sample_name, vector in samples:
        degrees = reps.degrees_from_vector(tree, vector)
        formula = formula_module.formula_value(axis_name, degrees)
        direct = formula_module.direct_raw_gap(case, tree, indices, axis_name, vector)
        error = formula - direct
        checks.append(
            {
                "sample": sample_name,
                "formula_value": rounded(formula, 15),
                "direct_raw_gap": rounded(direct, 15),
                "absolute_error": rounded(abs(error), 18),
                "within_tolerance": abs(error) <= FORMULA_TOLERANCE,
            }
        )
    return {
        "sample_count": len(checks),
        "max_abs_error": max(float(item["absolute_error"]) for item in checks),
        "all_within_tolerance": all(item["within_tolerance"] for item in checks),
        "samples": checks,
    }


def compact_record(
    record: dict,
    cell: dict,
    bounds: dict,
    formula_check: dict,
    intervals: dict[str, list[float]],
    certified: bool,
) -> dict:
    return {
        "cell_id": record["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "pair": record["pair"],
        "axis_name": record["axis_name"],
        "formula_certified": certified,
        "active_hinge": bounds.get("active_hinge"),
        "angle_coordinate_intervals_degrees": compact_intervals(intervals),
        "raw_gap_lower_bound": bounds.get("raw_gap_lower_bound"),
        "minimum_support_lower_bound": bounds.get("minimum_support_lower_bound"),
        "formula_check_sample_count": formula_check["sample_count"],
        "formula_check_max_abs_error": rounded(formula_check["max_abs_error"], 18),
        "widths": {key: rounded(value) for key, value in cell_widths(cell).items()},
    }


def audit_target(
    case: dict,
    inventory_target: dict,
    cell_by_id: dict[str, dict],
    nodes_by_id: dict[str, dict],
    signs_by_tree: dict[str, dict[str, int]],
) -> dict:
    tree_id = inventory_target["target"]["tree_id"]
    config = TARGETS[tree_id]
    tree = comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    formula_module = config["formula_module"]
    indices = config["indices_factory"](case)

    axis_counts = Counter()
    kind_counts = Counter()
    result_counts = Counter()
    active_hinge_counts = Counter()
    theta_interval_counts = Counter()
    radial_interval_counts = Counter()
    direction_sector_counts = Counter()
    sample_count_by_kind = Counter()
    raw_gap_lower_bounds = []
    support_lower_bounds = []
    formula_errors = []
    width_values = defaultdict(list)
    global_angle_intervals = defaultdict(list)
    examples = defaultdict(list)
    cell_reports = []

    face_records = [record for record in inventory_target["records"] if record["axis_category"] == "face_normal"]
    expected_count = int(inventory_target["summary_metrics"]["center_axis_face_normal_cell_count"])
    if len(face_records) != expected_count:
        raise AssertionError(f"{tree_id} expected {expected_count} face-normal cells, found {len(face_records)}")

    for record in face_records:
        axis_name = record["axis_name"]
        if axis_name not in config["expected_axes"]:
            raise AssertionError(f"Unexpected face-normal axis for {tree_id}: {axis_name}")
        cell = cell_by_id[record["cell_id"]]
        intervals = interval_lists(tree, signs, cell)
        bounds = formula_module.formula_lower_bounds(axis_name, intervals)
        samples = sample_vectors_for_cell(tree, signs, cell, nodes_by_id)
        formula_check = formula_check_for_cell(case, tree, formula_module, indices, axis_name, samples)
        certified = bool(
            bounds.get("formula_sign_certified")
            and bounds.get("support_sign_certified")
            and formula_check["all_within_tolerance"]
        )

        axis_counts[axis_name] += 1
        kind_counts[cell["kind"]] += 1
        active_hinge_counts[bounds.get("active_hinge")] += 1
        result_counts["certified" if certified else "uncovered"] += 1
        theta_interval_counts[str(cell["theta_interval_degrees"])] += 1
        radial_interval_counts[str(cell["radial_interval_degrees"])] += 1
        direction_sector_counts[str(cell["direction_sector"])] += 1
        sample_count_by_kind[cell["kind"]] += len(samples)
        if bounds.get("raw_gap_lower_bound") is not None:
            raw_gap_lower_bounds.append(float(bounds["raw_gap_lower_bound"]))
        if bounds.get("minimum_support_lower_bound") is not None:
            support_lower_bounds.append(float(bounds["minimum_support_lower_bound"]))
        formula_errors.append(float(formula_check["max_abs_error"]))
        for hinge_id, interval in intervals.items():
            global_angle_intervals[hinge_id].extend(interval)
        for key, value in cell_widths(cell).items():
            width_values[key].append(float(value))

        compact = compact_record(record, cell, bounds, formula_check, intervals, certified)
        cell_reports.append(compact)
        add_example(examples["certified" if certified else "uncovered"], compact)

    certified_count = result_counts.get("certified", 0)
    uncovered_count = result_counts.get("uncovered", 0)
    return {
        "target": {
            "tree_id": tree_id,
            "pair": list(config["pair"]),
            "target_axes": sorted(config["expected_axes"]),
            "source_formula_report": config["source_formula_report"],
        },
        "summary_metrics": {
            "input_face_normal_cell_count": len(face_records),
            "formula_certified_cell_count": certified_count,
            "formula_uncovered_cell_count": uncovered_count,
            "all_input_face_normal_cells_formula_certified": certified_count == len(face_records) and uncovered_count == 0,
            "formula_check_sample_count": sum(sample_count_by_kind.values()),
            "minimum_raw_gap_lower_bound": rounded(min(raw_gap_lower_bounds) if raw_gap_lower_bounds else None, 15),
            "minimum_support_lower_bound": rounded(min(support_lower_bounds) if support_lower_bounds else None, 15),
            "maximum_formula_check_abs_error": rounded(max(formula_errors) if formula_errors else None, 18),
            "formula_check_all_samples_within_tolerance": all(error <= FORMULA_TOLERANCE for error in formula_errors),
        },
        "breakdown": {
            "axis_counts": dict(axis_counts.most_common()),
            "cell_kind_counts": dict(kind_counts.most_common()),
            "active_hinge_counts": dict(active_hinge_counts.most_common()),
            "theta_interval_counts": top_counter(theta_interval_counts),
            "radial_interval_counts": top_counter(radial_interval_counts),
            "direction_sector_counts": top_counter(direction_sector_counts),
            "sample_count_by_cell_kind": dict(sample_count_by_kind.most_common()),
            "global_angle_intervals_degrees": {
                hinge_id: [rounded(min(values), 10), rounded(max(values), 10)]
                for hinge_id, values in sorted(global_angle_intervals.items())
            },
            "raw_gap_lower_bound_quantiles": quantiles(raw_gap_lower_bounds),
            "support_lower_bound_quantiles": quantiles(support_lower_bounds),
            "formula_check_abs_error_quantiles": quantiles(formula_errors),
            "width_quantiles": {key: quantiles(values) for key, values in sorted(width_values.items())},
        },
        "examples": dict(examples),
        "cell_reports": cell_reports,
    }


def aggregate_summary(target_reports: list[dict]) -> dict:
    def total(metric: str) -> int:
        return sum(int(report["summary_metrics"][metric]) for report in target_reports)

    axis_counts = Counter()
    kind_counts = Counter()
    for report in target_reports:
        axis_counts.update(report["breakdown"]["axis_counts"])
        kind_counts.update(report["breakdown"]["cell_kind_counts"])
    formula_errors = [
        float(record["formula_check_max_abs_error"])
        for report in target_reports
        for record in report["cell_reports"]
    ]
    return {
        "target_count": len(target_reports),
        "input_face_normal_cell_count": total("input_face_normal_cell_count"),
        "formula_certified_cell_count": total("formula_certified_cell_count"),
        "formula_uncovered_cell_count": total("formula_uncovered_cell_count"),
        "all_input_face_normal_cells_formula_certified": all(
            report["summary_metrics"]["all_input_face_normal_cells_formula_certified"]
            for report in target_reports
        ),
        "formula_check_sample_count": total("formula_check_sample_count"),
        "formula_check_all_samples_within_tolerance": all(
            report["summary_metrics"]["formula_check_all_samples_within_tolerance"]
            for report in target_reports
        ),
        "maximum_formula_check_abs_error": rounded(max(formula_errors) if formula_errors else None, 18),
        "axis_counts": dict(axis_counts.most_common()),
        "cell_kind_counts": dict(kind_counts.most_common()),
    }


def build_report() -> dict:
    inventory = load_json(RESULTS_DIR / SOURCE_INVENTORY_REPORT)
    case = batch.build_case()
    signs_by_tree = comp.certified_signs_by_tree()
    cell_by_id = {cell["cell_id"]: cell for cell in protocol.iter_cells()}
    nodes_by_id = {node["node_id"]: node for node in comp.all_node_records()}
    inventory_by_tree = {
        target["target"]["tree_id"]: target
        for target in inventory["target_reports"]
        if target["target"]["tree_id"] in TARGETS
    }
    missing = sorted(set(TARGETS) - set(inventory_by_tree))
    if missing:
        raise AssertionError(f"Missing target reports in inventory: {missing}")

    target_reports = [
        audit_target(case, inventory_by_tree[tree_id], cell_by_id, nodes_by_id, signs_by_tree)
        for tree_id in sorted(TARGETS)
    ]
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_face_normal_formula_guard_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_INVENTORY_REPORT}",
            f"results/{CASE_ID}/p0p2_face_normal_formula_guard_report.json",
            f"results/{CASE_ID}/tree007_p2p3_face_normal_formula_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
        ],
        "target": {
            "description": "full-cell formula guard for bounded-cell residual shared-face records classified as face-normal",
            "remaining_outside_scope": "edge-branch bounded-cell residual shared-face records",
            "formula_tolerance": FORMULA_TOLERANCE,
            "sample_check_protocol": "cell center plus all sampled cell vertices; sign proof uses full-cell hinge-coordinate intervals",
        },
        "summary_metrics": aggregate_summary(target_reports),
        "target_reports": target_reports,
        "limitations": [
            "This report certifies only the 544 bounded-cell residual shared-face records classified as face-normal by the inventory report.",
            "The remaining 723 edge-branch bounded-cell records are outside this formula guard and remain open.",
            "The trigonometric support-gap formulas are reused from existing local formula reports and checked numerically against direct transformed geometry at bounded-cell samples; the script does not derive them symbolically at runtime.",
            "This is not a full continuous 3-parameter component certificate, does not cover theta=0, and does not certify physical hinge thickness, offsets, CAD, mesh export, or printability.",
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