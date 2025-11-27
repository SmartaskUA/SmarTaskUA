from ortools.sat.python import cp_model
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
    schedule_to_table,
)

from algorithm.rules_engine import RuleEngine, register_default_handlers
from algorithm.contexts.CPSatContext import CPSatContext

def _build_allowed_teams(employees):
    """
    Convert employee 'teams' labels to internal numeric team IDs.
    Fallback to team 'A' when none provided.
    """
    allowed = []
    for emp in employees:
        codes = [get_team_code(t) for t in emp.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed

def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):

    num_days = 365
    n_employees = len(employees)
    S = range(1, int(shifts) + 1)
    Employees = range(n_employees)           # 0-based internal
    D = range(1, num_days + 1)               # 1-based days for model indexing

    allowed_teams_per_emp = _build_allowed_teams(employees)

    # Inputs → dictionaries
    vacs_dict = rows_to_vac_dict(vacations)                      # {emp_id(1b): [days]}
    mins_raw, _ideals_raw = rows_to_req_dicts(minimuns)          # {(day,shift,team_id): req}

    # Normalize mins to CP-SAT domain / filter by shift range
    min_required = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shifts):
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                min_required[(d, s, t)] = req

    # Special days (PT holidays + Sundays)
    year = int(year) if year is not None else 2025
    dias_ano, sundays_1based = build_calendar(year)
    pt_holidays = hl.country_holidays("PT", years=[year])
    start_date = dias_ano[0].date()
    special_days = {(d - start_date).days + 1 for d in pt_holidays}
    special_days |= set(sundays_1based)

    # Vacation mask (0-based employees, 1-based days)
    vac_mask = {(i, d): False for i in Employees for d in D}
    for emp_id_1b, days in vacs_dict.items():
        i = emp_id_1b - 1
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True

    m = cp_model.CpModel()

    # Vars
    y, off, shift_id = {}, {}, {}
    for e in Employees:
        for day in D:
            off[(e, day)] = m.NewBoolVar(f"off_{e}_{day}")
            shift_id[(e, day)] = m.NewIntVar(0, int(shifts), f"shift_{e}_{day}")
            if not vac_mask[(e, day)]:
                for s in S:
                    for t in allowed_teams_per_emp[e]:
                        y[(e, day, s, t)] = m.NewBoolVar(f"y_{e}_{day}_{s}_{t}")

    # Build rule engine (1-based IDs for metadata)
    teams_map = {i + 1: allowed_teams_per_emp[i] for i in Employees}
    engine = RuleEngine(
        rules_config=(rules or {}),
        num_days=num_days,
        shifts=int(shifts),
        employees=list(range(1, n_employees + 1)),
        teams_map=teams_map,
        vacations_1based=vacs_dict,
        special_days_1based=special_days,
        target_workdays=223,
    )
    register_default_handlers(engine)

    # If vacation rule is disabled, neutralize mask so vacation days don't force OFF
    if not engine.has_vac_block:
        vac_mask = {(e, d): False for e in Employees for d in D}

    # Exactly-one choice per (employee, day)
    for e in Employees:
        for day in D:
            choices = [off[(e, day)]]
            if not vac_mask[(e, day)]:
                choices += [y[(e, day, s, t)] for s in S for t in allowed_teams_per_emp[e]]
            m.Add(sum(choices) == 1)

    # Channeling shift_id ↔ off/y
    for e in Employees:
        for day in D:
            m.Add(shift_id[(e, day)] == 0).OnlyEnforceIf(off[(e, day)])
            if not vac_mask[(e, day)]:
                for s in S:
                    for t in allowed_teams_per_emp[e]:
                        v = y.get((e, day, s, t))
                        if v is not None:
                            m.Add(shift_id[(e, day)] == s).OnlyEnforceIf(v)

    # Apply rules via handlers
    ctx = CPSatContext(
        m=m, Employees=Employees, D=D, S=S, num_days=num_days, shifts=int(shifts),
        off=off, shift_id=shift_id, y=y,
        vac_mask=vac_mask,
        allowed_teams_per_emp=allowed_teams_per_emp,
        min_required=min_required,
        special_days=special_days,
    )
    engine.apply_cp_sat(ctx)

    # Objective (handlers contribute terms)
    if ctx.obj_terms:
        m.Minimize(sum(ctx.obj_terms))
    else:
        m.Minimize(0)

    # ----- Solve -----
    solver = cp_model.CpSolver()
    if maxTime is not None:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8

    status = solver.Solve(m)

    # ----- Extract solution -----
    assign = defaultdict(list)  # emp_id(1b) -> [(day, shift, team_id)]
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for e in Employees:
            emp_id = e + 1
            for day in D:
                if solver.Value(off[(e, day)]) == 0:
                    s_val = solver.Value(shift_id[(e, day)])
                    if s_val > 0:
                        team_val = None
                        for t in allowed_teams_per_emp[e]:
                            v = y.get((e, day, s_val, t))
                            if v is not None and solver.Value(v) == 1:
                                team_val = t
                                break
                        if team_val is not None:
                            assign[emp_id].append((day, s_val, team_val))

    # Export CSV
    class View: pass
    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign
    export_schedule_to_csv(v, "schedule_cpsat.csv", num_days=num_days)

    # Return standardized table
    return schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=int(shifts),
    )
