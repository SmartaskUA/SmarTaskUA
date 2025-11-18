import datetime
from collections import defaultdict

import pandas as pd
from ortools.sat.python import cp_model

from algorithm.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    export_schedule_to_csv,
    to_table,
)


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


def _holidays_in_year():
    """
    Same holidays set used in ILP_H.
    """
    feriados_pt = {
        datetime.date(2022, 1, 1): "New Year's Day",
        datetime.date(2022, 1, 6): 'Epiphany',
        datetime.date(2022, 3, 1): 'Day of Baleares',
        datetime.date(2022, 4, 14): 'Maundy Thursday',
        datetime.date(2022, 4, 15): 'Good Friday',
        datetime.date(2022, 5, 1): 'Labor Day',
        datetime.date(2022, 5, 2): 'Madrid Day',
        datetime.date(2022, 6, 29): 'Folga',
        datetime.date(2022, 7, 8): 'Folga',
        datetime.date(2022, 8, 15): 'Assumption Day',
        datetime.date(2022, 9, 8): 'Regional Holiday',
        datetime.date(2022, 10, 12): 'National Day',
        datetime.date(2021, 11, 1): "All Saints' Day",
        datetime.date(2021, 12, 6): 'Constitution Day',
        datetime.date(2021, 12, 8): 'Immaculate Conception',
        datetime.date(2021, 12, 25): 'Christmas Day',
    }
    return feriados_pt


def _generate_work_blocks():
    """
    Generate valid work blocks (A) based on specific combinations.
    Each tuple represents (start_hour, break_hour, end_hour).
    These are the same as in ILP_H.py.
    """
    blocks = [
        (9, 13, 18),   # 4h + 1h break + 4h
        (9, 14, 18),   # 5h + 1h break + 3h
        (9, 15, 18),   # 6h + 1h break + 2h
        (10, 14, 19),  # 4h + 1h break + 4h
        (10, 15, 19),  # 5h + 1h break + 3h
        (10, 16, 19),  # 6h + 1h break + 2h
        (11, 15, 20),  # 4h + 1h break + 4h
        (11, 16, 20),  # 5h + 1h break + 3h
        (11, 17, 20),  # 6h + 1h break + 2h
        (12, 16, 21),  # 4h + 1h break + 4h
        (12, 17, 21),  # 5h + 1h break + 3h
        (12, 18, 21),  # 6h + 1h break + 2h
        (13, 17, 22),  # 4h + 1h break + 4h
        (13, 18, 22),  # 5h + 1h break + 3h
        (13, 19, 22),  # 6h + 1h break + 2h
    ]
    return blocks


def _get_working_hours(block):
    """
    Returns the set of hours an employee is actually working (excluding the break hour).
    For block (9, 13, 18) -> {9,10,11,12,14,15,16,17}
    """
    start, break_start, end = block
    hours = set(range(start, break_start))            # first period
    hours.update(range(break_start + 1, end))         # second period (skip break hour)
    return hours


def _blocks_invalid_transition(block_today, block_tomorrow):
    """
    Check if transition from block_today to block_tomorrow is invalid
    (i.e., rest hours < 12). Used to enforce constraint (7).
    """
    end_today = block_today[2]
    start_tomorrow = block_tomorrow[0]
    # overnight rest: (24 - end_today) + start_tomorrow
    rest_hours = (24 - end_today) + start_tomorrow
    return rest_hours < 12


def solve(*, vacations, minimuns, employees, maxTime=None, year=2021, hours=13, rules=None):
    """
    CSP version implementing the ILP formulation on hourly blocks.

    Decision variable:
        x[i, d, a, e] = 1 if employee i works on day d with block a in team e.

    Constraints implemented (ILP1, hour version):
        (2) No work on vacations + at most one block per day
        (3) Only allowed teams per worker
        (4) Exactly 223 working days
        (5) Max 5 consecutive working days
        (6) Max 22 days on holidays/Sundays
        (7) Invalid transitions (rest < 12h) forbidden
        (8) y_dhe >= θ_dhe − ∑ α_a,h * x_i,d,a,e with y_dhe ≥ 0; objective = min ∑ y_dhe
    """

    # ------------------------- Sets and data ------------------------- #

    # Calendar same as ILP_H.py
    dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
    num_days = len(dates)  # should be 365
    D = range(1, num_days + 1)  # 1..365

    n_employees = len(employees)
    Employees = range(n_employees)

    work_blocks = _generate_work_blocks()
    num_blocks = len(work_blocks)
    Blocks = range(num_blocks)

    # Hours H: all hours that can appear in any block
    H = sorted({h for block in work_blocks for h in _get_working_hours(block)})

    # Ensure everyone has at least one team
    for idx, emp in enumerate(employees):
        if not emp.get("teams"):
            emp["teams"] = ["Equipa A"]

    allowed_teams_per_emp = _build_allowed_teams(employees)

    # All team IDs that appear in employees or in requirements
    all_team_ids_from_employees = set(t for emp_list in allowed_teams_per_emp for t in emp_list)

    # Vacations: vacs_dict maps employee_id(1-based) -> list of day indices (1..365)
    vacs_dict = rows_to_vac_dict(vacations)
    vac_mask = {(i, d): False for i in Employees for d in D}
    for emp_id, days in vacs_dict.items():
        i = emp_id - 1  # employees are 0-based inside solver
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True

    # Minimum and ideal requirements
    mins_raw, ideals_raw = rows_to_req_dicts(minimuns)

    # Convert mins_raw: (day, hour_str, team_id) -> integer θ_dhe
    # day is 1..365; hour_str '09-10', '10-11', ...; team_id integer keyed in TEAM_ID_TO_CODE
    min_required = {}
    for (day, hour_str, team_id), val in mins_raw.items():
        if not (1 <= day <= num_days):
            continue
        team_code = TEAM_ID_TO_CODE.get(team_id)
        if not team_code:
            continue
        try:
            req_val = int(val)
        except (ValueError, TypeError):
            continue
        min_required[(day, hour_str, team_code)] = req_val

    # Closed days: some entries use -1 as "closed" (no work)
    closed_days = {day for (day, hour_str, team_code), v in min_required.items() if v == -1}

    # Holidays/Sundays set F (for ILP constraint (6))
    pt_holidays = _holidays_in_year()
    year_int = int(year) if year is not None else 2025
    # 'dates' covers 2021-11-01..2022-10-31; we treat Sundays or feriados within this range
    sundays_holidays = [d for d in dates if d.weekday() == 6 or d.date() in pt_holidays]
    start_date = dates[0]
    special_days = {(d - start_date).days + 1 for d in sundays_holidays}
    special_days = {d for d in special_days if 1 <= d <= num_days}  # F

    print(f"Solving CSP-H: {n_employees} employees, {num_days} days, {num_blocks} blocks.")

    # ----------------------------- Model ----------------------------- #

    m = cp_model.CpModel()

    # Decision variables: x[e, d, b, t]
    # e: employee (0..n_employees-1)
    # d: day (1..num_days)
    # b: block index
    # t: team_id (only if allowed for employee e)
    x = {}

    # Also need shortage variables y_short[d, h, team_id] corresponding to y_dhe in model
    y_short = {}

    # Teams set: union of employees' teams and teams that appear in requirements
    team_ids_from_requirements = set()
    for (_, _, team_code), _v in min_required.items():
        team_ids_from_requirements.add(get_team_id(team_code))

    all_team_ids = sorted(all_team_ids_from_employees | team_ids_from_requirements)

    # Create x variables
    for e in Employees:
        allowed_teams = set(allowed_teams_per_emp[e])
        for d in D:
            for b in Blocks:
                for t in all_team_ids:
                    if t not in allowed_teams:
                        continue  # respects constraint (3)
                    var = m.NewBoolVar(f"x_{e}_{d}_{b}_{t}")
                    x[(e, d, b, t)] = var

    # Shortage variables y_dhe (only where there is a minimum defined and min_val >= 0)
    # Base index: (day, hour, team_id)
    for (day, hour_str, team_code), min_val in min_required.items():
        if min_val < 0:
            continue  # skip closed marker
        hour_num = int(hour_str.split("-")[0])
        team_id = get_team_id(team_code)
        key = (day, hour_num, team_id)
        if key not in y_short:
            y_short[key] = m.NewIntVar(0, n_employees, f"y_{day}_{hour_num}_{team_id}")

    # --------------------------- Constraints -------------------------- #

    # (2) Férias e máximo 1 horário por dia
    #   - Se dia de férias: nenhum bloco pode ser atribuído
    #   - Caso contrário: no máximo 1 bloco (qualquer equipa)
    for e in Employees:
        for d in D:
            vars_today = [x[(e, d, b, t)] for b in Blocks for t in all_team_ids if (e, d, b, t) in x]
            if not vars_today:
                continue
            if vac_mask[(e, d)]:
                # férias: proibido trabalhar
                m.Add(sum(vars_today) == 0)
            else:
                m.Add(sum(vars_today) <= 1)

    # (4) Total de dias de trabalho = 223 por trabalhador
    target_workdays = 223
    for e in Employees:
        workday_bools = [x[(e, d, b, t)] for d in D for b in Blocks for t in all_team_ids if (e, d, b, t) in x]
        if workday_bools:
            m.Add(sum(workday_bools) == target_workdays)

    # (5) Máximo 5 dias consecutivos de trabalho (janelas de 6 dias)
    for e in Employees:
        for j in range(1, num_days - 5 + 1):
            window_days = range(j, j + 6)  # j..j+5
            vars_window = [
                x[(e, d, b, t)]
                for d in window_days
                for b in Blocks
                for t in all_team_ids
                if (e, d, b, t) in x
            ]
            if vars_window:
                m.Add(sum(vars_window) <= 5)

    # (6) Máximo 22 dias de trabalho em F (feriados ou domingos)
    for e in Employees:
        vars_special = [
            x[(e, d, b, t)]
            for d in special_days
            for b in Blocks
            for t in all_team_ids
            if (e, d, b, t) in x
        ]
        if vars_special:
            m.Add(sum(vars_special) <= 22)

    # Closed days (min_val == -1) → ninguém trabalha
    for d in closed_days:
        for e in Employees:
            vars_day = [x[(e, d, b, t)] for b in Blocks for t in all_team_ids if (e, d, b, t) in x]
            if vars_day:
                m.Add(sum(vars_day) == 0)

    # (7) Transições inválidas entre blocos (descanso < 12h)
    # Implementado via combinação de blocos de dias consecutivos
    for e in Employees:
        for d in range(1, num_days):  # d e d+1
            for b_today in Blocks:
                for b_next in Blocks:
                    if _blocks_invalid_transition(work_blocks[b_today], work_blocks[b_next]):
                        for t in all_team_ids:
                            if (e, d, b_today, t) in x and (e, d + 1, b_next, t) in x:
                                m.Add(x[(e, d, b_today, t)] + x[(e, d + 1, b_next, t)] <= 1)

    # (8) y_dhe >= θ_dhe − ∑ α_a,h * x_i,d,a,e
    # α_a,h = 1 se horário a inclui hora h; caso contrário 0.
    for (day, hour_str, team_code), min_val in min_required.items():
        if min_val < 0:
            continue  # closed day already handled
        hour_num = int(hour_str.split("-")[0])
        team_id = get_team_id(team_code)
        key = (day, hour_num, team_id)
        if key not in y_short:
            # no need to define constraint if y not used
            continue
        y_var = y_short[key]
        # coverage at (day,hour,team_id)
        coverage_terms = []
        for e in Employees:
            for b in Blocks:
                if hour_num in _get_working_hours(work_blocks[b]):
                    if (e, day, b, team_id) in x:
                        coverage_terms.append(x[(e, day, b, team_id)])
        if not coverage_terms:
            # no candidate employees to cover this minimum; y_dhe >= theta (so y will be large)
            m.Add(y_var >= min_val)
        else:
            m.Add(y_var >= min_val - sum(coverage_terms))

    # Domain of y_short is already non-negative by construction.

    # ------------------------ Objective function ---------------------- #

    # ILP1 objective: minimize sum of shortages y_dhe over all d,h,e
    objective_terms = list(y_short.values())
    if objective_terms:
        m.Minimize(sum(objective_terms))
    else:
        # fallback: if no minimums were defined, minimize 0
        m.Minimize(0)

    # ---------------------------- Solve ------------------------------- #

    solver = cp_model.CpSolver()
    if maxTime is not None:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8

    status = solver.Solve(m)
    print(f"CSP-H status: {solver.StatusName(status)}")

    # ---------------------- Extract solution -------------------------- #

    assignment = defaultdict(list)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for e in Employees:
            emp_id = e + 1  # 1-based ID for output
            for d in D:
                # find which block/team was chosen on day d (if any)
                chosen = [
                    (b, t)
                    for b in Blocks
                    for t in all_team_ids
                    if (e, d, b, t) in x and solver.Value(x[(e, d, b, t)]) == 1
                ]
                if not chosen:
                    continue
                # by constraint (2) there is at most one
                b, t = chosen[0]
                assignment[emp_id].append((d, b, t))

    # ------------------------ Export / to_table ------------------------ #

    class View:
        pass

    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assignment

    export_schedule_to_csv(v, "schedule_cpsat_hours.csv", num_days=num_days)

    return to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        work_blocks=work_blocks,
    )
