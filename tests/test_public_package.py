import subprocess
import sys
from pathlib import Path


def test_public_package_check_passes():
    root = Path(__file__).resolve().parents[1]
    proc = subprocess.run([sys.executable, str(root / 'scripts/check_public_package.py')], cwd=str(root), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert proc.returncode == 0, proc.stdout + proc.stderr
