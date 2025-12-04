import datetime
import time
import pandas as pd
from ortools.sat.python import cp_model
import numpy as np
from collections import defaultdict

from algorithm.utils import (
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

    # Horas reais (9-22) derivadas dos blocos
    H = set()
    for block in work_blocks:
        H.update(_get_working_hours(block))
    H = sorted(H)

    Employees = range(n_employees)
    D = range(1, num_days + 1)

    allowed_teams_per_emp = _build_allowed_teams(employees)
    print(f"[CSP] Allowed teams (sample): {allowed_teams_per_emp[:3]}")

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
    if n_employees:
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
    y = {}               # y[e,d,h,t] : hora h em equipa t
    block_assigned = {}  # block_assigned[e,d,b] : bloco b está atribuído no dia d
    block_team = {}      # block_team[e,d,b,t] : bloco b atribuído à equipa t (link)
    off = {}             # off[e,d] : off no dia d
    team_active = {}     # team_active[e,d,t] : equipa t é escolhida no dia d

    for e in Employees:
        for d in D:
            off[(e, d)] = m.NewBoolVar(f"off_{e}_{d}")

            if not vac_mask[(e, d)]:
                for h in H:
                    for t in allowed_teams_per_emp[e]:
                        y[(e, d, h, t)] = m.NewBoolVar(f"y_{e}_{d}_{h}_{t}")

            for b_idx in range(len(work_blocks)):
                block_assigned[(e, d, b_idx)] = m.NewBoolVar(f"block_{e}_{d}_{b_idx}")
                for t in allowed_teams_per_emp[e]:
                    block_team[(e, d, b_idx, t)] = m.NewBoolVar(f"block_team_{e}_{d}_{b_idx}_{t}")

            for t in allowed_teams_per_emp[e]:
                team_active[(e, d, t)] = m.NewBoolVar(f"team_active_{e}_{d}_{t}")

    print(f"[CSP] Variables created: {len(y)} y-vars, {len(block_assigned)} block-vars, {len(block_team)} block-team-vars")

    # ======================== CONSTRAINTS ========================

    # 1) Férias -> off, nenhum bloco, e horas zero
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                m.Add(off[(e, d)] == 1)
                for b_idx in range(len(work_blocks)):
                    m.Add(block_assigned[(e, d, b_idx)] == 0)
                    for t in allowed_teams_per_emp[e]:
                        m.Add(block_team[(e, d, b_idx, t)] == 0)
                for h in H:
                    for t in allowed_teams_per_emp[e]:
                        if (e, d, h, t) in y:
                            m.Add(y[(e, d, h, t)] == 0)
                for t in allowed_teams_per_emp[e]:
                    m.Add(team_active[(e, d, t)] == 0)

    # 2) OFF <-> EXACTLY ONE block when working
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            total_blocks = sum(block_assigned[(e, d, b)] for b in range(len(work_blocks)))
            # off → zero blocks
            m.Add(total_blocks == 0).OnlyEnforceIf(off[(e, d)])
            # working → exactly one block
            m.Add(total_blocks == 1).OnlyEnforceIf(off[(e, d)].Not())

    # 3) Block_team linking: for each (e,d,b): sum_t block_team == block_assigned
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            for b_idx in range(len(work_blocks)):
                m.Add(sum(block_team[(e, d, b_idx, t)] for t in allowed_teams_per_emp[e]) == block_assigned[(e, d, b_idx)])

    # 4) team_active consistency: team_active == sum_b block_team over blocks
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            for t in allowed_teams_per_emp[e]:
                m.Add(team_active[(e, d, t)] == sum(block_team[(e, d, b_idx, t)] for b_idx in range(len(work_blocks))))

            # Exactly one team active when working
            m.Add(sum(team_active[(e, d, t)] for t in allowed_teams_per_emp[e]) == 1 - off[(e, d)])

    # 5) HOURS y ↔ block_team (tight linking)
    # If a block b is assigned to team t, then all hours in that block for that team must be 1 (if vars exist)
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            for b_idx, block in enumerate(work_blocks):
                working_hours = _get_working_hours(block)
                for t in allowed_teams_per_emp[e]:
                    # link: block_team -> hours
                    for h in working_hours:
                        if (e, d, h, t) in y:
                            m.Add(y[(e, d, h, t)] >= block_team[(e, d, b_idx, t)])
                    # conversely, if block not assigned to t then hours for that team must be 0
                    for h in working_hours:
                        if (e, d, h, t) in y:
                            m.Add(y[(e, d, h, t)] <= sum(block_team[(e, d, b2, t)] for b2 in range(len(work_blocks)) if h in _get_working_hours(work_blocks[b2])))

    # 6) Hour active -> there exists some block_team covering that hour
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                continue
            for h in H:
                # all blocks that contain h
                blocks_with_h = [b_idx for b_idx, block in enumerate(work_blocks) if h in _get_working_hours(block)]
                if not blocks_with_h:
                    continue
                for t in allowed_teams_per_emp[e]:
                    if (e, d, h, t) in y:
                        # If y is 1, at least one block_team that contains h and t must be active
                        m.Add(sum(block_team[(e, d, b_idx, t)] for b_idx in blocks_with_h) >= y[(e, d, h, t)])

    # 7) Days worked bounds (relaxed per-employee, based on availability)
    print("\n[CSP] Calculating relaxed work-day bounds per employee:")
    for e in Employees:
        vacation_count = sum(1 for d in D if vac_mask[(e, d)])
        available = num_days - vacation_count
        # keep flexible but feasible
        min_work = max(120, int(available * 0.4))  # at least 40% of available or 120
        max_work = min(250, int(available * 0.9))  # at most 90% of available or 250
        if min_work <= max_work and available > 0:
            days_worked = sum(1 - off[(e, d)] for d in D if not vac_mask[(e, d)])
            m.Add(days_worked >= min_work)
            m.Add(days_worked <= max_work)
            print(f"  Employee {e+1}: vacation {vacation_count}, available {available}, require {min_work}-{max_work}")

    # 8) Rest transitions (11h) - keep as hard constraints between blocks
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
                        # cannot have block b1 today and block b2 tomorrow
                        m.Add(block_assigned[(e, d, b1_idx)] + block_assigned[(e, d_next, b2_idx)] <= 1)

    # 9) Minimum coverage (soft via missed vars) - only for hours that exist in H
    missed = []
    coverage_stats = {"total": 0, "with_coverage": 0, "impossible": 0}
    sample_reqs = list(min_required.items())[:5]
    print(f"\n[DEBUG] Sample requirements: {sample_reqs}")
    print(f"[DEBUG] H (working hours): {H}")

    for (day, hour_str, team), min_val in min_required.items():
        if min_val <= 0:
            continue
        coverage_stats["total"] += 1

        # keep existing parsing logic (you asked not to touch 22h handling)
        try:
            if '-' in str(hour_str):
                hour_num = int(float(hour_str.split('-')[0]))
            else:
                hour_num = int(float(hour_str))
        except:
            print(f"[WARN] Cannot parse hour: {hour_str}")
            coverage_stats["impossible"] += 1
            continue

        if hour_num not in H:
            # hour not offered by any block (this is out of scope as requested)
            coverage_stats["impossible"] += 1
            continue

        team_id = get_team_id(team)
        cover = []
        for e in Employees:
            if (e, day, hour_num, team_id) in y and not vac_mask[(e, day)]:
                cover.append(y[(e, day, hour_num, team_id)])

        if cover:
            coverage_stats["with_coverage"] += 1
            covered = m.NewIntVar(0, n_employees, f"covered_{day}_{hour_num}_{team_id}")
            m.Add(covered == sum(cover))
            miss = m.NewIntVar(0, n_employees, f"miss_{day}_{hour_num}_{team_id}")
            # miss >= min_val - covered
            m.Add(miss >= min_val - covered)
            missed.append(miss)
        else:
            coverage_stats["impossible"] += 1

    print(f"\n[CSP] Coverage requirements total={coverage_stats['total']}, with_coverage={coverage_stats['with_coverage']}, impossible={coverage_stats['impossible']}")

    # ======================== OBJETIVO ========================
    # Prioritize minimizing misses; secondarily avoid making everyone off.
    if missed:
        # weight_miss large to force coverage
        weight_miss = 2000
        weight_off = 5
        objective_terms = []
        objective_terms.append(weight_miss * sum(missed))
        objective_terms.append(weight_off * sum(off[(e,d)] for e in Employees for d in D))
        # small penalty for block assignment to avoid unnecessary over-assignments
        objective_terms.append(1 * sum(block_assigned[(e,d,b)] for e in Employees for d in D for b in range(len(work_blocks))))
        m.Minimize(sum(objective_terms))
        print(f"[CSP] Objective: minimize {len(missed)} misses (weight {weight_miss}) + offs (weight {weight_off})")
    else:
        # if no misses to track, simply minimize offs
        m.Minimize(sum(off[(e,d)] for e in Employees for d in D))
        print("[CSP] No coverage misses detected - minimizing offs")

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
        print("\n[ERROR] No solution found!")
        print("DEBUG SUMMARY:")
        print(f" - Employees: {n_employees}")
        print(f" - Days: {num_days}")
        print(f" - Work blocks: {len(work_blocks)}")
        print(f" - Total vacation days: {total_vacation_days}")
        print(f" - Min requirements count: {len(min_required)}")
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
            # find the block assigned
            for b_idx in range(len(work_blocks)):
                if solver.Value(block_assigned[(e, d, b_idx)]) == 1:
                    # determine team's value
                    team_val = None
                    for t in allowed_teams_per_emp[e]:
                        if solver.Value(block_team[(e, d, b_idx, t)]) == 1:
                            team_val = t
                            break
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
