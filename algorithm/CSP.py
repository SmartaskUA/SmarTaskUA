from ortools.sat.python import cp_model
import numpy as np
from collections import defaultdict
import holidays as hl

from algorithm.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    export_schedule_to_csv,
    build_calendar,
    schedule_to_table
)

def _build_allowed_teams(employees):
    """
    Convert employee 'teams' labels to internal numeric team IDs.
    Fallback to team 'A' when none provided.
    """
    allowed = []
    for Employees in employees:
        codes = [get_team_code(t) for t in Employees.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed

def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):

    num_days = 365
    n_employees = len(employees)
    S = range(1, int(shifts) + 1)
    Employees = range(n_employees)
    D = range(1, num_days + 1)

    allowed_teams_per_emp = _build_allowed_teams(employees)
    vacs_dict = rows_to_vac_dict(vacations) 
    mins_raw, ideals_raw = rows_to_req_dicts(minimuns)

    min_required = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shifts):
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                min_required[(d, s, t)] = req

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

    # variables
    y, off, shift_id = {}, {}, {}
    # Iterate over all employees and days to create the variables
    # variable y[e,d,s,t] = 1 if employee e works shift s in team t on day d (binary)
    # variable off[employee,day] = 1 if employee e is off on day d (binary)
    # variable shift_id[employee,day] = s if employee e works shift s on day d (0 if off) (integer)
    for employee in Employees:
        for day in D:
            off[(employee, day)] = m.NewBoolVar(f"off_{employee}_{day}")
            shift_id[(employee, day)] = m.NewIntVar(0, int(shifts), f"shift_{employee}_{day}")
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

    # Max 5 worked days in any 6-day window
    window, max_in_window = 6, 5
    for employee in Employees:
        for start in range(1, num_days - window + 2):  # + 2 because range is exclusive at the end
            days = range(start, start + window)
            m.Add(sum(1 - off[(employee, day)] for day in days) <= max_in_window)

    # No special-days cap (22) per employee
    special_cap = 22
    for employee in Employees:
        sp_terms = [1 - off[(employee, day)] for day in D if day in special_days]
        if sp_terms:
            m.Add(sum(sp_terms) <= special_cap)

    # Cover Minimum Requirements
    unmet = {}
    for (day, s, t), req in min_required.items():
        cover = []
        for employee in Employees:
            if not vac_mask[(employee, day)] and t in allowed_teams_per_emp[employee]:
                cover.append(y[(employee, day, s, t)])
        u = m.NewIntVar(0, req, f"unmet_{day}_{s}_{t}")
        unmet[(day, s, t)] = u
        m.Add(sum(cover) + u >= req)

    # Workdays should be 223
    # --- Definitive Workday Rule: exactly 223 worked days per employee ---
    target_workdays = 223
    workdays = {}
    for employee in Employees:
        workdays[employee] = sum(1 - off[(employee, d)] for d in D)
        m.Add(workdays[employee] == target_workdays)

    # --- Objective: minimize unmet minimums only ---
    w_unmet_min = 1000
    m.Minimize(sum(w_unmet_min * unmet[k] for k in unmet))

    # Solve model
    solver = cp_model.CpSolver()
    if maxTime is not None:
        # maxTime is in minutes converted to seconds
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8

    status = solver.Solve(m)

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
        shifts=int(shifts),
    )