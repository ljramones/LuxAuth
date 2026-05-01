#!/usr/bin/env python3
"""Run unit tests with per-service import paths.

Each microservice has an `app` package, so running pytest once from the
monorepo root causes import collisions. This runner executes pytest from each
service directory with an isolated PYTHONPATH.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PYTHON = Path(sys.executable)


def run_pytest(cwd: Path, *paths: str) -> int:
    env = os.environ.copy()
    path_parts = [
        str(cwd),
        str(ROOT / "libs" / "auth_common"),
        str(ROOT / "ml"),
        env.get("PYTHONPATH", ""),
    ]
    env["PYTHONPATH"] = os.pathsep.join(p for p in path_parts if p)
    cmd = [str(PYTHON), "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths]
    print(f"\n==> {cwd.relative_to(ROOT)}")
    return subprocess.run(cmd, cwd=cwd, env=env, check=False).returncode


def main() -> int:
    targets: list[tuple[Path, tuple[str, ...]]] = [
        (ROOT / "libs" / "auth_common", ("tests",)),
    ]
    root_tests = ROOT / "tests"
    if root_tests.exists():
        targets.append((ROOT, ("tests",)))
    ml_experiments_tests = ROOT / "ml" / "experiments" / "tests"
    if ml_experiments_tests.exists():
        targets.append((ROOT / "ml", ("experiments/tests",)))
    for service_dir in sorted((ROOT / "services").iterdir()):
        tests_dir = service_dir / "tests"
        if tests_dir.exists():
            targets.append((service_dir, ("tests",)))

    failures = 0
    for cwd, paths in targets:
        result = run_pytest(cwd, *paths)
        if result:
            failures += 1

    if failures:
        print(f"\n{failures} test target(s) failed.")
        return 1
    print("\nAll unit test targets passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
