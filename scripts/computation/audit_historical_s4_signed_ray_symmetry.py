"""Signed-ray symmetry checker for all-ambient-edge S4 hinge trees.

This checker does not run collision tests. It consumes the dense refinement
reports and tests how certified signed rays transform under the 8 vertex
permutations preserving the unordered opposite-edge pair {AB, CD}.
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "signed_ray_symmetry_report.json"
TARGET_TREE_IDS = ["TREE_007", "TREE_009", "TREE_021", "TREE_093"]

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_ambient_edge_dense_refinement as dense  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def map_midpoint_label(label: str, permutation: dict[str, str]) -> str:
    if label in {"A", "B", "C", "D"}:
        return permutation[label]
    if not label.startswith("M_"):
        raise ValueError(f"Unsupported label for this checker: {label}")
    body = label[2:]
    if "_" in body:
        left, right = body.split("_")
    else:
        left, right = body[0], body[1]
    mapped = "".join(sorted([permutation[left], permutation[right]]))
    return f"M_{mapped}"


def normalize_midpoint_label(label: str) -> str:
    if label.startswith("M_") and "_" not in label[2:]:
        return f"M_{label[2]}{label[3]}"
    return label


def map_label(label: str, permutation: dict[str, str]) -> str:
    mapped = map_midpoint_label(label, permutation)
    return normalize_midpoint_label(mapped)


def piece_label_sets(case: dict) -> dict[str, frozenset[str]]:
    records = {}
    for piece_id, piece in case["pieces_by_id"].items():
        record = lib.piece_record(piece_id, piece, case["labels"])
        records[piece_id] = frozenset(vertex["label"] for vertex in record["vertices"])
    return records


def piece_map_for_permutation(case: dict, permutation: dict[str, str]) -> dict[str, str]:
    source_sets = piece_label_sets(case)
    target_by_set = {labels: piece_id for piece_id, labels in source_sets.items()}
    mapping = {}
    for piece_id, labels in source_sets.items():
        mapped_labels = frozenset(map_label(label, permutation) for label in labels)
        target_piece = target_by_set.get(mapped_labels)
        if target_piece is None:
            raise RuntimeError(f"Could not map piece {piece_id}: {sorted(mapped_labels)}")
        mapping[piece_id] = target_piece
    return mapping


def affine_matrix_for_permutation(case: dict, permutation: dict[str, str]) -> np.ndarray:
    labels = case["labels"]
    source_origin = labels["A"]
    target_origin = labels[permutation["A"]]
    source_basis = np.column_stack([labels["B"] - source_origin, labels["C"] - source_origin, labels["D"] - source_origin])
    target_basis = np.column_stack([
        labels[permutation["B"]] - target_origin,
        labels[permutation["C"]] - target_origin,
        labels[permutation["D"]] - target_origin,
    ])
    return target_basis @ np.linalg.inv(source_basis)


def determinant_sign(matrix: np.ndarray) -> int:
    det = float(np.linalg.det(matrix))
    if det > 0:
        return 1
    if det < 0:
        return -1
    raise RuntimeError("Degenerate isometry matrix")


def axis_orientation_sign(case: dict, source_hinge_id: str, target_hinge_id: str, matrix: np.ndarray) -> int:
    source_hinge = case["hinge_by_id"][source_hinge_id]
    target_hinge = case["hinge_by_id"][target_hinge_id]
    labels = case["labels"]
    source_a, source_b = source_hinge["axis_labels"]
    target_a, target_b = target_hinge["axis_labels"]
    mapped_vector = matrix @ (labels[source_b] - labels[source_a])
    target_vector = labels[target_b] - labels[target_a]
    dot = float(np.dot(mapped_vector, target_vector))
    if dot > 0:
        return 1
    if dot < 0:
        return -1
    raise RuntimeError(f"Axis orientation collapsed for {source_hinge_id}->{target_hinge_id}")


def tree_by_axis_set(tree_reports: list[dict]) -> dict[frozenset[str], str]:
    return {
        frozenset(report["hinge_ids"]): report["tree_id"]
        for report in tree_reports
    }


def load_dense_comparison() -> dict:
    path = RESULTS_DIR / "ambient_edge_dense_refinement_report.json"
    if not path.exists():
        raise RuntimeError(f"Missing dense comparison report: {path}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def transform_signed_ray(case: dict, source_report: dict, permutation: dict[str, str]) -> dict:
    matrix = affine_matrix_for_permutation(case, permutation)
    det_sign = determinant_sign(matrix)
    target_signs = {}
    axis_mappings = []
    for source_hinge_id, source_sign in source_report["ray_signs_by_hinge"].items():
        target_hinge_id = dense.map_axis_id(source_hinge_id, permutation)
        orient_sign = axis_orientation_sign(case, source_hinge_id, target_hinge_id, matrix)
        transported_sign = int(det_sign * orient_sign * int(source_sign))
        target_signs[target_hinge_id] = transported_sign
        axis_mappings.append(
            {
                "source_hinge_id": source_hinge_id,
                "target_hinge_id": target_hinge_id,
                "source_sign": int(source_sign),
                "determinant_sign": det_sign,
                "axis_orientation_sign": orient_sign,
                "transported_sign": transported_sign,
            }
        )
    piece_map = piece_map_for_permutation(case, permutation)
    return {
        "permutation": permutation,
        "determinant_sign": det_sign,
        "piece_map": piece_map,
        "root_piece_image": piece_map["P0"],
        "root_preserving": piece_map["P0"] == "P0",
        "axis_mappings": axis_mappings,
        "target_axis_set": sorted(target_signs),
        "target_signs_by_hinge": dict(sorted(target_signs.items())),
    }


def all_transforms(case: dict, dense_report: dict) -> list[dict]:
    tree_reports = dense_report["tree_reports"]
    target_by_axis_set = tree_by_axis_set(tree_reports)
    certified_signs_by_tree = {
        report["tree_id"]: dict(report["ray_signs_by_hinge"])
        for report in tree_reports
    }
    transforms = []
    for source_report in tree_reports:
        for permutation in dense.opposite_edge_stabilizer_permutations():
            transformed = transform_signed_ray(case, source_report, permutation)
            target_tree_id = target_by_axis_set.get(frozenset(transformed["target_axis_set"]))
            certified_target_signs = certified_signs_by_tree.get(target_tree_id, {}) if target_tree_id else {}
            signed_ray_match = transformed["target_signs_by_hinge"] == certified_target_signs
            transforms.append(
                {
                    "source_tree_id": source_report["tree_id"],
                    "target_tree_id": target_tree_id,
                    "permutation": transformed["permutation"],
                    "determinant_sign": transformed["determinant_sign"],
                    "root_piece_image": transformed["root_piece_image"],
                    "root_preserving": transformed["root_preserving"],
                    "piece_map": transformed["piece_map"],
                    "axis_mappings": transformed["axis_mappings"],
                    "transported_signs_by_hinge": transformed["target_signs_by_hinge"],
                    "certified_target_signs_by_hinge": certified_target_signs,
                    "signed_ray_match": signed_ray_match,
                    "root_preserving_signed_ray_match": signed_ray_match and transformed["root_preserving"],
                }
            )
    return transforms


def reachability_matrix(tree_ids: list[str], transforms: list[dict], root_preserving: bool) -> dict[str, dict[str, bool]]:
    matrix = {source: {target: False for target in tree_ids} for source in tree_ids}
    for transform in transforms:
        if not transform["signed_ray_match"]:
            continue
        if root_preserving and not transform["root_preserving"]:
            continue
        source = transform["source_tree_id"]
        target = transform["target_tree_id"]
        if source in matrix and target in matrix[source]:
            matrix[source][target] = True
    return matrix


def first_witnesses(tree_ids: list[str], transforms: list[dict], root_preserving: bool) -> dict[str, dict[str, dict | None]]:
    witnesses = {source: {target: None for target in tree_ids} for source in tree_ids}
    for transform in transforms:
        if not transform["signed_ray_match"]:
            continue
        if root_preserving and not transform["root_preserving"]:
            continue
        source = transform["source_tree_id"]
        target = transform["target_tree_id"]
        if source in witnesses and target in witnesses[source] and witnesses[source][target] is None:
            witnesses[source][target] = {
                "permutation": transform["permutation"],
                "determinant_sign": transform["determinant_sign"],
                "root_piece_image": transform["root_piece_image"],
                "piece_map": transform["piece_map"],
                "transported_signs_by_hinge": transform["transported_signs_by_hinge"],
            }
    return witnesses


def matrix_all_true(matrix: dict[str, dict[str, bool]]) -> bool:
    return all(value for row in matrix.values() for value in row.values())

def orbit_classes_from_matrix(matrix: dict[str, dict[str, bool]]) -> list[list[str]]:
    remaining = set(matrix)
    classes = []
    while remaining:
        start = sorted(remaining)[0]
        stack = [start]
        component = set()
        while stack:
            node = stack.pop()
            if node in component:
                continue
            component.add(node)
            for target, reachable in matrix[node].items():
                if reachable and target not in component:
                    stack.append(target)
            for source, row in matrix.items():
                if row.get(node) and source not in component:
                    stack.append(source)
        classes.append(sorted(component))
        remaining -= component
    return classes


def build_report() -> dict:
    case = batch.build_case()
    dense_report = load_dense_comparison()
    tree_ids = dense_report["tree_ids"]
    transforms = all_transforms(case, dense_report)
    signed_matrix = reachability_matrix(tree_ids, transforms, root_preserving=False)
    root_matrix = reachability_matrix(tree_ids, transforms, root_preserving=True)
    signed_witnesses = first_witnesses(tree_ids, transforms, root_preserving=False)
    root_witnesses = first_witnesses(tree_ids, transforms, root_preserving=True)
    exact_matches = [transform for transform in transforms if transform["signed_ray_match"]]
    root_exact_matches = [transform for transform in transforms if transform["root_preserving_signed_ray_match"]]

    return {
        "case_id": CASE_ID,
        "status": "signed_ray_symmetry_checked",
        "scope": {
            "tree_ids": tree_ids,
            "permutation_group": "vertex permutations preserving unordered opposite-edge pair {AB, CD}",
            "permutation_count": len(dense.opposite_edge_stabilizer_permutations()),
            "checked_transform_count": len(transforms),
        },
        "transport_rule": {
            "formula": "target_angle_sign = determinant_sign(isometry) * axis_orientation_sign * source_angle_sign",
            "determinant_sign_meaning": "+1 for proper rotation, -1 for improper/reflectional isometry",
            "axis_orientation_sign_meaning": "+1 if mapped oriented hinge axis agrees with target hinge axis labels, -1 otherwise",
        },
        "summary_metrics": {
            "signed_ray_exact_match_count": len(exact_matches),
            "root_preserving_signed_ray_exact_match_count": len(root_exact_matches),
            "all_signed_rays_same_orbit_ignoring_root": matrix_all_true(signed_matrix),
            "all_signed_rays_same_orbit_with_root_preserved": matrix_all_true(root_matrix),
            "signed_ray_orbit_classes_ignoring_root": orbit_classes_from_matrix(signed_matrix),
            "signed_ray_orbit_classes_root_preserving": orbit_classes_from_matrix(root_matrix),
        },
        "signed_ray_reachability_matrix_ignoring_root": signed_matrix,
        "signed_ray_reachability_matrix_root_preserving": root_matrix,
        "witnesses_ignoring_root": signed_witnesses,
        "witnesses_root_preserving": root_witnesses,
        "matching_transforms": exact_matches,
        "limitations": [
            "This checker certifies signed-ray equivalence under the finite vertex-permutation group only; it does not prove continuous path clearance.",
            "Root-preserving equivalence is reported separately because the motion scripts use root piece P0 for transform propagation.",
            "Physical hinge offsets, clearances, and printability are outside this check.",
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
                "signed_ray_exact_match_count": report["summary_metrics"]["signed_ray_exact_match_count"],
                "root_preserving_signed_ray_exact_match_count": report["summary_metrics"]["root_preserving_signed_ray_exact_match_count"],
                "all_signed_rays_same_orbit_ignoring_root": report["summary_metrics"]["all_signed_rays_same_orbit_ignoring_root"],
                "all_signed_rays_same_orbit_with_root_preserved": report["summary_metrics"]["all_signed_rays_same_orbit_with_root_preserved"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())