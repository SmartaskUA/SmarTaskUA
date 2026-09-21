"""Semantic checks for the declarative (problem) form.

Four tiers, in the order a reader most wants them:

  Tier 1  feasibility  - a worker-day whose cell cannot be satisfied at all
  Tier 2  structural   - per-week arithmetic and the labour-law caps
  Tier 3  integrity    - the CSVs and the codes they use
  Tier 4  reachability - declared-but-unusable things, reported as warnings

Everything here reads the files leniently: a malformed row is reported and
skipped, never raised, so one bad line cannot hide the rest of the file.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path

from . import core
from .core import DomainError, iso

GRAINS = (("days", "dataFileDays"), ("periods", "dataFilePeriods"), ("shifts", "dataFileShifts"))


class DeclarativeChecksMixin:
    problem: dict
    report: object
    base: Path

    def validate_declarative(self) -> None:
        days = self.horizon()
        rows_by_grain, open_days = self._validate_demand_csvs(days)
        cells, date_cols = self._validate_schedule_csv(days)

        self._check_day_off_codes()
        self._check_priority_hierarchy(rows_by_grain)
        self._check_schedules_catalogue()
        self._feasibility_preflight()
        self._check_structural(open_days, cells, date_cols)
        self._check_reachability(open_days, cells, rows_by_grain)

        self.report.stats["openDays"] = len(open_days)

    # -- Tier 3: the demand CSVs ------------------------------------------

    def _validate_demand_csvs(self, days: list[date]) -> tuple[dict[str, list], set[date]]:
        p, r = self.problem, self.report
        demand = p.get("demand", {})
        span = set(days)
        declared = core.dimension_set(p)
        slot = p.get("timeGrid", {}).get("slotMinutes", 30)

        rows_by_grain: dict[str, list] = {}
        open_days: set[date] = set()

        for grain, key in GRAINS:
            name = demand.get(key)
            if not name:
                continue
            path = self.base / name
            if not path.is_file():
                r.error(f"demand.{key}: file not found: {name}")
                rows_by_grain[grain] = []
                continue

            header, rows, problems = core.read_demand(path, grain)
            for msg in problems:
                r.error(f"{name}: {msg}")
            rows_by_grain[grain] = rows
            r.stats[f"demandRows.{grain}"] = len(rows)

            seen: set[tuple] = set()
            for row in rows:
                where = f"{name} row {row.line}"
                if span and row.date not in span:
                    r.error(f"{where}: date {row.date} lies outside temporalScope")
                pair = (row.table_name, row.table_value)
                if declared and pair not in declared:
                    r.error(f"{where}: {row.table_name}/{row.table_value} is not in demand.dimensions")
                for label, value in (("minimum", row.minimum), ("ideal", row.ideal),
                                     ("estimated", row.estimated)):
                    if value < 0:
                        r.error(f"{where}: {label} is negative ({core.format_number(value)})")

                if grain == "days":
                    # Workload minutes, not headcount: no window, and the value
                    # is a duration that must land on the grid.
                    if row.window is not None:
                        r.warn(f"{where}: the days grain is whole-day workload; a start/end "
                               f"window here is ignored")
                    if row.minimum and not core.on_grid(int(row.minimum), slot):
                        r.warn(f"{where}: {core.format_number(row.minimum)} workload minutes is not "
                               f"a multiple of the {slot}-minute grid")
                else:
                    if row.window is None:
                        r.error(f"{where}: start/end are mandatory on the {grain} grain")
                    else:
                        if not core.on_grid(row.window.start, slot) or not core.on_grid(row.window.end, slot):
                            r.error(f"{where}: window {row.window} does not land on the "
                                    f"{slot}-minute grid")
                        open_days.add(row.date)

                key_tuple = ((row.date, row.work_period, pair, row.window)
                             if grain == "shifts" else (row.date, pair, row.window))
                if key_tuple in seen:
                    r.error(f"{where}: duplicate row for {row.date} {row.table_name}/"
                            f"{row.table_value} {row.window or ''}".rstrip())
                seen.add(key_tuple)

            if grain == "periods":
                self._check_tiling(rows, name)

        if not open_days:
            r.warn("no demand row carries a window, so every day is closed and nothing "
                   "needs staffing")
        return rows_by_grain, open_days

    def _check_tiling(self, rows: list, name: str) -> None:
        """Overlapping windows for one (date, dimension) double-count the same slot."""
        buckets: dict[tuple, list] = defaultdict(list)
        for row in rows:
            if row.window is not None:
                buckets[(row.date, row.table_name, row.table_value)].append(row)
        for (day, tn, tv), group in sorted(buckets.items()):
            group.sort(key=lambda x: x.window.start)
            for a, b in zip(group, group[1:]):
                if a.window.overlaps(b.window):
                    self.report.warn(
                        f"{name}: {day} {tn}/{tv} has overlapping windows {a.window} (row "
                        f"{a.line}) and {b.window} (row {b.line}); a worker in the overlap "
                        f"counts toward both")

    # -- Tier 3: schedule_input.csv ---------------------------------------

    def _validate_schedule_csv(self, days: list[date]) -> tuple[dict, list[str]]:
        p, r = self.problem, self.report
        name = p.get("scheduleInput", {}).get("dataFile")
        if not name:
            return {}, []
        path = self.base / name
        if not path.is_file():
            r.error(f"scheduleInput.dataFile: file not found: {name}")
            return {}, []

        cells, date_cols, problems = core.read_schedule_input(path)
        for msg in problems:
            r.error(f"{name}: {msg}")

        wanted = [d.isoformat() for d in days]
        if days and date_cols != wanted:
            if len(date_cols) != len(wanted):
                r.error(f"{name}: has {len(date_cols)} date columns but temporalScope spans "
                        f"{len(wanted)} days")
            else:
                r.error(f"{name}: date columns do not match temporalScope "
                        f"({date_cols[0]}..{date_cols[-1]} vs {wanted[0]}..{wanted[-1]})")

        ids = {e.get("id") for e in p.get("employees", {}).get("list", [])}
        for missing in sorted(ids - set(cells)):
            r.error(f"{name}: employee {missing} has no row")
        for extra in sorted(set(cells) - ids):
            r.error(f"{name}: row {extra} is not an employee in employees.list")

        contracts = core.contracts_by_id(p)
        bad_cells: list[tuple[str, str]] = []
        mismatches: list[tuple[str, str]] = []
        for emp in p.get("employees", {}).get("list", []):
            eid = emp.get("id")
            row = cells.get(eid, {})
            for col in date_cols:
                raw = row.get(col, "")
                try:
                    rule = core.classify_cell(raw, p)
                except DomainError as exc:
                    bad_cells.append((str(exc), f"{name}: {eid} on {col}: {exc}"))
                    continue
                if rule.kind == "exact_hours":
                    cid = core.active_contract(emp, iso(col))
                    wanted_min = (contracts.get(cid) or {}).get("workMinutesPerDay")
                    if wanted_min is not None and rule.minutes != wanted_min:
                        mismatches.append((
                            f"{cid}:{rule.minutes}",
                            f"{name}: {eid} on {col}: cell {raw!r} is {rule.minutes} min but "
                            f"contract {cid} states {wanted_min}"))
        _report_grouped(r.error, bad_cells)
        _report_grouped(r.warn, mismatches)
        return cells, date_cols

    # -- Tier 3: integrity -------------------------------------------------

    def _check_day_off_codes(self) -> None:
        r = self.report
        codes = self.problem.get("scheduleInput", {}).get("dayOffCodes", {})
        if not codes:
            r.error("scheduleInput.dayOffCodes is empty: every non-numeric cell would be undeclared")
        for code, entry in codes.items():
            if not code.strip():
                r.error("scheduleInput.dayOffCodes: a code is blank")
            if entry.get("kind") not in ("preferable", "unavailable"):
                r.error(f"dayOffCodes[{code!r}]: kind must be 'preferable' or 'unavailable', "
                        f"found {entry.get('kind')!r}")

    def _check_priority_hierarchy(self, rows_by_grain: dict[str, list]) -> None:
        p, r = self.problem, self.report
        entries = p.get("priorityHierarchy", [])
        if not entries:
            return
        declared = core.dimension_set(p)
        demanded = {(row.table_name, row.table_value)
                    for rows in rows_by_grain.values() for row in rows}
        seen_rank: set[int] = set()
        for e in entries:
            rank = e.get("rank")
            if rank in seen_rank:
                r.error(f"priorityHierarchy: duplicate rank {rank}")
            seen_rank.add(rank)
            pair = (e.get("tableName"), e.get("tableValue"))
            if declared and pair not in declared:
                r.error(f"priorityHierarchy rank {rank}: {pair[0]}/{pair[1]} is not in "
                        f"demand.dimensions")
            elif demanded and pair not in demanded:
                r.warn(f"priorityHierarchy rank {rank}: {pair[0]}/{pair[1]} is never demanded, "
                       f"so this rank fills nothing")
            lo, hi = e.get("minAbilityLevel"), e.get("maxAbilityLevel")
            if isinstance(lo, int) and isinstance(hi, int) and lo > hi:
                r.error(f"priorityHierarchy rank {rank}: minAbilityLevel {lo} is above "
                        f"maxAbilityLevel {hi} (level 1 is the highest, so min must be the "
                        f"smaller number)")
        r.stats["priorityRanks"] = len(entries)

    def _check_schedules_catalogue(self) -> None:
        p, r = self.problem, self.report
        name = p.get("schedules", {}).get("dataFile")
        if not name:
            return
        path = self.base / name
        if not path.is_file():
            r.error(f"schedules.dataFile: file not found: {name}")
            return
        catalogue, problems = core.read_schedules(path)
        for msg in problems:
            r.error(f"{name}: {msg}")
        slot = p.get("timeGrid", {}).get("slotMinutes", 30)
        off_grid = [s.code for s in catalogue.values()
                    if s.interval and not (core.on_grid(s.interval.start, slot)
                                           and core.on_grid(s.interval.end, slot))]
        if off_grid:
            r.warn(f"{name}: {len(off_grid)} schedule(s) do not land on the {slot}-minute grid "
                   f"(e.g. {off_grid[0]}); a solver on this grid cannot emit them")
        mismatched = [s.code for s in catalogue.values()
                      if s.interval and s.interval.length != s.weight_minutes]
        if mismatched:
            r.warn(f"{name}: {len(mismatched)} schedule(s) whose window length differs from "
                   f"scheduleWeightMinutes (e.g. {mismatched[0]})")
        r.stats["schedules"] = len(catalogue)

    # -- Tier 1: feasibility ----------------------------------------------

    def _feasibility_preflight(self) -> None:
        r = self.report
        try:
            found = core.scan_feasibility(self.problem, self.base)
        except DomainError as exc:
            r.error(f"feasibility scan: {exc}")
            return
        except Exception as exc:                      # never let a preflight crash
            r.warn(f"feasibility scan did not complete ({exc}); real errors may be hidden")
            return
        _report_grouped(r.error, [(d.reason, str(d)) for d in found])
        r.stats["diagnostics"] = len(found)

    # -- Tier 2: structural ------------------------------------------------

    def _check_structural(self, open_days: set[date], cells: dict, date_cols: list[str]) -> None:
        p, r = self.problem, self.report
        if not cells or not date_cols:
            return
        days = self.horizon()
        if not days:
            return
        # validate_common has already reported an unusable weekStart; fall back
        # rather than abort, so the rest of the structural pass still runs.
        week_start = str(p.get("calendar", {}).get("weekStart", "monday")).lower()
        if week_start not in core.WEEKDAY_NAMES:
            week_start = "monday"
        origin = days[0]
        preferable, unavailable = core.day_off_sets(p.get("scheduleInput", {}))
        limits = self._legislation_limits()

        weeks: dict[int, list[date]] = defaultdict(list)
        for d in days:
            if d in open_days:
                weeks[core.week_index(d, origin, week_start)].append(d)

        negative = 0
        for emp in p.get("employees", {}).get("list", []):
            eid = emp.get("id")
            row = cells.get(eid, {})
            for wk, wdays in sorted(weeks.items()):
                u = sum(1 for d in wdays if row.get(d.isoformat()) in unavailable)
                dpref = sum(1 for d in wdays if row.get(d.isoformat()) in preferable)
                n_wk = len(wdays) - u - dpref
                if n_wk < 0:
                    negative += 1
                    r.error(f"employee {eid}, week {wk}: n_wk = {len(wdays)} open - {u} "
                            f"unavailable - {dpref} preferable = {n_wk}, which is impossible")
                cap = limits.get("MaxConsecutiveWorkDaysInWeek")
                if cap is not None and n_wk > cap:
                    r.error(f"employee {eid}, week {wk}: {n_wk} working days exceeds "
                            f"MaxConsecutiveWorkDaysInWeek of {cap}")

            cap = limits.get("MaxConsecutiveWorkDays")
            if cap is not None:
                run = 0
                for d in days:
                    cell = row.get(d.isoformat(), "")
                    working = d in open_days and cell not in unavailable and cell not in preferable
                    run = run + 1 if working else 0
                    if run > cap:
                        r.error(f"employee {eid}: forced to work {run} days in a row ending "
                                f"{d}, above MaxConsecutiveWorkDays of {cap}")
                        break
        r.stats["negative_n_wk"] = negative

    def _legislation_limits(self) -> dict[str, int]:
        """Flatten the enabled hard constraints' parameters into one lookup."""
        out: dict[str, int] = {}
        for entry in self.problem.get("constraints", {}).get("hard", []):
            if entry.get("enabled") is False:
                continue
            for k, v in (entry.get("parameters") or {}).items():
                if isinstance(v, int):
                    out[k] = v
        return out

    # -- Tier 4: reachability ---------------------------------------------

    def _check_reachability(self, open_days: set[date], cells: dict,
                            rows_by_grain: dict[str, list]) -> None:
        p, r = self.problem, self.report

        used = {c for row in cells.values() for c in row.values() if c}
        for code in p.get("scheduleInput", {}).get("dayOffCodes", {}):
            if code not in used:
                r.warn(f"dayOffCodes declares {code!r}, which no cell uses")

        demanded = {(row.table_name, row.table_value)
                    for rows in rows_by_grain.values() for row in rows}
        held: dict[tuple[str, str], int] = defaultdict(int)
        for e in p.get("employees", {}).get("list", []):
            for a in e.get("competencyAssignments", []):
                held[(a.get("tableName"), a.get("tableValue"))] += 1

        for pair in sorted(core.dimension_set(p)):
            if pair not in held:
                r.warn(f"dimension {pair[0]}/{pair[1]} is declared but nobody holds it")
            if demanded and pair not in demanded:
                r.warn(f"dimension {pair[0]}/{pair[1]} is declared but never demanded")

        # Headcount only: the days grain states workload MINUTES, so comparing
        # its minimum against a head count would read 960 minutes as 960 people.
        worst: dict[tuple[str, str], float] = {}
        for grain in ("periods", "shifts"):
            for row in rows_by_grain.get(grain, []):
                pair = (row.table_name, row.table_value)
                worst[pair] = max(worst.get(pair, 0.0), row.minimum)
        for pair, need in sorted(worst.items()):
            have = held.get(pair, 0)
            if need > have:
                r.warn(f"dimension {pair[0]}/{pair[1]} asks for up to "
                       f"{core.format_number(need)} workers but only {have} hold it")


def _report_grouped(emit, items: list[tuple[str, str]], keep: int = 3) -> None:
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
