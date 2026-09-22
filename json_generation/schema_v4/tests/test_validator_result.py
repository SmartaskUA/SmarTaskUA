"""The result form: its cross-checks against the problem, and its sidecar CSV."""

import csv
import json
import shutil

from helpers import C2, sisqual_result, validate


def test_the_example_result_validates():
    r = validate(C2 / "result.json")
    assert r.ok, r.errors
    assert r.stats["crossCheckedAgainst"] == "problem.json"
    assert r.stats["rosterDays"] == 465


def test_the_only_warning_is_the_documented_substitution():
    """PT_35 needs 420 min and no such code exists; 390 is the nearest."""
    r = validate(C2 / "result.json")
    assert all("390 min but" in w or "with the same cause" in w
               for w in r.warnings), r.warnings


def test_repeated_findings_are_collapsed():
    r = validate(C2 / "result.json")
    assert any("and 18 more with the same cause" in w for w in r.warnings), r.warnings
    assert len(r.warnings) < 6, r.warnings


# -- cross-checks against the problem ---------------------------------------

def test_unknown_employee(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][0]["EmployeeCode"] = "999999"
    r = validate(make_result_fixture(mutate))
    assert any("999999 is not in employees.list" in e for e in r.errors), r.errors


def test_roster_code_must_match(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][0]["RosterCode"] = "C9"
    r = validate(make_result_fixture(mutate))
    assert any("does not match the problem's metadata.rosterCode" in e
               for e in r.errors), r.errors


def test_date_outside_the_horizon(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][0]["Date"] = "2027-05-05T00:00:00"
    r = validate(make_result_fixture(mutate))
    assert any("lies outside temporalScope" in e for e in r.errors), r.errors


def test_two_entries_for_one_employee_day(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][1] = dict(d["OutRosterTeamDays"][0])
    r = validate(make_result_fixture(mutate))
    assert any("already has an entry for" in e for e in r.errors), r.errors


def test_working_on_an_unavailable_day(make_result_fixture):
    """2026-01-01 is HOL for everyone in this bundle."""
    def mutate(d):
        d["OutRosterTeamDays"][0]["ScheduleCode"] = 1014
    r = validate(make_result_fixture(mutate))
    assert any("unavailable" in e and "assigns ScheduleCode" in e
               for e in r.errors), r.errors


def test_a_rest_sentinel_on_an_unavailable_day_is_fine(make_result_fixture):
    r = validate(make_result_fixture())
    assert not any("assigns ScheduleCode" in e for e in r.errors), r.errors


def test_a_lone_result_warns_and_skips(tmp_path):
    shutil.copyfile(C2 / "result.json", tmp_path / "result.json")
    r = validate(tmp_path / "result.json")
    assert any("cross-checks were skipped" in w for w in r.warnings), r.warnings


def test_against_names_the_problem_explicitly(tmp_path):
    shutil.copyfile(C2 / "result.json", tmp_path / "result.json")
    r = validate(tmp_path / "result.json", against=C2 / "problem.json")
    assert r.stats["crossCheckedAgainst"] == "problem.json"


# -- the sidecar -------------------------------------------------------------

def test_a_missing_sidecar_warns_but_does_not_fail(make_result_fixture):
    path = make_result_fixture()
    (path.parent / "result_schedules.csv").unlink()
    r = validate(path)
    assert r.ok, r.errors
    assert any("carry no definition" in w for w in r.warnings), r.warnings


def test_a_code_missing_from_the_sidecar_is_an_error(make_result_fixture):
    path = make_result_fixture()
    side = path.parent / "result_schedules.csv"
    rows = [r for r in csv.reader(side.read_text(encoding="utf-8").splitlines())
            if r[0] != "1014"]
    with side.open("w", newline="", encoding="utf-8") as fh:
        csv.writer(fh, lineterminator="\n").writerows(rows)
    r = validate(path)
    assert any("1014 is used by the result but not defined here" in e
               for e in r.errors), r.errors


def test_an_unused_sidecar_row_warns(make_result_fixture):
    path = make_result_fixture()
    side = path.parent / "result_schedules.csv"
    with side.open("a", encoding="utf-8") as fh:
        fh.write("100000,00:00-03:00,180,0,180\n")
    r = validate(path)
    assert any("which the result never uses" in w for w in r.warnings), r.warnings


def test_a_sidecar_row_contradicting_the_menu_is_an_error(make_result_fixture):
    path = make_result_fixture()
    side = path.parent / "result_schedules.csv"
    text = side.read_text(encoding="utf-8").replace(
        "1014,08:00-16:00,480,480,960", "1014,08:00-16:00,999,480,960")
    side.write_text(text, encoding="utf-8")
    r = validate(path)
    assert any("but '08:00-16:00'/480min in the problem's catalogue" in e
               for e in r.errors), r.errors


def test_a_sidecar_code_outside_the_menu_is_an_error(make_result_fixture):
    """A solver may only use shifts the problem offers."""
    def mutate(d):
        d["OutRosterTeamDays"][1]["ScheduleCode"] = 999999
    path = make_result_fixture(mutate)
    side = path.parent / "result_schedules.csv"
    with side.open("a", encoding="utf-8") as fh:
        fh.write("999999,09:00-13:00,240,540,780\n")
    r = validate(path)
    assert any("999999 is not in the problem's catalogue" in e for e in r.errors), r.errors


def test_schedule_useds_contradicting_the_catalogue(make_result_fixture):
    def mutate(d):
        d["OutScheduleUseds"] = [{"ScheduleCode": 1014, "ScheduleWeight": 99}]
    r = validate(make_result_fixture(mutate))
    assert any("contradicts the catalogue's 480" in e for e in r.errors), r.errors


# -- Sisqual's own sample ----------------------------------------------------

def test_sisqual_sample_keeps_its_two_quirks_on_record(tmp_path):
    """import_1.Json is not shipped as an example, but its defects still matter.

    It is the only instance of an integer EmployeeCode and of a ScheduleCode we
    cannot resolve - 100154 has a meal break, and we hold only the without-meal
    catalogue. Both are live agenda items, so both keep a test.
    """
    result = sisqual_result(tmp_path)
    shutil.copyfile(C2 / "problem.json", tmp_path / "problem.json")
    for name in ("schedule_input.csv", "schedules_without_meal.csv"):
        shutil.copyfile(C2 / name, tmp_path / name)
    r = validate(result)
    assert any("EmployeeCode is an integer" in w for w in r.warnings), r.warnings
    assert any("100154 is not in the schedules catalogue" in e for e in r.errors), r.errors


def test_the_raw_sisqual_sample_is_not_valid_json():
    """U+2002 EN SPACE indentation from an Outlook paste - see next_meeting.md 22."""
    from helpers import RAW_C1
    raw = (RAW_C1 / "import_1.Json").read_bytes()
    assert raw.count(" ".encode()) == 12
    try:
        json.loads(raw.decode("utf-8-sig"))
        assert False, "expected this file to be malformed"
    except ValueError:
        pass
