"""
Paper-grade proof-prose checker for the theta-star finite-atlas draft.

This checker is intentionally bounded. It does not replay the geometry. It
checks that the local TeX proof-prose draft states the theorem with the right
scope, class decomposition, exact values, artifact spine, and a generated
108-tree status table matching the materialized T6 assembly artifact.
"""

from __future__ import annotations

from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions" / "theta_star_finite_atlas"
DRAFT = EXT / "paper_draft"
SECTIONS = DRAFT / "sections"
ART = EXT / "paper_package" / "artifacts" / "proof_spine"
ASSEMBLY = ART / "s4_theta_star_108_tree_theorem_assembly_gate.json"
POSJAM = ART / "s4_theta_star_positive_jam_max_over_8_certificate.json"
SOURCE_VIS = ART / "s4_theta_star_source_map_visibility_audit.json"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    checks.append((name, bool(condition), str(detail)))


def read(path: Path) -> str:
    check(f"file exists: {path.relative_to(ROOT)}", path.exists(), path)
    return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""


def load_json(path: Path) -> dict:
    check(f"json exists: {path.relative_to(ROOT)}", path.exists(), path)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def norm_support(text: str) -> str:
    return "_".join(str(text).split())


draft_text_main = read(DRAFT / "theta_star_finite_atlas.tex")
flat_text = read(DRAFT / "theta_star_finite_atlas_flat.tex")
skeleton_text = read(DRAFT / "theta_star_addendum_skeleton.tex")
check("built PDF exists: theta_star_finite_atlas.pdf", (DRAFT / "theta_star_finite_atlas.pdf").exists(), DRAFT / "theta_star_finite_atlas.pdf")
check("flat TeX source exists: theta_star_finite_atlas_flat.tex", (DRAFT / "theta_star_finite_atlas_flat.tex").exists(), DRAFT / "theta_star_finite_atlas_flat.tex")
check("flat TeX has no section inputs", "\\input{sections/" not in flat_text, "flat-source")

check("bibliography file exists", (DRAFT / "refs.bib").exists(), DRAFT / "refs.bib")
check("main TeX cites related work", "\\cite{" in draft_text_main and "\\bibliography{refs}" in draft_text_main, "bibliography")

section_names = [
    "02_formal_objects_and_tree_status_table.tex",
    "03_finite_angle_conjugacy.tex",
    "04_transport_and_theta_star_invariance.tex",
    "05_endpoint_free_class.tex",
    "06_wrapper_scope_class.tex",
    "07_positive_jam_class.tex",
    "08_instant_jam_class.tex",
]
sections = {name: read(SECTIONS / name) for name in section_names}
combined = "\n".join(sections.values())
combined_lower = combined.lower()
for name in section_names:
    stem = name[:-4]
    check(f"final TeX inputs section: {name}", f"\\input{{sections/{stem}}}" in draft_text_main, name)
check("final TeX declares companion addendum status", "Public companion addendum" in draft_text_main, "companion-addendum")
check("compatibility skeleton points to final TeX", "\\input{theta_star_finite_atlas}" in skeleton_text, "wrapper")

assembly = load_json(ASSEMBLY)
posjam = load_json(POSJAM)
source_vis = load_json(SOURCE_VIS)
summary = assembly.get("summary", {})
statement_counts = assembly.get("theorem_statement", {}).get("counts", {})
final_records = assembly.get("final_records", [])

expected_final = {
    "exact_positive_theta_jam_package_source_locked": 8,
    "exact_endpoint_free_witness_transport_certificate": 36,
    "exact_instant_jam_8_row_gate_source_locked": 60,
    "one_parameter_wrapper_scope_source_locked": 4,
}
expected_t = {"sqrt(3) endpoint reached": 40, "sqrt(2)": 8, "0": 60}
expected_theta = {
    "full_open_to_120": 36,
    "full_open_to_120_public_scope": 4,
    "jam_at_positive_t": 8,
    "instant_jam_t0": 60,
}

check("assembly status pass", assembly.get("status") == "pass", assembly.get("status"))
check("assembly local theorem supported", assembly.get("local_theorem_supported") is True, assembly.get("local_theorem_supported"))
check("assembly source artifact public promotion false", assembly.get("public_promotion_ready") is False, assembly.get("public_promotion_ready"))
check("assembly final class counts exact", summary.get("final_class_counts") == expected_final, summary.get("final_class_counts"))
check("assembly t-star counts exact", summary.get("t_star_counts") == expected_t, summary.get("t_star_counts"))
check("assembly theta status counts exact", summary.get("theta_status_counts") == expected_theta, summary.get("theta_status_counts"))
check("theorem statement class counts exact", statement_counts.get("final_certificate_class_counts") == expected_final, statement_counts.get("final_certificate_class_counts"))
check("positive-jam source cap sqrt(2)", posjam.get("t_cap_closed_form") == "sqrt(2)", posjam.get("t_cap_closed_form"))
check("source-map visibility pass", source_vis.get("status") == "pass", source_vis.get("status"))
check("assembly has 108 final_records", len(final_records) == 108, len(final_records))
check("assembly final_records target unique", len({r.get("target_tree") for r in final_records}) == 108, "targets")

required_global_phrases = [
    "S4 equal-magnitude theta-star finite-atlas theorem",
    "historical zero-thickness S4 scaffold",
    "108 connected three-hinge trees",
    "endpoint reached, not first contact",
    "t^*(T)=t^*(g(T))",
    "s'_{g(h)} = \\det(R_g)",
    "(G C_j)^{-1}(G C_i) = C_j^{-1} C_i",
    "axis-sign normalization",
    "\\operatorname{Rows}(T)",
    "t=\\tan(\\theta/2)",
    "t^*(T)=\\max",
    "row reach",
    "lower witnesses",
    "upper caps",
    "Finite predicate vocabulary",
]
for phrase in required_global_phrases:
    check(f"proof prose contains required phrase: {phrase}", phrase in combined, phrase)

forbidden_claim_phrases = [
    "global motion theorem",
    "physical hingeability theorem",
    "positive-thickness theorem",
    "three-parameter theorem",
    "non-equal-angle theorem",
    "general hinged-dissection theorem",
    "first contact at sqrt(3)",
    "first certified event value",
    "all S4 mechanisms",
]
for phrase in forbidden_claim_phrases:
    check(f"forbidden overclaim absent: {phrase}", phrase.lower() not in combined_lower, phrase)

# Generated table must match final_records row-by-row through hidden RECORD comments.
table = sections["02_formal_objects_and_tree_status_table.tex"]
record_re = re.compile(
    r"^% RECORD target=(TREE_\d{3}) source=(TREE_\d{3}) orbit=(\d+) "
    r"class=([^ ]+) t=(.*?) theta=([^ ]+) support=(.*)$",
    re.MULTILINE,
)
tex_records = [m.groupdict() for m in record_re.finditer(table)]
# Rebuild with named dicts because groupdict is not used with positional groups above.
tex_records = [
    {
        "target_tree": m.group(1),
        "source_tree": m.group(2),
        "orbit_id": int(m.group(3)),
        "final_certificate_class": m.group(4),
        "t_star_candidate": m.group(5),
        "theta_star_status": m.group(6),
        "support_gate": m.group(7),
    }
    for m in record_re.finditer(table)
]
check("generated table has 108 RECORD comments", len(tex_records) == 108, len(tex_records))
check("generated table target unique", len({r["target_tree"] for r in tex_records}) == 108, "targets")

json_by_target = {r["target_tree"]: r for r in final_records}
tex_by_target = {r["target_tree"]: r for r in tex_records}
check("generated table target set matches JSON", set(tex_by_target) == set(json_by_target), "target set")
for target in sorted(set(tex_by_target) & set(json_by_target)):
    tex = tex_by_target[target]
    js = json_by_target[target]
    check(f"table row matches source: {target}", tex["source_tree"] == js["source_tree"], tex)
    check(f"table row matches orbit: {target}", tex["orbit_id"] == js["orbit_id"], tex)
    check(f"table row matches final class: {target}", tex["final_certificate_class"] == js["final_certificate_class"], tex)
    check(f"table row matches t-star: {target}", tex["t_star_candidate"] == js["t_star_candidate"], tex)
    check(f"table row matches theta status: {target}", tex["theta_star_status"] == js["theta_star_status"], tex)
    check(f"table row matches support gate: {target}", tex["support_gate"] == norm_support(js["support_gate"]), tex)

check("table final class counts match", dict(Counter(r["final_certificate_class"] for r in tex_records)) == expected_final, Counter(r["final_certificate_class"] for r in tex_records))
check("table t-star counts match", dict(Counter(r["t_star_candidate"] for r in tex_records)) == expected_t, Counter(r["t_star_candidate"] for r in tex_records))
check("table theta status counts match", dict(Counter(r["theta_star_status"] for r in tex_records)) == expected_theta, Counter(r["theta_star_status"] for r in tex_records))

# Class proofs must expose final labels, counts, source representatives, source gates, and transported conclusion.
class_specs = {
    "endpoint": {
        "file": "05_endpoint_free_class.tex",
        "count": "36",
        "final_label": "exact\\_endpoint\\_free\\_witness\\_transport\\_certificate",
        "status": r"\(\sqrt{3}\) endpoint reached",
        "must": ["TREE\\_001", "TREE\\_004", "TREE\\_005", "TREE\\_027", "TREE\\_029", "T5c endpoint-free witness transport gate", "216 transported pair rows"],
    },
    "wrapper": {
        "file": "06_wrapper_scope_class.tex",
        "count": "4",
        "final_label": "one\\_parameter\\_wrapper\\_scope\\_source\\_locked",
        "status": r"\(\sqrt{3}\) endpoint reached",
        "must": [r"\texttt{TREE\_007}", r"\texttt{TREE\_009}", r"\texttt{TREE\_021}", r"\texttt{TREE\_093}", "public CL5/A7d", "local generalized-wedge", "selected hinge-side", "source-locked", "no broader motion claim"],
    },
    "positive": {
        "file": "07_positive_jam_class.tex",
        "count": "8",
        "final_label": "exact\\_positive\\_theta\\_jam\\_package\\_source\\_locked",
        "status": "t^* = \\sqrt{2}",
        "must": [r"\texttt{TREE\_000}", r"\texttt{TREE\_003}", "Stage3a", "Stage3b", "Stage3c", "max-over-8", "upper cap", "tetrahedral bond angle", "\\arccos(-1/3)"],
    },
    "instant": {
        "file": "08_instant_jam_class.tex",
        "count": "60",
        "final_label": "exact\\_instant\\_jam\\_8\\_row\\_gate\\_source\\_locked",
        "status": r"event value is \(0\)",
        "must": ["TREE\\_002", "TREE\\_008", "TREE\\_014", "TREE\\_015", "TREE\\_016", "TREE\\_017", "TREE\\_041", "TREE\\_043", "TREE\\_044", "TREE\\_068", "all eight", "t^*=0"],
    },
}

for label, spec in class_specs.items():
    body = sections[spec["file"]]
    check(f"{label} class final label present", spec["final_label"] in body, spec["final_label"])
    check(f"{label} class count present", f"{spec['count']} target trees" in body or f"Exactly {spec['count']} trees" in body, spec["count"])
    check(f"{label} class status present", spec["status"] in body, spec["status"])
    for phrase in spec["must"]:
        check(f"{label} class required detail: {phrase}", phrase in body, phrase)

# Arithmetic must be explicit in prose, not only implicit through individual classes.
check("theorem prose states 40 sqrt(3)", re.search(r"40\s*&:&\s*\\sqrt\{3\}", sections["04_transport_and_theta_star_invariance.tex"]) is not None, "40 sqrt(3)")
check("theorem prose states 8 sqrt(2)", re.search(r"8\s*&:&\s*\\sqrt\{2\}", sections["04_transport_and_theta_star_invariance.tex"]) is not None, "8 sqrt(2)")
check("theorem prose states 60 zero", re.search(r"60\s*&:&\s*0", sections["04_transport_and_theta_star_invariance.tex"]) is not None, "60 zero")
check("class decomposition sums to 108", sum(expected_final.values()) == 108, expected_final)
check("endpoint total is 36 plus 4", expected_t["sqrt(3) endpoint reached"] == expected_final["exact_endpoint_free_witness_transport_certificate"] + expected_final["one_parameter_wrapper_scope_source_locked"], expected_t)

# Make sure proof language still distinguishes endpoint from first contact and wrapper source-locking.
endpoint_wrapper = sections["05_endpoint_free_class.tex"] + "\n" + sections["06_wrapper_scope_class.tex"]
check("endpoint/wrapper path denies first-contact interpretation", "not a first-contact" in endpoint_wrapper and "separate class" in endpoint_wrapper, "endpoint wording")
sec04 = sections["04_transport_and_theta_star_invariance.tex"]
check("section 04 separates wrapper class", "The wrapper class is recorded separately" in sec04, "wrapper separation")
check("section 04 says wrapper not broad motion certificate", "not a new broad motion certificate" in sec04, "wrapper scope")

failed = [item for item in checks if not item[1]]
for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
print(f"\nstatus: {'pass' if not failed else 'fail'}")
print(f"checks: {len(checks) - len(failed)}/{len(checks)} pass")
if failed:
    sys.exit(1)
