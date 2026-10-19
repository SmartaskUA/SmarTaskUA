"""The problem a solver solves: one schema v4 package, read and interpreted once.

Every field here is already decided - cell grammar, which shifts are legal on
which day, levels, labour law, the fixed days of a partial result - so a solver
only reshapes it into its own variables and never re-reads a CSV. Solvers index
the model the way MathematicalDefinition7 does: days are ISO strings, slots are
absolute (slot ``i`` is ``[i*T, (i+1)*T)`` minutes from 00:00), and a skill is
the pair ``"tableName/tableValue"``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .schema_core import CellRule, Schedule, min_to_hhmm

#: The rest code a result writes for a day off. WFM's own number, kept by v4.0.
REST_CODE = 3

#: Day modes, in MathematicalDefinition7's vocabulary. Derived from the cell only.
WORK_MODES = frozenset({"work_template", "fixed_time_work"})


class ParseError(Exception):
    """A v4 package no solver can use. Carries every problem found, not just the first."""

    def __init__(self, problems: List[str]):
        self.problems = list(dict.fromkeys(problems))     # the same finding from two checks once
        preview = "; ".join(self.problems[:5])
        if len(self.problems) > 5:
            preview += f" (+{len(self.problems) - 5} more)"
        super().__init__(f"schema v4 package rejected: {preview}")


@dataclass(frozen=True)
class TimeSlot:
    index: int
    start_min: int
    end_min: int

    @property
    def label(self) -> str:
        return f"{min_to_hhmm(self.start_min)}-{min_to_hhmm(self.end_min)}"


@dataclass(frozen=True)
class Shift:
    """One daily assignment h in H_wd: a menu code on one employee-day."""
    key: str
    code: int
    start_min: int
    end_min: int
    slot_indices: Tuple[int, ...]

    @property
    def label(self) -> str:
        return f"{min_to_hhmm(self.start_min)}-{min_to_hhmm(self.end_min)}"


def make_shift(eid: str, day: str, schedule: Schedule, slot_minutes: int) -> Shift:
    """The candidate `schedule` becomes on one employee-day.

    The key's last two tokens (code, start slot) are unique per employee-day;
    MD7 builds its variable names from them.
    """
    iv = schedule.interval
    return Shift(
        key=f"{eid}_{day}_{schedule.code}_{iv.start // slot_minutes}",
        code=schedule.code,
        start_min=iv.start,
        end_min=iv.end,
        slot_indices=tuple(range(iv.start // slot_minutes, iv.end // slot_minutes)),
    )


@dataclass(frozen=True)
class FixedDay:
    """One employee-day a partial result decided. `shift` is None for a rest."""
    code: int
    shift: Optional[Shift]


@dataclass
class Employee:
    id: str
    name: str
    contract_minutes: Dict[str, Optional[int]]      # day -> workMinutesPerDay [H_w]
    skills: Dict[str, Dict[str, int]]               # day -> {skill: level} [S_w, l_ws]
    all_skills: Tuple[str, ...] = ()                # every skill held on any day, in instance order


@dataclass(frozen=True)
class Legislation:
    """Roster-wide labour law from constraints.hard[]. None means no such rule."""
    max_consecutive: Optional[int]      # MaxConsecutiveWorkDays
    max_week_days: Optional[int]        # MaxConsecutiveWorkDaysInWeek - a count per week
    min_rest_minutes: Optional[int]     # MinDistanceBetweenShiftsInMinutes


@dataclass
class V4Instance:
    problem_path: Path
    problem: dict
    problem_id: str
    roster_code: str
    slot_minutes: int
    days: List[str]
    weeks: List[List[str]]
    holidays: Dict[str, str]
    axes: Dict[str, Tuple[str, ...]]
    skills: List[str]
    skill_axis: Dict[str, str]
    time_slots: List[TimeSlot]
    alpha: Dict[Tuple[str, int, str], int]
    open_days: List[str]
    closed_days: set
    employees: List[Employee]
    cells: Dict[Tuple[str, str], CellRule]
    menu: Dict[int, Schedule]
    menu_synthesised: bool
    candidates: Dict[Tuple[str, str], List[Shift]]
    day_modes: Dict[Tuple[str, str], str]
    legislation: Legislation
    priority_tiers: List[dict]
    fixed: Dict[Tuple[str, str], FixedDay] = field(default_factory=dict)
    fixed_workday: Dict[Tuple[str, str], int] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def __post_init__(self):
        self._by_id = {e.id: e for e in self.employees}

    @property
    def base(self) -> Path:
        """The package folder; every CSV path in problem.json resolves against it."""
        return self.problem_path.parent

    # -- lookups -----------------------------------------------------------

    def employee(self, eid: str) -> Employee:
        return self._by_id[eid]

    def level(self, eid: str, day: str, skill: str) -> Optional[int]:
        """l_ws on `day`, or None when the employee does not hold `skill` that day."""
        return self._by_id[eid].skills.get(day, {}).get(skill)

    def priority(self, skill: str, level: Optional[int]) -> int:
        """The rank of the first priorityHierarchy tier matching (skill, level)."""
        if level is not None:
            for tier in self.priority_tiers:
                if tier["skill"] != skill or level < tier["min_n"]:
                    continue
                if tier["max_n"] is not None and level > tier["max_n"]:
                    continue
                return tier["priority"]
        return len(self.priority_tiers) + 1

    def priority_weight(self, skill: str, level: Optional[int]) -> int:
        """p_sl of ObjectiveFunction2: tier 1 weighs 1, tier 2 weighs 11, and so on."""
        return 1 + (self.priority(skill, level) - 1) * 10

    def raw_cell(self, eid: str, day: str) -> str:
        return self.cells[(eid, day)].raw.strip()

    def is_work_day(self, eid: str, day: str) -> bool:
        """Whether the cell - or the partial result - makes this day a worked one."""
        if (eid, day) in self.fixed_workday:
            return self.fixed_workday[(eid, day)] == 1
        return self.day_modes[(eid, day)] in WORK_MODES

    @property
    def open_cells(self) -> List[Tuple[str, str]]:
        """Employee-days the solver decides: everything the partial result left out."""
        return [(e.id, d) for e in self.employees for d in self.days if (e.id, d) not in self.fixed]
