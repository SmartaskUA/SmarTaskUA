"""Hybrid greedy heuristic for a schema v4 package, with competence levels.

The greedy pass, the rest check, fixed days and output are shared with the
no-levels variant in `algorithms.hybrid_sisqual_v4`. What this variant adds is
level-awareness from MathematicalDefinition7's ObjectiveFunction2: among skills
with the same remaining need, the one with the lower p_sl (higher-priority tier
for the worker's level) wins, and among blocks with the same coverage the one
paying less p_sl does. Restarts are ranked by (unassigned, shortage, p_sl cost).
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import List

from algorithms.hybrid_sisqual_v4 import HybridSisqualV4, write_results_log
from problem_v4 import Employee, SolveDirectives, evaluate
from problem_v4.runtime import finish, load_for_solver

ALGORITHM = "Hybrid_Heuristic_Sisqual_Levels_Included"


class Hybrid_Heuristic_Sisqual(HybridSisqualV4):
    """Greedy block assignment that breaks ties by competence-level priority."""

    def choose_skill(self, employee: Employee, day: str, slot_idx: int, skills: List[str]) -> str:
        # most remaining need, then the lowest p_sl for this worker's level, then the scarcest skill
        return min(skills, key=lambda s: (
            -self.remaining(day, slot_idx, s),
            self.inst.priority_weight(s, self.inst.level(employee.id, day, s)),
            self.skill_employee_count.get(s, 1),
        ))

    def rank_block(self, coverage: int, priority_cost: int) -> tuple:
        return (-coverage, priority_cost, random.random())


def solve(problem_path=None, maxTime=None, restarts=5, day_order_mode=None, **kwargs):
    """TaskManager / CLI entry. `day_order_mode` is 1, 2, 3 or a list; default all three."""
    directives = SolveDirectives.from_kwargs(kwargs)
    task_id = str(kwargs.get("task_id", "manual"))
    inst = load_for_solver(problem_path, directives, task_id, ALGORITHM)
    scheduler = Hybrid_Heuristic_Sisqual(inst, directives, max_time_minutes=maxTime)

    modes = [1, 2, 3] if day_order_mode is None else (
        day_order_mode if isinstance(day_order_mode, (list, tuple)) else [int(day_order_mode)])
    best_rows, best_key, results = None, None, []
    for restart in range(int(restarts)):
        for mode in modes:
            scheduler.Minimuns(day_order_mode=mode)
            rows = scheduler.build_output_rows()
            kpis = evaluate(inst, rows)
            key = (kpis["unassigned"], kpis["total_shortage"], kpis["priority_cost"])
            results.append({"restart_num": restart + 1, "day_order_mode": mode,
                            "unassigned_count": key[0], "kpi_shortage": key[1], "priority_cost": key[2]})
            if best_key is None or key < best_key:
                best_key, best_rows = key, rows

    write_results_log(kwargs.get("results_log_file") or Path.cwd() / "heuristic_results_levels.csv",
                      ["restart_num", "day_order_mode", "unassigned_count", "kpi_shortage", "priority_cost"],
                      results)
    print(f"[Heuristica] Best (unassigned_count, kpi_shortage, priority_cost) "
          f"after {restarts} restarts: {best_key}")
    return finish(inst, best_rows, kwargs)
