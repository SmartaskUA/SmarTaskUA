import random
import time
from collections import defaultdict
import holidays as hl

from algorithm.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    get_team_id,
    get_team_code,
    build_calendar,
    TEAM_ID_TO_CODE,
)

from algorithm.rules_engine import RuleEngine, register_default_greedy_handlers
from algorithm.contexts.GreedyContext import GreedyContext


def solve(*, vacations, minimuns, employees, maxTime=None, year=2025, shifts=2, rules=None):

    year = int(year)
    num_days = 366 if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0) else 365
    holi = [d for d in hl.country_holidays("PT", years=[year]).keys()]

    # --- Parse input structures ---
    vacs_dict = rows_to_vac_dict(vacations)
    mins, ideals = rows_to_req_dicts(minimuns)

    # --- Build team mapping ---
    allowed_teams_per_emp = []
    teams_map = {}
    for idx, e in enumerate(employees):
        emp_id = idx + 1
        codes = [get_team_code(t) for t in e.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed_teams_per_emp.append(ids)
        teams_map[emp_id] = ids

    dias_ano, sundays_1based = build_calendar(year)
    start_date = dias_ano[0].date()
    special_days = {(d - start_date).days + 1 for d in holi}
    special_days |= set(sundays_1based)

    # --- Initialize Rule Engine ---
    engine = RuleEngine(
        rules_config=(rules or {}),
        num_days=num_days,
        shifts=int(shifts),
        employees=list(range(1, len(employees) + 1)),
        teams_map=teams_map,
        vacations_1based=vacs_dict,
        special_days_1based=special_days,
    )
    register_default_greedy_handlers(engine)

    # --- Core state ---
    assignment = defaultdict(list)  # emp_id -> [(day, shift, team)]
    cover_count = defaultdict(int)  # (day, shift, team) -> coverage count
    Employees = list(range(1, len(employees) + 1))
    all_days = set(range(1, num_days + 1))

    # --- Time control ---
    max_seconds = float(int(maxTime) * 60) if maxTime else 30.0
    start_time = time.time()

    # --- Randomized Greedy main loop ---
    iteration = 0
    while time.time() - start_time < max_seconds:
        iteration += 1
        if iteration % 10 == 0:
            elapsed = time.time() - start_time

        # prefer employees with fewer team options and under max workdays
        prioritized = (
            [p for p in Employees if len(assignment[p]) < 223 and len(teams_map[p]) == 1]
            or [p for p in Employees if len(assignment[p]) < 223 and len(teams_map[p]) == 2]
            or [p for p in Employees if len(assignment[p]) < 223]
        )
        if not prioritized:
            break

        p = random.choice(prioritized)
        used_days = {day for (day, _, _) in assignment[p]}
        vacations = set(vacs_dict.get(p, []))
        available_days = list(all_days - used_days - vacations)
        if not available_days:
            continue

        best = None
        best_score = float("inf")
        inner_iters = 0

        while inner_iters < 10 and available_days:
            d = random.choice(available_days)
            s = random.choice(range(1, int(shifts) + 1))

            # Try all team options for that employee
            for t in teams_map[p]:
                ctx = GreedyContext(
                    Employees=Employees,
                    num_days=num_days,
                    shifts=int(shifts),
                    vacations=vacs_dict,
                    allowed_teams_per_emp=allowed_teams_per_emp,
                    min_required=mins,
                    ideal_required=ideals,
                    special_days=special_days,
                    cover_count=cover_count,
                    assignment=assignment,
                    e=p, d=d, s=s, t=t,
                )

                feasible = engine.apply_greedy(ctx)
                if not feasible:
                    continue

                # urgency heuristic (same as f2)
                current = cover_count.get((d, s, t), 0)
                min_req = mins.get((d, s, t), 0)
                ideal_req = ideals.get((d, s, t), min_req)
                if current < min_req:
                    score = 0
                elif current < ideal_req:
                    score = 1
                else:
                    score = 2 + (current - ideal_req)

                # lower is better (f2 style)
                score += random.uniform(0, 0.1)
                if score < best_score:
                    best_score = score
                    best = (d, s, t)

            inner_iters += 1

        if best:
            d, s, t = best
            assignment[p].append((d, s, t))
            cover_count[(d, s, t)] += 1

        # early exit if everyone full
        if all(len(assignment[e]) >= 223 for e in Employees):
            break

    elapsed = time.time() - start_time

    # --- Output table ---
    header = ["funcionario"] + [f"Dia {d}" for d in range(1, num_days + 1)]
    label = {1: "M_", 2: "T_", 3: "N_"}
    output = [header]

    for e in Employees:
        row = [e]
        vac_days = set(vacs_dict.get(e, []))
        assign_map = {day: (s, t) for (day, s, t) in assignment[e]}

        for d in range(1, num_days + 1):
            if d in vac_days:
                row.append("F")
            elif d in assign_map:
                s, t = assign_map[d]
                team_label = TEAM_ID_TO_CODE.get(t, str(t))
                row.append(f"{label.get(s, '')}{team_label}")
            else:
                row.append("0")
        output.append(row)

    return output
