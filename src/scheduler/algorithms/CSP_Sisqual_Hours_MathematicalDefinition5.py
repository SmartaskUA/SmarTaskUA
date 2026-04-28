"""
Hour-based CP-SAT model for the Sisqual bundle following MathematicalDefinition5.

This mirrors `ILP_Sisqual_Hours_MathematicalDefinition5.py` while using
OR-Tools CP-SAT:
  - ObjectiveFunction1: weighted priority shortage against alpha_dts
  - ObjectiveFunction2: weighted level-specific shortage against beta_dtsl
  - ObjectiveFunction3: linear competence score l * y'_wdtsl
  - ObjectiveFunction4: work assigned on preferred day-offs x'_wd
  - ObjectiveFunction5: assignment to lower-priority skills
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List

from ortools.sat.python import cp_model

from algorithms.sisqual_hours_utils import (
    build_half_hour_slots,
    build_objective1_priority_coefficients,
    build_objective1_priority_index,
    build_objective5_skill_priority,
    build_period_slot_map,
    build_sisqual_bundle_assignments,
    build_sisqual_day_modes,
    group_open_days_by_week,
    load_problem_json,
    minutes_to_hhmm,
    parse_beta_requirements,
    parse_contract_hours,
    parse_coverage_priority_tiers,
    parse_days,
    parse_demand_minimums,
    parse_employees_with_levels,
    parse_max_time_seconds,
    parse_min_rest_hours,
    parse_open_days,
    parse_schedule_input,
    parse_skill_codes,
    parse_soft_objectives,
    parse_work_periods,
)


def _int_weight(value: float, label: str) -> int:
    if value <= 0:
        return 0
    int_value = int(value)
    if value != int_value:
        raise ValueError(
            f"CP-SAT requires integer objective weights; {label} received {value!r}"
        )
    return int_value


class SisqualProblem5CSP:
    """Hour-based CP-SAT solver for the weighted Sisqual MathematicalDefinition5 model."""

    def __init__(
        self,
        problem_json_path: str,
        max_time_minutes=None,
    ):
        self.staff_team_code = "Employees"
        self.problem_json_path = Path(problem_json_path).resolve()
        self.base_dir = self.problem_json_path.parent
        self.problem = load_problem_json(self.problem_json_path)
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)
        self.min_rest_hours = parse_min_rest_hours(self.problem)

        self.contract_hours = parse_contract_hours(self.problem)
        self.work_periods = parse_work_periods(self.problem)
        self.employees = parse_employees_with_levels(
            self.problem,
            self.contract_hours,
            self.staff_team_code,
        )
        self.days = parse_days(self.problem)
        self.date_by_day = {
            day: datetime.strptime(day, "%Y-%m-%d").date()
            for day in self.days
        }
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.days)
        self.skills = parse_skill_codes(self.problem)
        self.time_slots = build_half_hour_slots(self.work_periods)
        self.coverage_by_period = build_period_slot_map(self.work_periods, self.time_slots)
        self.alpha = parse_demand_minimums(self.base_dir, self.problem, self.coverage_by_period)

        demand_days = {day for (day, _, _) in self.alpha.keys()}
        invalid_demand_days = sorted(demand_days - set(self.days))
        if invalid_demand_days:
            preview = ", ".join(invalid_demand_days[:5])
            if len(invalid_demand_days) > 5:
                preview += ", ..."
            raise ValueError(
                "Demand data contains dates outside targetPeriod: "
                f"{preview}. Update problem.json targetPeriod or demand.csv."
            )

        self.open_days = parse_open_days(self.days, self.alpha)
        self.closed_days = set(self.days) - set(self.open_days)
        self.coverage_priority_tiers = parse_coverage_priority_tiers(
            self.problem,
            self.skills,
            self.staff_team_code,
        )
        self.objective5_skill_priority = build_objective5_skill_priority(
            self.employees,
            self.coverage_priority_tiers,
        )
        self.objective1_priority_index = build_objective1_priority_index(
            self.alpha,
            self.coverage_priority_tiers,
        )
        self.objective1_priority_coefficients = build_objective1_priority_coefficients(
            self.coverage_priority_tiers,
        )

        (
            self.objective1_weight,
            self.objective2_weights,
            self.objective3_weight,
            self.objective4_weight,
            self.objective5_weight,
        ) = parse_soft_objectives(self.problem)
        self._validate_objective_weights()

        self.variable_days_off_active = self.objective4_weight > 0
        self.day_modes = build_sisqual_day_modes(
            self.employees,
            self.days,
            self.schedule_markers,
            self.closed_days,
        )
        self.assignments = build_sisqual_bundle_assignments(
            self.employees,
            self.days,
            self.schedule_markers,
            self.time_slots,
            self.day_modes,
            self.variable_days_off_active,
        )
        self.levels = sorted(
            {
                level
                for employee in self.employees
                for level in employee["skill_levels"].values()
            }
        )
        self.beta = parse_beta_requirements(
            self.base_dir,
            self.problem,
            self.coverage_by_period,
            self.time_slots,
            self.open_days,
            self.objective2_weights,
        )
        self.weeks = group_open_days_by_week(
            self.problem,
            self.open_days,
            self.date_by_day,
        )

        self.model = None
        self.solver = None
        self.x = {}
        self.workday = {}
        self.y = {}
        self.y_level = {}
        self.shortage = {}
        self.level_shortage = {}
        self.priority_shortage = {}
        self.preferred_day_work = {}
        self.coverage_terms_cache = {}
        self.status = None
        self.objective_value = None

    def _validate_objective_weights(self):
        _int_weight(self.objective1_weight, "ObjectiveFunction1")
        for (skill, level), weight in self.objective2_weights.items():
            _int_weight(weight, f"ObjectiveFunction2 {skill}:{level}")
        _int_weight(self.objective3_weight, "ObjectiveFunction3")
        _int_weight(self.objective4_weight, "ObjectiveFunction4")
        _int_weight(self.objective5_weight, "ObjectiveFunction5")

    def _coverage_terms(self, day: str, slot_idx: int, skill: str):
        cache_key = (day, slot_idx, skill)
        cached = self.coverage_terms_cache.get(cache_key)
        if cached is not None:
            return cached

        coverage_terms = []
        for employee in self.employees:
            employee_id = employee["id"]
            y_key = (employee_id, day, slot_idx, skill)
            if y_key in self.y:
                coverage_terms.append(self.y[y_key])

        self.coverage_terms_cache[cache_key] = coverage_terms
        return coverage_terms

    def build_model(self):
        model = cp_model.CpModel()
        level_objectives_active = bool(self.objective2_weights) or self.objective3_weight > 0
        self.coverage_terms_cache = {}

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                for assignment in self.assignments[(employee_id, day)]:
                    self.x[(employee_id, day, assignment.key)] = model.NewBoolVar(
                        f"x_{employee_id}_{day.replace('-', '')}_{assignment.key.split('_')[-2]}_{assignment.key.split('_')[-1]}"
                    )

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                self.workday[(employee_id, day)] = model.NewBoolVar(
                    f"workday_{employee_id}_{day.replace('-', '')}"
                )

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                if not self.assignments[(employee_id, day)]:
                    continue
                for slot in self.time_slots:
                    for skill in employee["assignable_skills"]:
                        self.y[(employee_id, day, slot.index, skill)] = model.NewBoolVar(
                            f"y_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}"
                        )

        for (day, slot_idx, skill), minimum in self.alpha.items():
            self.shortage[(day, slot_idx, skill)] = model.NewIntVar(
                0,
                int(minimum),
                f"z_{day.replace('-', '')}_{slot_idx}_{skill}",
            )

        if self.objective1_weight > 0:
            for (day, slot_idx, skill, nth_worker), tier_index in self.objective1_priority_index.items():
                self.priority_shortage[(day, slot_idx, skill, nth_worker)] = model.NewBoolVar(
                    f"zrank_{day.replace('-', '')}_{slot_idx}_{skill}_N{nth_worker}_P{tier_index + 1}"
                )

        if level_objectives_active:
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if not self.assignments[(employee_id, day)]:
                        continue
                    for slot in self.time_slots:
                        for skill in employee["assignable_skills"]:
                            level = employee["skill_levels"][skill]
                            self.y_level[(employee_id, day, slot.index, skill, level)] = model.NewBoolVar(
                                f"yprime_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}_L{level}"
                            )

        if self.objective2_weights:
            for (day, slot_idx, skill, level), minimum in self.beta.items():
                if (skill, level) not in self.objective2_weights:
                    continue
                self.level_shortage[(day, slot_idx, skill, level)] = model.NewIntVar(
                    0,
                    int(minimum),
                    f"zprime_{day.replace('-', '')}_{slot_idx}_{skill}_L{level}",
                )

        if self.objective4_weight > 0:
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] != "preferred_day_off":
                        continue
                    self.preferred_day_work[(employee_id, day)] = model.NewBoolVar(
                        f"xprime_{employee_id}_{day.replace('-', '')}"
                    )

        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                mode = self.day_modes[(employee_id, day)]
                x_vars = [
                    self.x[(employee_id, day, assignment.key)]
                    for assignment in self.assignments[(employee_id, day)]
                ]

                if mode in {"closed", "unavailable"}:
                    model.Add(sum(x_vars) == 0)
                    model.Add(self.workday[(employee_id, day)] == 0)
                elif mode == "preferred_day_off":
                    if self.variable_days_off_active:
                        model.Add(sum(x_vars) == self.workday[(employee_id, day)])
                    else:
                        model.Add(sum(x_vars) == 0)
                        model.Add(self.workday[(employee_id, day)] == 0)
                elif mode == "work_template":
                    if self.variable_days_off_active:
                        model.Add(sum(x_vars) == self.workday[(employee_id, day)])
                    else:
                        model.Add(sum(x_vars) == 1)
                        model.Add(self.workday[(employee_id, day)] == 1)
                else:
                    model.Add(sum(x_vars) == 1)
                    model.Add(self.workday[(employee_id, day)] == 1)

        for employee in self.employees:
            employee_id = employee["id"]
            assignment_list = {
                day: self.assignments[(employee_id, day)]
                for day in self.days
            }
            for day in self.days:
                if not assignment_list[day]:
                    continue
                for slot in self.time_slots:
                    rhs_terms = [
                        self.x[(employee_id, day, assignment.key)]
                        for assignment in assignment_list[day]
                        if slot.index in assignment.slot_indices
                    ]
                    lhs_terms = [
                        self.y[(employee_id, day, slot.index, skill)]
                        for skill in employee["assignable_skills"]
                    ]
                    model.Add(sum(lhs_terms) == sum(rhs_terms))

        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.open_days) - 5):
                window = self.open_days[start:start + 6]
                model.Add(
                    sum(self.workday[(employee_id, day)] for day in window) <= 5
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
                            model.Add(
                                self.x[(employee_id, day, today_assignment.key)]
                                + self.x[(employee_id, next_day, next_assignment.key)]
                                <= 1
                            )

        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = self._coverage_terms(day, slot_idx, skill)
            model.Add(self.shortage[(day, slot_idx, skill)] + sum(coverage_terms) >= minimum)

        if self.objective1_weight > 0 and self.priority_shortage:
            for (day, slot_idx, skill, nth_worker), variable in self.priority_shortage.items():
                coverage_terms = self._coverage_terms(day, slot_idx, skill)
                model.Add(sum(coverage_terms) + nth_worker * variable >= nth_worker)

        if level_objectives_active:
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if not self.assignments[(employee_id, day)]:
                        continue
                    for slot in self.time_slots:
                        for skill in employee["assignable_skills"]:
                            level = employee["skill_levels"][skill]
                            model.Add(
                                self.y_level[(employee_id, day, slot.index, skill, level)]
                                == self.y[(employee_id, day, slot.index, skill)]
                            )

        if self.objective2_weights:
            for (day, slot_idx, skill, level), minimum in self.beta.items():
                if (skill, level) not in self.objective2_weights:
                    continue
                coverage_terms = []
                for employee in self.employees:
                    employee_id = employee["id"]
                    y_level_key = (employee_id, day, slot_idx, skill, level)
                    if y_level_key in self.y_level:
                        coverage_terms.append(self.y_level[y_level_key])
                model.Add(
                    self.level_shortage[(day, slot_idx, skill, level)] + sum(coverage_terms) >= minimum
                )

        if self.variable_days_off_active:
            for employee in self.employees:
                employee_id = employee["id"]
                for week_days in self.weeks:
                    unavailable_days = sum(
                        1
                        for day in week_days
                        if self.day_modes[(employee_id, day)] == "unavailable"
                    )
                    preferred_days_off = sum(
                        1
                        for day in week_days
                        if self.day_modes[(employee_id, day)] == "preferred_day_off"
                    )
                    required_workdays = len(week_days) - unavailable_days - preferred_days_off
                    model.Add(
                        sum(self.workday[(employee_id, day)] for day in week_days)
                        == required_workdays
                    )

            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] == "preferred_day_off":
                        model.Add(
                            self.preferred_day_work[(employee_id, day)]
                            == self.workday[(employee_id, day)]
                        )

        objective_terms = []

        objective1_weight = _int_weight(self.objective1_weight, "ObjectiveFunction1")
        if objective1_weight > 0:
            if self.priority_shortage:
                objective_terms.extend(
                    objective1_weight
                    * self.objective1_priority_coefficients[self.objective1_priority_index[key]]
                    * variable
                    for key, variable in self.priority_shortage.items()
                )
            else:
                objective_terms.extend(
                    objective1_weight * variable
                    for variable in self.shortage.values()
                )

        for (skill, level), weight in sorted(self.objective2_weights.items()):
            objective2_weight = _int_weight(weight, f"ObjectiveFunction2 {skill}:{level}")
            if objective2_weight <= 0:
                continue
            objective_terms.extend(
                objective2_weight * variable
                for (day, slot_idx, pair_skill, pair_level), variable in self.level_shortage.items()
                if pair_skill == skill and pair_level == level
            )

        objective3_weight = _int_weight(self.objective3_weight, "ObjectiveFunction3")
        if objective3_weight > 0 and self.y_level:
            objective_terms.extend(
                objective3_weight * level * variable
                for (_, _, _, _, level), variable in self.y_level.items()
            )

        objective4_weight = _int_weight(self.objective4_weight, "ObjectiveFunction4")
        if objective4_weight > 0 and self.preferred_day_work:
            objective_terms.extend(
                objective4_weight * variable
                for variable in self.preferred_day_work.values()
            )

        objective5_weight = _int_weight(self.objective5_weight, "ObjectiveFunction5")
        if objective5_weight > 0 and self.y:
            fallback = len(self.objective5_skill_priority) + 1
            objective_terms.extend(
                objective5_weight
                * self.objective5_skill_priority.get((employee_id, skill), fallback)
                * variable
                for (employee_id, _, _, skill), variable in self.y.items()
            )

        model.Minimize(sum(objective_terms) if objective_terms else 0)
        self.model = model

    def solve(self, gap_rel: float = 0.01):
        if self.model is None:
            self.build_model()

        solver = cp_model.CpSolver()
        if self.max_time_seconds is not None:
            solver.parameters.max_time_in_seconds = float(self.max_time_seconds)
        if gap_rel is not None:
            solver.parameters.relative_gap_limit = float(gap_rel)
        solver.parameters.num_search_workers = 8
        solver.parameters.log_search_progress = True

        self.status = solver.Solve(self.model)
        self.solver = solver
        if self.status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            self.objective_value = solver.ObjectiveValue()
        return self.status

    def solution_status(self) -> str:
        if self.solver is not None and self.status is not None:
            return self.solver.StatusName(self.status)
        return "Unknown"

    def build_output_rows(self) -> List[List[str]]:
        rows = [["employee_id", *self.days]]
        solved = self.solver is not None and self.status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

        for employee in self.employees:
            employee_id = employee["id"]
            row = [employee_id]
            for day in self.days:
                marker = self.schedule_markers[employee_id][day]
                mode = self.day_modes[(employee_id, day)]

                if mode == "closed":
                    row.append("CLOSED")
                    continue
                if mode == "unavailable":
                    row.append(marker or "OFF")
                    continue

                chosen = None
                if solved:
                    for assignment in self.assignments[(employee_id, day)]:
                        value = self.solver.Value(self.x[(employee_id, day, assignment.key)])
                        if value > 0:
                            chosen = assignment
                            break

                if chosen is None:
                    if mode == "preferred_day_off":
                        row.append(marker or "DO")
                    elif self.variable_days_off_active and mode == "work_template":
                        row.append("OFF")
                    else:
                        row.append("UNASSIGNED")
                    continue

                segments = []
                current_skill = None
                current_start = None
                current_end = None
                for slot_idx in chosen.slot_indices:
                    slot = self.time_slots[slot_idx]
                    assigned_skill = None
                    for skill in employee["assignable_skills"]:
                        y_var = self.y.get((employee_id, day, slot_idx, skill))
                        if y_var is not None and self.solver.Value(y_var) > 0:
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
                            segments.append(
                                f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}"
                            )
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


def solve(
    problem_path=None,
    maxTime=None,
    **kwargs,
):
    if not problem_path:
        raise ValueError("This solver requires 'problem_path' pointing to problem.json")

    scheduler = SisqualProblem5CSP(
        problem_path,
        max_time_minutes=maxTime,
    )
    scheduler.build_model()
    scheduler.solve(gap_rel=float(kwargs.get("gap_rel", kwargs.get("gapRel", 0.01))))
    return scheduler.build_output_rows()


def main():
    parser = argparse.ArgumentParser(
        description="Solve the sisqual bundle with the weighted MathematicalDefinition5 hour-based CP-SAT model."
    )
    parser.add_argument("problem_json", help="Path to problem.json")
    parser.add_argument("--max-time", dest="max_time", default="10", help="Solver time limit in minutes")
    parser.add_argument("--output", dest="output", default=None, help="Optional output CSV path")
    parser.add_argument(
        "--gap-rel",
        dest="gap_rel",
        default="0.01",
        help="Relative gap limit for CP-SAT",
    )
    args = parser.parse_args()

    scheduler = SisqualProblem5CSP(
        args.problem_json,
        max_time_minutes=args.max_time,
    )
    scheduler.build_model()
    scheduler.solve(gap_rel=float(args.gap_rel))
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
