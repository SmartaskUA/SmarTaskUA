import csv
from collections import defaultdict
import datetime
import time
import numpy as np
import pandas as pd
import pulp

from algorithms.utils import (
    rows_to_vac_dict,
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code,
    rows_to_req_dicts_FIXED       
)


class HourlyILPScheduler:
    """
    ILP Scheduler that assigns employees to hourly blocks instead of shifts.
    Each employee works 8 hours per day with a 1-hour break (4h + break + 4h pattern).
    """
    
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2025, 
                 store_hours=13, work_blocks=None, solver="CBC"):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None
        self.solver_name = solver.upper() if solver else "CBC"  # "CBC" or "GUROBI"

        # Calendar - Using 2021-11-01 to 2022-10-31 as in original
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)

        # Employees
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)

        # Store operating hours (9:00-22:00 = 13 hours)
        self.store_hours = int(store_hours)
        
        # Define valid work blocks: (start_hour, break_hour, end_hour)
        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks

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

        """
        self.emp_team_code = {
          0: ("A",),        # Emp 0 só pode trabalhar equipa A
          1: ("A", "B"),    # Emp 1 pode trabalhar equipas A e B
          2: ("B",),        # Emp 2 só pode trabalhar equipa B
          3: ("C",),        # Emp 3 só pode trabalhar equipa C
        }
        """

        # Build team membership
        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        """
        self.teams = {
          "A": {0, 1},      # Equipa A tem empregados 0 e 1
          "B": {1, 2},      # Equipa B tem empregados 1 e 2
          "C": {3},         # Equipa C tem empregado 3
        }
        """

        # Vacations
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) 
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        """
        {
          0: {datetime(2021, 11, 5), datetime(2021, 11, 10), datetime(2021, 11, 15)},
          1: {datetime(2021, 11, 20), datetime(2021, 11, 21), datetime(2021, 11, 22)},
          2: {datetime(2021, 12, 8)},
        }
        """

        # Minimum requirements per hour
        mins, ideals = rows_to_req_dicts_FIXED(minimums_rows)
        self.minimos = {}
        self.ideais = {}

        for (day, hour, team_id), val in mins.items():
            # Se for inteiro, converte para Timestamp
            
            if isinstance(day, int):
                if 1 <= day <= self.num_days:
                    date_key = self.dates[day - 1]
                else:
                    continue
            elif isinstance(day, pd.Timestamp):
                if day in self.dates:
                    date_key = day
                else:
                    continue
            else:
                continue
            team_code = TEAM_ID_TO_CODE.get(team_id)
            if team_code:
                self.minimos[(date_key, hour, team_code)] = int(val)
                if int(val) == -1:
                    self.ideais[(date_key, hour, team_code)] = -1
                else:
                    self.ideais[(date_key, hour, team_code)] = self.minimos[(date_key, hour, team_code)] + 1

        """
        self.minimos = {
          (datetime(2021, 11, 1), '09-10', 'A'): -1,    # 1º dia, 09-10, equipa A → fechado
          (datetime(2021, 11, 2), '09-10', 'A'): 4,     # 2º dia, 09-10, equipa A → 4 pessoas
          (datetime(2021, 11, 3), '09-10', 'A'): 3,     # 3º dia, 09-10, equipa A → 3 pessoas
          ...
        }
        """

        # Br Blocos que influenciam o dia seguinte
        self.Ar = self._Ar_Builder(self.work_blocks, rest_hours=12)

        # Model variables
        self.x = None
        self.model = None
        self.status = None
        self.assignment = defaultdict(list)
        self.vacs_1based = {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

        """
        Somente para o export
        self.vacs_1based = {
          1: [6, 11, 16],           # Emp 1 tem férias nos dias 6, 11, 16 (1-based)
          2: [21, 22, 23],          # Emp 2 tem férias nos dias 21, 22, 23
          3: [39],                  # Emp 3 tem férias no dia 39
        }
        """

    def _generate_work_blocks(self):
        """
        Generate valid work blocks based on the specific combinations provided.
        Each tuple represents (start_hour, break_hour, end_hour).
        Examples:
        - (9, 13, 18): work 9-13 (4h), break 13-14, work 14-18 (4h) = 8h total
        - (9, 14, 18): work 9-14 (5h), break 14-15, work 15-18 (3h) = 8h total
        """
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
    

    def _Ar_Builder(self, work_Blocks, rest_hours):

        """
        Return a dictionary of blocks that are dependent on the previous day's block for Xh rest.
        {(9, 13, 18): [(12, 16, 21), (12, 17, 21), (12, 18, 21), (13, 17, 22), (13, 18, 22), (13, 19, 22)],
        (9, 14, 18): [(12, 16, 21), (12, 17, 21), (12, 18, 21), (13, 17, 22), (13, 18, 22), (13, 19, 22)],
        (9, 15, 18): [(12, 16, 21), (12, 17, 21), (12, 18, 21), (13, 17, 22), (13, 18, 22), (13, 19, 22)], 
        (10, 14, 19): [(13, 17, 22), (13, 18, 22), (13, 19, 22)], 
        (10, 15, 19): [(13, 17, 22), (13, 18, 22), (13, 19, 22)], 
        (10, 16, 19): [(13, 17, 22), (13, 18, 22), (13, 19, 22)]}
        ....
        """

        Non_Rest_Hours = 24 - rest_hours + 1
        Ar = {} # {() : [(), (), ()]} Key - Block a ; Value - Set of Blocks b that depend on a
        for b in work_Blocks:
            (start_b, break_b, end_b) = b
            for a in work_Blocks:
                (start_a, break_a, end_a) = a
                if start_b + round(Non_Rest_Hours) <= end_a:
                    if b not in Ar:
                        Ar[b] = []
                    Ar[(b)].append(a)
        return Ar


    def build_model(self):
        """Build the ILP model with hourly constraints."""
        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(len(self.work_blocks)))  # Block indices
        horas = [round(h, 1) for h in [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 
                          12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 
                          17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5]]        

        # Decision variables: X[employee][day][block][team]
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

        # Auxiliary: Number of workers at hour h on day d in team e
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

        self.z = {
            d: {
                h: {
                    team_code: pulp.LpVariable(
                        f"z_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, cat="Integer"
                    )
                    for team_code in self.teams.keys()
                }
                for h in horas
            }
            for d in dias
        }

        # minimizar modelo
        model = pulp.LpProblem("Hourly_Schedule_ILP", pulp.LpMinimize)


# -------------------------------------------------------

        penalties_min = []
        self.shortage = {}

        print(f"[ILP_4_Half_Intervals] Adding constraints...")

        # Link Y with X: count workers at each hour
        for d in dias:
            for h in horas:

                for team_code, members in self.teams.items():
                    minimo = self.minimos.get((d, h, team_code), None)

                    if minimo is None or minimo == -1:
                        continue
                
                    model += (
                        self.y[d][h][team_code] >= minimo - pulp.lpSum(
                            self.x[f][d][b][team_code]
                            for f in members
                            for b in blocos
                            if h in self._get_working_hours(self.work_blocks[b])
                        ),
                        f"short_def_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                    )

                    penalties_min.append(self.y[d][h][team_code])


        penalties_ideal = []


        for d in dias:
            for h in horas:

                for team_code, members in self.teams.items():
                    ideal = self.ideais.get((d, h, team_code), None)

                    # ignorar slots sem requisito ou fechados
                    if ideal is None or ideal == -1:
                        continue
                

                    model += (
                        self.z[d][h][team_code] >= ideal - pulp.lpSum(
                            self.x[f][d][b][team_code]
                            for f in members
                            for b in blocos
                            if h in self._get_working_hours(self.work_blocks[b])
                            # for tc in self.emp_team_code[f]
                            # if tc == team_code
                        ),
                        f"short_defs_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                    )

                    penalties_ideal.append(self.z[d][h][team_code])


        # Objective: Minimize deviations from minimums and ideals

        """
        O solver vai prioritariamente tentar reduzir as faltas aos mínimos, 
        porque cada pessoa que falta custa 10000 unidades na função objectivo.
        Pesos entre 1000 e 10000 tornam hard as violacoes aos minimos
        Viola apenas se não existir solucao viavel ou existir conflitos estruturais (Ferias ou dia total de trabalhos)
        """

        model += (
            pulp.lpSum(z for z in penalties_ideal) +
              10000 * pulp.lpSum(y for y in penalties_min),
            "Minimize_shortages"
        ) 

# ----------------------------------------------------        

        # CONSTRAINTS

        # 1. One block per day - exactly one block must be selected and no work on vacation days
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
        # Identify all dates where minimum is -1 for any team
        closed_days = set()
        for (date_key, hora_str, team_code), minimo in self.minimos.items():
            if minimo == -1:
                closed_days.add(date_key)
        
        # Force no work on closed days
        model += (
            pulp.lpSum(
                self.x[f][d][b][tc]
                for f in funcionarios
                for d in closed_days
                for b in blocos
                for tc in self.emp_team_code[f]
            ) == 0,
            f"no_work_closed_day_f{f}_{d.strftime('%Y%m%d')}"
        )



        # 4. Max 5 consecutive working days (sliding window of 6 days)
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]  # bloco de 6 dias consecutivos
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for d in window
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 5, # Se a soma das variaveis for maior que 5 nos 6 dias, viola a restrição
                    f"max_5_consecutive_f{f}_{dias[i].strftime('%Y%m%d')}"
                )


        # 5. Valid transitions between consecutive days (12h rest minimum)
        for f in funcionarios:
            for i in range(len(dias) - 1):

                d_today = dias[i]
                d_next = dias[i + 1]

                for a, ba in self.Ar.items():  # a ∈ A_r e b ∈ B_a

                    Ba = set()
                    for b in ba:
                        Ba.add(b)

                    team_codes = self.emp_team_code[f]

                    sum_next = pulp.lpSum(
                        self.x[f][d_next][self.work_blocks.index(a)][tc]
                        for tc in team_codes
                    )

                    sum_today = pulp.lpSum(
                        self.x[f][d_today][self.work_blocks.index(b)][tc]
                        for b in Ba
                        for tc in team_codes
                    )

                    model += (
                        sum_today + sum_next <= 1,
                        f"rest_12h_f{f}_{d_today.strftime('%Y%m%d')}_a{a}"
                    )

        self.model = model     
        print("[ILP_4_Half_Intervals] Model built successfully")

#   # =========================================================

    def solve(self, gap_rel=0.01):
        """Solve the ILP model."""
        if self.model is None:
            self.build_model()

        print(f"\n{'='*80}")
        print(f"[ILP_4_Half_Intervals] SOLVING ILP MODEL")
        print(f"{'='*80}")
        print(f"[ILP_4_Half_Intervals] Solver parameters:")
        print(f"  Gap relative: {gap_rel*100:.2f}%")
        print(f"  Variables: {self.model.numVariables()}")
        print(f"  Constraints: {self.model.numConstraints()}")
        print(f"  Solver: {self.solver_name}")
        print(f"\n[ILP_4_Half_Intervals] Starting solver ({self.solver_name})...")
        print(f"[ILP_4_Half_Intervals] Real-time progress will be shown below:")
        print(f"{'-'*80}")
        
        print(f"[ILP_4_Half_Intervals] Starting solver (max time: {self.maxTime_sec}s)...")
        print(f"[ILP_4_Half_Intervals] Optimality gap: {gap_rel * 100:.1f}%")
        print(f"  Solver will stop when solution is within {gap_rel * 100:.1f}% of optimal")
        
        # Choose solver based on solver_name
        if self.solver_name == "GUROBI":
            try:
                solver = pulp.GUROBI(
                    msg=False,
                    timeLimit=self.maxTime_sec if self.maxTime_sec else None,
                    gapRel=gap_rel,
                    Threads=8,
                    Method=2,      # Barrier method
                    Presolve=2     # Aggressive presolve
                )
                print("[ILP_4_Half_Intervals] Using GUROBI solver")
            except Exception as e:
                print(f"[ILP_4_Half_Intervals] GUROBI not available ({e}), falling back to CBC")
                solver = pulp.PULP_CBC_CMD(
                    msg=False,
                    timeLimit=(self.maxTime_sec if self.maxTime_sec is not None else 8 * 3600),
                    gapRel=gap_rel,
                )
        else:
            solver = pulp.PULP_CBC_CMD(
                msg=False,
                timeLimit=(self.maxTime_sec if self.maxTime_sec is not None else 8 * 3600),
                gapRel=gap_rel,
            )
            print("[ILP_4_Half_Intervals] Using CBC solver")
        
        start_time = time.time()
        self.status = self.model.solve(solver)
        solve_time = time.time() - start_time
        
        print(f"[ILP_4_Half_Intervals] Solver wall clock time: {solve_time:.2f} seconds")
        
        status_map = {
            pulp.LpStatusOptimal: "Optimal",
            pulp.LpStatusNotSolved: "Not Solved",
            pulp.LpStatusInfeasible: "Infeasible",
            pulp.LpStatusUnbounded: "Unbounded",
            pulp.LpStatusUndefined: "Undefined"
        }
        
        print(f"[ILP_4_Half_Intervals] Solver status: {status_map.get(self.status, 'Unknown')}")
        
        if self.status == pulp.LpStatusOptimal or self.status == pulp.LpStatusNotSolved:
            self._extract_assignments()
            print("[ILP_4_Half_Intervals] Solution extracted")
    
        return self.status


    def _extract_assignments(self):
        """Extract solution into assignment dict."""
        if self.x is None:
            return
        
        # Use integer indices as in build_model
        blocos = list(range(len(self.work_blocks)))
        
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
        
        print(f"[ILP_4_Half_Intervals] Schedule exported to {filename}")


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
          work_blocks=None, rules=None, solver="CBC", **kwargs):
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
        solver: Solver to use - "CBC" (default) or "GUROBI"
    
    Returns:
        Table representation of the schedule
    """
    print(f"[ILP_4_Half_Intervals] Using solver: {solver}")
    scheduler = HourlyILPScheduler(
        vacations_rows=vacations,
        minimums_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        store_hours=hours,
        work_blocks=work_blocks,
        solver=solver
    )

    scheduler.build_model()
    scheduler.solve(gap_rel=0.01) 
    scheduler.export_csv("hourly_schedule.csv")
    return scheduler.to_table()

