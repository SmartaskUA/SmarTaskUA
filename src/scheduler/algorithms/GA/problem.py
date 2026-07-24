"""
problem.py — Shared problem definition for SmarTask scheduling GA prototypes.

Chromosome encoding per (employee, day):
  0        →  OFF
  1, 2     →  Morning / Afternoon + Team A
  3, 4     →  Morning / Afternoon + Team B
  2k-1, 2k →  Morning / Afternoon + Team k   (generalises to N teams)

The exact gene→(shift, team) mapping is built dynamically from problem.json
and stored inside problem_data so that any number of teams is supported.

Phase 1 constraints (penalty-based):
  - Min coverage       (weight: 100 per missing worker-day)
  - Ideal coverage     (weight: 1   per missing worker-day)

Phase 2 constraints (repair operators — always feasible before fitness evaluation):
  - Vacation blocking  (forced OFF on vacation days)
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

# ── Constants that do NOT depend on the number of teams ──────────────────────
GENE_OFF  = 0
SHIFTS    = ["M", "T"]
SHIFT_IDX = {"M": 0, "T": 1}

# ── Phase 2 hard constraint parameters ───────────────────────────────────────
TARGET_WORKDAYS  = 223
WINDOW_SIZE      = 6
WINDOW_MAX       = 5
SPECIAL_DAYS_CAP = 22

# ── Penalty weights ───────────────────────────────────────────────────────────
W_MIN_COVER   = 100
W_IDEAL_COVER = 1


# ── Special days ──────────────────────────────────────────────────────────────

def _build_special_days(year: int, n_days: int) -> set:
    """
    Return a set of 0-based day indices that are Sundays or PT public holidays.
    """
    import holidays as hl

    pt_holidays = hl.country_holidays("PT", years=[year])
    start       = datetime.date(year, 1, 1)
    special     = set()

    for d in range(n_days):
        date = start + datetime.timedelta(days=d)
        if date.weekday() == 6:
            special.add(d)
        if date in pt_holidays:
            special.add(d)

    return special


def _build_encoding(teams: list[str]) -> dict:
    """
    Build gene encoding lookups for a given list of teams.

    Returns a dict with:
        shift_team_to_gene  : {(shift, team) -> int}
        gene_to_shift_team  : {int -> (shift, team)}
        team_idx            : {team -> int}
        gene_shift_order    : {gene -> int}  (0=OFF, 1=Morning, 2=Afternoon)
        gene_label          : {gene -> str}  human-readable
    """
    shift_team_to_gene: dict[tuple, int] = {}
    gene_idx = 1
    for team in teams:
        for shift in SHIFTS:
            shift_team_to_gene[(shift, team)] = gene_idx
            gene_idx += 1

    gene_to_shift_team = {v: k for k, v in shift_team_to_gene.items()}
    team_idx           = {team: i for i, team in enumerate(teams)}

    gene_shift_order = {GENE_OFF: 0}
    for gene, (shift, _) in gene_to_shift_team.items():
        gene_shift_order[gene] = SHIFTS.index(shift) + 1   # M→1, T→2

    gene_label = {GENE_OFF: "OFF"}
    for gene, (shift, team) in gene_to_shift_team.items():
        gene_label[gene] = f"{shift}-{team}"

    return {
        "shift_team_to_gene": shift_team_to_gene,
        "gene_to_shift_team": gene_to_shift_team,
        "team_idx":           team_idx,
        "gene_shift_order":   gene_shift_order,
        "gene_label":         gene_label,
    }


# ── Data loading ──────────────────────────────────────────────────────────────

def load_problem(data_dir: str = "SMARTASK_SIMPLE_2025") -> dict:
    """Load all problem data and return as a structured dict."""
    base = Path(data_dir)

    # 1. problem.json
    with open(base / "problem.json") as f:
        prob = json.load(f)

    n_days      = prob["temporalScope"]["numDays"]
    year        = prob["temporalScope"]["year"]
    employees   = prob["employees"]["simple"]
    n_employees = len(employees)
    teams       = prob["demand"]["organizationalUnits"]["teams"]
    n_teams     = len(teams)

    # Build gene encoding for this scenario
    enc = _build_encoding(teams)
    shift_team_to_gene = enc["shift_team_to_gene"]
    team_idx           = enc["team_idx"]

    # Allowed gene values per employee (from team membership)
    allowed_genes = []
    for emp in employees:
        vals = [GENE_OFF]
        for shift in SHIFTS:
            for team in emp.get("teams", []):
                gene = shift_team_to_gene.get((shift, team))
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

    min_demand   = np.zeros((n_days, len(SHIFTS), n_teams), dtype=int)
    ideal_demand = np.zeros((n_days, len(SHIFTS), n_teams), dtype=int)
    for _, row in dem_df.iterrows():
        d = int(row["day_idx"])
        s = SHIFT_IDX[row["shift"]]
        t = team_idx[row["team"]]
        min_demand[d, s, t]   = int(row["minimum"])
        ideal_demand[d, s, t] = int(row["ideal"])

    special_days = _build_special_days(year, n_days)

    # O1 — precomputed gene→(shift_idx, team_idx) lookup arrays for fast indexing
    gene_to_shift_team = enc["gene_to_shift_team"]
    max_gene = max(gene_to_shift_team.keys()) if gene_to_shift_team else 0
    gene_shift_arr = np.zeros(max_gene + 1, dtype=np.int32)
    gene_team_arr  = np.zeros(max_gene + 1, dtype=np.int32)
    for g, (s_code, t_code) in gene_to_shift_team.items():
        gene_shift_arr[g] = SHIFT_IDX[s_code]
        gene_team_arr[g]  = team_idx[t_code]

    return {
        "n_employees":       n_employees,
        "n_days":            n_days,
        "year":              year,
        "teams":             teams,
        "employees":         employees,
        "allowed_genes":     allowed_genes,
        "vac_mask":          vac_mask,
        "min_demand":        min_demand,
        "ideal_demand":      ideal_demand,
        "special_days":      special_days,
        "gene_shift_arr":    gene_shift_arr,
        "gene_team_arr":     gene_team_arr,
        # encoding lookups
        **enc,
    }


# ── Core penalty computation ──────────────────────────────────────────────────

def _compute_penalties(schedule: np.ndarray, problem_data: dict) -> tuple:
    """
    Compute raw penalty components for a schedule.

    Returns:
        (min_unmet, ideal_unmet)  — all non-negative ints
    """
    min_demand     = problem_data["min_demand"]
    ideal_demand   = problem_data["ideal_demand"]
    gene_shift_arr = problem_data["gene_shift_arr"]
    gene_team_arr  = problem_data["gene_team_arr"]
    n_days         = problem_data["n_days"]
    n_shifts       = len(SHIFTS)
    n_teams        = len(problem_data["teams"])

    # O2 — build coverage in one vectorised pass using np.bincount
    emp_i, day_j = np.where(schedule != GENE_OFF)
    genes = schedule[emp_i, day_j]
    coverage = np.bincount(
        np.ravel_multi_index(
            (day_j, gene_shift_arr[genes], gene_team_arr[genes]),
            (n_days, n_shifts, n_teams),
        ),
        minlength=n_days * n_shifts * n_teams,
    ).reshape(n_days, n_shifts, n_teams)

    min_unmet   = int(np.sum(np.maximum(0, min_demand   - coverage)))
    ideal_unmet = int(np.sum(np.maximum(0, ideal_demand - coverage)))
    return min_unmet, ideal_unmet


def compute_fitness(schedule: np.ndarray, problem_data: dict) -> float:
    """
    Evaluate a schedule. Higher (less negative) = better. 0 = perfect.
    """
    m, i = _compute_penalties(schedule, problem_data)
    return -float(m * W_MIN_COVER + i * W_IDEAL_COVER)


# ── Initialisation helpers ────────────────────────────────────────────────────

def random_schedule(problem_data: dict) -> np.ndarray:
    """
    Generate a demand-aware random schedule.
    Iterates day-first. Within each day, single-team employees are processed
    first (shuffled among themselves), then dual-team employees (shuffled among
    themselves). This ensures the flexible employees fill coverage gaps left by
    the fixed-team employees rather than competing for the same slots.
    For each employee on a given day:
      - Vacation day → GENE_OFF.
      - Any allowed gene (excluding OFF) covers a slot still below min_demand
        → pick randomly from those greedy candidates.
      - All slots already at or above min_demand → pick randomly from
        allowed_genes (including OFF) as a fallback.

    Returns:
        int array (n_employees, n_days)
    """
    n_emp              = problem_data["n_employees"]
    n_days             = problem_data["n_days"]
    n_teams            = len(problem_data["teams"])
    vac_mask           = problem_data["vac_mask"]
    allowed_genes      = problem_data["allowed_genes"]
    min_demand         = problem_data["min_demand"]
    gene_to_shift_team = problem_data["gene_to_shift_team"]
    team_idx           = problem_data["team_idx"]

    # Single-team employees have exactly 1 shift×team pair (2 genes + OFF)
    n_shifts = len(SHIFTS)
    single_team = [i for i in range(n_emp) if len(allowed_genes[i]) <= n_shifts + 1]
    dual_team   = [i for i in range(n_emp) if len(allowed_genes[i]) >  n_shifts + 1]

    schedule = np.zeros((n_emp, n_days), dtype=int)
    coverage = np.zeros((n_days, n_shifts, n_teams), dtype=int)

    for d in range(n_days):
        random.shuffle(single_team)
        random.shuffle(dual_team)
        for i in single_team + dual_team:
            if vac_mask[i, d]:
                schedule[i, d] = GENE_OFF
                continue

            greedy_genes = [
                g for g in allowed_genes[i]
                if g != GENE_OFF
                and coverage[d, SHIFT_IDX[gene_to_shift_team[g][0]], team_idx[gene_to_shift_team[g][1]]]
                    < min_demand[d, SHIFT_IDX[gene_to_shift_team[g][0]], team_idx[gene_to_shift_team[g][1]]]
            ]

            gene = random.choice(greedy_genes if greedy_genes else allowed_genes[i])
            schedule[i, d] = gene

            if gene != GENE_OFF:
                s_code, t_code = gene_to_shift_team[gene]
                coverage[d, SHIFT_IDX[s_code], team_idx[t_code]] += 1

    return schedule


def decode_schedule(flat: np.ndarray, problem_data: dict) -> np.ndarray:
    """Reshape a flat 1D chromosome into a 2D schedule (n_employees, n_days)."""
    return flat.reshape(problem_data["n_employees"], problem_data["n_days"]).astype(int)


# ── Phase 2: Repair operators ─────────────────────────────────────────────────
# Each repair guarantees one hard constraint. Applied in order before fitness
# evaluation so the GA only ever sees feasible schedules (Baldwinian approach:
# repair is applied to a copy for evaluation; the chromosome is not modified).

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
    n_emp              = problem_data["n_employees"]
    n_days             = problem_data["n_days"]
    allowed_genes      = problem_data["allowed_genes"]
    gene_shift_order   = problem_data["gene_shift_order"]
    gene_to_shift_team = problem_data["gene_to_shift_team"]
    shift_team_to_gene = problem_data["shift_team_to_gene"]

    for i in range(n_emp):
        for d in range(n_days - 1):
            g_today    = schedule[i, d]
            g_tomorrow = schedule[i, d + 1]
            if g_today == GENE_OFF or g_tomorrow == GENE_OFF:
                continue
            if gene_shift_order[g_tomorrow] < gene_shift_order[g_today]:
                # Upgrade tomorrow to Afternoon keeping its team
                team     = gene_to_shift_team[g_tomorrow][1]
                upgraded = shift_team_to_gene[("T", team)]
                schedule[i, d + 1] = (
                    upgraded if upgraded in allowed_genes[i] else GENE_OFF
                )
    return schedule


def _repair_6day_window(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    In any rolling window of WINDOW_SIZE days, at most WINDOW_MAX may be worked.
    When a window has too many, a worked day in the window is set to OFF
    (vacation days are never touched).
    Repeated until no window violates the constraint.

    Direction is randomised per employee (50/50):
      - Forward  (start = 0 … end): removes the last  worked day in the window.
      - Backward (start = end … 0): removes the first worked day in the window.
    This avoids a systematic bias where the same end of the year always absorbs
    the surplus days.
    """
    n_emp    = problem_data["n_employees"]
    n_days   = problem_data["n_days"]
    vac_mask = problem_data["vac_mask"]

    for i in range(n_emp):
        forward = random.random() < 0.5
        starts  = (range(n_days - WINDOW_SIZE + 1)
                   if forward
                   else range(n_days - WINDOW_SIZE, -1, -1))
        changed = True
        while changed:
            changed = False
            for start in starts:
                window = range(start, start + WINDOW_SIZE)
                worked = [d for d in window if schedule[i, d] > 0]
                if len(worked) > WINDOW_MAX:
                    candidates = reversed(worked) if forward else iter(worked)
                    for d in candidates:
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
        random.shuffle(worked_special)
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
    n_days           = problem_data["n_days"]
    vac_mask         = problem_data["vac_mask"]
    special_days     = problem_data["special_days"]
    allowed_genes    = problem_data["allowed_genes"]
    gene_shift_order = problem_data["gene_shift_order"]

    worked_special = sum(1 for d in special_days if schedule_row[d] > 0)
    candidates = []

    for d in range(n_days):
        if schedule_row[d] > 0 or vac_mask[i, d]:
            continue

        if d in special_days and worked_special >= SPECIAL_DAYS_CAP:
            continue

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

        g_prev = schedule_row[d - 1] if d > 0 else GENE_OFF
        g_next = schedule_row[d + 1] if d < n_days - 1 else GENE_OFF
        valid_genes = [
            g for g in allowed_genes[i]
            if g != GENE_OFF
            and (g_prev == GENE_OFF or gene_shift_order[g] >= gene_shift_order[g_prev])
            and (g_next == GENE_OFF or gene_shift_order[g_next] >= gene_shift_order[g])
        ]
        if valid_genes:
            candidates.append((d, valid_genes))

    return candidates


def _repair_workday_count(schedule: np.ndarray, problem_data: dict) -> np.ndarray:
    """
    Enforce exactly TARGET_WORKDAYS worked days per employee.
    - Too many → remove the day whose (shift, team) slot has the highest surplus
                 above ideal demand (least costly removal). Random tiebreak.
    - Too few  → add days from a constraint-safe candidate pool; among valid genes
                 for a day, prefer the one that most reduces unmet ideal demand.
    Coverage is tracked and updated after every removal/addition.
    """
    n_emp            = problem_data["n_employees"]
    n_days           = problem_data["n_days"]
    gene_shift_order = problem_data["gene_shift_order"]
    ideal_demand     = problem_data["ideal_demand"]
    min_demand       = problem_data["min_demand"]
    gene_shift_arr   = problem_data["gene_shift_arr"]
    gene_team_arr    = problem_data["gene_team_arr"]
    n_shifts         = len(SHIFTS)
    n_teams          = len(problem_data["teams"])

    # Build full-schedule coverage once (vectorised) for demand-aware decisions.
    emp_i, day_j = np.where(schedule > 0)
    genes_on = schedule[emp_i, day_j]
    coverage = np.bincount(
        np.ravel_multi_index(
            (day_j, gene_shift_arr[genes_on], gene_team_arr[genes_on]),
            (n_days, n_shifts, n_teams),
        ),
        minlength=n_days * n_shifts * n_teams,
    ).reshape(n_days, n_shifts, n_teams)

    for i in range(n_emp):
        row    = schedule[i]
        worked = [d for d in range(n_days) if row[d] > 0]

        # ── Too many: remove day with highest surplus above ideal ─────────────
        while len(worked) > TARGET_WORKDAYS:
            w_arr   = np.array(worked, dtype=np.int32)
            s_arr   = gene_shift_arr[row[w_arr]]
            t_arr   = gene_team_arr[row[w_arr]]
            surplus = coverage[w_arr, s_arr, t_arr] - ideal_demand[w_arr, s_arr, t_arr]
            max_s   = surplus.max()
            d = int(w_arr[np.random.choice(np.where(surplus == max_s)[0])])
            g = row[d]
            coverage[d, gene_shift_arr[g], gene_team_arr[g]] -= 1
            schedule[i, d] = GENE_OFF
            worked.remove(d)

        # ── Too few: add from constraint-aware candidate pool ─────────────────
        if len(worked) < TARGET_WORKDAYS:
            special_days   = problem_data["special_days"]
            worked_special = sum(1 for d in special_days if row[d] > 0)
            candidates     = _workday_candidates(row, i, problem_data)
            random.shuffle(candidates)
            for d, valid_genes in candidates:
                if len(worked) >= TARGET_WORKDAYS:
                    break
                if row[d] > 0:
                    continue

                window_ok = True
                for ws in range(max(0, d - WINDOW_SIZE + 1),
                                min(n_days - WINDOW_SIZE + 1, d + 1)):
                    if sum(1 for x in range(ws, ws + WINDOW_SIZE)
                           if x != d and row[x] > 0) >= WINDOW_MAX:
                        window_ok = False
                        break
                if not window_ok:
                    continue

                if d in special_days and worked_special >= SPECIAL_DAYS_CAP:
                    continue

                g_prev = row[d - 1] if d > 0 else GENE_OFF
                g_next = row[d + 1] if d < n_days - 1 else GENE_OFF
                valid_now = [
                    g for g in valid_genes
                    if (g_prev == GENE_OFF or gene_shift_order[g] >= gene_shift_order[g_prev])
                    and (g_next == GENE_OFF or gene_shift_order[g_next] >= gene_shift_order[g])
                ]
                if not valid_now:
                    continue

                # Pick gene that most reduces unmet demand (min first, then ideal)
                vg     = np.array(valid_now, dtype=np.int32)
                s_arr  = gene_shift_arr[vg]
                t_arr  = gene_team_arr[vg]
                cov_v  = coverage[d, s_arr, t_arr]
                scores = (np.maximum(0, min_demand[d, s_arr, t_arr] - cov_v) * 100
                          + np.maximum(0, ideal_demand[d, s_arr, t_arr] - np.maximum(cov_v, min_demand[d, s_arr, t_arr])))
                best   = scores.max()
                picks  = vg[scores == best] if best > 0 else vg
                gene   = int(picks[np.random.randint(len(picks))])

                coverage[d, gene_shift_arr[gene], gene_team_arr[gene]] += 1
                schedule[i, d] = gene
                worked.append(d)
                if d in special_days:
                    worked_special += 1

    return schedule


def repair_schedule(schedule: np.ndarray, problem_data: dict, debug: bool = False):
    """
    Apply all Phase 2 repair operators in one pass:
      1. Vacations          (forces OFF on all vacation days)
      2. No backward shift  (changes shift type only; may set days to OFF)
      3. Special days cap   (sets excess special days to OFF)
      4. 6-day window cap   (sets excess days to OFF)
      5. Workday count      (rebalances total; adds only constraint-safe days)

    If debug=True, returns (schedule, changes_dict) where changes_dict maps
    operator name to number of cells changed.
    """
    if not debug:
        schedule = _repair_vacations(schedule, problem_data)
        schedule = _repair_no_backward_shift(schedule, problem_data)
        schedule = _repair_special_days(schedule, problem_data)
        schedule = _repair_6day_window(schedule, problem_data)
        schedule = _repair_workday_count(schedule, problem_data)
        return schedule

    changes = {}
    for name, fn in [
        ("vacations",        _repair_vacations),
        ("no_backward",      _repair_no_backward_shift),
        ("special_days",     _repair_special_days),
        ("6day_window",      _repair_6day_window),
        ("workday_count",    _repair_workday_count),
    ]:
        before = schedule.copy()
        schedule = fn(schedule, problem_data)
        changes[name] = int(np.sum(schedule != before))
    return schedule, changes


def local_search_one_pass(schedule: np.ndarray, problem_data: dict) -> tuple:
    """
    Single-pass day-swap LS for use inside the Memetic GA loop.

    One scan through all employees: for each employee, finds and applies the
    first valid surplus→deficit swap (no outer restart loop). Much lighter than
    local_search_ideal — O(n_emp × surplus × free) per call.

    Returns:
        (improved_schedule, n_swaps)
    """
    n_emp          = problem_data["n_employees"]
    n_days         = problem_data["n_days"]
    allowed_genes  = problem_data["allowed_genes"]
    min_demand     = problem_data["min_demand"]
    ideal_demand   = problem_data["ideal_demand"]
    vac_mask       = problem_data["vac_mask"]
    special_days   = problem_data["special_days"]
    gene_shift_arr = problem_data["gene_shift_arr"]
    gene_team_arr  = problem_data["gene_team_arr"]
    n_teams        = len(problem_data["teams"])

    schedule = schedule.copy()
    T_IDX = SHIFT_IDX["T"]
    M_IDX = SHIFT_IDX["M"]

    coverage = np.zeros((n_days, len(SHIFTS), n_teams), dtype=int)
    ei, dj = np.where(schedule != GENE_OFF)
    if len(ei):
        gp = schedule[ei, dj]
        np.add.at(coverage, (dj, gene_shift_arr[gp], gene_team_arr[gp]), 1)

    work_genes_emp = [
        np.array([g for g in allowed_genes[i] if g != GENE_OFF])
        for i in range(n_emp)
    ]

    n_swaps = 0

    for i in range(n_emp):
        row        = schedule[i]
        work_genes = work_genes_emp[i]
        if not len(work_genes):
            continue

        worked  = np.where(row != GENE_OFF)[0]
        if not len(worked):
            continue
        gw      = row[worked]
        surplus = (coverage[worked, gene_shift_arr[gw], gene_team_arr[gw]]
                   - ideal_demand[worked, gene_shift_arr[gw], gene_team_arr[gw]])
        surplus_days = worked[surplus > 0]
        if not len(surplus_days):
            continue

        free_days = np.where((row == GENE_OFF) & ~vac_mask[i])[0]
        if not len(free_days):
            continue

        sp_count = int(np.sum(row[list(special_days)] != GENE_OFF))
        swapped  = False

        for d1 in surplus_days:
            if swapped:
                break
            old_gene   = int(row[d1])
            old_s      = int(gene_shift_arr[old_gene])
            old_t      = int(gene_team_arr[old_gene])
            d1_special = d1 in special_days

            for d2 in free_days:
                d2_special = d2 in special_days
                if d2_special and not d1_special and sp_count >= SPECIAL_DAYS_CAP:
                    continue

                window_ok = True
                for w in range(max(0, d2 - WINDOW_SIZE + 1),
                               min(n_days - WINDOW_SIZE + 1, d2 + 1)):
                    count = int(np.sum(row[w:w + WINDOW_SIZE] != GENE_OFF))
                    if w <= d1 < w + WINDOW_SIZE:
                        count -= 1
                    if count >= WINDOW_MAX:
                        window_ok = False
                        break
                if not window_ok:
                    continue

                s_c   = gene_shift_arr[work_genes]
                t_c   = gene_team_arr[work_genes]
                cov_c = coverage[d2, s_c, t_c].astype(int)
                sc    = np.maximum(0, ideal_demand[d2, s_c, t_c]
                                   - np.maximum(cov_c, min_demand[d2, s_c, t_c]))
                if sc.max() == 0:
                    continue

                for k in range(len(work_genes)):
                    ns = int(gene_shift_arr[work_genes[k]])
                    if ns == T_IDX:
                        if (d2 + 1 < n_days and row[d2 + 1] != GENE_OFF
                                and gene_shift_arr[row[d2 + 1]] == M_IDX):
                            sc[k] = 0
                    else:
                        if (d2 > 0 and row[d2 - 1] != GENE_OFF
                                and gene_shift_arr[row[d2 - 1]] == T_IDX):
                            sc[k] = 0
                if sc.max() == 0:
                    continue

                chosen = int(work_genes[np.argmax(sc)])
                coverage[d1, old_s, old_t] -= 1
                coverage[d2, gene_shift_arr[chosen], gene_team_arr[chosen]] += 1
                row[d1] = GENE_OFF
                row[d2] = chosen
                n_swaps += 1
                swapped  = True
                break

    return schedule, n_swaps


def local_search_ideal(schedule: np.ndarray, problem_data: dict) -> tuple:
    """
    Post-processing local search: day-swap surplus-to-deficit.

    For each employee, moves workdays from surplus days (coverage > ideal)
    to non-worked deficit days (a valid gene covers a slot below ideal).
    Iterates until no improving move exists. Preserves workday count exactly
    and enforces all Phase 2 constraints (backward shift, 6-day window,
    special days cap). Min coverage stays intact because surplus days have
    coverage > ideal >= min, so after removal coverage >= ideal >= min.

    Returns:
        (improved_schedule, n_swaps)
    """
    n_emp          = problem_data["n_employees"]
    n_days         = problem_data["n_days"]
    allowed_genes  = problem_data["allowed_genes"]
    min_demand     = problem_data["min_demand"]
    ideal_demand   = problem_data["ideal_demand"]
    vac_mask       = problem_data["vac_mask"]
    special_days   = problem_data["special_days"]
    gene_shift_arr = problem_data["gene_shift_arr"]
    gene_team_arr  = problem_data["gene_team_arr"]
    n_teams        = len(problem_data["teams"])

    schedule = schedule.copy()
    T_IDX = SHIFT_IDX["T"]
    M_IDX = SHIFT_IDX["M"]

    coverage = np.zeros((n_days, len(SHIFTS), n_teams), dtype=int)
    ei, dj = np.where(schedule != GENE_OFF)
    if len(ei):
        gp = schedule[ei, dj]
        np.add.at(coverage, (dj, gene_shift_arr[gp], gene_team_arr[gp]), 1)

    work_genes_emp = [
        np.array([g for g in allowed_genes[i] if g != GENE_OFF])
        for i in range(n_emp)
    ]

    n_swaps = 0

    while True:
        improved = False

        for i in range(n_emp):
            row        = schedule[i]
            work_genes = work_genes_emp[i]
            if not len(work_genes):
                continue

            worked  = np.where(row != GENE_OFF)[0]
            if not len(worked):
                continue
            gw      = row[worked]
            surplus = (coverage[worked, gene_shift_arr[gw], gene_team_arr[gw]]
                       - ideal_demand[worked, gene_shift_arr[gw], gene_team_arr[gw]])
            surplus_days = worked[surplus > 0]
            if not len(surplus_days):
                continue

            free_days = np.where((row == GENE_OFF) & ~vac_mask[i])[0]
            if not len(free_days):
                continue

            sp_count = int(np.sum(row[list(special_days)] != GENE_OFF))

            emp_improved = True
            while emp_improved:
                emp_improved = False

                worked  = np.where(row != GENE_OFF)[0]
                gw      = row[worked]
                surplus = (coverage[worked, gene_shift_arr[gw], gene_team_arr[gw]]
                           - ideal_demand[worked, gene_shift_arr[gw], gene_team_arr[gw]])
                surplus_days = worked[surplus > 0]
                free_days    = np.where((row == GENE_OFF) & ~vac_mask[i])[0]

                for d1 in surplus_days:
                    old_gene   = int(row[d1])
                    old_s      = int(gene_shift_arr[old_gene])
                    old_t      = int(gene_team_arr[old_gene])
                    d1_special = d1 in special_days

                    for d2 in free_days:
                        d2_special = d2 in special_days
                        if d2_special and not d1_special:
                            if sp_count >= SPECIAL_DAYS_CAP:
                                continue

                        window_ok = True
                        for w in range(max(0, d2 - WINDOW_SIZE + 1),
                                       min(n_days - WINDOW_SIZE + 1, d2 + 1)):
                            count = int(np.sum(row[w:w + WINDOW_SIZE] != GENE_OFF))
                            if w <= d1 < w + WINDOW_SIZE:
                                count -= 1
                            if count >= WINDOW_MAX:
                                window_ok = False
                                break
                        if not window_ok:
                            continue

                        s_c   = gene_shift_arr[work_genes]
                        t_c   = gene_team_arr[work_genes]
                        cov_c = coverage[d2, s_c, t_c].astype(int)
                        id_c  = ideal_demand[d2, s_c, t_c]
                        mn_c  = min_demand[d2, s_c, t_c]
                        sc    = np.maximum(0, id_c - np.maximum(cov_c, mn_c))

                        if sc.max() == 0:
                            continue

                        valid = np.ones(len(work_genes), dtype=bool)
                        for k in range(len(work_genes)):
                            ns = int(gene_shift_arr[work_genes[k]])
                            if ns == T_IDX:
                                if (d2 + 1 < n_days and row[d2 + 1] != GENE_OFF
                                        and gene_shift_arr[row[d2 + 1]] == M_IDX):
                                    valid[k] = False
                            else:
                                if (d2 > 0 and row[d2 - 1] != GENE_OFF
                                        and gene_shift_arr[row[d2 - 1]] == T_IDX):
                                    valid[k] = False

                        sc_valid = sc.copy()
                        sc_valid[~valid] = 0
                        if sc_valid.max() == 0:
                            continue

                        chosen = int(work_genes[np.argmax(sc_valid)])

                        coverage[d1, old_s, old_t] -= 1
                        coverage[d2, gene_shift_arr[chosen], gene_team_arr[chosen]] += 1
                        row[d1] = GENE_OFF
                        row[d2] = chosen

                        if d2_special and not d1_special:
                            sp_count += 1
                        elif d1_special and not d2_special:
                            sp_count -= 1

                        n_swaps     += 1
                        improved     = True
                        emp_improved = True
                        break

                    if emp_improved:
                        break

        if not improved:
            break

    return schedule, n_swaps


def local_search_cyclic(schedule: np.ndarray, problem_data: dict) -> tuple:
    """
    Post-processing local search: 2-employee cyclic exchanges.

    For each pair of employees (A, B):
    - A works day d1 in surplus and does NOT work day d2
    - B works day d2 in surplus and does NOT work day d1
    - Swap: A moves d1→d2, B moves d2→d1, each with best deficit gene
    - Apply if both employees bring net improvement and constraints hold

    Unlocks moves that single day-swap cannot make because d2 is occupied
    by another employee (not a free day). Run after local_search_ideal.

    Returns:
        (improved_schedule, n_swaps)
    """
    n_emp          = problem_data["n_employees"]
    n_days         = problem_data["n_days"]
    allowed_genes  = problem_data["allowed_genes"]
    min_demand     = problem_data["min_demand"]
    ideal_demand   = problem_data["ideal_demand"]
    vac_mask       = problem_data["vac_mask"]
    special_days   = problem_data["special_days"]
    gene_shift_arr = problem_data["gene_shift_arr"]
    gene_team_arr  = problem_data["gene_team_arr"]
    n_teams        = len(problem_data["teams"])

    schedule = schedule.copy()
    T_IDX = SHIFT_IDX["T"]
    M_IDX = SHIFT_IDX["M"]

    coverage = np.zeros((n_days, len(SHIFTS), n_teams), dtype=int)
    ei, dj = np.where(schedule != GENE_OFF)
    if len(ei):
        gp = schedule[ei, dj]
        np.add.at(coverage, (dj, gene_shift_arr[gp], gene_team_arr[gp]), 1)

    work_genes_emp = [
        np.array([g for g in allowed_genes[i] if g != GENE_OFF])
        for i in range(n_emp)
    ]

    def _best_gene(wg, d, row, cov_d):
        """Best deficit gene for employee at day d with simulated coverage cov_d."""
        s_c = gene_shift_arr[wg]
        t_c = gene_team_arr[wg]
        sc  = np.maximum(0, ideal_demand[d, s_c, t_c] - np.maximum(cov_d[s_c, t_c], min_demand[d, s_c, t_c]))
        for k in range(len(wg)):
            ns = int(gene_shift_arr[wg[k]])
            if ns == T_IDX:
                if d + 1 < n_days and row[d+1] != GENE_OFF and gene_shift_arr[row[d+1]] == M_IDX:
                    sc[k] = 0
            else:
                if d > 0 and row[d-1] != GENE_OFF and gene_shift_arr[row[d-1]] == T_IDX:
                    sc[k] = 0
        if sc.max() == 0:
            return None, 0
        return int(wg[np.argmax(sc)]), int(sc.max())

    def _window_ok(row, d_add, d_remove):
        """True if adding d_add (and removing d_remove) passes the 6-day window."""
        for w in range(max(0, d_add - WINDOW_SIZE + 1),
                       min(n_days - WINDOW_SIZE + 1, d_add + 1)):
            count = int(np.sum(row[w:w + WINDOW_SIZE] != GENE_OFF))
            if w <= d_remove < w + WINDOW_SIZE:
                count -= 1
            if count >= WINDOW_MAX:
                return False
        return True

    n_swaps = 0

    while True:
        improved = False

        surplus_per_emp = []
        for i in range(n_emp):
            row = schedule[i]
            w   = np.where(row != GENE_OFF)[0]
            if not len(w):
                surplus_per_emp.append(np.array([], dtype=int))
                continue
            gw  = row[w]
            sur = (coverage[w, gene_shift_arr[gw], gene_team_arr[gw]]
                   - ideal_demand[w, gene_shift_arr[gw], gene_team_arr[gw]])
            surplus_per_emp.append(w[sur > 0])

        found = False
        for i in range(n_emp):
            if found:
                break
            surplus_i = surplus_per_emp[i]
            if not len(surplus_i):
                continue
            row_i = schedule[i]
            wg_i  = work_genes_emp[i]

            for j in range(i + 1, n_emp):
                if found:
                    break
                surplus_j = surplus_per_emp[j]
                if not len(surplus_j):
                    continue
                row_j = schedule[j]
                wg_j  = work_genes_emp[j]

                for d1 in surplus_i:
                    if found:
                        break
                    if row_j[d1] != GENE_OFF or vac_mask[j, d1]:
                        continue

                    old_gi = int(row_i[d1])
                    old_si = int(gene_shift_arr[old_gi])
                    old_ti = int(gene_team_arr[old_gi])

                    for d2 in surplus_j:
                        if row_i[d2] != GENE_OFF or vac_mask[i, d2]:
                            continue

                        old_gj = int(row_j[d2])
                        old_sj = int(gene_shift_arr[old_gj])
                        old_tj = int(gene_team_arr[old_gj])

                        if not _window_ok(row_i, d2, d1):
                            continue
                        if not _window_ok(row_j, d1, d2):
                            continue

                        d1_sp = d1 in special_days
                        d2_sp = d2 in special_days
                        if d2_sp and not d1_sp:
                            if int(np.sum(row_i[list(special_days)] != GENE_OFF)) >= SPECIAL_DAYS_CAP:
                                continue
                        if d1_sp and not d2_sp:
                            if int(np.sum(row_j[list(special_days)] != GENE_OFF)) >= SPECIAL_DAYS_CAP:
                                continue

                        cov_d1 = coverage[d1].copy()
                        cov_d2 = coverage[d2].copy()
                        cov_d1[old_si, old_ti] -= 1
                        cov_d2[old_sj, old_tj] -= 1

                        chosen_i, sc_i = _best_gene(wg_i, d2, row_i, cov_d2)
                        if chosen_i is None:
                            continue
                        chosen_j, sc_j = _best_gene(wg_j, d1, row_j, cov_d1)
                        if chosen_j is None:
                            continue

                        coverage[d1, old_si, old_ti] -= 1
                        coverage[d2, old_sj, old_tj] -= 1
                        coverage[d2, gene_shift_arr[chosen_i], gene_team_arr[chosen_i]] += 1
                        coverage[d1, gene_shift_arr[chosen_j], gene_team_arr[chosen_j]] += 1

                        row_i[d1] = GENE_OFF
                        row_i[d2] = chosen_i
                        row_j[d2] = GENE_OFF
                        row_j[d1] = chosen_j

                        n_swaps += 1
                        improved  = True
                        found     = True
                        break

        if not improved:
            break

    return schedule, n_swaps


def compute_phase2_violations(schedule: np.ndarray, problem_data: dict) -> dict:
    """
    Count Phase 2 constraint violations in a schedule (for reporting).
    Returns a dict with counts per constraint.
    """
    n_emp            = problem_data["n_employees"]
    n_days           = problem_data["n_days"]
    special_days     = problem_data["special_days"]
    vac_mask         = problem_data["vac_mask"]
    gene_shift_order = problem_data["gene_shift_order"]

    vacation = int(np.sum((schedule > 0) & vac_mask))
    backward = window = special = workday = 0

    for i in range(n_emp):
        worked = sum(1 for d in range(n_days) if schedule[i, d] > 0)
        if worked != TARGET_WORKDAYS:
            workday += abs(worked - TARGET_WORKDAYS)

        worked_special = sum(1 for d in special_days if schedule[i, d] > 0)
        if worked_special > SPECIAL_DAYS_CAP:
            special += worked_special - SPECIAL_DAYS_CAP

        for d in range(n_days):
            if d < n_days - 1:
                g0, g1 = schedule[i, d], schedule[i, d + 1]
                if g0 != GENE_OFF and g1 != GENE_OFF:
                    if gene_shift_order[g1] < gene_shift_order[g0]:
                        backward += 1

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

def export_schedule(
    schedule: np.ndarray,
    problem_data: dict,
    path: str = "schedule.csv",
) -> None:
    """
    Export the schedule to two CSV files:

    1. <path>  — wide format (employees × days), one cell per day.
    2. <path stem>_coverage.csv — daily coverage check per (shift, team).
    """
    from pathlib import Path

    n_emp              = problem_data["n_employees"]
    n_days             = problem_data["n_days"]
    year               = problem_data["year"]
    employees          = problem_data["employees"]
    teams              = problem_data["teams"]
    min_demand         = problem_data["min_demand"]
    ideal_demand       = problem_data["ideal_demand"]
    gene_label         = problem_data["gene_label"]
    shift_team_to_gene = problem_data["shift_team_to_gene"]
    team_idx           = problem_data["team_idx"]

    start_date = pd.Timestamp(f"{year}-01-01")
    dates      = [start_date + pd.Timedelta(days=d) for d in range(n_days)]
    date_strs  = [d.strftime("%Y-%m-%d") for d in dates]

    # ── 1. Wide schedule CSV ──────────────────────────────────────────────────
    rows = []
    for i, emp in enumerate(employees):
        row = {"Employee": emp["name"]}
        for d in range(n_days):
            row[date_strs[d]] = gene_label[schedule[i, d]]
        rows.append(row)

    df_schedule = pd.DataFrame(rows).set_index("Employee")
    df_schedule.to_csv(path)
    print(f"Schedule exported → {path}  ({n_emp} employees × {n_days} days)")

    # ── 2. Daily coverage CSV ─────────────────────────────────────────────────
    coverage_rows = []
    for d in range(n_days):
        for s_idx, s_code in enumerate(SHIFTS):
            for t_code in teams:
                t_idx     = team_idx[t_code]
                gene_val  = shift_team_to_gene[(s_code, t_code)]
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
