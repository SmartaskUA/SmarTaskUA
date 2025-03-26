import copy
import random

class CSP:
    def __init__(self, variables, domains, constraints):
        """Initialize the CSP."""
        self.variables = variables
        self.domains = domains.copy()
        self.constraints = constraints
        self.current_domains = domains.copy()

    def check_constraints(self, var, value, assignment):
        """Check constraints and return a list of violations instead of a boolean."""
        print("DD")
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        violations = []
        for i, constraint in enumerate(self.constraints):
            if not constraint(var, temp_assignment):
                violations.append(f"Constraint {i} violated for {var} = {value}")
        return violations
    
    def propagate(self,domains,var, value):
        print("BB")
        temp_assignment = {v: domains[v][0] if len(domains[v]) == 1 else None for v in self.variables}
        temp_assignment[var] = value
        
        # For each unassigned variable, reduce its domain based on constraints
        for v in self.variables:
            if v not in temp_assignment or temp_assignment[v] is None:
                new_domain = []
                for val in domains[v]:
                    temp_assignment[v] = val
                    violations = self.check_constraints(v, val, temp_assignment)
                    if not violations:
                        new_domain.append(val)
                    temp_assignment[v] = None
                domains[v] = new_domain if new_domain else domains[v]
                # if not domains[v]:
                #     return False
        print("CC")
        return True

    def search(self,domains=None):    
        print("AA")    
        if domains==None:
            domains = self.domains

        # se alguma variavel tiver lista de valores vazia, falha
        if any([len(lv) == 0 for lv in domains.values()]):
            return None

        # se todas as variaveis exactamente um valor, sucesso
        # if all([len(lv) == 1 for lv in domains.values()]):
        #     return { v:lv[0] for (v,lv) in domains.items() }
        if all(len(lv) <= 1 for lv in domains.values()):
            assignment = {v: lv[0] for v, lv in domains.items() if lv}
            violations = []
            for var in assignment:
                violations.extend(self.check_constraints(var, assignment[var], assignment))
            return {"assignment": assignment, "violations": violations}
       
        # continuação da pesquisa
        for var in domains.keys():
            if len(domains[var])>1:
                for val in domains[var]:
                    newdomains = dict(domains)
                    newdomains[var] = [val]
                    self.propagate(newdomains,var, val)
                    solution = self.search(newdomains)
                    if solution != None:
                        return solution
        return None

def employee_scheduling():
    num_employees = 15
    num_days = 365
    holidays = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    vacations = {emp: set(random.sample(range(1, num_days + 1), 30)) for emp in employees}

    variables = [f"E{e}_{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else ["0", "M", "T"] for var in variables}

    constraints = [
        # No T->M transition
        lambda var, assignment: not any(
            assignment.get(var, "0") == "T" and 
            assignment.get(f"{var.split('_')[0]}_{int(var.split('_')[1]) - 1}", "0") == "M"
            for var in variables if int(var.split('_')[1]) > 1
        ),
        # Max 5 consecutive days
        lambda var, assignment: not any(
            all(assignment.get(f"{var.split('_')[0]}_{d-k}", "0") in ["M", "T"] for k in range(6))
            for d in range(6, num_days + 1) if var == f"{var.split('_')[0]}_{d}"
        ),
        # Max 223 workdays
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") in ["M", "T"]) == 223
            for e in range(1, num_employees + 1)
        ),
        # Max 22 Sundays/holidays
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_{d}", "0") in ["M", "T"] and ((d-1) % 7 == 6 or d in holidays)) <= 22
            for e in range(1, num_employees + 1)
        ),
        # Min 2 employees per shift per day
        lambda var, assignment: all(
            sum(1 for e in range(1, num_employees + 1) if assignment.get(f"E{e}_{d}", "0") in ["M", "T"]) >= 2
            for d in range(1, num_days + 1)
        )
    ]

    csp = CSP(variables, domains, constraints)
    solution = csp.search()
    if solution:
        print("Solution found for employee scheduling.")
        # export
    else:
        print("No solution found.")

if __name__ == "__main__":
    employee_scheduling()