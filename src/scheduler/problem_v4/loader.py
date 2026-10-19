"""`load_package`: one schema v4 package folder in, one `V4Instance` out.

This is the only place v4 is interpreted. The readers are the vendored
`schema_core` (byte-identical to json_generation/schema_v4/src/schema_v4/core.py),
so a cell, a window or a fixed day means here exactly what it means to the
validator. Anything a solver could not use is collected and raised together as
a `ParseError`, rather than surfacing later as an infeasible model.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from . import schema_core as core
from .directives import SolveDirectives
from .instance import (
    Employee,
    Legislation,
    ParseError,
    Shift,
    TimeSlot,
    V4Instance,
    make_shift,
)
from .partial import apply_partial_result, check_labour_law

GRAIN_KEYS = (("days", "dataFileDays"), ("periods", "dataFilePeriods"), ("shifts", "dataFileShifts"))

#: Codes minted for shifts synthesised when a problem carries no menu.
SYNTHESISED_CODE_BASE = 10000


# --------------------------------------------------------------------------
# package discovery
# --------------------------------------------------------------------------

def locate_package(path) -> Tuple[Path, dict, Optional[Path], Optional[dict]]:
    """(problem path, problem, result path, result) - documents found by content.

    The same rule as the validator's `validate_package`: a problem carries
    `"form": "input"`, a result carries `OutRosterTeamDays`, a folder holds
    exactly one problem and at most one result.
    """
    given = Path(path)
    folder = given if given.is_dir() else given.parent
    if not folder.is_dir():
        raise ParseError([f"{path}: no such package folder"])

    problems, results, unreadable = [], [], []
    for candidate in sorted(folder.glob("*.json")):
        try:
            doc = json.loads(candidate.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError) as exc:
            unreadable.append(f"{candidate.name}: not readable JSON ({exc})")
            continue
        if not isinstance(doc, dict):
            continue
        if doc.get("form") == "input":
            problems.append((candidate, doc))
        elif "OutRosterTeamDays" in doc:
            results.append((candidate, doc))

    errors = list(unreadable)
    if given.is_file() and given.resolve() not in {p.resolve() for p, _ in problems}:
        errors.append(f"{given.name} is not a v4 input problem (form != 'input')")
    if len(problems) != 1:
        errors.append(f"{folder}: a package holds exactly one problem, found {len(problems)}")
    if len(results) > 1:
        errors.append(f"{folder}: a package holds at most one result, found {len(results)}")
    if errors:
        raise ParseError(errors)

    problem_path, problem = problems[0]
    result_path, result = results[0] if results else (None, None)
    return problem_path, problem, result_path, result


# --------------------------------------------------------------------------
# the parser
# --------------------------------------------------------------------------

def load_package(path, directives: Optional[SolveDirectives] = None) -> V4Instance:
    """Read and interpret a v4 package. Raises `ParseError` listing every problem."""
    directives = directives or SolveDirectives()
    problem_path, problem, result_path, result = locate_package(path)
    base = problem_path.parent
    errors: List[str] = []
    warnings: List[str] = []

    if str(problem.get("schemaVersion")) != "4.0":
        errors.append(f"schemaVersion is {problem.get('schemaVersion')!r}; this parser reads 4.0 only")
    dates = core.horizon(problem)
    slot = problem.get("timeGrid", {}).get("slotMinutes")
    if not dates:
        errors.append("temporalScope has no usable start/end")
    if not isinstance(slot, int) or slot <= 0 or core.MINUTES_PER_DAY % slot:
        errors.append(f"timeGrid.slotMinutes {slot!r} must be a positive divisor of 1440")
    if errors:
        raise ParseError(errors)
    days = [d.isoformat() for d in dates]

    # Everything the validator calls impossible about a cell, from its single source.
    errors.extend(str(diag) for diag in core.scan_feasibility(problem, base))

    skills, skill_axis, axes = _read_axes(problem)
    alpha, open_days = _read_demand(problem, base, days, slot, skill_axis, errors, warnings)
    employees = _read_employees(problem, days, dates, skills, skill_axis, errors, warnings)
    cells = _read_cells(problem, base, days, employees, errors, warnings)
    if errors:
        raise ParseError(errors)

    menu, synthesised = _read_menu(problem, base, days, employees, cells, alpha, slot, directives, errors)
    candidates, day_modes = _build_candidates(
        days, employees, cells, menu, slot, directives, synthesised, errors
    )
    weeks = _group_weeks(problem, days, dates, errors)
    if errors:
        raise ParseError(errors)

    limits = core.legislation_limits(problem)
    inst = V4Instance(
        problem_path=problem_path,
        problem=problem,
        problem_id=str(problem.get("metadata", {}).get("problemId", "")),
        roster_code=str(problem.get("metadata", {}).get("rosterCode", "")),
        slot_minutes=slot,
        days=days,
        weeks=weeks,
        holidays={
            str(h.get("date")): str(h.get("code", ""))
            for h in problem.get("calendar", {}).get("holidays", [])
        },
        axes=axes,
        skills=skills,
        skill_axis=skill_axis,
        time_slots=[],
        alpha=alpha,
        open_days=[d for d in days if d in open_days],
        closed_days={d for d in days if d not in open_days},
        employees=employees,
        cells=cells,
        menu=dict(menu),
        menu_synthesised=synthesised,
        candidates=candidates,
        day_modes=day_modes,
        legislation=Legislation(
            max_consecutive=limits.get("MaxConsecutiveWorkDays"),
            max_week_days=limits.get("MaxConsecutiveWorkDaysInWeek"),
            min_rest_minutes=limits.get("MinDistanceBetweenShiftsInMinutes"),
        ),
        priority_tiers=_read_priority_tiers(problem),
        warnings=warnings,
    )

    if result is not None:
        apply_partial_result(inst, result_path, result)
    check_labour_law(inst)
    inst.time_slots = _build_time_slots(inst)
    inst.warnings.extend(directives.warnings(_max_priority_weight(inst)))
    return inst


# --------------------------------------------------------------------------
# sections
# --------------------------------------------------------------------------

def _read_axes(problem: dict) -> Tuple[List[str], Dict[str, str], Dict[str, Tuple[str, ...]]]:
    """Skills ("tableName/tableValue") grouped by axis, in declaration order."""
    by_axis: Dict[str, List[str]] = {}
    for dim in problem.get("demand", {}).get("dimensions", []):
        name = str(dim.get("tableName", "")).strip()
        value = str(dim.get("tableValue", "")).strip()
        if name and value and value not in by_axis.setdefault(name, []):
            by_axis[name].append(value)
    skills = [f"{name}/{value}" for name, values in by_axis.items() for value in values]
    skill_axis = {f"{name}/{value}": name for name, values in by_axis.items() for value in values}
    return skills, skill_axis, {name: tuple(values) for name, values in by_axis.items()}


def _read_demand(problem, base, days, slot, skill_axis, errors, warnings):
    """alpha_dts from the periods grain (the shifts grain where periods is silent).

    Overlapping windows of one pair take the max: each row states the headcount
    wanted during its window, not an increment. Headcount is rounded up, since
    CP-SAT needs integers and 4.5 workers can only be met by 5.
    """
    demand = problem.get("demand", {})
    horizon = set(days)
    by_grain: Dict[str, Dict[Tuple[str, str], list]] = {}
    open_days = set()

    for grain, key in GRAIN_KEYS:
        name = demand.get(key)
        path = base / str(name or "")
        if not name or not path.is_file():
            errors.append(f"demand.{key}: {name!r} not found next to problem.json")
            continue
        _, rows, problems = core.read_demand(path, grain)
        errors.extend(f"{name}: {p}" for p in problems)
        per: Dict[Tuple[str, str], list] = defaultdict(list)
        for row in rows:
            day = row.date.isoformat()
            skill = f"{row.table_name}/{row.table_value}"
            if day not in horizon:
                errors.append(f"{name} line {row.line}: {day} is outside temporalScope")
                continue
            if skill not in skill_axis:
                errors.append(f"{name} line {row.line}: ({row.table_name}, {row.table_value}) "
                              "is not declared in demand.dimensions")
                continue
            if grain == "days":
                per[(day, skill)].append((None, row.minimum))
                continue
            if row.window is None:
                errors.append(f"{name} line {row.line}: the {grain} grain needs a start-end window")
                continue
            open_days.add(day)
            per[(day, skill)].append((row.window, row.minimum))
        by_grain[grain] = per

    if by_grain.get("days"):
        warnings.append("days_demand.csv carries workload rows; no solver reads the days grain yet "
                        "(FUTURE.md section 4), so they are ignored")
    periods = by_grain.get("periods", {})
    shifts = by_grain.get("shifts", {})
    both = set(periods) & set(shifts)
    if both:
        warnings.append(f"{len(both)} (date, pair) coordinate(s) have rows on both the periods and "
                        "the shifts grain; the periods rows are used")

    alpha: Dict[Tuple[str, int, str], int] = {}
    chosen = list(periods.items()) + [(k, v) for k, v in shifts.items() if k not in periods]
    for (day, skill), entries in chosen:
        for window, minimum in entries:
            need = math.ceil(round(minimum, 6)) if minimum > 0 else 0
            if need <= 0:
                continue    # 0 means "unset" (FORMAT.md), not "zero workers"
            for t in range(window.start // slot, -(-window.end // slot)):
                key = (day, t, skill)
                alpha[key] = max(alpha.get(key, 0), need)
    return alpha, open_days


def _read_employees(problem, days, dates, skills, skill_axis, errors, warnings) -> List[Employee]:
    contracts = core.contracts_by_id(problem)
    employees: List[Employee] = []
    seen = set()
    undeclared = set()
    for raw in problem.get("employees", {}).get("list", []):
        eid = str(raw.get("id", "")).strip()
        if not eid or eid in seen:
            errors.append(f"employee id {eid!r} is empty or repeated")
            continue
        seen.add(eid)
        contract_minutes: Dict[str, Optional[int]] = {}
        held: Dict[str, Dict[str, int]] = {}
        for day, dt in zip(days, dates):
            contract = contracts.get(core.active_contract(raw, dt) or "")
            contract_minutes[day] = contract.get("workMinutesPerDay") if contract else None
            levels: Dict[str, int] = {}
            for comp in core.active_competencies(raw, dt):
                skill = f"{str(comp.get('tableName', '')).strip()}/{str(comp.get('tableValue', '')).strip()}"
                if skill not in skill_axis:
                    undeclared.add(skill)
                    continue
                level = comp.get("level")
                if not isinstance(level, int) or level < 1:
                    errors.append(f"employee {eid}: competency {skill} has level {level!r}")
                    continue
                # The same pair twice at two levels: take the higher competence (FORMAT.md).
                levels[skill] = min(levels.get(skill, level), level)
            held[day] = levels
        all_skills = tuple(s for s in skills if any(s in held[d] for d in days))
        employees.append(Employee(eid, str(raw.get("name") or eid), contract_minutes, held, all_skills))
    if undeclared:
        warnings.append(f"competencies on undeclared pairs are ignored: {', '.join(sorted(undeclared))}")
    if not employees:
        errors.append("employees.list is empty")
    return employees


def _read_cells(problem, base, days, employees, errors, warnings):
    section = problem.get("scheduleInput", {})
    name = section.get("dataFile")
    path = base / str(name or "")
    if not name or not path.is_file():
        errors.append(f"scheduleInput.dataFile: {name!r} not found next to problem.json")
        return {}
    rows, date_cols, problems = core.read_schedule_input(path)
    errors.extend(f"{name}: {p}" for p in problems)
    if list(date_cols) != days:
        errors.append(f"{name}: the date columns must be exactly the temporalScope days "
                      f"({days[0]}..{days[-1]})")
        return {}
    known = {e.id for e in employees}
    stray = sorted(set(rows) - known)
    if stray:
        warnings.append(f"{name}: rows for unknown employees are ignored: {', '.join(stray)}")

    cells = {}
    for employee in employees:
        row = rows.get(employee.id)
        if row is None:
            errors.append(f"employee {employee.id} has no row in {name}")
            continue
        for day in days:
            raw = row.get(day, "")
            try:
                cells[(employee.id, day)] = core.classify_cell(raw, problem)
            except core.DomainError as exc:
                # Same wording as scan_feasibility, so ParseError de-duplicates it.
                errors.append(str(core.Diagnostic(employee.id, day, raw, str(exc))))
    return cells


def _usable(schedule: core.Schedule, slot: int) -> bool:
    """A menu row a working day can pick: a real window, on the grid."""
    iv = schedule.interval
    return (iv is not None and not schedule.is_sentinel and schedule.weight_minutes > 0
            and core.on_grid(iv.start, slot) and core.on_grid(iv.end, slot))


def _read_menu(problem, base, days, employees, cells, alpha, slot, directives, errors):
    """(menu, synthesised). Without a menu, blocks are synthesised on the grid."""
    section = problem.get("schedules")
    if section is not None:
        name = section.get("dataFile")
        path = base / str(name or "")
        if not name or not path.is_file():
            errors.append(f"schedules.dataFile: {name!r} not found next to problem.json")
            return {}, False
        menu, problems = core.read_schedules(path)
        errors.extend(f"{name}: {p}" for p in problems)
        return menu, False

    # No menu: every length some cell asks for, at every grid start inside the
    # span demand and the cells' own windows cover (MD7's old block
    # enumeration, generalised to slotMinutes), plus each EQUALS window as-is.
    lengths, exact, bounds = set(), set(), []
    for (_, t, _) in alpha:
        bounds.extend([t * slot, (t + 1) * slot])
    for employee in employees:
        for day in days:
            rule = cells[(employee.id, day)]
            minutes = employee.contract_minutes[day]
            bounds.extend(b for w in rule.windows for b in (w.start, w.end))
            if rule.kind in core.ASKS_FOR_WORK:
                if rule.kind == "equals" and len(rule.windows) == 1:
                    exact.add(rule.windows[0])
                wanted = core.required_minutes(rule, minutes)
                if wanted:
                    lengths.add(wanted)
            elif rule.kind == "dayoff" and rule.day_off == "preferable" and directives.allow_day_off_swap and minutes:
                lengths.add(minutes)
    lo, hi = (min(bounds), max(bounds)) if bounds else (0, core.MINUTES_PER_DAY)
    lo -= lo % slot
    intervals = set(exact)
    for length in lengths:
        intervals.update(core.Interval(s, s + length) for s in range(lo, hi - length + 1, slot))
    menu = {}
    for i, iv in enumerate(sorted(intervals)):
        code = SYNTHESISED_CODE_BASE + i
        menu[code] = core.Schedule(code, str(iv), iv.length, iv)
    return menu, True


def _build_candidates(days, employees, cells, menu, slot, directives, synthesised, errors):
    """H_wd for every employee-day, and its day mode - both from the cell alone.

    `cell_conflict` is the validator's own test for a fixed day, so a candidate
    is exactly a shift the validator would accept on that day. It is too loose
    on its own (no interval, a sentinel, any length on a DO), hence `_usable`
    first and the contract length for a swappable DO.
    """
    shifts = sorted((s for s in menu.values() if _usable(s, slot)),
                    key=lambda s: (s.interval.start, s.interval.end, s.code))
    source = "synthesised block" if synthesised else "menu shift"
    candidates: Dict[Tuple[str, str], List[Shift]] = {}
    day_modes: Dict[Tuple[str, str], str] = {}

    for employee in employees:
        for day in days:
            key = (employee.id, day)
            rule = cells[key]
            minutes = employee.contract_minutes[day]
            legal: List[core.Schedule] = []
            if rule.kind == "empty" or (rule.kind == "dayoff" and rule.day_off == "unavailable"):
                mode = "unavailable"
            elif rule.kind == "dayoff":
                mode = "preferred_day_off"
                if directives.allow_day_off_swap and minutes:
                    auto = core.CellRule("auto")
                    legal = [s for s in shifts if core.cell_conflict(auto, s, minutes) is None]
            else:
                if rule.kind == "equals" and len(rule.windows) > 1:
                    errors.append(f"{employee.id} on {day}: cell {rule.raw!r} is a split shift, "
                                  "which no single ScheduleCode can express (no break model yet)")
                    candidates[key], day_modes[key] = [], "fixed_time_work"
                    continue
                mode = "fixed_time_work" if rule.kind == "equals" else "work_template"
                legal = [s for s in shifts if core.cell_conflict(rule, s, minutes) is None]
                if not legal:
                    errors.append(f"{employee.id} on {day}: cell {rule.raw!r} asks for work, "
                                  f"but no {source} satisfies it")
            candidates[key] = [make_shift(employee.id, day, s, slot) for s in legal]
            day_modes[key] = mode
    return candidates, day_modes


def _group_weeks(problem, days, dates, errors) -> List[List[str]]:
    week_start = problem.get("calendar", {}).get("weekStart", "monday")
    groups: Dict[int, List[str]] = defaultdict(list)
    try:
        for day, dt in zip(days, dates):
            groups[core.week_index(dt, dates[0], week_start)].append(day)
    except core.DomainError as exc:
        errors.append(f"calendar.weekStart: {exc}")
        return []
    return [groups[k] for k in sorted(groups)]


def _read_priority_tiers(problem) -> List[dict]:
    """priorityHierarchy ordered by rank; a tier's priority is its position (1 = first)."""
    ordered = sorted(problem.get("priorityHierarchy", []), key=lambda h: h.get("rank", 10 ** 6))
    tiers = []
    for position, entry in enumerate(ordered, start=1):
        skill = f"{str(entry.get('tableName', '')).strip()}/{str(entry.get('tableValue', '')).strip()}"
        max_level = entry.get("maxAbilityLevel")
        tiers.append({
            "priority": position,
            "skill": skill,
            "min_n": int(entry.get("minAbilityLevel") or 1),
            "max_n": int(max_level) if max_level is not None else None,
            "label": str(entry.get("label") or skill),
        })
    return tiers


def _build_time_slots(inst: V4Instance) -> List[TimeSlot]:
    """The absolute grid, long enough for every demanded slot and every shift."""
    last = 0
    for (_, t, _) in inst.alpha:
        last = max(last, t + 1)
    for shifts in inst.candidates.values():
        for shift in shifts:
            last = max(last, shift.slot_indices[-1] + 1 if shift.slot_indices else 0)
    slot = inst.slot_minutes
    return [TimeSlot(i, i * slot, (i + 1) * slot) for i in range(last)]


def _max_priority_weight(inst: V4Instance) -> int:
    worst = 1
    for employee in inst.employees:
        for day in inst.days:
            for skill, level in employee.skills[day].items():
                worst = max(worst, inst.priority_weight(skill, level))
    return worst
