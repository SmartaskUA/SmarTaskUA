import datetime
import time
import pandas as pd
from ortools.sat.python import cp_model
import numpy as np
from collections import defaultdict

from algorithms.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    export_schedule_to_csv_hours,
    to_table_hours
)


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


def _build_allowed_teams(employees):
    allowed = []
    for emp in employees:
        codes = [get_team_code(t) for t in emp.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed


def _generate_work_blocks():
    blocks = [
        (9, 13, 18),   (9, 14, 18),   (9, 15, 18),
        (10, 14, 19),  (10, 15, 19),  (10, 16, 19),
        (11, 15, 20),  (11, 16, 20),  (11, 17, 20),
        (12, 16, 21),  (12, 17, 21),  (12, 18, 21),
        (13, 17, 22),  (13, 18, 22),  (13, 19, 22),
    ]
    return blocks


def _get_working_hours(block):
    start, break_start, end = block
    hours = list(range(start, break_start)) + list(range(break_start + 1, end))
    return hours


def solve(*, vacations, minimuns, employees, maxTime=None, year=2021, hours=13, rules=None):
    
    solver = cp_model.CpSolver()
    num_days = 365
    n_employees = len(employees)

    print(f"[CSP] Solving for {n_employees} employees over {num_days} days with {hours} working hours.")

    dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
    work_blocks = _generate_work_blocks()
    
    # Horas reais (9-22)
    H = set()
    for block in work_blocks:
        H.update(_get_working_hours(block))
    H = sorted(H)

    Employees = range(n_employees)
    D = range(1, num_days + 1)

    # Teams permitidas por empregado
    allowed_teams_per_emp = _build_allowed_teams(employees)
    print(f"[CSP] Allowed teams: {allowed_teams_per_emp[:3]}...")

    # Férias
    vacs_dict = rows_to_vac_dict(vacations)
    vac_mask = {(i, d): False for i in Employees for d in D}
    total_vacation_days = 0
    for emp_id, days in vacs_dict.items():
        i = emp_id - 1
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True
                total_vacation_days += 1
    
    print(f"[CSP] Total vacation days across all employees: {total_vacation_days}")
    print(f"[CSP] Average vacation per employee: {total_vacation_days / n_employees:.1f} days")

    # Requisitos mínimos
    mins_raw, ideals = rows_to_req_dicts(minimuns)
    min_required = {}
    for (day, hour, team_id), val in mins_raw.items():
        if 1 <= day <= num_days:
            team_code = TEAM_ID_TO_CODE.get(team_id)
            if team_code:
                try:
                    min_required[(day, hour, team_code)] = int(val)
                except (ValueError, TypeError):
                    pass

    # Holidays e domingos
    pt_holidays = Holidays_in_year()
    start_date = dates[0]
    sundays_holidays = [d for d in dates if d.weekday() == 6 or d.date() in pt_holidays]
    special_days = {(d - start_date).days + 1 for d in sundays_holidays}
    special_days = {d for d in special_days if 1 <= d <= num_days}

    print(f"[CSP] Special days (holidays+sundays): {len(special_days)}")

    # ======================== MODELO ========================
    m = cp_model.CpModel()

    # Variáveis
    y = {}  
    block_assigned = {}  
    off = {}  

    for e in Employees:
        for d in D:
            off[(e, d)] = m.NewBoolVar(f"off_{e}_{d}")
            if not vac_mask[(e, d)]:
                for h in H:
                    for t in allowed_teams_per_emp[e]:
                        y[(e, d, h, t)] = m.NewBoolVar(f"y_{e}_{d}_{h}_{t}") 
            
            for b_idx in range(len(work_blocks)):
                block_assigned[(e, d, b_idx)] = m.NewBoolVar(f"block_{e}_{d}_{b_idx}")

    print(f"[CSP] Variables created: {len(y)} y-vars, {len(block_assigned)} block-vars, {len(off)} off-vars")

    # ======================== CONSTRAINTS ========================

    # --------------------- Hard Constraints ---------------------


    for e in Employees:
        for d in D:

    # Ligacao OFF -> y
            for h in H:
                hour_vars = []
                for t in allowed_teams_per_emp[e]:
                    if (e, d, h, t) in y:
                        hour_vars.append(y[(e, d, h, t)])
                if hour_vars:
                    total_hours = sum(hour_vars)
                    m.Add(total_hours == 0).OnlyEnforceIf(off[(e, d)])
                    m.Add(total_hours >= 1).OnlyEnforceIf(off[(e, d)].Not())

    # Ligacao y -> Blocks

            for b_idx, block in enumerate(work_blocks):
                working_hours = _get_working_hours(block)
                for h in working_hours:
                    hour_vars = []
                    for t in allowed_teams_per_emp[e]:
                        if (e, d, h, t) in y:
                            hour_vars.append(y[(e, d, h, t)])
                    if hour_vars:
                        total_hours = sum(hour_vars)
                        # If block is assigned, all its hours must be worked
                        m.Add(total_hours >= 1).OnlyEnforceIf(block_assigned[(e, d, b_idx)])
                    else :
                        # If no hours can be worked in this block, it cannot be assigned
                        m.Add(block_assigned[(e, d, b_idx)] == 0)

            for b_idx, block in enumerate(work_blocks):
                working_hours = _get_working_hours(block)
                blocks = []
                if (e,d,b_idx) in block_assigned:
                    # If block is not assigned, none of its hours can be worked
                    blocks.append(block_assigned[(e, d, b_idx)])
                if blocks:
                    m.Add(sum(blocks) == 0).OnlyEnforceIf(off[(e, d)])
                        
                

# ----------------------------- Hard Constraints -------------------------------
 
    # 0. No work on vacation days
    print("\n[CSP] Applying vacation constraints:")

    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                m.Add(off[(e, d)] == 1)
                for b_idx in range(len(work_blocks)):
                    m.Add(block_assigned[(e, d, b_idx)] == 0)
                for h in H:
                    for t in allowed_teams_per_emp[e]:
                        if (e, d, h, t) in y:
                            m.Add(y[(e, d, h, t)] == 0)
    
    print("[CSP] ✅ Constraint 0: No work on vacation days applied.")


    # 1. One block per day - exactly one block must be selected

    print("\n[CSP] Applying one block per day constraint:")
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            total_blocks = sum(block_assigned[(e, d, b)] for b in range(len(work_blocks)))
            m.Add(total_blocks == 1).OnlyEnforceIf(off[(e, d)].Not())

    print("[CSP] ✅ Constraint 1: One block per working day applied.")


    # 2. Employee can only work in allowed teams and only one team per day -> Rever

    print("\n[CSP] Applying allowed teams constraints:")


    team_active = {}  # Variável que indica qual equipa está ativa no dia

    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            
            # Criar variáveis binárias para cada equipa permitida
            for t in allowed_teams_per_emp[e]:
                team_active[(e, d, t)] = m.NewBoolVar(f"team_active_{e}_{d}_{t}")

            # CONSTRAINT: No máximo 1 equipa ativa por dia
            m.Add(sum(team_active[(e, d, t)] for t in allowed_teams_per_emp[e]) == 0).OnlyEnforceIf(off[(e, d)])
            # CONSTRAINT: Se trabalha (off=0), exatamente 1 equipa deve estar ativa
            m.Add(sum(team_active[(e, d, t)] for t in allowed_teams_per_emp[e]) == 1).OnlyEnforceIf(off[(e, d)].Not())

            # CONSTRAINT: Cada hora só pode estar ativa na equipa selecionada
            for h in H:
                for t in allowed_teams_per_emp[e]:
                    if (e, d, h, t) in y:
                        # Hora só pode estar ativa se a equipa estiver ativa
                        m.Add(y[(e, d, h, t)] <= team_active[(e, d, t)])

    print("[CSP] ✅ Constraint 2: Allowed teams and one team per day applied.")


    # 3. Total working days = 223 in the year

    print("\n[CSP] Calculating work requirements per employee:")

    target_workdays = 223
    # workdays = {employee: m.NewIntVar(0, target_workdays, f"work_{employee}") for employee in Employees}
    # dev_under = {employee: m.NewIntVar(0, target_workdays, f"dev_under_{employee}") for employee in Employees}
    # dev_over  = {employee: m.NewIntVar(0, target_workdays, f"dev_over_{employee}") for employee in Employees}
    # for employee in Employees:
    #     m.Add(workdays[employee] == sum(1 - off[(employee, d)] for d in D))
    #     m.Add(workdays[employee] + dev_under[employee] - dev_over[employee] == target_workdays)

    for e in Employees:
        vacation_count = sum(1 for d in D if vac_mask[(e, d)])
        available = []
        worked = sum(1 - off[(e, d)] for d in D)
        m.Add(worked == target_workdays)
        print(f"  Employee {e+1}: {vacation_count} vacation days, {available} available → require {worked} work days")

    print("\n[CSP] ✅ Constraint 3: Minimum work days (relaxed) : 150 - 250 days per employee")


    # 3.1. No work on days marked with -1 (closed days/holidays)
    # 4. Max 5 consecutive working days (sliding window of 6 days)

    # 5. Valid transitions between consecutive days (12h rest minimum)

    rest_violations = 0
    for e in Employees:
        for d in range(1, num_days):
            d_next = d + 1
            if d_next > num_days:
                continue
            
            for b1_idx, block1 in enumerate(work_blocks):
                end_today = block1[2]
                for b2_idx, block2 in enumerate(work_blocks):
                    start_tomorrow = block2[0]
                    rest_hours = (24 - end_today) + start_tomorrow
                    
                    if rest_hours < 11:
                        m.Add(block_assigned[(e, d, b1_idx)] + 
                              block_assigned[(e, d_next, b2_idx)] <= 1)
                        rest_violations += 1

    print(f"[CSP] ✅ Constraint 5: Rest time (11h) - {rest_violations} potential violations blocked")



    # ======================== OBJETIVO ========================
    # Objective: Minimize deviations from minimums and ideals

    print("\n[CSP] Building objective: Minimize coverage gaps")

    # Variáveis para mínimos não cumpridos (slack variables)
    unmet = {}
    total_unmet_constraints = 0
    
    for (day, h, t), req in min_required.items():
        print(f"[CSP] Minimum requirement on day {day}, hour {h}, team {t}: {req}")
        
        # Lista de funcionários disponíveis para esta hora/equipa
        available_employees = []
        for employee in Employees:
            if not vac_mask[(employee, day)] and t in allowed_teams_per_emp[employee]:
                available_employees.append(y[(employee, day, h, t)])
        
        if available_employees:
            # Variável slack para requisitos não cumpridos
            u = m.NewIntVar(0, req, f"unmet_{day}_{h}_{t}")
            unmet[(day, h, t)] = u
            
            # Constraint: funcionários atribuídos + não cumpridos >= mínimo requerido
            # sum(y[(e,d,h,t)]) + unmet >= req
            # Ou seja: unmet = max(0, req - sum(y[(e,d,h,t)]))
            m.Add(sum(available_employees) + u >= req)
            total_unmet_constraints += 1
    
    print(f"[CSP] Created {len(unmet)} unmet variables for {total_unmet_constraints} minimum requirements")

    # Função Objetivo: Minimizar número total de mínimos falhados
    if unmet:
        objective_terms = [unmet[k] for k in unmet]
        m.Minimize(sum(objective_terms))
        print(f"[CSP] Objective: Minimize sum of {len(objective_terms)} unmet requirements")
    else:
        print("[CSP] Warning: No minimum requirements found - no objective set")


    # ======================== RESOLVER ========================
    
    if maxTime is not None:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = True

    print("\n" + "="*60)
    print("[CSP] Starting solver...")
    print("="*60 + "\n")
    
    status = solver.Solve(m)

    status_map = {
        cp_model.OPTIMAL: "OPTIMAL",
        cp_model.FEASIBLE: "FEASIBLE",
        cp_model.INFEASIBLE: "INFEASIBLE",
        cp_model.MODEL_INVALID: "MODEL_INVALID",
        cp_model.UNKNOWN: "UNKNOWN"
    }
    print(f"\n[CSP] Status: {status_map.get(status, 'UNKNOWN')}")

    if status not in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print("\n" + "="*60)
        print("[ERROR] No solution found!")
        print("="*60)
        print("\nDEBUG INFO:")
        print(f"  - Employees: {n_employees}")
        print(f"  - Total days: {num_days}")
        print(f"  - Special days: {len(special_days)}")
        print(f"  - Total vacation days: {total_vacation_days}")
        # print(f"  - Coverage requirements: {len(missed)}")
        print(f"  - Work blocks: {len(work_blocks)}")
        print("="*60)
        return [["Employee"] + [f"Day{i}" for i in range(1, num_days + 1)]]

    # ======================== EXTRAIR SOLUÇÃO ========================
    
    assign = defaultdict(list)
    
    print("\n[CSP] Solution found! Extracting schedule...")
    for e in Employees:
        emp_id = e + 1
        days_worked = 0
        
        for d in D:
            if solver.Value(off[(e, d)]) == 1:
                continue
            
            days_worked += 1
            
            for b_idx in range(len(work_blocks)):
                if solver.Value(block_assigned[(e, d, b_idx)]) == 1:
                    block = work_blocks[b_idx]
                    working_hours = _get_working_hours(block)
                    
                    team_val = None
                    for h in working_hours:
                        for t in allowed_teams_per_emp[e]:
                            if (e, d, h, t) in y and solver.Value(y[(e, d, h, t)]) == 1:
                                team_val = t
                                break
                        if team_val:
                            break
                    
                    if team_val:
                        assign[emp_id].append((d, b_idx, team_val))
                    break
        
        print(f"[CSP] Employee {emp_id}: {days_worked} days worked")

    # ======================== EXPORTAR ========================
    
    class View: pass
    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign

    export_schedule_to_csv_hours(v, "schedule_cpsat_fixed.csv", num_days=num_days)
    
    return to_table_hours(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        work_blocks=work_blocks
    )