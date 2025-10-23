from algorithm.rules_engine import Rule
from algorithm.contexts.GreedyContext import GreedyContext

def g_no_earlier_shift_next_day(r: Rule, ctx: GreedyContext):
    e, d, s = ctx.e, ctx.d, ctx.s
    prev_shift = ctx.get_shift(e, d - 1)
    next_shift = ctx.get_shift(e, d + 1)
    if prev_shift and prev_shift > s:
        return False
    if next_shift and next_shift < s:
        return False
    return True



def g_max_consecutive_days(r: Rule, ctx: GreedyContext):
    """
    Reject if adding (e,d) causes more than 'max_worked' consecutive workdays.
    """
    e, d = ctx.e, ctx.d
    window = int(r.params.get("window", 6))
    max_in = int(r.params.get("max_worked", 5))

    worked = sorted(ctx.get_days_worked(e) + [d])
    consecutive = 1
    for i in range(1, len(worked)):
        if worked[i] == worked[i - 1] + 1:
            consecutive += 1
            if consecutive > max_in:
                return False
        else:
            consecutive = 1
    return True



def g_max_special_days(r: Rule, ctx: GreedyContext):
    """
    Reject assignment if it would exceed the maximum allowed holidays+Sundays.
    """
    e, d = ctx.e, ctx.d
    cap = int(r.params.get("cap", 22))
    special_days = ctx.special_days

    worked_special = sum(1 for day in ctx.get_days_worked(e) if day in special_days)
    if d in special_days:
        worked_special += 1
    return worked_special <= cap


def g_total_workdays(r: Rule, ctx: GreedyContext):
    e = ctx.e
    max_days = int(r.params.get("max", 223))
    min_days = int(r.params.get("min", 0))
    current = len(ctx.get_days_worked(e)) + 1  # +1 for proposed assignment
    if current > max_days:
        return False
    if current < min_days:
        # still building, always okay
        return True
    return True


def g_vacation_block(r: Rule, ctx: GreedyContext):
    """Reject if day is in employee vacation days."""
    e, d = ctx.e, ctx.d
    return d not in ctx.vacations.get(e, [])


def g_team_eligibility(r: Rule, ctx: GreedyContext):
    """Reject if team not allowed for employee."""
    e, t = ctx.e, ctx.t
    return t in ctx.allowed_teams_per_emp[e - 1]


def g_min_coverage(r: Rule, ctx: GreedyContext):
    """
    Compute coverage score for (day,shift,team).
    Used for heuristic ranking instead of hard rejection.
    """
    d, s, t = ctx.d, ctx.s, ctx.t
    kind = r.kind.lower()
    min_required = ctx.min_required.get((d, s, t), 0)
    ideal = ctx.ideal_required.get((d, s, t), min_required)
    current = ctx.cover_count.get((d, s, t), 0)

    if current < min_required:
        ctx.add_score(0 if kind == "hard" else 1)
    elif current < ideal:
        ctx.add_score(2)
    else:
        ctx.add_score(3 + (current - ideal))
    return True


def g_target_workdays_balancing(r: Rule, ctx: GreedyContext):
    """
    Adds soft penalty for deviating from target workdays.
    This does not reject — it influences the score.
    """
    e = ctx.e
    target = int(r.params.get("target", 223))
    weight = int(r.params.get("penalty", 1))
    current = len(ctx.get_days_worked(e)) + 1
    deviation = abs(current - target)
    ctx.add_score(weight * deviation)
    return True
