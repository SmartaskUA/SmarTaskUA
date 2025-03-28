import copy
import random

from generate_calendar import generate_calendar
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


def employee_scheduling():
    num_employees = 7
    num_days = 30
    holidays = {7, 14, 21, 28}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 5)) for emp in employees}

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else ["M", "T", "F", "0"]
               for var in variables}
    '''
     constraints = {
        (v1, v2): (lambda x1, x2: x1 == "T" and x2 == "F")
        for v1 in variables
        for v2 in variables
        if v1.split('_')[0] == v2.split('_')[0] and int(v1.split('_')[1]) + 1 == int(v2.split('_')[1])
    }

    handle_ho_constraint(domains, constraints, variables, lambda x: x[0] not in ["F", "0"] and x[1] not in ["F", "0"] and x[2] not in ["F", "0"] and x[3] not in ["F", "0"] and x[4] not in ["F", "0"] and x[5] in ["F", "0"]) 
    '''
    constraints = {
        # Impedir a sequência inválida Tarde -> Manhã (T->M)
        lambda var, assignment: not any(
            assignment.get(var, "0") == "T" and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) - 1}", "0") == "M"
            for var in variables if int(var.split('_')[1]) > 1
        ),
        # Garantir no máximo 5 dias consecutivos de trabalho (M ou T)
        lambda var, assignment: not any(
            all(assignment.get(f"{var.split('_')[0]}_{d - k}", "0") in ["M", "T"] for k in range(6))
            for d in range(5, num_days + 1) if var == f"{var.split('_')[0]}_{d}"
        ),
        # Garantir no máximo 22 domingos e feriados trabalhados por funcionário
        lambda var, assignment: all(
            sum(1 for d in holidays if assignment.get(f"E{e}_{d}", "0") in ["M", "T"]) <= 22
            for e in range(1, num_employees + 1)
        ),
        # Garantir no máximo 223 dias de trabalho no ano por funcionário
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") in ["M", "T"]) <= 223
            for e in range(1, num_employees + 1)
        ),
        # Garantir que cada funcionário tenha um único turno por dia
        lambda var, assignment: not any(
            assignment.get(var, "0") in ["M", "T"] and
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) + 1}", "0") == "T"
            for var in variables if int(var.split('_')[1]) < num_days
        )
    }
    csp = CSP(variables, domains, constraints)
    solution = csp.search()

    if solution:
        assignment = solution["assignment"]

        print("Solução encontrada com turnos da tarde distribuidos:")
        '''for var, val in assignment.items():
            print(f"{var}: {val}")'''

        generate_calendar(assignment,num_employees,num_days)
    else:
        print("Nenhuma solução encontrada.")

if __name__ == "__main__":
    employee_scheduling()