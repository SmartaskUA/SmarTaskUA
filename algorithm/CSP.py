# algorithm/cpsat_solver.py
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

def _to_table(assign, num_days, vacs_dict=None):
    """
    Build the TaskManager-compatible table, marking F on vacations.
    """
    header = ["funcionario"] + [f"Dia {d}" for d in range(1, num_days + 1)]
    rows = [header]
    label = {1: "M_", 2: "T_", 3: "N_"}
    all_emp_ids = set(assign.keys()) | set(vacs_dict.keys() if vacs_dict else [])
    for emp_id in sorted(all_emp_ids):
        day_to = {d: (s, t) for (d, s, t) in assign.get(emp_id, [])}
        vac_days = set(vacs_dict.get(emp_id, [])) if vacs_dict else set()
        line = [str(emp_id)]
        for d in range(1, num_days + 1):
            if d in vac_days:
                line.append("F")
            elif d in day_to:
                s, t = day_to[d]
                line.append(label.get(s, "") + TEAM_ID_TO_CODE.get(t, str(t)))
            else:
                line.append("0")
        rows.append(line)
    return rows

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
            lits = [off[(employee, day)]]
            if not vac_mask[(employee, day)]:
                lits += [y[(employee, day, s, t)] for s in S for t in allowed_teams_per_emp[employee]]
            m.Add(sum(lits) == 1)


    for employee in Employees:
        for day in range(1, num_days):
            m.Add(shift_id[(employee, day + 1)] >= shift_id[(employee, day)]).OnlyEnforceIf(
                [off[(employee, day)].Not(), off[(employee, day + 1)].Not()]
            )

    # link shift_id to assignment
    for employee in Employees:
        for day in D:
            m.Add(shift_id[(employee, day)] == 0).OnlyEnforceIf(off[(employee, day)])
            if not vac_mask[(employee, day)]:
                for s in S:
                    for t in allowed_teams_per_emp[employee]:
                        m.Add(shift_id[(employee, day)] == s).OnlyEnforceIf(y[(employee, day, s, t)])

    # Max 5 worked days in any 6-day window
    window, max_in_window = 6, 5
    for employee in Employees:
        for start in range(1, num_days - window + 2):
            days = range(start, start + window)
            m.Add(sum(1 - off[(employee, day)] for day in days) <= max_in_window)

    # No special-days cap (22) per employee
    special_cap = 22
    for employee in Employees:
        sp_terms = [1 - off[(employee, day)] for day in D if day in special_days]
        if sp_terms:
            m.Add(sum(sp_terms) <= special_cap)

    # No earlier shift on the next day
    for employee in Employees:
        for day in range(1, num_days):
            both = m.NewBoolVar(f"both_{employee}_{day}")
            m.AddBoolAnd([off[(employee, day)].Not(), off[(employee, day + 1)].Not()]).OnlyEnforceIf(both)
            m.Add(shift_id[(employee, day + 1)] >= shift_id[(employee, day)]).OnlyEnforceIf(both)

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
    target_workdays = 223
    workdays = {employee: m.NewIntVar(0, target_workdays, f"work_{employee}") for employee in Employees}
    dev_under = {employee: m.NewIntVar(0, target_workdays, f"dev_under_{employee}") for employee in Employees}
    dev_over  = {employee: m.NewIntVar(0, target_workdays, f"dev_over_{employee}") for employee in Employees}
    for employee in Employees:
        m.Add(workdays[employee] == sum(1 - off[(employee, d)] for d in D))
        m.Add(workdays[employee] + dev_under[employee] - dev_over[employee] == target_workdays)

    w_unmet_min, w_workday_dev = 1000, 1
    obj = []
    obj += [w_unmet_min * unmet[k] for k in unmet]
    obj += [w_workday_dev * (dev_under[employee] + dev_over[employee]) for employee in Employees]
    m.Minimize(sum(obj))

    # ----- solve -----
    solver = cp_model.CpSolver()
    if maxTime is not None:
        # maxTime is in minutes → convert to seconds
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    # parallel workers (tune as desired)
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

    return _to_table(assign, num_days, vacs_dict=vacs_dict)
