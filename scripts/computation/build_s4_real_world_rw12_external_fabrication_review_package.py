"""Build RW12 compact external fabrication/reviewer package.

RW12 is the handoff artifact: only necessary fabrication/review files, a clear
checklist, hash manifest, and operational instructions.  It intentionally omits
ambiguous assembly previews and historical rejected routes.
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_WORLD = ROOT / "results" / "historical_s4_median_planes" / "real_world"
RW10 = REAL_WORLD / "rw10_digital_final_prototype_package"
RW11 = REAL_WORLD / "rw11_tolerance_variant_package"
OUT = REAL_WORLD / "rw12_external_fabrication_review_package"
DOC = ROOT / "docs" / "S4_RW12_EXTERNAL_FABRICATION_REVIEW_PACKAGE.md"

RW10_MANIFEST = RW10 / "rw10_digital_final_prototype_manifest.json"
RW10_REPORT = RW10 / "rw10_digital_final_prototype_package_report.json"
RW11_REPORT = RW11 / "rw11_tolerance_variant_package_report.json"
RW11_MATRIX = RW11 / "RW11_TOLERANCE_DECISION_MATRIX.csv"

INCLUDED_PIN_VARIANTS = [
    ("v02_loose_fdm_2p40", "first printed-pin option / loose FDM"),
    ("v03_nominal_rw10_2p50", "nominal RW10 reference / metal pin target"),
    ("v04_tight_2p60", "after-measurement tighter option"),
]

CLAIM_BOUNDARY = (
    "RW12 is a compact digital external-fabrication review package only. It "
    "does not claim physical print success, measured tolerances, insertion, "
    "rotation, durability, support-cleanup safety, or hingeability."
)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_safe_clean(path: Path) -> None:
    resolved = path.resolve()
    base = REAL_WORLD.resolve()
    if base not in resolved.parents and resolved != base:
        raise RuntimeError(f"refusing to clean outside real-world results: {resolved}")
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def load_json(path: Path) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def record_existing(path: Path, role: str, source_label: str, expected_sha: str | None = None) -> dict:
    if not path.exists():
        raise FileNotFoundError(path)
    digest = sha256(path)
    return {
        "role": role,
        "source_label": source_label,
        "path": rel(path),
        "bytes": path.stat().st_size,
        "sha256": digest,
        "expected_sha256": expected_sha,
        "matches_expected_sha256": expected_sha is None or digest == expected_sha,
    }


def copy_file(src: Path, dst: Path, role: str, source_label: str, expected_sha: str | None = None) -> dict:
    if not src.exists():
        raise FileNotFoundError(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return record_existing(dst, role, source_label, expected_sha)


def copy_body_files(rw10_manifest: dict) -> list[dict]:
    records = []
    for component in rw10_manifest["fabrication_components"]:
        if component["component_kind"] != "printed_pieces":
            continue
        cid = component["component_id"]
        for ext, info in component["artifact_copies"].items():
            src = ROOT / info["target"]
            suffix = ".3mf" if ext == "threemf" else ".stl"
            dst = OUT / "fabrication_files" / "body_pieces" / f"{cid}{suffix}"
            records.append(copy_file(src, dst, "fabrication_body_piece", cid, info["sha256"]))
    return records


def copy_pin_variant_files() -> list[dict]:
    records = []
    for variant_id, label in INCLUDED_PIN_VARIANTS:
        variant_dir = RW11 / "pin_variants" / variant_id
        if not variant_dir.exists():
            raise FileNotFoundError(variant_dir)
        for src in sorted(variant_dir.glob("*.stl")):
            dst = OUT / "fabrication_files" / "pin_options" / variant_id / src.name
            records.append(copy_file(src, dst, "optional_pin_variant", label))
    return records


def write_text_artifacts(records: list[dict], rw10_manifest: dict) -> list[dict]:
    out_records = []
    readme = OUT / "README_RW12_EXTERNAL_FABRICATION_REVIEW.md"
    readme.write_text(f"""# RW12 compact external fabrication/reviewer package

Status: `rw12_external_fabrication_review_package_ready_no_physical_claim`.

This is the compact handoff package for TREE_007. It contains only the files a
reviewer or fabricator should inspect first:

- four RW10 body-preserving printed body pieces (`STL` and `3MF`);
- three practical pin-diameter option sets from RW11 (`2.40`, `2.50`, `2.60` mm);
- checklist, operating instructions, tolerance matrix, and hash manifest.

Assembly preview files are intentionally omitted. They are useful for internal
inspection but too easy to mistake for fabrication geometry. Print the separate
body pieces and choose a pin strategy after review.

## Recommended review order

1. Read `CLAIM_BOUNDARY.md`.
2. Read `OPERATING_INSTRUCTIONS.md`.
3. Review `RW12_FABRICATOR_CHECKLIST.csv`.
4. Inspect the four body pieces under `fabrication_files/body_pieces`.
5. Choose pin strategy from `fabrication_files/pin_options` and
   `reference/RW11_TOLERANCE_DECISION_MATRIX.csv`.
6. Verify hashes against `RW12_FILE_MANIFEST.csv` before fabrication.

## Boundary

{CLAIM_BOUNDARY}
""", encoding="utf-8", newline="\n")
    out_records.append(record_existing(readme, "package_instruction", "generated_readme"))

    boundary = OUT / "CLAIM_BOUNDARY.md"
    boundary.write_text(f"""# RW12 claim boundary

{CLAIM_BOUNDARY}

The digital geometry is traceable to RW10/RW11. The package does not certify:

- actual printed hole diameters;
- actual printed pin diameters;
- insertion force;
- hinge rotation;
- support cleanup effects;
- material wear/deformation;
- assembled mechanism success.

A physical claim requires external fabrication, measurement, and recorded review.
""", encoding="utf-8", newline="\n")
    out_records.append(record_existing(boundary, "package_instruction", "generated_claim_boundary"))

    instr = OUT / "OPERATING_INSTRUCTIONS.md"
    bom = rw10_manifest.get("bom_guidance", {})
    instr.write_text(f"""# RW12 operating instructions

## What to fabricate first

Fabricate the four body pieces in `fabrication_files/body_pieces`.

Preferred pin strategy:

1. Prefer commercial/metal dowel pins near `{bom.get('nominal_pin_diameter_mm', 2.5)}` mm if the fabricator can source and fit-check them.
2. If printing pins, start with `v02_loose_fdm_2p40` or `v03_nominal_rw10_2p50`.
3. Use `v04_tight_2p60` only after measuring printed hole diameters.

Nominal hole diameter encoded by the digital model: `{bom.get('nominal_hole_diameter_mm', 3.1)}` mm.
Nominal RW10 pin diameter: `{bom.get('nominal_pin_diameter_mm', 2.5)}` mm.

## Do not do this

- Do not print any internal assembly preview as one object.
- Do not treat generic PrusaSlicer G-code from earlier gates as machine-ready.
- Do not claim hingeability before physical insertion/rotation measurements exist.

## Required post-fabrication measurements

For each hinge axis:

- measured hole diameter on each knuckle/boss;
- measured pin diameter;
- insertion pass/fail;
- free rotation pass/fail;
- visible binding or cracking;
- support cleanup impact.
""", encoding="utf-8", newline="\n")
    out_records.append(record_existing(instr, "package_instruction", "generated_operating_instructions"))

    checklist = OUT / "RW12_FABRICATOR_CHECKLIST.csv"
    rows = [
        ("pre_fabrication", "Confirm body pieces are printed separately, not as a combined assembly", "required"),
        ("pre_fabrication", "Confirm printer/material/nozzle/profile selection", "required"),
        ("pre_fabrication", "Choose pin strategy: metal dowel, v02, v03, or v04", "required"),
        ("pre_fabrication", "Verify file hashes against RW12_FILE_MANIFEST.csv", "required"),
        ("fabrication", "Print body pieces with supports/orientation chosen by fabricator", "required"),
        ("fabrication", "Do not rely on generic G-code from previous diagnostic gates", "required"),
        ("post_fabrication", "Measure hole diameters and pin diameters", "required_for_physical_claim"),
        ("post_fabrication", "Record insertion and rotation result for each hinge", "required_for_physical_claim"),
        ("post_fabrication", "Report any cracking, binding, support cleanup damage, or tolerance mismatch", "required_for_physical_claim"),
    ]
    with checklist.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["phase", "item", "status_requirement"])
        writer.writerows(rows)
    out_records.append(record_existing(checklist, "package_checklist", "generated_fabricator_checklist"))

    return out_records


def copy_reference_files() -> list[dict]:
    records = []
    ref_dir = OUT / "reference"
    records.append(copy_file(RW11_MATRIX, ref_dir / RW11_MATRIX.name, "reference_tolerance_matrix", "rw11_matrix"))
    records.append(copy_file(RW10_REPORT, ref_dir / RW10_REPORT.name, "reference_report", "rw10_report"))
    records.append(copy_file(RW11_REPORT, ref_dir / RW11_REPORT.name, "reference_report", "rw11_report"))
    return records


def write_manifest(records: list[dict]) -> tuple[Path, Path]:
    manifest_csv = OUT / "RW12_FILE_MANIFEST.csv"
    with manifest_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(
            fh,
            fieldnames=["role", "source_label", "path", "bytes", "sha256", "expected_sha256", "matches_expected_sha256"],
        )
        writer.writeheader()
        writer.writerows(records)
    manifest_json = OUT / "rw12_external_fabrication_review_manifest.json"
    manifest_json.write_text(json.dumps({"files": records}, indent=2), encoding="utf-8", newline="\n")
    return manifest_csv, manifest_json


def zip_package() -> tuple[Path, str, int]:
    zip_path = OUT / "TREE_007_RW12_external_fabrication_review_package.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(OUT.rglob("*")):
            if path == zip_path or not path.is_file():
                continue
            zf.write(path, path.relative_to(OUT))
    return zip_path, sha256(zip_path), zip_path.stat().st_size


def write_report(records: list[dict], zip_path: Path, zip_hash: str, zip_bytes: int) -> dict:
    body_files = [r for r in records if r["role"] == "fabrication_body_piece"]
    pin_files = [r for r in records if r["role"] == "optional_pin_variant"]
    report = {
        "status": "rw12_external_fabrication_review_package_ready_no_physical_claim",
        "claim_boundary": CLAIM_BOUNDARY,
        "summary": {
            "body_piece_files": len(body_files),
            "body_piece_components": 4,
            "included_pin_variant_sets": [v[0] for v in INCLUDED_PIN_VARIANTS],
            "pin_variant_stl_files": len(pin_files),
            "assembly_preview_included": False,
            "all_expected_hashes_match": all(r.get("matches_expected_sha256", True) for r in records),
            "physical_claim_promoted": False,
            "zip_bytes": zip_bytes,
            "zip_sha256": zip_hash,
        },
        "acceptance": {
            "rw10_manifest_found": RW10_MANIFEST.exists(),
            "rw11_report_found": RW11_REPORT.exists(),
            "four_body_components_included_as_stl_and_3mf": len(body_files) == 8,
            "three_practical_pin_variants_included_for_three_axes": len(pin_files) == 9,
            "assembly_preview_omitted": True,
            "hash_manifest_written": (OUT / "RW12_FILE_MANIFEST.csv").exists(),
            "zip_written": zip_path.exists(),
            "no_physical_claim_promoted": True,
        },
        "artifacts": {
            "output_dir": rel(OUT),
            "zip": rel(zip_path),
            "file_manifest_csv": rel(OUT / "RW12_FILE_MANIFEST.csv"),
            "file_manifest_json": rel(OUT / "rw12_external_fabrication_review_manifest.json"),
            "report": rel(OUT / "rw12_external_fabrication_review_report.json"),
            "readme": rel(OUT / "README_RW12_EXTERNAL_FABRICATION_REVIEW.md"),
            "checklist": rel(OUT / "RW12_FABRICATOR_CHECKLIST.csv"),
            "doc": rel(DOC),
        },
    }
    report_path = OUT / "rw12_external_fabrication_review_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8", newline="\n")
    return report


def write_doc(report: dict) -> None:
    variants = ", ".join(report["summary"]["included_pin_variant_sets"])
    DOC.write_text(f"""# S4 RW12 external fabrication review package

Status: `{report['status']}`.

RW12 is the compact handoff package for an external reviewer or fabricator.  It
contains only the necessary first-pass files: the controlled RW10 body pieces,
three practical RW11 pin-variant sets, a checklist, operating instructions,
claim boundary, and hash manifest.  Ambiguous assembly-preview files are
intentionally omitted.

## Summary

| field | value |
| --- | --- |
| body_piece_files | {report['summary']['body_piece_files']} |
| body_piece_components | {report['summary']['body_piece_components']} |
| included_pin_variant_sets | {variants} |
| pin_variant_stl_files | {report['summary']['pin_variant_stl_files']} |
| assembly_preview_included | {report['summary']['assembly_preview_included']} |
| all_expected_hashes_match | {report['summary']['all_expected_hashes_match']} |
| physical_claim_promoted | {report['summary']['physical_claim_promoted']} |
| zip_sha256 | `{report['summary']['zip_sha256']}` |

## Main artifacts

| artifact | path |
| --- | --- |
| compact zip | `{report['artifacts']['zip']}` |
| manifest CSV | `{report['artifacts']['file_manifest_csv']}` |
| manifest JSON | `{report['artifacts']['file_manifest_json']}` |
| report | `{report['artifacts']['report']}` |
| README | `{report['artifacts']['readme']}` |
| checklist | `{report['artifacts']['checklist']}` |

## Claim boundary

{CLAIM_BOUNDARY}

## Next gate

Send RW12 to an external reviewer/fabricator.  If they provide a real printer,
material, nozzle, and profile, the next internal task is a printer-profile
specific slicer package.  If they fabricate it, the next task is measurement
ingest and physical review.  No physical claim is available before that.
""", encoding="utf-8", newline="\n")


def main() -> None:
    rw10_manifest = load_json(RW10_MANIFEST)
    ensure_safe_clean(OUT)

    records = []
    records.extend(copy_body_files(rw10_manifest))
    records.extend(copy_pin_variant_files())
    records.extend(copy_reference_files())
    records.extend(write_text_artifacts(records, rw10_manifest))
    manifest_csv, manifest_json = write_manifest(records)
    records.append(record_existing(manifest_csv, "package_manifest", "generated_manifest_csv"))
    records.append(record_existing(manifest_json, "package_manifest", "generated_manifest_json"))
    # Rewrite manifests with their own records included.
    write_manifest(records)

    zip_path, zip_hash, zip_bytes = zip_package()
    report = write_report(records, zip_path, zip_hash, zip_bytes)
    write_doc(report)

    failed = [k for k, v in report["acceptance"].items() if not v]
    print(json.dumps({
        "status": report["status"],
        "failed_acceptance": failed,
        "summary": report["summary"],
        "zip": report["artifacts"]["zip"],
    }, indent=2))
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
