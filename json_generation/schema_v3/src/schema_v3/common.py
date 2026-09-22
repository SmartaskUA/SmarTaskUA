#!/usr/bin/env python3
"""Validation foundation: the Report, the lenient range parse, and the
cross-reference layer shared by the declarative and expanded forms.

Split out of validator.py so each validation concern lives in its own module and
the orchestrator (validator.py) just wires them together. This module imports
core (the shared domain) and nothing else in the package -- never transform.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta

import core  # sibling module in this package
from core import MINUTES_PER_DAY, iso


def parse_range(start: str, end: str) -> tuple[int, int] | None:
    """Lenient range parse for validating possibly-bad input; None if malformed."""
    return core.try_parse_range(start, end)


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
    """Cross-references the schema cannot express, shared by both problem forms.

    A mixin on SchemaValidator: it reads `self.problem`/`self.report` supplied by
    the composed class, so it is never instantiated on its own.
    """

    def horizon(self) -> list[date]:
        scope = self.problem.get("temporalScope", {})
        start, end = iso(scope.get("start", "")), iso(scope.get("end", ""))
        if not start or not end:
            return []
        return [start + timedelta(days=i) for i in range((end - start).days + 1)]

    def validate_common(self) -> None:
        p = self.problem
        r = self.report

        if p.get("schemaVersion") != "3.0":
            r.error(f"schemaVersion must be '3.0', got {p.get('schemaVersion')!r}")

        slot = p.get("timeGrid", {}).get("slotMinutes")
        if slot and MINUTES_PER_DAY % slot:
            r.error(f"timeGrid.slotMinutes {slot} does not divide {MINUTES_PER_DAY}")

        # A reversed horizon makes horizon() empty, which would silently skip every
        # date-dependent check below and "validate" a schedule of nothing.
        scope = p.get("temporalScope", {})
        s, e = iso(scope.get("start", "")), iso(scope.get("end", ""))
        if s and e and s > e:
            r.error(f"temporalScope.start ({scope['start']}) is after end ({scope['end']})")

        days = self.horizon()
        horizon = set(days)
        for item in p.get("calendar", {}).get("holidays", []):
            d = iso(item.get("date", ""))
            if not d:
                continue
            if horizon and d not in horizon:
                r.warn(f"calendar.holidays: {item['date']} is outside the target period")
            # The eve is the day before, so a holiday on the first day of the horizon
            # has its eve outside it and cannot carry eve demand.
            if item.get("hasEve") and horizon and (d - timedelta(days=1)) not in horizon:
                r.warn(
                    f"calendar.holidays: {item['date']} has hasEve, but its eve "
                    f"({d - timedelta(days=1)}) falls outside the target period"
                )

        # contracts
        contracts = p.get("contracts", {}).get("definitions", [])
        ids = [c["id"] for c in contracts]
        for dup in {i for i in ids if ids.count(i) > 1}:
            r.error(f"duplicate contract id {dup!r}")
        contract_ids = set(ids)

        competencies = {t["code"] for t in p.get("demand", {}).get("organizationalUnits", {}).get("competencies", [])}

        # employees
        emp_ids: list[str] = []
        levels_by_competency: dict[str, set[int]] = defaultdict(set)
        for emp in p.get("employees", {}).get("list", []):
            eid = emp.get("id", "?")
            emp_ids.append(eid)

            self._check_periods(emp.get("contractAssignments", []), eid, "contractAssignments")
            for a in emp.get("contractAssignments", []):
                if a.get("contractType") not in contract_ids:
                    r.error(
                        f"employee {eid}: contractAssignments references unknown contract "
                        f"{a.get('contractType')!r}"
                    )

            by_competency: dict[str, list[dict]] = defaultdict(list)
            for a in emp.get("competencyAssignments", []):
                if a.get("competency") not in competencies:
                    r.error(f"employee {eid}: competencyAssignments references unknown competency {a.get('competency')!r}")
                by_competency[a.get("competency")].append(a)
                if "level" not in a:
                    r.error(f"employee {eid}: competency {a.get('competency')!r} has no level "
                            "(every competency assignment must carry one)")
                else:
                    levels_by_competency[a["competency"]].add(a["level"])
            # Overlap is only wrong within one competency: holding two at once is normal.
            for competency, entries in by_competency.items():
                self._check_periods(entries, eid, f"competencyAssignments[{competency}]")

            # A worker with no contract on a working day cannot be scheduled; catching
            # gaps here is cheaper than discovering an infeasible model later.
            if days and not self._covers(emp.get("contractAssignments", []), days):
                r.warn(f"employee {eid}: contractAssignments do not cover the whole target period")

        for dup in {i for i in emp_ids if emp_ids.count(i) > 1}:
            r.error(f"duplicate employee id {dup!r}")

        self._check_priority_order(competencies, levels_by_competency)

        # v3.0 carries no solve directives: how to schedule (algorithm, objectives,
        # demand interpretation, rules) reached no solver and was cut. These blocks
        # take no additionalProperties guard at the root, so a leftover one would
        # validate clean and be silently ignored. Errors, naming the deferred
        # registry (FUTURE.md), so a carried-over file cannot quietly lose its rules.
        for block in ("optimization", "constraints"):
            if block in p:
                r.error(
                    f"{block!r} was removed in v3.0 and is ignored. Solve directives "
                    "(algorithm, objectives, demandInterpretation, rules such as min_rest) "
                    "reached no solver; they return as one explicit registry when a v3 "
                    "solver is built (see FUTURE.md). See MIGRATION-2.6-to-3.0.md."
                )

        r.stats["employees"] = len(emp_ids)
        r.stats["contracts"] = len(contract_ids)
        r.stats["competencies"] = len(competencies)
        r.stats["days"] = len(days)

    def _check_priority_order(self, competencies, levels_by_competency) -> None:
        """demand.priorityOrder: ordered, first-match-wins fill order."""
        r = self.report
        p = self.problem
        # priorityOrder is honoured by presence: entries here mean "fill in this
        # order", an empty/absent list means "no preference". No separate toggle.
        entries = p.get("demand", {}).get("priorityOrder", [])

        seen_order: dict[int, dict] = {}
        for e in entries:
            o = e.get("order")
            if o in seen_order:
                # Ordering is the whole meaning of this list; a tie makes
                # first-match-wins depend on array position, which is exactly what
                # `order` exists to avoid.
                r.error(f"demand.priorityOrder: duplicate order {o} "
                        f"({seen_order[o].get('competency')!r} and {e.get('competency')!r}); order must be unique")
            seen_order[o] = e
            if e.get("competency") not in competencies:
                r.error(f"demand.priorityOrder: unknown competency {e.get('competency')!r}")
            elif "level" in e:
                if e["level"] not in levels_by_competency.get(e["competency"], set()):
                    r.warn(f"demand.priorityOrder: no employee holds competency {e['competency']!r} at level "
                           f"{e['level']}; entry order {o} never matches anyone")

        # first match wins, so an earlier broader entry hides a later narrower one
        ordered = sorted((e for e in entries if isinstance(e.get("order"), int)),
                         key=lambda e: e["order"])
        for i, e in enumerate(ordered):
            for earlier in ordered[:i]:
                if earlier.get("competency") != e.get("competency"):
                    continue
                if earlier.get("level") is None or earlier.get("level") == e.get("level"):
                    what = (f"competency {e['competency']!r}" if e.get("level") is None
                            else f"competency {e['competency']!r} level {e['level']}")
                    r.warn(
                        f"demand.priorityOrder: entry order {e['order']} ({what}) is unreachable -- "
                        f"order {earlier['order']} already matches it, and the first match wins"
                    )
                    break

    def _check_periods(self, entries: list[dict], eid: str, label: str) -> None:
        spans = []
        for a in entries:
            start = iso(a.get("start", ""))
            if not start:
                continue
            end = iso(a["end"]) if a.get("end") else date.max
            if end < start:
                self.report.error(f"employee {eid}: {label} has end before start ({a})")
            spans.append((start, end))
        spans.sort()
        for (s1, e1), (s2, e2) in zip(spans, spans[1:]):
            if s2 <= e1:
                self.report.error(
                    f"employee {eid}: {label} periods overlap ({s1}..{e1} and {s2}..{e2})"
                )

    def _covers(self, entries: list[dict], days: list[date]) -> bool:
        spans = []
        for a in entries:
            start = iso(a.get("start", ""))
            if not start:
                return False
            end = iso(a["end"]) if a.get("end") else date.max
            spans.append((start, end))
        return all(any(s <= d <= e for s, e in spans) for d in days)
