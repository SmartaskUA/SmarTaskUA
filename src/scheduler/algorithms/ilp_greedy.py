# ============================================================
# ILP: Weighted model with warm-start from greedy
# ============================================================

import pulp
import os
import time
import tempfile
from collections import defaultdict
import random
import holidays as hl

from algorithms.general.solver_logging import parse_cbc_log, write_ilp_log
from algorithms.utils import (
    TEAM_ID_TO_CODE,
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv,
    get_team_code,
    get_team_id,
    schedule_to_table,
)

# ============================================================
# Greedy heuristic
# ============================================================

def _build_allowed_teams(employees):
    """
    Convert employee 'teams' labels to internal numeric team IDs.
    Fallback to team 'A' when none provided.
    """
    allowed = []
    for emp in employees:
        codes = [get_team_code(t) for t in emp.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed


def _build_special_days(year, num_days=None):
    """
    Build set of 1-based day indices that are PT holidays or Sundays.
    Assumes build_calendar(year) returns (list_of_datetimes, list_of_sundays_1based).
    If num_days is None, uses length of calendar.
    """
    dias_ano, sundays_1based = build_calendar(year)
    if num_days is None:
        num_days = len(dias_ano)

    pt_holidays = hl.country_holidays("PT", years=[year])

    if not dias_ano:
        return set()

    start_date = dias_ano[0].date()

    holiday_days = set()
    for h_date in pt_holidays:
        d = (h_date - start_date).days + 1
        if 1 <= d <= num_days:
            holiday_days.add(d)

    special_days = set(sundays_1based) | holiday_days
    return special_days


def _violates_consecutive_work(e, d, work, max_consec=5):
    """
    Check if assigning work to (e, d) would create more than max_consec
    consecutive working days (i.e. forbid 6th consecutive day if max_consec=5).
    """
    n_days = len(work[e]) - 1  # because we index 1..num_days

    # count consecutive working days to the left of d
    run_left = 0
    dd = d - 1
    while dd >= 1 and work[e][dd] == 1:
        run_left += 1
        dd -= 1

    # count consecutive working days to the right of d
    run_right = 0
    dd = d + 1
    while dd <= n_days and work[e][dd] == 1:
        run_right += 1
        dd += 1

    # full run length including day d (if we assign it)
    full_run = run_left + 1 + run_right
    return full_run > max_consec


def _is_feasible_assignment(
    e,
    d,
    s,
    t,
    work,
    shift,
    total_work,
    total_special,
    vac_mask,
    special_days,
    target_workdays,
    special_cap,
):
    """
    Check if assigning employee e to (d,s,t) is feasible w.r.t. all hard constraints:
      - Vacation
      - Only one shift per day
      - No Afternoon→Morning (or more generally later→earlier) on consecutive work days
      - At most 5 consecutive working days
      - Max target_workdays total working days
      - Max special_cap special (Sunday/holiday) days
    """

    n_days = len(work[e]) - 1

    # Vacation
    if vac_mask[(e, d)]:
        return False

    # Already working that day
    if work[e][d] == 1:
        return False

    # No backward shift on consecutive work days:
    # previous day worked => its shift must be <= s
    if d > 1 and work[e][d - 1] == 1:
        prev_shift = shift[e][d - 1]
        if prev_shift > s:
            return False

    # Also check relation with next day (if already worked):
    # next day worked => its shift must be >= s
    if d < n_days and work[e][d + 1] == 1:
        next_shift = shift[e][d + 1]
        if next_shift < s:
            return False

    # No more than 5 consecutive working days (check both sides)
    if _violates_consecutive_work(e, d, work, max_consec=5):
        return False

    # Total work upper bound
    if total_work[e] + 1 > target_workdays:
        return False

    # Special days cap
    if d in special_days and total_special[e] + 1 > special_cap:
        return False

    return True


def _employee_score(e, d, is_special, total_work, total_special, target_workdays):
    """
    Lower score = more desirable to assign.
    Tunable heuristic.
    """
    w_work = 1.0
    w_special = 3.0
    w_under_target = 0.1
    w_random = 0.01

    score = 0.0
    score += w_work * total_work[e]
    score += w_special * total_special[e]

    # Slightly favor under-scheduled employees
    delta = target_workdays - total_work[e]
    if delta > 0:
        score -= w_under_target * delta

    score += w_random * random.random()
    return score


def solve_heuristic(
    vacations,
    minimuns,
    employees,
    maxTime=None,
    year=2025,
    shifts=2,
    rules=None,
    target_workdays=223,
    special_cap=22,
    return_view=False,
):
    """
    Heuristic schedule generator.

    Returns:
        - table (compatible with schedule_to_table)
        - if return_view=True, also returns the internal View with:
            view.employees
            view.vacs
            view.assignment  (emp_id -> list[(day, s, t)])
    """

    # Use actual calendar length for the year
    dias_ano, _ = build_calendar(year)
    num_days = len(dias_ano)

    n_employees = len(employees)
    S = range(1, int(shifts) + 1)
    Employees = list(range(n_employees))
    D = list(range(1, num_days + 1))

    # Allowed teams per employee
    allowed_teams_per_emp = _build_allowed_teams(employees)

    # Vacations mask
    vacs_dict = rows_to_vac_dict(vacations)
    vac_mask = {(i, d): False for i in Employees for d in D}
    for emp_id, days in vacs_dict.items():
        e = emp_id - 1
        if 0 <= e < n_employees:
            for d in days:
                if 1 <= d <= num_days:
                    vac_mask[(e, d)] = True

    # Requirements
    mins_raw, ideals_raw = rows_to_req_dicts(minimuns)

    min_required = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shifts):
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                min_required[(d, s, t)] = req

    ideal_required = {}
    for (d, s, t), v in ideals_raw.items():
        if 1 <= d <= num_days and 1 <= s <= int(shifts):
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                ideal_required[(d, s, t)] = req

    # Special days (Sundays + holidays)
    special_days = _build_special_days(year, num_days=num_days)

    # State variables
    work = [[0] * (num_days + 1) for _ in Employees]   # work[e][d] ∈ {0,1}
    shift = [[0] * (num_days + 1) for _ in Employees]  # shift[e][d] ∈ {0..S}
    team = [[None] * (num_days + 1) for _ in Employees]  # team[e][d] ∈ team_id or None

    total_work = [0] * n_employees
    total_special = [0] * n_employees

    # Coverage tracking
    assigned_min = defaultdict(int)  # (d,s,t) -> count assigned for min-coverage phase
    assigned = defaultdict(int)      # (d,s,t) -> overall coverage

    # =====================================================
    # PASS 1: Satisfy minimum coverage greedily
    # =====================================================

    for d in D:
        for s in S:
            # Determine teams that require coverage on this (d,s)
            teams_here = [
                t for (dd, ss, t) in min_required.keys() if dd == d and ss == s
            ]
            for t in teams_here:
                req = min_required[(d, s, t)]
                while assigned_min[(d, s, t)] < req:
                    candidates = []
                    for e in Employees:
                        if t not in allowed_teams_per_emp[e]:
                            continue
                        if not _is_feasible_assignment(
                            e,
                            d,
                            s,
                            t,
                            work,
                            shift,
                            total_work,
                            total_special,
                            vac_mask,
                            special_days,
                            target_workdays,
                            special_cap,
                        ):
                            continue
                        candidates.append(e)

                    if not candidates:
                        # Cannot meet this minimum; leave shortage here
                        break

                    best_e = min(
                        candidates,
                        key=lambda e: _employee_score(
                            e, d, d in special_days, total_work, total_special, target_workdays
                        ),
                    )

                    work[best_e][d] = 1
                    shift[best_e][d] = s
                    team[best_e][d] = t
                    total_work[e] += 1
                    if d in special_days:
                        total_special[best_e] += 1
                    assigned_min[(d, s, t)] += 1
                    assigned[(d, s, t)] += 1

    # =====================================================
    # PASS 2: Move toward ideal coverage and target_workdays
    # =====================================================

    for e in Employees:
        deficit = target_workdays - total_work[e]
        if deficit <= 0:
            continue

        # Two rounds:
        # 1) Assign only where coverage < ideal (if ideal defined) or < minimum if no ideal
        # 2) Assign anywhere feasible (even if over ideal / no requirement)
        for round_idx in (1, 2):
            if deficit <= 0:
                break

            for d in D:
                if deficit <= 0:
                    break
                if work[e][d] == 1:
                    continue
                if vac_mask[(e, d)]:
                    continue

                # Build candidate slots for this day
                slots = []
                for s in S:
                    for t in allowed_teams_per_emp[e]:
                        key = (d, s, t)
                        slots.append((s, t, key))

                if round_idx == 1:
                    # Filter to where coverage < ideal or (ideal absent and coverage < min)
                    filtered = []
                    for s, t, key in slots:
                        cov = assigned[key]
                        ideal = ideal_required.get(key, None)
                        minreq = min_required.get(key, 0)
                        if ideal is not None:
                            if cov < ideal:
                                filtered.append((s, t, key))
                        else:
                            if cov < minreq:
                                filtered.append((s, t, key))
                    slots = filtered
                    if not slots:
                        continue

                # Try slots in random order to diversify
                random.shuffle(slots)

                for s, t, key in slots:
                    if not _is_feasible_assignment(
                        e,
                        d,
                        s,
                        t,
                        work,
                        shift,
                        total_work,
                        total_special,
                        vac_mask,
                        special_days,
                        target_workdays,
                        special_cap,
                    ):
                        continue

                    work[e][d] = 1
                    shift[e][d] = s
                    team[e][d] = t
                    total_work[best_e] += 1
                    if d in special_days:
                        total_special[e] += 1
                    assigned[key] += 1
                    deficit -= 1
                    break  # next day

    # =====================================================
    # PASS 3: Fill remaining deficit anywhere feasible, even if overstaffing
    # =====================================================

    for e in Employees:
        deficit = target_workdays - total_work[e]
        if deficit <= 0:
            continue

        for d in D:
            if deficit <= 0:
                break
            if work[e][d] == 1:
                continue
            if vac_mask[(e, d)]:
                continue

            slots = []
            for s in S:
                for t in allowed_teams_per_emp[e]:
                    slots.append((s, t))

            random.shuffle(slots)

            for s, t in slots:
                if not _is_feasible_assignment(
                    e,
                    d,
                    s,
                    t,
                    work,
                    shift,
                    total_work,
                    total_special,
                    vac_mask,
                    special_days,
                    target_workdays,
                    special_cap,
                ):
                    continue

                work[e][d] = 1
                shift[e][d] = s
                team[e][d] = t
                total_work[e] += 1
                if d in special_days:
                    total_special[e] += 1
                assigned[(d, s, t)] += 1
                deficit -= 1
                break

    # =====================================================
    # Build assignment structure and export
    # =====================================================

    assign = defaultdict(list)  # emp_id -> list[(day, s, t)]
    for e in Employees:
        emp_id = e + 1
        for d in D:
            if work[e][d] == 1:
                s = shift[e][d]
                t = team[e][d]
                if s > 0 and t is not None:
                    assign[emp_id].append((d, s, t))

    class View:
        pass

    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign

    # Export greedy schedule (optional)
    export_schedule_to_csv(v, "schedule_heuristic.csv", num_days=num_days)

    table = schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=int(shifts),
    )

    if return_view:
        return table, v
    return table


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
        # Sundays
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
        self.model = None
        self.x = None
        self.y = None
        self.z = None

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
                    model += (
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
    # Warm start from greedy
    # ------------------------------------------------------------
    def apply_warm_start_from_greedy(self, greedy_assignment):
        """
        greedy_assignment: dict emp_id -> list[(day_idx, shift, team_id)]
        Uses this as a MIP start for CBC by setting initial values of x.
        """
        if self.x is None:
            raise RuntimeError("Model not built. Call build_model() before warm-start.")

        # Map (emp_id, day_idx) -> (shift, team_id)
        gmap = {}
        for emp_id, lst in greedy_assignment.items():
            for (day_idx, s, t) in lst:
                if 1 <= day_idx <= self.num_days:
                    gmap[(emp_id, day_idx)] = (s, t)

        t_range = range(1, self.shifts + 1)

        for emp_id in self.employees:
            allowed_teams = self.emp_allowed_teams[emp_id]
            for day_idx, d in enumerate(self.dates, start=1):
                key = (emp_id, day_idx)

                if key in gmap:
                    # Working day in greedy
                    s_g, t_g = gmap[key]
                    # Set the chosen (shift, team) to 1, everything else to 0
                    for s in range(0, self.shifts + 1):
                        for t in allowed_teams:
                            var = self.x[emp_id][d][s][t]
                            if s == s_g and t == t_g:
                                var.setInitialValue(1)
                            else:
                                var.setInitialValue(0)
                else:
                    if not allowed_teams:
                        continue
                    off_team = allowed_teams[0]
                    for s in range(0, self.shifts + 1):
                        for t in allowed_teams:
                            var = self.x[emp_id][d][s][t]
                            if s == 0 and t == off_team:
                                var.setInitialValue(1)
                            else:
                                var.setInitialValue(0)

    # ------------------------------------------------------------
    # SOLVE (with logging)
    # ------------------------------------------------------------
    def solve(self, gap_rel=None, log_to_file=True, log_dir="."):
        """
        Solve the model using CBC, capturing solver logs and writing them
        to a text file.
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

        try:
            self.model.solve(solver)
            with open(tmp_log_path, "r") as f:
                solver_output = f.read()
        finally:
            try:
                os.remove(tmp_log_path)
            except FileNotFoundError:
                pass

        # Re-print the solver log
        print(solver_output, end="")

        wall_time = time.time() - start
        status_str = pulp.LpStatus[self.model.status]
        print(f"Solver status: {status_str} | wall time: {wall_time:.2f}s")

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

        # Ensure history has at least one entry
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

        # Write log file
        if log_to_file:
            n_employees = len(self.employee_rows)
            write_ilp_log(
                history=history,
                final_obj=final_obj,
                final_bound=final_bound,
                final_gap=final_gap,
                solver_output=solver_output,
                n_employees=n_employees,
                max_time=self.maxTime,
                status_str=status_str,
                wall_time=wall_time,
                log_dir=log_dir,
            )

        # Store for programmatic inspection
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
        Uses the same export utility as ILP1/ILP2.
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

# ============================================================
# Hybrid external API: greedy warm-start + ILP
# ============================================================

def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):
    """
    Hybrid solver:
      1) Run greedy heuristic to get a feasible schedule.
      2) Use that schedule as a warm-start for the ILP.
      3) Solve ILP and return the final optimized table.
    """
    # 1) Greedy warm-start (also writes schedule_heuristic.csv)
    _, greedy_view = solve_heuristic(
        vacations=vacations,
        minimuns=minimuns,
        employees=employees,
        maxTime=None,
        year=year,
        shifts=shifts,
        rules=rules,
        target_workdays=223,
        special_cap=22,
        return_view=True,
    )

    # 2) Build ILP model
    ilp = ILPSchedulerWeighted(
        vacations_rows=vacations,
        minimuns_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        shifts=shifts,
        w_min=100,
        w_ideal=1,
    )
    ilp.build_model()

    # 3) Apply warm-start from greedy assignment
    ilp.apply_warm_start_from_greedy(greedy_view.assignment)

    # 4) Solve ILP
    ilp.solve(gap_rel=0.001, log_to_file=True)

    # 5) Export and return table
    ilp.export_csv("schedule_weighted.csv")
    return ilp.to_table()
