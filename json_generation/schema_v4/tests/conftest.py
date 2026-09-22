"""Fixtures: a valid package, and factories that break exactly one thing in it."""

from __future__ import annotations

import csv
import json
import shutil

import pytest
from helpers import SCHEMAS, TEMPLATES, C2


@pytest.fixture(scope="session")
def schemas():
    """Both schemas, parsed and checked as schemas."""
    from jsonschema import Draft202012Validator
    out = {}
    for path in sorted(SCHEMAS.glob("*.json")):
        with path.open(encoding="utf-8") as fh:
            schema = json.load(fh)
        Draft202012Validator.check_schema(schema)
        out[path.name] = schema
    return out


@pytest.fixture
def make_fixture(tmp_path):
    """Copy the templates package into tmp_path, optionally breaking one thing.

    The templates are the control: they validate with no errors and no warnings,
    so anything a fixture reports is what the test broke.
    """
    def _make(mutate_problem=None, schedule_rows=None, demand_rows=None,
              schedules_rows=None):
        for src in TEMPLATES.iterdir():
            if src.suffix in (".json", ".csv"):
                shutil.copyfile(src, tmp_path / src.name)

        problem_path = tmp_path / "problem_template.json"
        if mutate_problem:
            with problem_path.open(encoding="utf-8") as fh:
                doc = json.load(fh)
            mutate_problem(doc)
            with problem_path.open("w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, ensure_ascii=False)

        if schedule_rows:
            path = tmp_path / "schedule_input_template.csv"
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

        if demand_rows:
            (tmp_path / "periods_demand_template.csv").write_text(demand_rows,
                                                                  encoding="utf-8")
        if schedules_rows:
            (tmp_path / "schedules_template.csv").write_text(schedules_rows,
                                                             encoding="utf-8")
        return problem_path
    return _make


@pytest.fixture
def make_result_fixture(tmp_path):
    """Copy cenario2's whole package, optionally mutating the result."""
    def _make(mutate=None):
        for src in C2.iterdir():
            if src.is_file():
                shutil.copyfile(src, tmp_path / src.name)
        path = tmp_path / "result.json"
        if mutate:
            with path.open(encoding="utf-8") as fh:
                doc = json.load(fh)
            mutate(doc)
            with path.open("w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, ensure_ascii=False)
        return path
    return _make
