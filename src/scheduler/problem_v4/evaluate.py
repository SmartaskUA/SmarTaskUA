"""One yardstick for every algorithm: score schedule rows against the instance.

The terms are MathematicalDefinition7's objective, recomputed from the rows a
solver returns rather than from its variables, so an ILP, a CP-SAT model, a
heuristic and a GA are compared on exactly the same numbers.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, List

from .directives import SolveDirectives
from .instance import V4Instance
from .rows import UNASSIGNED, parse_worked_cell


def evaluate(inst: V4Instance, rows: List[List[str]]) -> Dict:
    """KPIs of a schedule.

    - total_shortage: sum over alpha of max(0, alpha_dts - covered)   [ObjectiveFunction1]
    - priority_cost:  sum of p_sl over demanded (day, slot, skill) worked [ObjectiveFunction2]
    - day_off_worked: preferred day-offs carrying a shift             [ObjectiveFunction3]
    - unassigned:     work days left without a shift (an invalid result)
    - foreign_skill_slots: slots credited to a skill the worker does not hold
    """
    days = [str(d) for d in rows[0][1:]]
    if days != inst.days:
        raise ValueError("the rows' header does not match the instance's days")
    slot = inst.slot_minutes
    cover: Dict[tuple, int] = defaultdict(int)
    priority_cost = 0
    day_off_worked = 0
    foreign = 0
    unassigned = []

    for row in rows[1:]:
        eid = str(row[0])
        for day, cell in zip(days, row[1:]):
            segments = parse_worked_cell(cell)
            if segments is None:
                if cell == UNASSIGNED or inst.is_work_day(eid, day):
                    unassigned.append((eid, day))
                continue
            if inst.day_modes[(eid, day)] == "preferred_day_off":
                day_off_worked += 1
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
    for key, need in inst.alpha.items():
        missing = need - cover.get(key, 0)
        if missing > 0:
            shortage_by_skill[key[2]] += missing
    return {
        "total_shortage": sum(shortage_by_skill.values()),
        "shortage_by_skill": dict(sorted(shortage_by_skill.items())),
        "total_demand": sum(inst.alpha.values()),
        "priority_cost": priority_cost,
        "day_off_worked": day_off_worked,
        "unassigned": len(unassigned),
        "unassigned_days": unassigned,
        "foreign_skill_slots": foreign,
    }


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
