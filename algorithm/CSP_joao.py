import copy
import random
import csv
from itertools import product

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints
    

    def check_constraints(self, var, value, assignment):
        """Verifica todas as restrições após uma atribuição."""
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        for constraint in self.constraints.values():  # Correção aqui
            if not constraint(var, temp_assignment):
                return False
        return True
    
    def propagate(self, domains, var, value):
        """Reduz os domínios com base nas restrições e propaga."""
        temp_assignment = {v: domains[v][0] if len(domains[v]) == 1 else None for v in self.variables}
        temp_assignment[var] = value

        for v in self.variables:
            if temp_assignment[v] is None:  # Apenas para variáveis não atribuídas
                new_domain = []
                for val in domains[v]:
                    if self.check_constraints(v, val, temp_assignment):
                        new_domain.append(val)
                if not new_domain:
                    return False  # Se esvaziar o domínio, inconsistente
                domains[v] = new_domain
        return True
    
    def select_variable(self, domains):
        unassigned_vars = [v for v in domains if len(domains[v]) > 1]
        return min(unassigned_vars, key=lambda var: len(domains[var]))

    def search(self, domains=None):
        if domains is None:
            domains = copy.deepcopy(self.domains)

        if any(len(lv) == 0 for lv in domains.values()):
            return None

        if all(len(lv) == 1 for lv in domains.values()):
            assignment = {v: lv[0] for v, lv in domains.items()}
            violations = [not self.check_constraints(var, assignment[var], assignment) for var in assignment]
            return {"assignment": assignment, "violations": violations}

        var = self.select_variable(domains)

        for val in domains[var]:
            new_domains = copy.deepcopy(domains)
            new_domains[var] = [val]
            if self.propagate(new_domains, var, val):
                solution = self.search(new_domains)
                if solution is not None:
                    return solution
        return None

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
        (v1, v2): (lambda x1, x2: x1 == "T" and x2 != "M")
        for v1 in variables
        for v2 in variables
        if v1.split('_')[0] == v2.split('_')[0] and int(v1.split('_')[1]) + 1 == int(v2.split('_')[1])
    }

    for emp in employees:
        emp_vars = [f"{emp}_{d}" for d in range(1, num_days + 1)]
        # Apply constraint on sliding window of 6 days
        for start in range(num_days - 5):
            window_vars = emp_vars[start:start+6]
            handle_ho_constraint (
                domains,
                constraints,
                window_vars,
                lambda schedule: not all(day in ["M", "T"] for day in schedule)
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
        print("EE")
        if constraint(combo):
            A_domain.append(combo)
    domains[A] = A_domain
    variables.append(A)
    for i, v in enumerate(variables):
        print("FF")
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