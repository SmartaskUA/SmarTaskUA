import csv
from collections import defaultdict
import datetime
from time import time

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
    get_team_code,
    create_Blocks,    
    drange,
    drange_indexed,
    drange_indexed_h,
    rows_to_req_dicts_Half_Hour
)


class HourlyILPScheduler:
    """
    ILP Scheduler that assigns employees to hourly blocks with 30-minute granularity.
    Each employee works 8 hours per day with a 1-hour break (4h + break + 4h pattern).
    
    FIXED VERSION with multi-solver support (Gurobi, CPLEX, HiGHS, SCIP, CBC)
    """
    
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2025, 
                 store_hours=13, work_blocks=None):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None

        # Calendar - Using 2021-11-01 to 2022-10-31 as in original
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)
        print(f"[HourlyILP] Calendar has {self.num_days} days")

        # Employees
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)
        print(f"[HourlyILP] Employees: {self.num_employees}")

        # Store operating hours (9:00-22:00 = 13 hours)
        self.store_hours = int(store_hours)
        print(f"[HourlyILP] Store hours: 9:00 to {9 + self.store_hours}:00")

        # Define valid work blocks: (start_hour, break_hour, end_hour)
        # Using 0.5h intervals for 30-minute granularity
        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks
        
        print(f"[HourlyILP] Work blocks: {len(self.work_blocks)} total")

        # Employee teams
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

        # Build team membership
        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        print(f"[HourlyILP] Teams: {list(self.teams.keys())}")

        # Holidays and Sundays
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
        
        self.sundays_holidays = [
            d for d in self.dates if d.weekday() == 6 or d.date() in feriados_pt
        ]

        # Vacations
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) 
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        vac_count = sum(1 for v in self.vacations_dates.values() if v)
        print(f"[HourlyILP] Vacations: {vac_count} employees have vacation days")

        # Minimum requirements per 30-minute interval
        mins, ideals = rows_to_req_dicts_Half_Hour(minimums_rows)
        self.minimos = {}
        
        for (day, hour, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, hour, team_code)] = int(val)

        print(f"[HourlyILP] Minimum requirements: {len(self.minimos)} constraints")

        # Model variables
        self.x = None
        self.y = None
        self.model = None
        self.status = None
        self.shortage = {}
        self.assignment = defaultdict(list)
        self.vacs_1based = {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

    def _generate_work_blocks(self):
        """
        Generate valid work blocks with 30-minute (0.5h) intervals.
        Each block: (start_hour, break_hour, end_hour)
        Examples: (9.0, 13.0, 18.0), (9.0, 14.0, 18.0), (9.5, 13.5, 18.5), etc.
        """
        blocks = create_Blocks(0.5, 9.0, 22.0)
        print(f"[HourlyILP] Generated {len(blocks)} work blocks (30-min intervals)")
        return blocks

    def _get_working_hours(self, block):
        """
        Returns set of 30-minute periods when employee is working (excluding break).
        For block (9, 13, 18): returns {9.0, 9.5, 10.0, ..., 12.5, 14.0, ..., 17.5}
        Total: 16 half-hours (8 hours of work)
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

        assert len(hours) == 16, f"Invalid block coverage: {block} has {len(hours)} half-hours, expected 16"

        return set(hours)

    def _validate_block_transition(self, block_today, block_tomorrow):
        """
        Check if transition from block_today to block_tomorrow respects 12h rest.
        """
        end_today = block_today[2]
        start_tomorrow = block_tomorrow[0]
        # Rest hours overnight
        rest_hours = (24 - end_today) + start_tomorrow
        return rest_hours >= 12

    def build_model(self):
        """Build the ILP model with 30-minute granularity constraints."""
        print(f"[HourlyILP] Building ILP model...")
        
        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(len(self.work_blocks)))
        
        # Generate 30-minute periods: 9.0, 9.5, 10.0, ..., 21.5
        horas = drange_indexed_h(9, 22, 0.5)
        horas_set = set(horas)
        horas = sorted(horas)
        
        print(f"[HourlyILP] Model dimensions:")
        print(f"  - Employees: {len(funcionarios)}")
        print(f"  - Days: {len(dias)}")
        print(f"  - Work blocks: {len(blocos)}")
        print(f"  - Half-hour periods: {len(horas)}")
        print(f"  - Estimated binary variables: ~{len(funcionarios) * len(dias) * len(blocos) * 2:,}")

        # Decision variables: X[employee][day][block][team]
        print(f"[HourlyILP] Creating decision variables X[f][d][b][t]...")
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

        # Auxiliary: Y[day][hour][team] = number of workers
        print(f"[HourlyILP] Creating auxiliary variables Y[d][h][t]...")
        self.y = {
            d: {
                h: {
                    team_code: pulp.LpVariable(
                        f"y_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, 
                        cat="Integer"
                    )
                    for team_code in self.teams.keys()
                }
                for h in horas
            }
            for d in dias
        }

        model = pulp.LpProblem("Hourly_Schedule_ILP_30min", pulp.LpMinimize)

        # Link Y with X: count workers at each 30-minute period
        print(f"[HourlyILP] Linking Y and X variables...")
        for d_idx, d in enumerate(dias):
            if d_idx % 50 == 0:
                print(f"  Progress: {d_idx}/{len(dias)} days")
            
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

        # Shortage variables
        print(f"[HourlyILP] Creating shortage variables...")
        penalties_min = []
        self.shortage = {}

        for d in dias:
            for h in horas:
                # Format hour string to match requirements: "09.0-09.5", "09.5-10.0", etc.
                hora_str = f"{h:04.1f}-{h+0.5:04.1f}"

                for team_code in self.teams.keys():
                    minimo = self.minimos.get((d, hora_str, team_code), None)
                    
                    # Skip slots without requirements or closed days (-1)
                    if minimo is None or minimo == -1:
                        continue
                    
                    s = pulp.LpVariable(
                        f"short_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0,
                        cat="Integer"
                    )

                    self.shortage[(d, h, team_code)] = s

                    model += (
                        s >= minimo - self.y[d][h][team_code],
                        f"short_def_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                    )

                    penalties_min.append(s)

        print(f"[HourlyILP] Total shortage variables: {len(penalties_min)}")

        # *** OBJECTIVE FUNCTION: Minimize total shortages ***
        print(f"[HourlyILP] Setting objective function...")
        model += pulp.lpSum(s for s in penalties_min), "Minimize_shortages"

        # CONSTRAINTS
        print(f"[HourlyILP] Adding constraints...")

        # 1. One block per day - exactly one block must be selected and no work on vacation days
        print(f"  [1/6] One block per day + vacation constraint...")
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 1 - (1 if d in self.vacations_dates[f] else 0),
                    f"one_block_or_vacation_f{f}_{d.strftime('%Y%m%d')}"
                )

        # 2. Total working days = 223 in the year
        print(f"  [2/6] Total working days = 223...")
        for f in funcionarios:
            model += (
                pulp.lpSum(
                    self.x[f][d][b][tc]
                    for d in dias
                    for b in blocos
                    for tc in self.emp_team_code[f]
                ) == 223,
                f"total_working_days_f{f}"
            )

        # 3. No work on days marked with -1 (closed days/holidays)
        print(f"  [3/6] Closed days constraint...")
        closed_days = set()
        for (date_key, hora_str, team_code), minimo in self.minimos.items():
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
                    f"no_work_closed_day_f{f}_{d.strftime('%Y%m%d')}"
                )

        print(f"    Closed days: {len(closed_days)}")

        # 4. Max 5 consecutive working days (sliding window of 6 days)
        print(f"  [4/6] Max 5 consecutive working days...")
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for d in window
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 5,
                    f"max_5_consecutive_f{f}_{dias[i].strftime('%Y%m%d')}"
                )

        # 5. Valid transitions between consecutive days (12h rest minimum)
        print(f"  [5/6] Valid transitions (12h rest)...")
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                for a in blocos:
                    for b in blocos:
                        if not self._validate_block_transition(self.work_blocks[b], self.work_blocks[a]):
                            for tc in self.emp_team_code[f]:
                                model += (
                                    self.x[f][d_today][b][tc] + self.x[f][d_next][a][tc] <= 1,
                                    f"invalid_transition_f{f}_{d_today.strftime('%Y%m%d')}_b{b}_a{a}_{tc}"
                                )

        self.model = model
        
        # Verify coverage
        print(f"  [6/6] Verifying half-hour coverage...")
        uncovered = []
        for h in sorted(horas):
            covered = any(
                h in self._get_working_hours(self.work_blocks[b])
                for b in blocos
            )
            if not covered:
                uncovered.append(h)
        
        if uncovered:
            print(f"    WARNING: Uncovered half-hours: {uncovered}")
        else:
            print(f"    All {len(horas)} half-hour periods are covered")
                
        print(f"[HourlyILP] Model built successfully!")
        print(f"  Total constraints: {len(model.constraints):,}")
        print(f"  Total variables: {len(model.variables()):,}")

    def solve(self, gap_rel=0.005, solver_name='gurobi'):
        """
        Solve the ILP model with automatic solver selection.
        
        Args:
            gap_rel: Relative gap tolerance (0.005 = 0.5%)
            solver_name: 'auto', 'gurobi', 'cplex', 'highs', 'scip', 'cbc'
        """
        if self.model is None:
            self.build_model()
        
        print(f"[HourlyILP] Solver configuration:")
        print(f"  Time limit: {self.maxTime_sec}s")
        print(f"  Gap tolerance: {gap_rel*100}%")
        
        # Detect available solvers
        available_solvers = []
        
        if solver_name == 'auto':
            # Try in order of preference: Gurobi > CPLEX > HiGHS > SCIP > CBC
            
            print(f"\n[HourlyILP] Checking solver availability...")
            
            # Check Gurobi via Python API (not command-line binary)
            try:
                import gurobipy
                available_solvers.append('gurobi')
                print(f"  ✓ Gurobi: Available (Python API v{gurobipy.gurobi.version()})")
            except ImportError:
                print(f"  ✗ Gurobi: Not installed")
            except Exception as e:
                print(f"  ✗ Gurobi: Error ({type(e).__name__}: {e})")
        
            try:
                if pulp.PULP_CBC_CMD(msg=False).available():
                    available_solvers.append('cbc')
                    print(f"  ✓ CBC: Available")
                else:
                    print(f"  ✗ CBC: Not available")
            except Exception as e:
                print(f"  ✗ CBC: Not installed ({type(e).__name__})")
            
            if not available_solvers:
                raise Exception("No solver available!")
            
            solver_name = available_solvers[0]
            
            print(f"  Available solvers: {available_solvers}")
            print(f"  Selected solver: {solver_name.upper()}")
        else:
            print(f"  Using specified solver: {solver_name.upper()}")
        
        # Create appropriate solver
        try:
            if solver_name == 'gurobi':
                # Use Python API instead of command-line binary
                solver = pulp.GUROBI(
                    msg=True,
                    timeLimit=self.maxTime_sec if self.maxTime_sec else None,
                    gapRel=gap_rel,
                    Threads=4,
                    Method=2,      # Barrier method, pode se escolher o metodo que quer
                    Presolve=2     # Aggressive presolve
                )
            
            else:  # cbc
                solver = pulp.PULP_CBC_CMD(
                    msg=True,
                    timeLimit=self.maxTime_sec if self.maxTime_sec else None,
                    gapRel=gap_rel,
                    threads=4
                )
            
            print(f"[HourlyILP] Starting solver...")
            self.status = self.model.solve(solver)
            
        except Exception as e:
            error_msg = str(e)
            print(f"[ERROR] Solver '{solver_name}' failed: {e}")
            
            # If Gurobi failed due to license, fallback to CBC
            if solver_name == 'gurobi' and ('HostID mismatch' in error_msg or 'license' in error_msg.lower()):
                print(f"[WARNING] Gurobi license issue detected - falling back to CBC solver")
                print(f"[INFO] To fix this:")
                print(f"  1. Get WLS license (works in Docker): https://license.gurobi.com/manager/licenses")
                print(f"  2. Or run outside Docker to use your local Gurobi license")
                
                try:
                    solver = pulp.PULP_CBC_CMD(
                        msg=True,
                        timeLimit=self.maxTime_sec if self.maxTime_sec else None,
                        gapRel=gap_rel,
                        threads=2
                    )
                    print(f"[HourlyILP] Retrying with CBC solver...")
                    self.status = self.model.solve(solver)
                except Exception as e2:
                    print(f"[ERROR] CBC fallback also failed: {e2}")
                    raise
            else:
                print(f"[ERROR] Recommendations:")
                print(f"  1. Install Gurobi: pip install gurobipy")
                print(f"  2. Get free academic WLS license: https://www.gurobi.com/academia/")
                print(f"  3. Problem may be too large for CBC")
                raise
        
        status_map = {
            pulp.LpStatusOptimal: "Optimal",
            pulp.LpStatusNotSolved: "Not Solved",
            pulp.LpStatusInfeasible: "Infeasible",
            pulp.LpStatusUnbounded: "Unbounded",
            pulp.LpStatusUndefined: "Undefined"
        }
        
        print(f"[HourlyILP] Solver status: {status_map.get(self.status, 'Unknown')}")
        
        if self.status == pulp.LpStatusOptimal or self.status == pulp.LpStatusNotSolved:
            self._extract_assignments()
            
            # Calculate metrics
            total_shortage = sum(
                int(pulp.value(s)) if pulp.value(s) else 0
                for s in self.shortage.values()
            )
            objective = pulp.value(self.model.objective) if self.model.objective else 0
            
            print(f"[HourlyILP] Total shortage: {total_shortage}")
            print(f"[HourlyILP] Objective value: {objective}")
            
            # Assignments per employee
            print(f"[HourlyILP] Employees with assignments:")
            for emp, assg in self.assignment.items():
                print(f"  Emp {emp}: {len(assg)} days")
        
        return self.status

    def _extract_assignments(self):
        """Extract solution into assignment dict."""
        if self.x is None:
            return
        
        blocos = list(range(len(self.work_blocks)))
        
        for f in self.employees:
            emp_id = f + 1
            team_codes = self.emp_team_code.get(f, ("A",))
            
            for day_idx, d in enumerate(self.dates, start=1):
                best_block = None
                best_val = 0
                best_team = team_codes[0]
                
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
                        row.append('F')
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
          work_blocks=None, rules=None, solver='auto'):
    """
    Main solve function for hourly scheduling with 30-minute granularity.
    
    Args:
        vacations: Vacation data rows
        minimuns: Minimum requirements rows (30-minute intervals)
        employees: List of employee dicts
        maxTime: Maximum solving time in minutes
        year: Year for scheduling
        hours: Total store operating hours (default 13: 9am-10pm)
        work_blocks: Optional custom work blocks
        rules: Optional rules dict
        solver: 'auto', 'gurobi', 'cplex', 'highs', 'scip', 'cbc'
    
    Returns:
        Table representation of the schedule
    
    IMPORTANT: This uses 30-minute intervals (0.5h), creating ~78 work blocks.
    For best results, use Gurobi or CPLEX:
        pip install gurobipy
        Free academic license: https://www.gurobi.com/academia/
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
    scheduler.solve(gap_rel=0.01, solver_name=solver)
    
    print("Total shortage:", sum(int(pulp.value(s)) for s in scheduler.shortage.values()))

    scheduler.export_csv("hourly_schedule.csv")
    
    return scheduler.to_table()