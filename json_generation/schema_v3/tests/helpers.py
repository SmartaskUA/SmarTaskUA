"""Shared test helpers: repo paths, an in-process `validate`, a CLI runner, and
the isolated-finding assertion. Importing this puts the package on sys.path, so
test modules can `import core` / `import validator` directly.
"""
import json
import subprocess
import sys
from pathlib import Path

V3 = Path(__file__).resolve().parent.parent   # schema_v3/
SRC = V3 / "src" / "schema_v3"
SCHEMAS = V3 / "schemas"
EX = V3 / "examples"
TC = EX / "time_constraints_example"
SIS = EX / "sisqual_example"
PY = sys.executable

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import validator  # noqa: E402  (after sys.path is set)


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())


def validate(path, against=None):
    """In-process single-file validation -> Report."""
    return validator.validate(Path(path), against=Path(against) if against else None)


def run_cli(*args) -> dict:
    """Run the validator CLI with --json and return the parsed report(s)."""
    r = subprocess.run(
        [PY, str(SRC / "validator.py"), *map(str, args), "--json"],
        capture_output=True, text=True,
    )
    return json.loads(r.stdout)


def assert_isolated(report, needle, want_error=True):
    """The report has EXACTLY ONE finding in the expected pool, matching `needle`,
    and nothing in the other pool. Mirrors the old suite's expect()."""
    pool = report.errors if want_error else report.warnings
    other = report.warnings if want_error else report.errors
    assert len(pool) == 1 and not other, f"pool={pool} other={other}"
    assert needle.lower() in pool[0].lower(), f"{needle!r} not in {pool[0]!r}"
