import random
from collections import defaultdict
import holidays as hl

from algorithm.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    export_schedule_to_csv,
    build_calendar,
    schedule_to_table,
)


# ============================================================
# Helpers
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


def _build_special_days(year, num_days=365):
    """
    Build set of 1-based day indices that are PT holidays or Sundays.
    Assumes build_calendar(year) returns (list_of_datetimes, list_of_sundays_1based).
    """
    dias_ano, sundays_1based = build_calendar(year)
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

    This checks both backwards and forwards around day d, so we also catch
    inserting work in the middle of an existing run.
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
        i.e. for any pair of consecutive worked days d, d+1 we require shift[d+1] >= shift[d]
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


# Main heuristic solver

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
):
    """
    Heuristic schedule generator.

    Arguments:
        vacations: rows used by rows_to_vac_dict
        minimuns: rows used by rows_to_req_dicts
        employees: list of dicts (with "teams" field)
        maxTime: unused (kept for API compatibility)
        year: int
        shifts: number of shifts per day (1..S)
        rules: unused (placeholder)
        target_workdays: desired working days per employee
        special_cap: max special (Sunday+holiday) days per employee

    """

    num_days = 365
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
                    total_work[best_e] += 1
                    if d in special_days:
                        total_special[best_e] += 1
                    assigned_min[(d, s, t)] += 1
                    assigned[(d, s, t)] += 1

    # =====================================================
    # PASS 2: Move toward ideal coverage and 223 workdays
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
                    total_work[e] += 1
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

    export_schedule_to_csv(v, "schedule_heuristic.csv", num_days=num_days)

    return schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=int(shifts),
    )


# ============================================================
# Wrapper to match your existing `solve` interface
# ============================================================

def solve(vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):
    return solve_heuristic(
        vacations=vacations,
        minimuns=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        shifts=shifts,
        rules=rules,
        target_workdays=223,
        special_cap=22,
    )
