import datetime
import pandas as pd
from ortools.sat.python import cp_model
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
    return {
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
    return [
        (9, 13, 18),   (9, 14, 18),   (9, 15, 18),
        (10, 14, 19),  (10, 15, 19),  (10, 16, 19),
        (11, 15, 20),  (11, 16, 20),  (11, 17, 20),
        (12, 16, 21),  (12, 17, 21),  (12, 18, 21),
        (13, 17, 22),  (13, 18, 22),  (13, 19, 22),
    ]


def _get_working_hours(block):
    start, break_start, end = block
    return list(range(start, break_start)) + list(range(break_start + 1, end))


def solve(*, vacations, minimuns, employees, maxTime=None, year=2021, hours=13, rules=None):
    
    solver = cp_model.CpSolver()
    num_days = 365
    n_employees = len(employees)

    if n_employees == 21:
        print ("✅ [CSP] Detected 21 employees")

    print(f"\n{'='*80}")
    print(f"[CSP] HOURLY SCHEDULER - DEBUGGING VERSION")
    print(f"{'='*80}")

    dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
    work_blocks = _generate_work_blocks()
    
    H = set()
    for block in work_blocks:
        H.update(_get_working_hours(block))
    H = sorted(H)

    print(f"[CSP] Hours considered: {H}")

    Employees = range(n_employees)
    D = range(1, num_days + 1)

    print(f"[CSP] Days: 1 to {num_days}")

    allowed_teams_per_emp = _build_allowed_teams(employees)

    print("[CSP] Allowed teams per employee:")
    for i, teams in enumerate(allowed_teams_per_emp):
        print(f"  Employee {i}: {teams}")

    # Férias
    vacs_dict = rows_to_vac_dict(vacations)
    vac_mask = {(i, d): False for i in Employees for d in D}
    
    for emp_id, days in vacs_dict.items():
        i = emp_id - 1
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True

    print(f"[CSP] Vacation days processed.")
    print(f"   Total vacation entries: {sum(1 for v in vac_mask.values() if v)}")

    # Requisitos
    mins_raw, _ = rows_to_req_dicts(minimuns)
    min_required = {}
    for (day, hour_str, team_id), val in mins_raw.items():
        if 1 <= day <= num_days:
            team_code = TEAM_ID_TO_CODE.get(team_id)
            if team_code:
                try:
                    min_required[(day, hour_str, team_code)] = max(0, int(val))
                except (ValueError, TypeError):
                    pass

    # Holidays
    pt_holidays = Holidays_in_year()
    start_date = dates[0]
    sundays_holidays = [d for d in dates if d.weekday() == 6 or d.date() in pt_holidays]
    special_days = {(d - start_date).days + 1 for d in sundays_holidays}
    special_days = {d for d in special_days if 1 <= d <= num_days}

    print(f"Special days: {len(special_days)}")
    print(f"  Dates: {[dates[d-1].date() for d in special_days]}")

    # ==================== MODELO SIMPLIFICADO ====================
    m = cp_model.CpModel()

    # VARIÁVEIS PRINCIPAIS
    y = {}          # y[e,d,h,t] = trabalha hora h em equipa t no dia d
    off = {}        # off[e,d] = está off no dia d
    block_day = {}  # block_day[e,d] = índice do bloco usado no dia d (0-14, ou 15=OFF)

    print("\n[1/7] Creating variables...")
    for e in Employees:
        for d in D:
            off[(e, d)] = m.NewBoolVar(f"off_{e}_{d}")
            
            # Criar bloco: 0-14 = blocos, 15 = OFF
            block_day[(e, d)] = m.NewIntVar(0, len(work_blocks), f"block_{e}_{d}")
            
            # Criar y apenas para dias trabalháveis
            for h in H:
                for t in allowed_teams_per_emp[e]:
                    y[(e, d, h, t)] = m.NewBoolVar(f"y_{e}_{d}_{h}_{t}")

    print(f"   Created: {len(y)} y-vars, {len(block_day)} block-vars, {len(off)} off-vars")

    # ==================== Relations between variables ====================
    print("\n[Relations] Linking variables...")
    for e in Employees:
        for d in D:
            # off=1 ↔ block=15
            m.Add(block_day[(e, d)] >= 15).OnlyEnforceIf(off[(e, d)])
            m.Add(block_day[(e, d)] < 15).OnlyEnforceIf(off[(e, d)].Not())

    for e in Employees:
        for d in D:
            for h in H:
                for t in allowed_teams_per_emp[e]:
                    # blockday == 15 → y=0
                    m.Add(y[(e, d, h, t)] == 0).OnlyEnforceIf(block_day[(e, d)] == 15)
                    # blockday < 15 → y definido por blocos
                    for b_idx, block in enumerate(work_blocks):
                        working_hours = _get_working_hours(block)
                        if h in working_hours:
                            m.Add(y[(e, d, h, t)] == 1).OnlyEnforceIf(block_day[(e, d)] == b_idx)
                        else:
                            m.Add(y[(e, d, h, t)] == 0).OnlyEnforceIf(block_day[(e, d)] == b_idx)

    # ==================== CONSTRAINTS ====================

    print("\n[2/7] Vacation and holiday constraints...")
    # Férias e holidays → OFF
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)] or d in special_days:
                m.Add(off[(e, d)] == 1)

    print("\n[3/7] Only one block can be choosen...")
    # Apenas um bloco por dia
    for e in Employees:
        for d in D:
            blocks = []
            for b_idx in range(len(work_blocks)):
                blocks.append(block_day[(e, d)] == b_idx)
            m.Add(sum(blocks) == 1)



    print("\n[4/7] Team selection (one team per day)...")
    # Uma equipa por dia
    for e in Employees:
        for d in D:
            for h in H:
                team_vars = [y[(e, d, h, t)] for t in allowed_teams_per_emp[e] if (e, d, h, t) in y]
                if team_vars:
                    m.Add(sum(team_vars) <= 1)


    print("\n[5/7] Exactly work days ...")
    # Trabalho máximo: 223 dias
    MAX_WORK_DAYS = 223
    for e in Employees:
        worked = sum(1 - off[(e, d)] for d in D)
        m.Add(worked == MAX_WORK_DAYS)


    print("\n[6/7] Rest time (11h)...")
    # Transições 11h
    for e in Employees:
        for d in range(1, num_days):
            for b_idx, block in enumerate(work_blocks):
                end_hour = block[2]
                for next_b_idx, next_block in enumerate(work_blocks):
                    start_hour = next_block[0]
                    if (24 - end_hour + start_hour) < 11:
                        m.Add(block_day[(e, d+1)] != next_b_idx).OnlyEnforceIf(block_day[(e, d)] == b_idx)


    # ==================== OBJETIVO ====================
    
    print("\n[OBJECTIVE] Minimizing coverage gaps...")
    unmet = []
    
    for (day, hour_str, team), req in min_required.items():
        if req <= 0 or day in special_days:
            continue
        
        hour_num = int(hour_str.split('-')[0])
        team_id = get_team_id(team)
        
        covers = []
        for e in Employees:
            if (e, day, hour_num, team_id) in y and not vac_mask[(e, day)]:
                covers.append(y[(e, day, hour_num, team_id)])
        
        if covers:
            covered = m.NewIntVar(0, n_employees, f"cov_{day}_{hour_num}_{team_id}")
            m.Add(covered == sum(covers))
            
            miss = m.NewIntVar(0, req, f"miss_{day}_{hour_num}_{team_id}")
            m.Add(miss >= req - covered)
            unmet.append(miss)

    if unmet:
        m.Minimize(sum(unmet))
        print(f"   Tracking {len(unmet)} coverage requirements")

    # ==================== SOLVER ====================
    
    if maxTime:
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8
    solver.parameters.log_search_progress = False

    print(f"\n{'='*80}")
    print("[SOLVING...]")
    print(f"{'='*80}\n")
    
    status = solver.Solve(m)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"✓ Solution found: {['OPTIMAL', 'FEASIBLE'][status-4]}\n")
    else:
        print(f"✗ No solution: {['UNKNOWN', 'INFEASIBLE', 'MODEL_INVALID'][status]}\n")
        return [["Employee"] + [f"Day{i}" for i in range(1, num_days + 1)]]

    # ==================== EXTRACT ====================
    
    assign = defaultdict(list)
    
    print("Extracting schedule:\n")
    for e in Employees:
        emp_id = e + 1
        worked = 0
        blocks_used = set()
        
        for d in D:
            if solver.Value(off[(e, d)]) == 1:
                continue
            
            worked += 1
            
            if (e, d) in block_day:
                b_idx = solver.Value(block_day[(e, d)])
                if b_idx < len(work_blocks):
                    blocks_used.add(b_idx)
                    
                    # Encontrar equipa
                    team_val = None
                    for t in allowed_teams_per_emp[e]:
                        if any(solver.Value(y[(e, d, h, t)]) == 1 
                              for h in H if (e, d, h, t) in y):
                            team_val = t
                            break
                    
                    if team_val:
                        assign[emp_id].append((d, b_idx, team_val))
        
        print(f"Emp {emp_id:2d}: {worked:3d} days, {len(blocks_used):2d} different blocks")

    # ==================== EXPORT ====================
    
    class View: pass
    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign

    export_schedule_to_csv_hours(v, "schedule_cpsat_debug.csv", num_days=num_days)
    
    print(f"\n{'='*80}")
    print("✓ Schedule exported!")
    print(f"{'='*80}\n")
    
    return to_table_hours(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        work_blocks=work_blocks
    )
