# algorithm/heuristic_sol_gabi.py

import time
import csv
import io
import numpy as np
from collections import defaultdict

from algorithm.utils import (
    build_calendar,
    rows_to_vac_dict,        # vacations rows -> {emp_id: [1-based days]}
    rows_to_req_dicts,       # minimuns rows -> mins/ideals dicts
    export_schedule_to_csv,  # exporter expects scheduler-like object
)

class HeuristicSol:

    def __init__(
        self,
        vacations_rows,  # CSV-style rows: ["Employee 1", "0","1",...]
        minimuns_rows,   # rows like ["Equipa A"|"Team_A", "Minimo", "M"|"T", d1, d2, ...]
        employees,       # [{'teams': ['Equipa A', 'Equipa B']}, ...] (A/B at the end is enough)
        year=2025,
        nDias=365,
        nDiasTrabalho=223,
        nDiasTrabalhoFDS=22,
        nDiasSeguidos=5,
        nMinTrabs=2,
        nMaxFolga=142,
        feriados=None     # list of day-of-year (1-based) ints
    ):
        self.year = year
        self.nDias = nDias
        self.nDiasTrabalho = nDiasTrabalho
        self.nDiasTrabalhoFDS = nDiasTrabalhoFDS
        self.nDiasSeguidos = nDiasSeguidos
        self.nMinTrabs = nMinTrabs
        self.nMaxFolga = nMaxFolga

        # Calendar (robust Sundays via utils)
        self.dias_ano, sundays = build_calendar(self.year)
        self.sundays_0based = np.array(sundays) - 1  # convert to 0-based indices

        # Holidays: convert to 0-based day indices for array masking
        feriados = feriados or []
        self.feriados_0based = np.array([d - 1 for d in feriados if 1 <= d <= self.nDias], dtype=int)

        # Vacations: rows -> dict -> boolean matrix
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.nTrabs = len(employees)
        self.Ferias = self._vac_dict_to_matrix(vacs_dict, self.nTrabs, self.nDias)

        # Preferences from teams (0 = morning -> "A"; 1 = afternoon -> "B")
        # We only need A/B membership; we infer by the last character of the team string.
        self.Prefs = self._gerar_preferencias_automatica(employees)

        # Minimum requirements by team/shift/day as four arrays (A_M, A_T, B_M, B_T)
        self.minA_M, self.minA_T, self.minB_M, self.minB_T, self.minA_N, self.minB_N = self._min_arrays_from_req_rows(minimuns_rows)
        # schedule tensor: [emp, day, shift], values 0/1/2
        self.horario = np.zeros((self.nTrabs, self.nDias, 3), dtype=int)

        # Weekend mask (both Sat & Sun marked True)
        self.fds_mask = np.zeros((self.nTrabs, self.nDias), dtype=bool)
        # Sunday indices from build_calendar
        self.fds_mask[:, self.sundays_0based] = True
        # Saturdays (weekday==5)
        saturdays = np.array([i for i, d in enumerate(self.dias_ano) if d.weekday() == 5], dtype=int)
        self.fds_mask[:, saturdays] = True

        # Convenience: (emp_idx array, day_idx array) for non-vacation days
        self.dias_nv = np.where(~self.Ferias)

    # ---------- adapters ----------

    @staticmethod
    def _vac_dict_to_matrix(vacs_dict, nTrabs, nDias):
        M = np.zeros((nTrabs, nDias), dtype=bool)
        for emp_id, days in vacs_dict.items():
            if 1 <= emp_id <= nTrabs:
                idx = np.array(days) - 1
                idx = idx[(idx >= 0) & (idx < nDias)]
                M[emp_id - 1, idx] = True
        return M

    @staticmethod
    def _emp_has_team(e, letter):
        # Accept "Equipa A", "Team_A", "A" ... only the last char matters
        return any(str(t).strip() and str(t).strip()[-1].upper() == letter for t in e.get("teams", []))

    def _gerar_preferencias_automatica(self, employees):
        Prefs = []
        for emp in employees:
            hasA = self._emp_has_team(emp, 'A')
            hasB = self._emp_has_team(emp, 'B')
            if hasA and hasB:
                Prefs.append([0, 1, 2])       # M, T, N
            elif hasA:
                Prefs.append([0, 2])          # M, N
            elif hasB:
                Prefs.append([1, 2])          # T, N
            else:
                raise ValueError(f"Empregado sem equipa A/B reconhecida: {emp}")
        return Prefs


    def _min_arrays_from_req_rows(self, minimuns_rows):
        mins, _ideals = rows_to_req_dicts(minimuns_rows)
        A_M = np.zeros(self.nDias, dtype=int)
        A_T = np.zeros(self.nDias, dtype=int)
        A_N = np.zeros(self.nDias, dtype=int)  
        B_M = np.zeros(self.nDias, dtype=int)
        B_T = np.zeros(self.nDias, dtype=int)
        B_N = np.zeros(self.nDias, dtype=int)  
        for (day, shift, team), val in mins.items():
            d = day - 1
            if d < 0 or d >= self.nDias:
                continue
            if team == 1 and shift == 1: A_M[d] = val
            elif team == 1 and shift == 2: A_T[d] = val
            elif team == 1 and shift == 3: A_N[d] = val 
            elif team == 2 and shift == 1: B_M[d] = val
            elif team == 2 and shift == 2: B_T[d] = val
            elif team == 2 and shift == 3: B_N[d] = val   
        return A_M, A_T, B_M, B_T, A_N, B_N


    # ---------- construction ----------

    def atribuir_turnos_eficiente(self):
        """
        Greedy fill respecting simple T->(next-day)M guard and trying to balance
        coverage per day/shift and avoid weekends/holidays when possible.
        """
        nTrabs, nDias = self.nTrabs, self.nDias
        turnos_cobertura = np.zeros((nDias, 3), dtype=int)

        # preferred work days (avoid weekends+holidays first)
        feriados_set = set(self.feriados_0based.tolist())
        weekends = set(np.where(self.fds_mask.any(axis=0))[0].tolist())
        dias_preferidos = [d for d in range(nDias) if (d not in feriados_set and d not in weekends)]

        for i in range(nTrabs):
            dias_disponiveis = np.where(~self.Ferias[i])[0]
            dias_normais = [d for d in dias_disponiveis if d in dias_preferidos]
            dias_eventuais = [d for d in dias_disponiveis if d not in dias_preferidos]

            turnos_assigned = 0

            # fill normal days first
            for dia in sorted(dias_normais, key=lambda d: turnos_cobertura[d].sum()):
                if turnos_assigned >= self.nDiasTrabalho:
                    break
                turno = self._choose_turno(i, dia, turnos_cobertura)
                if turno is not None:
                    self.horario[i, dia, turno] = 1
                    turnos_assigned += 1
                    turnos_cobertura[dia, turno] += 1

            # fallback: fill weekends/holidays if needed
            for dia in sorted(dias_eventuais, key=lambda d: turnos_cobertura[d].sum()):
                if turnos_assigned >= self.nDiasTrabalho:
                    break
                turno = self._choose_turno(i, dia, turnos_cobertura)
                if turno is not None:
                    self.horario[i, dia, turno] = 1
                    turnos_assigned += 1
                    turnos_cobertura[dia, turno] += 1

    def _choose_turno(self, i, dia, turnos_cobertura):
        poss = []
        # what was assigned yesterday/tomorrow (as shift index), or None
        prev = None
        if dia - 1 >= 0:
            if self.horario[i, dia - 1, 0] == 1: prev = 0
            elif self.horario[i, dia - 1, 1] == 1: prev = 1
            elif self.horario[i, dia - 1, 2] == 1: prev = 2
        nxt = None
        if dia + 1 < self.nDias:
            if self.horario[i, dia + 1, 0] == 1: nxt = 0
            elif self.horario[i, dia + 1, 1] == 1: nxt = 1
            elif self.horario[i, dia + 1, 2] == 1: nxt = 2

        for turno in self.Prefs[i]:  # turno in {0,1,2}
            if (prev is None or turno >= prev) and (nxt is None or nxt >= turno):
                poss.append(turno)

        if not poss:
            return None
        return min(poss, key=lambda t: turnos_cobertura[dia, t])

    # ---------- criteria ----------

    def criterio1(self):
        """Excesso de dias seguidos acima do máximo."""
        f1 = np.zeros(self.nTrabs, dtype=int)
        for i in range(self.nTrabs):
            worked = (self.horario[i].sum(axis=1) > 0).astype(int)
            run = 0
            for d in range(self.nDias):
                if worked[d]:
                    run += 1
                else:
                    if run > self.nDiasSeguidos:
                        f1[i] += (run - self.nDiasSeguidos)
                    run = 0
            if run > self.nDiasSeguidos:
                f1[i] += (run - self.nDiasSeguidos)
        return f1

    def criterio2(self):
        """Excesso de dias trabalhados em fins de semana/feriados acima do limite."""
        mask = self.fds_mask.copy()
        if self.feriados_0based.size:
            mask[:, self.feriados_0based] = True
        worked = (self.horario.sum(axis=2) > 0)
        wkends_holidays = (worked & mask)
        dias_fds_por_trab = wkends_holidays.sum(axis=1)
        excesso = np.maximum(dias_fds_por_trab - self.nDiasTrabalhoFDS, 0)
        return excesso

    def criterio3(self):
        """(Mantido) contagem de dias/turnos com menos que nMinTrabs por trabalhador."""
        trabalhadores_por_dia = np.sum(self.horario, axis=1)            # (nTrabs, nDias)
        dias_com_menos = np.sum(trabalhadores_por_dia < self.nMinTrabs, axis=1)
        return int(np.sum(dias_com_menos))

    def criterio4(self):
        """Diferença absoluta de dias trabalhados vs alvo (223), ignorando férias."""
        dias_trab = []
        for i in range(self.nTrabs):
            worked_day = (self.horario[i] > 0).sum(axis=1) > 0
            worked_nonvac = np.sum(worked_day & ~self.Ferias[i])
            dias_trab.append(worked_nonvac)
        return np.abs(np.array(dias_trab) - self.nDiasTrabalho)

    def criterio5(self):
        """Violação de ordem: turno(d+1) < turno(d)."""
        f5 = np.zeros(self.nTrabs, dtype=int)
        for i in range(self.nTrabs):
            for d in range(self.nDias - 1):
                td = 0 if self.horario[i, d, 0] == 1 else (1 if self.horario[i, d, 1] == 1 else (2 if self.horario[i, d, 2] == 1 else -1))
                tn = 0 if self.horario[i, d + 1, 0] == 1 else (1 if self.horario[i, d + 1, 1] == 1 else (2 if self.horario[i, d + 1, 2] == 1 else -1))
                if td != -1 and tn != -1 and tn < td:
                    f5[i] += 1
        return f5

    def criterio6(self):
        A_idx, B_idx, both_idx = self._indices_equipes()

        A_M_tot = np.sum(self.horario[A_idx + both_idx, :, 0], axis=0) if (A_idx or both_idx) else np.zeros(self.nDias, int)
        A_T_tot = np.sum(self.horario[A_idx + both_idx, :, 1], axis=0) if (A_idx or both_idx) else np.zeros(self.nDias, int)
        A_N_tot = np.sum(self.horario[A_idx + both_idx, :, 2], axis=0) if (A_idx or both_idx) else np.zeros(self.nDias, int)
        B_M_tot = np.sum(self.horario[B_idx + both_idx, :, 0], axis=0) if (B_idx or both_idx) else np.zeros(self.nDias, int)
        B_T_tot = np.sum(self.horario[B_idx + both_idx, :, 1], axis=0) if (B_idx or both_idx) else np.zeros(self.nDias, int)
        B_N_tot = np.sum(self.horario[B_idx + both_idx, :, 2], axis=0) if (B_idx or both_idx) else np.zeros(self.nDias, int)

        viol = 0
        viol += np.sum(np.maximum(self.minA_M - A_M_tot, 0))
        viol += np.sum(np.maximum(self.minA_T - A_T_tot, 0))
        viol += np.sum(np.maximum(self.minA_N - A_N_tot, 0))  
        viol += np.sum(np.maximum(self.minB_M - B_M_tot, 0))
        viol += np.sum(np.maximum(self.minB_T - B_T_tot, 0))
        viol += np.sum(np.maximum(self.minB_N - B_N_tot, 0))
        return int(viol)

    def _indices_equipes(self):
        A, B, both = [], [], []
        for i, pref in enumerate(self.Prefs):
            if 0 in pref and 1 in pref:
                both.append(i)
            elif 0 in pref:
                A.append(i)
            elif 1 in pref:
                B.append(i)
        return A, B, both

    def calcular_criterios(self):
        return (
            self.criterio1(),
            self.criterio2(),
            self.criterio3(),
            self.criterio4(),
            self.criterio5(),
            self.criterio6(),
        )

    # ---------- hill climbing ----------

    def optimize(self, maxTime_sec=600, max_iter=400_000):
        """
        Local search with a weighted objective over the 6 criteria.
        """
        start = time.time()
        f1o, f2o, f3o, f4o, f5o, f6o = self.calcular_criterios()
        iters = 0

        def peso(f1, f2, f3, f4, f5, f6):
            # keep your original weights
            return 2*np.sum(f1) + 3*np.sum(f2) + 2*f3 + 1*np.sum(f4) + 3*np.sum(f5) + 4*f6

        best_cost = peso(f1o, f2o, f3o, f4o, f5o, f6o)

        while iters < max_iter and best_cost > 0:
            if time.time() - start > maxTime_sec:
                print("Tempo máximo atingido, parando a otimização.")
                break

            iters += 1
            i = np.random.randint(self.nTrabs)
            mask = (self.dias_nv[0] == i)
            if np.sum(mask) < 2:
                continue

            cand_days = self.dias_nv[1][mask]
            dia1, dia2 = np.random.choice(cand_days, 2, replace=False)
            turno1, turno2 = np.random.choice(2, 2, replace=False)

            if self.horario[i, dia1, turno1] == self.horario[i, dia2, turno2]:
                continue

            hor = self.horario.copy()
            hor[i, dia1, turno1], hor[i, dia2, turno2] = hor[i, dia2, turno2], hor[i, dia1, turno1]

            # evaluate tentative
            old = self.horario
            self.horario = hor
            f1, f2, f3, f4, f5, f6 = self.calcular_criterios()
            cost = peso(f1, f2, f3, f4, f5, f6)
            if cost < best_cost:
                best_cost = cost
                f1o, f2o, f3o, f4o, f5o, f6o = f1, f2, f3, f4, f5, f6
            else:
                # revert
                self.horario = old

        return {
            "time_sec": round(time.time() - start, 2),
            "iterations": iters,
            "score": best_cost,
            "f1": f1o, "f2": f2o, "f3": f3o, "f4": f4o, "f5": f5o, "f6": f6o
        }

    # ---------- export via utils ----------

    def _infer_emp_team_letter(self, i):
        # morning-only -> 'A'; afternoon-only -> 'B'; both -> 'A' (arbitrary)
        pref = self.Prefs[i]
        if 0 in pref and 1 not in pref:
            return 'A'
        if 1 in pref and 0 not in pref:
            return 'B'
        return 'A'

    def _to_scheduler_like(self):
        """
        Build a minimal view with .employees, .vacs, .assignment for export_schedule_to_csv.
        team_id is inferred from preferences per employee for labeling only.
        """
        employees = list(range(1, self.nTrabs + 1))
        vacs = {i + 1: (np.nonzero(self.Ferias[i])[0] + 1).tolist() for i in range(self.nTrabs)}

        assignment = defaultdict(list)
        for i in range(self.nTrabs):
            team_letter = self._infer_emp_team_letter(i)
            team_id = 1 if team_letter == 'A' else 2
            for d in range(self.nDias):
                if self.horario[i, d, 0] == 1:
                    assignment[i + 1].append((d + 1, 1, team_id))
                if self.horario[i, d, 1] == 1:
                    assignment[i + 1].append((d + 1, 2, team_id))
                if self.horario[i, d, 2] == 1:                     
                    assignment[i + 1].append((d + 1, 3, team_id))

        class SchedView: pass
        sv = SchedView()
        sv.employees = employees
        sv.vacs = vacs
        sv.assignment = assignment
        return sv

    def export_csv(self, filename="calendario.csv"):
        sv = self._to_scheduler_like()
        export_schedule_to_csv(sv, filename=filename, num_days=self.nDias)

    def to_table(self):
        header = ["funcionario"] + [f"Dia {d+1}" for d in range(self.nDias)]
        rows = [header]
        for e in range(self.nTrabs):
            equipe = self._infer_emp_team_letter(e)
            line = [f"Empregado{e + 1}"]
            for d in range(self.nDias):
                if self.Ferias[e, d]:
                    line.append("F")
                elif self.horario[e, d, 0] == 1:
                    line.append(f"M_{equipe}")
                elif self.horario[e, d, 1] == 1:
                    line.append(f"T_{equipe}")
                elif self.horario[e, d, 2] == 1:                 
                    line.append(f"N_{equipe}")
                else:
                    line.append("0")
            rows.append(line)
        return rows


def solve(vacations, minimuns, employees, maxTime, year=2025):
    scheduler = HeuristicSolGabi(
        vacations_rows=vacations,
        minimuns_rows=minimuns,
        employees=employees,
        year=year,
        feriados=[1, 108, 110, 115, 121, 161, 170, 227, 278, 305, 335, 342, 359],
    )

    # Build + optimize (maxTime in minutes → seconds)
    scheduler.atribuir_turnos_eficiente()
    scheduler.optimize(maxTime_sec=int(maxTime) * 60)

    # Export CSV using utils
    scheduler.export_csv("calendario.csv")

    # Return the table (header + rows) like your previous function
    return scheduler.to_table()
