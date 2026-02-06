# HourlyILP_strict_FIXED.py - FLOAT PRECISION ISSUES RESOLVED

import csv
from collections import defaultdict
import pandas as pd
import pulp

from algorithms.utils import (
    rows_to_vac_dict,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
)

def rows_to_req_dicts_FIXED(req_rows):
    """
    FIXED: Store minimums with FLOAT keys (not strings)
    Key format: (pd.Timestamp, float, int)
    Example: (Timestamp('2021-11-02'), 9.0, 1)
    """
    mins = {}
    dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()

    print(f"[DEBUG] Created {len(dates)} dates for conversion")

    for row in req_rows:
        if not row or len(row) < 3:
            continue
        
        team_label = row[0].strip()
        if not team_label.upper().startswith('EQUIPA'):
            continue
        
        second_col = row[1].strip()
        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)

        if '-' not in second_col:
            continue
            
        hour_label = second_col
        counts = row[2:]

        # Parse hour to FLOAT
        if ':' in hour_label:
            try:
                start_str, _ = hour_label.split('-')
                start_hour, start_min = map(int, start_str.split(':'))
                start_float = round(float(start_hour) + (0.5 if start_min == 30 else 0.0), 1)
            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        else:
            try:
                parts = hour_label.split('-')
                start_float = round(float(parts[0]), 1)
            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        
        # Store with (Timestamp, FLOAT, team_id) format
        for day_num, val in enumerate(counts, start=1):
            v = str(val).strip()
            if not v:
                continue
            
            try:
                val_int = int(v)
            except ValueError:
                continue
            
            if 1 <= day_num <= len(dates):
                date_key = dates[day_num - 1]
                # KEY FIX: Store as (date, FLOAT, team_id)
                mins[(date_key, start_float, team_id)] = val_int
                
    print(f"[DEBUG] Processed {len(mins)} minimum entries")
    print(f"[DEBUG] Sample keys (first 10):")
    for i, (key, val) in enumerate(list(mins.items())[:10]):
        print(f"  {key} → {val}")

    return mins, {}


class HourlyILPStrictScheduler:
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2021,
                 store_hours=13, work_blocks=None):
        self.year = year
        
        if maxTime is not None:
            try:
                maxTime_num = float(maxTime)
                self.maxTime_sec = int(maxTime_num * 60)
            except (ValueError, TypeError):
                print(f"[ILP] Warning: Invalid maxTime '{maxTime}', using 8 hours")
                self.maxTime_sec = 8 * 3600
        else:
            self.maxTime_sec = None

        self.dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
        self.num_days = len(self.dates)
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)
        self.store_hours = int(store_hours)

        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks

        self.num_blocks = len(self.work_blocks)
        self.block_hours = [self._get_working_hours(b) for b in self.work_blocks]

        # FIX: Use rounded floats consistently
        self.slot_hours = [round(h, 1) for h in [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 
                          12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 
                          17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5]]

        # Employee teams
        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            codes = tuple(get_team_code(team) for team in teams) if teams else ("A",)
            self.emp_team_code[idx] = codes
            for c in codes:
                get_team_id(c)

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

        # Minimums - now stored as (date, float, team_id)
        mins, _ = rows_to_req_dicts_FIXED(minimums_rows)
        self.minimos = mins

        # Closed days
        self.closed_days = {d for (d, h, t), v in self.minimos.items() if v == -1}

        # Model variables
        self.model = None
        self.z = {}
        self.x = {}
        self.workday = {}
        self.y = {}
        self.shortage = {}
        self.assignment = defaultdict(list)

    def _generate_work_blocks(self):
        blocks = [
            (9.0, 13.0, 18.0), (9.0, 14.0, 18.0), (9.0, 15.0, 18.0),
            (9.5, 13.5, 18.5), (9.5, 14.5, 18.5), (9.5, 15.5, 18.5),
            (10.0, 14.0, 19.0), (10.0, 15.0, 19.0), (10.0, 16.0, 19.0),
            (10.5, 14.5, 19.5), (10.5, 15.5, 19.5), (10.5, 16.5, 19.5),
            (11.0, 15.0, 20.0), (11.0, 16.0, 20.0), (11.0, 17.0, 20.0),
            (11.5, 15.5, 20.5), (11.5, 16.5, 20.5), (11.5, 17.5, 20.5),
            (12.0, 16.0, 21.0), (12.0, 17.0, 21.0), (12.0, 18.0, 21.0),
            (12.5, 16.5, 21.5), (12.5, 17.5, 21.5), (12.5, 18.5, 21.5),
            (13.0, 17.0, 22.0), (13.0, 18.0, 22.0), (13.0, 19.0, 22.0),
        ]
        return blocks
    
    def _get_working_hours(self, block):
        # 1
        start, break_start, end = block
        hours = []

        h = start
        while h < break_start:
            hours.append(round(h, 1))
            h += 0.5

        h = break_start + 1
        while h < end:
            hours.append(round(h, 1))
            h += 0.5

        return hours

    def _validate_block_transition(self, block_today, block_tomorrow):
        end_today = block_today[2]
        start_tomorrow = block_tomorrow[0]
        rest_hours = round((24 - end_today) + start_tomorrow, 8)
        return rest_hours >= 11.99  # Tolerance for float precision

    def build_model(self):
        model = pulp.LpProblem("Hourly_Strict_ILP")

        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(self.num_blocks))
        horas = self.slot_hours
        teams = list(self.teams.keys())

        # 1) Variables z, x, workday, y, shortage
        for f in funcionarios:
            self.z[f] = {}
            for d in dias:
                self.z[f][d] = {}
                for b in blocos:
                    name = f"z_f{f}_d{d.strftime('%Y%m%d')}_b{b}"
                    self.z[f][d][b] = pulp.LpVariable(name, cat="Binary")

        for f in funcionarios:
            self.x[f] = {}
            for d in dias:
                self.x[f][d] = {}
                for b in blocos:
                    self.x[f][d][b] = {}
                    for tc in self.emp_team_code[f]:
                        name = f"x_f{f}_d{d.strftime('%Y%m%d')}_b{b}_t{tc}"
                        self.x[f][d][b][tc] = pulp.LpVariable(name, cat="Binary")

        for f in funcionarios:
            self.workday[f] = {}
            for d in dias:
                name = f"w_f{f}_d{d.strftime('%Y%m%d')}"
                self.workday[f][d] = pulp.LpVariable(name, cat="Binary")

        for d in dias:
            self.y[d] = {}
            for h in horas:
                self.y[d][h] = {}
                for tc in teams:
                    name = f"y_d{d.strftime('%Y%m%d')}_h{h}_{tc}"
                    ub = max(1, len(self.teams.get(tc, [])))
                    self.y[d][h][tc] = pulp.LpVariable(name, lowBound=0, upBound=ub, cat="Integer")

        for d in dias:
            for h in horas:
                for tc in teams:
                    # FIX: Look up with FLOAT key
                    team_id = get_team_id(tc)
                    if self.minimos.get((d, h, team_id), 0) == -1:
                        continue
                    name = f"short_d{d.strftime('%Y%m%d')}_h{h}_{tc}"
                    ub = len(self.employees) * 2
                    self.shortage[(d, h, tc)] = pulp.LpVariable(name, lowBound=0, upBound=ub, cat="Continuous")

        # 2) Constraints
        for f in funcionarios:
            for d in dias:
                for b in blocos:
                    if d in self.vacations_dates.get(f, set()) or d in self.closed_days:
                        model += (self.z[f][d][b] == 0, f"no_work_f{f}_{d.strftime('%Y%m%d')}_b{b}")
                        for tc in self.emp_team_code[f]:
                            model += (self.x[f][d][b][tc] == 0)
                        continue

                    for tc in self.emp_team_code[f]:
                        model += (self.x[f][d][b][tc] <= self.z[f][d][b])

                    model += (
                        pulp.lpSum(self.x[f][d][b][tc] for tc in self.emp_team_code[f]) == self.z[f][d][b],
                        f"one_team_f{f}_{d.strftime('%Y%m%d')}_b{b}"
                    )

        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(self.z[f][d][b] for b in blocos) <= 1,
                    f"at_most_one_f{f}_{d.strftime('%Y%m%d')}"
                )
                model += (
                    self.workday[f][d] == pulp.lpSum(self.z[f][d][b] for b in blocos),
                    f"workday_f{f}_{d.strftime('%Y%m%d')}"
                )

        # 223 days
        for f in funcionarios:
            model += (
                pulp.lpSum(self.workday[f][d] for d in dias) == 223,
                f"total_223_f{f}"
            )

        # Link y with x
        for d in dias:
            for h in horas:
                for tc in teams:
                    team_id = get_team_id(tc)
                    # FIX: Look up with FLOAT h
                    if self.minimos.get((d, h, team_id), 0) == -1:
                        model += (self.y[d][h][tc] == 0, f"y_closed_{d.strftime('%Y%m%d')}_h{h}_{tc}")
                        continue
                    
                    terms = []
                    for f in self.teams.get(tc, set()):
                        for b in blocos:
                            # FIX: Compare rounded floats
                            if round(h, 1) in [round(bh, 1) for bh in self.block_hours[b]]:
                                if tc in self.emp_team_code[f]:
                                    terms.append(self.x[f][d][b][tc])
                    
                    # if terms:
                    model += (self.y[d][h][tc] == pulp.lpSum(terms))
                    # else:
                    #     model += (self.y[d][h][tc] == 0)

        # Shortage constraints
        for d in dias:
            for h in horas:
                for tc in teams:
                    team_id = get_team_id(tc)
                    # FIX: Look up with FLOAT h
                    minimo = self.minimos.get((d, h, team_id), 0)
                    if minimo == -1:
                        continue
                    
                    s_var = self.shortage.get((d, h, tc))
                    if s_var is None:
                        continue
                    
                    model += (s_var + self.y[d][h][tc] >= minimo)

        # Max 5 consecutive
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.workday[f][d] for d in window) <= 5,
                    f"max5_f{f}_{i}"
                )

        # 12h rest
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                for b in blocos:
                    for a in blocos:
                        if not self._validate_block_transition(self.work_blocks[b], self.work_blocks[a]):
                            model += (
                                self.z[f][d_today][b] + self.z[f][d_next][a] <= 1,
                                f"rest_f{f}_{i}_b{b}_a{a}"
                            )

        # Objective
        # obj_terms = [s for s in self.shortage.values()]
        # model += pulp.lpSum(obj_terms), "Minimize_shortage"

        self.model = model
        print("[HourlyILP] Model built successfully")

    def solve(self, gap_rel=0.005):
        if self.model is None:
            self.build_model()
        
        print(f"\n{'='*80}")
        print(f"[HourlyILP] SOLVING ILP MODEL")
        print(f"  Variables: {self.model.numVariables()}")
        print(f"  Constraints: {self.model.numConstraints()}")
        
        try:
            import gurobipy
            solver = pulp.GUROBI(
                msg=True,
                timeLimit=self.maxTime_sec,
                gapRel=gap_rel,
                Threads=8,
                Method=2,
                Presolve=2
            )
            print(f"  Using Gurobi solver")
        except:
            solver = pulp.PULP_CBC_CMD(
                msg=True,
                timeLimit=self.maxTime_sec,
                gapRel=gap_rel,
                threads=4
            )
            print(f"  Using CBC solver")
        
        self.status = self.model.solve(solver)
        
        status_map = {
            pulp.LpStatusOptimal: "Optimal",
            pulp.LpStatusNotSolved: "Not Solved",
            pulp.LpStatusInfeasible: "Infeasible",
            pulp.LpStatusUnbounded: "Unbounded"
        }
        
        print(f"[HourlyILP] Status: {status_map.get(self.status, 'Unknown')}")
        
        if self.status == pulp.LpStatusOptimal or self.status == pulp.LpStatusNotSolved:
            self._extract_assignments()
            
            total_shortage = sum(
                int(pulp.value(s)) if pulp.value(s) else 0
                for s in self.shortage.values()
            )
            print(f"[HourlyILP] Total shortage: {total_shortage}")
        
        return self.status

    def _extract_assignments(self):
        self.assignment = defaultdict(list)
        for f in self.employees:
            emp_id = f + 1
            for d_idx, d in enumerate(self.dates, start=1):
                for b in range(self.num_blocks):
                    val_z = pulp.value(self.z[f][d][b])
                    if val_z and val_z > 0.5:
                        chosen_team = None
                        for tc in self.emp_team_code[f]:
                            val_x = pulp.value(self.x[f][d][b].get(tc, 0))
                            if val_x and val_x > 0.5:
                                chosen_team = tc
                                break
                        team_id = get_team_id(chosen_team or self.emp_team_code[f][0])
                        self.assignment[emp_id].append((d_idx, b, team_id))
                        break

    def export_csv(self, filename="hourly_schedule.csv"):
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            
            vacs_1b = {
                i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
                for i in self.employees
            }
            
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(vacs_1b.get(emp_id, []))
                day_to_block = {d: (b, t) for (d, b, t) in self.assignment.get(emp_id, [])}
                
                row = [f'Emp{emp_id}']
                for d in range(1, self.num_days + 1):
                    if d in vac_days:
                        row.append('F')
                    elif d in day_to_block:
                        b, team_id = day_to_block[d]
                        block = self.work_blocks[b]
                        team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                        row.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
                    else:
                        row.append('OFF')
                writer.writerow(row)
        
        print(f"[HourlyILP] Exported to {filename}")

    def to_table(self):
        rows = [["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]]
        
        vacs_1b = {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }
        
        for emp_id in sorted([i + 1 for i in self.employees]):
            vac_days = set(vacs_1b.get(emp_id, []))
            day_to_block = {d: (b, t) for (d, b, t) in self.assignment.get(emp_id, [])}
            
            line = [f"Emp{emp_id}"]
            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_block:
                    b, team_id = day_to_block[d]
                    block = self.work_blocks[b]
                    team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                    line.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
                else:
                    line.append("OFF")
            rows.append(line)
        
        return rows


def solve(vacations=None, minimuns=None, employees=None, maxTime=None, 
          year=2021, hours=13, work_blocks=None, rules=None, **kwargs):
    print(f"\n{'='*80}")
    print(f"[HourlyILP] SCHEDULER - ILP with Float Precision Fixes")
    print(f"{'='*80}")
    
    sched = HourlyILPStrictScheduler(
        vacations, minimuns, employees, maxTime, 
        year=year, store_hours=hours, work_blocks=work_blocks
    )
    sched.build_model()
    sched.solve(gap_rel=0.005)
    sched.export_csv("hourly_schedule.csv")
    
    return sched.to_table()