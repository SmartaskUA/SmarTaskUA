"""Shared domain for v4.0: time, dates, cells, and all CSV reading.

Decides nothing about what counts as an error - that is the validator's job. The
split matters because two callers read the same files with opposite needs: the
adapter and the feasibility scan want a hard failure on malformed input, while
the validator must never crash on it. So every parser comes in two forms, a
``try_`` one returning None and a strict one raising `DomainError`.

Symbols in square brackets refer to MathematicalDefinition7.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Iterable, Iterator

MINUTES_PER_DAY = 1440

WEEKDAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]

#: Operators a schedule_input cell may carry, each taking one or more
#: comma-separated ``HH:MM-HH:MM`` ranges. Carried over from v3.0; SISQUAL's
#: exporter emits none of them, but they remain authorable.
OPERATORS = ("EQUALS", "INCLUDE", "WITHIN", "EXCEPT")

#: Cell kinds that ask for a working day.
ASKS_FOR_WORK = frozenset({"auto", "exact_hours", "equals", "include", "within", "except"})


class DomainError(Exception):
    """Malformed input the domain layer refuses to guess at."""


# --------------------------------------------------------------------------
# numbers
#
# SISQUAL writes decimals with a comma and quotes the field: "7,2". A bare
# float() throws on that, and splitting on commas without honouring quotes
# silently turns one column into two. Both are handled here, once.
# --------------------------------------------------------------------------

def try_number(text: str) -> float | None:
    """Parse a number written with either a dot or a comma decimal separator."""
    if text is None:
        return None
    s = str(text).strip().replace(" ", "")
    if not s:
        return None
    if s.count(",") == 1 and "." not in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def number(text: str) -> float:
    value = try_number(text)
    if value is None:
        raise DomainError(f"not a number: {text!r}")
    return value


def format_number(value: float) -> str:
    """Render a number with a dot separator and no trailing .0 on whole values."""
    if value == int(value):
        return str(int(value))
    return repr(round(value, 6))


# --------------------------------------------------------------------------
# time
# --------------------------------------------------------------------------

_HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def try_hhmm_to_min(text: str) -> int | None:
    m = _HHMM.match((text or "").strip())
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def hhmm_to_min(text: str) -> int:
    value = try_hhmm_to_min(text)
    if value is None:
        raise DomainError(f"not a HH:MM clock time: {text!r}")
    return value


def min_to_hhmm(value: int) -> str:
    return f"{(value // 60) % 24:02d}:{value % 60:02d}"


def try_parse_range(start: str, end: str) -> tuple[int, int] | None:
    """(startMin, endMin) for a window, or None if either boundary is malformed.

    A window whose ``end <= start`` crosses midnight, and the roll-over is
    resolved here into minutes past 1440 so no later reader has to infer it.
    """
    a, b = try_hhmm_to_min(start), try_hhmm_to_min(end)
    if a is None or b is None:
        return None
    if b <= a:
        b += MINUTES_PER_DAY
    return a, b


def parse_range(start: str, end: str) -> tuple[int, int]:
    value = try_parse_range(start, end)
    if value is None:
        raise DomainError(f"not a HH:MM-HH:MM window: {start!r}-{end!r}")
    return value


def on_grid(value: int, slot_minutes: int) -> bool:
    return slot_minutes > 0 and value % slot_minutes == 0


def hours_to_minutes(hours: float) -> int | None:
    """Convert a schedule_input cell's hours to whole minutes, or None if it is not whole.

    v4.0 cells are HOURS (SISQUAL's unit) while contracts state minutes - the two
    coexist, deliberately and uncomfortably, until Sisqual agrees to switch. See
    docs/next_meeting.md item 16.
    """
    minutes = hours * 60
    if abs(minutes - round(minutes)) > 1e-6:
        return None
    return int(round(minutes))


@dataclass(frozen=True, order=True)
class Interval:
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Interval") -> bool:
        return self.start <= other.start and other.end <= self.end

    def __str__(self) -> str:
        return f"{min_to_hhmm(self.start)}-{min_to_hhmm(self.end)}"


def coalesce(intervals: Iterable[Interval]) -> tuple[Interval, ...]:
    """Merge overlapping *or touching* intervals into their union, ascending."""
    ordered = sorted(intervals)
    if not ordered:
        return ()
    merged = [ordered[0]]
    for iv in ordered[1:]:
        last = merged[-1]
        if iv.start <= last.end:
            merged[-1] = Interval(last.start, max(last.end, iv.end))
        else:
            merged.append(iv)
    return tuple(merged)


def slots_of(intervals: Iterable[Interval], slot_minutes: int) -> set[int]:
    """The timeslot indices an assignment covers [delta_wdht]."""
    slots: set[int] = set()
    for iv in intervals:
        slots.update(range(iv.start // slot_minutes, -(-iv.end // slot_minutes)))
    return slots


# --------------------------------------------------------------------------
# dates
# --------------------------------------------------------------------------

def iso(text: str) -> date | None:
    """Parse YYYY-MM-DD, or None if it is not a date.

    Tolerates a trailing time, because SISQUAL mixes three datetime spellings:
    a bare date, an ISO instant with Z, and a naive YYYY-MM-DDTHH:MM:SS.
    """
    if not isinstance(text, str):
        return None
    head = text.strip().replace(" ", "T").split("T", 1)[0]
    try:
        return date.fromisoformat(head)
    except ValueError:
        return None


def horizon(problem: dict) -> list[date]:
    """Every date in temporalScope, inclusive, or [] if the scope is unusable."""
    scope = problem.get("temporalScope", {})
    start, end = iso(scope.get("start", "")), iso(scope.get("end", ""))
    if not start or not end or end < start:
        return []
    return [start + timedelta(days=i) for i in range((end - start).days + 1)]


def week_index(day: date, origin: date, week_start: str) -> int:
    """Which week `day` falls in, counting from the week containing `origin`.

    Case-insensitive, because SISQUAL capitalises the weekday and a validator
    must report that rather than die on it.
    """
    try:
        start_idx = WEEKDAY_NAMES.index((week_start or "monday").strip().lower())
    except ValueError:
        raise DomainError(f"{week_start!r} is not a weekday name") from None
    shift = (origin.weekday() - start_idx) % 7
    week0 = origin - timedelta(days=shift)
    return (day - week0).days // 7


def covers(entry: dict, day: date) -> bool:
    """Whether a {start, end|null} assignment covers `day`. Inclusive; null end is open."""
    start = iso(entry.get("start", ""))
    if not start or day < start:
        return False
    end = iso(entry["end"]) if entry.get("end") else None
    return end is None or day <= end


def active_contract(employee: dict, day: date | None) -> str | None:
    """The contractType covering `day`, or None."""
    if day is None:
        return None
    for entry in employee.get("contractAssignments", []):
        if covers(entry, day):
            return entry.get("contractType")
    return None


def active_competencies(employee: dict, day: date | None) -> list[dict]:
    """The competencyAssignments covering `day`."""
    if day is None:
        return []
    return [e for e in employee.get("competencyAssignments", []) if covers(e, day)]


def contracts_by_id(problem: dict) -> dict[str, dict]:
    return {c["id"]: c for c in problem.get("contracts", {}).get("definitions", []) if "id" in c}


def dimension_set(problem: dict) -> set[tuple[str, str]]:
    """The declared (tableName, tableValue) coordinates [S]."""
    return {
        (d["tableName"], d["tableValue"])
        for d in problem.get("demand", {}).get("dimensions", [])
        if "tableName" in d and "tableValue" in d
    }


def day_off_sets(section: dict) -> tuple[set[str], set[str]]:
    """(preferable, unavailable) code sets from scheduleInput.dayOffCodes.

    The one place the dayOffCodes map shape is read, so every caller agrees on it.
    """
    codes = section.get("dayOffCodes", {})
    preferable = {c for c, v in codes.items() if v.get("kind") == "preferable"}
    unavailable = {c for c, v in codes.items() if v.get("kind") == "unavailable"}
    return preferable, unavailable


# --------------------------------------------------------------------------
# CSV reading
#
# SISQUAL's files are UTF-8 with a BOM and CRLF line endings. Reading them with
# a plain open() leaves '﻿date' as the first header name, which then fails
# every column lookup by a character nobody can see. utf-8-sig and newline=''
# are therefore not optional.
# --------------------------------------------------------------------------

def open_csv(path: Path) -> io.TextIOWrapper:
    return path.open(newline="", encoding="utf-8-sig")


def csv_lines(fh) -> Iterator[str]:
    """Yield CSV lines, skipping blank lines and '#' comments.

    A line whose first non-whitespace character is '#' is a comment, so the
    templates can document themselves in place. SISQUAL's own exports carry no
    comments, but reading both the same way keeps one code path.
    """
    for ln in fh:
        if ln.strip() and not ln.lstrip().startswith("#"):
            yield ln


def read_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    """(header, rows) from a CSV, BOM- and comment-tolerant."""
    with open_csv(path) as fh:
        reader = csv.DictReader(csv_lines(fh))
        header = list(reader.fieldnames or [])
        rows = [{k: (v if v is not None else "") for k, v in r.items() if k is not None}
                for r in reader]
    return header, rows


DEMAND_COLUMNS = ["date", "tableName", "tableValue", "minimum", "ideal", "estimated", "start", "end"]
SHIFTS_COLUMNS = ["date", "workPeriod", "tableName", "tableValue",
                  "minimum", "ideal", "estimated", "start", "end"]
SCHEDULE_COLUMNS = ["code", "description", "scheduleWeightMinutes", "startMin", "endMin"]


@dataclass(frozen=True)
class DemandRow:
    """One coverage row. `window` is None on the days grain, which has no window."""
    date: date
    table_name: str
    table_value: str
    minimum: float
    ideal: float
    estimated: float
    window: Interval | None
    work_period: str = ""
    line: int = 0


def read_demand(path: Path, grain: str) -> tuple[list[str], list[DemandRow], list[str]]:
    """(header, rows, problems) for one demand CSV.

    `grain` is days | periods | shifts. Lenient by design: a malformed row is
    reported in `problems` and skipped, so one bad line cannot hide the rest.
    The days and periods files have byte-identical headers - only the JSON key
    that pointed here says which is which, which is why `grain` is a parameter
    and never sniffed.
    """
    header, raw = read_rows(path)
    wanted = SHIFTS_COLUMNS if grain == "shifts" else DEMAND_COLUMNS
    problems: list[str] = []
    missing = [c for c in wanted if c not in header]
    if missing:
        problems.append(f"missing column(s) {', '.join(missing)}; expected {','.join(wanted)}")
        return header, [], problems

    rows: list[DemandRow] = []
    for n, r in enumerate(raw, start=2):
        day = iso(r["date"])
        if not day:
            problems.append(f"row {n}: bad date {r['date']!r}")
            continue
        values = []
        for col in ("minimum", "ideal", "estimated"):
            v = try_number(r[col])
            if v is None:
                problems.append(f"row {n}: {col} is not a number ({r[col]!r})")
                v = 0.0
            values.append(v)
        window = None
        if r["start"] or r["end"]:
            window_pair = try_parse_range(r["start"], r["end"])
            if window_pair is None:
                problems.append(f"row {n}: bad window {r['start']!r}-{r['end']!r}")
            else:
                window = Interval(*window_pair)
        rows.append(DemandRow(
            date=day,
            table_name=r["tableName"].strip(),
            table_value=r["tableValue"].strip(),
            minimum=values[0], ideal=values[1], estimated=values[2],
            window=window,
            work_period=r.get("workPeriod", "").strip(),
            line=n,
        ))
    return header, rows, problems


def read_schedule_input(path: Path) -> tuple[dict[str, dict[str, str]], list[str], list[str]]:
    """({employee_id: {date: cell}}, date columns, problems)."""
    header, raw = read_rows(path)
    problems: list[str] = []
    if not header or header[0] != "employee_id":
        problems.append(f"first column must be 'employee_id', found {header[:1] or ['(nothing)']!r}")
        return {}, [], problems
    dates = header[1:]
    for col in dates:
        if not iso(col):
            problems.append(f"header column {col!r} is not a YYYY-MM-DD date")
    cells: dict[str, dict[str, str]] = {}
    for n, r in enumerate(raw, start=2):
        eid = r["employee_id"].strip()
        if eid in cells:
            problems.append(f"row {n}: employee {eid} appears twice")
        cells[eid] = {d: (r.get(d) or "").strip() for d in dates}
    return cells, dates, problems


@dataclass(frozen=True)
class Schedule:
    """One ScheduleCode from the catalogue."""
    code: int
    description: str
    weight_minutes: int
    interval: Interval | None   # None for a sentinel or a Flexible entry

    @property
    def is_sentinel(self) -> bool:
        return self.interval is None and self.weight_minutes == 0


def read_schedules(path: Path) -> tuple[dict[int, Schedule], list[str]]:
    """({code: Schedule}, problems) from the ScheduleCode catalogue CSV."""
    header, raw = read_rows(path)
    problems: list[str] = []
    missing = [c for c in SCHEDULE_COLUMNS if c not in header]
    if missing:
        problems.append(f"missing column(s) {', '.join(missing)}; expected {','.join(SCHEDULE_COLUMNS)}")
        return {}, problems
    out: dict[int, Schedule] = {}
    for n, r in enumerate(raw, start=2):
        try:
            code = int(r["code"])
        except ValueError:
            problems.append(f"row {n}: code {r['code']!r} is not an integer")
            continue
        weight = try_number(r["scheduleWeightMinutes"])
        start, end = try_number(r["startMin"]), try_number(r["endMin"])
        interval = Interval(int(start), int(end)) if start is not None and end is not None else None
        if code in out:
            problems.append(f"row {n}: code {code} appears twice")
        out[code] = Schedule(code, r["description"].strip(),
                             int(weight or 0), interval)
    return out, problems


# --------------------------------------------------------------------------
# schedule_input cell grammar
# --------------------------------------------------------------------------

@dataclass
class CellRule:
    """What one schedule_input cell asks for.

    kind is one of: auto | exact_hours | equals | include | within | except
                  | dayoff | empty
    """
    kind: str
    minutes: int | None = None
    windows: tuple[Interval, ...] = ()
    day_off: str | None = None          # "preferable" | "unavailable"
    code: str | None = None
    raw: str = ""


def _parse_windows(spec: str) -> tuple[Interval, ...]:
    out = []
    for part in spec.split(","):
        part = part.strip()
        if "-" not in part:
            raise DomainError(f"window {part!r} is not HH:MM-HH:MM")
        a, b = part.split("-", 1)
        out.append(Interval(*parse_range(a, b)))
    if not out:
        raise DomainError("operator carries no window")
    return coalesce(out)


def classify_cell(raw: str, problem: dict) -> CellRule:
    """Parse one cell. Raises DomainError on anything it will not guess at.

    A numeric cell is HOURS in v4.0. v3.0 read the same position as minutes and
    rejected 1-24 as unmigrated v2.6 hours; v4.0 inverts that guard, because
    SISQUAL emits exactly those values and means them. A value above 24 is now
    the suspicious one - it is almost certainly v3 minutes that were never
    converted.
    """
    text = (raw or "").strip()
    if not text:
        return CellRule("empty", raw=raw)

    upper = text.upper()
    for op in OPERATORS:
        if upper.startswith(op + ":"):
            return CellRule(op.lower(), windows=_parse_windows(text[len(op) + 1:]), raw=raw)

    if upper == "A":
        return CellRule("auto", raw=raw)

    hours = try_number(text)
    if hours is not None:
        if hours <= 0:
            raise DomainError(f"cell {text!r}: a working day of {hours} hours")
        if hours > 24:
            raise DomainError(
                f"cell {text!r}: cells are HOURS in v4.0, and {format_number(hours)} hours "
                f"is longer than a day. A value this size is usually v3.0 minutes that were "
                f"never converted - divide by 60."
            )
        minutes = hours_to_minutes(hours)
        if minutes is None:
            raise DomainError(f"cell {text!r}: {format_number(hours)} hours is not a whole number of minutes")
        return CellRule("exact_hours", minutes=minutes, raw=raw)

    preferable, unavailable = day_off_sets(problem.get("scheduleInput", {}))
    if text in preferable:
        return CellRule("dayoff", day_off="preferable", code=text, raw=raw)
    if text in unavailable:
        return CellRule("dayoff", day_off="unavailable", code=text, raw=raw)
    raise DomainError(
        f"cell {text!r} is not a number, not an {'/'.join(OPERATORS)} window, and is not "
        f"declared in scheduleInput.dayOffCodes"
    )


# --------------------------------------------------------------------------
# feasibility
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Diagnostic:
    employee: str
    date: str
    cell: str
    reason: str

    def __str__(self) -> str:
        return f"{self.employee} on {self.date}: cell {self.cell!r} - {self.reason}"


def scan_feasibility(problem: dict, base: Path) -> list[Diagnostic]:
    """Worker-days whose cell cannot be satisfied. The single source of these.

    The validator turns each one into an error. Kept here, away from both, so
    they cannot disagree about what is impossible.
    """
    section = problem.get("scheduleInput", {})
    path = base / section.get("dataFile", "")
    if not path.is_file():
        return []
    cells, dates, _ = read_schedule_input(path)
    contracts = contracts_by_id(problem)
    slot = problem.get("timeGrid", {}).get("slotMinutes", 30)
    out: list[Diagnostic] = []

    for emp in problem.get("employees", {}).get("list", []):
        eid = emp.get("id", "")
        row = cells.get(eid)
        if row is None:
            continue
        for col in dates:
            day = iso(col)
            raw = row.get(col, "")
            try:
                rule = classify_cell(raw, problem)
            except DomainError as exc:
                out.append(Diagnostic(eid, col, raw, str(exc)))
                continue
            if rule.kind not in ASKS_FOR_WORK:
                continue

            contract_id = active_contract(emp, day)
            if contract_id is None:
                out.append(Diagnostic(eid, col, raw, "asks for work on a day no contract covers"))
                continue
            contract = contracts.get(contract_id)
            if contract is None:
                out.append(Diagnostic(eid, col, raw,
                                      f"contract {contract_id!r} is not in contracts.definitions"))
                continue

            wanted = contract.get("workMinutesPerDay")
            if rule.kind == "exact_hours" and wanted is not None and rule.minutes != wanted:
                out.append(Diagnostic(
                    eid, col, raw,
                    f"{rule.minutes} min does not match contract {contract_id}'s "
                    f"workMinutesPerDay of {wanted}"))
            duration = rule.minutes if rule.kind == "exact_hours" else wanted
            if duration is not None and not on_grid(duration, slot):
                out.append(Diagnostic(eid, col, raw,
                                      f"{duration} min is not a multiple of the {slot}-minute grid"))
            for win in rule.windows:
                if not on_grid(win.start, slot) or not on_grid(win.end, slot):
                    out.append(Diagnostic(eid, col, raw,
                                          f"window {win} does not land on the {slot}-minute grid"))
    return out
