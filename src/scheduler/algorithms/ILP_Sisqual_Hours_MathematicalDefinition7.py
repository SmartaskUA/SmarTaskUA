"""
Hour-based ILP for a schema v4 package, following `MathematicalDefinition7.pdf`.

The package is read by `problem_v4.load_package` - the one v4 parser - and the
model is declared over the index sets of `algorithms.md7_index`, shared with
the CP-SAT twin `CSP_Sisqual_Hours_MathematicalDefinition7.py`:
  - ObjectiveFunction1 (1): minimize total shortage against alpha_dts
  - ObjectiveFunction2 (1'): minimize priority-weighted skill assignment p_sl * y_wdts
  - ObjectiveFunction3 (1''): minimize worked preferred day-offs (day-off swap only)

Weights and the day-off swap are solve directives (`problem_v4.SolveDirectives`),
passed as keyword arguments; v4's `constraints.soft` carries none. A partial
result in the package fixes its days: their candidate set is the one shift the
result names, so every constraint below honours them unchanged.
"""

from __future__ import annotations

import argparse
import csv
from typing import List, Optional

import pulp

from algorithms.md7_index import MD7Index
from algorithms.sisqual_hours_utils import parse_max_time_seconds
from problem_v4 import Shift, SolveDirectives, V4Instance
from problem_v4.runtime import finish, load_for_solver, solver_failure

ALGORITHM = "ILP_Sisqual_Hours_MathematicalDefinition7"


class SisqualProblem5ILP:
    """MathematicalDefinition7 as a PuLP/CBC model over one v4 instance."""

    def __init__(self, inst: V4Instance, directives: Optional[SolveDirectives] = None, max_time_minutes=None):
        self.inst = inst
        self.directives = directives or SolveDirectives()
        self.index = MD7Index(inst, self.directives)
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)  # "10" -> 600; None -> no limit
        self.days = inst.days

        self.model = None
        self.x = {}
        self.workday = {}
        self.y = {}
        self.shortage = {}
        self.primary_objective = None
        self.status = None
        self.objective_value = None

    def build_model(self):
        inst, index = self.inst, self.index
        model = pulp.LpProblem("MathematicalDefinition7_v4", pulp.LpMinimize)

        # For every employee, day and candidate shift h in H_wd, x_wdh says whether
        # h was chosen. A fixed day's H_wd is the single shift the partial result
        # names (or empty for a fixed rest).
        for (eid, day), shifts in inst.candidates.items():
            for shift in shifts:
                self.x[(eid, day, shift.key)] = pulp.LpVariable(
                    f"x_{eid}_{day.replace('-', '')}_{shift.code}_{shift.slot_indices[0]}", cat="Binary"
                )

        # workday_wd: whether worker w works on day d. Used by (2), (4) and the swap.
        for employee in inst.employees:
            for day in inst.days:
                self.workday[(employee.id, day)] = pulp.LpVariable(
                    f"workday_{employee.id}_{day.replace('-', '')}", cat="Binary"
                )

        # y_wdts: worker w covers skill s in slot t, for demanded skills it holds.
        for (eid, day, t, skill) in index.y_level:
            self.y[(eid, day, t, skill)] = pulp.LpVariable(
                f"y_{eid}_{day.replace('-', '')}_{t}_{skill}", cat="Binary"
            )

        # z_dts: shortage against alpha_dts, for ObjectiveFunction1 and (5).
        for (day, t, skill), minimum in inst.alpha.items():
            self.shortage[(day, t, skill)] = pulp.LpVariable(
                f"z_{day.replace('-', '')}_{t}_{skill}", lowBound=0, upBound=minimum, cat="Integer"
            )

        # Constraint (2)
        # "each worker w can be assigned on each day d with at most one daily
        # assignment h in H_wd." A fixed day, a work cell and an unavailable cell
        # fix workday_wd; only the day-off swap leaves it to the solver.
        for employee in inst.employees:
            for day in inst.days:
                x_vars = [self.x[(employee.id, day, s.key)] for s in inst.candidates[(employee.id, day)]]
                workday = self.workday[(employee.id, day)]
                value = index.day_rule(employee.id, day)
                tag = f"{employee.id}_{day.replace('-', '')}"
                if value is None:
                    model += pulp.lpSum(x_vars) == workday, f"day_link_{tag}"
                else:
                    model += pulp.lpSum(x_vars) == value, f"day_fixed_{tag}"
                    model += workday == value, f"workday_fixed_{tag}"

        # Constraint (3), one link per axis
        # "a worker covering slot t with its chosen shift is assigned in t with one
        # of its skills" - once on every axis where it holds a demanded skill, so a
        # worker counts for Team/T1 and Responsibility/A in the same slot. Slots
        # where an axis has no demanded skill for the worker carry no link.
        for eid, day, t, axis, skills, shift_keys in index.links:
            model += (
                pulp.lpSum(self.y[(eid, day, t, s)] for s in skills)
                == pulp.lpSum(self.x[(eid, day, k)] for k in shift_keys),
                f"skill_cover_{eid}_{day.replace('-', '')}_{t}_{axis}",
            )

        # Constraint (4)
        # At most MaxConsecutiveWorkDays in any window one day longer, and at most
        # MaxConsecutiveWorkDaysInWeek days in any week.
        for eid, start, window, n in index.run_windows:
            model += (
                pulp.lpSum(self.workday[(eid, day)] for day in window) <= n,
                f"max_consecutive_{eid}_{start}",
            )
        for eid, week_index, week, cap in index.week_caps:
            model += (
                pulp.lpSum(self.workday[(eid, day)] for day in week) <= cap,
                f"max_week_days_{eid}_{week_index}",
            )

        # Minimum rest (MinDistanceBetweenShiftsInMinutes): no pair of shifts on
        # consecutive days closer than the minimum. Pairs against a fixed day were
        # already pruned from the open day's candidates by the parser.
        for n, (eid, day, a_key, next_day, b_key) in enumerate(index.rest_pairs):
            model += (
                self.x[(eid, day, a_key)] + self.x[(eid, next_day, b_key)] <= 1,
                f"min_rest_{eid}_{n}",
            )

        # Constraint (5)
        # "z_dts is at least the number of workers below alpha_dts."
        for (day, t, skill), minimum in inst.alpha.items():
            model += (
                self.shortage[(day, t, skill)]
                + pulp.lpSum(self.y[(eid, day, t, skill)] for eid in index.coverage.get((day, t, skill), ()))
                >= minimum,
                f"shortage_{day.replace('-', '')}_{t}_{skill}",
            )

        # Day-off swap only: each week keeps its template count n_wk, so working a
        # preferred day-off rests a work day elsewhere in the same week.
        if self.directives.allow_day_off_swap:
            for eid, week_index, week, required in index.swap_weeks():
                model += (
                    pulp.lpSum(self.workday[(eid, day)] for day in week) == required,
                    f"weekly_workdays_{eid}_{week_index}",
                )

        terms = []
        if self.directives.w1 > 0 and self.shortage:
            terms.append(self.directives.w1 * pulp.lpSum(self.shortage.values()))
        if self.directives.w2 > 0 and self.y:
            terms.append(self.directives.w2 * pulp.lpSum(
                index.priority_weight(eid, day, skill) * var for (eid, day, t, skill), var in self.y.items()
            ))
        worked_day_offs = index.day_off_days()
        if self.directives.w3 > 0 and worked_day_offs:
            terms.append(self.directives.w3 * pulp.lpSum(self.workday[key] for key in worked_day_offs))
        self.primary_objective = pulp.lpSum(terms) if terms else 0
        model += (self.primary_objective, "mathematical_definition_7") if terms else (0, "feasibility_only")
        self.model = model

    def solve(self, gap_rel: float = 0.01, verbose: bool = True):
        if self.model is None:
            self.build_model()
        solver = pulp.PULP_CBC_CMD(msg=1 if verbose else 0, timeLimit=self.max_time_seconds, gapRel=gap_rel)
        self.status = self.model.solve(solver)
        if self.has_solution():
            self.objective_value = pulp.value(self.primary_objective) or 0.0
        return self.status

    def has_solution(self) -> bool:
        # sol_status separates "optimal" (1) from "stopped with an incumbent" (2);
        # a time limit without one reports 0.
        return getattr(self.model, "sol_status", None) in (pulp.LpSolutionOptimal, pulp.LpSolutionIntegerFeasible)

    def solution_status(self) -> str:
        return pulp.LpStatus.get(self.status, "Unknown")

    def chosen_shift(self, eid: str, day: str) -> Optional[Shift]:
        for shift in self.inst.candidates[(eid, day)]:
            value = pulp.value(self.x[(eid, day, shift.key)])
            if value is not None and value > 0.5:
                return shift
        return None

    def build_output_rows(self) -> List[List[str]]:
        def covers(eid, day, t, skill):
            value = pulp.value(self.y[(eid, day, t, skill)])
            return value is not None and value > 0.5

        return self.index.output_rows(self.chosen_shift, covers)

    def export_csv(self, output_path: str):
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(self.build_output_rows())


def solve(problem_path=None, maxTime=None, **kwargs):
    """TaskManager / CLI entry. kwargs: w1, w2, w3, allow_day_off_swap, gap_rel, result_dir, task_id."""
    directives = SolveDirectives.from_kwargs(kwargs)
    task_id = str(kwargs.get("task_id", "manual"))
    inst = load_for_solver(problem_path, directives, task_id, ALGORITHM)
    scheduler = SisqualProblem5ILP(inst, directives, max_time_minutes=maxTime)
    scheduler.build_model()
    scheduler.solve(gap_rel=float(kwargs.get("gap_rel", kwargs.get("gapRel", 0.01))),
                    verbose=str(kwargs.get("verbose", True)).lower() not in {"0", "false", "no"})
    if not scheduler.has_solution():
        raise solver_failure(problem_path, task_id, ALGORITHM, scheduler.solution_status())
    return finish(inst, scheduler.build_output_rows(), kwargs)


def main():
    parser = argparse.ArgumentParser(description="Solve a schema v4 package with the MathematicalDefinition7 ILP.")
    parser.add_argument("problem", help="Path to a v4 package folder or its problem.json")
    parser.add_argument("--max-time", dest="max_time", default="10", help="Solver time limit in minutes")
    parser.add_argument("--gap-rel", dest="gap_rel", default="0.01", help="Relative MIP gap for CBC")
    parser.add_argument("--output", default=None, help="Optional output CSV of the schedule rows")
    parser.add_argument("--result-dir", default=None, help="Write the package plus result.json here")
    args = parser.parse_args()

    directives = SolveDirectives()
    inst = load_for_solver(args.problem, directives, "cli", ALGORITHM)
    scheduler = SisqualProblem5ILP(inst, directives, max_time_minutes=args.max_time)
    scheduler.build_model()
    scheduler.solve(gap_rel=float(args.gap_rel))
    print(f"Status: {scheduler.solution_status()}  Objective: {scheduler.objective_value}")
    if not scheduler.has_solution():
        raise SystemExit(1)
    rows = finish(inst, scheduler.build_output_rows(), {"result_dir": args.result_dir})
    if args.output:
        scheduler.export_csv(args.output)
        print(f"Wrote schedule to {args.output}")
    else:
        for row in rows[:5]:
            print(row[:4])


if __name__ == "__main__":
    main()
