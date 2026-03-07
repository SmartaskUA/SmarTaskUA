import random
from collections import defaultdict
import holidays as hl

from algorithms.general.constraints import parse_constraints
from algorithms.utils import (
    build_allowed_teams,
    build_calendar,
    infer_shift_count_from_dicts,
    rows_to_req_dicts_any,
    rows_to_vac_dict,
    safe_int,
    export_schedule_to_csv,
    schedule_to_table,
)


# ============================================================
# Helpers
# ============================================================

def _build_special_days(year, num_days, dias_ano, sundays_1based):
    pt_holidays = hl.country_holidays("PT", years=[year])
    if not dias_ano:
        return set()

    start_date = dias_ano[0].date()
    holiday_days = set()
    for h_date in pt_holidays:
        d = (h_date - start_date).days + 1
        if 1 <= d <= num_days:
            holiday_days.add(d)

    return set(sundays_1based) | holiday_days


def _violates_consecutive_work(e, d, work, max_consec):
    n_days = len(work[e]) - 1  # 1..num_days
    run_left = 0
    dd = d - 1
    while dd >= 1 and work[e][dd] == 1:
        run_left += 1
        dd -= 1

    run_right = 0
    dd = d + 1
    while dd <= n_days and work[e][dd] == 1:
        run_right += 1
        dd += 1

    return (run_left + 1 + run_right) > max_consec


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
    max_consecutive_worked,
    enforce_no_earlier,
):
    n_days = len(work[e]) - 1

    if vac_mask[(e, d)]:
        return False
    if work[e][d] == 1:
        return False

    if enforce_no_earlier:
        if d > 1 and work[e][d - 1] == 1:
            if shift[e][d - 1] > s:
                return False
        if d < n_days and work[e][d + 1] == 1:
            if shift[e][d + 1] < s:
                return False

    if _violates_consecutive_work(e, d, work, max_consecutive_worked):
        return False

    if target_workdays is not None and total_work[e] + 1 > target_workdays:
        return False

    if d in special_days and special_cap is not None and total_special[e] + 1 > special_cap:
        return False

    return True


def _employee_score(e, total_work, total_special, target_workdays):
    w_work = 1.0
    w_special = 3.0
    w_under_target = 0.1
    w_random = 0.01

    score = 0.0
    score += w_work * total_work[e]
    score += w_special * total_special[e]

    if target_workdays is not None:
        delta = target_workdays - total_work[e]
        if delta > 0:
            score -= w_under_target * delta

    score += w_random * random.random()
    return score


# ============================================================
# Main heuristic solver (general)
# ============================================================

def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None, constraints=None):
    plan = parse_constraints(constraints if constraints is not None else rules)

    resolved_year = safe_int(year, 2025)
    dias_ano, sundays_1based = build_calendar(resolved_year)
    num_days = len(dias_ano) if dias_ano else 365

    n_employees = len(employees)
    Employees = list(range(n_employees))

    mins_raw, ideals_raw = rows_to_req_dicts_any(minimuns, year=resolved_year)
    shift_count = safe_int(shifts, None)
    inferred_shifts = infer_shift_count_from_dicts(mins_raw, ideals_raw)
    if shift_count is None or shift_count <= 0:
        shift_count = inferred_shifts if inferred_shifts is not None else 2
    elif inferred_shifts is not None and inferred_shifts > shift_count:
        shift_count = inferred_shifts
    shift_count = int(shift_count)

    S = range(1, shift_count + 1)
    D = list(range(1, num_days + 1))

    allowed_teams_per_emp = build_allowed_teams(employees)

    vacs_dict = rows_to_vac_dict(vacations)
    vac_mask = {(i, d): False for i in Employees for d in D}
    if plan.enforce_vacation:
        for emp_id, days in vacs_dict.items():
            e = emp_id - 1
            if 0 <= e < n_employees:
                for d in days:
                    if 1 <= d <= num_days:
                        vac_mask[(e, d)] = True

    min_required = {}
    for (d, s, t), v in mins_raw.items():
        if 1 <= d <= num_days and 1 <= s <= shift_count:
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                min_required[(d, s, t)] = req

    ideal_required = {}
    for (d, s, t), v in ideals_raw.items():
        if 1 <= d <= num_days and 1 <= s <= shift_count:
            try:
                req = int(v)
            except Exception:
                continue
            if req > 0:
                ideal_required[(d, s, t)] = req

    special_days = _build_special_days(resolved_year, num_days, dias_ano, sundays_1based)

    work = [[0] * (num_days + 1) for _ in Employees]
    shift = [[0] * (num_days + 1) for _ in Employees]
    team = [[None] * (num_days + 1) for _ in Employees]

    total_work = [0] * n_employees
    total_special = [0] * n_employees

    assigned_min = defaultdict(int)
    assigned = defaultdict(int)

    target_workdays = plan.total_workdays_max or plan.total_workdays_min
    max_consecutive_worked = plan.max_consecutive_worked or 5
    special_cap = plan.special_cap
    enforce_no_earlier = plan.enforce_no_earlier

    # PASS 1: minimum coverage
    for d in D:
        for s in S:
            teams_here = [t for (dd, ss, t) in min_required.keys() if dd == d and ss == s]
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
                            max_consecutive_worked,
                            enforce_no_earlier,
                        ):
                            continue
                        candidates.append(e)

                    if not candidates:
                        break

                    best_e = min(
                        candidates,
                        key=lambda e: _employee_score(e, total_work, total_special, target_workdays),
                    )

                    work[best_e][d] = 1
                    shift[best_e][d] = s
                    team[best_e][d] = t
                    total_work[best_e] += 1
                    if d in special_days:
                        total_special[best_e] += 1
                    assigned_min[(d, s, t)] += 1
                    assigned[(d, s, t)] += 1

    # PASS 2: ideal coverage + target days
    for e in Employees:
        if target_workdays is None:
            break
        deficit = target_workdays - total_work[e]
        if deficit <= 0:
            continue

        for round_idx in (1, 2):
            if deficit <= 0:
                break

            for d in D:
                if deficit <= 0:
                    break
                if work[e][d] == 1 or vac_mask[(e, d)]:
                    continue

                slots = [(s, t, (d, s, t)) for s in S for t in allowed_teams_per_emp[e]]

                if round_idx == 1:
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
                        max_consecutive_worked,
                        enforce_no_earlier,
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
                    break

    # PASS 3: fill remaining deficit anywhere feasible
    for e in Employees:
        if target_workdays is None:
            break
        deficit = target_workdays - total_work[e]
        if deficit <= 0:
            continue

        for d in D:
            if deficit <= 0:
                break
            if work[e][d] == 1 or vac_mask[(e, d)]:
                continue

            slots = [(s, t) for s in S for t in allowed_teams_per_emp[e]]
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
                    max_consecutive_worked,
                    enforce_no_earlier,
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

    assign = defaultdict(list)
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

    export_schedule_to_csv(v, "schedule_heuristic_general.csv", num_days=num_days)
    return schedule_to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        shifts=shift_count,
    )
