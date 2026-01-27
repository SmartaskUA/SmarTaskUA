# HourlyILP_strict.py
import csv
from collections import defaultdict
import datetime
from time import time
import threading
import sys

import numpy as np
import pandas as pd
import pulp

from algorithms.utils import (
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv_shifts,
    TEAM_CODE_TO_ID,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code
)


class HourlyILPStrictScheduler:
    """
    ILP model that is mathematically equivalent to the CSP model.
    - Uses binary z[f,d,b] for block choice (one per employee-day).
    - Uses x[f,d,b,tc] for team assignment (x <= z and sum_tc x == z).
    - Uses workday[f,d] binary, y[d,h,tc] integer and shortage[d,h,tc] continuous >=0.
    """
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2021,
                 store_hours=13, work_blocks=None):
        self.year = year
        # Convert maxTime (minutes) to seconds, handle string input
        if maxTime is not None:
            try:
                maxTime_num = float(maxTime)
                self.maxTime_sec = int(maxTime_num * 60)
            except (ValueError, TypeError):
                print(f"[ILP_Extra] Warning: Invalid maxTime '{maxTime}', using default 8 hours")
                self.maxTime_sec = 8 * 3600
        else:
            self.maxTime_sec = None

        # Calendar - keep same range
        self.dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
        self.num_days = len(self.dates)

        # Employees
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)

        self.store_hours = int(store_hours)

        if work_blocks is None:
            self.work_blocks = [
                (9, 13, 18), (9, 14, 18), (9, 15, 18),
                (10, 14, 19), (10, 15, 19), (10, 16, 19),
                (11, 15, 20), (11, 16, 20), (11, 17, 20),
                (12, 16, 21), (12, 17, 21), (12, 18, 21),
                (13, 17, 22), (13, 18, 22), (13, 19, 22),
            ]
        else:
            self.work_blocks = work_blocks
        self.num_blocks = len(self.work_blocks)
        self.block_hours = [self._get_working_hours(b) for b in self.work_blocks]

        # Employee teams mapping
        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            if not teams:
                codes = ("A",)
            else:
                codes = tuple(get_team_code(team) for team in teams)
            self.emp_team_code[idx] = codes
            for c in codes:
                get_team_id(c)

        # teams -> members
        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        # Vacations
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, [])
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        # Minimums
        mins, ideals = rows_to_req_dicts(minimums_rows)
        self.minimos = {}
        for (day, hour, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, hour, team_code)] = int(val)

        # closed days set (if any team has -1 at some hour, we treat day as closed for all)
        self.closed_days = {d for (d, h, t), v in self.minimos.items() if v == -1}

        # Br Blocos que influenciam o dia seguinte
        self.Br = set()
        for b in self.work_blocks:
            for a in self.work_blocks:
                if not self._validate_block_transition(b, a):
                    self.Br.add(b)

        self.Ar = set()
        for b in self.work_blocks:
            for a in self.work_blocks:
                if not self._validate_block_transition(b, a):
                    self.Ar.add(a)

        # model placeholders
        self.model = None
        self.z = {}            # z[f,d,b] binary: employee f works block b on day d
        self.x = {}            # x[f,d,b,tc] binary: employee f uses block b on day d for team tc
        self.workday = {}      # workday[f,d] binary
        self.y = {}            # y[d,h,tc] integer number of workers
        self.shortage = {}     # shortage[d,h,tc] continuous >=0

        self.assignment = defaultdict(list)
        self.objective_value = None

    def _get_working_hours(self, block):
        start, break_start, end = block
        hours = set(range(start, break_start))
        hours |= set(range(break_start + 1, end))
        return hours

    def _validate_block_transition(self, block_today, block_tomorrow):
        end_today = block_today[2]
        start_tomorrow = block_tomorrow[0]
        rest_hours = (24 - end_today) + start_tomorrow
        return rest_hours >= 12

    def build_model(self):
        model = pulp.LpProblem("Hourly_Strict_ILP", pulp.LpMinimize)

        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(self.num_blocks))
        horas = list(range(9, 22))
        teams = list(self.teams.keys())

# ------------------------------------------------------------------------------

        # 1) Variables
        # z[f][d][b] binary: chosen block b for f on day d
        for f in funcionarios:
            self.z[f] = {}
            for d in dias:
                self.z[f][d] = {}
                for b in blocos:
                    name = f"z_f{f}_d{d.strftime('%Y%m%d')}_b{b}"
                    self.z[f][d][b] = pulp.LpVariable(name, cat="Binary")

        # x[f][d][b][tc] binary: assignment to a team when working that block (only for allowed teams)
        for f in funcionarios:
            self.x[f] = {}
            for d in dias:
                self.x[f][d] = {}
                for b in blocos:
                    self.x[f][d][b] = {}
                    for tc in self.emp_team_code[f]:
                        name = f"x_f{f}_d{d.strftime('%Y%m%d')}_b{b}_t{tc}"
                        self.x[f][d][b][tc] = pulp.LpVariable(name, cat="Binary")

        # workday[f][d] binary: 1 if f works some block that day
        for f in funcionarios:
            self.workday[f] = {}
            for d in dias:
                name = f"w_f{f}_d{d.strftime('%Y%m%d')}"
                self.workday[f][d] = pulp.LpVariable(name, cat="Binary")

        # y[d][h][tc] integer >=0: number of workers at d,h for team
        for d in dias:
            self.y[d] = {}
            for h in horas:
                self.y[d][h] = {}
                for tc in teams:
                    name = f"y_d{d.strftime('%Y%m%d')}_h{h}_{tc}"
                    # upper bound = number of team members (safe)
                    ub = max(1, len(self.teams.get(tc, [])))
                    self.y[d][h][tc] = pulp.LpVariable(name, lowBound=0, upBound=ub, cat="Integer")

        # shortage[d,h,tc] continuous >= 0
        for d in dias:
            for h in horas:
                hora_str = f"{h:02d}-{h+1:02d}"
                for tc in teams:
                    if self.minimos.get((d, hora_str, tc), 0) == -1:
                        # closed -> no shortage variable needed (we'll keep it 0)
                        continue
                    name = f"short_d{d.strftime('%Y%m%d')}_h{h}_{tc}"
                    # upper bound arbitrary: total employees
                    ub = max(0, len(self.employees) * 2)
                    self.shortage[(d, h, tc)] = pulp.LpVariable(name, lowBound=0, upBound=ub, cat="Continuous")

# ------------------------------------------------------------------------------


        # 2) Constraints
        # Link z and x: x[f,d,b,tc] <= z[f,d,b] and sum_tc x == z (if z==1 one tc must be 1)
        for f in funcionarios:
            for d in dias:
                for b in blocos:
                    # if day is a vacation for f -> z==0, x==0
                    if d in self.vacations_dates.get(f, set()):
                        model += (self.z[f][d][b] == 0, f"vac_z_f{f}_{d.strftime('%Y%m%d')}_b{b}")
                        for tc in self.emp_team_code[f]:
                            model += (self.x[f][d][b][tc] == 0, f"vac_x_f{f}_{d.strftime('%Y%m%d')}_b{b}_{tc}")
                        continue

                    # if day is closed -> no work
                    if d in self.closed_days:
                        model += (self.z[f][d][b] == 0, f"closed_z_f{f}_{d.strftime('%Y%m%d')}_b{b}")
                        for tc in self.emp_team_code[f]:
                            model += (self.x[f][d][b][tc] == 0, f"closed_x_f{f}_{d.strftime('%Y%m%d')}_b{b}_{tc}")
                        continue

                    # x <= z for each team, garante que todos os z == 0, os x == 0
                    for tc in self.emp_team_code[f]:
                        model += (self.x[f][d][b][tc] <= self.z[f][d][b], # Significa que se z==0 então x==0, se nao esta no bloco, x nao pode estar 
                                  f"x_le_z_f{f}_{d.strftime('%Y%m%d')}_b{b}_{tc}")

                    # agora se z == 1, exatamente uma equipa deve ser escolhido
                    # sum_tc x == z  (if z==1 then exactly one team must be selected)
                    # but if employee has only 1 allowed team this forces that x==z
                    model += (
                        pulp.lpSum(self.x[f][d][b][tc] for tc in self.emp_team_code[f]) == self.z[f][d][b],
                        f"one_team_if_work_f{f}_{d.strftime('%Y%m%d')}_b{b}"
                    )



        # Workday linking: workday[f,d] >= z[f,d,b] for all b, and workday <= sum z (so equals OR)
        # One Block per day
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(self.z[f][d][b] for b in blocos) <= 1,
                    f"at_most_one_block_f{f}_{d.strftime('%Y%m%d')}"
                )
                # workday equals sum z (since sum z ∈ {0,1})
                model += (
                    self.workday[f][d] == pulp.lpSum(self.z[f][d][b] for b in blocos),
                    f"workday_def_f{f}_{d.strftime('%Y%m%d')}"
                )




        # Total working days = 223
        for f in funcionarios:
            model += (
                pulp.lpSum(self.workday[f][d] for d in dias) == 223,
                f"total_223_f{f}"
            )



        # Link y with x: y[d,h,tc] == sum_{f,b} x[f,d,b,tc] for blocks that cover h
        for d in dias:
            for h in horas:
                hora_str = f"{h:02d}-{h+1:02d}"
                for tc in teams:
                    # if closed for this team-hour, then y forced to 0
                    if self.minimos.get((d, hora_str, tc), 0) == -1:
                        model += (self.y[d][h][tc] == 0, f"y_closed_d{d.strftime('%Y%m%d')}_h{h}_{tc}")
                        continue
                    # sum x over employees and blocks covering hour h
                    terms = []
                    for f in self.teams.get(tc, set()):
                        for b in blocos:
                            if h in self.block_hours[b]:
                                # x exist only if tc allowed for f
                                if tc in self.emp_team_code[f]:
                                    terms.append(self.x[f][d][b][tc])
                    if terms:
                        model += (self.y[d][h][tc] == pulp.lpSum(terms),
                                  f"y_def_d{d.strftime('%Y%m%d')}_h{h}_{tc}")
                    else:
                        # no possible members -> y == 0
                        model += (self.y[d][h][tc] == 0, f"y_zero_d{d.strftime('%Y%m%d')}_h{h}_{tc}")




        # Shortage linking and minimum constraints
        for d in dias:
            for h in horas:
                hora_str = f"{h:02d}-{h+1:02d}"
                for tc in teams:
                    minimo = self.minimos.get((d, hora_str, tc), 0)
                    if minimo == -1:
                        continue
                    # shortage >= minimo - y
                    s_var = self.shortage.get((d, h, tc), None)
                    if s_var is None:
                        # create if missing (unlikely)
                        name = f"short_d{d.strftime('%Y%m%d')}_h{h}_{tc}"
                        s_var = pulp.LpVariable(name, lowBound=0, cat="Continuous")
                        self.shortage[(d, h, tc)] = s_var
                    model += (s_var + self.y[d][h][tc] >= minimo, f"short_def_d{d.strftime('%Y%m%d')}_h{h}_{tc}")




        # Max 5 consecutive working days (window 6)
        for f in funcionarios:
            for i in range(0, len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.workday[f][d] for d in window) <= 5,
                    f"max5_consec_f{f}_{dias[i].strftime('%Y%m%d')}"
                )



        # Valid transitions (12h rest) using z variables (strict)
        # for f in funcionarios:
        #     for i in range(0, len(dias) - 1):
        #         d_today = dias[i]
        #         d_next = dias[i + 1]
        #         for b in blocos:
        #             for a in blocos:
        #                 # if transition invalid (end_today->start_tomorrow < 12h) then forbid z[f,d_today,b] + z[f,d_next,a] > 1
        #                 if not self._validate_block_transition(self.work_blocks[b], self.work_blocks[a]):
        #                     model += (
        #                         self.z[f][d_today][b] + self.z[f][d_next][a] <= 1,
        #                         f"invalid_trans_f{f}_{d_today.strftime('%Y%m%d')}_b{b}_a{a}"
        #                     )


        # Valid transitions (12h rest) - aggregate constraint
        # Equation: sum_{b∈B_a} z_edb + sum_{a∈A_r} z_{e,d+1,a} ≤ 1
        # If employee works late block (B_a) today, cannot work early block (A_r) tomorrow
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                
                # Construir conjuntos B_a (índices de blocos tardios) e A_r (índices de blocos cedo)
                B_a_indices = [self.work_blocks.index(b) for b in self.Br]
                A_r_indices = [self.work_blocks.index(a) for a in self.Ar]
                
                # Restrição agregada: soma de blocos tardios hoje + soma de blocos cedo amanhã ≤ 1
                # Usa z (decisão de bloco) em vez de x (decisão de equipa)
                model += (
                    pulp.lpSum(self.z[f][d_today][b_idx] for b_idx in B_a_indices) + 
                    pulp.lpSum(self.z[f][d_next][a_idx] for a_idx in A_r_indices) <= 1,
                    f"rest_12h_f{f}_{d_today.strftime('%Y%m%d')}"
                )




        # 3) Objective: minimize sum of weighted shortages
        obj_terms = []
        for (d, h, tc), s_var in self.shortage.items():
            obj_terms.append(s_var)
        model += pulp.lpSum(obj_terms), "Minimize_total_shortage" # Funcao objetivo poris nao existe qualquer comparacao


        self.model = model
        print("[HourlyILPStrict] Model built (variables: z,x,workday,y,shortage)")











# ------------------------------------------------------------------------------






    def solve(self, gap_rel=0.01):
        if self.model is None:
            self.build_model()

        time_limit = self.maxTime_sec if self.maxTime_sec is not None else 8*3600
        
        print(f"\n{'='*80}")
        print(f"[ILP_Extra] SOLVING ILP MODEL")
        print(f"{'='*80}")
        print(f"[ILP_Extra] Solver parameters:")
        print(f"  Time limit: {time_limit}s ({time_limit/60:.1f} minutes)")
        print(f"  Gap relative: {gap_rel*100:.2f}%")
        print(f"  Variables: {self.model.numVariables()}")
        print(f"  Constraints: {self.model.numConstraints()}")
        print(f"\n[ILP_Extra] Starting solver (CBC)...")
        print(f"[ILP_Extra] Real-time progress will be shown below:")
        print(f"{'-'*80}")
        
        # CBC with verbose output for real-time feedback
        solver = pulp.PULP_CBC_CMD(
            msg=1,           # Enable output messages
            timeLimit=time_limit,
            gapRel=gap_rel,
            threads=8,
            options=['logLevel=2']  # Detailed logging
        )
        
        start = time()
        status = self.model.solve(solver)
        elapsed = time() - start
        self.objective_value = pulp.value(self.model.objective)

        status_map = {
            pulp.LpStatusOptimal: "Optimal",
            pulp.LpStatusNotSolved: "Not Solved",
            pulp.LpStatusInfeasible: "Infeasible",
            pulp.LpStatusUnbounded: "Unbounded",
            pulp.LpStatusUndefined: "Undefined"
        }
        status_name = status_map.get(status, 'Unknown')
        
        print(f"\n[ILP_Extra] Solver finished!")
        print(f"  Status: {status_name}")
        print(f"  Wall time: {elapsed:.2f}s ({elapsed/60:.2f} minutes)")
        print(f"  Objective value: {self.objective_value}")
        
        if status == pulp.LpStatusOptimal:
            print(f"  ✓ OPTIMAL solution found!")
        elif status == pulp.LpStatusNotSolved:
            print(f"  ⚠ Time limit reached - solution may be suboptimal")
        elif status == pulp.LpStatusInfeasible:
            print(f"  ✗ INFEASIBLE - no solution exists with current constraints")
        
        print(f"{'='*80}\n")

        # extract assignments
        self._extract_assignments()
        return status

    def _extract_assignments(self):
        self.assignment = defaultdict(list)
        dias = self.dates
        blocos = list(range(self.num_blocks))

        for f in self.employees:
            emp_id = f + 1
            for d_idx, d in enumerate(dias, start=1):
                chosen_b = None
                chosen_team = None
                for b in blocos:
                    val_z = pulp.value(self.z[f][d][b])
                    if val_z is None:
                        continue
                    if val_z > 0.5:
                        chosen_b = b
                        # find team with x==1
                        for tc in self.emp_team_code[f]:
                            val_x = pulp.value(self.x[f][d][b].get(tc, 0))
                            if val_x is not None and val_x > 0.5:
                                chosen_team = tc
                                break
                        break
                if chosen_b is not None:
                    team_id = get_team_id(str(chosen_team)) if chosen_team is not None else get_team_id(self.emp_team_code[f][0])
                    self.assignment[emp_id].append((d_idx, chosen_b, team_id))

    def export_csv(self, filename="hourly_strict_schedule.csv"):
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(self.vacs_1based().get(emp_id, [])) if hasattr(self, "vacs_1based") else set()
                day_to_block = {d: (b, t) for (d, b, t) in self.assignment.get(emp_id, [])}
                row = [f'Emp{emp_id}']
                for d in range(1, self.num_days + 1):
                    if d in vac_days:
                        row.append('VACATION')
                    elif d in day_to_block:
                        block_idx, team_id = day_to_block[d]
                        block = self.work_blocks[block_idx]
                        team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                        row.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
                    else:
                        row.append('OFF')
                writer.writerow(row)
        print(f"[HourlyILPStrict] Schedule exported to {filename}")

    def vacs_1based(self):
        return {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }
    
    def to_table(self):
        # returns rows as list of lists (same layout as ILP to_table)
        rows = []
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows.append(header)
        vacs_1b = self.vacs_1based()
        for emp_id in sorted([i + 1 for i in self.employees]):
            vac_days = set(vacs_1b.get(emp_id, []))
            day_to_block = {d: (b, t) for (d, b, t) in self.assignment.get(emp_id, [])}
            line = [f"Emp{emp_id}"]
            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_block:
                    block_idx, team_id = day_to_block[d]
                    block = self.work_blocks[block_idx]
                    team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                    line.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
                else:
                    line.append("OFF")
            rows.append(line)
        return rows


def solve(vacations=None, minimuns=None, employees=None, maxTime=None, year=2021, hours=13, work_blocks=None, rules=None, **kwargs):
    print(f"\n{'='*80}")
    print(f"[ILP_Extra] HOURLY SCHEDULER - INTEGER LINEAR PROGRAMMING")
    print(f"{'='*80}")
    print(f"[ILP_Extra] Parameters:")
    print(f"  Employees: {len(employees) if employees else 0}")
    print(f"  Vacations: {len(vacations) if vacations else 0} rows")
    print(f"  Minimums: {len(minimuns) if minimuns else 0} rows")
    print(f"  Max time: {maxTime} minutes (type: {type(maxTime).__name__})" if maxTime else "  Max time: default (8 hours)")
    print(f"  Year: {year}")
    print(f"  Store hours: {hours}")
    
    print("\n[ILP_Extra] Building model...")
    sched = HourlyILPStrictScheduler(
        vacations, 
        minimuns, 
        employees, 
        maxTime, 
        year=year, 
        store_hours=hours, 
        work_blocks=work_blocks
    )
    sched.build_model()
    print(f"  Model built successfully!")
    
    print(f"\n[ILP_Extra] Solving...")
    status = sched.solve(gap_rel=0.01)
    
    print(f"\n[ILP_Extra] Exporting schedule...")
    sched.export_csv("hourly_strict_schedule.csv")
    
    print(f"{'='*80}")
    print(f"[ILP_Extra] COMPLETE")
    print(f"{'='*80}\n")
    
    return sched.to_table()
