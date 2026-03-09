import argparse
import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import pulp


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


class SisqualProblem1ILP:
    """Hour-based ILP for the sisqual bundle using the first model from MathematicalDefinition4."""

    def __init__(self, problem_json_path: str, max_time_minutes=None):
        self.problem_json_path = Path(problem_json_path).resolve()
        self.base_dir = self.problem_json_path.parent
        self.problem = self._load_json(self.problem_json_path)
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)

        self.contract_hours = self._parse_contract_hours()
        self.work_periods = self._parse_work_periods()
        self.employees = self._parse_employees()
        self.days = self._parse_days()
        self.schedule_markers = self._parse_schedule_input()
        self.skills = self._parse_skill_codes()
        self.time_slots = self._build_half_hour_slots()
        self.coverage_by_period = self._build_period_slot_map()
        self.alpha = self._parse_demand_minimums()
        self.assignments = self._build_assignments()

        self.model = None
        self.x = {}
        self.y = {}
        self.shortage = {}
        self.status = None
        self.objective_value = None

    def _load_json(self, path: Path) -> Dict:
        with path.open() as f:
            return json.load(f)

    def _parse_contract_hours(self) -> Dict[str, int]:
        definitions = self.problem.get("contracts", {}).get("definitions", [])
        result = {}
        for item in definitions:
            contract_id = str(item.get("id", "")).strip()
            hours = item.get("workHoursPerDay")
            if contract_id and hours is not None:
                result[contract_id] = int(hours)
        return result

    def _parse_work_periods(self) -> Dict[str, Tuple[int, int]]:
        result = {}
        for period in self.problem.get("demand", {}).get("workPeriods", []):
            code = str(period.get("code", "")).strip()
            time_range = period.get("timeRange", {})
            start = parse_hhmm(str(time_range.get("start", "")))
            end = parse_hhmm(str(time_range.get("end", "")))
            if code:
                result[code] = (start, end)
        return result

    def _parse_employees(self) -> List[Dict]:
        raw_employees = self.problem.get("employees", {}).get("competency", [])
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
                    "contract_hours": self.contract_hours.get(contract_type),
                    "skills": tuple(dict.fromkeys(skills)),
                }
            )
        return employees

    def _parse_days(self) -> List[str]:
        target = self.problem.get("temporalScope", {}).get("targetPeriod", {})
        start = datetime.strptime(target["start"], "%Y-%m-%d").date()
        end = datetime.strptime(target["end"], "%Y-%m-%d").date()
        days = []
        current = start
        while current <= end:
            days.append(current.isoformat())
            current += timedelta(days=1)
        return days

    def _parse_schedule_input(self) -> Dict[str, Dict[str, str]]:
        schedule_path = self.base_dir / self.problem.get("scheduleInput", {}).get("dataFile", "schedule_input.csv")
        with schedule_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = {}
            for row in reader:
                employee_id = str(row.get("employee_id", "")).strip()
                rows[employee_id] = {day: str(row.get(day, "")).strip() for day in self.days}
        return rows

    def _parse_skill_codes(self) -> List[str]:
        teams = self.problem.get("demand", {}).get("organizationalUnits", {}).get("teams", [])
        codes = []
        for item in teams:
            if isinstance(item, dict):
                code = item.get("code")
            else:
                code = item
            if code:
                codes.append(str(code).strip())
        return list(dict.fromkeys(codes))

    def _build_half_hour_slots(self) -> List[TimeSlot]:
        if not self.work_periods:
            raise ValueError("No work periods defined in problem.json")
        min_start = min(start for start, _ in self.work_periods.values())
        max_end = max(end for _, end in self.work_periods.values())
        slots = []
        idx = 0
        current = min_start
        while current < max_end:
            slots.append(TimeSlot(index=idx, start_min=current, end_min=current + 30))
            idx += 1
            current += 30
        return slots

    def _build_period_slot_map(self) -> Dict[str, Tuple[int, ...]]:
        result = {}
        for code, (start_min, end_min) in self.work_periods.items():
            covered = []
            for slot in self.time_slots:
                if slot.start_min >= start_min and slot.end_min <= end_min:
                    covered.append(slot.index)
            result[code] = tuple(covered)
        return result

    def _parse_demand_minimums(self) -> Dict[Tuple[str, int, str], int]:
        demand_path = self.base_dir / self.problem.get("demand", {}).get("dataFile", "demand.csv")
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
                for slot_idx in self.coverage_by_period.get(period_code, ()):
                    alpha[(date_str, slot_idx, skill)] += minimum
        return dict(alpha)

    def _build_assignments(self) -> Dict[Tuple[str, str], List[Assignment]]:
        assignments = {}
        first_slot_start = self.time_slots[0].start_min
        last_slot_end = self.time_slots[-1].end_min
        num_slots = len(self.time_slots)

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                marker = self.schedule_markers.get(employee_id, {}).get(day, "")
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
                        for slot in self.time_slots
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
                    start_min = self.time_slots[start_idx].start_min
                    end_min = self.time_slots[start_idx + required_slots - 1].end_min
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

    def build_model(self):
        model = pulp.LpProblem("SisqualProblem1HourlyILP", pulp.LpMinimize)

        # x_{w,d,h}
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                for assignment in self.assignments[(employee_id, day)]:
                    self.x[(employee_id, day, assignment.key)] = pulp.LpVariable(
                        f"x_{employee_id}_{day.replace('-', '')}_{assignment.key.split('_')[-2]}_{assignment.key.split('_')[-1]}",
                        cat="Binary",
                    )

        # y_{w,d,t,s}
        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["skills"]
            for day in self.days:
                if not self.assignments[(employee_id, day)]:
                    continue
                for slot in self.time_slots:
                    for skill in skills:
                        self.y[(employee_id, day, slot.index, skill)] = pulp.LpVariable(
                            f"y_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}",
                            cat="Binary",
                        )

        # z_{d,t,s}
        for (day, slot_idx, skill), minimum in self.alpha.items():
            self.shortage[(day, slot_idx, skill)] = pulp.LpVariable(
                f"z_{day.replace('-', '')}_{slot_idx}_{skill}",
                lowBound=0,
                cat="Integer",
            )

        # (2) Fixed day template: exactly one assignment on work days, none otherwise.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                marker = normalize_marker(self.schedule_markers[employee_id][day])
                x_vars = [self.x[(employee_id, day, assignment.key)] for assignment in self.assignments[(employee_id, day)]]
                if marker in OFF_MARKERS or not marker:
                    if x_vars:
                        model += pulp.lpSum(x_vars) == 0, f"off_{employee_id}_{day}"
                else:
                    model += pulp.lpSum(x_vars) == 1, f"work_{employee_id}_{day}"

        # (3) Assign exactly one skill to every covered timeslot of the selected daily assignment.
        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["skills"]
            assignment_list = {
                day: self.assignments[(employee_id, day)]
                for day in self.days
            }
            for day in self.days:
                if not assignment_list[day]:
                    continue
                for slot in self.time_slots:
                    rhs_terms = []
                    for assignment in assignment_list[day]:
                        if slot.index in assignment.slot_indices:
                            rhs_terms.append(self.x[(employee_id, day, assignment.key)])
                    lhs_terms = [self.y[(employee_id, day, slot.index, skill)] for skill in skills]
                    model += pulp.lpSum(lhs_terms) == pulp.lpSum(rhs_terms), f"skill_cover_{employee_id}_{day}_{slot.index}"

        # (4) No more than 5 work days in any 6 consecutive days.
        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.days) - 5):
                window = self.days[start:start + 6]
                model += (
                    pulp.lpSum(
                        self.x[(employee_id, day, assignment.key)]
                        for day in window
                        for assignment in self.assignments[(employee_id, day)]
                    ) <= 5,
                    f"max5in6_{employee_id}_{start}",
                )

        # (5) Shortage definition.
        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = []
            for employee in self.employees:
                employee_id = employee["id"]
                y_key = (employee_id, day, slot_idx, skill)
                if skill in employee["skills"] and y_key in self.y:
                    coverage_terms.append(self.y[y_key])
            model += self.shortage[(day, slot_idx, skill)] + pulp.lpSum(coverage_terms) >= minimum, f"shortage_{day}_{slot_idx}_{skill}"

        model += pulp.lpSum(self.shortage.values()), "minimize_total_shortage"
        self.model = model

    def solve(self, gap_rel: float = 0.01):
        if self.model is None:
            self.build_model()
        solver = pulp.PULP_CBC_CMD(
            msg=1,
            timeLimit=self.max_time_seconds,
            gapRel=gap_rel,
        )
        self.status = self.model.solve(solver)
        self.objective_value = pulp.value(self.model.objective)
        return self.status

    def solution_status(self) -> str:
        return pulp.LpStatus.get(self.status, "Unknown")

    def build_output_rows(self) -> List[List[str]]:
        rows = [["employee_id", *self.days]]
        for employee in self.employees:
            employee_id = employee["id"]
            row = [employee_id]
            for day in self.days:
                marker = self.schedule_markers[employee_id][day]
                normalized = normalize_marker(marker)
                if normalized in OFF_MARKERS or not normalized:
                    row.append(marker or "OFF")
                    continue
                chosen = None
                for assignment in self.assignments[(employee_id, day)]:
                    value = pulp.value(self.x.get((employee_id, day, assignment.key)))
                    if value is not None and value > 0.5:
                        chosen = assignment
                        break
                if chosen is None:
                    row.append("UNASSIGNED")
                    continue
                segments = []
                current_skill = None
                current_start = None
                current_end = None
                for slot_idx in chosen.slot_indices:
                    slot = self.time_slots[slot_idx]
                    assigned_skill = None
                    for skill in employee["skills"]:
                        value = pulp.value(self.y.get((employee_id, day, slot_idx, skill)))
                        if value is not None and value > 0.5:
                            assigned_skill = skill
                            break
                    if assigned_skill is None:
                        assigned_skill = employee["skills"][0]
                    if current_skill == assigned_skill:
                        current_end = slot.end_min
                    else:
                        if current_skill is not None:
                            segments.append(f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}")
                        current_skill = assigned_skill
                        current_start = slot.start_min
                        current_end = slot.end_min
                if current_skill is not None:
                    segments.append(f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}")
                row.append(" | ".join(segments) if segments else chosen.label)
            rows.append(row)
        return rows

    def export_csv(self, output_path: str):
        rows = self.build_output_rows()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerows(rows)

    def shortage_summary(self) -> Dict[str, int]:
        summary = defaultdict(int)
        for (day, slot_idx, skill), var in self.shortage.items():
            value = pulp.value(var)
            if value:
                summary[skill] += int(round(value))
        return dict(summary)


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


def solve(problem_path=None, maxTime=None, **kwargs):
    if not problem_path:
        raise ValueError("This solver requires 'problem_path' pointing to problem.json")
    scheduler = SisqualProblem1ILP(problem_path, max_time_minutes=maxTime)
    scheduler.build_model()
    scheduler.solve()
    return scheduler.build_output_rows()


def main():
    parser = argparse.ArgumentParser(description="Solve sisqual_example_2 with the hour-based ILP Problem 1 model.")
    parser.add_argument("problem_json", help="Path to problem.json")
    parser.add_argument("--max-time", dest="max_time", default="10", help="Solver time limit in minutes")
    parser.add_argument("--output", dest="output", default=None, help="Optional output CSV path")
    args = parser.parse_args()

    scheduler = SisqualProblem1ILP(args.problem_json, max_time_minutes=args.max_time)
    scheduler.build_model()
    status = scheduler.solve()
    rows = scheduler.build_output_rows()

    print(f"Status: {pulp.LpStatus.get(status, 'Unknown')}")
    print(f"Objective: {scheduler.objective_value}")
    print(f"Shortage summary: {scheduler.shortage_summary()}")

    if args.output:
        scheduler.export_csv(args.output)
        print(f"Wrote schedule to {args.output}")
    else:
        for row in rows[:5]:
            print(row[:6])


if __name__ == "__main__":
    main()
