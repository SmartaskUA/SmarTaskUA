# scheduler.py
import random
import time
from collections import defaultdict
import holidays
import pandas as pd
import os

from algorithms.utils import (
    TEAM_CODE_TO_ID,    
    TEAM_ID_TO_CODE,
    get_team_id,        
    build_calendar,
    parse_vacs_file,
    parse_requirements_file,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv_shifts,
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
                 num_iter=10, maxTime=None, year=2025, shifts=3):
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


def _evaluate_shortages(assignment, mins, ideals):
    """
    Return the number of unmet minimum and ideal slots for one schedule.
    """
    assigned_counts = defaultdict(int)
    for _emp_id, entries in assignment.items():
        for day, shift, team in entries:
            assigned_counts[(day, shift, team)] += 1

    missed_mins = 0
    for key, required in mins.items():
        actual = assigned_counts.get(key, 0)
        missed_mins += max(0, required - actual)

    missed_ideals = 0
    for key, required in ideals.items():
        actual = assigned_counts.get(key, 0)
        missed_ideals += max(0, required - actual)

    return missed_mins, missed_ideals


def _build_output(scheduler, vacs, num_days):
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
        output.append(row)

    return output

def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=3,rules=None):
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

    iterations = 300
    if isinstance(rules, dict) and rules.get("iterations"):
        iterations = int(rules["iterations"])
    iterations = max(1, int(iterations))

    start_time = time.perf_counter()
    total_min_short = 0
    total_ideal_short = 0
    best_min_short = None
    best_ideal_short = None
    best_scores = None
    best_scheduler = None
    best_output = None

    for _ in range(iterations):

        # print(f"Iteração {_ + 1}/{iterations}...")

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
        min_short, ideal_short = _evaluate_shortages(scheduler.assignment, mins, ideals)

        total_min_short += min_short
        total_ideal_short += ideal_short

        if best_min_short is None or min_short < best_min_short:
            best_min_short = min_short
        if best_ideal_short is None or ideal_short < best_ideal_short:
            best_ideal_short = ideal_short

        current_scores = (min_short, ideal_short)
        if best_scores is None or current_scores < best_scores:
            best_scores = current_scores
            best_scheduler = scheduler
            best_output = _build_output(scheduler, vacs, num_days)

    total_time = time.perf_counter() - start_time
    avg_min_short = total_min_short / iterations
    avg_ideal_short = total_ideal_short / iterations
    avg_time = total_time / iterations

    print(f"[{iterations} iterações] Tempo total da heurística: {total_time:.2f}s")
    print(f"[{iterations} iterações] Tempo médio por iteração: {avg_time:.2f}s")
    print(
        f"Melhor valor de mínimos nas {iterations} iterações: "
        f"{best_min_short if best_min_short is not None else 0}"
    )
    print(
        f"Melhor valor de ideais nas {iterations} iterações: "
        f"{best_ideal_short if best_ideal_short is not None else 0}"
    )
    print(f"Média de mínimos        : {avg_min_short:.2f}")
    print(f"Média de ideais         : {avg_ideal_short:.2f}")

    if best_scheduler is not None:
        export_schedule_to_csv_shifts(best_scheduler, "schedule_greedy_randomized.csv", num_days=num_days)

    return best_output if best_output is not None else _build_output(
        GreedyRandomized(
            employees=emp_ids,
            num_days=num_days,
            holidays_set=holi,
            vacs=vacs,
            mins=mins,
            ideals=ideals,
            teams=teams,
            num_iter=1,
            maxTime=(int(maxTime) if maxTime is not None else None),
            year=year,
            shifts=shifts,
        ),
        vacs,
        num_days,
    )
