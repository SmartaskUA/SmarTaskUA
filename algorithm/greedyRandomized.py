import random
from collections import defaultdict
import holidays
from datetime import date, timedelta
import csv
import time
import pandas as pd
import numpy as np
import os

TEAM_LETTER_TO_ID = {'A': 1, 'B': 2}

class GreedyRandomized:
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

def schedule():
    num_employees = 12
    employees = list(range(1, num_employees + 1))
    num_days = 365  
    holiDays = holidays.country_holidays("PT", years=[2025])

    vacations_file = os.path.join(os.path.dirname(__file__), "feriasA.csv")
    vacs = parse_vacs(vacations_file)
    minimuns_file = os.path.join(os.path.dirname(__file__), "minimuns.csv")
    mins, ideals = parse_requirements(minimuns_file)

    print(f"Employees: {employees}")
    print(f"Vacations: {vacs}")
    print(f"Minimuns: {mins}")
    print(f"Ideals: {ideals}")
    teams = {
        1: [1], 2: [1], 3: [1], 4: [1],
        5: [1, 2], 6: [1, 2], 7: [1], 8: [1],
        9: [1], 10: [2], 11: [2, 1], 12: [2]
    }

    start_time = time.time()
    scheduler = GreedyRandomized(employees, num_days, holiDays, vacs, mins, ideals, teams)
    scheduler.build_schedule()
    end_time = time.time()

    print(f"Execution time: {end_time - start_time:.2f} seconds")
    print("Schedule generation complete.")
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
                    if shift == 1:
                        row.append(f"M_{'A' if team == 1 else 'B'}")
                    else:
                        row.append(f"T_{'A' if team == 1 else 'B'}")
                else:
                    row.append("0")

            writer.writerow(row)

    print(f"Schedule exported to {filename}")

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
                        minimos[(dia, equipa, turno)] = valor_int
                    else:
                        ideais[(dia, equipa, turno)] = valor_int
                except ValueError:
                    continue 

    return minimos, ideais


def solve(vacations, minimuns, employees, maxTime=10):
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
        

    scheduler = GreedyRandomized(
        employees=emp,
        num_days=num_days,
        holidays=feriados,
        vacs=vacs,
        mins=mins,
        ideals=ideals,
        teams=teams,
        num_iter=10
    )
    scheduler.build_schedule()

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


scheduler = schedule()
export_schedule_to_csv(scheduler)
