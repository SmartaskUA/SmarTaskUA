import copy
import random
import csv
import time
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

def handle_ho_constraint(csp, variables, constraint_func):
    def constraint(values):
        return constraint_func(values)
    csp.constraints[tuple(variables)] = constraint

def solve_calendar():
    tic = time.time()
    variables, domains, employee_teams, employees, num_days, num_employees, holidays = generate_initial_calendar()

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

    for day in range(1, num_days + 1):
        day_vars = [f"{emp}_{day}" for emp in employees]
        handle_ho_constraint(csp, day_vars, lambda values: sum(1 for v in values if v == "M_A") >= 2 and 
                                                          sum(1 for v in values if v == "T_A") >= 2 and 
                                                          sum(1 for v in values if v == "M_B") >= 1 and 
                                                          sum(1 for v in values if v == "T_B") >= 1)

    solution = csp.search(timeout=600)
    if solution and "assignment" in solution:
        assignment = solution["assignment"]
        generate_calendar(assignment, num_employees, num_days)
        toc = time.time()
        print(f"Execution time: {toc - tic:.2f} seconds")
        analyze_solution(assignment, employees, num_days, holidays)
    else:
        print("No solution found within timeout or constraints too restrictive.")

def generate_calendar(assignment, num_employees, num_days):
    calendar = {}
    for e in range(1, num_employees + 1):
        emp = f"E{e}"
        calendar[emp] = []
        for d in range(1, num_days + 1):
            val = assignment.get(f"E{e}_{d}", "0")
            if val == "F":
                shift = "FF"
            elif val == "0":
                shift = "00"
            elif val.startswith("M_"):
                shift = val.split('_')[1] + "0"
            else:
                shift = "0" + val.split('_')[1]
            calendar[emp].append(shift)

    with open("solved_calendar.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        col_width = 5
        first_col_width = 6
        header = ["dia".ljust(first_col_width)] + [f"|{str(day).ljust(col_width-2)}" for day in range(1, num_days + 1)] + ["|"]
        csvwriter.writerow(header)
        subheader = ["turno".ljust(first_col_width)] + [f"|{'MT'.ljust(col_width-2)}" for _ in range(num_days)] + ["|"]
        csvwriter.writerow(subheader)
        for e in range(1, num_employees + 1):
            emp = f"E{e}"
            emp_id = emp.lower()
            row = [emp_id.ljust(first_col_width)] + [f"| {shift.ljust(col_width-3)}" for shift in calendar[emp]] + ["|"]
            csvwriter.writerow(row)
        print("Solved calendar saved to 'solved_calendar.csv'")

def analyze_solution(assignment, employees, num_days, holidays):
    tm_violations = 0
    for emp in employees:
        for d in range(1, num_days):
            curr_day = assignment.get(f"{emp}_{d}", "0")
            next_day = assignment.get(f"{emp}_{d+1}", "0")
            if curr_day.startswith("T_") and next_day.startswith("M_"):
                tm_violations += 1
    print(f"\nNumber of T->M restriction violations: {tm_violations}")

    print("\nShifts per team per day:")
    for day in range(1, num_days + 1):
        day_vars = [assignment.get(f"{emp}_{day}", "0") for emp in employees]
        m_a = sum(1 for v in day_vars if v == "M_A")
        t_a = sum(1 for v in day_vars if v == "T_A")
        m_b = sum(1 for v in day_vars if v == "M_B")
        t_b = sum(1 for v in day_vars if v == "T_B")
        print(f"Day {day}: M_A={m_a}, T_A={t_a}, M_B={m_b}, T_B={t_b}")

    print("\nWorkdays on holidays per employee:")
    for emp in employees:
        holiday_workdays = sum(1 for d in holidays if assignment.get(f"{emp}_{d}", "0") in ["M_A", "M_B", "T_A", "T_B"])
        print(f"{emp}: {holiday_workdays} workdays on holidays")

if __name__ == "__main__":
    solve_calendar()