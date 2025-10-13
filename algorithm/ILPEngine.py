import pulp
import pandas as pd
from algorithm.rules_engine import RuleEngine, register_default_ilp_handlers
from algorithm.contexts.ILPContext import ILPContext
from algorithm.utils import rows_to_req_dicts, rows_to_vac_dict, get_team_code


class ILPEngine:
    def __init__(self, rules_config, *, num_days, shifts, employees, dates,
                 teams, vacations, sundays_holidays, min_required):
        print(f"[DEBUG] Initializing ILPEngine | days={num_days}, shifts={shifts}, employees={len(employees)}")
        self.model = pulp.LpProblem("ILP_Schedule", pulp.LpMinimize)
        self.x = {}
        self.y = {}
        self.employees = employees
        self.shifts = int(shifts)
        self.dates = dates
        self.teams = teams
        self.vacations = vacations       # ✅ store vacation mapping (emp_id → list of days)
        self.sundays_holidays = sundays_holidays
        self.min_required = min_required

        # --- Decision variables ---
        turnos = range(0, self.shifts + 1)
        for f in employees:
            self.x[f] = {
                d: {t: pulp.LpVariable(f"x_{f}_{d}_{t}", cat="Binary") for t in turnos}
                for d in dates
            }

        self.y = {
            d: {s: {team_code: pulp.LpVariable(f"y_{d}_{s}_{team_code}", lowBound=0, cat="Integer")
                    for team_code in teams.keys()}
                for s in range(1, self.shifts + 1)}
            for d in dates
        }

        # --- Rule Engine ---
        self.engine = RuleEngine(
            rules_config=rules_config,
            num_days=num_days,
            shifts=shifts,
            employees=employees,
            teams_map=teams,
            vacations_1based=vacations,  # ✅ pass vacations here as well
            special_days_1based=sundays_holidays,
        )
        register_default_ilp_handlers(self.engine)
        print(f"[DEBUG] ILPEngine rule handlers registered ({len(self.engine.rules)} rules).")

    def build(self):
        """Applies all ILP rule handlers to build the model constraints."""
        ctx = ILPContext(
            model=self.model,
            x=self.x,
            y=self.y,
            employees=self.employees,
            dates=self.dates,
            shifts=self.shifts,
            teams=self.teams,
            vacations=self.vacations,            # ✅ propagate to context
            sundays_holidays=self.sundays_holidays,
            min_required=self.min_required,
        )

        self.engine.apply_ilp(ctx)
        print(f"[DEBUG] ILP model built: {len(self.model.constraints)} constraints.")
        return ctx

    def solve(self, max_seconds=3600, gap_rel=0.005):
        """Runs PuLP solver and returns optimization status."""
        print(f"[DEBUG] Solving ILP model (timeLimit={max_seconds}s, gap={gap_rel})...")
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=max_seconds, gapRel=gap_rel)
        status = self.model.solve(solver)
        print(f"[DEBUG] ILP Solver status: {pulp.LpStatus[status]}")
        return status


# =============================================================
# ✅ Drop-in entrypoint (TaskManager-compatible)
# =============================================================
def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2, rules=None):
    from algorithm.utils import get_team_code

    print(f"\n[DEBUG] ===== Starting ILP Engine =====")
    print(f"[DEBUG] Year={year}, Shifts={shifts}, MaxTime={maxTime}, Employees={len(employees)}")

    # --- Parse inputs ---
    mins, _ = rows_to_req_dicts(minimuns)
    vacs_dict = rows_to_vac_dict(vacations)

    # build basic team structure
    teams = {}
    for idx, e in enumerate(employees):
        if not e.get("teams"):
            continue
        first_team = get_team_code(e["teams"][0])
        teams.setdefault(first_team, []).append(idx)

    # convert vacation dict into 0-based employee → list of day indices
    vac_0based = {emp_id - 1: days for emp_id, days in vacs_dict.items()}

    ilp_engine = ILPEngine(
        rules_config=rules or {},
        num_days=365,
        shifts=shifts,
        employees=list(range(len(employees))),
        dates=pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31"),
        teams=teams,
        vacations=vac_0based,                 # ✅ now passed here
        sundays_holidays=[],                  # you can fill with computed holidays if needed
        min_required=mins,
    )

    ctx = ilp_engine.build()
    ilp_engine.solve(max_seconds=int(maxTime) * 60 if maxTime else 1800)

    print(f"[DEBUG] ===== ILP Engine COMPLETE =====\n")
    return ctx.model
