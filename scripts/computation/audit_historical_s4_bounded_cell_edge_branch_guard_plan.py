"""Guard plan for S4 bounded-cell edge-branch residual shared-face cells.

This report turns the bounded-cell edge-branch stability classifier into a
concrete implementation plan. It does not certify any new cells. It assigns each
of the 723 edge-branch cells to a proof route, records gap-risk bands, and
selects the first tactical batches for the next executable guard.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import json
import math
import sys
from pathlib import Path


CASE_ID = "historical_s4_median_planes"
REPORT_NAME = "bounded_cell_edge_branch_guard_plan_report.json"
SOURCE_CLASSIFIER_REPORT = "bounded_cell_edge_branch_stability_classifier_report.json"
MAX_STORED_EXAMPLES = 40

SCRIPT_PATH = Path(__file__).resolve()
sys.path.insert(0, str(SCRIPT_PATH.parent))

import mechanical_audit_lib as lib  # noqa: E402

RESULTS_DIR = lib.MECH_ROOT / "results" / CASE_ID

ROUTE_BY_PROFILE = {
    "assigned_edge_axis_sample_stable": "G1_fixed_assigned_axis_lower_bound_guard",
    "assigned_separating_edge_axis_switch": "G2_multi_edge_axis_switch_guard",
    "assigned_separating_face_normal_or_mixed_switch": "G3_hybrid_edge_face_axis_switch_guard",
    "assigned_axis_nonseparating_sample": "G4_adaptive_nonseparating_axis_isolation",
}

ROUTE_ORDER = [
    "G1_fixed_assigned_axis_lower_bound_guard",
    "G2_multi_edge_axis_switch_guard",
    "G3_hybrid_edge_face_axis_switch_guard",
    "G4_adaptive_nonseparating_axis_isolation",
]

ROUTE_DESCRIPTIONS = {
    "G1_fixed_assigned_axis_lower_bound_guard": {
        "purpose": "first executable guard target",
        "model": "use the center-assigned edge-edge axis as the branch axis; attempt a full-cell support/displacement lower bound",
        "acceptance_condition": "assigned branch gap lower bound minus full-cell displacement/support error is positive",
        "fallback": "if the bound fails, route to G2 or adaptive subdivision by local best-axis samples",
    },
    "G2_multi_edge_axis_switch_guard": {
        "purpose": "second executable guard target",
        "model": "use the assigned axis plus sampled best edge axes as a finite candidate family; prove at least one edge branch separates over each subcell or split by switch pattern",
        "acceptance_condition": "finite multi-axis branch ledger covers the cell or all adaptive children",
        "fallback": "subdivide direction/radius first, then theta only for persistent low-gap cells",
    },
    "G3_hybrid_edge_face_axis_switch_guard": {
        "purpose": "hybrid routing target",
        "model": "combine edge-axis support bounds with the existing face-normal formulas on subregions where sampled best axes switch to face normals",
        "acceptance_condition": "edge or face-normal branch ledger covers every child after controlled subdivision",
        "fallback": "split into face-normal-recheck and edge-switch batches",
    },
    "G4_adaptive_nonseparating_axis_isolation": {
        "purpose": "do not attack with a fixed assigned-axis guard first",
        "model": "isolate the 22 coarse cells where the center-assigned edge axis already fails at a sample; subdivide and reclassify before proof attempts",
        "acceptance_condition": "children move to G1/G2/G3 or produce a smaller explicit obstruction ledger",
        "fallback": "if children remain nonseparating, promote to a dedicated local-axis search rather than a branch formula guard",
    },
}


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def rounded(value: float | None, digits: int = 12) -> float | None:
    if value is None:
        return None
    if math.isinf(float(value)):
        return float(value)
    return round(float(value), digits)


def quantiles(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {key: None for key in ["min", "p05", "p10", "p25", "p50", "p75", "p90", "p95", "max"]}
    ordered = sorted(values)
    n = len(ordered)

    def q(percent: float) -> float:
        if n == 1:
            return ordered[0]
        position = percent * (n - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "min": rounded(ordered[0], 15),
        "p05": rounded(q(0.05), 15),
        "p10": rounded(q(0.10), 15),
        "p25": rounded(q(0.25), 15),
        "p50": rounded(q(0.50), 15),
        "p75": rounded(q(0.75), 15),
        "p90": rounded(q(0.90), 15),
        "p95": rounded(q(0.95), 15),
        "max": rounded(ordered[-1], 15),
    }


def add_example(bucket: list[dict], record: dict) -> None:
    if len(bucket) < MAX_STORED_EXAMPLES:
        bucket.append(record)


def gap_band(gap_min: float | None) -> str:
    if gap_min is None:
        return "gap_unknown"
    if gap_min <= 0.0:
        return "gap_zero_or_nonseparating"
    if gap_min < 1.0e-5:
        return "gap_tiny_lt_1e-5"
    if gap_min < 1.0e-3:
        return "gap_small_1e-5_to_1e-3"
    if gap_min < 1.0e-2:
        return "gap_medium_1e-3_to_1e-2"
    return "gap_large_ge_1e-2"


def width_signature(cell: dict) -> str:
    return (
        f"theta={cell['widths']['theta_width_degrees']}|"
        f"radial={cell['widths']['radial_width_degrees']}|"
        f"sector={cell['widths']['direction_sector_width']}"
    )


def compact_cell(cell: dict, route: str, band: str) -> dict:
    return {
        "cell_id": cell["cell_id"],
        "tree_id": cell.get("tree_id"),
        "pair": cell["pair"],
        "kind": cell["kind"],
        "theta_interval_degrees": cell["theta_interval_degrees"],
        "radial_interval_degrees": cell["radial_interval_degrees"],
        "direction_sector": cell["direction_sector"],
        "assigned_axis_name": cell["assigned_axis_name"],
        "sample_profile": cell["sample_profile"],
        "route": route,
        "gap_band": band,
        "assigned_axis_gap_interval": cell["assigned_axis_gap_interval"],
        "assigned_axis_best_sample_count": cell["assigned_axis_best_sample_count"],
        "assigned_axis_separating_sample_count": cell["assigned_axis_separating_sample_count"],
        "sample_count": cell["sample_count"],
        "best_axis_name_counts": cell["best_axis_name_counts"],
        "widths": cell["widths"],
    }


def annotate_target_cells(target_report: dict) -> list[dict]:
    tree_id = target_report["target"]["tree_id"]
    cells = []
    for cell in target_report["cell_reports"]:
        profile = cell["sample_profile"]
        route = ROUTE_BY_PROFILE[profile]
        gap_min = cell["assigned_axis_gap_interval"][0]
        band = gap_band(None if gap_min is None else float(gap_min))
        cells.append({**cell, "tree_id": tree_id, "route": route, "gap_band": band})
    return cells


def summarize_cells(cells: list[dict]) -> dict:
    route_counts = Counter()
    profile_counts = Counter()
    tree_counts = Counter()
    route_tree_counts = defaultdict(Counter)
    route_profile_counts = defaultdict(Counter)
    route_gap_band_counts = defaultdict(Counter)
    route_axis_counts = defaultdict(Counter)
    route_width_counts = defaultdict(Counter)
    route_kind_counts = defaultdict(Counter)
    gap_min_by_route = defaultdict(list)
    gap_max_by_route = defaultdict(list)
    best_fraction_by_route = defaultdict(list)
    separating_fraction_by_route = defaultdict(list)
    examples = defaultdict(list)

    for cell in cells:
        route = cell["route"]
        profile = cell["sample_profile"]
        route_counts[route] += 1
        profile_counts[profile] += 1
        tree_counts[cell["tree_id"]] += 1
        route_tree_counts[route][cell["tree_id"]] += 1
        route_profile_counts[route][profile] += 1
        route_gap_band_counts[route][cell["gap_band"]] += 1
        route_axis_counts[route][cell["assigned_axis_name"]] += 1
        route_width_counts[route][width_signature(cell)] += 1
        route_kind_counts[route][cell["kind"]] += 1
        gap_min, gap_max = cell["assigned_axis_gap_interval"]
        if gap_min is not None:
            gap_min_by_route[route].append(float(gap_min))
        if gap_max is not None:
            gap_max_by_route[route].append(float(gap_max))
        best_fraction_by_route[route].append(cell["assigned_axis_best_sample_count"] / cell["sample_count"])
        separating_fraction_by_route[route].append(cell["assigned_axis_separating_sample_count"] / cell["sample_count"])
        add_example(examples[route], compact_cell(cell, route, cell["gap_band"]))

    route_reports = []
    for route in ROUTE_ORDER:
        count = route_counts.get(route, 0)
        route_reports.append(
            {
                "route": route,
                "cell_count": count,
                "description": ROUTE_DESCRIPTIONS[route],
                "tree_counts": dict(route_tree_counts[route].most_common()),
                "profile_counts": dict(route_profile_counts[route].most_common()),
                "gap_band_counts": dict(route_gap_band_counts[route].most_common()),
                "cell_kind_counts": dict(route_kind_counts[route].most_common()),
                "top_assigned_axis_counts": dict(route_axis_counts[route].most_common(16)),
                "top_width_signatures": dict(route_width_counts[route].most_common(16)),
                "assigned_gap_min_quantiles": quantiles(gap_min_by_route[route]),
                "assigned_gap_max_quantiles": quantiles(gap_max_by_route[route]),
                "assigned_best_sample_fraction_quantiles": quantiles(best_fraction_by_route[route]),
                "assigned_separating_sample_fraction_quantiles": quantiles(separating_fraction_by_route[route]),
                "examples": examples[route],
            }
        )

    first_guard_count = route_counts.get("G1_fixed_assigned_axis_lower_bound_guard", 0)
    sample_separating_count = sum(
        route_counts.get(route, 0)
        for route in [
            "G1_fixed_assigned_axis_lower_bound_guard",
            "G2_multi_edge_axis_switch_guard",
            "G3_hybrid_edge_face_axis_switch_guard",
        ]
    )
    adaptive_count = route_counts.get("G4_adaptive_nonseparating_axis_isolation", 0)
    return {
        "summary_metrics": {
            "input_edge_branch_cell_count": len(cells),
            "route_count": len(route_reports),
            "first_guard_fixed_axis_cell_count": first_guard_count,
            "sample_separating_guard_candidate_cell_count": sample_separating_count,
            "adaptive_isolation_cell_count": adaptive_count,
            "route_counts": {route: route_counts.get(route, 0) for route in ROUTE_ORDER},
            "sample_profile_counts": dict(profile_counts.most_common()),
            "tree_counts": dict(tree_counts.most_common()),
        },
        "route_reports": route_reports,
    }


def build_report() -> dict:
    classifier = load_json(RESULTS_DIR / SOURCE_CLASSIFIER_REPORT)
    target_cells = []
    target_summaries = []
    for target in classifier["target_reports"]:
        cells = annotate_target_cells(target)
        target_cells.extend(cells)
        target_summary = summarize_cells(cells)
        target_summaries.append(
            {
                "target": target["target"],
                "summary_metrics": target_summary["summary_metrics"],
                "route_reports": target_summary["route_reports"],
            }
        )
    aggregate = summarize_cells(target_cells)
    return {
        "case_id": CASE_ID,
        "status": "bounded_cell_edge_branch_guard_plan_completed",
        "source_reports": [
            f"results/{CASE_ID}/{SOURCE_CLASSIFIER_REPORT}",
            f"results/{CASE_ID}/bounded_cell_face_normal_formula_guard_report.json",
            f"results/{CASE_ID}/bounded_cell_residual_shared_face_inventory_report.json",
        ],
        "target": {
            "description": "implementation plan for bounded-cell edge-branch residual shared-face closure",
            "certification_status": "plan_only_no_new_cells_certified",
            "route_order": ROUTE_ORDER,
        },
        "summary_metrics": aggregate["summary_metrics"],
        "route_reports": aggregate["route_reports"],
        "target_reports": target_summaries,
        "implementation_sequence": [
            {
                "step": "E1",
                "route": "G1_fixed_assigned_axis_lower_bound_guard",
                "target_cell_count": aggregate["summary_metrics"]["route_counts"]["G1_fixed_assigned_axis_lower_bound_guard"],
                "deliverable": "first executable full-cell lower-bound guard over sample-stable assigned edge-axis cells",
            },
            {
                "step": "E2",
                "route": "G2_multi_edge_axis_switch_guard",
                "target_cell_count": aggregate["summary_metrics"]["route_counts"]["G2_multi_edge_axis_switch_guard"],
                "deliverable": "multi-edge-axis candidate guard or targeted split by edge-axis switch signature",
            },
            {
                "step": "E3",
                "route": "G3_hybrid_edge_face_axis_switch_guard",
                "target_cell_count": aggregate["summary_metrics"]["route_counts"]["G3_hybrid_edge_face_axis_switch_guard"],
                "deliverable": "hybrid edge/face-normal guard after subcell routing",
            },
            {
                "step": "E4",
                "route": "G4_adaptive_nonseparating_axis_isolation",
                "target_cell_count": aggregate["summary_metrics"]["route_counts"]["G4_adaptive_nonseparating_axis_isolation"],
                "deliverable": "adaptive subdivision and reclassification of nonseparating-sample cells",
            },
        ],
        "limitations": [
            "This is an implementation plan derived from a finite sample classifier; it certifies no new edge-branch cells.",
            "The route labels are proof-workflow targets, not mathematical statuses of the full cells.",
            "Full-cell certification still requires executable lower-bound/adaptive reports and closure overlays.",
            "This report does not cover theta=0, dynamic class connectedness, physical hinge thickness, CAD, mesh export, or printability.",
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
                "summary_metrics": report["summary_metrics"],
                "implementation_sequence": report["implementation_sequence"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())