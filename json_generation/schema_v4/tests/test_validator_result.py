"""The result form: its cross-checks against the problem, and its sidecar CSV."""

import csv

import pytest
from helpers import C2, load, validate

SIDECAR = "result_schedules.csv"


def test_the_example_result_validates():
    r = validate(C2 / "result.json")
    assert r.ok, r.errors
    assert not r.warnings, r.warnings
    assert r.stats["crossCheckedAgainst"] == "problem.json"


def test_it_covers_every_employee_day():
    """15 employees x 31 days -- stated as the product, not as 465."""
    from schema_v4 import core
    problem = load(C2 / "problem.json")
    expected = len(problem["employees"]["list"]) * len(core.horizon(problem))
    assert len(load(C2 / "result.json")["OutRosterTeamDays"]) == expected
    assert validate(C2 / "result.json").stats["rosterDays"] == expected


# -- cross-checks against the problem ----------------------------------------

@pytest.mark.parametrize("field, value, needle", [
    ("EmployeeCode", "999999", "999999 is not in employees.list"),
    ("RosterCode", "C9", "does not match the problem's metadata.rosterCode"),
    ("Date", "2027-05-05T00:00:00", "lies outside temporalScope"),
    ("Date", "not-a-date", "is not a date"),
])
def test_one_bad_field_on_one_entry(make_result_fixture, field, value, needle):
    def mutate(d):
        d["OutRosterTeamDays"][0][field] = value
    r = validate(make_result_fixture(mutate))
    assert any(needle in e for e in r.errors), r.errors


def test_two_entries_for_one_employee_day(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][1] = dict(d["OutRosterTeamDays"][0])
    r = validate(make_result_fixture(mutate))
    assert any("already has an entry for" in e for e in r.errors), r.errors


def test_an_integer_employee_code_warns(make_result_fixture):
    """JSON-Import.docx says string; SISQUAL's own sample emits an integer."""
    def mutate(d):
        d["OutRosterTeamDays"][0]["EmployeeCode"] = int(
            d["OutRosterTeamDays"][0]["EmployeeCode"])
    r = validate(make_result_fixture(mutate))
    assert any("EmployeeCode is an integer in 1 of" in w for w in r.warnings), r.warnings


def test_working_on_an_unavailable_day(make_result_fixture):
    """2026-01-01 is HOL for everyone in this bundle."""
    def mutate(d):
        d["OutRosterTeamDays"][0]["ScheduleCode"] = 9001
    r = validate(make_result_fixture(mutate))
    assert any("unavailable" in e and "assigns ScheduleCode" in e
               for e in r.errors), r.errors


def test_the_first_entry_really_is_a_rest_on_a_holiday():
    """The premise of the test above, asserted rather than assumed."""
    from schema_v4 import core
    entry = load(C2 / "result.json")["OutRosterTeamDays"][0]
    catalogue, _ = core.read_schedules(C2 / SIDECAR)
    assert entry["Date"].startswith("2026-01-01")
    assert catalogue[entry["ScheduleCode"]].is_sentinel


def test_resting_on_a_day_that_asks_for_work_warns(make_result_fixture):
    def mutate(d):
        working = next(e for e in d["OutRosterTeamDays"] if e["ScheduleCode"] != 3)
        working["ScheduleCode"] = 3
    r = validate(make_result_fixture(mutate))
    assert any("although the problem's cell asks for work" in w
               for w in r.warnings), r.warnings


def test_a_lone_result_warns_and_skips(lone_result):
    r = validate(lone_result)
    assert any("cross-checks were skipped" in w for w in r.warnings), r.warnings


def test_against_names_the_problem_explicitly(lone_result):
    r = validate(lone_result, against=C2 / "problem.json")
    assert r.stats["crossCheckedAgainst"] == "problem.json"


# -- the sidecar -------------------------------------------------------------

def test_a_missing_sidecar_warns_but_does_not_fail(make_result_fixture):
    path = make_result_fixture()
    (path.parent / SIDECAR).unlink()
    r = validate(path)
    assert r.ok, r.errors
    assert any("carry no definition" in w for w in r.warnings), r.warnings


def test_a_code_missing_from_the_sidecar_is_an_error(make_result_fixture):
    path = make_result_fixture()
    side = path.parent / SIDECAR
    kept = [r for r in csv.reader(side.read_text(encoding="utf-8").splitlines())
            if r[0] != "9001"]
    with side.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(kept)
    r = validate(path)
    assert any("9001 is used by the result but not defined here" in e
               for e in r.errors), r.errors


def test_an_unused_sidecar_row_warns(make_result_fixture):
    path = make_result_fixture()
    with (path.parent / SIDECAR).open("a", encoding="utf-8") as fh:
        fh.write("9004,13:00-17:00,240,780,1020\n")
    r = validate(path)
    assert any("which the result never uses" in w for w in r.warnings), r.warnings


def test_a_sidecar_row_contradicting_the_menu_is_an_error(make_result_fixture):
    path = make_result_fixture()
    side = path.parent / SIDECAR
    side.write_text(side.read_text(encoding="utf-8").replace(
        "9001,09:00-13:00,240,540,780", "9001,09:00-13:00,999,540,780"), encoding="utf-8")
    r = validate(path)
    assert any("but '09:00-13:00'/240min in the problem's catalogue" in e
               for e in r.errors), r.errors


def test_a_sidecar_code_outside_the_menu_is_an_error(make_result_fixture):
    """A result may only use shifts the problem offers."""
    def mutate(d):
        d["OutRosterTeamDays"][1]["ScheduleCode"] = 999999
    path = make_result_fixture(mutate)
    with (path.parent / SIDECAR).open("a", encoding="utf-8") as fh:
        fh.write("999999,09:00-13:00,240,540,780\n")
    r = validate(path)
    assert any("999999 is not in the problem's catalogue" in e for e in r.errors), r.errors


def test_a_missing_menu_is_said_out_loud(make_result_fixture):
    """Returning an empty menu quietly would turn every menu check into a no-op,
    and a result using a code nobody offers would pass for the wrong reason."""
    path = make_result_fixture()
    (path.parent / "schedules.csv").unlink()
    r = validate(path)
    assert any("menu (schedules.csv) is missing" in w for w in r.warnings), r.warnings


def test_a_problem_with_no_menu_at_all_is_also_said(make_result_fixture, tmp_path):
    path = make_result_fixture()
    doc = load(path.parent / "problem.json")
    del doc["schedules"]
    from helpers import dump
    dump(path.parent / "problem.json", doc)
    r = validate(path)
    assert any("declares no shift menu" in w for w in r.warnings), r.warnings


def test_the_sidecar_is_not_a_copy_of_the_menu():
    """It holds what the result used, which is fewer codes than the menu offers."""
    from schema_v4 import core
    problem = load(C2 / "problem.json")
    menu, _ = core.read_schedules(C2 / problem["schedules"]["dataFile"])
    sidecar, _ = core.read_schedules(C2 / SIDECAR)
    assert set(sidecar) < set(menu)


# -- OutScheduleUseds --------------------------------------------------------

def test_schedule_useds_contradicting_the_catalogue(make_result_fixture):
    def mutate(d):
        d["OutScheduleUseds"] = [{"ScheduleCode": 9001, "ScheduleWeight": 99}]
    r = validate(make_result_fixture(mutate))
    assert any("contradicts the catalogue's 240" in e for e in r.errors), r.errors


def test_a_repeated_schedule_used(make_result_fixture):
    def mutate(d):
        d["OutScheduleUseds"] = [{"ScheduleCode": 9001}, {"ScheduleCode": 9001}]
    r = validate(make_result_fixture(mutate))
    assert any("appears twice" in e for e in r.errors), r.errors


def test_an_orphan_schedule_used(make_result_fixture):
    def mutate(d):
        d["OutScheduleUseds"] = [{"ScheduleCode": 9004}]
    r = validate(make_result_fixture(mutate))
    assert any("which no roster day uses" in w for w in r.warnings), r.warnings
