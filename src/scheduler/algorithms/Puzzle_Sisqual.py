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


    def dynamical_ILP(self):
        """
        Placeholder for a future ILP-based refinement step.
        """
        pass



    def solve(self, day_lenght):
        """
        This is the central function
        """

        num_days = len(self.days)
        weeks = (len(self.days) + day_lenght - 1) // day_lenght

        for week_index in range(weeks):

            print(f"Week {week_index + 1}")

            week_number    = week_index + 1
            week_start_day = week_index * day_lenght + 1 
            week_end_day   = min(week_start_day + day_lenght - 1, num_days)

            print(f"Processing days {week_start_day} to {week_end_day} of {num_days}")
            


        time.sleep(10)  # Simulate some processing time

        # Data Preparation to ILP

        # Solving ILP for competencies
        # ILP_Solution = self.dynamical_ILP()

        # Solving Levels by Heuristic Method

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



def solve(problem_path=None, maxTime=None, restarts=5, day_lenght=7, **kwargs):

    best_rows = None
    best_key = None

    all_results = []

    for i in range(restarts):


        scheduler = Hybrid_Heuristic_Sisqual(problem_path, max_time_minutes=maxTime)
        scheduler.solve(day_lenght=day_lenght)
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