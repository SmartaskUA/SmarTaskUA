"""
Hour-based CP-SAT model for a schema v4 package, following MathematicalDefinition7.

The twin of `ILP_Sisqual_Hours_MathematicalDefinition7.py`: the same model over
the same index sets (`algorithms.md7_index`), declared with OR-Tools CP-SAT:
  - ObjectiveFunction1: weighted total shortage against alpha_dts
  - ObjectiveFunction2: priority-weighted skill assignment p_sl * y_wdts
  - ObjectiveFunction3: worked preferred day-offs (day-off swap only)

CP-SAT needs integer objective coefficients; `SolveDirectives` weights are
integers, and alpha_dts is rounded up to whole workers by the parser.
"""

from __future__ import annotations

import argparse
import csv
from typing import List, Optional

from ortools.sat.python import cp_model

from algorithms.md7_index import MD7Index
from algorithms.sisqual_hours_utils import parse_max_time_seconds
from problem_v4 import Shift, SolveDirectives, V4Instance
from problem_v4.runtime import finish, load_for_solver, solver_failure

ALGORITHM = "CSP_Sisqual_Hours_MathematicalDefinition7"


class SisqualProblem5CSP:
    """MathematicalDefinition7 as a CP-SAT model over one v4 instance."""

    def __init__(self, inst: V4Instance, directives: Optional[SolveDirectives] = None, max_time_minutes=None):
        self.inst = inst
        self.directives = directives or SolveDirectives()
        self.index = MD7Index(inst, self.directives)
        self.max_time_seconds = parse_max_time_seconds(max_time_minutes)
        self.days = inst.days

        self.model = None
        self.solver = None
        self.x = {}
        self.workday = {}
        self.y = {}
        self.shortage = {}
        self.primary_objective_active = False
        self.status = None
        self.objective_value = None

    def build_model(self):
        inst, index = self.inst, self.index
        model = cp_model.CpModel()

        # x_wdh for every candidate shift h in H_wd (a fixed day has one, or none).
        for (eid, day), shifts in inst.candidates.items():
            for shift in shifts:
                self.x[(eid, day, shift.key)] = model.NewBoolVar(
                    f"x_{eid}_{day.replace('-', '')}_{shift.code}_{shift.slot_indices[0]}"
                )

        # workday_wd, used by (2), (4) and the swap.
        for employee in inst.employees:
            for day in inst.days:
                self.workday[(employee.id, day)] = model.NewBoolVar(f"workday_{employee.id}_{day.replace('-', '')}")

        # y_wdts for demanded skills the worker holds in slots its shifts can cover.
        for (eid, day, t, skill) in index.y_level:
            self.y[(eid, day, t, skill)] = model.NewBoolVar(f"y_{eid}_{day.replace('-', '')}_{t}_{skill}")

        # z_dts: shortage, bounded by the demand itself.
        for (day, t, skill), minimum in inst.alpha.items():
            self.shortage[(day, t, skill)] = model.NewIntVar(0, int(minimum), f"z_{day.replace('-', '')}_{t}_{skill}")

        # Constraint (2): at most one daily assignment; fixed days, work cells and
        # unavailable cells fix workday_wd, only the swap leaves it free.
        for employee in inst.employees:
            for day in inst.days:
                x_vars = [self.x[(employee.id, day, s.key)] for s in inst.candidates[(employee.id, day)]]
                workday = self.workday[(employee.id, day)]
                value = index.day_rule(employee.id, day)
                if value is None:
                    model.Add(sum(x_vars) == workday)
                else:
                    model.Add(sum(x_vars) == value)
                    model.Add(workday == value)

        # Constraint (3), one link per axis: a covered slot takes exactly one
        # demanded skill on each axis where the worker holds one.
        for eid, day, t, axis, skills, shift_keys in index.links:
            model.Add(
                sum(self.y[(eid, day, t, s)] for s in skills)
                == sum(self.x[(eid, day, k)] for k in shift_keys)
            )

        # Constraint (4): consecutive-day windows and the per-week count.
        for eid, start, window, n in index.run_windows:
            model.Add(sum(self.workday[(eid, day)] for day in window) <= n)
        for eid, week_index, week, cap in index.week_caps:
            model.Add(sum(self.workday[(eid, day)] for day in week) <= cap)

        # Minimum rest between shifts on consecutive days.
        for eid, day, a_key, next_day, b_key in index.rest_pairs:
            model.AddBoolOr([self.x[(eid, day, a_key)].Not(), self.x[(eid, next_day, b_key)].Not()])

        # Constraint (5): shortage plus coverage reaches alpha_dts.
        for (day, t, skill), minimum in inst.alpha.items():
            model.Add(
                self.shortage[(day, t, skill)]
                + sum(self.y[(eid, day, t, skill)] for eid in index.coverage.get((day, t, skill), ()))
                >= minimum
            )

        # Day-off swap only: each week keeps its template count n_wk.
        if self.directives.allow_day_off_swap:
            for eid, week_index, week, required in index.swap_weeks():
                model.Add(sum(self.workday[(eid, day)] for day in week) == required)

        terms = []
        if self.directives.w1 > 0:
            terms.extend(self.directives.w1 * var for var in self.shortage.values())
        if self.directives.w2 > 0:
            terms.extend(self.directives.w2 * index.priority_weight(eid, day, skill) * var
                         for (eid, day, t, skill), var in self.y.items())
        if self.directives.w3 > 0:
            terms.extend(self.directives.w3 * self.workday[key] for key in index.day_off_days())
        self.primary_objective_active = bool(terms)
        model.Minimize(sum(terms) if terms else 0)
        self.model = model

    def solve(self, gap_rel: float = 0.01, verbose: bool = True):
        if self.model is None:
            self.build_model()
        solver = cp_model.CpSolver()
        if self.max_time_seconds is not None:
            solver.parameters.max_time_in_seconds = float(self.max_time_seconds)
        if gap_rel is not None:
            solver.parameters.relative_gap_limit = float(gap_rel)
        solver.parameters.num_search_workers = 8
        solver.parameters.log_search_progress = bool(verbose)
        self.status = solver.Solve(self.model)
        self.solver = solver
        if self.has_solution():
            self.objective_value = int(round(solver.ObjectiveValue())) if self.primary_objective_active else 0
        return self.status

    def has_solution(self) -> bool:
        return self.status in (cp_model.OPTIMAL, cp_model.FEASIBLE)

    def solution_status(self) -> str:
        if self.solver is not None and self.status is not None:
            return self.solver.StatusName(self.status)
        return "Unknown"

    def chosen_shift(self, eid: str, day: str) -> Optional[Shift]:
        for shift in self.inst.candidates[(eid, day)]:
            if self.solver.Value(self.x[(eid, day, shift.key)]) > 0:
                return shift
        return None

    def build_output_rows(self) -> List[List[str]]:
        return self.index.output_rows(
            self.chosen_shift,
            lambda eid, day, t, skill: self.solver.Value(self.y[(eid, day, t, skill)]) > 0,
        )

    def export_csv(self, output_path: str):
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(self.build_output_rows())


def solve(problem_path=None, maxTime=None, **kwargs):
    """TaskManager / CLI entry. kwargs: w1, w2, w3, allow_day_off_swap, gap_rel, result_dir, task_id."""
    directives = SolveDirectives.from_kwargs(kwargs)
    task_id = str(kwargs.get("task_id", "manual"))
    inst = load_for_solver(problem_path, directives, task_id, ALGORITHM)
    scheduler = SisqualProblem5CSP(inst, directives, max_time_minutes=maxTime)
    scheduler.build_model()
    scheduler.solve(gap_rel=float(kwargs.get("gap_rel", kwargs.get("gapRel", 0.01))),
                    verbose=str(kwargs.get("verbose", True)).lower() not in {"0", "false", "no"})
    if not scheduler.has_solution():
        raise solver_failure(problem_path, task_id, ALGORITHM, scheduler.solution_status())
    return finish(inst, scheduler.build_output_rows(), kwargs)


def main():
    parser = argparse.ArgumentParser(description="Solve a schema v4 package with the MathematicalDefinition7 CP-SAT model.")
    parser.add_argument("problem", help="Path to a v4 package folder or its problem.json")
    parser.add_argument("--max-time", dest="max_time", default="10", help="Solver time limit in minutes")
    parser.add_argument("--gap-rel", dest="gap_rel", default="0.01", help="Relative gap limit for CP-SAT")
    parser.add_argument("--output", default=None, help="Optional output CSV of the schedule rows")
    parser.add_argument("--result-dir", default=None, help="Write the package plus result.json here")
    args = parser.parse_args()

    directives = SolveDirectives()
    inst = load_for_solver(args.problem, directives, "cli", ALGORITHM)
    scheduler = SisqualProblem5CSP(inst, directives, max_time_minutes=args.max_time)
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
