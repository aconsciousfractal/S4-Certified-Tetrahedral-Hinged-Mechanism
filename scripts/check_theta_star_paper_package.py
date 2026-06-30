"""
Paper-package consistency checker for the theta-star proof spine.

This is a bounded paper-package check, not a full mathematical replay.  It
verifies that every proof-spine artifact named for the addendum roadmap is
materially present and hash-consistent in extensions/theta_star_finite_atlas.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions" / "theta_star_finite_atlas"
PKG = EXT / "paper_package"
MANIFEST = PKG / "PAPER_PACKAGE_MANIFEST.json"
SHA = PKG / "SHA256SUMS.txt"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    checks.append((name, bool(condition), str(detail)))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

check("paper package manifest exists", MANIFEST.exists(), MANIFEST)
manifest = json.loads(MANIFEST.read_text(encoding="utf-8")) if MANIFEST.exists() else {}
check("paper package status is proof spine closure", manifest.get("status") == "proof_spine_materialized_with_public_addendum_promotion", manifest.get("status"))
check("scope mentions zero-thickness", "zero-thickness" in manifest.get("scope", ""), manifest.get("scope"))
check("scope mentions equal-magnitude", "equal-magnitude" in manifest.get("scope", ""), manifest.get("scope"))

expected = manifest.get("expected_artifacts", [])
files = manifest.get("files", [])
by_source = {item.get("source_basename"): item for item in files}
check("12 expected proof-spine artifacts", len(expected) == 12, len(expected))
check("12 manifest proof-spine files", len(files) == 12, len(files))
closure_files = manifest.get("closure_files", [])
check("3 closure files listed", set(closure_files) == {"PAPER_PROOF_SPINE_CLOSURE.json", "RED_TEAM_CLOSURE_REPORT.md", "PAPER_PROMOTION_DECISION.md"}, closure_files)
for rel in closure_files:
    path = PKG / rel
    check(f"closure file exists: {rel}", path.exists(), rel)

for name in expected:
    item = by_source.get(name)
    check(f"manifest entry exists: {name}", item is not None, name)
    if not item:
        continue
    path = PKG / item["path"]
    check(f"artifact exists: {name}", path.exists(), path)
    if path.exists():
        check(f"sha256 matches: {name}", sha256(path) == item.get("sha256"), name)
        check(f"size matches: {name}", path.stat().st_size == item.get("size_bytes"), name)


# Public package hygiene: proof-spine artifacts must not depend on private local
# workspace paths. Historical source locations may be represented only as
# redacted provenance fields, never as absolute P:/... strings.
private_path_hits = []
for json_path in (PKG / "artifacts" / "proof_spine").glob("*.json"):
    body = json_path.read_text(encoding="utf-8", errors="replace")
    if "P:/GitHub_puba/HAN" in body or "P:\\GitHub_puba\\HAN" in body:
        private_path_hits.append(str(json_path.relative_to(ROOT)))
check("proof-spine JSON has no private local workspace paths", not private_path_hits, private_path_hits)

check("SHA256SUMS exists", SHA.exists(), SHA)
if SHA.exists():
    for line in SHA.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected_hash, rel = line.split("  ", 1)
        path = PKG / rel
        check(f"sha listed file exists: {rel}", path.exists(), rel)
        if path.exists():
            check(f"sha listed file matches: {rel}", sha256(path) == expected_hash, rel)

# Lightweight semantic checks on core gates.
def load_artifact(name: str) -> dict:
    path = PKG / "artifacts" / "proof_spine" / name
    check(f"json exists: {name}", path.exists(), name)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

assembly = load_artifact("s4_theta_star_108_tree_theorem_assembly_gate.json")
assembly_replay = load_artifact("s4_theta_star_108_tree_theorem_assembly_gate_replay.json")
proof_gate = load_artifact("s4_theta_star_108_tree_theorem_proof_package_gate.json")
t6b = load_artifact("s4_theta_star_t6b_theorem_prose_audit.json")
posjam = load_artifact("s4_theta_star_positive_jam_max_over_8_certificate.json")
source = load_artifact("s4_theta_star_source_map_visibility_audit.json")

check("assembly gate pass", assembly.get("status") == "pass", assembly.get("status"))
check("assembly local theorem supported", assembly.get("local_theorem_supported") is True, assembly.get("local_theorem_supported"))
check("assembly source artifact public promotion false", assembly.get("public_promotion_ready") is False, assembly.get("public_promotion_ready"))
check("assembly replay pass", assembly_replay.get("status") == "pass", assembly_replay.get("status"))
check("proof gate pass with review obligations", proof_gate.get("status") == "pass_with_review_obligations", proof_gate.get("status"))
check("T6B pass with review obligations", t6b.get("status") == "pass_with_review_obligations", t6b.get("status"))
check("positive jam certificate pass", posjam.get("status") == "pass", posjam.get("status"))
check("positive jam cap sqrt(2)", posjam.get("t_cap_closed_form") == "sqrt(2)", posjam.get("t_cap_closed_form"))
check("source-map visibility pass", source.get("status") == "pass", source.get("status"))

summary = assembly.get("summary", {})
check("108 final records", summary.get("final_record_count") == 108 or len(assembly.get("final_records", [])) == 108, summary.get("final_record_count"))
check("final class counts expected", summary.get("final_class_counts") == {
    "exact_positive_theta_jam_package_source_locked": 8,
    "exact_endpoint_free_witness_transport_certificate": 36,
    "exact_instant_jam_8_row_gate_source_locked": 60,
    "one_parameter_wrapper_scope_source_locked": 4,
}, summary.get("final_class_counts"))
check("t-star counts expected", summary.get("t_star_counts") == {
    "sqrt(3) endpoint reached": 40,
    "0": 60,
    "sqrt(2)": 8,
}, summary.get("t_star_counts"))


# Proof-prose draft checks added by P0-03/P0-04 and updated for the
# companion addendum entry point.
DRAFT = EXT / "paper_draft"
final_tex = DRAFT / "theta_star_finite_atlas.tex"
flat_tex = DRAFT / "theta_star_finite_atlas_flat.tex"
final_pdf = DRAFT / "theta_star_finite_atlas.pdf"
build_doc = DRAFT / "BUILD.md"
handoff = EXT / "EXTERNAL_RED_TEAM_HANDOFF.md"
skeleton = DRAFT / "theta_star_addendum_skeleton.tex"
sec02 = DRAFT / "sections" / "02_formal_objects_and_tree_status_table.tex"
sec03 = DRAFT / "sections" / "03_finite_angle_conjugacy.tex"
sec04 = DRAFT / "sections" / "04_transport_and_theta_star_invariance.tex"
check("proof-prose draft README exists", (DRAFT / "README.md").exists(), DRAFT / "README.md")
check("standalone TeX companion addendum exists", final_tex.exists(), final_tex)
check("single-file flat TeX companion source exists", flat_tex.exists(), flat_tex)
check("standalone PDF companion addendum exists", final_pdf.exists(), final_pdf)
check("paper build instructions exist", build_doc.exists(), build_doc)
check("draft refs.bib exists", (DRAFT / "refs.bib").exists(), DRAFT / "refs.bib")
check("external red-team handoff exists", handoff.exists(), handoff)
check("compatibility skeleton exists", skeleton.exists(), skeleton)
check("section 02 formal objects and tree table exists", sec02.exists(), sec02)
check("section 03 finite-angle conjugacy exists", sec03.exists(), sec03)
check("section 04 theta-star invariance exists", sec04.exists(), sec04)
final_text = final_tex.read_text(encoding="utf-8", errors="replace") if final_tex.exists() else ""
flat_text = flat_tex.read_text(encoding="utf-8", errors="replace") if flat_tex.exists() else ""
skeleton_text = skeleton.read_text(encoding="utf-8", errors="replace") if skeleton.exists() else ""
sec02_text = sec02.read_text(encoding="utf-8", errors="replace") if sec02.exists() else ""
sec03_text = sec03.read_text(encoding="utf-8", errors="replace") if sec03.exists() else ""
sec04_text = sec04.read_text(encoding="utf-8", errors="replace") if sec04.exists() else ""
for phrase in [
    "Theta-Star Finite Atlas",
    "\\input{sections/02_formal_objects_and_tree_status_table}",
    "\\input{sections/03_finite_angle_conjugacy}",
    "\\input{sections/04_transport_and_theta_star_invariance}",
    "\\input{sections/08_instant_jam_class}",
]:
    check(f"standalone TeX contains: {phrase}", phrase in final_text, phrase)
check("single-file flat TeX contains no section inputs", "\\input{sections/" not in flat_text, flat_tex)
check("single-file flat TeX preserves generated tree table", "BEGIN GENERATED TREE STATUS TABLE" in flat_text, flat_tex)
check("external handoff names flat TeX", "theta_star_finite_atlas_flat.tex" in (handoff.read_text(encoding="utf-8", errors="replace") if handoff.exists() else ""), handoff)
check("compatibility skeleton points to standalone TeX", "\\input{theta_star_finite_atlas}" in skeleton_text, skeleton)
for phrase in ["Formal objects", "\\operatorname{Rows}(T)", "t=\\tan(\\theta/2)", "BEGIN GENERATED TREE STATUS TABLE"]:
    check(f"section 02 contains: {phrase}", phrase in sec02_text, phrase)
for phrase in ["Finite-angle scaffold conjugacy", "s'_{g(h)}", "(G C_j)^{-1}(G C_i) = C_j^{-1} C_i", "SAT"]:
    check(f"section 03 contains: {phrase}", phrase in sec03_text, phrase)
for phrase in ["Eight-row bijection", "t^*(T)=t^*(g(T))", "endpoint reached, not first contact", "The wrapper class is recorded separately"]:
    check(f"section 04 contains: {phrase}", phrase in sec04_text, phrase)

class_files = {
    "endpoint_free": DRAFT / "sections" / "05_endpoint_free_class.tex",
    "wrapper_scope": DRAFT / "sections" / "06_wrapper_scope_class.tex",
    "positive_jam": DRAFT / "sections" / "07_positive_jam_class.tex",
    "instant_jam": DRAFT / "sections" / "08_instant_jam_class.tex",
}
for label, path in class_files.items():
    check(f"class proof exists: {label}", path.exists(), path)
class_expected = {
    "endpoint_free": ["36 target trees", "T5c endpoint-free witness transport gate"],
    "wrapper_scope": ["4 target trees", "selected hinge-side"],
    "positive_jam": ["8 target trees", "max-over-8", "sqrt(2)"],
    "instant_jam": ["60 target trees", "all eight", "t^*=0"],
}
for label, phrases in class_expected.items():
    path = class_files[label]
    body = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    for phrase in phrases:
        check(f"class proof {label} contains: {phrase}", phrase in body, phrase)

proof_prose_checker = ROOT / "scripts" / "check_theta_star_proof_prose.py"
check("proof-prose checker exists", proof_prose_checker.exists(), proof_prose_checker)
if proof_prose_checker.exists():
    checker_text = proof_prose_checker.read_text(encoding="utf-8", errors="replace")
    for phrase in ["expected_final", "expected_t", "class_specs", "forbidden overclaim absent", "theta_star_finite_atlas.pdf"]:
        check(f"proof-prose checker contains: {phrase}", phrase in checker_text, phrase)

failed = [c for c in checks if not c[1]]
for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
print(f"\nstatus: {'pass' if not failed else 'fail'}")
print(f"checks: {len(checks) - len(failed)}/{len(checks)} pass")
if failed:
    sys.exit(1)
