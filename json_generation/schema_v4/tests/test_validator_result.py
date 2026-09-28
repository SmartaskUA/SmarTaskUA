"""The result form: its cross-checks against the problem, and its sidecar CSV."""

import csv

import pytest
from helpers import C2, assert_isolated, load, validate

SIDECAR = "result_schedules.csv"
RESULT = "result_template.json"


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
    r = validate(C2 / "result.json")
    assert r.stats["rosterDays"] == r.stats["rosterDaysExpected"] == expected
    assert r.stats["rosterDaysLeft"] == 0


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
    assert any("(unavailable), but the day is worked" in e for e in r.errors), r.errors


def test_the_first_entry_really_is_a_rest_on_a_holiday():
    """The premise of the test above, asserted rather than assumed."""
    from schema_v4 import core
    entry = load(C2 / "result.json")["OutRosterTeamDays"][0]
    catalogue, _ = core.read_schedules(C2 / SIDECAR)
    assert entry["Date"].startswith("2026-01-01")
    assert catalogue[entry["ScheduleCode"]].is_sentinel


def test_resting_on_a_day_that_asks_for_work_is_an_error(make_result_fixture):
    """A fixed rest on a working day contradicts the cell, so it is no longer a warning."""
    def mutate(d):
        working = next(e for e in d["OutRosterTeamDays"] if e["ScheduleCode"] != 3)
        working["ScheduleCode"] = 3
    r = validate(make_result_fixture(mutate))
    assert any("the cell asks for work, but the day is a rest" in e
               for e in r.errors), r.errors


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


# -- fixed days, on the templates --------------------------------------------
#
# The template package validates with no errors and no warnings, so every finding
# below is what the test broke. Mutations only reuse codes the sidecar defines
# (3, 9001, 9002, 9003) and never retire a code's last use, or the sidecar checks
# would fire too.

def fixed(make_fixture, codes=None, drop=(), **kw):
    """Validate the template result after setting or dropping (employee, date) entries."""
    def mutate(d):
        kept = []
        for e in d["OutRosterTeamDays"]:
            key = (e["EmployeeCode"], e["Date"][:10])
            if key in drop:
                continue
            if codes and key in codes:
                e["ScheduleCode"] = codes[key]
            kept.append(e)
        d["OutRosterTeamDays"] = kept
    return validate(make_fixture(mutate_result=mutate, **kw).parent / RESULT)


def cap(name, value):
    def mutate(d):
        d["constraints"]["hard"][0]["parameters"][name] = value
    return mutate


@pytest.mark.parametrize("cell, code, needle", [
    ("EQUALS:09:00-17:00", 9001, "is not the 09:00-17:00 the cell asks for"),
    ("EQUALS:09:00-12:00,13:00-17:00", 9003, "split shift"),
    ("INCLUDE:07:00-10:00", 9003, "does not cover 07:00-10:00"),
    ("WITHIN:13:00-17:00", 9001, "fits inside none of 13:00-17:00"),
    ("EXCEPT:09:00-10:00", 9003, "overlaps 09:00-10:00"),
    ("4", 9003, "480 min but the cell asks for 240"),
    ("A", 9001, "240 min but the cell asks for 480"),
    ("", 9003, "the cell is blank"),
])
def test_a_fixed_day_that_contradicts_its_cell(make_fixture, cell, code, needle):
    """EMP001 is on the 8-hour contract; 2026-03-02 is a plain working day."""
    key = ("EMP001", "2026-03-02")
    r = fixed(make_fixture, codes={key: code}, schedule_rows={key: cell})
    assert_isolated(r, needle)


def test_a_fixed_day_may_work_a_preferable_day_off(make_fixture):
    r = fixed(make_fixture, codes={("EMP001", "2026-03-06"): 9003})
    assert r.ok and not r.warnings, (r.errors, r.warnings)


def test_a_partial_result_is_clean_and_counts_what_is_left(make_fixture):
    """Drop the last day for everyone: every code keeps a use, so nothing else moves."""
    drop = {(e, "2026-03-08") for e in ("EMP001", "EMP002", "EMP003", "EMP004")}
    r = fixed(make_fixture, drop=drop)
    assert r.ok and not r.warnings, (r.errors, r.warnings)
    assert r.stats["rosterDaysExpected"] == 28
    assert r.stats["rosterDaysLeft"] == 4


def test_fixed_days_above_max_consecutive_work_days(make_fixture):
    """EMP001 works 03-02..03-05, four in a row; nobody else reaches four."""
    r = fixed(make_fixture, mutate_problem=cap("MaxConsecutiveWorkDays", 3))
    assert_isolated(r, "EMP001: fixed to work 4 days in a row ending 2026-03-05")


def test_an_open_day_breaks_a_run(make_fixture):
    """The solver may yet rest the day left out, so the two halves are judged apart."""
    r = fixed(make_fixture, drop={("EMP001", "2026-03-04")},
              mutate_problem=cap("MaxConsecutiveWorkDays", 3))
    assert r.ok and not r.warnings, (r.errors, r.warnings)


def test_fixed_days_above_the_weekly_cap(make_fixture):
    """Everyone works five days in the template's one week; EMP001 now works six."""
    r = fixed(make_fixture, codes={("EMP001", "2026-03-06"): 9003},
              mutate_problem=cap("MaxConsecutiveWorkDaysInWeek", 5))
    assert_isolated(r, "EMP001, week 0: 6 fixed working days exceeds "
                       "MaxConsecutiveWorkDaysInWeek of 5")


def test_too_little_rest_between_fixed_shifts(make_fixture):
    """A night shift on 03-02 leaves three hours before 09:00 on 03-03."""
    def mutate(d):
        d["OutRosterTeamDays"][0]["ScheduleCode"] = 9004      # EMP001, 2026-03-02
    path = make_fixture(mutate_result=mutate).parent
    with (path / "result_template_schedules.csv").open("a", encoding="utf-8") as fh:
        fh.write("9004,22:00-06:00,480,1320,1800\n")
    assert_isolated(validate(path / RESULT),
                    "180 min of rest between 22:00-06:00 on 2026-03-02")
