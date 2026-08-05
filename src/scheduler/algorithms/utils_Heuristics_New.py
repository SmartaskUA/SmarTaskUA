from datetime import date, time
import pandas as pd
from collections import defaultdict
from time import sleep
import random

from algorithms.utils import (
    get_team_id,
    get_team_code,
)


# =========================================================================
# ATOMIC STATE MANAGEMENT
# =========================================================================
def _assign(self, emp_id, day_1b, shift, team):
    """
    Atribuição atómica — actualiza todas as estruturas globais em simultâneo.
    Todo o código deve usar este método em vez de escrever directamente
    em self.assignment / self.assignment_by_day / self.Total_Days /
    self.sundays_holidays_worked.
    """
    self.assignment[emp_id].append((day_1b, shift, team))
    self.assignment_by_day[day_1b].append((emp_id, shift, team))
    self.Total_Days[emp_id] = self.Total_Days.get(emp_id, 0) + 1
    date = self.dates[day_1b - 1]
    if date in self._sun_hol_set:
        self.sundays_holidays_worked[emp_id] = (
            self.sundays_holidays_worked.get(emp_id, 0) + 1
        )

def _unassign(self, emp_id, day_1b, shift, team):
    """
    Remoção atómica — actualiza todas as estruturas globais em simultâneo.
    """
    self.assignment[emp_id] = [
        e for e in self.assignment[emp_id]
        if not (e[0] == day_1b and e[1] == shift and e[2] == team)
    ]
    self.assignment_by_day[day_1b] = [
        e for e in self.assignment_by_day[day_1b]
        if not (e[0] == emp_id and e[1] == shift and e[2] == team)
    ]
    self.Total_Days[emp_id] = max(0, self.Total_Days.get(emp_id, 0) - 1)
    date = self.dates[day_1b - 1]
    if date in self._sun_hol_set:
        self.sundays_holidays_worked[emp_id] = max(
            0, self.sundays_holidays_worked.get(emp_id, 0) - 1
        )

# =========================================================================
# HELPERS
# =========================================================================
def _build_emp_team_map(self, employees):
    mapping = {}
    for i, e in enumerate(employees, start=1):
        codes = [get_team_code(t) for t in e.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        mapping[i] = ids
    return mapping

def _build_teams(self, employees):
    teams = {}
    for i, e in enumerate(employees, start=1):
        codes = [get_team_code(t) for t in e.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        for t in ids:
            teams.setdefault(t, set()).add(i)
    return teams

def _validate_block_transition_beta(self, previous_shift, next_shift):
    if previous_shift is None or next_shift is None:
        return True
    return not (
        (previous_shift == 3 and next_shift == 1) or
        (previous_shift == 3 and next_shift == 2) or
        (previous_shift == 2 and next_shift == 1)
    )


def get_next_assigned_shift(self, emp_id, day):
    for day_1b, shift, team_code in self.assignment.get(emp_id, []):
        if day_1b == day + 1:
            return shift
    return None

def get_previous_assigned_shift(self, emp_id, day):
    for day_1b, shift, team_code in self.assignment.get(emp_id, []):
        if day_1b == day - 1:
            return shift
    return None


def consecutivechecker(self, emp_id, day, assignment):
    streak_before = 0
    for past_day in range(day - 1, max(0, day - 6), -1):
        worked = any(emp == emp_id for emp, _, _ in assignment.get(past_day, []))
        if worked:
            streak_before += 1
        else:
            break
    streak_after = 0
    for future_day in range(day + 1, day + 6):
        worked = any(emp == emp_id for emp, _, _ in assignment.get(future_day, []))
        if worked:
            streak_after += 1
        else:
            break
    return streak_before + 1 + streak_after

def evaluate_Day_Toshifts_minimos(self, day, mins):
    result = {}
    for team_code in self.teams.keys():
        mandatory = []
        for shift in range(1, self.shifts + 1):
            key = (shift, team_code)
            min_count = mins.get(key, 0)
            mandatory.extend([shift] * min_count)
        result[team_code] = {"mandatory": mandatory, "optional": []}
    return result

def evaluate_Day_Toshifts_ideais(self, day, ideals):
    result = {}
    for team_code in self.teams.keys():
        optional = []
        for shift in range(1, self.shifts + 1):
            key = (shift, team_code)
            ideal_count = ideals.get(key, 0)
            if ideal_count > 0:
                optional.extend([shift] * ideal_count)
        random.shuffle(optional)
        result[team_code] = {"mandatory": [], "optional": optional}
    return result


# =========================================================================
# TABLE CONSTRUCTION HELPERS
# =========================================================================
def construct_mins_table(self, minimos, dates, teams, week_number, turnos, spacing):
    mins = {}
    week_start_day = (week_number - 1) * spacing + 1
    week_end_day = min(week_number * spacing, len(dates))
    if week_start_day > week_end_day:
        return mins
    for day in range(week_start_day, week_end_day + 1):
        mins[day] = {}
        for s in range(1, turnos + 1):
            for team_code in self.teams.keys():
                d = dates[day - 1]
                key = (d, s, team_code)
                if key in self.minimos:
                    mins[day][(s, team_code)] = self.minimos[key]
        # print(f"Day {day}: {mins[day]}")  # Debugging line to check the contents of mins for each day
    return mins


def construct_ideals_table(self, ideais, dates, teams, week_number, turnos, spacing):
    ideals = {}
    week_start_day = (week_number - 1) * spacing + 1
    week_end_day = min(week_number * spacing, len(dates))
    if week_start_day > week_end_day:
        return ideals
    for day in range(week_start_day, week_end_day + 1):
        ideals[day] = {}
        for s in range(1, turnos + 1):
            for team_code in self.teams.keys():
                d = dates[day - 1]
                key = (d, s, team_code)
                if key in self.ideais:
                    ideals[day][(s, team_code)] = self.ideais[key]
        # print(f"Day {day}: {ideals[day]}")  # Debugging line to check the contents of ideals for each day

    return ideals
