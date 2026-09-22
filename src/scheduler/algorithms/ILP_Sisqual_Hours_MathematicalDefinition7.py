"""
Hour-based ILP for the Sisqual bundle following `MathematicalDefinition7.pdf`.

This solver extends `ILP_Sisqual_Hours.py` with the optional weighted objective
functions described in the PDF:
  - ObjectiveFunction1 (1): minimize total shortage against alpha_dts
  - ObjectiveFunction2 (1'): minimize priority-weighted skill/level assignment p_sl * y'_wdtsl
  - ObjectiveFunction3 (1''): minimize work assigned on preferred day-offs x'_wd

Objective terms are activated from `problem.json -> constraints.soft`.
Each objective stays inactive unless a positive weight exists in a matching soft
constraint.
If no objective receives a weight, the model runs as a feasibility model.

"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import pulp

from algorithms.sisqual_hours_utils import (
    Assignment,
    build_half_hour_slots,
    build_period_slot_map,
    build_sisqual_bundle_assignments,
    build_sisqual_day_modes,
    fixed_context_assignment,
    fixed_context_workday,
    group_open_days_by_week,
    load_problem_json,
    minutes_to_hhmm,
    parse_before_context_days,
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
    priority_weight_for_skill_level,
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


class SisqualProblem5ILP:
    """Hour-based ILP for the Sisqual bundle using the weighted MathematicalDefinition7 model."""

    def __init__(
        self,
        problem_json_path: str,
        max_time_minutes=None,
    ):
        self.staff_team_code = "Employees"  
        self.problem_json_path = Path(problem_json_path).resolve()  
        self.base_dir = self.problem_json_path.parent  
        self.problem = load_problem_json(self.problem_json_path)  # problem.json dict 
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)  # "10" -> 600; None -> no CBC time limit
        self.min_rest_hours = parse_min_rest_hours(self.problem)  # 11.0

        self.contract_hours = parse_contract_hours(self.problem)  # {"fullTime_8h": 8, "partTime_4h": 4, "partTime_5h": 5, "partTime_7h": 7}
        self.work_periods = parse_work_periods(self.problem)  # {"STORAGE_0830_1530": (510, 930), "CHECKOUT_1100_2100": (660, 1260), ...}
        self.employees = parse_employees_with_levels(
            self.problem,
            self.contract_hours,
            self.staff_team_code,
        )  # [{"id": "20072412", "assignable_skills": ("Management", "Employees"), "skill_levels": {"Management": 2, "Employees": 6}, ...}, ...]
        # `self.days` is still the optimization/output horizon: these are the
        # dates that get decision variables, coverage terms, and exported cells.
        self.days = parse_days(self.problem)  # target/output days, e.g. ["2025-10-01", ..., "2025-10-31"]

        # The PDF specification allows days before the target month as context.
        # We only use columns that already exist in schedule_input.csv. They are
        # immutable history and never appear in the generated schedule output.
        self.before_context_days = parse_before_context_days(self.base_dir, self.problem)

        # `constraint_days` lets boundary-sensitive hard rules scan history and
        # target days together. Any day in `context_day_set` is a constant, not a
        # decision variable.
        self.constraint_days = [*self.before_context_days, *self.days]
        self.context_day_set = set(self.before_context_days)
        self.date_by_day = {day: datetime.strptime(day, "%Y-%m-%d").date() for day in self.constraint_days}
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.constraint_days)  # target markers plus optional before-context markers
        self.skills = parse_skill_codes(self.problem)  # ["Storage", "Checkout", "Management", "Employees"]
        self.time_slots = build_half_hour_slots(self.work_periods)  # 08:30-09:00, 09:00-09:30, ..., 20:30-21:00
        self.coverage_by_period = build_period_slot_map(self.work_periods, self.time_slots)  # {"STORAGE_0830_1530": (0, 1, ..., 13), "CHECKOUT_1100_2100": (5, 6, ..., 24), ...}
        self.alpha = parse_demand_minimums(self.base_dir, self.problem, self.coverage_by_period)  # minimum demand by (day, slot, skill), e.g. ("2025-10-01", 0, "Storage") -> 1
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
        self.open_days = parse_open_days(self.days, self.alpha)  # ["2025-10-01", ..., "2025-10-31"] or only the days that appear in demand.csv
        self.closed_days = set(self.days) - set(self.open_days)  # set() for the current October bundle; otherwise {"2025-10-05", ...}
        self.coverage_priority_tiers = parse_coverage_priority_tiers(self.problem,self.skills,self.staff_team_code)  # [{"priority": 1, "skill": "Storage", "min_n": 1, ...}, {"priority": 2, "skill": "Management", "min_n": 1, "max_n": 1, ...}, ...]
        (
            self.objective1_weight,
            self.objective2_weight,
            self.objective3_weight,
        ) = parse_definition7_soft_objectives(self.problem)  # e.g. (1000.0, 100.0, 10.0)
        self.variable_days_off_active = self.objective3_weight > 0  # True when preferred day-offs may be swapped; False keeps template DO days fixed off
        self.day_modes = build_sisqual_day_modes(self.employees, self.days, self.schedule_markers, self.closed_days)  # {("20072412", "2025-10-01"): "work_template", ("20072412", "2025-10-05"): "preferred_day_off", ...}
        self.assignments = build_sisqual_bundle_assignments(
            self.employees,
            self.days,
            self.schedule_markers,
            self.time_slots,
            self.day_modes,
            self.variable_days_off_active,
        )  # feasible daily blocks per (employee, day), e.g. ("20072412", "2025-10-01") -> [08:30-16:30, 09:00-17:00, ...]
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

        self.model = None
        self.x = {}
        self.workday = {}
        self.y = {}
        self.y_level = {}
        self.shortage = {}
        self.preferred_day_work = {}
        self.coverage_terms_cache = {}
        self.primary_objective = None
        self.primary_objective_active = False
        self.status = None
        self.objective_value = None

    def _priority_weight(self, skill: str, level: int) -> int:
        return priority_weight_for_skill_level(
            self.coverage_priority_tiers,
            skill,
            level,
        )

    def _coverage_terms(self, day: str, slot_idx: int, skill: str) -> List[pulp.LpVariable]:
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
        model = pulp.LpProblem("SisqualProblem5HourlyILP", pulp.LpMinimize)
        level_objectives_active = self.objective2_weight > 0
        self.coverage_terms_cache = {}

        # For every employee, every day, and every feasible daily block, create one binary
        # variable x_{wdh} that says whether that whole assignment h in H_wd was chosen.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                for assignment in self.assignments[(employee_id, day)]:
                    self.x[(employee_id, day, assignment.key)] = pulp.LpVariable(
                        f"x_{employee_id}_{day.replace('-', '')}_{assignment.key.split('_')[-2]}_{assignment.key.split('_')[-1]}",
                        cat="Binary",
                    )

        # For every employee/day create workday_{wd}, the binary indicator stating whether
        # worker w is assigned on day d. This is used in constraints (2), (4), (9), and (10).
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                self.workday[(employee_id, day)] = pulp.LpVariable(
                    f"workday_{employee_id}_{day.replace('-', '')}",
                    cat="Binary",
                )

        # For every employee/day/slot/allowed-skill combination, create the slot-level skill
        # assignment variable y_{wdts} used in constraint (3).
        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["assignable_skills"]
            for day in self.days:
                if not self.assignments[(employee_id, day)]:
                    continue
                for slot in self.time_slots:
                    for skill in skills:
                        if self.alpha.get((day, slot.index, skill), 0) <= 0:
                            continue
                        self.y[(employee_id, day, slot.index, skill)] = pulp.LpVariable(
                            f"y_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}",
                            cat="Binary",
                        )

        # For every demanded (day, slot, skill) tuple, create shortage z_{dts}, the integer
        # variable used in ObjectiveFunction1 (1) and in constraint (5).
        for (day, slot_idx, skill), minimum in self.alpha.items():
            self.shortage[(day, slot_idx, skill)] = pulp.LpVariable(
                f"z_{day.replace('-', '')}_{slot_idx}_{skill}",
                lowBound=0,
                cat="Integer",
            )

        if level_objectives_active:
            # y'_{wdtsl} from constraint (6): for each worker/slot/skill, only the employee's
            # own competence level l_ws is materialized because all other levels are fixed to 0.
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if not self.assignments[(employee_id, day)]:
                        continue
                    for slot in self.time_slots:
                        for skill in employee["assignable_skills"]:
                            if (employee_id, day, slot.index, skill) not in self.y:
                                continue
                            level = employee["skill_levels"][skill]
                            self.y_level[(employee_id, day, slot.index, skill, level)] = pulp.LpVariable(
                                f"yprime_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}_L{level}",
                                cat="Binary",
                            )

        if self.objective3_weight > 0:
            # x'_{wd} from ObjectiveFunction3 (1'') and constraint (9): 1 when worker w is
            # assigned on a preferred day-off d, 0 otherwise.
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] != "preferred_day_off":
                        continue
                    self.preferred_day_work[(employee_id, day)] = pulp.LpVariable(
                        f"xprime_{employee_id}_{day.replace('-', '')}",
                        cat="Binary",
                    )

        # Constraint (2)
        # "each worker w∈W can be assigned on each open day d∈D_o with at most one
        # working daily assignment h∈H_wd."
        # When the bundle keeps a day fixed (old template behavior), this becomes equality.
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                mode = self.day_modes[(employee_id, day)]
                x_vars = [self.x[(employee_id, day, assignment.key)] for assignment in self.assignments[(employee_id, day)]]

                if mode in {"closed", "unavailable"}:
                    if x_vars:
                        model += pulp.lpSum(x_vars) == 0, f"closed_or_unavailable_{employee_id}_{day}"
                    model += self.workday[(employee_id, day)] == 0, f"workday_off_{employee_id}_{day}"
                elif mode == "preferred_day_off":
                    if self.variable_days_off_active:
                        model += (
                            pulp.lpSum(x_vars) == self.workday[(employee_id, day)],
                            f"preferred_day_off_link_{employee_id}_{day}",
                        )
                    else:
                        if x_vars:
                            model += pulp.lpSum(x_vars) == 0, f"preferred_day_off_fixed_{employee_id}_{day}"
                        model += self.workday[(employee_id, day)] == 0, f"preferred_day_off_workday_{employee_id}_{day}"
                elif mode == "work_template":
                    if self.variable_days_off_active:
                        model += (
                            pulp.lpSum(x_vars) == self.workday[(employee_id, day)],
                            f"flex_work_template_{employee_id}_{day}",
                        )
                    else:
                        model += pulp.lpSum(x_vars) == 1, f"mandatory_work_{employee_id}_{day}"
                        model += self.workday[(employee_id, day)] == 1, f"mandatory_workday_{employee_id}_{day}"
                else:
                    model += pulp.lpSum(x_vars) == 1, f"fixed_time_work_{employee_id}_{day}"
                    model += self.workday[(employee_id, day)] == 1, f"fixed_time_workday_{employee_id}_{day}"

        # Constraint (3)
        # "each worker w∈W assigned on day d∈D_o with a working daily assignment
        # h∈H_wd that covers timeslot t∈T_d must be assigned in timeslot t with
        # one of its skills S_w."
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
                    lhs_terms = [
                        self.y[(employee_id, day, slot.index, skill)]
                        for skill in skills
                        if (employee_id, day, slot.index, skill) in self.y
                    ]
                    model += (
                        pulp.lpSum(lhs_terms) == pulp.lpSum(rhs_terms),
                        f"skill_cover_{employee_id}_{day}_{slot.index}",
                    )

        # Constraint (4)
        # "each worker w∈W cannot be assigned with more than 5 working days in
        # any set of 6 consecutive days." Optional before-context days are fixed
        # history, so they only contribute constants to windows crossing the
        # target-period boundary.
        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.constraint_days) - 5):
                window = self.constraint_days[start:start + 6]

                # Pure-history windows need no constraint because they contain no
                # target decision variables. We only constrain windows that touch
                # the target period.
                if not any(day not in self.context_day_set for day in window):
                    continue

                # Previous days are fixed input history: add them as constants.
                # Target days remain normal binary workday variables.
                fixed_workdays = sum(
                    fixed_context_workday(self.schedule_markers, employee_id, day)
                    for day in window
                    if day in self.context_day_set
                )
                target_terms = [
                    self.workday[(employee_id, day)]
                    for day in window
                    if day not in self.context_day_set
                ]
                model += (
                    fixed_workdays + pulp.lpSum(target_terms) <= 5,
                    f"max5in6_{employee_id}_{start}",
                )

        # Extra hard constraint from problem.json, kept from the original hourly model:
        # forbid consecutive-day assignment pairs whose overnight rest is below the
        # configured minimum rest hours.
        for employee in self.employees:
            employee_id = employee["id"]

            # First handle the single boundary from the last available context
            # day into the first target day. Context days only restrict the
            # target assignment when they have exact EQUALS times; numeric
            # markers do not provide a safe previous-day end time.
            for day, next_day in zip(self.constraint_days, self.constraint_days[1:]):
                if day not in self.context_day_set or next_day in self.context_day_set:
                    continue
                context_assignment = fixed_context_assignment(self.schedule_markers, employee_id, day)
                if context_assignment is None:
                    continue
                for next_assignment in self.assignments[(employee_id, next_day)]:
                    rest_hours = ((24 * 60 - context_assignment.end_min) + next_assignment.start_min) / 60.0
                    if rest_hours < self.min_rest_hours:
                        model += (
                            self.x[(employee_id, next_day, next_assignment.key)] == 0,
                            f"min_rest_context_{employee_id}_{day.replace('-', '')}_{next_day.replace('-', '')}_{next_assignment.key}",
                        )

            # Then keep the original target-period rest constraints between
            # pairs of target days, where both assignments are solver decisions.
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
        # the required value alpha_dts for each open day d∈D_o, each timeslot t∈T_d
        # and each skill s∈S."
        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = self._coverage_terms(day, slot_idx, skill)
            model += (
                self.shortage[(day, slot_idx, skill)] + pulp.lpSum(coverage_terms) >= minimum,
                f"shortage_{day}_{slot_idx}_{skill}",
            )

        if level_objectives_active:
            # Constraint (6)
            # "each worker w∈W that works in day d∈D_o in timeslot t∈T with skill s∈S_w
            # is assigned with its competence level l_ws and all other levels are set to 0."
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if not self.assignments[(employee_id, day)]:
                        continue
                    for slot in self.time_slots:
                        for skill in employee["assignable_skills"]:
                            level = employee["skill_levels"][skill]
                            if (employee_id, day, slot.index, skill, level) not in self.y_level:
                                continue
                            model += (
                                self.y_level[(employee_id, day, slot.index, skill, level)]
                                == self.y[(employee_id, day, slot.index, skill)],
                                f"level_link_{employee_id}_{day}_{slot.index}_{skill}_L{level}",
                            )

        if self.variable_days_off_active:
            # Constraint (5)
            # "each worker w∈W cannot be assigned with any working daily assignment
            # in the days that he is unavailable on each week."
            # This is already enforced day-by-day above through mode == "unavailable" -> x = 0.

            # Constraint (6)
            # "each worker w∈W must be assigned on each week k∈K with n_wk working days."
            for employee in self.employees:
                employee_id = employee["id"]
                for week_index, week_days in enumerate(self.weeks):
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
                    model += (
                        pulp.lpSum(self.workday[(employee_id, day)] for day in week_days) == required_workdays,
                        f"weekly_workdays_{employee_id}_{week_index}",
                    )

            # Constraint (9)
            # "x'_{wd} is set to 1 when worker w works on a preferable day-off d,
            # and is set to 0 otherwise."
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] == "preferred_day_off":
                        model += (
                            self.preferred_day_work[(employee_id, day)] == self.workday[(employee_id, day)],
                            f"preferred_day_indicator_{employee_id}_{day}",
                        )

        objective_terms = []

        # ObjectiveFunction1
        # Try to fulfil as much as possible the minimum number alpha_dts of workers
        # in all open days, timeslots, and skills.
        if self.objective1_weight > 0 and self.shortage:
            objective_terms.append(self.objective1_weight * pulp.lpSum(self.shortage.values()))

        # ObjectiveFunction2
        # Prefer higher-priority skill/level combinations by minimizing
        # sum(p_sl * y'_wdtsl).
        if self.objective2_weight > 0 and self.y_level:
            objective_terms.append(
                self.objective2_weight
                * pulp.lpSum(
                    self._priority_weight(skill, level) * variable
                    for (_, _, _, skill, level), variable in self.y_level.items()
                )
            )

        # ObjectiveFunction3 (1'')
        # trying to assign as much as possible the preferable days-off by minimizing
        # the number of preferred day-offs that become worked days.
        if self.objective3_weight > 0 and self.preferred_day_work:
            objective_terms.append(
                self.objective3_weight * pulp.lpSum(self.preferred_day_work.values())
            )

        self.primary_objective = pulp.lpSum(objective_terms) if objective_terms else 0
        self.primary_objective_active = bool(objective_terms)

        if self.primary_objective_active:
            model += self.primary_objective, "weighted_mathematical_definition_7_objective"
        else:
            model += 0, "feasibility_only"

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
        if pulp.LpStatus.get(self.status) not in {"Optimal", "Feasible"}:
            self.objective_value = pulp.value(self.model.objective)
            return self.status

        primary_value = pulp.value(self.primary_objective) or 0.0
        self.objective_value = primary_value

        return self.status

    def solution_status(self) -> str:
        return pulp.LpStatus.get(self.status, "Unknown")

    def build_output_rows(self) -> List[List[str]]:
        rows = [["employee_id", *self.days]]  # [["employee_id", "2025-10-01", "2025-10-02", ..., "2025-10-31"], ...]

        for employee in self.employees:
            employee_id = employee["id"]  # "20072412"
            row = [employee_id]  # ["20072412"]
            for day in self.days:
                marker = self.schedule_markers[employee_id][day]  # original template cell like "DO", "VAC", "8", "EQUALS:11:00-16:00"
                mode = self.day_modes[(employee_id, day)]  # "closed", "unavailable", "preferred_day_off", "fixed_time_work", or "work_template"

                if mode == "closed":
                    row.append("CLOSED")  # export explicit store-closed day marker
                    continue
                if mode == "unavailable":
                    row.append(marker or "OFF")  # preserve original off marker such as "VAC" / "MED";
                    continue

                chosen = None  # the one daily Assignment selected by x_{wdh}, e.g. 14:00-22:00 block
                for assignment in self.assignments[(employee_id, day)]:
                    value = pulp.value(self.x.get((employee_id, day, assignment.key)))
                    if value is not None and value > 0.5:
                        chosen = assignment
                        break

                if chosen is None:
                    if mode == "preferred_day_off":
                        row.append(marker or "DO")  # untouched preferred day-off remains DO
                    elif self.variable_days_off_active and mode == "work_template":
                        row.append("OFF")  # swappable template work day that the solver decided to leave off
                    else:
                        row.append("UNASSIGNED")  # defensive fallback: expected work day but no assignment selected
                    continue

                segments = []  # merged export pieces like ["10:00-11:00@Checkout", "11:00-14:00@Management"]
                current_skill = None  # currently open segment skill while scanning the chosen half-hour slots
                current_start = None  # segment start minute, e.g. 600 for 10:00
                current_end = None  # segment end minute, updated as adjacent equal-skill slots are merged
                # Walk the chosen half-hour slots in order and merge adjacent slots with the
                # same skill into one exported segment.
                for slot_idx in chosen.slot_indices:
                    slot = self.time_slots[slot_idx]  # one 30-minute slot, e.g. TimeSlot(index=5, start_min=660, end_min=690)
                    assigned_skill = None  # actual team chosen by y_{wdts} for this slot
                    for skill in employee["assignable_skills"]:
                        y_var = self.y.get((employee_id, day, slot_idx, skill))
                        if y_var is None:
                            continue
                        value = pulp.value(y_var)
                        if value is not None and value > 0.5:
                            assigned_skill = skill
                            break
                    if assigned_skill is None:
                        if employee["assignable_skills"]:
                            assigned_skill = employee["assignable_skills"][0]  # defensive fallback to the first declared competency if y was not materialized
                        else:
                            assigned_skill = self.staff_team_code  # final fallback; should not be needed for valid Sisqual employees
                    if current_skill == assigned_skill:
                        current_end = slot.end_min  # keep extending the current contiguous segment
                    else:
                        if current_skill is not None:
                            segments.append(
                                f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}"
                            )  # close previous segment, e.g. "10:00-11:00@Checkout"
                        current_skill = assigned_skill  # start a new segment for the new skill
                        current_start = slot.start_min
                        current_end = slot.end_min
                if current_skill is not None:
                    segments.append(f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}")  # append the final open segment
                row.append(" | ".join(segments) if segments else chosen.label)  # "10:00-11:00@Checkout | 11:00-14:00@Management"
            rows.append(row)  # ["20072412", "14:00-22:00@Management", "DO", "CLOSED", ...]
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

    scheduler = SisqualProblem5ILP(
        problem_path,
        max_time_minutes=maxTime,
    )
    scheduler.build_model()
    status = scheduler.solve(gap_rel=float(kwargs.get("gap_rel", kwargs.get("gapRel", 0.01))))
    status_name = pulp.LpStatus.get(status, "Unknown")
    if status_name == "Infeasible":
        from validators.sisqual_feasibility import build_solver_infeasible_report

        raise build_solver_infeasible_report(
            problem_path,
            str(kwargs.get("task_id", "manual")),
            "ILP_Sisqual_Hours_MathematicalDefinition7",
            status_name,
            model_stats={
                "variables": len(scheduler.model.variables()) if scheduler.model is not None else None,
                "constraints": len(scheduler.model.constraints) if scheduler.model is not None else None,
            },
        )
    return scheduler.build_output_rows()


def main():
    parser = argparse.ArgumentParser(
        description="Solve the sisqual bundle with the weighted MathematicalDefinition7 hour-based ILP model."
    )
    parser.add_argument("problem_json", help="Path to problem.json")
    parser.add_argument("--max-time", dest="max_time", default="10", help="Solver time limit in minutes")
    parser.add_argument("--output", dest="output", default=None, help="Optional output CSV path")
    parser.add_argument(
        "--gap-rel",
        dest="gap_rel",
        default="0.01",
        help="Relative MIP gap for CBC",
    )
    args = parser.parse_args()

    scheduler = SisqualProblem5ILP(
        args.problem_json,
        max_time_minutes=args.max_time,
    )
    scheduler.build_model()
    status = scheduler.solve(gap_rel=float(args.gap_rel))
    rows = scheduler.build_output_rows()

    print(f"Status: {pulp.LpStatus.get(status, 'Unknown')}")
    print(f"Objective: {scheduler.objective_value}")

    if args.output:
        scheduler.export_csv(args.output)
        print(f"Wrote schedule to {args.output}")
    else:
        for row in rows[:5]:
            print(row[:6])


if __name__ == "__main__":
    main()
