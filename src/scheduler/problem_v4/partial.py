"""Partial resolution: a result's entries become fixed days on the instance.

A result may leave employee-days out (FORMAT.md, "Partial results"). What it
carries is fixed and what it omits is open, and nothing marks it as partial. A
fixed day is applied as a domain restriction - its candidate set shrinks to the
one shift it names, or to nothing for a rest - so every solver honours it
through the candidate set it already chooses from, and the labour-law rules
across a fixed/open boundary stay ordinary constraints.

Everything a partial result could get wrong is checked here, before any solver
runs, so a contradiction is reported with coordinates instead of as a bare
"Infeasible".
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Tuple

from . import schema_core as core
from .instance import WORK_MODES, FixedDay, ParseError, V4Instance, make_shift

#: A result at result.json names its shifts in result_schedules.csv.
SIDECAR_SUFFIX = "_schedules.csv"


def apply_partial_result(inst: V4Instance, result_path: Path, result: dict) -> None:
    """Read `result` into `inst.fixed` and restrict the candidate sets. Raises ParseError."""
    errors: List[str] = []
    defined: Dict[int, core.Schedule] = dict(inst.menu)
    sidecar = result_path.parent / (result_path.stem + SIDECAR_SUFFIX)
    if sidecar.is_file():
        side, problems = core.read_schedules(sidecar)
        errors.extend(f"{sidecar.name}: {p}" for p in problems)
        defined.update(side)    # the sidecar defines the codes this result used
    else:
        inst.warnings.append(f"{result_path.name} has no {sidecar.name}; its codes resolve against the menu")

    entries = result.get("OutRosterTeamDays")
    if not isinstance(entries, list):
        raise ParseError([f"{result_path.name}: OutRosterTeamDays is not a list"])

    days = set(inst.days)
    fixed: Dict[Tuple[str, str], FixedDay] = {}
    for n, entry in enumerate(entries):
        where = f"{result_path.name} OutRosterTeamDays[{n}]"
        if inst.roster_code and entry.get("RosterCode") != inst.roster_code:
            errors.append(f"{where}: RosterCode {entry.get('RosterCode')!r} is not "
                          f"metadata.rosterCode {inst.roster_code!r}")
        eid = str(entry.get("EmployeeCode", "")).strip()
        date = core.iso(entry.get("Date"))
        day = date.isoformat() if date else None
        code = entry.get("ScheduleCode")
        if not any(e.id == eid for e in inst.employees):
            errors.append(f"{where}: EmployeeCode {eid!r} is not an employee")
            continue
        if day not in days:
            errors.append(f"{where}: Date {entry.get('Date')!r} is outside temporalScope")
            continue
        if (eid, day) in fixed:
            errors.append(f"{where}: {eid} on {day} is fixed twice")
            continue
        if isinstance(code, bool) or not isinstance(code, int) or code not in defined:
            errors.append(f"{where}: ScheduleCode {code!r} is defined by neither the sidecar nor the menu")
            continue

        schedule = defined[code]
        if schedule.is_sentinel:
            shift = None
        elif schedule.interval is None:
            errors.append(f"{where}: code {code} has no start/end, so the fixed day's times are unknown")
            continue
        elif not (core.on_grid(schedule.interval.start, inst.slot_minutes)
                  and core.on_grid(schedule.interval.end, inst.slot_minutes)):
            errors.append(f"{where}: code {code} ({schedule.interval}) is off the "
                          f"{inst.slot_minutes}-minute grid")
            continue
        else:
            shift = make_shift(eid, day, schedule, inst.slot_minutes)

        # The validator's own rule for a fixed day against its cell.
        reason = core.cell_conflict(inst.cells[(eid, day)], schedule,
                                    inst.employee(eid).contract_minutes[day])
        if reason:
            errors.append(f"{where}: {eid} on {day} is fixed to code {code}, but {reason}")
            continue
        fixed[(eid, day)] = FixedDay(code, shift)

    if errors:
        raise ParseError(errors)

    inst.menu = defined
    inst.fixed = fixed
    for key, fixed_day in fixed.items():
        inst.candidates[key] = [fixed_day.shift] if fixed_day.shift else []
        inst.fixed_workday[key] = 1 if fixed_day.shift else 0
    _prune_rest_next_to_fixed(inst)


def _prune_rest_next_to_fixed(inst: V4Instance) -> None:
    """Drop open-day shifts that break the minimum rest against a fixed neighbour.

    The parser owns this so no solver ever tries a shift that is already
    impossible. A working day left with nothing is a contradiction in the input.
    """
    min_rest = inst.legislation.min_rest_minutes
    if not min_rest:
        return
    errors: List[str] = []
    position = {day: i for i, day in enumerate(inst.days)}
    for (eid, day), fixed_day in inst.fixed.items():
        if fixed_day.shift is None:
            continue
        i = position[day]
        for j, neighbour_is_before in ((i - 1, True), (i + 1, False)):
            if not 0 <= j < len(inst.days):
                continue
            key = (eid, inst.days[j])
            if key in inst.fixed:
                continue
            if neighbour_is_before:
                keep = [c for c in inst.candidates[key]
                        if core.MINUTES_PER_DAY - c.end_min + fixed_day.shift.start_min >= min_rest]
            else:
                keep = [c for c in inst.candidates[key]
                        if core.MINUTES_PER_DAY - fixed_day.shift.end_min + c.start_min >= min_rest]
            if len(keep) == len(inst.candidates[key]):
                continue
            inst.candidates[key] = keep
            if not keep and inst.day_modes[key] in WORK_MODES:
                errors.append(f"{eid} on {key[1]}: every shift its cell allows breaks the "
                              f"{min_rest}-minute rest against the fixed {fixed_day.shift.label} on {day}")
    if errors:
        raise ParseError(errors)


def check_labour_law(inst: V4Instance) -> None:
    """Fail fast when the days that must be worked already break the roster's law.

    A must-work day is a fixed worked day or an open work cell (the cell alone
    decides work vs rest in v4). Unlike the validator's check of a result on its
    own - where an open day breaks a run because the solver may yet rest it - an
    open work cell here is certainly worked, so it counts.
    """
    law = inst.legislation
    errors: List[str] = []
    for employee in inst.employees:
        worked = [inst.is_work_day(employee.id, day) for day in inst.days]

        if law.max_consecutive is not None:
            run = 0
            for day, is_worked in zip(inst.days, worked):
                run = run + 1 if is_worked else 0
                if run > law.max_consecutive:
                    errors.append(f"{employee.id}: must work {run} days in a row ending {day}, above "
                                  f"MaxConsecutiveWorkDays of {law.max_consecutive}")
                    break

        if law.max_week_days is not None:
            position = {day: i for i, day in enumerate(inst.days)}
            for week in inst.weeks:
                count = sum(worked[position[day]] for day in week)
                if count > law.max_week_days:
                    errors.append(f"{employee.id}: must work {count} days in the week of {week[0]}, above "
                                  f"MaxConsecutiveWorkDaysInWeek of {law.max_week_days}")

        if law.min_rest_minutes is not None:
            for day, next_day in zip(inst.days, inst.days[1:]):
                before = _determined_shift(inst, employee.id, day)
                after = _determined_shift(inst, employee.id, next_day)
                if before is None or after is None:
                    continue
                rest = core.MINUTES_PER_DAY - before.end_min + after.start_min
                if rest < law.min_rest_minutes:
                    errors.append(f"{employee.id}: {rest} min of rest between {before.label} on {day} and "
                                  f"{after.label} on {next_day}, below MinDistanceBetweenShiftsInMinutes "
                                  f"of {law.min_rest_minutes}")
    if errors:
        raise ParseError(errors)


def _determined_shift(inst: V4Instance, eid: str, day: str):
    """The shift a day will certainly carry - fixed, or an EQUALS cell's only option."""
    fixed_day = inst.fixed.get((eid, day))
    if fixed_day is not None:
        return fixed_day.shift
    options = inst.candidates[(eid, day)]
    if inst.day_modes[(eid, day)] == "fixed_time_work" and len(options) == 1:
        return options[0]
    return None
