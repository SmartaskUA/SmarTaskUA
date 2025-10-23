from algorithm.rules_engine import Rule
from algorithm.contexts.CPSatContext import CPSatContext


def h_no_earlier_shift_next_day(r: Rule, ctx: CPSatContext):
    """Forbid backward transitions: no T->M, N->M, N->T between consecutive days."""
    m = ctx.m
    for e in ctx.Employees:
        for day in range(1, ctx.num_days):
            m.Add(ctx.shift_id[(e, day + 1)] >= ctx.shift_id[(e, day)]).OnlyEnforceIf(
                [ctx.off[(e, day)].Not(), ctx.off[(e, day + 1)].Not()]
            )


def h_max_consecutive_days(r: Rule, ctx: CPSatContext):
    """No employee may work more than X days in any Y-day window."""
    m = ctx.m
    window = int(r.params.get("window", 6))  # default window = 6
    max_in = int(r.params.get("max_worked", 5))  # from JSON: "max_worked": 5
    for e in ctx.Employees:
        for start in range(1, ctx.num_days - window + 2):
            days = range(start, start + window)
            m.Add(sum(1 - ctx.off[(e, d)] for d in days) <= max_in)


def h_max_special_days(r: Rule, ctx: CPSatContext):
    m = ctx.m
    cap = int(r.params.get("cap", 22))
    for e in ctx.Employees:
        sp_terms = [1 - ctx.off[(e, d)] for d in ctx.D if d in ctx.special_days]
        if sp_terms:
            m.Add(sum(sp_terms) <= cap)


def h_total_workdays(r: Rule, ctx: CPSatContext):
    """
    Enforce total yearly workdays based on min/max parameters:
      - If only 'max' is given → <= max
      - If only 'min' is given → >= min
      - If both 'min' and 'max' are given:
            if equal → == total
            else     → between min and max
    """
    m = ctx.m
    params = r.params or {}
    max_days = params.get("max")
    min_days = params.get("min")

    max_days = int(max_days) if max_days is not None else None
    min_days = int(min_days) if min_days is not None else None

    for e in ctx.Employees:
        workdays = []
        for d in ctx.D:
            w = m.NewBoolVar(f"work_{e}_{d}")
            m.Add(w == 1).OnlyEnforceIf(ctx.off[(e, d)].Not())
            m.Add(w == 0).OnlyEnforceIf(ctx.off[(e, d)])
            workdays.append(w)

        total_work_expr = sum(workdays)

        if max_days is not None and min_days is not None:
            if max_days == min_days:
                m.Add(total_work_expr == max_days)
            else:
                m.Add(total_work_expr >= min_days)
                m.Add(total_work_expr <= max_days)
        elif max_days is not None:
            m.Add(total_work_expr <= max_days)
        elif min_days is not None:
            m.Add(total_work_expr >= min_days)
        else:
            m.Add(total_work_expr <= 223)



def h_vacation_block(r: Rule, ctx: CPSatContext):
    """Vacation days marked 'F' cannot be scheduled for work."""
    # Enforced structurally via ctx.vac_mask when building ctx.y
    return


def h_team_eligibility(r: Rule, ctx: CPSatContext):
    """Employees can only be assigned to allowed teams."""
    # Enforced structurally via ctx.allowed_teams_per_emp when building ctx.y
    return


def h_min_coverage(r: Rule, ctx: CPSatContext):
    """Try to meet minimum coverage requirements; penalize unmet demand if soft."""
    m = ctx.m
    kind = r.kind.lower()
    penalty = int(r.params.get("penalty_per_missing", 1000))
    unmet = ctx.extras.setdefault("unmet", {})

    for (day, s, t), req in ctx.min_required.items():
        cover = []
        for e in ctx.Employees:
            if (not ctx.vac_mask[(e, day)]) and (t in ctx.allowed_teams_per_emp[e]):
                v = ctx.y.get((e, day, s, t))
                if v is not None:
                    cover.append(v)
        if kind == "soft":
            u = m.NewIntVar(0, req, f"unmet_{day}_{s}_{t}")
            unmet[(day, s, t)] = u
            m.Add(sum(cover) + u >= req)
            ctx.obj_terms.append(penalty * u)
        else:
            m.Add(sum(cover) >= req)


def h_target_workdays_balancing(r: Rule, ctx: CPSatContext):
    """Soft objective: balance total yearly workdays among employees."""
    m = ctx.m
    target = int(r.params.get("target", 223))
    weight = int(r.params.get("penalty", 1))
    work = {}
    dev_under, dev_over = {}, {}

    for e in ctx.Employees:
        work[e] = m.NewIntVar(0, ctx.num_days, f"work_{e}")
        dev_under[e] = m.NewIntVar(0, ctx.num_days, f"dev_under_{e}")
        dev_over[e]  = m.NewIntVar(0, ctx.num_days, f"dev_over_{e}")
        m.Add(work[e] == sum(1 - ctx.off[(e, d)] for d in ctx.D))
        m.Add(work[e] + dev_under[e] - dev_over[e] == target)
        ctx.obj_terms.append(weight * (dev_under[e] + dev_over[e]))

    ctx.extras["workdays"] = work
