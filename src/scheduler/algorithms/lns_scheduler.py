"""
lns_scheduler.py
----------------
Scheduler ALNS para o problema Sisqual (Versão 1 do modelo matemático).

Usa a biblioteca `alns` (pip install alns) para:
  - Gestão adaptativa de pesos dos operadores (RouletteWheel)
  - Critério de aceitação Simulated Annealing
  - Loop de iterações com estatísticas integradas

Dois modos de repair configuráveis via repair_mode=:
  "greedy"  — rápido, centenas de iterações por minuto
  "ilp"     — sub-problema exacto com PuLP/CBC, óptimo no neighbourhood

Os dois modos podem ser combinados num mesmo run:
  - Fase 1 (exploração): repair greedy com temperatura alta
  - Fase 2 (intensificação): repair ILP com temperatura baixa

Destroy operators
-----------------
  D1 — Random Employee Days
  D2 — Worst Shortage Days
  D3 — Shift-Time Perturbation
  D4 — Skill Reallocation Only

Uso
---
  from lns_scheduler import LNSScheduler

  # modo greedy puro
  s = LNSScheduler("problem.json")
  s.run(time_limit_seconds=300, repair_mode="greedy")

  # modo ILP puro
  s.run(time_limit_seconds=300, repair_mode="ilp", ilp_time_limit=3)

  # modo híbrido (greedy fase 1, ILP fase 2)
  s.run(time_limit_seconds=300, repair_mode="hybrid")

  rows = s.build_output_rows()

CLI:
  python lns_scheduler.py problem.json --time 5 --repair ilp --output sched.csv
"""

from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

# biblioteca alns
from alns import ALNS
from alns.accept import SimulatedAnnealing
from alns.select  import RouletteWheel
from alns.stop import MaxRuntime

# utilitários do ILP existente
from algorithms.sisqual_hours_utils import (
    OFF_MARKERS,
    build_assignments as _build_assignments_ilp,
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

from .lns_solution import Assignment, CoverageTracker, Solution
from .lns_constraints import MIN_REST_HOURS_DEFAULT, is_off_marker
from .lns_destroy import (
    destroy_random_employees,
    destroy_worst_shortage_days,
    destroy_shift_time,
    destroy_skill_only,
    rollback_destroy,
)
from .lns_repair import (
    build_greedy_initial_solution,
    repair,
    DEFAULT_PRIORITY,
    STAFF_TEAM,
)


# ---------------------------------------------------------------------------
# Estado da solução encapsulado para a biblioteca alns
# ---------------------------------------------------------------------------

class ScheduleState:
    """
    Wrapper que a biblioteca alns espera: tem um atributo `objective_value`
    e um método `copy()`.

    Internamente guarda a Solution + CoverageTracker + contexto do problema
    para que os operadores de destroy/repair possam actuar directamente.
    """

    def __init__(
        self,
        solution:  Solution,
        tracker:   CoverageTracker,
        ctx:       "LNSScheduler",
    ):
        self.solution = solution
        self.tracker  = tracker
        self.ctx      = ctx   # referência ao scheduler (problema, params, etc.)

        # Último destroy/rollback — usado para reverter se SA rejeitar
        self._last_rollback: Optional[list] = None

    @property
    def objective_value(self) -> float:
        """A biblioteca alns minimiza este valor."""
        return float(self.tracker.total_shortage())

    def objective(self) -> float:
        return self.objective_value

    def copy(self) -> "ScheduleState":
        """
        Cópia rasa da solução + rebuild do tracker.
        Chamada pela biblioteca quando é encontrado um novo best.
        """
        new_sol = self.solution.copy()
        new_tracker = CoverageTracker(self.ctx.alpha, self.ctx.employees)
        new_tracker.rebuild_from_solution(new_sol)
        return ScheduleState(new_sol, new_tracker, self.ctx)


# ---------------------------------------------------------------------------
# Adaptador: converte assignments do ILP para dataclasses LNS
# ---------------------------------------------------------------------------

def _adapt_assignments(
    ilp_assignments,
    time_slots,
) -> Dict[Tuple[str, str], List[Assignment]]:
    result: Dict[Tuple[str, str], List[Assignment]] = {}
    for (emp_id, day), blocks in ilp_assignments.items():
        result[(emp_id, day)] = [
            Assignment(
                key=b.key, label=b.label,
                start_min=b.start_min, end_min=b.end_min,
                slot_indices=tuple(b.slot_indices),
            )
            for b in blocks
        ]
    return result


# ---------------------------------------------------------------------------
# Fábrica de operadores de destroy compatíveis com a biblioteca alns
# ---------------------------------------------------------------------------

def _make_destroy_op(scheduler: "LNSScheduler", op_name: str):
    """
    Retorna uma função com assinatura (state, rng) → state
    conforme a API da biblioteca alns.

    O destroy é feito in-place na cópia que a biblioteca passou,
    guardando o rollback em state._last_rollback para poder reverter.
    """
    rng_py = scheduler.rng   # random.Random — usado internamente

    def destroy_op(
        state: ScheduleState,
        rng: np.random.Generator,
        **kwargs,
    ) -> ScheduleState:
        solution = state.solution
        tracker  = state.tracker
        ctx      = state.ctx

        if op_name == "D1":
            destroyed, rollback = destroy_random_employees(
                solution, tracker,
                employees    = ctx.employees,
                days         = ctx.days,
                markers      = ctx.markers,
                q_employees  = rng_py.randint(1, 3),
                days_per_emp = rng_py.uniform(0.3, 0.7),
                rng          = rng_py,
            )
        elif op_name == "D2":
            destroyed, rollback = destroy_worst_shortage_days(
                solution, tracker,
                employees = ctx.employees,
                days      = ctx.days,
                n_days    = rng_py.randint(1, 3),
                rng       = rng_py,
            )
        elif op_name == "D3":
            destroyed, rollback = destroy_shift_time(
                solution, tracker,
                employees   = ctx.employees,
                days        = ctx.days,
                markers     = ctx.markers,
                q_employees = rng_py.randint(2, 5),
                rng         = rng_py,
            )
        else:  # D4
            destroyed, rollback = destroy_skill_only(
                solution, tracker,
                employees = ctx.employees,
                days      = ctx.days,
                q_pairs   = rng_py.randint(3, 8),
                rng       = rng_py,
            )

        # Guardar destroyed + rollback no estado para o repair poder actuar
        state._destroyed        = destroyed
        state._last_rollback    = rollback

        return state

    destroy_op.__name__ = op_name
    return destroy_op


def _make_repair_op(
    scheduler: "LNSScheduler",
    mode: str,
    ilp_time_limit: int,
):
    """
    Retorna uma função com assinatura (state, rng) → state.

    A reparação usa os destroyed guardados pelo destroy_op anterior.
    Se não houver destroyed (D4 retornou lista vazia), faz fallback D1.
    """
    def repair_op(
        state: ScheduleState,
        rng: np.random.Generator,
        **kwargs,
    ) -> ScheduleState:
        ctx       = state.ctx
        destroyed = getattr(state, "_destroyed", [])

        if not destroyed:
            # Fallback: destroy_random_employees e repair imediato
            destroyed, rollback = destroy_random_employees(
                state.solution, state.tracker,
                employees=ctx.employees, days=ctx.days,
                markers=ctx.markers, q_employees=1,
                days_per_emp=0.5, rng=ctx.rng,
            )
            state._destroyed     = destroyed
            state._last_rollback = rollback

        skill_only = {
            (e, d) for e, d, *rest in state._last_rollback
            if len(rest) == 3 and rest[2] == "skill_only"
        }

        repair(
            destroyed      = destroyed,
            solution       = state.solution,
            tracker        = state.tracker,
            employees      = ctx.employees,
            days           = ctx.days,
            assignments_by = ctx.assignments_by,
            markers        = ctx.markers,
            alpha          = ctx.alpha,
            time_slots     = ctx.time_slots,
            priority       = ctx.priority,
            min_rest_hours = ctx.min_rest_hours,
            skill_only_set = skill_only,
            mode           = mode,
            ilp_time_limit = ilp_time_limit,
        )

        return state

    repair_op.__name__ = f"repair_{mode}"
    return repair_op


# ---------------------------------------------------------------------------
# LNSScheduler
# ---------------------------------------------------------------------------

class LNSScheduler:
    """
    Scheduler ALNS usando a biblioteca `alns` com:
      - RouletteWheel para selecção adaptativa de operadores
      - SimulatedAnnealing como critério de aceitação
      - Repair greedy ou ILP (sub-problema exacto com PuLP/CBC)
    """

    STAFF_TEAM = "Employees"

    def __init__(
        self,
        problem_json_path: str,
        max_time_minutes=1,
        seed: int = 42,
    ):
        self.problem_json_path = Path(problem_json_path).resolve()
        self.base_dir          = self.problem_json_path.parent
        self.problem           = load_problem_json(self.problem_json_path)
        self.max_time_seconds  = parse_max_time_seconds(max_time_minutes)

        import random
        self.rng = random.Random(seed)
        self.np_rng = np.random.default_rng(seed)

        # Parse do problema (idêntico ao ILP)
        self.min_rest_hours   = self._parse_min_rest_hours()
        self.contract_hours   = parse_contract_hours(self.problem)
        self.work_periods     = parse_work_periods(self.problem)
        self.employees        = parse_employees(self.problem, self.contract_hours)
        for emp in self.employees:
            emp["assignable_skills"] = tuple(
                s for s in emp["skills"] if s != self.STAFF_TEAM
            )
        self.days             = parse_days(self.problem)
        self.schedule_markers = parse_schedule_input(
            self.base_dir, self.problem, self.days)
        self.skills           = parse_skill_codes(self.problem)
        self.time_slots       = build_half_hour_slots(self.work_periods)
        self.coverage_by_period = build_period_slot_map(
            self.work_periods, self.time_slots)
        self.alpha            = parse_demand_minimums(
            self.base_dir, self.problem, self.coverage_by_period)
        self.assignments_by   = _adapt_assignments(
            _build_assignments_ilp(
                self.employees, self.days, self.schedule_markers, self.time_slots),
            self.time_slots,
        )
        self.markers: Dict[Tuple[str, str], str] = {
            (emp["id"], day): self.schedule_markers[emp["id"]][day]
            for emp in self.employees for day in self.days
        }
        ph = self.problem.get("demand", {}).get("priorityHierarchy", [])
        self.priority: Dict[str, int] = (
            {e["team"]: e["rank"] for e in ph} if ph else DEFAULT_PRIORITY
        )

        # Resultados (preenchidos por run())
        self.best_solution: Optional[Solution] = None
        self.best_cost:     float = float("inf")
        self.initial_cost:  float = float("inf")
        self.iterations:    int   = 0
        self.elapsed:       float = 0.0

    # ------------------------------------------------------------------
    # run() — loop ALNS principal
    # ------------------------------------------------------------------

    def run(
        self,
        time_limit_seconds: Optional[int] = None,
        repair_mode:    str = "greedy",   # "greedy" | "ilp" | "hybrid"
        ilp_time_limit: int = 5,
        # Parâmetros SA
        sa_start_temp:  float = None,     # None → auto (5% do custo inicial)
        sa_end_temp:    float = 1.0,
        sa_step:        float = 0.9995,
        # Parâmetros RouletteWheel
        scores:         List[float] = None,  # [new_best, better, accepted, rejected]
        decay:          float = 0.8,
    ):
        """
        Executa o loop ALNS.

        repair_mode="hybrid": usa greedy na fase de exploração (T alto)
        e ILP na fase de intensificação (T < sa_end_temp * 10).
        """
        limit = time_limit_seconds or self.max_time_seconds or 300
        if scores is None:
            scores = [3, 2, 1, 0]

        # ---- Solução inicial greedy ----
        solution, tracker = build_greedy_initial_solution(
            employees=self.employees, days=self.days,
            assignments_by=self.assignments_by, markers=self.markers,
            alpha=self.alpha, priority=self.priority,
            min_rest_hours=self.min_rest_hours,
        )
        self.initial_cost = tracker.total_shortage()
        print(f"[ALNS] Initial shortage: {self.initial_cost}")

        if sa_start_temp is None:
            sa_start_temp = max(1.0, 0.05 * self.initial_cost)

        initial_state = ScheduleState(solution, tracker, self)

        # ---- Construir instância ALNS ----
        alns_inst = ALNS(self.np_rng)

        # Registar destroy operators
        for name in ["D1", "D2", "D3", "D4"]:
            alns_inst.add_destroy_operator(_make_destroy_op(self, name))

        # Registar repair operator(s)
        # Em modo hybrid registamos dois repair — a biblioteca vai gerir os pesos
        if repair_mode == "hybrid":
            alns_inst.add_repair_operator(_make_repair_op(self, "greedy", ilp_time_limit))
            alns_inst.add_repair_operator(_make_repair_op(self, "ilp",    ilp_time_limit))
        else:
            alns_inst.add_repair_operator(_make_repair_op(self, repair_mode, ilp_time_limit))

        # Critério de aceitação SA
        criterion = SimulatedAnnealing(
            start_temperature = sa_start_temp,
            end_temperature   = sa_end_temp,
            step              = sa_step,
            method            = "exponential",
        )

        # Selecção adaptativa RouletteWheel
        select = RouletteWheel(
            scores       = scores,
            decay        = decay,
            num_destroy  = 4,
            num_repair   = 2 if repair_mode == "hybrid" else 1,
        )

        # ---- Executar ALNS com limite de tempo ----
        start = time.time()
        result = alns_inst.iterate(
            initial_state,
            select,
            criterion,
            MaxRuntime(limit),
            collect_stats = True,
        )

        self.elapsed    = time.time() - start
        best_state      = result.best_state
        self.best_solution = best_state.solution
        self.best_cost     = best_state.objective_value
        self.iterations    = self._count_iterations(result.statistics)

        print(
            f"[ALNS] Done  iters={self.iterations}  "
            f"best_shortage={self.best_cost}  "
            f"time={self.elapsed:.1f}s"
        )

        # Imprimir estatísticas de uso dos operadores
        self._print_operator_stats(result)

    # ------------------------------------------------------------------
    # Output (compatível com SisqualProblem1ILP)
    # ------------------------------------------------------------------

    def build_output_rows(self) -> List[List[str]]:
        if self.best_solution is None:
            return []

        solution = self.best_solution
        rows     = [["employee_id", *self.days]]

        for emp in self.employees:
            emp_id = emp["id"]
            row    = [emp_id]
            for day in self.days:
                marker     = self.schedule_markers[emp_id][day]
                normalized = normalize_marker(marker)
                if normalized in OFF_MARKERS or not normalized:
                    row.append(marker or "OFF")
                    continue
                asgn = solution.assignments.get((emp_id, day))
                if asgn is None:
                    row.append("UNASSIGNED")
                    continue

                segments      = []
                current_skill = None
                current_start = None
                current_end   = None

                for slot_idx in asgn.slot_indices:
                    slot  = self.time_slots[slot_idx]
                    skill = solution.skill_map.get((emp_id, day, slot_idx))
                    if skill is None:
                        skill = (emp["assignable_skills"][0]
                                 if emp["assignable_skills"] else self.STAFF_TEAM)

                    if skill == current_skill:
                        current_end = slot.end_min
                    else:
                        if current_skill is not None:
                            segments.append(
                                f"{minutes_to_hhmm(current_start)}-"
                                f"{minutes_to_hhmm(current_end)}@{current_skill}"
                            )
                        current_skill = skill
                        current_start = slot.start_min
                        current_end   = slot.end_min

                if current_skill is not None:
                    segments.append(
                        f"{minutes_to_hhmm(current_start)}-"
                        f"{minutes_to_hhmm(current_end)}@{current_skill}"
                    )
                row.append(" | ".join(segments) if segments else asgn.label)
            rows.append(row)

        return rows

    def export_csv(self, output_path: str):
        rows = self.build_output_rows()
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerows(rows)

    def solution_summary(self) -> dict:
        return {
            "initial_shortage": self.initial_cost,
            "best_shortage":    self.best_cost,
            "improvement_pct":  round(
                100 * (self.initial_cost - self.best_cost)
                / max(1, self.initial_cost), 2),
            "iterations":  self.iterations,
            "elapsed_sec": round(self.elapsed, 2),
        }

    # ------------------------------------------------------------------
    # Helpers privados
    # ------------------------------------------------------------------

    def _parse_min_rest_hours(self) -> float:
        for c in self.problem.get("constraints", {}).get("hard", []):
            if c.get("type") == "min_rest_hours" and c.get("enabled", True):
                h = c.get("params", {}).get("hours")
                if isinstance(h, (int, float)):
                    return float(h)
        return MIN_REST_HOURS_DEFAULT

    @staticmethod
    def _estimate_iterations(time_limit: int, repair_mode: str) -> int:
        """
        Estima o número de iterações para o tempo limite.
        Greedy: ~200 iter/s;  ILP: ~5 iter/s.
        """
        if repair_mode == "ilp":
            return max(10, time_limit * 5)
        if repair_mode == "hybrid":
            return max(20, time_limit * 50)
        return max(100, time_limit * 200)

    @staticmethod
    def _count_iterations(stats) -> int:
        runtimes = getattr(stats, "runtimes", None)
        if runtimes is not None:
            try:
                return len(runtimes)
            except TypeError:
                pass

        objectives = getattr(stats, "objectives", None)
        if objectives is not None:
            try:
                return max(0, len(objectives) - 1)
            except TypeError:
                pass

        return 0

    @staticmethod
    def _print_operator_stats(result):
        """Imprime estatísticas de uso e scores dos operadores."""
        try:
            stats = result.statistics
            print("\n[ALNS] Operator statistics:")
            d_names = ["D1-random", "D2-worst", "D3-shift", "D4-skill"]
            destroy_counts = getattr(stats, "destroy_operator_counts", {})
            for name in d_names:
                counts = destroy_counts.get(name)
                if counts is None:
                    continue
                print(f"  {name}: best={counts[0]}  better={counts[1]}  "
                      f"accepted={counts[2]}  rejected={counts[3]}")
        except Exception:
            pass   # Estatísticas não disponíveis nesta versão da biblioteca


# ---------------------------------------------------------------------------
# Thin wrapper para TaskManager API
# ---------------------------------------------------------------------------

def solve(problem_path=None, maxTime=None, seed=42,
          repair_mode="greedy", ilp_time_limit=5, **kwargs):
    if not problem_path:
        raise ValueError("'problem_path' pointing to problem.json is required.")
    scheduler = LNSScheduler(problem_path, max_time_minutes=maxTime, seed=seed)
    scheduler.run(repair_mode=repair_mode, ilp_time_limit=ilp_time_limit)
    return scheduler.build_output_rows()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Sisqual ALNS scheduler (greedy | ilp | hybrid repair)")
    parser.add_argument("problem_json")
    parser.add_argument("--time",   default="5",
                        help="Tempo limite em minutos (default 5)")
    parser.add_argument("--repair", default="greedy",
                        choices=["greedy", "ilp", "hybrid"],
                        help="Modo de repair (default: greedy)")
    parser.add_argument("--ilp-time", dest="ilp_time", type=int, default=5,
                        help="Tempo limite do CBC por sub-problema em s (default 5)")
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    scheduler = LNSScheduler(
        args.problem_json,
        max_time_minutes=args.time,
        seed=args.seed,
    )
    scheduler.run(
        repair_mode    = args.repair,
        ilp_time_limit = args.ilp_time,
    )

    summary = scheduler.solution_summary()
    print("\n=== Summary ===")
    for k, v in summary.items():
        print(f"  {k}: {v}")

    if args.output:
        scheduler.export_csv(args.output)
        print(f"\nSchedule written to {args.output}")
    else:
        rows = scheduler.build_output_rows()
        print("\nFirst 3 employee rows (truncated to 8 days):")
        for row in rows[1:4]:
            print(" | ".join(str(c) for c in row[:9]))


if __name__ == "__main__":
    main()