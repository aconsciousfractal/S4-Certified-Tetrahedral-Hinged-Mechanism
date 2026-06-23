#!/usr/bin/env python
"""
Build the A2 symbolic one-parameter ray model and B05 common-edge pilot objects.

A2 is the first concrete step after the post-R61 pivot.  It does not attempt to
promote B05 reports.  Instead it emits exact symbolic one-parameter kinematic
records for the two representative S4 rays and a B05 common-edge pilot
expression for every current B05 real-source record.

The pilot expression is the common-edge support gap on the common-edge support
signature:

    lower/upper support labels = {M_AB, M_CD}.

For all 7 B05 records this reduces to

    raw_gap(theta) = sqrt(2) * sin(theta)^2 / 4

and, together with the R43 axis factor

    ||n_ij(theta)||^2 = sin(theta)^2 * (2 - sin(theta)^2) / 4,

it recovers the Lemma 06 normalized shared-edge expression.  This remains a
symbolic pilot object: support-switch stability, branch validity, operation
enclosures, accepted B05 reports, and theorem promotion are out of scope.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import sympy as sp


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
MANIFEST_ID = "S4-CL5-A2-SYMBOLIC-RAY-MODEL-PILOT-2026-06-22"
CLAIM_LEVEL = "SYMBOLIC_RAY_MODEL_PILOT"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"

DEFAULT_R40_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_nondegeneracy_endpoint_transform_manifest.json"
)
DEFAULT_R60_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_report_field_extraction_audit_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "a2_symbolic_ray_model_pilot"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_a2_symbolic_ray_model_pilot_manifest.json"
)
TREE_SOURCE_DIR = Path(
    "results/historical_s4_median_planes/ambient_edge_dense_refinements"
)

R40_SCRIPT = Path("scripts/build_s4_cl5_b05_axis_nondegeneracy_endpoint_transform_emitter.py")
R43_SCRIPT = Path("scripts/build_s4_cl5_b05_axis_norm_symbolic_lower_bound_backend.py")

PIECE_VERTICES = {
    "P0": ["A", "M_AB", "C", "M_CD"],
    "P1": ["A", "M_AB", "D", "M_CD"],
    "P2": ["B", "M_AB", "C", "M_CD"],
    "P3": ["B", "M_AB", "D", "M_CD"],
}

COMMON_EDGE_LABELS = ["M_AB", "M_CD"]
EXPECTED_RAW_GAP = "sqrt(2)*sin_theta^2/4"
EXPECTED_AXIS_NORM_SQUARE = "sin_theta^2*(2-sin_theta^2)/4"

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_support_switch_stability_claim",
    "no_operation_enclosure_claim",
    "no_full_domain_b05_proof_claim",
    "no_physical_hingeability_claim",
    "no_theorem_promotion_claim",
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


def load_helper(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import helper: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


R40 = load_helper("r40_axis_endpoint_helpers", R40_SCRIPT)
R43 = load_helper("r43_axis_norm_helpers", R43_SCRIPT)

S = R43.S
C = R43.C
T = sp.symbols("t")


def expr_str(expr: sp.Expr) -> str:
    return str(sp.factor(R43.reduce_trig_identity(expr)))


def rational_expr_str(expr: sp.Expr) -> str:
    return str(sp.factor(sp.cancel(expr)))


def vector_expr(vector: sp.Matrix) -> list[str]:
    return [expr_str(item) for item in vector]


def weierstrass(expr: sp.Expr) -> dict[str, str]:
    rational = sp.factor(sp.together(expr.subs({
        S: 2 * T / (1 + T * T),
        C: (1 - T * T) / (1 + T * T),
    })))
    num, den = sp.fraction(rational)
    return {
        "denominator": str(sp.factor(den)),
        "numerator": str(sp.factor(num)),
        "rational_expr": str(rational),
        "substitution": "t = tan(theta/2), sin(theta)=2*t/(1+t^2), cos(theta)=(1-t^2)/(1+t^2)",
    }


def tree_source(tree_id: str) -> dict[str, Any]:
    data = read_json(ROOT / TREE_SOURCE_DIR / f"{tree_id}_dense_refinement.json")
    data["_source_path"] = rel(ROOT / TREE_SOURCE_DIR / f"{tree_id}_dense_refinement.json")
    return data


def signs_from_tree_source(source: dict[str, Any]) -> dict[str, int]:
    signs = source.get("dense_refinement", {}).get("sign_vector_by_hinge")
    if not isinstance(signs, dict):
        raise TypeError(f"missing sign_vector_by_hinge in {source.get('_source_path')}")
    return {str(k): int(v) for k, v in signs.items()}


def transform_paths(source: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    return R40.transform_paths_from_root(R40.selected_hinges(source))


def transformed_label(label: str, steps: list[dict[str, Any]], signs: dict[str, int]) -> sp.Matrix:
    return R43.apply_transform_path(label, steps, signs)


def build_tree_model(tree_id: str, *, out_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, sp.Matrix]]]:
    source = tree_source(tree_id)
    signs = signs_from_tree_source(source)
    paths = transform_paths(source)
    transformed: dict[str, dict[str, sp.Matrix]] = {}
    piece_json: dict[str, Any] = {}

    for piece, labels in PIECE_VERTICES.items():
        steps = paths[piece]
        transformed[piece] = {}
        piece_json[piece] = {
            "path_length": len(steps),
            "transform_steps": [
                {
                    "axis_labels": step["axis_labels"],
                    "from_piece": step["from_piece"],
                    "hinge_id": step["hinge_id"],
                    "signed_ray_sign": signs[str(step["hinge_id"])],
                    "to_piece": step["to_piece"],
                }
                for step in steps
            ],
            "vertices": {},
        }
        for label in labels:
            vec = transformed_label(label, steps, signs)
            transformed[piece][label] = vec
            piece_json[piece]["vertices"][label] = vector_expr(vec)

    record = {
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"A2-SYMBOLIC-RAY-MODEL-{tree_id}",
        "object_status": "symbolic_one_parameter_ray_model_emitted",
        "piece_vertex_expressions": piece_json,
        "ray_interval_degrees": source.get("dense_refinement", {}).get("ray_interval_degrees"),
        "signed_ray_signs": signs,
        "symbolic_ring": {
            "variables": ["s = sin(theta)", "c = cos(theta)"],
            "relation": "c^2 + s^2 = 1",
            "weierstrass_substitution": "t = tan(theta/2)",
        },
        "tree_id": tree_id,
        "tree_source": source.get("_source_path"),
    }
    out_path = out_dir / "ray_models" / f"{tree_id.lower()}_symbolic_ray_model.json"
    write_json_lf(out_path, record)
    return {
        "object_record": rel(out_path),
        "object_status": record["object_status"],
        "tree_id": tree_id,
    }, transformed


SUPPORT_RE = re.compile(r"lower=(P\d)\[([^\]]*)\]\|upper=(P\d)\[([^\]]*)\]")


def common_edge_support_signatures(r60_manifest: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for item in r60_manifest.get("records", []):
        if not isinstance(item, dict):
            continue
        signature = str(item.get("support_signature"))
        if signature.count("[M_AB,M_CD]") == 2:
            out[str(item["original_report_id"])] = signature
    return out


def parse_support_signature(signature: str) -> tuple[str, list[str], str, list[str]]:
    match = SUPPORT_RE.fullmatch(signature)
    if not match:
        raise ValueError(f"unexpected support signature: {signature}")
    lower_piece, lower_labels, upper_piece, upper_labels = match.groups()
    return (
        lower_piece,
        [x for x in lower_labels.split(",") if x],
        upper_piece,
        [x for x in upper_labels.split(",") if x],
    )


def dot(axis: sp.Matrix, point: sp.Matrix) -> sp.Expr:
    return sp.expand(axis.dot(point))


def build_b05_pilot(
    r40_summary: dict[str, Any],
    transformed_by_tree: dict[str, dict[str, dict[str, sp.Matrix]]],
    support_signatures: dict[str, str],
    *,
    out_dir: Path,
) -> dict[str, Any]:
    r40_path = ROOT / r40_summary["object_record"]
    r40 = read_json(r40_path)
    tree_id = str(r40["tree_id"])
    report_id = str(r40["original_report_id"])
    pair = str(r40["piece_pair"]).split("-")
    support_signature = support_signatures[report_id]
    lower_piece, lower_labels, upper_piece, upper_labels = parse_support_signature(support_signature)
    transformed = transformed_by_tree[tree_id]

    e_left = sp.simplify(transformed[pair[0]]["M_CD"] - transformed[pair[0]]["M_AB"])
    e_right = sp.simplify(transformed[pair[1]]["M_CD"] - transformed[pair[1]]["M_AB"])
    axis = R43.v_cross(e_left, e_right)
    axis_norm_square = R43.reduce_trig_identity(R43.norm_square(axis))
    expected_axis = S * S * (2 - S * S) / 4
    if sp.simplify(axis_norm_square - expected_axis) != 0:
        raise ValueError(f"unexpected axis factor for {report_id}: {sp.factor(axis_norm_square)}")

    lower_projection = dot(axis, transformed[lower_piece][lower_labels[0]])
    upper_projection = dot(axis, transformed[upper_piece][upper_labels[0]])
    raw_gap = R43.reduce_trig_identity(upper_projection - lower_projection)
    expected_gap = sp.sqrt(2) * S * S / 4
    if sp.simplify(raw_gap - expected_gap) != 0:
        raise ValueError(f"unexpected raw gap for {report_id}: {sp.factor(raw_gap)}")

    projection_table: dict[str, dict[str, str]] = {}
    for piece in pair:
        projection_table[piece] = {}
        for label in PIECE_VERTICES[piece]:
            projection_table[piece][label] = expr_str(dot(axis, transformed[piece][label]))

    normalized_gap_square = sp.factor(sp.cancel((raw_gap * raw_gap) / axis_norm_square))
    normalized_gap_square_expected = S * S / (2 * (2 - S * S))
    if sp.simplify(sp.cancel(normalized_gap_square - normalized_gap_square_expected)) != 0:
        raise ValueError(f"unexpected normalized gap square for {report_id}")

    record = {
        "accepted_real_b05_report": False,
        "axis_cross_product_components": vector_expr(axis),
        "axis_norm_square": {
            "trig_expr": EXPECTED_AXIS_NORM_SQUARE,
            "computed_expr": expr_str(axis_norm_square),
            "weierstrass": weierstrass(axis_norm_square),
        },
        "blockers": [
            "support_switch_stability_not_proved",
            "operation_enclosures_not_emitted",
            "accepted_report_promotion_out_of_scope",
        ],
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "common_edge_vectors": {
            pair[0]: vector_expr(e_left),
            pair[1]: vector_expr(e_right),
        },
        "common_edge_support_signature": support_signature,
        "domain_family": r40["domain_family"],
        "input_r40_axis_endpoint_record": rel(r40_path),
        "lower_piece": lower_piece,
        "lower_support_labels": lower_labels,
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "normalized_gap_square": {
            "computed_expr": rational_expr_str(normalized_gap_square),
            "trig_expr": "sin_theta^2/(2*(2-sin_theta^2)) = sin_theta^2/(2*(1+cos_theta^2))",
            "weierstrass": weierstrass(normalized_gap_square),
        },
        "object_id": f"A2-B05-COMMON-EDGE-PILOT-{sanitize(report_id)}",
        "object_status": "a2_common_edge_symbolic_pilot_ready",
        "original_report": r40["original_report"],
        "original_report_id": report_id,
        "piece_pair": r40["piece_pair"],
        "predicate_id": PREDICATE_ID,
        "projection_table_on_n_ij": projection_table,
        "raw_common_edge_gap": {
            "computed_expr": expr_str(raw_gap),
            "trig_expr": EXPECTED_RAW_GAP,
            "weierstrass": weierstrass(raw_gap),
        },
        "symbolic_pilot_ready": True,
        "tree_id": tree_id,
        "upper_piece": upper_piece,
        "upper_support_labels": upper_labels,
    }
    out_path = (
        out_dir
        / "b05_common_edge_pilots"
        / str(r40["domain_family"])
        / f"{sanitize(report_id)}_a2_common_edge_pilot.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "common_edge_support_signature": support_signature,
        "domain_family": r40["domain_family"],
        "object_record": rel(out_path),
        "object_status": record["object_status"],
        "original_report_id": report_id,
        "piece_pair": r40["piece_pair"],
        "raw_gap_expr": EXPECTED_RAW_GAP,
        "symbolic_pilot_ready": True,
        "tree_id": tree_id,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r40-manifest", default=DEFAULT_R40_MANIFEST.as_posix())
    parser.add_argument("--r60-manifest", default=DEFAULT_R60_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r40_manifest_path = ROOT / args.r40_manifest
    r60_manifest_path = ROOT / args.r60_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r40_manifest = read_json(r40_manifest_path)
    r60_manifest = read_json(r60_manifest_path)
    r40_records = r40_manifest.get("records")
    if not isinstance(r40_records, list):
        raise TypeError("R40 manifest must expose records list")

    tree_ids = sorted({str(item["tree_id"]) for item in r40_records if isinstance(item, dict)})
    tree_model_summaries = []
    transformed_by_tree = {}
    for tree_id in tree_ids:
        summary, transformed = build_tree_model(tree_id, out_dir=out_dir)
        tree_model_summaries.append(summary)
        transformed_by_tree[tree_id] = transformed

    support_signatures = common_edge_support_signatures(r60_manifest)
    missing_support = [
        str(item["original_report_id"])
        for item in r40_records
        if str(item["original_report_id"]) not in support_signatures
    ]
    if missing_support:
        raise ValueError(f"missing common-edge support signatures: {missing_support}")

    pilots = [
        build_b05_pilot(
            item,
            transformed_by_tree,
            support_signatures,
            out_dir=out_dir,
        )
        for item in r40_records
        if isinstance(item, dict)
    ]

    status_counts = Counter(item["object_status"] for item in pilots)
    tree_counts = Counter(item["tree_id"] for item in pilots)
    domain_counts = Counter(item["domain_family"] for item in pilots)
    signature_counts = Counter(item["common_edge_support_signature"] for item in pilots)

    manifest = {
        "accepted_real_b05_report_count": 0,
        "b05_common_edge_pilot_record_count": len(pilots),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "common_raw_gap_expr": EXPECTED_RAW_GAP,
        "input_r40_manifest": rel(r40_manifest_path),
        "input_r60_manifest": rel(r60_manifest_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_status_counts": dict(sorted(status_counts.items())),
        "predicate_id": PREDICATE_ID,
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "record_count_by_support_signature": dict(sorted(signature_counts.items())),
        "record_count_by_tree_id": dict(sorted(tree_counts.items())),
        "records": pilots,
        "recommended_next_task": (
            "A3/A4: use the emitted A2 common-edge pilot expressions to build "
            "a Weierstrass/Sturm sign certificate for raw gap, axis norm, and "
            "support-switch inequalities on the one-parameter ray domains."
        ),
        "symbolic_ring": {
            "variables": ["s = sin(theta)", "c = cos(theta)"],
            "relation": "c^2 + s^2 = 1",
            "weierstrass_substitution": "t = tan(theta/2)",
        },
        "tree_model_record_count": len(tree_model_summaries),
        "tree_models": tree_model_summaries,
        "uniform_axis_norm_square_expr": EXPECTED_AXIS_NORM_SQUARE,
    }
    write_json_lf(manifest_path, manifest)

    print(f"tree symbolic models emitted: {len(tree_model_summaries)}")
    print(f"B05 common-edge pilot records emitted: {len(pilots)}")
    print(f"accepted real B05 reports: 0")
    print(f"common raw gap expression: {EXPECTED_RAW_GAP}")
    print(f"axis norm square expression: {EXPECTED_AXIS_NORM_SQUARE}")
    print(f"object status counts: {dict(sorted(status_counts.items()))}")
    print(f"manifest: {rel(manifest_path)}")

    if len(tree_model_summaries) != 2:
        return 1
    if len(pilots) != len(r40_records):
        return 1
    if any(not item["symbolic_pilot_ready"] for item in pilots):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
