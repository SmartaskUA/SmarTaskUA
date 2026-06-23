#!/usr/bin/env python3
"""Generate the SISQUAL_FULL_YEAR_2025 benchmark problem.

The source dataset is the company-provided October 2025 Sisqual problem. Since
only one real month is available, non-October dates are synthesized by copying
the October day with the same weekday, cycling through all matching October
dates to avoid a single repeated template. A deterministic repair pass then
adds synthetic DO days outside October so the generated roster respects the
hard max-5-in-6 consecutive workday rule.
"""

from __future__ import annotations

import copy
import csv
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "problems" / "SISQUAL_OCTOBER_2025"
TARGET_DIR = ROOT / "data" / "problems" / "SISQUAL_FULL_YEAR_2025"

SOURCE_PROBLEM_ID = "SISQUAL_OCTOBER_2025"
TARGET_PROBLEM_ID = "SISQUAL_FULL_YEAR_2025"
YEAR = 2025
YEAR_START = date(YEAR, 1, 1)
YEAR_END = date(YEAR, 12, 31)
OCTOBER_START = date(YEAR, 10, 1)
OCTOBER_END = date(YEAR, 10, 31)
MAX_CONSECUTIVE_WORKDAYS = 5
OFF_MARKERS = {"", "DO", "FDO", "VAC", "NOT", "MED"}


def read_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def write_json(path: Path, data: dict) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)
        file.write("\n")


def read_dict_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def write_dict_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def read_raw_csv(path: Path) -> tuple[list[str], list[list[str]]]:
    with path.open(newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        rows = list(reader)
    if not rows:
        raise ValueError(f"CSV is empty: {path}")
    return rows[0], rows[1:]


def write_raw_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)


def date_range(start: date, end: date) -> list[date]:
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    return days


def normalize_marker(value: str) -> str:
    return value.strip().upper()


def is_october_date(value: str) -> bool:
    current = date.fromisoformat(value)
    return OCTOBER_START <= current <= OCTOBER_END


def is_work_marker(value: str) -> bool:
    return normalize_marker(value) not in OFF_MARKERS


def source_dates_by_weekday(source_dates: list[date]) -> dict[int, list[date]]:
    by_weekday: dict[int, list[date]] = defaultdict(list)
    for source_date in source_dates:
        by_weekday[source_date.weekday()].append(source_date)
    missing = sorted(set(range(7)) - set(by_weekday))
    if missing:
        raise ValueError(f"Source month does not contain all weekdays: {missing}")
    return {weekday: sorted(days) for weekday, days in by_weekday.items()}


def build_full_year_mapping(source_dates: list[date]) -> dict[str, str]:
    by_weekday = source_dates_by_weekday(source_dates)
    counters: Counter[int] = Counter()
    mapping = {}

    for target_date in date_range(YEAR_START, YEAR_END):
        if OCTOBER_START <= target_date <= OCTOBER_END:
            source_date = target_date
        else:
            weekday = target_date.weekday()
            options = by_weekday[weekday]
            source_date = options[counters[weekday] % len(options)]
            counters[weekday] += 1
        mapping[target_date.isoformat()] = source_date.isoformat()

    return mapping


def full_year_problem(source_problem: dict) -> dict:
    problem = copy.deepcopy(source_problem)
    metadata = problem.setdefault("metadata", {})
    metadata["problemId"] = TARGET_PROBLEM_ID
    metadata["createdAt"] = "2026-06-21T00:00:00Z"
    metadata["description"] = (
        "Full-year Sisqual 2025 benchmark synthesized from the company-provided "
        "October 2025 dataset using weekday-matched demand and schedule templates."
    )
    metadata["source"] = (
        "Generated from data/problems/SISQUAL_OCTOBER_2025 using "
        "scripts/create_sisqual_full_year_problem.py"
    )

    temporal_scope = problem.setdefault("temporalScope", {})
    temporal_scope["year"] = YEAR
    temporal_scope["numDays"] = len(date_range(YEAR_START, YEAR_END))
    temporal_scope["targetPeriod"] = {
        "start": YEAR_START.isoformat(),
        "end": YEAR_END.isoformat(),
        "includeBufferWeeks": False,
    }

    problem.setdefault("demand", {})["dataFile"] = "demand.csv"
    problem.setdefault("scheduleInput", {})["dataFile"] = "schedule_input.csv"
    return problem


def full_year_demand_rows(
    source_rows: list[dict[str, str]],
    date_mapping: dict[str, str],
) -> list[dict[str, str]]:
    rows_by_date: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in source_rows:
        rows_by_date[row["date"]].append(row)

    result = []
    for target_date in date_mapping:
        source_date = date_mapping[target_date]
        source_day_rows = rows_by_date.get(source_date, [])
        if not source_day_rows:
            raise ValueError(f"No source demand rows for mapped source date {source_date}")
        for source_row in source_day_rows:
            new_row = source_row.copy()
            new_row["date"] = target_date
            result.append(new_row)
    return result


def full_year_schedule_rows(
    source_header: list[str],
    source_rows: list[list[str]],
    date_mapping: dict[str, str],
) -> tuple[list[str], list[list[str]]]:
    source_dates = source_header[1:]
    source_date_to_index = {day: index for index, day in enumerate(source_dates, start=1)}
    target_dates = list(date_mapping.keys())
    target_header = ["employee_id", *target_dates]
    target_rows = []

    for source_row in source_rows:
        if len(source_row) != len(source_header):
            raise ValueError(f"Source schedule row has wrong column count: {source_row[0]}")
        target_row = [source_row[0]]
        for target_date in target_dates:
            source_date = date_mapping[target_date]
            try:
                source_index = source_date_to_index[source_date]
            except KeyError as exc:
                raise ValueError(f"Mapped source date missing from schedule header: {source_date}") from exc
            target_row.append(source_row[source_index])
        target_rows.append(target_row)

    return target_header, target_rows


def repair_max_consecutive_workdays(
    header: list[str],
    rows: list[list[str]],
) -> list[tuple[str, str, str]]:
    """Convert synthetic work days to DO when an employee exceeds max streak.

    October 2025 is the real company-provided month and is never modified. All
    repairs are made outside October and are deterministic: the current 6th
    synthetic workday is changed to DO whenever possible.
    """

    repairs = []
    date_columns = header[1:]

    for row in rows:
        employee_id = row[0]
        streak_indices: list[int] = []

        for column_index, day in enumerate(date_columns, start=1):
            if is_work_marker(row[column_index]):
                streak_indices.append(column_index)
            else:
                streak_indices = []
                continue

            if len(streak_indices) <= MAX_CONSECUTIVE_WORKDAYS:
                continue

            repair_index = None
            if not is_october_date(day):
                repair_index = column_index
            else:
                for candidate_index in reversed(streak_indices):
                    candidate_day = header[candidate_index]
                    if not is_october_date(candidate_day):
                        repair_index = candidate_index
                        break

            if repair_index is None:
                streak_days = [header[index] for index in streak_indices]
                raise ValueError(
                    "Source October schedule violates max consecutive workdays "
                    f"for {employee_id}: {streak_days}"
                )

            previous_marker = row[repair_index]
            row[repair_index] = "DO"
            repairs.append((employee_id, header[repair_index], previous_marker))
            streak_indices = [
                index
                for index in streak_indices
                if index > repair_index and is_work_marker(row[index])
            ]

    return repairs


def validate_max_consecutive_workdays(header: list[str], rows: list[list[str]]) -> None:
    for row in rows:
        employee_id = row[0]
        streak = []
        for column_index, day in enumerate(header[1:], start=1):
            if is_work_marker(row[column_index]):
                streak.append(day)
            else:
                streak = []
            if len(streak) > MAX_CONSECUTIVE_WORKDAYS:
                raise ValueError(
                    f"{employee_id} has {len(streak)} consecutive workdays ending on {day}: "
                    f"{streak}"
                )


def validate_problem(problem: dict) -> None:
    metadata = problem.get("metadata", {})
    if metadata.get("problemId") != TARGET_PROBLEM_ID:
        raise ValueError("Generated problem id does not match target id")

    target = problem.get("temporalScope", {}).get("targetPeriod", {})
    if target.get("start") != YEAR_START.isoformat() or target.get("end") != YEAR_END.isoformat():
        raise ValueError("Generated temporalScope targetPeriod is not full-year 2025")
    if problem.get("temporalScope", {}).get("numDays") != 365:
        raise ValueError("Generated temporalScope numDays must be 365")


def validate_demand(rows: list[dict[str, str]]) -> None:
    target_days = {day.isoformat() for day in date_range(YEAR_START, YEAR_END)}
    row_days = {row["date"] for row in rows}
    outside = sorted(row_days - target_days)
    missing = sorted(target_days - row_days)
    if outside:
        raise ValueError(f"Demand contains dates outside 2025: {outside[:5]}")
    if missing:
        raise ValueError(f"Demand is missing dates: {missing[:5]}")

    bad_rows = [
        (row.get("date"), row.get("workPeriod"), row.get("team"))
        for row in rows
        if not row.get("date") or not row.get("workPeriod") or not row.get("team")
    ]
    if bad_rows:
        raise ValueError(f"Demand rows with missing required fields: {bad_rows[:5]}")


def validate_schedule(problem: dict, header: list[str], rows: list[list[str]]) -> None:
    expected_dates = [day.isoformat() for day in date_range(YEAR_START, YEAR_END)]
    if header != ["employee_id", *expected_dates]:
        raise ValueError("Schedule header does not contain exactly employee_id plus all 365 dates")

    bad_rows = [row[0] for row in rows if len(row) != len(header)]
    if bad_rows:
        raise ValueError(f"Schedule rows with wrong column count: {bad_rows[:5]}")

    problem_ids = {employee["id"] for employee in problem["employees"]["competency"]}
    schedule_ids = {row[0] for row in rows}
    if problem_ids != schedule_ids:
        missing = sorted(problem_ids - schedule_ids)
        extra = sorted(schedule_ids - problem_ids)
        raise ValueError(f"Schedule/problem employee mismatch. Missing={missing}, extra={extra}")

    validate_max_consecutive_workdays(header, rows)


def main() -> None:
    source_problem = read_json(SOURCE_DIR / "problem.json")
    if source_problem.get("metadata", {}).get("problemId") != SOURCE_PROBLEM_ID:
        raise ValueError("Source problem id does not match the expected company dataset")

    demand_header, source_demand_rows = read_dict_csv(SOURCE_DIR / "demand.csv")
    schedule_header, source_schedule_rows = read_raw_csv(SOURCE_DIR / "schedule_input.csv")
    source_dates = [date.fromisoformat(day) for day in schedule_header[1:]]

    if min(source_dates) != OCTOBER_START or max(source_dates) != OCTOBER_END:
        raise ValueError("Source schedule must cover exactly October 2025")

    date_mapping = build_full_year_mapping(source_dates)
    problem = full_year_problem(source_problem)
    demand_rows = full_year_demand_rows(source_demand_rows, date_mapping)
    schedule_header_out, schedule_rows = full_year_schedule_rows(
        schedule_header,
        source_schedule_rows,
        date_mapping,
    )
    repairs = repair_max_consecutive_workdays(schedule_header_out, schedule_rows)

    validate_problem(problem)
    validate_demand(demand_rows)
    validate_schedule(problem, schedule_header_out, schedule_rows)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    write_json(TARGET_DIR / "problem.json", problem)
    write_dict_csv(TARGET_DIR / "demand.csv", demand_header, demand_rows)
    write_raw_csv(TARGET_DIR / "schedule_input.csv", schedule_header_out, schedule_rows)

    print(f"Generated {TARGET_DIR.relative_to(ROOT)}")
    print(f"Days: {len(date_mapping)}")
    print(f"Demand rows: {len(source_demand_rows)} -> {len(demand_rows)}")
    print(f"Employees: {len(schedule_rows)}")
    print(f"Synthetic DO repairs: {len(repairs)}")
    print("Recommended execution: solve monthly subproblems, not full-year monolithic ILP/CSP.")


if __name__ == "__main__":
    main()
