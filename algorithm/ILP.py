import csv
from collections import defaultdict

import numpy as np
import pandas as pd
import pulp
import holidays

from algorithm.utils import (
    build_calendar,
    rows_to_vac_dict,      
    rows_to_req_dicts,     
    export_schedule_to_csv 
)

TEAM_ID_TO_LETTER = {1: "A", 2: "B"}
LETTER_TO_TEAM_ID = {"A": 1, "B": 2}


def _last_letter_ab(s: str) -> str:
    """Extract final A/B letter from strings like 'Equipa A', 'Team_B', 'A', 'B'."""
    if not s:
        return ""
    return s.strip()[-1].upper()


class ILPScheduler:
    def __init__(self, vacations_rows, minimuns_rows, employees, maxTime, year=2025):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None

        # Calendar
        self.dates = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31").to_list()
        self.num_days = len(self.dates)
        self.dias_ano, _sundays = build_calendar(self.year)  # (not strictly needed here, but consistent)

        # Employees
        self.employees = list(range(len(employees)))  # indices 0..n-1
        self.num_employees = len(self.employees)

        # Normalize team of each employee: use the first team listed, map to A/B letter.
        self.emp_team_letter = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            if not teams:
                # default to A if missing, or raise—your original code warned only
                self.emp_team_letter[idx] = "A"
                continue
            self.emp_team_letter[idx] = _last_letter_ab(teams[0])

        # Build team -> set(employees) mapping, only for teams present
        self.teams = {}
        for idx, letter in self.emp_team_letter.items():
            if letter not in ("A", "B"):
                continue
            self.teams.setdefault(letter, set()).add(idx)

        # Holidays (PT) + Sundays
        feriados_pt = holidays.country_holidays("PT", years=[year])
        self.sundays_holidays = [
            d for d in self.dates if d.weekday() == 6 or d.date() in feriados_pt
        ]

        # Vacations: rows -> dict -> sets of pd.Timestamp
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        # Minimum requirements: normalize via utils
        mins, _ideals = rows_to_req_dicts(minimuns_rows)
        # Convert (day, shift, team_id) -> by (date, team_letter, shift)
        self.minimos = {}
        for (day, shift, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_letter = TEAM_ID_TO_LETTER.get(team_id)
                if team_letter:
                    self.minimos[(date_key, team_letter, shift)] = int(val)

        # ILP containers
        self.x = None
        self.y = None
        self.model = None
        self.status = None

        # Export-friendly attributes
        self.assignment = defaultdict(list)  # emp_id(1-based) -> list[(day, shift, team_id)]
        self.vacs_1based = {i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
                            for i in self.employees}

    # ------------ model building ------------

    def build_model(self):
        funcionarios = self.employees
        dias = self.dates
        turnos = [0, 1, 2]  # 0=off, 1=morning, 2=afternoon

        # Decision Vars
        self.x = {
            f: {
                d: {
                    t: pulp.LpVariable(f"x_{f}_{d.strftime('%Y%m%d')}_{t}", cat="Binary")
                    for t in turnos
                } for d in dias
            } for f in funcionarios
        }

        # Count Vars by day, shift, team letter
        self.y = {
            d: {
                t: {
                    team: pulp.LpVariable(f"y_{d.strftime('%Y%m%d')}_{t}_{team}", lowBound=0, cat="Integer")
                    for team in self.teams.keys()
                } for t in [1, 2]
            } for d in dias
        }

        model = pulp.LpProblem("Escala_Trabalho_ILP", pulp.LpMinimize)

        # Link y with x per team
        for d in dias:
            for t in [1, 2]:
                for team_letter, members in self.teams.items():
                    model += (
                        self.y[d][t][team_letter] == pulp.lpSum(self.x[f][d][t] for f in members),
                        f"count_{team_letter}_{d}_{t}"
                    )

        # Penalize shortages against minimos
        penalties = []
        for d in dias:
            for t in [1, 2]:
                for team_letter in self.teams.keys():
                    minimo = self.minimos.get((d, team_letter, t), 0)
                    penal = pulp.LpVariable(f"penal_{d.strftime('%Y%m%d')}_{t}_{team_letter}",
                                            lowBound=0, cat="Continuous")
                    model += penal >= minimo - self.y[d][t][team_letter], f"shortage_{d}_{t}_{team_letter}"
                    penalties.append(penal)

        # Objective: minimize sum of penalties
        model += pulp.lpSum(penalties), "Minimize_shortage_below_minimos"

        # --- Constraints ---

        # one shift per day
        for f in funcionarios:
            for d in dias:
                model += (pulp.lpSum(self.x[f][d][t] for t in turnos) == 1, f"one_shift_per_day_{f}_{d}")

        # total working days = 223
        for f in funcionarios:
            model += (
                pulp.lpSum(self.x[f][d][1] + self.x[f][d][2] for d in dias) == 223,
                f"total_working_days_{f}"
            )

        # Sundays + holidays <= 22
        for f in funcionarios:
            model += (
                pulp.lpSum(self.x[f][d][1] + self.x[f][d][2] for d in self.sundays_holidays) <= 22,
                f"weekend_holiday_cap_{f}"
            )

        # No more than 5 consecutive working days (sliding window of 6 days)
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.x[f][d][1] + self.x[f][d][2] for d in window) <= 5,
                    f"max_5_consecutive_{f}_{dias[i]}"
                )

        # Forbid working on T(d) -> M(d+1)
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d = dias[i]
                d_next = dias[i + 1]
                model += (self.x[f][d][2] + self.x[f][d_next][1] <= 1, f"forbid_T_to_M_{f}_{d}")

        # Vacations -> off
        for f in funcionarios:
            for d in self.vacations_dates[f]:
                model += (self.x[f][d][0] == 1, f"vacation_off_{f}_{d}")

        # Simple daily coverage floors (global, independent of teams)
        for d in dias:
            model += (
                pulp.lpSum(self.x[f][d][1] + self.x[f][d][2] for f in funcionarios) >= 2,
                f"min_total_{d}"
            )
            model += (
                pulp.lpSum(self.x[f][d][1] for f in funcionarios) >= 2,
                f"min_morning_{d}"
            )
            model += (
                pulp.lpSum(self.x[f][d][2] for f in funcionarios) >= 2,
                f"min_afternoon_{d}"
            )

        self.model = model

    # ------------ solve + extract ------------

    def solve(self, gap_rel=0.005):
        if self.model is None:
            self.build_model()

        solver = pulp.PULP_CBC_CMD(
            msg=True,
            timeLimit=(self.maxTime_sec if self.maxTime_sec is not None else 8 * 3600),
            gapRel=gap_rel,
        )
        self.status = self.model.solve(solver)
        # Build assignments for export
        self._extract_assignments()

    def _extract_assignments(self):
        """
        Fill self.assignment as: emp_id(1-based) -> [(day, shift, team_id)]
        Also keeps self.vacs_1based already prepared at __init__.
        """
        if self.x is None:
            return
        for f in self.employees:
            emp_id = f + 1
            team_letter = self.emp_team_letter.get(f, "A")
            team_id = LETTER_TO_TEAM_ID.get(team_letter, 1)

            for day_idx, d in enumerate(self.dates, start=1):
                # choose t with highest value (should be integral)
                vals = [(t, pulp.value(self.x[f][d][t]) or 0.0) for t in (0, 1, 2)]
                t_sel = max(vals, key=lambda kv: kv[1])[0]
                if t_sel in (1, 2):
                    self.assignment[emp_id].append((day_idx, t_sel, team_id))

    # ------------ export / table ------------

    def export_csv(self, filename="calendario4.csv"):
        class View: pass
        v = View()
        v.employees = [i + 1 for i in self.employees]
        v.vacs = self.vacs_1based
        v.assignment = self.assignment
        export_schedule_to_csv(v, filename=filename, num_days=self.num_days)

    def to_table(self):
        """
        Build header + rows (same shape as other modules) without re-reading from disk.
        """
        header = ["funcionario"] + [f"Dia {i}" for i in range(1, self.num_days + 1)]
        rows = [header]
        for emp_id in [i + 1 for i in self.employees]:
            vac_days = set(self.vacs_1based.get(emp_id, []))
            day_to_st = {d: (s, t) for (d, s, t) in self.assignment.get(emp_id, [])}
            line = [str(emp_id)]
            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_st:
                    s, team_id = day_to_st[d]
                    line.append(("M_" if s == 1 else "T_") + TEAM_ID_TO_LETTER.get(team_id, "A"))
                else:
                    line.append("0")
            rows.append(line)
        return rows

def solve(vacations, minimuns, employees, maxTime, year=2025):
    ilp = ILPScheduler(
        vacations_rows=vacations,
        minimuns_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
    )
    ilp.build_model()
    ilp.solve(gap_rel=0.005)
    ilp.export_csv("calendario4.csv")
    return ilp.to_table()
