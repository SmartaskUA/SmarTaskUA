import csv
from collections import defaultdict

import numpy as np
import pandas as pd
import pulp

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

from algorithm.ILP import ILPScheduler

class ILPScheduler2(ILPScheduler):
    def __init__(self, vacations_rows, minimuns_rows, employees, maxTime, year=2025, shifts=2, y_opt=None):
        super().__init__(vacations_rows, minimuns_rows, employees, maxTime, year, shifts)
        self.y_opt = y_opt 


    def build_model(self):
        funcionarios = self.employees
        dias = self.dates
        t_range = range(1, self.shifts + 1)
        turnos = range(0, self.shifts + 1)
        

        # --- Decision variables ---
        self.x = {
            f: {
                d: {
                    t: {
                        team: pulp.LpVariable(f"x_{f}_{d.strftime('%Y%m%d')}_{t}_{team}", cat="Binary")
                        for team in self.emp_allowed_teams[f]
                    }
                    for t in turnos  
                }
                for d in dias
            }
            for f in funcionarios
        }

        # --- Shortages below minimum (y) and ideal (z) ---
        self.y = {
            d: {s: {team: pulp.LpVariable(f"y_{d.strftime('%Y%m%d')}_{s}_{team}", lowBound=0, cat="Continuous")
                    for team in self.teams.keys()}
                for s in t_range}
            for d in dias
        }
        self.z = {
            d: {s: {team: pulp.LpVariable(f"z_{d.strftime('%Y%m%d')}_{s}_{team}", lowBound=0, cat="Continuous")
                    for team in self.teams.keys()}
                for s in t_range}
            for d in dias
        }

        model = pulp.LpProblem("Escala_Trabalho_ILP2", pulp.LpMinimize)

        # === Shortage relationships ===
        # y >= theta - sum(x)
        for d in dias:
            for s in t_range:
                for team, members in self.teams.items():
                    minimo = self.minimos.get((d, team, s), 0)
                    model += (
                        self.y[d][s][team] >= minimo - pulp.lpSum( self.x[f][d][s][team_code] for f in self.teams.get(team, set()) for team_code in self.emp_allowed_teams[f] if team_code == team
                        ),
                        f"min_shortage_{team}_{d.strftime('%Y%m%d')}_S{s}"
                    )

        # z >= beta - sum(x)
        for d in dias:
            for s in t_range:
                for team, members in self.teams.items():
                    ideal = self.ideais.get((d, team, s), 0)
                    model += (self.z[d][s][team] >= ideal - pulp.lpSum(self.x[f][d][s][team_code] for f in self.teams.get(team, set()) for team_code in self.emp_allowed_teams[f] if team_code == team
                        ),
                        f"ideal_shortage_{team}_{d.strftime('%Y%m%d')}_S{s}"
                    )

        # Keep y within ILP1 optimum
        if self.y_opt is not None:
            model += (pulp.lpSum(self.y[d][s][team] for d in dias for s in t_range for team in self.teams.keys())
                      <= self.y_opt, "keep_y_optimum")

        # Objective: minimize sum of z shortages
        model += pulp.lpSum(self.z[d][s][team] for d in dias for s in t_range for team in self.teams.keys()), \
                 "Minimize_shortage_below_ideals"

        # === Common constraints (same as ILP1) ===

        # One shift per day
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum( self.x[f][d][t][team] for t in turnos for team in self.emp_allowed_teams[f] ) == 1,
                    f"one_shift_per_day_f{f}_{d.strftime('%Y%m%d')}"
                )

        # One team per shift
        for f in funcionarios:
            for d in dias:
                for t in t_range:
                    model += (
                        pulp.lpSum(self.x[f][d][t][team] for team in self.emp_allowed_teams[f]) <= 1,
                        f"one_team_per_shift_f{f}_{d.strftime('%Y%m%d')}_S{t}"
                    )

        # Exactly 223 working days per employee
        for f in funcionarios:
            model += (pulp.lpSum(self.x[f][d][s][team] for d in dias for s in t_range for team in self.emp_allowed_teams[f]) == 223,
                      f"total_working_days_f{f}")

        # ≤ 22 Sundays or holidays per employee
        for f in funcionarios:
            model += (pulp.lpSum(self.x[f][d][s][team] for d in self.sundays_holidays for s in t_range for team in self.emp_allowed_teams[f]) <= 22,
                      f"weekend_holiday_cap_f{f}")

        # No more than 5 consecutive working days in any 6-day window
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (pulp.lpSum(self.x[f][d][s][team] for d in window for s in t_range for team in self.emp_allowed_teams[f]) <= 5,
                          f"max_5_consecutive_f{f}_{dias[i].strftime('%Y%m%d')}")

        # Forbid backward transitions (e.g., T→M, N→M, N→T)
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
                    pulp.lpSum(self.x[f_emp][vac_day][0][team] for team in self.emp_allowed_teams[f_emp]) == 1,
                    f"vacation_off_f{f_emp}_{vac_day.strftime('%Y%m%d')}"
                )

        self.model = model

def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2, rules=None):

    # === ILP1: minimize shortage below minimums ===
    ilp1 = ILPScheduler(vacations, minimuns, employees, maxTime, year, shifts)
    ilp1.build_model()
    ilp1.solve()

    # Compute y_OPT from ILP1
    y_opt = pulp.value(pulp.lpSum(
        var for name, var in ilp1.model.variablesDict().items() if name.startswith("y_")
    ))

    # === ILP2: minimize shortage below ideals (keeping ILP1’s optimal y) ===
    ilp2 = ILPScheduler2(vacations, minimuns, employees, maxTime, year, shifts, y_opt=y_opt)
    ilp2.build_model()
    ilp2.solve()
    ilp2.export_csv("calendario_ilp2.csv")

    return ilp2.to_table()