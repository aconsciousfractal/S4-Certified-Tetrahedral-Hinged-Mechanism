"""Local helpers for mechanical-extension audits.

The library is intentionally project-local. It keeps the first hingeability
audits independent from PAPP mesh dependencies while following the same bounded
JSON-report discipline.
"""

from __future__ import annotations

from collections import deque
import importlib.util
import itertools
import json
import math
import sys
import types
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


TOL = 1.0e-9

SCRIPT_PATH = Path(__file__).resolve()
MECH_ROOT = SCRIPT_PATH.parents[1]
TETRA_ROOT = SCRIPT_PATH.parents[2]
SRC_DIR = TETRA_ROOT / "06-computational" / "src"


def load_tetra_module(module_name: str):
    """Load modules from 06-computational/src without executing markdown __init__."""
    package_name = "tetra_src_runtime"
    if package_name not in sys.modules:
        package = types.ModuleType(package_name)
        package.__path__ = [str(SRC_DIR)]
        sys.modules[package_name] = package
    qualified_name = f"{package_name}.{module_name}"
    spec = importlib.util.spec_from_file_location(qualified_name, SRC_DIR / f"{module_name}.py")
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load {module_name} from {SRC_DIR}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[qualified_name] = module
    spec.loader.exec_module(module)
    return module


tetrahedron = load_tetra_module("tetrahedron")
dissections = load_tetra_module("dissections")

barycentre = tetrahedron.barycentre
edge_midpoint = tetrahedron.edge_midpoint
face_centroid = tetrahedron.face_centroid
regular_tetrahedron = tetrahedron.regular_tetrahedron
tet_volume_from_vertices = tetrahedron.tet_volume_from_vertices
volume = tetrahedron.volume


def json_ready(value):
    if isinstance(value, dict):
        return {key: json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    if isinstance(value, np.ndarray):
        return [json_ready(item) for item in value.tolist()]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(json_ready(payload), handle, indent=2)
        handle.write("\n")


def as_list(point: np.ndarray) -> list[float]:
    return [round(float(x), 12) for x in point]


def canonical_labels(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray) -> dict[str, np.ndarray]:
    return {
        "A": A,
        "B": B,
        "C": C,
        "D": D,
        "M_AB": edge_midpoint(A, B),
        "M_AC": edge_midpoint(A, C),
        "M_AD": edge_midpoint(A, D),
        "M_BC": edge_midpoint(B, C),
        "M_BD": edge_midpoint(B, D),
        "M_CD": edge_midpoint(C, D),
        "G_ABC": face_centroid(A, B, C),
        "G_ABD": face_centroid(A, B, D),
        "G_ACD": face_centroid(A, C, D),
        "G_BCD": face_centroid(B, C, D),
        "G_T": barycentre(A, B, C, D),
    }


def label_for(point: np.ndarray, labels: dict[str, np.ndarray]) -> str:
    for name, candidate in labels.items():
        if np.linalg.norm(point - candidate) <= TOL:
            return name
    return "UNLABELED_" + "_".join(f"{x:.9f}" for x in point)


def edge_spectrum(piece: Sequence[np.ndarray]) -> list[float]:
    values = []
    for i, j in itertools.combinations(range(len(piece)), 2):
        values.append(float(np.linalg.norm(piece[i] - piece[j])))
    return [round(x, 12) for x in sorted(values)]


def piece_record(piece_id: str, vertices: Sequence[np.ndarray], labels: dict[str, np.ndarray]) -> dict:
    vertex_labels = [label_for(v, labels) for v in vertices]
    return {
        "piece_id": piece_id,
        "vertices": [
            {"label": label, "coordinates": as_list(vertex)}
            for label, vertex in zip(vertex_labels, vertices)
        ],
        "faces": [
            {"labels": sorted(vertex_labels[i] for i in face)}
            for face in itertools.combinations(range(4), 3)
        ],
        "volume": round(float(tet_volume_from_vertices(*vertices)), 15),
        "edge_spectrum": edge_spectrum(vertices),
    }


def ambient_faces(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]]:
    return {
        "ABC": (A, B, C),
        "ABD": (A, B, D),
        "ACD": (A, C, D),
        "BCD": (B, C, D),
    }


def ambient_edges(A: np.ndarray, B: np.ndarray, C: np.ndarray, D: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray]]:
    return {
        "AB": (A, B),
        "AC": (A, C),
        "AD": (A, D),
        "BC": (B, C),
        "BD": (B, D),
        "CD": (C, D),
    }


def point_on_triangle(point: np.ndarray, triangle: Iterable[np.ndarray]) -> bool:
    P = np.asarray(point, dtype=float)
    A, B, C = [np.asarray(v, dtype=float) for v in triangle]
    v0 = B - A
    v1 = C - A
    v2 = P - A
    normal = np.cross(v0, v1)
    norm = np.linalg.norm(normal)
    if norm <= TOL:
        return False
    if abs(np.dot(P - A, normal / norm)) > 1.0e-8:
        return False
    dot00 = float(np.dot(v0, v0))
    dot01 = float(np.dot(v0, v1))
    dot02 = float(np.dot(v0, v2))
    dot11 = float(np.dot(v1, v1))
    dot12 = float(np.dot(v1, v2))
    denom = dot00 * dot11 - dot01 * dot01
    if abs(denom) <= TOL:
        return False
    u = (dot11 * dot02 - dot01 * dot12) / denom
    v = (dot00 * dot12 - dot01 * dot02) / denom
    return u >= -1.0e-8 and v >= -1.0e-8 and (u + v) <= 1.0 + 1.0e-8


def point_on_segment(point: np.ndarray, a: np.ndarray, b: np.ndarray) -> bool:
    point = np.asarray(point, dtype=float)
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    ab = b - a
    ap = point - a
    if np.linalg.norm(np.cross(ab, ap)) > 1.0e-8:
        return False
    denom = float(np.dot(ab, ab))
    if denom <= TOL:
        return False
    t = float(np.dot(ap, ab) / denom)
    return -1.0e-8 <= t <= 1.0 + 1.0e-8


def boundary_faces_for_segment(
    p: np.ndarray,
    q: np.ndarray,
    faces: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> list[str]:
    hits = []
    for face_name, face_vertices in faces.items():
        if point_on_triangle(p, face_vertices) and point_on_triangle(q, face_vertices):
            hits.append(face_name)
    return hits


def ambient_edge_hits(p: np.ndarray, q: np.ndarray, edges: dict[str, tuple[np.ndarray, np.ndarray]]) -> list[str]:
    hits = []
    for name, (a, b) in edges.items():
        if point_on_segment(p, a, b) and point_on_segment(q, a, b):
            hits.append(name)
    return hits


def extract_contacts(piece_records: Sequence[dict]) -> list[dict]:
    contacts = []
    for left, right in itertools.combinations(piece_records, 2):
        left_labels = {v["label"] for v in left["vertices"]}
        right_labels = {v["label"] for v in right["vertices"]}
        shared = sorted(left_labels & right_labels)
        if len(shared) >= 3:
            contact_type = "shared_face"
        elif len(shared) == 2:
            contact_type = "shared_edge"
        elif len(shared) == 1:
            contact_type = "shared_vertex"
        else:
            contact_type = "none"
        if contact_type != "none":
            contacts.append(
                {
                    "contact_id": f"C{len(contacts)}",
                    "pieces": [left["piece_id"], right["piece_id"]],
                    "type": contact_type,
                    "vertices": shared,
                }
            )
    return contacts


def enumerate_candidate_hinges(
    contacts: Sequence[dict],
    labels: dict[str, np.ndarray],
    faces: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
) -> list[dict]:
    hinges = []
    for contact in contacts:
        if contact["type"] != "shared_face":
            continue
        for a, b in itertools.combinations(contact["vertices"], 2):
            p = labels[a]
            q = labels[b]
            boundary_faces = boundary_faces_for_segment(p, q, faces)
            hinges.append(
                {
                    "hinge_id": f"H{len(hinges)}_{a}_{b}",
                    "pieces": contact["pieces"],
                    "type": "edge_hinge",
                    "axis_labels": [a, b],
                    "axis_points": [as_list(p), as_list(q)],
                    "axis_length": round(float(np.linalg.norm(q - p)), 12),
                    "axis_class": "boundary" if boundary_faces else "internal",
                    "ambient_boundary_faces": boundary_faces,
                    "source_contact": contact["contact_id"],
                }
            )
    return hinges


def augment_hinge_support(
    hinges: Sequence[dict],
    labels: dict[str, np.ndarray],
    edges: dict[str, tuple[np.ndarray, np.ndarray]],
) -> None:
    for hinge in hinges:
        p = labels[hinge["axis_labels"][0]]
        q = labels[hinge["axis_labels"][1]]
        edge_hits = ambient_edge_hits(p, q, edges)
        hinge["ambient_boundary_edges"] = edge_hits
        if edge_hits:
            hinge["axis_support"] = "ambient_edge_subsegment"
        elif hinge["axis_class"] == "boundary":
            hinge["axis_support"] = "ambient_face_segment"
        else:
            hinge["axis_support"] = "internal_segment"


def is_tree(piece_ids: Sequence[str], selected_hinges: Sequence[dict]) -> bool:
    parent = {piece: piece for piece in piece_ids}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> bool:
        ra = find(a)
        rb = find(b)
        if ra == rb:
            return False
        parent[rb] = ra
        return True

    if len(selected_hinges) != len(piece_ids) - 1:
        return False
    for hinge in selected_hinges:
        a, b = hinge["pieces"]
        if not union(a, b):
            return False
    return len({find(piece) for piece in piece_ids}) == 1


def enumerate_hinge_trees(piece_ids: Sequence[str], hinges: Sequence[dict]) -> list[dict]:
    trees = []
    for combo in itertools.combinations(hinges, len(piece_ids) - 1):
        if not is_tree(piece_ids, list(combo)):
            continue
        internal_count = sum(1 for hinge in combo if hinge["axis_support"] == "internal_segment")
        ambient_edge_count = sum(1 for hinge in combo if hinge["axis_support"] == "ambient_edge_subsegment")
        total_length = sum(float(hinge["axis_length"]) for hinge in combo)
        trees.append(
            {
                "tree_id": f"TREE_{len(trees):03d}",
                "hinge_ids": [hinge["hinge_id"] for hinge in combo],
                "contact_ids": [hinge["source_contact"] for hinge in combo],
                "piece_edges": [hinge["pieces"] for hinge in combo],
                "axis_labels": [hinge["axis_labels"] for hinge in combo],
                "axis_supports": [hinge["axis_support"] for hinge in combo],
                "internal_axis_count": internal_count,
                "ambient_edge_axis_count": ambient_edge_count,
                "boundary_axis_count": sum(1 for hinge in combo if hinge["axis_class"] == "boundary"),
                "total_axis_length": round(total_length, 12),
                "rank_key": [internal_count, -ambient_edge_count, round(total_length, 12)],
            }
        )
    trees.sort(key=lambda tree: tuple(tree["rank_key"]))
    for index, tree in enumerate(trees):
        tree["rank"] = index + 1
    return trees


def contact_graph_summary(contacts: Sequence[dict]) -> dict:
    face_contacts = [contact for contact in contacts if contact["type"] == "shared_face"]
    edge_contacts = [contact for contact in contacts if contact["type"] == "shared_edge"]
    return {
        "face_contact_count": len(face_contacts),
        "edge_contact_count": len(edge_contacts),
        "face_contact_edges": [
            {"contact_id": c["contact_id"], "pieces": c["pieces"], "vertices": c["vertices"]}
            for c in face_contacts
        ],
        "edge_only_contacts": [
            {"contact_id": c["contact_id"], "pieces": c["pieces"], "vertices": c["vertices"]}
            for c in edge_contacts
        ],
    }


def rotation_matrix(axis: np.ndarray, angle_radians: float) -> np.ndarray:
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c = math.cos(angle_radians)
    s = math.sin(angle_radians)
    C = 1.0 - c
    return np.array(
        [
            [c + x * x * C, x * y * C - z * s, x * z * C + y * s],
            [y * x * C + z * s, c + y * y * C, y * z * C - x * s],
            [z * x * C - y * s, z * y * C + x * s, c + z * z * C],
        ]
    )


def identity_transform() -> dict[str, np.ndarray]:
    return {"R": np.eye(3), "t": np.zeros(3)}


def compose_transform(left: dict[str, np.ndarray], right: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    return {"R": left["R"] @ right["R"], "t": left["R"] @ right["t"] + left["t"]}


def axis_rotation_transform(p0: np.ndarray, p1: np.ndarray, angle_radians: float) -> dict[str, np.ndarray]:
    R = rotation_matrix(p1 - p0, angle_radians)
    return {"R": R, "t": p0 - R @ p0}


def apply_transform_to_point(transform: dict[str, np.ndarray], point: np.ndarray) -> np.ndarray:
    return transform["R"] @ np.asarray(point, dtype=float) + transform["t"]


def apply_transform_to_poly(transform: dict[str, np.ndarray], poly: Sequence[np.ndarray]) -> list[np.ndarray]:
    return [apply_transform_to_point(transform, p) for p in poly]


def rotate_about_axis(points: Sequence[np.ndarray], p0: np.ndarray, p1: np.ndarray, angle_radians: float) -> list[np.ndarray]:
    return apply_transform_to_poly(axis_rotation_transform(p0, p1, angle_radians), points)


def tetra_faces(poly: Sequence[np.ndarray]) -> list[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    return [tuple(poly[i] for i in combo) for combo in itertools.combinations(range(4), 3)]


def tetra_edges(poly: Sequence[np.ndarray]) -> list[np.ndarray]:
    return [poly[j] - poly[i] for i, j in itertools.combinations(range(4), 2)]


def sat_axes(poly_a: Sequence[np.ndarray], poly_b: Sequence[np.ndarray]) -> list[np.ndarray]:
    axes: list[np.ndarray] = []
    for face in tetra_faces(poly_a) + tetra_faces(poly_b):
        normal = np.cross(face[1] - face[0], face[2] - face[0])
        if np.linalg.norm(normal) > TOL:
            axes.append(normal)
    for edge_a in tetra_edges(poly_a):
        for edge_b in tetra_edges(poly_b):
            axis = np.cross(edge_a, edge_b)
            if np.linalg.norm(axis) > TOL:
                axes.append(axis)
    return axes


def strict_interior_overlap(poly_a: Sequence[np.ndarray], poly_b: Sequence[np.ndarray], tol: float = 1.0e-8) -> tuple[bool, float]:
    min_overlap = float("inf")
    for axis in sat_axes(poly_a, poly_b):
        axis = axis / np.linalg.norm(axis)
        a_values = [float(np.dot(v, axis)) for v in poly_a]
        b_values = [float(np.dot(v, axis)) for v in poly_b]
        overlap = min(max(a_values), max(b_values)) - max(min(a_values), min(b_values))
        min_overlap = min(min_overlap, overlap)
        if overlap <= tol:
            return False, min_overlap
    return True, min_overlap


def single_hinge_motion_audit(
    piece_fixed: Sequence[np.ndarray],
    piece_rotating: Sequence[np.ndarray],
    hinge: dict,
    sample_degrees: Sequence[int] | None = None,
) -> dict:
    p0 = np.array(hinge["axis_points"][0], dtype=float)
    p1 = np.array(hinge["axis_points"][1], dtype=float)
    samples = list(sample_degrees or [0, 5, 10, 15, 30, 45, 60, 75, 90, 105, 120])
    direction_reports = []
    for sign in [1, -1]:
        collisions = []
        min_clearance_proxy = float("inf")
        for degrees in samples:
            moved = rotate_about_axis(piece_rotating, p0, p1, math.radians(sign * degrees))
            has_overlap, min_overlap = strict_interior_overlap(piece_fixed, moved)
            min_clearance_proxy = min(min_clearance_proxy, min_overlap)
            if has_overlap:
                collisions.append({"angle_degrees": sign * degrees, "min_axis_overlap": min_overlap})
        direction_reports.append(
            {
                "direction_sign": sign,
                "sample_degrees": [sign * d for d in samples],
                "status": "sampled_collision_free" if not collisions else "blocked",
                "collisions": collisions,
                "minimum_axis_overlap_proxy": round(float(min_clearance_proxy), 12),
            }
        )
    preferred = next((r for r in direction_reports if r["status"] == "sampled_collision_free"), direction_reports[0])
    return {
        "hinge_id": hinge["hinge_id"],
        "axis_labels": hinge["axis_labels"],
        "method": "strict convex SAT; touching/contact is allowed, positive-volume interior overlap is blocked",
        "preferred_direction_sign": preferred["direction_sign"] if preferred["status"] == "sampled_collision_free" else None,
        "status": preferred["status"],
        "directions": direction_reports,
    }


def transforms_for_hinge_tree(
    piece_ids: Sequence[str],
    selected_hinges: Sequence[dict],
    labels: dict[str, np.ndarray],
    angles_by_hinge_id: dict[str, float],
    root_piece: str = "P0",
) -> dict[str, dict[str, np.ndarray]]:
    adjacency: dict[str, list[tuple[str, dict]]] = {piece_id: [] for piece_id in piece_ids}
    for hinge in selected_hinges:
        left, right = hinge["pieces"]
        adjacency[left].append((right, hinge))
        adjacency[right].append((left, hinge))

    transforms: dict[str, dict[str, np.ndarray]] = {root_piece: identity_transform()}
    queue: deque[str] = deque([root_piece])
    while queue:
        parent = queue.popleft()
        parent_transform = transforms[parent]
        for child, hinge in adjacency[parent]:
            if child in transforms:
                continue
            a_label, b_label = hinge["axis_labels"]
            p0_world = apply_transform_to_point(parent_transform, labels[a_label])
            p1_world = apply_transform_to_point(parent_transform, labels[b_label])
            angle = float(angles_by_hinge_id.get(hinge["hinge_id"], 0.0))
            relative = axis_rotation_transform(p0_world, p1_world, angle)
            transforms[child] = compose_transform(relative, parent_transform)
            queue.append(child)

    missing = sorted(set(piece_ids) - set(transforms))
    if missing:
        raise ValueError(f"Hinge tree does not connect all pieces from {root_piece}: {missing}")
    return transforms


def transform_pieces(
    pieces_by_id: dict[str, Sequence[np.ndarray]],
    transforms: dict[str, dict[str, np.ndarray]],
) -> dict[str, list[np.ndarray]]:
    return {piece_id: apply_transform_to_poly(transforms[piece_id], piece) for piece_id, piece in pieces_by_id.items()}


def collision_report(transformed_pieces: dict[str, Sequence[np.ndarray]]) -> dict:
    collisions = []
    min_proxy = float("inf")
    for left, right in itertools.combinations(sorted(transformed_pieces), 2):
        has_overlap, min_overlap = strict_interior_overlap(transformed_pieces[left], transformed_pieces[right])
        min_proxy = min(min_proxy, min_overlap)
        if has_overlap:
            collisions.append(
                {
                    "pieces": [left, right],
                    "min_axis_overlap": round(float(min_overlap), 12),
                }
            )
    return {
        "status": "collision_free" if not collisions else "blocked",
        "collisions": collisions,
        "minimum_axis_overlap_proxy": None if min_proxy == float("inf") else round(float(min_proxy), 12),
    }