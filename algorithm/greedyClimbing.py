import random
import pandas as pd
import numpy as np
import time
import holidays
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
        f1_opt, f2_opt, f3_opt, f4_opt, f5_opt = self.calculate_criteria(self.schedule_table)

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

    def calculate_criteria(self, schedule_table):
        pass


def generate_schedule():
    num_employees = 12
    employees = list(range(1, num_employees + 1))
    num_days = 365
    holidays = holidays.country_holidays("PT", years=[2025])
    
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
    # Export logic
    pass

