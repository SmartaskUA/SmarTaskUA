# ILP3 – Scheduler por HORAS (intervalos de 1h)
# Segue rigorosamente o método do PDF (ILP1 + ILP2)
# Usa blocos horários (start, break, end) como enviados pelo utilizador
import datetime

import csv
import pulp
import pandas as pd
from collections import defaultdict
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

            if not v:
                continue
            
            try:
                val_int = int(v)
            except ValueError:
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


class ILP3Scheduler:
    """
    Scheduler por HORAS (09-10, 10-11, ...), baseado em blocos de 8h
    Resolve em dois passos:
      1) ILP1 – minimizar violações aos mínimos
      2) ILP2 – fixar mínimos ótimos e minimizar violações aos ideais
    """

    def __init__(self, vacations_rows, minimums_rows, employees, maxTime,
                 year=2021, store_hours=13, work_blocks=None):

        # ---------------- Calendário ----------------
        self.dates = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31").to_list()
        self.num_days = len(self.dates)
        self.D = list(range(self.num_days))

        # ---------------- Empregados ----------------
        self.employees = list(range(len(employees)))
        self.I = self.employees

        # ---------------- Equipas ----------------
        self.emp_team_code = {}
        for i, emp in enumerate(employees):
            teams = emp.get("teams", []) or ["A"]
            self.emp_team_code[i] = tuple(get_team_code(t) for t in teams)
            for t in self.emp_team_code[i]:
                get_team_id(t)
        self.teams = sorted({t for ts in self.emp_team_code.values() for t in ts})

        # ---------------- Blocos ----------------
        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks
            
        self.num_blocks = len(self.work_blocks)
        self.A = list(range(self.num_blocks))

        # ---------------- Horas (1h) ----------------
        self.horas = drange_indexed_h(9, 22, 0.5)
        self.H = [f"{h:04.1f}-{h+0.5:04.1f}" for h in self.horas]

        # ---------------- Alpha[a,h] ----------------
        self.alpha = defaultdict(int)
        for a, (start, brk, end) in enumerate(self.work_blocks):
            for h in drange_indexed_h(start, brk, 0.5):
                self.alpha[(a, f"{h:04.1f}-{h+0.5:04.1f}")] = 1
            for h in drange_indexed_h(brk + 1, end, 0.5):
                self.alpha[(a, f"{h:04.1f}-{h+0.5:04.1f}")] = 1

        # ---------------- Férias ----------------
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
        self.delta = {(i, d): 1 if self.dates[d] in self.vacations_dates[i] else 0
                      for i in self.I for d in self.D}

        # ---------------- Requisitos ----------------
        self.theta, self.beta = rows_to_req_dicts_FIXED(minimums_rows)

        self.model = None
        self.assignment = defaultdict(list)
        self.maxTime_sec = int(maxTime) * 60 if maxTime else None

    
    def _generate_work_blocks(self):
        """
        Generate valid work blocks with 30-minute (0.5h) intervals.
        Each block: (start_hour, break_hour, end_hour)
        Examples: (9.0, 13.0, 18.0), (9.0, 14.0, 18.0), (9.5, 13.5, 18.5), etc.
        """
        blocks = create_Blocks(0.5, 9, 22)
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
    
    
    # =========================================================
    # BUILD MODEL (ILP1 + ILP2)
    # =========================================================



    def build_model(self):

        print(f"[HourlyILPStrict] Building ILP model...")
        
        model = pulp.LpProblem("ILP3_Hourly", pulp.LpMinimize)

        # Variáveis
        self.x = pulp.LpVariable.dicts(
            "x", (self.I, self.D, self.A, self.teams), cat="Binary"
        )
        self.z = pulp.LpVariable.dicts(
            "z", (self.I, self.D, self.A), cat="Binary"
        )
        self.y = pulp.LpVariable.dicts(
            "y", (self.D, self.H, self.teams), lowBound=0, cat="Integer"
        )

        # ---------- Objetivo (ILP1: mínimos) ----------
        # model += pulp.lpSum(self.y[d][h][e] for d in self.D for h in self.H for e in self.teams)

        # ---------- Restrições ----------

        # (2) 1 bloco por dia ou férias
        for i in self.I:
            for d in self.D:
                model += (
                    pulp.lpSum(self.z[i][d][a] for a in self.A)
                    <= 1 - self.delta[(i, d)]
                )

        # ligação z -> x
        for i in self.I:
            for d in self.D:
                for a in self.A:
                    model += (
                        pulp.lpSum(self.x[i][d][a][e] for e in self.emp_team_code[i])
                        == self.z[i][d][a]
                    )

        # (3) equipas permitidas
        for i in self.I:
            for e in self.teams:
                if e not in self.emp_team_code[i]:
                    for d in self.D:
                        for a in self.A:
                            model += self.x[i][d][a][e] == 0

        # (4) 223 dias de trabalho
        for i in self.I:
            model += pulp.lpSum(self.z[i][d][a] for d in self.D for a in self.A) == 223

        # (5) máximo 5 dias consecutivos
        for i in self.I:
            for d in range(self.num_days - 5):
                model += (
                    pulp.lpSum(self.z[i][dd][a]
                               for dd in range(d, d + 6)
                               for a in self.A) <= 5
                )

        # (6) descanso mínimo de 12h entre dias consecutivos
        for i in self.I:
            for d in range(self.num_days - 1):
                for a in self.A:
                    end_today = self.work_blocks[a][2]
                    for a in self.A:
                        start_tomorrow = self.work_blocks[a][0]
                        rest_hours = (24 - end_today) + start_tomorrow
                        if rest_hours < 12:
                            model += self.z[i][d][a] + self.z[i][d + 1][a] <= 1

        # (8) definição de y (mínimos) + regra de OFF quando mínimo = -1
        # Se theta = -1 ⇒ loja fechada nessa hora/equipa ⇒ ninguém pode trabalhar
        for d in self.D:
            for h in self.H:
                for e in self.teams:
                    theta = self.theta.get((d + 1, h, get_team_id(e)), 0)

                    total_workers = pulp.lpSum(
                        self.alpha[(a, h)] * self.x[i][d][a][e]
                        for i in self.I for a in self.A
                    )

                    if theta == -1:
                        # loja fechada → zero trabalhadores
                        model += total_workers == 0
                        model += self.y[d][h][e] == 0
                    else:
                        # violações aos mínimos
                        model += self.y[d][h][e] >= theta - total_workers
                    # if theta == -1:
                    #     model += self.y[d][h][e] == 0
                    # else:
                    #     model += (
                    #         self.y[d][h][e]
                    #         >= theta - pulp.lpSum(
                    #             self.alpha[(a, h)] * self.x[i][d][a][e]
                    #             for i in self.I for a in self.A
                    #         )
                    #     )

        self.model = model

    # =========================================================
    # SOLVE
    # =========================================================
    def solve(self, gap_rel=0.01, solver_name='gurobi'):
        """
        Solve the ILP model with automatic solver selection.
        
        Args:
            gap_rel: Relative gap tolerance (0.005 = 0.5%)
            solver_name: 'auto', 'gurobi', 'cplex', 'highs', 'scip', 'cbc'
        """
        if self.model is None:
            self.build_model()
        
        print(f"[HourlyILP] Model built successfully!")
        print(f"  Total constraints: {len(self.model.constraints):,}")
        print(f"  Total variables: {len(self.model.variables()):,}")
        
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
                    Threads=8,
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
            # total_shortage = sum(
            #     int(pulp.value(s)) if pulp.value(s) else 0
            #     for s in self.shortage.values()
            # )
            objective = pulp.value(self.model.objective) if self.model.objective else 0
            
            # print(f"[HourlyILP] Total shortage: {total_shortage}")
            print(f"[HourlyILP] Objective value: {objective}")
            
            # Assignments per employee
            print(f"[HourlyILP] Employees with assignments:")
            for emp, assg in self.assignment.items():
                print(f"  Emp {emp}: {len(assg)} days")
        
        return self.status

    # =========================================================
    # EXTRAÇÃO / EXPORTAÇÃO (como pedido)
    # =========================================================
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
                    val_z = pulp.value(self.z[f][d_idx - 1][b])
                    if val_z is not None and val_z > 0.5:
                        chosen_b = b
                        for tc in self.emp_team_code[f]:
                            val_x = pulp.value(self.x[f][d_idx - 1][b].get(tc, 0))
                            if val_x is not None and val_x > 0.5:
                                chosen_team = tc
                                break
                        break
                if chosen_b is not None:
                    team_id = get_team_id(str(chosen_team)) if chosen_team else get_team_id(self.emp_team_code[f][0])
                    self.assignment[emp_id].append((d_idx, chosen_b, team_id))

    def vacs_1based(self):
        return {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

    def export_csv(self, filename="hourly_strict_schedule.csv"):
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            vacs_1b = self.vacs_1based()
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(vacs_1b.get(emp_id, []))
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

    def to_table(self):
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


def solve(vacations=None, minimuns=None, employees=None, maxTime=None,
          year=2021, hours=13, work_blocks=None, rules=None, **kwargs):

    print("\n" + "=" * 80)
    print("[ILP_Extra] HOURLY SCHEDULER - INTEGER LINEAR PROGRAMMING")
    print("=" * 80)

    sched = ILP3Scheduler(
        vacations,
        minimuns,
        employees,
        maxTime,
        year=year,
        store_hours=hours,
        work_blocks=work_blocks
    )

    sched.build_model()
    sched.solve(gap_rel=0.005)
    sched.export_csv("hourly_strict_schedule.csv")

    print("=" * 80)
    print("[ILP_Extra] COMPLETE")
    print("=" * 80 + "\n")

    return sched.to_table()
