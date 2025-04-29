import copy
import random
import csv
import time
import string
import os
import json
from formulation import generate_initial_calendar

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints

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
                            return False
                else:
                    values = [temp_assignment.get(v) for v in constraint_key]
                    if None not in values and not constraint_func(values):
                        return False
            else:
                if not constraint_func(var, temp_assignment):
                    return False
        return True

    def propagate(self, domains, var, value):
        domains[var] = [value]
        queue = [(var, value)]
        while queue:
            curr_var, curr_val = queue.pop(0)
            for other_var in self.variables:
                if other_var == curr_var or len(domains[other_var]) == 1:
                    continue
                new_domain = []
                for val in domains[other_var]:
                    if self.check_constraints(other_var, val, {curr_var: curr_val, other_var: val}):
                        new_domain.append(val)
                if not new_domain:
                    return False
                domains[other_var] = new_domain
                if len(new_domain) == 1:
                    queue.append((other_var, new_domain[0]))
        return True

    def select_variable(self, domains):
        unassigned_vars = [v for v in domains if len(domains[v]) > 1]
        if not unassigned_vars:
            return None
        return min(unassigned_vars, key=lambda var: len(domains[var]))

    def search(self, domains=None, timeout=60):
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
                return {"assignment": assignment}
            var = self.select_variable(domains)
            if var is None:
                return None
            values = domains[var].copy()
            random.shuffle(values)
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
    variables, domains, employees, num_days, holidays = generate_initial_calendar()

    constraints = {}
    
    for emp in employees:
        for d in range(1, num_days):
            var_t = f"{emp}_{d}_T"
            var_m = f"{emp}_{d+1}_M"
            constraints[(var_t, var_m)] = lambda t_val, m_val: not (t_val in ["A", "B"] and m_val in ["A", "B"])
    
    for emp in employees:
        for d in range(1, num_days + 1):
            m_var = f"{emp}_{d}_M"
            t_var = f"{emp}_{d}_T"
            constraints[(m_var, t_var)] = lambda m_val, t_val: not (m_val in ["A", "B"] and t_val in ["A", "B"])


    csp = CSP(variables, domains, constraints)

    for emp in employees:
        emp_vars = [f"{emp}_{d}_{s}" for d in range(1, num_days + 1) for s in ["M", "T"]]
        for start in range(num_days - 5):
            window_vars = [f"{emp}_{d}_{s}" for d in range(start, start + 6) for s in ["M", "T"]]
            handle_ho_constraint(csp, window_vars, lambda values: not all(v in ["A", "B"] for v in values))   
        handle_ho_constraint(csp, emp_vars, lambda values: sum(1 for v in values if v in ["A", "B"]) <= 23)
        holiday_vars = [f"{emp}_{d}_{s}" for d in holidays for s in ["M", "T"]]
        handle_ho_constraint(csp, holiday_vars, lambda values: sum(1 for v in values if v in ["A", "B"]) <= 2)

    for day in range(1, num_days + 1):
        for shift in ["M", "T"]:
            day_shift_vars = [f"{emp}_{day}_{shift}" for emp in employees]
            handle_ho_constraint(csp, day_shift_vars, lambda values: (
                sum(1 for v in values if v == "A") >= 2 and
                sum(1 for v in values if v == "B") >= 1))

    solution = csp.search(timeout=600)
    if solution and "assignment" in solution:
        assignment = solution["assignment"]
        generate_calendar(assignment, num_days, employees)
        toc = time.time()
        print(f"Execution time: {toc - tic:.2f} seconds")
        analyze_solution(assignment, employees, num_days, holidays)
        return build_schedule_table(assignment, num_days, employees)
    else:
        print("No solution found within timeout or constraints too restrictive.")
        return None

def handle_ho_constraint(csp, variables, constraint_func):
    def constraint(var, assignment):
        values = [assignment.get(v, None) for v in variables]
        if None in values:
            return True
        return constraint_func(values)
    constraint_key = f"multi_{'_'.join(variables)}"
    csp.constraints[constraint_key] = constraint

def build_schedule_table(assignment, num_days, employees):
    table = []
    header = ["Employee"] + [str(day) for day in range(1, num_days + 1)]
    table.append(header)
    for emp in employees:
        row = [emp]
        for d in range(1, num_days + 1):
            m_val = assignment.get(f"{emp}_{d}_M", "0")
            t_val = assignment.get(f"{emp}_{d}_T", "0")
            if m_val == "F" or t_val == "F":
                shift = "FF"
            else:
                shift = f"{m_val if m_val in ['A', 'B'] else '-'}{t_val if t_val in ['A', 'B'] else '-'}"
            row.append(shift)
        table.append(row)
    return table

def generate_calendar(assignment, num_days, employees):
    with open("solved_calendar.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(["Employee"] + [str(day) for day in range(1, num_days + 1)])
        for emp in employees:
            employee_schedule = []
            m_count = 0
            t_count = 0
            for d in range(1, num_days + 1):
                m_val = assignment.get(f"{emp}_{d}_M", "0")
                t_val = assignment.get(f"{emp}_{d}_T", "0")
                if m_val == "F" or t_val == "F":
                    shift = "FF"
                else:
                    shift = f"{m_val}{t_val}"
                    if m_val in ["A", "B"]:
                        m_count += 1
                    if t_val in ["A", "B"]:
                        t_count += 1
                employee_schedule.append(shift)
            csvwriter.writerow([emp] + employee_schedule)
            print(f"Employee {emp}: {t_count} afternoon shifts (T), {m_count} morning shifts (M)")

def analyze_solution(assignment, employees, num_days, holidays):
    tm_violations = 0
    for emp in employees:
        for d in range(1, num_days):
            t_val = assignment.get(f"{emp}_{d}_T", "0")
            m_val = assignment.get(f"{emp}_{d+1}_M", "0")
            if t_val in ["A", "B"] and m_val in ["A", "B"]:
                tm_violations += 1
    print(f"\nNumber of T->M restriction violations: {tm_violations}")

    print("\nShifts per team per day:")
    for day in range(1, num_days + 1):
        m_a = sum(1 for emp in employees if assignment.get(f"{emp}_{day}_M", "0") == "A")
        t_a = sum(1 for emp in employees if assignment.get(f"{emp}_{day}_T", "0") == "A")
        m_b = sum(1 for emp in employees if assignment.get(f"{emp}_{day}_M", "0") == "B")
        t_b = sum(1 for emp in employees if assignment.get(f"{emp}_{day}_T", "0") == "B")
        print(f"Day {day}: M_A={m_a}, T_A={t_a}, M_B={m_b}, T_B={t_b}")

    print("\nWorkdays on holidays per employee:")
    for emp in employees:
        holiday_workdays = sum(1 for d in holidays for s in ["M", "T"] if assignment.get(f"{emp}_{d}_{s}", "0") in ["A", "B"])
        print(f"{emp}: {holiday_workdays} work shifts on holidays")

if __name__ == "__main__":
    employee_scheduling()