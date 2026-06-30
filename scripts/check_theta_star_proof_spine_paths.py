"""
Path-hygiene checker for theta-star proof-spine artifacts.

This is a bounded public-package hygiene check, not a mathematical replay.  It
ensures that raw proof-spine JSON records do not depend on private local paths.
If an absolute local path ever appears, it must be confined to an explicitly
non-operational provenance/redaction field; portable relative source-artifact
labels are allowed.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
PROOF_SPINE = ROOT / "extensions" / "theta_star_finite_atlas" / "paper_package" / "artifacts" / "proof_spine"

checks: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: object = "") -> None:
    checks.append((name, bool(condition), str(detail)))


def iter_strings(obj, stack=()):
    if isinstance(obj, dict):
        for key, value in obj.items():
            yield from iter_strings(value, stack + (str(key),))
    elif isinstance(obj, list):
        for index, value in enumerate(obj):
            yield from iter_strings(value, stack + (str(index),))
    elif isinstance(obj, str):
        yield stack, obj


def is_provenance_stack(stack: tuple[str, ...]) -> bool:
    joined = "/".join(stack).lower()
    tokens = [
        "source_original",
        "provenance",
        "historical_source",
        "non_operational",
        "public_package_note",
        "redacted",
        "original_relative",
    ]
    return any(token in joined for token in tokens)


PRIVATE_PATTERNS = [
    ("windows_drive_path", re.compile(r"(?i)(?:^|[^A-Za-z0-9_])([A-Z]:[\\/][^\"'\s,}\]]*)")),
    ("msys_drive_path", re.compile(r"(?i)(?:^|[^A-Za-z0-9_])(/p/[^\"'\s,}\]]*)")),
    ("private_repo_token", re.compile(r"GitHub_puba")),
]

check("proof-spine directory exists", PROOF_SPINE.exists(), PROOF_SPINE)
json_files = sorted(PROOF_SPINE.glob("*.json")) if PROOF_SPINE.exists() else []
check("proof-spine JSON files present", len(json_files) >= 12, len(json_files))

bad_private_hits: list[str] = []
allowed_private_hits: list[str] = []
relative_historical_refs = 0
malformed_json: list[str] = []

for path in json_files:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # pragma: no cover - failure path reports exact file.
        malformed_json.append(f"{path.relative_to(ROOT)}:{exc}")
        continue
    for stack, value in iter_strings(data):
        stack_name = "/".join(stack)
        if value.startswith("results/historical_s4_median_planes/") or value.startswith("results\\historical_s4_median_planes\\"):
            relative_historical_refs += 1
        for label, pattern in PRIVATE_PATTERNS:
            if not pattern.search(value):
                continue
            hit = f"{path.relative_to(ROOT)}:{stack_name}:{label}:{value[:180]}"
            if is_provenance_stack(stack):
                allowed_private_hits.append(hit)
            else:
                bad_private_hits.append(hit)

check("proof-spine JSON parse", not malformed_json, malformed_json[:5])
check("private absolute paths absent outside provenance whitelist", not bad_private_hits, bad_private_hits[:8])
check("private absolute path hits, if any, are provenance-only", not bad_private_hits, f"allowed={len(allowed_private_hits)} bad={len(bad_private_hits)}")
check("relative historical source refs are portable", relative_historical_refs > 0, relative_historical_refs)

for name, ok, detail in checks:
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""))
failed = [item for item in checks if not item[1]]
print(f"\nstatus: {'pass' if not failed else 'fail'}")
print(f"checks: {len(checks) - len(failed)}/{len(checks)} pass")
if failed:
    sys.exit(1)
