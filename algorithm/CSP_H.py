import datetime
import time
import pandas as pd
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
    schedule_to_table,
    to_table
)


# depois de m foi escrito para "model_proto.txt"
def find_empty_bool_or(proto_path="/home/hugo/Desktop/SmarTaskUA/algorithm/model_proto.txt"):
    """
    Analisa o arquivo model_proto.txt procurando por blocos bool_or vazios.
    Esta função deve ser chamada apenas após solve() ser executado e gerar o arquivo.
    """
    import os
    import re

    # Verificar se o arquivo existe antes de tentar abrir
    if not os.path.exists(proto_path):
        print(f"[INFO] Arquivo {proto_path} não existe ainda (será criado após solve())")
        return

    with open(proto_path, "r") as f:
        text = f.read()

    blocks = re.finditer(r"bool_or\s*\{\s*(.*?)\s*\}", text, re.DOTALL)
    empties = []
    for i, b in enumerate(blocks, start=1):
        inner = b.group(1).strip()
        if inner == "":
            empties.append(i)
    print(f"[INFO] bool_or blocks found with empty body: {len(empties)}")
    if len(empties) > 0:
        for match in re.finditer(r"(.{0,200}bool_or\s*\{\s*(.*?)\s*\}.{0,200})", text, re.DOTALL):
            inner = match.group(2).strip()
            if inner == "":
                print("---- context ----")
                print(match.group(1))
                print("-----------------")
                break


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


def Holidays_in_year():
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
        datetime.date(2021, 12, 25): 'Christmas Day'
    }
    return feriados_pt


def _generate_work_blocks():
    """
    Same blocks as ILP_Horas: (start_hour, break_hour, end_hour).
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
    Returns set of hours an employee is actually working (excluding break).
    For block (9, 13, 18): {9,10,11,12,14,15,16,17}
    """
    start, break_start, end = block
    hours = set(range(start, break_start))
    hours.update(range(break_start + 1, end))
    return hours


def _blocks_invalid_transition(block_today, block_tomorrow):
    """
    Transition invalid if overnight rest < 12h.
    """
    end_today = block_today[2]
    start_tomorrow = block_tomorrow[0]
    rest_hours = (24 - end_today) + start_tomorrow
    return rest_hours < 12


def solve(*, vacations, minimuns, employees, maxTime=None, year=2021, hours=13, rules=None):
    """
    CSP version implementing the ILP_Horas formulation with block variables x[i,d,a,e].
    """

    # ---------------------------- Dados iniciais ---------------------------- #

    dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
    num_days = len(dates)  # 365
    D = range(1, num_days + 1)

    n_employees = len(employees)
    Employees = range(n_employees)

    print(f"Solving for {n_employees} employees over {num_days} days with {hours} working hours.")
    print(f"Employees data sample: {employees}")

    work_blocks = _generate_work_blocks()
    num_blocks = len(work_blocks)
    Blocks = range(num_blocks)

    # Set of all hours that appear in any block
    H = sorted({h for block in work_blocks for h in _get_working_hours(block)})

    for idx, emp in enumerate(employees):
        if not emp.get("teams"):
            print(f"[ERROR] Employee {idx+1} has NO teams assigned!")
            emp["teams"] = ["Equipa A"]

    allowed_teams_per_emp = _build_allowed_teams(employees)

    vacs_dict = rows_to_vac_dict(vacations)

    mins_raw, ideals = rows_to_req_dicts(minimuns)

    min_required = {}
    for (day, hour, team_id), val in mins_raw.items():
        if 1 <= day <= num_days:
            team_code = TEAM_ID_TO_CODE.get(team_id)
            if team_code:
                try:
                    req_val = int(val)
                    min_required[(day, hour, team_code)] = req_val
                except (ValueError, TypeError):
                    pass

    # Days with -1 → closed
    closed_days = {d for (d, h, t), v in min_required.items() if v == -1}

    pt_holidays = Holidays_in_year()
    year = int(year) if year is not None else 2025
    sundays_holidays = [
        d for d in dates if d.weekday() == 6 or d.date() in pt_holidays
    ]

    start_date = dates[0]
    special_days = {(d - start_date).days + 1 for d in sundays_holidays}
    special_days = {d for d in special_days if 1 <= d <= num_days}
    print(f"[DEBUG] special_days count (1..{num_days}): {len(special_days)}")

    vac_mask = {(i, d): False for i in Employees for d in D}
    for emp_id, days in vacs_dict.items():
        i = emp_id - 1
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True

    # ---------------------------- Modelo ---------------------------- #

    m = cp_model.CpModel()

    # Decision variables: x[e, d, b, t]
    x = {}

    # Shortage variables y_dhe
    y_short = {}

    # All team IDs from employees and requirements
    all_team_ids_from_emp = set(t for per in allowed_teams_per_emp for t in per)
    team_ids_from_req = set(get_team_id(tc) for (_, _, tc) in min_required.keys())
    all_team_ids = sorted(all_team_ids_from_emp | team_ids_from_req)

    # Create x
    for e in Employees:
        allowed_teams = set(allowed_teams_per_emp[e])
        for d in D:
            for b in Blocks:
                for t in all_team_ids:
                    if t not in allowed_teams:
                        continue
                    x[(e, d, b, t)] = m.NewBoolVar(f"x_{e}_{d}_{b}_{t}")

    # Create y_short[d,h,team_id] for positive mins
    for (day, hour_str, team_code), min_val in min_required.items():
        if min_val < 0:
            continue
        hour_num = int(hour_str.split('-')[0])
        team_id = get_team_id(team_code)
        key = (day, hour_num, team_id)
        if key not in y_short:
            y_short[key] = m.NewIntVar(0, n_employees, f"y_{day}_{hour_num}_{team_id}")

    # ---------------------------- Restrições ---------------------------- #

    # (2) Férias e no máximo 1 bloco por dia
    for e in Employees:
        for d in D:
            vars_today = [x[(e, d, b, t)]
                          for b in Blocks
                          for t in all_team_ids
                          if (e, d, b, t) in x]
            if not vars_today:
                continue
            if vac_mask[(e, d)]:
                m.Add(sum(vars_today) == 0)
            else:
                m.Add(sum(vars_today) <= 1)

    # (4) 223 dias de trabalho por trabalhador
    target_workdays = 223
    for e in Employees:
        workday_bools = [x[(e, d, b, t)]
                         for d in D
                         for b in Blocks
                         for t in all_team_ids
                         if (e, d, b, t) in x]
        if workday_bools:
            m.Add(sum(workday_bools) == target_workdays)

    # (5) Máx. 5 dias consecutivos (janela de 6)
    for e in Employees:
        for j in range(1, num_days - 5 + 1):
            window_days = range(j, j + 6)
            vars_window = [x[(e, d, b, t)]
                           for d in window_days
                           for b in Blocks
                           for t in all_team_ids
                           if (e, d, b, t) in x]
            if vars_window:
                m.Add(sum(vars_window) <= 5)

    # (6) Máx. 22 dias de trabalho em feriados/domingos
    for e in Employees:
        vars_special = [x[(e, d, b, t)]
                        for d in special_days
                        for b in Blocks
                        for t in all_team_ids
                        if (e, d, b, t) in x]
        if vars_special:
            m.Add(sum(vars_special) <= 22)

    # Closed days: ninguém trabalha
    for d in closed_days:
        for e in Employees:
            vars_day = [x[(e, d, b, t)]
                        for b in Blocks
                        for t in all_team_ids
                        if (e, d, b, t) in x]
            if vars_day:
                m.Add(sum(vars_day) == 0)

    # (7) Transições inválidas (descanso < 12h) proibidas
    for e in Employees:
        for d in range(1, num_days):
            for b_today in Blocks:
                for b_next in Blocks:
                    if _blocks_invalid_transition(work_blocks[b_today], work_blocks[b_next]):
                        for t in all_team_ids:
                            if (e, d, b_today, t) in x and (e, d+1, b_next, t) in x:
                                m.Add(x[(e, d, b_today, t)] + x[(e, d+1, b_next, t)] <= 1)

    # (8) y_dhe >= theta_dhe - sum alpha_a,h * x_i,d,a,e
    for (day, hour_str, team_code), min_val in min_required.items():
        if min_val < 0:
            continue
        hour_num = int(hour_str.split('-')[0])
        team_id = get_team_id(team_code)
        key = (day, hour_num, team_id)
        if key not in y_short:
            continue
        y_var = y_short[key]

        coverage_terms = []
        for e in Employees:
            for b in Blocks:
                if hour_num in _get_working_hours(work_blocks[b]):
                    if (e, day, b, team_id) in x:
                        coverage_terms.append(x[(e, day, b, team_id)])

        if not coverage_terms:
            m.Add(y_var >= min_val)
        else:
            m.Add(y_var >= min_val - sum(coverage_terms))

    # ---------------------------- Função objetivo ---------------------------- #

    missed_terms = list(y_short.values())
    if missed_terms:
        m.Minimize(sum(missed_terms))
    else:
        m.Minimize(0)

    # ---------------------------- Resolver modelo ---------------------------- #

    solver = cp_model.CpSolver()
    if maxTime is not None:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8

    status = solver.Solve(m)
    print(f"CSP-H status: {solver.StatusName(status)}")

    print("\n[DEBUG] Workdays per employee:")
    for e in Employees:
        worked = 0
        for d in D:
            if any(solver.Value(x[(e, d, b, t)]) == 1
                   for b in Blocks
                   for t in all_team_ids
                   if (e, d, b, t) in x):
                worked += 1
        print(f"  Emp {e+1}: {worked}")

    # ---------------------------- Extrair solução ---------------------------- #

    assign = defaultdict(list)
    for e in Employees:
        emp_id = e + 1
        for d in D:
            chosen = [(b, t)
                      for b in Blocks
                      for t in all_team_ids
                      if (e, d, b, t) in x and solver.Value(x[(e, d, b, t)]) == 1]
            if not chosen:
                continue
            b, t = chosen[0]
            assign[emp_id].append((d, b, t))

    # ---------------------------- Exportar e retornar tabela ---------------------------- #

    class View:
        pass

    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign

    # Debug: flattened assignments
    rows = []
    for emp, assigns in assign.items():
        for (d, block_idx, team_val) in assigns:
            rows.append({
                "employee": emp,
                "day": d,
                "block_idx": block_idx,
                "team_id": team_val,
                "team_code": TEAM_ID_TO_CODE.get(team_val, None)
            })

    df_debug = pd.DataFrame(rows)
    df_debug.to_csv("debug_assign.csv", index=False)
    print("DEBUG assign head:")
    print(df_debug.head(20))
    print("Counts per team_id:")
    print(df_debug['team_id'].value_counts(dropna=False))
    print("Counts per team_code:")
    print(df_debug['team_code'].value_counts(dropna=False))

    export_schedule_to_csv(v, "schedule_cpsat.csv", num_days=num_days)
    print(pd.read_csv("schedule_cpsat.csv").head(30))

    return to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        work_blocks=work_blocks
    )
