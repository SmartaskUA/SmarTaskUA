"""
Hour-based ILP for the Sisqual bundle.

This solver implements the first mathematical model from
`MathematicalDefinition4.docx` for the current bundle format:
  - choose one daily assignment per employee/day when the template says they work
  - assign one skill/team to each covered half-hour slot
  - minimize shortage against the demand minimums

The bundle is work-period based, but the model itself runs on a 30-minute grid
so long work periods and exact-time requirements can be expressed uniformly.
"""

import argparse
import csv
from pathlib import Path
from typing import Dict, List

import pulp

from algorithms.sisqual_hours_utils import (
    OFF_MARKERS,
    build_assignments,
    build_half_hour_slots,
    build_period_slot_map,
    load_problem_json,
    minutes_to_hhmm,
    normalize_marker,
    parse_contract_hours,
    parse_days,
    parse_demand_minimums,
    parse_employees,
    parse_max_time_seconds,
    parse_schedule_input,
    parse_skill_codes,
    parse_work_periods,
)


class SisqualProblem1ILP:
    """Hour-based ILP for the sisqual bundle using the first model from MathematicalDefinition4."""

    def __init__(self, problem_json_path: str, max_time_minutes=None):
        self.staff_team_code = "Employees"
        self.problem_json_path = Path(problem_json_path).resolve()
        self.base_dir = self.problem_json_path.parent
        self.problem = load_problem_json(self.problem_json_path)
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)
        self.min_rest_hours = self._parse_min_rest_hours()

        self.contract_hours = parse_contract_hours(self.problem)  # {"fullTime_8h": 8, "partTime_4h": 4, ...}
        self.work_periods = parse_work_periods(self.problem)  # {"CHECKOUT_1100_2100": (660, 1260), ...}
        self.employees = parse_employees(self.problem, self.contract_hours)  # [{"id": "20067009", "skills": (...), ...}, ...]
        for employee in self.employees:
            employee["assignable_skills"] = tuple(
                skill for skill in employee["skills"] if skill != self.staff_team_code
            )  # "Employees" is staff-level coverage, not an assignable task team.
        self.days = parse_days(self.problem)  # ["2025-10-01", "2025-10-02", ...]
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.days)  # {"20056459": {"2025-10-07": "EQUALS:10:00-14:00", ...}, ...}
        self.skills = parse_skill_codes(self.problem)  # ["Storage", "Checkout", "Management", "Employees"]
        self.time_slots = build_half_hour_slots(self.work_periods)  # 08:30-09:00, 09:00-09:30, ...
        self.coverage_by_period = build_period_slot_map(self.work_periods, self.time_slots)  # {"STORAGE_0830_1530": (0, 1, 2, ..., 13), ...}
        self.alpha = parse_demand_minimums(self.base_dir, self.problem, self.coverage_by_period)  # minimum demand by (day, slot, skill), e.g. ("2025-10-01", 3, "Storage") -> 1
        self.assignments = build_assignments(self.employees, self.days, self.schedule_markers, self.time_slots)  # feasible daily blocks; marker "4" means every 4h contiguous block on the half-hour grid

        self.model = None
        self.x = {}
        self.y = {}
        self.shortage = {}
        self.status = None
        self.objective_value = None

    def _parse_min_rest_hours(self) -> float:
        constraints = self.problem.get("constraints", {}).get("hard", [])
        for constraint in constraints:
            if constraint.get("type") != "min_rest_hours" or not constraint.get("enabled", True):
                continue
            hours = constraint.get("params", {}).get("hours")
            if isinstance(hours, (int, float)):
                return float(hours)
        return 11.0

    def build_model(self):
        model = pulp.LpProblem("SisqualProblem1HourlyILP", pulp.LpMinimize)

        # For every employee, every day, and every feasible daily block, create one binary
        # variable that says whether that whole assignment was chosen.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                for assignment in self.assignments[(employee_id, day)]:
                    self.x[(employee_id, day, assignment.key)] = pulp.LpVariable(
                        f"x_{employee_id}_{day.replace('-', '')}_{assignment.key.split('_')[-2]}_{assignment.key.split('_')[-1]}",
                        cat="Binary",
                    )

        # For every employee/day/slot/allowed-skill combination, create the slot-level skill
        # assignment variable used to decide what the employee is doing in each half-hour.
        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["assignable_skills"]  # y_{w,d,t,s} only exists for real task teams; "Employees" is aggregate staff coverage.
            for day in self.days:
                if not self.assignments[(employee_id, day)]:
                    continue
                for slot in self.time_slots:
                    for skill in skills:
                        self.y[(employee_id, day, slot.index, skill)] = pulp.LpVariable(
                            f"y_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}",
                            cat="Binary",
                        )

        # For every demanded (day, slot, skill) tuple, create the shortage variable that will
        # absorb unmet coverage.
        for (day, slot_idx, skill), minimum in self.alpha.items():
            self.shortage[(day, slot_idx, skill)] = pulp.LpVariable(
                f"z_{day.replace('-', '')}_{slot_idx}_{skill}",  # z_{d,t,s}: uncovered demand for skill s at slot t on day d.
                lowBound=0,
                cat="Integer",
            )

        # Constraint (2)
        # "each worker w∈W can be assigned on each day d∈D with at most one
        # working daily assignment h∈Hwd."
        # The bundle's fixed day markers tighten this to exactly one assignment on
        # work days and zero assignments on off/unavailable days.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                marker = normalize_marker(self.schedule_markers[employee_id][day])
                x_vars = [self.x[(employee_id, day, assignment.key)] for assignment in self.assignments[(employee_id, day)]]
                if marker in OFF_MARKERS or not marker:
                    if x_vars:
                        model += pulp.lpSum(x_vars) == 0, f"off_{employee_id}_{day}"  # (2) Off / unavailable days cannot receive an assignment.
                else:
                    model += pulp.lpSum(x_vars) == 1, f"work_{employee_id}_{day}"  # (2) Work days must choose exactly one candidate assignment.

        # Constraint (3)
        # "each worker w∈W assigned on day d∈D with a working daily assignment
        # h∈Hwd that covers timeslot t∈Td must be assigned in timeslot t with
        # one of its skills Sw."
        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["assignable_skills"]
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
                    model += pulp.lpSum(lhs_terms) == pulp.lpSum(rhs_terms), f"skill_cover_{employee_id}_{day}_{slot.index}"  # (3) Covered slots get exactly one skill; uncovered slots get none.

        # Constraint (4)
        # "each worker w∈W cannot be assigned with more than 5 working days in
        # any set of 6 consecutive days."
        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.days) - 5):
                window = self.days[start:start + 6]
                model += (
                    pulp.lpSum(
                        self.x[(employee_id, day, assignment.key)]
                        for day in window
                        for assignment in self.assignments[(employee_id, day)]
                    ) <= 5,  # (4) No more than 5 worked days in any 6-day window.
                    f"max5in6_{employee_id}_{start}",
                )

        # Extra constraint
        # forbid consecutive-day assignment pairs whose overnight rest is below
        # the configured minimum rest hours in problem.json.
        for employee in self.employees:
            employee_id = employee["id"]
            for day, next_day in zip(self.days, self.days[1:]):
                today_assignments = self.assignments[(employee_id, day)]
                next_day_assignments = self.assignments[(employee_id, next_day)]
                if not today_assignments or not next_day_assignments:
                    continue
                for today_assignment in today_assignments:
                    for next_assignment in next_day_assignments:
                        rest_hours = ((24 * 60 - today_assignment.end_min) + next_assignment.start_min) / 60.0
                        if rest_hours < self.min_rest_hours:
                            model += (
                                self.x[(employee_id, day, today_assignment.key)]
                                + self.x[(employee_id, next_day, next_assignment.key)]
                                <= 1,
                                f"min_rest_{employee_id}_{day.replace('-', '')}_{today_assignment.key}_{next_day.replace('-', '')}_{next_assignment.key}",
                            )

        # Constraint (5)
        # "the value of variable z_dts is at least the number of workers below
        # the required value α_dts for each day d∈D, each timeslot t∈Td and
        # each skill s∈S."
        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = []
            if skill == self.staff_team_code:
                # Staff-level demand counts any employee who is present in that slot, regardless
                # of the operational team they are assigned to.
                for employee in self.employees:
                    employee_id = employee["id"]
                    for assignment in self.assignments[(employee_id, day)]:
                        if slot_idx in assignment.slot_indices:
                            coverage_terms.append(self.x[(employee_id, day, assignment.key)])
            else:
                for employee in self.employees:
                    employee_id = employee["id"]
                    y_key = (employee_id, day, slot_idx, skill)
                    if skill in employee["assignable_skills"] and y_key in self.y:
                        coverage_terms.append(self.y[y_key])
            model += self.shortage[(day, slot_idx, skill)] + pulp.lpSum(coverage_terms) >= minimum, f"shortage_{day}_{slot_idx}_{skill}"  # (5) Shortage absorbs unmet slot demand.

        # Objective (1) from MathematicalDefinition4.docx:
        # minimize the sum of workers below the required value for all days,
        # timeslots, and skills.
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
        # Rebuild the final CSV one employee row at a time, preserving the original day markers
        # for non-working days and decoding x/y back into readable time@skill segments.
        for employee in self.employees:
            employee_id = employee["id"]
            row = [employee_id]
            for day in self.days:
                marker = self.schedule_markers[employee_id][day]
                normalized = normalize_marker(marker)
                if normalized in OFF_MARKERS or not normalized:
                    row.append(marker or "OFF")  # Preserve the original non-working marker in the exported schedule.
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
                # Walk the chosen half-hour slots in order and merge adjacent slots with the
                # same skill into one exported segment.
                for slot_idx in chosen.slot_indices:
                    slot = self.time_slots[slot_idx]
                    assigned_skill = None
                    for skill in employee["assignable_skills"]:
                        value = pulp.value(self.y.get((employee_id, day, slot_idx, skill)))
                        if value is not None and value > 0.5:
                            assigned_skill = skill
                            break
                    if assigned_skill is None:
                        if employee["assignable_skills"]:
                            assigned_skill = employee["assignable_skills"][0]
                        else:
                            assigned_skill = self.staff_team_code
                    if current_skill == assigned_skill:
                        current_end = slot.end_min  # Merge consecutive slots with the same chosen skill into one readable segment.
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

def solve(problem_path=None, maxTime=None, **kwargs):
    if not problem_path:
        raise ValueError("This solver requires 'problem_path' pointing to problem.json")
    # TaskManager uses this thin wrapper so the algorithm matches the common scheduler API.
    scheduler = SisqualProblem1ILP(problem_path, max_time_minutes=maxTime)
    scheduler.build_model()
    scheduler.solve()
    rows = scheduler.build_output_rows()

    return rows
