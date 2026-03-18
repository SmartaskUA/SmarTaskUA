from collections import defaultdict
from ortools.sat.python import cp_model
import pandas as pd
import csv
from algorithms.utils import get_team_code, get_team_id, rows_to_req_dicts_FIXED, rows_to_vac_dict, TEAM_ID_TO_CODE 
import datetime

class CPHourScheduler:
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2025, 
                 store_hours=13, work_blocks=None):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None

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

        self.hours = [round(h, 1) for h in [
            9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5,
            13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5,
            17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5
        ]]

        # Minimum requirements per hour - using FIXED function
        mins, ideals = rows_to_req_dicts_FIXED(minimums_rows)
        self.minimos = {}  # (date, hour_float, team_code): val
        self.ideais = {}
        
        for (day, hour, team_id), val in mins.items():
            # day can be int or Timestamp, hour is float, team_id is int
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
        self.model = cp_model.CpModel()
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
        Generate valid work blocks with 0.5h intervals.
        Each tuple represents (start_hour, break_hour, end_hour) as floats.
        Examples:
        - (9.0, 13.0, 18.0): work 9:00-13:00 (4h), break 13:00-14:00, work 14:00-18:00 (4h) = 8h total
        - (9.5, 13.5, 18.5): work 9:30-13:30 (4h), break 13:30-14:30, work 14:30-18:30 (4h) = 8h total
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
        """
        Returns set of hours (floats) an employee is actually working (excluding break).
        For block (9.0, 13.0, 18.0): returns {9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5}
        """
        start, break_start, end = block
        hours = set()
        # First period: start to break_start
        h = start
        while h < break_start:
            hours.add(round(h, 1))
            h = round(h + 0.5, 1)
        # Second period: break_start + 1h to end
        h = break_start + 1
        while h < end:
            hours.add(round(h, 1))
            h = round(h + 0.5, 1)
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

    def _define_vars(self):
        # x[i,d,a,e] boolean
        self.x = {}
        for f in self.employees:
            for d in self.dates:
                for b in list(range(len(self.work_blocks))):
                    for team_code in self.emp_team_code[f]:
                        self.x[(f,d,b,team_code)] = self.model.NewBoolVar(f"x_{f}_{d}_{b}_{team_code}")

        self.y = {}
        for d in self.dates:
            for h in self.hours:  # Use float hours list
                for e in self.teams.keys():
                    self.y[(d,h,e)] = self.model.NewIntVar(
                        0, len(self.employees), f"y_{d}_{h}_{e}"
                    )


    def build_model(self):
        """Build the ILP model with hourly constraints."""
        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(len(self.work_blocks)))  # Block indices

        self._define_vars()


# -------------------------------------------------------

        penalties_min = []
        self.shortage = {}

        print(f"[COP2_Half_Intervals] Adding constraints...")
 
        for d in dias:
            for h in self.hours:  # Use float hours list
                for team_code, members in self.teams.items():
                    minimo = self.minimos.get((d, h, team_code), None)

                    if minimo is None or minimo == -1:
                        continue

                    self.model.Add(
                        self.y[(d,h,team_code)] >= minimo - sum(
                            self.x[(f,d,b,team_code)]
                            for f in members
                            for b in blocos
                            if h in self._get_working_hours(self.work_blocks[b])
                        ),
                    )

                    penalties_min.append(self.y[(d,h,team_code)])

        self.model.Minimize(sum(y for y in penalties_min))

# ----------------------------------------------------        

        # CONSTRAINTS


        # 1. One block per day - exactly one block must be selected and no work on vacation days
        for f in funcionarios:
            for d in dias:
                self.model.Add(
                    sum(
                        self.x[(f,d,b,tc)]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 1 - (1 if d in self.vacations_dates[f] else 0),
                )


        # 3. Total working days = 223 in the year
        for f in funcionarios:
            self.model.Add(
                sum(
                    self.x[(f,d,b,tc)]
                    for d in dias
                    for b in blocos
                    for tc in self.emp_team_code[f]
                ) == 223,
            )



        # 4. No work on days marked with -1 (closed days/holidays)
        # Identify all dates where minimum is -1 for any team
        closed_days = set()
        for (date_key, hora_str, team_code), minimo in self.minimos.items():
            if minimo == -1:
                closed_days.add(date_key)
        
        # Force no work on closed days
        self.model.Add(
            sum(
                self.x[(f,d,b,tc)]
                for f in funcionarios
                for d in closed_days
                for b in blocos
                for tc in self.emp_team_code[f]
            ) == 0,
        )



        # 5. Max 5 consecutive working days (sliding window of 6 days)
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]  # bloco de 6 dias consecutivos
                self.model.Add(
                    sum(
                        self.x[(f,d,b,tc)]
                        for d in window
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 5, # Se a soma das variaveis for maior que 5 nos 6 dias, viola a restrição
                )


        # 6. Valid transitions between consecutive days (12h rest minimum)
        for f in funcionarios:
            for i in range(len(dias) - 1):

                d_today = dias[i]
                d_next = dias[i + 1]

                for a, ba in self.Ar.items():  # a ∈ A_r e b ∈ B_a

                    Ba = set()
                    for b in ba:
                        Ba.add(b)

                    team_codes = self.emp_team_code[f]

                    sum_next = sum(
                        self.x[(f,d_next,self.work_blocks.index(a),tc)]
                        for tc in team_codes
                    )

                    sum_today = sum(
                        self.x[(f,d_today,self.work_blocks.index(b),tc)]
                        for b in Ba
                        for tc in team_codes
                    )

                    self.model.Add(
                        sum_today + sum_next <= 1,
                    )
                        
        print("[COP2_Half_Intervals] Model built successfully")



    def solve(self, time_limit_sec=60):
        solver = cp_model.CpSolver()

        solver.parameters.max_time_in_seconds = self.maxTime_sec if self.maxTime_sec is not None else 28800
        solver.parameters.num_search_workers = 8 # Number of parallel workers (Threads)
        solver.parameters.log_search_progress = False  # Enable detailed logging
        solver.parameters.relative_gap_limit = 0.01
        solver.parameters.absolute_gap_limit = 0
        
        self.solver = solver
        
        print(f"[COP2_Half_Intervals] Solver parameters:")
        print(f"  max_time_in_seconds: {solver.parameters.max_time_in_seconds}")
        print(f"  num_search_workers: {solver.parameters.num_search_workers}")
        print(f"  log_search_progress: {solver.parameters.log_search_progress}")
        print(f"  relative_gap_limit: {solver.parameters.relative_gap_limit * 100:.1f}%")
        print(f"  absolute_gap_limit: {solver.parameters.absolute_gap_limit}")
        
        print(f"\n[COP2_Half_Intervals] Starting solver.Solve()...")
        print(f"  Model has {len(self.model.Proto().variables)} variables")
        print(f"  Model has {len(self.model.Proto().constraints)} constraints")
        
        result = solver.Solve(self.model)
        
        status = solver.StatusName(result)
        print(f"\n[COP2_Half_Intervals] Solver finished!")
        print(f"  Status: {status}")
        print(f"  Wall time: {solver.WallTime():.2f}s")
        print(f"  Branches: {solver.NumBranches()}")
        print(f"  Conflicts: {solver.NumConflicts()}")
        print(f"  Best objective bound: {solver.BestObjectiveBound()}")
        if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print(f"  Objective value: {solver.ObjectiveValue()}")
        
        # extract if optimal or feasible
        self.assignment = defaultdict(list)  # emp_id (1-based) -> list of (day_idx+1, block_idx, team_id)
        if result in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            print("\n[COP2_Half_Intervals] Extracting solution...")
            for i in self.employees:
                emp_id = i + 1
                for d_idx in range(self.num_days):
                    d = self.dates[d_idx]
                    chosen_block = None
                    chosen_team = None
                    for b in range(len(self.work_blocks)):
                        for tc in self.emp_team_code[i]:
                            var = self.x[(i, d, b, tc)]
                            if solver.Value(var) == 1:
                                chosen_block = b
                                chosen_team = tc
                                break
                        if chosen_block is not None:
                            break
                    if chosen_block is not None:
                        team_id = get_team_id(str(chosen_team))
                        self.assignment[emp_id].append((d_idx + 1, chosen_block, team_id))
            print(f"[COP2_Half_Intervals] Extracted assignments for {len(self.assignment)} employees")
        else:
            print("\n[COP2_Half_Intervals] ⚠️ No feasible solution found.")
            print("  This could mean:")
            print("    - Constraints are too restrictive (INFEASIBLE)")
            print("    - Time limit reached before finding solution (UNKNOWN)")
            print("    - Model has errors (MODEL_INVALID)")

        return result


    def export_csv(self, filename="hourly_strict_schedule.csv"):
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
        print(f"[COP2_Half_Intervals] Schedule exported to {filename}")
    
    def to_table(self):
        rows = []
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows.append(header)
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


def solve(vacations=None, minimuns=None, employees=None, maxTime=None, year=2021, hours=13, work_blocks=None, rules=None, **kwargs):
    print(f"\n{'='*80}")
    print(f"[COP2_Half_Intervals] HOURLY SCHEDULER - CONSTRAINT PROGRAMMING (CP-SAT)")
    print(f"{'='*80}")
    print(f"[COP2_Half_Intervals] Parameters:")
    print(f"  Employees: {len(employees) if employees else 0}")
    print(f"  Vacations: {len(vacations) if vacations else 0} rows")
    print(f"  Minimums: {len(minimuns) if minimuns else 0} rows")
    print(f"  Max time: {maxTime} minutes (type: {type(maxTime).__name__})" if maxTime else "  Max time: default (8 hours)")
    print(f"  Year: {year}")
    print(f"  Store hours: {hours}")
    
    print("\n[COP2_Half_Intervals] Building model...")
    sched = CPHourScheduler(
        vacations_rows=vacations,
        minimums_rows=minimuns,
        employees=employees,
        work_blocks=work_blocks,
        maxTime=maxTime,
        year=year
    )
    sched.build_model()
    print(f"  Model built successfully!")
    
    print(f"\n[COP2_Half_Intervals] Solving...")
    status = sched.solve()
    
    print(f"\n[COP2_Half_Intervals] Exporting schedule...")
    sched.export_csv("hourly_strict_schedule.csv")
    
    print(f"{'='*80}")
    print(f"[COP2_Half_Intervals] COMPLETE")
    print(f"{'='*80}\n")
    
    return sched.to_table()

