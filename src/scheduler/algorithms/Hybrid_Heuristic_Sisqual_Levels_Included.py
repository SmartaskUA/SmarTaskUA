from __future__ import annotations

import copy
import csv
import random
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import pulp

import numpy as np
import pandas as pd
import holidays

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
from analyzer.kpiVerification_Sisqual import KpiEvaluator_Sisqual


class Hybrid_Heuristic_Sisqual:
    def __init__(self,
                problem_json_path: str,
                max_time_minutes=None
                ):
        """
        Hybrid heuristic scheduler for the hour-based / multi-skill Sisqual
        bundle described in MathematicalDefinition7.pdf.
        """
        # Original employee dicts
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
        # Lookup O(1) por id -- usado pelo objetivo 2 (p_sl) e pelo diagnostico
        # de total_priority_cost(), que precisam de aceder a skill_levels sem
        # percorrer self.employees.
        self.employees_by_id = {employee["id"]: employee for employee in self.employees}

        # `self.days` is still the optimization/output horizon: these are the
        # dates that get decision variables, coverage terms, and exported cells.
        self.days = parse_days(self.problem)  # target/output days, e.g. ["2025-10-01", ..., "2025-10-31"]

        # The PDF specification allows days before the target month as context.
        # We only use columns that already exist in schedule_input.csv. They are
        # immutable history and never appear in the generated schedule output.
        self.before_context_days = parse_before_context_days(self.base_dir, self.problem)

        self.employees_by_level = defaultdict(list)

        for employee in self.employees:
            for skill, level in employee["skill_levels"].items():
                self.employees_by_level[level].append((employee["id"], skill, employee["name"]))

        # `constraint_days` lets boundary-sensitive hard rules scan history and
        # target days together. Any day in `context_day_set` is a constant, not a
        # decision variable.
        self.constraint_days = [*self.before_context_days, *self.days]
        self.context_day_set = set(self.before_context_days)
        self.date_by_day = {day: datetime.strptime(day, "%Y-%m-%d").date() for day in self.constraint_days}
        self.schedule_markers = parse_schedule_input(self.base_dir, self.problem, self.constraint_days)  # target markers plus optional before-context markers
        self.skills = parse_skill_codes(self.problem)  # ["Storage", "Checkout", "Management", "Employees"]

        self.skill_employee_count = {
            skill: sum(1 for employee in self.employees if skill in employee["assignable_skills"])
            for skill in self.skills
        }

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

        self.day_modes = build_sisqual_day_modes(self.employees, self.days, self.schedule_markers, self.closed_days)  # {("20072412", "2025-10-01"): "work_template", ("20072412", "2025-10-05"): "preferred_day_off", ...}
        self.assignments = build_sisqual_bundle_assignments(
            self.employees,
            self.days,
            self.schedule_markers,
            self.time_slots,
            self.day_modes,
            None
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

        # Fase A outputs (populated by build_phase_a_weekly_quota)
        self.day_by_date = {v: k for k, v in self.date_by_day.items()}
        self.week_of_day = {}
        self.eligible_days = {}
        self.preferred_off_days = {}
        self.n_wk = {}
        self.work_days = {}
        self.day_off_swap = {}
        self.d_bar_windows = []

        # ---- Greedy assignment state (populated by Minimuns / assign_all) ----
        # need[(day, slot_idx, skill)] -> remaining minimum still uncovered.
        # Starts as a copy of alpha; decremented as blocks get fixed.
        self.need: Dict[Tuple[str, int, str], int] = dict(self.alpha)
        # chosen block per (employee, day) -> Assignment | None
        self.employee_day_block: Dict[Tuple[str, str], Optional[Assignment]] = {}
        # skill worked per (employee, day, slot_idx) -> skill code
        self.slot_skill: Dict[Tuple[str, str, int], str] = {}
        # employees left with no feasible block on a given day (rest-hours
        # conflicts exhausted every candidate, or no candidates existed)
        self.unassigned: List[Tuple[str, str]] = []

        # print(f"\n{'='*80}")
        # print(f"[Heuristica] Initialized Heuristic Scheduler")
        # print(f"{'='*80}")
        # print(f"Employees: {len(self.employees)}")
        # print(f"Days: {len(self.days)}")
        # print(f"Time Slots: {len(self.time_slots)}")
        # print(f"Levels: {len(self.levels)}")
# 
        # print(f"Weeks: {len(self.weeks)}")
        # print(f"Open Days: {len(self.open_days)}")
        # print(f"Closed Days: {len(self.closed_days)}")
        # print(f"Coverage Priority Tiers: {len(self.coverage_priority_tiers)}")
        # print(f"Min Rest Hours: {self.min_rest_hours}")
        # print(f"Max Time Seconds: {self.max_time_seconds}")


    def Order(self):
        
        skill_employee_count = {
            skill: sum(1 for employee in self.employees if skill in employee["assignable_skills"])
            for skill in self.skills
        }

        ordered_employees = sorted(
            self.employees,
            key=lambda employee: (
                len(employee["assignable_skills"]),
                tuple(
                    sorted(
                        (skill_employee_count.get(skill, 0) for skill in employee["assignable_skills"])
                    )
                ),
                employee["id"],
            ),
        )

        return [employee["id"] for employee in ordered_employees]

    # ------------------------------------------------------------------
    # Helpers for the greedy block-assignment heuristic
    # ------------------------------------------------------------------

    def _best_skill_for_slot(self, employee: Dict, day: str, slot_idx: int) -> Tuple[Optional[str], int]:
        
        best_skill = None
        best_need = -1
        best_p_sl: Optional[float] = None
        best_count = None

        for skill in employee["assignable_skills"]:
            remaining = self.need.get((day, slot_idx, skill), 0)
            level = employee["skill_levels"].get(skill)
            p_sl = (
                priority_weight_for_skill_level(self.coverage_priority_tiers, skill, level)
                if level is not None
                else float("inf")
            )
            count = self.skill_employee_count.get(skill, 1)

            if best_skill is None:
                better = True
            elif remaining > best_need:
                better = True
            elif remaining == best_need and p_sl < best_p_sl:
                better = True
            elif remaining == best_need and p_sl == best_p_sl and count < best_count:
                better = True
            else:
                better = False

            if better:
                best_need = remaining
                best_skill = skill
                best_p_sl = p_sl
                best_count = count

        if best_skill is None:
            return None, 0
        return best_skill, max(best_need, 0)


    def _score_block(self, employee: Dict, day: str, block: Assignment) -> Tuple[int, float, Dict[int, Optional[str]]]:
        
        coverage = 0
        priority_cost = 0.0
        skill_by_slot: Dict[int, Optional[str]] = {}
        for slot_idx in block.slot_indices:
            skill, need_here = self._best_skill_for_slot(employee, day, slot_idx)
            coverage += need_here
            skill_by_slot[slot_idx] = skill
            if skill is not None:
                level = employee["skill_levels"].get(skill)
                if level is not None:
                    priority_cost += priority_weight_for_skill_level(
                        self.coverage_priority_tiers, skill, level
                    )
        return coverage, priority_cost, skill_by_slot


    def _neighbor_end_min(self, employee_id: str, day: str) -> Optional[int]:
        
        current_date = self.date_by_day[day]
        prev_date = (current_date - timedelta(days=1)).isoformat()

        if prev_date in self.day_by_date:
            prev_day = self.day_by_date[prev_date]
        else:
            prev_day = prev_date if prev_date in self.date_by_day else None

        if prev_day is None or prev_day not in self.date_by_day:
            return None

        if prev_day in self.context_day_set:
            fixed = fixed_context_assignment(self.schedule_markers, employee_id, prev_day)
            # print(f"[Heuristica_Neighbor_End_Min] Employee {employee_id} on {day}: Found fixed assignment on {prev_day}, end time = {fixed.end_min if fixed else None}")
            return fixed.end_min if fixed else None

        block = self.employee_day_block.get((employee_id, prev_day))
        # print(f"[Heuristica_Neighbor_End_Min] Employee {employee_id} on {day}: No fixed assignment on {prev_day}, end time = {block.end_min if block else None}")
        return block.end_min if block else None


    def _neighbor_start_min(self, employee_id: str, day: str) -> Optional[int]:
        
        current_date = self.date_by_day[day]
        next_date = (current_date + timedelta(days=1)).isoformat()

        if next_date not in self.date_by_day:
            return None
        next_day = next_date

        # Days after the target period are never context (context is only
        # ever *before* targetPeriod.start), so just look at what's fixed.
        block = self.employee_day_block.get((employee_id, next_day))
        # print(f"[Heuristica_Neighbor_Start_Min] Employee {employee_id} on {day}: Found block on {next_day}, start time = {block.start_min if block else None}") 
        return block.start_min if block else None


    def _rest_ok(self, employee_id: str, day: str, block: Assignment) -> bool:
        
        min_gap = self.min_rest_hours * 60

        prev_end = self._neighbor_end_min(employee_id, day)
        if prev_end is not None:
            gap = (24 * 60 - prev_end) + block.start_min
            if gap < min_gap:
                return False

        next_start = self._neighbor_start_min(employee_id, day)
        if next_start is not None:
            gap = (24 * 60 - block.end_min) + next_start
            if gap < min_gap:
                return False

        return True


    def _apply_block(
        self,
        employee: Dict,
        day: str,
        block: Assignment,
        skill_by_slot: Optional[Dict[int, Optional[str]]] = None,
    ) -> None:
        
        employee_id = employee["id"]
        for slot_idx in block.slot_indices:
            if skill_by_slot is not None:
                skill = skill_by_slot.get(slot_idx)
            else:
                skill, _ = self._best_skill_for_slot(employee, day, slot_idx)

            if skill is None:
                continue

            self.slot_skill[(employee_id, day, slot_idx)] = skill
            key = (day, slot_idx, skill)

            if key in self.need:
                self.need[key] = max(0, self.need[key] - 1)

        self.employee_day_block[(employee_id, day)] = block


    def assign_employee_day(self, employee: Dict, day: str) -> bool:
        
        employee_id = employee["id"]
        candidates = self.assignments.get((employee_id, day), [])
    
        if not candidates:
            self.employee_day_block[(employee_id, day)] = None
            self.unassigned.append((employee_id, day))   # <-- adicionar esta linha
            return False
    
        scored = []
        for block in candidates:
            coverage, priority_cost, skill_by_slot = self._score_block(employee, day, block)
            scored.append((coverage, priority_cost, random.random(), block, skill_by_slot))
    
        scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    
        for _, _, _, block, skill_by_slot in scored:
            if self._rest_ok(employee_id, day, block):
                self._apply_block(employee, day, block, skill_by_slot)
                return True
    
        self.employee_day_block[(employee_id, day)] = None
        self.unassigned.append((employee_id, day))
        return False


    def _day_bottleneck_score(self, day: str) -> float:
        
        demand_by_skill: Dict[str, int] = defaultdict(int)
        for (d, _slot_idx, skill), minimum in self.alpha.items():
            if d == day:
                demand_by_skill[skill] += minimum

        score = 0.0
        for skill, total_need in demand_by_skill.items():
            available = sum(
                1
                for employee in self.employees
                if skill in employee["assignable_skills"]
                and self.day_modes.get((employee["id"], day))
                not in {"closed", "unavailable", "preferred_day_off"}
            )
            score += total_need / max(available, 1)
        return score


    def _compute_day_order(self, day_order_mode: int = 1) -> List[str]:
        
        if day_order_mode == 1:
            ordered = list(self.days)
            random.shuffle(ordered)
            return ordered

        if day_order_mode == 2:
            demand_by_day: Dict[str, int] = defaultdict(int)
            for (day, _slot_idx, _skill), minimum in self.alpha.items():
                demand_by_day[day] += minimum

            tiebreak = {day: random.random() for day in self.days}
            return sorted(
                self.days,
                key=lambda d: (-demand_by_day.get(d, 0), tiebreak[d]),
            )

        if day_order_mode == 3:
            bottleneck_by_day = {day: self._day_bottleneck_score(day) for day in self.days}
            tiebreak = {day: random.random() for day in self.days}
            return sorted(
                self.days,
                key=lambda d: (-bottleneck_by_day[d], tiebreak[d]),
            )

        raise ValueError(f"day_order_mode invalido: {day_order_mode!r} (usa 1, 2 ou 3)")


    def total_priority_cost(self) -> float:
        
        total = 0.0
        for (employee_id, _day, _slot_idx), skill in self.slot_skill.items():
            employee = self.employees_by_id.get(employee_id)
            if employee is None:
                continue
            level = employee["skill_levels"].get(skill)
            if level is None:
                continue
            total += priority_weight_for_skill_level(self.coverage_priority_tiers, skill, level)
        return total


    def Minimuns(self, day_order_mode):

        random_days = self._compute_day_order(day_order_mode)

        Daily_Needs = {}
        for skill in self.skills:
            Daily_Needs[skill] = {}

        ordered_employee_ids = self.Order()
        employees_by_id = self.employees_by_id

        self.unassigned = []

        for d in random_days:

            skill_employee_count = {
                skill: sum(1 for employee in self.employees if skill in employee["assignable_skills"])
                for skill in self.skills
            }
            groups = {}
            key_order = []
            
            for emp_id in ordered_employee_ids:
                emp = employees_by_id[emp_id]
                key = (
                    len(emp["assignable_skills"]),
                    tuple(sorted(skill_employee_count.get(skill, 0) for skill in emp["assignable_skills"]))
                )
                if key not in groups:
                    groups[key] = []
                    key_order.append(key)
                groups[key].append(emp_id)

            day_order = []
            for key in key_order:
                bucket = groups[key]
                random.shuffle(bucket)
                day_order.extend(bucket)

            for emp_id in day_order:
                employee = employees_by_id[emp_id]
                mode = self.day_modes.get((emp_id, d))
                if mode in {"closed", "unavailable", "preferred_day_off"}:
                    self.employee_day_block[(emp_id, d)] = None
                    continue

                ok = self.assign_employee_day(employee, d)
                if ok:
                    block = self.employee_day_block[(emp_id, d)]
                    # print(f" - {emp_id}: {block.label}")
                else:
                    # print(f" - {emp_id}: SEM atribuicao viavel hoje")
                    pass

        self._print_summary()
        return

    def _print_summary(self) -> None:

        total_shortage = sum(v for v in self.need.values() if v > 0)
        print(f"\n{'='*80}")
        print(f"[Heuristica] Resumo")
        print(f"{'='*80}")
        print(f"Falhas de atribuicao (empregado sem bloco viavel): {len(self.unassigned)}")
        for emp_id, day in self.unassigned:
            print(f" - {emp_id} em {day}")
        print(f"Minimos ainda em falta (slots*skill somados): {total_shortage}")
        print(f"Custo total de prioridade (objetivo 2, p_sl somado): {self.total_priority_cost()}")


    def build_output_rows(self) -> List[List[str]]:
        
        rows = [["employee_id", *self.days]]
    
        # Lookup O(1) em vez de percorrer a lista `self.unassigned` por célula.
        unassigned_set = set(self.unassigned)
    
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
                    row.append(marker or "OFF")  # preserva VAC/NOT/MED originais
                    continue
                
                chosen = self.employee_day_block.get((employee_id, day))
    
                if chosen is None:
                    if mode == "preferred_day_off":
                        row.append(marker or "DO")  # DO não tocado (sem swap por agora)
                    elif (employee_id, day) in unassigned_set:
                        row.append("UNASSIGNED")  # sem bloco viável (choque de descanso, etc.)
                    else:
                        row.append("UNASSIGNED")
                    continue
                
                # Junta slots meia-hora adjacentes com a mesma competência num
                # único segmento exportado, tal como a versão ILP fazia.
                segments = []
                current_skill = None
                current_start = None
                current_end = None
    
                for slot_idx in chosen.slot_indices:
                    slot = self.time_slots[slot_idx]
                    assigned_skill = self.slot_skill.get((employee_id, day, slot_idx))
    
                    if assigned_skill is None:
                        # Fallback defensivo: não deveria faltar skill para um
                        # slot dentro de um bloco já fixado por _apply_block.
                        assigned_skill = (
                            employee["assignable_skills"][0]
                            if employee["assignable_skills"]
                            else self.staff_team_code
                        )
    
                    if current_skill == assigned_skill:
                        current_end = slot.end_min  # estende o segmento atual
                    else:
                        if current_skill is not None:
                            segments.append(
                                f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}"
                            )
                        current_skill = assigned_skill
                        current_start = slot.start_min
                        current_end = slot.end_min
    
                if current_skill is not None:
                    segments.append(
                        f"{minutes_to_hhmm(current_start)}-{minutes_to_hhmm(current_end)}@{current_skill}"
                    )
    
                row.append(" | ".join(segments) if segments else chosen.label)
            rows.append(row)
    
        return rows

    def compute_true_shortage(self) -> int:
        
        rows = self.build_output_rows()
        demand_file = self.problem.get("demand", {}).get("dataFile", "demand.csv")
        demand_path = str(self.base_dir / demand_file)
        kpi = KpiEvaluator_Sisqual(rows, demand_csv_path=demand_path, problem_json=self.problem)
        res = kpi.compute_Total_Shortage()
        if isinstance(res, dict):
            val = int(res.get("value", 0))
        else:
            val = int(res)
        self.total_shortage = val
        return val


def solve(problem_path=None, maxTime=None, restarts=5, day_order_mode=None, **kwargs):

    best_rows = None
    best_key = None

    all_results = []

    day_order_mode_list = [1, 2, 3] if day_order_mode is None else day_order_mode

    for i in range(restarts):

        for current_mode in day_order_mode_list:

            scheduler = Hybrid_Heuristic_Sisqual(problem_path, max_time_minutes=maxTime)
            scheduler.Minimuns(day_order_mode=current_mode)

            # Compute the true shortage using KPI evaluator to match reporting
            try:
                kpi_shortage = scheduler.compute_true_shortage()
            except Exception as ex:
                # Fallback: use internal remaining need if KPI evaluation fails
                print(f"[Heuristica] Warning: KPI evaluation failed: {ex}")
                kpi_shortage = sum(v for v in scheduler.need.values() if v > 0)

            priority_cost = scheduler.total_priority_cost()

            unassigned_count = len(scheduler.unassigned)


            # Record this result
            all_results.append({
                'restart_num': i + 1,
                'day_order_mode': current_mode,
                'unassigned_count': unassigned_count,
                'kpi_shortage': kpi_shortage,
                'priority_cost': priority_cost,
            })

            key = (unassigned_count, kpi_shortage, priority_cost)
            if best_key is None or key < best_key:
                best_key = key
                best_rows = scheduler.build_output_rows()

    # Write results to CSV file
    _write_results_log(problem_path, all_results, best_key)

    print(f"[Heuristica] Best (unassigned_count, kpi_shortage, priority_cost) after {restarts} restarts: {best_key}")
    return best_rows


def _write_results_log(problem_path: str, all_results: list, best_key):
    """Write all restart results to a CSV log file next to problem.json."""
    try:
        problem_path = Path(problem_path)
        base_dir = problem_path.parent
        log_file = base_dir / "heuristic_results_levels.csv"

        with log_file.open('w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(
                f,
                fieldnames=['restart_num', 'day_order_mode', 'unassigned_count', 'kpi_shortage', 'priority_cost'],
            )
            writer.writeheader()
            for row in all_results:
                writer.writerow(row)

        print(f"[Heuristica] Results saved to: {log_file}")
        print(f"[Heuristica] Best (unassigned_count, kpi_shortage, priority_cost): {best_key}")
    except Exception as ex:
        print(f"[Heuristica] Warning: Could not write results log: {ex}")