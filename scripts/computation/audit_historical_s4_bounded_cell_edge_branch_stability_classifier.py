"""Bounded-cell edge-branch stability classifier for S4 representatives.

The bounded-cell shared-edge front is closed and the face-normal subset of the
residual shared-face front is certified. This diagnostic targets the remaining
edge-branch bounded cells from the residual shared-face inventory:

- TREE_021 P0-P2
- TREE_007 P2-P3

For every edge-branch cell, the script evaluates the assigned center edge-axis
family at the cell center and all sampled cell vertices. It records whether the
assigned branch remains separating at the samples and whether the best named SAT
axis remains the same edge branch. This is a routing/stability classifier for
choosing the next edge-branch guard; it is not a full-cell certificate.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_edge_branch_stability_classifier_report.json"
SOURCE_INVENTORY_REPORT = "bounded_cell_residual_shared_face_inventory_report.json"
MAX_STORED_EXAMPLES = 48

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_representatives as reps  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402
import audit_historical_s4_two_class_ray_cell_guard as ray_guard  # noqa: E402
import audit_historical_s4_bounded_cell_cover_protocol_spec as protocol  # noqa: E402
import audit_historical_s4_bounded_cell_guard_first_pass as first_pass  # noqa: E402
import audit_historical_s4_residual_contact_failure_classification as classify  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID

TARGETS = {
    "TREE_021": {"pair": ("P0", "P2")},
    "TREE_007": {"pair": ("P2", "P3")},
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


def top_counter(counter: Counter, limit: int = 48) -> dict[str, int]:
    return {str(key): int(value) for key, value in counter.most_common(limit)}


def label_indices(case: dict) -> dict[str, dict[str, int]]:
    return {
        piece_id: {
            lib.label_for(vertex, case["labels"]): index
            for index, vertex in enumerate(piece)
        }
        for piece_id, piece in case["pieces_by_id"].items()
    }


def point(pieces: dict[str, list[np.ndarray]], indices: dict[str, dict[str, int]], piece_id: str, label: str) -> np.ndarray:
    return pieces[piece_id][indices[piece_id][label]]


def parse_edge_axis(axis_name: str) -> tuple[list[str], list[str]]:
    if not axis_name.startswith("edge:"):
        raise ValueError(f"Not an edge axis: {axis_name}")
    left_text, right_text = axis_name[len("edge:"):].split(" x ", 1)
    return left_text.split("-"), right_text.split("-")


def assigned_branch_overlap(
    pieces: dict[str, list[np.ndarray]],
    indices: dict[str, dict[str, int]],
    pair: tuple[str, str],
    axis_name: str,
) -> dict:
    left_labels, right_labels = parse_edge_axis(axis_name)
    left_a = point(pieces, indices, pair[0], left_labels[0])
    left_b = point(pieces, indices, pair[0], left_labels[1])
    right_a = point(pieces, indices, pair[1], right_labels[0])
    right_b = point(pieces, indices, pair[1], right_labels[1])
    axis = np.cross(left_b - left_a, right_b - right_a)
    axis_norm = float(np.linalg.norm(axis))
    if axis_norm <= lib.TOL:
        return {"axis_norm": axis_norm, "overlap": None, "gap": None, "separating": False}
    unit = axis / axis_norm
    left_values = [float(np.dot(vertex, unit)) for vertex in pieces[pair[0]]]
    right_values = [float(np.dot(vertex, unit)) for vertex in pieces[pair[1]]]
    overlap = min(max(left_values), max(right_values)) - max(min(left_values), min(right_values))
    return {
        "axis_norm": axis_norm,
        "overlap": float(overlap),
        "gap": max(0.0, -float(overlap)),
        "separating": float(overlap) < 0.0,
    }


def cell_widths(cell: dict) -> dict[str, float]:
    theta_left, theta_right = [float(value) for value in cell["theta_interval_degrees"]]
    radial_left, radial_right = [float(value) for value in cell["radial_interval_degrees"]]
    return {
        "theta_width_degrees": theta_right - theta_left,
        "radial_width_degrees": radial_right - radial_left,
        "direction_sector_width": 1.0,
    }


def compact_intervals(intervals: dict[str, dict]) -> dict[str, list[float]]:
    return {
        hinge_id: [rounded(record["minimum_degrees"], 10), rounded(record["maximum_degrees"], 10)]
        for hinge_id, record in sorted(intervals.items())
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


def evaluate_sample(
    case: dict,
    tree: dict,
    labels_by_piece: dict[str, list[str]],
    indices: dict[str, dict[str, int]],
    pair: tuple[str, str],
    assigned_axis: str,
    sample_name: str,
    vector: np.ndarray,
) -> dict:
    degrees = reps.degrees_from_vector(tree, vector)
    transforms = ray_guard.transforms_for_degrees(case, tree, degrees)
    pieces = lib.transform_pieces(case["pieces_by_id"], transforms)
    best = classify.best_named_axis(
        pieces[pair[0]],
        pieces[pair[1]],
        labels_by_piece[pair[0]],
        labels_by_piece[pair[1]],
    )
    assigned = assigned_branch_overlap(pieces, indices, pair, assigned_axis)
    return {
        "sample": sample_name,
        "best_axis_name": best["axis_name"],
        "best_axis_category": "edge_branch" if best["axis_name"].startswith("edge:") else "face_normal",
        "best_axis_overlap": rounded(best["center_axis_overlap"], 15),
        "assigned_axis_overlap": rounded(assigned["overlap"], 15),
        "assigned_axis_gap": rounded(assigned["gap"], 15),
        "assigned_axis_norm": rounded(assigned["axis_norm"], 15),
        "assigned_axis_separating": bool(assigned["separating"]),
        "assigned_axis_is_best": best["axis_name"] == assigned_axis,
    }


def classify_cell(samples: list[dict], assigned_axis: str) -> str:
    assigned_separating = all(sample["assigned_axis_separating"] for sample in samples)
    exact_stable = all(sample["best_axis_name"] == assigned_axis for sample in samples)
    all_best_edge = all(sample["best_axis_category"] == "edge_branch" for sample in samples)
    if exact_stable and assigned_separating:
        return "assigned_edge_axis_sample_stable"
    if assigned_separating and all_best_edge:
        return "assigned_separating_edge_axis_switch"
    if assigned_separating:
        return "assigned_separating_face_normal_or_mixed_switch"
    return "assigned_axis_nonseparating_sample"


def compact_cell_report(record: dict, cell: dict, coordinate_intervals: dict, samples: list[dict], profile: str) -> dict:
    assigned_gaps = [float(sample["assigned_axis_gap"]) for sample in samples if sample["assigned_axis_gap"] is not None]
    assigned_overlaps = [float(sample["assigned_axis_overlap"]) for sample in samples if sample["assigned_axis_overlap"] is not None]
    best_axes = Counter(sample["best_axis_name"] for sample in samples)
    return {
        "cell_id": record["cell_id"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "pair": record["pair"],
        "assigned_axis_name": record["axis_name"],
        "sample_profile": profile,
        "sample_count": len(samples),
        "assigned_axis_separating_sample_count": sum(1 for sample in samples if sample["assigned_axis_separating"]),
        "assigned_axis_best_sample_count": sum(1 for sample in samples if sample["assigned_axis_is_best"]),
        "best_axis_name_counts": dict(best_axes.most_common()),
        "assigned_axis_gap_interval": [rounded(min(assigned_gaps), 15), rounded(max(assigned_gaps), 15)] if assigned_gaps else [None, None],
        "assigned_axis_overlap_interval": [rounded(min(assigned_overlaps), 15), rounded(max(assigned_overlaps), 15)] if assigned_overlaps else [None, None],
        "angle_coordinate_intervals_degrees": compact_intervals(coordinate_intervals),
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
    pair = TARGETS[tree_id]["pair"]
    tree = comp.find_tree(case, tree_id)
    signs = signs_by_tree[tree_id]
    labels_by_piece = classify.labels_by_piece(case)
    indices = label_indices(case)

    edge_records = [record for record in inventory_target["records"] if record["axis_category"] == "edge_branch"]
    expected_count = int(inventory_target["summary_metrics"]["center_axis_edge_branch_cell_count"])
    if len(edge_records) != expected_count:
        raise AssertionError(f"{tree_id} expected {expected_count} edge-branch cells, found {len(edge_records)}")

    profile_counts = Counter()
    assigned_axis_counts = Counter()
    best_axis_sample_counts = Counter()
    cell_kind_counts = Counter()
    theta_interval_counts = Counter()
    radial_interval_counts = Counter()
    direction_sector_counts = Counter()
    sample_count_by_kind = Counter()
    assigned_gap_mins = []
    assigned_gap_maxes = []
    assigned_overlap_mins = []
    assigned_overlap_maxes = []
    assigned_best_sample_fractions = []
    assigned_separating_sample_fractions = []
    width_values = defaultdict(list)
    global_angle_intervals = defaultdict(list)
    transition_counts = Counter()
    examples = defaultdict(list)
    cell_reports = []

    for record in edge_records:
        assigned_axis = record["axis_name"]
        cell = cell_by_id[record["cell_id"]]
        coordinate_intervals = first_pass.angle_coordinate_intervals(tree, signs, cell)
        samples = [
            evaluate_sample(case, tree, labels_by_piece, indices, pair, assigned_axis, sample_name, vector)
            for sample_name, vector in sample_vectors_for_cell(tree, signs, cell, nodes_by_id)
        ]
        profile = classify_cell(samples, assigned_axis)
        compact = compact_cell_report(record, cell, coordinate_intervals, samples, profile)
        cell_reports.append(compact)
        add_example(examples[profile], {**compact, "samples": samples})

        profile_counts[profile] += 1
        assigned_axis_counts[assigned_axis] += 1
        cell_kind_counts[cell["kind"]] += 1
        theta_interval_counts[str(cell["theta_interval_degrees"])] += 1
        radial_interval_counts[str(cell["radial_interval_degrees"])] += 1
        direction_sector_counts[str(cell["direction_sector"])] += 1
        sample_count_by_kind[cell["kind"]] += len(samples)
        for sample in samples:
            best_axis_sample_counts[sample["best_axis_name"]] += 1
        best_axis_signature = tuple(sorted(compact["best_axis_name_counts"].items()))
        transition_counts[(assigned_axis, best_axis_signature)] += 1
        assigned_best_sample_fractions.append(compact["assigned_axis_best_sample_count"] / compact["sample_count"])
        assigned_separating_sample_fractions.append(compact["assigned_axis_separating_sample_count"] / compact["sample_count"])
        gap_min, gap_max = compact["assigned_axis_gap_interval"]
        overlap_min, overlap_max = compact["assigned_axis_overlap_interval"]
        if gap_min is not None:
            assigned_gap_mins.append(float(gap_min))
            assigned_gap_maxes.append(float(gap_max))
        if overlap_min is not None:
            assigned_overlap_mins.append(float(overlap_min))
            assigned_overlap_maxes.append(float(overlap_max))
        for hinge_id, interval in coordinate_intervals.items():
            global_angle_intervals[hinge_id].append(float(interval["minimum_degrees"]))
            global_angle_intervals[hinge_id].append(float(interval["maximum_degrees"]))
        for key, value in cell_widths(cell).items():
            width_values[key].append(float(value))

    all_samples = sum(sample_count_by_kind.values())
    assigned_stable_count = profile_counts.get("assigned_edge_axis_sample_stable", 0)
    assigned_separating_count = sum(
        count for profile, count in profile_counts.items()
        if profile.startswith("assigned_separating") or profile == "assigned_edge_axis_sample_stable"
    )
    return {
        "target": {
            "tree_id": tree_id,
            "pair": list(pair),
            "role": "residual_shared_face_edge_branch",
        },
        "summary_metrics": {
            "input_edge_branch_cell_count": len(edge_records),
            "sample_count": all_samples,
            "assigned_edge_axis_sample_stable_cell_count": assigned_stable_count,
            "assigned_edge_axis_sample_stable_fraction": rounded(assigned_stable_count / len(edge_records), 6) if edge_records else 0.0,
            "assigned_axis_separating_all_samples_cell_count": assigned_separating_count,
            "assigned_axis_separating_all_samples_fraction": rounded(assigned_separating_count / len(edge_records), 6) if edge_records else 0.0,
            "assigned_axis_nonseparating_sample_cell_count": profile_counts.get("assigned_axis_nonseparating_sample", 0),
            "distinct_assigned_edge_axis_count": len(assigned_axis_counts),
            "distinct_best_sample_axis_count": len(best_axis_sample_counts),
        },
        "breakdown": {
            "sample_profile_counts": dict(profile_counts.most_common()),
            "assigned_axis_counts": dict(assigned_axis_counts.most_common()),
            "best_axis_sample_counts": top_counter(best_axis_sample_counts),
            "cell_kind_counts": dict(cell_kind_counts.most_common()),
            "theta_interval_counts": top_counter(theta_interval_counts),
            "radial_interval_counts": top_counter(radial_interval_counts),
            "direction_sector_counts": top_counter(direction_sector_counts),
            "sample_count_by_cell_kind": dict(sample_count_by_kind.most_common()),
            "assigned_gap_min_quantiles": quantiles(assigned_gap_mins),
            "assigned_gap_max_quantiles": quantiles(assigned_gap_maxes),
            "assigned_overlap_min_quantiles": quantiles(assigned_overlap_mins),
            "assigned_overlap_max_quantiles": quantiles(assigned_overlap_maxes),
            "assigned_best_sample_fraction_quantiles": quantiles(assigned_best_sample_fractions),
            "assigned_separating_sample_fraction_quantiles": quantiles(assigned_separating_sample_fractions),
            "global_angle_intervals_degrees": {
                hinge_id: [rounded(min(values), 10), rounded(max(values), 10)]
                for hinge_id, values in sorted(global_angle_intervals.items())
            },
            "width_quantiles": {key: quantiles(values) for key, values in sorted(width_values.items())},
            "top_assigned_to_best_axis_sample_signatures": {
                f"{assigned} -> {dict(signature)}": int(count)
                for (assigned, signature), count in transition_counts.most_common(24)
            },
        },
        "examples": dict(examples),
        "cell_reports": cell_reports,
    }


def aggregate_summary(target_reports: list[dict]) -> dict:
    def total(metric: str) -> int:
        return sum(int(report["summary_metrics"][metric]) for report in target_reports)

    profile_counts = Counter()
    assigned_axis_counts = Counter()
    best_axis_counts = Counter()
    for report in target_reports:
        profile_counts.update(report["breakdown"]["sample_profile_counts"])
        assigned_axis_counts.update(report["breakdown"]["assigned_axis_counts"])
        best_axis_counts.update(report["breakdown"]["best_axis_sample_counts"])
    total_cells = total("input_edge_branch_cell_count")
    stable = total("assigned_edge_axis_sample_stable_cell_count")
    separating = total("assigned_axis_separating_all_samples_cell_count")
    return {
        "target_count": len(target_reports),
        "input_edge_branch_cell_count": total_cells,
        "sample_count": total("sample_count"),
        "assigned_edge_axis_sample_stable_cell_count": stable,
        "assigned_edge_axis_sample_stable_fraction": rounded(stable / total_cells, 6) if total_cells else 0.0,
        "assigned_axis_separating_all_samples_cell_count": separating,
        "assigned_axis_separating_all_samples_fraction": rounded(separating / total_cells, 6) if total_cells else 0.0,
        "assigned_axis_nonseparating_sample_cell_count": total("assigned_axis_nonseparating_sample_cell_count"),
        "sample_profile_counts": dict(profile_counts.most_common()),
        "assigned_axis_counts": dict(assigned_axis_counts.most_common()),
        "top_best_axis_sample_counts": top_counter(best_axis_counts, 24),
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
        "status": "bounded_cell_edge_branch_stability_classifier_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_INVENTORY_REPORT}",
            f"results/{CASE_ID}/bounded_cell_face_normal_formula_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_guard_first_pass_report.json",
        ],
        "target": {
            "description": "sample stability classifier for bounded-cell residual shared-face records classified as edge-branch",
            "sample_protocol": "cell center plus all sampled cell vertices",
            "certification_status": "diagnostic_only_not_a_full_cell_guard",
        },
        "summary_metrics": aggregate_summary(target_reports),
        "target_reports": target_reports,
        "limitations": [
            "This report classifies the 723 edge-branch bounded cells at center/vertex samples only; it is not a full-cell interval certificate.",
            "An assigned edge axis separating at all sampled cell vertices does not prove separation throughout the bounded cell interior.",
            "Axis switches at samples are routing information for the next edge-branch guard/adaptive subdivision workflow.",
            "This report does not certify theta=0, the full continuous 3-parameter component, dynamic class connectedness, physical hinge thickness, CAD, mesh export, or printability.",
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