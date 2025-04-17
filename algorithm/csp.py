import copy
import time
import csv
import os
import json
from collections import deque
from formulation import generate_initial_calendar

class Constraint:
    def __init__(self, vars):
        self.vars = vars
    def propagate(self, domains, csp):
        """Return True if domains changed, None if no change, or False on failure."""
        raise NotImplementedError

def revise(domains, xi, xj, func):
    """Revise domain of xi wrt xj and func(xi_val, xj_val)."""
    revised = False
    to_remove = []
    for a in domains[xi]:
        if not any(func(a, b) for b in domains[xj]):
            to_remove.append(a)
    if to_remove:
        domains[xi] = [a for a in domains[xi] if a not in to_remove]
        revised = True
    return revised

class BinaryConstraint(Constraint):
    def __init__(self, x, y, func):
        super().__init__([x, y])
        self.x, self.y = x, y
        self.func = func

    def propagate(self, domains, csp):
        r1 = revise(domains, self.x, self.y, self.func)
        r2 = revise(domains, self.y, self.x, lambda b,a: self.func(a,b))
        if r1 is False or r2 is False:
            return False
        if r1 or r2:
            return True
        return None

class SumAtMost(Constraint):
    def __init__(self, vars, k):
        super().__init__(vars)
        self.k = k

    def propagate(self, domains, csp):
        lb = 0; ub = 0
        for v in self.vars:
            dom = domains[v]
            if '0' in dom or 'F' in dom:
                minv = 0
            else:
                minv = 1
            maxv = 1 if any(val in ['A','B'] for val in dom) else 0
            lb += minv; ub += maxv
        if lb > self.k:
            return False
        if ub <= self.k:
            return None
        changed = False
        if lb == self.k:
            for v in self.vars:
                dom = domains[v]
                if '0' in dom or 'F' in dom:
                    newdom = [val for val in dom if val not in ['A','B']]
                    if len(newdom) < len(dom):
                        domains[v] = newdom
                        changed = True
        return True if changed else None

class CountAtLeast(Constraint):
    def __init__(self, vars, team, k):
        super().__init__(vars)
        self.team = team
        self.k = k

    def propagate(self, domains, csp):
        ub = 0
        for v in self.vars:
            dom = domains[v]
            if self.team in dom:
                ub += 1
        if ub < self.k:
            return False
        return None

class No6ConsecutiveWork(Constraint):
    def __init__(self, emp, num_days):
        windows = []
        for start in range(1, num_days - 5):
            win = []
            for d in range(start, start + 6):
                win.extend([f"{emp}_{d}_M", f"{emp}_{d}_T"] )
            windows.append(win)
        super().__init__([v for win in windows for v in win])
        self.windows = windows

    def propagate(self, domains, csp):
        for win in self.windows:
            full = True
            for i in range(0, len(win), 2):
                dom_m = domains[win[i]]
                dom_t = domains[win[i+1]]
                if any(val in ['0','F'] for val in dom_m) or any(val in ['0','F'] for val in dom_t):
                    full = False
                    break
            if full:
                return False
        return None

class CSP:
    def __init__(self, variables, domains):
        self.variables = list(variables)
        self.domains = {v:list(domains[v]) for v in variables}
        self.var_to_constraints = {v: [] for v in variables}

    def add_constraint(self, constraint):
        for v in constraint.vars:
            self.var_to_constraints[v].append(constraint)

    def propagate(self, var):
        queue = deque([var])
        while queue:
            v = queue.popleft()
            for c in list(self.var_to_constraints[v]):
                res = c.propagate(self.domains, self)
                if res is False:
                    return False
                if res:
                    for u in c.vars:
                        if len(self.domains[u]) == 1 and u not in queue:
                            queue.append(u)
        return True

    def select_variable(self):
        choices = [v for v in self.variables if len(self.domains[v]) > 1]
        if not choices:
            return None
        return min(choices, key=lambda v: len(self.domains[v]))

    def order_values(self, var):
        dom = self.domains[var]
        return sorted(dom, key=lambda val: 0 if val in ['A','B'] else 1)

    def validate_solution(self, assignment):
        for v, dom in self.domains.items():
            if len(dom) != 1:
                return False
        assign = {v:self.domains[v][0] for v in self.domains}
        return True

    def search(self, timeout=60):
        start = time.time()
        def backtrack():
            if time.time() - start > timeout:
                return None
            var = self.select_variable()
            if var is None:
                return {v:self.domains[v][0] for v in self.domains}
            orig_dom = list(self.domains[var])
            for val in self.order_values(var):
                backup = copy.deepcopy(self.domains)
                self.domains[var] = [val]
                if self.propagate(var):
                    result = backtrack()
                    if result is not None:
                        return result
                self.domains = backup
            return None
        return backtrack()

def solve_calendar():
    vars, domains, employees, num_days, num_employees, holidays = generate_initial_calendar()
    csp = CSP(vars, domains)

    for emp in employees:
        for d in range(1, num_days):
            v_t = f"{emp}_{d}_T"
            v_m = f"{emp}_{d+1}_M"
            csp.add_constraint(BinaryConstraint(v_t, v_m,
                lambda x,y: not (x in ['A','B'] and y in ['A','B'])))
    for emp in employees:
        for d in range(1, num_days+1):
            v_m = f"{emp}_{d}_M"; v_t = f"{emp}_{d}_T"
            csp.add_constraint(BinaryConstraint(v_m, v_t,
                lambda x,y: not (x in ['A','B'] and y in ['A','B'])))

    for emp in employees:
        emp_vars = [f"{emp}_{d}_{s}" for d in range(1, num_days+1) for s in ('M','T')]
        csp.add_constraint(SumAtMost(emp_vars, 20))
        holiday_vars = [f"{emp}_{h}_{s}" for h in holidays for s in ('M','T')]
        csp.add_constraint(SumAtMost(holiday_vars, 2))
        csp.add_constraint(No6ConsecutiveWork(emp, num_days))

    for d in range(1, num_days+1):
        m_vars = [f"{e}_{d}_M" for e in employees]
        t_vars = [f"{e}_{d}_T" for e in employees]
        csp.add_constraint(CountAtLeast(m_vars, 'A', 2))
        csp.add_constraint(CountAtLeast(m_vars, 'B', 1))
        csp.add_constraint(CountAtLeast(t_vars, 'A', 2))
        csp.add_constraint(CountAtLeast(t_vars, 'B', 1))

    sol = csp.search(timeout=600)
    if sol:
        print("Solution found!")
    else:
        print("No solution within timeout.")

if __name__ == '__main__':
    solve_calendar()
