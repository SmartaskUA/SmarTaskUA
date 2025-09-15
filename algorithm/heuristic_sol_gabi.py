import time
import csv
import io
import numpy as np
from collections import defaultdict

from algorithm.utils import (
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
)

class HeuristicSolGabi:

    def __init__(
        self,
        vacations_rows,
        minimuns_rows,
        employees,
        year=2025,
        nDias=365,
        nDiasTrabalho=223,
        nDiasTrabalhoFDS=22,
        nDiasSeguidos=5,
        nMinTrabs=2,
        nMaxFolga=142,
        feriados=None,
        shifts=2
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
        self.sundays_0based = np.array(sundays) - 1
        # Holidays: convert to 0-based day indices for array masking
        feriados = feriados or []
        self.feriados_0based = np.array([d - 1 for d in feriados if 1 <= d <= self.nDias], dtype=int)
        # Number of shifts (2 or 3)
        self.shifts = int(shifts)

        # Vacations: rows -> dict -> boolean matrix
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.nTrabs = len(employees)
        self.Ferias = self._vac_dict_to_matrix(vacs_dict, self.nTrabs, self.nDias)
        # Shift preferences (independent of team). Default: allow all available shifts.
        # Allowed teams per employee (list of team_ids) derived from labels using utils.
        self.Prefs = self._shift_prefs(employees)
        self.allowed_teams = self._allowed_teams(employees)

        # Read mins/ideals directly; keys: (day, shift, team_id)
        self.mins, self.ideals = rows_to_req_dicts(minimuns_rows)

        # schedule tensor: [emp, day, shift] with team_id or 0
        self.horario = np.zeros((self.nTrabs, self.nDias, 3), dtype=int)

        # Weekend mask (both Sat & Sun marked True)
        self.fds_mask = np.zeros((self.nTrabs, self.nDias), dtype=bool)
        self.fds_mask[:, self.sundays_0based] = True
        saturdays = np.array([i for i, d in enumerate(self.dias_ano) if d.weekday() == 5], dtype=int)
        self.fds_mask[:, saturdays] = True

        self.dias_nv = np.where(~self.Ferias)

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
                Prefs.append([0, 1, 2])
            elif hasA:
                Prefs.append([0, 2])
            elif hasB:
                Prefs.append([1, 2])
            else:
                raise ValueError(f"Empregado sem equipa A/B reconhecida: {emp}")
        return Prefs

    def _pick_team_for(self, emp_idx, dia_idx, turno_idx):
        candidates = self.allowed_teams[emp_idx]
        if not candidates:
            return None

        counts = defaultdict(int)
        for e in range(self.nTrabs):
            t = int(self.horario[e, dia_idx, turno_idx])
            if t > 0:
                counts[t] += 1

        day1 = dia_idx + 1
        shift1 = turno_idx + 1

        def score(team_id):
            req = int(self.mins.get((day1, shift1, team_id), 0))
            have = counts.get(team_id, 0)
            gap = max(req - have, 0)
            return (-gap, have)

        return sorted(candidates, key=score)[0]

    def atribuir_turnos_eficiente(self):
        nTrabs, nDias = self.nTrabs, self.nDias
        turnos_cobertura = np.zeros((nDias, 3), dtype=int)

        feriados_set = set(self.feriados_0based.tolist())
        weekends = set(np.where(self.fds_mask.any(axis=0))[0].tolist())
        dias_preferidos = [d for d in range(nDias) if (d not in feriados_set and d not in weekends)]

        for i in range(nTrabs):
            dias_disponiveis = np.where(~self.Ferias[i])[0]
            dias_normais = [d for d in dias_disponiveis if d in dias_preferidos]
            dias_eventuais = [d for d in dias_disponiveis if d not in dias_preferidos]

            turnos_assigned = 0

            for dia in sorted(dias_normais, key=lambda d: turnos_cobertura[d].sum()):
                if turnos_assigned >= self.nDiasTrabalho:
                    break
                turno = self._choose_turno(i, dia, turnos_cobertura)
                if turno is not None:
                    team_id = self._pick_team_for(i, dia, turno)
                    if team_id is not None:
                        self.horario[i, dia, turno] = team_id
                        turnos_assigned += 1
                        turnos_cobertura[dia, turno] += 1

            for dia in sorted(dias_eventuais, key=lambda d: turnos_cobertura[d].sum()):
                if turnos_assigned >= self.nDiasTrabalho:
                    break
                turno = self._choose_turno(i, dia, turnos_cobertura)
                if turno is not None:
                    team_id = self._pick_team_for(i, dia, turno)
                    if team_id is not None:
                        self.horario[i, dia, turno] = team_id
                        turnos_assigned += 1
                        turnos_cobertura[dia, turno] += 1

    def _choose_turno(self, i, dia, turnos_cobertura):
        poss = []
        prev = None
        if dia - 1 >= 0:
            if self.horario[i, dia - 1, 0] > 0: prev = 0
            elif self.horario[i, dia - 1, 1] > 0: prev = 1
            elif self.horario[i, dia - 1, 2] > 0: prev = 2
        nxt = None
        if dia + 1 < self.nDias:
            if self.horario[i, dia + 1, 0] > 0: nxt = 0
            elif self.horario[i, dia + 1, 1] > 0: nxt = 1
            elif self.horario[i, dia + 1, 2] > 0: nxt = 2

        for turno in self.Prefs[i]:
            if turno >= self.shifts:
                continue
            if (prev is None or turno >= prev) and (nxt is None or nxt >= turno):
                poss.append(turno)

        if not poss:
            return None
        return min(poss, key=lambda t: turnos_cobertura[dia, t])

    def _shift_prefs(self, employees):
        allowed = list(range(self.shifts))
        return [allowed[:] for _ in employees]

    def _allowed_teams(self, employees):
        allowed = []
        for emp in employees:
            codes = [get_team_code(t) for t in emp.get("teams", []) if t]
            ids = [get_team_id(c) for c in codes if c]
            if not ids:
                ids = [get_team_id("A")]
            allowed.append(ids)
        return allowed

    # ---------- criteria ----------

    def criterio1(self):
        """Excesso de dias seguidos acima do máximo."""
        f1 = np.zeros(self.nTrabs, dtype=int)
        for i in range(self.nTrabs):
            # FIX: self.horario[i] has shape (nDias, 3); sum over axis=1
            worked = ((self.horario[i] > 0).sum(axis=1) > 0).astype(int)
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
        mask = self.fds_mask.copy()
        if self.feriados_0based.size:
            mask[:, self.feriados_0based] = True
        worked = (self.horario.sum(axis=2) > 0)
        wkends_holidays = (worked & mask)
        dias_fds_por_trab = wkends_holidays.sum(axis=1)
        excesso = np.maximum(dias_fds_por_trab - self.nDiasTrabalhoFDS, 0)
        return excesso

    def criterio3(self):
        trabalhadores_por_dia = (self.horario > 0).sum(axis=2)
        dias_com_menos = np.sum(trabalhadores_por_dia < self.nMinTrabs, axis=1)
        return int(np.sum(dias_com_menos))

    def criterio4(self):
        dias_trab = []
        for i in range(self.nTrabs):
            worked_day = (self.horario[i] > 0).sum(axis=1) > 0
            worked_nonvac = np.sum(worked_day & ~self.Ferias[i])
            dias_trab.append(worked_nonvac)
        return np.abs(np.array(dias_trab) - self.nDiasTrabalho)

    def criterio5(self):
        f5 = np.zeros(self.nTrabs, dtype=int)
        for i in range(self.nTrabs):
            for d in range(self.nDias - 1):
                td = 0 if self.horario[i, d, 0] > 0 else (1 if self.horario[i, d, 1] > 0 else (2 if self.horario[i, d, 2] > 0 else -1))
                tn = 0 if self.horario[i, d + 1, 0] > 0 else (1 if self.horario[i, d + 1, 1] > 0 else (2 if self.horario[i, d + 1, 2] > 0 else -1))
                if td != -1 and tn != -1 and tn < td:
                    f5[i] += 1
        return f5

    def criterio6(self):
        counts = defaultdict(int)
        for e in range(self.nTrabs):
            for d in range(self.nDias):
                for s in range(self.shifts):
                    t = int(self.horario[e, d, s])
                    if t > 0:
                        counts[(d + 1, s + 1, t)] += 1

        viol = 0
        for (day, shift, team_id), req in self.mins.items():
            if 1 <= day <= self.nDias and 1 <= shift <= self.shifts:
                have = counts.get((day, shift, team_id), 0)
                if have < req:
                    viol += (req - have)
        return int(viol)

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
        start = time.time()
        f1o, f2o, f3o, f4o, f5o, f6o = self.calcular_criterios()
        iters = 0

        def peso(f1, f2, f3, f4, f5, f6):
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
            turno1, turno2 = np.random.choice(self.shifts, 2, replace=False)

            if self.horario[i, dia1, turno1] == self.horario[i, dia2, turno2]:
                continue

            hor = self.horario.copy()
            hor[i, dia1, turno1], hor[i, dia2, turno2] = hor[i, dia2, turno2], hor[i, dia1, turno1]

            old = self.horario
            self.horario = hor
            f1, f2, f3, f4, f5, f6 = self.calcular_criterios()
            cost = peso(f1, f2, f3, f4, f5, f6)
            if cost < best_cost:
                best_cost = cost
                f1o, f2o, f3o, f4o, f5o, f6o = f1, f2, f3, f4, f5, f6
            else:
                self.horario = old

        return {
            "time_sec": round(time.time() - start, 2),
            "iterations": iters,
            "score": best_cost,
            "f1": f1o, "f2": f2o, "f3": f3o, "f4": f4o, "f5": f5o, "f6": f6o
        }

    def _to_scheduler_like(self):
        employees = list(range(1, self.nTrabs + 1))
        vacs = {i + 1: (np.nonzero(self.Ferias[i])[0] + 1).tolist() for i in range(self.nTrabs)}

        assignment = defaultdict(list)
        for i in range(self.nTrabs):
            for d in range(self.nDias):
                for s in range(self.shifts):
                    t = int(self.horario[i, d, s])
                    if t > 0:
                        assignment[i + 1].append((d + 1, s + 1, t))

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
        """
        One row per employee; each cell "<Shift>_<TeamCode>", "F" for vacation, "0" if off.
        """
        header = ["funcionario"] + [f"Dia {d + 1}" for d in range(self.nDias)]
        rows = [header]
        label = {0: "M_", 1: "T_", 2: "N_"}
        for e in range(self.nTrabs):
            line = [f"Empregado{e + 1}"]
            for d in range(self.nDias):
                if self.Ferias[e, d]:
                    line.append("F")
                    continue
                cell = "0"
                for s in range(self.shifts):
                    team_id = int(self.horario[e, d, s])
                    if team_id > 0:
                        team_code = TEAM_ID_TO_CODE.get(team_id, str(team_id))
                        cell = f"{label.get(s, '')}{team_code}"
                        break
                line.append(cell)
            rows.append(line)
        return rows

def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2):
    scheduler = HeuristicSolGabi(
        vacations_rows=vacations,
        minimuns_rows=minimuns,
        employees=employees,
        year=year,
        feriados=[1, 108, 110, 115, 121, 161, 170, 227, 278, 305, 335, 342, 359],
        shifts=shifts
    )

    scheduler.atribuir_turnos_eficiente()
    scheduler.optimize(maxTime_sec=int(maxTime) * 60)

    scheduler.export_csv("calendario.csv")

    return scheduler.to_table()
