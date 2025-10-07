from ortools.sat.python import cp_model
from algorithm.rules_engine import Rule, CPSatContext

def h_no_earlier_shift_next_day(r: Rule, ctx: CPSatContext):
    # kind must be hard; params unused
    m = ctx.m
    for e in ctx.Employees:
        for day in range(1, ctx.num_days):
            m.Add(ctx.shift_id[(e, day+1)] >= ctx.shift_id[(e, day)]).OnlyEnforceIf(
                [ctx.off[(e, day)].Not(), ctx.off[(e, day+1)].Not()]
            )

def h_max_consecutive_days(r: Rule, ctx: CPSatContext):
    m = ctx.m
    window = int(r.params.get("window", 6))
    max_in = int(r.params.get("max_worked", 5))
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
    m = ctx.m
    total_workdays = int(r.params.get("total", 223))
    for e in ctx.Employees:
        m.Add(sum(1 - ctx.off[(e, d)] for d in ctx.D) == total_workdays)
        
def h_vacation_block(r: Rule, ctx: CPSatContext):
    # already enforced structurally via vac_mask in the "exactly one" constraint
    # nothing to add here; documented to show rule is acknowledged.
    return

def h_team_eligibility(r: Rule, ctx: CPSatContext):
    # already enforced structurally by only creating y[(e,d,s,t)] for allowed teams
    return

def h_min_coverage(r: Rule, ctx: CPSatContext):
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
        else:  # hard
            m.Add(sum(cover) >= req)

def h_target_workdays_balancing(r: Rule, ctx: CPSatContext):
    """
    Soft fairness around target_workdays using under/over deviations.
    """
    m = ctx.m
    target = int(r.params.get("target", 223))
    weight = int(r.params.get("penalty", 1))
    work = {}
    dev_under, dev_over = {}, {}
    for e in ctx.Employees:
        work[e] = m.NewIntVar(0, target, f"work_{e}")
        dev_under[e] = m.NewIntVar(0, target, f"dev_under_{e}")
        dev_over[e]  = m.NewIntVar(0, target, f"dev_over_{e}")
        m.Add(work[e] == sum(1 - ctx.off[(e, d)] for d in ctx.D))
        m.Add(work[e] + dev_under[e] - dev_over[e] == target)
        ctx.obj_terms.append(weight * (dev_under[e] + dev_over[e]))
    # stash for reading later if you want:
    ctx.extras["workdays"] = work
