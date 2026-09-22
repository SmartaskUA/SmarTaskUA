"""Paths and assertions shared by the suite.

Importing this puts ``schema_v4/src`` on sys.path, which is the only setup the
suite needs: v4 is a real package, so no module-name juggling is involved.
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
REFERENCE = V4 / "reference"
RAW = V4 / "IntegracaoUA_SISQUAL" / "JSON" / "20260917_JSON_Cenarios_GeradoSisqual"
RAW_C1 = RAW / "Cenário_1"
RAW_C2 = RAW / "Cenário_2"
RAW_JULY = V4 / "IntegracaoUA_SISQUAL" / "sisqual-alg-input"
CATALOGUE = REFERENCE / "schedules" / "schedules_without_meal.csv"

C2 = EXAMPLES / "cenario2_retail"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from schema_v4 import validator  # noqa: E402  (after sys.path is set)


def sisqual_result(tmp_path) -> Path:
    """Sisqual's own emailed result sample, repaired into `tmp_path`.

    `import_1.Json` is indented with U+2002 EN SPACE characters from an Outlook
    paste and is not valid JSON, so it cannot be read where it lies. Repairing a
    copy keeps its two quirks - an integer EmployeeCode and a ScheduleCode that is
    not in the catalogue we hold - available as fixtures without touching the raw
    drop.
    """
    src = RAW_C1 / "import_1.Json"
    text = src.read_text(encoding="utf-8-sig").replace("\u2002", " ")
    out = tmp_path / "result.json"
    out.write_text(text, encoding="utf-8")
    return out


def load(path) -> dict:
    with Path(path).open(encoding="utf-8") as fh:
        return json.load(fh)


def validate(path, against=None):
    return validator.validate(path, against)


def run_cli(*args) -> dict:
    """Run the validator CLI in a subprocess and return its --json output."""
    out = subprocess.run(
        [sys.executable, "-m", "schema_v4.validator", *map(str, args), "--json"],
        capture_output=True, text=True, cwd=V4,
        env={"PYTHONPATH": str(SRC), "PATH": "/usr/bin:/bin"},
    )
    return json.loads(out.stdout)


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
