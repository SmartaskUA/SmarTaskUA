import copy
import random
import csv

class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains
        self.constraints = constraints

    def is_consistent(self, var, value, assignment):
        assignment[var] = value
        for constraint in self.constraints:
            if not constraint(var, assignment):
                del assignment[var]
                return False
        del assignment[var]
        return True

    def select_unassigned_variable(self, assignment):
        # Heurística MRV: variável com o menor domínio restante
        unassigned_vars = [v for v in self.variables if v not in assignment]
        return min(unassigned_vars, key=lambda var: len([val for val in self.domains[var] if self.is_consistent(var, val, assignment)]))

    def order_domain_values(self, var, assignment):
        return self.domains[var]

    def backtrack(self, assignment):
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
        return {"assignment": self.backtrack({})}


def employee_scheduling():
    num_employees = 7
    num_days = 30
    holidays = {7, 14, 21, 28}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]

    # Domínios balanceados para incluir mais turnos "T"
    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]]
        else ["M", "T", "0"]
        for var in variables
    }

    # Restrições
    constraints = [
        # Evitar sequência "T->M"
        lambda var, assignment: not any(
            assignment.get(var, "0") == "T" and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) - 1}", "0") == "M"
            for var in variables if int(var.split('_')[1]) > 1
        ),
        # Evitar 5 dias consecutivos de turnos "M" ou "T"
        lambda var, assignment: not any(
            all(assignment.get(f"{var.split('_')[0]}_{d - k}", "0") in ["M", "T"] for k in range(5))
            for d in range(5, num_days + 1) if var == f"{var.split('_')[0]}_{d}"
        ),

        # Evitar sequência inválida T -> M
        lambda var, assignment: not any(
            assignment.get(var, "0") == "T" and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) + 1}", "0") == "M"
            for var in variables if int(var.split('_')[1]) < num_days
        ),
        # Balancear turnos "M" e "T" por funcionário
        lambda var, assignment: all(
            abs(
                sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") == "M") -
                sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") == "T")
            ) <= 2  # Mantém diferença mínima entre "M" e "T"
            for e in range(1, num_employees + 1)
        ),
    ]

    # Resolver o problema CSP
    csp = CSP(variables, domains, constraints)
    solution = csp.search()

    if solution:
        assignment = solution["assignment"]
        print("Solução encontrada:")
        for e in range(1, num_employees + 1):
            schedule = [assignment.get(f"E{e}_{d}", "0") for d in range(1, num_days + 1)]
            print(f"E{e}: {' '.join(schedule)}")
        generate_calendar(assignment, num_employees, num_days)
    else:
        print("Nenhuma solução encontrada.")




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