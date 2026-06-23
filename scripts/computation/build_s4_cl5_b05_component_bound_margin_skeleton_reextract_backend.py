#!/usr/bin/env python
"""
Re-run B05 component-bound and M_gap/M_L/M_U skeleton extraction from R54.

R55 consumes the R54 center-projection/non-support endpoint records.  Unlike
R49, which could only use the R42 common-edge endpoint intervals, R54 provides
full piece-local endpoint packages for A/B/C/D/M_AB/M_CD.  This backend
therefore re-extracts conservative component-bound envelopes for all 23 support
partitions and rebuilds R50-style M_gap/M_L/M_U formula skeletons wherever the
support partition source stats can be joined.

This is still not an accepted B05 report layer.  It does not promote the R54
center-projection numerator attempts to positive g0 intervals, does not emit
per-side c_L/c_U support-competition intervals, does not emit tau/outward-error
intervals, does not emit operation enclosures, and does not claim positive
M_gap/M_L/M_U.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-COMPONENT-BOUND-MARGIN-SKELETON-REEXTRACT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_COMPONENT_BOUND_MARGIN_SKELETON_REEXTRACT"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
SOURCE_IDENTITY_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"
BOUND_RULE_ID = "R55-FULL-ENDPOINT-L1-COORDINATE-DIAMETER-PROJECTION-ENVELOPE"

DEFAULT_R54_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_center_projection_non_support_endpoint_backend_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "component_bound_margin_skeleton_reextract"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_component_bound_margin_skeleton_reextract_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_positive_g0_center_gap_interval_claim",
    "no_per_side_c_L_c_U_support_competition_interval_claim",
    "no_tau_outward_error_interval_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
    "no_formula_shape_real_report_claim",
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


def frac(value: dict[str, Any]) -> Fraction:
    return Fraction(int(value["num"]), int(value["den"]))


def frac_obj(value: Fraction) -> dict[str, str]:
    return {"den": str(value.denominator), "num": str(value.numerator)}


def interval_obj(*, lo: Fraction, hi: Fraction, unit: str, source_expr: str) -> dict[str, Any]:
    if lo < 0 or hi < lo:
        raise ValueError(f"invalid nonnegative interval: {lo}..{hi}")
    return {
        "endpoint_semantics": "closed",
        "hi": frac_obj(hi),
        "lo": frac_obj(lo),
        "source_expr": source_expr,
        "unit": unit,
    }


def load_manifest_records(manifest_path: Path) -> list[dict[str, Any]]:
    manifest = read_json(manifest_path)
    records = manifest.get("records") or []
    if not isinstance(records, list):
        raise TypeError(f"records must be a list: {manifest_path}")
    return records


def piece_blueprint(r48_record: dict[str, Any], role: str) -> dict[str, Any]:
    blueprint = r48_record.get("component_motion_bound_blueprint")
    if not isinstance(blueprint, dict):
        return {}
    item = blueprint.get(role)
    return item if isinstance(item, dict) else {}


def rodrigues_terms_from_blueprint(r48_record: dict[str, Any]) -> dict[str, Any] | None:
    blueprint = r48_record.get("component_motion_bound_blueprint")
    if not isinstance(blueprint, dict):
        return None
    terms = blueprint.get("rodrigues_terms")
    if isinstance(terms, dict) and isinstance(terms.get("value"), dict):
        return terms["value"]
    return None


def max_l1_diameter(
    package: dict[str, Any],
    labels: list[str],
) -> tuple[Fraction, list[dict[str, Any]], list[str]]:
    diameters = package.get("endpoint_coordinate_l1_diameter_bounds")
    if not isinstance(diameters, dict):
        return Fraction(0), [], labels
    missing = [label for label in labels if label not in diameters]
    entries: list[dict[str, Any]] = []
    maximum = Fraction(0)
    for label in labels:
        if label not in diameters:
            continue
        item = diameters[label]
        value = frac(item["coordinate_l1_diameter_bound"])
        maximum = max(maximum, value)
        entries.append({
            "coordinate_l1_diameter_bound": item["coordinate_l1_diameter_bound"],
            "coordinate_widths": item.get("coordinate_widths") or [],
            "label": label,
            "source_rule": item.get(
                "source_rule",
                "|u dot (x-y)| <= ||x-y||_1 for unit projection direction u",
            ),
        })
    return maximum, entries, missing


def support_bound_names(role: str, required: list[str]) -> list[str]:
    if required:
        return required
    if role == "lower_piece":
        return ["Delta_pos_L_support", "Delta_neg_L_support"]
    return ["Delta_pos_U_support", "Delta_neg_U_support"]


def non_support_bound_names(role: str) -> list[str]:
    if role == "lower_piece":
        return ["Delta_pos_L_non_support", "Delta_neg_L_non_support"]
    return ["Delta_pos_U_non_support", "Delta_neg_U_non_support"]


def build_bound_map(
    *,
    names: list[str],
    max_diameter: Fraction,
    piece_id: str,
    labels: list[str],
    label_class: str,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name in names:
        out[name] = interval_obj(
            lo=Fraction(0),
            hi=max_diameter,
            unit="projection",
            source_expr=(
                f"{name}:max_full_endpoint_L1_coordinate_diameter_envelope"
                f"({piece_id};{label_class};{','.join(labels)})"
            ),
        )
    return out


def build_piece_bounds(
    *,
    role: str,
    blueprint: dict[str, Any],
    package: dict[str, Any],
) -> dict[str, Any]:
    piece_id = str(blueprint.get("piece_id") or package.get("piece_id"))
    support_labels = [str(label) for label in blueprint.get("support_labels") or []]
    non_support_labels = [str(label) for label in blueprint.get("non_support_labels") or []]
    required_support_names = support_bound_names(
        role,
        [str(name) for name in blueprint.get("required_component_bound_names") or []],
    )
    support_max, support_entries, missing_support = max_l1_diameter(package, support_labels)
    non_support_max, non_support_entries, missing_non_support = max_l1_diameter(
        package, non_support_labels
    )
    support_ready = bool(required_support_names) and bool(support_labels) and not missing_support
    non_support_ready = not missing_non_support

    support_bounds = (
        build_bound_map(
            names=required_support_names,
            max_diameter=support_max,
            piece_id=piece_id,
            labels=support_labels,
            label_class="support",
        )
        if support_ready
        else {}
    )
    non_support_bounds = (
        build_bound_map(
            names=non_support_bound_names(role),
            max_diameter=non_support_max,
            piece_id=piece_id,
            labels=non_support_labels,
            label_class="non_support",
        )
        if non_support_labels and non_support_ready
        else {}
    )

    blockers = []
    if missing_support:
        blockers.append("support_label_endpoint_coordinate_intervals_missing")
    if missing_non_support:
        blockers.append("non_support_label_endpoint_coordinate_intervals_missing")
    if not support_ready:
        blockers.append("support_component_interval_bounds_not_emitted")

    checker_shape_piece = {}
    checker_shape_piece.update(support_bounds)
    checker_shape_piece.update(non_support_bounds)
    checker_shape_piece.update({
        "bound_rule_id": BOUND_RULE_ID,
        "non_support_labels": non_support_labels,
        "piece_id": piece_id,
        "support_labels": support_labels,
    })

    return {
        "blockers": blockers,
        "checker_shape_piece": checker_shape_piece,
        "component_interval_bounds": {
            "non_support": non_support_bounds,
            "support": support_bounds,
        },
        "component_interval_bounds_ready": support_ready,
        "full_endpoint_package_available": bool(package.get("full_endpoint_coordinate_intervals_ready")),
        "label_coordinate_diameter_bounds": {
            "non_support": non_support_entries,
            "support": support_entries,
        },
        "max_coordinate_l1_diameter_bound": {
            "non_support": frac_obj(non_support_max),
            "support": frac_obj(support_max),
        },
        "missing_non_support_endpoint_coordinate_labels": missing_non_support,
        "missing_support_endpoint_coordinate_labels": missing_support,
        "non_support_component_bounds_ready": non_support_ready,
        "non_support_labels": non_support_labels,
        "piece_id": piece_id,
        "required_component_bound_names": required_support_names,
        "role": role,
        "support_labels": support_labels,
    }


def finite_stats_semantics(stats: Any) -> str | None:
    if not isinstance(stats, dict):
        return None
    value = stats.get("finite_float_semantics")
    return str(value) if value is not None else None


def join_support_partition_stats(r48_record: dict[str, Any], support_signature: str) -> dict[str, Any]:
    r47_path = ROOT / r48_record["input_r47_support_partition_record"]
    r47_record = read_json(r47_path)
    source_path = ROOT / r47_record["input_support_source_record"]
    source_record = read_json(source_path)
    inventory = source_record.get("support_partition_inventory") or []
    if not isinstance(inventory, list):
        inventory = []
    matches = [
        item for item in inventory
        if isinstance(item, dict)
        and str(item.get("signature") or item.get("support_signature")) == support_signature
    ]
    matched = matches[0] if matches else None
    return {
        "input_r47_support_partition_record": rel(r47_path),
        "input_support_source_backend": r47_record.get("input_support_source_backend"),
        "input_support_source_record": rel(source_path),
        "matched_support_partition_count": len(matches),
        "matched_support_partition_stats": matched,
        "support_source_claim_level": source_record.get("claim_level"),
        "support_source_object_status": source_record.get("object_status"),
    }


def diagnostic_inputs(joined_stats: dict[str, Any]) -> dict[str, Any]:
    stats = joined_stats.get("matched_support_partition_stats")
    out: dict[str, Any] = {}
    if isinstance(stats, dict):
        for field in [
            "finite_gap_stats",
            "finite_minimum_stability_margin_stats",
            "finite_signed_component_bound_stats",
            "finite_signed_component_margin_stats",
        ]:
            if field in stats:
                out[field] = stats[field]
    return out


def diagnostic_signed_margin_min(joined_stats: dict[str, Any]) -> float | None:
    stats = joined_stats.get("matched_support_partition_stats")
    if not isinstance(stats, dict):
        return None
    margin = stats.get("finite_signed_component_margin_stats")
    if not isinstance(margin, dict):
        return None
    value = margin.get("min")
    if isinstance(value, (int, float)):
        return float(value)
    return None


def component_interval_inputs(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "bound_rule_id": candidate.get("bound_rule_id"),
        "lower_piece": candidate.get("lower_piece"),
        "rodrigues_terms": candidate.get("rodrigues_terms"),
        "upper_piece": candidate.get("upper_piece"),
    }


def build_formula_skeleton(
    *,
    candidate: dict[str, Any],
    joined_stats: dict[str, Any],
    lower: dict[str, Any],
    upper: dict[str, Any],
    r54_record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "source_identity_id": SOURCE_IDENTITY_ID,
        "formulae": {
            "M_gap": "g0 - Delta_pos(L,S_L) - Delta_neg(U,S_U) - tau",
            "M_L": "c_L - Delta_neg(L,S_L) - Delta_pos(L,N_L) - tau",
            "M_U": "c_U - Delta_pos(U,S_U) - Delta_neg(U,N_U) - tau",
        },
        "center_projection_attempt": r54_record.get("center_projection_attempt"),
        "component_interval_inputs": component_interval_inputs(candidate),
        "diagnostic_float_seed_stats": diagnostic_inputs(joined_stats),
        "non_support_requirements": {
            "lower_piece": {
                "non_support_component_bounds_ready": lower["non_support_component_bounds_ready"],
                "non_support_labels": lower["non_support_labels"],
                "piece_id": lower["piece_id"],
            },
            "upper_piece": {
                "non_support_component_bounds_ready": upper["non_support_component_bounds_ready"],
                "non_support_labels": upper["non_support_labels"],
                "piece_id": upper["piece_id"],
            },
        },
        "exact_seed_requirements": {
            "g0_center_gap_interval_ready": False,
            "lower_non_support_component_bounds_ready": lower["non_support_component_bounds_ready"],
            "lower_support_competition_margin_interval_ready": False,
            "tau_outward_error_interval_ready": False,
            "upper_non_support_component_bounds_ready": upper["non_support_component_bounds_ready"],
            "upper_support_competition_margin_interval_ready": False,
        },
    }


def build_record(r54_summary: dict[str, Any], out_dir: Path) -> dict[str, Any]:
    r54_path = ROOT / r54_summary["object_record"]
    r54 = read_json(r54_path)
    r48_path = ROOT / r54["input_r48_component_motion_bound_object_record"]
    r48 = read_json(r48_path)
    packages = r54["full_endpoint_coordinate_interval_packages"]
    lower = build_piece_bounds(
        role="lower_piece",
        blueprint=piece_blueprint(r48, "lower_piece"),
        package=packages["lower_piece"],
    )
    upper = build_piece_bounds(
        role="upper_piece",
        blueprint=piece_blueprint(r48, "upper_piece"),
        package=packages["upper_piece"],
    )
    rodrigues_terms = rodrigues_terms_from_blueprint(r48)
    rodrigues_ready = rodrigues_terms is not None
    support_component_ready = (
        lower["component_interval_bounds_ready"]
        and upper["component_interval_bounds_ready"]
        and rodrigues_ready
    )
    non_support_component_ready = (
        lower["non_support_component_bounds_ready"]
        and upper["non_support_component_bounds_ready"]
    )
    candidate = {
        "bound_rule_id": BOUND_RULE_ID,
        "bound_rule_semantics": (
            "Conservative rational projection envelope from R54 full endpoint coordinate "
            "interval L1 diameters; not accepted without g0/c_L/c_U/tau and operation enclosures."
        ),
        "lower_piece": lower["checker_shape_piece"],
        "rodrigues_terms": rodrigues_terms,
        "upper_piece": upper["checker_shape_piece"],
    }
    support_signature = str(r54["support_signature"])
    joined_stats = join_support_partition_stats(r48, support_signature)
    skeleton_ready = support_component_ready and joined_stats["matched_support_partition_count"] == 1
    signed_min = diagnostic_signed_margin_min(joined_stats)
    diagnostic_positive = signed_min is not None and signed_min > 0

    blockers = {
        "accepted_report_promotion_out_of_scope",
        "formula_shape_real_report_not_emitted",
        "operation_enclosures_missing",
        "exact_center_gap_interval_missing",
        "exact_support_competition_margin_intervals_missing",
        "tau_outward_error_interval_missing",
        "diagnostic_float_seed_stats_not_fraction_intervals",
        "positive_M_gap_M_L_M_U_not_extracted",
    }
    blockers.update(lower["blockers"])
    blockers.update(upper["blockers"])
    if not rodrigues_ready:
        blockers.add("rodrigues_terms_not_joined")
    if not support_component_ready:
        blockers.add("component_bound_interval_envelopes_not_ready")
    if not non_support_component_ready:
        blockers.add("non_support_component_bounds_not_ready")
    if joined_stats["matched_support_partition_count"] != 1:
        blockers.add("support_partition_diagnostic_stats_not_joined")
    if signed_min is not None and signed_min <= 0:
        blockers.add("diagnostic_signed_component_margin_nonpositive")
    if signed_min is None:
        blockers.add("diagnostic_signed_component_margin_missing")
    if not r54.get("g0_center_gap_interval_ready"):
        blockers.add("g0_center_gap_interval_not_promoted_from_full_domain_projection_attempt")
    if not r54.get("per_side_support_competition_intervals_ready"):
        blockers.add("per_side_c_L_c_U_support_competition_reextract_missing")

    if not skeleton_ready:
        object_status = "component_bound_margin_skeleton_reextract_blocked_support_stats_missing"
    elif not diagnostic_positive:
        object_status = "component_bound_margin_skeleton_reextract_ready_diagnostic_nonpositive_margin"
    else:
        object_status = "component_bound_margin_skeleton_reextract_ready_g0_c_tau_blocked"

    original_id = str(r54["original_report_id"])
    partition_index = int(r54["partition_index"])
    domain = str(r54["domain_family"])
    out_path = (
        out_dir
        / sanitize(domain)
        / sanitize(original_id)
        / f"partition_{partition_index:02d}_component_bound_margin_skeleton_reextract.json"
    )
    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": sorted(blockers),
        "case_id": CASE_ID,
        "center_projection_numerator_interval_ready": bool(
            r54.get("center_projection_numerator_interval_ready")
        ),
        "claim_level": CLAIM_LEVEL,
        "component_bound_interval_envelope_ready": support_component_ready,
        "component_bound_interval_reextract": {
            "bound_rule_id": BOUND_RULE_ID,
            "lower_piece": lower,
            "upper_piece": upper,
        },
        "component_motion_bounds_candidate": candidate,
        "component_motion_bounds_ready": support_component_ready,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "exact_gap_formula_skeleton": (
            build_formula_skeleton(
                candidate=candidate,
                joined_stats=joined_stats,
                lower=lower,
                upper=upper,
                r54_record=r54,
            )
            if skeleton_ready
            else None
        ),
        "formula_shape_contract_ready": False,
        "full_endpoint_coordinate_intervals_ready": bool(
            r54.get("full_endpoint_coordinate_intervals_ready")
        ),
        "g0_center_gap_interval_ready": False,
        "input_r48_component_motion_bound_object_record": rel(r48_path),
        "input_r54_center_projection_non_support_endpoint_record": rel(r54_path),
        "input_r54_manifest_summary_object_status": r54_summary.get("object_status"),
        "manifest_id": MANIFEST_ID,
        "margin_formula_skeleton_ready": skeleton_ready,
        "margin_source_join": joined_stats,
        "non_support_component_bounds_ready": non_support_component_ready,
        "nonclaim": NONCLAIMS,
        "object_id": (
            f"B05-COMPONENT-BOUND-MARGIN-SKELETON-REEXTRACT-{sanitize(original_id).upper()}-"
            f"PART-{partition_index:02d}"
        ),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r54.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r54.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "source_identity_id": SOURCE_IDENTITY_ID,
        "support_signature": support_signature,
        "tau_outward_error_interval_ready": False,
        "tree_id": r54.get("tree_id"),
    }
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "center_projection_numerator_interval_ready": record[
            "center_projection_numerator_interval_ready"
        ],
        "component_bound_interval_envelope_ready": support_component_ready,
        "component_motion_bounds_ready": support_component_ready,
        "diagnostic_positive_signed_component_margin_candidate": diagnostic_positive,
        "domain_family": domain,
        "exact_M_gap_M_L_M_U_ready": False,
        "formula_shape_contract_ready": False,
        "full_endpoint_coordinate_intervals_ready": record[
            "full_endpoint_coordinate_intervals_ready"
        ],
        "g0_center_gap_interval_ready": False,
        "margin_formula_skeleton_ready": skeleton_ready,
        "non_support_component_bounds_ready": non_support_component_ready,
        "object_record": rel(out_path),
        "object_status": object_status,
        "operation_enclosures_ready": False,
        "original_report": r54.get("original_report"),
        "original_report_id": original_id,
        "partition_index": partition_index,
        "per_side_support_competition_intervals_ready": False,
        "piece_pair": r54.get("piece_pair"),
        "support_signature": support_signature,
        "tau_outward_error_interval_ready": False,
        "tree_id": r54.get("tree_id"),
    }


def build_manifest(records: list[dict[str, Any]], r54_manifest: Path) -> dict[str, Any]:
    status_counts = Counter(record["object_status"] for record in records)
    domain_counts = Counter(record["domain_family"] for record in records)
    blocker_counts = Counter()
    diagnostic_positive = 0
    diagnostic_nonpositive = 0
    for summary in records:
        record = read_json(ROOT / summary["object_record"])
        blocker_counts.update(record["blockers"])
        if summary["margin_formula_skeleton_ready"]:
            if summary["diagnostic_positive_signed_component_margin_candidate"]:
                diagnostic_positive += 1
            else:
                diagnostic_nonpositive += 1
    return {
        "accepted_real_b05_report_count": sum(1 for r in records if r["accepted_real_b05_report"]),
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "center_projection_numerator_interval_ready_count": sum(
            1 for r in records if r["center_projection_numerator_interval_ready"]
        ),
        "claim_level": CLAIM_LEVEL,
        "component_bound_interval_envelope_ready_count": sum(
            1 for r in records if r["component_bound_interval_envelope_ready"]
        ),
        "component_motion_bounds_ready_count": sum(
            1 for r in records if r["component_motion_bounds_ready"]
        ),
        "diagnostic_nonpositive_signed_component_margin_candidate_count": diagnostic_nonpositive,
        "diagnostic_positive_signed_component_margin_candidate_count": diagnostic_positive,
        "exact_M_gap_M_L_M_U_ready_count": sum(1 for r in records if r["exact_M_gap_M_L_M_U_ready"]),
        "formula_shape_contract_ready_count": sum(1 for r in records if r["formula_shape_contract_ready"]),
        "full_endpoint_coordinate_intervals_ready_count": sum(
            1 for r in records if r["full_endpoint_coordinate_intervals_ready"]
        ),
        "g0_center_gap_interval_ready_count": sum(1 for r in records if r["g0_center_gap_interval_ready"]),
        "input_r54_manifest": rel(r54_manifest),
        "manifest_id": MANIFEST_ID,
        "margin_formula_skeleton_ready_count": sum(
            1 for r in records if r["margin_formula_skeleton_ready"]
        ),
        "non_support_component_bounds_ready_count": sum(
            1 for r in records if r["non_support_component_bounds_ready"]
        ),
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "operation_enclosures_ready_count": sum(1 for r in records if r["operation_enclosures_ready"]),
        "per_side_support_competition_intervals_ready_count": sum(
            1 for r in records if r["per_side_support_competition_intervals_ready"]
        ),
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": (
            "R56: isolate exact replayable g0 center-gap intervals and per-side c_L/c_U "
            "support-competition intervals from the R55 full-endpoint skeletons."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
        "tau_outward_error_interval_ready_count": sum(
            1 for r in records if r["tau_outward_error_interval_ready"]
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r54-manifest", default=DEFAULT_R54_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r54_manifest = ROOT / args.r54_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    records = [
        build_record(summary, out_dir)
        for summary in load_manifest_records(r54_manifest)
    ]
    manifest = build_manifest(records, r54_manifest)
    write_json_lf(manifest_path, manifest)

    print(f"input R54 records: {len(records)}")
    print(f"component-bound/margin skeleton records emitted: {manifest['object_record_count']}")
    print(
        "component-bound interval envelopes ready: "
        f"{manifest['component_bound_interval_envelope_ready_count']}"
    )
    print(f"component motion bounds ready: {manifest['component_motion_bounds_ready_count']}")
    print(f"non-support component bounds ready: {manifest['non_support_component_bounds_ready_count']}")
    print(f"margin formula skeletons ready: {manifest['margin_formula_skeleton_ready_count']}")
    print(
        "diagnostic positive signed-component candidates: "
        f"{manifest['diagnostic_positive_signed_component_margin_candidate_count']}"
    )
    print(
        "diagnostic nonpositive signed-component candidates: "
        f"{manifest['diagnostic_nonpositive_signed_component_margin_candidate_count']}"
    )
    print(f"g0 center gap intervals ready: {manifest['g0_center_gap_interval_ready_count']}")
    print(
        "per-side support competition intervals ready: "
        f"{manifest['per_side_support_competition_intervals_ready_count']}"
    )
    print(f"tau outward error intervals ready: {manifest['tau_outward_error_interval_ready_count']}")
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_M_gap_M_L_M_U_ready_count']}")
    print(f"operation enclosures ready: {manifest['operation_enclosures_ready_count']}")
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
