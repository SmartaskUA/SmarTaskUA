import copy
import random
import csv
import time
import os
import json

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints

def generate_initial_calendar():
    num_employees = 12
    num_days = 30
    employee_teams = {
        "E1": ["A"], "E2": ["A"], "E3": ["A"], "E4": ["A"],
        "E5": ["A", "B"], "E6": ["A", "B"], "E7": ["A"], "E8": ["A"],
        "E9": ["A"], "E10": ["B"], "E11": ["A", "B"], "E12": ["B"]
    }
    holidays = {7, 14, 21, 28}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    num_of_vacations = 4
    shifts = ["M", "T"]

    if os.path.exists("vacations.json"):
        with open("vacations.json", "r") as f:
            vacations = json.load(f)
            vacations = {emp: set(days) for emp, days in vacations.items()}
    else:
        vacations = {emp: set(random.sample(range(1, num_days + 1), num_of_vacations)) for emp in employees}
        with open("vacations.json", "w") as f:
            json.dump({emp: list(days) for emp, days in vacations.items()}, f, indent=2)

    variables = [f"{emp}_{day}_{shift}" for emp in employees for day in range(1, num_days + 1) for shift in shifts]

    def define_domain(emp):
        return [f"{t}" for t in employee_teams[emp]] + ["0"]

    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else define_domain(var.split('_')[0])
        for var in variables
    }

    calendar = {}
    for emp in employees:
        calendar[emp] = []
        for day in range(1, num_days + 1):
            m_var = f"{emp}_{day}_M"
            t_var = f"{emp}_{day}_T"
            if day in vacations[emp]:
                calendar[emp].append(("F", "F"))
            else:
                m_val = "0" if "0" in domains[m_var] else domains[m_var][0]
                t_val = "0" if "0" in domains[t_var] else domains[t_var][0]
                calendar[emp].append((m_val, t_val))

    with open("initial_calendar.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        header = ["Employee"] + [str(day) for day in range(1, num_days + 1)]
        csvwriter.writerow(header)
        for emp in employees:
            row = [emp]
            for m_val, t_val in calendar[emp]:
                row.append(f"{m_val},{t_val}")
            csvwriter.writerow(row)
    print("Full initial calendar saved to 'initial_calendar.csv'")

if __name__ == "__main__":
    generate_initial_calendar()