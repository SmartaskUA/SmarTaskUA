"""The adapter: it reproduces examples/, and it reports what it changed."""

import json

import pytest
from helpers import C1, C2, CATALOGUE, RAW_C1, RAW_C2, RAW_JULY, validate

from schema_v4 import sisqual_adapt
from schema_v4.sisqual_adapt import AdaptError


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


@pytest.mark.parametrize("raw, expected, schedules", [
    (RAW_C2, C2, None),
    (RAW_C1, C1, CATALOGUE),
])
def test_adapting_reproduces_the_committed_example(raw, expected, schedules, tmp_path):
    sisqual_adapt.adapt(raw, tmp_path, schedules)
    for name in ("problem.json", "days_demand.csv", "periods_demand.csv",
                 "shifts_demand.csv", "schedule_input.csv"):
        assert _read(tmp_path / name) == _read(expected / name), f"{name} drifted"


def test_every_known_misspelling_is_reported(tmp_path):
    _, fixes = sisqual_adapt.adapt(RAW_C2, tmp_path)
    labels = [label for label, _ in fixes]
    for needle in ("contractAssigments -> contractAssignments",
                   "priorityHierachy -> priorityHierarchy",
                   "calendar.inpUAHolidaysCollection -> calendar.holidays",
                   'weekStart "Monday" -> "monday"',
                   'end "9999-12-31" -> null',
                   'tableName "Equipa" -> "Team"',
                   'tableName "Piso" -> "Responsibility"',
                   "stripped UTF-8 BOM"):
        assert any(needle in l for l in labels), f"{needle!r} not reported in {labels}"


def test_the_output_carries_none_of_the_misspellings(tmp_path):
    problem, _ = sisqual_adapt.adapt(RAW_C2, tmp_path)
    blob = json.dumps(problem, ensure_ascii=False)
    for bad in ("contractAssigments", "priorityHierachy", "inpUAHolidaysCollection",
                '"Preferable"', '"Unavailable"', '"Monday"', "9999-12-31",
                '"Equipa"', '"Piso"'):
        assert bad not in blob, f"{bad!r} survived into the canonical output"


def test_decimal_commas_are_normalised(tmp_path):
    """Cenario 1's NL contract is 7.2 h, written "7,2" in a quoted field."""
    _, fixes = sisqual_adapt.adapt(RAW_C1, tmp_path)
    assert any("decimal comma -> dot" in l for l, _ in fixes)
    assert '"7,2"' not in _read(tmp_path / "schedule_input.csv")
    assert "7.2" in _read(tmp_path / "schedule_input.csv")


def test_dimensions_are_synthesised_from_all_three_sources(tmp_path):
    problem, _ = sisqual_adapt.adapt(RAW_C2, tmp_path)
    pairs = {(d["tableName"], d["tableValue"]) for d in problem["demand"]["dimensions"]}
    assert pairs == {("Team", "T1"), ("Responsibility", "A"),
                     ("Responsibility", "C"), ("Responsibility", "G")}


def test_cenario1_dimensions_come_from_priority_alone(tmp_path):
    """Its employees hold nothing and its demand is empty, so only one source is left."""
    problem, _ = sisqual_adapt.adapt(RAW_C1, tmp_path)
    assert len(problem["demand"]["dimensions"]) == 3
    assert all(not e["competencyAssignments"] for e in problem["employees"]["list"])


def test_adapted_output_validates(tmp_path):
    sisqual_adapt.adapt(RAW_C2, tmp_path)
    r = validate(tmp_path / "problem.json")
    assert r.ok, r.errors


def test_the_adapter_does_not_invent_missing_contracts(tmp_path):
    """The July bundle stays broken, and the validator says so."""
    problem, _ = sisqual_adapt.adapt(RAW_JULY, tmp_path)
    assert problem["contracts"]["definitions"] == []
    r = validate(tmp_path / "problem.json")
    assert any("unknown contract 'PT_40'" in e for e in r.errors), r.errors


def test_raw_bundles_do_not_validate_directly():
    """By design: the canon is correct, so their spelling must be converted first."""
    raw = next(p for p in RAW_C2.iterdir() if p.suffix.lower() == ".json")
    r = validate(raw)
    assert not r.ok
    assert any("sisqual_adapt" in e for e in r.errors), r.errors


def test_a_directory_with_no_problem_is_refused(tmp_path):
    with pytest.raises(AdaptError):
        sisqual_adapt.adapt(tmp_path, tmp_path / "out")


def test_roster_code_is_derived_from_the_problem_id(tmp_path):
    problem, _ = sisqual_adapt.adapt(RAW_C2, tmp_path)
    assert problem["metadata"]["rosterCode"] == "C2"
    assert problem["metadata"]["problemId"] == "C2_January_2026"
