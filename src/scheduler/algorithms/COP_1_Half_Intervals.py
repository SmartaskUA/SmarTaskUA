from collections import defaultdict
from ortools.sat.python import cp_model
import pandas as pd
import csv
from algorithms.utils import get_team_code, get_team_id, rows_to_req_dicts_FIXED, rows_to_vac_dict, TEAM_ID_TO_CODE
        

class CPHourScheduler:
    def __init__(self, vacations, minimums, employees, work_blocks=None, maxTime=None, year=2021):
        self.vacations = vacations
        self.minimums = minimums
        self.employees = employees
        
        # Generate default work blocks if not provided
        if work_blocks is None:
            self.work_blocks = [
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
        else:
            self.work_blocks = work_blocks
            
        self.year = year
        self.max_time_seconds = int(maxTime) * 60 if maxTime is not None else 3600

        self.model = cp_model.CpModel()

        self._prepare_data()
        self._define_vars()
        self._add_constraints()

    def _prepare_data(self):
        
        # Store get_team_id for later use
        self.get_team_id = get_team_id
        
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)
        self.I = list(range(len(self.employees)))
        self.A = list(range(len(self.work_blocks)))

        # equipas permitidas por empregado
        self.emp_teams = {}
        for i, emp in enumerate(self.employees):
            teams = emp.get("teams", []) or ["A"]
            self.emp_teams[i] = [get_team_code(t) for t in teams]
        
        # all_teams deve vir DEPOIS de emp_teams ser definido
        self.all_teams = sorted(
            {t for teams in self.emp_teams.values() for t in teams}
        )

        # mínimos (theta) e ideais (beta)
        mins, ideal = rows_to_req_dicts_FIXED(self.minimums)
        self.theta = {}
        self.beta = {}

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
                self.theta[(date_key, hour, team_code)] = int(val)

        # férias delta
        vacs = rows_to_vac_dict(self.vacations)
        self.delta = {
            (i, d): 1 if (d + 1) in vacs.get(i + 1, []) else 0
            for i in self.I for d in range(self.num_days)
        }
        
        # vacations_dates para compatibilidade com export
        self.vacations_dates = {
            i: {self.dates[day - 1] for day in vacs.get(i + 1, []) if 1 <= day <= self.num_days}
            for i in self.I
        }

        # horas (intervalos de 0.5h)
        self.hours = [round(h, 1) for h in [
            9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5,
            13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5,
            17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5
        ]]

        # alpha[a, h] - 1 se o bloco cobre essa hora (intervalos de 0.5h)
        from collections import defaultdict
        self.alpha = defaultdict(int)
        for a, (start, brk, end) in enumerate(self.work_blocks):
            # Horas antes da pausa
            h = start
            while h < brk:
                self.alpha[(a, round(h, 1))] = 1
                h = round(h + 0.5, 1)
            h = brk + 1
            while h < end:
                self.alpha[(a, round(h, 1))] = 1
                h = round(h + 0.5, 1)

        self.incompatible_blocks = defaultdict(set)

        for a1, (s1, b1, e1) in enumerate(self.work_blocks):
            end1 = e1
            for a2, (s2, b2, e2) in enumerate(self.work_blocks):
                if s2 < end1 - 12:
                    self.incompatible_blocks[a1].add(a2)
        
        self.Ar = self._Ar_Builder(self.work_blocks, rest_hours=12)

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
        for i in self.I:
            for d in range(self.num_days):
                for a in self.A:
                    for e in self.emp_teams[i]:
                        self.x[(i,d,a,e)] = self.model.NewBoolVar(f"x_{i}_{d}_{a}_{e}")

        # auxiliar: worked this day
        self.worked = {}
        for i in self.I:
            for d in range(self.num_days):
                self.worked[(i,d)] = self.model.NewBoolVar(f"worked_{i}_{d}")

        self.y = {}
        for d in range(self.num_days):
            for h in self.hours:
                for e in self.all_teams:
                    self.y[(d,h,e)] = self.model.NewIntVar(
                        0, len(self.I), f"y_{d}_{h}_{e}"
                    )


    def _add_constraints(self):

        # 1. um bloco por dia + definição correta de worked
        for i in self.I:
            for d in range(self.num_days):
                work_sum = sum(
                    self.x[(i, d, a, e)]
                    for a in self.A
                    for e in self.emp_teams[i]
                )
                self.model.Add(work_sum <= 1)
                self.model.Add(self.worked[(i, d)] == work_sum)


        # 2. não trabalhar em férias / dias fechados
        for i in self.I:
            for d in range(self.num_days):
                if self.delta[(i,d)] == 1:
                    self.model.Add(self.worked[(i,d)] == 0)

        # 4. 223 dias
        for i in self.I:
            self.model.Add(sum(self.worked[(i,d)] for d in range(self.num_days)) == 223)

        # 5. max 5 consecutivos
        for i in self.I:
            for start in range(self.num_days - 5):
                self.model.Add(
                    sum(self.worked[(i,d)] for d in range(start, start+6)) <= 5
                )

        # 7. Mínimos com penalização
        for d in range(self.num_days):
            for h in self.hours:
                for e in self.all_teams:
                    theta_val = self.theta.get((self.dates[d], h, e), 0)

                    # Quantos trabalham esta hora com esta equipa?
                    covered = sum(
                        self.x[(i,d,a,e)] * self.alpha[(a,h)]
                        for i in self.I if e in self.emp_teams[i]  # Filtro adicionado!
                        for a in self.A
                    )
                    """
                        Dia 1, Hora 09-10, Equipa A,
                        x[0, 1, bloco2, A] * alpha[bloco2, 09-10] = 1 se o empregado 0 trabalhar no bloco2 (09-14-18)
                    """

                    if theta_val == -1:
                        self.model.Add(covered == 0)
                        self.model.Add(self.y[(d,h,e)] == 0)
                    else:
                        self.model.Add(covered + self.y[(d,h,e)] >= theta_val)



        # (6) descanso mínimo de 12h entre dias consecutivos
        for e in self.I:
            for i in range(self.num_days - 1):
                d_today = i
                d_next = i + 1

                for a, ba in self.Ar.items():  # a ∈ A_r e b ∈ B_a

                    Ba = set()
                    for b in ba:
                        Ba.add(b)

                    team_codes = self.emp_teams[e]

                    sum_next = sum(
                        self.x[(e, d_next, self.work_blocks.index(a), tc)]
                        for tc in team_codes
                    )

                    sum_today = sum(
                        self.x[(e, d_today, self.work_blocks.index(b), tc)]
                        for b in Ba
                        for tc in team_codes
                    )

                    self.model.Add(
                        sum_today + sum_next <= 1
                    )

        # Solver procura o valor que minimiza esta função
        self.model.Minimize(
            sum(self.y[(d,h,e)]
                for d in range(self.num_days)
                for h in self.hours
                for e in self.all_teams)
        )



    def solve(self, time_limit_sec=60):
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = 8 # Number of parallel workers (Threads)
        solver.parameters.log_search_progress = False  # Enable detailed logging
        solver.parameters.relative_gap_limit = 0.01
        solver.parameters.absolute_gap_limit = 0
        
        self.solver = solver
        
        print(f"[COP1_Half_Intervals] Solver parameters:")
        print(f"  max_time_in_seconds: {solver.parameters.max_time_in_seconds}")
        print(f"  num_search_workers: {solver.parameters.num_search_workers}")
        print(f"  log_search_progress: {solver.parameters.log_search_progress}")
        print(f"  relative_gap_limit: {solver.parameters.relative_gap_limit * 100:.1f}%")
        print(f"  absolute_gap_limit: {solver.parameters.absolute_gap_limit}")
        
        print(f"\n[COP1_Half_Intervals] Starting solver.Solve()...")
        print(f"  Model has {len(self.model.Proto().variables)} variables")
        print(f"  Model has {len(self.model.Proto().constraints)} constraints")
        
        result = solver.Solve(self.model)
        
        status = solver.StatusName(result)
        print(f"\n[COP1_Half_Intervals] Solver finished!")
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
            print("\n[COP1_Half_Intervals] Extracting solution...")
            for i in self.I:
                emp_id = i + 1
                for d_idx in range(self.num_days):
                    chosen_block = None
                    chosen_team = None
                    for a in self.A:
                        for e in self.emp_teams[i]:
                            var = self.x[(i, d_idx, a, e)]
                            if solver.Value(var) == 1:
                                chosen_block = a
                                chosen_team = e
                                break
                        if chosen_block is not None:
                            break
                    if chosen_block is not None:
                        team_id = get_team_id(str(chosen_team))
                        self.assignment[emp_id].append((d_idx + 1, chosen_block, team_id))
            print(f"[COP1_Half_Intervals] Extracted assignments for {len(self.assignment)} employees")
        else:
            print("\n[COP1_Half_Intervals] ⚠️ No feasible solution found.")
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
            for emp_id in sorted([i + 1 for i in self.I]):
                vac_days = set(self.vacs_1based().get(emp_id, []))
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
        print(f"[COP1_Half_Intervals] Schedule exported to {filename}")

    def vacs_1based(self):
        return {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.I
        }
    
    def to_table(self):
        # returns rows as list of lists (same layout as ILP to_table)
        rows = []
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows.append(header)
        vacs_1b = self.vacs_1based()
        for emp_id in sorted([i + 1 for i in self.I]):
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
    print(f"[COP1_Half_Intervals] HOURLY SCHEDULER - CONSTRAINT PROGRAMMING (CP-SAT)")
    print(f"{'='*80}")
    print(f"[COP1_Half_Intervals] Parameters:")
    print(f"  Employees: {len(employees) if employees else 0}")
    print(f"  Vacations: {len(vacations) if vacations else 0} rows")
    print(f"  Minimums: {len(minimuns) if minimuns else 0} rows")
    print(f"  Max time: {maxTime} minutes (type: {type(maxTime).__name__})" if maxTime else "  Max time: default (8 hours)")
    print(f"  Year: {year}")
    print(f"  Store hours: {hours}")
    
    print("\n[COP1_Half_Intervals] Building model...")
    sched = CPHourScheduler(
        vacations=vacations,
        minimums=minimuns,
        employees=employees,
        work_blocks=work_blocks,
        maxTime=maxTime,
        year=year
    )
    print(f"  Model built successfully!")
    
    print(f"\n[COP1_Half_Intervals] Solving...")
    status = sched.solve()
    
    print(f"\n[COP1_Half_Intervals] Exporting schedule...")
    sched.export_csv("hourly_strict_schedule.csv")
    
    print(f"{'='*80}")
    print(f"[COP1_Half_Intervals] COMPLETE")
    print(f"{'='*80}\n")
    
    return sched.to_table()

