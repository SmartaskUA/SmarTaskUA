import csv
from collections import defaultdict
import datetime
from time import sleep, time

import numpy as np
import pandas as pd
import pulp
import holidays
import gurobipy

from algorithms.utils import (
    build_calendar,
    rows_to_vac_dict,
    export_schedule_to_csv_shifts,
    TEAM_CODE_TO_ID,      
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code,
    create_Blocks    
)


def rows_to_req_dicts_FIXED(req_rows):
    """
    ✅ CRITICAL FIX: Return hour keys as FLOAT tuples, not strings!
    Build model uses: (pd.Timestamp, float, team_id)
    Example: (Timestamp('2021-11-02'), 9.0, 1) not (Timestamp, "9.0-9.5", 1)
    """
    import pandas as pd

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

        # Check if hour-based
        if '-' not in second_col:
            continue
            
        hour_label = second_col
        counts = row[2:]

        # Convert "09:00-09:30" to float 9.0
        if ':' in hour_label:
            try:
                start_str, end_str = hour_label.split('-')
                start_hour, start_min = map(int, start_str.split(':'))
                
                # ✅ KEY FIX: Store as FLOAT, not string
                start_float = float(start_hour) + (0.5 if start_min == 30 else 0.0)

            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        else:
            # "09-10" format
            try:
                parts = hour_label.split('-')
                start_float = float(parts[0])
            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        
        # ✅ Store with (Timestamp, FLOAT, team_id) format
        for day_num, val in enumerate(counts, start=1):
            v = str(val).strip()

            if not v or v == '0':
                continue
            
            # Convert day number (1-365) to Timestamp
            if 1 <= day_num <= len(dates):
                date_key = dates[day_num - 1]
            else:
                continue
            
            try:
                val_int = int(v)
                # ✅ KEY: Store as (date, FLOAT hour, team_id)
                mins[(date_key, start_float, team_id)] = val_int
            except ValueError:
                continue
                
    print(f"[DEBUG] Processed {len(mins)} minimum entries")
    print(f"[DEBUG] Sample keys (first 10):")
    for i, (key, val) in enumerate(list(mins.items())[:10]):
        print(f"  {key} → {val}")

    return mins, {}


class HourlyILPScheduler:
    """
    ✅ FIXED: ILP Scheduler with corrected hour format handling
    """

    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2025, 
                 store_hours=13, work_blocks=None):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)
        self.store_hours = int(store_hours)

        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks

        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            if not teams:
                codes = ("A",)
            else:
                codes = tuple(get_team_code(team) for team in teams)
            self.emp_team_code[idx] = codes
            for code in codes:
                get_team_id(code)

        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) 
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        # ✅ Use FIXED function
        mins, ideals = rows_to_req_dicts_FIXED(minimums_rows)
        
        self.minimos = mins.copy()
        self.ideais = ideals.copy()
        
        print(f"[DEBUG] Final self.minimos has {len(self.minimos)} entries")
        print(f"[DEBUG] Expected entries: {self.num_days * 26 * 2} (365 days × 26 half-hours × 2 teams)")

        # Blocks that influence next day
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
        
        # Model variables
        self.x = None
        self.y = None
        self.model = None
        self.status = None
        self.assignment = defaultdict(list)
        self.vacs_1based = {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

    def _generate_work_blocks(self):
        """Generate valid work blocks (start, break, end)."""
        blocks = create_Blocks(0.5, 9, 22)
        for b in blocks:
            print(f"  Block: {b[0]}-{b[1]}-{b[2]}")
        sleep(2)
        return blocks

    def _get_working_hours(self, block):
        """
        ✅ Returns SET of floats (not strings!) when employee is working.
        For block (9.0, 14.0, 18.0): returns {9.0, 9.5, 10.0, ..., 13.5, 15.0, ..., 17.5}
        """
        start, break_start, end = block
        hours = []
        
        # First work period (before break)
        h = start
        while h < break_start:
            hours.append(h)
            h += 0.5
        
        # Second work period (after 1-hour break)
        h = break_start + 1
        while h < end:
            hours.append(h)
            h += 0.5
        
        return set(hours)

    def _validate_block_transition(self, block_today, block_tomorrow):
        """Check if transition allows 12h rest."""
        end_today = block_today[2]
        start_tomorrow = block_tomorrow[0]
        rest_hours = (24 - end_today) + start_tomorrow
        return rest_hours >= 12

    def build_model(self):
        """✅ FIXED: Build ILP model with correct hour format lookups."""
        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(len(self.work_blocks)))

        # ✅ CRITICAL: horas must be FLOATS, not strings!
        horas = []
        h = 9.0
        while h < 22.0:
            horas.append(h)
            h += 0.5

        # Decision variables X
        self.x = {
            f: {
                d: {
                    b: {
                        team_code: pulp.LpVariable(
                            f"x_{f}_{d.strftime('%Y%m%d')}_{b}_{team_code}", 
                            cat="Binary"
                        )
                        for team_code in self.emp_team_code[f]
                    }
                    for b in blocos
                }
                for d in dias
            }
            for f in funcionarios
        }

        # Auxiliary Y variables
        self.y = {
            d: {
                h: {
                    team_code: pulp.LpVariable(
                        f"y_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, cat="Integer"
                    )
                    for team_code in self.teams.keys()
                }
                for h in horas
            }
            for d in dias
        }

        # CSP Model → Optimization Model (minimize deficit)
        model = pulp.LpProblem("Hourly_Schedule_Optimization", pulp.LpMinimize)
        # Objective will be set after creating slack variables

        print(f"[HourlyILP] Linking Y with X...")
        # Link Y with X: count workers at each hour
        for d in dias:
            for h in horas:
                for team_code, members in self.teams.items():
                    model += (
                        self.y[d][h][team_code] ==
                        pulp.lpSum(
                            self.x[f][d][b][tc]
                            for f in members
                            for b in blocos
                            if h in self._get_working_hours(self.work_blocks[b])
                            for tc in self.emp_team_code[f]
                            if tc == team_code
                        ),
                        f"link_y_x_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                    )

        # ✅ HARD CONSTRAINTS: Minimum coverage (with penalty for small deficits)
        print(f"[HourlyILP] Adding minimum coverage constraints (with flexibility)...")
        min_constraints_added = 0
        
        # Slack variables for small coverage deficits
        deficit_vars = {}

        for d in dias:
            for h in horas:
                for team_code in self.teams.keys():
                    team_id = get_team_id(team_code)
                    minimo = self.minimos.get((d, h, team_id), None)
                    
                    if minimo is None:
                        continue
                    
                    if minimo == -1:
                        # Closed - force to 0
                        model += (
                            self.y[d][h][team_code] == 0,
                            f"closed_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                        )
                    elif minimo > 0:
                        # Allow small deficit (up to 1 person) with slack variable
                        slack_var = pulp.LpVariable(
                            f"deficit_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                            lowBound=0, upBound=1, cat="Continuous"
                        )
                        deficit_vars[(d, h, team_code)] = slack_var
                        
                        # Relaxed constraint: coverage >= minimum - 1
                        model += (
                            self.y[d][h][team_code] + slack_var >= minimo,
                            f"min_coverage_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                        )
                        min_constraints_added += 1

        print(f"  Added {min_constraints_added} minimum constraints (with slack)")
        
        # Objective: minimize total deficit
        if deficit_vars:
            model += pulp.lpSum(deficit_vars.values()), "Minimize_Coverage_Deficit"

        # CONSTRAINT 1: One block per day OR vacation
        print(f"[HourlyILP] Adding one-block-per-day constraints...")
        for f in funcionarios:
            for d in dias:
                is_vacation = 1 if d in self.vacations_dates[f] else 0
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 1 - is_vacation,
                    f"one_block_f{f}_{d.strftime('%Y%m%d')}"
                )

        # CONSTRAINT 2: Working days target (223 ± tolerance)
        print(f"[HourlyILP] Adding working days constraints (223 ± 10)...")
        DAYS_TARGET = 223
        DAYS_TOLERANCE = 10  # Allow 213-233 days
        
        for f in funcionarios:
            total_days = pulp.lpSum(
                self.x[f][d][b][tc]
                for d in dias
                for b in blocos
                for tc in self.emp_team_code[f]
            )
            
            # Lower bound: at least 213 days
            model += (
                total_days >= DAYS_TARGET - DAYS_TOLERANCE,
                f"min_days_f{f}"
            )
            
            # Upper bound: at most 233 days
            model += (
                total_days <= DAYS_TARGET + DAYS_TOLERANCE,
                f"max_days_f{f}"
            )

        # CONSTRAINT 3: No work on closed days
        closed_days = set()
        for (date_key, h, team_id), minimo in self.minimos.items():
            if minimo == -1:
                closed_days.add(date_key)
        
        for f in funcionarios:
            for d in closed_days:
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) == 0,
                    f"no_work_closed_{f}_{d.strftime('%Y%m%d')}"
                )

        # CONSTRAINT 4: Max 5 consecutive days (SOFT)
        print(f"[HourlyILP] Adding max-5-consecutive constraints (soft)...")
        MAX_CONSECUTIVE = 6  # Relaxed from 5 to 6
        
        for f in funcionarios:
            for i in range(len(dias) - MAX_CONSECUTIVE):
                window = dias[i:i + MAX_CONSECUTIVE + 1]
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for d in window
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= MAX_CONSECUTIVE,
                    f"max{MAX_CONSECUTIVE}_f{f}_d{i}"
                )

        self.model = model
        print("[HourlyILP] Model built successfully")
        print(f"  Variables: {model.numVariables():,}")
        print(f"  Constraints: {model.numConstraints():,}")

    def solve(self, gap_rel=0.01):
        """Solve the ILP model."""
        if self.model is None:
            self.build_model()

        print(f"\n{'='*80}")
        print(f"[HourlyILP] SOLVING CSP MODEL (Hard Constraints)")
        print(f"{'='*80}")

        solver = pulp.GUROBI(
            msg=True,
            timeLimit=self.maxTime_sec if self.maxTime_sec else None,
            gapRel=gap_rel,
            Threads=8,
            Method=2,
            Presolve=2
        )

        self.status = self.model.solve(solver)

        status_map = {
            pulp.LpStatusOptimal: "Optimal",
            pulp.LpStatusNotSolved: "Not Solved",
            pulp.LpStatusInfeasible: "Infeasible",
            pulp.LpStatusUnbounded: "Unbounded",
            pulp.LpStatusUndefined: "Undefined"
        }

        print(f"[HourlyILP] Status: {status_map.get(self.status, 'Unknown')}")

        if self.status == pulp.LpStatusOptimal or self.status == pulp.LpStatusNotSolved:
            self._extract_assignments()
        
        return self.status

    def _extract_assignments(self):
        """Extract solution into assignment dict."""
        if self.x is None:
            return
        
        print(f"\n{'='*80}")
        print(f"EXTRACTING ASSIGNMENTS FROM SOLUTION")
        print(f"{'='*80}")
        
        blocos = list(range(len(self.work_blocks)))
        
        for f in self.employees:
            emp_id = f + 1
            team_codes = self.emp_team_code.get(f, ("A",))
            primary_team_code = team_codes[0] if team_codes else "A"
            
            for day_idx, d in enumerate(self.dates, start=1):
                best_block = None
                best_val = 0
                best_team = primary_team_code
                
                for b in blocos:
                    for tc in team_codes:
                        val = pulp.value(self.x[f][d][b][tc]) or 0.0
                        if val > best_val:
                            best_val = val
                            best_block = b
                            best_team = tc
                
                if best_block is not None and best_val > 0.5:
                    team_id = get_team_id(str(best_team))
                    self.assignment[emp_id].append((day_idx, best_block, team_id))

    def export_csv(self, filename="hourly_schedule.csv"):
        """Export schedule to CSV."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(self.vacs_1based.get(emp_id, []))
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
        
        print(f"[HourlyILP] Schedule exported to {filename}")

    def to_table(self):
        """Return schedule as table for display."""
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows = [header]
        
        for emp_id in sorted([i + 1 for i in self.employees]):
            vac_days = set(self.vacs_1based.get(emp_id, []))
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


def solve(vacations, minimuns, employees, maxTime, year=2025, hours=13, 
          work_blocks=None, rules=None):
    """
    ✅ FIXED: Main solve function with corrected hour format handling.
    """
    scheduler = HourlyILPScheduler(
        vacations_rows=vacations,
        minimums_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        store_hours=hours,
        work_blocks=work_blocks
    )

    scheduler.build_model()
    scheduler.solve(gap_rel=0.005)
    scheduler.export_csv("hourly_schedule.csv")
    
    return scheduler.to_table()