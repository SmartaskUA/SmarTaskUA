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

    if os.path.exists("vacations.json"):
        with open("vacations.json", "r") as f:
            vacations = json.load(f)
            vacations = {emp: set(days) for emp, days in vacations.items()}
    else:
        vacations = {emp: set(random.sample(range(1, num_days + 1), num_of_vacations)) for emp in employees}
        with open("vacations.json", "w") as f:
            json.dump({emp: list(days) for emp, days in vacations.items()}, f, indent=2)

    variables = [f"{emp}_{d}" for emp in employees for d in range(1, num_days + 1)]

    def define_domain(emp):
        return [f"M_{t}" for t in employee_teams[emp]] + [f"T_{t}" for t in employee_teams[emp]] + ["0"]

    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else define_domain(var.split('_')[0])
        for var in variables
    }

    calendar = {}
    for emp in employees:
        calendar[emp] = []
        for day in range(1, num_days + 1):
            if day in vacations[emp]:
                calendar[emp].append("FF")
            else:
                calendar[emp].append("00")

    with open("initial_calendar.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        col_width = 5
        first_col_width = 6
        header = ["dia".ljust(first_col_width)] + [f"|{str(day).ljust(col_width-2)}" for day in range(1, num_days + 1)] + ["|"]
        csvwriter.writerow(header)
        subheader = ["turno".ljust(first_col_width)] + [f"|{'MT'.ljust(col_width-2)}" for _ in range(num_days)] + ["|"]
        csvwriter.writerow(subheader)
        for emp in employees:
            emp_id = emp.lower().replace("E", "e")
            row = [emp_id.ljust(first_col_width)] + [f"| {shift.ljust(col_width-3)}" for shift in calendar[emp]] + ["|"]
            csvwriter.writerow(row)
    print("Full initial calendar saved to 'initial_calendar.csv'")

    return variables, domains, employee_teams, employees, num_days, num_employees, holidays

if __name__ == "__main__":
    variables, domains, employee_teams, employees, num_days, num_employees, holidays = generate_initial_calendar()