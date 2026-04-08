"""
Hour-based ILP for the Sisqual bundle following `MathematicalDefinition5_Corrigido.pdf`.

This solver extends `ILP_Sisqual_Hours.py` with the optional weighted objective
functions described in the PDF:
  - ObjectiveFunction1 (1): minimize total shortage against alpha_dts
  - ObjectiveFunction2 (1'): minimize level-specific shortage against beta_dtsl
  - ObjectiveFunction3 (1''): minimize the linear competence score l * y'_wdtsl
  - ObjectiveFunction4 (1'''): minimize work assigned on preferred day-offs x'_wd

Objective terms are activated from `problem.json -> constraints.soft`.
Each objective stays inactive unless a positive weight exists in a matching soft
constraint.
If no objective receives a weight, the model runs as a feasibility model.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import pulp

from algorithms.sisqual_hours_utils import (
    OFF_MARKERS,
    Assignment,
    build_half_hour_slots,
    build_period_slot_map,
    load_problem_json,
    minutes_to_hhmm,
    normalize_marker,
    parse_beta_requirements,
    parse_contract_hours,
    parse_days,
    parse_demand_minimums,
    parse_employees_with_levels,
    parse_hhmm,
    parse_max_time_seconds,
    parse_min_rest_hours,
    parse_open_days,
    parse_schedule_input,
    parse_skill_codes,
    parse_soft_objectives,
    parse_work_periods,
)


UNAVAILABLE_MARKERS = OFF_MARKERS - {"DO"}


class SisqualProblem5ILP:
    """Hour-based ILP for the Sisqual bundle using the weighted MathematicalDefinition5 model."""

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
        self.date_by_day = {day: datetime.strptime(day, "%Y-%m-%d").date() for day in self.days}
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.days)
        self.skills = parse_skill_codes(self.problem)
        self.time_slots = build_half_hour_slots(self.work_periods)
        self.coverage_by_period = build_period_slot_map(self.work_periods, self.time_slots)
        self.alpha = parse_demand_minimums(self.base_dir, self.problem, self.coverage_by_period)
        self.open_days = parse_open_days(self.days, self.alpha)
        self.closed_days = set(self.days) - set(self.open_days)
        self.objective1_weight, self.objective2_weights, self.objective3_weight, self.objective4_weight = (
            parse_soft_objectives(self.problem)
        )
        self.variable_days_off_active = self.objective4_weight > 0
        self.day_modes = self._build_day_modes()
        self.assignments = self._build_assignments()
        self.levels = sorted(
            {
                level
                for employee in self.employees
                for skill, level in employee["skill_levels"].items()
                if skill != self.staff_team_code
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
        self.weeks = self._group_open_days_by_week()

        self.model = None
        self.x = {}
        self.workday = {}
        self.y = {}
        self.y_level = {}
        self.shortage = {}
        self.level_shortage = {}
        self.preferred_day_work = {}
        self.status = None
        self.objective_value = None

    def _build_day_modes(self) -> Dict[Tuple[str, str], str]:
        day_modes = {}
        for employee in self.employees:
            employee_id = employee["id"]
            for day in self.days:
                marker = normalize_marker(self.schedule_markers[employee_id][day])
                if day in self.closed_days:
                    day_modes[(employee_id, day)] = "closed"
                elif marker in UNAVAILABLE_MARKERS or not marker:
                    day_modes[(employee_id, day)] = "unavailable"
                elif marker == "DO":
                    day_modes[(employee_id, day)] = "preferred_day_off"
                elif marker.startswith("EQUALS:"):
                    day_modes[(employee_id, day)] = "fixed_time_work"
                elif marker == "A" or marker.isdigit():
                    day_modes[(employee_id, day)] = "work_template"
                else:
                    raise ValueError(
                        f"Unsupported schedule marker '{self.schedule_markers[employee_id][day]}' "
                        f"for {employee_id} on {day}"
                    )
        return day_modes

    def _build_assignments(self) -> Dict[Tuple[str, str], List[Assignment]]:
        assignments = {}
        num_slots = len(self.time_slots)

        for employee in self.employees:
            employee_id = employee["id"]
            contract_hours = employee["contract_hours"]
            for day in self.days:
                key = (employee_id, day)
                mode = self.day_modes[key]
                marker = normalize_marker(self.schedule_markers[employee_id][day])
                day_assignments = []

                if mode in {"closed", "unavailable"}:
                    assignments[key] = day_assignments
                    continue

                if mode == "preferred_day_off" and not self.variable_days_off_active:
                    assignments[key] = day_assignments
                    continue

                if marker.startswith("EQUALS:"):
                    time_range = marker.split(":", 1)[1]
                    start_text, end_text = time_range.split("-", 1)
                    start_min = parse_hhmm(start_text)
                    end_min = parse_hhmm(end_text)
                    slot_indices = tuple(
                        slot.index
                        for slot in self.time_slots
                        if slot.start_min >= start_min and slot.end_min <= end_min
                    )
                    if not slot_indices:
                        raise ValueError(
                            f"No slots found for exact marker '{marker}' on {employee_id} {day}"
                        )
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

                hours = None
                if marker == "A":
                    hours = contract_hours
                elif marker == "DO":
                    hours = contract_hours
                elif marker.isdigit():
                    hours = int(marker)

                if hours is None or hours <= 0:
                    raise ValueError(
                        f"Missing or invalid hours for swappable marker '{self.schedule_markers[employee_id][day]}' "
                        f"on {employee_id} {day}"
                    )

                required_slots = hours * 2
                for start_idx in range(0, num_slots - required_slots + 1):
                    covered = tuple(range(start_idx, start_idx + required_slots))
                    start_min = self.time_slots[start_idx].start_min
                    end_min = self.time_slots[start_idx + required_slots - 1].end_min
                    day_assignments.append(
                        Assignment(
                            key=f"{employee_id}_{day}_{start_idx}_{required_slots}",
                            start_min=start_min,
                            end_min=end_min,
                            slot_indices=covered,
                        )
                    )

                if not day_assignments:
                    raise ValueError(
                        f"No feasible assignments generated for {employee_id} on {day} "
                        f"with marker '{self.schedule_markers[employee_id][day]}'"
                    )

                assignments[key] = day_assignments

        return assignments

    def _group_open_days_by_week(self) -> List[List[str]]:
        if not self.open_days:
            return []

        day_off_cfg = (
            self.problem.get("constraints", {})
            .get("advanced", {})
            .get("dayOffSwapping", {})
        )
        week_definition = str(day_off_cfg.get("weekDefinition", "monday-sunday")).strip().lower()

        groups = defaultdict(list)
        for day in self.open_days:
            current = self.date_by_day[day]
            if week_definition == "sunday-saturday":
                offset = (current.weekday() + 1) % 7
            else:
                offset = current.weekday()
            week_start = current - timedelta(days=offset)
            groups[week_start].append(day)

        return [groups[key] for key in sorted(groups)]

    def build_model(self):
        model = pulp.LpProblem("SisqualProblem5HourlyILP", pulp.LpMinimize)
        level_objectives_active = bool(self.objective2_weights) or self.objective3_weight > 0

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
                            level = employee["skill_levels"][skill]
                            self.y_level[(employee_id, day, slot.index, skill, level)] = pulp.LpVariable(
                                f"yprime_{employee_id}_{day.replace('-', '')}_{slot.index}_{skill}_L{level}",
                                cat="Binary",
                            )

        if self.objective2_weights:
            # z'_{dtsl} from ObjectiveFunction2 (1') and constraint (7), only for the
            # weighted (skill, level) pairs that were explicitly activated.
            for (day, slot_idx, skill, level), minimum in self.beta.items():
                if (skill, level) not in self.objective2_weights:
                    continue
                self.level_shortage[(day, slot_idx, skill, level)] = pulp.LpVariable(
                    f"zprime_{day.replace('-', '')}_{slot_idx}_{skill}_L{level}",
                    lowBound=0,
                    cat="Integer",
                )

        if self.objective4_weight > 0:
            # x'_{wd} from ObjectiveFunction4 (1''') and constraint (10): 1 when worker w is
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
                    lhs_terms = [self.y[(employee_id, day, slot.index, skill)] for skill in skills]
                    model += (
                        pulp.lpSum(lhs_terms) == pulp.lpSum(rhs_terms),
                        f"skill_cover_{employee_id}_{day}_{slot.index}",
                    )

        # Constraint (4)
        # "each worker w∈W cannot be assigned with more than 5 working days in
        # any set of 6 consecutive open days."
        for employee in self.employees:
            employee_id = employee["id"]
            for start in range(0, len(self.open_days) - 5):
                window = self.open_days[start:start + 6]
                model += (
                    pulp.lpSum(self.workday[(employee_id, day)] for day in window) <= 5,
                    f"max5in6_{employee_id}_{start}",
                )

        # Extra hard constraint from problem.json, kept from the original hourly model:
        # forbid consecutive-day assignment pairs whose overnight rest is below the
        # configured minimum rest hours.
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
        # the required value alpha_dts for each open day d∈D_o, each timeslot t∈T_d
        # and each skill s∈S."
        for (day, slot_idx, skill), minimum in self.alpha.items():
            coverage_terms = []
            if skill == self.staff_team_code:
                # Staff-level demand counts any worker present in that slot, regardless of
                # the operational skill assigned in y_{wdts}.
                for employee in self.employees:
                    employee_id = employee["id"]
                    for assignment in self.assignments[(employee_id, day)]:
                        if slot_idx in assignment.slot_indices:
                            coverage_terms.append(self.x[(employee_id, day, assignment.key)])
            else:
                for employee in self.employees:
                    employee_id = employee["id"]
                    y_key = (employee_id, day, slot_idx, skill)
                    if y_key in self.y:
                        coverage_terms.append(self.y[y_key])
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
                            model += (
                                self.y_level[(employee_id, day, slot.index, skill, level)]
                                == self.y[(employee_id, day, slot.index, skill)],
                                f"level_link_{employee_id}_{day}_{slot.index}_{skill}_L{level}",
                            )

        if self.objective2_weights:
            # Constraint (7)
            # "the value of variable z'_dtsl is at least the number of workers below
            # the required value beta_dtsl for each open day d∈D_o, each timeslot t∈T_d,
            # each skill s∈S and each competence level l∈L."
            for (day, slot_idx, skill, level), minimum in self.beta.items():
                if (skill, level) not in self.objective2_weights:
                    continue
                coverage_terms = []
                for employee in self.employees:
                    employee_id = employee["id"]
                    y_level_key = (employee_id, day, slot_idx, skill, level)
                    if y_level_key in self.y_level:
                        coverage_terms.append(self.y_level[y_level_key])
                model += (
                    self.level_shortage[(day, slot_idx, skill, level)] + pulp.lpSum(coverage_terms) >= minimum,
                    f"level_shortage_{day}_{slot_idx}_{skill}_L{level}",
                )

        if self.variable_days_off_active:
            # Constraint (8)
            # "each worker w∈W cannot be assigned with any working daily assignment
            # in the days that he is unavailable on each week."
            # This is already enforced day-by-day above through mode == "unavailable" -> x = 0.

            # Constraint (9)
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

            # Constraint (10)
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

        # ObjectiveFunction1 (1)
        # trying to fulfil as much as possible the minimum number alpha_dts of workers
        # in all open days, timeslots, and skills.
        if self.objective1_weight > 0:
            objective_terms.append(self.objective1_weight * pulp.lpSum(self.shortage.values()))

        # ObjectiveFunction2 (1')
        # for a given skill s and competence level l, trying to fulfil as much as
        # possible the minimum number beta_dtsl of workers in all open days and timeslots.
        for (skill, level), weight in sorted(self.objective2_weights.items()):
            if weight <= 0:
                continue
            pair_terms = [
                variable
                for (day, slot_idx, pair_skill, pair_level), variable in self.level_shortage.items()
                if pair_skill == skill and pair_level == level
            ]
            if pair_terms:
                objective_terms.append(weight * pulp.lpSum(pair_terms))

        # ObjectiveFunction3 (1'')
        # trying to obtain the best possible average competence level by minimizing
        # the linear score sum(l * y'_wdtsl).
        if self.objective3_weight > 0 and self.y_level:
            objective_terms.append(
                self.objective3_weight
                * pulp.lpSum(
                    level * variable
                    for (_, _, _, _, level), variable in self.y_level.items()
                )
            )

        # ObjectiveFunction4 (1''')
        # trying to assign as much as possible the preferable days-off by minimizing
        # the number of preferred day-offs that become worked days.
        if self.objective4_weight > 0 and self.preferred_day_work:
            objective_terms.append(
                self.objective4_weight * pulp.lpSum(self.preferred_day_work.values())
            )

        if objective_terms:
            model += pulp.lpSum(objective_terms), "weighted_mathematical_definition_5_objective"
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
        self.objective_value = pulp.value(self.model.objective)
        return self.status

    def solution_status(self) -> str:
        return pulp.LpStatus.get(self.status, "Unknown")

    def build_output_rows(self) -> List[List[str]]:
        rows = [["employee_id", *self.days]]

        # Rebuild the final CSV one employee row at a time, preserving original off markers
        # and decoding x/y back into readable time@skill segments.
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
                for assignment in self.assignments[(employee_id, day)]:
                    value = pulp.value(self.x.get((employee_id, day, assignment.key)))
                    if value is not None and value > 0.5:
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

    scheduler = SisqualProblem5ILP(
        problem_path,
        max_time_minutes=maxTime,
    )
    scheduler.build_model()
    scheduler.solve(gap_rel=float(kwargs.get("gap_rel", kwargs.get("gapRel", 0.01))))
    return scheduler.build_output_rows()


def main():
    parser = argparse.ArgumentParser(
        description="Solve the sisqual bundle with the weighted MathematicalDefinition5 hour-based ILP model."
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
