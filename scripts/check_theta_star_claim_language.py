"""
Claim-language checker for the theta-star proof-prose draft.

This is a bounded editorial/mathematical hygiene check. It only scans the local
proof-prose draft and boundary text for the intended theorem name/scope and for
phrases that would overclaim the result. It is not a mathematical replay.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions" / "theta_star_finite_atlas"
DRAFT = EXT / "paper_draft"
SECTIONS = DRAFT / "sections"
BOUNDARY = EXT / "THETA_STAR_CLAIM_BOUNDARY.md"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    checks.append((name, bool(condition), str(detail)))


files = [DRAFT / "README.md", DRAFT / "theta_star_finite_atlas.tex", DRAFT / "theta_star_finite_atlas_flat.tex", BOUNDARY] + sorted(SECTIONS.glob("*.tex"))
for path in files:
    check(f"claim file exists: {path.relative_to(ROOT)}", path.exists(), path)

scope_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in files if path.exists())
lower = scope_text.lower()
draft_files = [DRAFT / "README.md", DRAFT / "theta_star_finite_atlas.tex", DRAFT / "theta_star_finite_atlas_flat.tex"] + sorted(SECTIONS.glob("*.tex"))
draft_text = "\n".join(path.read_text(encoding="utf-8", errors="replace") for path in draft_files if path.exists()).lower()

required_phrases = [
    "s4 equal-magnitude theta-star finite-atlas theorem",
    "zero-thickness",
    "equal-magnitude",
    "finite atlas",
    "endpoint reached, not first contact",
]
for phrase in required_phrases:
    check(f"required claim phrase present: {phrase}", phrase in lower, phrase)

forbidden_phrases = [
    "global motion theorem",
    "physical hingeability theorem",
    "positive-thickness theorem",
    "three-parameter theorem",
    "non-equal-angle theorem",
    "general hinged-dissection theorem",
    "first contact at sqrt(3)",
    "all s4 mechanisms",
]
for phrase in forbidden_phrases:
    check(f"forbidden claim phrase absent: {phrase}", phrase not in draft_text, phrase)

sec03 = (SECTIONS / "03_finite_angle_conjugacy.tex").read_text(encoding="utf-8", errors="replace") if (SECTIONS / "03_finite_angle_conjugacy.tex").exists() else ""
sec04 = (SECTIONS / "04_transport_and_theta_star_invariance.tex").read_text(encoding="utf-8", errors="replace") if (SECTIONS / "04_transport_and_theta_star_invariance.tex").exists() else ""

for phrase in [
    "Finite-angle scaffold conjugacy",
    "s'_{g(h)}",
    "(G C_j)^{-1}(G C_i) = C_j^{-1} C_i",
    "SAT",
    "axis-sign normalization",
]:
    check(f"section 03 proof ingredient present: {phrase}", phrase in sec03, phrase)

for phrase in [
    "Eight-row bijection",
    "Row predicate preservation",
    "row reach",
    "upper caps",
    "t^*(T)=t^*(g(T))",
    "endpoint reached, not first contact",
    r"\sqrt{2}",
]:
    check(f"section 04 proof ingredient present: {phrase}", phrase in sec04, phrase)

class_sections = {
    "endpoint-free": SECTIONS / "05_endpoint_free_class.tex",
    "wrapper": SECTIONS / "06_wrapper_scope_class.tex",
    "positive-jam": SECTIONS / "07_positive_jam_class.tex",
    "instant-jam": SECTIONS / "08_instant_jam_class.tex",
}
for label, path in class_sections.items():
    check(f"class proof exists: {label}", path.exists(), path)

class_texts = {label: path.read_text(encoding="utf-8", errors="replace") if path.exists() else "" for label, path in class_sections.items()}
class_requirements = {
    "endpoint-free": ["Endpoint-free transported witness class", "36 target trees", "T5c endpoint-free witness transport gate", r"\sqrt{3}"],
    "wrapper": ["Source-locked wrapper class", "4 target trees", "TREE\\_007", "TREE\\_009", "TREE\\_021", "TREE\\_093", "selected hinge-side", "source-locked", "public CL5/A7d", "local generalized-wedge"],
    "positive-jam": ["Positive-jam class at sqrt(2)", "8 target trees", "max-over-8", "upper cap", "t^* = \\sqrt{2}", "tetrahedral bond angle"],
    "instant-jam": ["Instant-jam eight-row class", "60 target trees", "all eight", "t^*=0"],
}
for label, phrases in class_requirements.items():
    body = class_texts[label]
    for phrase in phrases:
        check(f"class proof {label} contains: {phrase}", phrase in body, phrase)

failed = [item for item in checks if not item[1]]
for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
print(f"\nstatus: {'pass' if not failed else 'fail'}")
print(f"checks: {len(checks) - len(failed)}/{len(checks)} pass")
if failed:
    sys.exit(1)
