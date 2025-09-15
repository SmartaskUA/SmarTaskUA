# scheduler.py
import random
import time
from collections import defaultdict
import holidays
import pandas as pd
import os

from algorithm.utils import (
    TEAM_CODE_TO_ID,    
    TEAM_ID_TO_CODE,
    get_team_id,        
    build_calendar,
    parse_vacs_file,
    parse_requirements_file,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    get_team_code
)

class GreedyRandomized:
    """
    Pure greedy randomized builder:
      - Feasibility check f1
      - Slot-urgency heuristic f2
      - Random proposals with small inner budget (num_iter)
      - Time-boxed outer loop (maxTime in seconds, if provided)
    """
    def __init__(self, employees, num_days, holidays_set, vacs, mins, ideals, teams,
                 num_iter=10, maxTime=None, year=2025, shifts=2):
        self.employees = employees
        self.num_days = num_days
        self.vacs = vacs
        self.mins = mins
        self.ideals = ideals
        self.teams = teams
        self.num_iter = num_iter
        self.assignment = defaultdict(list)      # p -> [(day, shift, team)]
        self.schedule_table = defaultdict(list)  # (day, shift, team) -> [p,...]
        self.year = year
        self.shifts = int(shifts)  # Number of shifts

        # Calendar
        self.dias_ano, self.sunday = build_calendar(self.year)
        start_date = self.dias_ano[0].date()
        # 'holidays_set' is an iterable of date-like objects from holidays lib
        self.holidays = {(d - start_date).days + 1 for d in holidays_set}

        # timing
        self.maxTime = maxTime
        self.start_time = time.time()

    # ---------- feasibility ----------
    def f1(self, p, d, s):
        """
        Feasibility for assigning employee p on day d to shift s.
        Rules:
          - no >5 consecutive days
          - <=22 Sundays+holidays
          - forbid T (day X) -> M (day X+1) and M (day X) -> T (day X-1)
        """
        assignments = self.assignment[p]

        # Consecutive-day window
        days = sorted([day for (day, _, _) in assignments] + [d])
        run = 1
        for i in range(1, len(days)):
            if days[i] == days[i-1] + 1:
                run += 1
                if run > 5:
                    return False
            else:
                run = 1

        # Sundays & holidays cap (22)
        special_days = set(self.holidays).union(self.sunday)
        sund_hol = sum(1 for (day, _, _) in assignments if day in special_days)
        if d in special_days:
            sund_hol += 1
        if sund_hol > 22:
            return False

        # No T -> next-day M (and symmetric check)
        for (day, shift, _) in assignments:
            if day + 1 == d and s < shift:  # today is the next day after a worked day
                return False
            if day - 1 == d and shift < s:  # today is the previous day before a worked day
                return False

        # If you want to forbid double shift same day, uncomment:
        # if any(day == d for (day, _, _) in assignments):
        #     return False

        return True

    # ---------- slot urgency ----------
    def f2(self, d, s, t):
        """
        Lower is better.
          0 -> below minimum
          1 -> between min and ideal
          2+k -> at/above ideal by k
        Keys must be (day, shift, team_id)
        """
        current = len(self.schedule_table[(d, s, t)])
        min_required = self.mins.get((d, s, t), 0)
        ideal_required = self.ideals.get((d, s, t), min_required)

        if current < min_required:
            return 0
        elif current < ideal_required:
            return 1
        else:
            return 2 + (current - ideal_required)

    # ---------- main loop ----------
    def build_schedule(self):
        all_days = set(range(1, self.num_days + 1))

        while (not self.is_complete()) and (self.maxTime is None or time.time() - self.start_time < self.maxTime):
            # Prefer employees constrained to one team first; then two; then ANY (including 3+ teams)
            P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 1]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 2]
            if not P:
                # allow employees with 3 or more teams to be chosen 
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) >= 1]
            if not P:
                break  # nobody left who can take more work

            p = random.choice(P)
            f_value = float('inf')
            count = 0
            best = None

            used_days = {day for (day, _, _) in self.assignment[p]}
            vacations = set(self.vacs.get(p, []))
            available_days = list(all_days - used_days - vacations)
            if not available_days:
                continue

            while f_value > 0 and count < self.num_iter and available_days:
                d = random.choice(available_days)
                s = random.choice(list(range(1, self.shifts + 1)))

                if self.f1(p, d, s):
                    count += 1
                    for t in self.teams[p]:
                        score = self.f2(d, s, t)
                        if score < f_value:
                            f_value = score
                            best = (d, s, t)

            if best:
                d, s, t = best
                self.assignment[p].append((d, s, t))
                self.schedule_table[(d, s, t)].append(p)

    def is_complete(self):
        return all(len(self.assignment[p]) >= 223 for p in self.employees)

def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2):
    """
    Library-style API:
      vacations_rows: list of rows like ['Employee 1', '0','1','0',...]
      requirements_rows: list of rows like ['Team_A','Minimum','M', <day1>, <day2>, ...]
      employees_list: [{'teams': ['Team_A','Team_B']}, ...] (order -> employee id)
    Returns: table with header + per-employee day values.
    """

    num_days = 365
    holi = holidays.country_holidays("PT", years=[year])

    emp_ids = [i + 1 for i in range(len(employees))]
    vacs    = rows_to_vac_dict(vacations)
    mins, ideals = rows_to_req_dicts(minimuns)

    teams = {}
    for idx, e in enumerate(employees):
        emp_id = idx + 1
        codes = [ get_team_code(t) for t in e.get("teams", []) ]
        ids = [ get_team_id(c) for c in codes if c ]
        if not ids:
            ids = [ get_team_id("A") ]
        teams[emp_id] = ids

    scheduler = GreedyRandomized(
        employees=emp_ids,
        num_days=num_days,
        holidays_set=holi,
        vacs=vacs,
        mins=mins,
        ideals=ideals,
        teams=teams,
        num_iter=10,
        maxTime=(int(maxTime) if maxTime is not None else None),
        year=year,
        shifts=shifts, 
    )
    scheduler.build_schedule()

    header = ["funcionario"] + [f"Dia {d}" for d in range(1, num_days + 1)]
    label = {1: "M_", 2: "T_", 3: "N_"} 
    output = [header]
    for p in scheduler.employees:
        row = [p]
        assign = {day: (s, t) for (day, s, t) in scheduler.assignment[p]}
        vacation_days = set(vacs.get(p, []))
        for d in range(1, num_days + 1):
            if d in vacation_days:
                row.append("F")
            elif d in assign:
                s, t = assign[d]
                row.append(label.get(s, "") + TEAM_ID_TO_CODE.get(t, str(t)))
            else:
                row.append("0")
        row and output.append(row)
    return output
