"""
Hour-based CP-SAT model for the Sisqual bundle following MathematicalDefinition5.

This mirrors `ILP_Sisqual_Hours_MathematicalDefinition5.py` while using
OR-Tools CP-SAT:
  - ObjectiveFunction1: weighted total shortage against alpha_dts
  - ObjectiveFunction2: weighted level-specific shortage against beta_dtsl
  - ObjectiveFunction3: linear competence score l * y'_wdtsl
  - ObjectiveFunction4: work assigned on preferred day-offs x'_wd
  - ObjectiveFunction5: assignment to lower-priority skills

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
from typing import Dict, List

from ortools.sat.python import cp_model

from algorithms.sisqual_hours_utils import (
    build_half_hour_slots,
    build_objective1_priority_coefficients,
    build_objective1_priority_index,
    build_objective5_priority_penalties,
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
    parse_skill_switch_phase2_max_seconds,
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
        self.objective1_priority_index = build_objective1_priority_index(
            self.alpha,
            self.coverage_priority_tiers,
        )
        self.objective1_priority_weights = build_objective1_priority_coefficients(
            self.coverage_priority_tiers,
        )
        self.objective5_skill_priority = build_objective5_skill_priority(
            self.employees,
            self.coverage_priority_tiers,
        )  # {("20051291", "Storage"): 0, ("20072412", "Management"): 1, ("20054956", "Checkout"): 4, ...}
        self.objective5_priority_penalties = build_objective5_priority_penalties(
            self.coverage_priority_tiers,
        )
        self.objective_hierarchy_scale = max(self.objective1_priority_weights.values(), default=1)

        (
            self.objective1_weight,
            self.objective2_weights,
            self.objective3_weight,
            self.objective4_weight,
            self.objective5_weight,
            self.skill_switch_weight,
        ) = parse_soft_objectives(self.problem)  # e.g. (1000.0, {}, 0.0, 10.0, 100.0, 0.0)
        self.skill_switch_phase2_max_seconds = parse_skill_switch_phase2_max_seconds(self.problem)
        self._validate_objective_weights()

        # Objective 4 activates the "swap preferred day-off" behavior. When it
        # is inactive, template DO days remain fixed off exactly like the input.
        self.variable_days_off_active = self.objective4_weight > 0  # True when preferred day-offs may be swapped within the week
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
        self.beta = parse_beta_requirements(
            self.base_dir,
            self.problem,
            self.coverage_by_period,
            self.time_slots,
            self.open_days,
            self.objective2_weights,
        )  # {(day, slot, skill, level): minimum, ...} when ObjectiveFunction2 is configured; otherwise {}
        self.weeks = group_open_days_by_week(
            self.problem,
            self.open_days,
            self.date_by_day,
        )  # [["2025-10-01", ..., "2025-10-05"], ["2025-10-06", ..., "2025-10-12"], ...]

        #   x[(w, d, h)]              -> chosen daily assignment
        #   workday[(w, d)]           -> whether worker w works on day d
        #   y[(w, d, t, s)]           -> slot/team assignment
        #   y_level[(w, d, t, s, l)]  -> slot/team/level assignment
        #   switch[(w, d, t)]         -> skill change between adjacent worked slots
        #   shortage[(d, t, s)]       -> z_dts coverage shortage
        #   level_shortage[(d,t,s,l)] -> z'_dtsl level shortage
        #   preferred_day_work[(w,d)] -> x'_wd preferred day-off worked
        self.model = None
        self.solver = None
        self.x = {}  # {("20072412", "2025-10-01", "A_510_990"): BoolVar(...), ...}
        self.workday = {}  # {("20072412", "2025-10-01"): BoolVar(...), ...}
        self.y = {}  # {("20072412", "2025-10-01", 5, "Management"): BoolVar(...), ...}
        self.y_level = {}  # {("20072412", "2025-10-01", 5, "Management", 1): BoolVar(...), ...}
        self.switch = {}  # {("20072412", "2025-10-01", 5): BoolVar(...), ...}
        self.shortage = {}  # {("2025-10-01", 5, "Checkout"): IntVar(...), ...}
        self.shortage_unit = {}  # {("2025-10-01", 5, "Checkout", 1): BoolVar(...), ...}
        self.level_shortage = {}  # {("2025-10-01", 5, "Checkout", 2): IntVar(...), ...}
        self.preferred_day_work = {}  # {("20072412", "2025-10-05"): BoolVar(...), ...}
        self.coverage_terms_cache = {}  # {("2025-10-01", 5, "Checkout"): [y_var, y_var, ...], ...}
        self.primary_objective = None
        self.primary_objective_active = False
        self.switch_objective = None
        self.status = None
        self.objective_value = None
        self.switch_objective_value = None

    def _validate_objective_weights(self):
        _int_weight(self.objective1_weight, "ObjectiveFunction1")
        for (skill, level), weight in self.objective2_weights.items():
            _int_weight(weight, f"ObjectiveFunction2 {skill}:{level}")
        _int_weight(self.objective3_weight, "ObjectiveFunction3")
        _int_weight(self.objective4_weight, "ObjectiveFunction4")
        _int_weight(self.objective5_weight, "ObjectiveFunction5")
        _int_weight(self.skill_switch_weight, "minimize_skill_switches")

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

    def _add_skill_switch_minimization(self):
        if self.model is None or self.switch:
            return

        model = self.model
        for employee in self.employees:
            employee_id = employee["id"]
            skills = employee["assignable_skills"]
            if len(skills) < 2:
                continue
            for day in self.days:
                adjacent_slots = set()
                for assignment in self.assignments[(employee_id, day)]:
                    for left_slot, right_slot in zip(assignment.slot_indices, assignment.slot_indices[1:]):
                        if right_slot == left_slot + 1:
                            adjacent_slots.add(left_slot)
                for slot_idx in sorted(adjacent_slots):
                    switch_var = model.NewBoolVar(
                        f"switch_{employee_id}_{day.replace('-', '')}_{slot_idx}"
                    )
                    self.switch[(employee_id, day, slot_idx)] = switch_var

                    left_work_terms = [
                        self.y[(employee_id, day, slot_idx, skill)]
                        for skill in skills
                    ]
                    right_work_terms = [
                        self.y[(employee_id, day, slot_idx + 1, skill)]
                        for skill in skills
                    ]
                    # Do not count a boundary unless both adjacent slots are
                    # actually worked by this employee.
                    model.Add(switch_var <= sum(left_work_terms))
                    model.Add(switch_var <= sum(right_work_terms))
                    for first_skill in skills:
                        first_y = self.y[(employee_id, day, slot_idx, first_skill)]
                        for second_skill in skills:
                            second_y = self.y[(employee_id, day, slot_idx + 1, second_skill)]
                            if first_skill == second_skill:
                                # Same skill on both sides forces switch=0.
                                model.Add(switch_var <= 2 - first_y - second_y)
                                continue
                            # Different skills on adjacent worked slots force switch=1.
                            model.Add(switch_var >= first_y + second_y - 1)

        self.switch_objective = sum(self.switch.values()) if self.switch else 0

    def _phase2_time_limit_seconds(self):
        if self.max_time_seconds is None:
            return self.skill_switch_phase2_max_seconds
        return min(self.max_time_seconds, self.skill_switch_phase2_max_seconds)

    def _fix_phase2_daily_assignments(self, solver):
        """Keep phase 2 focused on skill labels, not the whole shift schedule.

        Phase 1 decides the business schedule: which daily block each employee
        works, whether a flexible day-off is used, and the primary Objective 1-5
        value. Phase 2 is only a cleanup tie-breaker, so fixing x/workday keeps
        the selected shifts intact and lets CP-SAT spend the short phase-2 time
        cap on reducing role switches within those already-chosen worked slots.
        """

        for variable in self.x.values():
            self.model.Add(variable == solver.Value(variable))
        for variable in self.workday.values():
            self.model.Add(variable == solver.Value(variable))

    def _lock_phase2_minimum_shortages(self, solver):
        """Prevent switch cleanup from worsening minimum coverage.

        The primary objective lock protects the weighted MD5 score, but equal or
        better weighted scores can still reshuffle raw minimum gaps across skills
        or priority tiers. Switch minimization is only a display/operations
        cleanup, so phase 2 may reduce existing shortages but must not increase
        any shortage value that phase 1 already achieved.
        """

        for variable in self.shortage.values():
            self.model.Add(variable <= solver.Value(variable))
        for variable in self.shortage_unit.values():
            self.model.Add(variable <= solver.Value(variable))
        for variable in self.level_shortage.values():
            self.model.Add(variable <= solver.Value(variable))

    def _add_phase2_solution_hint(self, solver):
        hinted = set()

        def add_hint(variable, value):
            if variable is None or variable in hinted:
                return
            self.model.AddHint(variable, int(value))
            hinted.add(variable)

        for variable in self.x.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.workday.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.y.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.y_level.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.shortage.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.shortage_unit.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.level_shortage.values():
            add_hint(variable, solver.Value(variable))
        for variable in self.preferred_day_work.values():
            add_hint(variable, solver.Value(variable))
        for (employee_id, day, slot_idx), switch_var in self.switch.items():
            left_skill = None
            right_skill = None
            for employee in self.employees:
                if employee["id"] != employee_id:
                    continue
                for skill in employee["assignable_skills"]:
                    if solver.Value(self.y[(employee_id, day, slot_idx, skill)]) > 0:
                        left_skill = skill
                    if solver.Value(self.y[(employee_id, day, slot_idx + 1, skill)]) > 0:
                        right_skill = skill
                break
            add_hint(switch_var, 1 if left_skill and right_skill and left_skill != right_skill else 0)

    def build_model(self):
        model = cp_model.CpModel()
        level_objectives_active = bool(self.objective2_weights) or self.objective3_weight > 0
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
            if self.objective1_weight > 0:
                for nth_worker in range(1, int(minimum) + 1):
                    self.shortage_unit[(day, slot_idx, skill, nth_worker)] = model.NewBoolVar(
                        f"zu_{day.replace('-', '')}_{slot_idx}_{skill}_{nth_worker}"
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

        if self.objective2_weights:
            # Level-specific shortage z'_{dtsl} for ObjectiveFunction2. Only
            # configured (skill, level) pairs are created to keep the CP model smaller.
            for (day, slot_idx, skill, level), minimum in self.beta.items():
                if (skill, level) not in self.objective2_weights:
                    continue
                self.level_shortage[(day, slot_idx, skill, level)] = model.NewIntVar(
                    0,
                    int(minimum),
                    f"zprime_{day.replace('-', '')}_{slot_idx}_{skill}_L{level}",
                )

        if self.objective4_weight > 0:
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
        # days are forced to 0. Preferred DO behavior depends on Objective 4.
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
            for nth_worker in range(1, int(minimum) + 1):
                unit_key = (day, slot_idx, skill, nth_worker)
                if unit_key not in self.shortage_unit:
                    continue
                # Unit shortages make priorityHierarchy a true hierarchy. Missing
                # one worker in a higher tier is more important than two misses in
                # the next lower tier.
                model.Add(
                    sum(coverage_terms)
                    + nth_worker * self.shortage_unit[unit_key]
                    >= nth_worker
                )

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

        if self.objective2_weights:
            # Constraint (7)
            # Level-specific shortage z'_dtsl plus coverage at that exact level
            # must reach beta_dtsl for each activated skill/level requirement.
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
            # Constraint (8)
            # Unavailable days are already enforced above through mode == "unavailable".
            #
            # Constraint (9)
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

            # Constraint (10)
            # x'_{wd} is exactly the workday indicator on preferred day-off cells,
            # so ObjectiveFunction4 can count how many DO days were worked.
            for employee in self.employees:
                employee_id = employee["id"]
                for day in self.days:
                    if self.day_modes[(employee_id, day)] == "preferred_day_off":
                        model.Add(
                            self.preferred_day_work[(employee_id, day)]
                            == self.workday[(employee_id, day)]
                        )

        objective_terms = []
        hierarchy_objective_active = self.objective1_weight > 0 or self.objective5_weight > 0
        hierarchy_scale = self.objective_hierarchy_scale if hierarchy_objective_active else 1

        # ObjectiveFunction1
        # Minimize shortage against alpha_dts across all open days, half-hour
        # slots, and skills. Shortage is scored per demanded worker unit so
        # priorityHierarchy is respected: one miss in a higher tier is more
        # important than two misses in the next lower tier.
        objective1_weight = _int_weight(self.objective1_weight, "ObjectiveFunction1")
        if objective1_weight > 0:
            if self.shortage_unit:
                objective_terms.extend(
                    objective1_weight
                    * self.objective1_priority_weights[
                        self.objective1_priority_index[(day, slot_idx, skill, nth_worker)]
                    ]
                    * variable
                    for (day, slot_idx, skill, nth_worker), variable in self.shortage_unit.items()
                )
            else:
                objective_terms.extend(
                    objective1_weight * variable
                    for variable in self.shortage.values()
                )

        # ObjectiveFunction2
        # For configured skill/level pairs, minimize shortage against beta_dtsl.
        for (skill, level), weight in sorted(self.objective2_weights.items()):
            objective2_weight = _int_weight(weight, f"ObjectiveFunction2 {skill}:{level}")
            if objective2_weight <= 0:
                continue
            objective2_weight *= hierarchy_scale
            objective_terms.extend(
                objective2_weight * variable
                for (day, slot_idx, pair_skill, pair_level), variable in self.level_shortage.items()
                if pair_skill == skill and pair_level == level
            )

        # ObjectiveFunction3
        # Minimize the linear competence score sum(l * y'_{wdtsl}).
        objective3_weight = _int_weight(self.objective3_weight, "ObjectiveFunction3")
        if objective3_weight > 0 and self.y_level:
            objective3_weight *= hierarchy_scale
            objective_terms.extend(
                objective3_weight * level * variable
                for (_, _, _, _, level), variable in self.y_level.items()
            )

        # ObjectiveFunction4
        # Minimize preferred day-offs that become worked days.
        objective4_weight = _int_weight(self.objective4_weight, "ObjectiveFunction4")
        if objective4_weight > 0 and self.preferred_day_work:
            objective4_weight *= hierarchy_scale
            objective_terms.extend(
                objective4_weight * variable
                for variable in self.preferred_day_work.values()
            )

        # ObjectiveFunction5
        # Prefer assigning multi-skilled workers to higher-priority Sisqual teams.
        # Penalties are cumulative hierarchy weights, not raw rank numbers, so one
        # higher-priority downgrade is more important than two downgrades one level
        # below it.
        objective5_weight = _int_weight(self.objective5_weight, "ObjectiveFunction5")
        if objective5_weight > 0 and self.y:
            fallback_tier = len(self.coverage_priority_tiers)
            objective_terms.extend(
                objective5_weight
                * self.objective5_priority_penalties[
                    self.objective5_skill_priority.get((employee_id, skill), fallback_tier)
                ]
                * variable
                for (employee_id, _, _, skill), variable in self.y.items()
            )

        self.primary_objective = sum(objective_terms) if objective_terms else 0
        self.primary_objective_active = bool(objective_terms)
        self.switch_objective = 0

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

            if self.skill_switch_weight > 0:
                # Secondary lexicographic tie-breaker: switch_{wdt}=1 when a worker
                # changes assigned skill between adjacent worked half-hour slots. These
                # variables are created after phase 1 so the primary MD5 solve remains
                # the same size as before this tie-breaker existed.
                self._add_skill_switch_minimization()
            if self.skill_switch_weight > 0 and self.switch:
                if self.primary_objective_active:
                    # Lexicographic phase 2: keep every Objective 1-5 tradeoff exactly
                    # as good as phase 1, then use switch count only to break ties.
                    self.model.Add(self.primary_objective <= primary_value)
                # The tie-breaker should not spend its limited time moving shifts
                # around. We freeze the phase-1 daily block choices and only allow
                # skill assignments inside those blocks to change.
                self._lock_phase2_minimum_shortages(solver)
                self._fix_phase2_daily_assignments(solver)
                # With the primary objective locked, minimizing switches cannot reduce
                # covered minimums or worsen Objective 5.
                self.model.Minimize(self.switch_objective)

                phase2_solver = cp_model.CpSolver()
                if self.max_time_seconds is not None:
                    phase2_solver.parameters.max_time_in_seconds = float(self._phase2_time_limit_seconds())
                else:
                    phase2_solver.parameters.max_time_in_seconds = float(self._phase2_time_limit_seconds())
                if gap_rel is not None:
                    phase2_solver.parameters.relative_gap_limit = float(gap_rel)
                phase2_solver.parameters.num_search_workers = 8
                phase2_solver.parameters.log_search_progress = True

                self._add_phase2_solution_hint(solver)
                phase2_status = phase2_solver.Solve(self.model)
                if phase2_status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                    self.status = phase2_status
                    self.solver = phase2_solver
                    self.objective_value = (
                        phase2_solver.Value(self.primary_objective)
                        if self.primary_objective_active
                        else 0
                    )
                    self.switch_objective_value = phase2_solver.Value(self.switch_objective)
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
