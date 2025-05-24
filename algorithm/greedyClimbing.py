import random
import pandas as pd
import numpy as np
import time
import holidays as hl
from collections import defaultdict
import csv
import io
import holidays

TEAM_LETTER_TO_ID = {'A': 1, 'B': 2}

class GreedyClimbing:
    def __init__(self, employees, num_days, holidays, vacs, mins, ideals, teams, num_iter=10):
        self.employees = employees   
        self.num_days = num_days     
        self.vacs = vacs   
        self.mins = mins     
        self.ideals = ideals         
        self.teams = teams           
        self.num_iter = num_iter
        self.assignment = defaultdict(list)    
        self.schedule_table = defaultdict(list)
        self.ano = 2025
        self.dias_ano = pd.date_range(start=f'{self.ano}-01-01', end=f'{self.ano}-12-31').to_list()
        start_date = self.dias_ano[0].date()
        self.holidays = {(d - start_date).days + 1 for d in holidays}
        self.sunday = [d.dayofyear for d in self.dias_ano if d.weekday() == 6]
        self.vac_array = self._create_vacation_array()
        self.fds = np.zeros_like(self.vac_array)
        for day in self.sunday:
            self.fds[:, day-1] = True

    def _create_vacation_array(self):
        vac_array = np.zeros((len(self.employees), self.num_days), dtype=bool)
        for emp in self.employees:
            for day in self.vacs.get(emp, []):
                vac_array[emp - 1, day - 1] = True
        return vac_array

    def f1(self, p, d, s):
        assignments = self.assignment[p]
        days = sorted([day for (day, _, _) in assignments] + [d])
        count = 1
        for i in range(1, len(days)):
            if days[i] == days[i-1] + 1:
                count += 1
                if count > 5:
                    return False
            else:
                count = 1
                
        special_days = set(self.holidays).union(self.sunday)
        sundays_and_holidays = sum(1 for (day, _, _) in assignments if day in special_days)
        if d in special_days:
            sundays_and_holidays += 1
        if sundays_and_holidays > 22:
            return False
        for (day, shift, _) in assignments:
            if shift == 2 and day + 1 == d and s == 1:
                return False
            if shift == 1 and day - 1 == d and s == 2:
                return False
        return True

    def f2(self, d, s, t):
        current = len(self.schedule_table[(d, s, t)])
        min_required = self.mins.get((d, s, t), 0)
        ideal_required = self.ideals.get((d, s, t), min_required)

        if current < min_required:
            return 0
        elif current < ideal_required:
            return 1
        else:
            return 2 + (current - ideal_required)

    def build_schedule(self):
        all_days = set(range(1, self.num_days + 1))

        while not self.is_complete():
            P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 1]
            if not P:
                P = [p for p in self.employees if len(self.assignment[p]) < 223 and len(self.teams[p]) == 2]

            if not P:
                break

            p = random.choice(P)
            f_value = float('inf')
            count = 0
            best = None
            available_days = list(all_days - {day for (day, _, _) in self.assignment[p]} - set(self.vacs.get(p, [])))

            while f_value > 0 and count < self.num_iter and available_days:
                d = random.choice(available_days)
                s = random.choice([1, 2])

                if self.f1(p, d, s):
                    count += 1
                    for t in self.teams[p]:
                        f_aux = self.f2(d, s, t)
                        if f_aux < f_value:
                            f_value = f_aux
                            best = (d, s, t)

            if best:
                d, s, t = best
                self.assignment[p].append((d, s, t))
                self.schedule_table[(d, s, t)].append(p)

    def is_complete(self):
        return all(len(self.assignment[p]) >= 223 for p in self.employees)

    def create_horario(self):
        horario = np.zeros((len(self.employees), self.num_days, 2), dtype=int)
        for p in self.employees:
            for d, s, t in self.assignment[p]:
                shift_idx = s - 1  # shift 1 -> morning (0), shift 2 -> afternoon (1)
                horario[p - 1, d - 1, shift_idx] = t
        return horario

    def update_from_horario(self, horario):
        self.assignment.clear()
        self.schedule_table.clear()
        for p_idx, emp in enumerate(self.employees):
            for d in range(self.num_days):
                for s in range(2):
                    t = horario[p_idx, d, s]
                    if t > 0:
                        self.assignment[emp].append((d + 1, s + 1, t))
                        self.schedule_table[(d + 1, s + 1, t)].append(emp)

    def hill_climbing(self, max_iterations=400000, maxTime=60):
        maxTime = maxTime * 60  # Convert minutes to seconds
        start_time = time.time()
        horario = self.create_horario()
        f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = self.criterios(horario)
        best_score = f1_opt + f2_opt + f3_opt + f4_opt + f5_opt
        iteration = 0
        cont = 0  # Track actual iterations with swap attempts
        perfect_solution = False

        while iteration < max_iterations and best_score > 0:
            cont += 1
            if time.time() - start_time > maxTime:
                print("Tempo máximo atingido, parando a otimização.")
                break

            emp_idx = np.random.randint(len(self.employees))
            emp = self.employees[emp_idx]

            available_days = [d for d in range(self.num_days) if not self.vac_array[emp_idx, d]]
            if len(available_days) < 2:
                iteration += 1
                continue

            d1, d2 = np.random.choice(available_days, 2, replace=False)
            s1, s2 = np.random.choice([0, 1], 2, replace=False)

            t1 = horario[emp_idx, d1, s1]
            t2 = horario[emp_idx, d2, s2]

            can_work_team_A = 1 in self.teams[emp]
            can_work_team_B = 2 in self.teams[emp]

            if t1 != t2:
                new_horario = horario.copy()
                if can_work_team_A and can_work_team_B:
                    new_horario[emp_idx, d1, s1], new_horario[emp_idx, d2, s2] = t2, t1
                elif can_work_team_A:
                    new_horario[emp_idx, d1, s1] = 1
                    new_horario[emp_idx, d2, s2] = 0
                elif can_work_team_B:
                    new_horario[emp_idx, d1, s1] = 0
                    new_horario[emp_idx, d2, s2] = 2
                else:
                    iteration += 1
                    continue

                # Check forbidden shift sequences
                if s1 == 1 and d1 + 1 < self.num_days and new_horario[emp_idx, d1 + 1, 0] > 0:
                    iteration += 1
                    continue
                if s2 == 1 and d2 + 1 < self.num_days and new_horario[emp_idx, d2 + 1, 0] > 0:
                    iteration += 1
                    continue
                if s1 == 0 and d1 > 0 and new_horario[emp_idx, d1 - 1, 1] > 0:
                    iteration += 1
                    continue
                if s2 == 0 and d2 > 0 and new_horario[emp_idx, d2 - 1, 1] > 0:
                    iteration += 1
                    continue

                f1, f2, f3, f4, f5 = self.criterios(new_horario)
                new_score = f1 + f2 + f3 + f4 + f5

                if f1 == 0 and f2 == 0 and f3 == 0 and f4 == 0 and f5 == 0:
                    horario = new_horario
                    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt= f1, f2, f3, f4, f5
                    best_score = new_score
                    self.update_from_horario(horario)
                    print(f"Iteration {cont}: Perfect solution found with score = {best_score}")
                    perfect_solution = True
                    break

                if new_score < best_score:
                    horario = new_horario
                    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = f1, f2, f3, f4, f5
                    best_score = new_score
                    self.update_from_horario(horario)
                    print(f"Iteration {cont}: Improved score = {best_score}")
                else:
                    print(f"Iteration {cont}: No improvement, score = {best_score}")

            iteration += 1

        execution_time = time.time() - start_time
        print(f"Local Search Optimization completed after {cont} iterations. Final score = {best_score}")
        print(f"Execution time: {execution_time:.2f} seconds")

    def score(self, horario):
        c1, c2, c3, c4, c5 = self.criterios(horario)
        return c1 + c2 + c3 + c4 + c5
    
    def criterios(self, horario):
        f1 = self.criterio1(horario)
        f2 = self.criterio2(horario)
        f3 = self.criterio3(horario)
        f4 = self.criterio4(horario)
        f5 = self.criterio5(horario)
        print(f"f1: {f1}, f2: {f2}, f3: {f3}, f4: {f4}, f5: {f5}")
        return f1, f2, f3, f4, f5

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
                if worked[i, d] and d + 1 in special_days:
                    num += 1
            if num > allowed:
                total_violation = num - allowed
        return total_violation

    def criterio3(self, horario):
        counts = np.zeros((self.num_days, 2, 2)).astype(int)
        n_emps = horario.shape[0]
        for p in range(n_emps):
            for d in range(self.num_days):
                for s in (0, 1):
                    t = horario[p, d, s]
                    if t > 0:
                        counts[d, s, t-1] += 1

        shortage = 0
        for (day, shift, team), required in self.mins.items():
            d_idx = day - 1
            s_idx = shift - 1
            t_idx = team - 1
            assigned = counts[d_idx, s_idx, t_idx]
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
                if horario[i, d, 1] > 0 and horario[i, d+1, 0] > 0:
                    violations += 1
        return violations
    
    def identificar_equipes(self):
        equipe_A = [emp - 1 for emp in self.employees if 1 in self.teams[emp] and 2 not in self.teams[emp]]
        equipe_B = [emp - 1 for emp in self.employees if 2 in self.teams[emp] and 1 not in self.teams[emp]]
        ambas = [emp - 1 for emp in self.employees if 1 in self.teams[emp] and 2 in self.teams[emp]]
        return equipe_A, equipe_B, ambas

def parse_vacs(file_path):
    vacs = {}
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row[0].startswith("Employee"):
                emp_id = int(row[0].split()[1])
                vacs[emp_id] = [i + 1 for i, val in enumerate(row[1:]) if val.strip() == "1"]
    return vacs

def parse_requirements(file_path):
    minimos = {}
    ideais = {}
    with open(file_path, newline='', encoding='ISO-8859-1') as f:
        reader = list(csv.reader(f))
        dias_colunas = list(range(1, len(reader[0]) - 3 + 1))
        linhas_requisitos = {
            ("A", 1, "Minimo"): 1,
            ("A", 2, "Minimo"): 3,
            ("B", 1, "Minimo"): 5,
            ("B", 2, "Minimo"): 7,
            ("A", 1, "Ideal"): 2,
            ("A", 2, "Ideal"): 4,
            ("B", 1, "Ideal"): 6,
            ("B", 2, "Ideal"): 8
        }
        for (equipa, turno, tipo), linha_idx in linhas_requisitos.items():
            valores = reader[linha_idx][3:]
            for dia, valor in zip(dias_colunas, valores):
                try:
                    valor_int = int(valor)
                    if tipo == "Minimo":
                        minimos[(dia, turno, 1 if equipa == "A" else 2)] = valor_int
                    else:
                        ideais[(dia, turno, 1 if equipa == "A" else 2)] = valor_int
                except ValueError:
                    continue
    return minimos, ideais

def generate_schedule(maxTime=60):
    num_employees = 12
    employees = list(range(1, num_employees + 1))
    num_days = 365
    holidays = hl.country_holidays("PT", years=[2025])

    vacs = parse_vacs("horarioReferencia.csv")
    mins, ideals = parse_requirements("minimuns.csv")

    teams = {
        1: [1], 2: [1], 3: [1], 4: [1],
        5: [1, 2], 6: [1, 2], 7: [1], 8: [1],
        9: [1], 10: [2], 11: [2, 1], 12: [2]
    }

    start_time = time.time()
    scheduler = GreedyClimbing(employees, num_days, holidays, vacs, mins, ideals, teams)
    scheduler.build_schedule()
    export_schedule_to_csv(scheduler, "schedule1.csv")
    score = scheduler.score(scheduler.create_horario())
    print("Initial solution criteria:")
    print(f"Score: {score}")
    scheduler.hill_climbing(maxTime=maxTime)
    end_time = time.time()

    print(f"Execution time: {end_time - start_time:.2f} seconds")
    return scheduler

def export_schedule_to_csv(scheduler, filename="schedule.csv"):
    header = ["funcionario"] + [f"Dia {i+1}" for i in range(365)]
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        for emp in scheduler.employees:
            row = [emp]
            day_assignments = {day: (shift, team) for (day, shift, team) in scheduler.assignment[emp]}
            vacation_days = set(scheduler.vacs.get(emp, []))
            for day_num in range(1, 366):
                if day_num in vacation_days:
                    row.append("F")
                elif day_num in day_assignments:
                    shift, team = day_assignments[day_num]
                    row.append(f"{'M' if shift == 1 else 'T'}_{'A' if team == 1 else 'B'}")
                else:
                    row.append("0")
            writer.writerow(row)
    print(f"Schedule exported to {filename}")

def solve(vacations, minimuns, employees, maxTime=None):
    print(f"[GreedyRandomized] Executando Greedy Randomized Scheduling")
    num_employees = len(employees)
    print(f"[GreedyRandomized] Número de funcionários: {num_employees}")
    num_days = 365
    feriados = holidays.country_holidays("PT", years=[2025])

    emp = [i + 1 for i in range(len(employees))]
    vacs      = rows_to_vac_dict(vacations)
    mins, ideals = rows_to_req_dicts(minimuns)

    teams = {idx + 1: [TEAM_LETTER_TO_ID[t[-1]]  
                       for t in e["teams"]]
             for idx, e in enumerate(employees)}
        

    scheduler = GreedyClimbing(
        employees=emp,
        num_days=num_days,
        holidays=feriados,
        vacs=vacs,
        mins=mins,
        ideals=ideals,
        teams=teams,
        num_iter=10,
        maxTime=maxTime
    )
    scheduler.build_schedule()
    score = scheduler.score(scheduler.create_horario())
    print("Initial solution criteria:")
    print(f"Score: {score}")
    scheduler.hill_climbing(maxTime=maxTime)
    export_schedule_to_csv(scheduler, "schedule_hybrid.csv")

    header = ["funcionario"] + [f"Dia {d}" for d in range(1, num_days + 1)]
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
                suffix = "A" if t == 1 else "B"
                row.append(("M_" if s == 1 else "T_") + suffix)
            else:
                row.append("0")
        output.append(row)

    return output

def rows_to_vac_dict(vac_rows):
    vacs = {}
    for row in vac_rows:
        emp_id = int(row[0].split()[-1])
        vacs[emp_id] = [
            idx + 1  
            for idx, bit in enumerate(row[1:])
            if bit.strip() == '1'
        ]
    return vacs


def rows_to_req_dicts(req_rows):
    mins, ideals = {}, {}

    for row in req_rows:
        team_label, kind, shift_code, *counts = row

        team_id  = TEAM_LETTER_TO_ID[team_label[-1]]
        shift    = 1 if shift_code.strip().upper() == 'M' else 2
        target   = mins if kind.lower().startswith('min') else ideals

        for day, value in enumerate(counts, start=1):
            if value.strip(): 
                target[(day, shift, team_id)] = int(value)
    return mins, ideals

if __name__ == "__main__":
    scheduler = generate_schedule(maxTime=60)
    export_schedule_to_csv(scheduler, "schedule_hybrid.csv")
    print("Schedule generation complete.")