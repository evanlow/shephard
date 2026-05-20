# Coverage enforcement script for Shepherd
# Usage: python coverage_gate.py
import sys
import subprocess

COVERAGE_FAIL_UNDER = 90  # Minimum line coverage % required

# Run tests with coverage (line + branch)
result = subprocess.run([
    sys.executable, '-m', 'coverage', 'run', '--branch', 'tests/run_all_smoke.py'
])
if result.returncode != 0:
    print("Test run failed.")
    sys.exit(result.returncode)

# Print coverage report and enforce threshold
result = subprocess.run([
    sys.executable, '-m', 'coverage', 'report', '--fail-under', str(COVERAGE_FAIL_UNDER)
])
if result.returncode != 0:
    print(f"Coverage below {COVERAGE_FAIL_UNDER}%! Gate failed.")
    sys.exit(result.returncode)

print("Coverage gate passed.")
