"""Shepherd smoke test runner.

Auto-discovers all tests/smoke_*.py files, runs them, and prints a
consolidated pass/fail count.  Exit code 0 = all pass, 1 = any failures.

Usage (from project root, venv active):
    .\\Scripts\\python.exe tests/run_all_smoke.py
"""

import glob
import importlib.util
import os
import sys
import unittest


def _load_module(filepath: str):
    """Load a .py file as a module by absolute path."""
    module_name = os.path.splitext(os.path.basename(filepath))[0]
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    # Project root must be on sys.path so `from app import ...` works
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    tests_dir = os.path.dirname(os.path.abspath(__file__))
    smoke_files = sorted(glob.glob(os.path.join(tests_dir, "smoke_*.py")))

    if not smoke_files:
        print("ERROR: No smoke_*.py files found in tests/")
        sys.exit(1)

    print(f"Discovered {len(smoke_files)} smoke test file(s):")
    for f in smoke_files:
        print(f"  {os.path.basename(f)}")
    print()

    suite = unittest.TestSuite()
    loader = unittest.TestLoader()

    for filepath in smoke_files:
        module = _load_module(filepath)
        suite.addTests(loader.loadTestsFromModule(module))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    total = result.testsRun
    failures = len(result.failures) + len(result.errors)
    passed = total - failures

    print()
    print("=" * 60)
    print(f"Shepherd Smoke Tests  |  {passed}/{total} passed  |  {failures} failures")
    print("=" * 60)

    sys.exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
