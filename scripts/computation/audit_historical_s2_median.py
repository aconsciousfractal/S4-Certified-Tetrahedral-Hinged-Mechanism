"""Audit the historical S2 median dissection for hinge candidates and motion."""

from __future__ import annotations

import json
import sys
from pathlib import Path


CASE_ID = "historical_s2_median"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID


def build_reports() -> dict[str, dict]:
    A, B, C, D = lib.regular_tetrahedron(edge_length=1.0)
    labels = lib.canonical_labels(A, B, C, D)
    pieces = lib.dissections.dissect_n2(A, B, C, D)
    piece_records = [lib.piece_record(f"P{i}", piece, labels) for i, piece in enumerate(pieces)]
    contacts = lib.extract_contacts(piece_records)
    hinges = lib.enumerate_candidate_hinges(contacts, labels, lib.ambient_faces(A, B, C, D))
    recommended_hinge = next(
        (hinge for hinge in hinges if hinge["axis_labels"] == ["A", "B"]),
        hinges[0] if hinges else None,
    )

    geometry_payload = {
        "case_id": CASE_ID,
        "status": "geometry_valid",
        "source_constructor": "../06-computational/src/dissections.py::dissect_n2",
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

    hinge_report = {
        "case_id": CASE_ID,
        "status": "candidate_axes_enumerated",
        "contacts": contacts,
        "candidate_hinges": hinges,
        "recommended_first_hinge": recommended_hinge["hinge_id"] if recommended_hinge else None,
        "notes": [
            "S2 has one shared triangular contact face: A-B-M_CD.",
            "The three edge-hinge axes on that contact face lie on the boundary of the ambient tetrahedron.",
            "The A-B axis is the recommended first benchmark because it is an original tetrahedron edge.",
        ],
    }

    motion_reports = []
    if recommended_hinge is not None:
        motion_reports.append(lib.single_hinge_motion_audit(pieces[0], pieces[1], recommended_hinge))

    motion_report = {
        "case_id": CASE_ID,
        "status": motion_reports[0]["status"] if motion_reports else "not_started",
        "selected_hinge": recommended_hinge["hinge_id"] if recommended_hinge else None,
        "reports": motion_reports,
        "limitations": [
            "This is a sampled zero-thickness rigid-body audit, not a physical hinge-offset prototype.",
            "Only the recommended A-B hinge is motion-sampled in this first report.",
            "The SAT check treats touching as allowed and flags only positive-volume interior overlap.",
        ],
    }

    return {
        "geometry_payload.json": geometry_payload,
        "hinge_candidate_report.json": hinge_report,
        "motion_report_ab_axis.json": motion_report,
    }


def main() -> int:
    outputs = build_reports()
    for filename, payload in outputs.items():
        lib.write_json(RESULTS_DIR / filename, payload)

    motion_report = outputs["motion_report_ab_axis.json"]
    print(
        json.dumps(
            {
                "case_id": CASE_ID,
                "results_dir": str(RESULTS_DIR),
                "status": motion_report["status"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())