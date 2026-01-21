# ILP3 – Scheduler por HORAS (intervalos de 1h)
# Segue rigorosamente o método do PDF (ILP1 + ILP2)
# Usa blocos horários (start, break, end) como enviados pelo utilizador

import csv
import pulp
import pandas as pd
from collections import defaultdict
from algorithms.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_code,
    get_team_id,
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
        self.dates = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31").to_list()
        self.num_days = len(self.dates)
        self.D = list(range(self.num_days))

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

        """
        self.T = {
            0: ("A",),        # Emp 0 só pode A
            1: ("A", "B"),    # Emp 1 pode A e B
            2: ("B",),        # Emp 2 só pode B
            3: ("C",),        # Emp 3 só pode C
        }
        """

        self.teams = sorted({t for ts in self.T.values() for t in ts})

        # ---------------- Blocos ----------------
        self.work_blocks = [
                (9, 13, 18), (9, 14, 18), (9, 15, 18),
                (10, 14, 19), (10, 15, 19), (10, 16, 19),
                (11, 15, 20), (11, 16, 20), (11, 17, 20),
                (12, 16, 21), (12, 17, 21), (12, 18, 21),
                (13, 17, 22), (13, 18, 22), (13, 19, 22),
            ]
        self.num_blocks = len(self.work_blocks)
        self.B = list(range(self.num_blocks))

        # ---------------- Horas (1h) ----------------
        self.hours = list(range(9, 9 + store_hours))  # ex: 9..21
        self.H = [f"{h:02d}-{h+1:02d}" for h in self.hours]

        # ---------------- Alpha[a,h] ----------------
        self.alpha = defaultdict(int)
        for a, (start, brk, end) in enumerate(self.work_blocks):
            for h in range(start, brk):
                self.alpha[(a, f"{h:02d}-{h+1:02d}")] = 1
            for h in range(brk + 1, end):
                self.alpha[(a, f"{h:02d}-{h+1:02d}")] = 1
        
        """
        {
          (0, "09-10"): 1,
          (0, "10-11"): 1,
          (0, "11-12"): 1,
          (0, "12-13"): 1,
          (0, "14-15"): 1,
          (0, "15-16"): 1,
          (0, "16-17"): 1,
          (0, "17-18"): 1,
          (1, "09-10"): 1,
          (1, "10-11"): 1,
          ...
        }
        """

        # ---------------- Férias ----------------
        vacs = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            i: {self.dates[d - 1] for d in vacs.get(i + 1, []) if 1 <= d <= self.num_days}
            for i in self.E
        }
        self.delta = {(i, d): 1 if self.dates[d] in self.vacations_dates[i] else 0
                      for i in self.E for d in self.D}
        
        """
        delta[(0, 0)] = 1   # emp 0 está de férias no dia 0 (2021‑01‑01)
        delta[(0, 1)] = 0   # emp 0 não está de férias no dia 1
        delta[(0, 2)] = 1   # emp 0 está de férias no dia 2

        delta[(1, 0)] = 0   # emp 1 não está de férias no dia 0
        delta[(1, 1)] = 1   # emp 1 está de férias no dia 1
        """

        # ---------------- Requisitos ----------------
        self.theta, self.beta = rows_to_req_dicts(minimums_rows)

        """
        theta = {
            (1, "09-10", team_id_A): 2,
            (2, "09-10", team_id_A): 3,
            (3, "09-10", team_id_A): 0,
            (1, "10-11", team_id_A): 1,
            (2, "10-11", team_id_A): 1,
            (3, "10-11", team_id_A): 1,
        }
        """

        self.model = None
        self.assignment = defaultdict(list)
        self.maxTime_sec = int(maxTime) * 60 if maxTime else None

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
                    pulp.lpSum(self.z[e][dd][b]
                               for dd in range(d, d + 6)
                               for b in self.B) <= 5
                )

        # (6) descanso mínimo de 12h entre dias consecutivos
        for e in self.E:
            for d in range(self.num_days - 1):
                for b in self.B:
                    end_today = self.work_blocks[b][2]
                    for a in self.B:
                        start_tomorrow = self.work_blocks[a][0]
                        rest_hours = (24 - end_today) + start_tomorrow
                        if rest_hours < 12:
                            model += self.z[e][d][b] + self.z[e][d + 1][a] <= 1

        # (8) definição de y (mínimos) + regra de OFF quando mínimo = -1
        # Se theta = -1 ⇒ loja fechada nessa hora/equipa ⇒ ninguém pode trabalhar
        for d in self.D:
            for h in self.H:
                for t in self.teams:
                    theta = self.theta.get((d + 1, h, get_team_id(t)), 0)
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
                    # if theta == -1:
                    #     model += self.y[d][h][e] == 0
                    # else:
                    #     model += (
                    #         self.y[d][h][e]
                    #         >= theta - pulp.lpSum(
                    #             self.alpha[(a, h)] * self.x[i][d][a][e]
                    #             for i in self.E for a in self.A
                    #         )
                    #     )

        self.model = model

    # =========================================================
    # SOLVE
    # =========================================================
    def solve(self, gap_rel=0.01):

        print(f"\n{'='*80}")
        print(f"[ILP_Extra] SOLVING ILP MODEL")
        print(f"{'='*80}")
        print(f"[ILP_Extra] Solver parameters:")
        print(f"  Gap relative: {gap_rel*100:.2f}%")
        print(f"  Variables: {self.model.numVariables()}")
        print(f"  Constraints: {self.model.numConstraints()}")
        print(f"\n[ILP_Extra] Starting solver (CBC)...")
        print(f"[ILP_Extra] Real-time progress will be shown below:")
        print(f"{'-'*80}")

        solver = pulp.PULP_CBC_CMD(
            msg=True,
            timeLimit=self.maxTime_sec,
            threads=8,
            gapRel=gap_rel
        )
        status = self.model.solve(solver)
        self._extract_assignments()
        return status

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
                        for tc in self.T[f]:
                            val_x = pulp.value(self.x[f][d_idx - 1][b].get(tc, 0))
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
 

# ┌─────────────────────────────────────────────────────────────┐
# │ x[i][d][a][e] = 1                                           │
# │ ↓                                                           │
# │ Empregado 7 trabalha dia 120, bloco (11,15,20), equipa B    │
# │                                                             │
# │ Implica automaticamente:                                    │
# │ z[7][120][6] = 1  (bloco 6 é (11,15,20))                    │
# │                                                             │
# │ Contribui para cobertura:                                   │
# │ covered[120]["11-12"]["B"] += 1                             │
# │ covered[120]["12-13"]["B"] += 1                             │
# │ covered[120]["13-14"]["B"] += 1                             │
# │ covered[120]["14-15"]["B"] += 1  (pausa 15-16)              │
# │ covered[120]["16-17"]["B"] += 1                             │
# │ covered[120]["17-18"]["B"] += 1                             │
# │ covered[120]["18-19"]["B"] += 1                             │
# │ covered[120]["19-20"]["B"] += 1                             │
# │                                                             │
# │ Se theta[120]["14-15"]["B"] = 3 e covered = 2:              │
# │ y[120]["14-15"]["B"] = 1  (falta 1 pessoa)                  │ 
# └─────────────────────────────────────────────────────────────┘