import random
import time
from collections import defaultdict

import numpy as np
import pandas as pd
import holidays as hl
import holidays

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

class GreedyClimbing:
    """
    Builds an initial schedule via greedy randomized assignment,
    then improves it via hill climbing (local search).
    """

    def __init__(self, employees, num_days, holidays_set, vacs, mins, ideals, teams,
                 num_iter=10, maxTime=None, year=2025, shifts=2, rules=None):
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
          - forbid next-day earlier shift (non-decreasing across days)
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

        # No earlier shift the next/previous day (e.g., T->M, N->T/M)
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

            # Prefer employees with fewer allowed teams (1, then 2, then >=3)
            P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 1]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 2]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) >= 3]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) > 0]
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

            if t1 != t2:
                new_h = horario.copy()
                allowed = set(self.teams[emp])

                # try swapping if both targets are allowed
                if (t2 in allowed) and (t1 in allowed):
                    new_h[emp_idx, d1, s1], new_h[emp_idx, d2, s2] = t2, t1
                else:
                    # fallbacks: keep only allowed teams, drop others to 0 (off)
                    new_h[emp_idx, d1, s1] = t2 if t2 in allowed else 0
                    new_h[emp_idx, d2, s2] = t1 if t1 in allowed else 0

                # guard against earlier next-day shift
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
                total_violation += (num - allowed)
        return total_violation

    def criterio3(self, horario):
        # days x shifts x teams
        team_ids = set()
        for ids in self.teams.values():
            team_ids.update(ids)
        team_ids.update(t for (_d, _s, t) in self.mins.keys())
        num_teams = (max(team_ids) if team_ids else 0)

        counts = np.zeros((self.num_days, self.shifts, num_teams), dtype=int)

        n_emps = horario.shape[0]
        for p in range(n_emps):
            for d in range(self.num_days):
                for s in range(self.shifts):
                    t = horario[p, d, s]  # this stores team_id or 0
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
        # map team_id -> list of employee indices (0-based) who can work that team
        all_team_ids = sorted({tid for ids in self.teams.values() for tid in ids})
        team_to_emps = {
            tid: [emp - 1 for emp in self.employees if tid in self.teams[emp]]
            for tid in all_team_ids
        }
        multi_team = [emp - 1 for emp in self.employees if len(self.teams[emp]) > 1]
        return team_to_emps, multi_team
    def audit_schedule(self):
        """
        Scans the built schedule and reports violations:
          - team eligibility (employee assigned to a team they can't work)
          - vacation blocks (worked on vacation day)
          - >5 consecutive days
          - backward shift transitions (earlier shift next day)
          - cap of 22 Sundays+holidays
          - cap of 223 total workdays
        Returns a dict with lists of issues; also prints a short report.
        """
        issues = {
            "team_eligibility": [],   # (emp, day, shift, team_id)
            "vacation_block": [],     # (emp, day)
            "max_consecutive_days": [],  # (emp, start_day, length)
            "backward_transition": [],   # (emp, day, shift_today, shift_next)
            "special_days_cap": [],      # (emp, count)
            "max_total_workdays": [],    # (emp, count)
        }

        # --- fast helpers ---
        special_days = set(self.holidays).union(self.sunday)  # 1-based days
        vacs = self.vacs                                      # {emp -> [days]}
        team_map = self.teams                                  # {emp -> [team_ids]}

        # Build easy lookup: first working shift per day for each emp
        worked_shift = {p: {} for p in self.employees}  # p -> {day: shift}
        for p in self.employees:
            for (d, s, t) in self.assignment[p]:
                worked_shift[p][d] = s

        # 1) team eligibility + vacation block
        for p in self.employees:
            allowed = set(team_map.get(p, []))
            vac_days = set(vacs.get(p, []))
            for (d, s, t) in self.assignment[p]:
                if t not in allowed:
                    issues["team_eligibility"].append((p, d, s, t))
                if d in vac_days:
                    issues["vacation_block"].append((p, d))

        # 2) >5 consecutive days
        for p in self.employees:
            days = sorted(set(d for (d, _s, _t) in self.assignment[p]))
            if not days:
                continue
            run_len = 1
            for i in range(1, len(days)):
                if days[i] == days[i-1] + 1:
                    run_len += 1
                else:
                    if run_len > 5:
                        issues["max_consecutive_days"].append((p, days[i-run_len], run_len))
                    run_len = 1
            if run_len > 5:
                issues["max_consecutive_days"].append((p, days[-run_len], run_len))

        # 3) backward shift transitions (earlier next day)
        for p in self.employees:
            for d in range(1, self.num_days):
                s_today = worked_shift[p].get(d)
                s_next  = worked_shift[p].get(d+1)
                if s_today is not None and s_next is not None and s_next < s_today:
                    issues["backward_transition"].append((p, d, s_today, s_next))

        # 4) caps: special days (22) and total workdays (223)
        for p in self.employees:
            worked_days = sorted(set(d for (d, _s, _t) in self.assignment[p]))
            total = len(worked_days)
            special = sum(1 for d in worked_days if d in special_days)
            if special > 22:
                issues["special_days_cap"].append((p, special))
            if total > 223:
                issues["max_total_workdays"].append((p, total))

        # --- pretty print summary ---
        def pr(label, items):
            print(f"[AUDIT] {label}: {len(items)}")
            for x in items[:20]:
                print("   ", x)
            if len(items) > 20:
                print("    ... (truncated)")

        print("\n=== SCHEDULE AUDIT ===")
        pr("Team eligibility violations (emp, day, shift, team_id)", issues["team_eligibility"])
        pr("Vacation day assignments (emp, day)", issues["vacation_block"])
        pr(">5 consecutive day runs (emp, start_day, run_length)", issues["max_consecutive_days"])
        pr("Backward shift transitions (emp, day, shift_today, shift_next)", issues["backward_transition"])
        pr("Special-days cap >22 (emp, count)", issues["special_days_cap"])
        pr("Total workdays >223 (emp, count)", issues["max_total_workdays"])
        print("======================\n")

        return issues
def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):
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
    teams = {}
    for idx, e in enumerate(employees):
        emp_id = idx + 1
        codes = [get_team_code(t) for t in e.get("teams", [])]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        teams[emp_id] = ids
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
    audit = scheduler.audit_schedule()

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
                row.append(label.get(s, "") + TEAM_ID_TO_CODE.get(t, str(t)))
            else:
                row.append("0")
        output.append(row)

    return output
