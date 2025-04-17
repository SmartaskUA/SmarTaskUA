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
        print(f"Checking constraints for {var} = {value}")
        for constraint_key, constraint_func in self.constraints.items():
            if isinstance(constraint_key, tuple):
                if len(constraint_key) == 2:
                    v1, v2 = constraint_key
                    if v1 in temp_assignment and v2 in temp_assignment:
                        val1 = temp_assignment[v1]
                        val2 = temp_assignment[v2]
                        if not constraint_func(val1, val2):
                            print(f"Binary constraint failed: ({v1}={val1}, {v2}={val2})")
                            return False
                else:
                    values = [temp_assignment.get(v) for v in constraint_key]
                    if not constraint_func(values, constraint_key):
                        print(f"Higher-order constraint failed for {constraint_key}: values={values}")
                        return False
            else:
                if not constraint_func(var, temp_assignment):
                    print(f"Single constraint failed for {var}={value}")
                    return False
        print(f"All constraints passed for {var} = {value}")
        return True

    def propagate(self, domains, var, value):
        domains[var] = [value]
        queue = [(var, value)]
        print(f"Propagating: {var} = {value}")
        while queue:
            curr_var, curr_val = queue.pop(0)
            for other_var in self.variables:
                if other_var == curr_var or len(domains[other_var]) == 1:
                    continue
                print(f"Checking domain of {other_var}: {domains[other_var]}")
                new_domain = []
                for val in domains[other_var]:
                    if self.check_constraints(other_var, val, {curr_var: curr_val, other_var: val}):
                        new_domain.append(val)
                if not new_domain:
                    print(f"Domain wiped out for {other_var} when assigning {curr_var} = {curr_val}")
                    return False
                domains[other_var] = new_domain
                if len(new_domain) == 1:
                    print(f"Domain reduced to singleton: {other_var} = {new_domain[0]}")
                    queue.append((other_var, new_domain[0]))
        return True

    def select_variable(self, domains):
        unassigned_vars = [v for v in domains if len(domains[v]) > 1]
        if not unassigned_vars:
            print("No unassigned variables left to select.")
            return None
        var = min(unassigned_vars, key=lambda var: len(domains[var]))
        print(f"Selected variable: {var} with domain {domains[var]}")
        return var

    def search(self, domains=None, timeout=60):
        start_time = time.time()
        if domains is None:
            domains = copy.deepcopy(self.domains)
        print("Starting CSP search...")
        assigned_count = 0
        total_vars = len(self.variables)

        def timed_search(domains, depth=0):
            nonlocal assigned_count
            if time.time() - start_time > timeout:
                print(f"Search timed out after {timeout} seconds")
                return None
            if any(len(lv) == 0 for lv in domains.values()):
                print("Empty domain detected, search failed.")
                return None
            if all(len(lv) == 1 for lv in domains.values()):
                assignment = {v: lv[0] for v, lv in domains.items()}
                print("Solution found!")
                return {"assignment": assignment}
            var = self.select_variable(domains)
            if var is None:
                print("No variable to select, solution may be complete.")
                return None
            print(f"Depth {depth}: Trying variable {var} with domain {domains[var]}")
            values = domains[var].copy()
            random.shuffle(values)
            for val in values:
                print(f"Trying {var} = {val}")
                new_domains = copy.deepcopy(domains)
                new_domains[var] = [val]
                if self.propagate(new_domains, var, val):
                    assigned_count += 1
                    print(f"Progress: {assigned_count}/{total_vars} variables assigned ({(assigned_count/total_vars)*100:.1f}%)")
                    solution = timed_search(new_domains, depth + 1)
                    if solution is not None:
                        return solution
                else:
                    print(f"Propagation failed for {var} = {val}, backtracking...")
                    assigned_count -= 1
                    print(f"Progress after backtrack: {assigned_count}/{total_vars} variables assigned ({(assigned_count/total_vars)*100:.1f}%)")
            print(f"No valid values for {var}, backtracking...")
            return None

        return timed_search(domains)

def handle_ho_constraint(csp, variables, constraint_func):
    csp.constraints[tuple(variables)] = constraint_func

# def handle_ho_constraint(csp, variables, constraint_func):
#     def constraint(values):
#         return constraint_func(values)
#     csp.constraints[tuple(variables)] = constraint


# def handle_ho_constraint(domains,constraints,variables,constraint):
#     A = "".join(variables)
#     ho_domains = [domains[v] for v in variables]
#     A_domain = []
#     for combo in product(*ho_domains):
#         if constraint(combo):
#             A_domain.append(combo)
#     domains[A] = A_domain
#     variables.append(A)
#     for i, v in enumerate(variables):
#         if v == A:
#             continue
#         def make_constraint(index, aux=A, var=v):
#             def binary_constraint(varA, valA, varV, valV):
#                 if varA == aux:
#                     return valA[index] == valV
#                 if varV == aux:
#                     return valV[index] == valA
#                 return True
#             return binary_constraint
#         c_fn = make_constraint(i)
#         constraints[(A,v)] = c_fn
#         constraints[(v,A)] = c_fn

def solve_calendar():
    tic = time.time()
    print("Loading initial calendar data...")
    variables, domains, employees, num_days, num_employees, holidays = generate_initial_calendar()
    # holidays = {7, 14, 21, 28}
    print(f"Variables: {len(variables)}, Employees: {num_employees}, Days: {num_days}")
    print("Setting up T-to-M constraints...")
    constraints = {}

    for v1 in variables:
        for v2 in variables:
            if (v1.split('_')[0] == v2.split('_')[0] and 
                int(v1.split('_')[1]) + 1 == int(v2.split('_')[1]) and 
                v1.endswith('_T') and v2.endswith('_M')):
                constraints[(v1, v2)] = lambda x1, x2: not (x1 in ["A", "B"] and x2 in ["A", "B"])

    for v1 in variables:
        for v2 in variables:
            if (v1.split('_')[0] == v2.split('_')[0] and 
                int(v1.split('_')[1]) == int(v2.split('_')[1]) and 
                v1.endswith('_M') and v2.endswith('_T')):
                constraints[(v1, v2)] = lambda x1, x2: not (x1 in ["A", "B"] and x2 in ["A", "B"])

    csp = CSP(variables, domains, constraints)

    print("Setting up higher-order constraints...")
    for emp in employees:
        emp_vars = [f"{emp}_{d}_M" for d in range(1, num_days + 1)] + [f"{emp}_{d}_T" for d in range(1, num_days + 1)]
        for start in range(num_days - 5):
            window_vars = []
            for d in range(start + 1, start + 7):
                window_vars.extend([f"{emp}_{d}_M", f"{emp}_{d}_T"])
            handle_ho_constraint(csp, window_vars, lambda values, vars: not all(
                val in ["A", "B"] for val, var in zip(values, vars) if val is not None
            ) or any(val is None for val in values))
        handle_ho_constraint(csp, emp_vars, lambda values, vars: 
            sum(1 for val in values if val in ["A", "B"]) <= 20 or 
            any(val is None for val in values)
        )
        holiday_vars = []
        for d in holidays:
            holiday_vars.extend([f"{emp}_{d}_M", f"{emp}_{d}_T"])
        handle_ho_constraint(csp, holiday_vars, lambda values, vars: 
            sum(1 for val in values if val in ["A", "B"]) <= 2 or 
            any(val is None for val in values)
        )

    print("Setting up daily shift requirements...")
    for day in range(1, num_days + 1):
        m_vars = [f"{emp}_{day}_M" for emp in employees]
        t_vars = [f"{emp}_{day}_T" for emp in employees]
        handle_ho_constraint(csp, m_vars, lambda values, vars: 
            sum(1 for val in values if val == "A") >= 2 and 
            sum(1 for val in values if val == "B") >= 1 or 
            any(val is None for val in values)
        )
        handle_ho_constraint(csp, t_vars, lambda values, vars: 
            sum(1 for val in values if val == "A") >= 2 and 
            sum(1 for val in values if val == "B") >= 1 or 
            any(val is None for val in values)
        )

    print("Starting search...")
    solution = csp.search(timeout=600)
    if solution and "assignment" in solution:
        assignment = solution["assignment"]
        print("Generating calendar...")
        generate_calendar(assignment, num_employees, num_days)
        toc = time.time()
        print(f"Execution time: {toc - tic:.2f} seconds")
        print("Analyzing solution...")
        analyze_solution(assignment, employees, num_days, holidays)
    else:
        print("No solution found within timeout or constraints too restrictive.")

def generate_calendar(assignment, num_employees, num_days):
    calendar = {}
    for e in range(1, num_employees + 1):
        emp = f"E{e}"
        calendar[emp] = []
        for d in range(1, num_days + 1):
            m_val = assignment.get(f"E{e}_{d}_M", "0")
            t_val = assignment.get(f"E{e}_{d}_T", "0")
            if m_val == "F" or t_val == "F":
                shift = "FF"
            elif m_val == "0" and t_val == "0":
                shift = "00"
            else:
                m_shift = m_val if m_val in ["A", "B"] else "0"
                t_shift = t_val if t_val in ["A", "B"] else "0"
                shift = f"{m_shift}{t_shift}"
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
            curr_t = assignment.get(f"{emp}_{d}_T", "0")
            next_m = assignment.get(f"{emp}_{d+1}_M", "0")
            if curr_t in ["A", "B"] and next_m in ["A", "B"]:
                tm_violations += 1
    print(f"\nNumber of T->M restriction violations: {tm_violations}")

    print("\nShifts per team per day:")
    for day in range(1, num_days + 1):
        m_vars = [assignment.get(f"{emp}_{day}_M", "0") for emp in employees]
        t_vars = [assignment.get(f"{emp}_{day}_T", "0") for emp in employees]
        m_a = sum(1 for v in m_vars if v == "A")
        t_a = sum(1 for v in t_vars if v == "A")
        m_b = sum(1 for v in m_vars if v == "B")
        t_b = sum(1 for v in t_vars if v == "B")
        print(f"Day {day}: M_A={m_a}, T_A={t_a}, M_B={m_b}, T_B={t_b}")

    print("\nWorkdays on holidays per employee:")
    for emp in employees:
        holiday_workdays = 0
        for d in holidays:
            m_val = assignment.get(f"{emp}_{d}_M", "0")
            t_val = assignment.get(f"{emp}_{d}_T", "0")
            if m_val in ["A", "B"] or t_val in ["A", "B"]:
                holiday_workdays += 1
        print(f"{emp}: {holiday_workdays} workdays on holidays")

    print("\nConsecutive workdays analysis:")
    for emp in employees:
        max_consecutive = 0
        current_streak = 0
        for d in range(1, num_days + 1):
            m_val = assignment.get(f"{emp}_{d}_M", "0")
            t_val = assignment.get(f"{emp}_{d}_T", "0")
            if m_val in ["A", "B"] or t_val in ["A", "B"]:
                current_streak += 1
                max_consecutive = max(max_consecutive, current_streak)
            else:
                current_streak = 0
        print(f"{emp}: Max consecutive workdays = {max_consecutive}")

    print("\nTotal workdays per employee:")
    for emp in employees:
        workdays = 0
        for d in range(1, num_days + 1):
            m_val = assignment.get(f"{emp}_{d}_M", "0")
            t_val = assignment.get(f"{emp}_{d}_T", "0")
            if m_val in ["A", "B"] or t_val in ["A", "B"]:
                workdays += 1
        print(f"{emp}: Total workdays = {workdays}")

if __name__ == "__main__":
    solve_calendar()