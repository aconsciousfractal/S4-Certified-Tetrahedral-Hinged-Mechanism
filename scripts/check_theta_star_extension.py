"""
Bounded consistency checker for the theta-star public companion addendum.

This is not a full mathematical replay.  It verifies that the curated public
extension contains the expected artifacts, hashes, scope documents, manifest,
and summary counts after external mathematical red-team and addendum promotion.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
EXT = ROOT / "extensions" / "theta_star_finite_atlas"
ART = EXT / "artifacts"
DOCS = EXT / "docs"
PKG = EXT / "paper_package"
MANIFEST = EXT / "EXTENSION_MANIFEST.json"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    checks.append((name, bool(condition), str(detail)))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path: Path) -> dict:
    check(f"json exists: {path.relative_to(ROOT)}", path.exists(), path)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


manifest = load_json(MANIFEST)
check("extension status is public companion addendum", manifest.get("status") == "public_companion_addendum", manifest.get("status"))
check("extension is not main paper update", manifest.get("main_paper_update") is False, manifest.get("main_paper_update"))
check("extension public theorem promotion recorded", manifest.get("public_theorem_promotion") is True, manifest.get("public_theorem_promotion"))
check("extension companion note recorded", manifest.get("main_paper_companion_note") is True, manifest.get("main_paper_companion_note"))
check("external mathematical red-team pass recorded", manifest.get("external_mathematical_red_team", {}).get("status") == "pass", manifest.get("external_mathematical_red_team"))
check("no remaining review obligations", manifest.get("remaining_review_obligations") == [], manifest.get("remaining_review_obligations"))
check("extension branch recorded", manifest.get("branch") == "theta-star-addendum-review", manifest.get("branch"))

for item in manifest.get("files", []):
    rel = item.get("path", "")
    path = EXT / rel
    check(f"manifest file exists: {rel}", path.exists(), rel)
    if path.exists():
        check(f"manifest sha256 matches: {rel}", sha256(path) == item.get("sha256"), rel)
        check(f"manifest size matches: {rel}", path.stat().st_size == item.get("size_bytes"), rel)

sha_manifest = ART / "SHA256SUMS.txt"
check("SHA256SUMS exists", sha_manifest.exists(), sha_manifest)
if sha_manifest.exists():
    for line in sha_manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        expected, rel = line.split("  ", 1)
        path = EXT / rel
        check(f"sha listed file exists: {rel}", path.exists(), rel)
        if path.exists():
            check(f"sha listed file matches: {rel}", sha256(path) == expected, rel)

required_docs = [
    EXT / "README.md",
    EXT / "THETA_STAR_CLAIM_BOUNDARY.md",
    EXT / "THETA_STAR_REPRODUCE.md",
    EXT / "THETA_STAR_EXTERNAL_RED_TEAM_SCOPE.md",
    EXT / "THETA_STAR_EXTERNAL_RED_TEAM_PROMPT.md",
    EXT / "EXTERNAL_RED_TEAM_HANDOFF.md",
    DOCS / "S4_THETA_STAR_108_TREE_THEOREM_PROOF_DRAFT.md",
    DOCS / "S4_THETA_STAR_108_TREE_THEOREM_CROSSWALK.md",
    DOCS / "S4_THETA_STAR_REPRESENTATIVE_SOURCE_CERTIFICATE_TABLE.md",
    DOCS / "S4_THETA_STAR_THEOREM_CLASS_PREDICATE_AUDIT.md",
    DOCS / "S4_THETA_STAR_CERTIFICATE_TRANSPORT_LEMMA.md",
    DOCS / "S4_FINITE_ANGLE_SCAFFOLD_CONJUGACY_LEMMA.md",
    DOCS / "S4_THETA_STAR_108_TREE_STATUS_MAP.md",
    EXT / "paper_draft" / "BUILD.md",
    EXT / "paper_draft" / "theta_star_finite_atlas.tex",
    EXT / "paper_draft" / "theta_star_finite_atlas_flat.tex",
    EXT / "paper_draft" / "theta_star_finite_atlas.pdf",
    EXT / "paper_draft" / "refs.bib",
    PKG / "PAPER_PROOF_SPINE_CLOSURE.json",
    PKG / "RED_TEAM_CLOSURE_REPORT.md",
    PKG / "PAPER_PROMOTION_DECISION.md",
]
for path in required_docs:
    check(f"document exists: {path.relative_to(ROOT)}", path.exists(), path)

status_map_path = DOCS / "S4_THETA_STAR_108_TREE_STATUS_MAP.md"
status_map_text = status_map_path.read_text(encoding="utf-8") if status_map_path.exists() else ""
stale_transport_label = "orbit_inherited_label_not_finite_angle_transport"
supersession_phrase = "historical/pre-T4 status, superseded by T4/T5/T6 proof spine"
check("STATUS_MAP has supersession note", "## Supersession note - 2026-06-29" in status_map_text, "")
check("STATUS_MAP stale transport labels are superseded",
      stale_transport_label not in status_map_text or supersession_phrase in status_map_text,
      stale_transport_label)

source = load_json(ART / "s4_theta_star_source_map_visibility_audit.json")
t6b = load_json(ART / "s4_theta_star_t6b_theorem_prose_audit.json")
gate = load_json(ART / "s4_theta_star_108_tree_theorem_proof_package_gate.json")
posjam = load_json(ART / "s4_theta_star_positive_jam_max_over_8_certificate.json")

check("source-map audit pass", source.get("status") == "pass", source.get("status"))
check("source-map audit 43/0", source.get("passed") == 43 and source.get("failed") == 0,
      {"passed": source.get("passed"), "failed": source.get("failed")})
check("source-map visibility obligations closed", source.get("visibility_obligations_closed") == [
    "O-selected-hinge-side-map-visibility",
    "O-support-feature-map-visibility",
], source.get("visibility_obligations_closed"))

check("T6B prose audit status", t6b.get("status") == "pass_with_review_obligations", t6b.get("status"))
check("T6B prose audit 26/0", t6b.get("passed") == 26 and t6b.get("failed") == 0,
      {"passed": t6b.get("passed"), "failed": t6b.get("failed")})
check("T6B only theorem-name-scope open", t6b.get("summary", {}).get("open_obligations") == ["O-theorem-name-scope"],
      t6b.get("summary", {}).get("open_obligations"))
check("representative class counts", t6b.get("summary", {}).get("representative_class_counts") == manifest.get("expected_counts", {}).get("representative_class_counts"),
      t6b.get("summary", {}).get("representative_class_counts"))

summary = gate.get("summary", {})
expected = manifest.get("expected_counts", {})
check("108-tree gate status", gate.get("status") == "pass_with_review_obligations", gate.get("status"))
check("108-tree gate 48/0", gate.get("passed") == 48 and gate.get("failed") == 0,
      {"passed": gate.get("passed"), "failed": gate.get("failed")})
check("108-tree only theorem-name-scope open", summary.get("open_obligations") == ["O-theorem-name-scope"],
      summary.get("open_obligations"))
check("theta status counts", summary.get("theta_status_counts") == expected.get("theta_status_counts"), summary.get("theta_status_counts"))
check("t-star counts", summary.get("t_star_counts") == expected.get("t_star_counts"), summary.get("t_star_counts"))
check("final class counts", summary.get("final_class_counts") == expected.get("final_class_counts"), summary.get("final_class_counts"))

check("positive-jam certificate pass", posjam.get("status") == "pass", posjam.get("status"))
check("positive-jam certificate 5/0", posjam.get("passed") == 5 and posjam.get("failed") == 0,
      {"passed": posjam.get("passed"), "failed": posjam.get("failed")})
check("positive-jam cap is sqrt(2)", posjam.get("t_cap_closed_form") == "sqrt(2)", posjam.get("t_cap_closed_form"))
check("positive-jam theta cap is tetrahedral angle", posjam.get("theta_cap_closed_form") == "2*atan(sqrt(2)) = acos(-1/3)",
      posjam.get("theta_cap_closed_form"))

# Public-review hygiene.  These are exact bad strings, not every nonclaim use of
# risk words.  Boundary files are expected to mention risk categories as things
# explicitly not claimed.
# Public-facing hygiene scans narrative/review files.  Raw proof-spine JSON
# artifacts are checked by check_theta_star_paper_package.py and may preserve
# historical source/provenance paths from the local computation workspace.
proof_spine_dir = EXT / "paper_package" / "artifacts" / "proof_spine"
text_files = []
for p in EXT.rglob("*"):
    if not p.is_file() or p.suffix.lower() not in {".md", ".json", ".txt", ".py"}:
        continue
    try:
        p.relative_to(proof_spine_dir)
        continue
    except ValueError:
        pass
    text_files.append(p)
combined = "\n".join(p.read_text(encoding="utf-8", errors="replace") for p in text_files)
for label, bad in [
    ("local drive slash path", "P:" + "/"),
    ("local drive backslash path", "P:" + "\\"),
    ("local repository root token", "GitHub" + "_puba"),
    ("promotion-ready true flag", "public_promotion_ready" + "=true"),
    ("global mechanism theorem phrase", "global S4" + " mechanism theorem"),
    ("all-open overclaim phrase", "all 108" + " open to 120"),
    ("physical proof overclaim phrase", "physical hingeability" + " is proved"),
]:
    check(f"forbidden public-review string absent: {label}", bad not in combined, label)

reproduce = (EXT / "THETA_STAR_REPRODUCE.md").read_text(encoding="utf-8")
check("reproduce names actual checker", "python scripts/check_theta_star_extension.py" in reproduce, "")
check("reproduce no stale checker wording", ("expected" + " to be") not in reproduce and ("Until" + " it exists") not in reproduce, "")

boundary = (EXT / "THETA_STAR_CLAIM_BOUNDARY.md").read_text(encoding="utf-8")
for phrase in ["positive-thickness", "three-parameter", "non-equal", "physical"]:
    check(f"boundary names nonclaim: {phrase}", phrase in boundary, phrase)

failed = [item for item in checks if not item[1]]
for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
print(f"\nstatus: {'pass' if not failed else 'fail'}")
print(f"checks: {len(checks) - len(failed)}/{len(checks)} pass")

if failed:
    sys.exit(1)
