import copy
import random
import csv
import time
import string
import os
import json

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints

    def is_consistent(self, assignment):
        for key, func in self.constraints.items():
            if isinstance(key, tuple):
                if len(key) == 2:
                    if not func(assignment[key[0]], assignment[key[1]]):
                        return False
                else:
                    if not func([assignment[v] for v in key]):
                        return False
            else:
                if not func(None, assignment):
                    return False
        return True

    def check_constraints(self, var, value, assignment):
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        for constraint_key, constraint_func in self.constraints.items():
            if isinstance(constraint_key, tuple):
                if len(constraint_key) == 2:
                    v1, v2 = constraint_key
                    if v1 in temp_assignment and v2 in temp_assignment:
                        val1 = temp_assignment[v1]
                        val2 = temp_assignment[v2]
                        if not constraint_func(val1, val2):
                            print(f"Constraint failed for {v1}={val1}, {v2}={val2}")
                            return False
                else:
                    values = [temp_assignment.get(v) for v in constraint_key]
                    if None not in values and not constraint_func(values):
                        print(f"Higher-order constraint failed for {constraint_key}")
                        return False
            else:
                if not constraint_func(var, temp_assignment):
                    print(f"Single constraint failed for {var}={value}")
                    return False
        return True

    def propagate(self, domains, var, value):
        domains[var] = [value]
        queue = [var]
        while queue:
            curr_var = queue.pop(0)
            current_assignment = {v: d[0] for v, d in domains.items() if len(d) == 1}
            for other_var in self.variables:
                if other_var == curr_var or len(domains[other_var]) == 1:
                    continue
                new_domain = []
                for val in domains[other_var]:
                    if self.check_constraints(other_var, val, {**current_assignment, other_var: val}):
                        new_domain.append(val)
                if not new_domain:
                    return False
                if len(new_domain) < len(domains[other_var]):
                    domains[other_var] = new_domain
                    if len(new_domain) == 1:
                        queue.append(other_var)
        return True

    def select_variable(self, domains):
        unassigned_vars = [v for v in domains if len(domains[v]) > 1]
        if not unassigned_vars:
            return None
        return min(unassigned_vars, key=lambda var: len(domains[var]))

    def search(self, domains=None, timeout=300):
        start_time = time.time()
        if domains is None:
            domains = copy.deepcopy(self.domains)

        def timed_search(domains, depth=0):
            if time.time() - start_time > timeout:
                print(f"\nExited at the timeout of {timeout} s")
                return None
            if any(len(lv) == 0 for lv in domains.values()):
                return None
            if all(len(lv) == 1 for lv in domains.values()):
                assignment = {v: lv[0] for v, lv in domains.items()}
                if self.is_consistent(assignment):
                    return {"assignment": assignment}
                return None
            var = self.select_variable(domains)
            if var is None:
                return None
            print(f"Depth {depth}: Selecting {var} with domain {domains[var]}")
            values = domains[var].copy()
            random.shuffle(values)  # Randomize value order
            for val in values:
                new_domains = copy.deepcopy(domains)
                new_domains[var] = [val]
                if self.propagate(new_domains, var, val):
                    solution = timed_search(new_domains, depth + 1)
                    if solution is not None:
                        return solution
            return None

        return timed_search(domains)

def employee_scheduling():
    tic = time.time()
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

    constraints = {
        (v1, v2): (lambda x1, x2: not (x1.startswith("T_") and x2.startswith("M_")))
        for v1 in variables for v2 in variables
        if v1.split('_')[0] == v2.split('_')[0] and int(v1.split('_')[1]) + 1 == int(v2.split('_')[1])
    }

    csp = CSP(variables, domains, constraints)

    for emp in employees:
        emp_vars = [f"{emp}_{d}" for d in range(1, num_days + 1)]
        for start in range(num_days - 5):
            window_vars = emp_vars[start:start + 6]
            handle_ho_constraint(csp, window_vars, lambda values: not all(v in ["M_A", "M_B", "T_A", "T_B"] for v in values))
        handle_ho_constraint(csp, emp_vars, lambda values: sum(1 for v in values if v in ["M_A", "M_B", "T_A", "T_B"]) <= 20)
        holiday_vars = [var for var in emp_vars if int(var.split('_')[1]) in holidays]
        handle_ho_constraint(csp, holiday_vars, lambda values: sum(1 for v in values if v in ["M_A", "M_B", "T_A", "T_B"]) <= 2)

    solution = csp.search(timeout=600)
    if solution and "assignment" in solution:
        assignment = solution["assignment"]
        generate_calendar(assignment, num_employees, num_days)
        toc = time.time()
        print(f"Execution time: {toc - tic:.2f} seconds")        
        analyze_solution(assignment, employees, num_days, holidays)
        return build_schedule_table(assignment, num_employees, num_days)
    else:
        print("No solution found within timeout or constraints too restrictive.")
        return None

# def handle_ho_constraint(csp, variables, constraint_func):
#     def constraint(values):
#         return constraint_func(values)
#     csp.constraints[tuple(variables)] = constraint

# def handle_ho_constraint(csp, variables, constraint_func):
#     def constraint(var, assignment):
#         values = [assignment.get(v, None) for v in variables]
#         if None in values:
#             return True
#         return constraint_func(values)
#     constraint_key = f"multi_{'_'.join(variables)}"
#     csp.constraints[constraint_key] = constraint

def handle_ho_constraint(csp, variables, constraint_func):
    csp.constraints[tuple(variables)] = lambda values: constraint_func(values)

def build_schedule_table(assignment, num_employees, num_days):
    table = []
    header = ["Employee"] + [str(day) for day in range(1, num_days + 1)]
    table.append(header)
    for e in range(1, num_employees + 1):
        row = [f"E{e}"]
        for d in range(1, num_days + 1):
            row.append(assignment.get(f"E{e}_{d}", "-"))
        table.append(row)
    return table

def generate_calendar(assignment, num_employees, num_days):
    with open("csp_fourth_run.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Employee"] + [str(day) for day in range(1, num_days + 1)])
        for e in range(1, num_employees + 1):
            employee_schedule = [assignment.get(f"E{e}_{d}", "-") for d in range(1, num_days + 1)]
            csvwriter.writerow([f"E{e}"] + employee_schedule)

def analyze_solution(assignment, employees, num_days, holidays, filename="csp_fourth_run.txt"):
    MORNING = {"M_A", "M_B"}
    AFTERNOON = {"T_A", "T_B"}
    WORK = MORNING | AFTERNOON
    lines = []
    tm_violations = 0

    for emp in employees:
        for d in range(1, num_days):
            curr_day = assignment.get(f"{emp}_{d}", "-")
            next_day = assignment.get(f"{emp}_{d+1}", "-")
            if curr_day.startswith("T_") and next_day.startswith("M_"):
                tm_violations += 1
    lines.append(f"\nNumber of T->M restriction violations: {tm_violations}")

    lines.append("\nWorkdays on holidays per employee:")
    holiday_counts   = {} 
    shifts = [] 

    for emp in employees:
        holiday_workdays = sum(
            1
            for d in holidays
            if assignment.get(f"{emp}_{d}", "-") in WORK
        )
        holiday_counts[emp] = holiday_workdays
        lines.append(f"{emp}: {holiday_workdays} workdays on holidays")

        morning = afternoon = 0
        for d in range(1, num_days + 1):
            v = assignment.get(f"{emp}_{d}", "-")
            if v in MORNING:
                morning += 1
            elif v in AFTERNOON:
                afternoon += 1
        shifts.append((emp, morning, afternoon, morning + afternoon))

    employees_over_5 = []
    for emp in employees:
        streak = max_streak = 0
        for d in range(1, num_days + 1):
            shift = assignment.get(f"{emp}_{d}", "-")
            if shift in ["M_A", "M_B", "T_A", "T_B"]:
                streak += 1
                max_streak = max(max_streak, streak)
            else:
                streak = 0
        if max_streak > 5:
            employees_over_5.append((emp, max_streak))

    lines.append("\nEmployees working more than 5 consecutive days:")
    if employees_over_5:
        for emp, streak_len in employees_over_5:
            lines.append(f"{emp}: {streak_len} consecutive workdays")
    else:
        lines.append("None")

    lines.append("\nShifts worked per employee:")
    for emp, morning, afternoon, total in shifts:
        lines.append(f"{emp}: {morning} morning shifts, {afternoon} afternoon shifts, {total} total shifts")

    report_text = "\n".join(lines)
    print(report_text)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nAnalysis written to {filename}")


if __name__ == "__main__":
    employee_scheduling()