import random
import time
from collections import defaultdict

import numpy as np
import pandas as pd
import holidays as hl
import holidays

from algorithm.utils import (
    TEAM_LETTER_TO_ID,
    build_calendar,
    parse_vacs_file,
    parse_requirements_file,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
)

class GreedyClimbing:
    """
    Builds an initial schedule via greedy randomized assignment,
    then improves it via hill climbing (local search).
    """

    def __init__(self, employees, num_days, holidays_set, vacs, mins, ideals, teams,
                 num_iter=10, maxTime=None, year=2025, shifts=2):
        self.employees = employees
        self.num_days = num_days
        self.shifts = int(shifts) 
        self.vacs = vacs
        self.mins = mins
        self.ideals = ideals
        self.teams = teams
        self.num_iter = num_iter
        self.assignment = defaultdict(list)      # p -> [(day, shift, team)]
        self.schedule_table = defaultdict(list)  # (day, shift, team) -> [p,...]
        self.year = year
        self.dias_ano, self.sunday = build_calendar(self.year)
        start_date = self.dias_ano[0].date()
        self.holidays = {(d - start_date).days + 1 for d in holidays_set}
        self.vac_array = self._create_vacation_array()
        self.fds = np.zeros_like(self.vac_array, dtype=bool)
        for day in self.sunday:
            self.fds[:, day - 1] = True
        # timing: maxTime in seconds for greedy phase
        self.maxTime = maxTime
        self.start_time = time.time()

    # ---------- helpers ----------

    def _create_vacation_array(self):
        vac_array = np.zeros((len(self.employees), self.num_days), dtype=bool)
        for emp in self.employees:
            for day in self.vacs.get(emp, []):
                vac_array[emp - 1, day - 1] = True
        return vac_array

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

        # Max 5 consecutive days
        days = sorted([day for (day, _, _) in assignments] + [d])
        run = 1
        for i in range(1, len(days)):
            if days[i] == days[i - 1] + 1:
                run += 1
                if run > 5:
                    return False
            else:
                run = 1

        # Sundays & holidays cap (<=22)
        special_days = set(self.holidays).union(self.sunday)
        sundays_and_holidays = sum(1 for (day, _, _) in assignments if day in special_days)
        if d in special_days:
            sundays_and_holidays += 1
        if sundays_and_holidays > 22:
            return False

        # No T -> next-day M (and symmetric)
        for (day, shift, _) in assignments:
            if day + 1 == d and s < shift:
                return False
            if day - 1 == d and shift < s:
                return False
        return True


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

    # ---------- greedy construction ----------

    def build_schedule(self):
        all_days = set(range(1, self.num_days + 1))

        while not self.is_complete():
            if self.maxTime is not None and time.time() - self.start_time >= self.maxTime:
                print("Maximum time reached, stopping generation.")
                break

            # Prefer employees with a single allowed team
            P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 1]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 2]
            if not P:
                break

            p = random.choice(P)
            best = None
            best_val = float('inf')
            count = 0

            used = {day for (day, _, _) in self.assignment[p]}
            vacations = set(self.vacs.get(p, []))
            available_days = list(all_days - used - vacations)
            if not available_days:
                continue

            while best_val > 0 and count < self.num_iter and available_days:
                d = random.choice(available_days)
                s = random.choice(list(range(1, self.shifts + 1)))

                if self.f1(p, d, s):
                    count += 1
                    for t in self.teams[p]:
                        val = self.f2(d, s, t)
                        if val < best_val:
                            best_val = val
                            best = (d, s, t)

            if best:
                d, s, t = best
                self.assignment[p].append((d, s, t))
                self.schedule_table[(d, s, t)].append(p)

    def is_complete(self):
        return all(len(self.assignment[p]) >= 223 for p in self.employees)

    def create_horario(self):
        horario = np.zeros((len(self.employees), self.num_days, self.shifts), dtype=int)
        for p in self.employees:
            for d, s, t in self.assignment[p]:
                horario[p - 1, d - 1, s - 1] = t    # shift 1 -> morning (0), shift 2 -> afternoon (1), shift 3 -> night (2)
        return horario

    def update_from_horario(self, horario):
        self.assignment.clear()
        self.schedule_table.clear()
        for p_idx, emp in enumerate(self.employees):
            for d in range(self.num_days):
                for s in range(self.shifts):
                    t = horario[p_idx, d, s]
                    if t > 0:
                        self.assignment[emp].append((d + 1, s + 1, t))
                        self.schedule_table[(d + 1, s + 1, t)].append(emp)


    def hill_climbing(self, max_iterations=400000, maxTime=60):
        max_seconds = maxTime * 60 if maxTime is not None else None
        start_hc = time.time()

        horario = self.create_horario()
        f1, f2, f3, f4, f5 = self.criterios(horario)
        best_score = f1 + f2 + f3 + f4 + f5

        iteration = 0
        steps = 0

        while iteration < max_iterations and best_score > 0:
            steps += 1
            if max_seconds is not None and (time.time() - start_hc) >= max_seconds:
                print("Maximum time reached, stopping generation.")
                break

            emp_idx = np.random.randint(len(self.employees))
            emp = self.employees[emp_idx]

            available_days = [d for d in range(self.num_days) if not self.vac_array[emp_idx, d]]
            if len(available_days) < 2:
                iteration += 1
                continue

            d1, d2 = np.random.choice(available_days, 2, replace=False)
            s1, s2 = np.random.choice(list(range(self.shifts)), 2, replace=False)

            t1 = horario[emp_idx, d1, s1]
            t2 = horario[emp_idx, d2, s2]

            can_A = 1 in self.teams[emp]
            can_B = 2 in self.teams[emp]

            if t1 != t2:
                new_h = horario.copy()
                if can_A and can_B:
                    new_h[emp_idx, d1, s1], new_h[emp_idx, d2, s2] = t2, t1
                elif can_A:
                    new_h[emp_idx, d1, s1] = 1
                    new_h[emp_idx, d2, s2] = 0
                elif can_B:
                    new_h[emp_idx, d1, s1] = 0
                    new_h[emp_idx, d2, s2] = 2
                else:
                    iteration += 1
                    continue

                # guard against T -> next-day M
                if d1 + 1 < self.num_days:
                    next_slots = [s for s in range(self.shifts) if new_h[emp_idx, d1 + 1, s] > 0]
                    if next_slots and next_slots[0] < s1:
                        iteration += 1
                        continue
                if d1 - 1 >= 0:
                    prev_slots = [s for s in range(self.shifts) if new_h[emp_idx, d1 - 1, s] > 0]
                    if prev_slots and s1 < prev_slots[0]:
                        iteration += 1
                        continue

                # same for d2
                if d2 + 1 < self.num_days:
                    next_slots = [s for s in range(self.shifts) if new_h[emp_idx, d2 + 1, s] > 0]
                    if next_slots and next_slots[0] < s2:
                        iteration += 1
                        continue
                if d2 - 1 >= 0:
                    prev_slots = [s for s in range(self.shifts) if new_h[emp_idx, d2 - 1, s] > 0]
                    if prev_slots and s2 < prev_slots[0]:
                        iteration += 1
                        continue


                c1, c2, c3, c4, c5 = self.criterios(new_h)
                new_score = c1 + c2 + c3 + c4 + c5

                if new_score < best_score:
                    horario = new_h
                    best_score = new_score
                    self.update_from_horario(horario)
                    print(f"Iteration {steps}: Improved score = {best_score}")

                    if best_score == 0:
                        print(f"Iteration {steps}: Perfect solution found with score = 0")
                        break

            iteration += 1

        print(f"Local Search Optimization completed after {steps} iterations. Final score = {best_score}")
        print(f"Execution time (hill climbing): {time.time() - start_hc:.2f} seconds")

    # ---------- scoring ----------

    def score(self, horario):
        c1, c2, c3, c4, c5 = self.criterios(horario)
        return c1 + c2 + c3 + c4 + c5

    def criterios(self, horario):
        return (
            self.criterio1(horario),
            self.criterio2(horario),
            self.criterio3(horario),
            self.criterio4(horario),
            self.criterio5(horario),
        )

    def criterio1(self, horario, max_consec=5):
        worked = (horario.sum(axis=2) > 0).astype(int)
        total_violation = 0
        for i in range(worked.shape[0]):
            run = 0
            for d in range(worked.shape[1]):
                if worked[i, d]:
                    run += 1
                else:
                    if run > max_consec:
                        total_violation += 1
                    run = 0
            if run > max_consec:
                total_violation += 1
        return total_violation

    def criterio2(self, horario):
        """
        Sum over employees of excess special days (Sundays+holidays) above 22.
        (Fixed accumulation: += instead of assignment.)
        """
        worked = (horario.sum(axis=2) > 0).astype(int)
        allowed = 22
        total_violation = 0
        special_days = set(self.holidays).union(self.sunday)
        for i in range(worked.shape[0]):
            num = 0
            for d in range(worked.shape[1]):
                if worked[i, d] and (d + 1) in special_days:
                    num += 1
            if num > allowed:
                total_violation += (num - allowed)  # <-- fix
        return total_violation

    def criterio3(self, horario):
        # days x shifts x teams
        num_teams = 2  # A,B — adjust if you ever support more
        counts = np.zeros((self.num_days, self.shifts, num_teams), dtype=int)

        n_emps = horario.shape[0]
        for p in range(n_emps):
            for d in range(self.num_days):
                for s in range(self.shifts):
                    t = horario[p, d, s]
                    if t > 0:
                        counts[d, s, t - 1] += 1

        shortage = 0
        for (day, shift, team), required in self.mins.items():
            assigned = counts[day - 1, shift - 1, team - 1]
            if assigned < required:
                shortage += (required - assigned)
        return int(shortage)

    def criterio4(self, horario, target_workdays=223):
        work = (horario.sum(axis=2) > 0).astype(int)
        diffs = np.abs(np.sum(work & ~self.vac_array, axis=1) - target_workdays)
        return int(np.sum(diffs))

    def criterio5(self, horario):
        violations = 0
        for i in range(horario.shape[0]):
            for d in range(self.num_days - 1):
                s_today = next((s for s in range(self.shifts) if horario[i, d, s] > 0), None)
                s_next  = next((s for s in range(self.shifts) if horario[i, d + 1, s] > 0), None)
                if s_today is not None and s_next is not None and s_next < s_today:
                    violations += 1
        return violations

    def identificar_equipes(self):
        equipe_A = [emp - 1 for emp in self.employees if 1 in self.teams[emp] and 2 not in self.teams[emp]]
        equipe_B = [emp - 1 for emp in self.employees if 2 in self.teams[emp] and 1 not in self.teams[emp]]
        ambas = [emp - 1 for emp in self.employees if 1 in self.teams[emp] and 2 in self.teams[emp]]
        return equipe_A, equipe_B, ambas

def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2):
    """
    vacations: rows like ['Employee 1','0','1',...]
    minimuns:  rows like ['Team_A','Minimum','M', ...]
    employees: list of dicts like {'teams': ['Team_A','Team_B']} in order → employee id
    """
    tag = "[Greedy Randomized + Hill Climbing]"
    print(f"{tag} Executando algoritmo")
    print(f"{tag} Número de funcionários: {len(employees)}")

    # guard year (TaskManager may pass None)
    year = int(year) if year is not None else 2025

    num_days = 365
    feriados = holidays.country_holidays("PT", years=[year])

    emp_ids = [i + 1 for i in range(len(employees))]
    vacs = rows_to_vac_dict(vacations)
    mins, ideals = rows_to_req_dicts(minimuns)
    teams = {idx + 1: [TEAM_LETTER_TO_ID[t[-1]] for t in e["teams"]] for idx, e in enumerate(employees)}

    scheduler = GreedyClimbing(
        employees=emp_ids,
        num_days=num_days,
        holidays_set=feriados,
        vacs=vacs,
        mins=mins,
        ideals=ideals,
        teams=teams,
        num_iter=10,
        maxTime=(int(maxTime) if maxTime else None),
        year=year,
        shifts=shifts,
    )

    # Build + evaluate + hill climb
    scheduler.build_schedule()
    initial_score = scheduler.score(scheduler.create_horario())
    print(f"{tag} Initial score: {initial_score}")
    scheduler.hill_climbing(maxTime=(int(maxTime) if maxTime else None))

    # Optional artifact
    export_schedule_to_csv(scheduler, "schedule_hybrid.csv", num_days=num_days)

    # Return table for TaskManager
    header = ["funcionario"] + [f"Dia {d}" for d in range(1, num_days + 1)]
    output = [header]
    label = {1: "M_", 2: "T_", 3: "N_"}
    for p in scheduler.employees:
        row = [p]
        assign = {day: (s, t) for (day, s, t) in scheduler.assignment[p]}
        vacation_days = set(vacs.get(p, []))
        for d in range(1, num_days + 1):
            if d in vacation_days:
                row.append("F")
            elif d in assign:
                s, t = assign[d]
                row.append(label.get(s, "") + ("A" if t == 1 else "B"))
            else:
                row.append("0")
        output.append(row)

    return output