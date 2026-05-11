"""
lns_solution.py
---------------
Solution representation and incremental coverage tracking for the LNS scheduler.

The solution mirrors the ILP variables directly:
  x_wdh  →  solution.assignments[(emp_id, day)]  : Assignment | None
  y_wdts →  solution.skill_map[(emp_id, day, slot_idx)] : str | None

CoverageTracker maintains coverage and shortage counts incrementally so the
objective can be evaluated in O(k × slots) rather than O(|W|×|D|×|T|×|S|).
"""

from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------
EmpId   = str
Day     = str          # "2025-10-01"
SlotIdx = int
Skill   = str

AssignmentKey = str    # e.g. "20067009_20251001_660_960"

# ---------------------------------------------------------------------------
# Assignment (mirrors the feasible daily blocks built by build_assignments)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Assignment:
    """A feasible daily working block for one employee on one day."""
    key:         AssignmentKey
    label:       str            # human-readable, e.g. "11:00-16:00"
    start_min:   int            # absolute minutes from midnight
    end_min:     int
    slot_indices: Tuple[int, ...]  # half-hour slot indices covered

    @property
    def duration_hours(self) -> float:
        return (self.end_min - self.start_min) / 60.0


# ---------------------------------------------------------------------------
# Solution
# ---------------------------------------------------------------------------

class Solution:
    """
    Complete schedule for all employees and days.

    assignments[(emp_id, day)]            → Assignment | None
    skill_map[(emp_id, day, slot_idx)]    → skill str | None
    """

    def __init__(self):
        self.assignments: Dict[Tuple[EmpId, Day], Optional[Assignment]] = {}
        self.skill_map:   Dict[Tuple[EmpId, Day, SlotIdx], Optional[Skill]] = {}

    # ------------------------------------------------------------------
    # Convenience helpers
    # ------------------------------------------------------------------

    def set_assignment(
        self,
        emp_id:     EmpId,
        day:        Day,
        assignment: Optional[Assignment],
        skill_map:  Dict[SlotIdx, Optional[Skill]],
    ):
        """Set the full assignment + skill choices for one (employee, day)."""
        self.assignments[(emp_id, day)] = assignment
        # Clear any previous skill entries for this (emp, day)
        keys_to_delete = [k for k in self.skill_map if k[0] == emp_id and k[1] == day]
        for k in keys_to_delete:
            del self.skill_map[k]
        if assignment is not None:
            for slot_idx, skill in skill_map.items():
                self.skill_map[(emp_id, day, slot_idx)] = skill

    def clear_assignment(self, emp_id: EmpId, day: Day):
        """Remove the assignment and all skill choices for (emp, day)."""
        self.assignments[(emp_id, day)] = None
        keys = [k for k in self.skill_map if k[0] == emp_id and k[1] == day]
        for k in keys:
            del self.skill_map[k]

    def worked_days(self, emp_id: EmpId, days: List[Day]) -> List[Day]:
        """Return the days on which emp_id has a non-None assignment."""
        return [d for d in days if self.assignments.get((emp_id, d)) is not None]

    def copy(self) -> "Solution":
        new = Solution()
        new.assignments = dict(self.assignments)
        new.skill_map   = dict(self.skill_map)
        return new


# ---------------------------------------------------------------------------
# CoverageTracker
# ---------------------------------------------------------------------------

class CoverageTracker:
    """
    Maintains coverage[day, slot_idx, skill] and shortage[day, slot_idx, skill]
    incrementally.

    shortage = max(0, alpha - coverage)
    total_shortage = sum of all shortage values  (Objective Function 1)

    The tracker also counts staff-level coverage (team "Employees") which counts
    any employee present in the slot regardless of their assigned skill.
    """

    STAFF_TEAM = "Employees"

    def __init__(
        self,
        alpha: Dict[Tuple[Day, SlotIdx, Skill], int],
        employees: List[dict],
    ):
        """
        alpha   : {(day, slot_idx, skill): minimum_required}
        employees : list of employee dicts with 'id' and 'assignable_skills'
        """
        self.alpha     = alpha
        self.employees = {e["id"]: e for e in employees}

        # coverage[(day, slot_idx, skill)] → int  (number of workers currently assigned)
        self.coverage: Dict[Tuple[Day, SlotIdx, Skill], int] = {k: 0 for k in alpha}

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def apply(
        self,
        emp_id:     EmpId,
        day:        Day,
        assignment: Assignment,
        skill_map:  Dict[SlotIdx, Optional[Skill]],
    ):
        """Register an employee assignment, updating coverage counts."""
        emp = self.employees[emp_id]
        for slot_idx in assignment.slot_indices:
            # Staff-level coverage — any present employee contributes
            staff_key = (day, slot_idx, self.STAFF_TEAM)
            if staff_key in self.coverage:
                self.coverage[staff_key] += 1

            # Skill-specific coverage
            skill = skill_map.get(slot_idx)
            if skill and skill != self.STAFF_TEAM:
                skill_key = (day, slot_idx, skill)
                if skill_key in self.coverage:
                    self.coverage[skill_key] += 1

    def revert(
        self,
        emp_id:     EmpId,
        day:        Day,
        assignment: Assignment,
        skill_map:  Dict[SlotIdx, Optional[Skill]],
    ):
        """Undo a previously applied assignment."""
        for slot_idx in assignment.slot_indices:
            staff_key = (day, slot_idx, self.STAFF_TEAM)
            if staff_key in self.coverage:
                self.coverage[staff_key] = max(0, self.coverage[staff_key] - 1)

            skill = skill_map.get(slot_idx)
            if skill and skill != self.STAFF_TEAM:
                skill_key = (day, slot_idx, skill)
                if skill_key in self.coverage:
                    self.coverage[skill_key] = max(0, self.coverage[skill_key] - 1)

    def shortage_at(self, day: Day, slot_idx: SlotIdx, skill: Skill) -> int:
        key = (day, slot_idx, skill)
        return max(0, self.alpha.get(key, 0) - self.coverage.get(key, 0))

    def total_shortage(self) -> int:
        return sum(
            max(0, self.alpha[k] - self.coverage.get(k, 0))
            for k in self.alpha
        )

    def shortage_on_day(self, day: Day) -> int:
        return sum(
            max(0, self.alpha[k] - self.coverage.get(k, 0))
            for k in self.alpha if k[0] == day
        )

    def shortage_snapshot(self) -> Dict[Tuple[Day, SlotIdx, Skill], int]:
        """Return a copy of all current shortage values (for diagnostics)."""
        return {
            k: max(0, self.alpha[k] - self.coverage.get(k, 0))
            for k in self.alpha
        }

    def coverage_snapshot(self) -> Dict[Tuple[Day, SlotIdx, Skill], int]:
        return dict(self.coverage)

    def delta_if_applied(
        self,
        emp_id:     EmpId,
        day:        Day,
        assignment: Assignment,
        skill_map:  Dict[SlotIdx, Optional[Skill]],
    ) -> int:
        """
        Compute the change in total shortage if this assignment were applied,
        WITHOUT actually modifying state.  Negative = improvement.
        """
        delta = 0
        for slot_idx in assignment.slot_indices:
            # Staff-level
            staff_key = (day, slot_idx, self.STAFF_TEAM)
            if staff_key in self.alpha:
                before = max(0, self.alpha[staff_key] - self.coverage.get(staff_key, 0))
                after  = max(0, self.alpha[staff_key] - (self.coverage.get(staff_key, 0) + 1))
                delta += after - before

            # Skill-level
            skill = skill_map.get(slot_idx)
            if skill and skill != self.STAFF_TEAM:
                skill_key = (day, slot_idx, skill)
                if skill_key in self.alpha:
                    before = max(0, self.alpha[skill_key] - self.coverage.get(skill_key, 0))
                    after  = max(0, self.alpha[skill_key] - (self.coverage.get(skill_key, 0) + 1))
                    delta += after - before
        return delta

    def rebuild_from_solution(self, solution: Solution):
        """Full rebuild — used after a batch revert or for validation."""
        self.coverage = {k: 0 for k in self.alpha}
        for (emp_id, day), assignment in solution.assignments.items():
            if assignment is None:
                continue
            skill_map = {
                slot_idx: solution.skill_map.get((emp_id, day, slot_idx))
                for slot_idx in assignment.slot_indices
            }
            self.apply(emp_id, day, assignment, skill_map)
