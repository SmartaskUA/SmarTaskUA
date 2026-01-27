from ortools.sat.python import cp_model
from collections import defaultdict
import holidays as hl
import os

from algorithms.ilp_greedy import solve_heuristic
from algorithms.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    get_team_id,
    get_team_code,
    export_schedule_to_csv_shifts,
    build_calendar,
    schedule_to_table,
)


def _build_allowed_teams(employees):
    """Convert employee team labels to internal numeric IDs."""
    allowed = []
    for emp in employees:
        codes = [get_team_code(t) for t in emp.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed


def _build_greedy_hint(vacations, minimuns, employees, year, shifts):
    """Run the greedy heuristic and return its assignment (best effort)."""
    try:
        _, greedy_view = solve_heuristic(
            vacations=vacations,
            minimuns=minimuns,
            employees=employees,
            maxTime=None,
            year=year,
            shifts=shifts,
            rules=None,
            target_workdays=223,
            special_cap=22,
            return_view=True,
        )
        return greedy_view.assignment
    except Exception as exc:
        print(f"[CSPv2_greedy] Greedy warm-start failed: {exc}")
        return None


def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):
    num_days = 365
    n_employees = len(employees)
    shifts = int(shifts)
    S = range(1, shifts + 1)
    Employees = range(n_employees)
    D = range(1, num_days + 1)

    allowed_teams_per_emp = _build_allowed_teams(employees)
    vacs_dict = rows_to_vac_dict(vacations)
    mins_raw, ideals_raw = rows_to_req_dicts(minimuns)

    min_required = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= shifts:
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                min_required[(d, s, t)] = req

    ideal_required = {}
    for (d, s, t), v in ideals_raw.items():
        if 1 <= d <= num_days and 1 <= s <= shifts:
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                ideal_required[(d, s, t)] = req

    year = int(year) if year is not None else 2025
    dias_ano, sundays_1based = build_calendar(year)
    pt_holidays = hl.country_holidays("PT", years=[year])
    start_date = dias_ano[0].date()
    special_days = {(d - start_date).days + 1 for d in pt_holidays}
    special_days |= set(sundays_1based)

    vac_mask = {(i, d): False for i in Employees for d in D}
    for emp_id, days in vacs_dict.items():
        i = emp_id - 1
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True

    m = cp_model.CpModel()

    # Variables
    y, off = {}, {}
    for employee in Employees:
        for day in D:
            off[(employee, day)] = m.NewBoolVar(f"off_{employee}_{day}")
            if not vac_mask[(employee, day)]:
                for s in S:
                    for t in allowed_teams_per_emp[employee]:
                        y[(employee, day, s, t)] = m.NewBoolVar(f"y_{employee}_{day}_{s}_{t}")

    # Exactly one of: OFF or exactly one (s, t)
    for employee in Employees:
        for day in D:
            choices = [off[(employee, day)]]
            if not vac_mask[(employee, day)]:
                choices += [y[(employee, day, s, t)] for s in S for t in allowed_teams_per_emp[employee]]
            m.Add(sum(choices) == 1)

    # Forbid backward transitions directly on y (later shift -> earlier shift).
    for employee in Employees:
        allowed = allowed_teams_per_emp[employee]
        for day in range(1, num_days):
            next_day = day + 1
            for s_prev in S:
                for s_next in S:
                    if s_next >= s_prev:
                        continue
                    today_vars = [
                        y[(employee, day, s_prev, t)]
                        for t in allowed
                        if (employee, day, s_prev, t) in y
                    ]
                    next_vars = [
                        y[(employee, next_day, s_next, t)]
                        for t in allowed
                        if (employee, next_day, s_next, t) in y
                    ]
                    if today_vars and next_vars:
                        m.Add(sum(today_vars) + sum(next_vars) <= 1)

    # Max 5 worked days in any 6-day window
    window, max_in_window = 6, 5
    for employee in Employees:
        for start in range(1, num_days - window + 2):
            days = range(start, start + window)
            m.Add(sum(1 - off[(employee, day)] for day in days) <= max_in_window)

    # Special-days cap (22) per employee
    special_cap = 22
    for employee in Employees:
        sp_terms = [1 - off[(employee, day)] for day in D if day in special_days]
        if sp_terms:
            m.Add(sum(sp_terms) <= special_cap)

    # Cover minimum requirements
    unmet = {}
    for (day, s, t), req in min_required.items():
        cover = []
        for employee in Employees:
            if not vac_mask[(employee, day)] and t in allowed_teams_per_emp[employee]:
                cover.append(y[(employee, day, s, t)])
        u = m.NewIntVar(0, req, f"unmet_{day}_{s}_{t}")
        unmet[(day, s, t)] = u
        m.Add(sum(cover) + u >= req)

    unmet_ideal = {}
    for (day, s, t), ideal in ideal_required.items():
        cover = []
        for employee in Employees:
            if not vac_mask[(employee, day)] and t in allowed_teams_per_emp[employee]:
                cover.append(y[(employee, day, s, t)])
        z = m.NewIntVar(0, ideal, f"unmet_ideal_{day}_{s}_{t}")
        unmet_ideal[(day, s, t)] = z
        m.Add(sum(cover) + z >= ideal)

    # Exactly 223 working days per employee
    target_workdays = 223
    for employee in Employees:
        total_work = sum(1 - off[(employee, d)] for d in D)
        m.Add(total_work == target_workdays)

    # Objective
    w_unmet_min = 100
    w_unmet_ideal = 1
    obj = []
    obj += [w_unmet_min * unmet[k] for k in unmet]
    obj += [w_unmet_ideal * unmet_ideal[k] for k in unmet_ideal]
    m.Minimize(sum(obj))

    # Greedy warm-start hints (best effort).
    greedy_assignment = _build_greedy_hint(vacations, minimuns, employees, year, shifts)
    if greedy_assignment:
        gmap = {}
        for emp_id, lst in greedy_assignment.items():
            emp_idx = emp_id - 1
            if emp_idx not in Employees:
                continue
            for day, s, t in lst:
                if 1 <= day <= num_days and 1 <= s <= shifts:
                    gmap[(emp_idx, day)] = (s, t)

        for employee in Employees:
            for day in D:
                if vac_mask[(employee, day)]:
                    m.AddHint(off[(employee, day)], 1)
                    continue
                hint = gmap.get((employee, day))
                if hint is None:
                    continue
                s_hint, t_hint = hint
                m.AddHint(off[(employee, day)], 0)
                y_var = y.get((employee, day, s_hint, t_hint))
                if y_var is not None:
                    m.AddHint(y_var, 1)

    # Solve model
    solver = cp_model.CpSolver()
    if maxTime is not None:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.relative_gap_limit = 0.001
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True

    tracker = SolutionTracker()
    status = solver.Solve(m, tracker)

    # Generate log file
    base_name = f"logs_{n_employees}_employees_scenario"
    scenario_id = 1
    while True:
        filename = f"{base_name}_{scenario_id}.txt"
        if not os.path.exists(filename):
            break
        scenario_id += 1

    final_gap = 0.0
    if tracker.best_objective != 0 and tracker.best_objective != float("inf"):
        final_gap = abs(tracker.best_objective - tracker.best_bound) / abs(tracker.best_objective)

    with open(filename, "w") as f:
        f.write("SOLVER REPORT\n")
        f.write("=============\n")
        f.write(f"Employees: {n_employees}\n")
        f.write(f"Max Time Allowed: {maxTime if maxTime else 'Unlimited'} mins\n")
        f.write(f"Final Status: {solver.StatusName(status)}\n")
        f.write(f"Total Solutions Found: {tracker.solution_count}\n")
        f.write("\n--- PROGRESS LOG ---\n")
        f.write(f"{'Count':<8} | {'Time (s)':<12} | {'Objective':<15} | {'Gap':<10}\n")
        f.write("-" * 55 + "\n")

        for entry in tracker.history:
            f.write(f"{entry['count']:<8} | {entry['time']:<12.4f} | {entry['obj']:<15} | {entry['gap']:.4%}\n")

        f.write("-" * 55 + "\n")
        f.write("FINAL RESULTS:\n")
        f.write(f"Best Solution Time: {tracker.best_solution_time:.4f}s\n")
        f.write(f"Objective Value:    {tracker.best_objective}\n")
        f.write(f"Lower Bound:        {tracker.best_bound}\n")
        f.write(f"Final Gap:          {final_gap:.4%}\n")

    print(f"\nLog file saved to: {filename}")

    # Export schedule
    assign = defaultdict(list)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for employee in Employees:
            emp_id = employee + 1
            for day in D:
                if solver.Value(off[(employee, day)]) == 0:
                    assigned = None
                    for s in S:
                        for t in allowed_teams_per_emp[employee]:
                            v = y.get((employee, day, s, t))
                            if v is not None and solver.Value(v) == 1:
                                assigned = (s, t)
                                break
                        if assigned is not None:
                            break
                    if assigned is not None:
                        s_val, team_val = assigned
                        assign[emp_id].append((day, s_val, team_val))

    class View:
        pass

    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign
    v.shifts = shifts
    export_schedule_to_csv_shifts(v, "schedule_cpsat_greedy.csv", num_days=num_days)

    return schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=shifts,
    )


class SolutionTracker(cp_model.CpSolverSolutionCallback):
    def __init__(self):
        super().__init__()
        self.best_solution_time = 0.0
        self.best_objective = float("inf")
        self.best_bound = float("-inf")
        self.solution_count = 0
        self.history = []

    def on_solution_callback(self):
        self.solution_count += 1
        self.best_solution_time = self.WallTime()
        self.best_objective = self.ObjectiveValue()
        self.best_bound = self.BestObjectiveBound()

        gap = 0.0
        if self.best_objective != 0:
            gap = abs(self.best_objective - self.best_bound) / abs(self.best_objective)

        self.history.append(
            {
                "count": self.solution_count,
                "time": self.best_solution_time,
                "obj": self.best_objective,
                "bound": self.best_bound,
                "gap": gap,
            }
        )

        print(
            f"Solution #{self.solution_count} found at {self.best_solution_time:.2f}s "
            f"| Obj: {self.best_objective} | Gap: {gap:.2%}"
        )
