from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
cmd = [sys.executable, str(ROOT / 'scripts/check_public_package.py')]
raise SystemExit(subprocess.run(cmd, cwd=str(ROOT)).returncode)
