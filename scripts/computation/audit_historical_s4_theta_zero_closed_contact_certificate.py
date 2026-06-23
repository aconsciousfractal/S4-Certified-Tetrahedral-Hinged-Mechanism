"""Closed-contact theta=0 certificate for catalogued S4.

This audit is intentionally different from the strict-clearance reports:
theta=0 is the catalogued closed assembly, so zero-margin contacts are
expected. The script verifies closed-set contact semantics by checking that
all pieces lie in the ambient tetrahedron, have no positive-volume interior
overlap, and every pairwise intersection is a catalogued dissection contact.
"""

from __future__ import annotations

import itertools
import json
import math
import sys
from pathlib import Path

import numpy as np


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "theta_zero_closed_contact_certificate_report.json"
REPRESENTATIVES = {
    "CLASS_A_TREE007_TREE009": "TREE_007",
    "CLASS_B_TREE021_TREE093": "TREE_021",
}
TOLERANCE = 1.0e-8

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402
import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import audit_historical_s4_two_class_component_search as comp  # noqa: E402


RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def barycentric_coordinates(point: np.ndarray, tet: tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]) -> list[float]:
    a, b, c, d = tet
    matrix = np.column_stack([b - a, c - a, d - a])
    u, v, w = np.linalg.solve(matrix, point - a)
    return [float(1.0 - u - v - w), float(u), float(v), float(w)]


def containment_record(case: dict) -> dict:
    labels = case["labels"]
    ambient = (labels["A"], labels["B"], labels["C"], labels["D"])
    vertex_records = []
    max_negative_barycentric = 0.0
    max_excess_barycentric = 0.0
    for piece_id, piece in case["pieces_by_id"].items():
        for index, vertex in enumerate(piece):
            bary = barycentric_coordinates(vertex, ambient)
            min_bary = min(bary)
            max_bary = max(bary)
            max_negative_barycentric = max(max_negative_barycentric, max(0.0, -min_bary))
            max_excess_barycentric = max(max_excess_barycentric, max(0.0, max_bary - 1.0))
            vertex_records.append(
                {
                    "piece_id": piece_id,
                    "vertex_index": index,
                    "label": lib.label_for(vertex, labels),
                    "barycentric": [round(value, 15) for value in bary],
                    "inside_ambient_closed_tetrahedron": min_bary >= -TOLERANCE and max_bary <= 1.0 + TOLERANCE,
                }
            )
    return {
        "vertex_count": len(vertex_records),
        "all_piece_vertices_inside_ambient_closed_tetrahedron": all(
            record["inside_ambient_closed_tetrahedron"] for record in vertex_records
        ),
        "max_negative_barycentric": round(float(max_negative_barycentric), 15),
        "max_excess_barycentric": round(float(max_excess_barycentric), 15),
        "vertex_records": vertex_records,
    }


def volume_record(case: dict) -> dict:
    ambient_volume = float(lib.volume(edge_length=1.0))
    piece_volumes = {
        piece_id: float(lib.tet_volume_from_vertices(*piece))
        for piece_id, piece in case["pieces_by_id"].items()
    }
    piece_volume_sum = sum(piece_volumes.values())
    return {
        "ambient_volume": round(ambient_volume, 15),
        "piece_volumes": {piece_id: round(value, 15) for piece_id, value in piece_volumes.items()},
        "piece_volume_sum": round(piece_volume_sum, 15),
        "volume_error": round(abs(piece_volume_sum - ambient_volume), 15),
        "volume_sum_matches_ambient": abs(piece_volume_sum - ambient_volume) <= 1.0e-12,
    }


def contacts_by_pair(case: dict) -> dict[tuple[str, str], dict]:
    return {tuple(sorted(contact["pieces"])): contact for contact in case["contacts"]}


def pair_records(case: dict) -> list[dict]:
    contact_map = contacts_by_pair(case)
    records = []
    for left, right in itertools.combinations(case["piece_ids"], 2):
        pair = tuple(sorted([left, right]))
        has_overlap, min_overlap = lib.strict_interior_overlap(case["pieces_by_id"][left], case["pieces_by_id"][right])
        contact = contact_map.get(pair)
        records.append(
            {
                "pieces": list(pair),
                "catalogued_contact": contact is not None,
                "contact_id": contact["contact_id"] if contact else None,
                "contact_type": contact["type"] if contact else "none",
                "shared_vertices": contact["vertices"] if contact else [],
                "shared_vertex_count": len(contact["vertices"]) if contact else 0,
                "strict_interior_overlap": bool(has_overlap),
                "min_axis_overlap_proxy": round(float(min_overlap), 15),
                "closed_contact_semantics_status": (
                    "catalogued_zero_margin_contact_without_interior_overlap"
                    if contact is not None and not has_overlap
                    else "noncatalogued_or_overlapping_pair"
                ),
            }
        )
    return records


def zero_transform_record(case: dict, tree_id: str) -> dict:
    tree = comp.find_tree(case, tree_id)
    selected_hinges = batch.selected_hinges_for_tree(case, tree)
    zero_angles = {hinge["hinge_id"]: 0.0 for hinge in selected_hinges}
    transforms = lib.transforms_for_hinge_tree(
        case["piece_ids"],
        selected_hinges,
        case["labels"],
        zero_angles,
        root_piece="P0",
    )
    transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
    max_vertex_displacement = 0.0
    for piece_id, original_piece in case["pieces_by_id"].items():
        for original_vertex, transformed_vertex in zip(original_piece, transformed[piece_id]):
            max_vertex_displacement = max(
                max_vertex_displacement,
                float(np.linalg.norm(transformed_vertex - original_vertex)),
            )
    selected_hinge_pairs = [hinge["pieces"] for hinge in selected_hinges]
    selected_hinge_contact_types = []
    contact_map = contacts_by_pair(case)
    for hinge in selected_hinges:
        pair = tuple(sorted(hinge["pieces"]))
        contact = contact_map[pair]
        selected_hinge_contact_types.append(
            {
                "hinge_id": hinge["hinge_id"],
                "pieces": list(pair),
                "contact_id": contact["contact_id"],
                "contact_type": contact["type"],
                "axis_labels": hinge["axis_labels"],
            }
        )
    return {
        "tree_id": tree_id,
        "hinge_ids": tree["hinge_ids"],
        "selected_hinge_pairs": selected_hinge_pairs,
        "selected_hinge_contact_types": selected_hinge_contact_types,
        "zero_angle_transform_max_vertex_displacement": round(max_vertex_displacement, 15),
        "zero_angle_transforms_are_identity_on_vertices": max_vertex_displacement <= TOLERANCE,
    }


def build_report() -> dict:
    case = batch.build_case()
    containment = containment_record(case)
    volumes = volume_record(case)
    pairs = pair_records(case)
    representative_records = [
        {
            "class_id": class_id,
            **zero_transform_record(case, tree_id),
        }
        for class_id, tree_id in REPRESENTATIVES.items()
    ]
    face_contacts = [record for record in pairs if record["contact_type"] == "shared_face"]
    edge_contacts = [record for record in pairs if record["contact_type"] == "shared_edge"]
    noncatalogued = [record for record in pairs if not record["catalogued_contact"]]
    overlaps = [record for record in pairs if record["strict_interior_overlap"]]
    closed_certificate_completed = (
        containment["all_piece_vertices_inside_ambient_closed_tetrahedron"]
        and volumes["volume_sum_matches_ambient"]
        and not overlaps
        and not noncatalogued
        and all(record["zero_angle_transforms_are_identity_on_vertices"] for record in representative_records)
    )
    return {
        "case_id": CASE_ID,
        "status": (
            "theta_zero_closed_contact_certificate_completed"
            if closed_certificate_completed
            else "theta_zero_closed_contact_certificate_incomplete"
        ),
        "certificate_id": "S4-ZT-CLOSED-THETA0-2026-06-21",
        "semantics": {
            "theta_degrees": 0.0,
            "configuration": "catalogued_closed_s4_assembly",
            "contact_model": "closed-set non-interpenetration with intended zero-margin dissection contacts",
            "clearance_model": "not a positive-clearance certificate",
            "sat_method": "strict convex SAT; touching/contact allowed, positive-volume interior overlap blocked",
            "tolerance": TOLERANCE,
        },
        "representatives": REPRESENTATIVES,
        "containment": containment,
        "volume_check": volumes,
        "pair_contact_records": pairs,
        "representative_zero_transform_records": representative_records,
        "summary_metrics": {
            "piece_count": len(case["piece_ids"]),
            "pair_count": len(pairs),
            "catalogued_contact_pair_count": sum(1 for record in pairs if record["catalogued_contact"]),
            "shared_face_contact_pair_count": len(face_contacts),
            "shared_edge_contact_pair_count": len(edge_contacts),
            "noncatalogued_pair_count": len(noncatalogued),
            "strict_interior_overlap_pair_count": len(overlaps),
            "all_piece_vertices_inside_ambient_closed_tetrahedron": containment[
                "all_piece_vertices_inside_ambient_closed_tetrahedron"
            ],
            "volume_sum_matches_ambient": volumes["volume_sum_matches_ambient"],
            "all_zero_angle_transforms_identity_on_vertices": all(
                record["zero_angle_transforms_are_identity_on_vertices"] for record in representative_records
            ),
            "theta_zero_closed_contact_certificate_completed": closed_certificate_completed,
        },
        "limitations": [
            "This certifies the catalogued theta=0 closed assembly under zero-thickness closed-contact semantics.",
            "This is not a positive-clearance certificate at theta=0.",
            "This does not add physical hinge thickness, offsets, tolerances, sweep volumes, CAD, or printability.",
            "This does not prove dynamic connectedness between TREE_007 and TREE_021.",
            "The one-sided open motion remains supplied by the separate open-domain certificate.",
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
                "certificate_id": report["certificate_id"],
                "summary_metrics": report["summary_metrics"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
