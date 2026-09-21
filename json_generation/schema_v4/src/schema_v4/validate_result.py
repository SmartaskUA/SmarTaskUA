"""Cross-checks for the result form.

A result does not restate the problem, it references it - by RosterCode,
EmployeeCode, Date and ScheduleCode. Those references point into other files,
so the JSON Schema layer cannot enforce them and this module does, given the
problem to check against. Without one it warns and skips, rather than passing
silently.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from . import core
from .core import iso

#: Catalogue codes that mean "no shift" rather than a worked block.
SENTINEL_CODES = {1: "Espaco", 3: "Day off", 4: "Vazio"}


class ResultChecksMixin:
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
            if head.get("form") == "declarative":
                candidates.append(path)
        return candidates[0] if len(candidates) == 1 else None

    def validate_result(self) -> None:
        r = self.report
        result = self.problem
        entries = result.get("OutRosterTeamDays", [])
        r.stats["rosterDays"] = len(entries)

        path = self._locate_problem()
        if path is None:
            r.warn("no declarative problem found beside this result (and no --against), "
                   "so the cross-checks were skipped: only the schema layer ran")
            return
        try:
            with path.open(encoding="utf-8") as fh:
                problem = json.load(fh)
        except (ValueError, OSError) as exc:
            r.error(f"could not read the problem at {path.name}: {exc}")
            return
        r.stats["crossCheckedAgainst"] = path.name

        roster = problem.get("metadata", {}).get("rosterCode")
        span = set(core.horizon(problem))
        employees = {str(e.get("id")): e for e in problem.get("employees", {}).get("list", [])}
        contracts = core.contracts_by_id(problem)
        catalogue = self._load_catalogue(problem, path.parent)
        preferable, unavailable = core.day_off_sets(problem.get("scheduleInput", {}))
        cells = self._load_cells(problem, path.parent)

        seen: dict[tuple[str, str], int] = defaultdict(int)
        int_codes = 0

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

            code = e.get("ScheduleCode")
            self._check_code(where, code, eid, day, catalogue, contracts,
                             employees, cells, preferable, unavailable)

        if int_codes:
            r.warn(f"EmployeeCode is an integer in {int_codes} of {len(entries)} entries, but a "
                   f"string in the problem. JSON-Import.docx says string - see "
                   f"docs/next_meeting.md item 14.")
        self._check_schedule_useds(result, catalogue)

    def _check_code(self, where, code, eid, day, catalogue, contracts, employees,
                    cells, preferable, unavailable) -> None:
        r = self.report
        if not isinstance(code, int):
            return
        if catalogue and code not in catalogue:
            r.error(f"{where}: ScheduleCode {code} is not in the schedules catalogue")
            return

        cell = (cells.get(eid) or {}).get(day.isoformat(), "")
        is_rest = code in SENTINEL_CODES
        if cell in unavailable and not is_rest:
            r.error(f"{where}: {eid} is {cell!r} (unavailable) on {day}, but the result "
                    f"assigns ScheduleCode {code}")
        if is_rest and cell and cell not in preferable and cell not in unavailable:
            r.warn(f"{where}: {eid} rests on {day} ({SENTINEL_CODES[code]}) although the "
                   f"problem's cell asks for work ({cell!r})")

        entry = catalogue.get(code) if catalogue else None
        if entry is None or entry.interval is None:
            return
        emp = employees.get(eid)
        if emp is None:
            return
        cid = core.active_contract(emp, day)
        wanted = (contracts.get(cid) or {}).get("workMinutesPerDay")
        if wanted is not None and entry.weight_minutes != wanted:
            r.warn(f"{where}: ScheduleCode {code} is {entry.weight_minutes} min but "
                   f"{eid}'s contract {cid} states {wanted}")

    @staticmethod
    def _load_catalogue(problem: dict, base: Path) -> dict:
        name = problem.get("schedules", {}).get("dataFile")
        if not name:
            return {}
        path = base / name
        if not path.is_file():
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

    def _check_schedule_useds(self, result: dict, catalogue: dict) -> None:
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
            entry = catalogue.get(code) if catalogue else None
            weight = s.get("ScheduleWeight")
            if entry and isinstance(weight, int) and weight != entry.weight_minutes:
                r.error(f"OutScheduleUseds[{n}]: ScheduleWeight {weight} contradicts the "
                        f"catalogue's {entry.weight_minutes} for code {code}")
        used_codes = {e.get("ScheduleCode") for e in result.get("OutRosterTeamDays", [])}
        for orphan in sorted(seen - used_codes, key=lambda x: (x is None, x)):
            r.warn(f"OutScheduleUseds defines ScheduleCode {orphan}, which no roster day uses")
