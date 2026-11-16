"""The payload WFM imports: worked days as start/end, rests as a code, a team on every day."""

import re
from datetime import date, timedelta

import pytest

from conftest import EXAMPLES, REPO

from problem_v4 import SolveDirectives, sisqual_import
from problem_v4.rows import format_worked_cell, parse_worked_cell, rest_cell
from problem_v4.runtime import load_for_solver

STAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}$")
COMMON = {"RosterCode", "TeamCode", "EmployeeCode", "Date",
          "OutRosterTeamDayTasks", "OutRosterTeamDayResponsibilities"}
WORKED_KEYS = COMMON | {"ScheduleStartDate", "ScheduleEndDate"}
REST_KEYS = COMMON | {"ScheduleCode"}


def _load(package):
    return load_for_solver(str(package), SolveDirectives(), "test", "test")


def _first_candidate_rows(inst):
    """Every open work day on its first candidate, every other day a rest."""
    rows = [["employee_id", *inst.days]]
    for employee in inst.employees:
        row = [employee.id]
        for day in inst.days:
            shifts = inst.candidates.get((employee.id, day)) or []
            if (employee.id, day) in inst.fixed or not shifts or not inst.is_work_day(employee.id, day):
                row.append(rest_cell(inst, employee.id, day))
                continue
            teams = [s for s in employee.skills.get(day, {}) if s.startswith("Team/")]
            shift = shifts[0]
            row.append(format_worked_cell(shift, {t: teams[:1] for t in shift.slot_indices},
                                          inst.slot_minutes))
        rows.append(row)
    return rows


def _check_shape(payload, inst):
    assert set(payload) == {"OutRosterTeamDays"}
    for entry in payload["OutRosterTeamDays"]:
        assert entry["TeamCode"]
        if "ScheduleCode" in entry:
            assert set(entry) == REST_KEYS
            assert inst.menu[entry["ScheduleCode"]].is_sentinel
        else:
            assert set(entry) == WORKED_KEYS
            assert STAMP.match(entry["ScheduleStartDate"]) and STAMP.match(entry["ScheduleEndDate"])
            assert entry["ScheduleStartDate"].startswith(entry["Date"])
            assert entry["ScheduleStartDate"] < entry["ScheduleEndDate"]


def test_worked_days_carry_the_hours_and_rests_the_code():
    inst = _load(EXAMPLES / "cenario2_partial")
    rows = _first_candidate_rows(inst)
    payload = sisqual_import(inst, rows)
    _check_shape(payload, inst)

    cells = {r[0]: dict(zip(inst.days, r[1:])) for r in rows[1:]}
    worked = [e for e in payload["OutRosterTeamDays"] if "ScheduleStartDate" in e]
    assert worked
    for entry in worked:
        key = (entry["EmployeeCode"], entry["Date"])
        segments = parse_worked_cell(cells[key[0]][key[1]])
        if segments:
            start, end = segments[0][0], segments[-1][1]
        else:  # a fixed work day: its code's hours
            interval = inst.menu[inst.fixed[key].code].interval
            start, end = interval.start, interval.end
        assert entry["ScheduleStartDate"][11:16] == f"{start // 60:02d}:{start % 60:02d}"
        assert entry["ScheduleEndDate"][11:16] == f"{end // 60 % 24:02d}:{end % 60:02d}"


@pytest.fixture(scope="module")
def three_shifts():
    """A quick legacy GA run on two teams and a night shift, as the GA writes it."""
    name = "V4_SMARTASK_3SHIFTS_2TEAMS_2025"
    package = REPO / "data" / "problems" / name
    if not package.is_dir():
        pytest.skip(f"{name} is not in data/problems")
    import numpy as np
    from algorithms.GA.legacy_v4 import load_problem_v4, schedule_rows

    inst = _load(package)
    problem_data, ga, gp = load_problem_v4(inst.problem_path)
    params = dict(ga._GA_PARAMS, pop_size=10, num_generations=2)
    ga.random.seed(1)
    np.random.seed(1)
    best, _, _, _ = ga.run_ga(problem_data, params)
    schedule = np.array(best["genes"], dtype=int).reshape(problem_data["n_employees"],
                                                          problem_data["n_days"])
    rows = schedule_rows(inst, problem_data, schedule, gp)
    return inst, rows, sisqual_import(inst, rows)


def test_a_night_shift_ends_the_next_morning(three_shifts):
    inst, _, payload = three_shifts
    _check_shape(payload, inst)
    nights = [e for e in payload["OutRosterTeamDays"]
              if e.get("ScheduleStartDate", "").endswith("T22:00:00")]
    assert nights
    for entry in nights:
        next_day = (date.fromisoformat(entry["Date"]) + timedelta(days=1)).isoformat()
        assert entry["ScheduleEndDate"] == f"{next_day}T06:00:00"


def test_two_team_employees_get_the_team_they_worked_or_the_nearest(three_shifts):
    inst, rows, payload = three_shifts
    by_day = {(e["EmployeeCode"], e["Date"]): e["TeamCode"] for e in payload["OutRosterTeamDays"]}
    checked = 0
    for row in rows[1:]:
        employee = inst.employee(str(row[0]))
        if len({s for d in employee.skills.values() for s in d if s.startswith("Team/")}) < 2:
            continue
        worked = {i: parse_worked_cell(c)[0][2][0].split("/", 1)[1]
                  for i, c in enumerate(row[1:]) if parse_worked_cell(c)}
        for i, day in enumerate(inst.days):
            nearest = worked[i] if i in worked else worked[min(worked, key=lambda j: (abs(j - i), j))]
            assert by_day[(employee.id, day)] == nearest
            checked += 1
    assert checked
