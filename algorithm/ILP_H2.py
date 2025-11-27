import csv
from collections import defaultdict
import datetime
from time import time

import numpy as np
import pandas as pd
import pulp
import holidays

from algorithm.utils import (
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    TEAM_CODE_TO_ID,      
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code       
)


class HourlyILPScheduler:
    """
    ILP Scheduler that assigns employees to hourly blocks instead of shifts.
    Each employee works 8 hours per day with a 1-hour break (4h + break + 4h pattern).
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

        print(f"[HourlyILP] Employees loaded:")
        for emp in employees:
            print(f" - {emp.get('name', 'Unknown')} (ID: {emp.get('id', 'Unknown')})")
        print(f"[HourlyILP] Employees loaded: " + str(employees))
        print(f"[HourlyILP] Number of employees: {self.num_employees}")
        

        # Store operating hours (9:00-22:00 = 13 hours)
        self.store_hours = int(store_hours)
        
        print(f"[HourlyILP] Store operates for {self.store_hours} hours daily")

        # Define valid work blocks: (start_hour, break_hour, end_hour)
        # Each block = 4h + 1h break + 4h = 8 working hours
        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks
        
        print(f"[HourlyILP] {self.num_employees} employees, {len(self.work_blocks)} work blocks")
        print(f"[HourlyILP] Work blocks: {self.work_blocks}")

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

        print(f"[HourlyILP] Employee team codes: {self.emp_team_code}")

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
            datetime.date(2021, 11, 1): "All Saints' Day", 
            datetime.date(2022, 5, 2): 'Madrid Day', 
            datetime.date(2022, 6, 29): 'Folga', 
            datetime.date(2022, 5, 1): 'Labor Day', 
            datetime.date(2022, 7, 8): 'Folga', 
            datetime.date(2022, 8, 15): 'Assumption Day', 
            datetime.date(2022, 9, 8): 'Regional Holiday', 
            datetime.date(2022, 10, 12): 'National Day',
            datetime.date(2021, 12, 6): 'Constitution Day',
            datetime.date(2021, 12, 8): 'Immaculate Conception',
            datetime.date(2021, 12, 25): 'Christmas Day'
        }
        print(f"[HourlyILP] Loaded {len(feriados_pt)} holidays for Portugal")
        
        self.sundays_holidays = [
            d for d in self.dates if d.weekday() == 6 or d.date() in feriados_pt
        ]
        print(f"[HourlyILP] Sundays + Holidays: {len(self.sundays_holidays)}")

        # Vacations
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) 
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }
        print(f"[HourlyILP] Loaded vacations for {len(self.vacations_dates)} employees")

        # Minimum requirements per hour
        mins, ideals = rows_to_req_dicts(minimums_rows)
        self.minimos = {}
        self.ideais = {}
        
        for (day, hour, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, hour, team_code)] = int(val)
        
        for (day, hour, team_id), val in ideals.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.ideais[(date_key, hour, team_code)] = int(val)

        print(f"[HourlyILP] Loaded {len(self.minimos)} minimum requirements")

        print(f"[HourlyILP] Loaded {len(self.ideais)} ideal requirements")

        # Model variables
        self.x = None
        self.model = None
        self.status = None
        self.assignment = defaultdict(list)
        self.vacs_1based = {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

    # --------------------- Work Block Utilities --------------------- #

    def _generate_work_blocks(self):
        """
        Generate valid work blocks based on the specific combinations provided.
        Each tuple represents (start_hour, break_hour, end_hour).
        Examples:
        - (9, 13, 18): work 9-13 (4h), break 13-14, work 14-18 (4h) = 8h total
        - (9, 14, 18): work 9-14 (5h), break 14-15, work 15-18 (3h) = 8h total
        """
        blocks = {
            (9, 13, 18):  '000000000111101111000000',  # 4h + 1h break + 4h
            (9, 14, 18):  '000000000111110111000000',  # 5h + 1h break + 3h
            (9, 15, 18):  '000000000111111011000000',  # 6h + 1h break + 2h
            (10, 14, 19): '000000000011110111100000',  # 4h + 1h break + 4h
            (10, 15, 19): '000000000011111011100000',  # 5h + 1h break + 3h
            (10, 16, 19): '000000000011111101100000',  # 6h + 1h break + 2h
            (11, 15, 20): '000000000001111011110000',  # 4h + 1h break + 4h
            (11, 16, 20): '000000000001111101110000',  # 5h + 1h break + 3h
            (11, 17, 20): '000000000001111110110000',  # 6h + 1h break + 2h
            (12, 16, 21): '000000000000111101111000',  # 4h + 1h break + 4h
            (12, 17, 21): '000000000000111110111000',  # 5h + 1h break + 3h
            (12, 18, 21): '000000000000111111011000',  # 6h + 1h break + 2h
            (13, 17, 22): '000000000000011110111100',  # 4h + 1h break + 4h
            (13, 18, 22): '000000000000011111011100',  # 5h + 1h break + 3h
            (13, 19, 22): '000000000000011111101100'  # 6h + 1h break + 2h
        }
        
        return blocks

    def _get_working_hours(self, block):
        """
        Returns set of hours an employee is actually working (excluding break).
        For block (9, 13, 18): returns {9,10,11,12,14,15,16,17}
        """
        start, break_start, end = block
        hours = set(range(start, break_start))  # First period
        hours.update(range(break_start + 1, end))  # Second period (skip break hour)
        return hours

    def _blocks_overlap(self, block1, block2):
        """Check if two work blocks have overlapping working hours."""
        hours1 = self._get_working_hours(block1)
        hours2 = self._get_working_hours(block2)
        return len(hours1 & hours2) > 0

    def _validate_block_transition(self, block_today, block_tomorrow):
        """
        Check if transition from block_today to block_tomorrow is valid.
        Rules: 
        - Must have at least 11 hours rest between end and start
        """
        end_today = block_today[2]  # End hour of today's block
        start_tomorrow = block_tomorrow[0]  # Start hour of tomorrow's block
        
        # Calculate rest hours (always overnight, so add 24 to tomorrow's start)
        rest_hours = (24 - end_today) + start_tomorrow
        
        # Must have at least 11 hours rest
        return rest_hours >= 11
    
    # --------------------- Modelo ILP --------------------- #

    def build_model(self):
        """Build the ILP model with hourly constraints."""
        funcionarios = self.employees
        dias = self.dates
        blocos = list(self.work_blocks.keys())  # Block keys (tuples)
        horas = range(9, 22)  # Store hours 9:00-21:59

        # Decision variables: X[employee][day][block][team]
        # Variables:
        # (9) Core variable
        # x_{i,d,t,e} = 1 if employee i works day d, HOUR t, in team e -> 0 otherwise
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

        #print(self.x)

        ## Add OFF variable (no work) - only one OFF variable per day
        #for f in funcionarios:
        #    for d in dias:
        #        self.x[f][d][-1] = pulp.LpVariable(
        #            f"x_{f}_{d.strftime('%Y%m%d')}_OFF", 
        #            cat="Binary"
        #        )

        # Auxiliary: Number of workers at hour h on day d in team e
        # Shortage variables:
        # y[d][s][team] → shortage relative to minimum (represents the number of missing employees in day d, hour t, team)
        self.y = {
            d: {
                h: {
                    team_code: pulp.LpVariable(
                        f"y_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, cat="Integer"
                    )
                    for team_code in self.teams.keys()
                }
                for h in blocos
            }
            for d in dias
        }
        print(self.y)


        model = pulp.LpProblem("Hourly_Schedule_ILP", pulp.LpMinimize)

        # Link Y with X: count workers at each hour
        for d in dias:
            for h in horas:
                for team_code, members in self.teams.items():
                    minimo = self.minimos.get((d, team_code, h), 0)
                    print(minimo)
                    model += (
                        self.y[d][h][team_code] >= minimo - pulp.lpSum(
                            self.x[f][d][b][tc]
                            for f in members
                            for b in blocos
                            if h in self._get_working_hours(self.work_blocks[b])
                            for tc in self.emp_team_code[f]
                            if tc == team_code
                        ),
                        f"count_{team_code}_{d.strftime('%Y%m%d')}_h{h}"
                    )

        # Objective: Minimize deviations from minimums and ideals
        # ---------------------- OBJECTIVE FUNCTION ---------------------- #
        # (11) Minimize total shortage below IDEAL coverage

        penalties_min = []

        for d in dias:
            for h in horas:
                for team_code in self.teams.keys():
                    minimo = self.minimos.get((d, h, team_code), 0)
                    if minimo > 0:
                        model += (
                            self.y[d][h][team_code] >= minimo,
                            f"min_staff_{team_code}_{d.strftime('%Y%m%d')}_h{h}"
                        )

                    # Penalty for being below minimum
                    penal_min = pulp.LpVariable(
                        f"penal_min_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, cat="Continuous"
                    )
                    model += (
                        penal_min >= minimo - self.y[d][h][team_code],
                        f"shortage_min_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                    )
                    penalties_min.append(penal_min * 100)  # High weight for minimums
                    
                    # Penalty for being below ideal
                    penal_ideal = pulp.LpVariable(
                        f"penal_ideal_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, cat="Continuous"
                    )

        model += (
            pulp.lpSum(penalties_min),
            "Minimize_shortages"
        )

    # ------------------------ CONSTRAINTS ------------------------ #

        # 1. One block per day (or OFF)
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) + self.x[f][d][-1] == 1,
                    f"one_block_per_day_f{f}_{d.strftime('%Y%m%d')}"
                )

        # 2. Total working days = 223 in the year
        for f in funcionarios:
            model += (
                pulp.lpSum(
                    self.x[f][d][b][tc]
                    for d in dias
                    for b in blocos
                    for tc in self.emp_team_code[f]
                ) == 262,
                f"total_working_days_f{f}"
            )

        # 3. Max 22 working days on Sundays/Holidays
        # Ninguém trabalha em domingos/feriados
        for f in funcionarios:
            for d in self.sundays_holidays:
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) == 0,
                    f"no_work_sunday_holiday_f{f}_{d.strftime('%Y%m%d')}"
                )


        # 4. Max 5 consecutive working days (sliding window of 6 days)
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

        # 5. Valid transitions between consecutive days (11h rest minimum)
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_tomorrow = dias[i + 1]
                
                # For each pair of blocks, check if transition is invalid
                for b1 in blocos:
                    block1 = self.work_blocks[b1]
                    for b2 in blocos:
                        block2 = self.work_blocks[b2]
                        
                        # Calculate rest hours between blocks
                        end_today = block1[2]
                        start_tomorrow = block2[0]
                        rest_hours = (24 - end_today) + start_tomorrow
                        
                        # If rest < 11 hours, forbid this transition
                        if rest_hours < 11:
                            model += (
                                pulp.lpSum(
                                    self.x[f][d_today][b1][tc1] + self.x[f][d_tomorrow][b2][tc2]
                                    for tc1 in self.emp_team_code[f]
                                    for tc2 in self.emp_team_code[f]
                                ) <= 1,
                                f"forbid_rest_{f}_{d_today.strftime('%Y%m%d')}_b{b1}_to_b{b2}"
                            )

        # 6. Vacations must be OFF
        for f in funcionarios:
            for vac_day in self.vacations_dates[f]:
                model += (
                    self.x[f][vac_day][-1] == 1,
                    f"vacation_off_f{f}_{vac_day.strftime('%Y%m%d')}"
                )

        # 7. Break time constraint (4th-6th hour must have break)
        # Workers should have their break during the 4th-6th hour of work
        # This is implicitly handled by the work_blocks structure

        self.model = model
        print("[HourlyILP] Model built successfully")

    def solve(self, gap_rel=0.005):
        """Solve the ILP model."""
        if self.model is None:
            self.build_model()

        print(f"[HourlyILP] Starting solver (max time: {self.maxTime_sec}s)...")
        
        solver = pulp.PULP_CBC_CMD(
            msg=True,
            timeLimit=(self.maxTime_sec if self.maxTime_sec is not None else 8 * 3600),
            gapRel=gap_rel,
        )
        
        self.status = self.model.solve(solver)

        # 🔧 Corrigir valores negativos e None em y (erros numéricos do solver)
        for d in self.y:
            for h in self.y[d]:
                for team_code in self.y[d][h]:
                    val = self.y[d][h][team_code].varValue
                    if val is None or val < 0:
                        self.y[d][h][team_code].varValue = 0

        
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
            print("[HourlyILP] Solution extracted")
        
        return self.status

    def _extract_assignments(self):
        """Extract solution into assignment dict."""
        if self.x is None:
            return
        
        for f in self.employees:
            emp_id = f + 1
            team_codes = self.emp_team_code.get(f, ("A",))
            primary_team_code = team_codes[0] if team_codes else "A"
            primary_team_id = get_team_id(str(primary_team_code))
            
            for day_idx, d in enumerate(self.dates, start=1):
                # Find which block was assigned
                best_block = None
                best_val = 0
                best_team = primary_team_code
                
                for b in range(len(self.work_blocks)):
                    for tc in team_codes:
                        val = pulp.value(self.x[f][d][b][tc]) or 0.0
                        if val > best_val:
                            best_val = val
                            best_block = b
                            best_team = tc
                
                if best_block is not None and best_val > 0.5:
                    # Store: (day, block_id, team_id)
                    # You can store work_blocks[best_block] for full info
                    team_id = get_team_id(str(best_team))
                    self.assignment[emp_id].append((day_idx, best_block, team_id))

    def export_csv(self, filename="hourly_schedule.csv"):
        """Export schedule to CSV."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            
            # Each employee
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
                    start, break_h, end = block
                    line.append(f"{start}-{break_h}-{end}_{team_code}")
                else:
                    line.append("OFF")
            
            rows.append(line)
        
        return rows

    def print_x_values(self):
        for f in self.x: #funcionarios
            for d in self.x[f]: # dia
                for b in self.x[f][d]: # bloco
                    for team_code, var in self.x[f][d][b].items(): # equipe
                        val = pulp.value(var)
                        print(f"x_{f}_{d.strftime('%Y%m%d')}_{b}_{team_code} = {val}")


def solve(vacations, minimuns, employees, maxTime, year=2025, hours=13, 
          work_blocks=None, rules=None):
    """
    Main solve function for hourly scheduling.
    
    Args:
        vacations: Vacation data rows
        minimuns: Minimum requirements rows  
        employees: List of employee dicts
        maxTime: Maximum solving time in minutes
        year: Year for scheduling
        hours: Total store operating hours (default 13: 9am-10pm)
        work_blocks: Optional custom work blocks, otherwise auto-generated
        rules: Optional rules dict (for future extensions)
    
    Returns:
        Table representation of the schedule
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