#!/usr/bin/env python3
"""Unified project health & code quality checker.

Usage:
    python scripts/check.py          # Runs ruff linter
    python scripts/check.py --tests  # Runs ruff linter + fast unit tests
"""
import subprocess
import sys
from pathlib import Path

if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

APP_ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    print("[CHECK] [1/2] Running Ruff lint checks on backend...")
    res = subprocess.run([sys.executable, "-m", "ruff", "check", "backend"], cwd=APP_ROOT)
    if res.returncode != 0:
        print("[FAIL] Ruff checks failed.")
        return res.returncode

    print("[OK] Ruff checks passed cleanly.")

    if "--tests" in sys.argv:
        print("[CHECK] [2/2] Running fast unit tests...")
        t_res = subprocess.run(
            [sys.executable, "-m", "pytest", "backend/tests", "-m", "not slow"],
            cwd=APP_ROOT,
        )
        return t_res.returncode

    return 0


if __name__ == "__main__":
    sys.exit(main())
