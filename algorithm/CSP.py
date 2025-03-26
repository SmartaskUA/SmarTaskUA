import copy
import random

class CSP:
    def __init__(self, variables, domains, constraints):
        """
        Initialize the CSP.
        - variables: List of variable names (e.g., ['X1', 'X2', ...])
        - domains: Dict mapping variables to their possible values (e.g., {'X1': [0, 1], 'X2': [0, 1]})
        - constraints: List of functions that take (var, assignment) and return True if satisfied
        """
        self.variables = variables
        self.domains = domains.copy()  # Original domains
        self.constraints = constraints
        self.current_domains = domains.copy()  # Domains reduced during search

    def is_valid_assignment(self, var, value, assignment):
        """Check if assigning 'value' to 'var' satisfies all constraints."""
        temp_assignment = assignment.copy()
        temp_assignment[var] = value
        return all(constraint(var, temp_assignment) for constraint in self.constraints)

    def forward_check(self, var, value, assignment):
        """Propagate constraints by reducing domains of unassigned variables."""
        affected_vars = set()
        temp_assignment = assignment.copy()
        temp_assignment[var] = value

        # Identify variables affected by constraints involving 'var'
        for constraint in self.constraints:
            for v in self.variables:
                if v != var and v not in assignment:
                    if constraint(v, temp_assignment):  # Constraint might involve var and v
                        affected_vars.add(v)

        # Reduce domains of affected variables
        new_domains = copy.deepcopy(self.current_domains)
        for v in affected_vars:
            new_domains[v] = [val for val in new_domains[v] if self.is_valid_assignment(v, val, temp_assignment)]
            if not new_domains[v]:  # Domain wipeout
                return None
        return new_domains

    def select_unassigned_variable(self, assignment):
        """Select the unassigned variable with the smallest remaining domain (MRV heuristic)."""
        unassigned = [v for v in self.variables if v not in assignment]
        if not unassigned:
            return None
        return min(unassigned, key=lambda v: len(self.current_domains[v]))

    def order_domain_values(self, var, assignment):
        """Return the current domain values for the variable."""
        return self.current_domains[var]

    def backtracking_search(self):
        """Perform iterative backtracking search with forward checking."""
        stack = []
        stack.append(({}, self.domains.copy()))  # (assignment, domains)

        while stack:
            assignment, domains = stack.pop()
            if len(assignment) == len(self.variables):
                return assignment

            self.current_domains = domains  # Update current domains for this state
            var = self.select_unassigned_variable(assignment)
            for value in self.order_domain_values(var, assignment):
                if self.is_valid_assignment(var, value, assignment):
                    new_assignment = assignment.copy()
                    new_assignment[var] = value
                    new_domains = self.forward_check(var, value, assignment)
                    if new_domains is not None:
                        stack.append((new_assignment, new_domains))
        return None

def employee_scheduling():
    num_employees = 15
    num_days = 365
    holidays = {1, 25, 50, 75, 100, 150, 200, 250, 300, 350}
    vacations = {f"E{e}": set(random.sample(range(1, num_days + 1), 30)) for e in range(1, num_employees + 1)}

    variables = [f"E{e}_D{d}" for e in range(1, num_employees + 1) for d in range(1, num_days + 1)]
    domains = {var: ["F"] if int(var.split('_')[1][1:]) in vacations[var.split('_')[0]] else ["0", "M", "T", "MT"] for var in variables}

    constraints = [
        # No T-to-M transition
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
        # Add export logic here if needed
    else:
        print("No solution found.")

if __name__ == "__main__":
    employee_scheduling()