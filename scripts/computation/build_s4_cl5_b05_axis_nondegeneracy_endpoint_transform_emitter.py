#!/usr/bin/env python
"""
Build the B05 axis-nondegeneracy / endpoint-transform object layer.

R40 consumes the R39 real formula backend bridge.  It materializes, for each
real B05 diagnostic, the source-locked symbolic transform paths for the common
edge endpoints M_AB and M_CD on both pieces of the B05 pair, plus the symbolic
cross-product axis expression

    n_ij = (F_i(M_CD)-F_i(M_AB)) x (F_j(M_CD)-F_j(M_AB)).

This is still not a report-promotion step.  The output deliberately separates
symbolic endpoint/axis objects from exact interval objects that are still
missing: endpoint coordinate intervals, trigonometric/fraction enclosures, and
a positive lower bound for ||n_ij||.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, deque
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-AXIS-ENDPOINT-TRANSFORM-EMITTER-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_AXIS_ENDPOINT_TRANSFORM_BRIDGE"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"

DEFAULT_R39_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_formula_backend_bridge_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "axis_nondegeneracy_endpoint_transform"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_nondegeneracy_endpoint_transform_manifest.json"
)
TREE_SOURCE_DIR = Path(
    "results/historical_s4_median_planes/ambient_edge_dense_refinements"
)

COMMON_EDGE_LABELS = ["M_AB", "M_CD"]
ROOT_PIECE = "P0"

AMBIENT_LABEL_DEFINITIONS = {
    "A": "A",
    "B": "B",
    "C": "C",
    "D": "D",
    "M_AB": "(A+B)/2",
    "M_CD": "(C+D)/2",
}

AXIS_LOWER_BOUND_BLOCKERS = [
    "exact_transform_endpoint_coordinates",
    "hinge_angle_fraction_interval_backend_missing",
    "positive_axis_norm_lower_bound_not_proved",
    "trig_component_bounds",
]

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_axis_norm_lower_bound_claim",
    "no_exact_endpoint_coordinate_interval_claim",
    "no_formula_shape_contract_ready_real_report_claim",
    "no_support_component_or_gap_margin_claim",
    "no_physical_hingeability_claim",
]


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise TypeError(f"expected JSON object: {path}")
    return data


def write_json_lf(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, sort_keys=True) + "\n"
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def sanitize(value: Any) -> str:
    text = str(value)
    out: list[str] = []
    for ch in text:
        if ch.isalnum():
            out.append(ch.lower())
        elif ch in {"-", "_"}:
            out.append("_")
    return "_".join("".join(out).split("_")).strip("_") or "x"


def load_tree_source(tree_id: str, cache: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if tree_id not in cache:
        path = ROOT / TREE_SOURCE_DIR / f"{tree_id}_dense_refinement.json"
        data = read_json(path)
        data["_source_path"] = rel(path)
        cache[tree_id] = data
    return cache[tree_id]


def selected_hinges(tree_source: dict[str, Any]) -> list[dict[str, Any]]:
    hinges = tree_source.get("selected_hinges")
    if not isinstance(hinges, list):
        raise TypeError(f"selected_hinges missing in {tree_source.get('_source_path')}")
    return [h for h in hinges if isinstance(h, dict)]


def parse_pair(piece_pair: str) -> list[str]:
    parts = piece_pair.split("-")
    if len(parts) != 2 or not all(p.startswith("P") for p in parts):
        raise ValueError(f"unexpected piece pair: {piece_pair}")
    return parts


def tree_adjacency(hinges: list[dict[str, Any]]) -> dict[str, list[tuple[str, dict[str, Any]]]]:
    adjacency: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for hinge in hinges:
        pieces = hinge.get("pieces")
        if not isinstance(pieces, list) or len(pieces) != 2:
            continue
        a, b = str(pieces[0]), str(pieces[1])
        adjacency.setdefault(a, []).append((b, hinge))
        adjacency.setdefault(b, []).append((a, hinge))
    return adjacency


def transform_paths_from_root(hinges: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    adjacency = tree_adjacency(hinges)
    paths: dict[str, list[dict[str, Any]]] = {ROOT_PIECE: []}
    queue: deque[str] = deque([ROOT_PIECE])
    while queue:
        parent = queue.popleft()
        for child, hinge in adjacency.get(parent, []):
            if child in paths:
                continue
            axis_labels = hinge.get("axis_labels")
            if not isinstance(axis_labels, list) or len(axis_labels) != 2:
                axis_labels = ["UNKNOWN_A", "UNKNOWN_B"]
            step = {
                "axis_labels": [str(axis_labels[0]), str(axis_labels[1])],
                "axis_support": hinge.get("axis_support"),
                "from_piece": parent,
                "hinge_id": hinge.get("hinge_id"),
                "source_contact": hinge.get("source_contact"),
                "theta_symbol": f"theta_{hinge.get('hinge_id')}",
                "to_piece": child,
            }
            paths[child] = paths[parent] + [step]
            queue.append(child)
    return paths


def transform_name(piece: str) -> str:
    return f"T_{piece}"


def transform_definition(piece: str, path: list[dict[str, Any]]) -> dict[str, Any]:
    if not path:
        return {
            "expression": "Id",
            "piece": piece,
            "root_piece": ROOT_PIECE,
            "status": "root_identity_transform",
        }
    steps = []
    current_expression = "Id"
    for step in path:
        h_id = step["hinge_id"]
        axis_a, axis_b = step["axis_labels"]
        parent = step["from_piece"]
        child = step["to_piece"]
        local_rotation = (
            f"R_{h_id}({step['theta_symbol']}; "
            f"{transform_name(parent)}({axis_a}), {transform_name(parent)}({axis_b}))"
        )
        current_expression = f"{local_rotation} o {transform_name(parent)}"
        steps.append({
            **step,
            "child_transform_expression": f"{transform_name(child)} = {current_expression}",
        })
    return {
        "expression": current_expression,
        "piece": piece,
        "root_piece": ROOT_PIECE,
        "status": "selected_hinge_tree_symbolic_transform_path",
        "steps": steps,
    }


def endpoint_expression(label: str, path: list[dict[str, Any]]) -> str:
    expr = label
    for step in path:
        h_id = step["hinge_id"]
        axis_a, axis_b = step["axis_labels"]
        parent = step["from_piece"]
        expr = (
            f"R_{h_id}({step['theta_symbol']}; "
            f"{transform_name(parent)}({axis_a}), {transform_name(parent)}({axis_b}))"
            f"({expr})"
        )
    return expr


def endpoint_transform_object(piece: str, path: list[dict[str, Any]]) -> dict[str, Any]:
    endpoints = {
        label: {
            "ambient_definition": AMBIENT_LABEL_DEFINITIONS[label],
            "symbolic_endpoint_expression": endpoint_expression(label, path),
            "exact_coordinate_interval_status": "blocked_not_emitted",
            "exact_coordinate_interval_blockers": [
                "exact_transform_endpoint_coordinates",
                "hinge_angle_fraction_interval_backend_missing",
                "trig_component_bounds",
            ],
        }
        for label in COMMON_EDGE_LABELS
    }
    return {
        "endpoint_labels": COMMON_EDGE_LABELS,
        "endpoints": endpoints,
        "piece": piece,
        "source_status": "source_locked_symbolic_endpoint_transform_emitted",
        "transform_definition": transform_definition(piece, path),
    }


def axis_object(left_piece: str, right_piece: str) -> dict[str, Any]:
    left = transform_name(left_piece)
    right = transform_name(right_piece)
    e_left = f"{left}(M_CD)-{left}(M_AB)"
    e_right = f"{right}(M_CD)-{right}(M_AB)"
    n_expr = f"({e_left}) x ({e_right})"
    return {
        "axis_expression_status": "source_locked_symbolic_axis_expression_emitted",
        "axis_norm_lower_bound": None,
        "axis_norm_lower_bound_blockers": AXIS_LOWER_BOUND_BLOCKERS,
        "axis_norm_lower_bound_status": "blocked_positive_lower_bound_not_proved",
        "axis_norm_squared_expression": f"dot({n_expr}, {n_expr})",
        "common_edge_labels": COMMON_EDGE_LABELS,
        "edge_vector_expressions": {
            left_piece: e_left,
            right_piece: e_right,
        },
        "n_ij_expression": n_expr,
        "piece_pair": f"{left_piece}-{right_piece}",
    }


def build_record(
    bridge_summary: dict[str, Any],
    *,
    out_dir: Path,
    tree_cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    bridge_path = ROOT / bridge_summary["bridge_record"]
    bridge = read_json(bridge_path)
    original_path = ROOT / bridge["original_report"]
    original = read_json(original_path)

    tree_id = str(bridge["tree_id"])
    pair = parse_pair(str(bridge["piece_pair"]))
    tree_source = load_tree_source(tree_id, tree_cache)
    hinges = selected_hinges(tree_source)
    paths = transform_paths_from_root(hinges)

    missing_paths = [piece for piece in pair if piece not in paths]
    endpoint_objects = {
        piece: endpoint_transform_object(piece, paths[piece])
        for piece in pair
        if piece in paths
    }
    path_ready = not missing_paths and len(endpoint_objects) == 2
    axis = axis_object(pair[0], pair[1]) if path_ready else None

    exact_endpoint_ready = False
    positive_axis_norm_ready = False
    contract_ready = exact_endpoint_ready and positive_axis_norm_ready

    object_status = (
        "symbolic_endpoint_and_axis_objects_emitted_backend_blocked"
        if path_ready
        else "selected_hinge_tree_path_reconstruction_blocked"
    )
    blockers = sorted(set(
        AXIS_LOWER_BOUND_BLOCKERS
        + bridge.get("missing_backend_or_exact_objects", [])
        + (["selected_hinge_tree_path_reconstruction"] if missing_paths else [])
    ))

    record = {
        "accepted_real_b05_report": False,
        "ambient_label_definitions": {
            label: AMBIENT_LABEL_DEFINITIONS[label]
            for label in ["A", "B", "C", "D", *COMMON_EDGE_LABELS]
        },
        "axis_nondegeneracy_contract_ready": contract_ready,
        "axis_object": axis,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": blockers,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "common_edge_labels": COMMON_EDGE_LABELS,
        "domain_family": bridge["domain_family"],
        "endpoint_coordinate_interval_ready": exact_endpoint_ready,
        "endpoint_transform_objects": endpoint_objects,
        "exact_endpoint_transform_status": "symbolic_only_no_fraction_interval_coordinates",
        "input_bridge_record": rel(bridge_path),
        "manifest_id": MANIFEST_ID,
        "missing_transform_paths": missing_paths,
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-AXIS-ENDPOINT-{sanitize(bridge['original_report_id'])}",
        "object_status": object_status,
        "original_report": rel(original_path),
        "original_report_accepted": bool(original.get("accepted")),
        "original_report_id": bridge["original_report_id"],
        "parent_overlay_key": original.get("predicate_data", {}).get("parent_overlay_key"),
        "piece_pair": bridge["piece_pair"],
        "positive_axis_norm_lower_bound_ready": positive_axis_norm_ready,
        "predicate_id": PREDICATE_ID,
        "selected_hinge_tree_source": {
            "selected_tree": tree_source.get("selected_tree"),
            "source_path": tree_source.get("_source_path"),
        },
        "symbolic_endpoint_transform_ready": path_ready,
        "tree_id": tree_id,
    }

    out_path = (
        out_dir
        / str(bridge["domain_family"])
        / f"{sanitize(bridge['original_report_id'])}_axis_endpoint.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "axis_nondegeneracy_contract_ready": contract_ready,
        "axis_object_status": None if axis is None else axis["axis_expression_status"],
        "endpoint_coordinate_interval_ready": exact_endpoint_ready,
        "object_record": rel(out_path),
        "object_status": object_status,
        "original_report": rel(original_path),
        "original_report_id": bridge["original_report_id"],
        "piece_pair": bridge["piece_pair"],
        "positive_axis_norm_lower_bound_ready": positive_axis_norm_ready,
        "symbolic_endpoint_transform_ready": path_ready,
        "tree_id": tree_id,
        "domain_family": bridge["domain_family"],
        "blockers": blockers,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r39-manifest", default=DEFAULT_R39_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r39_manifest_path = ROOT / args.r39_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r39 = read_json(r39_manifest_path)
    bridge_summaries = r39.get("report_bridges")
    if not isinstance(bridge_summaries, list):
        raise TypeError("R39 manifest report_bridges must be a list")

    tree_cache: dict[str, dict[str, Any]] = {}
    objects = [
        build_record(summary, out_dir=out_dir, tree_cache=tree_cache)
        for summary in bridge_summaries
        if isinstance(summary, dict)
    ]

    status_counts = Counter(obj["object_status"] for obj in objects)
    domain_counts = Counter(obj["domain_family"] for obj in objects)
    tree_counts = Counter(obj["tree_id"] for obj in objects)
    blocker_counts = Counter(blocker for obj in objects for blocker in obj["blockers"])

    symbolic_ready_count = sum(obj["symbolic_endpoint_transform_ready"] for obj in objects)
    endpoint_interval_ready_count = sum(obj["endpoint_coordinate_interval_ready"] for obj in objects)
    axis_bound_ready_count = sum(obj["positive_axis_norm_lower_bound_ready"] for obj in objects)
    contract_ready_count = sum(obj["axis_nondegeneracy_contract_ready"] for obj in objects)

    manifest = {
        "accepted_real_b05_report_count": 0,
        "axis_nondegeneracy_contract_ready_count": contract_ready_count,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "endpoint_coordinate_interval_ready_count": endpoint_interval_ready_count,
        "input_r39_manifest": rel(r39_manifest_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(objects),
        "object_status_counts": dict(sorted(status_counts.items())),
        "positive_axis_norm_lower_bound_ready_count": axis_bound_ready_count,
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "record_count_by_tree_id": dict(sorted(tree_counts.items())),
        "records": objects,
        "recommended_next_task": (
            "R41: implement the B05 exact trigonometric/fraction interval backend for "
            "selected-hinge endpoint transforms, then use it to prove positive lower "
            "bounds for the common-edge cross-product axis norm."
        ),
        "symbolic_endpoint_transform_ready_count": symbolic_ready_count,
        "tree_sources": {
            tree_id: source.get("_source_path")
            for tree_id, source in sorted(tree_cache.items())
        },
    }
    write_json_lf(manifest_path, manifest)

    print(f"input bridge records: {len(objects)}")
    print(f"symbolic endpoint transforms ready: {symbolic_ready_count}")
    print(f"endpoint coordinate intervals ready: {endpoint_interval_ready_count}")
    print(f"positive axis norm lower bounds ready: {axis_bound_ready_count}")
    print(f"axis-nondegeneracy contract ready: {contract_ready_count}")
    print(f"accepted real B05 reports: 0")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"blocker counts: {dict(sorted(blocker_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")

    if len(objects) != len(bridge_summaries):
        return 1
    if symbolic_ready_count != len(objects):
        return 1
    if endpoint_interval_ready_count or axis_bound_ready_count or contract_ready_count:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
