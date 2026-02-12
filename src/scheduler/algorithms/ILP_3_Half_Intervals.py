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
    rows_to_req_dicts_Half_Hour,
    rows_to_req_dicts_FIXED
)



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
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)
        self.D = self.dates

        # ---------------- Empregados ----------------
        self.employees = list(range(len(employees)))
        self.E = self.employees

        # ---------------- Equipas ----------------
        self.T = {}
        for i, emp in enumerate(employees):
            teams = emp.get("teams", []) or ["A"]
            self.T[i] = tuple(get_team_code(t) for t in teams)
            for t in self.T[i]:
                get_team_id(t)
        self.teams = sorted({t for ts in self.T.values() for t in ts})

        # ---------------- Blocos ----------------
        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks
            
        self.num_blocks = len(self.work_blocks)
        self.B = list(range(self.num_blocks))

        # ---------------- Horas (intervalos de 0.5h) ----------------
        # Usar floats diretamente como chaves (evitar strings)
        self.H = [round(h, 1) for h in [
            9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5,
            13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5,
            17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5
        ]]

        # ---------------- Alpha[a,h] ----------------
        # alpha[(bloco, hora_float)] = 1 se o bloco cobre essa hora
        self.alpha = defaultdict(int)
        for a, (start, brk, end) in enumerate(self.work_blocks):
            # Horas antes da pausa
            h = start
            while h < brk:
                self.alpha[(a, round(h, 1))] = 1
                h = round(h + 0.5, 1)
            # Horas depois da pausa (pausa dura 1h)
            h = brk + 1
            while h < end:
                self.alpha[(a, round(h, 1))] = 1
                h = round(h + 0.5, 1)

        # Br Blocos que influenciam o dia seguinte
        self.Ar = self._Ar_Builder(self.work_blocks, rest_hours=12)
        print(f"Dictionary Ar de blocos dependentes para descanso de 12h: {self.Ar}")


        # Vacations
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) 
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        self.delta = {(i, d): 1 if d in self.vacations_dates[i] else 0
                      for i in self.E for d in self.dates}


        # ---------------- Requisitos ----------------
        # theta[(day_index, hour_float, team_code)] = mínimo de trabalhadores
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

        self.model = None
        self.assignment = defaultdict(list)
        self.maxTime_sec = int(maxTime) * 60 if maxTime else None

    
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
                    print(f"Adicionando bloco {b} em Ar pois e dependente de {a} com {rest_hours}h de descanso")
        return Ar

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

    
    # =========================================================
    # BUILD MODEL (ILP1 + ILP2)
    # =========================================================



    def build_model(self):
        model = pulp.LpProblem("ILP3_Hourly", pulp.LpMinimize)

        # Variáveis
        self.x = pulp.LpVariable.dicts(
            "x", (self.E, self.D, self.B, self.teams), cat="Binary"
        )
        self.z = pulp.LpVariable.dicts( # Simplifica restricoes que nao precisam de equipa.
            "z", (self.E, self.D, self.B), cat="Binary"
        )
        self.y = pulp.LpVariable.dicts(
            "y", (self.D, self.H, self.teams), lowBound=0, cat="Integer"
        )

        # ---------- Objetivo (ILP1: mínimos) ----------
        # Não exprime qualquer tipo de comparação
        # Minimiza a falta aos minimos 
        # Ex : 0 + 1 + 2 + 0 + 0 + 0 + 1 + 0 ... Tenta minimizar esta soma que exprime as violaçoes aos minimos
        model += pulp.lpSum(self.y[d][h][t] for d in self.D for h in self.H for t in self.teams)

        # ---------- Restrições ----------

        # (2) 1 bloco por dia ou férias
        for e in self.E:
            for d in self.D:
                model += (
                    pulp.lpSum(self.z[e][d][b] for b in self.B)
                    <= 1 - self.delta[(e, d)] # O numero de blocos disponivel e no maximo 1 ou entao 0 se estiver de ferias
                )

        # ligação z -> x
        for e in self.E:
            for d in self.D:
                for b in self.B:
                    model += (
                        pulp.lpSum(self.x[e][d][b][t] for t in self.T[e])
                        == self.z[e][d][b]
                    )

        # (3) equipas permitidas
        for e in self.E:
            for t in self.teams:
                if t not in self.T[e]:
                    for d in self.D:
                        for b in self.B:
                            model += self.x[e][d][b][t] == 0

        # Se empregado i não está autorizado para equipa e, então x[i][d][a][e] DEVE ser 0 para todos os dias e blocos.

        # (4) 223 dias de trabalho
        for e in self.E:
            model += pulp.lpSum(self.z[e][d][b] for d in self.D for b in self.B) == 223

        # (5) máximo 5 dias consecutivos
        for e in self.E:
            for d in range(self.num_days - 5):
                model += (
                    pulp.lpSum(self.z[e][self.D[dd]][b]
                               for dd in range(d, d + 6)
                               for b in self.B) <= 5
                )

        # (6) descanso mínimo de 12h entre dias consecutivos
        for e in self.E:
            for i in range(len(self.D) - 1):

                d_today = self.D[i]
                d_next = self.D[i + 1]

                for a, ba in self.Ar.items():  # a ∈ A_r e b ∈ B_a

                    Ba = set()
                    for b in ba:
                        Ba.add(b)

                    team_codes = self.T[e]

                    sum_next = pulp.lpSum(
                        self.x[e][d_next][self.work_blocks.index(a)][tc]
                        for tc in team_codes
                    )

                    sum_today = pulp.lpSum(
                        self.x[e][d_today][self.work_blocks.index(b)][tc]
                        for b in Ba
                        for tc in team_codes
                    )

                    model += (
                        sum_today + sum_next <= 1,
                        f"rest_12h_f{e}_{d_today.strftime('%Y%m%d')}_a{a}"
                    )
        
        

        # (8) definição de y (mínimos) + regra de OFF quando mínimo = -1
        # Se theta = -1 ⇒ loja fechada nessa hora/equipa ⇒ ninguém pode trabalhar
        for d in self.D:
            for h in self.H:
                for t in self.teams:
                    theta = self.minimos.get((d, h, t), 0)
                    # Total de trabalhadores para aquele dia hora e equipa
                    total_workers = pulp.lpSum(         
                        self.alpha[(b, h)] * self.x[e][d][b][t]
                        for e in self.E for b in self.B
                    )

                    if theta == -1:
                        # loja fechada → zero trabalhadores
                        model += total_workers == 0
                        model += self.y[d][h][t] == 0
                    else:
                        # violações aos mínimos
                        model += self.y[d][h][t] >= theta - total_workers
                
        self.model = model

    # =========================================================
    # SOLVE
    # =========================================================
    def solve(self, gap_rel=0.01, solver_name=''):
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
                    val_z = pulp.value(self.z[f][d][b])
                    if val_z is not None and val_z > 0.5:
                        chosen_b = b
                        for tc in self.T[f]:
                            val_x = pulp.value(self.x[f][d][b].get(tc, 0))
                            if val_x is not None and val_x > 0.5:
                                chosen_team = tc
                                break
                        break
                if chosen_b is not None:
                    team_id = get_team_id(str(chosen_team)) if chosen_team else get_team_id(self.T[f][0])
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
    sched.solve(gap_rel=0.01)
    sched.export_csv("hourly_strict_schedule.csv")

    print("=" * 80)
    print("[ILP_Extra] COMPLETE")
    print("=" * 80 + "\n")

    return sched.to_table()
