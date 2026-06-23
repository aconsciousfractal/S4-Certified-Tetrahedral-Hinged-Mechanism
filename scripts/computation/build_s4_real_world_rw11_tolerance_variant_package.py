"""Build RW11 tolerance-variant support package for S4 TREE_007.

RW11 is a digital-fabrication support gate.  It keeps the RW10 body-preserving
printed pieces fixed and generates simple dowel-style pin variants along the
same hinge axes as the RW10 removable-pin references.  It does not validate a
physical print or claim hingeability.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import trimesh


ROOT = Path(__file__).resolve().parents[1]
REAL_WORLD_DIR = ROOT / "results" / "historical_s4_median_planes" / "real_world"
RW10_DIR = REAL_WORLD_DIR / "rw10_digital_final_prototype_package"
RW10_MANIFEST = RW10_DIR / "rw10_digital_final_prototype_manifest.json"
OUT_DIR = REAL_WORLD_DIR / "rw11_tolerance_variant_package"
DOC_PATH = ROOT / "docs" / "S4_RW11_TOLERANCE_VARIANT_PACKAGE.md"

NOMINAL_HOLE_DIAMETER_MM = 3.1
NO_PHYSICAL_CLAIM = (
    "digital tolerance support package only; no physical fit, print, or "
    "hingeability claim"
)


@dataclass(frozen=True)
class Variant:
    variant_id: str
    pin_diameter_mm: float
    strategy: str
    use_note: str


VARIANTS = [
    Variant(
        "v01_loose_debug_2p20",
        2.20,
        "loose_debug",
        "First external-fit debug option if printed holes shrink strongly or if insertion must be very easy.",
    ),
    Variant(
        "v02_loose_fdm_2p40",
        2.40,
        "loose_fdm_first",
        "Conservative first FDM option; leaves extra clearance while staying closer to nominal.",
    ),
    Variant(
        "v03_nominal_rw10_2p50",
        2.50,
        "rw10_nominal",
        "RW10 nominal pin diameter; preferred reference for external metal/dowel pins before printed pins.",
    ),
    Variant(
        "v04_tight_2p60",
        2.60,
        "tight_after_measurement",
        "Use only if measured holes are close to nominal or oversized and more stiffness is desired.",
    ),
    Variant(
        "v05_very_tight_2p80",
        2.80,
        "risky_after_measurement_only",
        "Do not use first; included to bracket tolerance space if holes print substantially oversized.",
    ),
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def clean_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def read_manifest() -> dict:
    if not RW10_MANIFEST.exists():
        raise FileNotFoundError(f"RW10 manifest missing: {RW10_MANIFEST}")
    return json.loads(RW10_MANIFEST.read_text(encoding="utf-8"))


def mesh_axis_center_length(mesh: trimesh.Trimesh) -> tuple[np.ndarray, np.ndarray, float]:
    pts = np.asarray(mesh.vertices, dtype=float)
    center = pts.mean(axis=0)
    cov = np.cov((pts - center).T)
    vals, vecs = np.linalg.eigh(cov)
    axis = vecs[:, int(np.argmax(vals))]
    axis = axis / np.linalg.norm(axis)
    proj = (pts - center) @ axis
    length = float(proj.max() - proj.min())
    return center, axis, length


def cylinder_on_axis(center: np.ndarray, axis: np.ndarray, length: float, diameter: float) -> trimesh.Trimesh:
    mesh = trimesh.creation.cylinder(
        radius=diameter / 2.0,
        height=length,
        sections=64,
        segment=None,
    )
    transform = trimesh.geometry.align_vectors([0, 0, 1], axis)
    mesh.apply_transform(transform)
    mesh.apply_translation(center)
    return mesh


def copy_baseline_rw10(manifest: dict) -> list[dict]:
    baseline_dir = OUT_DIR / "rw10_baseline_fabrication_files"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for component in manifest["fabrication_components"]:
        cid = component["component_id"]
        kind = component["component_kind"]
        for ext, info in component["artifact_copies"].items():
            source = ROOT / info["target"]
            if not source.exists():
                raise FileNotFoundError(source)
            target = baseline_dir / kind / cid / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            copied.append(
                {
                    "component_id": cid,
                    "component_kind": kind,
                    "extension": ext,
                    "target": str(target.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                    "matches_rw10_sha256": sha256(target) == info["sha256"],
                }
            )
    return copied


def build_pin_variants(manifest: dict) -> tuple[list[dict], list[dict]]:
    pin_components = [
        component for component in manifest["fabrication_components"]
        if component["component_kind"] == "removable_pin_references"
    ]
    if len(pin_components) != 3:
        raise ValueError(f"expected 3 RW10 pin references, found {len(pin_components)}")

    variant_records = []
    decision_rows = []
    for variant in VARIANTS:
        diametral_clearance = NOMINAL_HOLE_DIAMETER_MM - variant.pin_diameter_mm
        radial_clearance = diametral_clearance / 2.0
        variant_dir = OUT_DIR / "pin_variants" / variant.variant_id
        variant_dir.mkdir(parents=True, exist_ok=True)
        decision_rows.append(
            {
                "variant_id": variant.variant_id,
                "pin_diameter_mm": f"{variant.pin_diameter_mm:.2f}",
                "nominal_hole_diameter_mm": f"{NOMINAL_HOLE_DIAMETER_MM:.2f}",
                "diametral_clearance_mm": f"{diametral_clearance:.2f}",
                "radial_clearance_mm": f"{radial_clearance:.2f}",
                "strategy": variant.strategy,
                "use_note": variant.use_note,
                "physical_claim": "none",
            }
        )
        components = []
        for component in pin_components:
            cid = component["component_id"]
            source = ROOT / component["artifact_copies"]["stl"]["target"]
            base_mesh = trimesh.load_mesh(source, process=False)
            center, axis, length = mesh_axis_center_length(base_mesh)
            pin_mesh = cylinder_on_axis(center, axis, length, variant.pin_diameter_mm)
            target = variant_dir / f"{cid}__{variant.variant_id}_simple_dowel.stl"
            pin_mesh.export(target)
            reloaded = trimesh.load_mesh(target, process=True)
            bbox = [float(x) for x in reloaded.extents]
            components.append(
                {
                    "component_id": cid,
                    "source_rw10_reference": str(source.relative_to(ROOT)).replace("\\", "/"),
                    "generated_stl": str(target.relative_to(ROOT)).replace("\\", "/"),
                    "bytes": target.stat().st_size,
                    "sha256": sha256(target),
                    "pin_diameter_mm": variant.pin_diameter_mm,
                    "axis_length_mm": length,
                    "mesh_watertight": bool(reloaded.is_watertight),
                    "mesh_is_volume": bool(reloaded.is_volume),
                    "mesh_volume_mm3": float(reloaded.volume),
                    "bbox_mm": bbox,
                    "note": "simple dowel proxy on RW10 pin axis; collar/retention behavior is not physically validated",
                }
            )
        variant_records.append(
            {
                "variant_id": variant.variant_id,
                "pin_diameter_mm": variant.pin_diameter_mm,
                "nominal_hole_diameter_mm": NOMINAL_HOLE_DIAMETER_MM,
                "nominal_diametral_clearance_mm": diametral_clearance,
                "nominal_radial_clearance_mm": radial_clearance,
                "strategy": variant.strategy,
                "use_note": variant.use_note,
                "components": components,
            }
        )
    return variant_records, decision_rows


def write_decision_matrix(rows: list[dict]) -> Path:
    path = OUT_DIR / "RW11_TOLERANCE_DECISION_MATRIX.csv"
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_external_review_note(matrix_path: Path) -> Path:
    path = OUT_DIR / "RW11_EXTERNAL_TOLERANCE_REVIEW.md"
    path.write_text(
        f"""# RW11 external tolerance review request

Status: `rw11_tolerance_variant_package_ready_external_review_no_physical_claim`.

This package supports external fabrication review of the RW10 TREE_007 digital prototype.
It keeps the RW10 body-preserving printed pieces fixed and adds simple dowel-style pin
variants along the same hinge axes.

## Use order

1. Treat the RW10 body pieces as the controlled body geometry.
2. Prefer commercial/metal dowel pins near the RW10 nominal diameter before printed pins.
3. Use the RW11 pin STL variants as diameter/clearance references, not as validated moving hardware.
4. Start with `v02_loose_fdm_2p40` or `v03_nominal_rw10_2p50` unless the fabricator recommends otherwise.
5. Use `v04_tight_2p60` or `v05_very_tight_2p80` only after measured hole data exists.

## Decision matrix

`{matrix_path.relative_to(OUT_DIR).as_posix()}`

## Claim boundary

{NO_PHYSICAL_CLAIM}.  This package does not certify insertion force, rotation,
wear, stiffness, material behavior, support cleanup, or successful assembly.
""",
        encoding="utf-8",
        newline="\n",
    )
    return path


def write_doc(report: dict) -> None:
    rows = "\n".join(
        f"| {v['variant_id']} | {v['pin_diameter_mm']:.2f} | "
        f"{v['nominal_diametral_clearance_mm']:.2f} | "
        f"{v['nominal_radial_clearance_mm']:.2f} | {v['strategy']} |"
        for v in report["pin_variants"]
    )
    DOC_PATH.write_text(
        f"""# S4 RW11 tolerance-variant package

Status: `{report['status']}`.

RW11 is a digital support package for external fabrication review.  It keeps the
RW10 body-preserving printed pieces fixed and creates simple dowel-style pin
variants along the same hinge axes.  This is the safest next step without a
printer: the mathematical body geometry stays controlled, while the external
fabricator gets a bounded tolerance menu.

## Summary

| field | value |
| --- | --- |
| baseline_rw10_files_copied | {report['summary']['baseline_rw10_files_copied']} |
| pin_variant_count | {report['summary']['pin_variant_count']} |
| generated_pin_stl_count | {report['summary']['generated_pin_stl_count']} |
| all_generated_pin_meshes_watertight | {report['summary']['all_generated_pin_meshes_watertight']} |
| all_generated_pin_meshes_valid_volume | {report['summary']['all_generated_pin_meshes_valid_volume']} |
| rw10_body_geometry_modified | {report['summary']['rw10_body_geometry_modified']} |
| physical_claim_promoted | {report['summary']['physical_claim_promoted']} |

## Pin/clearance variants

| variant | pin diameter mm | diametral clearance mm | radial clearance mm | strategy |
| --- | ---: | ---: | ---: | --- |
{rows}

## Main artifacts

| artifact | path |
| --- | --- |
| manifest | `{report['artifacts']['manifest']}` |
| report | `{report['artifacts']['report']}` |
| decision matrix | `{report['artifacts']['decision_matrix']}` |
| external review request | `{report['artifacts']['external_review_request']}` |
| baseline RW10 copied files | `{report['artifacts']['baseline_dir']}` |
| generated pin variants | `{report['artifacts']['pin_variants_dir']}` |

## Claim boundary

{NO_PHYSICAL_CLAIM}.  RW11 does not validate printed tolerances, insertion,
rotation, support cleanup, material wear, or assembled hingeability.

## Next gate

External fabricator review can now choose a pin strategy or request a specific
printer/material/nozzle profile.  A physical claim remains blocked until real
measurements exist.
""",
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    manifest = read_manifest()
    clean_dir(OUT_DIR)
    baseline = copy_baseline_rw10(manifest)
    variants, decision_rows = build_pin_variants(manifest)
    matrix_path = write_decision_matrix(decision_rows)
    external_note = write_external_review_note(matrix_path)

    all_pin_records = [component for variant in variants for component in variant["components"]]
    summary = {
        "baseline_rw10_files_copied": len(baseline),
        "baseline_hashes_match_rw10": all(item["matches_rw10_sha256"] for item in baseline),
        "pin_variant_count": len(variants),
        "generated_pin_stl_count": len(all_pin_records),
        "all_generated_pin_meshes_watertight": all(item["mesh_watertight"] for item in all_pin_records),
        "all_generated_pin_meshes_valid_volume": all(item["mesh_is_volume"] for item in all_pin_records),
        "rw10_body_geometry_modified": False,
        "physical_claim_promoted": False,
    }
    acceptance = {
        "rw10_manifest_found": RW10_MANIFEST.exists(),
        "baseline_files_preserve_rw10_hashes": summary["baseline_hashes_match_rw10"],
        "three_pin_axes_variantized": all(len(v["components"]) == 3 for v in variants),
        "five_clearance_variants_present": len(variants) == 5,
        "no_body_mesh_variant_generated": not summary["rw10_body_geometry_modified"],
        "no_physical_claim_promoted": not summary["physical_claim_promoted"],
    }

    report = {
        "status": "rw11_tolerance_variant_package_ready_external_review_no_physical_claim",
        "source_rw10_manifest": str(RW10_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "claim_boundary": NO_PHYSICAL_CLAIM,
        "nominal_hole_diameter_mm": NOMINAL_HOLE_DIAMETER_MM,
        "summary": summary,
        "acceptance": acceptance,
        "baseline_rw10_files": baseline,
        "pin_variants": variants,
        "artifacts": {
            "manifest": str((OUT_DIR / "rw11_tolerance_variant_manifest.json").relative_to(ROOT)).replace("\\", "/"),
            "report": str((OUT_DIR / "rw11_tolerance_variant_package_report.json").relative_to(ROOT)).replace("\\", "/"),
            "decision_matrix": str(matrix_path.relative_to(ROOT)).replace("\\", "/"),
            "external_review_request": str(external_note.relative_to(ROOT)).replace("\\", "/"),
            "baseline_dir": str((OUT_DIR / "rw10_baseline_fabrication_files").relative_to(ROOT)).replace("\\", "/"),
            "pin_variants_dir": str((OUT_DIR / "pin_variants").relative_to(ROOT)).replace("\\", "/"),
            "doc": str(DOC_PATH.relative_to(ROOT)).replace("\\", "/"),
        },
    }

    manifest_out = OUT_DIR / "rw11_tolerance_variant_manifest.json"
    report_out = OUT_DIR / "rw11_tolerance_variant_package_report.json"
    manifest_out.write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    report_out.write_text(json.dumps({
        "status": report["status"],
        "summary": summary,
        "acceptance": acceptance,
        "artifacts": report["artifacts"],
        "claim_boundary": report["claim_boundary"],
    }, indent=2), encoding="utf-8", newline="\n")
    write_doc(report)

    failed = [name for name, value in acceptance.items() if not value]
    print(json.dumps({
        "status": report["status"],
        "failed_acceptance": failed,
        "summary": summary,
        "output_dir": str(OUT_DIR),
    }, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
