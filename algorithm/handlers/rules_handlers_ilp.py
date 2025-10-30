import pulp

def i_one_shift_per_day(r, ctx):
    for f in ctx.employees:
        for d in ctx.dates:
            ctx.add_constraint(
                pulp.lpSum(ctx.x[f][d][t] for t in range(0, ctx.shifts + 1)) == 1,
                f"one_shift_day_f{f}_{d}"
            )

def i_total_workdays(r, ctx):
    """
    Enforces total workday bounds or equality.
    JSON params may include:
      - min: minimum number of total workdays
      - max: maximum number of total workdays
      If both are provided and equal, an equality constraint is used.
    """
    min_days = r.params.get("min")
    max_days = r.params.get("max")
    t_range = range(1, ctx.shifts + 1) 
    for f in ctx.employees:
        sum_work = pulp.lpSum(ctx.x[f][d][s] for d in ctx.dates for s in t_range)

        if r.kind.lower() == "hard":
            if min_days is not None and max_days is not None and int(min_days) == int(max_days):
                ctx.add_constraint(sum_work == int(min_days),
                                   f"total_workdays_eq_f{f}")
            else:
                if min_days is not None:
                    ctx.add_constraint(sum_work >= int(min_days),
                                       f"total_workdays_min_f{f}")
                if max_days is not None:
                    ctx.add_constraint(sum_work <= int(max_days),
                                       f"total_workdays_max_f{f}")

        else:
            sp = pulp.LpVariable(f"slack_plus_total_{r.id}_f{f}", lowBound=0, cat="Continuous")
            sm = pulp.LpVariable(f"slack_minus_total_{r.id}_f{f}", lowBound=0, cat="Continuous")

            if min_days is not None and max_days is not None and int(min_days) == int(max_days):
                ctx.add_constraint(sum_work + sm - sp == int(min_days),
                                   f"total_workdays_soft_eq_f{f}")
            else:
                if min_days is not None:
                    ctx.add_constraint(sum_work + sm >= int(min_days),
                                       f"total_workdays_soft_min_f{f}")
                if max_days is not None:
                    ctx.add_constraint(sum_work - sp <= int(max_days),
                                       f"total_workdays_soft_max_f{f}")

            weight = float(r.params.get("weight", 10.0))
            ctx.add_penalty(sp + sm, weight)



def i_max_consecutive_days(r, ctx):
    """
    If hard:   in any window of (max+1) days, <= max working days
    If soft:   allow +slack per window and penalize
    Params:
      max: int (default 5)
      weight: float (default 5)
    """
    max_consec = int(r.params.get("max", 5))
    weight = float(r.params.get("weight", 5.0))
    t_range = range(1, ctx.shifts + 1)

    for f in ctx.employees:
        for i in range(len(ctx.dates) - max_consec):
            window = ctx.dates[i:i + (max_consec + 1)]
            work_in_window = pulp.lpSum(ctx.x[f][d][s] for d in window for s in t_range)
            if r.kind.lower() == "hard":
                ctx.add_constraint(work_in_window <= max_consec,
                                   f"max_consec_{f}_{ctx.dates[i]}")
            else:
                slack = pulp.LpVariable(f"slack_consec_{r.id}_f{f}_{i}", lowBound=0, cat="Continuous")
                ctx.add_constraint(work_in_window <= max_consec + slack,
                                   f"max_consec_soft_{f}_{ctx.dates[i]}")
                ctx.add_penalty(slack, weight)


def i_max_special_days(r, ctx):
    """
    Cap Sundays+holidays per employee.
    If soft, add slack and penalize.
    Params:
      cap: int (default 22)
      weight: float (default 3)
    """
    cap = int(r.params.get("cap", 22))
    weight = float(r.params.get("weight", 3.0))
    t_range = range(1, ctx.shifts + 1)

    for f in ctx.employees:
        sum_special = pulp.lpSum(ctx.x[f][d][s] for d in ctx.sundays_holidays for s in t_range)
        if r.kind.lower() == "hard":
            ctx.add_constraint(sum_special <= cap, f"max_special_days_f{f}")
        else:
            slack = pulp.LpVariable(f"slack_special_{r.id}_f{f}", lowBound=0, cat="Continuous")
            ctx.add_constraint(sum_special <= cap + slack, f"max_special_days_soft_f{f}")
            ctx.add_penalty(slack, weight)


def i_no_earlier_shift_next_day(r, ctx):
    """
    Forbid going from a later shift to an earlier one next day.
    If soft, allow violation with slack per (f, day, pair) and penalize.
    Params:
      weight: float (default 1)
    """
    weight = float(r.params.get("weight", 1.0))
    if ctx.shifts < 2:
        return

    for f in ctx.employees:
        for i in range(len(ctx.dates) - 1):
            d_today = ctx.dates[i]
            d_next = ctx.dates[i + 1]
            for s_prev in range(1, ctx.shifts + 1):
                for s_next in range(1, ctx.shifts + 1):
                    if s_next < s_prev:
                        lhs = ctx.x[f][d_today][s_prev] + ctx.x[f][d_next][s_next]
                        if r.kind.lower() == "hard":
                            ctx.add_constraint(lhs <= 1,
                                               f"no_earlier_f{f}_{d_today}_{s_prev}_to_{s_next}")
                        else:
                            slack = pulp.LpVariable(
                                f"slack_noearlier_{r.id}_f{f}_{i}_{s_prev}_{s_next}",
                                lowBound=0, cat="Continuous")
                            ctx.add_constraint(lhs <= 1 + slack,
                                               f"no_earlier_soft_f{f}_{d_today}_{s_prev}_to_{s_next}")
                            ctx.add_penalty(slack, weight)


def i_vacation_block(r, ctx):
    for f, vac_days in ctx.vacations.items():
        for d in vac_days:
            d_key = ctx.dates[d-1] if isinstance(d, int) else d
            if d_key in ctx.x.get(f, {}):
                ctx.add_constraint(ctx.x[f][d_key][0] == 1, f"vacation_off_f{f}_{d_key}")



def i_min_coverage(r, ctx):
    """
    Ensure minimum coverage per (date, shift, team). If soft, penalize shortages.
    Params:
      weight: float (default 50)
    """
    weight = float(r.params.get("weight", 50.0))

    for d in ctx.dates:
        for s in range(1, ctx.shifts + 1):
            for team_code, members in ctx.teams.items():
                # link y = sum of x for members
                ctx.add_constraint(
                    ctx.y[d][s][team_code] == pulp.lpSum(ctx.x[f][d][s] for f in members),
                    f"count_{team_code}_{d}_S{s}"
                )
                minimo = ctx.min_required.get((d, team_code, s), 0)
                if minimo > 0:
                    if r.kind.lower() == "hard":
                        ctx.add_constraint(ctx.y[d][s][team_code] >= minimo,
                                           f"mincov_hard_{team_code}_{d}_S{s}")
                    else:
                        shortage = pulp.LpVariable(
                            f"shortage_{r.id}_{d}_S{s}_{team_code}",
                            lowBound=0, cat="Continuous")
                        # shortage >= minimo - y
                        ctx.add_constraint(shortage >= minimo - ctx.y[d][s][team_code],
                                           f"mincov_soft_{team_code}_{d}_S{s}")
                        ctx.add_penalty(shortage, weight)
