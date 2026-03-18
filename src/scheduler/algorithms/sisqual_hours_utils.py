import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple


OFF_MARKERS = {"DO", "FDO", "VAC", "NOT", "MED"}


@dataclass(frozen=True)
class TimeSlot:
    index: int
    start_min: int
    end_min: int

    @property
    def label(self) -> str:
        return f"{minutes_to_hhmm(self.start_min)}-{minutes_to_hhmm(self.end_min)}"


@dataclass(frozen=True)
class Assignment:
    key: str
    start_min: int
    end_min: int
    slot_indices: Tuple[int, ...]

    @property
    def label(self) -> str:
        return f"{minutes_to_hhmm(self.start_min)}-{minutes_to_hhmm(self.end_min)}"


def load_problem_json(path: Path) -> Dict:
    with path.open() as f:
        return json.load(f)


def parse_contract_hours(problem: Dict) -> Dict[str, int]:
    definitions = problem.get("contracts", {}).get("definitions", [])
    result = {}
    for item in definitions:
        contract_id = str(item.get("id", "")).strip()
        hours = item.get("workHoursPerDay")
        if contract_id and hours is not None:
            result[contract_id] = int(hours)
    return result


def parse_work_periods(problem: Dict) -> Dict[str, Tuple[int, int]]:
    result = {}
    for period in problem.get("demand", {}).get("workPeriods", []):
        code = str(period.get("code", "")).strip()
        time_range = period.get("timeRange", {})
        start = parse_hhmm(str(time_range.get("start", "")))
        end = parse_hhmm(str(time_range.get("end", "")))
        if code:
            result[code] = (start, end)
    return result


def parse_employees(problem: Dict, contract_hours: Dict[str, int]) -> List[Dict]:
    raw_employees = problem.get("employees", {}).get("competency", [])
    employees = []
    for raw in raw_employees:
        employee_id = str(raw.get("id", "")).strip()
        contract_type = str(raw.get("contractType", "")).strip()
        skills = []
        for team in raw.get("teams", []):
            code = str(team.get("code", "")).strip()
            if code:
                skills.append(code)
        employees.append(
            {
                "id": employee_id,
                "name": raw.get("name", employee_id),
                "contract_type": contract_type,
                "contract_hours": contract_hours.get(contract_type),
                "skills": tuple(dict.fromkeys(skills)),
            }
        )
    return employees


def parse_days(problem: Dict) -> List[str]:
    target = problem.get("temporalScope", {}).get("targetPeriod", {})
    start = datetime.strptime(target["start"], "%Y-%m-%d").date()
    end = datetime.strptime(target["end"], "%Y-%m-%d").date()
    days = []
    current = start
    while current <= end:
        days.append(current.isoformat())
        current += timedelta(days=1)
    return days


def parse_schedule_input(base_dir: Path, problem: Dict, days: List[str]) -> Dict[str, Dict[str, str]]:
    schedule_path = base_dir / problem.get("scheduleInput", {}).get("dataFile", "schedule_input.csv")
    with schedule_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = {}
        for row in reader:
            employee_id = str(row.get("employee_id", "")).strip()
            rows[employee_id] = {day: str(row.get(day, "")).strip() for day in days}
    return rows


def parse_skill_codes(problem: Dict) -> List[str]:
    teams = problem.get("demand", {}).get("organizationalUnits", {}).get("teams", [])
    codes = []
    for item in teams:
        if isinstance(item, dict):
            code = item.get("code")
        else:
            code = item
        if code:
            codes.append(str(code).strip())
    return list(dict.fromkeys(codes))


def build_half_hour_slots(work_periods: Dict[str, Tuple[int, int]]) -> List[TimeSlot]:
    if not work_periods:
        raise ValueError("No work periods defined in problem.json")
    min_start = min(start for start, _ in work_periods.values())
    max_end = max(end for _, end in work_periods.values())
    slots = []
    idx = 0
    current = min_start
    while current < max_end:
        slots.append(TimeSlot(index=idx, start_min=current, end_min=current + 30))
        idx += 1
        current += 30
    return slots


def build_period_slot_map(work_periods: Dict[str, Tuple[int, int]], time_slots: List[TimeSlot]) -> Dict[str, Tuple[int, ...]]:
    result = {}
    for code, (start_min, end_min) in work_periods.items():
        covered = []
        for slot in time_slots:
            if slot.start_min >= start_min and slot.end_min <= end_min:
                covered.append(slot.index)
        result[code] = tuple(covered)
    return result


def parse_demand_minimums(base_dir: Path, problem: Dict, coverage_by_period: Dict[str, Tuple[int, ...]]) -> Dict[Tuple[str, int, str], int]:
    demand_path = base_dir / problem.get("demand", {}).get("dataFile", "demand.csv")
    alpha = defaultdict(int)
    with demand_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            date_str = str(row.get("date", "")).strip()
            period_code = str(row.get("workPeriod", "")).strip()
            skill = str(row.get("team", "")).strip()
            minimum_text = str(row.get("minimum", "")).strip()
            if not date_str or not period_code or not skill or not minimum_text:
                continue
            minimum = int(minimum_text)
            for slot_idx in coverage_by_period.get(period_code, ()):
                alpha[(date_str, slot_idx, skill)] += minimum
    return dict(alpha)


def build_assignments(
    employees: List[Dict],
    days: List[str],
    schedule_markers: Dict[str, Dict[str, str]],
    time_slots: List[TimeSlot],
) -> Dict[Tuple[str, str], List[Assignment]]:
    assignments = {}
    first_slot_start = time_slots[0].start_min
    last_slot_end = time_slots[-1].end_min
    num_slots = len(time_slots)

    for employee in employees:
        employee_id = employee["id"]
        for day in days:
            marker = schedule_markers.get(employee_id, {}).get(day, "")
            normalized = normalize_marker(marker)
            key = (employee_id, day)
            day_assignments = []

            if normalized in OFF_MARKERS or not normalized:
                assignments[key] = day_assignments
                continue

            if normalized.startswith("EQUALS:"):
                time_range = normalized.split(":", 1)[1]
                start_text, end_text = time_range.split("-", 1)
                start_min = parse_hhmm(start_text)
                end_min = parse_hhmm(end_text)
                slot_indices = tuple(
                    slot.index
                    for slot in time_slots
                    if slot.start_min >= start_min and slot.end_min <= end_min
                )
                if not slot_indices:
                    raise ValueError(f"No slots found for exact marker '{marker}' on {employee_id} {day}")
                day_assignments.append(
                    Assignment(
                        key=f"{employee_id}_{day}_exact_{start_min}_{end_min}",
                        start_min=start_min,
                        end_min=end_min,
                        slot_indices=slot_indices,
                    )
                )
                assignments[key] = day_assignments
                continue

            if not normalized.isdigit():
                raise ValueError(f"Unsupported schedule marker '{marker}' for {employee_id} on {day}")

            hours = int(normalized)
            required_slots = hours * 2
            if required_slots <= 0:
                assignments[key] = day_assignments
                continue
            for start_idx in range(0, num_slots - required_slots + 1):
                covered = tuple(range(start_idx, start_idx + required_slots))
                start_min = time_slots[start_idx].start_min
                end_min = time_slots[start_idx + required_slots - 1].end_min
                if start_min < first_slot_start or end_min > last_slot_end:
                    continue
                day_assignments.append(
                    Assignment(
                        key=f"{employee_id}_{day}_{start_idx}_{required_slots}",
                        start_min=start_min,
                        end_min=end_min,
                        slot_indices=covered,
                    )
                )
            if not day_assignments:
                raise ValueError(f"No feasible assignments generated for {employee_id} on {day} with marker '{marker}'")
            assignments[key] = day_assignments
    return assignments


def parse_hhmm(value: str) -> int:
    hour, minute = value.strip().split(":", 1)
    return int(hour) * 60 + int(minute)


def minutes_to_hhmm(value: int) -> str:
    hour = value // 60
    minute = value % 60
    return f"{hour:02d}:{minute:02d}"


def normalize_marker(value: str) -> str:
    text = str(value or "").strip()
    if text.upper().startswith("EQUALS:"):
        return "EQUALS:" + text.split(":", 1)[1]
    return text.upper()


def parse_max_time_seconds(value) -> int | None:
    if value is None or value == "":
        return None
    try:
        minutes = float(value)
    except (TypeError, ValueError):
        return None
    if minutes <= 0:
        return None
    return int(minutes * 60)
