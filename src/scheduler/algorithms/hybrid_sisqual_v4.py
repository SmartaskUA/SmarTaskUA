"""The greedy block assignment both Hybrid Sisqual heuristics share, on a V4Instance.

`Hybrid_Heuristic_Sisqual_Levels_Included.py` and
`Hybrid_Heuristic_Sisqual_No_Levels_Included.py` differ only in how a skill is
picked for a slot and how a candidate block is ranked; everything else - the
day order, the employee order, the rest check, fixed days, output - is here, so
the two cannot drift apart on what the problem means.

v4 changes to the original heuristic:
  - candidates, day modes and fixed days come from `problem_v4.load_package`;
  - a partial result's days are seeded before the greedy starts, so the rest
    check sees them as neighbours on both sides and the loop never touches them;
  - skills are chosen per axis: a worker covers one demanded value on every axis
    it holds one on (Team/T1 and Responsibility/A in the same slot);
  - a work day whose every block breaks the rest against its neighbours first
    tries re-picking a neighbour's block, instead of going straight to UNASSIGNED.
"""

from __future__ import annotations

import csv
import random
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from problem_v4 import (
    UNASSIGNED,
    Employee,
    Shift,
    SolveDirectives,
    V4Instance,
    format_worked_cell,
    rest_cell,
)
from problem_v4.schema_core import MINUTES_PER_DAY

SkillChoice = Dict[int, Dict[str, str]]     # slot -> {axis: skill}


class HybridSisqualV4:
    def __init__(self, inst: V4Instance, directives: Optional[SolveDirectives] = None, max_time_minutes=None):
        self.inst = inst
        self.directives = directives or SolveDirectives()
        self.max_time_minutes = max_time_minutes
        self.days = inst.days
        self.employees = inst.employees
        self.employees_by_id = {e.id: e for e in inst.employees}
        self.skills = inst.skills
        self.alpha = inst.alpha
        self.assignments = inst.candidates
        self.day_modes = inst.day_modes
        self.min_rest = inst.legislation.min_rest_minutes
        self.day_position = {day: i for i, day in enumerate(inst.days)}
        # How many workers hold each skill at all: scarcer skills win ties.
        self.skill_employee_count = {
            skill: sum(1 for e in inst.employees if skill in e.all_skills) for skill in inst.skills
        }
        self.reset()

    def reset(self) -> None:
        """Clear the greedy state so one parsed instance serves every restart."""
        self.cover: Dict[Tuple[str, int, str], int] = defaultdict(int)
        # chosen block per (employee, day) -> Shift | None
        self.employee_day_block: Dict[Tuple[str, str], Optional[Shift]] = {}
        # skill worked per (employee, day, slot) -> {axis: skill}
        self.slot_skill: Dict[Tuple[str, str, int], Dict[str, str]] = {}
        # work days left with no feasible block
        self.unassigned: List[Tuple[str, str]] = []

    # ------------------------------------------------------------------
    # skill choice - the two variants override `choose_skill` / `rank_block`
    # ------------------------------------------------------------------

    def remaining(self, day: str, slot_idx: int, skill: str) -> int:
        """Minimum still uncovered for (day, slot, skill)."""
        return max(0, self.alpha.get((day, slot_idx, skill), 0) - self.cover[(day, slot_idx, skill)])

    def demanded_by_axis(self, employee: Employee, day: str, slot_idx: int) -> Dict[str, List[str]]:
        """The employee's skills on `day` that slot `slot_idx` demands, grouped by axis."""
        out: Dict[str, List[str]] = defaultdict(list)
        held = employee.skills[day]
        for skill in self.skills:
            if skill in held and self.alpha.get((day, slot_idx, skill), 0) > 0:
                out[self.inst.skill_axis[skill]].append(skill)
        return out

    def choose_skill(self, employee: Employee, day: str, slot_idx: int, skills: List[str]) -> str:
        """Among the demanded skills on one axis: most remaining need, then scarcest."""
        return min(skills, key=lambda s: (-self.remaining(day, slot_idx, s), self.skill_employee_count.get(s, 1)))

    def slot_choice(self, employee: Employee, day: str, slot_idx: int) -> Dict[str, str]:
        return {axis: self.choose_skill(employee, day, slot_idx, skills)
                for axis, skills in self.demanded_by_axis(employee, day, slot_idx).items()}

    def block_choice(self, employee: Employee, day: str, block: Shift) -> Tuple[int, int, SkillChoice]:
        """(outstanding need touched, p_sl paid, skills per slot) if `block` were fixed now.

        Coverage sums the remaining minimum of each chosen skill, as the original
        heuristic did, so blocks over the slots with the most unmet need win.
        """
        coverage, priority_cost, choice = 0, 0, {}
        for slot_idx in block.slot_indices:
            picked = self.slot_choice(employee, day, slot_idx)
            choice[slot_idx] = picked
            for skill in picked.values():
                coverage += self.remaining(day, slot_idx, skill)
                priority_cost += self.inst.priority_weight(skill, self.inst.level(employee.id, day, skill))
        return coverage, priority_cost, choice

    def rank_block(self, coverage: int, priority_cost: int) -> tuple:
        """Sort key for a candidate block; lower sorts first. Most coverage first."""
        return (-coverage, random.random())

    # ------------------------------------------------------------------
    # state updates
    # ------------------------------------------------------------------

    def _apply_block(self, employee: Employee, day: str, block: Shift,
                     choice: Optional[SkillChoice] = None) -> None:
        for slot_idx in block.slot_indices:
            picked = choice[slot_idx] if choice is not None else self.slot_choice(employee, day, slot_idx)
            self.slot_skill[(employee.id, day, slot_idx)] = picked
            for skill in picked.values():
                self.cover[(day, slot_idx, skill)] += 1
        self.employee_day_block[(employee.id, day)] = block

    def _unapply_block(self, employee: Employee, day: str) -> None:
        block = self.employee_day_block.get((employee.id, day))
        if block is None:
            return
        for slot_idx in block.slot_indices:
            for skill in self.slot_skill.pop((employee.id, day, slot_idx), {}).values():
                self.cover[(day, slot_idx, skill)] -= 1
        self.employee_day_block[(employee.id, day)] = None

    def seed_fixed_days(self) -> None:
        """Fix a partial result's days before the greedy runs. Skill routing stays greedy."""
        for (eid, day), fixed in sorted(self.inst.fixed.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            if fixed.shift is None:
                self.employee_day_block[(eid, day)] = None
            else:
                self._apply_block(self.employees_by_id[eid], day, fixed.shift)

    # ------------------------------------------------------------------
    # rest between consecutive days
    # ------------------------------------------------------------------

    def _neighbour(self, eid: str, day: str, offset: int) -> Optional[Shift]:
        position = self.day_position[day] + offset
        if not 0 <= position < len(self.days):
            return None
        return self.employee_day_block.get((eid, self.days[position]))

    def _rest_ok(self, eid: str, day: str, block: Shift) -> bool:
        if not self.min_rest:
            return True
        before = self._neighbour(eid, day, -1)
        if before is not None and MINUTES_PER_DAY - before.end_min + block.start_min < self.min_rest:
            return False
        after = self._neighbour(eid, day, +1)
        if after is not None and MINUTES_PER_DAY - block.end_min + after.start_min < self.min_rest:
            return False
        return True

    def _repair_neighbour(self, employee: Employee, day: str) -> bool:
        """Re-pick one non-fixed neighbour's block so that `day` gets a feasible one."""
        for offset in (-1, +1):
            position = self.day_position[day] + offset
            if not 0 <= position < len(self.days):
                continue
            other = self.days[position]
            key = (employee.id, other)
            current = self.employee_day_block.get(key)
            if current is None or key in self.inst.fixed:
                continue
            self._unapply_block(employee, other)
            for alternative in self.assignments[key]:
                if alternative is current or not self._rest_ok(employee.id, other, alternative):
                    continue
                self.employee_day_block[key] = alternative
                fits = any(self._rest_ok(employee.id, day, block) for block in self.assignments[(employee.id, day)])
                self.employee_day_block[key] = None
                if fits:
                    self._apply_block(employee, other, alternative)
                    return True
            self._apply_block(employee, other, current)
        return False

    def assign_employee_day(self, employee: Employee, day: str) -> bool:
        """Fix the best-ranked block that keeps the rest; repair a neighbour if none does."""
        candidates = self.assignments.get((employee.id, day), [])
        if not candidates:
            self.employee_day_block[(employee.id, day)] = None
            self.unassigned.append((employee.id, day))
            return False
        for attempt in range(2):
            scored = []
            for block in candidates:
                coverage, priority_cost, choice = self.block_choice(employee, day, block)
                scored.append((self.rank_block(coverage, priority_cost), block, choice))
            scored.sort(key=lambda item: item[0])
            for _, block, choice in scored:
                if self._rest_ok(employee.id, day, block):
                    self._apply_block(employee, day, block, choice)
                    return True
            if attempt == 0 and not self._repair_neighbour(employee, day):
                break
        self.employee_day_block[(employee.id, day)] = None
        self.unassigned.append((employee.id, day))
        return False

    # ------------------------------------------------------------------
    # orders
    # ------------------------------------------------------------------

    def Order(self) -> List[str]:
        """Employees with fewer, scarcer skills first."""
        ordered = sorted(
            self.employees,
            key=lambda e: (
                len(e.all_skills),
                tuple(sorted(self.skill_employee_count.get(s, 0) for s in e.all_skills)),
                e.id,
            ),
        )
        return [e.id for e in ordered]

    def _day_bottleneck_score(self, day: str) -> float:
        """Demand still to cover over the workers able to cover it, summed by skill."""
        demand_by_skill: Dict[str, int] = defaultdict(int)
        for (d, _t, skill), minimum in self.alpha.items():
            if d == day:
                demand_by_skill[skill] += minimum
        score = 0.0
        for skill, total_need in demand_by_skill.items():
            available = sum(
                1 for e in self.employees
                if skill in e.skills[day] and self.assignments.get((e.id, day))
            )
            score += total_need / max(available, 1)
        return score

    def _compute_day_order(self, day_order_mode: int = 1) -> List[str]:
        """1 random, 2 by total demand, 3 by bottleneck - ties broken at random."""
        if day_order_mode == 1:
            ordered = list(self.days)
            random.shuffle(ordered)
            return ordered
        tiebreak = {day: random.random() for day in self.days}
        if day_order_mode == 2:
            demand_by_day: Dict[str, int] = defaultdict(int)
            for (day, _t, _s), minimum in self.alpha.items():
                demand_by_day[day] += minimum
            return sorted(self.days, key=lambda d: (-demand_by_day.get(d, 0), tiebreak[d]))
        if day_order_mode == 3:
            bottleneck = {day: self._day_bottleneck_score(day) for day in self.days}
            return sorted(self.days, key=lambda d: (-bottleneck[d], tiebreak[d]))
        raise ValueError(f"day_order_mode invalido: {day_order_mode!r} (usa 1, 2 ou 3)")

    # ------------------------------------------------------------------
    # the greedy pass
    # ------------------------------------------------------------------

    def Minimuns(self, day_order_mode: int = 1) -> None:
        """One greedy pass over the open employee-days, in the chosen day order."""
        self.reset()
        self.seed_fixed_days()
        base_order = self.Order()
        groups: Dict[tuple, List[str]] = defaultdict(list)
        key_order: List[tuple] = []
        for eid in base_order:
            employee = self.employees_by_id[eid]
            key = (len(employee.all_skills),
                   tuple(sorted(self.skill_employee_count.get(s, 0) for s in employee.all_skills)))
            if key not in groups:
                key_order.append(key)
            groups[key].append(eid)

        for day in self._compute_day_order(day_order_mode):
            # Keep Order()'s priority, shuffling only among true ties.
            day_order: List[str] = []
            for key in key_order:
                bucket = list(groups[key])
                random.shuffle(bucket)
                day_order.extend(bucket)
            for eid in day_order:
                if (eid, day) in self.inst.fixed:
                    continue        # seeded; must come before the rest-day branch
                if not self.assignments.get((eid, day)):
                    self.employee_day_block[(eid, day)] = None
                    continue
                self.assign_employee_day(self.employees_by_id[eid], day)

    def total_priority_cost(self) -> int:
        total = 0
        for (eid, day, _t), picked in self.slot_skill.items():
            for skill in picked.values():
                total += self.inst.priority_weight(skill, self.inst.level(eid, day, skill))
        return total

    def build_output_rows(self) -> List[List[str]]:
        rows = [["employee_id", *self.days]]
        order = {skill: i for i, skill in enumerate(self.skills)}
        for employee in self.employees:
            row = [employee.id]
            for day in self.days:
                block = self.employee_day_block.get((employee.id, day))
                if block is None:
                    row.append(UNASSIGNED if self.inst.is_work_day(employee.id, day)
                               else rest_cell(self.inst, employee.id, day))
                    continue
                slot_skills = {
                    t: sorted(self.slot_skill.get((employee.id, day, t), {}).values(), key=order.get)
                    for t in block.slot_indices
                }
                row.append(format_worked_cell(block, slot_skills, self.inst.slot_minutes))
            rows.append(row)
        return rows


def write_results_log(path, fieldnames: List[str], results: List[dict]) -> None:
    """The per-restart log. Written where asked; never into the problem's folder."""
    try:
        log_file = Path(path)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        with log_file.open("w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(results)
        print(f"[Heuristica] Results saved to: {log_file}")
    except OSError as ex:
        print(f"[Heuristica] Warning: Could not write results log: {ex}")
