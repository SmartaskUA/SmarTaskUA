import copy
import random
import csv
from itertools import product

from handle_ho_constraint import handle_ho_constraint


class CSP:
    def __init__(self, variables, domains, constraints):
        self.variables = variables
        self.domains = domains.copy()
        self.constraints = constraints

    def check_constraints(self, var, value, assignment):
        """Verifica todas as restrições após uma atribuição."""
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        for (var1, var2), constraint in self.constraints.items():
            if var == var1 or var == var2:
                if not constraint(var1, temp_assignment[var1], var2, temp_assignment.get(var2, None)):
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
    num_employees = 12
    num_days = 30
    holidays = {7, 14, 21, 28}  # Domingos e feriados
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}

    # Definição de variáveis e domínios
    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]]
        else ["M", "T", "0"]
        for var in variables
    }

    constraints = {}

    # Restrições binárias
    # 1. Dias de trabalho máximo (223 dias de trabalho máximo no total)
    constraints[("E1_1", "E2_1")] = lambda e1, v1, e2, v2: sum(
        [1 for e in range(1, num_employees + 1) if v1 == "M" or v1 == "T"]) <= 223

    # 2. 5 dias de trabalho consecutivo máximo (com folga obrigatória depois de 5 dias)
    constraints[("E1_1", "E2_1")] = lambda e1, v1, e2, v2: sum(
        [1 for e in range(1, num_employees + 1) if v1 == "M" or v1 == "T"]) <= 5

    # 3. Sequências válidas de turno: M->M, T->T, M->T
    for e in range(1, num_employees + 1):
        for d in range(1, num_days):
            constraints[(f"E{e}_{d}", f"E{e}_{d + 1}")] = lambda e1, v1, e2, v2: (
                    (v1 == "M" and v2 == "M") or
                    (v1 == "T" and v2 == "T") or
                    (v1 == "M" and v2 == "T")
            )

    # 4. Sequência inválida T->M
    for e in range(1, num_employees + 1):
        for d in range(1, num_days):
            constraints[(f"E{e}_{d}", f"E{e}_{d + 1}")] = lambda e1, v1, e2, v2: not (v1 == "T" and v2 == "M")

    # 5. Cobrir os alarmes da melhor forma possível (restrição personalizada, adaptada com handle_ho_constraint)
    # handle_ho_constraint(domains, constraints, ['E1_1', 'E1_2', 'X1'], lambda t: 2 * t[0] == t[1] + 10 * t[2])

    # 6. Férias (30 dias de férias distribuídos entre os funcionários)
    for e in range(1, num_employees + 1):
        constraints[(f"E{e}_F", f"E{e}_F")] = lambda e1, v1, e2, v2: v1 == "F"

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
