from __future__ import annotations

import copy
import csv
import json
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Callable

from validators.sisqual_feasibility import validate_sisqual_problem_or_raise


MONTHLY_THRESHOLD_DAYS = 45
CONTEXT_DAYS = 5
OFF_CONTEXT_MARKERS = {"", "DO", "FDO", "VAC", "NOT", "MED", "ENFD", "DC-E", "OFF", "CLOSED", "UNASSIGNED"}


@dataclass
class MonthlySisqualResult:
    schedule: list[list[str]]
    metadata: dict


def should_run_monthly(problem_path: str | None) -> bool:
    """Return True when a Sisqual bundle is too large for the default monolithic run."""

    if not problem_path:
        return False
    problem_json = _resolve_problem_json(problem_path)
    if not problem_json.is_file():
        return False
    problem = _read_json(problem_json)
    target_days = _target_days(problem)
    return len(target_days) > MONTHLY_THRESHOLD_DAYS


def run_sisqual_monthly(
    *,
    problem_path: str,
    algorithm: Callable,
    algorithm_name: str,
    max_time,
    task_id: str,
) -> MonthlySisqualResult:
    """Solve a long Sisqual bundle one calendar month at a time.

    Each temporary monthly bundle keeps the same employees, contracts, skills,
    constraints, and objective configuration as the source bundle. Only
    targetPeriod, demand.csv, and schedule_input.csv are sliced. After each
    month, the generated schedule becomes immutable before-context for the next
    month, so boundary-sensitive constraints can still see recent history.
    """

    source_problem_json = _resolve_problem_json(problem_path)
    source_dir = source_problem_json.parent
    source_problem = _read_json(source_problem_json)
    all_target_days = _target_days(source_problem)
    month_groups = _group_days_by_month(all_target_days)

    demand_file = source_problem.get("demand", {}).get("dataFile", "demand.csv")
    schedule_file = source_problem.get("scheduleInput", {}).get("dataFile", "schedule_input.csv")
    demand_header, source_demand_rows = _read_dict_csv(source_dir / demand_file)
    source_schedule_header, source_schedule_rows = _read_raw_csv(source_dir / schedule_file)
    source_schedule = _schedule_rows_to_map(source_schedule_header, source_schedule_rows)
    employee_order = [row[0] for row in source_schedule_rows]

    run_root = _monthly_run_root(task_id)
    run_root.mkdir(parents=True, exist_ok=True)

    merged_by_employee = {employee_id: {} for employee_id in employee_order}
    month_metadata = []

    for index, month_days in enumerate(month_groups, start=1):
        month_label = month_days[0][:7]
        month_dir = run_root / month_label
        month_dir.mkdir(parents=True, exist_ok=True)

        before_days = _available_before_context_days(month_days[0], merged_by_employee)
        month_problem = _monthly_problem(source_problem, month_days, month_label)
        month_demand_rows = [row for row in source_demand_rows if row.get("date") in set(month_days)]
        month_schedule_header, month_schedule_rows = _monthly_schedule_rows(
            employee_order,
            source_schedule,
            merged_by_employee,
            before_days,
            month_days,
        )

        _write_json(month_dir / "problem.json", month_problem)
        _write_dict_csv(month_dir / "demand.csv", demand_header, month_demand_rows)
        _write_raw_csv(month_dir / "schedule_input.csv", month_schedule_header, month_schedule_rows)

        validate_sisqual_problem_or_raise(
            str(month_dir / "problem.json"),
            f"{task_id}-{month_label}",
            algorithm_name=algorithm_name,
        )

        started = time.time()
        print(
            f"[SisqualMonthlyRunner] Solving {month_label} "
            f"({month_days[0]} to {month_days[-1]}) with {len(before_days)} before-context days."
        )
        month_schedule = algorithm(
            problem_path=str(month_dir / "problem.json"),
            maxTime=max_time,
            print_json=True,
            task_id=f"{task_id}-{month_label}",
        )
        elapsed = time.time() - started

        _merge_month_schedule(merged_by_employee, month_schedule)
        month_metadata.append(
            {
                "index": index,
                "month": month_label,
                "start": month_days[0],
                "end": month_days[-1],
                "days": len(month_days),
                "beforeContextDays": before_days,
                "elapsedSeconds": elapsed,
                "temporaryProblemPath": str(month_dir / "problem.json"),
            }
        )
        print(f"[SisqualMonthlyRunner] Finished {month_label} in {elapsed:.2f}s.")

    merged_schedule = _merged_schedule_rows(employee_order, all_target_days, merged_by_employee)
    metadata = {
        "executionMode": "monthly",
        "sourceProblemPath": str(source_problem_json),
        "monthlyThresholdDays": MONTHLY_THRESHOLD_DAYS,
        "contextDays": CONTEXT_DAYS,
        "months": month_metadata,
        "temporaryRunPath": str(run_root),
    }
    return MonthlySisqualResult(schedule=merged_schedule, metadata=metadata)


def _resolve_problem_json(problem_path: str) -> Path:
    path = Path(problem_path)
    if not path.is_absolute():
        path = (Path.cwd() / path).resolve()
    if path.is_dir():
        path = path / "problem.json"
    return path


def _read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def _write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def _read_dict_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def _write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _read_raw_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        rows = list(csv.reader(file))
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows[0], rows[1:]


def _write_raw_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def _target_days(problem: dict) -> list[str]:
    target = problem.get("temporalScope", {}).get("targetPeriod", {})
    start = date.fromisoformat(target["start"])
    end = date.fromisoformat(target["end"])
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def _group_days_by_month(days: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current_group: list[str] = []
    current_month = None
    for day in days:
        month = day[:7]
        if current_month is not None and month != current_month:
            groups.append(current_group)
            current_group = []
        current_month = month
        current_group.append(day)
    if current_group:
        groups.append(current_group)
    return groups


def _monthly_run_root(task_id: str) -> Path:
    shared_mount = Path("/shared_tmp")
    if shared_mount.exists():
        return shared_mount / "monthly_sisqual_runs" / task_id
    for parent in Path(__file__).resolve().parents:
        if (parent / ".git").exists():
            return parent / "shared_tmp" / "monthly_sisqual_runs" / task_id
    return Path.cwd() / "shared_tmp" / "monthly_sisqual_runs" / task_id


def _monthly_problem(source_problem: dict, month_days: list[str], month_label: str) -> dict:
    problem = copy.deepcopy(source_problem)
    metadata = problem.setdefault("metadata", {})
    source_problem_id = str(metadata.get("problemId", "SISQUAL")).strip()
    metadata["problemId"] = f"{source_problem_id}_{month_label}"
    metadata["source"] = f"Monthly slice generated from {source_problem_id}"

    temporal_scope = problem.setdefault("temporalScope", {})
    temporal_scope["numDays"] = len(month_days)
    temporal_scope["targetPeriod"] = {
        "start": month_days[0],
        "end": month_days[-1],
        "includeBufferWeeks": False,
    }
    problem.setdefault("demand", {})["dataFile"] = "demand.csv"
    problem.setdefault("scheduleInput", {})["dataFile"] = "schedule_input.csv"
    return problem


def _schedule_rows_to_map(header: list[str], rows: list[list[str]]) -> dict[str, dict[str, str]]:
    dates = header[1:]
    result = {}
    for row in rows:
        if len(row) != len(header):
            raise ValueError(f"Schedule row has wrong column count for employee {row[0] if row else '<empty>'}")
        result[row[0]] = dict(zip(dates, row[1:]))
    return result


def _available_before_context_days(month_start: str, merged_by_employee: dict[str, dict[str, str]]) -> list[str]:
    available = set()
    for employee_days in merged_by_employee.values():
        available.update(employee_days)

    context = []
    current = date.fromisoformat(month_start) - timedelta(days=1)
    while len(context) < CONTEXT_DAYS and current.isoformat() in available:
        context.append(current.isoformat())
        current -= timedelta(days=1)
    return list(reversed(context))


def _monthly_schedule_rows(
    employee_order: list[str],
    source_schedule: dict[str, dict[str, str]],
    merged_by_employee: dict[str, dict[str, str]],
    before_days: list[str],
    month_days: list[str],
) -> tuple[list[str], list[list[str]]]:
    header = ["employee_id", *before_days, *month_days]
    rows = []
    for employee_id in employee_order:
        row = [employee_id]
        for day in before_days:
            row.append(_context_marker_from_output(merged_by_employee[employee_id].get(day, "")))
        for day in month_days:
            row.append(source_schedule[employee_id].get(day, ""))
        rows.append(row)
    return header, rows


def _context_marker_from_output(marker: str) -> str:
    text = str(marker or "").strip()
    if text.upper() in OFF_CONTEXT_MARKERS:
        return "DO"
    if text.upper().startswith("EQUALS:"):
        return text

    ranges = re.findall(r"(\d{1,2}:\d{2})-(\d{1,2}:\d{2})", text)
    if not ranges:
        return "DO"

    starts = [_minutes(start) for start, _ in ranges]
    ends = [_minutes(end) for _, end in ranges]
    return f"EQUALS:{_hhmm(min(starts))}-{_hhmm(max(ends))}"


def _minutes(value: str) -> int:
    parsed = datetime.strptime(value, "%H:%M")
    return parsed.hour * 60 + parsed.minute


def _hhmm(value: int) -> str:
    return f"{value // 60:02d}:{value % 60:02d}"


def _merge_month_schedule(merged_by_employee: dict[str, dict[str, str]], month_schedule: list[list[str]]) -> None:
    if not month_schedule:
        return
    header = month_schedule[0]
    days = header[1:]
    for row in month_schedule[1:]:
        employee_id = row[0]
        merged_by_employee.setdefault(employee_id, {})
        for day, marker in zip(days, row[1:]):
            merged_by_employee[employee_id][day] = marker


def _merged_schedule_rows(
    employee_order: list[str],
    days: list[str],
    merged_by_employee: dict[str, dict[str, str]],
) -> list[list[str]]:
    rows = [["employee_id", *days]]
    for employee_id in employee_order:
        employee_days = merged_by_employee.get(employee_id, {})
        rows.append([employee_id, *[employee_days.get(day, "") for day in days]])
    return rows
