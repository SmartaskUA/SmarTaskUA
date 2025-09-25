import random
import time
from collections import defaultdict

import numpy as np
import holidays
from algorithm.rules_engine import RuleEngine
from algorithm.utils import (
    TEAM_ID_TO_CODE,
    get_team_id,
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    get_team_code,
)

class GreedyClimbing:
    """
    Greedy randomized construction + Hill Climbing.
    All feasibility goes through RuleEngine; f2 remains the greedy tie-breaker.
    """

    def __init__(
        self,
        employees,
        num_days,
        holidays_set,
        vacs,
        mins,
        ideals,
        teams,
        num_iter=10,
        maxTime=None,   # minutes
        year=2025,
        shifts=2,
        rules=None,
    ):
        self.employees = employees
        self.num_days = int(num_days)
        self.shifts = int(shifts)
        self.vacs = vacs
        self.mins = mins
        self.ideals = ideals
        self.teams = teams
        self.num_iter = int(num_iter)
        self.assignment = defaultdict(list)     # p -> [(day, shift, team)]
        self.schedule_table = defaultdict(list) # (day, shift, team) -> [p,...]
        self.year = int(year)

        # Calendar & special days
        self.dias_ano, self.sunday = build_calendar(self.year)
        start_date = self.dias_ano[0].date()
        self.holidays = {(d - start_date).days + 1 for d in holidays_set}

        # Vacation matrix
        self.vac_array = self._create_vacation_array()
        self.fds = np.zeros_like(self.vac_array, dtype=bool)
        for day in self.sunday:
            self.fds[:, day - 1] = True

        # Timing (minutes -> seconds)
        self.maxTime = (int(maxTime) * 60) if maxTime is not None else None
        self.start_time = None

        # Rule engine
        self.rule_engine = RuleEngine(
            rules=rules,
            employees=self.employees,
            num_days=self.num_days,
            shifts=self.shifts,
            teams=self.teams,
            vacation_array=self.vac_array,
            holidays_set=set(self.holidays),
            sunday_set=set(self.sunday),
        )
        self.rule_engine.set_mins_map(self.mins)

    # ---------- helpers ----------

    def _create_vacation_array(self):
        vac_array = np.zeros((len(self.employees), self.num_days), dtype=bool)
        for emp in self.employees:
            for day in self.vacs.get(emp, []):
                vac_array[emp - 1, day - 1] = True
        return vac_array

    # ---------- feasibility (engine-backed) ----------

    def f1(self, p, d, s):
        # keep the name/signature; only a cheap prefilter (vacation)
        return not self.vac_array[p - 1, d - 1]

    def f2(self, d, s, t):
        """
        Lower is better.
          0 -> below minimum
          1 -> between min and ideal
          2+k -> at/above ideal by k
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

    # ---------- greedy construction (fixed to consider ALL shifts before pruning a day) ----------

    def build_schedule(self):
        self.start_time = time.time()
        all_days = set(range(1, self.num_days + 1))
        stalled = set()

        while not self.is_complete():
            if self.maxTime is not None and time.time() - self.start_time >= self.maxTime:
                print("[Greedy] Maximum time reached, stopping generation.")
                break

            # choose an employee who still needs days and isn't stalled
            eligible = [p for p in self.employees if len(self.assignment[p]) < 223 and p not in stalled]
            if not eligible:
                break
            # bias toward fewer allowed teams to reduce future bottlenecks
            eligible.sort(key=lambda p: len(self.teams[p]))
            p = random.choice(eligible[:max(1, len(eligible)//3)])

            used_days = {day for (day, _, _) in self.assignment[p]}
            vacation_days = set(self.vacs.get(p, []))
            available_days = [d for d in all_days if d not in used_days and d not in vacation_days]
            if not available_days:
                stalled.add(p)
                continue

            best = None
            best_val = float("inf")

            # FULL search over (day, shift, team) for this employee; early-accept f2==0
            for d in available_days:
                # cheap prefilter
                # (we don’t remove the day if one shift fails; we try ALL shifts first)
                for s in range(1, self.shifts + 1):
                    if not self.f1(p, d, s):
                        continue
                    for t in self.teams[p]:
                        if not self.rule_engine.can_assign(p, d, s, t, self.assignment):
                            continue
                        val = self.f2(d, s, t)
                        if val < best_val:
                            best_val = val
                            best = (d, s, t)
                            if best_val == 0:  # perfect wrt coverage; take it
                                break
                    if best_val == 0:
                        break
                if best_val == 0:
                    break

                # time check inside the heavy loop
                if self.maxTime is not None and time.time() - self.start_time >= self.maxTime:
                    print("[Greedy] Maximum time reached during inner search.")
                    break

            if best:
                d, s, t = best
                self.assignment[p].append((d, s, t))
                self.schedule_table[(d, s, t)].append(p)
                # if we just placed, make sure p isn't considered stalled
                if p in stalled:
                    stalled.remove(p)
            else:
                # nothing feasible right now for this employee
                stalled.add(p)

            # if everyone left is stalled, we’re done
            if all((len(self.assignment[p]) >= 223) or (p in stalled) for p in self.employees):
                break

    def is_complete(self):
        return all(len(self.assignment[p]) >= 223 for p in self.employees)

    def create_horario(self):
        horario = np.zeros((len(self.employees), self.num_days, self.shifts), dtype=int)
        for p in self.employees:
            for d, s, t in self.assignment[p]:
                horario[p - 1, d - 1, s - 1] = t
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

    # ---------- hill climbing (unchanged feasibility via engine) ----------

    def _engine_move_ok(self, emp, new_h, d1, s1, d2, s2):
        emp_idx = emp - 1
        temp_assign = {k: list(v) for k, v in self.assignment.items()}

        # remove original placements at these (day,shift) coordinates for emp
        filtered = []
        for (dd, ss, tt) in temp_assign.get(emp, []):
            if not ((dd - 1, ss - 1) == (d1, s1) or (dd - 1, ss - 1) == (d2, s2)):
                filtered.append((dd, ss, tt))
        temp_assign[emp] = filtered

        # add tentative placements if >0
        t1 = new_h[emp_idx, d1, s1]
        t2 = new_h[emp_idx, d2, s2]

        if t1 > 0:
            if not self.rule_engine.can_assign(emp, d1 + 1, s1 + 1, t1, temp_assign):
                return False
            temp_assign[emp].append((d1 + 1, s1 + 1, t1))

        if t2 > 0:
            if not self.rule_engine.can_assign(emp, d2 + 1, s2 + 1, t2, temp_assign):
                return False

        return True

    def hill_climbing(self, max_iterations=400000, max_seconds=None):
        start_hc = time.time()
        horario = self.create_horario()

        f1, f2, f3, f4, f5 = self.criterios(horario)
        best_score = f1 + f2 + f3 + f4 + f5

        iteration = 0
        steps = 0

        while iteration < max_iterations and best_score > 0:
            steps += 1
            if max_seconds is not None and (time.time() - start_hc) >= max_seconds:
                print("[HC] Maximum time reached, stopping optimization.")
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
            if t1 == t2:
                iteration += 1
                continue

            new_h = horario.copy()
            allowed = set(self.teams[emp])

            # swap if both allowed; otherwise drop disallowed to 0 (off)
            if (t2 in allowed) and (t1 in allowed):
                new_h[emp_idx, d1, s1], new_h[emp_idx, d2, s2] = t2, t1
            else:
                new_h[emp_idx, d1, s1] = t2 if t2 in allowed else 0
                new_h[emp_idx, d2, s2] = t1 if t1 in allowed else 0

            # quick monotone shift guards
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

            # engine feasibility for tentative move
            if not self._engine_move_ok(emp, new_h, d1, s1, d2, s2):
                iteration += 1
                continue

            # score with your criterios
            c1, c2, c3, c4, c5 = self.criterios(new_h)
            new_score = c1 + c2 + c3 + c4 + c5

            if new_score < best_score:
                horario = new_h
                best_score = new_score
                self.update_from_horario(horario)
                print(f"[HC] Iteration {steps}: Improved score = {best_score}")
                if best_score == 0:
                    print(f"[HC] Iteration {steps}: Perfect solution found (score = 0)")
                    break

            iteration += 1

        print(f"[HC] Completed after {steps} iterations. Final score = {best_score}")
        print(f"[HC] Execution time: {time.time() - start_hc:.2f} seconds")

    # ---------- scoring (unchanged) ----------

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
                s_next = next((s for s in range(self.shifts) if horario[i, d + 1, s] > 0), None)
                if s_today is not None and s_next is not None and s_next < s_today:
                    violations += 1
        return violations

    # ---------- utils ----------

    def identificar_equipes(self):
        all_team_ids = sorted({tid for ids in self.teams.values() for tid in ids})
        team_to_emps = {
            tid: [emp - 1 for emp in self.employees if tid in self.teams[emp]]
            for tid in all_team_ids
        }
        multi_team = [emp - 1 for emp in self.employees if len(self.teams[emp]) > 1]
        return team_to_emps, multi_team


def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):
    tag = "[Greedy Randomized + Hill Climbing]"
    print(f"{tag} Executando algoritmo")
    print(f"{tag} Número de funcionários: {len(employees)}")

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
        maxTime=(int(maxTime) if maxTime else None),  # minutes
        year=year,
        shifts=shifts,
        rules=rules,
    )

    scheduler.build_schedule()
    sec = (int(maxTime) * 60) if maxTime else None
    scheduler.hill_climbing(max_seconds=sec)

    export_schedule_to_csv(scheduler, "schedule_hybrid.csv", num_days=num_days)

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
