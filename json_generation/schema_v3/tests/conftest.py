"""Pytest fixtures shared across the v3 conformance suite."""
import csv
import json
import shutil

import pytest

from helpers import SCHEMAS, SIS, TC


@pytest.fixture(scope="session")
def schemas():
    """The three form schemas, loaded once and checked to compile (Draft 2020-12)."""
    from jsonschema import Draft202012Validator
    docs = {}
    for f in ("schema-v3-declarative.json", "schema-v3-expanded.json", "schema-v3-solution.json"):
        d = json.loads((SCHEMAS / f).read_text())
        Draft202012Validator.check_schema(d)
        docs[f] = d
    return docs


@pytest.fixture
def make_fixture(tmp_path):
    """Factory: copy time_constraints_example into a fresh temp dir, optionally
    breaking exactly one thing (a problem mutation, cell overrides, or a whole
    demand.csv). Auto-cleaned via tmp_path."""
    n = 0

    def _make(mutate_problem=None, schedule_rows=None, demand_rows=None):
        nonlocal n
        n += 1
        d = tmp_path / f"fx{n}"
        d.mkdir()
        for f in ("problem.json", "demand.csv", "schedule_input.csv"):
            shutil.copy(TC / f, d / f)
        if mutate_problem:
            doc = json.loads((d / "problem.json").read_text())
            mutate_problem(doc)
            (d / "problem.json").write_text(json.dumps(doc, indent=2))
        if schedule_rows:
            rows = list(csv.reader(open(TC / "schedule_input.csv")))
            hdr = rows[0]
            for r in rows[1:]:
                for i, _ in enumerate(r[1:]):
                    if (r[0], hdr[i + 1]) in schedule_rows:
                        r[i + 1] = schedule_rows[(r[0], hdr[i + 1])]
            with open(d / "schedule_input.csv", "w", newline="") as fh:
                csv.writer(fh).writerows(rows)
        if demand_rows is not None:
            with open(d / "demand.csv", "w", newline="") as fh:
                csv.writer(fh).writerows(demand_rows)
        return d

    return _make


@pytest.fixture
def make_sol_fixture(tmp_path):
    """Factory: a temp dir with the sisqual expanded problem + a (optionally
    mutated) copy of its solution, so validate() cross-checks the two."""
    n = 0

    def _make(mutate=None):
        nonlocal n
        n += 1
        d = tmp_path / f"sol{n}"
        d.mkdir()
        shutil.copy(SIS / "problem.expanded.json", d / "problem.expanded.json")
        s = json.loads((SIS / "solution.json").read_text())
        if mutate:
            mutate(s)
        (d / "solution.json").write_text(json.dumps(s))
        return d

    return _make
