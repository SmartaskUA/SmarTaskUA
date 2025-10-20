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

        # FIXED HERE
        # BEFORE (it was only mapping to one team (the first one))
        #self.emp_team_code = {}
        #for idx, emp in enumerate(employees):
        #    teams = emp.get("teams", [])
        #    code = get_team_code(teams[0]) if teams else "A"
        #    self.emp_team_code[idx] = code
        #    get_team_id(code)

        # AFTER EDIT: map to ALL declared teams (or "A" if none)
        self.emp_allowed_teams = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            codes = [get_team_code(t) for t in teams] 
            self.emp_allowed_teams[idx] = codes
            for c in codes:
                get_team_id(c)

        # Build team -> set(employees) for ALL present codes
        self.teams = {}
        for idx, codes in self.emp_allowed_teams.items():
            for code in codes:
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

        # Minimum + Ideal requirements
        mins, ideals = rows_to_req_dicts(minimuns_rows)

        # Convert both into (date, team_code, shift)
        self.minimos = {}
        self.ideais = {}
        for (day, shift, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, team_code, shift)] = int(val)

        for (day, shift, team_id), val in ideals.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.ideais[(date_key, team_code, shift)] = int(val)


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
                d: {
                    t: {
                        team: pulp.LpVariable(f"x_{f}_{d.strftime('%Y%m%d')}_{t}_{team}", cat="Binary")
                        for team in self.emp_allowed_teams[f]
                    }
                    for t in turnos  # 0=OFF + working shifts
                }
                for d in dias
            }
            for f in funcionarios
        }

        # --- Count vars per team/day/shift (covers all shifts present) ---
        # y vars
        self.y = {
            d: {s: {team_code: pulp.LpVariable(
                f"y_{d.strftime('%Y%m%d')}_{s}_{team_code}",
                lowBound=0, cat="Continuous")  # shortage variable
                for team_code in self.teams.keys()}
                for s in t_range}
            for d in dias
        }

        model = pulp.LpProblem("Escala_Trabalho_ILP", pulp.LpMinimize)
        
        # shortages + objective
        penalties = []
        for d in dias:
            for s in t_range:
                for team_code in self.teams.keys():
                    minimo = self.minimos.get((d, team_code, s), 0)
                    # link y to coverage shortfall
                    model += (
                        self.y[d][s][team_code] >= minimo - pulp.lpSum(
                            self.x[f][d][s][team_code]
                            for f in self.teams.get(team_code, set())
                            if team_code in self.x[f][d][s]
                        ),
                        f"shortage_{team_code}_{d.strftime('%Y%m%d')}_S{s}"
                    )
                    penalties.append(self.y[d][s][team_code])

        model += pulp.lpSum(penalties), "Minimize_shortage_below_minimos"



        # --- Constraints ---

        # one shift per day
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(self.x[f][d][t][team]
                            for t in turnos
                            for team in self.emp_allowed_teams[f]) == 1,
                    f"one_shift_per_day_f{f}_{d.strftime('%Y%m%d')}")


        for f in funcionarios:
            for d in dias:
                for t in t_range:
                    model += (
                        pulp.lpSum(self.x[f][d][t][team] for team in self.emp_allowed_teams[f]) <= 1,
                        f"one_team_per_shift_f{f}_{d.strftime('%Y%m%d')}_S{t}"
                    )

        # Total working days = 223 (count ALL working shifts, including Night)
        for f in funcionarios:
            model += (pulp.lpSum(self.x[f][d][s][team] for d in dias for s in t_range for team in self.emp_allowed_teams[f]) == 223,
                    f"total_working_days_f{f}")

        # Sundays+holidays <= 22 (count all shifts)
        for f in funcionarios:
            model += (pulp.lpSum(self.x[f][d][s][team] for d in self.sundays_holidays for s in t_range for team in self.emp_allowed_teams[f]) <= 22,
                    f"weekend_holiday_cap_f{f}")

        # No more than 5 consecutive working days (sliding window of 6) — count all shifts
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.x[f][d][s][team] for d in window for s in t_range for team in self.emp_allowed_teams[f]) <= 5,
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
                                pulp.lpSum(self.x[f][d_today][s_prev][team] for team in self.emp_allowed_teams[f]) +
                                pulp.lpSum(self.x[f][d_next][s_next][team] for team in self.emp_allowed_teams[f])
                                <= 1,
                                f"forbid_{s_prev}_to_{s_next}_f{f}_{d_today.strftime('%Y%m%d')}"
                            )


        # Vacations -> Off 
        for f_emp in funcionarios:
            for vac_day in self.vacations_dates[f_emp]:
                model += (
                    pulp.lpSum(self.x[f_emp][vac_day][0][team]
                            for team in self.emp_allowed_teams[f_emp]) == 1,
                    f"vacation_off_f{f_emp}_{vac_day.strftime('%Y%m%d')}"
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
        Supports multiple possible teams per employee.
        """
        if self.x is None:
            return

        for f in self.employees:
            emp_id = f + 1

            for day_idx, d in enumerate(self.dates, start=1):
                best_val = 0
                best_shift = None
                best_team = None

                # check all shifts and all allowed teams
                for t in range(1, self.shifts + 1):
                    for team_code in self.emp_allowed_teams[f]:
                        val = pulp.value(self.x[f][d][t][team_code]) or 0.0
                        if val > best_val:
                            best_val = val
                            best_shift = t
                            best_team = team_code

                # save assignment if worked
                if best_shift is not None and best_val > 0.5:
                    team_id = get_team_id(best_team)
                    self.assignment[emp_id].append((day_idx, best_shift, team_id))



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


def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2, rules=None):
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
