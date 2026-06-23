"""Audit the historical S4 median-plane dissection for hinge candidates.

This script stops at contact, edge-hinge, and connected hinge-tree enumeration.
It does not claim local mobility or collision-free motion for S4.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def build_reports() -> dict[str, dict]:
    A, B, C, D = lib.regular_tetrahedron(edge_length=1.0)
    labels = lib.canonical_labels(A, B, C, D)
    pieces = lib.dissections.dissect_n4(A, B, C, D)
    piece_records = [lib.piece_record(f"P{i}", piece, labels) for i, piece in enumerate(pieces)]
    contacts = lib.extract_contacts(piece_records)
    hinges = lib.enumerate_candidate_hinges(contacts, labels, lib.ambient_faces(A, B, C, D))
    lib.augment_hinge_support(hinges, labels, lib.ambient_edges(A, B, C, D))
    piece_ids = [piece["piece_id"] for piece in piece_records]
    hinge_trees = lib.enumerate_hinge_trees(piece_ids, hinges)

    geometry_payload = {
        "case_id": CASE_ID,
        "status": "geometry_valid",
        "source_constructor": "../06-computational/src/dissections.py::dissect_n4",
        "ambient": {
            "polyhedron": "regular_tetrahedron",
            "edge_length": 1,
            "vertices": {name: lib.as_list(labels[name]) for name in ["A", "B", "C", "D"]},
            "volume": round(float(lib.volume(edge_length=1.0)), 15),
        },
        "pieces": piece_records,
        "checks": {
            "piece_count": len(piece_records),
            "piece_volume_sum": round(sum(piece["volume"] for piece in piece_records), 15),
            "ambient_volume": round(float(lib.volume(edge_length=1.0)), 15),
            "volume_error": round(abs(sum(piece["volume"] for piece in piece_records) - float(lib.volume(edge_length=1.0))), 15),
            "congruent_edge_spectra": len({tuple(piece["edge_spectrum"]) for piece in piece_records}) == 1,
        },
    }

    hinge_candidate_report = {
        "case_id": CASE_ID,
        "status": "candidate_axes_enumerated",
        "contact_graph": lib.contact_graph_summary(contacts),
        "contacts": contacts,
        "candidate_hinges": hinges,
        "summary": {
            "piece_count": len(piece_records),
            "contact_count": len(contacts),
            "face_contact_count": sum(1 for contact in contacts if contact["type"] == "shared_face"),
            "edge_only_contact_count": sum(1 for contact in contacts if contact["type"] == "shared_edge"),
            "candidate_edge_hinge_count": len(hinges),
            "internal_axis_candidate_count": sum(1 for hinge in hinges if hinge["axis_support"] == "internal_segment"),
            "ambient_edge_axis_candidate_count": sum(1 for hinge in hinges if hinge["axis_support"] == "ambient_edge_subsegment"),
            "ambient_face_axis_candidate_count": sum(1 for hinge in hinges if hinge["axis_support"] == "ambient_face_segment"),
        },
    }

    hinge_tree_report = {
        "case_id": CASE_ID,
        "status": "hinge_trees_enumerated",
        "tree_count": len(hinge_trees),
        "boundary_only_tree_count": sum(1 for tree in hinge_trees if tree["internal_axis_count"] == 0),
        "recommended_tree": hinge_trees[0] if hinge_trees else None,
        "trees": hinge_trees,
        "limitations": [
            "Tree enumeration is combinatorial only; it does not prove local mobility.",
            "Trees are ranked by fewest internal axes, then most ambient-edge-supported axes, then total axis length.",
            "S4 motion and collision checks require a separate kinematic audit.",
        ],
    }

    return {
        "geometry_payload.json": geometry_payload,
        "hinge_candidate_report.json": hinge_candidate_report,
        "hinge_tree_report.json": hinge_tree_report,
    }


def main() -> int:
    outputs = build_reports()
    for filename, payload in outputs.items():
        lib.write_json(RESULTS_DIR / filename, payload)

    hinge_candidate_report = outputs["hinge_candidate_report.json"]
    hinge_tree_report = outputs["hinge_tree_report.json"]
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_dir": str(RESULTS_DIR),
                "status": hinge_tree_report["status"],
                "candidate_hinges": len(hinge_candidate_report["candidate_hinges"]),
                "hinge_trees": hinge_tree_report["tree_count"],
                "recommended_tree": hinge_tree_report["recommended_tree"]["tree_id"] if hinge_tree_report["recommended_tree"] else None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())