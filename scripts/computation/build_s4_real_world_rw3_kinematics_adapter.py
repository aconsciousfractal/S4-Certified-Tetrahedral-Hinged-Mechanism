#!/usr/bin/env python
"""Build RW3 kinematics adapter artifacts for the S4 real-world branch.

RW3 attaches the exact RW2 body solids to the existing zero-thickness rigid
transforms for TREE_007 and TREE_021.  It is still not a hardware, CAD,
finite-thickness, printability, or prototype-validity artifact.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
DATE = "2026-06-22"
CASE_ID = "historical_s4_median_planes"
RESULTS_ROOT = ROOT / "results" / CASE_ID
RESULT_ROOT = RESULTS_ROOT / "real_world"
KINEMATICS_ROOT = RESULT_ROOT / "kinematics"
SNAPSHOT_ROOT = KINEMATICS_ROOT / "snapshots"
DOC_PATH = ROOT / "docs" / "S4_RW3_KINEMATICS_ADAPTER.md"
JSON_PATH = RESULT_ROOT / "rw3_kinematics_adapter_manifest.json"

RW1_PATH = RESULT_ROOT / "rw1_physical_source_lock.json"
RW2_PATH = RESULT_ROOT / "rw2_mesh_payload_manifest.json"
GEOMETRY_PATH = RESULTS_ROOT / "geometry_payload.json"
DENSE_REPORT_PATH = RESULTS_ROOT / "ambient_edge_dense_refinement_report.json"

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import audit_historical_s4_boundary_tree_batch as batch  # noqa: E402
import mechanical_audit_lib as lib  # noqa: E402


TARGET_TREES = ["TREE_007", "TREE_021"]
SAMPLE_THETA_DEGREES = [0.0, 0.5, 1.0, 5.0, 15.0, 30.0, 60.0, 90.0, 120.0]
SNAPSHOT_THETA_DEGREES = {0.0, 60.0, 120.0}
ROOT_PIECE = "P0"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(lib.json_ready(payload), indent=2) + "\n", encoding="utf-8", newline="\n")


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def table(headers: list[str], rows: list[list[Any]]) -> str:
    out = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        out.append("| " + " | ".join(str(item).replace("\n", " ") for item in row) + " |")
    return "\n".join(out)


def find_tree(case: dict[str, Any], tree_id: str) -> dict[str, Any]:
    tree = next((candidate for candidate in case["hinge_trees"] if candidate["tree_id"] == tree_id), None)
    if tree is None:
        raise RuntimeError(f"tree not found in reconstructed case: {tree_id}")
    return tree


def dense_signs_by_tree(dense_report: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {
        record["tree_id"]: {hinge_id: int(sign) for hinge_id, sign in record["ray_signs_by_hinge"].items()}
        for record in dense_report["tree_reports"]
        if record["tree_id"] in TARGET_TREES
    }


def rw2_hinges_by_tree(rw2: dict[str, Any]) -> dict[str, list[str]]:
    return {
        tree["tree_id"]: [hinge["hinge_id"] for hinge in tree["hinges"]]
        for tree in rw2["hinge_axis_payload"]["trees"]
        if tree["tree_id"] in TARGET_TREES
    }


def signed_degrees(tree: dict[str, Any], signs_by_hinge: dict[str, int], theta_degrees: float) -> dict[str, float]:
    return {
        hinge_id: float(signs_by_hinge[hinge_id]) * float(theta_degrees)
        for hinge_id in tree["hinge_ids"]
    }


def transforms_for_sample(
    case: dict[str, Any],
    tree: dict[str, Any],
    signs_by_hinge: dict[str, int],
    theta_degrees: float,
) -> tuple[dict[str, dict[str, np.ndarray]], dict[str, float]]:
    degrees_by_hinge = signed_degrees(tree, signs_by_hinge, theta_degrees)
    angles = {hinge_id: math.radians(degrees) for hinge_id, degrees in degrees_by_hinge.items()}
    selected_hinges = batch.selected_hinges_for_tree(case, tree)
    transforms = lib.transforms_for_hinge_tree(
        case["piece_ids"],
        selected_hinges,
        case["labels"],
        angles,
        root_piece=ROOT_PIECE,
    )
    return transforms, degrees_by_hinge


def transform_quality(transforms: dict[str, dict[str, np.ndarray]]) -> dict[str, float]:
    max_orthogonality_error = 0.0
    max_det_error = 0.0
    max_translation_norm = 0.0
    for transform in transforms.values():
        R = transform["R"]
        t = transform["t"]
        max_orthogonality_error = max(max_orthogonality_error, float(np.linalg.norm(R.T @ R - np.eye(3))))
        max_det_error = max(max_det_error, abs(float(np.linalg.det(R)) - 1.0))
        max_translation_norm = max(max_translation_norm, float(np.linalg.norm(t)))
    return {
        "max_orthogonality_error": round(max_orthogonality_error, 15),
        "max_det_error": round(max_det_error, 15),
        "max_translation_norm": round(max_translation_norm, 15),
    }


def theta_zero_identity_error(transforms: dict[str, dict[str, np.ndarray]]) -> float:
    err = 0.0
    for transform in transforms.values():
        err = max(err, float(np.linalg.norm(transform["R"] - np.eye(3))))
        err = max(err, float(np.linalg.norm(transform["t"])))
    return round(err, 15)


def compact_transforms(transforms: dict[str, dict[str, np.ndarray]]) -> dict[str, dict[str, Any]]:
    return {
        piece_id: {
            "R": np.round(transform["R"], 12).tolist(),
            "t": np.round(transform["t"], 12).tolist(),
        }
        for piece_id, transform in sorted(transforms.items())
    }


def transformed_piece_vertices(geometry: dict[str, Any], transforms: dict[str, dict[str, np.ndarray]]) -> dict[str, dict[str, list[float]]]:
    out: dict[str, dict[str, list[float]]] = {}
    for piece in geometry["pieces"]:
        piece_id = piece["piece_id"]
        transform = transforms[piece_id]
        vertices: dict[str, list[float]] = {}
        for vertex in piece["vertices"]:
            point = np.asarray(vertex["coordinates"], dtype=float)
            moved = transform["R"] @ point + transform["t"]
            vertices[vertex["label"]] = [round(float(value), 12) for value in moved]
        out[piece_id] = vertices
    return out


def face_indices(piece: dict[str, Any]) -> list[list[int]]:
    labels = [vertex["label"] for vertex in piece["vertices"]]
    label_to_index = {label: index + 1 for index, label in enumerate(labels)}
    return [[label_to_index[label] for label in face["labels"]] for face in piece["faces"]]


def write_snapshot_obj(
    geometry: dict[str, Any],
    transforms: dict[str, dict[str, np.ndarray]],
    tree_id: str,
    theta_degrees: float,
    out_path: Path,
) -> None:
    moved = transformed_piece_vertices(geometry, transforms)
    lines = [
        "# S4 RW3 transformed exact body-solid snapshot",
        f"# tree_id: {tree_id}",
        f"# theta_degrees: {theta_degrees:.8f}",
        "# source geometry: RW2 exact body solids; no hardware geometry included",
        "# units: model units; physical scale remains exploratory from RW1",
        f"o S4_RW3_{tree_id}_theta_{theta_degrees:.3f}".replace(".", "_"),
    ]
    offset = 0
    for piece in geometry["pieces"]:
        piece_id = piece["piece_id"]
        lines.append(f"g {piece_id}")
        for vertex in piece["vertices"]:
            label = vertex["label"]
            x, y, z = moved[piece_id][label]
            lines.append(f"v {x:.12f} {y:.12f} {z:.12f} # {piece_id}:{label}")
        for face in face_indices(piece):
            lines.append("f " + " ".join(str(index + offset) for index in face))
        offset += len(piece["vertices"])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def snapshot_name(tree_id: str, theta_degrees: float) -> str:
    scaled = int(round(theta_degrees * 1000))
    return f"{tree_id.lower()}_theta_{scaled:06d}.obj"


def sample_tree(
    case: dict[str, Any],
    geometry: dict[str, Any],
    tree: dict[str, Any],
    signs_by_hinge: dict[str, int],
) -> dict[str, Any]:
    tree_id = tree["tree_id"]
    samples = []
    snapshot_exports = []
    for theta in SAMPLE_THETA_DEGREES:
        transforms, degrees_by_hinge = transforms_for_sample(case, tree, signs_by_hinge, theta)
        transformed = lib.transform_pieces(case["pieces_by_id"], transforms)
        collision = lib.collision_report(transformed)
        quality = transform_quality(transforms)
        sample = {
            "theta_degrees": theta,
            "signed_degrees_by_hinge": degrees_by_hinge,
            "status": collision["status"],
            "collisions": collision["collisions"],
            "minimum_axis_overlap_proxy": collision["minimum_axis_overlap_proxy"],
            "transform_quality": quality,
            "piece_transforms": compact_transforms(transforms),
        }
        if theta == 0.0:
            sample["theta_zero_identity_error"] = theta_zero_identity_error(transforms)
        if theta in SNAPSHOT_THETA_DEGREES:
            out_path = SNAPSHOT_ROOT / snapshot_name(tree_id, theta)
            write_snapshot_obj(geometry, transforms, tree_id, theta, out_path)
            snapshot_exports.append(
                {
                    "tree_id": tree_id,
                    "theta_degrees": theta,
                    "format": "OBJ",
                    "geometry_role": "transformed_exact_body_solid_snapshot",
                    "hardware_features": False,
                    "path": rel(out_path),
                }
            )
        samples.append(sample)
    return {
        "tree_id": tree_id,
        "hinge_ids": list(tree["hinge_ids"]),
        "sign_vector_by_hinge": signs_by_hinge,
        "sample_count": len(samples),
        "samples": samples,
        "snapshot_exports": snapshot_exports,
    }


def build_doc(manifest: dict[str, Any]) -> str:
    rows = []
    for tree in manifest["trees"]:
        statuses = sorted({sample["status"] for sample in tree["samples"]})
        rows.append(
            [
                tree["tree_id"],
                ", ".join(tree["hinge_ids"]),
                ", ".join(f"{hinge}:{sign:+d}" for hinge, sign in tree["sign_vector_by_hinge"].items()),
                tree["sample_count"],
                ", ".join(statuses),
                len(tree["snapshot_exports"]),
            ]
        )

    sample_rows = []
    for tree in manifest["trees"]:
        for sample in tree["samples"]:
            sample_rows.append(
                [
                    tree["tree_id"],
                    sample["theta_degrees"],
                    sample["status"],
                    sample["minimum_axis_overlap_proxy"],
                    sample["transform_quality"]["max_orthogonality_error"],
                    sample["transform_quality"]["max_det_error"],
                ]
            )

    snapshot_rows = [
        [item["tree_id"], item["theta_degrees"], item["path"], item["hardware_features"]]
        for item in manifest["exports"]["snapshot_objs"]
    ]

    acceptance_rows = [[key, value] for key, value in manifest["acceptance"].items()]

    return "\n".join(
        [
            "# S4 RW3 Kinematics Adapter",
            "",
            "Status: kinematics adapter created; not hardware-ready.",
            f"Date: {DATE}",
            "",
            "## Scope",
            "",
            "RW3 attaches the RW2 exact body-solid payload to the existing zero-thickness",
            "rigid transforms for `TREE_007` and `TREE_021`. It replays the certified",
            "one-parameter sign rays as transform ledgers and lightweight OBJ snapshots.",
            "",
            "It does not add hinge hardware, finite-thickness offsets, cutbacks, pins,",
            "holes, CAD validity checks, printability checks, or prototype validation.",
            "",
            "## Sources",
            "",
            table(
                ["Source", "Path"],
                [
                    ["RW1 source lock", str(RW1_PATH)],
                    ["RW2 mesh payload", str(RW2_PATH)],
                    ["geometry payload", str(GEOMETRY_PATH)],
                    ["dense zero-thickness sign report", str(DENSE_REPORT_PATH)],
                    ["kinematics library", str(ROOT / "scripts" / "mechanical_audit_lib.py")],
                ],
            ),
            "",
            "## Tree Replay Summary",
            "",
            table(["Tree", "Hinges", "Signs", "Samples", "Statuses", "OBJ snapshots"], rows),
            "",
            "## Sample Ledger",
            "",
            table(
                ["Tree", "Theta degrees", "Status", "Minimum axis overlap proxy", "Max orthogonality error", "Max det error"],
                sample_rows,
            ),
            "",
            "## Snapshot Exports",
            "",
            table(["Tree", "Theta degrees", "Path", "Hardware features"], snapshot_rows),
            "",
            "## Explicit Nonclaims",
            "",
            "- hinge bosses",
            "- pins",
            "- holes",
            "- cutbacks",
            "- finite-thickness clearance",
            "- sweep-volume clearance",
            "- CAD validity",
            "- printability",
            "- fabrication readiness",
            "- prototype validation",
            "",
            "## Acceptance",
            "",
            table(["Check", "Value"], acceptance_rows),
            "",
            "## Next Task",
            "",
            manifest["next_task"],
            "",
        ]
    )


def main() -> int:
    if not RW1_PATH.exists():
        raise RuntimeError(f"missing RW1 source lock: {RW1_PATH}")
    if not RW2_PATH.exists():
        raise RuntimeError(f"missing RW2 mesh payload: {RW2_PATH}")

    rw1 = load_json(RW1_PATH)
    rw2 = load_json(RW2_PATH)
    geometry = load_json(GEOMETRY_PATH)
    dense_report = load_json(DENSE_REPORT_PATH)
    case = batch.build_case()

    signs_by_tree = dense_signs_by_tree(dense_report)
    rw2_hinges = rw2_hinges_by_tree(rw2)
    tree_records = []
    sign_vectors_match_dense_report = True
    tree_hinges_match_rw2 = True
    for tree_id in TARGET_TREES:
        tree = find_tree(case, tree_id)
        signs = signs_by_tree.get(tree_id)
        if signs is None:
            raise RuntimeError(f"missing dense sign vector for {tree_id}")
        sign_vectors_match_dense_report = sign_vectors_match_dense_report and set(signs) == set(tree["hinge_ids"])
        tree_hinges_match_rw2 = tree_hinges_match_rw2 and rw2_hinges.get(tree_id) == list(tree["hinge_ids"])
        tree_records.append(sample_tree(case, geometry, tree, signs))

    all_samples = [sample for tree in tree_records for sample in tree["samples"]]
    all_snapshot_exports = [item for tree in tree_records for item in tree["snapshot_exports"]]
    theta_zero_samples = [sample for sample in all_samples if sample["theta_degrees"] == 0.0]
    max_orthogonality_error = max(sample["transform_quality"]["max_orthogonality_error"] for sample in all_samples)
    max_det_error = max(sample["transform_quality"]["max_det_error"] for sample in all_samples)
    max_theta_zero_identity_error = max(sample.get("theta_zero_identity_error", 0.0) for sample in theta_zero_samples)

    manifest = {
        "manifest_id": "S4-RW3-KINEMATICS-ADAPTER-2026-06-22",
        "case_id": CASE_ID,
        "date": DATE,
        "status": "kinematics_adapter_created_not_hardware_ready",
        "precondition": {
            "rw1_source_lock": rel(RW1_PATH),
            "rw1_status": rw1.get("status"),
            "rw2_mesh_payload": rel(RW2_PATH),
            "rw2_status": rw2.get("status"),
            "zero_thickness_sign_source": rel(DENSE_REPORT_PATH),
        },
        "scope": {
            "adapter_role": "attach_exact_body_solids_to_existing_zero_thickness_rigid_transforms",
            "root_piece": ROOT_PIECE,
            "target_trees": TARGET_TREES,
            "sample_theta_degrees": SAMPLE_THETA_DEGREES,
            "snapshot_theta_degrees": sorted(SNAPSHOT_THETA_DEGREES),
            "hardware_geometry_absent": True,
            "finite_thickness_clearance_status": "not_run",
            "printability_validation_status": "not_run",
            "cad_validity_status": "not_run",
        },
        "trees": tree_records,
        "exports": {
            "manifest": rel(JSON_PATH),
            "report": rel(DOC_PATH),
            "snapshot_objs": all_snapshot_exports,
        },
        "acceptance": {
            "rw1_source_lock_present": RW1_PATH.exists(),
            "rw2_mesh_payload_present": RW2_PATH.exists(),
            "rw2_status_locked": rw2.get("status") == "mesh_payload_created_not_fabrication_ready",
            "target_tree_count_is_2": len(tree_records) == 2,
            "sign_vectors_match_dense_report": sign_vectors_match_dense_report,
            "tree_hinges_match_rw2": tree_hinges_match_rw2,
            "sample_count": len(all_samples),
            "sample_count_expected_18": len(all_samples) == 18,
            "all_samples_collision_free": all(sample["status"] == "collision_free" for sample in all_samples),
            "theta_zero_identity": max_theta_zero_identity_error <= 1.0e-12,
            "max_theta_zero_identity_error": max_theta_zero_identity_error,
            "transforms_are_rotations": max_orthogonality_error <= 1.0e-12 and max_det_error <= 1.0e-12,
            "max_orthogonality_error": max_orthogonality_error,
            "max_det_error": max_det_error,
            "snapshot_count": len(all_snapshot_exports),
            "snapshot_count_expected_6": len(all_snapshot_exports) == 6,
            "hardware_geometry_absent": True,
            "finite_thickness_clearance_status": "not_run",
            "printability_validation_status": "not_run",
            "cad_validity_status": "not_run",
        },
        "next_task": "RW4 collision/sweep evidence: begin finite-thickness-aware collision and swept-volume checks, still before printability or fabrication claims.",
    }

    write_json(JSON_PATH, manifest)
    DOC_PATH.write_text(build_doc(manifest), encoding="utf-8", newline="\n")
    print(json.dumps({"status": manifest["status"], "manifest": rel(JSON_PATH), "report": rel(DOC_PATH)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
