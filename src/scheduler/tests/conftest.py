"""Shared setup for the scheduler tests.

Imports resolve the way they do in the scheduler container (/app is
src/scheduler), plus src/ for the `analyzer` package the heuristics import.
The v4 validator is imported from json_generation/schema_v4 - by the tests
only; the scheduler itself never depends on that tree.
"""

import json
import shutil
import sys
from pathlib import Path

import pytest

SCHEDULER = Path(__file__).resolve().parents[1]
REPO = SCHEDULER.parents[1]
SCHEMA_V4 = REPO / "json_generation" / "schema_v4"
EXAMPLES = SCHEMA_V4 / "examples"

for path in (SCHEDULER, SCHEDULER.parent, SCHEMA_V4 / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))


@pytest.fixture
def example_copy(tmp_path):
    """Copy an example package to a tmp folder, so a test may edit it."""
    def _copy(name: str) -> Path:
        target = tmp_path / name
        shutil.copytree(EXAMPLES / name, target)
        return target
    return _copy


def read_result(package: Path) -> dict:
    return json.loads((package / "result.json").read_text(encoding="utf-8"))


def write_result(package: Path, doc: dict) -> None:
    (package / "result.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")


def set_fixed_code(package: Path, employee: str, day: str, code: int) -> None:
    """Change one fixed day's ScheduleCode in a package's result."""
    doc = read_result(package)
    for entry in doc["OutRosterTeamDays"]:
        if entry["EmployeeCode"] == employee and entry["Date"].startswith(day):
            entry["ScheduleCode"] = code
            break
    else:
        raise AssertionError(f"{employee} on {day} is not fixed in {package}")
    write_result(package, doc)


def add_code(package: Path, row: str, menu: bool = True, sidecar: bool = True) -> None:
    """Define a ScheduleCode in the menu and/or the result's sidecar.

    A sidecar-only code is one the partial result used but the menu does not
    offer, so it can be fixed without becoming a candidate for open days.
    """
    names = (["schedules.csv"] if menu else []) + (["result_schedules.csv"] if sidecar else [])
    for name in names:
        path = package / name
        if path.is_file():
            path.write_text(path.read_text(encoding="utf-8").rstrip("\n") + "\n" + row + "\n", encoding="utf-8")


def validate_v4_package(package: Path) -> dict:
    """{name: Report} from the v4 validator, for a package on disk."""
    from schema_v4.validator import validate_package
    return validate_package(package)


def assert_valid_complete(package: Path) -> None:
    reports = validate_v4_package(package)
    errors = {name: r.errors for name, r in reports.items() if r.errors}
    assert not errors, errors
    assert reports["result.json"].stats["rosterDaysLeft"] == 0
