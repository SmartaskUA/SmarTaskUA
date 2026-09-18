"""
Hour-based CP-SAT model for the Sisqual bundle.

This mirrors `ILP_Sisqual_Hours.py` on the same half-hour assignment model:
  - choose one daily assignment per employee/day when the template says they work
  - assign one skill/team to each covered half-hour slot
  - minimize shortage against the demand minimums
"""

import argparse
import csv
from pathlib import Path
from typing import List

from ortools.sat.python import cp_model
from ortools.sat.python.cp_model import LinearExpr

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


class SisqualProblem1CSP:
    """Hour-based CP-SAT solver for the sisqual bundle using the first model."""

    def __init__(self, problem_json_path: str, max_time_minutes=None):
        self.staff_team_code = "Employees"
        self.problem_json_path = Path(problem_json_path).resolve()
        self.base_dir = self.problem_json_path.parent
        self.problem = load_problem_json(self.problem_json_path)
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)
        self.min_rest_hours = self._parse_min_rest_hours()

        self.contract_hours = parse_contract_hours(self.problem)
        self.work_periods = parse_work_periods(self.problem)
        self.employees = parse_employees(self.problem, self.contract_hours)
        for employee in self.employees:
            employee["assignable_skills"] = tuple(
                skill for skill in employee["skills"] if skill != self.staff_team_code
            )
        self.days = parse_days(self.problem)
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.days)
        self.skills = parse_skill_codes(self.problem)
        self.time_slots = build_half_hour_slots(self.work_periods)
        self.coverage_by_period = build_period_slot_map(self.work_periods, self.time_slots)
        self.alpha = parse_demand_minimums(self.base_dir, self.problem, self.coverage_by_period)
        self.assignments = build_assignments(self.employees, self.days, self.schedule_markers, self.time_slots)

        self.model = cp_model.CpModel()
        self.solver = cp_model.CpSolver()
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

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                for assignment in self.assignments[(employee_id, day)]:
                    self.x[(employee_id, day, assignment.key)] = self.model.NewBoolVar(
                        f"x_{employee_id}_{day.replace('-', '')}_{assignment.key.split('_')[-2]}_{assignment.key.split('_')[-1]}"
                    )

        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["assignable_skills"]
            for day in self.days:
                if not self.assignments[(employee_id, day)]:
                    continue
                for slot in self.time_slots:
                    for skill in skills:
                        self.y[(employee_id, day, slot.index, skill)] = self.model.NewBoolVar(
                            f"y_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}"
                        )

        for (day, slot_idx, skill), minimum in self.alpha.items():
            self.shortage[(day, slot_idx, skill)] = self.model.NewIntVar(
                0,
                len(self.employees),
                f"z_{day.replace('-', '')}_{slot_idx}_{skill}",
            )

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                marker = normalize_marker(self.schedule_markers[employee_id][day])
                x_vars = [self.x[(employee_id, day, assignment.key)] for assignment in self.assignments[(employee_id, day)]]
                if marker in OFF_MARKERS or not marker:
                    self.model.Add(LinearExpr.Sum(x_vars) == 0)
                else:
                    self.model.Add(LinearExpr.Sum(x_vars) == 1)

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
                    if lhs_terms:
                        self.model.Add(
                            cp_model.LinearExpr.Sum(lhs_terms) == cp_model.LinearExpr.Sum(rhs_terms)
                        )
                    else:
                        # ninguém pode trabalhar → força RHS = 0
                        self.model.Add(cp_model.LinearExpr.Sum(rhs_terms) == 0)

        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.days) - 5):
                window = self.days[start:start + 6]
                self.model.Add(
                    LinearExpr.Sum([
                        self.x[(employee_id, day, assignment.key)]
                        for day in window
                        for assignment in self.assignments[(employee_id, day)]
                    ]) <= 5
                )

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
                            self.model.Add(
                                self.x[(employee_id, day, today_assignment.key)]
                                + self.x[(employee_id, next_day, next_assignment.key)]
                                <= 1
                            )

        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = []
            if skill == self.staff_team_code:
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
            if coverage_terms:
                self.model.Add(
                    self.shortage[(day, slot_idx, skill)] +
                    LinearExpr.Sum(coverage_terms)
                    >= minimum
                )
            else:
                self.model.Add(self.shortage[(day, slot_idx, skill)] >= minimum)

        self.model.Minimize(
            LinearExpr.Sum(list(self.shortage.values()))
        )
        self.model = self.model

    def solve(self):
        if self.model is None:
            self.build_model()

        if self.max_time_seconds is not None:
            self.solver.parameters.max_time_in_seconds = float(self.max_time_seconds)
        self.solver.parameters.num_search_workers = 8
        self.solver.parameters.log_search_progress = True
        self.solver.parameters.cp_model_presolve = True
        self.solver.parameters.linearization_level = 2
        self.solver.parameters.search_branching = cp_model.PORTFOLIO_SEARCH

        self.status = self.solver.Solve(self.model)
        self.solver = self.solver
        if self.status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            self.objective_value = self.solver.ObjectiveValue()
        return self.status

    def solution_status(self) -> str:
        status_map = {
            cp_model.OPTIMAL: "Optimal",
            cp_model.FEASIBLE: "Feasible",
            cp_model.INFEASIBLE: "Infeasible",
            cp_model.MODEL_INVALID: "ModelInvalid",
            cp_model.UNKNOWN: "Unknown",
        }
        return status_map.get(self.status, "Unknown")

    def build_output_rows(self) -> List[List[str]]:
        rows = [["employee_id", *self.days]]
        solved = self.solver is not None and self.status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

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
                    var = self.x.get((employee_id, day, assignment.key))
                    if var is not None and self.solver.Value(var) == 1:                   
                        chosen = assignment
                        break

                if chosen is None:
                    row.append("UNASSIGNED")
                    continue

                segments = []
                current_skill = None
                current_start = None
                current_end = None
                for slot_idx in sorted(chosen.slot_indices):
                    slot = self.time_slots[slot_idx]
                    assigned_skill = None
                    for skill in employee["assignable_skills"]:
                        y_var = self.y.get((employee_id, day, slot_idx, skill))
                        if y_var is not None:
                            val = self.solver.Value(y_var)
                            if val is not None and val > 0.5:
                                assigned_skill = skill
                                break
                    if assigned_skill is None:
                        if employee["assignable_skills"]:
                            assigned_skill = employee["assignable_skills"][0]
                        else:
                            assigned_skill = self.staff_team_code
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


def solve(problem_path=None, maxTime=None, **kwargs):
    if not problem_path:
        raise ValueError("This solver requires 'problem_path' pointing to problem.json")
    scheduler = SisqualProblem1CSP(problem_path, max_time_minutes=maxTime)
    scheduler.build_model()
    scheduler.solve()
    rows = scheduler.build_output_rows()
    return rows


def main():
    parser = argparse.ArgumentParser(description="Solve sisqual bundle with the hour-based CP-SAT Problem 1 model.")
    parser.add_argument("problem_json", help="Path to problem.json")
    parser.add_argument("--max-time", dest="max_time", default="10", help="Solver time limit in minutes")
    parser.add_argument("--output", dest="output", default=None, help="Optional output CSV path")
    parser.add_argument("--print-json", dest="print_json", action="store_true", help="Print JSON of returned rows to stdout")
    args = parser.parse_args()

    scheduler = SisqualProblem1CSP(args.problem_json, max_time_minutes=args.max_time)
    scheduler.build_model()
    scheduler.solve()
    rows = scheduler.build_output_rows()

    print(f"Status: {scheduler.solution_status()}")
    print(f"Objective: {scheduler.objective_value}")

    if args.output:
        scheduler.export_csv(args.output)
        print(f"Wrote schedule to {args.output}")
    else:
        for row in rows[:5]:
            print(row[:6])


if __name__ == "__main__":
    main()
