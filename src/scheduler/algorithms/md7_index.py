"""The index sets of MathematicalDefinition7, built once from a V4Instance.

`ILP_Sisqual_Hours_MathematicalDefinition7` (PuLP) and
`CSP_Sisqual_Hours_MathematicalDefinition7` (CP-SAT) declare the same model
over the same sets. This module owns those sets - which x, y and z exist,
which constraints link them - and the rows a solution is reported as, so the
two solvers differ only in how they spell a variable and a constraint.

Symbols follow the PDF: x_wdh (worker w works shift h on day d), y_wdts (w
covers skill s in slot t of day d), z_dts (shortage), workday_wd.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List, Optional, Tuple

from problem_v4 import (
    UNASSIGNED,
    Shift,
    SolveDirectives,
    V4Instance,
    format_worked_cell,
    rest_cell,
)
from problem_v4.schema_core import MINUTES_PER_DAY

# (employee, day, slot, axis, skills on that axis, keys of the shifts covering the slot)
Link = Tuple[str, str, int, str, List[str], List[str]]


class MD7Index:
    def __init__(self, inst: V4Instance, directives: SolveDirectives):
        self.inst = inst
        self.directives = directives
        self.swap = directives.allow_day_off_swap
        law = inst.legislation

        # y_wdts exists where some candidate shift of (w, d) covers t, w holds s on
        # d, and alpha_dts > 0. Only the worker's own level l_ws is ever 1, so
        # constraint (6)'s y'_wdtsl is y_wdts itself: ObjectiveFunction2 weighs
        # y_wdts by p_{s, l_ws} directly instead of doubling the variables.
        self.y_level: Dict[Tuple[str, str, int, str], int] = {}
        self.links: List[Link] = []
        for employee in inst.employees:
            for day in inst.days:
                shifts = inst.candidates[(employee.id, day)]
                if not shifts:
                    continue
                covering: Dict[int, List[str]] = defaultdict(list)
                for shift in shifts:
                    for t in shift.slot_indices:
                        covering[t].append(shift.key)
                held = employee.skills[day]
                for t in sorted(covering):
                    per_axis: Dict[str, List[str]] = defaultdict(list)
                    for skill in inst.skills:
                        level = held.get(skill)
                        if level is not None and inst.alpha.get((day, t, skill), 0) > 0:
                            self.y_level[(employee.id, day, t, skill)] = level
                            per_axis[inst.skill_axis[skill]].append(skill)
                    for axis, skills in per_axis.items():
                        self.links.append((employee.id, day, t, axis, skills, covering[t]))

        self.coverage: Dict[Tuple[str, int, str], List[str]] = defaultdict(list)
        for (eid, day, t, skill) in self.y_level:
            self.coverage[(day, t, skill)].append(eid)

        # Shift pairs on consecutive days closer than the minimum rest.
        self.rest_pairs: List[Tuple[str, str, str, str, str]] = []
        if law.min_rest_minutes:
            for employee in inst.employees:
                for day, next_day in zip(inst.days, inst.days[1:]):
                    for a in inst.candidates[(employee.id, day)]:
                        for b in inst.candidates[(employee.id, next_day)]:
                            if MINUTES_PER_DAY - a.end_min + b.start_min < law.min_rest_minutes:
                                self.rest_pairs.append((employee.id, day, a.key, next_day, b.key))

        # Constraint (4): at most n worked days in any n + 1 consecutive days, and
        # at most `max_week_days` in any one week - a count per week, as the v4
        # validator reads MaxConsecutiveWorkDaysInWeek.
        self.run_windows: List[Tuple[str, int, List[str], int]] = []
        if law.max_consecutive is not None:
            n = law.max_consecutive
            for employee in inst.employees:
                for start in range(len(inst.days) - n):
                    self.run_windows.append((employee.id, start, inst.days[start:start + n + 1], n))
        self.week_caps: List[Tuple[str, int, List[str], int]] = []
        if law.max_week_days is not None:
            for employee in inst.employees:
                for index, week in enumerate(inst.weeks):
                    if len(week) > law.max_week_days:
                        self.week_caps.append((employee.id, index, week, law.max_week_days))

    # -- constraint (2) ------------------------------------------------------

    def day_rule(self, eid: str, day: str) -> Optional[int]:
        """The value workday_wd is fixed to, or None when the solver chooses it.

        A partial result's day wins; otherwise the cell decides. Without the
        swap directive a work cell must work and a DO rests.
        """
        key = (eid, day)
        if key in self.inst.fixed_workday:
            return self.inst.fixed_workday[key]
        mode = self.inst.day_modes[key]
        if mode == "unavailable":
            return 0
        if mode == "fixed_time_work":
            return 1
        if self.swap:
            return None
        return 1 if mode == "work_template" else 0

    def swap_weeks(self) -> List[Tuple[str, int, List[str], int]]:
        """Swap only: each week keeps its template count n_wk = |D_k| - |U_wk| - |D_wk|."""
        out = []
        for employee in self.inst.employees:
            for index, week in enumerate(self.inst.weeks):
                modes = [self.inst.day_modes[(employee.id, day)] for day in week]
                required = len(week) - modes.count("unavailable") - modes.count("preferred_day_off")
                out.append((employee.id, index, week, required))
        return out

    def day_off_days(self) -> List[Tuple[str, str]]:
        """ObjectiveFunction3's x'_wd: preferred day-offs the solver may work (swap only)."""
        if not self.swap:
            return []
        return [(e.id, d) for e in self.inst.employees for d in self.inst.days
                if self.inst.day_modes[(e.id, d)] == "preferred_day_off" and self.day_rule(e.id, d) is None]

    def priority_weight(self, eid: str, day: str, skill: str) -> int:
        """p_{s, l_ws}: the weight ObjectiveFunction2 puts on y_wdts."""
        return self.inst.priority_weight(skill, self.inst.level(eid, day, skill))

    # -- output -------------------------------------------------------------

    def output_rows(self, chosen: Callable[[str, str], Optional[Shift]],
                    covers: Callable[[str, str, int, str], bool]) -> List[List[str]]:
        """Rows from a solution: `chosen(e, d)` is the shift picked, `covers` reads y."""
        inst = self.inst
        rows = [["employee_id", *inst.days]]
        for employee in inst.employees:
            row = [employee.id]
            for day in inst.days:
                shift = chosen(employee.id, day)
                if shift is None:
                    if self.day_rule(employee.id, day) == 1:
                        row.append(UNASSIGNED)
                    elif inst.day_modes[(employee.id, day)] in {"work_template", "fixed_time_work"}:
                        row.append("OFF")       # a work cell the swap left off
                    else:
                        row.append(rest_cell(inst, employee.id, day))
                    continue
                slot_skills = {
                    t: [s for s in inst.skills
                        if (employee.id, day, t, s) in self.y_level and covers(employee.id, day, t, s)]
                    for t in shift.slot_indices
                }
                row.append(format_worked_cell(shift, slot_skills, inst.slot_minutes))
            rows.append(row)
        return rows
