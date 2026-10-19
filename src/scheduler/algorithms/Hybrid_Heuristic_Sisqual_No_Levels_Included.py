"""Hybrid greedy heuristic for a schema v4 package, without competence levels.

Registered as "Hybrid_Heuristic_Sisqual_3". The greedy pass, the rest check,
fixed days and output are shared with the levels variant in
`algorithms.hybrid_sisqual_v4`. This variant ignores levels: a slot's skill is
the one with the most remaining need (scarcest skill on ties), and a block is
ranked by coverage alone. Restarts are ranked by (unassigned, shortage).
"""

from __future__ import annotations

from pathlib import Path

from algorithms.hybrid_sisqual_v4 import HybridSisqualV4, write_results_log
from problem_v4 import SolveDirectives, evaluate
from problem_v4.runtime import finish, load_for_solver

ALGORITHM = "Hybrid_Heuristic_Sisqual_3"


class Hybrid_Heuristic_Sisqual(HybridSisqualV4):
    """Greedy block assignment by remaining need; `choose_skill`/`rank_block` are the base's."""


def solve(problem_path=None, maxTime=None, restarts=10, day_order_mode=None, **kwargs):
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
            key = (kpis["unassigned"], kpis["total_shortage"])
            results.append({"restart_num": restart + 1, "day_order_mode": mode, "kpi_shortage": key[1]})
            if best_key is None or key < best_key:
                best_key, best_rows = key, rows

    write_results_log(kwargs.get("results_log_file") or kwargs.get("log_file")
                      or Path.cwd() / "heuristic_results_no_levels.csv",
                      ["restart_num", "day_order_mode", "kpi_shortage"], results)
    print(f"[Heuristica] Best total shortage after {restarts} restarts: {best_key[1]}")
    return finish(inst, best_rows, kwargs)
