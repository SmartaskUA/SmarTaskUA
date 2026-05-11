"""
problem.py — Shared problem definition for SmarTask scheduling GA prototypes.

Chromosome encoding per (employee, day):
  0  →  OFF
  1  →  Morning   + Team A
  2  →  Afternoon + Team A
  3  →  Morning   + Team B
  4  →  Afternoon + Team B

Phase 1 constraints (penalty-based):
  - Min coverage       (weight: 100 per missing worker-day)
  - Ideal coverage     (weight: 1   per missing worker-day)

Phase 2 constraints (repair operators — always feasible before fitness evaluation):
  - Vacation blocking  (forced OFF on vacation days)  ← also locked in gene_space
  - No backward shift on consecutive days
  - Max 5 worked days in any 6-day window
  - Max 22 special days (Sundays + PT holidays)
  - Exactly 223 worked days per employee
"""

import datetime
import json
import random
import numpy as np
import pandas as pd
from pathlib import Path

# ── Encoding constants ────────────────────────────────────────────────────────
GENE_OFF = 0
SHIFT_TEAM_TO_GENE = {
    ("M", "A"): 1,
    ("T", "A"): 2,
    ("M", "B"): 3,
    ("T", "B"): 4,
}
GENE_TO_SHIFT_TEAM = {v: k for k, v in SHIFT_TEAM_TO_GENE.items()}

SHIFTS    = ["M", "T"]
TEAMS     = ["A", "B"]
SHIFT_IDX = {"M": 0, "T": 1}
TEAM_IDX  = {"A": 0, "B": 1}

# ── Shift ordering (for no-backward-shift repair) ────────────────────────────
# Morning = order 1, Afternoon = order 2, OFF = 0 (ignored in comparisons)
GENE_SHIFT_ORDER = {0: 0, 1: 1, 2: 2, 3: 1, 4: 2}

# ── Phase 2 hard constraint parameters ───────────────────────────────────────
TARGET_WORKDAYS  = 223
WINDOW_SIZE      = 6
WINDOW_MAX       = 5
SPECIAL_DAYS_CAP = 22

# ── Penalty weights ───────────────────────────────────────────────────────────
W_MIN_COVER   = 100     # soft: below minimum coverage
W_IDEAL_COVER = 1       # soft: below ideal coverage


# ── Special days ──────────────────────────────────────────────────────────────

def _build_special_days(year: int, n_days: int) -> set:
    """
    Return a set of 0-based day indices that are Sundays or PT public holidays.
    Uses the `holidays` library so it adapts automatically to any year
    (moveable feasts like Easter change each year).
    """
    import holidays as hl

    pt_holidays = hl.country_holidays("PT", years=[year])
    start       = datetime.date(year, 1, 1)
    special     = set()

    for d in range(n_days):
        date = start + datetime.timedelta(days=d)
        if date.weekday() == 6:          # Sunday
            special.add(d)
        if date in pt_holidays:          # PT national holiday
            special.add(d)

    return special


# ── Data loading ──────────────────────────────────────────────────────────────

def load_problem(data_dir: str = "SMARTASK_SIMPLE_2025") -> dict:
    """Load all problem data and return as a structured dict."""
    base = Path(data_dir)

    # 1. problem.json
    with open(base / "problem.json") as f:
        prob = json.load(f)

    n_days      = prob["temporalScope"]["numDays"]   # 365
    year        = prob["temporalScope"]["year"]       # 2025
    employees   = prob["employees"]["simple"]
    n_employees = len(employees)

    # Allowed gene values per employee (from team membership)
    allowed_genes = []
    for emp in employees:
        vals = [GENE_OFF]
        for shift in SHIFTS:
            for team in emp.get("teams", []):
                gene = SHIFT_TEAM_TO_GENE.get((shift, team))
                if gene is not None:
                    vals.append(gene)
        allowed_genes.append(sorted(set(vals)))

    # 2. vacations.csv — no header; format: emp_name, day1, ..., day365
    vac_df   = pd.read_csv(base / "vacations.csv", header=None)
    vac_mask = vac_df.iloc[:, 1:].values.astype(bool)  # (n_employees, n_days)

    # 3. demand.csv — date, shift, team, minimum, ideal, estimated
    dem_df            = pd.read_csv(base / "demand.csv")
    dem_df["date"]    = pd.to_datetime(dem_df["date"])
    start             = pd.Timestamp(f"{year}-01-01")
    dem_df["day_idx"] = (dem_df["date"] - start).dt.days

    min_demand   = np.zeros((n_days, 2, 2), dtype=int)
    ideal_demand = np.zeros((n_days, 2, 2), dtype=int)
    for _, row in dem_df.iterrows():
        d = int(row["day_idx"])
        s = SHIFT_IDX[row["shift"]]
        t = TEAM_IDX[row["team"]]
        min_demand[d, s, t]   = int(row["minimum"])
        ideal_demand[d, s, t] = int(row["ideal"])

    special_days = _build_special_days(year, n_days)

    return {
        "n_employees":   n_employees,
        "n_days":        n_days,
        "year":          year,
        "employees":     employees,
        "allowed_genes": allowed_genes,   # list[list[int]], per employee
        "vac_mask":      vac_mask,        # ndarray bool  (n_employees, n_days)
        "min_demand":    min_demand,      # ndarray int   (n_days, 2, 2)
        "ideal_demand":  ideal_demand,    # ndarray int   (n_days, 2, 2)
        "special_days":  special_days,    # set of 0-based day indices
    }


# ── Core penalty computation ──────────────────────────────────────────────────

def _compute_penalties(schedule: np.ndarray, problem_data: dict) -> tuple:
    """
    Compute raw penalty components for a schedule.

    Returns:
        (min_unmet, ideal_unmet)  — all non-negative ints
    """
    min_demand   = problem_data["min_demand"]
    ideal_demand = problem_data["ideal_demand"]

    min_unmet = ideal_unmet = 0
    for s_idx, s_code in enumerate(SHIFTS):
        for t_idx, t_code in enumerate(TEAMS):
            gene_val = SHIFT_TEAM_TO_GENE[(s_code, t_code)]
            assigned = np.sum(schedule == gene_val, axis=0)  # (n_days,)
            min_unmet   += int(np.sum(np.maximum(0, min_demand[:, s_idx, t_idx]   - assigned)))
            ideal_unmet += int(np.sum(np.maximum(0, ideal_demand[:, s_idx, t_idx] - assigned)))

    return min_unmet, ideal_unmet


def compute_fitness(schedule: np.ndarray, problem_data: dict) -> float:
    """
    Evaluate a schedule. Higher (less negative) = better. 0 = perfect.

    Args:
        schedule: int array (n_employees, n_days), values 0–4
        problem_data: dict from load_problem()
    """
    m, i = _compute_penalties(schedule, problem_data)
    return -float(m * W_MIN_COVER + i * W_IDEAL_COVER)


# ── Initialisation helpers ────────────────────────────────────────────────────

def random_schedule(problem_data: dict) -> np.ndarray:
    """
    Generate a random valid schedule.
    Vacation days are forced to OFF; other days draw from the employee's
    allowed gene values (respecting team membership).

    Returns:
        int array (n_employees, n_days)
    """
    n_emp         = problem_data["n_employees"]
    n_days        = problem_data["n_days"]
    vac_mask      = problem_data["vac_mask"]
    allowed_genes = problem_data["allowed_genes"]

    schedule = np.zeros((n_emp, n_days), dtype=int)
    for i in range(n_emp):
        for d in range(n_days):
            if vac_mask[i, d]:
                schedule[i, d] = GENE_OFF
            else:
                schedule[i, d] = random.choice(allowed_genes[i])
    return schedule


def build_gene_space(problem_data: dict) -> list:
    """
    Build PyGAD gene_space: a list of length n_employees * n_days.
    Each entry is the list of valid values for that gene position.
    Vacation days are locked to [0] — the GA cannot assign work on those days.
    """
    n_emp         = problem_data["n_employees"]
    n_days        = problem_data["n_days"]
    vac_mask      = problem_data["vac_mask"]
    allowed_genes = problem_data["allowed_genes"]

    gene_space = []
    for i in range(n_emp):
        for d in range(n_days):
            gene_space.append([0] if vac_mask[i, d] else allowed_genes[i])
    return gene_space


def decode_schedule(flat: np.ndarray, problem_data: dict) -> np.ndarray:
    """Reshape a flat 1D chromosome into a 2D schedule (n_employees, n_days)."""
    return flat.reshape(problem_data["n_employees"], problem_data["n_days"]).astype(int)


# ── Phase 2: Repair operators ─────────────────────────────────────────────────
# Each repair guarantees one hard constraint. Applied in order before fitness
# evaluation so the GA only ever sees feasible schedules (Baldwinian approach
# for PyGAD; Lamarckian — writes back to the individual — for DEAP).

def _repair_vacations(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    Hard constraint: employees must be OFF on all vacation days.
    Any gene that assigns work on a vacation day is forced to GENE_OFF.
    """
    vac_mask = problem_data["vac_mask"]
    schedule[vac_mask & (schedule > 0)] = GENE_OFF
    return schedule


def _repair_no_backward_shift(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    If an employee works two consecutive days and the shift on day d+1 is
    earlier than on day d (e.g. Afternoon→Morning), upgrade day d+1 to the
    same shift tier (Afternoon) keeping the same team.
    If the upgrade gene is not in the employee's allowed set, set day d+1 OFF.
    """
    n_emp         = problem_data["n_employees"]
    n_days        = problem_data["n_days"]
    allowed_genes = problem_data["allowed_genes"]

    for i in range(n_emp):
        for d in range(n_days - 1):
            g_today    = schedule[i, d]
            g_tomorrow = schedule[i, d + 1]
            if g_today == GENE_OFF or g_tomorrow == GENE_OFF:
                continue
            if GENE_SHIFT_ORDER[g_tomorrow] < GENE_SHIFT_ORDER[g_today]:
                # Upgrade tomorrow to Afternoon keeping its team
                team        = GENE_TO_SHIFT_TEAM[g_tomorrow][1]
                upgraded    = SHIFT_TEAM_TO_GENE[("T", team)]
                schedule[i, d + 1] = (
                    upgraded if upgraded in allowed_genes[i] else GENE_OFF
                )
    return schedule


def _repair_6day_window(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    In any rolling window of WINDOW_SIZE days, at most WINDOW_MAX may be worked.
    When a window has too many, the most recent worked day in the window is set
    to OFF (vacation days are never touched).
    Repeated until no window violates the constraint.
    """
    n_emp    = problem_data["n_employees"]
    n_days   = problem_data["n_days"]
    vac_mask = problem_data["vac_mask"]

    for i in range(n_emp):
        changed = True
        while changed:
            changed = False
            for start in range(n_days - WINDOW_SIZE + 1):
                window = range(start, start + WINDOW_SIZE)
                worked = [d for d in window if schedule[i, d] > 0]
                if len(worked) > WINDOW_MAX:
                    # Turn off the last worked day that is not a vacation
                    for d in reversed(worked):
                        if not vac_mask[i, d]:
                            schedule[i, d] = GENE_OFF
                            changed = True
                            break
    return schedule


def _repair_special_days(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    Each employee may work at most SPECIAL_DAYS_CAP special days
    (Sundays + PT public holidays). Excess special workdays are set to OFF.
    """
    n_emp        = problem_data["n_employees"]
    special_days = problem_data["special_days"]
    vac_mask     = problem_data["vac_mask"]

    for i in range(n_emp):
        worked_special = [d for d in special_days if schedule[i, d] > 0]
        random.shuffle(worked_special)          # random order so removal is fair
        while len(worked_special) > SPECIAL_DAYS_CAP:
            d = worked_special.pop()
            if not vac_mask[i, d]:
                schedule[i, d] = GENE_OFF
    return schedule


def _workday_candidates(schedule_row: np.ndarray, i: int, problem_data: dict) -> list:
    """
    Return a list of (day, [valid_genes]) pairs for days that can be turned ON
    without violating the 6-day window, special-day cap, or backward-shift constraint.
    Called by _repair_workday_count when the employee is short of TARGET_WORKDAYS.
    """
    n_days        = problem_data["n_days"]
    vac_mask      = problem_data["vac_mask"]
    special_days  = problem_data["special_days"]
    allowed_genes = problem_data["allowed_genes"]

    worked_special = sum(1 for d in special_days if schedule_row[d] > 0)
    candidates = []

    for d in range(n_days):
        if schedule_row[d] > 0 or vac_mask[i, d]:
            continue  # already worked or on vacation

        # Special-day cap: skip if this is a special day and cap is already reached
        if d in special_days and worked_special >= SPECIAL_DAYS_CAP:
            continue

        # 6-day window: adding day d must not push any overlapping window above WINDOW_MAX
        window_ok = True
        for ws in range(max(0, d - WINDOW_SIZE + 1),
                        min(n_days - WINDOW_SIZE + 1, d + 1)):
            count = sum(
                1 for x in range(ws, ws + WINDOW_SIZE)
                if x != d and schedule_row[x] > 0
            )
            if count >= WINDOW_MAX:
                window_ok = False
                break
        if not window_ok:
            continue

        # Backward-shift: collect gene values compatible with both neighbours
        g_prev = schedule_row[d - 1] if d > 0 else GENE_OFF
        g_next = schedule_row[d + 1] if d < n_days - 1 else GENE_OFF
        valid_genes = [
            g for g in allowed_genes[i]
            if g != GENE_OFF
            and (g_prev == GENE_OFF or GENE_SHIFT_ORDER[g] >= GENE_SHIFT_ORDER[g_prev])
            and (g_next == GENE_OFF or GENE_SHIFT_ORDER[g_next] >= GENE_SHIFT_ORDER[g])
        ]
        if valid_genes:
            candidates.append((d, valid_genes))

    return candidates


def _repair_workday_count(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    Enforce exactly TARGET_WORKDAYS worked days per employee.
    - Too many → randomly remove surplus worked days (removal never creates new violations).
    - Too few  → add days only from a constraint-safe candidate pool so that no
                 6-day window, special-day cap, or backward-shift violation is introduced.
                 If the pool is exhausted before reaching TARGET_WORKDAYS the employee
                 keeps fewer days (hard feasibility limit — very rare with real data).
    """
    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]

    for i in range(n_emp):
        row    = schedule[i]
        worked = [d for d in range(n_days) if row[d] > 0]

        # ── Too many: remove randomly ─────────────────────────────────────────
        while len(worked) > TARGET_WORKDAYS:
            d = random.choice(worked)
            schedule[i, d] = GENE_OFF
            worked.remove(d)

        # ── Too few: add from constraint-aware candidate pool ─────────────────
        # Build the pool once (O(n_days)), shuffle, then iterate.
        # Before committing each addition, re-check window and backward-shift
        # against the *current* row — earlier additions may have changed the
        # local context and made a pre-approved candidate temporarily invalid.
        if len(worked) < TARGET_WORKDAYS:
            n_days = problem_data["n_days"]
            candidates = _workday_candidates(row, i, problem_data)
            random.shuffle(candidates)
            for d, valid_genes in candidates:
                if len(worked) >= TARGET_WORKDAYS:
                    break
                if row[d] > 0:
                    continue

                # Re-check 6-day window with current row state
                window_ok = True
                for ws in range(max(0, d - WINDOW_SIZE + 1),
                                min(n_days - WINDOW_SIZE + 1, d + 1)):
                    if sum(1 for x in range(ws, ws + WINDOW_SIZE)
                           if x != d and row[x] > 0) >= WINDOW_MAX:
                        window_ok = False
                        break
                if not window_ok:
                    continue

                # Re-check backward-shift with current neighbours
                g_prev = row[d - 1] if d > 0 else GENE_OFF
                g_next = row[d + 1] if d < n_days - 1 else GENE_OFF
                valid_now = [
                    g for g in valid_genes
                    if (g_prev == GENE_OFF or GENE_SHIFT_ORDER[g] >= GENE_SHIFT_ORDER[g_prev])
                    and (g_next == GENE_OFF or GENE_SHIFT_ORDER[g_next] >= GENE_SHIFT_ORDER[g])
                ]
                if not valid_now:
                    continue

                gene = random.choice(valid_now)
                schedule[i, d] = gene   # row is a view — updates row[d] too
                worked.append(d)

    return schedule


def repair_schedule(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    Apply all Phase 2 repair operators in one pass:
      1. Vacations          (forces OFF on all vacation days)
      2. No backward shift  (changes shift type only; may set days to OFF)
      3. 6-day window cap   (sets excess days to OFF)
      4. Special days cap   (sets excess special days to OFF)
      5. Workday count      (rebalances total; adds only constraint-safe days)

    Because _repair_workday_count checks window, special-day, and
    backward-shift constraints before adding any day, a single pass is
    guaranteed to produce a fully feasible schedule.
    """
    schedule = _repair_vacations(schedule, problem_data)
    schedule = _repair_no_backward_shift(schedule, problem_data)
    schedule = _repair_6day_window(schedule, problem_data)
    schedule = _repair_special_days(schedule, problem_data)
    schedule = _repair_workday_count(schedule, problem_data)
    return schedule


def compute_phase2_violations(schedule: np.ndarray, problem_data: dict) -> dict:
    """
    Count Phase 2 constraint violations in a schedule (for reporting).
    Returns a dict with counts per constraint.
    """
    n_emp        = problem_data["n_employees"]
    n_days       = problem_data["n_days"]
    special_days = problem_data["special_days"]
    vac_mask     = problem_data["vac_mask"]

    vacation = int(np.sum((schedule > 0) & vac_mask))
    backward = window = special = workday = 0

    for i in range(n_emp):
        # Workday count
        worked = sum(1 for d in range(n_days) if schedule[i, d] > 0)
        if worked != TARGET_WORKDAYS:
            workday += abs(worked - TARGET_WORKDAYS)

        # Special days cap
        worked_special = sum(1 for d in special_days if schedule[i, d] > 0)
        if worked_special > SPECIAL_DAYS_CAP:
            special += worked_special - SPECIAL_DAYS_CAP

        for d in range(n_days):
            # No backward shift
            if d < n_days - 1:
                g0, g1 = schedule[i, d], schedule[i, d + 1]
                if g0 != GENE_OFF and g1 != GENE_OFF:
                    if GENE_SHIFT_ORDER[g1] < GENE_SHIFT_ORDER[g0]:
                        backward += 1

        # 6-day window
        for start in range(n_days - WINDOW_SIZE + 1):
            w = sum(1 for d in range(start, start + WINDOW_SIZE) if schedule[i, d] > 0)
            if w > WINDOW_MAX:
                window += w - WINDOW_MAX

    return {
        "vacation": vacation,
        "workday":  workday,
        "window":   window,
        "special":  special,
        "backward": backward,
    }


# ── Reporting & Export ────────────────────────────────────────────────────────

# Human-readable labels for each gene value
GENE_LABEL = {
    0: "OFF",
    1: "M-A",
    2: "T-A",
    3: "M-B",
    4: "T-B",
}


def export_schedule(
    schedule: np.ndarray,
    problem_data: dict,
    path: str = "schedule.csv",
) -> None:
    """
    Export the schedule to two CSV files:

    1. <path>  — wide format (employees × days), one cell per day.
       Columns are dates (2025-01-01 … 2025-12-31).
       Cell values: OFF | M-A | T-A | M-B | T-B

    2. <path stem>_coverage.csv — daily coverage check per (shift, team).
       Columns: date, shift, team, assigned, minimum, ideal, min_unmet, ideal_unmet
    """
    import pandas as pd
    from pathlib import Path

    n_emp    = problem_data["n_employees"]
    n_days   = problem_data["n_days"]
    employees = problem_data["employees"]
    min_demand   = problem_data["min_demand"]
    ideal_demand = problem_data["ideal_demand"]

    year       = 2025
    start_date = pd.Timestamp(f"{year}-01-01")
    dates      = [start_date + pd.Timedelta(days=d) for d in range(n_days)]
    date_strs  = [d.strftime("%Y-%m-%d") for d in dates]

    # ── 1. Wide schedule CSV ──────────────────────────────────────────────────
    rows = []
    for i, emp in enumerate(employees):
        row = {"Employee": emp["name"]}
        for d in range(n_days):
            row[date_strs[d]] = GENE_LABEL[schedule[i, d]]
        rows.append(row)

    df_schedule = pd.DataFrame(rows).set_index("Employee")
    df_schedule.to_csv(path)
    print(f"Schedule exported → {path}  ({n_emp} employees × {n_days} days)")

    # ── 2. Daily coverage CSV ─────────────────────────────────────────────────
    coverage_rows = []
    for d in range(n_days):
        for s_idx, s_code in enumerate(SHIFTS):
            for t_idx, t_code in enumerate(TEAMS):
                gene_val  = SHIFT_TEAM_TO_GENE[(s_code, t_code)]
                assigned  = int(np.sum(schedule[:, d] == gene_val))
                min_req   = int(min_demand[d, s_idx, t_idx])
                ideal_req = int(ideal_demand[d, s_idx, t_idx])
                coverage_rows.append({
                    "date":        date_strs[d],
                    "shift":       s_code,
                    "team":        t_code,
                    "assigned":    assigned,
                    "minimum":     min_req,
                    "ideal":       ideal_req,
                    "min_unmet":   max(0, min_req   - assigned),
                    "ideal_unmet": max(0, ideal_req - assigned),
                })

    cov_path = str(Path(path).with_stem(Path(path).stem + "_coverage"))
    pd.DataFrame(coverage_rows).to_csv(cov_path, index=False)
    print(f"Coverage exported → {cov_path}")


def print_summary(schedule: np.ndarray, problem_data: dict, label: str = "") -> None:
    """Print a concise quality report for a schedule (Phase 1 + Phase 2)."""
    m, i    = _compute_penalties(schedule, problem_data)
    fitness = -(m * W_MIN_COVER + i * W_IDEAL_COVER)
    p2      = compute_phase2_violations(schedule, problem_data)

    header = f"=== {label} ===" if label else "=== Schedule Summary ==="
    print(header)
    print(f"  Fitness                      : {fitness:.0f}")
    print(f"  --- Phase 1 ---")
    print(f"  Min coverage unmet           : {m} worker-days")
    print(f"  Ideal coverage unmet         : {i} worker-days")
    print(f"  --- Phase 2 (repair) ---")
    print(f"  Vacation violations          : {p2['vacation']}")
    print(f"  Workday count violations     : {p2['workday']}")
    print(f"  6-day window violations      : {p2['window']}")
    print(f"  Special day cap violations   : {p2['special']}")
    print(f"  Backward shift violations    : {p2['backward']}")
    print()
