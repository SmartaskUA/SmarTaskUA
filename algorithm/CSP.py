import copy
import random
import calendar
import csv


class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains.copy()
        self.constraints = constraints

    def check_constraints(self, var, value, assignment):
        """Verifica todas as restrições após uma atribuição."""
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        for constraint in self.constraints:
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
        """Seleciona a variável com menos valores restantes (MRV)."""
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


def distribute_afternoon_shifts(assignment, num_employees, num_days):
    """Distribui turnos de manhã (M) e tarde (T) para garantir balanceamento sem violar as restrições."""
    for e in range(1, num_employees + 1):
        morning_slots = [f"E{e}_{d}" for d in range(1, num_days + 1) if assignment[f"E{e}_{d}"] == "M"]
        afternoon_slots = [f"E{e}_{d}" for d in range(1, num_days + 1) if assignment[f"E{e}_{d}"] == "T"]

        # Balance morning and afternoon shifts to ensure both M and T are present for each employee
        total_slots = len(morning_slots) + len(afternoon_slots)
        max_shifts_per_type = total_slots // 2

        # If the morning slots exceed the max limit, convert some to afternoon
        if len(morning_slots) > max_shifts_per_type:
            excess_morning = morning_slots[max_shifts_per_type:]
            for slot in excess_morning:
                assignment[slot] = "T"

        # If the afternoon slots exceed the max limit, convert some to morning
        elif len(afternoon_slots) > max_shifts_per_type:
            excess_afternoon = afternoon_slots[max_shifts_per_type:]
            for slot in excess_afternoon:
                assignment[slot] = "M"

    return assignment

def employee_scheduling():
    num_employees = 7
    num_days = 30
    holidays = {7, 14, 21, 28}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else ["M", "T", "F", "0"]
               for var in variables}

    constraints = [
        lambda var, assignment: not any(
            assignment.get(var, "0") == "T" and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) - 1}", "0") == "M"
            for var in variables if int(var.split('_')[1]) > 1
        ),
        lambda var, assignment: not any(
            all(assignment.get(f"{var.split('_')[0]}_{d - k}", "0") in ["M", "T"] for k in range(5))
            for d in range(5, num_days + 1) if var == f"{var.split('_')[0]}_{d}"
        ),
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") in ["M", "T"]) <= 20
            for e in range(1, num_employees + 1)
        ),
        lambda var, assignment: not any(
            assignment.get(var, "0") == "M" and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) + 1}", "0") == "T"
            for var in variables if int(var.split('_')[1]) < num_days
        ),

    ]

    csp = CSP(variables, domains, constraints)
    solution = csp.search()
    if solution:
        assignment = solution["assignment"]
        assignment = distribute_afternoon_shifts(assignment, num_employees, num_days)
        print("Solução encontrada:")
        for var, val in assignment.items():
            print(f"{var}: {val}")
        generate_calendar(assignment, num_employees, num_days)
    else:
        print("Nenhuma solução encontrada.")


def generate_calendar(assignment, num_employees, num_days):
    days_of_week = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    # Gera a primeira linha com os dias do mês
    print("\nCalendário:")
    print(" ".join(f"{day:2}" for day in range(1, num_days + 1)))

    # Gera a segunda linha com os dias da semana
    print(" ".join(f"{days_of_week[(day - 1) % 7]:3}" for day in range(1, num_days + 1)))

    # Criação do arquivo CSV
    with open("calendario_turnos.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)

        # Escreve os dias e os dias da semana no CSV
        csvwriter.writerow([str(day) for day in range(1, num_days + 1)])
        csvwriter.writerow([days_of_week[(day - 1) % 7] for day in range(1, num_days + 1)])

        # Gera as linhas dos funcionários
        for e in range(1, num_employees + 1):
            employee_schedule = [assignment.get(f"E{e}_{d}", "-") for d in range(1, num_days + 1)]
            print(f"E{e}: " + " ".join(f"{shift:2}" for shift in employee_schedule))

            # Escreve a linha do funcionário no CSV
            csvwriter.writerow([f"E{e}"] + employee_schedule)


if __name__ == "__main__":
    employee_scheduling()
