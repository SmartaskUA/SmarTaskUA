import random
import pandas as pd
import numpy as np
import time
import holidays as hl
from collections import defaultdict
import csv
import io


class CombinedScheduler:
    def __init__(self, employees, num_days, holidays, vacs, mins, ideals, teams, num_iter=10):
        self.employees = employees   
        self.num_days = num_days     
        self.holidays = set(holidays)
        self.vacs = vacs   
        self.mins = mins     
        self.ideals = ideals         
        self.teams = teams           
        self.num_iter = num_iter
        self.assignment = defaultdict(list)    
        self.schedule_table = defaultdict(list)
        self.fds = np.zeros((len(self.employees), self.num_days), dtype=bool)
        self.fds[:, 4::7] = True

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

        sundays_and_holidays = sum(1 for (day, _, _) in assignments if day in self.holidays)
        if d in self.holidays:
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

    def hill_climbing(self):
        f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = self.calculate_criteria()

        t = 0
        cont = 0
        while t < 400000 and (np.any(f1_opt) or np.any(f2_opt) or np.any(f4_opt) or np.any(f5_opt)):
            cont += 1
            i = np.random.randint(len(self.employees))
            aux = np.random.choice(len(self.assignment[self.employees[i]]), 2, replace=False)
            d1, d2 = aux[0], aux[1]
            s1, s2 = np.random.choice([1, 2], 2, replace=False)

            if self.assignment[self.employees[i]][d1][s1] != self.assignment[self.employees[i]][d2][s2]:
                self.assignment[self.employees[i]][d1][s1], self.assignment[self.employees[i]][d2][s2] = self.assignment[self.employees[i]][d2][s2], self.assignment[self.employees[i]][d1][s1]

                f1, f2, f3, f4, f5 = self.calculate_criteria(self.schedule_table)

                if np.all(f1 == 0) and np.all(f2 == 0) and f3 == 0 and np.all(f4 == 0) and np.all(f5 == 0):
                    f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = f1, f2, f3, f4, f5
                    print("\nSolução ótima encontrada!")
                    break

                if f1[i] + f2[i] + f3 + f4[i] + f5[i] < f1_opt[i] + f2_opt[i] + f3_opt + f4_opt[i] + f5_opt[i]:
                    f1_opt[i], f2_opt[i], f3_opt, f4_opt[i], f5_opt[i], self.schedule_table = f1[i], f2[i], f3, f4[i], f5[i], self.schedule_table

            t += 1

    def create_horario(self):
        horario = np.zeros((len(self.employees), self.num_days, 2), dtype=int)  # 2 shifts per day (0: morning, 1: afternoon)

        for p, assignments in self.assignment.items():
            for d, s, t in assignments:
                shift_idx = s - 1  # shift 1 -> 0 (morning), shift 2 -> 1 (afternoon)
                horario[p - 1, d - 1, shift_idx] = t  # Assign the team (t) for the shift on that day

        return horario

    def calculate_criteria(self):
        horario = self.create_horario()
        f1 = criterio1(horario, 5)
        f2 = criterio2(horario, self.fds, 22, self.holidays)
        f3 = criterio3(horario, 2) 
        f4 = criterio4(horario, self.vacs) 
        f5 = criterio5(horario, self.teams)
        return f1, f2, f3, f4, f5

def criterio1(horario, nDiasSeguidos):
    f1 = np.zeros(horario.shape[0], dtype=int)                                               
    dias_trabalhados = np.sum(horario, axis=2) > 0                                           
    janela = np.ones(nDiasSeguidos, dtype=int)                                               
    for i in range(horario.shape[0]):
        sequencia = np.convolve(dias_trabalhados[i].astype(int), janela, mode='valid')       
        f1[i] = np.sum(sequencia == nDiasSeguidos)                                           

    return f1


def criterio2(horario, fds, nDiasTrabalhoFDS, feriados):
    dias_ano = np.arange(horario.shape[1])     
    dias_fds = fds.sum(axis=0) > 0                                              
    dias_feriados = np.isin(dias_ano, feriados)                                 
    dias_fds_feriados = dias_fds | dias_feriados                                
    dias_fds_feriados = dias_fds_feriados[None, :, None]                        
    dias_trabalhados = np.sum(horario * dias_fds_feriados, axis=(1, 2))       
    excedente = np.maximum(dias_trabalhados - nDiasTrabalhoFDS, 0)              
    return excedente

def criterio3(horario, nMinTrabs):
    trabalhadores_por_dia = np.sum(horario, axis=1)                                    
    dias_com_menos_trabalhadores = np.sum(trabalhadores_por_dia < nMinTrabs, axis=1)  
    return np.sum(dias_com_menos_trabalhadores)

def criterio4(horario, vacs):
    dias_trabalhados_por_trabalhador = []
    for i in range(horario.shape[0]): 
        dias_trabalhados = 0
        dias_trabalhados = np.sum(np.sum(horario[i, :] > 0, axis=1) & vacs[i, :])
        dias_trabalhados_por_trabalhador.append(dias_trabalhados)

    dias_diferenca = np.abs(np.array(dias_trabalhados_por_trabalhador) - 223)
    return dias_diferenca

def criterio5(horario, Prefs):
    f5 = np.zeros(horario.shape[0], dtype=int)
    
    for i, pref in enumerate(Prefs):  
        if any(p in pref for p in [0, 1]):  

            for d in range(365 - 1):
                if horario[i, d, 1] == 1 and horario[i, d + 1, 0] == 1:
                    f5[i] += 1
    return f5

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

def generate_schedule():
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

    scheduler = CombinedScheduler(employees, num_days, holidays, vacs, mins, ideals, teams)
    scheduler.build_schedule()    
    scheduler.hill_climbing()

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

if __name__ == "__main__":
    scheduler = generate_schedule()
    export_schedule_to_csv(scheduler, "schedule2.csv")
    print("Schedule generation complete.")


