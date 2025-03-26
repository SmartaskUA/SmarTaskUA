import copy
import random

class CSP:
    def __init__(self, variables, domains, constraints):
        """Initialize the CSP."""
        self.variables = variables
        self.domains = domains.copy()
        self.constraints = constraints
        self.current_domains = domains.copy()

    def is_valid_assignment(self, var, value, assignment):
        """Check if assigning 'value' to 'var' satisfies all constraints."""
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        return all(constraint(var, temp_assignment) for constraint in self.constraints)
    
    def propagate(self,domains,var):
        edges = [ e for e in self.constraints if e[1]==var ]
        while edges!=[]:
            (vj,vi) = edges.pop()
            constraint = self.constraints[vj,vi]
            newdomain = [ xj for xj in domains[vj] 
                             if any(constraint(vj,xj,vi,xi) for xi in domains[vi] ) ]
            if len(newdomain)<len(domains[vj]):
                domains[vj] = newdomain
                edges += [ e for e in self.constraints if e[1]==vj ]

    def search(self,domains=None):
        self.calls += 1 
        
        if domains==None:
            domains = self.domains

        # se alguma variavel tiver lista de valores vazia, falha
        if any([lv==[] for lv in domains.values()]):
            return None

        # se todas as variaveis exactamente um valor, sucesso
        if all([len(lv)==1 for lv in list(domains.values())]):
            return { v:lv[0] for (v,lv) in domains.items() }
       
        # continuação da pesquisa
        for var in domains.keys():
            if len(domains[var])>1:
                for val in domains[var]:
                    newdomains = dict(domains)
                    newdomains[var] = [val]
                    self.propagate(newdomains,var)
                    solution = self.search(newdomains)
                    if solution != None:
                        return solution
        return None

def employee_scheduling():
    num_employees = 15
    num_days = 365
    holidays = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}
    vacations = {f"E{e}": set(random.sample(range(1, num_days + 1), 30)) for e in range(1, num_employees + 1)}

    variables = [f"E{e}_D{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {var: ["F"] if int(var.split('_')[1][1:]) in vacations[var.split('_')[0]] else ["0", "M", "T", "MT"] for var in variables}

    constraints = [
        # No T->M transition
        lambda var, assignment: not any(
            assignment.get(var, "0") in ["M", "MT"] and 
            assignment.get(f"{var.split('_')[0]}_D{d-1}", "0") in ["T", "MT"]
            for d in range(2, num_days + 1) if var == f"{var.split('_')[0]}_D{d}"
        ),
        # Max 5 consecutive days
        lambda var, assignment: not any(
            all(assignment.get(f"{var.split('_')[0]}_D{d-k}", "0") in ["M", "T", "MT"] for k in range(6))
            for d in range(6, num_days + 1) if var == f"{var.split('_')[0]}_D{d}"
        ),
        # Min 2 employees per shift per day
        lambda var, assignment: all(
            sum(1 for e in range(1, num_employees + 1) if assignment.get(f"E{e}_D{d}", "0") in ["M", "MT"]) >= 2 and
            sum(1 for e in range(1, num_employees + 1) if assignment.get(f"E{e}_D{d}", "0") in ["T", "MT"]) >= 2
            for d in range(1, num_days + 1)
        ),
        # Max 223 workdays
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_D{d}", "0") in ["M", "T", "MT"]) <= 223
            for e in range(1, num_employees + 1)
        ),
        # Max 22 Sundays/holidays
        lambda var, assignment: all(
            sum(1 for d in range(1, num_days + 1) if assignment.get(f"E{e}_D{d}", "0") in ["M", "T", "MT"] and ((d-1) % 7 == 6 or d in holidays)) <= 22
            for e in range(1, num_employees + 1)
        )
    ]

    csp = CSP(variables, domains, constraints)
    solution = csp.backtracking_search()
    if solution:
        print("Solution found for employee scheduling.")
        # export
    else:
        print("No solution found.")

if __name__ == "__main__":
    employee_scheduling()