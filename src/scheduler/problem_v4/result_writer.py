"""Schedule rows -> a v4 result (`OutRosterTeamDays`) and its sidecar.

Works for every solver, because every solver returns rows. A worked cell
becomes the menu code with that interval, a fixed day keeps the code the
partial result gave it, and a rest becomes code 3 ("Day off", WFM's number).
The output is always complete - no day left out - and is checked by the v4
validator against the input it came from.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from . import schema_core as core
from .instance import REST_CODE, V4Instance
from .rows import parse_worked_cell

RESULT_NAME = "result.json"
SIDECAR_NAME = "result_schedules.csv"


class ResultError(ValueError):
    """Rows that cannot become a valid v4 result."""

    def __init__(self, problems: List[str]):
        self.problems = list(problems)
        preview = "; ".join(self.problems[:5])
        if len(self.problems) > 5:
            preview += f" (+{len(self.problems) - 5} more)"
        super().__init__(f"cannot write a v4 result: {preview}")


def result_from_rows(inst: V4Instance, rows: List[List[str]]) -> Tuple[dict, List[core.Schedule]]:
    """(result document, sidecar rows) for a complete roster. Raises ResultError."""
    if [str(d) for d in rows[0][1:]] != inst.days:
        raise ResultError(["the rows' header does not match the instance's days"])

    by_interval: Dict[Tuple[int, int], int] = {}
    for code in sorted(inst.menu):
        schedule = inst.menu[code]
        if schedule.interval is not None and not schedule.is_sentinel:
            by_interval.setdefault((schedule.interval.start, schedule.interval.end), code)
    rest = inst.menu.get(REST_CODE)
    if rest is None or not rest.is_sentinel:
        rest = core.Schedule(REST_CODE, "Day off", 0, None)

    by_id = {str(row[0]): row for row in rows[1:]}
    entries, used, problems = [], {}, []
    for employee in inst.employees:
        row = by_id.get(employee.id)
        if row is None:
            problems.append(f"no row for employee {employee.id}")
            continue
        for day, cell in zip(inst.days, row[1:]):
            key = (employee.id, day)
            if key in inst.fixed:
                code = inst.fixed[key].code
                schedule = inst.menu[code]
            else:
                segments = parse_worked_cell(cell)
                if segments:
                    start, end = segments[0][0], segments[-1][1]
                    code = by_interval.get((start, end))
                    if code is None:
                        problems.append(f"{employee.id} on {day}: worked {core.Interval(start, end)}, "
                                        "which no menu code defines")
                        continue
                    schedule = inst.menu[code]
                elif inst.is_work_day(*key):
                    problems.append(f"{employee.id} on {day}: a work day left as {cell!r}")
                    continue
                else:
                    code, schedule = rest.code, rest
            used[code] = schedule
            entries.append({
                "RosterCode": inst.roster_code,
                "TeamCode": "1",
                "EmployeeCode": employee.id,
                "Date": f"{day}T00:00:00",
                "ScheduleCode": code,
                "OutRosterTeamDayTasks": [],
                "OutRosterTeamDayResponsibilities": [],
            })
    if problems:
        raise ResultError(problems)
    return {"OutRosterTeamDays": entries}, [used[c] for c in sorted(used)]


def _package_files(inst: V4Instance) -> List[str]:
    """problem.json and every CSV it names, relative to the package folder."""
    problem = inst.problem
    names = [inst.problem_path.name]
    demand = problem.get("demand", {})
    names += [demand[k] for k in ("dataFileDays", "dataFilePeriods", "dataFileShifts") if demand.get(k)]
    names.append(problem.get("scheduleInput", {}).get("dataFile"))
    if problem.get("schedules", {}).get("dataFile"):
        names.append(problem["schedules"]["dataFile"])
    return [n for n in names if n]


def write_package(inst: V4Instance, rows: List[List[str]], out_dir) -> Path:
    """Copy the input package to `out_dir` and write the result beside it.

    Never into the input folder: a package holds at most one result, and the
    next load would read a complete result as "every day fixed".
    """
    out = Path(out_dir).resolve()
    if out == inst.base.resolve():
        raise ValueError(f"refusing to write a result into the input package {out}")
    doc, sidecar = result_from_rows(inst, rows)
    out.mkdir(parents=True, exist_ok=True)
    for other in out.glob("*.json"):
        if other.name != RESULT_NAME and other.name != inst.problem_path.name:
            raise ValueError(f"{out} already holds {other.name}; choose an empty folder")

    for name in _package_files(inst):
        target = out / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(inst.base / name, target)
    (out / RESULT_NAME).write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out / SIDECAR_NAME).open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(core.SCHEDULE_COLUMNS)
        for schedule in sidecar:
            iv = schedule.interval
            writer.writerow([schedule.code, schedule.description, schedule.weight_minutes,
                             iv.start if iv else "", iv.end if iv else ""])
    return out / RESULT_NAME
