#!/usr/bin/env python3
"""Shared domain for the v3.0 tooling.

The transformer and the validator both need to reason about the same things --
minutes on a grid, what a schedule-input cell means, which assignment blocks a
worker-day could take, why a day came out empty.  Those definitions live here,
once.  This module imports neither tool; both import it.

Nothing here does I/O beyond reading the two CSVs a problem points at, and
nothing here decides policy (what is an error, what to emit) -- that belongs to
the callers.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

MINUTES_PER_DAY = 1440

WEEKDAY_NAMES = [
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
]

# Codes that are unavailable by definition: if a problem uses them they must be
# declared in dayOffCodes with kind "unavailable", never "preferable". (They are no
# longer implicitly accepted -- every code used is declared explicitly.)
ALWAYS_UNAVAILABLE = {"VAC", "NOT"}

# Cell kinds that ask for work to happen. A day-off code does not, and a blank
# cell does not, so neither can ever be "impossible".
ASKS_FOR_WORK = frozenset({"auto", "exact_minutes", "equals", "include", "except"})
# 'auto' means "fill this day from the contract IF the contract allows it", so it
# is not a contradiction on a weekday the contract excludes. Naming a shift
# explicitly on such a day is.
EXPLICIT_WORK = ASKS_FOR_WORK - {"auto"}


class DomainError(Exception):
    """Raised when a problem cannot be interpreted (malformed times, unknown cells)."""


# --------------------------------------------------------------------------
# time
# --------------------------------------------------------------------------

# Two parsing contracts, on purpose. The transformer interprets input the schema
# has already accepted, so a bad time there is a bug -> the strict forms raise.
# The validator is looking AT possibly-bad input, so it must not crash on it ->
# the try_ forms return None and let the caller report a clean error.

def try_hhmm_to_min(text: str) -> int | None:
    """'08:30' -> 510, or None if it is not a valid HH:MM."""
    try:
        h, m = str(text).strip().split(":")
        h, m = int(h), int(m)
    except (ValueError, AttributeError):
        return None
    if not (0 <= h <= 23 and 0 <= m <= 59):
        return None
    return h * 60 + m


def hhmm_to_min(text: str) -> int:
    """'08:30' -> 510. Raises DomainError on malformed input."""
    value = try_hhmm_to_min(text)
    if value is None:
        raise DomainError(f"malformed time {text!r}, expected HH:MM")
    return value


def min_to_hhmm(value: int) -> str:
    """510 -> '08:30'.  Values past midnight wrap for display only."""
    value %= MINUTES_PER_DAY
    return f"{value // 60:02d}:{value % 60:02d}"


def try_parse_range(start: str, end: str) -> tuple[int, int] | None:
    """Clock range -> half-open minute range, or None if either end is malformed."""
    lo, hi = try_hhmm_to_min(start), try_hhmm_to_min(end)
    if lo is None or hi is None:
        return None
    if hi <= lo:
        hi += MINUTES_PER_DAY
    return lo, hi


def parse_range(start: str, end: str) -> tuple[int, int]:
    """Clock range -> half-open minute range, unrolling midnight. Raises on malformed.

    v2.6 stored bare HH:MM and left readers to infer roll-over from start > end.
    Here the end is carried past 1440 instead, so 22:00-06:30 is (1320, 1830)
    and no consumer has to guess.
    """
    lo, hi = hhmm_to_min(start), hhmm_to_min(end)
    if hi <= lo:
        hi += MINUTES_PER_DAY
    return lo, hi


def on_grid(value: int, slot_minutes: int) -> bool:
    return value % slot_minutes == 0


@dataclass(frozen=True, order=True)
class Interval:
    start: int
    end: int

    def overlaps(self, other: "Interval") -> bool:
        return self.start < other.end and other.start < self.end

    def contains(self, other: "Interval") -> bool:
        return self.start <= other.start and other.end <= self.end

    @property
    def length(self) -> int:
        return self.end - self.start


def slots_of(intervals: tuple[Interval, ...], slot_minutes: int) -> set[int]:
    """Timeslot indices covered by the intervals -- the model's delta_wdht."""
    covered: set[int] = set()
    for iv in intervals:
        covered.update(range(iv.start // slot_minutes, iv.end // slot_minutes))
    return covered


def render_slots(slots: set[int], slot_minutes: int) -> str:
    """Describe a set of timeslot indices as human clock ranges."""
    if not slots:
        return "nothing"
    ordered = sorted(slots)
    spans, start, prev = [], ordered[0], ordered[0]
    for idx in ordered[1:]:
        if idx == prev + 1:
            prev = idx
            continue
        spans.append((start, prev))
        start = prev = idx
    spans.append((start, prev))
    return ", ".join(
        f"{min_to_hhmm(a * slot_minutes)}-{min_to_hhmm((b + 1) * slot_minutes)}" for a, b in spans
    )


# --------------------------------------------------------------------------
# dates
# --------------------------------------------------------------------------

def iso(text: str) -> date | None:
    """Parse YYYY-MM-DD, or None if it is not a date."""
    try:
        return date.fromisoformat(text)
    except (ValueError, TypeError):
        return None


def week_index(day: date, origin: date, week_start: str) -> int:
    """Which week `day` falls in, counting from the week containing `origin`."""
    start_idx = WEEKDAY_NAMES.index(week_start)
    shift = (origin.weekday() - start_idx) % 7
    week0 = origin - timedelta(days=shift)
    return (day - week0).days // 7


def _covers(entry: dict, day: date) -> bool:
    """Whether a {start, end|null} assignment covers `day`. Inclusive; null end is open."""
    start = iso(entry.get("start", ""))
    if not start or day < start:
        return False
    end = iso(entry["end"]) if entry.get("end") else None
    return end is None or day <= end


def active_period(assignments: list[dict], day: date | None, key: str):
    """Value of `key` on the assignment covering `day`, or None."""
    if day is None:
        return None
    for entry in assignments:
        if _covers(entry, day):
            return entry.get(key)
    return None


def active_teams(assignments: list[dict], day: date | None) -> list[dict]:
    """All team assignments covering `day`."""
    if day is None:
        return []
    return [entry for entry in assignments if _covers(entry, day)]


# --------------------------------------------------------------------------
# work periods -> operating window
# --------------------------------------------------------------------------

def period_ranges(problem: dict) -> dict[str, Interval]:
    """Clock range of each declared work period.

    Work periods are DEMAND BUCKETS, not employee shifts: demand.csv keys its
    coverage numbers on them, and together they delimit the operating window.
    They are not the menu a worker chooses from -- see build_day_candidates.
    """
    out: dict[str, Interval] = {}
    for wp in problem["demand"]["workPeriods"]:
        code = wp["code"]
        if "timeRange" not in wp:
            raise DomainError(f"work period {code!r} has no timeRange")
        lo, hi = parse_range(wp["timeRange"]["start"], wp["timeRange"]["end"])
        out[code] = Interval(lo, hi)
    return out


def operating_window(periods: dict[str, Interval], slot: int) -> Interval:
    """Earliest start to latest end across all work periods -- the extent of T."""
    if not periods:
        raise DomainError("demand.workPeriods is empty; cannot derive an operating window")
    lo = min(iv.start for iv in periods.values())
    hi = max(iv.end for iv in periods.values())
    for bound in (lo, hi):
        if not on_grid(bound, slot):
            raise DomainError(
                f"operating window boundary {min_to_hhmm(bound)} does not fall on the "
                f"{slot}-minute grid"
            )
    return Interval(lo, hi)


def period_meta(problem: dict, periods: dict[str, Interval]) -> dict[Interval, tuple[str, int]]:
    """Map each period's exact range to (code, unpaid break minutes)."""
    meta: dict[Interval, tuple[str, int]] = {}
    for wp in problem["demand"]["workPeriods"]:
        unpaid = sum(
            b["durationMinutes"] for b in wp.get("breaks", []) if not b.get("paid", False)
        )
        meta[periods[wp["code"]]] = (wp["code"], unpaid)
    return meta


def generate_blocks(duration: int, window: Interval, slot: int) -> list[Interval]:
    """Every contiguous block of `duration` that fits in `window`, stepping by one slot."""
    if duration <= 0 or duration > window.length:
        return []
    return [
        Interval(start, start + duration)
        for start in range(window.start, window.end - duration + 1, slot)
    ]


# --------------------------------------------------------------------------
# I/O: the two CSVs
# --------------------------------------------------------------------------

def read_demand(
    problem: dict, base: Path, periods: dict[str, Interval]
) -> tuple[dict[str, set[int]], list[dict]]:
    """Return (timeslots demanded per date [T_d], raw rows).

    Dates with no rows are closed: v2.6 established that a missing row means the
    shift is not operating, and a date with no rows at all is outside D_o.
    """
    demand = problem["demand"]
    data_file = demand.get("dataFile")
    if not data_file:
        raise DomainError("demand.dataFile is required to expand a problem")

    path = base / data_file
    if not path.exists():
        raise DomainError(f"demand file not found: {path}")

    slot = problem["timeGrid"]["slotMinutes"]
    t_d: dict[str, set[int]] = {}
    rows: list[dict] = []

    with path.open(newline="") as fh:
        for lineno, row in enumerate(csv.DictReader(fh), start=2):
            if not row.get("date"):
                continue
            rows.append(row)
            code = row["workPeriod"]
            if code not in periods:
                raise DomainError(f"{path.name}:{lineno}: unknown workPeriod {code!r}")

            start, end = row.get("start") or "", row.get("end") or ""
            if bool(start) != bool(end):
                raise DomainError(
                    f"{path.name}:{lineno}: start and end must be given together or not at all"
                )
            if start:
                lo, hi = parse_range(start, end)
            else:
                lo, hi = periods[code].start, periods[code].end

            t_d.setdefault(row["date"], set()).update(slots_of((Interval(lo, hi),), slot))

    return t_d, rows


def read_schedule_input(problem: dict, base: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    """Return ({employee_id: {date: cell}}, ordered date columns)."""
    section = problem["scheduleInput"]
    path = base / section["dataFile"]
    if not path.exists():
        raise DomainError(f"schedule input file not found: {path}")

    with path.open(newline="") as fh:
        reader = csv.reader(fh)
        header = next(reader)
        if not header or header[0] != "employee_id":
            raise DomainError("schedule_input.csv: first column must be 'employee_id'")
        dates = [h.strip() for h in header[1:]]

        cells: dict[str, dict[str, str]] = {}
        for row in reader:
            if not row or not row[0].strip():
                continue
            cells[row[0].strip()] = {
                d: (row[i + 1].strip() if i + 1 < len(row) else "")
                for i, d in enumerate(dates)
            }

    return cells, dates


# --------------------------------------------------------------------------
# cells
# --------------------------------------------------------------------------

def day_off_sets(section: dict) -> tuple[set[str], set[str]]:
    """(preferable, unavailable) code sets from scheduleInput.dayOffCodes.

    The one place the dayOffCodes map shape is read, so the transformer and the
    validator agree on it.
    """
    codes = section.get("dayOffCodes", {})
    preferable = {c for c, v in codes.items() if v.get("kind") == "preferable"}
    unavailable = {c for c, v in codes.items() if v.get("kind") == "unavailable"}
    return preferable, unavailable


@dataclass
class CellRule:
    """What one schedule-input cell says about one worker-day."""

    kind: str  # auto | exact_minutes | equals | include | except | dayoff | empty
    minutes: int | None = None
    window: Interval | None = None
    day_off: str | None = None  # preferable | unavailable
    reason: str | None = None
    code: str | None = None


def classify_cell(raw: str, problem: dict) -> CellRule:
    """Interpret a schedule-input cell."""
    text = (raw or "").strip()
    if not text:
        # A blank cell offers the worker nothing, matching the live solver, which
        # treats an empty marker exactly like an off marker.  It does NOT mean
        # "unconstrained".
        return CellRule(kind="empty")

    preferable, unavailable = day_off_sets(problem["scheduleInput"])

    upper = text.upper()

    for op in ("EQUALS", "INCLUDE", "EXCEPT"):
        if upper.startswith(op + ":"):
            body = text.split(":", 1)[1]
            try:
                start, end = body.split("-")
            except ValueError as exc:
                raise DomainError(
                    f"malformed time-window constraint {text!r}, expected {op}:HH:MM-HH:MM"
                ) from exc
            lo, hi = parse_range(start, end)
            return CellRule(kind=op.lower(), window=Interval(lo, hi), code=text)

    if upper == "A":
        return CellRule(kind="auto", code=text)

    if text in preferable:
        return CellRule(kind="dayoff", day_off="preferable", code=text)

    if text in unavailable:
        reason = {
            "VAC": "vacation",
            "NOT": "not_available",
            "FDO": "fixed_day_off",
            "Med": "medical",
        }.get(text, "other")
        return CellRule(kind="dayoff", day_off="unavailable", reason=reason, code=text)

    if text.isdigit():
        value = int(text)
        # v2.6 wrote whole hours here (integers 1-16).  v3 is minutes throughout,
        # so an unmigrated file would silently turn an 8-hour day into 8 minutes.
        # Nothing in the corpus is a legitimate sub-25-minute assignment, so this
        # range is far more likely to be a stale hours value than a real one.
        if 1 <= value <= 24:
            raise DomainError(
                f"schedule input cell {text!r}: numeric cells are MINUTES in v3.0, and "
                f"{value} looks like a v2.6 hours value. Write {value * 60} for {value} hours. "
                "See MIGRATION-2.6-to-3.0.md."
            )
        return CellRule(kind="exact_minutes", minutes=value, code=text)

    raise DomainError(
        f"schedule input cell {text!r} is not recognised. Declare it in "
        "scheduleInput.dayOffCodes with kind 'preferable' (may be worked at a penalty) or "
        "'unavailable' (cannot be worked)."
    )


# --------------------------------------------------------------------------
# candidate assignments (H_wd before the T_d filter)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Candidate:
    """One way a worker could spend a day, before the T_d filter."""

    intervals: tuple[Interval, ...]
    weight: int
    work_period: str | None = None

    def key(self) -> tuple:
        """Identity for deduplication.

        Keyed on coverage and paid weight only, deliberately excluding the
        originating work period: two options that resolve to the same intervals
        and weight are the same option as far as the model is concerned, and
        emitting both would hand the solver a pair of symmetric duplicates.
        """
        return (self.intervals, self.weight)


def day_allowed(contract: dict | None, weekday: str) -> bool:
    """Whether the contract permits work on this weekday at all."""
    constraints = (contract or {}).get("constraints", {})
    allowed = constraints.get("availableDays")
    if constraints.get("weekdaysOnly"):
        allowed = WEEKDAY_NAMES[:5]
    elif constraints.get("weekendsOnly"):
        allowed = WEEKDAY_NAMES[5:]
    return not allowed or weekday in allowed


def build_day_candidates(
    rule: CellRule,
    contract: dict | None,
    window: Interval,
    slot: int,
    meta: dict[Interval, tuple[str, int]],
) -> list[Candidate]:
    """The daily working assignments a worker could take -- H_wd before the T_d filter.

    A worker is NOT choosing from the menu of declared work periods.  Those are
    demand buckets; a shop that wants one person on Checkout 11:00-21:00 is not
    saying anyone works a ten-hour shift.  What the worker takes is a contiguous
    block of their contracted length, positioned anywhere on the grid inside the
    operating window -- which is how the live solver reads a numeric cell and why
    the sisqual example can ask a full-timer for 8h when no declared period is 8h.

    The cell fixes the block's length, its position, or both:
      A                     contract's daily minutes, any position
      <minutes>             exactly that many minutes, any position
      EQUALS:a-b            exactly that block
      INCLUDE:a-b           contract length, must cover [a,b]
      EXCEPT:a-b            contract length, must avoid [a,b]
    """
    if rule.kind == "equals":
        blocks = [rule.window]
    elif rule.kind in ("auto", "include", "except", "exact_minutes") or (
        rule.kind == "dayoff" and rule.day_off == "preferable"
    ):
        # A preferable day off still gets the full menu: it is a soft wish, and the
        # model is allowed to schedule over it at a penalty (x'_wd, OF3).  Give it
        # no options and it silently degrades into a hard day off.
        if rule.kind == "exact_minutes":
            duration = rule.minutes
        elif contract is None:
            return []
        else:
            duration = contract["workMinutesPerDay"]
        blocks = generate_blocks(duration, window, slot)
        if rule.kind == "include":
            blocks = [b for b in blocks if b.contains(rule.window)]
        elif rule.kind == "except":
            blocks = [b for b in blocks if not b.overlaps(rule.window)]
    else:
        return []

    out = []
    for block in blocks:
        # An assignment that happens to coincide exactly with a declared period
        # inherits that period's unpaid breaks, which is the only place breaks can
        # attach: a free-floating block has no period to take them from.
        match = meta.get(block)
        if match:
            code, unpaid = match
            out.append(Candidate((block,), max(0, block.length - unpaid), code))
        else:
            out.append(Candidate((block,), block.length, None))
    return out


def required_duration(rule: CellRule, contract: dict | None) -> int | None:
    """Minutes of work the cell asks for, or None if it asks for none."""
    if rule.kind == "equals":
        return rule.window.length
    if rule.kind == "exact_minutes":
        return rule.minutes
    if rule.kind in ("auto", "include", "except"):
        return contract["workMinutesPerDay"] if contract else None
    return None


def diagnose(
    rule: CellRule,
    contract: dict | None,
    window: Interval,
    slot: int,
    demanded: set[int],
    had_candidates: bool,
) -> str | None:
    """Explain why a worker-day ended up with no possible assignment.

    Ordered so the most specific cause wins: an EQUALS reaching outside opening
    hours is reported as exactly that, rather than as the downstream symptom of
    every candidate being filtered out.
    """
    duration = required_duration(rule, contract)
    if duration is None:
        return None

    def clock(iv: Interval) -> str:
        return f"{min_to_hhmm(iv.start)}-{min_to_hhmm(iv.end)}"

    if rule.kind == "equals":
        if not window.contains(rule.window):
            return (
                f"it asks for {clock(rule.window)}, which is outside the operating window "
                f"{clock(window)}"
            )
        for bound in (rule.window.start, rule.window.end):
            if bound % slot:
                return f"the boundary {min_to_hhmm(bound)} is not on the {slot}-minute grid"

    if rule.kind == "include":
        if rule.window.length > duration:
            return (
                f"it asks to cover {clock(rule.window)} ({rule.window.length} min) but only "
                f"{duration} min is worked that day, so no block can contain it"
            )
        if not window.contains(rule.window):
            return (
                f"it asks to cover {clock(rule.window)}, which is outside the operating window "
                f"{clock(window)}"
            )

    if duration % slot:
        return (
            f"the required {duration} min is not a multiple of the {slot}-minute grid, so no "
            "block can align to it"
        )
    if duration > window.length:
        return (
            f"the required {duration} min exceeds the operating window {clock(window)} "
            f"({window.length} min)"
        )

    if rule.kind == "except":
        return (
            f"excluding {clock(rule.window)} leaves no room for a {duration}-min block inside "
            f"the operating window {clock(window)}"
        )

    if had_candidates:
        return (
            f"every {duration}-min block falls outside the hours demanded on this date "
            f"(demand covers {render_slots(demanded, slot)})"
        )
    return f"no {duration}-min block could be placed in the operating window {clock(window)}"


@dataclass(frozen=True)
class Diagnostic:
    """A worker-day whose cell asks for work that can never happen.

    Left alone, these are the quietest kind of bad data: the expansion turns the
    day into a day off, which changes that week's working-day target n_wk, and the
    file still validates.  The problem simply becomes a different problem than the
    author wrote.  Reporting them is the point.
    """

    employee: str
    date: str
    cell: str
    reason: str

    def __str__(self) -> str:
        return f"{self.employee} {self.date}: cell {self.cell!r} can never be satisfied -- {self.reason}"


def scan_feasibility(problem: dict, base: Path) -> list[Diagnostic]:
    """Every worker-day whose cell asks for work no assignment can provide.

    The single source of these diagnostics: the transformer reports them, and the
    validator errors on them, both by calling this -- so neither has to import the
    other and the two cannot disagree about what "impossible" means.

    A day is diagnosed only when it (a) is open, (b) is not already hard-off, and
    (c) asks for work that leaves H_wd empty.  A preferable day-off that turns out
    impossible is not diagnosed: it degrades to a plain day off, which is a
    legitimate outcome for a soft wish.
    """
    slot = problem["timeGrid"]["slotMinutes"]
    periods = period_ranges(problem)
    window = operating_window(periods, slot)
    meta = period_meta(problem, periods)
    t_d, _ = read_demand(problem, base, periods)
    cells, date_columns = read_schedule_input(problem, base)
    contracts = {c["id"]: c for c in problem["contracts"]["definitions"]}

    out: list[Diagnostic] = []
    for emp in problem["employees"]["list"]:
        emp_id = emp["id"]
        blackout = set(emp.get("restrictions", {}).get("blackoutDates", []))
        row = cells.get(emp_id, {})
        for iso_d in date_columns:
            demanded = t_d.get(iso_d, set())
            if not demanded:
                continue  # closed day, nothing is required
            day = date.fromisoformat(iso_d)
            weekday = WEEKDAY_NAMES[day.weekday()]
            try:
                rule = classify_cell(row.get(iso_d, ""), problem)
            except DomainError:
                # An unparseable cell (undeclared code, malformed window, hours-in-cell)
                # is a declaration error the validator's CSV layer reports precisely;
                # don't also raise a vaguer "cannot be interpreted" from here. The
                # transformer proper still raises on it in its own per-cell loop.
                continue
            contract_id = active_period(emp["contractAssignments"], day, "contractType")
            contract = contracts.get(contract_id) if contract_id else None

            # Hard-off days (matching the transformer's precedence) are never
            # diagnosed -- the worker simply isn't available, by design.
            if rule.kind == "dayoff" and rule.day_off == "unavailable":
                continue
            if contract_id is None or not active_teams(emp["teamAssignments"], day):
                continue
            if iso_d in blackout:
                continue

            if not day_allowed(contract, weekday):
                if rule.kind in EXPLICIT_WORK:
                    out.append(Diagnostic(
                        emp_id, iso_d, rule.code or "",
                        f"it names a shift on a {weekday}, which contract {contract_id!r} "
                        "does not permit",
                    ))
                continue

            eligible = build_day_candidates(rule, contract, window, slot, meta)
            kept = [c for c in eligible if slots_of(c.intervals, slot) <= demanded]
            if kept:
                continue
            # No option survives. A preferable day-off is allowed to end up empty.
            if rule.kind == "dayoff":
                continue
            if rule.kind in ASKS_FOR_WORK:
                why = diagnose(rule, contract, window, slot, demanded, bool(eligible))
                if why:
                    out.append(Diagnostic(emp_id, iso_d, rule.code or "", why))
    return out
