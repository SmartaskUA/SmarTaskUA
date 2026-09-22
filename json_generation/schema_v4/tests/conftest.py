"""Fixtures: a clean package, and factories that break exactly one thing in it."""

from __future__ import annotations

import csv
import shutil

import pytest
from helpers import C2, SCHEMAS, TEMPLATES, dump, load

DEMAND_CSV = "periods_demand_template.csv"
SCHEDULES_CSV = "schedules_template.csv"
INPUT_CSV = "schedule_input_template.csv"
PROBLEM = "problem_template.json"


@pytest.fixture(scope="session")
def schemas():
    """Both schemas, parsed and checked as schemas."""
    from jsonschema import Draft202012Validator
    out = {}
    for path in sorted(SCHEMAS.glob("*.json")):
        schema = load(path)
        Draft202012Validator.check_schema(schema)
        out[path.name] = schema
    return out


@pytest.fixture
def make_fixture(tmp_path):
    """Copy the templates package into tmp_path, optionally breaking one thing.

    The templates are the control: they validate with no errors and no warnings,
    so anything a fixture reports is what the test broke.

    That claim holds for `mutate_problem`, `schedule_rows` and `add_demand` --
    each leaves the rest of the package intact. It does NOT hold for
    `demand_rows` / `schedules_rows`, which replace a whole CSV: replacing the
    demand file collapses `open_days` from seven dates to one, which silently
    disables most of the structural pass. Prefer `add_demand` and reach for the
    wholesale replacement only when the header itself is under test.
    """
    def _make(mutate_problem=None, schedule_rows=None, demand_rows=None,
              schedules_rows=None, add_demand=None):
        for src in TEMPLATES.iterdir():
            if src.suffix in (".json", ".csv"):
                shutil.copyfile(src, tmp_path / src.name)

        problem_path = tmp_path / PROBLEM
        if mutate_problem:
            doc = load(problem_path)
            mutate_problem(doc)
            dump(problem_path, doc)

        if schedule_rows:
            path = tmp_path / INPUT_CSV
            lines = [l for l in path.read_text(encoding="utf-8").splitlines()
                     if l.strip() and not l.startswith("#")]
            rows = list(csv.reader(lines))
            header = rows[0]
            for (emp, day), value in schedule_rows.items():
                col = header.index(day)
                for r in rows[1:]:
                    if r[0] == emp:
                        r[col] = value
            with path.open("w", newline="", encoding="utf-8") as fh:
                csv.writer(fh, lineterminator="\n").writerows(rows)

        if add_demand:
            # Append to the control rather than replace it, so open_days, the week
            # buckets and the reachability sets all stay as they were.
            path = tmp_path / DEMAND_CSV
            with path.open("a", encoding="utf-8") as fh:
                for row in add_demand:
                    fh.write(row.rstrip("\n") + "\n")

        if demand_rows is not None:
            (tmp_path / DEMAND_CSV).write_text(demand_rows, encoding="utf-8")
        if schedules_rows is not None:
            (tmp_path / SCHEDULES_CSV).write_text(schedules_rows, encoding="utf-8")
        return problem_path
    return _make


@pytest.fixture
def make_result_fixture(tmp_path):
    """Copy the whole cenario2 package, optionally mutating the result."""
    def _make(mutate=None):
        for src in C2.iterdir():
            if src.is_file():
                shutil.copyfile(src, tmp_path / src.name)
        path = tmp_path / "result.json"
        if mutate:
            doc = load(path)
            mutate(doc)
            dump(path, doc)
        return path
    return _make


@pytest.fixture
def lone_result(tmp_path):
    """The example result with no problem beside it."""
    shutil.copyfile(C2 / "result.json", tmp_path / "result.json")
    return tmp_path / "result.json"


@pytest.fixture
def bom_csv(tmp_path):
    """A demand CSV written the way SISQUAL writes them: UTF-8 BOM, CRLF.

    Built here rather than read from the vendor drop, so the test pins the
    reader's behaviour instead of a file somebody may move.
    """
    path = tmp_path / "bom_periods.csv"
    body = ("date,tableName,tableValue,minimum,ideal,estimated,start,end\r\n"
            "2026-03-02,Team,T1,2,0,0,09:00,13:00\r\n")
    path.write_bytes(b"\xef\xbb\xbf" + body.encode("utf-8"))
    return path
