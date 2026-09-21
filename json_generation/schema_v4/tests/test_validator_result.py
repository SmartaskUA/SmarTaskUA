"""The result form's cross-checks against its problem."""

from helpers import C1, validate


def test_the_real_result_fails_only_on_the_missing_catalogue():
    """ScheduleCode 100154 has a meal break, and we only have the without-meal list."""
    r = validate(C1 / "result.json")
    assert r.errors
    assert all("100154 is not in the schedules catalogue" in e for e in r.errors), r.errors
    assert r.stats["crossCheckedAgainst"] == "problem.json"


def test_employee_code_type_mismatch_warns():
    r = validate(C1 / "result.json")
    assert any("EmployeeCode is an integer" in w for w in r.warnings), r.warnings


def test_unknown_employee(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][0]["EmployeeCode"] = 999999
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
        d["OutRosterTeamDays"][0]["Date"] = "2026-01-01T00:00:00"
        d["OutRosterTeamDays"][0]["ScheduleCode"] = 100000
    r = validate(make_result_fixture(mutate))
    assert any("unavailable" in e and "assigns ScheduleCode" in e
               for e in r.errors), r.errors


def test_a_rest_sentinel_on_an_unavailable_day_is_fine(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][0]["Date"] = "2026-01-01T00:00:00"
        d["OutRosterTeamDays"][0]["ScheduleCode"] = 3        # Day off
    r = validate(make_result_fixture(mutate))
    assert not any("assigns ScheduleCode" in e for e in r.errors), r.errors


def test_schedule_useds_contradicting_the_catalogue(make_result_fixture):
    def mutate(d):
        d["OutRosterTeamDays"][0]["ScheduleCode"] = 100000
        d["OutScheduleUseds"] = [{"ScheduleCode": 100000, "ScheduleWeight": 99}]
    r = validate(make_result_fixture(mutate))
    assert any("contradicts the catalogue's 180" in e for e in r.errors), r.errors


def test_a_lone_result_warns_and_skips(tmp_path):
    import shutil
    shutil.copyfile(C1 / "result.json", tmp_path / "result.json")
    r = validate(tmp_path / "result.json")
    assert r.ok
    assert any("cross-checks were skipped" in w for w in r.warnings), r.warnings


def test_against_names_the_problem_explicitly(tmp_path):
    import shutil
    shutil.copyfile(C1 / "result.json", tmp_path / "result.json")
    r = validate(tmp_path / "result.json", against=C1 / "problem.json")
    assert r.stats["crossCheckedAgainst"] == "problem.json"
