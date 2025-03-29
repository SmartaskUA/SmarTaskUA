import copy
import random
import csv
from itertools import product
import time

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints
    
    def check_constraints(self, var, value, assignment):
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        
        for constraint_key, constraint_func in self.constraints.items():
            if isinstance(constraint_key, tuple):  # Pairwise constraint
                v1, v2 = constraint_key
                if v1 in temp_assignment and v2 in temp_assignment:
                    val1 = temp_assignment[v1]
                    val2 = temp_assignment[v2]
                    if not constraint_func(val1, val2):
                        print(f"Constraint failed: {v1}={val1}, {v2}={val2} (pairwise)")
                        return False
            else:  # Multi-variable constraint
                if not constraint_func(var, temp_assignment):
                    print(f"Constraint failed: {constraint_key} for {var}={value}")
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
                    temp_assignment = {v: domains[v][0] if len(domains[v]) == 1 else None 
                                     for v in self.variables}
                    temp_assignment[curr_var] = curr_val
                    temp_assignment[other_var] = val
                    if self.check_constraints(other_var, val, temp_assignment):
                        new_domain.append(val)
                if not new_domain:
                    print(f"Propagation failed: {other_var} domain reduced to empty after {curr_var}={curr_val}")
                    return False
                if len(new_domain) < len(domains[other_var]):
                    domains[other_var] = new_domain
                    if len(new_domain) == 1:
                        queue.append((other_var, new_domain[0]))
        return True
    
    def select_variable(self, domains):
        unassigned_vars = [v for v in domains if len(domains[v]) > 1]
        if not unassigned_vars:
            return None
        return min(unassigned_vars, key=lambda var: (
            len(domains[var]),
            -sum(1 for key in self.constraints.keys()
                if isinstance(key, tuple) and (var == key[0] or var == key[1]))
        ))

    def search(self, domains=None, timeout=30):
        start_time = time.time()
        if domains is None:
            domains = copy.deepcopy(self.domains)
        
        def timed_search(domains, depth=0):
            if time.time() - start_time > timeout:
                print(f"Search timed out after {timeout} seconds.")
                return None
            
            if any(len(lv) == 0 for lv in domains.values()):
                print(f"Empty domain detected at depth {depth}")
                return None
            
            if all(len(lv) == 1 for lv in domains.values()):
                assignment = {v: lv[0] for v, lv in domains.items()}
                violations = [not self.check_constraints(var, assignment[var], assignment) 
                             for var in assignment]
                print(f"Solution found at depth {depth} with {sum(violations)} violations")
                return {"assignment": assignment, "violations": violations}
            
            var = self.select_variable(domains)
            if var is None:
                return None
            
            if depth % 5 == 0:
                print(f"Depth {depth}: Exploring {var}, domain size {len(domains[var])}")
            
            for val in domains[var]:
                new_domains = copy.deepcopy(domains)
                new_domains[var] = [val]
                if self.propagate(new_domains, var, val):
                    solution = timed_search(new_domains, depth + 1)
                    if solution is not None:
                        return solution
            return None
        
        return timed_search(domains)

def employee_scheduling():
    num_employees = 12
    num_days = 30
    holidays = {7, 14, 21, 28}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    print(f"Total variables: {len(variables)}")

    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]]
        else ["M", "T", "0"]
        for var in variables
    }

    constraints = {
        (v1, v2): (lambda x1, x2: x1 == "T" and x2 != "M")
        for v1 in variables
        for v2 in variables
        if v1.split('_')[0] == v2.split('_')[0] and int(v1.split('_')[1]) + 1 == int(v2.split('_')[1])
    }

    csp = CSP(variables, domains, constraints)
    for emp in employees:
        emp_vars = [f"{emp}_{d}" for d in range(1, num_days + 1)]
        for start in range(num_days - 5):
            window_vars = emp_vars[start:start+6]
            handle_ho_constraint(
                csp,
                window_vars,
                lambda values: not all(v in ["M", "T"] for v in values)
            )

    solution = csp.search()
    if solution and solution["assignment"]:
        assignment = solution["assignment"]
        print("Solution found:")
        for e in range(1, num_employees + 1):
            schedule = [assignment.get(f"E{e}_{d}", "0") for d in range(1, num_days + 1)]
            print(f"E{e}: {' '.join(schedule)}")
        generate_calendar(assignment, num_employees, num_days)
    else:
        print("No solution found.")

def handle_ho_constraint(csp, variables, constraint_func):
    def constraint(var, assignment):
        if not all(v in assignment for v in variables):
            return True
        values = [assignment[v] for v in variables]
        return constraint_func(values)
    
    constraint_key = f"multi_{'_'.join(variables)}"
    csp.constraints[constraint_key] = constraint

def generate_calendar(assignment, num_employees, num_days):
    days_of_week = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    print("\nCalendário:")
    print(" ".join(f"{day:2}" for day in range(1, num_days + 1)))
    print(" ".join(f"{days_of_week[(day - 1) % 7]:3}" for day in range(1, num_days + 1)))

    with open("calendario_turnos.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([str(day) for day in range(1, num_days + 1)])
        csvwriter.writerow([days_of_week[(day - 1) % 7] for day in range(1, num_days + 1)])

        for e in range(1, num_employees + 1):
            employee_schedule = [assignment.get(f"E{e}_{d}", "-") for d in range(1, num_days + 1)]
            print(f"E{e}: " + " ".join(f"{shift:2}" for shift in employee_schedule))
            csvwriter.writerow([f"E{e}"] + employee_schedule)

if __name__ == "__main__":
    employee_scheduling()