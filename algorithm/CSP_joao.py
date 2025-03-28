import copy
import csv
import random


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
                    print(f"Domínio de {v} esvaziado. Conflito detectado!")
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
        print(f"Tentando atribuir valores à variável {var} com domínio {domains[var]}")

        for val in domains[var]:
            print(f"Tentando {val} para {var}")
            new_domains = copy.deepcopy(domains)
            new_domains[var] = [val]
            if self.propagate(new_domains, var, val):
                solution = self.search(new_domains)
                if solution is not None:
                    return solution
        return None


def employee_scheduling():
    num_employees = 12  # Reduzido para simplificar o teste
    num_days = 30  # Teste inicial com 30 dias
    holidays = {7, 14, 21, 28}  # Apenas 4 feriados para simplificação
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}  # 5 dias de férias

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else [ "M", "T","0"] for var in
               variables}

    constraints = [
        # Sequência inválida T -> M
        lambda var, assignment: not any(
            assignment.get(var, "0") == "T" and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) - 1}", "0") == "M"
            for var in variables if int(var.split('_')[1]) > 1
        ),
        # Máximo 5 dias consecutivos de trabalho
        lambda var, assignment: not any(
            all(assignment.get(f"{var.split('_')[0]}_{d - k}", "0") in ["M", "T"] for k in range(5))
            for d in range(5, num_days + 1) if var == f"{var.split('_')[0]}_{d}"
        ),
        # 20 dias de trabalho no total (para simplificar)
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") in ["M", "T"]) <= 223
            for e in range(1, num_employees + 1)
        ),
        # Máximo 2 domingos/feriados trabalhados no mês
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if
                assignment.get(f"E{e}_{d}", "0") in ["M", "T"] and ((d - 1) % 7 == 6 or d in holidays)) <= 20
            for e in range(1, num_employees + 1)
        )
    ]

    csp = CSP(variables, domains, constraints)
    solution = csp.search()
    if solution:
        assignment = solution["assignment"]

        generate_calendar(assignment, num_employees, num_days)
        print("Solução encontrada:")
        for var, val in solution["assignment"].items():
            print(f"{var}: {val}")


    else:
        print("Nenhuma solução encontrada.")

def generate_calendar(assignment, num_employees, num_days):
    days_of_week = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

    print("\nCalendário:")
    print(" ".join(f"{day:2}" for day in range(1, num_days + 1)))
    print(" ".join(f"{days_of_week[(day - 1) % 7]:3}" for day in range(1, num_days + 1)))

    with open("schedule.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow([str(day) for day in range(1, num_days + 1)])
        csvwriter.writerow([days_of_week[(day - 1) % 7] for day in range(1, num_days + 1)])

        for e in range(1, num_employees + 1):
            employee_schedule = [assignment.get(f"E{e}_{d}", "-") for d in range(1, num_days + 1)]
            print(f"E{e}: " + " ".join(f"{shift:2}" for shift in employee_schedule))
            csvwriter.writerow([f"E{e}"] + employee_schedule)

if __name__ == "__main__":
    employee_scheduling()