#!/usr/bin/env python3
"""Validate a v3.0 scheduling problem (declarative or expanded) or solution.

Runs three layers:
  1. JSON Schema, against the form named by the instance's `form` field.
  2. Cross-references the schema cannot express (ids resolving, date ranges not
     overlapping, invariants between sibling fields).
  3. Conformance with MathematicalDefinition7, for expanded problems -- the rules
     that make the difference between a file that parses and a model that means
     what it says.

Usage:
    python3 validator.py problem.json
    python3 validator.py problem.json -v
    python3 validator.py problem.json --json
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

import core  # sibling module in this package
from core import (
    ALWAYS_UNAVAILABLE,
    MINUTES_PER_DAY,
    DomainError,
    active_period,
    iso,
    week_index,
)

# The domain (time maths, cell semantics, candidate generation) lives in core,
# shared with the transformer. This file adds only policy: which findings are
# errors, which are warnings, and how the JSON Schema layer runs.

SCHEMA_FILES = {
    "declarative": "schema-v3-declarative.json",
    "expanded": "schema-v3-expanded.json",
    "solution": "schema-v3-solution.json",
}


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


class SchemaValidator:
    def __init__(self, path: Path):
        self.path = path
        self.base = path.parent
        self.report = Report()
        self.problem: dict = {}

    # -- layer 1 ---------------------------------------------------------
    def load(self) -> bool:
        try:
            self.problem = json.loads(self.path.read_text())
        except FileNotFoundError:
            self.report.error(f"file not found: {self.path}")
            return False
        except json.JSONDecodeError as exc:
            self.report.error(f"invalid JSON: {exc}")
            return False
        return True

    def validate_schema(self) -> None:
        try:
            from jsonschema import Draft202012Validator
        except ImportError:
            self.report.warn("jsonschema not installed; skipped schema layer")
            return

        form = self.problem.get("form")
        if form not in SCHEMA_FILES:
            self.report.error(
                f"form must be one of {sorted(SCHEMA_FILES)}, got {form!r}"
            )
            return

        # this file: <root>/src/schema_v3/validator.py -> schemas at <root>/schemas
        schema_dir = Path(__file__).resolve().parents[2] / "schemas"
        try:
            # Each form schema is standalone, so it loads and validates on its own --
            # no registry, and no resolution order to get wrong.
            schema = json.loads((schema_dir / SCHEMA_FILES[form]).read_text())
        except FileNotFoundError as exc:
            self.report.warn(f"schema file not found ({exc}); skipped schema layer")
            return

        validator = Draft202012Validator(schema)
        for err in sorted(validator.iter_errors(self.problem), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.path) or "(root)"
            self.report.error(f"schema: {where}: {err.message}")

    # -- layer 2 ---------------------------------------------------------
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

        teams = {t["code"] for t in p.get("demand", {}).get("organizationalUnits", {}).get("teams", [])}

        # employees
        model = p.get("employees", {}).get("model")
        emp_ids: list[str] = []
        levels_by_team: dict[str, set[int]] = defaultdict(set)
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

            by_team: dict[str, list[dict]] = defaultdict(list)
            for a in emp.get("teamAssignments", []):
                if a.get("team") not in teams:
                    r.error(f"employee {eid}: teamAssignments references unknown team {a.get('team')!r}")
                by_team[a.get("team")].append(a)
                if model == "competency":
                    if "level" not in a:
                        r.error(f"employee {eid}: team {a.get('team')!r} has no level "
                                "(required for the competency model)")
                    else:
                        levels_by_team[a["team"]].add(a["level"])
            # Overlap is only wrong within one team: holding two teams at once is normal.
            for team, entries in by_team.items():
                self._check_periods(entries, eid, f"teamAssignments[{team}]")

            # A worker with no contract on a working day cannot be scheduled; catching
            # gaps here is cheaper than discovering an infeasible model later.
            if days and not self._covers(emp.get("contractAssignments", []), days):
                r.warn(f"employee {eid}: contractAssignments do not cover the whole target period")

        for dup in {i for i in emp_ids if emp_ids.count(i) > 1}:
            r.error(f"duplicate employee id {dup!r}")

        self._check_priority_order(teams, levels_by_team, model)

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
        r.stats["teams"] = len(teams)
        r.stats["days"] = len(days)
        r.stats["model"] = model

    def _check_priority_order(self, teams, levels_by_team, model) -> None:
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
                        f"({seen_order[o].get('team')!r} and {e.get('team')!r}); order must be unique")
            seen_order[o] = e
            if e.get("team") not in teams:
                r.error(f"demand.priorityOrder: unknown team {e.get('team')!r}")
            elif model == "competency" and "level" in e:
                if e["level"] not in levels_by_team.get(e["team"], set()):
                    r.warn(f"demand.priorityOrder: no employee holds team {e['team']!r} at level "
                           f"{e['level']}; entry order {o} never matches anyone")

        # first match wins, so an earlier broader entry hides a later narrower one
        ordered = sorted((e for e in entries if isinstance(e.get("order"), int)),
                         key=lambda e: e["order"])
        for i, e in enumerate(ordered):
            for earlier in ordered[:i]:
                if earlier.get("team") != e.get("team"):
                    continue
                if earlier.get("level") is None or earlier.get("level") == e.get("level"):
                    what = (f"team {e['team']!r}" if e.get("level") is None
                            else f"team {e['team']!r} level {e['level']}")
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

    # -- declarative CSVs -------------------------------------------------
    def validate_declarative(self) -> None:
        p = self.problem
        r = self.report
        slot = p.get("timeGrid", {}).get("slotMinutes", 15)

        periods = {}
        for wp in p.get("demand", {}).get("workPeriods", []):
            tr = wp.get("timeRange")
            if tr:
                rng = parse_range(tr["start"], tr["end"])
                if rng is None:
                    r.error(f"work period {wp['code']!r}: malformed timeRange")
                    continue
                for bound in rng:
                    if bound % slot:
                        r.error(
                            f"work period {wp['code']!r}: boundary {bound} min is not on the "
                            f"{slot}-minute grid"
                        )
                periods[wp["code"]] = rng
            else:
                periods[wp["code"]] = None

        teams = {t["code"] for t in p["demand"]["organizationalUnits"]["teams"]}
        horizon = set(self.horizon())

        window = None
        spans = [v for v in periods.values() if v]
        if spans:
            window = (min(a for a, _ in spans), max(b for _, b in spans))
            r.stats["operatingWindow"] = f"{window[0]}-{window[1]} min ({window[1] - window[0]})"

        for c in p.get("contracts", {}).get("definitions", []):
            mins = c.get("workMinutesPerDay")
            if not isinstance(mins, int):
                continue
            if mins % slot:
                r.error(
                    f"contract {c['id']!r}: workMinutesPerDay {mins} is not a multiple of the "
                    f"{slot}-minute grid, so no assignment block can ever align to it"
                )
            if window and mins > window[1] - window[0]:
                r.error(
                    f"contract {c['id']!r}: workMinutesPerDay {mins} exceeds the operating window "
                    f"({window[1] - window[0]} min), so no assignment block can ever fit"
                )

        self._check_day_off_codes()
        open_days = self._validate_demand_csv(periods, teams, horizon, slot)
        cells, date_cols = self._validate_schedule_csv(horizon, slot)
        self._check_structural(open_days, cells, date_cols)
        self._check_reachability(open_days, cells, teams)
        self._feasibility_preflight()

    def _check_day_off_codes(self) -> None:
        """Tier 3: VAC/NOT are unavailable by definition.

        Disjointness and declared-vs-classified are no longer possible to get wrong:
        dayOffCodes is one map keyed by code, so a code has exactly one kind and is
        declared by being present. The schema enforces the shape; only the VAC/NOT
        semantic needs a content check.
        """
        r = self.report
        section = self.problem.get("scheduleInput", {})
        codes = section.get("dayOffCodes", {})
        for code in sorted(ALWAYS_UNAVAILABLE & set(codes)):
            if codes[code].get("kind") != "unavailable":
                r.error(
                    f"scheduleInput.dayOffCodes: {code!r} is unavailable by definition and "
                    f"cannot be kind {codes[code].get('kind')!r}"
                )

    def _check_structural(self, open_days: set[str], cells: dict, date_cols: list[str]) -> None:
        """Tier 2: per-week working-day counts that the model cannot satisfy."""
        p = self.problem
        r = self.report
        days = self.horizon()
        if not days or not open_days:
            return
        origin = days[0]
        week_start = p.get("calendar", {}).get("weekStart", "monday")
        contracts = {c["id"]: c for c in p.get("contracts", {}).get("definitions", [])}

        preferable, unavailable = core.day_off_sets(p.get("scheduleInput", {}))

        # D-bar: days starting a run of six consecutive calendar days that are ALL open.
        # The 5-in-6 rule only ranges over these, so a week whose open days are broken
        # up by a closure is never caught by it -- which is why this cannot be judged
        # from per-week counts alone.
        d_bar = [
            d for d in days
            if all((d + timedelta(days=i)).isoformat() in open_days for i in range(6))
        ]

        for emp in p.get("employees", {}).get("list", []):
            eid = emp["id"]
            row = cells.get(eid, {})
            weeks: dict[int, dict] = defaultdict(
                lambda: {"open": 0, "U": 0, "D": 0, "first": None, "days": set()}
            )
            for iso_d in date_cols:
                if iso_d not in open_days:
                    continue
                dd = iso(iso_d)
                if not dd:
                    continue
                w = weeks[week_index(dd, origin, week_start)]
                w["open"] += 1
                w["first"] = w["first"] or dd
                w["days"].add(iso_d)
                cell = (row.get(iso_d) or "").strip()
                if cell in unavailable:
                    w["U"] += 1
                elif cell in preferable:
                    w["D"] += 1

            must_work: set[str] = set()
            for k, w in sorted(weeks.items()):
                n_wk = w["open"] - w["U"] - w["D"]
                if n_wk < 0:
                    r.error(f"{eid} week {k}: derived n_wk is {n_wk}")
                    continue

                cid = active_period(emp.get("contractAssignments", []), w["first"], "contractType")
                contract = contracts.get(cid, {})
                cons = contract.get("constraints", {})

                if n_wk == w["open"]:
                    # Constraint (6) forces exactly n_wk working days, so with no days
                    # off marked every open day of this week is compulsory.
                    must_work |= w["days"]
                elif n_wk == 6 and w["open"] == 7:
                    # Only genuinely tight at seven open days: the week then contains two
                    # six-day runs, and the single rest day has to break both, so it must
                    # land mid-week. At six open days, 5-of-6 always yields exactly 5 in
                    # the one run and placement cannot fail -- warning there is noise.
                    r.warn(
                        f"{eid} week {k}: n_wk=6 of 7 open days is tight -- satisfiable only if "
                        "the single rest day falls mid-week, and runs spanning the adjacent weeks "
                        "may still break the 5-in-6 rule"
                    )

                if n_wk == w["open"] and cons.get("maxConsecutiveDays", 99) < w["open"]:
                    r.error(
                        f"{eid} week {k}: must work all {w['open']} open days, but contract "
                        f"{cid!r} caps consecutive days at {cons['maxConsecutiveDays']}"
                    )
                mx = cons.get("maxMinutesPerWeek")
                per_day = contract.get("workMinutesPerDay")
                if mx and per_day and n_wk * per_day > mx:
                    r.error(
                        f"{eid} week {k}: n_wk={n_wk} x {per_day} min = {n_wk * per_day} min "
                        f"exceeds contract {cid!r} maxMinutesPerWeek {mx}"
                    )
                rest = cons.get("minRestDaysPerWeek")
                if rest and n_wk > 7 - rest:
                    r.error(
                        f"{eid} week {k}: n_wk={n_wk} leaves fewer than the "
                        f"{rest} rest days contract {cid!r} requires"
                    )

            # Provably unsatisfiable: six consecutive open days every one of which the
            # worker is compelled to work.
            for d0 in d_bar:
                run = [(d0 + timedelta(days=i)).isoformat() for i in range(6)]
                if all(x in must_work for x in run):
                    r.error(
                        f"{eid}: compelled to work all six consecutive open days "
                        f"{run[0]}..{run[-1]} (those weeks mark no days off), but at most 5 of any "
                        "6 consecutive open days may be worked"
                    )
                    break

    def _check_reachability(self, open_days: set[str], cells: dict, teams: set) -> None:
        """Tier 4: coverage that cannot be met, and configuration that does nothing."""
        p = self.problem
        r = self.report
        section = p.get("scheduleInput", {})

        declared = set(section.get("dayOffCodes", {}))
        used = {c.strip() for row in cells.values() for c in row.values() if c and c.strip()}
        for code in sorted(declared - used):
            r.warn(f"scheduleInput.dayOffCodes: {code!r} is declared but never used")

        held: dict[str, list] = defaultdict(list)
        for emp in p.get("employees", {}).get("list", []):
            for ta in emp.get("teamAssignments", []):
                held[ta.get("team")].append(ta)
        for team in sorted(teams - set(held)):
            r.warn(f"team {team!r} is defined but no employee holds it; its demand can never be met")
        for team in sorted(set(held) - teams):
            r.warn(f"team {team!r} is held by employees but never appears in demand")

        # minimum vs the number of people who could possibly serve that team that day
        data_file = p.get("demand", {}).get("dataFile")
        if not data_file:
            return
        path = self.base / data_file
        if not path.exists():
            return
        flagged = set()
        with path.open(newline="") as fh:
            rows_iter = list(csv.DictReader(core.csv_lines(fh)))
        for row in rows_iter:
            d = iso(row.get("date", ""))
            team = row.get("team")
            if not d or team not in held:
                continue
            try:
                minimum = float(row.get("minimum", 0))
            except ValueError:
                continue
            if minimum <= 0:
                continue
            headcount = sum(
                1 for ta in held[team]
                if iso(ta["start"]) and iso(ta["start"]) <= d
                and (ta.get("end") is None or (iso(ta["end"]) and d <= iso(ta["end"])))
            )
            if minimum > headcount and (team, headcount) not in flagged:
                flagged.add((team, headcount))
                r.warn(
                    f"demand for team {team!r} asks for {minimum:g} on {row['date']} but only "
                    f"{headcount} employee(s) hold that team then; a shortfall is guaranteed"
                )

    def _feasibility_preflight(self) -> None:
        """Tier 1: every cell that asks for work no assignment can provide is an error.

        Calls core.scan_feasibility -- the same function the transformer reports
        from -- so the validator and transformer cannot disagree about what is
        impossible, and neither has to import the other.
        """
        r = self.report
        try:
            diagnostics = core.scan_feasibility(self.problem, self.base)
        except DomainError as exc:
            r.error(f"the problem cannot be interpreted: {exc}")
            return
        except Exception as exc:  # noqa: BLE001 - never let a preflight crash mask real errors
            r.warn(f"feasibility layer failed unexpectedly ({exc}); skipped")
            return

        for d in diagnostics:
            r.error(str(d))

    def _validate_demand_csv(self, periods, teams, horizon, slot) -> set[str]:
        r = self.report
        open_days: set[str] = set()
        data_file = self.problem["demand"].get("dataFile")
        if not data_file:
            r.error("demand.dataFile is required")
            return open_days
        path = self.base / data_file
        if not path.exists():
            r.error(f"demand file not found: {path}")
            return open_days

        required = ["date", "workPeriod", "team", "minimum", "empiric", "maximum"]
        seen = set()
        rows = 0
        with path.open(newline="") as fh:
            reader = csv.DictReader(core.csv_lines(fh))
            fields = reader.fieldnames or []
            if "ideal" in fields or "estimated" in fields:
                # An unmigrated v2.6 file. Renaming the header alone is NOT the
                # migration: v2.6's rule was minimum <= estimated <= ideal, so `ideal`
                # was the UPPER bound in the MIDDLE column. The two right-hand columns
                # exchange values.
                r.error(
                    f"{path.name}: this is a v2.6 header ({','.join(fields)}). v3.0 expects "
                    "'minimum,empiric,maximum'. Do NOT just rename: v2.6's rule was "
                    "minimum <= estimated <= ideal, so `ideal` was the UPPER bound sitting in the "
                    "MIDDLE column -- empiric <- estimated and maximum <- ideal, i.e. the last two "
                    "columns swap VALUES. See MIGRATION-2.6-to-3.0.md section 1."
                )
                return open_days
            missing = [c for c in required if c not in fields]
            if missing:
                r.error(f"{path.name}: missing columns {missing}. See MIGRATION-2.6-to-3.0.md.")
                return open_days
            for lineno, row in enumerate(reader, start=2):
                if not row.get("date"):
                    continue
                rows += 1
                open_days.add(row["date"])
                d = iso(row["date"])
                if not d:
                    r.error(f"{path.name}:{lineno}: invalid date {row['date']!r}")
                elif horizon and d not in horizon:
                    r.error(f"{path.name}:{lineno}: date {row['date']} is outside the target period")
                if row["workPeriod"] not in periods:
                    r.error(f"{path.name}:{lineno}: unknown workPeriod {row['workPeriod']!r}")
                if row["team"] not in teams:
                    r.error(f"{path.name}:{lineno}: unknown team {row['team']!r}")

                key = (row["date"], row["workPeriod"], row["team"])
                if key in seen:
                    r.error(f"{path.name}:{lineno}: duplicate row for {key}")
                seen.add(key)

                bounds = {}
                for col in ("minimum", "empiric", "maximum"):
                    try:
                        val = float(row[col])
                    except (TypeError, ValueError):
                        r.error(f"{path.name}:{lineno}: {col} is not numeric ({row[col]!r})")
                        continue
                    if val < 0:
                        r.error(f"{path.name}:{lineno}: {col} is negative")
                    bounds[col] = val

                # 0 means "unset", so the ordering only binds the bounds actually given.
                given = {k: v for k, v in bounds.items() if v != 0}
                lo, mid, hi = given.get("minimum"), given.get("empiric"), given.get("maximum")
                if lo is not None and mid is not None and lo > mid:
                    r.error(f"{path.name}:{lineno}: minimum ({lo}) > empiric ({mid})")
                if mid is not None and hi is not None and mid > hi:
                    r.error(f"{path.name}:{lineno}: empiric ({mid}) > maximum ({hi})")
                if lo is not None and hi is not None and lo > hi:
                    r.error(f"{path.name}:{lineno}: minimum ({lo}) > maximum ({hi})")

                start, end = row.get("start") or "", row.get("end") or ""
                if bool(start) != bool(end):
                    r.error(f"{path.name}:{lineno}: start and end must both be given or both omitted")
                elif start:
                    rng = parse_range(start, end)
                    if rng is None:
                        r.error(f"{path.name}:{lineno}: malformed start/end")
                    else:
                        for bound in rng:
                            if bound % slot:
                                r.error(
                                    f"{path.name}:{lineno}: override boundary {bound} min is not "
                                    f"on the {slot}-minute grid"
                                )
        r.stats["demandRows"] = rows
        r.stats["openDays"] = len(open_days)
        return open_days

    def _validate_schedule_csv(self, horizon, slot) -> tuple[dict, list[str]]:
        r = self.report
        cells: dict[str, dict[str, str]] = {}
        section = self.problem.get("scheduleInput", {})
        path = self.base / section.get("dataFile", "")
        if not path.exists():
            r.error(f"schedule input file not found: {path}")
            return cells, []

        # One set now: every custom code must appear in dayOffCodes, which both
        # declares and classifies it.
        declared = set(section.get("dayOffCodes", {}))
        emp_ids = {e["id"] for e in self.problem.get("employees", {}).get("list", [])}

        with path.open(newline="") as fh:
            reader = csv.reader(core.csv_lines(fh))
            header = next(reader, [])
            if not header or header[0] != "employee_id":
                r.error(f"{path.name}: first column must be 'employee_id'")
                return cells, []
            dates = [h.strip() for h in header[1:]]
            for d in dates:
                if not iso(d):
                    r.error(f"{path.name}: column header {d!r} is not a date")
            span = len(self.horizon())
            if span and len(dates) != span:
                r.error(f"{path.name}: {len(dates)} date columns but temporalScope spans {span} days "
                        f"({self.problem['temporalScope'].get('start')}..{self.problem['temporalScope'].get('end')})")

            seen_ids = set()
            for row in reader:
                if not row or not row[0].strip():
                    continue
                eid = row[0].strip()
                if eid in seen_ids:
                    r.error(f"{path.name}: duplicate employee_id {eid!r}")
                seen_ids.add(eid)
                cells[eid] = {
                    d: (row[i + 1].strip() if i + 1 < len(row) else "")
                    for i, d in enumerate(dates)
                }
                for i, cell in enumerate(row[1:]):
                    self._check_cell(cell.strip(), eid, dates[i] if i < len(dates) else "?",
                                     declared, path.name, slot)

            for missing in emp_ids - seen_ids:
                r.error(f"{path.name}: employee {missing!r} has no row")
            for extra in seen_ids - emp_ids:
                r.error(f"{path.name}: row for {extra!r}, which is not in employees.list")

        return cells, dates

    def _check_cell(self, cell, eid, day, declared, fname, slot) -> None:
        r = self.report
        if not cell:
            return
        upper = cell.upper()
        for op in ("EQUALS", "INCLUDE", "EXCEPT"):
            if upper.startswith(op + ":"):
                body = cell.split(":", 1)[1]
                if "-" not in body or parse_range(*body.split("-", 1)) is None:
                    r.error(f"{fname}: {eid} {day}: malformed {op} constraint {cell!r}")
                return
        if upper == "A":
            return
        if cell.isdigit():
            value = int(cell)
            # v2.6 wrote whole hours in these cells. v3 is minutes, so an unmigrated
            # file would turn an 8-hour day into 8 minutes and still validate. No real
            # assignment is under 25 minutes, so this range is a migration miss.
            if 1 <= value <= 24:
                r.error(
                    f"{fname}: {eid} {day}: numeric cells are MINUTES in v3.0 and {value} looks "
                    f"like a v2.6 hours value; write {value * 60}. See MIGRATION-2.6-to-3.0.md."
                )
            elif value % slot:
                r.error(
                    f"{fname}: {eid} {day}: {value} min is not a multiple of the {slot}-minute "
                    "grid, so no assignment block can align to it"
                )
            return
        if cell not in declared:
            # Every custom code, VAC/NOT included, must be declared in dayOffCodes.
            r.error(
                f"{fname}: {eid} {day}: undeclared code {cell!r}; add it to "
                "scheduleInput.dayOffCodes with kind 'preferable' or 'unavailable'"
            )

    # -- layer 3: expanded / V7 conformance -------------------------------
    def validate_expanded(self) -> None:
        p = self.problem
        r = self.report
        slot = p["timeGrid"]["slotMinutes"]

        catalog = {}
        for a in p.get("assignmentCatalog", []):
            catalog[a["id"]] = a
            covered = set()
            prev_end = None
            for iv in a["intervals"]:
                lo, hi = iv["startMin"], iv["endMin"]
                if hi <= lo:
                    r.error(f"assignment {a['id']}: endMin {hi} is not after startMin {lo}")
                if prev_end is not None and lo < prev_end:
                    r.error(
                        f"assignment {a['id']}: intervals are not in ascending order "
                        f"({lo} starts before the previous interval ended at {prev_end})"
                    )
                prev_end = hi
                for bound in (lo, hi):
                    if bound % slot:
                        r.error(
                            f"assignment {a['id']}: boundary {bound} min is not on the "
                            f"{slot}-minute grid"
                        )
                slots = set(range(lo // slot, hi // slot))
                if slots & covered:
                    r.error(f"assignment {a['id']}: intervals overlap each other")
                covered |= slots

        t_d = self._demand_slots(slot)
        open_days = {d for d, s in t_d.items() if s}
        week_start = p.get("calendar", {}).get("weekStart", "monday")
        days = self.horizon()
        origin = days[0] if days else None

        n_wk: dict[tuple[str, int], dict[str, int]] = defaultdict(
            lambda: {"open": 0, "unavailable": 0, "preferable": 0}
        )
        for d in open_days:
            dd = iso(d)
            if not dd or not origin:
                continue
            k = week_index(dd, origin, week_start)
            for emp in p.get("employees", {}).get("list", []):
                n_wk[(emp["id"], k)]["open"] += 1

        for entry in p.get("availability", []):
            eid = entry["employeeId"]
            for day in entry["days"]:
                iso_d = day["date"]
                ids = day.get("assignmentIds", [])
                day_off = day.get("dayOff")

                for aid in ids:
                    if aid not in catalog:
                        r.error(f"{eid} {iso_d}: assignmentId {aid!r} is not in assignmentCatalog")

                if day_off == "unavailable" and ids:
                    r.error(
                        f"{eid} {iso_d}: dayOff is 'unavailable' but {len(ids)} assignments are "
                        "offered; V7 constraint (5) forbids any assignment on an unavailable day"
                    )
                if day_off == "preferable" and not ids:
                    r.error(
                        f"{eid} {iso_d}: dayOff is 'preferable' but no assignments are offered. "
                        "A preferable day off is soft -- it may be worked at a penalty [x'_wd] -- "
                        "so with no options it is really 'unavailable'."
                    )
                if day.get("forced") and day["forced"] not in ids:
                    r.error(f"{eid} {iso_d}: forced assignment {day['forced']!r} is not in assignmentIds")

                if iso_d in open_days and not ids and day_off != "unavailable":
                    r.error(
                        f"{eid} {iso_d}: open day with no assignments and no 'unavailable' marker. "
                        "n_wk would count this day as workable while H_wd offers nothing, making "
                        "V7 constraint (6) unsatisfiable."
                    )

                # H_wd must not reach outside the demanded window (V7, H_wd definition).
                demanded = t_d.get(iso_d, set())
                for aid in ids:
                    a = catalog.get(aid)
                    if not a:
                        continue
                    covered = set()
                    for iv in a["intervals"]:
                        covered |= set(range(iv["startMin"] // slot, iv["endMin"] // slot))
                    if not covered <= demanded:
                        r.error(
                            f"{eid} {iso_d}: assignment {aid} covers timeslots outside T_d; V7 "
                            "requires H_wd to exclude such assignments entirely"
                        )

                if iso_d in open_days and origin:
                    dd = iso(iso_d)
                    if dd:
                        k = week_index(dd, origin, week_start)
                        if day_off == "unavailable":
                            n_wk[(eid, k)]["unavailable"] += 1
                        elif day_off == "preferable":
                            n_wk[(eid, k)]["preferable"] += 1

        negative = 0
        for (eid, k), c in sorted(n_wk.items()):
            value = c["open"] - c["unavailable"] - c["preferable"]
            if value < 0:
                negative += 1
                r.error(
                    f"{eid} week {k}: derived n_wk is {value} (open {c['open']} - unavailable "
                    f"{c['unavailable']} - preferable {c['preferable']}); V7 constraint (6) "
                    "requires a non-negative working-day count"
                )

        referenced = {
            aid for entry in p.get("availability", [])
            for day in entry["days"] for aid in day.get("assignmentIds", [])
        }
        for dead in sorted(set(catalog) - referenced):
            r.warn(f"assignmentCatalog: {dead!r} is referenced by no worker-day")

        sizes = [len(d.get("assignmentIds", [])) for e in p.get("availability", [])
                 for d in e["days"] if d.get("assignmentIds")]
        r.stats["assignmentCatalog"] = len(catalog)
        r.stats["openDays"] = len(open_days)
        r.stats["weeks"] = len({k for _, k in n_wk})
        r.stats["negative_n_wk"] = negative
        r.stats["hwdMax"] = max(sizes) if sizes else 0
        r.stats["hwdMean"] = round(sum(sizes) / len(sizes), 1) if sizes else 0

    def _demand_slots(self, slot: int) -> dict[str, set[int]]:
        """T_d per date: the timeslots demanded on each day.

        Each demand row names a work period; the row's own start/end override it
        when present, otherwise the period's declared range applies.  A date with
        no rows is closed and lies outside D_o.
        """
        out: dict[str, set[int]] = defaultdict(set)
        demand = self.problem.get("demand", {})
        data_file = demand.get("dataFile")
        if not data_file:
            return out
        path = self.base / data_file
        if not path.exists():
            self.report.warn(f"demand file {path} not found; skipped the H_wd-within-T_d check")
            return out

        periods: dict[str, tuple[int, int]] = {}
        for wp in demand.get("workPeriods", []):
            tr = wp.get("timeRange")
            if tr:
                rng = parse_range(tr["start"], tr["end"])
                if rng:
                    periods[wp["code"]] = rng

        with path.open(newline="") as fh:
            for row in csv.DictReader(core.csv_lines(fh)):
                if not row.get("date"):
                    continue
                if row.get("start") and row.get("end"):
                    rng = parse_range(row["start"], row["end"])
                else:
                    rng = periods.get(row.get("workPeriod", ""))
                if rng:
                    out[row["date"]].update(range(rng[0] // slot, rng[1] // slot))
        return out

    def run(self) -> Report:
        if not self.load():
            return self.report
        self.validate_schema()
        form = self.problem.get("form")
        if form in ("declarative", "expanded"):
            self.validate_common()
        if form == "declarative":
            self.validate_declarative()
        elif form == "expanded":
            self.validate_expanded()
        return self.report


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("problem", type=Path)
    ap.add_argument("-v", "--verbose", action="store_true", help="print stats")
    ap.add_argument("-j", "--json", action="store_true", help="machine-readable output")
    args = ap.parse_args()

    report = SchemaValidator(args.problem).run()

    if args.json:
        print(json.dumps({
            "valid": report.ok,
            "errors": report.errors,
            "warnings": report.warnings,
            "stats": report.stats,
        }, indent=2))
        return 0 if report.ok else 1

    for w in report.warnings:
        print(f"WARN  {w}")
    for e in report.errors:
        print(f"ERROR {e}")

    if args.verbose and report.stats:
        print("\nstats")
        for k, v in report.stats.items():
            print(f"  {k:20s} {v}")

    print()
    if report.ok:
        print(f"VALID  {args.problem}"
              + (f"  ({len(report.warnings)} warning(s))" if report.warnings else ""))
        return 0
    print(f"INVALID  {args.problem}  ({len(report.errors)} error(s))")
    return 1


if __name__ == "__main__":
    sys.exit(main())
