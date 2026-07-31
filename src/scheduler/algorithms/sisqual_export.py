"""Convert a solved Sisqual "hours" schedule into the partner import JSON.

Consumes the `List[List[str]]` rows produced by `build_output_rows()` on any of
the Sisqual hours algorithms (header row `["employee_id", day1, day2, ...]`,
cells like `"10:00-11:00@Checkout | 11:00-14:00@Management"`, `"DO"`, `"VAC"`,
`"CLOSED"`, `"UNASSIGNED"`, `"OFF"`) and produces the
`{"OutRosterTeamDays": [...], "OutScheduleUseds": [...]}` structure documented
in the partner's "Importacao da estrutura de dados do schedule generator" spec.

v3 model: the team a segment is worked on is represented as a Task
(OutRosterTeamDayTasks), with TaskID = team name and the segment's real
StartDate/EndDate. TeamCode on OutRosterTeamDays is a fixed placeholder,
since team assignment now lives at the task level, not the day level. This
means each employee-day produces exactly one OutRosterTeamDays entry (unless
the day's periods overflow the 2-window OutScheduleUseds cap, see
MAX_PERIODS_PER_SCHEDULE below).

ScheduleCode: for a single continuous worked period, a 2-period split shift
(one unpaid break in the middle), and for non-worked markers, ScheduleCode is
looked up directly against Sisqual's real registry (see
sisqual_schedule_codes.py) -- it is a real Sisqual code, not one we invented.
When ScheduleCode comes from the registry, ScheduleWeight is also taken from
the registry rather than recomputed, since the registry is the authoritative
source (confirmed: span-minus-break exactly matches ScheduleWeightMinutes
for all 89,390 break-annotated entries in the file Sisqual provided).

Two cases still fall back to a synthetic, locally-unique code (clearly
marked in the output via NEEDS_SISQUAL_CONFIRMATION on that OutScheduleUseds
entry), because no real Sisqual code exists for them in the registry:
  - a worked period (or split shift) with no exact registry match (times not
    aligned to the registry's grid, or a combination of span/break/duration
    the registry doesn't happen to enumerate). CONFIRMED PATTERN: break-free
    codes for ~6h+ spans exist only as 3 hand-picked legacy entries at fixed
    "round" boundaries (08:00-16:00, 16:00-00:00, 00:00-08:00) -- the
    auto-generated grid never produces a break-free code for a long span at
    an arbitrary start time (e.g. there is no plain 14:00-22:00 entry at
    all, even though the grid has hundreds of *with-break* 14:00-22:00
    variants). A zero-gap multi-task day this long (our solvers produce
    these routinely, e.g. Management 14:00-17:00 then Employees 17:00-22:00
    back to back, no gap) therefore has no matching plain-range code and
    always falls back here. This needs a direct answer from Sisqual: either
    they expect us to invent an arbitrary break inside such a shift to match
    their grid, or their grid is genuinely missing break-free codes for
    longer spans at non-legacy start times.
  - a day with 3+ disjoint periods (more than one break): the registry only
    ever encodes a single break per code, so a day with 2+ breaks has no
    possible single-code representation and always falls back
"""

from __future__ import annotations

from itertools import count
from typing import Dict, List, Optional, Tuple

from algorithms.sisqual_hours_utils import minutes_to_hhmm, parse_hhmm
from algorithms.sisqual_schedule_codes import SisqualScheduleCodeRegistry

# Cell tokens with no time range. ScheduleCode for these is looked up from
# the real Sisqual registry (see NON_WORKED_LABEL_BY_MARKER in
# sisqual_schedule_codes.py); DayType is our own bookkeeping value, since the
# registry has no DayType column -- Sisqual's file only lists code,
# Description, and ScheduleWeightMinutes.
SPECIAL_TOKEN_DAY_TYPES = {
    "DO": 1,
    "FDO": 2,
    "VAC": 3,
    "NOT": 4,
    "MED": 5,
    "CLOSED": 6,
    "OFF": 7,
    "UNASSIGNED": 8,
}

# Fallback base for ScheduleCodes we must invent ourselves: a worked period
# with no exact registry match, or a split-shift day (2+ periods), which
# has no known real Sisqual representation yet. Kept far above Sisqual's
# real code range (max real code in the registry is ~300010) so invented and
# real codes can never collide.
SYNTHETIC_SCHEDULE_CODE_BASE = 900_000_000

WORK_DAY_TYPE = 0  # DayType for days with an actual worked schedule.

# Team assignment now lives at the Task level (see OutRosterTeamDayTasks), so
# TeamCode on OutRosterTeamDays is a fixed, generic placeholder.
TEAM_CODE_PLACEHOLDER = "00"

# Fixed placeholder date for OutScheduleUseds Start/EndDate fields. Only the
# time-of-day component of these fields carries meaning to the partner system.
SCHEDULE_TEMPLATE_DATE = "2026-01-01"


def _parse_segment(segment: str) -> Tuple[int, int, str]:
    """'"14:00-22:00@Management"' -> (840, 1320, "Management")."""

    time_part, team = segment.strip().split("@")
    start_text, end_text = time_part.split("-")
    return parse_hhmm(start_text), parse_hhmm(end_text), team.strip()


def _group_into_periods(
    segments: List[Tuple[int, int, str]],
) -> List[List[Tuple[int, int, str]]]:
    """Group a day's segments into periods of contiguous time, across teams.

    Two segments belong to the same period if the first ends exactly when the
    second starts, regardless of which team each is on. A gap in time (e.g. an
    unpaid break) starts a new period. Returns a list of periods, each a list
    of consecutive segments (only its first start / last end matter for
    OutScheduleUseds; every segment still becomes its own Task).
    """

    segments_sorted = sorted(segments, key=lambda item: item[0])
    periods: List[List[Tuple[int, int, str]]] = [[segments_sorted[0]]]
    for segment in segments_sorted[1:]:
        prev_end = periods[-1][-1][1]
        if segment[0] == prev_end:
            periods[-1].append(segment)
        else:
            periods.append([segment])
    return periods


class _SyntheticScheduleCodeAllocator:
    """Assigns deterministic, sequential fallback ScheduleCodes.

    Used ONLY when no real Sisqual registry code applies: a worked period
    with no exact registry match, or a split-shift day (2+ periods), which
    Sisqual's registry has no representation for at all (see module
    docstring). NOT a real Sisqual code -- every OutScheduleUseds entry that
    uses one of these is flagged with NEEDS_SISQUAL_CONFIRMATION: true.

    Codes are handed out in increasing order starting at
    SYNTHETIC_SCHEDULE_CODE_BASE, one per distinct periods pattern, in
    first-seen order. The exact same periods pattern always reuses the same
    code (OutScheduleUseds is a deduplicated lookup table).
    """

    def __init__(self, base: int = SYNTHETIC_SCHEDULE_CODE_BASE):
        self._codes_by_signature: Dict[Tuple, int] = {}
        self._counter = count(base)

    def code_for(self, periods: List[List[Tuple[int, int, str]]]) -> int:
        signature = tuple((period[0][0], period[-1][1]) for period in periods)
        existing = self._codes_by_signature.get(signature)
        if existing is not None:
            return existing

        code = next(self._counter)
        self._codes_by_signature[signature] = code
        return code


# OutScheduleUseds only has room for 2 time windows (StartDate1/2, EndDate1/2)
# per the partner spec. A day can have more than 2 disjoint time-contiguous
# periods (e.g. 3+ breaks), so periods are chunked into groups of at most
# this size, each becoming its own OutRosterTeamDays entry and ScheduleCode
# rather than silently dropping the extra periods.
MAX_PERIODS_PER_SCHEDULE = 2


def _chunk_periods(
    periods: List[List[Tuple[int, int, str]]],
    size: int = MAX_PERIODS_PER_SCHEDULE,
) -> List[List[List[Tuple[int, int, str]]]]:
    return [periods[i:i + size] for i in range(0, len(periods), size)]


def build_sisqual_import_json(
    rows: List[List[str]],
    problem: Dict,
    roster_code: Optional[str] = None,
    registry: Optional[SisqualScheduleCodeRegistry] = None,
) -> Dict:
    """Convert solved schedule rows into the Sisqual import JSON structure.

    `rows` is the `List[List[str]]` returned by a Sisqual hours algorithm's
    `build_output_rows()` (or the equivalent `solve()` return value): header
    row `["employee_id", day1, day2, ...]` followed by one row per employee.
    """

    if not rows:
        return {"OutRosterTeamDays": [], "OutScheduleUseds": []}

    header, *employee_rows = rows
    days = header[1:]

    if roster_code is None:
        roster_code = str(problem.get("metadata", {}).get("problemId", "")).strip() or "UNKNOWN_ROSTER"

    if registry is None:
        registry = SisqualScheduleCodeRegistry()

    roster_team_days: List[Dict] = []
    schedule_used_map: Dict[int, Dict] = {}
    synthetic_allocator = _SyntheticScheduleCodeAllocator()

    for row in employee_rows:
        employee_code = str(row[0]).strip()
        for date_str, raw_cell in zip(days, row[1:]):
            cell = str(raw_cell).strip()
            if not cell:
                continue

            normalized = cell.upper()
            if normalized in SPECIAL_TOKEN_DAY_TYPES:
                day_type = SPECIAL_TOKEN_DAY_TYPES[normalized]
                schedule_code = registry.code_for_non_worked_marker(normalized)
                needs_confirmation = schedule_code is None
                if schedule_code is None:
                    # No real Sisqual code found for this marker even after
                    # collapsing onto Day off / Espaço -- should not happen
                    # given today's registry, but fall back safely instead
                    # of crashing if the registry ever changes.
                    schedule_code = synthetic_allocator.code_for([[(0, 0, normalized)]])

                roster_team_days.append(
                    {
                        "RosterCode": roster_code,
                        "TeamCode": TEAM_CODE_PLACEHOLDER,
                        "EmployeeCode": employee_code,
                        "Date": date_str,
                        "ScheduleCode": schedule_code,
                        "OutRosterTeamDayTasks": [],
                        "OutRosterTeamDayResponsibilities": [],
                    }
                )
                if schedule_code not in schedule_used_map:
                    entry = {
                        "ScheduleCode": schedule_code,
                        "DayType": day_type,
                        "ScheduleWeight": 0,
                    }
                    if needs_confirmation:
                        entry["NEEDS_SISQUAL_CONFIRMATION"] = True
                    schedule_used_map[schedule_code] = entry
                continue

            segments = [_parse_segment(part) for part in cell.split("|")]
            periods = _group_into_periods(segments)

            # A day with more than MAX_PERIODS_PER_SCHEDULE disjoint periods
            # needs more than one OutRosterTeamDays entry, since a single
            # ScheduleCode can only carry 2 windows. Each chunk gets its own
            # entry, carrying only the tasks (segments) that fall within it.
            for period_chunk in _chunk_periods(periods):
                total_minutes = sum(
                    end - start
                    for period in period_chunk
                    for (start, end, _team) in period
                )

                schedule_code = None
                needs_confirmation = False
                if len(period_chunk) == 1:
                    # A single continuous period: look up the real Sisqual
                    # code directly.
                    period_start = period_chunk[0][0][0]
                    period_end = period_chunk[0][-1][1]
                    schedule_code = registry.code_for_time_range(period_start, period_end)
                elif len(period_chunk) == 2:
                    # A split shift: one unpaid break between the two
                    # periods. Look up the real Sisqual code for the overall
                    # span with that exact break window.
                    overall_start = period_chunk[0][0][0]
                    overall_end = period_chunk[1][-1][1]
                    break_start = period_chunk[0][-1][1]
                    break_end = period_chunk[1][0][0]
                    schedule_code = registry.code_for_split_shift(
                        overall_start, overall_end, break_start, break_end
                    )

                if schedule_code is None:
                    # No exact registry match (times not aligned to the
                    # registry's grid, or 3+ periods in one day, which the
                    # registry has no representation for at all): fall back
                    # to a synthetic, locally-consistent code.
                    schedule_code = synthetic_allocator.code_for(period_chunk)
                    needs_confirmation = True
                else:
                    registry_weight = registry.weight_for_code(schedule_code)
                    if registry_weight is not None:
                        total_minutes = registry_weight

                tasks = [
                    {
                        "TaskID": team,
                        "StartDate": f"{date_str}T{minutes_to_hhmm(start)}:00",
                        "EndDate": f"{date_str}T{minutes_to_hhmm(end)}:00",
                    }
                    for period in period_chunk
                    for (start, end, team) in period
                ]

                roster_team_days.append(
                    {
                        "RosterCode": roster_code,
                        "TeamCode": TEAM_CODE_PLACEHOLDER,
                        "EmployeeCode": employee_code,
                        "Date": date_str,
                        "ScheduleCode": schedule_code,
                        "OutRosterTeamDayTasks": tasks,
                        "OutRosterTeamDayResponsibilities": [],
                    }
                )

                if schedule_code not in schedule_used_map:
                    schedule_entry = {
                        "ScheduleCode": schedule_code,
                        "DayType": WORK_DAY_TYPE,
                        "ScheduleWeight": total_minutes,
                    }
                    for index, period in enumerate(period_chunk, start=1):
                        period_start = period[0][0]
                        period_end = period[-1][1]
                        schedule_entry[f"StartDate{index}"] = (
                            f"{SCHEDULE_TEMPLATE_DATE}T{minutes_to_hhmm(period_start)}:00"
                        )
                        schedule_entry[f"EndDate{index}"] = (
                            f"{SCHEDULE_TEMPLATE_DATE}T{minutes_to_hhmm(period_end)}:00"
                        )
                    if needs_confirmation:
                        schedule_entry["NEEDS_SISQUAL_CONFIRMATION"] = True
                    schedule_used_map[schedule_code] = schedule_entry

    return {
        "OutRosterTeamDays": roster_team_days,
        "OutScheduleUseds": list(schedule_used_map.values()),
    }
