"""The row format, the shared evaluator and the result writer."""

import csv
import shutil
from collections import Counter

import pytest

from conftest import EXAMPLES, assert_valid_complete, read_result
from problem_v4 import (
    ResultError,
    Shift,
    SolveDirectives,
    evaluate,
    fixed_days,
    format_worked_cell,
    load_package,
    parse_worked_cell,
    objective,
    rest_cell,
    result_from_rows,
    write_package,
)


def rows_from_fixed(inst, skills_for=lambda eid, day, t: ()):
    """Rows that replay a complete result's fixed days, crediting `skills_for` per slot."""
    rows = [["employee_id", *inst.days]]
    for employee in inst.employees:
        row = [employee.id]
        for day in inst.days:
            fixed = inst.fixed[(employee.id, day)]
            if fixed.shift is None:
                row.append(rest_cell(inst, employee.id, day))
            else:
                slot_skills = {t: skills_for(employee.id, day, t) for t in fixed.shift.slot_indices}
                row.append(format_worked_cell(fixed.shift, slot_skills, inst.slot_minutes))
        rows.append(row)
    return rows


def test_a_worked_cell_round_trips_through_the_row_format():
    shift = Shift("k", 9001, 540, 780, tuple(range(18, 26)))
    skills = {t: ("Responsibility/A", "Team/T1") if t < 20 else ("Team/T1",) for t in range(18, 26)}
    text = format_worked_cell(shift, skills, 30)
    assert text == "09:00-10:00@Responsibility/A+Team/T1 | 10:00-13:00@Team/T1"
    assert parse_worked_cell(text) == [(540, 600, ("Responsibility/A", "Team/T1")), (600, 780, ("Team/T1",))]


def test_a_shift_past_midnight_keeps_its_minutes_past_1440():
    shift = Shift("k", 1, 1320, 1560, tuple(range(44, 52)))
    text = format_worked_cell(shift, {}, 30)
    assert text == "22:00-02:00@idle"
    assert parse_worked_cell(text) == [(1320, 1560, ())]
    assert parse_worked_cell("DO") is None and parse_worked_cell("") is None


def test_the_writer_reproduces_a_complete_result():
    inst = load_package(EXAMPLES / "cenario2_retail")
    doc, sidecar = result_from_rows(inst, rows_from_fixed(inst))
    written = {(e["EmployeeCode"], e["Date"][:10]): e["ScheduleCode"] for e in doc["OutRosterTeamDays"]}
    original = {(str(e["EmployeeCode"]), e["Date"][:10]): e["ScheduleCode"]
                for e in read_result(EXAMPLES / "cenario2_retail")["OutRosterTeamDays"]}
    assert written == original
    assert sorted(s.code for s in sidecar) == sorted(set(original.values()))


def test_a_written_package_passes_the_v4_validator(tmp_path):
    inst = load_package(EXAMPLES / "cenario2_retail")
    write_package(inst, rows_from_fixed(inst), tmp_path / "out")
    assert_valid_complete(tmp_path / "out")


def test_the_writer_never_writes_into_the_input_package():
    inst = load_package(EXAMPLES / "cenario2_retail")
    with pytest.raises(ValueError, match="input package"):
        write_package(inst, rows_from_fixed(inst), EXAMPLES / "cenario2_retail")


def test_a_work_day_left_without_a_shift_cannot_become_a_result():
    inst = load_package(EXAMPLES / "cenario2_input_only")
    rows = [["employee_id", *inst.days]] + [[e.id, *(rest_cell(inst, e.id, d) for d in inst.days)]
                                             for e in inst.employees]
    with pytest.raises(ResultError, match="a work day left as"):
        result_from_rows(inst, rows)


def test_evaluate_counts_shortage_and_priority_per_skill():
    inst = load_package(EXAMPLES / "cenario2_retail")
    idle = evaluate(inst, rows_from_fixed(inst))
    assert idle["total_shortage"] == idle["total_demand"] == sum(inst.alpha.values())
    assert idle["priority_cost"] == 0 and idle["unassigned"] == 0

    t1 = evaluate(inst, rows_from_fixed(inst, lambda eid, day, t: ("Team/T1",)))
    # the same count, done independently: workers on shift per (day, slot)
    on_shift = Counter((day, t) for (eid, day), f in inst.fixed.items() if f.shift for t in f.shift.slot_indices)
    expected = sum(max(0, need - on_shift[(day, t)])
                   for (day, t, skill), need in inst.alpha.items() if skill == "Team/T1")
    assert t1["shortage_by_skill"].get("Team/T1", 0) == expected
    # Team/T1 is tier 1, so p_sl = 1 for every worker on every demanded T1 slot
    assert t1["priority_cost"] == sum(on_shift[(d, t)] for (d, t, s) in inst.alpha if s == "Team/T1")


def test_fixed_days_lists_what_a_partial_result_decided():
    decided = fixed_days(load_package(EXAMPLES / "cenario2_partial"))
    assert len(decided["fixed"]) == 105             # the first week, 15 employees x 7 days
    assert decided["open_days"] == 360
    assert decided["fixed"] == sorted(decided["fixed"])
    assert {day for _, day in decided["fixed"]} == {f"2026-01-0{d}" for d in range(1, 8)}


def test_without_a_result_nothing_is_fixed():
    assert fixed_days(load_package(EXAMPLES / "cenario2_input_only")) == {"fixed": [], "open_days": 465}


def test_evaluate_counts_surplus_and_the_default_objective():
    inst = load_package(EXAMPLES / "cenario2_retail")
    kpis = evaluate(inst, rows_from_fixed(inst, lambda eid, day, t: ("Team/T1",)))
    on_shift = Counter((day, t) for (eid, day), f in inst.fixed.items() if f.shift for t in f.shift.slot_indices)
    expected = sum(max(0, on_shift[(day, t)] - need)
                   for (day, t, skill), need in inst.alpha.items() if skill == "Team/T1")
    assert kpis["surplus_by_skill"].get("Team/T1", 0) == expected
    assert kpis["total_surplus"] == sum(kpis["surplus_by_skill"].values())
    assert kpis["objective"] == objective(kpis, SolveDirectives())


def test_a_worked_day_off_fixed_by_the_result_is_not_the_solvers_choice():
    inst = load_package(EXAMPLES / "cenario2_retail")
    kpis = evaluate(inst, rows_from_fixed(inst))
    fixed_worked_dos = sum(1 for key, f in inst.fixed.items()
                           if f.shift and inst.day_modes[key] == "preferred_day_off")
    assert kpis["day_off_worked"] == 0
    assert kpis["day_off_worked_fixed"] == fixed_worked_dos


def test_an_employee_missing_from_the_rows_leaves_its_work_days_unassigned():
    inst = load_package(EXAMPLES / "cenario2_retail")
    rows = rows_from_fixed(inst)
    dropped = rows.pop(1)[0]
    kpis = evaluate(inst, rows)
    work_days = sum(inst.is_work_day(dropped, d) for d in inst.days)
    assert kpis["missing_rows"] == 1
    assert kpis["unassigned"] == work_days
    assert {eid for eid, _ in kpis["unassigned_days"]} == {dropped}


def test_open_shifts_on_unavailable_days_and_days_off_are_counted():
    inst = load_package(EXAMPLES / "cenario2_input_only")
    shift = next(s for shifts in inst.candidates.values() for s in shifts)
    worked = format_worked_cell(shift, {}, inst.slot_minutes)
    unavailable = next(k for k, m in inst.day_modes.items() if m == "unavailable")
    day_off = next(k for k, m in inst.day_modes.items() if m == "preferred_day_off")
    rows = [["employee_id", *inst.days]]
    for e in inst.employees:
        rows.append([e.id, *(worked if (e.id, d) in (unavailable, day_off) else rest_cell(inst, e.id, d)
                             for d in inst.days)])
    kpis = evaluate(inst, rows)
    assert kpis["work_on_unavailable"] == 1
    assert kpis["day_off_worked"] == 1 and kpis["day_off_worked_fixed"] == 0


def test_without_ideal_columns_there_is_no_ideal_target():
    inst = load_package(EXAMPLES / "cenario2_retail")
    kpis = evaluate(inst, rows_from_fixed(inst, lambda eid, day, t: ("Team/T1",)))
    assert inst.ideal == {}
    assert kpis["total_ideal"] == 0 and kpis["ideal_shortage"] == 0


def test_ideal_shortage_measures_the_gap_to_the_ideal_not_the_minimum(tmp_path):
    package = tmp_path / "pkg"
    shutil.copytree(EXAMPLES / "cenario2_retail", package)
    demand = package / "periods_demand.csv"
    with demand.open(newline="") as fh:
        rows = list(csv.DictReader(fh))
    for i, row in enumerate(rows):
        # one row asks for an ideal below its minimum: the target is still the minimum
        row["ideal"] = "1" if i == 0 else str(float(row["minimum"]) + 1)
    with demand.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    plain = load_package(EXAMPLES / "cenario2_retail")
    inst = load_package(package)
    assert inst.alpha == plain.alpha                      # the minimum, and so every solver, is untouched
    assert set(inst.ideal) == set(inst.alpha)
    assert all(inst.ideal[k] >= inst.alpha[k] for k in inst.alpha)
    assert sum(inst.ideal[k] - inst.alpha[k] for k in inst.alpha) > 0

    empty = evaluate(inst, rows_from_fixed(inst))         # shifts that cover no skill
    assert empty["total_shortage"] == empty["total_demand"]
    assert empty["ideal_shortage"] == empty["total_ideal"] == sum(inst.ideal.values())

    kpis = evaluate(inst, rows_from_fixed(inst, lambda eid, day, t: ("Team/T1",)))
    on_shift = Counter((day, t) for (eid, day), f in inst.fixed.items() if f.shift for t in f.shift.slot_indices)
    expected = sum(max(0, want - on_shift[(day, t)])
                   for (day, t, skill), want in inst.ideal.items() if skill == "Team/T1")
    assert kpis["ideal_shortage_by_skill"].get("Team/T1", 0) == expected
    assert kpis["ideal_shortage"] >= kpis["total_shortage"]
    assert kpis["objective"] == objective(kpis, SolveDirectives())   # ideal stays out of the objective
