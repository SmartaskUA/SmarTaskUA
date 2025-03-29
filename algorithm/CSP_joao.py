import copy
import random
import csv
from itertools import product

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints

    def is_consistent(self, var, value, assignment):
        assignment[var] = value
        for (v1, v2), constraint_fn in self.constraints.items():
            if v1 == var and v2 in assignment:
                if not constraint_fn(value, assignment[v2]):
                    del assignment[var]
                    return False
            elif v2 == var and v1 in assignment:
                if not constraint_fn(assignment[v1], value):
                    del assignment[var]
                    return False
        del assignment[var]
        return True

    def select_unassigned_variable(self, assignment):
        unassigned_vars = [v for v in self.variables if v not in assignment]
        return min(unassigned_vars, key=lambda var: len([val for val in self.domains[var] if self.is_consistent(var, val, assignment)]))

    def order_domain_values(self, var, assignment):
        return self.domains[var]

    def backtrack(self, assignment):
        print("BB")
        if len(assignment) == len(self.variables):
            return assignment

        var = self.select_unassigned_variable(assignment)
        for value in self.order_domain_values(var, assignment):
            if self.is_consistent(var, value, assignment):
                assignment[var] = value
                result = self.backtrack(assignment)
                if result is not None:
                    return result
                del assignment[var]

        return None

    def search(self):
        print("CC")
        return {"assignment": self.backtrack({})}

def employee_scheduling():
    num_employees = 12
    num_days = 30
    holidays = {7, 14, 21, 28}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    print(len(variables))

    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]]
        else ["M", "T", "0"]
        for var in variables
    }

    constraints = {
        (v1, v2): (lambda x1, x2: x1 == "T" and x2 == "F")
        for v1 in variables
        for v2 in variables
        if v1.split('_')[0] == v2.split('_')[0] and int(v1.split('_')[1]) + 1 == int(v2.split('_')[1])
    }

    for emp in employees:
        print("DD")
        emp_vars = [f"{emp}_{d}" for d in range(1, num_days + 1)]
        handle_ho_constraint (
            domains,
            constraints,
            emp_vars,
            lambda schedule: all(
                not all(day in ["M", "T"] for day in schedule[i:i+6])
                for i in range(len(schedule) - 5)
            )
        )

    # Resolver o problema CSP
    csp = CSP(variables, domains, constraints)
    solution = csp.search()

    if solution and solution["assignment"]:
        assignment = solution["assignment"]
        print("Solução encontrada:")
        for e in range(1, num_employees + 1):
            schedule = [assignment.get(f"E{e}_{d}", "0") for d in range(1, num_days + 1)]
            print(f"E{e}: {' '.join(schedule)}")
        generate_calendar(assignment, num_employees, num_days)
    else:
        print("Nenhuma solução encontrada.")

def handle_ho_constraint(domains,constraints,variables,constraint):
    print("AA")
    A = "".join(variables)
    ho_domains = [domains[v] for v in variables]
    A_domain = []
    for combo in product(*ho_domains):
        if constraint(combo):
            A_domain.append(combo)
    domains[A] = A_domain
    variables.append(A)
    for i, v in enumerate(variables):
        if v == A:
            continue
        def make_constraint(index, aux=A, var=v):
            def binary_constraint(varA, valA, varV, valV):
                if varA == aux:
                    return valA[index] == valV
                if varV == aux:
                    return valV[index] == valA
                return True
            return binary_constraint
        c_fn = make_constraint(i)
        constraints[(A,v)] = c_fn
        constraints[(v,A)] = c_fn

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