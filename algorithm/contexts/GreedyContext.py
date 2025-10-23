# greedy_context.py
from dataclasses import dataclass
from typing import Dict, List, Tuple, Set, Callable, Optional
import numpy as np

@dataclass
class GreedyContext:
    """
    Shared greedy scheduling state for rule handlers.
    Mirrors CPSatContext but for iterative feasibility checks.
    """
    def __init__(self, *, Employees, num_days, shifts,
                 vacations, allowed_teams_per_emp,
                 min_required, ideal_required,
                 special_days, cover_count,
                 e=None, d=None, s=None, t=None,
                 assignment=None):
        self.Employees = Employees
        self.num_days = num_days
        self.shifts = shifts
        self.vacations = vacations
        self.allowed_teams_per_emp = allowed_teams_per_emp
        self.min_required = min_required
        self.ideal_required = ideal_required
        self.special_days = special_days
        self.cover_count = cover_count
        self.assignment = assignment or {}

        self.e, self.d, self.s, self.t = e, d, s, t

        self.score = 0

    def get_days_worked(self, e):
        return [day for (day, _s, _t) in self.assignment.get(e, [])]

    def get_shift(self, e, day):
        for (d, s, _t) in self.assignment.get(e, []):
            if d == day:
                return s
        return None

    def add_score(self, value):
        self.score += value
