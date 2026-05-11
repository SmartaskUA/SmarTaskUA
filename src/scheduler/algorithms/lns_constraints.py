"""
lns_constraints.py
------------------
Hard-constraint checkers used by the repair operator.

All functions return True when a constraint is VIOLATED so callers can do:

    if violates_rest(emp_id, day, candidate, solution, days):
        continue
"""

from __future__ import annotations

from typing import Dict, List, Optional, Set, Tuple

from .lns_solution import Assignment, Day, EmpId, Solution

# Markers that mean the employee cannot work — sourced from sisqual_hours_utils
OFF_MARKERS: Set[str] = {"DO", "FDO", "VAC", "NOT", "Med", "DC-E", "OFF"}
MIN_REST_HOURS_DEFAULT = 11.0


# ---------------------------------------------------------------------------
# Minimum rest between consecutive shifts
# ---------------------------------------------------------------------------

def violates_min_rest(
    emp_id:          EmpId,
    day:             Day,
    candidate:       Assignment,
    solution:        Solution,
    days:            List[Day],
    min_rest_hours:  float = MIN_REST_HOURS_DEFAULT,
) -> bool:
    """
    True if placing `candidate` on `day` for `emp_id` would leave less than
    `min_rest_hours` between:
      • the END of the previous day's shift  →  START of candidate
      • the END of candidate                 →  START of the next day's shift
    Destroyed slots (where assignments[(emp,day)] is None) are ignored —
    those will be re-assigned during repair and checked then.
    """
    day_idx = days.index(day)

    # --- check with previous worked day ---
    if day_idx > 0:
        prev_day = days[day_idx - 1]
        prev_asgn = solution.assignments.get((emp_id, prev_day))
        if prev_asgn is not None:
            rest = (24 * 60 - prev_asgn.end_min + candidate.start_min) / 60.0
            if rest < min_rest_hours:
                return True

    # --- check with next worked day ---
    if day_idx < len(days) - 1:
        next_day = days[day_idx + 1]
        next_asgn = solution.assignments.get((emp_id, next_day))
        if next_asgn is not None:
            rest = (24 * 60 - candidate.end_min + next_asgn.start_min) / 60.0
            if rest < min_rest_hours:
                return True

    return False


# ---------------------------------------------------------------------------
# Maximum 5 working days in any 6 consecutive days
# ---------------------------------------------------------------------------

def violates_5_in_6(
    emp_id:    EmpId,
    day:       Day,
    solution:  Solution,
    days:      List[Day],
) -> bool:
    """
    True if adding a working day on `day` would give emp_id more than 5
    worked days in any 6-consecutive-day window that includes `day`.

    We only count days that currently have an assignment (non-None).  Days
    that are still in the 'destroyed' / None state don't count yet.
    """
    day_idx = days.index(day)

    # Windows of 6 that contain day_idx
    window_starts = range(
        max(0, day_idx - 5),
        min(len(days) - 5, day_idx + 1),
    )

    for ws in window_starts:
        window = days[ws: ws + 6]
        # Count already-committed worked days in this window, excluding `day`
        worked = sum(
            1
            for d in window
            if d != day and solution.assignments.get((emp_id, d)) is not None
        )
        if worked >= 5:
            return True

    return False


# ---------------------------------------------------------------------------
# Schedule-marker hard locks
# ---------------------------------------------------------------------------

def is_off_marker(marker: str) -> bool:
    """True if the schedule marker means the employee cannot work."""
    if marker is None:
        return False
    normalized = marker.strip().upper()
    return normalized in OFF_MARKERS or normalized.startswith("FDO")


def is_fixed_shift(marker: str) -> bool:
    """
    True if the marker encodes a fixed shift (EQUALS:HH:MM-HH:MM).
    Fixed shifts constrain the exact time window — the assignment key must
    match the encoded interval.
    """
    if marker is None:
        return False
    return marker.strip().upper().startswith("EQUALS:")


def fixed_shift_bounds(marker: str) -> Optional[Tuple[int, int]]:
    """
    Parse "EQUALS:HH:MM-HH:MM" → (start_min, end_min).
    Returns None if parsing fails.
    """
    try:
        time_part = marker.split(":", 1)[1]   # "HH:MM-HH:MM"
        start_str, end_str = time_part.split("-")
        sh, sm = map(int, start_str.split(":"))
        eh, em = map(int, end_str.split(":"))
        return sh * 60 + sm, eh * 60 + em
    except Exception:
        return None


def violates_fixed_shift(marker: str, candidate: Assignment) -> bool:
    """
    True if `marker` is a fixed-shift marker AND `candidate` does not match
    the required time window exactly.
    """
    if not is_fixed_shift(marker):
        return False
    bounds = fixed_shift_bounds(marker)
    if bounds is None:
        return False
    start_min, end_min = bounds
    return candidate.start_min != start_min or candidate.end_min != end_min


# ---------------------------------------------------------------------------
# Convenience: all hard constraints in one call
# ---------------------------------------------------------------------------

def is_feasible(
    emp_id:          EmpId,
    day:             Day,
    candidate:       Assignment,
    marker:          str,
    solution:        Solution,
    days:            List[Day],
    min_rest_hours:  float = MIN_REST_HOURS_DEFAULT,
) -> bool:
    """
    Return True iff placing `candidate` for (emp_id, day) violates NO hard
    constraint:
      1. marker is not an off/unavailable marker
      2. fixed-shift marker is respected
      3. minimum rest hours satisfied
      4. no more than 5 days in any 6-consecutive-day window
    """
    if is_off_marker(marker):
        return False
    if violates_fixed_shift(marker, candidate):
        return False
    if violates_min_rest(emp_id, day, candidate, solution, days, min_rest_hours):
        return False
    if violates_5_in_6(emp_id, day, solution, days):
        return False
    return True
