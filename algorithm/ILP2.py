"""
Phase 1 (ILPScheduler):
    → Minimizes shortages below the *minimum* required staffing per team/shift/day.

Phase 2 (ILPScheduler2):
    → Minimizes shortages below the *ideal* staffing (i.e., tries to fill optimally)
      while keeping ILP1’s minimal feasible shortages (y_opt).

Core binary variable:
    x_{i,d,t,e} = 1 if employee i works on day d, shift t, in team e; 0 otherwise.
"""

import csv
from collections import defaultdict
import numpy as np
import pandas as pd
import pulp  # Linear programming solver

# --- Utility imports (project specific) ---
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
    def __init__(self, vacations_rows, minimuns_rows, employees,
                 maxTime, year=2025, shifts=2, y_opt=None):

        super().__init__(vacations_rows, minimuns_rows, employees, maxTime, year, shifts)
        self.y_opt = y_opt  # From ILP1 – ensures we do not violate minimum feasibility

    # ---------------------------------------------------------------------
    # MODEL CREATION (ILP2)
    # ---------------------------------------------------------------------
    def build_model(self):
        funcionarios = self.employees
        dias = self.dates
        t_range = range(1, self.shifts + 1)   # 1..N → working shifts 
        turnos = range(0, self.shifts + 1)    # 0 = OFF + working shifts

        # Variables:
        # (9) Core variable
        # x_{i,d,t,e} = 1 if employee i works day d, shift t, in team e -> 0 otherwise
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

        # Shortage variables:
        # y[d][s][team] → shortage relative to minimum (represents the number of missing employees in day d, shift s, team)
        # z[d][s][team] → shortage relative to ideal (represents the number of missing employees in day d, shift s, team)

        # (10) Shortage relative to MINIMUM coverage
        # y[d][s][team] → shortage relative to minimum (0 if fully covered)
        self.y = {
            d: {s: {team: pulp.LpVariable(f"y_{d.strftime('%Y%m%d')}_{s}_{team}",
                                          lowBound=0, cat="Continuous")
                    for team in self.teams.keys()}
                for s in t_range}
            for d in dias
        }

        # (14) Shortage relative to IDEAL coverage
        # z[d][s][team] → shortage relative to ideal (0 if fully covered
        self.z = {
            d: {s: {team: pulp.LpVariable(f"z_{d.strftime('%Y%m%d')}_{s}_{team}",
                                          lowBound=0, cat="Continuous")
                    for team in self.teams.keys()}
                for s in t_range}
            for d in dias
        }

        model = pulp.LpProblem("Escala_Trabalho_ILP2", pulp.LpMinimize)

        # For each day, shift, and team:
        #   y[d][s][team] ≥ minimum_required - total_assigned_to_team
        #   z[d][s][team] ≥ ideal_required   - total_assigned_to_team

        # (8) RELATIONSHIP BETWEEN COVERAGE AND SHORTAGE
        for d in dias:
            for s in t_range:
                for team, members in self.teams.items():
                    minimo = self.minimos.get((d, team, s), 0)
                    model += (
                        self.y[d][s][team] >= minimo - pulp.lpSum(
                            self.x[f][d][s][team_code]
                            for f in self.teams.get(team, set())
                            for team_code in self.emp_allowed_teams[f]
                            if team_code == team
                        ),
                        f"min_shortage_{team}_{d.strftime('%Y%m%d')}_S{s}"
                    )

        # (13) Guarantee shortage relative to IDEAL coverage
        for d in dias:
            for s in t_range:
                for team, members in self.teams.items():
                    ideal = self.ideais.get((d, team, s), 0)
                    model += (
                        self.z[d][s][team] >= ideal - pulp.lpSum(
                            self.x[f][d][s][team_code]
                            for f in self.teams.get(team, set())
                            for team_code in self.emp_allowed_teams[f]
                            if team_code == team
                        ),
                        f"ideal_shortage_{team}_{d.strftime('%Y%m%d')}_S{s}"
                    )

        # (12) Keep total shortage relative to MINIMUM coverage (KEEP minimum y under ILP1’s optimum (y_opt))
        if self.y_opt is not None:
            model += (
                pulp.lpSum(self.y[d][s][team]
                           for d in dias for s in t_range for team in self.teams.keys())
                <= self.y_opt,
                "keep_y_optimum"
            )

        # OBJECTIVE FUNCTION
        # (11) Minimize total shortage below IDEAL coverage 
        model += pulp.lpSum(
            self.z[d][s][team] for d in dias for s in t_range for team in self.teams.keys()
        ), "Minimize_shortage_below_ideals"

        
        # RULES (same as ILP1)
        # Sum of all x(i,d,t,e) = 1  (either OFF or working) since t = 0 is OFF
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(self.x[f][d][t][team] for t in turnos for team in self.emp_allowed_teams[f]) == 1,
                    f"one_shift_per_day_f{f}_{d.strftime('%Y%m%d')}"
                )

        # (2) Disables working on vacation days and limits to 1 shift per day
        for f in funcionarios:
            for d in dias:
                is_vacation = 1 if d in self.vacations_dates[f] else 0
                model += (
                    pulp.lpSum(
                        self.x[f][d][t][team]
                        for t in t_range
                        for team in self.emp_allowed_teams[f]
                    ) <= 1 - is_vacation,
                    f"daily_assignment_limit_f{f}_{d.strftime('%Y%m%d')}"
                )

        # (3) Exactly 223 total working days (regulatory limit)
        for f in funcionarios:
            model += (
                pulp.lpSum(self.x[f][d][s][team]
                           for d in dias for s in t_range for team in self.emp_allowed_teams[f]) == 223,
                f"total_working_days_f{f}"
            )

        # (4) Max 22 Sundays/holidays worked
        for f in funcionarios:
            model += (
                pulp.lpSum(self.x[f][d][s][team]
                           for d in self.sundays_holidays
                           for s in t_range
                           for team in self.emp_allowed_teams[f]) <= 22,
                f"weekend_holiday_cap_f{f}"
            )

        # (5) No more than 5 consecutive working days
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.x[f][d][s][team]
                               for d in window for s in t_range for team in self.emp_allowed_teams[f]) <= 5,
                    f"max_5_consecutive_f{f}_{dias[i].strftime('%Y%m%d')}"
                )

        # (6) Forbid backward transitions (e.g., T→M)
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                for s_prev in range(1, self.shifts + 1):
                    for s_next in range(1, self.shifts + 1):
                        if s_next < s_prev:  # e.g. cannot go from Afternoon→Morning
                            model += (
                                pulp.lpSum(self.x[f][d_today][s_prev][team]
                                           for team in self.emp_allowed_teams[f]) +
                                pulp.lpSum(self.x[f][d_next][s_next][team]
                                           for team in self.emp_allowed_teams[f])
                                <= 1,
                                f"forbid_{s_prev}_to_{s_next}_f{f}_{d_today.strftime('%Y%m%d')}"
                            )

        # (7)Vacation days must be OFF
        for f_emp in funcionarios:
            for vac_day in self.vacations_dates[f_emp]:
                model += (
                    pulp.lpSum(self.x[f_emp][vac_day][0][team]
                               for team in self.emp_allowed_teams[f_emp]) == 1,
                    f"vacation_off_f{f_emp}_{vac_day.strftime('%Y%m%d')}"
                )

        self.model = model


# -------------------------------------------------------------------------
# Solve ILP1 + ILP2 sequentially
# -------------------------------------------------------------------------
def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2, rules=None):
    """
    Runs both ILP phases:
        1. ILP1: minimize shortages below MINIMUMS
        2. ILP2: minimize shortages below IDEALS (keeping ILP1’s minimum result)
    """

    # ------------------ Phase 1 ------------------
    ilp1 = ILPScheduler(vacations, minimuns, employees, maxTime, year, shifts)
    ilp1.build_model()
    ilp1.solve()

    # Compute y_OPT (total minimum shortage from ILP1)
    y_opt = pulp.value(pulp.lpSum(
        var for name, var in ilp1.model.variablesDict().items() if name.startswith("y_")
    ))

    # ------------------ Phase 2 ------------------
    ilp2 = ILPScheduler2(vacations, minimuns, employees, maxTime, year, shifts, y_opt=y_opt)
    ilp2.build_model()
    ilp2.solve()
    ilp2.export_csv("calendario_ilp2.csv")

    # Output as table for API/frontend
    return ilp2.to_table()
