"""Report, and the cross-reference checks every form shares.

Errors are accumulated as plain strings, never raised: one bad fact must not hide
the rest of the file. `DomainError` from `core` is caught at the boundary and
turned into a report line.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from . import core
from .core import iso


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    def error(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


class CommonChecksMixin:
    """Checks that apply to the problem form regardless of what else it carries.

    A mixin on `SchemaValidator`, reading ``self.problem`` and ``self.report``.
    Never instantiated alone.
    """

    problem: dict
    report: Report

    def horizon(self) -> list[date]:
        return core.horizon(self.problem)

    def validate_common(self) -> None:
        p, r = self.problem, self.report

        version = p.get("schemaVersion")
        if version != "4.0":
            if version == "3.0":
                r.error(
                    "schemaVersion is '3.0'. This is a v3.0 document, or a SISQUAL export - "
                    "their generator still stamps 3.0 on a payload that is neither v3.0 nor "
                    "v4.0. See docs/MIGRATION-3.0-to-4.0.md for the field-by-field conversion."
                )
            else:
                r.error(f"schemaVersion must be '4.0', found {version!r}")

        slot = p.get("timeGrid", {}).get("slotMinutes")
        if isinstance(slot, int) and slot > 0 and core.MINUTES_PER_DAY % slot:
            r.error(f"timeGrid.slotMinutes {slot} does not divide 1440")

        days = self.horizon()
        scope = p.get("temporalScope", {})
        if not days:
            r.error(f"temporalScope {scope.get('start')}..{scope.get('end')} is empty or reversed")
        r.stats["days"] = len(days)

        week_start = p.get("calendar", {}).get("weekStart", "monday")
        if week_start not in core.WEEKDAY_NAMES:
            r.error(f"calendar.weekStart {week_start!r} is not one of {', '.join(core.WEEKDAY_NAMES)}")

        self._check_holidays(days)
        self._check_contracts()
        self._check_employees(days)
        self._check_dimensions()

    # -- holidays ----------------------------------------------------------

    def _check_holidays(self, days: list[date]) -> None:
        r = self.report
        span = set(days)
        seen: set[str] = set()
        for h in self.problem.get("calendar", {}).get("holidays", []):
            raw = h.get("date", "")
            day = iso(raw)
            if not day:
                r.error(f"calendar.holidays: {raw!r} is not a date")
                continue
            if raw in seen:
                r.error(f"calendar.holidays: {raw} appears twice")
            seen.add(raw)
            if day not in span:
                r.warn(f"calendar.holidays: {raw} lies outside temporalScope")
            if h.get("hasEve"):
                if day - timedelta(days=1) not in span:
                    r.warn(f"calendar.holidays: {raw} has hasEve, but its eve lies outside temporalScope")

    # -- contracts ---------------------------------------------------------

    def _check_contracts(self) -> None:
        r = self.report
        defs = self.problem.get("contracts", {}).get("definitions", [])
        seen: set[str] = set()
        slot = self.problem.get("timeGrid", {}).get("slotMinutes", 30)
        for c in defs:
            cid = c.get("id")
            if cid in seen:
                r.error(f"contracts.definitions: duplicate id {cid!r}")
            seen.add(cid)
            minutes = c.get("workMinutesPerDay")
            if isinstance(minutes, int) and isinstance(slot, int) and slot > 0:
                if not core.on_grid(minutes, slot):
                    r.error(f"contract {cid}: workMinutesPerDay {minutes} is not a multiple "
                            f"of the {slot}-minute grid")
        r.stats["contracts"] = len(defs)
        if not defs:
            r.warn("contracts.definitions is empty")

    # -- employees ---------------------------------------------------------

    def _check_employees(self, days: list[date]) -> None:
        r = self.report
        known = set(core.contracts_by_id(self.problem))
        declared = core.dimension_set(self.problem)
        employees = self.problem.get("employees", {}).get("list", [])
        seen: set[str] = set()

        for e in employees:
            eid = e.get("id", "?")
            if eid in seen:
                r.error(f"employees.list: duplicate id {eid!r}")
            seen.add(eid)

            contracts = e.get("contractAssignments", [])
            for a in contracts:
                ct = a.get("contractType")
                if ct not in known:
                    r.error(f"employee {eid}: contractAssignments references unknown contract {ct!r}")
            self._check_overlaps(contracts, f"employee {eid}: contractAssignments")
            if days and not self._covers_all(contracts, days):
                r.warn(f"employee {eid}: contract coverage has a gap inside temporalScope")

            comps = e.get("competencyAssignments", [])
            by_pair: dict[tuple[str, str], list[dict]] = {}
            for a in comps:
                pair = (a.get("tableName"), a.get("tableValue"))
                if declared and pair not in declared:
                    r.error(f"employee {eid}: competency {pair[0]}/{pair[1]} is not in demand.dimensions")
                by_pair.setdefault(pair, []).append(a)
            # Holding two different competencies at once is normal. Holding the
            # same one twice over the same dates leaves l_ws undefined - but
            # SISQUAL emits exactly that for some employees, so it is a warning
            # naming the levels rather than an error: the fact is ambiguous, not
            # impossible, and a consumer can resolve it by taking the highest
            # competence (the LOWEST number). See next_meeting.md item 18 ("the same competency twice").
            for pair, entries in by_pair.items():
                self._check_competency_overlaps(entries, eid, pair)
            if not comps:
                r.warn(f"employee {eid}: holds no competencies, so no demand row can be covered by them")

        r.stats["employees"] = len(employees)

    def _check_competency_overlaps(self, entries: list[dict], eid: str,
                                   pair: tuple) -> None:
        spans = []
        for a in entries:
            start = iso(a.get("start", ""))
            end = iso(a["end"]) if a.get("end") else date.max
            if start:
                spans.append((start, end, a.get("level")))
        for (s1, e1, l1), (s2, e2, l2) in _overlapping_pairs(spans):
            if l1 == l2:
                detail = f"the same level {l1} twice"
            else:
                detail = (f"levels {l1} and {l2} at once, so its competence level is "
                          f"ambiguous; take {min(l1, l2)}, the higher competence")
            self.report.warn(
                f"employee {eid}: holds {pair[0]}/{pair[1]} over overlapping dates "
                f"({s1}..{e1} and {s2}..{e2}) with {detail}")

    def _check_overlaps(self, entries: list[dict], label: str) -> None:
        spans = []
        for a in entries:
            start = iso(a.get("start", ""))
            end = iso(a["end"]) if a.get("end") else date.max
            if start:
                spans.append((start, end))
        for a, b in _overlapping_pairs(spans):
            self.report.error(f"{label}: {a[0]}..{a[1]} overlaps {b[0]}..{b[1]}")

    @staticmethod
    def _covers_all(entries: list[dict], days: list[date]) -> bool:
        return all(any(core.covers(a, d) for a in entries) for d in days)

    # -- dimensions --------------------------------------------------------

    def _check_dimensions(self) -> None:
        r = self.report
        dims = self.problem.get("demand", {}).get("dimensions", [])
        seen: set[tuple[str, str]] = set()
        for d in dims:
            pair = (d.get("tableName"), d.get("tableValue"))
            if pair in seen:
                r.error(f"demand.dimensions: duplicate coordinate {pair[0]}/{pair[1]}")
            seen.add(pair)
        r.stats["dimensions"] = len(dims)
        if not dims:
            r.error(
                "demand.dimensions is empty. It is the only declaration of which "
                "(tableName, tableValue) coordinates exist, so without it nothing can be "
                "cross-checked - see docs/FORMAT.md."
            )


def report_grouped(emit, items: list[tuple[str, str]], keep: int = 3) -> None:
    """Emit findings, collapsing repeats of one cause.

    A contract whose length does not fit the grid produces one finding per
    worker-day - 360 identical lines for a 12-employee month, which buries
    everything else. Grouping by cause keeps the first few and counts the rest,
    so the report stays the size of the problem rather than the size of the data.
    """
    groups: dict[str, list[str]] = {}
    for cause, message in items:
        groups.setdefault(cause, []).append(message)
    for cause, messages in groups.items():
        for message in messages[:keep]:
            emit(message)
        if len(messages) > keep:
            emit(f"... and {len(messages) - keep} more with the same cause "
                 f"({len(messages)} in total)")


def _overlapping_pairs(spans, closed: bool = True):
    """Every pair of spans that overlap, not merely the adjacent ones.

    The obvious `zip(spans, spans[1:])` after sorting compares neighbours only, so
    one long span swallowing several later ones reports the first and misses the
    rest. Spans are tuples whose first two elements are (start, end); anything after
    that is carried through untouched.

    `closed` says whether the endpoint belongs to the span. Date ranges are closed,
    so 01-05..01-10 and 01-10..01-15 share the 10th and do overlap. Time windows are
    half-open, so 20:00-21:00 and 21:00-22:00 merely touch and do not.
    """
    ordered = sorted(spans)
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if (b[0] > a[1]) if closed else (b[0] >= a[1]):
                break          # sorted by start, so nothing later can overlap either
            yield a, b
