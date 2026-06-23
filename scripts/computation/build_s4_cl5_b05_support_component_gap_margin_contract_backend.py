#!/usr/bin/env python
"""
Build the B05 support/component/gap margin contract backend.

R44 consumes the R39 formula backend bridge and the R43 symbolic axis-norm
lower-bound backend.  It upgrades every real-source B05 contract record with
the now-proved positive common-edge axis lower bound, then inventories the
finite support/component/gap seeds available in the historical ledgers.

This is deliberately not an accepted B05 report generator.  The finite ledgers
contain useful support signatures, signed component margins, gap samples, and
stability margins, but they are still floating/adaptive evidence.  Until a
replayable exact extractor emits support labels, component motion intervals,
M_gap/M_L/M_U intervals, and operation enclosures, the real B05 reports must
remain diagnostic-only.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


SCRIPT_PATH = Path(__file__).resolve()
ROOT = SCRIPT_PATH.parents[1]
CASE_ID = "historical_s4_median_planes"
PREDICATE_ID = "B05_COMMON_EDGE_PROJECTION_SOUNDNESS"
MANIFEST_ID = "S4-CL5-B05-SUPPORT-COMPONENT-GAP-MARGIN-CONTRACT-2026-06-22"
CLAIM_LEVEL = "COMMON_EDGE_PROJECTION_SUPPORT_COMPONENT_GAP_MARGIN_CONTRACT_BACKEND"
BACKEND_LOCK_ID = "S4-CL5-EXACT-INTERVAL-BACKEND-SCHEMA-LOCK-2026-06-21"
R35_SOURCE_ID = "S4-CL5-B05-COMMON-EDGE-EXACT-GAP-DERIVATION-2026-06-22"

DEFAULT_R39_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_formula_backend_bridge_manifest.json"
)
DEFAULT_R43_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_axis_norm_symbolic_lower_bound_manifest.json"
)
DEFAULT_OUT_DIR = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "support_component_gap_margin_contract"
)
DEFAULT_MANIFEST = Path(
    "results/historical_s4_median_planes/exact_interval/b05_common_edge_projection/"
    "manifests/b05_support_component_gap_margin_contract_manifest.json"
)

NONCLAIMS = [
    "no_b05_accepted_true_report_claim",
    "no_exact_support_label_claim",
    "no_exact_component_motion_bound_claim",
    "no_exact_positive_M_gap_M_L_M_U_claim",
    "no_operation_enclosure_claim",
    "no_theorem_promotion_claim",
    "no_physical_hingeability_claim",
]

FINITE_SEED_KEYS = {
    "gap": "finite_gap_sample_count",
    "signed_component_bound": "finite_signed_component_bound_count",
    "signed_component_margin": "finite_signed_component_margin_count",
    "signed_component_margin_interval": "finite_signed_component_margin_interval_count",
    "minimum_stability_margin": "finite_minimum_stability_margin_count",
    "support_signature": "finite_support_signature_count",
    "lower_expanded_support_labels": "finite_lower_expanded_support_label_count",
    "upper_expanded_support_labels": "finite_upper_expanded_support_label_count",
    "terminal_records": "finite_terminal_record_block_count",
    "certified_leaves": "finite_certified_leaf_block_count",
}


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


def zero_seed_counts() -> dict[str, int]:
    return {value: 0 for value in FINITE_SEED_KEYS.values()}


def compact_sample(value: Any) -> Any:
    if isinstance(value, dict):
        return {"type": "dict", "keys": sorted(str(k) for k in value.keys())[:20]}
    if isinstance(value, list):
        return {"type": "list", "len": len(value)}
    return value


def ledger_seed_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "exists": False,
            "ledger": rel(path),
            "seed_counts": zero_seed_counts(),
            "status": "missing",
        }
    data = read_json(path)
    counts = zero_seed_counts()
    samples: dict[str, Any] = {}

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            for key, item in value.items():
                if key in FINITE_SEED_KEYS:
                    counts[FINITE_SEED_KEYS[key]] += 1
                    samples.setdefault(key, compact_sample(item))
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    has_support_seed = any(
        counts[name] > 0
        for name in [
            "finite_support_signature_count",
            "finite_lower_expanded_support_label_count",
            "finite_upper_expanded_support_label_count",
        ]
    )
    has_component_seed = any(
        counts[name] > 0
        for name in [
            "finite_signed_component_bound_count",
            "finite_signed_component_margin_count",
            "finite_signed_component_margin_interval_count",
        ]
    )
    has_gap_seed = any(
        counts[name] > 0
        for name in [
            "finite_gap_sample_count",
            "finite_signed_component_margin_count",
            "finite_minimum_stability_margin_count",
        ]
    )
    return {
        "exists": True,
        "ledger": rel(path),
        "ledger_status": data.get("status"),
        "seed_counts": counts,
        "seed_samples": samples,
        "source_kind": classify_source_ledger(path),
        "status": "finite_seeds_detected"
        if has_support_seed or has_component_seed or has_gap_seed
        else "no_relevant_finite_seed_detected",
    }


def classify_source_ledger(path: Path) -> str:
    name = path.name
    if "closure_stack" in name:
        return "adaptive_closure_stack_finite_ledger"
    if "margin_endgame" in name:
        return "adaptive_margin_endgame_finite_ledger"
    if "common_edge_guard" in name:
        return "adaptive_common_edge_guard_finite_ledger"
    if "common_edge_overlay" in name:
        return "bounded_cell_common_edge_overlay_finite_ledger"
    if "exact_source_layer" in name:
        return "exact_source_layer_manifest"
    if path.suffix in {".md", ".yaml", ".py"}:
        return "documentation_or_schema_or_checker_source"
    return "other_source"


def aggregate_seed_counts(summaries: list[dict[str, Any]]) -> dict[str, int]:
    total = zero_seed_counts()
    for summary in summaries:
        for key, value in summary.get("seed_counts", {}).items():
            total[key] = total.get(key, 0) + int(value)
    return total


def field_status(
    status: str,
    *,
    emitted_value: Any = None,
    blockers: list[str] | None = None,
    finite_seed_counts: dict[str, int] | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {"status": status}
    if emitted_value is not None:
        out["emitted_value"] = emitted_value
    if blockers:
        out["blockers"] = blockers
    if finite_seed_counts is not None:
        out["finite_seed_counts"] = finite_seed_counts
    return out


def source_ledger_paths(report: dict[str, Any]) -> list[Path]:
    paths: list[Path] = []
    for item in report.get("source_ledger") or []:
        if isinstance(item, str) and item.startswith("results/"):
            paths.append(ROOT / item)
    return paths


def support_seed_ready(seed_counts: dict[str, int]) -> bool:
    return any(
        seed_counts.get(key, 0) > 0
        for key in [
            "finite_support_signature_count",
            "finite_lower_expanded_support_label_count",
            "finite_upper_expanded_support_label_count",
        ]
    )


def component_seed_ready(seed_counts: dict[str, int]) -> bool:
    return any(
        seed_counts.get(key, 0) > 0
        for key in [
            "finite_signed_component_bound_count",
            "finite_signed_component_margin_count",
            "finite_signed_component_margin_interval_count",
        ]
    )


def margin_seed_ready(seed_counts: dict[str, int]) -> bool:
    return any(
        seed_counts.get(key, 0) > 0
        for key in [
            "finite_gap_sample_count",
            "finite_signed_component_margin_count",
            "finite_minimum_stability_margin_count",
        ]
    )


def index_r43_records(r43_manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in r43_manifest.get("records") or []:
        if isinstance(item, dict):
            out[str(item.get("original_report_id"))] = item
    return out


def build_record(
    bridge_summary: dict[str, Any],
    r43_by_report_id: dict[str, dict[str, Any]],
    *,
    ledger_cache: dict[str, dict[str, Any]],
    out_dir: Path,
) -> dict[str, Any]:
    bridge_path = ROOT / bridge_summary["bridge_record"]
    bridge = read_json(bridge_path)
    report_id = str(bridge["original_report_id"])
    r43_summary = r43_by_report_id.get(report_id)
    if r43_summary is None:
        raise KeyError(f"missing R43 record for {report_id}")
    r43_record_path = ROOT / r43_summary["object_record"]
    r43 = read_json(r43_record_path)
    original_report_path = ROOT / bridge["original_report"]
    original_report = read_json(original_report_path)

    ledger_summaries: list[dict[str, Any]] = []
    for ledger_path in source_ledger_paths(original_report):
        key = rel(ledger_path)
        if key not in ledger_cache:
            ledger_cache[key] = ledger_seed_summary(ledger_path)
        ledger_summaries.append(ledger_cache[key])
    seed_counts = aggregate_seed_counts(ledger_summaries)

    axis_interval = r43["axis_norm_square_interval"]
    axis_contract_ready = bool(r43.get("axis_nondegeneracy_contract_ready"))
    bridge_field_ready = dict(bridge["contract_field_ready"])
    bridge_field_status = dict(bridge["contract_field_status"])
    bridge_field_ready["axis_nondegeneracy.axis_norm_lower_bound"] = axis_contract_ready
    bridge_field_status["axis_nondegeneracy.axis_norm_lower_bound"] = field_status(
        "emitted_from_r43_positive_symbolic_interval",
        emitted_value=axis_interval,
    )

    support_blockers = [
        "exact_support_label_extractor_missing",
        "support_finite_extrema_operation_enclosure_missing",
    ]
    if not support_seed_ready(seed_counts):
        support_blockers.append("finite_support_seed_not_detected_for_this_source")
    support_status = (
        "finite_support_seeds_detected_exact_extractor_missing"
        if support_seed_ready(seed_counts)
        else "blocked_no_finite_support_seed_detected"
    )
    for key in [
        "support_state.lower_support_labels",
        "support_state.upper_support_labels",
        "support_state.lower_non_support_labels",
        "support_state.upper_non_support_labels",
    ]:
        bridge_field_ready[key] = False
        bridge_field_status[key] = field_status(
            support_status,
            blockers=support_blockers,
            finite_seed_counts=seed_counts,
        )

    component_blockers = [
        "exact_component_motion_bound_extractor_missing",
        "component_bound_operation_enclosure_missing",
    ]
    if not component_seed_ready(seed_counts):
        component_blockers.append("finite_component_margin_seed_not_detected_for_this_source")
    component_status = (
        "finite_component_margin_seeds_detected_exact_interval_extractor_missing"
        if component_seed_ready(seed_counts)
        else "blocked_no_finite_component_seed_detected"
    )
    for key in [
        "component_motion_bounds.lower_piece_interval_bounds",
        "component_motion_bounds.upper_piece_interval_bounds",
    ]:
        bridge_field_ready[key] = False
        bridge_field_status[key] = field_status(
            component_status,
            blockers=component_blockers,
            finite_seed_counts=seed_counts,
        )

    margin_blockers = [
        "exact_M_gap_M_L_M_U_interval_extractor_missing",
        "op_M_gap_operation_enclosure_missing",
        "real_report_gap_interval_still_diagnostic_zero_placeholder",
    ]
    if not margin_seed_ready(seed_counts):
        margin_blockers.append("finite_gap_or_margin_seed_not_detected_for_this_source")
    margin_status = (
        "finite_gap_margin_seeds_detected_exact_interval_extractor_missing"
        if margin_seed_ready(seed_counts)
        else "blocked_no_finite_gap_margin_seed_detected"
    )
    for key in ["exact_gap_formula.M_gap", "exact_gap_formula.M_L", "exact_gap_formula.M_U"]:
        bridge_field_ready[key] = False
        bridge_field_status[key] = field_status(
            margin_status,
            blockers=margin_blockers,
            finite_seed_counts=seed_counts,
        )

    bridge_field_status["operation_enclosures.required_ops"] = field_status(
        "axis_source_ready_support_and_gap_ops_missing",
        emitted_value={
            "op_axis_cross_product": "source_ready_from_R43_not_inserted_into_real_report",
            "existing_real_report_operation_ids": [
                op.get("op_id")
                for op in original_report.get("operation_enclosures", [])
                if isinstance(op, dict)
            ],
        },
        blockers=[
            "op_support_finite_extrema_missing",
            "op_M_gap_missing",
            "operation_enclosure_trace_not_replayed_as_schema_object",
        ],
    )
    bridge_field_ready["operation_enclosures.required_ops"] = False

    ready_count = sum(1 for value in bridge_field_ready.values() if value)
    blocked_count = sum(1 for value in bridge_field_ready.values() if not value)
    exact_support_ready = False
    exact_component_ready = False
    exact_margin_ready = False
    exact_ops_ready = False
    formula_shape_contract_ready = all(bridge_field_ready.values())
    blockers = sorted({
        blocker
        for status in bridge_field_status.values()
        for blocker in status.get("blockers", [])
    } | {
        "formula_shape_report_not_emitted",
        "accepted_report_promotion_out_of_scope",
    })
    object_status = (
        "axis_contract_ready_support_component_gap_exact_extractors_blocked"
        if axis_contract_ready
        else "axis_contract_not_ready"
    )

    record = {
        "accepted_real_b05_report": False,
        "backend_lock_id": BACKEND_LOCK_ID,
        "blockers": blockers,
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "contract_blocked_field_count": blocked_count,
        "contract_field_ready": bridge_field_ready,
        "contract_field_ready_count": ready_count,
        "contract_field_status": bridge_field_status,
        "domain_family": bridge.get("domain_family"),
        "exact_component_motion_bounds_ready": exact_component_ready,
        "exact_gap_margins_ready": exact_margin_ready,
        "exact_operation_enclosures_ready": exact_ops_ready,
        "exact_support_labels_ready": exact_support_ready,
        "finite_source_ledger_summaries": ledger_summaries,
        "finite_source_seed_counts": seed_counts,
        "formula_shape_contract_ready": formula_shape_contract_ready,
        "input_r39_bridge_record": rel(bridge_path),
        "input_r43_axis_norm_record": rel(r43_record_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_id": f"B05-SUPPORT-COMPONENT-GAP-CONTRACT-{sanitize(report_id)}",
        "object_status": object_status,
        "original_report": rel(original_report_path),
        "original_report_id": report_id,
        "piece_pair": bridge.get("piece_pair"),
        "predicate_id": PREDICATE_ID,
        "r35_source_identity_id": R35_SOURCE_ID,
        "r43_axis_nondegeneracy_contract_ready": axis_contract_ready,
        "r43_axis_norm_square_interval": axis_interval,
        "tree_id": bridge.get("tree_id"),
    }
    out_path = (
        out_dir
        / str(record["domain_family"])
        / f"{sanitize(report_id)}_support_component_gap_contract.json"
    )
    write_json_lf(out_path, record)
    return {
        "accepted_real_b05_report": False,
        "contract_blocked_field_count": blocked_count,
        "contract_field_ready_count": ready_count,
        "domain_family": record["domain_family"],
        "exact_component_motion_bounds_ready": exact_component_ready,
        "exact_gap_margins_ready": exact_margin_ready,
        "exact_operation_enclosures_ready": exact_ops_ready,
        "exact_support_labels_ready": exact_support_ready,
        "finite_component_seed_detected": component_seed_ready(seed_counts),
        "finite_gap_margin_seed_detected": margin_seed_ready(seed_counts),
        "finite_source_seed_counts": seed_counts,
        "finite_support_seed_detected": support_seed_ready(seed_counts),
        "formula_shape_contract_ready": formula_shape_contract_ready,
        "object_record": rel(out_path),
        "object_status": object_status,
        "original_report": rel(original_report_path),
        "original_report_id": report_id,
        "piece_pair": record["piece_pair"],
        "r43_axis_nondegeneracy_contract_ready": axis_contract_ready,
        "tree_id": record["tree_id"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--r39-manifest", default=DEFAULT_R39_MANIFEST.as_posix())
    parser.add_argument("--r43-manifest", default=DEFAULT_R43_MANIFEST.as_posix())
    parser.add_argument("--out-dir", default=DEFAULT_OUT_DIR.as_posix())
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST.as_posix())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    r39_path = ROOT / args.r39_manifest
    r43_path = ROOT / args.r43_manifest
    out_dir = ROOT / args.out_dir
    manifest_path = ROOT / args.manifest

    r39 = read_json(r39_path)
    r43 = read_json(r43_path)
    r43_by_report_id = index_r43_records(r43)
    bridges = r39.get("report_bridges") or []
    if not isinstance(bridges, list):
        raise TypeError("R39 report_bridges must be a list")

    ledger_cache: dict[str, dict[str, Any]] = {}
    records = [
        build_record(
            item,
            r43_by_report_id,
            ledger_cache=ledger_cache,
            out_dir=out_dir,
        )
        for item in bridges
    ]

    status_counts = Counter(item["object_status"] for item in records)
    domain_counts = Counter(item["domain_family"] for item in records)
    blocker_counts = Counter()
    seed_totals = zero_seed_counts()
    field_ready_counts = Counter()
    field_blocked_counts = Counter()
    for item in records:
        for key, value in item["finite_source_seed_counts"].items():
            seed_totals[key] = seed_totals.get(key, 0) + int(value)
        record = read_json(ROOT / item["object_record"])
        for field, ready in record["contract_field_ready"].items():
            if ready:
                field_ready_counts[field] += 1
            else:
                field_blocked_counts[field] += 1
        blocker_counts.update(record["blockers"])

    manifest = {
        "accepted_real_b05_report_count": 0,
        "axis_nondegeneracy_contract_ready_count": sum(
            1 for item in records if item["r43_axis_nondegeneracy_contract_ready"]
        ),
        "backend_lock_id": BACKEND_LOCK_ID,
        "blocker_counts": dict(sorted(blocker_counts.items())),
        "case_id": CASE_ID,
        "claim_level": CLAIM_LEVEL,
        "contract_blocked_field_counts": dict(sorted(field_blocked_counts.items())),
        "contract_ready_field_counts": dict(sorted(field_ready_counts.items())),
        "exact_component_motion_bounds_ready_count": sum(
            1 for item in records if item["exact_component_motion_bounds_ready"]
        ),
        "exact_gap_margins_ready_count": sum(
            1 for item in records if item["exact_gap_margins_ready"]
        ),
        "exact_operation_enclosures_ready_count": sum(
            1 for item in records if item["exact_operation_enclosures_ready"]
        ),
        "exact_support_labels_ready_count": sum(
            1 for item in records if item["exact_support_labels_ready"]
        ),
        "finite_component_seed_detected_count": sum(
            1 for item in records if item["finite_component_seed_detected"]
        ),
        "finite_gap_margin_seed_detected_count": sum(
            1 for item in records if item["finite_gap_margin_seed_detected"]
        ),
        "finite_source_ledger_count": len(ledger_cache),
        "finite_source_seed_totals": seed_totals,
        "finite_support_seed_detected_count": sum(
            1 for item in records if item["finite_support_seed_detected"]
        ),
        "formula_shape_contract_ready_count": sum(
            1 for item in records if item["formula_shape_contract_ready"]
        ),
        "input_r39_manifest": rel(r39_path),
        "input_r43_manifest": rel(r43_path),
        "manifest_id": MANIFEST_ID,
        "nonclaim": NONCLAIMS,
        "object_record_count": len(records),
        "object_status_counts": dict(sorted(status_counts.items())),
        "predicate_id": PREDICATE_ID,
        "recommended_next_task": (
            "R45: implement the exact support finite-extrema extractor that turns "
            "the detected finite support signatures and expanded-support labels "
            "into replayable support_state objects and op_support_finite_extrema "
            "operation enclosures."
        ),
        "record_count_by_domain_family": dict(sorted(domain_counts.items())),
        "records": records,
    }
    write_json_lf(manifest_path, manifest)

    print(f"input R39 bridge records: {len(records)}")
    print(
        "axis-nondegeneracy contracts ready: "
        f"{manifest['axis_nondegeneracy_contract_ready_count']}"
    )
    print(f"finite support seeds detected: {manifest['finite_support_seed_detected_count']}")
    print(f"finite component seeds detected: {manifest['finite_component_seed_detected_count']}")
    print(f"finite gap/margin seeds detected: {manifest['finite_gap_margin_seed_detected_count']}")
    print(f"exact support labels ready: {manifest['exact_support_labels_ready_count']}")
    print(
        "exact component motion bounds ready: "
        f"{manifest['exact_component_motion_bounds_ready_count']}"
    )
    print(f"exact M_gap/M_L/M_U ready: {manifest['exact_gap_margins_ready_count']}")
    print(f"operation enclosures ready: {manifest['exact_operation_enclosures_ready_count']}")
    print(f"formula-shape contract ready: {manifest['formula_shape_contract_ready_count']}")
    print(f"accepted real B05 reports: {manifest['accepted_real_b05_report_count']}")
    print(f"object status counts: {manifest['object_status_counts']}")
    print(f"manifest: {rel(manifest_path)}")

    if len(records) != len(r43_by_report_id):
        return 1
    if manifest["axis_nondegeneracy_contract_ready_count"] != len(records):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
