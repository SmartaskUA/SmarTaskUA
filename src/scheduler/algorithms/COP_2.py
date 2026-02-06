from collections import defaultdict
from ortools.sat.python import cp_model
import pandas as pd
import csv
from algorithms.utils import get_team_code, get_team_id, rows_to_req_dicts, rows_to_vac_dict, TEAM_ID_TO_CODE
        

class CPHourScheduler:
    def __init__(self, vacations, minimums, employees, work_blocks=None, maxTime=None, year=2021):
        self.vacations = vacations
        self.minimums = minimums
        self.employees = employees
        
        # Generate default work blocks if not provided
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
            
        self.year = year
        self.max_time_seconds = int(maxTime) * 60 if maxTime is not None else 3600

        self.model = cp_model.CpModel()

        self._prepare_data()
        self._define_vars()
        self._add_constraints()

    def _prepare_data(self):
        
        # Store get_team_id for later use
        self.get_team_id = get_team_id
        
        self.dates = pd.date_range(start=f"{self.year}-01-01", end=f"{self.year}-12-31").to_list()
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
        self.theta, self.beta = rows_to_req_dicts(self.minimums)

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

        # horas (ex. "09-10", "10-11", ...)
        self.hours = [f"{h:02d}-{h+1:02d}" for h in range(9, 22)]

        # alpha[a, h]
        from collections import defaultdict
        self.alpha = defaultdict(int)
        for a, (start, brk, end) in enumerate(self.work_blocks):
            for h in range(start, brk):
                self.alpha[(a, f"{h:02d}-{h+1:02d}")] = 1
            for h in range(brk+1, end):
                self.alpha[(a, f"{h:02d}-{h+1:02d}")] = 1

        self.incompatible_blocks = defaultdict(set)

        for a1, (s1, b1, e1) in enumerate(self.work_blocks):
            end1 = e1
            for a2, (s2, b2, e2) in enumerate(self.work_blocks):
                # descanso de 12h ENTRE DIAS
                # s2 + 24 < end1 + 12  <=>  s2 < end1 - 12
                if s2 < end1 - 12:
                    self.incompatible_blocks[a1].add(a2)
        
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
        
    def _validate_block_transition(self, block_today, block_tomorrow):
        """
        Check if transition from block_today to block_tomorrow is valid.
        Rules: Must have at least 12 hours rest between end and start.
        """
        end_today = block_today[2]  # End hour of today's block
        start_tomorrow = block_tomorrow[0]  # Start hour of tomorrow's block
        # Calculate rest hours (always overnight, so add 24 to tomorrow's start)
        rest_hours = (24 - end_today) + start_tomorrow
        # Must have at least 12 hours rest
        return rest_hours >= 12

    def _define_vars(self):
        # x[i,d,a,e] boolean
        self.x = {}
        for i in self.I:
            for d in range(self.num_days):
                for a in self.A:
                    for e in self.emp_teams[i]:
                        self.x[(i,d,a,e)] = self.model.NewBoolVar(f"x_{i}_{d}_{a}_{e}")

        self.y = {}
        for d in range(self.num_days):
            for h in self.hours:
                for e in self.all_teams:
                    self.y[(d,h,e)] = self.model.NewIntVar(
                        0, len(self.I), f"y_{d}_{h}_{e}"
                    )


    def _add_constraints(self):
        # 1. um bloco por dia
        # 1. um bloco por dia + definição correta de worked
        for i in self.I:
            for d in range(self.num_days):
                work_sum = sum(
                    self.x[(i, d, a, e)]
                    for a in self.A
                    for e in self.emp_teams[i]
                )
                self.model.Add(work_sum <= 1 - self.delta[(i,d)])

        # closed days quando minimo == -1
        closed_days = set()
        for d in range(self.num_days):
            for h in self.hours:
                for e in self.all_teams:
                    theta_val = self.theta.get((d+1, h, get_team_id(e)), 0)
                    if theta_val == -1:
                        closed_days.add(d)
        # 2. não trabalhar em férias / dias fechados
        self.model.Add(
            sum(
                self.x[(i,d,a,e)]
                for i in self.I
                for d in closed_days
                for a in self.A
                for e in self.emp_teams[i]
        ) == 0)

        # 4. 223 dias
        for i in self.I:
            self.model.Add(
                sum(
                    self.x[(i, d, a, e)]
                    for d in range(self.num_days)
                    for a in self.A
                    for e in self.emp_teams[i]
                ) == 223
            )

        # 5. max 5 consecutivos
        for i in self.I:
            for start in range(self.num_days - 5):
                window = range(start, start + 6)
                self.model.Add(
                    sum(
                        self.x[(i, d, a, e)]
                        for d in window
                        for a in self.A
                        for e in self.emp_teams[i]
                    ) <= 5
                )

        # 7. mínimos cobertura horária
        # 7. Mínimos com penalização
        for d in range(self.num_days):
            for h in self.hours:
                for e in self.all_teams:
                    theta_val = self.theta.get((d+1, h, get_team_id(e)), 0)

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


        # 6. Rest constraint (12h minimum between consecutive days)
        # Equação: sum_{b∈B_a} x + sum_{a∈A_r} x ≤ 1
        for f in self.I:
            for d_today in range(self.num_days - 1):
                d_next = d_today + 1
                
                # Construir conjuntos B_a (índices de blocos tardios) e A_r (índices de blocos cedo)
                B_a_indices = [self.work_blocks.index(b) for b in self.Br]
                A_r_indices = [self.work_blocks.index(a) for a in self.Ar]
                
                # Restrição agregada: soma de blocos tardios hoje + soma de blocos cedo amanhã ≤ 1
                self.model.Add(
                    sum(
                        self.x[(f, d_today, b_idx, tc)]
                        for b_idx in B_a_indices
                        for tc in self.emp_teams[f]
                    ) + 
                    sum(
                        self.x[(f, d_next, a_idx, tc)]
                        for a_idx in A_r_indices
                        for tc in self.emp_teams[f]
                    ) <= 1
                )

        # Poderia não usar um minimizador e tornar a regra hard porém assim evita infeasibilidades
        # Que por acaso dava para fazer
        # Função objetivo: minimizar somatório de y[d,h,e]
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
        solver.parameters.log_search_progress = True  # Enable detailed logging
        
        # Optimality gap: stop if within 5% of optimal
        # For minimization: stops when (upper_bound - lower_bound) / lower_bound <= 0.05
        solver.parameters.relative_gap_limit = 0.01
        # Absolute gap: stop if gap <= 10 (for coverage minimization)
        solver.parameters.absolute_gap_limit = 0
        
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
            print(f"[CSP_Extra.solve()] Extracted assignments for {len(self.assignment)} employees")
        else:
            print("\n[CSP_Extra.solve()] ⚠️ No feasible solution found.")
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
        print(f"[HourlyILPStrict] Schedule exported to {filename}")

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
    print(f"[CSP_2] HOURLY SCHEDULER - CONSTRAINT PROGRAMMING (CP-SAT)")
    print(f"{'='*80}")
    print(f"[CSP_2] Parameters:")
    print(f"  Employees: {len(employees) if employees else 0}")
    print(f"  Vacations: {len(vacations) if vacations else 0} rows")
    print(f"  Minimums: {len(minimuns) if minimuns else 0} rows")
    print(f"  Max time: {maxTime} minutes (type: {type(maxTime).__name__})" if maxTime else "  Max time: default (8 hours)")
    print(f"  Year: {year}")
    print(f"  Store hours: {hours}")
    
    print("\n[CSP_2] Building model...")
    sched = CPHourScheduler(
        vacations=vacations,
        minimums=minimuns,
        employees=employees,
        work_blocks=work_blocks,
        maxTime=maxTime,
        year=year
    )
    print(f"  Model built successfully!")
    
    print(f"\n[CSP_2] Solving...")
    status = sched.solve()
    
    print(f"\n[CSP_2] Exporting schedule...")
    sched.export_csv("hourly_strict_schedule.csv")
    
    print(f"{'='*80}")
    print(f"[CSP_2] COMPLETE")
    print(f"{'='*80}\n")
    
    return sched.to_table()

