from ortools.sat.python import cp_model
import numpy as np
from collections import defaultdict
import holidays as hl

from algorithms.general.constraints import parse_constraints
from algorithms.general.solver_logging import SolutionTracker, write_csp_log
from algorithms.utils import (
    build_allowed_teams,
    infer_shift_count_from_dicts,
    rows_to_vac_dict,
    rows_to_req_dicts_any,
    safe_int,
    export_schedule_to_csv,
    build_calendar,
    schedule_to_table
)


def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None, constraints=None):

    resolved_year = safe_int(year, 2025)
    dias_ano, sundays_1based = build_calendar(resolved_year)
    num_days = len(dias_ano)
    n_employees = len(employees)
    Employees = range(n_employees)
    D = range(1, num_days + 1)

    plan = parse_constraints(constraints if constraints is not None else rules)

    allowed_teams_per_emp = build_allowed_teams(employees)
    vacs_dict = rows_to_vac_dict(vacations)
    mins_raw, ideals_raw = rows_to_req_dicts_any(minimuns, year=resolved_year)
    shift_count = safe_int(shifts, None)
    inferred_shifts = infer_shift_count_from_dicts(mins_raw, ideals_raw)
    if shift_count is None or shift_count <= 0:
        shift_count = inferred_shifts if inferred_shifts is not None else 2
    elif inferred_shifts is not None and inferred_shifts > shift_count:
        shift_count = inferred_shifts
    S = range(1, int(shift_count) + 1)

    min_required = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shift_count):
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                min_required[(d, s, t)] = req

    ideal_required = {}
    for (d, s, t), v in ideals_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shift_count):
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                ideal_required[(d, s, t)] = req

    pt_holidays = hl.country_holidays("PT", years=[resolved_year])
    start_date = dias_ano[0].date()
    special_days = {(d - start_date).days + 1 for d in pt_holidays}
    special_days |= set(sundays_1based)

    vac_mask = {(i, d): False for i in Employees for d in D}
    if plan.enforce_vacation:
        for emp_id, days in vacs_dict.items():
            i = emp_id - 1
            for d in days:
                if 1 <= d <= num_days:
                    vac_mask[(i, d)] = True


    m = cp_model.CpModel()

    # variables
    y, off, shift_id = {}, {}, {}
    # Iterate over all employees and days to create the variables
    # variable y[e,d,s,t] = 1 if employee e works shift s in team t on day d (binary)
    # variable off[employee,day] = 1 if employee e is off on day d (binary)
    # variable shift_id[employee,day] = s if employee e works shift s on day d (0 if off) (integer)
    for employee in Employees:
        for day in D:
            off[(employee, day)] = m.NewBoolVar(f"off_{employee}_{day}")
            shift_id[(employee, day)] = m.NewIntVar(0, int(shift_count), f"shift_{employee}_{day}")
            if not vac_mask[(employee, day)]:
                for s in S:
                    for t in allowed_teams_per_emp[employee]:
                        y[(employee, day, s, t)] = m.NewBoolVar(f"y_{employee}_{day}_{s}_{t}")

    # exactly one of: OFF or exactly one (s, t) (vacation days forced OFF)
    for employee in Employees:
        for day in D:
            choices = [off[(employee, day)]] 
            if not vac_mask[(employee, day)]:
                choices += [y[(employee, day, s, t)] for s in S for t in allowed_teams_per_emp[employee]]
            m.Add(sum(choices) == 1)

    # No earlier shift on the next day (if not off)
    if plan.enforce_no_earlier:
        for employee in Employees:
            for day in range(1, num_days):
                m.Add(shift_id[(employee, day + 1)] >= shift_id[(employee, day)]).OnlyEnforceIf(
                    [off[(employee, day)].Not(), off[(employee, day + 1)].Not()]
                )
            
    # Keep shift_id consistent with off and y
    # (off -> shift_id=0, assigned to (s,t) -> shift_id=s)
    for employee in Employees:
        for day in D:
            m.Add(shift_id[(employee, day)] == 0).OnlyEnforceIf(off[(employee, day)]) # if the employee is off, shift_id is 0 (does not work)
            if not vac_mask[(employee, day)]: # if not on vacation, can work
                for s in S: # iterate over possible shifts
                    for t in allowed_teams_per_emp[employee]: # iterate over possible teams
                        m.Add(shift_id[(employee, day)] == s).OnlyEnforceIf(y[(employee, day, s, t)]) # if y is 1 it means the employee works shift s

    # Max worked days in any window
    if plan.max_consecutive_window is not None and plan.max_consecutive_worked is not None:
        window = int(plan.max_consecutive_window)
        max_in_window = int(plan.max_consecutive_worked)
        for employee in Employees:
            for start in range(1, num_days - window + 2):
                days = range(start, start + window)
                m.Add(sum(1 - off[(employee, day)] for day in days) <= max_in_window)

    # Max special-days cap per employee
    if plan.special_cap is not None:
        special_cap = int(plan.special_cap)
        for employee in Employees:
            sp_terms = [1 - off[(employee, day)] for day in D if day in special_days]
            if sp_terms:
                m.Add(sum(sp_terms) <= special_cap)

    # Cover Minimum Requirements
    unmet = {}
    min_cov_weight = int(plan.min_coverage_weight)
    min_cov_hard = plan.min_coverage_hard
    if min_cov_hard or min_cov_weight > 0:
        for (day, s, t), req in min_required.items():
            cover = []
            for employee in Employees:
                if not vac_mask[(employee, day)] and t in allowed_teams_per_emp[employee]:
                    cover.append(y[(employee, day, s, t)])
            if min_cov_hard:
                m.Add(sum(cover) >= req)
            else:
                u = m.NewIntVar(0, req, f"unmet_{day}_{s}_{t}")
                unmet[(day, s, t)] = u
                m.Add(sum(cover) + u >= req)

    unmet_ideal = {}
    ideal_cov_weight = int(plan.ideal_coverage_weight)
    ideal_cov_hard = plan.ideal_coverage_hard
    if ideal_cov_hard or ideal_cov_weight > 0:
        for (day, s, t), ideal in ideal_required.items():
            cover = []
            for employee in Employees:
                if not vac_mask[(employee, day)] and t in allowed_teams_per_emp[employee]:
                    cover.append(y[(employee, day, s, t)])
            if ideal_cov_hard:
                m.Add(sum(cover) >= ideal)
            else:
                z = m.NewIntVar(0, ideal, f"unmet_ideal_{day}_{s}_{t}")
                unmet_ideal[(day, s, t)] = z
                m.Add(sum(cover) + z >= ideal)

    total_min = plan.total_workdays_min
    total_max = plan.total_workdays_max
    if total_min is not None or total_max is not None:
        for employee in Employees:
            total_work = sum(1 - off[(employee, d)] for d in D)
            if total_min is not None and total_max is not None:
                if total_min == total_max:
                    m.Add(total_work == total_min)
                else:
                    m.Add(total_work >= total_min)
                    m.Add(total_work <= total_max)
            elif total_min is not None:
                m.Add(total_work >= total_min)
            else:
                m.Add(total_work <= total_max)


    w_unmet_min = min_cov_weight
    w_unmet_ideal = ideal_cov_weight
    obj = []
    obj += [w_unmet_min * unmet[k] for k in unmet]
    obj += [w_unmet_ideal * unmet_ideal[k] for k in unmet_ideal]
    m.Minimize(sum(obj))

    # Solve model
    # --- SOLVING ---
    solver = cp_model.CpSolver()
    if maxTime is not None:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.relative_gap_limit = 0.001
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True 

    # Attach the tracker
    tracker = SolutionTracker()
    status = solver.Solve(m, solution_callback=tracker)
    write_csp_log(
        tracker=tracker,
        solver=solver,
        status=status,
        n_employees=n_employees,
        max_time=maxTime,
    )

    # --- EXPORT SCHEDULE ---
    assign = defaultdict(list)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for employee in Employees:
            emp_id = employee + 1
            for day in D:
                if solver.Value(off[(employee, day)]) == 0:
                    s_val = solver.Value(shift_id[(employee, day)])
                    if s_val > 0:
                        team_val = None
                        for t in allowed_teams_per_emp[employee]:
                            v = y.get((employee, day, s_val, t))
                            if v is not None and solver.Value(v) == 1:
                                team_val = t
                                break
                        if team_val is not None:
                            assign[emp_id].append((day, s_val, team_val))

    class View: pass
    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign
    export_schedule_to_csv(v, "schedule_cpsat.csv", num_days=num_days)

    return schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=int(shift_count),
    )
