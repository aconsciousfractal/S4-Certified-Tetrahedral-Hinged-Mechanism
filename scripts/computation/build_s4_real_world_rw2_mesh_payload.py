#!/usr/bin/env python
"""Build RW2 mesh/CAD payload artifacts for the S4 real-world branch."""

from __future__ import annotations

from collections import Counter
import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULT_ROOT = ROOT / "results" / CASE_ID / "real_world"
MESH_ROOT = RESULT_ROOT / "meshes"
BODY_ROOT = MESH_ROOT / "body_solids"
AXIS_ROOT = MESH_ROOT / "hinge_axes"
DOC_PATH = ROOT / "docs" / "S4_RW2_MESH_PAYLOAD_ADAPTER.md"
JSON_PATH = RESULT_ROOT / "rw2_mesh_payload_manifest.json"

RW1_PATH = RESULT_ROOT / "rw1_physical_source_lock.json"
GEOMETRY_PATH = ROOT / "results" / CASE_ID / "geometry_payload.json"
HINGE_CANDIDATE_PATH = ROOT / "results" / CASE_ID / "hinge_candidate_report.json"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(x).replace("\n", " ") for x in row) + " |")
    return "\n".join(out)


def sub(a: list[float], b: list[float]) -> list[float]:
    return [a[i] - b[i] for i in range(3)]


def cross(a: list[float], b: list[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def dot(a: list[float], b: list[float]) -> float:
    return sum(a[i] * b[i] for i in range(3))


def norm(a: list[float]) -> float:
    return math.sqrt(dot(a, a))


def tetra_volume(vertices: dict[str, list[float]]) -> float:
    labels = list(vertices)
    p0, p1, p2, p3 = (vertices[label] for label in labels)
    return abs(dot(sub(p1, p0), cross(sub(p2, p0), sub(p3, p0)))) / 6.0


def face_indices(piece: dict[str, Any]) -> list[list[int]]:
    labels = [v["label"] for v in piece["vertices"]]
    label_to_index = {label: i + 1 for i, label in enumerate(labels)}
    return [[label_to_index[label] for label in face["labels"]] for face in piece["faces"]]


def mesh_edge_counts(piece: dict[str, Any]) -> Counter[tuple[str, str]]:
    counts: Counter[tuple[str, str]] = Counter()
    for face in piece["faces"]:
        labels = face["labels"]
        for i in range(3):
            edge = tuple(sorted((labels[i], labels[(i + 1) % 3])))
            counts[edge] += 1
    return counts


def piece_vertices(piece: dict[str, Any]) -> dict[str, list[float]]:
    return {v["label"]: [float(x) for x in v["coordinates"]] for v in piece["vertices"]}


def write_piece_obj(piece: dict[str, Any], out_path: Path) -> None:
    lines = [
        f"# S4 RW2 exact body solid payload",
        f"# piece_id: {piece['piece_id']}",
        f"# source: {GEOMETRY_PATH.as_posix()}",
        "# units: model units; physical scale is exploratory from RW1",
        "# no hinge hardware, clearance, boss, pin, or printability geometry included",
        f"o {piece['piece_id']}",
    ]
    for vertex in piece["vertices"]:
        x, y, z = vertex["coordinates"]
        lines.append(f"v {x:.12f} {y:.12f} {z:.12f} # {vertex['label']}")
    for face in face_indices(piece):
        lines.append("f " + " ".join(str(i) for i in face))
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def write_combined_obj(pieces: list[dict[str, Any]], out_path: Path) -> None:
    lines = [
        "# S4 RW2 exact body solid combined payload",
        f"# source: {GEOMETRY_PATH.as_posix()}",
        "# units: model units; physical scale is exploratory from RW1",
        "# no hinge hardware, clearance, boss, pin, or printability geometry included",
    ]
    offset = 0
    for piece in pieces:
        lines.append(f"g {piece['piece_id']}")
        for vertex in piece["vertices"]:
            x, y, z = vertex["coordinates"]
            lines.append(f"v {x:.12f} {y:.12f} {z:.12f} # {piece['piece_id']}:{vertex['label']}")
        for face in face_indices(piece):
            lines.append("f " + " ".join(str(i + offset) for i in face))
        offset += len(piece["vertices"])
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def candidate_by_id(candidates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["hinge_id"]: item for item in candidates["candidate_hinges"]}


def unique_axis_key(axis_labels: list[str]) -> str:
    return "__".join(axis_labels)


def build_axis_payload(rw1: dict[str, Any], candidates: dict[str, Any]) -> dict[str, Any]:
    by_id = candidate_by_id(candidates)
    trees = [
        rw1["hinge_tree_source"]["first_tree"],
        rw1["hinge_tree_source"]["second_tree"],
    ]
    unique_axes: dict[str, dict[str, Any]] = {}
    tree_payloads = []
    for tree in trees:
        hinge_payloads = []
        for hinge_id in tree["hinge_ids"]:
            if hinge_id not in by_id:
                raise KeyError(f"hinge id missing from candidate report: {hinge_id}")
            item = by_id[hinge_id]
            length = float(item["axis_length"])
            if length <= 0:
                raise ValueError(f"zero-length hinge axis: {hinge_id}")
            axis_labels = list(item["axis_labels"])
            key = unique_axis_key(axis_labels)
            unique_axes.setdefault(
                key,
                {
                    "axis_key": key,
                    "axis_labels": axis_labels,
                    "axis_points": item["axis_points"],
                    "axis_length_model_units": length,
                    "axis_class": item["axis_class"],
                    "axis_support": item["axis_support"],
                    "source_hinge_ids": [],
                },
            )
            if hinge_id not in unique_axes[key]["source_hinge_ids"]:
                unique_axes[key]["source_hinge_ids"].append(hinge_id)
            hinge_payloads.append(
                {
                    "hinge_id": hinge_id,
                    "piece_edge": tree["piece_edges"][tree["hinge_ids"].index(hinge_id)],
                    "contact_id": tree["contact_ids"][tree["hinge_ids"].index(hinge_id)],
                    "axis_key": key,
                    "axis_labels": axis_labels,
                    "axis_points": item["axis_points"],
                    "axis_length_model_units": length,
                    "axis_support": item["axis_support"],
                    "axis_placeholder_only": True,
                }
            )
        tree_payloads.append(
            {
                "tree_id": tree["tree_id"],
                "role": "first_test" if tree["tree_id"] == rw1["first_tree_to_test"] else "second_replay",
                "hinges": hinge_payloads,
            }
        )
    return {"trees": tree_payloads, "unique_axes": list(unique_axes.values())}


def write_axis_obj(axis_payload: dict[str, Any], out_path: Path) -> None:
    lines = [
        "# S4 RW2 hinge-axis placeholder payload",
        f"# source: {HINGE_CANDIDATE_PATH.as_posix()}",
        "# line elements only; not hinge hardware, not CAD validity, not printability",
        "o S4_RW2_hinge_axis_placeholders",
    ]
    index = 1
    for axis in axis_payload["unique_axes"]:
        labels = axis["axis_labels"]
        points = axis["axis_points"]
        lines.append(f"g axis_{axis['axis_key']}")
        for point, label in zip(points, labels):
            lines.append(f"v {point[0]:.12f} {point[1]:.12f} {point[2]:.12f} # {label}")
        lines.append(f"l {index} {index + 1}")
        index += 2
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def validate_piece(piece: dict[str, Any]) -> dict[str, Any]:
    vertices = piece_vertices(piece)
    edge_counts = mesh_edge_counts(piece)
    watertight = all(count == 2 for count in edge_counts.values()) and len(edge_counts) == 6
    volume = tetra_volume(vertices)
    return {
        "piece_id": piece["piece_id"],
        "vertex_count": len(piece["vertices"]),
        "face_count": len(piece["faces"]),
        "triangle_faces_only": all(len(face["labels"]) == 3 for face in piece["faces"]),
        "unique_mesh_edge_count": len(edge_counts),
        "all_mesh_edges_double_covered": watertight,
        "computed_volume_model_units": volume,
        "source_volume_model_units": piece.get("volume"),
        "positive_volume": volume > 0,
    }


def build_manifest() -> dict[str, Any]:
    rw1 = load_json(RW1_PATH)
    geometry = load_json(GEOMETRY_PATH)
    candidates = load_json(HINGE_CANDIDATE_PATH)

    if rw1.get("status") != "source_lock_created_not_fabrication_ready":
        raise ValueError("RW1 source lock is missing or not in the expected status")
    if geometry.get("status") != "geometry_valid":
        raise ValueError("Geometry payload is missing or invalid")
    if candidates.get("status") != "candidate_axes_enumerated":
        raise ValueError("Hinge candidate report is missing or invalid")

    BODY_ROOT.mkdir(parents=True, exist_ok=True)
    AXIS_ROOT.mkdir(parents=True, exist_ok=True)

    pieces = geometry["pieces"]
    piece_exports = []
    validations = []
    for piece in pieces:
        out_path = BODY_ROOT / f"{piece['piece_id']}.obj"
        write_piece_obj(piece, out_path)
        validation = validate_piece(piece)
        validations.append(validation)
        piece_exports.append(
            {
                "piece_id": piece["piece_id"],
                "path": out_path.relative_to(ROOT).as_posix(),
                "format": "OBJ",
                "geometry_role": "exact_body_solid",
                "hardware_features": False,
            }
        )

    combined_path = BODY_ROOT / "s4_body_solids_combined.obj"
    write_combined_obj(pieces, combined_path)

    axis_payload = build_axis_payload(rw1, candidates)
    axis_json_path = AXIS_ROOT / "hinge_axis_placeholders.json"
    axis_obj_path = AXIS_ROOT / "hinge_axis_placeholders.obj"
    axis_json_path.write_text(
        json.dumps(axis_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    write_axis_obj(axis_payload, axis_obj_path)

    acceptance = {
        "rw1_source_lock_present": True,
        "piece_count_is_4": len(pieces) == 4,
        "piece_objs_written": len(piece_exports) == 4,
        "combined_obj_written": combined_path.exists(),
        "axis_placeholder_json_written": axis_json_path.exists(),
        "axis_placeholder_obj_written": axis_obj_path.exists(),
        "all_piece_meshes_tetrahedral_closed": all(
            item["vertex_count"] == 4
            and item["face_count"] == 4
            and item["triangle_faces_only"]
            and item["all_mesh_edges_double_covered"]
            and item["positive_volume"]
            for item in validations
        ),
        "tree_007_axes_present": any(item["tree_id"] == "TREE_007" for item in axis_payload["trees"]),
        "tree_021_axes_present": any(item["tree_id"] == "TREE_021" for item in axis_payload["trees"]),
        "all_axes_nonzero_length": all(
            axis["axis_length_model_units"] > 0 for axis in axis_payload["unique_axes"]
        ),
        "hardware_geometry_absent": True,
        "printability_validation_status": "not_run",
        "cad_validity_status": "payload_only_not_cad",
    }

    return {
        "manifest_id": "S4-RW2-MESH-PAYLOAD-ADAPTER-2026-06-22",
        "date": DATE,
        "case_id": CASE_ID,
        "status": "mesh_payload_created_not_fabrication_ready",
        "precondition": {
            "rw1_source_lock": RW1_PATH.as_posix(),
            "rw1_status": rw1.get("status"),
            "geometry_source": GEOMETRY_PATH.as_posix(),
            "hinge_candidate_source": HINGE_CANDIDATE_PATH.as_posix(),
        },
        "scope": {
            "body_solids": "exact median-plane S4 piece solids exported as OBJ triangle meshes",
            "hinge_axes": "named line-placeholder payloads for TREE_007 and TREE_021",
            "excluded": [
                "hinge bosses",
                "pins",
                "holes",
                "cutbacks",
                "finite-thickness clearance",
                "printability",
                "fabrication readiness",
                "prototype validation",
            ],
        },
        "exports": {
            "piece_objs": piece_exports,
            "combined_obj": combined_path.relative_to(ROOT).as_posix(),
            "hinge_axis_json": axis_json_path.relative_to(ROOT).as_posix(),
            "hinge_axis_obj": axis_obj_path.relative_to(ROOT).as_posix(),
        },
        "piece_validations": validations,
        "hinge_axis_payload": axis_payload,
        "acceptance": acceptance,
        "next_task": "RW3 kinematics adapter: attach named body solids to TREE_007/TREE_021 rigid transforms and replay zero-thickness motion before any hardware geometry.",
    }


def build_doc(manifest: dict[str, Any]) -> str:
    export_rows = [
        [item["piece_id"], item["format"], item["path"], item["geometry_role"], item["hardware_features"]]
        for item in manifest["exports"]["piece_objs"]
    ]
    validation_rows = [
        [
            item["piece_id"],
            item["vertex_count"],
            item["face_count"],
            item["unique_mesh_edge_count"],
            item["all_mesh_edges_double_covered"],
            f"{item['computed_volume_model_units']:.15f}",
        ]
        for item in manifest["piece_validations"]
    ]
    axis_rows = []
    for tree in manifest["hinge_axis_payload"]["trees"]:
        for hinge in tree["hinges"]:
            axis_rows.append(
                [
                    tree["tree_id"],
                    hinge["hinge_id"],
                    "-".join(hinge["piece_edge"]),
                    "-".join(hinge["axis_labels"]),
                    hinge["axis_support"],
                    hinge["axis_length_model_units"],
                ]
            )
    acceptance_rows = [[key, value] for key, value in manifest["acceptance"].items()]
    return f"""# S4 RW2 Mesh Payload Adapter

Status: mesh payload created; not fabrication ready.
Date: {DATE}

## Scope

RW2 exports the exact S4 body solids and named hinge-axis placeholders from
the RW1 source lock.  It is a payload adapter only.  It does not create hinge
hardware, does not perform CAD validity checks, does not certify finite-
thickness clearance, and does not certify printability.

## Sources

| Source | Path |
| --- | --- |
| RW1 source lock | `{manifest['precondition']['rw1_source_lock']}` |
| exact geometry payload | `{manifest['precondition']['geometry_source']}` |
| hinge candidate report | `{manifest['precondition']['hinge_candidate_source']}` |

## Body Solid Exports

{table(['Piece', 'Format', 'Path', 'Role', 'Hardware features'], export_rows)}

Combined body OBJ:

`{manifest['exports']['combined_obj']}`

## Mesh Integrity Checks

These are topology sanity checks for the exported tetrahedral body meshes.
They are not printability or CAD-manifold certifications.

{table(['Piece', 'Vertices', 'Faces', 'Unique edges', 'Edges double covered', 'Computed volume'], validation_rows)}

## Hinge-Axis Placeholders

Axis JSON:

`{manifest['exports']['hinge_axis_json']}`

Axis OBJ line payload:

`{manifest['exports']['hinge_axis_obj']}`

{table(['Tree', 'Hinge', 'Piece edge', 'Axis labels', 'Support', 'Length'], axis_rows)}

## Explicit Nonclaims

{chr(10).join('- ' + item for item in manifest['scope']['excluded'])}

## Acceptance

{table(['Check', 'Value'], acceptance_rows)}

## Next Task

{manifest['next_task']}
"""


def main() -> int:
    manifest = build_manifest()
    JSON_PATH.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    DOC_PATH.write_text(build_doc(manifest).rstrip() + "\n", encoding="utf-8", newline="\n")

    checks_ok = all(value is True or value in {"not_run", "payload_only_not_cad"} for value in manifest["acceptance"].values())
    print(f"rw2_mesh_payload_created={checks_ok}")
    print(f"piece_obj_count={len(manifest['exports']['piece_objs'])}")
    print(f"unique_axis_count={len(manifest['hinge_axis_payload']['unique_axes'])}")
    print(f"status={manifest['status']}")
    print(f"wrote {DOC_PATH.relative_to(ROOT).as_posix()}")
    print(f"wrote {JSON_PATH.relative_to(ROOT).as_posix()}")
    return 0 if checks_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
