from pathlib import Path
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "results/public_package_check.json"

REQUIRED = [
    "README.md", "README_REVIEWER.md", "REPRODUCE.md", "CITATION.cff", "LICENSE",
    "paper/s4_certified_tetrahedral_hinged_mechanism.tex",
    "paper/s4_certified_tetrahedral_hinged_mechanism.pdf",
    "paper/BUILD.md", "paper/refs.bib",
    "docs/PUBLIC_CLAIM_BOUNDARY.md", "docs/CLAIM_LEDGER.md", "docs/PROOF_OBLATIONS.md",
    "certified/a7d_one_parameter_theorem_wrapper_manifest.json",
    "certified/b04_a7c_contact_side_bridge_manifest.json",
    "certified/source_docs/README.md",
    "results/rw12_external_fabrication_review_package/rw12_external_fabrication_review_report.json",
    "results/rw12_external_fabrication_review_package/TREE_007_RW12_external_fabrication_review_package.zip",
    "paper/PUBLIC_PACKAGE_MANIFEST.json",
]
# Backward-compatible typo guard: prefer the correct PROOF_OBLIGATIONS path below.
REQUIRED = [x.replace("PROOF_OBLATIONS", "PROOF_OBLIGATIONS") for x in REQUIRED]

FORBIDDEN = [
    "physically validated",
    "physical hingeability is proved",
    "printed prototype validated",
    "measured prototype passes",
]
STALE_BLOCKING_PHRASES = [
    "paper package still remains blocked",
    "public export remains blocked",
    "internal package only",
    "paper/main.md",
    "appendix/rw12_external_fabrication_review",
    "PAPER_WORKSPACE_MANIFEST.json",
]
PUBLIC_TEXT = [
    "README.md",
    "paper/s4_certified_tetrahedral_hinged_mechanism.tex",
    "docs/PUBLIC_CLAIM_BOUNDARY.md",
]
STALE_SCAN_GLOBS = [
    "*.md", "docs/*.md", "paper/*.md", "paper/sections/*.tex", "certified/source_docs/*.md"
]

checks = []

def check(name, passed, detail=""):
    checks.append({"name": name, "passed": bool(passed), "detail": detail})

def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def pdf_page_count(path):
    data = path.read_bytes()
    # Sufficient for the deterministic pdfTeX output shipped here; catches stale manifest metadata.
    return data.count(b"/Type /Page") - data.count(b"/Type /Pages")

def load_json(rel):
    path = ROOT / rel
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def path_exists(rel):
    return (ROOT / rel).exists()

def iter_json_strings(obj, stack=()):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from iter_json_strings(v, stack + (str(k),))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from iter_json_strings(v, stack + (str(i),))
    elif isinstance(obj, str):
        yield stack, obj

def stack_is_provenance(stack):
    joined = "/".join(stack).lower()
    return "source_original" in joined or "provenance" in joined or joined.endswith("original")

for rel in REQUIRED:
    p = ROOT / rel
    check(f"required file exists: {rel}", p.exists() and p.is_file() and p.stat().st_size > 0, rel)

bridge = load_json("certified/b04_a7c_contact_side_bridge_manifest.json")
if bridge:
    check("B04/A7c bridge accepted count is 6", bridge.get("accepted_bridge_record_count") == 6, str(bridge.get("accepted_bridge_record_count")))
    check("B04/A7c bridge row count is 6", bridge.get("record_count") == 6, str(bridge.get("record_count")))
    missing_deps = [rel for rel in bridge.get("source_dependencies", []) if not path_exists(rel)]
    check("B04 bridge package-local source dependencies exist", not missing_deps, ", ".join(missing_deps[:8]))
    missing_records = []
    for rec in bridge.get("records", []):
        for key in ("object_record", "source_a7c_record"):
            rel = rec.get(key)
            if not rel or not path_exists(rel):
                missing_records.append(f"{rec.get('tree_id')}:{key}:{rel}")
    check("B04 bridge package-local record paths exist", not missing_records, ", ".join(missing_records[:8]))

rw_report = ROOT / "results/rw12_external_fabrication_review_package/rw12_external_fabrication_review_report.json"
rw_zip = ROOT / "results/rw12_external_fabrication_review_package/TREE_007_RW12_external_fabrication_review_package.zip"
if rw_report.exists() and rw_zip.exists():
    data = json.loads(rw_report.read_text(encoding="utf-8"))
    check("RW12 physical claim not promoted", data.get("summary", {}).get("physical_claim_promoted") is False)
    check("RW12 zip hash matches report", sha256(rw_zip) == data.get("summary", {}).get("zip_sha256"), sha256(rw_zip))

for rel in PUBLIC_TEXT:
    p = ROOT / rel
    if p.exists():
        text = p.read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN:
            check(f"forbidden phrase absent from {rel}: {phrase}", phrase not in text)

for pattern in STALE_SCAN_GLOBS:
    for p in ROOT.glob(pattern):
        if p.is_file():
            text = p.read_text(encoding="utf-8", errors="replace").lower()
            for phrase in STALE_BLOCKING_PHRASES:
                check(f"stale/blocking phrase absent from {p.relative_to(ROOT).as_posix()}: {phrase}", phrase.lower() not in text)

# A7d must not reintroduce the old A7c-alone route wording.
a7d = load_json("certified/a7d_one_parameter_theorem_wrapper_manifest.json")
if a7d:
    statement = a7d.get("scoped_wrapper_statement", "")
    check("A7d statement cites B04/A7c bridge", "B04/A7c" in statement or "B04/A7c-bridge" in statement, statement)
    check("A7d statement no longer routes to A7c alone", "A6/A7a/A7b/A7c certificate layers" not in statement, statement)
    missing = [rel for rel in a7d.get("package_local_sources", {}).values() if not path_exists(rel)]
    check("A7d package-local sources exist", not missing, ", ".join(missing[:8]))
    bad_object_records = [rec.get("object_record") for rec in a7d.get("records", []) if "object_record" in rec]
    check("A7d records do not use nonlocal object_record fields", not bad_object_records, ", ".join(map(str, bad_object_records[:8])))

# A7c package-local rows must explain the legacy accepted_real_report=false field.
a7c = load_json("certified/a7c_selected_hinge_contact_side_certificate_manifest.json")
if a7c:
    missing = []
    for rec in a7c.get("records", []):
        rel = rec.get("package_local_record")
        if not rel or not path_exists(rel):
            missing.append(str(rel))
    check("A7c package-local record paths exist", not missing, ", ".join(missing[:8]))

    bad = []
    for rel in [rec.get("package_local_record") for rec in a7c.get("records", []) if rec.get("package_local_record")]:
        row = load_json(rel)
        if not row:
            continue
        if row.get("accepted_real_report") is False:
            if not row.get("accepted_real_report_schema_note") or row.get("contact_side_certified_current_claim") is not True:
                bad.append(rel)
    check("A7c legacy accepted_real_report=false is explained in each row", not bad, ", ".join(bad[:8]))

# JSON provenance separation: historical source paths must be explicitly source_original/provenance.
json_paths = [
    "certified/a7d_one_parameter_theorem_wrapper_manifest.json",
    "certified/a7c_selected_hinge_contact_side_certificate_manifest.json",
    "certified/b04_a7c_contact_side_bridge_manifest.json",
]
json_paths += [str(p.relative_to(ROOT).as_posix()) for p in (ROOT / "certified/a7c_b04_contact_side_bridge_records").glob("*.json")]
json_paths += [str(p.relative_to(ROOT).as_posix()) for p in (ROOT / "certified/a7c_selected_hinge_contact_side_records").glob("*.json")]
violations = []
for rel in json_paths:
    data = load_json(rel)
    if data is None:
        continue
    for stack, value in iter_json_strings(data):
        if value.startswith("results/historical_s4_median_planes") or value.startswith("docs/S4_"):
            if not stack_is_provenance(stack):
                violations.append(f"{rel}:{'/'.join(stack)}={value}")
check("historical/internal JSON references are provenance-labelled", not violations, "; ".join(violations[:8]))

manifest_path = ROOT / "paper/PUBLIC_PACKAGE_MANIFEST.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    hash_fail = []
    report_rel = REPORT.relative_to(ROOT).as_posix()
    for item in manifest.get("paper_package_files", []):
        # The checker writes REPORT at the end of each run, so hashing that
        # self-output would make the gate fail on the next replay.
        if item["path"].replace("\\", "/") == report_rel:
            continue
        p = ROOT / item["path"]
        if not p.exists():
            hash_fail.append("missing:" + item["path"])
        elif item.get("sha256") and sha256(p) != item.get("sha256"):
            hash_fail.append("hash:" + item["path"])
    check("public package manifest file hashes match", not hash_fail, ", ".join(hash_fail[:8]))
    check("public package does not claim physical validation", manifest.get("physical_validation_claimed") is False)
    check("public package records deterministic PDF build policy", manifest.get("deterministic_pdf_build") is True)
    pdf_rel = "paper/s4_certified_tetrahedral_hinged_mechanism.pdf"
    observed_pages = pdf_page_count(ROOT / pdf_rel) if path_exists(pdf_rel) else None
    manifest_pages = manifest.get("summary", {}).get("paper_pdf_pages_observed_from_pdflatex")
    check("public package manifest PDF page count matches shipped PDF",
          observed_pages is not None and manifest_pages == observed_pages,
          f"manifest={manifest_pages} observed={observed_pages}")


# Public-facing surfaces must not expose internal methodology labels.
public_surface_paths = []
for pattern in ["*.md", "*.cff", "docs/*.md", "paper/*.md", "paper/*.tex", "paper/sections/*.tex", "paper/*.cff", "certified/*.json", "certified/source_docs/*.md"]:
    public_surface_paths.extend(ROOT.glob(pattern))
public_surface_bad = []
for path in sorted(set(public_surface_paths)):
    if not path.exists() or not path.is_file():
        continue
    rel = path.relative_to(ROOT).as_posix()
    text = path.read_text(encoding="utf-8", errors="replace")
    for banned in ["PAPP", "papp", "public-candidate", "public candidate", "PUBLIC_CANDIDATE", "package style", "PAPP-style"]:
        if banned in text:
            public_surface_bad.append(f"{rel}:{banned}")
check("public-facing text has no internal methodology labels", not public_surface_bad, "; ".join(public_surface_bad[:12]))


result = {
    "status": "pass" if all(c["passed"] for c in checks) else "fail",
    "checks_total": len(checks),
    "checks_pass": sum(1 for c in checks if c["passed"]),
    "checks_fail": sum(1 for c in checks if not c["passed"]),
    "checks": checks,
}
REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, indent=2))
if result["status"] != "pass":
    sys.exit(1)
