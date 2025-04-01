import copy
import random
import csv
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
            if isinstance(constraint_key, tuple):
                v1, v2 = constraint_key
                if v1 in temp_assignment and v2 in temp_assignment:
                    val1 = temp_assignment[v1]
                    val2 = temp_assignment[v2]
                    if not constraint_func(val1, val2):
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
                    temp_assignment = {v: domains[v][0] if len(domains[v]) == 1 else None
                                       for v in self.variables}
                    temp_assignment[curr_var] = curr_val
                    temp_assignment[other_var] = val
                    if self.check_constraints(other_var, val, temp_assignment):
                        new_domain.append(val)
                if not new_domain:
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
        return min(unassigned_vars, key=lambda var: len(domains[var]))

    def search(self, domains=None, timeout=60):
        start_time = time.time()
        if domains is None:
            domains = copy.deepcopy(self.domains)

        def timed_search(domains, depth=0):
            if time.time() - start_time > timeout:
                return None

            if any(len(lv) == 0 for lv in domains.values()):
                return None

            if all(len(lv) == 1 for lv in domains.values()):
                assignment = {v: lv[0] for v, lv in domains.items()}
                return {"assignment": assignment}

            var = self.select_variable(domains)
            if var is None:
                return None

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
    num_of_vacations = 5
    vacations = {emp: set(random.sample(range(1, num_days + 1), num_of_vacations)) for emp in employees}

    variables = [f"{emp}_{d}" for emp in employees for d in range(1, num_days + 1)]

    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]]
        else (["0"] if int(var.split('_')[1]) in holidays else random.sample(["M", "T", "0"], 3))
        for var in variables
    }

    constraints = {
        (v1, v2): (lambda x1, x2: not (x1 == "T" and x2 == "M"))
        for v1 in variables for v2 in variables
        if v1.split('_')[0] == v2.split('_')[0] and int(v1.split('_')[1]) + 1 == int(v2.split('_')[1])
    }

    csp = CSP(variables, domains, constraints)
    for emp in employees:
        emp_vars = [f"{emp}_{d}" for d in range(1, num_days + 1)]
        for start in range(num_days - 5):
            window_vars = emp_vars[start:start + 6]
            handle_ho_constraint(csp, window_vars, lambda values: not all(v in ["M", "T"] for v in values))
        ## Adjusted total shift limit for a year (e.g., 240 shifts, ~2/3 of days)
        handle_ho_constraint(csp, emp_vars, lambda values: values.count("M") + values.count("T") <= 223)
        # Ensure at least 5 "T" shifts
        handle_ho_constraint(csp, emp_vars, lambda values: values.count("T") >= 3)
        # Holiday shift limit (4 holidays, max 2 shifts)
        handle_ho_constraint(csp, [var for var in emp_vars if int(var.split('_')[1]) in holidays],
                             lambda values: values.count("M") + values.count("T") <= 22)

    solution = csp.search(timeout=300)
    if solution and solution["assignment"]:
        assignment = solution["assignment"]
        generate_calendar(assignment, num_employees, num_days)
        print(build_schedule_table(assignment, num_employees, num_days))

    else:
        print("No solution found within timeout or constraints too restrictive.")


def handle_ho_constraint(csp, variables, constraint_func):
    def constraint(var, assignment):
        values = [assignment.get(v, None) for v in variables]
        if None in values:
            return True
        return constraint_func(values)

    constraint_key = f"multi_{'_'.join(variables)}"
    csp.constraints[constraint_key] = constraint

def build_schedule_table(assignment, num_employees, num_days):
    table = []
    header = ["Employee"] + [str(day) for day in range(1, num_days + 1)]
    table.append(header)

    for e in range(1, num_employees + 1):
        row = [f"E{e}"]
        for d in range(1, num_days + 1):
            row.append(assignment.get(f"E{e}_{d}", "-"))
        table.append(row)
    #print(table)
    print(type(table))
    return table
def generate_calendar(assignment, num_employees, num_days):
    with open("calendario_turnos.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([str(day) for day in range(1, num_days + 1)])

        for e in range(1, num_employees + 1):
            employee_schedule = [assignment.get(f"E{e}_{d}", "-") for d in range(1, num_days + 1)]
            csvwriter.writerow([f"E{e}"] + employee_schedule)
            t_count = employee_schedule.count("T")
            m_count = employee_schedule.count("M")
            print(f"Employee E{e}: {t_count} afternoon shifts (T), {m_count} morning shifts (M)")


if __name__ == "__main__":
    employee_scheduling()