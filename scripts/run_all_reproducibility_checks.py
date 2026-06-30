from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]

STEPS = [
    ("public package", [sys.executable, "-B", str(ROOT / "scripts/check_public_package.py")]),
    ("theta-star claim language", [sys.executable, "-B", str(ROOT / "scripts/check_theta_star_claim_language.py")]),
    ("theta-star paper package", [sys.executable, "-B", str(ROOT / "scripts/check_theta_star_paper_package.py")]),
    ("theta-star proof prose", [sys.executable, "-B", str(ROOT / "scripts/check_theta_star_proof_prose.py")]),
    ("theta-star extension", [sys.executable, "-B", str(ROOT / "scripts/check_theta_star_extension.py")]),
    ("theta-star proof-spine path hygiene", [sys.executable, "-B", str(ROOT / "scripts/check_theta_star_proof_spine_paths.py")]),
    ("pytest", [sys.executable, "-m", "pytest", "-q"]),
]


def main() -> int:
    failed = []
    for name, cmd in STEPS:
        print(f"\n=== {name} ===", flush=True)
        result = subprocess.run(cmd, cwd=str(ROOT))
        if result.returncode != 0:
            failed.append((name, result.returncode))
            break
    if failed:
        name, code = failed[0]
        print(f"\nstatus: fail ({name}, exit {code})")
        return code
    print("\nstatus: pass")
    print(f"checks: {len(STEPS)}/{len(STEPS)} gates passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
