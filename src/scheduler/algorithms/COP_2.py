# CSP_H.py
"""
CSP/CP-SAT Scheduler (horário por horas) - Tradução do ILP para OR-Tools CP-SAT.

Como usar:
  - Fornece:
      vacations_rows: lista de rows (formato utils.rows_to_vac_dict)
      minimums_rows: lista de rows (formato utils.rows_to_req_dicts)
      employees: lista de dicts { "id": ..., "teams": ["A", "B"] } ou similar (veja ILP_H.py)
      max_time_seconds: tempo máximo para o solver (int)
  - Chama solve(...)

Dependências:
  - ortools (pip install ortools)
  - pandas, numpy (opcional, igual ao ILP)
  - utils.py (fornecido pelo utilizador)
"""
from ortools.sat.python import cp_model
from collections import defaultdict
import datetime
import math

# Import utilities from your project (as in ILP_H.py / utils.py)
from algorithms.utils import (
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_CODE_TO_ID,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
)
# Referência: funções/estrutura em utils.py e ILP_H.py. :contentReference[oaicite:2]{index=2} :contentReference[oaicite:3]{index=3}

class HourlyCPScheduler:
    def __init__(self, vacations_rows, minimums_rows, employees, max_time_seconds=120,
                 year=2021, store_hours=13, work_blocks=None):
        # Calendar: usa calendário idêntico ao ILP (podes ajustar a data)
        # No ILP original as datas foram 2021-11-01 ... 2022-10-31 — aqui usamos o mesmo range por defeito
        self.dates = __import__("pandas").date_range(start="2021-11-01", end="2022-10-31").to_list()
        self.num_days = len(self.dates)

        # Employees (internally index from 0)
        self.emp_objects = employees
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)

        # Store hours (9..21 correspondem a intervalos 09-10 ... 21-22)
        self.hours = list(range(9, 22))  # 9..21 inclusive

        # Work blocks (list of tuples (start, break_start, end))
        if work_blocks is None:
            # copiado do ILP_H.py
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

        # Employee teams: extrai códigos tal como no ILP
        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            if not teams:
                codes = ("A",)
            else:
                codes = tuple(get_team_code(team) for team in teams)
            self.emp_team_code[idx] = codes
            # garante id de equipa
            for c in codes:
                get_team_id(c)

        # Build membership: teams -> set(employees)
        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        # Vacations: usa rows_to_vac_dict (formato id 1-based)
        vacs = rows_to_vac_dict(vacations_rows)
        # converte para conjuntos de timestamps
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs.get(e_idx + 1, [])
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        # Minimums: usa rows_to_req_dicts (retorna keys (day, hour_or_shift, team_id))
        mins, ideals = rows_to_req_dicts(minimums_rows)
        # Converter para formato (date, hour_label, team_code) -> int
        self.minimos = {}
        for (day, hour_label, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, hour_label, team_code)] = int(val)

        # closed days (mínimo == -1)
        self.closed_days = {d for (d, h, t), v in self.minimos.items() if v == -1}

        # solver params
        self.max_time_seconds = max_time_seconds

        # model placeholders
        self.model = cp_model.CpModel()
        self.solver = None

        # variable containers
        # x[(f,d_idx,b,team_code)] -> Bool
        # y[(d_idx,h,team_code)] -> Int (count)
        self.x = {}
        self.y = {}
        self.shortage = {}

        # helper: precompute working hours per block (set of ints)
        self.block_hours = [self._get_working_hours(b) for b in self.work_blocks]

    def _get_working_hours(self, block):
        start, break_start, end = block
        hours = set(range(start, break_start))  # first span
        hours |= set(range(break_start + 1, end))  # second span (skip break hour)
        return hours

    def _validate_block_transition(self, block_today, block_tomorrow):
        end_today = block_today[2]
        start_tomorrow = block_tomorrow[0]
        rest_hours = (24 - end_today) + start_tomorrow
        return rest_hours >= 12

    def build_model(self):
        model = self.model
        # Create variables
        # x[f,d,b,team_code]
        for f in self.employees:
            for d_idx, d in enumerate(self.dates):
                for b in range(self.num_blocks):
                    for tc in self.emp_team_code[f]:
                        name = f"x_f{f}_d{d_idx}_b{b}_t{tc}"
                        v = model.NewBoolVar(name)
                        self.x[(f, d_idx, b, tc)] = v

        # y[d_idx,h,team_code]  (number of employees working at hour h on day d in team)
        max_workers_upper = max(10, len(self.employees))  # upper bound guess
        for d_idx, d in enumerate(self.dates):
            for h in self.hours:
                for tc in self.teams.keys():
                    name = f"y_d{d_idx}_h{h}_t{tc}"
                    v = model.NewIntVar(0, max_workers_upper, name) # count variable, minimos atribuidos
                    self.y[(d_idx, h, tc)] = v

        # shortage variables for each (d,h,team) when minimo >= 0
        for d_idx, d in enumerate(self.dates):
            for h in self.hours:
                hora_str = f"{h:02d}-{h+1:02d}"
                for tc in self.teams.keys():
                    minimo = self.minimos.get((d, hora_str, tc), 0)
                    if minimo >= 0:
                        name = f"shortage_d{d_idx}_h{h}_t{tc}" # Para cada dia d, hora h, equipa tc, conta os minimos que faltam
                        s = model.NewIntVar(0, max(0, minimo + 30), name)
                        self.shortage[(d_idx, h, tc)] = (s, minimo) # (0, 9, 'A'): (IntVar_shortage_d0_h9_tA, 3)
                    # if minimo == -1 -> closed day (handled below)

        # Link y with x: y[d,h,team] == sum of employees assigned to any block whose working hours include h
        for d_idx, d in enumerate(self.dates):
            for h in self.hours:
                for tc, members in self.teams.items():
                    # sum over f in members, b where block covers hour h and team allowed for f
                    terms = []
                    for f in members:
                        # only blocks where employee f has team tc allowed (emp_team_code[f] contains tc)
                        if tc not in self.emp_team_code[f]:
                            continue
                        for b in range(self.num_blocks):
                            if h in self.block_hours[b]:
                                terms.append(self.x[(f, d_idx, b, tc)])
                    if terms:
                        model.Add(self.y[(d_idx, h, tc)] == sum(terms))
                    else:
                        # no possible worker -> y == 0
                        model.Add(self.y[(d_idx, h, tc)] == 0)

        # Shortage linking: shortage >= minimo - y
        for (d_idx, h, tc), (s, minimo) in self.shortage.items(): # self.shortage[(0, 9, 'A')] = (IntVar_shortage_d0_h9_tA, 3)
            # model: s >= minimo - y  -> s + y >= minimo
            model.Add(s + self.y[(d_idx, h, tc)] >= minimo)

        # CONSTRAINTS

        """
        sum_vars = [
            x[(5, 10, 0, 'A')],  # bloco 0, equipa A
            x[(5, 10, 1, 'A')],  # bloco 1, equipa A
            ...
            x[(5, 10, 14, 'A')], # bloco 14, equipa A
            x[(5, 10, 0, 'B')],  # bloco 0, equipa B
            x[(5, 10, 1, 'B')],  # bloco 1, equipa B
            ...
            x[(5, 10, 14, 'B')]  # bloco 14, equipa B
        ]

        model.Add(sum(sum_vars) <= 1)  # No máximo 1 pode ser True
        """

        # 1) One block per day OR vacation/off OR One team per day: sum_{b,tc} x[f,d,b,tc] <= 1, and if vacation day -> == 0
        for f in self.employees:
            for d_idx, d in enumerate(self.dates):
                sum_vars = []
                for b in range(self.num_blocks):
                    for tc in self.emp_team_code[f]:
                        sum_vars.append(self.x[(f, d_idx, b, tc)])
                if d in self.vacations_dates.get(f, set()):
                    # vacation: force all zero
                    for v in sum_vars:
                        model.Add(v == 0)
                else:
                    # at most 1 block
                    model.Add(sum(sum_vars) <= 1)

        # 3) Total working days = 223 in the year for each employee
        for f in self.employees:
            total_work = []
            for d_idx in range(self.num_days):
                for b in range(self.num_blocks):
                    for tc in self.emp_team_code[f]:
                        total_work.append(self.x[(f, d_idx, b, tc)])
            # equality to 223
            model.Add(sum(total_work) == 223)

        # 4) No work on closed days (-1)
        for f in self.employees:
            for d_idx, d in enumerate(self.dates):
                if d in self.closed_days:
                    # force all x for that day to 0
                    for b in range(self.num_blocks):
                        for tc in self.emp_team_code[f]:
                            model.Add(self.x[(f, d_idx, b, tc)] == 0)

        # 5) Max 5 consecutive working days (sliding window of 6 days)
        # For each employee and each window of 6 consecutive days: sum <= 5
        for f in self.employees:
            for start in range(0, self.num_days - 5):
                window_vars = []
                for d_idx in range(start, start + 6):
                    for b in range(self.num_blocks):
                        for tc in self.emp_team_code[f]:
                            window_vars.append(self.x[(f, d_idx, b, tc)])
                model.Add(sum(window_vars) <= 5)

        # 6) Valid transitions between consecutive days (12h rest minimum)
        # For each employee, for each consecutive day pair, for each pair of blocks (b_today, b_next)
        # if transition invalid -> x[f,d_today,b_today,tc] + x[f,d_next,b_next,tc] <= 1
        for f in self.employees:
            for d_idx in range(self.num_days - 1):
                for b_today in range(self.num_blocks):
                    for b_next in range(self.num_blocks):
                        # check for at least one team shared between day choices for which this matters
                        if not self._validate_block_transition(self.work_blocks[b_today], self.work_blocks[b_next]):
                            # for every team that employee may work in, prevent the pair
                            for tc in self.emp_team_code[f]:
                                model.Add(self.x[(f, d_idx, b_today, tc)] + self.x[(f, d_idx+1, b_next, tc)] <= 1)

        # OBJECTIVE: minimize weighted sum of shortages
        # Give a high weight to shortages (e.g. 100)
        # objective_terms = []
        # weight_shortage = 100
        # for (d_idx, h, tc), (s, minimo) in self.shortage.items():
        #     objective_terms.append(weight_shortage * s)
# 
        # # optional: punish using more employees than minimal? (not required, left out)
        # model.Minimize(sum(objective_terms))

        print("[CSP] Model built with variables and constraints.")

        # Save model
        self.model = model

    def solve(self):
        print("\n[CSP_Extra.solve()] Configuring solver...")
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = 8 # Number of parallel workers (Threads)
        solver.parameters.log_search_progress = True  # Enable detailed logging
        
        # Optimality gap: stop if within 5% of optimal
        # For minimization: stops when (upper_bound - lower_bound) / lower_bound <= 0.05
        solver.parameters.relative_gap_limit = 0.01
        # Absolute gap: stop if gap <= 10 (for coverage minimization)
        solver.parameters.absolute_gap_limit = 10.0
        
        self.solver = solver
        
        print(f"[CSP_Extra.solve()] Solver parameters:")
        print(f"  max_time_in_seconds: {solver.parameters.max_time_in_seconds}")
        print(f"  num_search_workers: {solver.parameters.num_search_workers}")
        print(f"  log_search_progress: {solver.parameters.log_search_progress}")
        print(f"  relative_gap_limit: {solver.parameters.relative_gap_limit * 100:.1f}%")
        print(f"  absolute_gap_limit: {solver.parameters.absolute_gap_limit}")
        
        print(f"\n[CSP_Extra.solve()] Starting solver.Solve()...")
        print(f"  Model has {len(self.model.Proto().variables)} variables")
        print(f"  Model has {len(self.model.Proto().constraints)} constraints")
        
        result = solver.Solve(self.model)
        
        status = solver.StatusName(result)
        print(f"\n[CSP_Extra.solve()] Solver finished!")
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
            print("\n[CSP_Extra.solve()] Extracting solution...")
            for f in self.employees:
                emp_id = f + 1
                for d_idx, d in enumerate(self.dates):
                    chosen_block = None
                    chosen_team = None
                    for b in range(self.num_blocks):
                        for tc in self.emp_team_code[f]:
                            var = self.x[(f, d_idx, b, tc)]
                            if solver.Value(var) == 1:
                                chosen_block = b
                                chosen_team = tc
                                break
                        if chosen_block is not None:
                            break
                    if chosen_block is not None:
                        team_id = get_team_id(str(chosen_team))
                        self.assignment[emp_id].append((d_idx + 1, chosen_block, team_id))
            print(f"[CSP_Extra.solve()] Extracted assignments for {len(self.assignment)} employees")
        else:
            print("\n[CSP_Extra.solve()] ⚠️ No feasible solution found.")
            print("  This could mean:")
            print("    - Constraints are too restrictive (INFEASIBLE)")
            print("    - Time limit reached before finding solution (UNKNOWN)")
            print("    - Model has errors (MODEL_INVALID)")

        # also compute shortages (optional)
        self.calculated_shortages = {}
        for (d_idx, h, tc), (svar, minimo) in self.shortage.items():
            sval = self.solver.Value(svar) if self.solver is not None else None
            self.calculated_shortages[(d_idx + 1, f"{h:02d}-{h+1:02d}", tc)] = sval

        return result

    def export_csv(self, filename="csp_hourly_schedule.csv"):
        # similar export as ILP export
        import csv
        header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(header)
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(self._vacs_1based().get(emp_id, []))
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
                w.writerow(row)
        print("[CSP] Schedule exported to", filename)

    def _vacs_1based(self):
        # helper to return vacations in 1-based day indices for export
        return {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

    def to_table(self):
        # returns rows as list of lists (same layout as ILP to_table)
        rows = []
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows.append(header)
        vacs_1b = self._vacs_1based()
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
    # Convert maxTime (minutes) to seconds for compatibility
    if maxTime is not None:
        # Ensure maxTime is numeric (handle string input)
        try:
            maxTime_num = float(maxTime)
            max_time_seconds = int(maxTime_num * 60)
        except (ValueError, TypeError):
            print(f"[CSP_Extra] Warning: Invalid maxTime '{maxTime}', using default 60 minutes")
            max_time_seconds = 3600
    else:
        max_time_seconds = 3600  # default 60 minutes if not provided
    
    print(f"\n{'='*80}")
    print(f"[CSP_Extra] HOURLY SCHEDULER - CPLEX CP OPTIMIZER")
    print(f"{'='*80}")
    print(f"[CSP_Extra] Parameters:")
    print(f"  Employees: {len(employees) if employees else 0}")
    print(f"  Vacations: {len(vacations) if vacations else 0} rows")
    print(f"  Minimums: {len(minimuns) if minimuns else 0} rows")
    print(f"  Max time: {max_time_seconds / 60:.1f} minutes ({max_time_seconds} seconds)")
    print(f"  Year: {year}")
    print(f"  Store hours: {hours}")
    
    sched = HourlyCPScheduler(
        vacations_rows=vacations,
        minimums_rows=minimuns,
        employees=employees,
        max_time_seconds=max_time_seconds,
        year=year,
        store_hours=hours,
        work_blocks=work_blocks
    )
    
    print("\n[CSP_Extra] Building model...")
    sched.build_model()
    print(f"  Constraints added: (model built)")
    
    print(f"\n[CSP_Extra] Solving (max {max_time_seconds}s)...")
    result = sched.solve()

    res = compute_lower_bound_and_report(sched, csv_filename="csp_hourly_lb_report.csv", verbose=True)

    print("Quality %:", res['quality_pct'])
    
    print(f"\n[CSP_Extra] Result: {result}")
    if result:
        print(f"  Solution found!")
    else:
        print(f"  No solution or timeout")
    
    print("\n[CSP_Extra] Exporting schedule...")
    sched.export_csv("csp_hourly_schedule.csv")
    
    print(f"{'='*80}")
    print(f"[CSP_Extra] COMPLETE")
    print(f"{'='*80}\n")
    
    return sched.to_table()
