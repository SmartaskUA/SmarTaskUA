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
    export_schedule_to_csv,
    TEAM_CODE_TO_ID,      
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code       
)


class ILPScheduler:
    def __init__(self, vacations_rows, minimuns_rows, employees, maxTime, year=2025, shifts=2):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None

        # Calendar
        self.dates = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31").to_list()
        self.num_days = len(self.dates)
        self.dias_ano, _sundays = build_calendar(self.year)  # (not strictly needed here, but consistent)

        # Employees
        self.employees = list(range(len(employees)))  # indices 0..n-1
        self.num_employees = len(self.employees)

        # Number of shifts
        self.shifts = int(shifts)  

        # Normalize team of each employee: use the first team listed, map to A/B letter.
        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            code = get_team_code(teams[0]) if teams else "A"  # choose your own default
            self.emp_team_code[idx] = code
            # ensure an id exists for this code (creates if new)
            get_team_id(code)

        # Build team -> set(employees) for ALL present codes
        self.teams = {}
        for idx, code in self.emp_team_code.items():
            self.teams.setdefault(code, set()).add(idx)

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
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, team_code, shift)] = int(val)

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
        t_range = range(1, self.shifts + 1)        # working shifts
        turnos = range(0, self.shifts + 1)         # 0=off + working shifts

        # --- Decision variables ---
        self.x = {
            f: {
                d: {t: pulp.LpVariable(f"x_{f}_{d.strftime('%Y%m%d')}_{t}", cat="Binary")
                    for t in turnos}
                for d in dias
            } for f in funcionarios
        }

        # --- Count vars per team/day/shift (covers all shifts present) ---
        # y vars
        self.y = {
            d: {s: {team_code: pulp.LpVariable(f"y_{d.strftime('%Y%m%d')}_{s}_{team_code}",
                                            lowBound=0, cat="Integer")
                    for team_code in self.teams.keys()}
                for s in t_range}
            for d in dias
        }

        model = pulp.LpProblem("Escala_Trabalho_ILP", pulp.LpMinimize)

        # Link y with x per team
        for d in dias:
            for s in t_range:
                for team_code, members in self.teams.items():
                    model += (
                        self.y[d][s][team_code] == pulp.lpSum(self.x[f][d][s] for f in members),
                        f"count_{team_code}_{d.strftime('%Y%m%d')}_S{s}"
                    )

        # Penalize shortages against minimos
        penalties = []
        for d in dias:
            for s in t_range:
                for team_code in self.teams.keys():
                    minimo = self.minimos.get((d, team_code, s), 0)
                    penal = pulp.LpVariable(f"penal_{d.strftime('%Y%m%d')}_S{s}_{team_code}",
                                            lowBound=0, cat="Continuous")
                    model += (penal >= minimo - self.y[d][s][team_code],
                            f"shortage_{d.strftime('%Y%m%d')}_S{s}_{team_code}")
                    penalties.append(penal)

        model += pulp.lpSum(penalties), "Minimize_shortage_below_minimos"

        # --- Constraints ---

        # one shift per day
        for f in funcionarios:
            for d in dias:
                model += (pulp.lpSum(self.x[f][d][t] for t in turnos) == 1,
                        f"one_shift_per_day_f{f}_{d.strftime('%Y%m%d')}")

        # Total working days = 223 (count ALL working shifts, including Night)
        for f in funcionarios:
            model += (pulp.lpSum(self.x[f][d][s] for d in dias for s in t_range) == 223,
                    f"total_working_days_f{f}")

        # Sundays+holidays <= 22 (count all shifts)
        for f in funcionarios:
            model += (pulp.lpSum(self.x[f][d][s] for d in self.sundays_holidays for s in t_range) <= 22,
                    f"weekend_holiday_cap_f{f}")

        # No more than 5 consecutive working days (sliding window of 6) — count all shifts
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.x[f][d][s] for d in window for s in t_range) <= 5,
                    f"max_5_consecutive_f{f}_{dias[i].strftime('%Y%m%d')}"
                )

        # Next-day transition rules
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                for s_prev in range(1, self.shifts + 1):
                    for s_next in range(1, self.shifts + 1):
                        if s_next < s_prev:
                            model += (
                                self.x[f][d_today][s_prev] + self.x[f][d_next][s_next] <= 1,
                                f"forbid_{s_prev}_to_{s_next}_f{f}_{d_today.strftime('%Y%m%d')}"
                            )

        # Vacations -> Off  (moved OUTSIDE the loop above, and no shadowing)
        for f_emp in funcionarios:
            for vac_day in self.vacations_dates[f_emp]:
                model += (
                    self.x[f_emp][vac_day][0] == 1,
                    f"vacation_off_f{f_emp}_{vac_day.strftime('%Y%m%d')}"
                )


        # Global daily floor (keep if you want it):
        # (If you don't want a global floor, remove these 3 constraints.)
        for d in dias:
            model += (
                pulp.lpSum(self.x[f][d][s] for f in funcionarios for s in t_range) >= 2,
                f"min_total_{d.strftime('%Y%m%d')}"
            )
            if self.shifts == 2:
                # Legacy per-shift floors only for 2 shifts
                model += (pulp.lpSum(self.x[f][d][1] for f in funcionarios) >= 2,
                        f"min_morning_{d.strftime('%Y%m%d')}")
                model += (pulp.lpSum(self.x[f][d][2] for f in funcionarios) >= 2,
                        f"min_afternoon_{d.strftime('%Y%m%d')}")

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
            team_code = self.emp_team_code.get(f, "A")
            team_id = get_team_id(team_code)

            for day_idx, d in enumerate(self.dates, start=1):
                # consider OFF (0) + all working shifts [1..self.shifts]
                vals = [(t, pulp.value(self.x[f][d][t]) or 0.0)
                        for t in range(0, self.shifts + 1)]
                t_sel = max(vals, key=lambda kv: kv[1])[0]
                if 1 <= t_sel <= self.shifts:          # keep M/T/N
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
        header = ["funcionario"] + [f"Dia {i}" for i in range(1, self.num_days + 1)]
        rows = [header]
        label = {1: "M_", 2: "T_", 3: "N_"}
        for emp_id in [i + 1 for i in self.employees]:
            vac_days = set(self.vacs_1based.get(emp_id, []))
            day_to_st = {d: (s, t) for (d, s, t) in self.assignment.get(emp_id, [])}
            line = [str(emp_id)]
            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_st:
                    s, team_id = day_to_st[d]
                    line.append(label.get(s, "") + TEAM_ID_TO_CODE.get(team_id, "A"))
                else:
                    line.append("0")
            rows.append(line)
        return rows


def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2):
    ilp = ILPScheduler(
        vacations_rows=vacations,
        minimuns_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        shifts=shifts
    )
    ilp.build_model()
    ilp.solve(gap_rel=0.005)
    ilp.export_csv("calendario4.csv")
    return ilp.to_table()
