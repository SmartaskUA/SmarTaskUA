#!/usr/bin/env python3
"""Generate the SISQUAL_COMPLETE_EXPANDED_PLUS6 benchmark problem."""

from __future__ import annotations

import copy
import csv
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "problems" / "SISQUAL_COMPLETE"
TARGET_DIR = ROOT / "data" / "problems" / "SISQUAL_COMPLETE_EXPANDED_PLUS6"

SOURCE_PROBLEM_ID = "SISQUAL_HOURS_OCTOBER_COMPLETE_OBJ1_4_5"
TARGET_PROBLEM_ID = "SISQUAL_COMPLETE_EXPANDED_PLUS6"

EMPLOYEES_PEAK_PERIODS = {
    "EMPLOYEES_1000_1100",
    "EMPLOYEES_1100_1200",
    "EMPLOYEES_1200_1300",
    "EMPLOYEES_1300_1400",
    "EMPLOYEES_1700_1800",
    "EMPLOYEES_1800_1900",
    "EMPLOYEES_1900_2000",
    "EMPLOYEES_2000_2100",
    "EMPLOYEES_2100_2200",
}

NEW_EMPLOYEES = [
    {
        "id": "900200001",
        "name": "Storage Backup Expanded",
        "teams": [{"code": "Storage", "level": 1}, {"code": "Employees", "level": 6}],
        "contractType": "partTime_7h",
        "copyScheduleFrom": "20051291",
    },
    {
        "id": "900200002",
        "name": "Manager Level 1 Backup Expanded",
        "teams": [{"code": "Management", "level": 1}, {"code": "Employees", "level": 6}],
        "contractType": "fullTime_8h",
        "copyScheduleFrom": "20072412",
    },
    {
        "id": "900200003",
        "name": "Manager Level 2 / Checkout Backup Expanded",
        "teams": [
            {"code": "Management", "level": 2},
            {"code": "Checkout", "level": 2},
            {"code": "Employees", "level": 6},
        ],
        "contractType": "fullTime_8h",
        "copyScheduleFrom": "20066543",
    },
    {
        "id": "900200004",
        "name": "Checkout Level 2 Peak Support Expanded A",
        "teams": [{"code": "Checkout", "level": 2}, {"code": "Employees", "level": 6}],
        "contractType": "partTime_4h",
        "copyScheduleFrom": "20067696",
    },
    {
        "id": "900200005",
        "name": "Checkout Level 2 Peak Support Expanded B",
        "teams": [{"code": "Checkout", "level": 2}, {"code": "Employees", "level": 6}],
        "contractType": "partTime_5h",
        "copyScheduleFrom": "20058959",
    },
    {
        "id": "900200006",
        "name": "Checkout-L1 / Manager-L3 Flex Expanded",
        "teams": [
            {"code": "Checkout", "level": 1},
            {"code": "Management", "level": 3},
            {"code": "Employees", "level": 6},
        ],
        "contractType": "partTime_5h",
        "copyScheduleFrom": "20067009",
    },
]


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_raw_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        rows = list(reader)
    return rows[0], rows[1:]


def write_raw_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def time_to_minutes(value: str) -> int:
    hours, minutes = value.split(":", 1)
    return int(hours) * 60 + int(minutes)


def work_period_hours(problem: dict) -> dict[str, float]:
    durations = {}
    for period in problem["demand"]["workPeriods"]:
        time_range = period["timeRange"]
        start = time_to_minutes(time_range["start"])
        end = time_to_minutes(time_range["end"])
        durations[period["code"]] = (end - start) / 60
    return durations


def minimum_worker_hours(
    demand_rows: list[dict[str, str]], period_hours: dict[str, float]
) -> dict[str, float]:
    totals: dict[str, float] = defaultdict(float)
    for row in demand_rows:
        totals[row["team"]] += int(row["minimum"]) * period_hours[row["workPeriod"]]
    return dict(sorted(totals.items()))


def mark_hours(mark: str) -> float:
    if mark in {"", "DO", "FDO", "VAC", "NOT", "Med"}:
        return 0
    if mark.startswith("EQUALS:"):
        start, end = mark.removeprefix("EQUALS:").split("-", 1)
        return (time_to_minutes(end) - time_to_minutes(start)) / 60
    try:
        return float(mark)
    except ValueError as exc:
        raise ValueError(f"Unknown schedule mark: {mark}") from exc


def schedule_capacity_hours(rows: list[list[str]]) -> float:
    return sum(mark_hours(mark) for row in rows for mark in row[1:])


def should_increase_demand(row: dict[str, str]) -> bool:
    row_date = date.fromisoformat(row["date"])
    weekday = row_date.weekday()
    team = row["team"]
    work_period = row["workPeriod"]
    minimum = int(row["minimum"])

    if team == "Employees":
        return minimum >= 2 and work_period in EMPLOYEES_PEAK_PERIODS
    if team == "Checkout":
        return work_period == "CHECKOUT_1100_2100" and weekday in {4, 5, 6}
    if team == "Management":
        return work_period in {"MANAGEMENT_1400_1900", "MANAGEMENT_1900_2100"} and weekday in {5, 6}
    if team == "Storage":
        return work_period == "STORAGE_0830_1530" and weekday in {0, 5}
    return False


def expanded_problem(source_problem: dict) -> dict:
    problem = copy.deepcopy(source_problem)
    metadata = problem.setdefault("metadata", {})
    metadata["problemId"] = TARGET_PROBLEM_ID
    metadata["createdAt"] = "2026-05-03T00:00:00Z"
    metadata["description"] = (
        "Expanded Sisqual October benchmark based on "
        f"{SOURCE_PROBLEM_ID}: all original workers and rules are kept, six realistic "
        "workers are added, and demand is raised in targeted peak periods so ILP/CSP "
        "coverage, day-off, skill-priority, and employee-level KPI tradeoffs remain meaningful."
    )
    metadata["source"] = (
        "Generated from data/problems/SISQUAL_COMPLETE using "
        "scripts/create_sisqual_expanded_problem.py"
    )

    problem.setdefault("demand", {}).setdefault("workPeriodModel", "fixed")
    problem.setdefault("scheduleInput", {}).setdefault("markingTypes", {})["Med"] = (
        "Medical reason - unavailable"
    )

    existing_ids = {employee["id"] for employee in problem["employees"]["competency"]}
    for employee in NEW_EMPLOYEES:
        if employee["id"] in existing_ids:
            raise ValueError(f"New employee id already exists: {employee['id']}")
        clean_employee = {key: value for key, value in employee.items() if key != "copyScheduleFrom"}
        problem["employees"]["competency"].append(clean_employee)

    return problem


def expanded_schedule_rows(source_rows: list[list[str]]) -> list[list[str]]:
    rows = [row[:] for row in source_rows]
    by_employee = {row[0]: row for row in source_rows}
    for employee in NEW_EMPLOYEES:
        source_id = employee["copyScheduleFrom"]
        if source_id not in by_employee:
            raise ValueError(f"Schedule pattern source not found: {source_id}")
        copied = by_employee[source_id][:]
        copied[0] = employee["id"]
        rows.append(copied)
    return rows


def expanded_demand_rows(
    source_rows: list[dict[str, str]],
) -> tuple[list[dict[str, str]], Counter[str], int]:
    rows = [row.copy() for row in source_rows]
    changed_by_team: Counter[str] = Counter()
    total_increments = 0

    for row in rows:
        if not should_increase_demand(row):
            continue
        for column in ("minimum", "ideal", "estimated"):
            row[column] = str(int(row[column]) + 1)
        changed_by_team[row["team"]] += 1
        total_increments += 1

    return rows, changed_by_team, total_increments


def assert_unique_employee_ids(problem: dict) -> None:
    employee_ids = [employee["id"] for employee in problem["employees"]["competency"]]
    duplicates = [employee_id for employee_id, count in Counter(employee_ids).items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate employee ids in problem.json: {duplicates}")


def assert_schedule_matches_problem(problem: dict, header: list[str], rows: list[list[str]]) -> None:
    if len(header) != 32:
        raise ValueError(f"Expected employee_id plus 31 date columns, got {len(header)} columns")
    bad_rows = [row[0] for row in rows if len(row) != len(header)]
    if bad_rows:
        raise ValueError(f"Schedule rows with wrong column count: {bad_rows}")

    problem_ids = {employee["id"] for employee in problem["employees"]["competency"]}
    schedule_ids = {row[0] for row in rows}
    if problem_ids != schedule_ids:
        missing = sorted(problem_ids - schedule_ids)
        extra = sorted(schedule_ids - problem_ids)
        raise ValueError(f"Schedule/problem employee mismatch. Missing={missing}, extra={extra}")


def assert_original_schedule_unchanged(
    source_rows: list[list[str]], expanded_rows: list[list[str]]
) -> None:
    expanded_by_employee = {row[0]: row for row in expanded_rows}
    for row in source_rows:
        if expanded_by_employee.get(row[0]) != row:
            raise ValueError(f"Original schedule row changed for employee {row[0]}")


def assert_demand_consistent(rows: list[dict[str, str]]) -> None:
    inconsistent = [
        (row["date"], row["workPeriod"], row["team"])
        for row in rows
        if len({row["minimum"], row["ideal"], row["estimated"]}) != 1
    ]
    if inconsistent:
        raise ValueError(f"Demand rows with inconsistent min/ideal/estimated: {inconsistent[:5]}")


def main() -> None:
    source_problem = read_json(SOURCE_DIR / "problem.json")
    demand_header, source_demand_rows = read_csv_rows(SOURCE_DIR / "demand.csv")
    schedule_header, source_schedule_rows = read_raw_csv(SOURCE_DIR / "schedule_input.csv")

    if source_problem.get("metadata", {}).get("problemId") != SOURCE_PROBLEM_ID:
        raise ValueError("Source problem id does not match the expected Sisqual benchmark")

    problem = expanded_problem(source_problem)
    demand_rows, changed_by_team, total_increments = expanded_demand_rows(source_demand_rows)
    schedule_rows = expanded_schedule_rows(source_schedule_rows)

    assert_unique_employee_ids(problem)
    assert_schedule_matches_problem(problem, schedule_header, schedule_rows)
    assert_original_schedule_unchanged(source_schedule_rows, schedule_rows)
    assert_demand_consistent(demand_rows)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    write_json(TARGET_DIR / "problem.json", problem)
    write_csv_rows(TARGET_DIR / "demand.csv", demand_header, demand_rows)
    write_raw_csv(TARGET_DIR / "schedule_input.csv", schedule_header, schedule_rows)

    durations = work_period_hours(source_problem)
    old_minimum_hours = minimum_worker_hours(source_demand_rows, durations)
    new_minimum_hours = minimum_worker_hours(demand_rows, durations)
    source_employee_count = len(source_problem["employees"]["competency"])
    target_employee_count = len(problem["employees"]["competency"])

    print(f"Generated {TARGET_DIR.relative_to(ROOT)}")
    print(f"Employees: {source_employee_count} -> {target_employee_count}")
    print(f"Schedule capacity hours: {schedule_capacity_hours(source_schedule_rows):.1f} -> {schedule_capacity_hours(schedule_rows):.1f}")
    print(f"Changed demand rows: {total_increments}")
    for team, count in sorted(changed_by_team.items()):
        old_hours = old_minimum_hours.get(team, 0)
        new_hours = new_minimum_hours.get(team, 0)
        print(f"  {team}: {count} rows, minimum worker-hours {old_hours:.1f} -> {new_hours:.1f}")


if __name__ == "__main__":
    main()
