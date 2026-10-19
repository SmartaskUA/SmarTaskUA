"""Cross-checks for the result form.

A result does not restate the problem, it references it - by RosterCode,
EmployeeCode, Date and ScheduleCode. Those references point into other files, so
the JSON Schema layer cannot enforce them and this module does, given the problem
to check against. Without one it warns and skips, rather than passing silently.

A result also carries a **sidecar catalogue**, `<stem>_schedules.csv`, defining the
codes it used - see `SIDECAR_SUFFIX`. That file is our convention, not Sisqual's:
the result document itself is their WFM import API and stays verbatim, so the
definition of what its codes mean lives beside it rather than inside it.

A result may be **partial**. The entries it carries are fixed days - each is held
to its schedule_input cell and to the labour law as a hard rule - and a day it
leaves out is open for the solver. Nothing marks a result as partial and nothing
complains about a missing day; the stats say how much is left.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from . import core
from .common import report_grouped
from .core import iso

#: Rest codes assumed when no catalogue is in reach. With one, a sentinel is
#: recognised from the data instead -- a row with no window and zero weight -- so a
#: roster that mints its own codes is not held to these three numbers.
FALLBACK_SENTINELS = {1: "Espaco", 3: "Day off", 4: "Vazio"}

#: A result at `foo.json` pairs with `foo_schedules.csv`.
SIDECAR_SUFFIX = "_schedules.csv"


class ResultChecksMixin:
    path: Path
    problem: dict          # here: the *result* document
    report: object
    base: Path
    against: Path | None

    def _locate_problem(self) -> Path | None:
        if self.against:
            return self.against
        candidates = []
        for path in sorted(self.base.glob("*.json")):
            try:
                with path.open(encoding="utf-8") as fh:
                    head = json.load(fh)
            except (ValueError, OSError):
                continue
            if head.get("form") == "input":
                candidates.append(path)
        return candidates[0] if len(candidates) == 1 else None

    def _locate_sidecar(self) -> Path | None:
        path = self.base / (self.path.stem + SIDECAR_SUFFIX)
        return path if path.is_file() else None

    def validate_result(self) -> None:
        r = self.report
        result = self.problem
        entries = result.get("OutRosterTeamDays", [])
        r.stats["rosterDays"] = len(entries)

        sidecar = self._load_sidecar()
        used_codes = {e.get("ScheduleCode") for e in entries}

        path = self._locate_problem()
        if path is None:
            r.warn("no input problem found beside this result (and no --against), "
                   "so the cross-checks were skipped: only the schema layer ran")
            self._check_sidecar(sidecar, used_codes, menu={})
            return
        try:
            with path.open(encoding="utf-8") as fh:
                problem = json.load(fh)
        except (ValueError, OSError) as exc:
            r.error(f"could not read the problem at {path.name}: {exc}")
            return
        r.stats["crossCheckedAgainst"] = path.name

        roster = problem.get("metadata", {}).get("rosterCode")
        days = core.horizon(problem)
        span = set(days)
        employees = {str(e.get("id")): e for e in problem.get("employees", {}).get("list", [])}
        contracts = core.contracts_by_id(problem)
        menu = self._load_menu(problem, path.parent)
        cells = self._load_cells(problem, path.parent)

        # A code's definition comes from the sidecar when there is one - it is what
        # the producer says it used - and from the problem's menu otherwise.
        defined = sidecar if sidecar is not None else menu

        seen: dict[tuple[str, str], int] = defaultdict(int)
        fixed: dict[str, dict[date, core.Schedule | None]] = defaultdict(dict)
        int_codes = 0
        self._grouped: list[tuple[str, str]] = []

        for n, e in enumerate(entries, start=1):
            where = f"OutRosterTeamDays[{n - 1}]"
            emp_raw = e.get("EmployeeCode")
            if isinstance(emp_raw, int):
                int_codes += 1
            eid = str(emp_raw)

            if roster and e.get("RosterCode") != roster:
                r.error(f"{where}: RosterCode {e.get('RosterCode')!r} does not match the "
                        f"problem's metadata.rosterCode {roster!r}")
            if eid not in employees:
                r.error(f"{where}: EmployeeCode {eid} is not in employees.list")

            day = iso(e.get("Date", ""))
            if day is None:
                r.error(f"{where}: Date {e.get('Date')!r} is not a date")
                continue
            if span and day not in span:
                r.error(f"{where}: Date {day} lies outside temporalScope")

            key = (eid, day.isoformat())
            seen[key] += 1
            if seen[key] == 2:
                r.error(f"{where}: {eid} already has an entry for {day}")
                continue

            code = e.get("ScheduleCode")
            if not isinstance(code, int):
                continue
            if menu and code not in menu:
                self._grouped.append((f"missing:{code}",
                                      f"{where}: ScheduleCode {code} is not in the "
                                      f"schedules catalogue"))
                continue
            schedule = self._resolve(code, defined)
            if eid in employees and (not span or day in span):
                fixed[eid][day] = schedule
            self._check_cell(where, code, schedule, employees.get(eid), eid, day,
                             contracts, cells, problem)

        report_grouped(r.error, self._grouped)
        self._check_fixed_law(fixed, days, problem)

        filled = {(eid, d) for eid, d in seen
                  if eid in employees and (not span or iso(d) in span)}
        expected = len(employees) * len(days)
        r.stats["rosterDaysExpected"] = expected
        r.stats["rosterDaysLeft"] = max(0, expected - len(filled))

        if int_codes:
            r.warn(f"EmployeeCode is an integer in {int_codes} of {len(entries)} entries, but a "
                   f"string in the problem. JSON-Import.docx says string - see "
                   f"next_meeting.md item 13 ('EmployeeCode is an integer').")
        self._check_sidecar(sidecar, used_codes, menu)
        self._check_schedule_useds(result, defined)

    # -- the sidecar -------------------------------------------------------

    def _load_sidecar(self) -> dict | None:
        """The codes this result says it used, or None when no sidecar is present."""
        path = self._locate_sidecar()
        if path is None:
            return None
        catalogue, problems = core.read_schedules(path)
        for msg in problems:
            self.report.error(f"{path.name}: {msg}")
        self.report.stats["sidecarCodes"] = len(catalogue)
        return catalogue

    def _check_sidecar(self, sidecar: dict | None, used: set, menu: dict) -> None:
        r = self.report
        name = self.path.stem + SIDECAR_SUFFIX
        if sidecar is None:
            r.warn(f"no {name} beside this result, so its ScheduleCodes carry no "
                   f"definition. A result should ship the codes it used - see "
                   f"docs/FORMAT.md.")
            return
        for code in sorted(c for c in used if isinstance(c, int) and c not in sidecar):
            r.error(f"{name}: ScheduleCode {code} is used by the result but not defined here")
        for code in sorted(c for c in sidecar if c not in used):
            r.warn(f"{name}: defines ScheduleCode {code}, which the result never uses "
                   f"(the sidecar is the used set, not a copy of the menu)")
        if not menu:
            return
        for code, entry in sorted(sidecar.items()):
            other = menu.get(code)
            if other is None:
                r.error(f"{name}: ScheduleCode {code} is not in the problem's catalogue - "
                        f"a result may only use shifts the problem offers")
            elif (entry.description, entry.weight_minutes, entry.interval) != \
                    (other.description, other.weight_minutes, other.interval):
                r.error(f"{name}: ScheduleCode {code} is defined as "
                        f"{entry.description!r}/{entry.weight_minutes}min here but "
                        f"{other.description!r}/{other.weight_minutes}min in the "
                        f"problem's catalogue")

    # -- per entry: the fixed day against its cell --------------------------

    @staticmethod
    def _resolve(code: int, defined: dict) -> core.Schedule | None:
        """What a code stands for, or None for a worked code nobody defines."""
        known = (defined or {}).get(code)
        if known is not None:
            return known
        if code in FALLBACK_SENTINELS:
            return core.Schedule(code, FALLBACK_SENTINELS[code], 0, None)
        return None

    def _check_cell(self, where, code, schedule, emp, eid, day, contracts, cells,
                    problem) -> None:
        raw = (cells.get(eid) or {}).get(day.isoformat())
        if emp is None or raw is None:
            return
        try:
            rule = core.classify_cell(raw, problem)
        except core.DomainError:
            return      # a malformed cell is the problem's finding, not this result's
        cid = core.active_contract(emp, day)
        wanted = (contracts.get(cid) or {}).get("workMinutesPerDay")
        reason = core.cell_conflict(rule, schedule, wanted)
        if reason:
            self._grouped.append((
                f"cell:{reason}",
                f"{where}: ScheduleCode {code} for {eid} on {day} contradicts the cell "
                f"{raw!r}: {reason}"))

    # -- the fixed days against the labour law -----------------------------

    def _check_fixed_law(self, fixed: dict, days: list[date], problem: dict) -> None:
        """The roster-wide caps, over the days the result fixes.

        A day left open breaks a run, because the solver may yet rest it: only what
        is already decided can be judged, so a finding here is a real violation.
        """
        limits = core.legislation_limits(problem)
        if not limits or not days:
            return
        week_start = str(problem.get("calendar", {}).get("weekStart", "monday")).lower()
        if week_start not in core.WEEKDAY_NAMES:
            week_start = "monday"
        run_cap = limits.get("MaxConsecutiveWorkDays")
        week_cap = limits.get("MaxConsecutiveWorkDaysInWeek")
        min_rest = limits.get("MinDistanceBetweenShiftsInMinutes")
        found: list[tuple[str, str]] = []

        for eid, by_day in sorted(fixed.items()):
            worked = {d: s for d, s in by_day.items() if s is None or not s.is_sentinel}

            if run_cap is not None:
                run = 0
                for d in days:
                    run = run + 1 if d in worked else 0
                    if run > run_cap:
                        found.append(("MaxConsecutiveWorkDays",
                                      f"{eid}: fixed to work {run} days in a row ending {d}, "
                                      f"above MaxConsecutiveWorkDays of {run_cap}"))
                        break

            if week_cap is not None:
                per_week = Counter(core.week_index(d, days[0], week_start) for d in worked)
                for wk, n in sorted(per_week.items()):
                    if n > week_cap:
                        found.append(("MaxConsecutiveWorkDaysInWeek",
                                      f"{eid}, week {wk}: {n} fixed working days exceeds "
                                      f"MaxConsecutiveWorkDaysInWeek of {week_cap}"))

            if min_rest is not None:
                for d, before in sorted(worked.items()):
                    after = worked.get(d + timedelta(days=1))
                    if before is None or after is None or \
                            before.interval is None or after.interval is None:
                        continue
                    rest = after.interval.start + core.MINUTES_PER_DAY - before.interval.end
                    if rest < min_rest:
                        found.append(("MinDistanceBetweenShiftsInMinutes",
                                      f"{eid}: {rest} min of rest between {before.interval} "
                                      f"on {d} and {after.interval} the next day, below "
                                      f"MinDistanceBetweenShiftsInMinutes of {min_rest}"))
        report_grouped(self.report.error, found)

    # -- loading the problem's own files -----------------------------------

    def _load_menu(self, problem: dict, base: Path) -> dict:
        """The menu the problem offers, which a result may only pick from.

        An unreadable menu must be said out loud. Returning {} quietly turns every
        menu check below into a no-op, and a result that used a code nobody offers
        would then pass for the wrong reason.
        """
        name = problem.get("schedules", {}).get("dataFile")
        if not name:
            self.report.warn("the problem declares no shift menu, so this result's codes "
                             "were not checked against one")
            return {}
        path = base / name
        if not path.is_file():
            self.report.warn(f"the problem's menu ({name}) is missing, so this result's "
                             f"codes were not checked against it")
            return {}
        catalogue, _ = core.read_schedules(path)
        return catalogue

    @staticmethod
    def _load_cells(problem: dict, base: Path) -> dict:
        name = problem.get("scheduleInput", {}).get("dataFile")
        if not name:
            return {}
        path = base / name
        if not path.is_file():
            return {}
        cells, _, _ = core.read_schedule_input(path)
        return cells

    def _check_schedule_useds(self, result: dict, defined: dict) -> None:
        r = self.report
        useds = result.get("OutScheduleUseds")
        if not useds:
            return
        r.stats["scheduleUseds"] = len(useds)
        seen: set[int] = set()
        for n, s in enumerate(useds):
            code = s.get("ScheduleCode")
            if code in seen:
                r.error(f"OutScheduleUseds[{n}]: ScheduleCode {code} appears twice")
            seen.add(code)
            entry = defined.get(code) if defined else None
            weight = s.get("ScheduleWeight")
            if entry and isinstance(weight, int) and weight != entry.weight_minutes:
                r.error(f"OutScheduleUseds[{n}]: ScheduleWeight {weight} contradicts the "
                        f"catalogue's {entry.weight_minutes} for code {code}")
        used_codes = {e.get("ScheduleCode") for e in result.get("OutRosterTeamDays", [])}
        for orphan in sorted(seen - used_codes, key=lambda x: (x is None, x)):
            r.warn(f"OutScheduleUseds defines ScheduleCode {orphan}, which no roster day uses")
