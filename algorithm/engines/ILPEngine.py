import pulp
import pandas as pd
import holidays
from algorithm.engines.rules_engine import RuleEngine, register_default_ilp_handlers
from algorithm.contexts.ILPContext import ILPContext
from algorithm.utils import (
    rows_to_req_dicts,
    rows_to_vac_dict,
    get_team_code,
    get_team_id,
    export_schedule_to_csv,
)


class ILPEngine:
    def __init__(self, rules_config, *, num_days, shifts, employees, dates,
                 teams, vacations, sundays_holidays, min_required):
        self.model = pulp.LpProblem("ILP_Schedule", pulp.LpMinimize)
        self.x = {}
        self.y = {}
        self.employees = employees
        self.shifts = int(shifts)
        self.dates = list(dates)
        self.teams = teams                         # {team_code: [emp_idx]}
        self.vacations = vacations                 # {emp_idx: [1-based day ints or pd.Timestamp]}
        self.sundays_holidays = list(sundays_holidays)  # [pd.Timestamp]
        self.min_required = min_required           # {(date, team_code, shift): minimo}
        self.assignment = {}  # emp_id(1-based) -> list[(day, shift, team_id)]

        # --- Decision variables ---
        turnos = range(0, self.shifts + 1)  # 0=off, 1..shifts=working
        for f in employees:
            self.x[f] = {
                d: {t: pulp.LpVariable(f"x_{f}_{pd.Timestamp(d).strftime('%Y%m%d')}_{t}", cat="Binary")
                    for t in turnos}
                for d in self.dates
            }

        self.y = {
            d: {s: {team_code: pulp.LpVariable(f"y_{pd.Timestamp(d).strftime('%Y%m%d')}_{s}_{team_code}",
                                               lowBound=0, cat="Integer")
                    for team_code in teams.keys()}
                for s in range(1, self.shifts + 1)}
            for d in self.dates
        }

        # --- Rule Engine ---
        self.engine = RuleEngine(
            rules_config=rules_config,
            num_days=num_days,
            shifts=shifts,
            employees=employees,
            teams_map=teams,
            vacations_1based=vacations,             # handlers accept ints or timestamps
            special_days_1based=set(),              # not used in ILP; we pass actual timestamps in ctx
        )
        self._ilp_handlers = {}
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
            vacations=self.vacations,
            sundays_holidays=self.sundays_holidays,
            min_required=self.min_required,
        )

        from algorithm.rules.handlers.rules_handlers_ilp import i_one_shift_per_day
        i_one_shift_per_day(None, ctx) 
        self.engine.apply_ilp(ctx)

        # Assemble objective once from accumulated penalties
        if ctx.objective_terms:
            self.model += pulp.lpSum(ctx.objective_terms), "TotalPenalty"

        print(f"[DEBUG] ILP model built: {len(self.model.constraints)} constraints.")
        return ctx

    def solve(self, max_seconds=3600, gap_rel=0.005):
        """Runs PuLP solver and extracts assignments."""
        print(f"[DEBUG] Solving ILP model (timeLimit={max_seconds}s, gap={gap_rel})...")
        solver = pulp.PULP_CBC_CMD(msg=True, timeLimit=max_seconds, gapRel=gap_rel)
        status = self.model.solve(solver)
        print(f"[DEBUG] ILP Solver status: {pulp.LpStatus[status]}")

        # Extract assignments
        self.assignment = self._extract_assignments()
        return status

    def _extract_assignments(self):
        """Extract (day, shift, team_id) tuples for each employee."""
        assignment = {}
        for f in self.employees:
            emp_id = f + 1
            assignment[emp_id] = []
            # Infer team from membership
            team_code = next((tc for tc, members in self.teams.items() if f in members), "A")
            team_id = get_team_id(team_code)

            for day_idx, d in enumerate(self.dates, start=1):
                vals = [(t, pulp.value(self.x[f][d][t]) or 0.0) for t in range(0, self.shifts + 1)]
                t_sel = max(vals, key=lambda kv: kv[1])[0]
                if 1 <= t_sel <= self.shifts:
                    assignment[emp_id].append((day_idx, t_sel, team_id))
        return assignment

def solve(vacations, minimuns, employees, maxTime, year=2025, shifts=2, rules=None):
    print(f"\n[DEBUG] ===== Starting ILP Engine =====")
    print(f"[DEBUG] Year={year}, Shifts={shifts}, MaxTime={maxTime}, Employees={len(employees)}")

    mins, _ = rows_to_req_dicts(minimuns)       
    vacs_dict = rows_to_vac_dict(vacations)     

    teams = {}
    for idx, e in enumerate(employees):
        if not e.get("teams"):
            continue
        first_team = get_team_code(e["teams"][0])
        teams.setdefault(first_team, []).append(idx)

    # --- Convert vacations to 0-based employee → list[day ints]
    vac_0based = {emp_id - 1: days for emp_id, days in vacs_dict.items()}

    # --- Dates
    dates = pd.date_range(start=f"{year}-01-01", end=f"{year}-12-31")
    num_days = len(dates)

    # --- Sundays + PT Holidays
    feriados_pt = holidays.country_holidays("PT", years=[year])
    sundays_holidays = [d for d in dates if d.weekday() == 6 or d.date() in feriados_pt]

    # --- Remap mins from (day, shift, team_id) -> (date, team_code, shift)
    from algorithm.utils import TEAM_ID_TO_CODE, get_team_id  # ensure imported
    min_required = {}
    for (day, shift, team_id), val in mins.items():
        if 1 <= day <= num_days:
            date_key = dates[day - 1]
            team_code = TEAM_ID_TO_CODE.get(team_id)
            if team_code:
                min_required[(date_key, team_code, shift)] = int(val)

    # --- Initialize and solve ILP
    ilp_engine = ILPEngine(
        rules_config=rules or {},                 # JSON rule set
        num_days=num_days,
        shifts=shifts,
        employees=list(range(len(employees))),
        dates=dates,
        teams=teams,
        vacations=vac_0based,                    # handlers accept 1-based ints (translated inside)
        sundays_holidays=sundays_holidays,
        min_required=min_required,
    )

    ctx = ilp_engine.build()
    ilp_engine.solve(max_seconds=int(maxTime) * 60 if maxTime else 1800)

    # --- Export CSV (includes vacations)
    ilp_engine.vacs_1based = {i + 1: vac_0based.get(i, []) for i in ilp_engine.employees}
    ilp_engine.employees = [i + 1 for i in ilp_engine.employees]
    ilp_engine.assignment = ilp_engine.assignment

    export_schedule_to_csv(ilp_engine, filename="calendario_ilp.csv", num_days=num_days)

    # --- Return schedule table for Mongo
    from algorithm.utils import schedule_to_table
    schedule_data = schedule_to_table(
        employees=ilp_engine.employees,
        vacs=ilp_engine.vacs_1based,
        assignment=ilp_engine.assignment,
        num_days=num_days,
        shifts=ilp_engine.shifts,
    )
    return schedule_data
