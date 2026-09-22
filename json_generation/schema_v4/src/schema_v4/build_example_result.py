#!/usr/bin/env python3
"""Build the worked result for examples/cenario2_retail.

**This produces a constructed artifact, not solver output.** No solver has run on
v4.0 yet; this script assigns each worker-day a shift from the ScheduleCode
menu by a fixed, stated rule, so that the result form and its sidecar CSV have a
realistic instance to be validated against. Any substitution it has to make -- a
shift that is not the contracted length, or one reaching outside the day's demand --
is counted into the `_comment` block it writes at the top of result.json.

    make result
    # or: PYTHONPATH=src python3 -m schema_v4.build_example_result

The rule, in full:

  1. A day-off cell in schedule_input.csv (any declared dayOffCode) becomes
     ScheduleCode 3, "Day off". A numeric cell becomes a working shift.
  2. The target duration is the employee's contract workMinutesPerDay.
  3. Candidates are catalogue entries that have a window and whose boundaries both
     land on the problem's timeGrid.
  4. Rank by |duration - target|, then by how much the window overlaps that date's
     demand for the dimensions the employee holds, then by earliest start. The
     first three keys are enough to make the choice unique and reproducible.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

from . import core

V4 = Path(__file__).resolve().parents[2]

PACKAGE = V4 / "examples" / "cenario2_retail"
REST_CODE = 3                       # "Day off" in the catalogue


def demand_by_date_and_pair(path: Path) -> dict:
    """{(date, tableName, tableValue): [Interval, ...]} from the periods grain."""
    _, rows, _ = core.read_demand(path, "periods")
    out = defaultdict(list)
    for r in rows:
        if r.window is not None:
            out[(r.date, r.table_name, r.table_value)].append(r.window)
    return out


def overlap(a: core.Interval, windows: list) -> int:
    """Minutes of `a` that fall inside the demanded time.

    The windows are coalesced first: Team and Responsibility rows overlap each
    other by design, and summing across them raw would count the same minute
    twice and inflate the score past the shift's own length.
    """
    return sum(max(0, min(a.end, w.end) - max(a.start, w.start))
               for w in core.coalesce(windows))


def main(argv=None) -> int:
    problem = json.loads((PACKAGE / "problem.json").read_text(encoding="utf-8"))
    slot = problem["timeGrid"]["slotMinutes"]
    roster = problem["metadata"]["rosterCode"]
    contracts = core.contracts_by_id(problem)
    catalogue, problems = core.read_schedules(PACKAGE / problem["schedules"]["dataFile"])
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1

    candidates = [s for s in catalogue.values()
                  if s.interval and core.on_grid(s.interval.start, slot)
                  and core.on_grid(s.interval.end, slot)]
    demand = demand_by_date_and_pair(PACKAGE / problem["demand"]["dataFilePeriods"])
    cells, dates, _ = core.read_schedule_input(PACKAGE / problem["scheduleInput"]["dataFile"])
    off_codes = set(problem["scheduleInput"]["dayOffCodes"])

    entries = []
    used: set[int] = set()
    substitutions: Counter[str] = Counter()
    rest_days = work_days = 0

    for emp in problem["employees"]["list"]:
        eid = emp["id"]
        row = cells.get(eid, {})
        for col in dates:
            day = core.iso(col)
            cell = row.get(col, "")
            if cell in off_codes:
                code = REST_CODE
                rest_days += 1
            else:
                cid = core.active_contract(emp, day)
                target = contracts[cid]["workMinutesPerDay"]
                pairs = [(a["tableName"], a["tableValue"])
                         for a in core.active_competencies(emp, day)]
                windows = [w for p in pairs for w in demand.get((day, *p), [])]
                best = min(candidates, key=lambda s: (abs(s.weight_minutes - target),
                                                      -overlap(s.interval, windows),
                                                      s.interval.start))
                code = best.code
                work_days += 1
                if best.weight_minutes != target:
                    substitutions[
                        f"{cid} needs {target} min; no such code exists, so "
                        f"{best.code} ({best.description}, {best.weight_minutes} min) "
                        f"was substituted"] += 1
                elif not windows or overlap(best.interval, windows) < best.weight_minutes:
                    substitutions[
                        f"{cid}: {best.code} ({best.description}) is the contracted "
                        f"length but reaches outside that day's demand window"] += 1
            used.add(code)
            entries.append({
                "RosterCode": roster,
                "TeamCode": "1",
                "EmployeeCode": eid,
                "Date": f"{col}T00:00:00",
                "ScheduleCode": code,
                "OutRosterTeamDayTasks": [],
                "OutRosterTeamDayResponsibilities": [],
            })

    result = {
        "_comment": (
            "CONSTRUCTED ARTIFACT, NOT SOLVER OUTPUT. Built by "
            "`make result` (src/schema_v4/build_example_result.py) so that the result "
            "form and its sidecar CSV have a realistic instance to validate against. "
            "No v4.0 solver exists yet."
        ),
        "_comment_coverage": (
            f"{len(entries)} employee-days: {work_days} worked, {rest_days} rest "
            f"(ScheduleCode {REST_CODE}). {len(used)} distinct codes, defined in "
            f"result_schedules.csv."
        ),
        "_comment_substitutions": (
            [f"{n}x {text}" for text, n in substitutions.most_common()]
            or ["none - every worked day got a shift of exactly the contracted length"]
        ),
        "OutRosterTeamDays": entries,
    }
    with (PACKAGE / "result.json").open("w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, ensure_ascii=False)
        fh.write("\n")

    # The sidecar: the codes this result used, in catalogue shape. A solver emits
    # this alongside its result so the result is readable without the full menu.
    with (PACKAGE / "result_schedules.csv").open("w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(core.SCHEDULE_COLUMNS)
        for code in sorted(used):
            s = catalogue[code]
            w.writerow([s.code, s.description, s.weight_minutes,
                        s.interval.start if s.interval else "",
                        s.interval.end if s.interval else ""])

    print(f"result.json           {len(entries)} employee-days "
          f"({work_days} worked, {rest_days} rest)")
    print(f"result_schedules.csv  {len(used)} distinct codes")
    if substitutions:
        print("substitutions:")
        for text, n in substitutions.most_common():
            print(f"  {n:4}x {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
