"""
assignment_map.py
-----------------
Drop-in replacement for Heuristica._print_daily_assignment_map.

Features
--------
* ANSI colour-coded cells: M=blue, T=yellow, N=magenta, F=cyan, 0=dim
* Violation flags inline:
    [!] next to any employee whose last 5 cells are ALL worked (consecutive-day rule)
    [~] next to any employee whose previous-day → today transition is invalid (N→M)
* Per-employee running counters appended at the right edge:
    Tot=<total days worked> | Seq=<current streak> | Wk=<days worked this ISO week>
* Compact 3-char cells so 365 days fit in a wide terminal (~1400 chars/row)
  – pass `wide=False` to get a 30-day rolling window instead
* Summary block at the bottom: shift coverage vs minimums for today

Usage
-----
Replace the call inside build_model with:

    from assignment_map import print_daily_assignment_map

    print_daily_assignment_map(
        scheduler   = self,
        day         = d,
        daily_assignments = daily_assignments,
        tracking    = {
            "Worked_Total_Days":      Worked_Total_Days,
            "Worked_Sequential_Days": Worked_Sequential_Days,
            "Worked_Previous_Day":    Worked_Previous_Day,
        },
        mins        = mins,         # {(shift, team_code): min_count}
        wide        = True,         # True=all days, False=rolling-30 window
        window      = 30,           # only used when wide=False
    )
"""

from __future__ import annotations
from collections import defaultdict
from typing import Any

# ── ANSI helpers ─────────────────────────────────────────────────────────────

RESET  = "\033[0m"
BOLD   = "\033[1m"
DIM    = "\033[2m"

# Foreground colours
FG_RED     = "\033[91m"
FG_GREEN   = "\033[92m"
FG_YELLOW  = "\033[93m"
FG_BLUE    = "\033[94m"
FG_DARK_BLUE = "\033[34m"
FG_MAGENTA = "\033[95m"
FG_CYAN    = "\033[96m"
FG_WHITE   = "\033[97m"
FG_GRAY    = "\033[90m"

# Background colours (subtle)
BG_DARK    = "\033[40m"

def _c(text: str, *codes: str) -> str:
    return "".join(codes) + text + RESET


# ── Cell renderer ─────────────────────────────────────────────────────────────

SHIFT_COLOUR = {
    1: FG_BLUE,        # Morning  → blue
    2: FG_YELLOW,      # Tarde    → yellow
    3: FG_MAGENTA,     # Noite    → magenta
}

TEAM_ID_TO_CODE: dict[int, str] = {}   # populated lazily from scheduler

def _cell(day_idx: int,
          day_to_st: dict[int, tuple[int, int]],
          vac_days: set[int],
          closed_days: set[int],
          all_dates: list,
          highlight_today: bool = False) -> str:
    """Return a 3-char coloured string for one cell."""
    if day_idx in vac_days:
        return _c(" F ", FG_CYAN)
    if day_idx in day_to_st:
        shift, team_id = day_to_st[day_idx]
        tc = TEAM_ID_TO_CODE.get(team_id, "?")
        label = f"{('M','T','N')[shift-1]}{tc}"          # e.g. "MA"
        label = label[:2].ljust(2)                        # exactly 2 chars
        colour = SHIFT_COLOUR.get(shift, FG_WHITE)
        cell = _c(f" {label}", colour + BOLD)
        return cell
    # Not worked, not vacation
    ts = all_dates[day_idx - 1] if 1 <= day_idx <= len(all_dates) else None
    if ts is not None and ts in closed_days:
        return _c(" ─ ", FG_GRAY + DIM)   # store closed
    return _c(" · ", FG_GRAY + DIM)


# ── Violation detectors ───────────────────────────────────────────────────────

def _has_consecutive_violation(day_to_st: dict[int, tuple], vac_days: set[int],
                                current_day_idx: int, window: int = 6) -> bool:
    """True if the last `window` days up to current_day_idx are ALL worked."""
    if current_day_idx < window:
        return False
    for d in range(current_day_idx - window + 1, current_day_idx + 1):
        if d not in day_to_st or d in vac_days:
            return False
    return True


def _has_transition_violation(prev_shift, today_shift) -> bool:
    """True if N→M transition (shift 3 → shift 1)."""
    return prev_shift == 3 and today_shift == 1


# ── ISO week helper ───────────────────────────────────────────────────────────

def _days_worked_this_week(day_to_st: dict[int, tuple], all_dates: list,
                            current_day_idx: int) -> int:
    """Count worked days in the same ISO week as current_day_idx."""
    if not (1 <= current_day_idx <= len(all_dates)):
        return 0
    target_week = all_dates[current_day_idx - 1].isocalendar()[1]
    target_year = all_dates[current_day_idx - 1].isocalendar()[0]
    count = 0
    for d, _ in day_to_st.items():
        if 1 <= d <= len(all_dates):
            iso = all_dates[d - 1].isocalendar()
            if iso[0] == target_year and iso[1] == target_week:
                count += 1
    return count


# ── Coverage summary ──────────────────────────────────────────────────────────

def _coverage_summary(daily_assignments: list[tuple],
                       mins: dict[tuple, int],
                       shifts: int,
                       teams: dict) -> list[str]:
    """
    Compare today's actual assignments against minimums.
    daily_assignments: list of (emp_id, shift, team_code)
    mins: {(shift, team_code): min_count}
    """
    # Count actual
    actual: dict[tuple, int] = defaultdict(int)
    for _, shift, team_code in daily_assignments:
        actual[(shift, team_code)] += 1

    lines = []
    shift_label = {1: "M", 2: "T", 3: "N"}
    all_keys = set(mins.keys()) | set(actual.keys())

    for key in sorted(all_keys):
        shift, team_code = key
        got = actual.get(key, 0)
        need = mins.get(key, 0)
        label = f"  Shift {shift_label.get(shift, shift)} Team {TEAM_ID_TO_CODE.get(team_code, team_code)}"
        bar_filled = min(got, need)
        bar_over   = max(0, got - need)
        bar_short  = max(0, need - got)
        bar = (
            _c("█" * bar_filled, FG_GREEN) +
            _c("█" * bar_over,   FG_YELLOW) +
            _c("░" * bar_short,  FG_RED)
        )
        status = _c("✓", FG_GREEN) if got >= need else _c(f"✗ (need {need}, got {got})", FG_RED)
        lines.append(f"{label}: [{bar}] {got}/{need} {status}")

    return lines


# ── Main function ─────────────────────────────────────────────────────────────

def print_daily_assignment_map(
    scheduler,
    day,
    daily_assignments: list[tuple],
    tracking: dict[str, Any],
    mins: dict[tuple, int],
    wide: bool = True,
    window: int = 30,
):
    """
    Print the cumulative assignment map to the terminal.

    Parameters
    ----------
    scheduler         : Heuristica instance (needs .dates, .assignment,
                        .vacs_1based, .sundays_holidays, .employee_rows,
                        .emp_allowed_teams, TEAM_ID_TO_CODE)
    day               : current pandas Timestamp
    daily_assignments : list of (emp_id, shift, team_code) assigned TODAY
    tracking          : dict with keys
                          "Worked_Total_Days"      {emp_id: int}
                          "Worked_Sequential_Days" {emp_id: int}
                          "Worked_Previous_Day"    {emp_id: shift|None}
    mins              : {(shift, team_code): min_count} for today
    wide              : if True show all days; if False show rolling window
    window            : window size when wide=False
    """

    # Populate module-level team code map from scheduler
    global TEAM_ID_TO_CODE
    try:
        from algorithms.utils import TEAM_ID_TO_CODE as _T
        TEAM_ID_TO_CODE = _T
    except ImportError:
        TEAM_ID_TO_CODE = getattr(scheduler, "_TEAM_ID_TO_CODE", TEAM_ID_TO_CODE)

    all_dates   = scheduler.dates
    day_index   = all_dates.index(day) + 1          # 1-based
    n_employees = len(scheduler.employee_rows)
    closed_set  = set(scheduler.sundays_holidays)

    WTD  = tracking.get("Worked_Total_Days",      {})
    WSD  = tracking.get("Worked_Sequential_Days", {})
    WPD  = tracking.get("Worked_Previous_Day",    {})

    # Column range to display
    if wide:
        col_start, col_end = 1, day_index
    else:
        col_start = max(1, day_index - window + 1)
        col_end   = day_index

    cols = list(range(col_start, col_end + 1))

    # ── Header ──────────────────────────────────────────────────────────────
    sep = "─" * 80
    print(f"\n{_c(sep, FG_GRAY)}")
    print(
        _c(f"  SCHEDULE MAP ", BOLD + FG_WHITE + BG_DARK) +
        f"  Day {day_index:>3} / {len(all_dates)}  "
        f"({_c(str(day.date()), FG_CYAN)})  "
        f"Assigned today: {_c(str(len(daily_assignments)), FG_GREEN + BOLD)}"
    )
    print(
        f"  Legend: "
        f"{_c('M', FG_BLUE+BOLD)}=Morning  "
        f"{_c('T', FG_YELLOW+BOLD)}=Tarde  "
        f"{_c('N', FG_MAGENTA+BOLD)}=Noite  "
        f"{_c('F', FG_CYAN)}=Férias  "
        f"{_c('·', FG_GRAY+DIM)}=Off  "
        f"{_c('─', FG_GRAY+DIM)}=Closed  "
        f"{_c('[!]', FG_RED+BOLD)}=≥6consec  "
        f"{_c('[~]', FG_YELLOW+BOLD)}=N→M"
    )
    print(_c(sep, FG_GRAY))

    # ── Column header (day numbers) ──────────────────────────────────────────
    EMP_W  = 8    # width of employee label column
    CELL_W = 3    # chars per day cell
    STAT_W = 26   # width of stats column on the right

    # Day-number header: every 5th day gets its number, rest get "·"
    hdr_emp = "Emp".center(EMP_W)
    hdr_days = ""
    for c in cols:
        if c == day_index:
            hdr_days += _c(f"{c:>3}", FG_WHITE + BOLD)
        elif c % 5 == 0:
            hdr_days += f"{c:>3}"
        else:
            hdr_days += _c("  ·", FG_GRAY + DIM)

    # Month change markers
    month_markers = ""
    prev_month = None
    for c in cols:
        ts = all_dates[c - 1]
        if ts.month != prev_month:
            month_markers += _c(ts.strftime("%b")[:2].ljust(CELL_W), FG_CYAN + BOLD)
            prev_month = ts.month
        else:
            month_markers += " " * CELL_W

    print(" " * EMP_W + _c(month_markers, ""))
    print(hdr_emp + hdr_days + "  " + "Tot Seq Wk  Flags".center(STAT_W))
    print(_c(" " * EMP_W + "─" * (len(cols) * CELL_W) + "  " + "─" * STAT_W, FG_GRAY + DIM))

    # ── Employee rows ────────────────────────────────────────────────────────
    for emp_id in range(1, n_employees + 1):
        # Internal emp index in tracking is emp_id - 1 (0-based in build_model)
        # but assignments are stored under emp_id+1 due to off-by-one in original.
        # We support both: check what keys exist.
        # Tracking uses f (0-based index into employees list, so 0..N-1).
        # self.assignment uses f+1 (so 1..N) in the original, but the fixed version
        # stores under emp_id directly.  Try both.
        f_track = emp_id - 1   # 0-based key used in Worked_* dicts

        vac_days: set[int] = set(scheduler.vacs_1based.get(emp_id, []))
        # assignments stored under emp_id in fixed code, emp_id+1 in original
        raw_assign = (
            scheduler.assignment.get(emp_id)
            or scheduler.assignment.get(emp_id + 1)
            or []
        )
        day_to_st: dict[int, tuple[int, int]] = {d: (s, t) for (d, s, t) in raw_assign}

        # Build cell string for displayed columns
        cells = ""
        for c in cols:
            cells += _cell(c, day_to_st, vac_days, closed_set, all_dates,
                           highlight_today=(c == day_index))

        # Stats
        tot = WTD.get(f_track, WTD.get(emp_id, 0))
        seq = WSD.get(f_track, WSD.get(emp_id, 0))
        wk  = _days_worked_this_week(day_to_st, all_dates, day_index)

        # Violation flags
        flags = ""
        if _has_consecutive_violation(day_to_st, vac_days, day_index, window=6):
            flags += _c("[!]", FG_RED + BOLD)
        prev_s  = WPD.get(f_track, WPD.get(emp_id))
        today_s = day_to_st.get(day_index, (None,))[0]
        if prev_s is not None and today_s is not None and _has_transition_violation(prev_s, today_s):
            flags += _c("[~]", FG_YELLOW + BOLD)

        stats = f"  {_c(str(tot).rjust(3), FG_WHITE)} {_c(str(seq).rjust(3), FG_CYAN)} {_c(str(wk).rjust(2), FG_YELLOW)}  {flags}"

        emp_label = _c(f"Emp{emp_id:>2}".ljust(EMP_W), FG_DARK_BLUE + BOLD)
        print(emp_label + cells + stats)

    # ── Today's coverage summary ─────────────────────────────────────────────
    print(_c(" " * EMP_W + "─" * (len(cols) * CELL_W), FG_GRAY + DIM))
    print(_c("\n  Coverage vs Minimums (today):", BOLD))
    cov_lines = _coverage_summary(daily_assignments, mins, scheduler.shifts, scheduler.teams)
    if cov_lines:
        for line in cov_lines:
            print(line)
    else:
        print(_c("  (no minimums defined for today)", FG_GRAY + DIM))

    print(_c(sep, FG_GRAY))