"""
ILPSchedulerWeighted (ILPv3)
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
import io
import re
import os
import time
import tempfile
from collections import defaultdict
import holidays as hl

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
        """
        Weighted ILP scheduler.

        employees: list of employee dicts (with "teams" etc.).
        Internally we index employees as 1..N for this ILP.
        """
        # Original employee dicts
        self.employee_rows = employees

        # Internal employee IDs: 1..N
        self.employees = list(range(1, len(employees) + 1))

        self.vacations_rows = vacations_rows
        self.minimuns_rows = minimuns_rows
        self.maxTime = maxTime
        self.year = year
        self.shifts = shifts
        self.w_min = w_min
        self.w_ideal = w_ideal

        # === Preprocessing ===
        self.teams = self._build_teams(self.employee_rows)
        self.emp_allowed_teams = self._build_emp_team_map(self.employee_rows)
        self.dates, sundays_idx = build_calendar(year)
        self.num_days = len(self.dates)
        # convert sunday indices (1-based day numbers) to actual Timestamp objects
        sundays = {
            self.dates[idx - 1]
            for idx in sundays_idx
            if 1 <= idx <= len(self.dates)
        }

        # PT holidays
        pt_holidays = hl.country_holidays("PT", years=[year])
        holiday_dates = {
            d
            for d in self.dates
            if d.date() in pt_holidays
        }

        # Combined: Sundays + Holidays
        self.sundays_holidays = sorted(sundays | holiday_dates)

        raw_vacs = rows_to_vac_dict(vacations_rows)
        self.vacs_1based = {
            emp_id: sorted(raw_vacs.get(emp_id, []))
            for emp_id in self.employees
        }
        self.vacs = self.vacs_1based
        self.vacations_dates = {
            emp_id: {
                self.dates[day - 1]
                for day in raw_vacs.get(emp_id, [])
                if 1 <= day <= self.num_days
            }
            for emp_id in self.employees
        }

        mins_raw, ideals_raw = rows_to_req_dicts(minimuns_rows)
        self.minimos = {}
        self.ideais = {}
        for (day, shift, team_id), value in mins_raw.items():
            if 1 <= day <= self.num_days:
                self.minimos[(self.dates[day - 1], team_id, shift)] = int(value)
        for (day, shift, team_id), value in ideals_raw.items():
            if 1 <= day <= self.num_days:
                self.ideais[(self.dates[day - 1], team_id, shift)] = int(value)

        # Containers filled after solving
        self.assignment = defaultdict(list)

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _build_emp_team_map(self, employees):
        """
        Map employee_id (1..N) -> list of allowed team_ids.
        """
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
        Build dictionary of teams: team_id → set of employee_ids (1..N)
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
        funcionarios = self.employees          # 1..N
        dias = self.dates
        t_range = range(1, self.shifts + 1)   # working shifts
        turnos = range(0, self.shifts + 1)    # 0 = OFF + shifts

        model = pulp.LpProblem("Escala_Trabalho_WeightedILP", pulp.LpMinimize)

        # === Variables ===
        # Work assignment x_{i,d,t,e}
        self.x = {
            f: {
                d: {
                    t: {
                        team: pulp.LpVariable(
                            f"x_{f}_{d.strftime('%Y%m%d')}_{t}_{team}",
                            cat="Binary"
                        )
                        for team in self.emp_allowed_teams[f]
                    }
                    for t in turnos
                }
                for d in dias
            }
            for f in funcionarios
        }

        # Shortage vs minimum
        self.y = {
            d: {
                s: {
                    team: pulp.LpVariable(
                        f"y_{d.strftime('%Y%m%d')}_{s}_{team}", lowBound=0
                    )
                    for team in self.teams
                }
                for s in t_range
            }
            for d in dias
        }

        # Shortage vs ideal
        self.z = {
            d: {
                s: {
                    team: pulp.LpVariable(
                        f"z_{d.strftime('%Y%m%d')}_{s}_{team}", lowBound=0
                    )
                    for team in self.teams
                }
                for s in t_range
            }
            for d in dias
        }

        # === Coverage Constraints (minimo & ideal) ===
        for d in dias:
            d_str = d.strftime("%Y%m%d")
            for s in t_range:
                for team in self.teams.keys():
                    minimo = self.minimos.get((d, team, s), 0)
                    ideal = self.ideais.get((d, team, s), minimo + 1)

                    # Minimum coverage shortage
                    # IMPORTANT CHANGE: sum over all funcionarios, filter with emp_allowed_teams[f]
                    model += (
                        self.y[d][s][team] >= minimo - pulp.lpSum(
                            self.x[f][d][s][team]
                            for f in funcionarios
                            if team in self.emp_allowed_teams[f]
                        ),
                        f"min_shortage_{team}_{d_str}_S{s}"
                    )

                    # Ideal coverage shortage
                    model += (
                        self.z[d][s][team] >= ideal - pulp.lpSum(
                            self.x[f][d][s][team]
                            for f in funcionarios
                            if team in self.emp_allowed_teams[f]
                        ),
                        f"ideal_shortage_{team}_{d_str}_S{s}"
                    )

        # === Hard Rules ===

        # (1) Each employee/day: exactly one status (OFF or one shift)
        for f in funcionarios:
            for d in dias:
                d_str = d.strftime("%Y%m%d")
                model += (
                    pulp.lpSum(
                        self.x[f][d][t][team]
                        for t in turnos
                        for team in self.emp_allowed_teams[f]
                    ) == 1,
                    f"one_shift_per_day_f{f}_{d_str}"
                )

        # (2) Vacations → must be OFF (no working shifts that day)
        for f in funcionarios:
            for d in dias:
                if d in self.vacations_dates.get(f, set()):
                    d_str = d.strftime("%Y%m%d")
                    model += (
                        pulp.lpSum(
                            self.x[f][d][0][team]
                            for team in self.emp_allowed_teams[f]
                        ) == 1,
                        f"vacation_off_f{f}_{d_str}"
                    )
                    model +=(
                        pulp.lpSum(
                            self.x[f][d][t][team]
                            for t in t_range
                            for team in self.emp_allowed_teams[f]
                        ) == 0,
                        f"vacation_nowork_f{f}_{d_str}"
                    )

        # (3) Exactly 223 total working days
        for f in funcionarios:
            model += (
                pulp.lpSum(
                    self.x[f][d][s][team]
                    for d in dias
                    for s in t_range
                    for team in self.emp_allowed_teams[f]
                ) == 223,
                f"total_working_days_f{f}"
            )

        # (4) Max 22 Sundays/holidays worked
        for f in funcionarios:
            model += (
                pulp.lpSum(
                    self.x[f][d][s][team]
                    for d in self.sundays_holidays
                    for s in t_range
                    for team in self.emp_allowed_teams[f]
                ) <= 22,
                f"weekend_holiday_cap_f{f}"
            )

        # (5) No more than 5 consecutive working days
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                start_str = window[0].strftime("%Y%m%d")
                model += (
                    pulp.lpSum(
                        self.x[f][d][s][team]
                        for d in window
                        for s in t_range
                        for team in self.emp_allowed_teams[f]
                    ) <= 5,
                    f"max_5_consecutive_f{f}_{start_str}"
                )

        # (6) Forbid backward transitions (e.g., T→M)
        for f in funcionarios:
            for i in range(len(dias) - 1):
                d_today = dias[i]
                d_next = dias[i + 1]
                d_today_str = d_today.strftime("%Y%m%d")
                for s_prev in range(1, self.shifts + 1):
                    for s_next in range(1, self.shifts + 1):
                        if s_next < s_prev:
                            model += (
                                pulp.lpSum(
                                    self.x[f][d_today][s_prev][team]
                                    for team in self.emp_allowed_teams[f]
                                )
                                + pulp.lpSum(
                                    self.x[f][d_next][s_next][team]
                                    for team in self.emp_allowed_teams[f]
                                )
                                <= 1,
                                f"forbid_{s_prev}_to_{s_next}_f{f}_{d_today_str}"
                            )

        # === Objective: weighted combination ===
        w_min = self.w_min
        w_ideal = self.w_ideal
        model += (
            w_min * pulp.lpSum(
                self.y[d][s][team]
                for d in dias for s in t_range for team in self.teams
            )
            + w_ideal * pulp.lpSum(
                self.z[d][s][team]
                for d in dias for s in t_range for team in self.teams
            ),
            "Weighted_shortage_objective"
        )

        self.model = model

    # ------------------------------------------------------------
    # SOLVE (with logging, no change to model logic)
    # ------------------------------------------------------------
    def solve(self, gap_rel=None, log_to_file=True, log_dir="."):
        """
        Solve the model using CBC, capturing solver logs and writing them
        to a text file. Model structure and objective are unchanged.
        """
        time_limit = int(self.maxTime) * 60 if self.maxTime else None

        tmp_log = tempfile.NamedTemporaryFile(delete=False, mode="w+", suffix=".cbc.log")
        tmp_log_path = tmp_log.name
        tmp_log.close()

        solver = pulp.PULP_CBC_CMD(
            msg=True,
            timeLimit=time_limit,
            gapRel=gap_rel if gap_rel is not None else None,
            logPath=tmp_log_path,
        )

        start = time.time()

        # Capture CBC log from stdout
        try:
            self.model.solve(solver)

            with open(tmp_log_path, "r") as f:
                solver_output = f.read()
        finally:
            try:
                os.remove(tmp_log_path)
            except FileNotFoundError:
                pass

        # Re-print the solver log so behavior stays similar to before
        print(solver_output, end="")

        wall_time = time.time() - start
        status_str = pulp.LpStatus[self.model.status]
        print(f"✅ Solver status: {status_str} | wall time: {wall_time:.2f}s")

        # Parse solver log
        history, final_obj, final_bound, final_gap = parse_cbc_log(solver_output)

        # Fallback for final_obj if not detected
        if final_obj is None:
            try:
                final_obj = pulp.value(self.model.objective)
            except Exception:
                final_obj = None

        # Compute final_gap if missing and we have bound + obj
        if final_gap is None and final_obj is not None and final_bound is not None:
            if final_obj != 0:
                final_gap = abs(final_obj - final_bound) / abs(final_obj)
            else:
                final_gap = 0.0
        # Ensure history has at least one entry so logs always show final stats
        if not history and final_obj is not None:
            history.append(
                {
                    "nodes": 0,
                    "iters": 0,
                    "time": wall_time,
                    "obj": final_obj,
                    "bound": final_bound,
                    "gap": final_gap,
                }
            )

        # Write log file similar to CSP tracker
        if log_to_file:
            n_employees = len(self.employee_rows)
            base_name = f"logs_ilp_{n_employees}_employees_scenario"
            scenario_id = 1
            while True:
                filename = os.path.join(log_dir, f"{base_name}_{scenario_id}.txt")
                if not os.path.exists(filename):
                    break
                scenario_id += 1

            with open(filename, "w") as f:
                f.write("SOLVER REPORT (ILP / CBC)\n")
                f.write("=========================\n")
                f.write(f"Employees: {n_employees}\n")
                f.write(f"Max Time Allowed: {self.maxTime if self.maxTime else 'Unlimited'} mins\n")
                f.write(f"Final Status: {status_str}\n")
                f.write(f"Wall Time: {wall_time:.4f}s\n")
                f.write(f"Final Objective: {final_obj if final_obj is not None else 'N/A'}\n")
                f.write(f"Final Bound: {final_bound if final_bound is not None else 'N/A'}\n")
                if final_gap is not None:
                    f.write(f"Final Gap: {final_gap:.4%}\n")
                else:
                    f.write("Final Gap: N/A\n")

                f.write("\n--- PROGRESS LOG ---\n")
                f.write(
                    f"{'Count':<8} | {'Time (s)':<10} | "
                    f"{'Objective':<15} | {'Bound':<15} | "
                    f"{'Gap':<10} | {'Iters':<8} | {'Nodes':<8}\n"
                )
                f.write("-" * 98 + "\n")

                for idx, h in enumerate(history, start=1):
                    gap_str = f"{h['gap']:.4%}" if h["gap"] is not None else "N/A"
                    bound_str = f"{h['bound']:.4f}" if h["bound"] is not None else "N/A"
                    f.write(
                        f"{idx:<8} | {h['time']:<10.4f} | "
                        f"{h['obj']:<15.4f} | {bound_str:<15} | "
                        f"{gap_str:<10} | {h['iters']:<8} | {h['nodes']:<8}\n"
                    )

                f.write("\n--- CBC RAW LOG ---\n")
                f.write(solver_output)

            print(f"Log file saved to: {filename}")

        # Store for programmatic inspection if needed
        self.log_history = history
        self.final_obj = final_obj
        self.final_bound = final_bound
        self.final_gap = final_gap
        self._extract_assignments()

    def _extract_assignments(self):
        """
        Populate self.assignment with tuples (day_idx, shift, team_id) per employee.
        """
        if self.x is None:
            return

        self.assignment.clear()
        for emp_id in self.employees:
            for day_idx, day in enumerate(self.dates, start=1):
                assigned = False
                for shift in range(1, self.shifts + 1):
                    for team_id in self.emp_allowed_teams[emp_id]:
                        value = pulp.value(self.x[emp_id][day][shift][team_id]) or 0.0
                        if value > 0.5:
                            self.assignment[emp_id].append((day_idx, shift, team_id))
                            assigned = True
                            break
                    if assigned:
                        break

    # ------------------------------------------------------------
    # EXPORT
    # ------------------------------------------------------------
    def export_csv(self, filename="schedule_weighted.csv"):
        """
        Uses the same export utility as ILP1/ILP2, which is expected
        to fill self.assignment and self.vacs_1based.
        """
        export_schedule_to_csv(self, filename)

    # ------------------------------------------------------------
    # Output formatting (API/frontend table)
    # ------------------------------------------------------------
    def to_table(self):
        """
        Build a table similar to ILP1/ILP2:
        First column = employee id
        Other columns = Dia 1..N with codes like M_A, T_B, F, 0, etc.
        """
        header = ["funcionario"] + [f"Dia {i}" for i in range(1, self.num_days + 1)]
        rows = [header]

        label = {1: "M_", 2: "T_", 3: "N_"}
        n_emps = len(self.employee_rows)

        for emp_id in range(1, n_emps + 1):
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
    ilp = ILPSchedulerWeighted(
        vacations,
        minimuns,
        employees,
        maxTime,
        year,
        shifts,
        w_min=100,
        w_ideal=1,
    )
    ilp.build_model()
    ilp.solve(gap_rel=0.001, log_to_file=True)
    ilp.export_csv("schedule_weighted.csv")
    return ilp.to_table()

def parse_cbc_log(log_text):
    """
    Parse CBC solver output to extract progress (time, obj, bound, iterations, nodes).

    Returns:
      history: list of dicts with keys:
          nodes, iters, time, obj, bound, gap
      final_obj, final_bound, final_gap
    """
    history = []
    final_obj = None
    final_bound = None
    final_gap = None

    # Example progress line:
    # Cbc0010I After 0 nodes, 0 on tree, 0 iterations, 0 seconds, objective 0, best possible 0
    prog_re = re.compile(
        r"After\s+(?P<nodes>\d+)\s+nodes.*?,\s+"
        r"(?P<iters>\d+)\s+iterations,\s+"
        r"(?P<time>[0-9.]+)\s+seconds.*?"
        r"objective\s+(?P<obj>-?[0-9.]+)"
        r"(?:.*?best possible\s+(?P<bound>-?[0-9.]+))?",
        re.IGNORECASE,
    )

    # Example pass line:
    # Cbc0038I Pass   1: (12.54 seconds) ... obj. 1165 iterations 12504
    pass_re = re.compile(
        r"Cbc0038I\s+(?:Pass\s+(?P<pass>\d+):\s+)?\("
        r"(?P<time>[0-9.]+)\s+seconds\).*?"
        r"obj\.\s+(?P<obj>-?[0-9.]+)\s+iterations\s+(?P<iters>\d+)",
        re.IGNORECASE,
    )

    # Example final line:
    # Cbc0038I ... best objective 123.45, best possible 120.00 (gap 2.80%)
    final_re = re.compile(
        r"best objective\s+(-?[0-9.]+),\s+best possible\s+(-?[0-9.]+)\s+\(gap\s+([0-9.]+)%",
        re.IGNORECASE,
    )

    for line in log_text.splitlines():
        m = prog_re.search(line)
        if m:
            nodes = int(m.group("nodes"))
            iters = int(m.group("iters"))
            t = float(m.group("time"))
            obj = float(m.group("obj"))
            bound_raw = m.group("bound")
            bound = float(bound_raw) if bound_raw is not None else None
            history.append(
                {
                    "nodes": nodes,
                    "iters": iters,
                    "time": t,
                    "obj": obj,
                    "bound": bound,
                    "gap": None,  # filled later if possible
                }
            )

        m2 = final_re.search(line)
        if m2:
            final_obj = float(m2.group(1))
            final_bound = float(m2.group(2))
            final_gap = float(m2.group(3)) / 100.0

        m3 = pass_re.search(line)
        if m3:
            pass_id = m3.group("pass")
            nodes = int(pass_id) if pass_id is not None else None
            t = float(m3.group("time"))
            obj = float(m3.group("obj"))
            iters = int(m3.group("iters"))
            history.append(
                {
                    "nodes": nodes,
                    "iters": iters,
                    "time": t,
                    "obj": obj,
                    "bound": None,
                    "gap": None,
                }
            )

    # If we know final_bound, fill per-step gaps
    if final_bound is not None:
        for h in history:
            obj = h["obj"]
            if obj != 0:
                h["gap"] = abs(obj - final_bound) / abs(obj)
            else:
                h["gap"] = 0.0

    return history, final_obj, final_bound, final_gap
