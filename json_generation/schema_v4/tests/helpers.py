"""Paths and assertions shared by the suite.

`pytest.ini` puts `src` and `tests` on the path, so this module is only about
locations and assertions. Nothing here reads `reference/` -- the vendor drop is
provenance, not a fixture, and a test that depends on it breaks the moment
somebody reorganises it (which is exactly what happened).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

V4 = Path(__file__).resolve().parent.parent
SRC = V4 / "src"
SCHEMAS = V4 / "schemas"
EXAMPLES = V4 / "examples"
TEMPLATES = V4 / "templates"

#: The one shipped example package.
C2 = EXAMPLES / "cenario2_retail"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from schema_v4 import validator  # noqa: E402  (after sys.path is set)


def load(path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def dump(path, doc: dict) -> None:
    with Path(path).open("w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")


def validate(path, against=None):
    return validator.validate(path, against)


def run_cli(*args, json_output: bool = True):
    """Run the validator CLI in a subprocess.

    Returns (returncode, stdout, stderr). stderr is kept, because discarding it
    turns a crash into an opaque JSONDecodeError at the call site.
    """
    argv = [sys.executable, "-m", "schema_v4.validator", *map(str, args)]
    if json_output:
        argv.append("--json")
    proc = subprocess.run(argv, capture_output=True, text=True, cwd=V4,
                          env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"})
    return proc.returncode, proc.stdout, proc.stderr


def findings(report, want_error: bool = True) -> list[str]:
    return report.errors if want_error else report.warnings


def assert_isolated(report, needle: str, want_error: bool = True) -> None:
    """Assert exactly one finding, in the expected pool, matching `needle`.

    The point is isolation: a fixture breaks one thing, so one thing must be
    reported and the other pool must stay empty. A check that merely fires
    somewhere is not evidence that it fired for the right reason.
    """
    wanted = findings(report, want_error)
    other = findings(report, not want_error)
    label = "error" if want_error else "warning"
    assert len(wanted) == 1, f"expected exactly one {label}, got {wanted}"
    assert needle in wanted[0], f"expected {needle!r} in {wanted[0]!r}"
    assert not other, f"expected no {'warnings' if want_error else 'errors'}, got {other}"


def assert_reports(report, needle: str, want_error: bool = True, count: int = 1) -> None:
    """Assert `count` findings match `needle`, and that at least one exists.

    For the cases where isolation is the wrong demand -- several findings are
    legitimately expected -- but `any(...)` would pass on an empty list.
    """
    pool = findings(report, want_error)
    hits = [f for f in pool if needle in f]
    assert hits, f"expected {needle!r} among {pool}"
    assert len(hits) == count, f"expected {count} matching {needle!r}, got {len(hits)}: {hits}"
