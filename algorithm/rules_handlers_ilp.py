from algorithm.rules_engine import Rule
from algorithm.contexts.ILPContext import ILPContext
import pulp


def i_one_shift_per_day(r: Rule, ctx: ILPContext):
    for f in ctx.employees:
        for d in ctx.dates:
            ctx.add_constraint(
                pulp.lpSum(ctx.x[f][d][t] for t in range(0, ctx.shifts + 1)) == 1,
                f"one_shift_day_f{f}_{d}"
            )


def i_total_workdays(r: Rule, ctx: ILPContext):
    total = int(r.params.get("total", 223))
    for f in ctx.employees:
        ctx.add_constraint(
            pulp.lpSum(ctx.x[f][d][s] for d in ctx.dates for s in range(1, ctx.shifts + 1)) == total,
            f"total_workdays_f{f}"
        )


def i_max_consecutive_days(r: Rule, ctx: ILPContext):
    max_consec = int(r.params.get("max", 5))
    for f in ctx.employees:
        for i in range(len(ctx.dates) - max_consec):
            window = ctx.dates[i:i + (max_consec + 1)]
            ctx.add_constraint(
                pulp.lpSum(ctx.x[f][d][s] for d in window for s in range(1, ctx.shifts + 1)) <= max_consec,
                f"max_consec_{f}_{ctx.dates[i]}"
            )


def i_max_special_days(r: Rule, ctx: ILPContext):
    cap = int(r.params.get("cap", 22))
    for f in ctx.employees:
        ctx.add_constraint(
            pulp.lpSum(ctx.x[f][d][s] for d in ctx.sundays_holidays for s in range(1, ctx.shifts + 1)) <= cap,
            f"max_special_days_f{f}"
        )


def i_no_earlier_shift_next_day(r: Rule, ctx: ILPContext):
    for f in ctx.employees:
        for i in range(len(ctx.dates) - 1):
            d_today = ctx.dates[i]
            d_next = ctx.dates[i + 1]
            for s_prev in range(1, ctx.shifts + 1):
                for s_next in range(1, ctx.shifts + 1):
                    if s_next < s_prev:
                        ctx.add_constraint(
                            ctx.x[f][d_today][s_prev] + ctx.x[f][d_next][s_next] <= 1,
                            f"no_earlier_f{f}_{d_today}_{s_prev}_to_{s_next}"
                        )


def i_vacation_block(r, ctx):
    """Forces employees to be OFF (x[f][d][0] == 1) on vacation days."""
    for f, vac_days in ctx.vacations.items():
        for d in vac_days:
            # support both integer days and Timestamp keys
            if isinstance(d, int):
                if 1 <= d <= len(ctx.dates):
                    d_key = ctx.dates[d - 1]
                else:
                    continue
            else:
                d_key = d

            if d_key in ctx.x[f]:
                ctx.model += (ctx.x[f][d_key][0] == 1,
                              f"vacation_off_f{f}_{d_key}")


def i_min_coverage(r: Rule, ctx: ILPContext):
    # create linkage between y and x per team/day/shift
    for d in ctx.dates:
        for s in range(1, ctx.shifts + 1):
            for team_code, members in ctx.teams.items():
                ctx.add_constraint(
                    ctx.y[d][s][team_code] == pulp.lpSum(ctx.x[f][d][s] for f in members),
                    f"count_{team_code}_{d}_S{s}"
                )

                minimo = ctx.min_required.get((d, team_code, s), 0)
                penal = pulp.LpVariable(f"penal_{d}_S{s}_{team_code}", lowBound=0, cat="Continuous")
                ctx.model += (penal >= minimo - ctx.y[d][s][team_code])
                ctx.model += penal  # part of objective
