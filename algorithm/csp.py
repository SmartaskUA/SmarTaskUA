import copy
import csv
import json

class CSP:
    def __init__(self, variables, domains, employee_teams, num_days, num_employees):
        self.variables = variables
        self.domains = domains
        self.employee_teams = employee_teams
        self.num_days = num_days
        self.num_employees = num_employees
        self.neighbors = self.build_neighbors()

    def build_neighbors(self):
        neighbors = {var: [] for var in self.variables}
        for var in self.variables:
            emp, day, shift = var.split('_')
            day = int(day)
            if shift == "M":
                t_var = f"{emp}_{day}_T"
                if t_var in self.variables:
                    neighbors[var].append(t_var)
                    neighbors[t_var].append(var)
            if shift == "T" and day < self.num_days:
                m_var = f"{emp}_{day+1}_M"
                if m_var in self.variables:
                    neighbors[var].append(m_var)
                    neighbors[m_var].append(var)
            for other_var in self.variables:
                other_emp, other_day, other_shift = other_var.split('_')
                if other_day == str(day) and other_shift == shift and other_var != var:
                    neighbors[var].append(other_var)
        return neighbors

def forward_check(csp, var, value, assignment, domains):
    emp, day, shift = var.split('_')
    day = int(day)
    new_domains = copy.deepcopy(domains)

    for neighbor in csp.neighbors[var]:
        n_emp, n_day, n_shift = neighbor.split('_')
        n_day = int(n_day)

        if neighbor in assignment:
            continue

        if n_day == day and n_shift != shift:
            if value == "F":
                new_domains[neighbor] = ["F"]
            elif value in ["A", "B"]:
                new_domains[neighbor] = ["0"]
            elif value == "0":
                pass
            else:
                new_domains[neighbor] = ["0"]
        elif shift == "T" and n_shift == "M" and n_day == day + 1 and n_emp == emp:
            if value in ["A", "B"]:
                new_domains[neighbor] = ["0"]

        if not new_domains[neighbor]:
            return None

        if n_day == day and n_shift == shift and neighbor != var:
            m_a_count = 0
            m_b_count = 0
            t_a_count = 0
            t_b_count = 0
            assigned = set()
            for v in csp.variables:
                e, d, s = v.split('_')
                if int(d) != day or v in assigned:
                    continue
                val = assignment.get(v, new_domains[v][0] if len(new_domains[v]) == 1 else None)
                if val:
                    assigned.add(v)
                    if s == "M":
                        if val == "A":
                            m_a_count += 1
                        elif val == "B":
                            m_b_count += 1
                    else:
                        if val == "A":
                            t_a_count += 1
                        elif val == "B":
                            t_b_count += 1
            unassigned = sum(1 for v in csp.variables if int(v.split('_')[1]) == day and v not in assigned and v != neighbor)
            if shift == "M":
                if value == "A":
                    m_a_count += 1
                elif value == "B":
                    m_b_count += 1
                remaining_a = sum(1 for v in csp.variables if int(v.split('_')[1]) == day and v.split('_')[2] == "M" and v not in assigned and "A" in new_domains[v])
                remaining_b = sum(1 for v in csp.variables if int(v.split('_')[1]) == day and v.split('_')[2] == "M" and v not in assigned and "B" in new_domains[v])
                if m_a_count + remaining_a < 2 or m_b_count + remaining_b < 1:
                    return None
            else:
                if value == "A":
                    t_a_count += 1
                elif value == "B":
                    t_b_count += 1
                remaining_a = sum(1 for v in csp.variables if int(v.split('_')[1]) == day and v.split('_')[2] == "T" and v not in assigned and "A" in new_domains[v])
                remaining_b = sum(1 for v in csp.variables if int(v.split('_')[1]) == day and v.split('_')[2] == "T" and v not in assigned and "B" in new_domains[v])
                if t_a_count + remaining_a < 2 or t_b_count + remaining_b < 1:
                    return None

    return new_domains

def select_unassigned_variable(csp, assignment):
    unassigned = [var for var in csp.variables if var not in assignment]
    return min(unassigned, key=lambda var: len(csp.domains[var]), default=None)

def order_domain_values(csp, var):
    return sorted(csp.domains[var], key=lambda val: 0 if val == "0" else 1)

def backtrack(csp, assignment, domains):
    if len(assignment) == len(csp.variables):
        return assignment

    var = select_unassigned_variable(csp, assignment)
    if not var:
        return None

    for value in order_domain_values(csp, var):
        new_domains = forward_check(csp, var, value, assignment, domains)
        if new_domains is not None:
            assignment[var] = value
            result = backtrack(csp, assignment, new_domains)
            if result is not None:
                return result
            del assignment[var]
    return None

def solve_calendar():
    num_employees = 12
    num_days = 30
    employee_teams = {
        "E1": ["A"], "E2": ["A"], "E3": ["A"], "E4": ["A"],
        "E5": ["A", "B"], "E6": ["A", "B"], "E7": ["A"], "E8": ["A"],
        "E9": ["A"], "E10": ["B"], "E11": ["A", "B"], "E12": ["B"]
    }
    employees = [f"E{e}" for e in range(1, num_employees + 1)]
    shifts = ["M", "T"]

    with open("vacations.json", "r") as f:
        vacations = json.load(f)
        vacations = {emp: set(days) for emp, days in vacations.items()}

    variables = [f"{emp}_{day}_{shift}" for emp in employees for day in range(1, num_days + 1) for shift in shifts]

    def define_domain(emp):
        return [f"{t}" for t in employee_teams[emp]] + ["0"]

    domains = {
        var: ["F"] if int(var.split('_')[1]) in vacations[var.split('_')[0]] else define_domain(var.split('_')[0])
        for var in variables
    }

    csp = CSP(variables, domains, employee_teams, num_days, num_employees)
    assignment = {}
    for var in variables:
        if domains[var] == ["F"]:
            assignment[var] = "F"

    solution = backtrack(csp, assignment, domains)
    if solution is None:
        print("No solution found.")
        return

    calendar = {}
    for emp in employees:
        calendar[emp] = []
        for day in range(1, num_days + 1):
            m_var = f"{emp}_{day}_M"
            t_var = f"{emp}_{day}_T"
            m_val = solution[m_var]
            t_val = solution[t_var]
            if m_val == "F":
                shift = "FF"
            elif m_val == "0" and t_val == "0":
                shift = "00"
            else:
                shift = f"{m_val}{t_val}"
            calendar[emp].append(shift)

    with open("solved_calendar.csv", "w", newline="") as csvfile:
        csvwriter = csv.writer(csvfile, delimiter=',')
        col_width = 5
        first_col_width = 6
        header = ["dia".ljust(first_col_width)] + [f"|{str(day).ljust(col_width-2)}" for day in range(1, num_days + 1)] + ["|"]
        csvwriter.writerow(header)
        subheader = ["turno".ljust(first_col_width)] + [f"|{'MT'.ljust(col_width-2)}" for _ in range(num_days)] + ["|"]
        csvwriter.writerow(subheader)
        for emp in employees:
            emp_id = emp.lower().replace("E", "e")
            row = [emp_id.ljust(first_col_width)] + [f"| {shift.ljust(col_width-3)}" for shift in calendar[emp]] + ["|"]
            csvwriter.writerow(row)
    print("Solved calendar saved to 'solved_calendar.csv'")

if __name__ == "__main__":
    solve_calendar()