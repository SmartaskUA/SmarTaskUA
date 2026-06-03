"""
Hour-based CP-SAT model for the Sisqual bundle following MathematicalDefinition7.

This mirrors `ILP_Sisqual_Hours_MathematicalDefinition7.py` while using
OR-Tools CP-SAT:
  - ObjectiveFunction1: weighted total shortage against alpha_dts
  - ObjectiveFunction2: priority-weighted skill/level assignment p_sl * y'_wdtsl
  - ObjectiveFunction3: work assigned on preferred day-offs x'_wd

Objective terms are activated from `problem.json -> constraints.soft`.
CP-SAT requires integer objective coefficients, so positive configured weights
are validated before model construction.
If no objective receives a weight, the model runs as a feasibility model.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

from ortools.sat.python import cp_model

from algorithms.sisqual_hours_utils import (
    build_half_hour_slots,
    build_period_slot_map,
    build_sisqual_bundle_assignments,
    build_sisqual_day_modes,
    group_open_days_by_week,
    load_problem_json,
    match_coverage_priority_tier,
    minutes_to_hhmm,
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
    parse_soft_constraint_weight,
    parse_work_periods,
)


OBJECTIVE1_TYPES = {
    "coverage_shortage",
    "min_coverage",
    "objective1",
    "minimize_shortages",
    "minimize_total_shortage",
    "minimize_coverage_shortage",
}
OBJECTIVE2_TYPES = {
    "objective2",
    "skill_priority_assignment",
    "priority_skill_assignment",
    "assign_higher_priority_skills",
    "minimize_lower_priority_skill_assignment",
    "objective5",
    "skill_priority",
}
OBJECTIVE3_TYPES = {
    "objective3",
    "day_off_swap_penalty",
    "preferred_day_off",
    "preferred_day_off_work",
    "minimize_preferred_day_off_work",
    "objective4",
    "minimize_day_off_changes",
}


def parse_definition7_soft_objectives(problem: Dict) -> Tuple[float, float, float]:
    objective1_weight = 0.0
    objective2_weight = 0.0
    objective3_weight = 0.0

    for constraint in problem.get("constraints", {}).get("soft", []):
        if not constraint.get("enabled", True):
            continue
        type_name = str(
            constraint.get("type")
            or constraint.get("id")
            or ""
        ).strip().lower()
        weight = parse_soft_constraint_weight(constraint)
        if weight <= 0:
            continue

        if type_name in OBJECTIVE1_TYPES:
            objective1_weight = weight
        elif type_name in OBJECTIVE2_TYPES:
            objective2_weight = weight
        elif type_name in OBJECTIVE3_TYPES:
            objective3_weight = weight

    return objective1_weight, objective2_weight, objective3_weight


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
    """Hour-based CP-SAT solver for the weighted Sisqual MathematicalDefinition7 model."""

    def __init__(
        self,
        problem_json_path: str,
        max_time_minutes=None,
    ):
        self.staff_team_code = "Employees"  # generic staff-demand team used by the Sisqual bundle
        self.problem_json_path = Path(problem_json_path).resolve()  # /.../data/problems/SISQUAL_COMPLETE/problem.json
        self.base_dir = self.problem_json_path.parent  # /.../data/problems/SISQUAL_COMPLETE
        self.problem = load_problem_json(self.problem_json_path)  # full problem.json dict
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)  # "10" -> 600; None -> no CP-SAT time limit
        self.min_rest_hours = parse_min_rest_hours(self.problem)  # 11.0 for the current Sisqual bundle
        self.contract_hours = parse_contract_hours(self.problem)  # {"fullTime_8h": 8, "partTime_4h": 4, "partTime_5h": 5, "partTime_7h": 7}
        self.work_periods = parse_work_periods(self.problem)  # {"STORAGE_0830_1530": (510, 930), "CHECKOUT_1100_2100": (660, 1260), ...}
        self.employees = parse_employees_with_levels(
            self.problem,
            self.contract_hours,
            self.staff_team_code,
        )  # [{"id": "20072412", "assignable_skills": ("Management", "Employees"), "skill_levels": {"Management": 1, "Employees": 6}, ...}, ...]
        self.days = parse_days(self.problem)  # ["2025-10-01", "2025-10-02", ..., "2025-10-31"]
        self.date_by_day = {
            day: datetime.strptime(day, "%Y-%m-%d").date()
            for day in self.days
        }  # {"2025-10-01": date(2025, 10, 1), ...}
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.days)  # {"20072412": {"2025-10-01": "8", "2025-10-02": "8", ...}, ...}
        self.skills = parse_skill_codes(self.problem)  # ["Storage", "Management", "Checkout", "Employees"]
        self.time_slots = build_half_hour_slots(self.work_periods)  # [TimeSlot(index=0, 08:30-09:00), TimeSlot(index=1, 09:00-09:30), ...]
        self.coverage_by_period = build_period_slot_map(self.work_periods, self.time_slots)  # {"STORAGE_0830_1530": (0, 1, ..., 13), "CHECKOUT_1100_2100": (5, 6, ..., 24), ...}
        self.alpha = parse_demand_minimums(self.base_dir, self.problem, self.coverage_by_period)  # {("2025-10-01", 0, "Storage"): 1, ("2025-10-01", 5, "Checkout"): 1, ...}

        # Demand must stay inside temporalScope.targetPeriod. This catches a
        # common data issue before the model creates variables for impossible days.
        demand_days = {day for (day, _, _) in self.alpha.keys()}  # {"2025-10-01", "2025-10-02", ..., "2025-10-31"}
        invalid_demand_days = sorted(demand_days - set(self.days))  # [] when demand.csv matches targetPeriod
        if invalid_demand_days:
            preview = ", ".join(invalid_demand_days[:5])
            if len(invalid_demand_days) > 5:
                preview += ", ..."
            raise ValueError(
                "Demand data contains dates outside targetPeriod: "
                f"{preview}. Update problem.json targetPeriod or demand.csv."
            )

        self.open_days = parse_open_days(self.days, self.alpha)  # days with demand, usually all October days in this bundle
        self.closed_days = set(self.days) - set(self.open_days)  # set() for current Sisqual data, or {"2025-10-05", ...}

        self.coverage_priority_tiers = parse_coverage_priority_tiers(
            self.problem,
            self.skills,
            self.staff_team_code,
        )  # [{"priority": 1, "skill": "Storage", "min_n": 1, ...}, {"priority": 2, "skill": "Management", ...}, ...]

        (
            self.objective1_weight,
            self.objective2_weight,
            self.objective3_weight,
        ) = parse_definition7_soft_objectives(self.problem)  # e.g. (1000.0, 100.0, 10.0)
        self._validate_objective_weights()

        # Objective 3 activates the "swap preferred day-off" behavior. When it
        # is inactive, template DO days remain fixed off exactly like the input.
        self.variable_days_off_active = self.objective3_weight > 0  # True when preferred day-offs may be swapped within the week
        self.day_modes = build_sisqual_day_modes(
            self.employees,
            self.days,
            self.schedule_markers,
            self.closed_days,
        )  # {("20072412", "2025-10-01"): "work_template", ("20072412", "2025-10-05"): "preferred_day_off", ...}
        self.assignments = build_sisqual_bundle_assignments(
            self.employees,
            self.days,
            self.schedule_markers,
            self.time_slots,
            self.day_modes,
            self.variable_days_off_active,
        )  # {("20072412", "2025-10-01"): [Assignment("08:30-16:30"), Assignment("09:00-17:00"), ...], ...}

        self.levels = sorted(
            {
                level
                for employee in self.employees
                for level in employee["skill_levels"].values()
            }
        )  # [1, 2, 3, 4, 5, 6]
        self.weeks = group_open_days_by_week(
            self.problem,
            self.open_days,
            self.date_by_day,
        )  # [["2025-10-01", ..., "2025-10-05"], ["2025-10-06", ..., "2025-10-12"], ...]

        #   x[(w, d, h)]              -> chosen daily assignment
        #   workday[(w, d)]           -> whether worker w works on day d
        #   y[(w, d, t, s)]           -> slot/team assignment
        #   y_level[(w, d, t, s, l)]  -> slot/team/level assignment
        #   shortage[(d, t, s)]       -> z_dts coverage shortage
        #   preferred_day_work[(w,d)] -> x'_wd preferred day-off worked
        self.model = None
        self.solver = None
        self.x = {}  # {("20072412", "2025-10-01", "A_510_990"): BoolVar(...), ...}
        self.workday = {}  # {("20072412", "2025-10-01"): BoolVar(...), ...}
        self.y = {}  # {("20072412", "2025-10-01", 5, "Management"): BoolVar(...), ...}
        self.y_level = {}  # {("20072412", "2025-10-01", 5, "Management", 1): BoolVar(...), ...}
        self.shortage = {}  # {("2025-10-01", 5, "Checkout"): IntVar(...), ...}
        self.preferred_day_work = {}  # {("20072412", "2025-10-05"): BoolVar(...), ...}
        self.coverage_terms_cache = {}  # {("2025-10-01", 5, "Checkout"): [y_var, y_var, ...], ...}
        self.primary_objective = None
        self.primary_objective_active = False
        self.status = None
        self.objective_value = None

    def _validate_objective_weights(self):
        _int_weight(self.objective1_weight, "ObjectiveFunction1")
        _int_weight(self.objective2_weight, "ObjectiveFunction2")
        _int_weight(self.objective3_weight, "ObjectiveFunction3")

    def _priority_weight(self, skill: str, level: int) -> int:
        try:
            tier_index = match_coverage_priority_tier(
                self.coverage_priority_tiers,
                skill,
                level,
            )
        except ValueError:
            return len(self.coverage_priority_tiers) + 1
        return int(self.coverage_priority_tiers[tier_index].get("priority", tier_index + 1))

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
        level_objectives_active = self.objective2_weight > 0
        self.coverage_terms_cache = {}

        # For every employee, every day, and every feasible daily block, create
        # one binary variable x_{wdh} that says whether assignment h in H_wd was chosen.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                for assignment in self.assignments[(employee_id, day)]:
                    self.x[(employee_id, day, assignment.key)] = model.NewBoolVar(
                        f"x_{employee_id}_{day.replace('-', '')}_{assignment.key.split('_')[-2]}_{assignment.key.split('_')[-1]}"
                    )

        # Binary workday_{wd}: 1 when employee w is assigned on day d. It is used
        # by the daily assignment link, max-consecutive-days, weekly balance, and
        # preferred day-off indicator constraints.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                self.workday[(employee_id, day)] = model.NewBoolVar(
                    f"workday_{employee_id}_{day.replace('-', '')}"
                )

        # Slot-level team assignment y_{wdts}: if a chosen daily block covers a
        # half-hour slot, exactly one of the employee's assignable skills is used.
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

        # Coverage shortage z_{dts} for ObjectiveFunction1. The upper bound is
        # the required minimum because shortage cannot exceed the full demand.
        for (day, slot_idx, skill), minimum in self.alpha.items():
            self.shortage[(day, slot_idx, skill)] = model.NewIntVar(
                0,
                int(minimum),
                f"z_{day.replace('-', '')}_{slot_idx}_{skill}",
            )

        if level_objectives_active:
            # y'_{wdtsl} from constraint (6). Only the employee's own competence
            # level for each skill is materialized; all other levels are implicitly 0.
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

        if self.objective3_weight > 0:
            # Preferred day-off indicator x'_{wd}: 1 when worker w is assigned on
            # an input DO day that the objective allows the solver to swap.
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] != "preferred_day_off":
                        continue
                    self.preferred_day_work[(employee_id, day)] = model.NewBoolVar(
                        f"xprime_{employee_id}_{day.replace('-', '')}"
                    )

        # Constraint (2)
        # Each worker can receive at most one daily assignment on each open day.
        # For fixed-template days this becomes equality, while unavailable/closed
        # days are forced to 0. Preferred DO behavior depends on Objective 3.
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

        # Constraint (3)
        # Link daily block choices x_{wdh} to slot/team assignments y_{wdts}.
        # If the chosen block covers slot t, exactly one assignable skill must be
        # selected for that slot; if no chosen block covers it, all y variables are 0.
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

        # Constraint (4)
        # No worker can be assigned more than 5 working days in any 6 consecutive
        # open days, matching the Sisqual max-consecutive-days hard rule.
        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.open_days) - 5):
                window = self.open_days[start:start + 6]
                model.Add(
                    sum(self.workday[(employee_id, day)] for day in window) <= 5
                )

        # Extra hard constraint from problem.json:
        # forbid adjacent-day assignment pairs whose overnight rest is below the
        # configured minimum rest hours, usually 11h in the Sisqual bundle.
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

        # Constraint (5)
        # Shortage z_dts plus assigned coverage must reach minimum demand alpha_dts.
        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = self._coverage_terms(day, slot_idx, skill)
            model.Add(self.shortage[(day, slot_idx, skill)] + sum(coverage_terms) >= minimum)

        if level_objectives_active:
            # Constraint (6)
            # Link each slot/team assignment y_{wdts} to the employee's actual
            # competence level variable y'_{wdtsl}.
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

        if self.variable_days_off_active:
            # Constraint (5)
            # Unavailable days are already enforced above through mode == "unavailable".
            #
            # Constraint (6)
            # Keep each worker's weekly number of workdays equal to the original
            # template count, while allowing preferred DO days to swap inside the week.
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

            # Constraint (9)
            # x'_{wd} is exactly the workday indicator on preferred day-off cells,
            # so ObjectiveFunction3 can count how many DO days were worked.
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] == "preferred_day_off":
                        model.Add(
                            self.preferred_day_work[(employee_id, day)]
                            == self.workday[(employee_id, day)]
                        )

        objective_terms = []

        # ObjectiveFunction1
        # Minimize shortage against alpha_dts across all open days, half-hour
        # slots, and skills.
        objective1_weight = _int_weight(self.objective1_weight, "ObjectiveFunction1")
        if objective1_weight > 0:
            objective_terms.extend(
                objective1_weight * variable
                for variable in self.shortage.values()
            )

        # ObjectiveFunction2
        # Prefer higher-priority skill/level combinations by minimizing
        # sum(p_sl * y'_wdtsl).
        objective2_weight = _int_weight(self.objective2_weight, "ObjectiveFunction2")
        if objective2_weight > 0 and self.y_level:
            objective_terms.extend(
                objective2_weight * self._priority_weight(skill, level) * variable
                for (_, _, _, skill, level), variable in self.y_level.items()
            )

        # ObjectiveFunction3
        # Minimize preferred day-offs that become worked days.
        objective3_weight = _int_weight(self.objective3_weight, "ObjectiveFunction3")
        if objective3_weight > 0 and self.preferred_day_work:
            objective_terms.extend(
                objective3_weight * variable
                for variable in self.preferred_day_work.values()
            )

        self.primary_objective = sum(objective_terms) if objective_terms else 0
        self.primary_objective_active = bool(objective_terms)

        model.Minimize(self.primary_objective)
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
            primary_value = int(round(solver.ObjectiveValue())) if self.primary_objective_active else 0
            self.objective_value = primary_value
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

                # Find the selected daily Assignment h from x_{wdh}. A solved CP-SAT
                # model has exactly one chosen assignment on mandatory work days.
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

                # Walk the selected half-hour slots and merge adjacent slots with
                # the same y_{wdts} skill into readable "HH:MM-HH:MM@Team" segments.
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
        description="Solve the sisqual bundle with the weighted MathematicalDefinition7 hour-based CP-SAT model."
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
