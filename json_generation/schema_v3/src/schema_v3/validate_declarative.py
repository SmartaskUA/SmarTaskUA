#!/usr/bin/env python3
"""Declarative-form validation: the JSON's CSV companions and the feasibility of
what they ask for -- demand.csv, schedule_input.csv, cell semantics, per-week
working-day counts, coverage reachability, and the impossible-cell preflight.

A mixin on SchemaValidator (reads self.problem/base/report). Imports core and the
shared foundation; never transform.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import timedelta

import core  # sibling module in this package
from common import parse_range
from core import ALWAYS_UNAVAILABLE, DomainError, active_period, iso, week_index


class DeclarativeChecksMixin:
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
                # Each comma-separated segment must be a valid HH:MM-HH:MM range.
                # Overlaps are not an error: the parser coalesces them.
                for segment in body.split(","):
                    if "-" not in segment or parse_range(*segment.split("-", 1)) is None:
                        r.error(f"{fname}: {eid} {day}: malformed {op} constraint {cell!r}")
                        return
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
