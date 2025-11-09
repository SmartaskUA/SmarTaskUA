"""
ILPSchedulerWeighted
------------------------------------------------------------
Unified ILP model that minimizes shortages below both
Minimum and Ideal staffing levels in a single optimization.

Core variable:
  x_{i,d,t,e} = 1 if employee i works on day d, shift t, in team e.

Objective:
  Minimize:
      w_min * Σ y[d,s,t] + w_ideal * Σ z[d,s,t]
  where:
      y[d,s,t] = shortage vs minimum
      z[d,s,t] = shortage vs ideal
------------------------------------------------------------
"""

import pulp
from algorithm.utils import (
    TEAM_ID_TO_CODE,
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    get_team_code,
    get_team_id
)


class ILPSchedulerWeighted:
    def __init__(self, vacations_rows, minimuns_rows, employees,
                 maxTime, year=2025, shifts=2, w_min=100, w_ideal=1):
        self.vacations_rows = vacations_rows
        self.minimuns_rows = minimuns_rows
        self.employees = employees
        self.maxTime = maxTime
        self.year = year
        self.shifts = shifts
        self.w_min = w_min
        self.w_ideal = w_ideal

        # === Preprocessing (same as ILP1) ===
        self.vacations_dates = rows_to_vac_dict(vacations_rows)
        self.minimos, self.ideais = rows_to_req_dicts(minimuns_rows)
        self.teams = self._build_teams(employees)
        self.emp_allowed_teams = self._build_emp_team_map(employees)
        self.dates, self.sundays_holidays = build_calendar(year)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _build_emp_team_map(self, employees):
        mapping = {}
        for i, e in enumerate(employees, start=1):
            codes = [get_team_code(t) for t in e.get("teams", []) if t]
            ids = [get_team_id(c) for c in codes if c]
            if not ids:
                ids = [get_team_id("A")]
            mapping[i] = ids
        return mapping

    def _build_teams(self, employees):
        """
        Build dictionary of teams: team_id → set of employee_ids
        """
        teams = {}
        for i, e in enumerate(employees, start=1):
            codes = [get_team_code(t) for t in e.get("teams", []) if t]
            ids = [get_team_id(c) for c in codes if c]
            if not ids:
                ids = [get_team_id("A")]
            for t in ids:
                teams.setdefault(t, set()).add(i)
        return teams

    # ------------------------------------------------------------
    # MODEL CREATION
    # ------------------------------------------------------------
    def build_model(self):
        funcionarios = self.employees
        dias = self.dates
        t_range = range(1, self.shifts + 1)
        turnos = range(0, self.shifts + 1)  # 0 = OFF

        model = pulp.LpProblem("Escala_Trabalho_WeightedILP", pulp.LpMinimize)

        # === Variables ===
        # Work assignment x_{i,d,t,e}
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

        # Shortage variables
        self.y = {  # shortage vs minimum
            d: {s: {team: pulp.LpVariable(f"y_{d.strftime('%Y%m%d')}_{s}_{team}", lowBound=0)
                    for team in self.teams}
                for s in t_range}
            for d in dias
        }

        self.z = {  # shortage vs ideal
            d: {s: {team: pulp.LpVariable(f"z_{d.strftime('%Y%m%d')}_{s}_{team}", lowBound=0)
                    for team in self.teams}
                for s in t_range}
            for d in dias
        }

        # === Coverage Constraints ===
        for d in dias:
            for s in t_range:
                for team, members in self.teams.items():
                    minimo = self.minimos.get((d, team, s), 0)
                    ideal = self.ideais.get((d, team, s), minimo + 1)

                    # Minimum coverage shortage
                    model += (
                        self.y[d][s][team] >= minimo - pulp.lpSum(
                            self.x[f][d][s][team_code]
                            for f in self.teams[team]
                            for team_code in self.emp_allowed_teams[f]
                            if team_code == team
                        )
                    )

                    # Ideal coverage shortage
                    model += (
                        self.z[d][s][team] >= ideal - pulp.lpSum(
                            self.x[f][d][s][team_code]
                            for f in self.teams[team]
                            for team_code in self.emp_allowed_teams[f]
                            if team_code == team
                        )
                    )

        # === Hard rules (same as ILP1) ===

        # 1️⃣ Each employee/day: exactly one status (OFF or one shift)
        for f in funcionarios:
            for d in dias:
                model += (
                    pulp.lpSum(self.x[f][d][t][team]
                               for t in turnos for team in self.emp_allowed_teams[f]) == 1
                )

        # 2️⃣ Vacations → must be OFF
        for f in funcionarios:
            for d in dias:
                if d in self.vacations_dates[f]:
                    model += (
                        pulp.lpSum(self.x[f][d][0][team]
                                   for team in self.emp_allowed_teams[f]) == 1
                    )
                    # no working shifts that day
                    model += (
                        pulp.lpSum(self.x[f][d][t][team]
                                   for t in t_range for team in self.emp_allowed_teams[f]) == 0
                    )

        # 3️⃣ Exactly 223 total working days
        for f in funcionarios:
            model += (
                pulp.lpSum(self.x[f][d][s][team]
                           for d in dias for s in t_range for team in self.emp_allowed_teams[f]) == 223
            )

        # 4️⃣ Max 22 Sundays/holidays
        for f in funcionarios:
            model += (
                pulp.lpSum(self.x[f][d][s][team]
                           for d in self.sundays_holidays
                           for s in t_range for team in self.emp_allowed_teams[f]) <= 22
            )

        # 5️⃣ No more than 5 consecutive working days
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(self.x[f][d][s][team]
                               for d in window for s in t_range for team in self.emp_allowed_teams[f]) <= 5
                )

        # 6️⃣ Forbid backward transitions (Afternoon → Morning)
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                for s_prev in range(1, self.shifts + 1):
                    for s_next in range(1, self.shifts + 1):
                        if s_next < s_prev:
                            model += (
                                pulp.lpSum(self.x[f][d_today][s_prev][team]
                                           for team in self.emp_allowed_teams[f]) +
                                pulp.lpSum(self.x[f][d_next][s_next][team]
                                           for team in self.emp_allowed_teams[f])
                                <= 1
                            )

        # === Objective: weighted combination ===
        w_min = self.w_min
        w_ideal = self.w_ideal
        model += (
            w_min * pulp.lpSum(self.y[d][s][team] for d in dias for s in t_range for team in self.teams)
            + w_ideal * pulp.lpSum(self.z[d][s][team] for d in dias for s in t_range for team in self.teams)
        )

        self.model = model

    # ------------------------------------------------------------
    # SOLVE
    # ------------------------------------------------------------
    def solve(self):
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=int(self.maxTime) * 60 if self.maxTime else None)
        self.model.solve(solver)
        print(f"✅ Solver status: {pulp.LpStatus[self.model.status]}")

    # ------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------
    def export_csv(self, filename="schedule_weighted.csv"):
        export_schedule_to_csv(self, filename)

    # ------------------------------------------------------------
    # Output formatting (optional)
    # ------------------------------------------------------------
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
    ilp = ILPSchedulerWeighted(vacations, minimuns, employees, maxTime, year, shifts,
                               w_min=100, w_ideal=1)
    ilp.build_model()
    ilp.solve(gap_rel=0.001)
    ilp.export_csv("schedule_weighted.csv")
    return ilp.to_table()
