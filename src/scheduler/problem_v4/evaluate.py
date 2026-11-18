"""One yardstick for every algorithm: score schedule rows against the instance.

The terms are MathematicalDefinition7's objective, recomputed from the rows a
solver returns rather than from its variables, so an ILP, a CP-SAT model, a
heuristic and a GA are compared on exactly the same numbers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from .directives import SolveDirectives
from .instance import V4Instance
from .rows import UNASSIGNED, parse_worked_cell


def evaluate(inst: V4Instance, rows: List[List[str]],
             directives: Optional[SolveDirectives] = None) -> Dict:
    """KPIs of a schedule.

    Objective terms (MathematicalDefinition7):
    - total_shortage: sum over alpha of max(0, alpha_dts - covered)   [ObjectiveFunction1]
    - priority_cost:  sum of p_sl over demanded (day, slot, skill) worked [ObjectiveFunction2]
    - day_off_worked: preferred day-offs the solver chose to work      [ObjectiveFunction3]
    - objective:      w1, w2, w3 applied to the three above (`directives`, default weights)

    Context and quality:
    - total_demand:   sum of alpha (headcount rounded up by the loader)
    - total_surplus:  sum over alpha of max(0, covered - alpha_dts) - workers beyond the need
    - day_off_worked_fixed: preferred day-offs worked because a partial result fixed them;
      not the solver's choice, so outside ObjectiveFunction3
    - ideal_shortage: sum over the ideal targets of max(0, ideal_dts - covered); not in the
      objective, so no solver aims at it. total_ideal is the sum of those targets.

    Validity (all 0 for a valid result):
    - unassigned:     work days without a shift, employees missing from the rows included
    - missing_rows:   employees with no row (each counts every work day as unassigned)
    - work_on_unavailable: shifts on a day the cell marks unavailable
    - foreign_skill_slots: slots credited to a skill the worker does not hold
    """
    days = [str(d) for d in rows[0][1:]]
    if days != inst.days:
        raise ValueError("the rows' header does not match the instance's days")
    slot = inst.slot_minutes
    cover: Dict[tuple, int] = defaultdict(int)
    priority_cost = 0
    day_off_worked = 0
    day_off_worked_fixed = 0
    work_on_unavailable = 0
    foreign = 0
    unassigned = []

    by_id: Dict[str, List[str]] = {}
    for row in rows[1:]:
        by_id.setdefault(str(row[0]), row)     # a repeated row is read once
    missing = [e.id for e in inst.employees if e.id not in by_id]
    for eid in missing:
        unassigned.extend((eid, day) for day in days if inst.is_work_day(eid, day))

    for employee in inst.employees:
        eid = employee.id
        row = by_id.get(eid)
        if row is None:
            continue
        for day, cell in zip(days, row[1:]):
            segments = parse_worked_cell(cell)
            if segments is None:
                if cell == UNASSIGNED or inst.is_work_day(eid, day):
                    unassigned.append((eid, day))
                continue
            mode = inst.day_modes[(eid, day)]
            if mode == "preferred_day_off":
                if (eid, day) in inst.fixed:
                    day_off_worked_fixed += 1
                else:
                    day_off_worked += 1
            elif mode == "unavailable" and (eid, day) not in inst.fixed:
                work_on_unavailable += 1
            for start, end, skills in segments:
                for t in range(start // slot, end // slot):
                    for skill in skills:
                        level = inst.level(eid, day, skill)
                        if level is None:
                            foreign += 1
                            continue
                        cover[(day, t, skill)] += 1
                        if inst.alpha.get((day, t, skill), 0) > 0:
                            priority_cost += inst.priority_weight(skill, level)

    shortage_by_skill: Dict[str, int] = defaultdict(int)
    surplus_by_skill: Dict[str, int] = defaultdict(int)
    for key, need in inst.alpha.items():
        gap = need - cover.get(key, 0)
        if gap > 0:
            shortage_by_skill[key[2]] += gap
        elif gap < 0:
            surplus_by_skill[key[2]] -= gap
    ideal_shortage_by_skill: Dict[str, int] = defaultdict(int)
    for key, want in inst.ideal.items():
        gap = want - cover.get(key, 0)
        if gap > 0:
            ideal_shortage_by_skill[key[2]] += gap
    kpis = {
        "total_shortage": sum(shortage_by_skill.values()),
        "shortage_by_skill": dict(sorted(shortage_by_skill.items())),
        "total_demand": sum(inst.alpha.values()),
        "total_surplus": sum(surplus_by_skill.values()),
        "surplus_by_skill": dict(sorted(surplus_by_skill.items())),
        "total_ideal": sum(inst.ideal.values()),
        "ideal_shortage": sum(ideal_shortage_by_skill.values()),
        "ideal_shortage_by_skill": dict(sorted(ideal_shortage_by_skill.items())),
        "priority_cost": priority_cost,
        "day_off_worked": day_off_worked,
        "day_off_worked_fixed": day_off_worked_fixed,
        "unassigned": len(unassigned),
        "unassigned_days": unassigned,
        "missing_rows": len(missing),
        "work_on_unavailable": work_on_unavailable,
        "foreign_skill_slots": foreign,
    }
    kpis["objective"] = objective(kpis, directives or SolveDirectives())
    return kpis


def fixed_days(inst: V4Instance) -> Dict:
    """What a partial result decided: its fixed employee-days, sorted, and how many it left open.

    Stored with a solved schedule, so the calendar can mark the days the solver did not choose.
    Without a result, `fixed` is empty and every day is open.
    """
    return {
        "fixed": sorted([eid, day] for eid, day in inst.fixed),
        "open_days": len(inst.open_cells),
    }


def objective(kpis: Dict, directives: SolveDirectives) -> int:
    """MathematicalDefinition7's weighted objective from `evaluate`'s KPIs."""
    return (directives.w1 * kpis["total_shortage"]
            + directives.w2 * kpis["priority_cost"]
            + directives.w3 * kpis["day_off_worked"])
