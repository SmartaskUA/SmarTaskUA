import copy
import csv
from collections import defaultdict
import datetime
from itertools import cycle, groupby
import json
import threading
import os
from xml.parsers.expat import model

import numpy as np
import pandas as pd
import holidays
import time
import random
import pulp

from algorithms.assignmentmap import print_daily_assignment_map

from algorithms.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    build_calendar,
    export_schedule_to_csv,
)

from algorithms.utils_Heuristics_New import (
    _assign,
    _unassign,
    _build_emp_team_map,
    _build_teams,
    _validate_block_transition_beta,
    get_next_assigned_shift,
    get_previous_assigned_shift,
    consecutivechecker,
    evaluate_Day_Toshifts_minimos,
    evaluate_Day_Toshifts_ideais,
    construct_mins_table,
    construct_ideals_table,
)
# from algorithms.Puzzle_Heuristic_Calibrate import calibrate_max_admissible


# =============================================================================
# TIMEOUT EXCEPTION
# =============================================================================

class SchedulerTimeout(Exception):
    """Levantada quando o algoritmo excede o tempo máximo permitido."""
    pass


class Heuristica:
    # =========================================================================
    # CONSTANTS
    # =========================================================================

    _assign                       = _assign
    _unassign                     = _unassign
    _build_emp_team_map           = _build_emp_team_map
    _build_teams                  = _build_teams
    _validate_block_transition    = _validate_block_transition_beta
    get_next_assigned_shift       = get_next_assigned_shift
    get_previous_assigned_shift   = get_previous_assigned_shift
    consecutivechecker            = consecutivechecker
    evaluate_Day_Toshifts_minimos = evaluate_Day_Toshifts_minimos
    evaluate_Day_Toshifts_ideais  = evaluate_Day_Toshifts_ideais
    construct_mins_table          = construct_mins_table
    construct_ideals_table        = construct_ideals_table
    # calibrate_max_admissible          = calibrate_max_admissible
    
    CALIBRATE = False  # mudar para True para correr calibração

    MAX_DAYS             = 223
    MAX_SUN_HOL          = 22
    MAX_CONSECUTIVE      = 5

    # ILP time limit por semana (segundos) — CBC abandona e retorna a melhor solução encontrada
    ILP_TIME_LIMIT_SECONDS = 600

    # Employee scoring weights
    W_PACE    = 0.52
    W_SEQ     = 0.38
    W_SUN_HOL = 0.00
    W_TEAMS   = 0.03
    W_TRANS   = 0.15


    MAX_ADMISSIBLE_PER_EMP = 2000  # ajustar empiricamente


    def __init__(self, vacations_rows, minimums_rows, employees,
                 maxTime, year=2025, w_min=100, w_ideal=1, spacing=None, full=None, **kwargs):
        """
        Weighted ILP scheduler.

        employees: list of employee dicts (with "teams" etc.).
        Internally we index employees as 1..N for this ILP.
        """

        self.employee_rows = employees
        self.employees = list(range(1, len(employees) + 1))

        self.vacations_rows = vacations_rows
        self.minimums_rows = minimums_rows
        self.maxTime = maxTime
        
        self.full = full
        if self.full is None:
            print("Warning: 'full' parameter not provided. Defaulting to False.")

        self.year = year
        self.shifts = 3
        self.w_min = w_min
        self.w_ideal = w_ideal

        # --- tracking do tempo gasto pelo ILP (Pontuate), por semana ---
        self.total_ilp_time = 0.0
        self.ilp_times_log = []   # [(week_start_day, seconds), ...]

        self.patterns_used = set()

        if spacing is None:
            # Throw error if spacing is not provided, as it's required for the algorithm to function correctly.
            raise ValueError("The 'spacing' parameter must be provided and cannot be None.")
        else:
            self.spacing = spacing
        
        
        self.TARGET_DAYS_PER_WEEK = 201 / (365 / self.spacing)

        # === Preprocessing ===
        self.teams = self._build_teams(self.employee_rows)
        self.emp_allowed_teams = self._build_emp_team_map(self.employee_rows)

        self.dates, sundays_idx = build_calendar(year)
        self.num_days = len(self.dates)

        sundays = {
            self.dates[idx - 1]
            for idx in sundays_idx
            if 1 <= idx <= len(self.dates)
        }

        pt_holidays = holidays.country_holidays("PT", years=[year])
        holiday_dates = {
            d
            for d in self.dates
            if d.date() in pt_holidays
        }

        self.sundays_holidays = sorted(sundays | holiday_dates)
        self._sun_hol_set = set(self.sundays_holidays)

        raw_vacs = rows_to_vac_dict(vacations_rows)
        self.vacs_1based = {
            emp_id: sorted(raw_vacs.get(emp_id, []))
            for emp_id in self.employees
        }
        self.vacs = self.vacs_1based
        self.vacations_dates = {
            emp_id: {
                self.dates[day - 1]
                for day in raw_vacs.get(emp_id, [])
                if 1 <= day <= self.num_days
            }
            for emp_id in self.employees
        }

        mins_raw, ideals_raw = rows_to_req_dicts(minimums_rows)
        self.minimos = {}
        self.ideais = {}
        for (day, shift, team_id), value in mins_raw.items():
            if 1 <= day <= self.num_days:
                self.minimos[(self.dates[day - 1], shift, team_id)] = int(value)
        for (day, shift, team_id), value in ideals_raw.items():
            if 1 <= day <= self.num_days:
                self.ideais[(self.dates[day - 1], shift, team_id)] = int(value)

        # ── Global mutable state ──────────────────────────────────────────────
        # Fonte de verdade: todas as escritas passam por _assign / _unassign
        self.assignment = defaultdict(list)          # emp_id → [(day, shift, team), ...]
        self.assignment_by_day = defaultdict(list)   # day    → [(emp_id, shift, team), ...]
        self.Total_Days = {f: 0 for f in self.employees}
        self.sundays_holidays_worked = {f: 0 for f in self.employees}

        self.removed_days = 0
        self.solution_history = []
        self.exact_solution_state = None
        self.best_solution_state = None
        self.best_solution_kpis = None

    def order_of_ranks(self, scores):
        ranked = list(scores.items())
        random.shuffle(ranked)
        ranked.sort(key=lambda x: x[1], reverse=True)
        return [emp_id for emp_id, _ in ranked]

    def recreate_days(self, assignment):
        days = defaultdict(list)
        for emp_id, entries in assignment.items():
            for day, shift, team_code in entries:
                days[day].append((emp_id, shift, team_code))
        sorted_days = {
            day: sorted(days.get(day, []), key=lambda x: x[0])
            for day in range(1, self.num_days + 1)
        }
        return sorted_days
    
    def export_ilp_time_summary(self, filename="/app/ilp_time_summary.csv"):
        file_exists = os.path.exists(filename) and os.path.getsize(filename) > 0
        with open(filename, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["spacing", "num_weeks", "total_ilp_seconds", "avg_ilp_seconds"])
            n_weeks = len(self.ilp_times_log)
            avg = self.total_ilp_time / n_weeks if n_weeks else 0.0
            writer.writerow([self.spacing, n_weeks, f"{self.total_ilp_time:.3f}", f"{avg:.3f}"])

    def choose_Employee(self, Worked_Total_Days, Worked_Sequential_Days,
                        Worked_Previous_Day, emp_allowed_teams, f, d):

        total_days = Worked_Total_Days.get(f, 0)
        pace_delta = total_days / self.MAX_DAYS
        pace_component = 1.0 - pace_delta ** 2

        streak = Worked_Sequential_Days.get(f, 0)
        seq_component = 1.0 - (streak / self.MAX_CONSECUTIVE) ** 2

        sun_hol = self.sundays_holidays_worked.get(f, 0)
        sun_hol_component = 1.0 - sun_hol / self.MAX_SUN_HOL

        num_teams = len(emp_allowed_teams)
        max_teams = max(len(v) for v in self.emp_allowed_teams.values())
        team_component = (1.0 - (num_teams) / (max_teams)) if max_teams > 1 else 0.0

        prev = Worked_Previous_Day.get(f) if isinstance(Worked_Previous_Day, dict) else Worked_Previous_Day
        if prev == 3:
            value = 0.75
        elif prev == 2:
            value = 0.5
        else:
            value = 0.0
        trans_component = value

        return (
            self.W_PACE    * pace_component    +
            self.W_SEQ     * seq_component     +
            self.W_SUN_HOL * sun_hol_component +
            self.W_TEAMS   * team_component    +
            self.W_TRANS   * trans_component
        )

    # =========================================================================
    # PATTERN GENERATION
    # =========================================================================

    def build_Weekly_Possible_Atributions(self, sun_hol_offsets=None):
        weekly_attributions = {}
        week_length = self.spacing
        if week_length <= 0:
            return weekly_attributions

        target = self.TARGET_DAYS_PER_WEEK
        rounded = round(target)

        # Semana "cheia" (sem domingos/feriados) → janela mais apertada
        # Semana "normal" → janela mais larga para flexibilidade
        is_full_week = (sun_hol_offsets is None or len(sun_hol_offsets) == 0)
        #margin = 1 if is_full_week else 2
        margin = 1

        sigma_min = rounded - margin
        sigma_max = rounded + margin

        def backtrack(day_index, previous_shift, worked_streak, 
                      current_pattern, days_worked, work_blocks, last_was_work):
            if day_index == week_length:
                # Filtro sigma 
                if not (sigma_min <= days_worked <= sigma_max):
                    # Excepção: sigma=0 sempre válido (funcionário de férias)
                    if days_worked != 0:
                        return
                # Filtro de blocos: em semanas cheias, limitar fragmentação
                # Filtro só faz sentido para períodos curtos onde fragmentação é real
                # Um bloco é uma sequência contínua de dias trabalhados, separada por pelo menos um dia de descanso.
                if is_full_week:
                    max_blocks = max(2, week_length // 3)
                else:
                    max_blocks = max(2, week_length // 2)  # mais permissivo para semanas parciais

                if work_blocks > max_blocks:
                    # print(f"Pattern {current_pattern} rejected: {work_blocks} blocks > {max_blocks}")
                    # time.sleep(0.5)  # para evitar flood de prints
                    return
                
                weekly_attributions[tuple(current_pattern)] = 0
                return

            remaining = week_length - day_index - 1

            # Poda por sigma mínimo (já existia)
            if days_worked + remaining < sigma_min and days_worked != 0:
                return

            # Dia de descanso
            current_pattern.append(0)
            backtrack(day_index + 1, None, 0, current_pattern,
                      days_worked, work_blocks, False)
            current_pattern.pop()

            if worked_streak >= self.MAX_CONSECUTIVE:
                return

            # Poda por sigma máximo
            if days_worked >= sigma_max:
                return

            for shift in range(1, self.shifts + 1):
                if previous_shift is not None and not self._validate_block_transition(previous_shift, shift):
                    continue
                new_blocks = work_blocks + (1 if not last_was_work else 0)
                current_pattern.append(shift)
                backtrack(day_index + 1, shift, worked_streak + 1, current_pattern,
                          days_worked + 1, new_blocks, True)
                current_pattern.pop()

        backtrack(0, None, 0, [], 0, 0, False)
        return weekly_attributions
    

    def _reduce_patterns(self, patterns, sun_hol_offsets, target_days, max_keep=None):
        """
        Reduz a lista de padrões admissíveis mantendo apenas os mais úteis.

        Estratégia em 3 camadas aplicadas por ordem:

        1. CLUSTER por vector de cobertura
           Dois padrões com o mesmo vector (offset→shift) têm impacto idêntico
           na cobertura dos slots. Mantém apenas um por cluster.

        2. FILTRO por proximidade ao target de dias
           Dentro de cada cluster (ou directamente se não houver clusters),
           ordena por |dias_trabalhados - target| e mantém os mais próximos.

        3. CAP final
           Limita ao máximo definido por max_keep.

        Parâmetros
        ----------
        patterns       : list of tuples  — padrões já mascarados (dom/feriados = 0)
        sun_hol_offsets: set of int      — offsets a ignorar na cobertura
        target_days    : float           — TARGET_DAYS_PER_WEEK
        max_keep       : int | None      — limite máximo de padrões a manter

        Retorna
        -------
        list of tuples  — padrões reduzidos
        """

        if not patterns:
            return patterns

        # ── 1. Cluster por vector de cobertura ────────────────────────────────
        # A chave é: quais offsets têm turno 1, 2 ou 3 (ignorando dom/feriados).
        # Dois padrões com a mesma chave têm impacto idêntico no ILP.

        def coverage_key(pattern):
            return tuple(
                pattern[offset] if offset not in sun_hol_offsets else 0
                for offset in range(len(pattern))
            )

        clusters = {}
        for p in patterns:
            key = coverage_key(p)
            if key not in clusters:
                clusters[key] = p   # mantém o primeiro representante
        
        reduced = list(clusters.values())

        # ── 2. Ordenar por proximidade ao target ──────────────────────────────
        # Dentro dos representantes, prefere os mais próximos do número de dias alvo.
        # Secundariamente, prefere padrões com dias distribuídos (menos blocos).

        def sort_key(p):
            days_worked  = sum(1 for s in p if s != 0)
            dist_target  = abs(days_worked - target_days)

            # Contar blocos de trabalho contíguos (menos = melhor distribuição)
            blocks = 0
            in_block = False
            for s in p:
                if s != 0 and not in_block:
                    blocks += 1
                    in_block = True
                elif s == 0:
                    in_block = False

            return (dist_target, blocks)

        reduced.sort(key=sort_key)

        # ── 3. Cap final ──────────────────────────────────────────────────────
        if max_keep is not None and len(reduced) > max_keep:
            reduced = reduced[:max_keep]

        return reduced


    def _build_cap_table(self):
        """
        Devolve o número máximo de padrões a manter por funcionário,
        em função do spacing. Valores calibrados empiricamente.
        """
        cap_table = {
            2:  7,
            3:  26,
            4:  18,
            5:  201,
            6:  77,
            7:  139,
            8:  335,
            9:  694,
        }
        return cap_table.get(self.spacing, 200)


    # =========================================================================
    # ILP — PONTUATE
    # =========================================================================

    def EvaluateWeeks(self, week_index, employees_this_week,
                      Previous_weekranks, Weekly_Attributions,
                      Weekly_Attributions_Dyn, mins, ideals,
                      week_start_day=None):
        if not employees_this_week:
            return {}

        result, team_assignments = self.Pontuate(
            Weekly_Attributions,
            employees_this_week,
            Previous_weekranks,
            Weekly_Attributions_Dyn,
            mins,
            ideals,
            week_start_day=week_start_day,
        )
        return result, team_assignments

    def Pontuate(self, Weekly_Attributions, employees_this_week,
                 Previous_weekranks, Weekly_Attributions_Dyn, mins, ideals,
                 week_start_day=None, w_min=1000, w_ideal=1):
        """
        Resolve um ILP para escolher padrões semanais por empregado,
        respeitando domingos, feriados e férias individuais de cada um.
        O CBC tem um limite de ILP_TIME_LIMIT_SECONDS segundos por semana —
        se ultrapassar, retorna a melhor solução parcial encontrada.
        """

        start_wall = time.time()
        
        sun_hol_set = set(self.sundays_holidays)

        # Offsets relativos à semana actual que são domingos ou feriados
        sun_hol_offsets = set()
        if week_start_day is not None:
            for offset in range(self.spacing):
                day_1b = week_start_day + offset
                if 1 <= day_1b <= self.num_days and self.dates[day_1b - 1] in sun_hol_set:
                    sun_hol_offsets.add(offset)

        def mask_pattern_emp(pattern, vac_offsets):
            p = list(pattern)
            for offset in sun_hol_offsets | vac_offsets:
                p[offset] = 0
            return tuple(p)

        admissible = {}
        for emp_id in employees_this_week:
            prev = Previous_weekranks.get(emp_id)

            # Offsets relativos à semana actual que são férias do empregado
            emp_vac_offsets = set()
            if week_start_day is not None:
                for offset in range(self.spacing):
                    day_1b = week_start_day + offset
                    if day_1b in self.vacs_1based.get(emp_id, []):
                        emp_vac_offsets.add(offset)

            # Trailing para a streak anterior — limita o início da semana seguinte
            trailing = 0
            if prev is not None:
                for shift in reversed(prev):
                    if shift == 0:
                        break
                    trailing += 1

            last_shift_prev = prev[-1] if prev else None
            if last_shift_prev == 2:
                first_allowed = {2, 3}
            elif last_shift_prev == 3:
                first_allowed = {3}
            else:
                first_allowed = {1, 2, 3}

            max_start_streak = max(0, self.MAX_CONSECUTIVE - trailing)
            filtered = []
            seen = set()

            # Validar relativamente a semana anterior
            for pattern in Weekly_Attributions:
                start_streak = 0
                valid = True
                for shift in pattern:
                    if shift == 0: # Se for 0, nao ha streak nem transicao invalida, logo da break
                        break
                    if shift not in first_allowed:
                        valid = False
                        break
                    start_streak += 1

                if not valid or start_streak > max_start_streak:
                    continue

                # Trnsformar o padrão para a forma final, com 0s em domingos/feriados e férias
                masked = mask_pattern_emp(pattern, emp_vac_offsets)
                if masked not in seen:
                    seen.add(masked)
                    filtered.append(masked)

            # Se não houver padrões filtrados, usar o primeiro padrão disponível
            if not filtered and Weekly_Attributions:
                filtered = [mask_pattern_emp(next(iter(Weekly_Attributions)), emp_vac_offsets)]
            

            if not self.full:
                cap = self._build_cap_table()
                admissible[emp_id] = self._reduce_patterns(
                    filtered,
                    sun_hol_offsets,
                    self.TARGET_DAYS_PER_WEEK,
                    max_keep=cap,
                )

            else:
                admissible[emp_id] = filtered
            
            
            # No Pontuate, substituir o cap fixo por:
            # cap_table = {
            #     2:  (12,  13, 9), # (full, partial) 9 used :  4 not used
            #     3:  (26,  41, 31), # 31 used :  10 not used
            #     4:  (46,  100, 60), # 60 used : 54 not used
            #     5:  (144, 300, 232), # 232 used :  174 not used
            #     6:  (274, 500, 348), # 348 used : 902 not used
            #     7:  (1038, 800, 574), # 574 used :  1945 not used
            #     8:  (1200, 2000, 700), # 700 used :  500 not used
            #     9:  (1400, 3200, 900), # 900 used :  300 not used
            #     10: (1600, 4400, 1100), # 1100 used :  500 not used
# 
            # }
# 
            # cap_full, cap_partial, cap_used_pat = cap_table.get(self.spacing, (200, 300, 500))
            # cap = cap_partial
 
            # if len(filtered) > cap:
            #     target = self.TARGET_DAYS_PER_WEEK
            #     filtered.sort(key=lambda p: abs(sum(1 for s in p if s != 0) - target))
            #     filtered = filtered[:cap]
 
            # admissible[emp_id] = filtered

        # for e, pat in admissible.items():
        #     print(f"Employee {e} has {len(pat)} admissible patterns.")
            
        all_slots_min = {}
        all_slots_ideal = {}

        for day_1b, shift_team_dict in mins.items():
            offset = (day_1b - 1) % self.spacing
            if offset in sun_hol_offsets:
                continue
            for (shift, team_code), count in shift_team_dict.items():
                key = (offset, shift, team_code)
                all_slots_min[key] = all_slots_min.get(key, 0) + count

        for day_1b, shift_team_dict in ideals.items():
            offset = (day_1b - 1) % self.spacing
            if offset in sun_hol_offsets:
                continue
            for (shift, team_code), count in shift_team_dict.items():
                key = (offset, shift, team_code)
                all_slots_ideal[key] = all_slots_ideal.get(key, 0) + count

        all_patterns = set(p for patterns in admissible.values() for p in patterns)

        delta = {}
        for pattern in all_patterns:
            for offset in range(self.spacing):
                if offset in sun_hol_offsets:
                    continue
                for shift in range(1, self.shifts + 1):
                    delta[(pattern, offset, shift)] = 1 if pattern[offset] == shift else 0

        sigma = {
            pattern: sum(1 for s in pattern if s != 0)
            for pattern in all_patterns
        }

        model = pulp.LpProblem("WeeklyPatternSelection", pulp.LpMinimize)

        x = {}
        pattern_list = {}

        for emp_id in employees_this_week:
            pattern_list[emp_id] = admissible[emp_id]
            x[emp_id] = {}
            for i, _pattern in enumerate(pattern_list[emp_id]):
                for team_code in self.emp_allowed_teams.get(emp_id, []):
                    x[emp_id][(i, team_code)] = pulp.LpVariable(
                        f"x_{emp_id}_{i}_{team_code}", cat="Binary"
                    )

        miss_min = {
            slot: pulp.LpVariable(f"mm_{slot[0]}_{slot[1]}_{slot[2]}", lowBound=0)
            for slot in all_slots_min
        }
        miss_ideal = {
            slot: pulp.LpVariable(f"mi_{slot[0]}_{slot[1]}_{slot[2]}", lowBound=0)
            for slot in all_slots_ideal
        }

        over_days = {
            emp_id: pulp.LpVariable(f"over_{emp_id}", lowBound=0)
            for emp_id in employees_this_week
        }

        # Em Pontuate, antes de construir o modelo:
        w_days = 2.5 if self.spacing >= 5 else 2.23

        model += (
            w_min   * pulp.lpSum(miss_min.values())   +
            w_ideal * pulp.lpSum(miss_ideal.values()) +
            w_days  * pulp.lpSum(over_days.values())
        ), "objective"

        for emp_id in employees_this_week:
            model += pulp.lpSum(x[emp_id].values()) == 1, f"one_pattern_{emp_id}"

        def coverage_expr(offset, shift, team_code):
            terms = []
            for emp_id in employees_this_week:
                if team_code not in self.emp_allowed_teams.get(emp_id, []):
                    continue
                for i, pattern in enumerate(pattern_list[emp_id]):
                    if delta.get((pattern, offset, shift), 0) != 1:
                        continue
                    var = x[emp_id].get((i, team_code))
                    if var is not None:
                        terms.append(var)
            return pulp.lpSum(terms)

        for emp_id in employees_this_week:
            model += (
                pulp.lpSum(
                    sigma[pattern_list[emp_id][i]] * x[emp_id][(i, team_code)]
                    for i in range(len(pattern_list[emp_id]))
                    for team_code in self.emp_allowed_teams.get(emp_id, [])
                    if (i, team_code) in x[emp_id]
                )
                - self.TARGET_DAYS_PER_WEEK <= over_days[emp_id]
            ), f"max_days_{emp_id}"

        for slot, required in all_slots_min.items():
            offset, shift, team_code = slot
            model += coverage_expr(offset, shift, team_code) + miss_min[slot] >= required, f"c2_{offset}_{shift}_{team_code}"

        for slot, target in all_slots_ideal.items():
            offset, shift, team_code = slot
            model += coverage_expr(offset, shift, team_code) + miss_ideal[slot] >= target, f"c3_{offset}_{shift}_{team_code}"

        medium_time = time.time() - start_wall
        
        # print(f"ILP model built in {medium_time:.2f} seconds. Starting solver...")

        preferred_solver = os.environ.get("SCHEDULER_SOLVER", "CBC").upper()

        # timeLimit faz o CBC parar ao fim de N segundos e retornar
        # a melhor solução inteira encontrada até esse momento.
        solver = None
        if preferred_solver == "GUROBI":
            try:
                solver = pulp.GUROBI(
                    msg=0,
                    timeLimit=self.ILP_TIME_LIMIT_SECONDS,
                    gapRel=0.02,
                    Threads=8,
                    Method=2,      # Barrier method
                    Presolve=2     # Aggressive presolve
                )
                # print("Using GUROBI solver")
            except Exception as exc:
                print(f"GUROBI not available ({exc}), falling back to CBC")

        if solver is None:
            solver = pulp.PULP_CBC_CMD(
                msg=0,
                timeLimit=self.ILP_TIME_LIMIT_SECONDS,
                gapRel=0.02,   # para de procurar quando a melhoria possível for < 2% do objective
                gapAbs=1.0,    # para de procurar quando a melhoria possível for < 1 unidade do objective
                threads=4,      # força 1 thread para evitar problemas de concorrência
            )
            print("Using CBC solver")

        # print(f"Number of variables: {len(model.variables())}, Number of constraints: {len(model.constraints)}")
        
        try:
            model.solve(solver)
        except Exception as exc:
            if not isinstance(solver, pulp.PULP_CBC_CMD):
                print(f"Solver execution failed with {type(solver).__name__} ({exc}), retrying with CBC")
                solver = pulp.PULP_CBC_CMD(
                    msg=0,
                    timeLimit=self.ILP_TIME_LIMIT_SECONDS,
                    gapRel=0.02,
                    gapAbs=1.0,
                    threads=4,
                )
                model.solve(solver)
            else:
                raise
        # print(f"Status: {pulp.LpStatus[model.status]}, Objective: {pulp.value(model.objective)}")

        wall_time = time.time() - medium_time - start_wall

        # print(f"ILP solved in {wall_time:.2f} seconds. Status: {pulp.LpStatus[model.status]}")

        self.total_ilp_time += wall_time
        self.ilp_times_log.append((week_start_day, wall_time))

        result = {}
        team_assignments = {}
        for emp_id in employees_this_week:
            chosen_pat  = None
            chosen_team = None
            best_val    = -1
            for (i, team_code), var in x[emp_id].items():
                val = pulp.value(var)
                if val is not None and val > best_val:
                    best_val    = val
                    chosen_pat  = pattern_list[emp_id][i]
                    chosen_team = team_code

            if chosen_pat is None and pattern_list[emp_id]:
                chosen_pat  = pattern_list[emp_id][0]
                emp_teams   = self.emp_allowed_teams.get(emp_id, [])
                chosen_team = emp_teams[0] if emp_teams else None

            result[emp_id]           = chosen_pat
            team_assignments[emp_id] = chosen_team

        return result, team_assignments

    # =========================================================================
    # PHASE 1 — BUILD IDEALS (ILP weekly loop)
    # =========================================================================

    def build_ideals(self):
        

        weeks = (self.num_days + self.spacing - 1) // self.spacing

        employees = self.employees
        Previous_weekrank = {f: None for f in employees}

        for week_index in range(weeks):
            print(f"Week {week_index + 1}")

            week_number    = week_index + 1
            week_start_day = week_index * self.spacing + 1 
            week_end_day   = min(week_start_day + self.spacing - 1, self.num_days)

            print (f"Week {week_number}: days {week_start_day} to {week_end_day}")

            sun_hol_offsets_week = set()
            
            for offset in range(self.spacing):
                day_1b = week_start_day + offset
                if 1 <= day_1b <= self.num_days and self.dates[day_1b - 1] in self._sun_hol_set:
                    sun_hol_offsets_week.add(offset)

            Weekly_Attributions = self.build_Weekly_Possible_Atributions(sun_hol_offsets=sun_hol_offsets_week)
            self.weekly_possible_attributions = Weekly_Attributions

            Weekly_Attributions_Dyn = {f: [] for f in employees}

            mins   = self.construct_mins_table(self.minimos, self.dates, self.teams, week_number, self.shifts, self.spacing)
            ideals = self.construct_ideals_table(self.ideais, self.dates, self.teams, week_number, self.shifts, self.spacing)

            chosen_patterns, team_assignments = self.EvaluateWeeks(
                week_index,
                employees,
                Previous_weekrank,
                Weekly_Attributions,
                Weekly_Attributions_Dyn,
                mins,
                ideals,
                week_start_day=week_start_day,
            )

            # print(f"Chosen patterns for week {week_number}:")
            # print(chosen_patterns)

            random.shuffle(employees)

            for e in employees:
                attribution = chosen_patterns.get(e)
                if not attribution:
                    continue

                team = team_assignments.get(e)
                if team is None:
                    emp_teams = self.emp_allowed_teams[e]
                    team = emp_teams[0] if emp_teams else None

                for day_offset, shift in enumerate(attribution):
                    day = week_start_day + day_offset
                    if day > week_end_day:
                        break
                    if shift == 0:
                        continue
                    self._assign(e, day, shift, team)

                Weekly_Attributions_Dyn[e] = attribution
                Previous_weekrank[e]       = attribution
                self.patterns_used.add(attribution)
        
        patterns_not_used = set(Weekly_Attributions.keys()) - self.patterns_used
        print(f"Patterns not used: {(patterns_not_used)} - length: {len(patterns_not_used)}")
        print(f"================================")
        print(f"Patterns used: {(self.patterns_used)} - length: {len(self.patterns_used)}")

        return True

    # =========================================================================
    # PHASE 2 — POST-PROCESSING (remove excess, add sunday/holiday workers)
    # =========================================================================

    def remove_one(self, emp_id, day_1b, shift, team, cov, total_days_emp, sun_hol_emp, sun_hol_set):
        """
        Remove uma atribuição — actualiza estruturas globais via _unassign
        e os contadores locais de Excessive_deletion.
        """
        self._unassign(emp_id, day_1b, shift, team)
        date = self.dates[day_1b - 1]
        cov[(date, shift, team)] = max(0, cov.get((date, shift, team), 1) - 1)
        total_days_emp[emp_id]   = max(0, total_days_emp[emp_id] - 1)
        if date in sun_hol_set:
            sun_hol_emp[emp_id] = max(0, sun_hol_emp[emp_id] - 1)

    def Remove_Excessive_Ideals(self, date_to_day, max_days, total_days_emp, cov, sun_hol_emp, sun_hol_set):
        for (date, s, t) in list(cov.keys()):
            ideal = self.ideais.get((date, s, t), 0)
            day   = date_to_day.get(date, date)

            while cov[(date, s, t)] > ideal:
                candidates = []
                for emp_id, shift, team in self.assignment_by_day.get(day, []):
                    if shift == s and team == t:
                        candidates.append((total_days_emp[emp_id], emp_id))

                if not candidates:
                    break
                
                # Ordenar candidatos por total_days_emp (maior primeiro) e escolher o primeiro, com empates resolvidos aleatoriamente
                random.shuffle(candidates)
                candidates.sort(key=lambda x: x[0], reverse=True)
                _, to_remove = candidates[0]

                if to_remove is not None:
                    self.remove_one(to_remove, day, s, t, cov,
                                    total_days_emp, sun_hol_emp, sun_hol_set)
                    self.removed_days += 1

        return True

    def Fix_Weekday_Ideals(self, total_days_emp, sun_hol_emp, sun_hol_set):
        """
        Pós-processamento: percorre todos os dias normais onde
        os ideais não estão cumpridos e tenta adicionar funcionários.
        """
        days_assignments = self.recreate_days(self.assignment)
        scores = {emp_id: 0 for emp_id in self.employees}

        normal_days = [d for d in self.dates if d not in self._sun_hol_set]

        deficit_days = []
        for d in normal_days:
            day_index = self.dates.index(d) + 1
            for shift in range(1, self.shifts + 1):
                for team_code in self.teams.keys():
                    key = (d, shift, team_code)
                    ideal = self.ideais.get(key, 0)
                    if ideal == 0:
                        continue
                    actual = sum(
                        1 for emp, s, t in days_assignments.get(day_index, [])
                        if s == shift and t == team_code
                    )
                    if actual < ideal:
                        deficit_days.append((day_index, d, shift, team_code, ideal - actual))

        random.shuffle(deficit_days)

        for day_index, d, needed_shift, needed_team, deficit in deficit_days:
            employees_worked_today = {
                emp for emp, _, _ in days_assignments.get(day_index, [])
            }
            previous_days_emp = {
                emp: shift
                for emp, shift, _ in days_assignments.get(day_index - 1, [])
            }

            order = self.order_of_ranks(scores)

            added = 0
            for emp_id in order:
                if added >= deficit:
                    break
                if emp_id in employees_worked_today:
                    continue
                if d in self.vacations_dates[emp_id]:
                    continue
                if total_days_emp.get(emp_id, 0) >= self.MAX_DAYS:
                    continue
                if self.consecutivechecker(emp_id, day_index, days_assignments) > self.MAX_CONSECUTIVE:
                    continue
                if needed_team not in self.emp_allowed_teams.get(emp_id, []):
                    continue

                prev_shift = previous_days_emp.get(emp_id)
                if prev_shift and not self._validate_block_transition(prev_shift, needed_shift):
                    continue
                next_shift = self.get_next_assigned_shift(emp_id, day_index)
                if next_shift and not self._validate_block_transition(needed_shift, next_shift):
                    continue

                self._assign(emp_id, day_index, needed_shift, needed_team)
                days_assignments[day_index].append((emp_id, needed_shift, needed_team))
                total_days_emp[emp_id] = total_days_emp.get(emp_id, 0) + 1
                employees_worked_today.add(emp_id)
                added += 1

                scores[emp_id] = self.choose_Employee(
                    self.Total_Days,
                    {emp_id: self.consecutivechecker(emp_id, day_index, days_assignments)},
                    previous_days_emp,
                    self.emp_allowed_teams[emp_id],
                    emp_id,
                    day_index,
                )

    def build_ideal_assignments(self, total_days_emp, sun_hol_emp, sun_hol_set):
        """
        Phase 2: fill ideal slots on normal weekdays that still have deficit.
        """
        days_assignments = self.recreate_days(self.assignment)
        Pontuation = {emp_id: 0 for emp_id in self.employees}

        normal_days = [d for d in self.dates if d not in self._sun_hol_set]

        deficit_days = []
        for day_date in normal_days:
            day_index = self.dates.index(day_date) + 1
            for shift in range(1, self.shifts + 1):
                for team_code in self.teams.keys():
                    key = (day_date, shift, team_code)
                    ideal = self.ideais.get(key, 0)
                    if ideal == 0:
                        continue
                    actual = sum(
                        1 for emp, s, t in days_assignments.get(day_index, [])
                        if s == shift and t == team_code
                    )
                    if actual < ideal:
                        deficit_days.append((day_index, day_date, shift, team_code, ideal - actual))

        funcionarios = self.employees
        turnos       = range(1, self.shifts + 1)
        random.shuffle(deficit_days)

        for day_index, day_date, _shift, _team_code, _deficit in deficit_days:
            Actual_Streaks = {
                f: self.consecutivechecker(f, day_index, days_assignments)
                for f in funcionarios
            }
            Employees_Worked_today     = {emp for emp, _, _ in days_assignments.get(day_index, [])}
            Employees_Worked_Yesterday = {emp for emp, _, _ in days_assignments.get(day_index - 1, [])}

            Previous_days_emp = {}
            for emp_id in Employees_Worked_Yesterday:
                for emp, shift, team_code in days_assignments.get(day_index - 1, []):
                    if emp == emp_id:
                        Previous_days_emp[emp_id] = shift

            ideals = {}
            for s in turnos:
                for team_code in self.teams.keys():
                    key = (day_date, s, team_code)
                    if key in self.ideais:
                        ideals[(s, team_code)] = self.ideais[key]

            ideals_Table = self.evaluate_Day_Toshifts_ideais(day_date, ideals)
            Order = self.order_of_ranks(Pontuation)

            for f in Order:
                if f in Employees_Worked_today:
                    continue
                if day_date in self.vacations_dates[f]:
                    continue
                if self.Total_Days.get(f, 0) >= self.MAX_DAYS:
                    continue
                if Actual_Streaks[f] > self.MAX_CONSECUTIVE:
                    continue
                if day_date in self.sundays_holidays and self.sundays_holidays_worked.get(f, 0) >= self.MAX_SUN_HOL:
                    continue

                Emp_Teams = self.emp_allowed_teams[f]
                most_needed = sorted(
                    (
                        (team, len(shifts_needed["optional"]))
                        for team, shifts_needed in ideals_Table.items()
                        if team in Emp_Teams and shifts_needed["optional"]
                    ),
                    key=lambda x: x[1],
                    reverse=True,
                )

                assigned = False
                for team_code, shifts_needed_count in most_needed:
                    if assigned:
                        break
                    optional_shifts = ideals_Table[team_code]["optional"]
                    if shifts_needed_count <= 0:
                        continue
                    for slot_index, candidate_shift in enumerate(optional_shifts):
                        prev_shift = Previous_days_emp.get(f)
                        if prev_shift is not None and not self._validate_block_transition(prev_shift, candidate_shift):
                            continue
                        next_shift = self.get_next_assigned_shift(f, day_index)
                        if next_shift is not None and not self._validate_block_transition(candidate_shift, next_shift):
                            continue
                        assigned_shift = optional_shifts.pop(slot_index)
                        self._assign(f, day_index, assigned_shift, team_code)
                        days_assignments[day_index].append((f, assigned_shift, team_code))
                        total_days_emp[f] = total_days_emp.get(f, 0) + 1
                        Employees_Worked_today.add(f)
                        assigned = True
                        break
                    if assigned:
                        break

                if not assigned:
                    Actual_Streaks[f] = 0

                Pontuation[f] = self.choose_Employee(
                    self.Total_Days,
                    Actual_Streaks,
                    Previous_days_emp,
                    self.emp_allowed_teams[f],
                    f,
                    day_index,
                )

        return True

    def Add_Sunday_Holiday_Workers(self, total_days_emp, cov, sun_hol_emp, sun_hol_set):
        """
        Sequential fixing para adicionar trabalhadores a domingos/feriados
        sub-ideais, respeitando o limite de MAX_SUN_HOL por funcionário.
        """
        employees            = self.employees
        turnos               = range(1, self.shifts + 1)
        all_sundays_holidays = set(self.sundays_holidays)

        days_assignments = self.recreate_days(self.assignment)
        scores           = {emp_id: 0 for emp_id in employees}

        def build_requirements(day_date, day_index):
            mins   = {}
            ideals = {}
            for shift in turnos:
                for team_code in self.teams.keys():
                    key = (day_date, shift, team_code)
                    if key in self.minimos:
                        already = sum(
                            1 for emp, s, t in days_assignments.get(day_index, [])
                            if s == shift and t == team_code
                        )
                        remaining = max(0, self.minimos[key] - already)
                        if remaining > 0:
                            mins[(shift, team_code)] = remaining
                    if key in self.ideais:
                        already = sum(
                            1 for emp, s, t in days_assignments.get(day_index, [])
                            if s == shift and t == team_code
                        )
                        remaining = max(0, self.ideais[key] - already)
                        if remaining > 0:
                            ideals[(shift, team_code)] = remaining

            return (
                self.evaluate_Day_Toshifts_minimos(day_date, mins),
                self.evaluate_Day_Toshifts_ideais(day_date, ideals),
            )

        mins_added   = 0
        ideals_added = 0

        for phase in range(2):
            random_days = list(all_sundays_holidays)
            random.shuffle(random_days)

            for d in random_days:
                day_index = self.dates.index(d) + 1
                day_date  = day_index

                actual_streaks = {
                    emp_id: self.consecutivechecker(emp_id, day_date, days_assignments)
                    for emp_id in employees
                }

                employees_worked_today     = {emp for emp, _, _ in days_assignments.get(day_date, [])}
                employees_worked_yesterday = {emp for emp, _, _ in days_assignments.get(day_date - 1, [])}

                previous_days_emp = {}
                for emp_id in employees_worked_yesterday:
                    for emp, shift, _team_code in days_assignments.get(day_date - 1, []):
                        if emp == emp_id:
                            previous_days_emp[emp_id] = shift

                mins_table, ideals_table = build_requirements(d, day_index)
                order = self.order_of_ranks(scores)

                for emp_id in order:
                    if emp_id in employees_worked_today:
                        continue
                    if d in self.vacations_dates[emp_id]:
                        continue
                    if total_days_emp.get(emp_id, 0) >= self.MAX_DAYS:
                        continue
                    if actual_streaks[emp_id] > self.MAX_CONSECUTIVE:
                        continue
                    if d in self.sundays_holidays and sun_hol_emp.get(emp_id, 0) >= self.MAX_SUN_HOL:
                        continue

                    emp_teams = self.emp_allowed_teams[emp_id]

                    if phase == 0:
                        slots_by_team = sorted(
                            (
                                (team, len(shifts_needed["mandatory"]))
                                for team, shifts_needed in mins_table.items()
                                if team in emp_teams and shifts_needed["mandatory"]
                            ),
                            key=lambda item: item[1],
                            reverse=True,
                        )
                    else:
                        slots_by_team = sorted(
                            (
                                (team, len(shifts_needed["optional"]))
                                for team, shifts_needed in ideals_table.items()
                                if team in emp_teams and shifts_needed["optional"]
                            ),
                            key=lambda item: item[1],
                            reverse=True,
                        )

                    assigned = False

                    for team_code, shifts_needed_count in slots_by_team:
                        if assigned:
                            break

                        candidate_shifts = (
                            mins_table[team_code]["mandatory"]
                            if phase == 0
                            else ideals_table[team_code]["optional"]
                        )

                        if shifts_needed_count <= 0:
                            continue

                        for slot_index, candidate_shift in enumerate(candidate_shifts):
                            prev_shift = previous_days_emp.get(emp_id)
                            if prev_shift is not None and not self._validate_block_transition(prev_shift, candidate_shift):
                                continue

                            next_shift = self.get_next_assigned_shift(emp_id, day_date)
                            if next_shift is not None and not self._validate_block_transition(candidate_shift, next_shift):
                                continue

                            assigned_shift = candidate_shifts.pop(slot_index)

                            self._assign(emp_id, day_date, assigned_shift, team_code)
                            days_assignments[day_date].append((emp_id, assigned_shift, team_code))
                            total_days_emp[emp_id] += 1
                            if d in self.sundays_holidays:
                                sun_hol_emp[emp_id] += 1

                            actual_streaks[emp_id] = self.consecutivechecker(emp_id, day_date, days_assignments)
                            employees_worked_today.add(emp_id)

                            assigned = True
                            if phase == 0:
                                mins_added += 1
                            else:
                                ideals_added += 1
                            break

                        if assigned:
                            break

                    if not assigned:
                        actual_streaks[emp_id] = 0

                    scores[emp_id] = self.choose_Employee(
                        self.Total_Days,
                        actual_streaks,
                        previous_days_emp,
                        self.emp_allowed_teams[emp_id],
                        emp_id,
                        day_date,
                    )

        return True

    def Pos_Weeks(self, max_days=None, max_sun_hol=None):

        max_days    = max_days    or self.MAX_DAYS
        max_sun_hol = max_sun_hol or self.MAX_SUN_HOL
        sun_hol_set = set(self.sundays_holidays)

        def build_coverage():
            cov = {}
            for emp_id, entries in self.assignment.items():
                for day_1b, shift, team in entries:
                    date = self.dates[day_1b - 1]
                    cov[(date, shift, team)] = cov.get((date, shift, team), 0) + 1
            return cov

        cov = build_coverage()

        total_days_emp = {e: len(self.assignment.get(e, [])) for e in self.employees}
        sun_hol_emp    = {
            e: sum(1 for d, _, _ in self.assignment.get(e, [])
                   if self.dates[d - 1] in sun_hol_set)
            for e in self.employees
        }

        emp_order = list(self.employees)
        random.shuffle(emp_order)

        date_to_day = {date: idx + 1 for idx, date in enumerate(self.dates)}

        self.Remove_Excessive_Ideals(date_to_day, max_days, total_days_emp, cov, sun_hol_emp, sun_hol_set)
        self.Add_Sunday_Holiday_Workers(total_days_emp, cov, sun_hol_emp, sun_hol_set)
        
        
        self.Fix_Weekday_Ideals(total_days_emp, sun_hol_emp, sun_hol_set)
        # self.build_ideal_assignments(total_days_emp, sun_hol_emp, sun_hol_set)
        
        
        # Check days worked in total per employee
        for emp_id in self.employees:
            if total_days_emp.get(emp_id, 0) > max_days:
                print(f"Warning: Employee {emp_id} has {total_days_emp[emp_id]} days assigned, exceeding max_days {max_days}.")
            if sun_hol_emp.get(emp_id, 0) > max_sun_hol:
                print(f"Warning: Employee {emp_id} has {sun_hol_emp[emp_id]} Sundays/Holidays assigned, exceeding max_sun_hol {max_sun_hol}.")
        
        return True

    # =========================================================================
    # MAIN SOLVE
    # =========================================================================

    def solve(self, n_grasp_runs=1, record_history=True, history_file=None):

        print(f"\n{'='*80}")
        print(f"[Heuristica] EXECUTING")
        print(f"{'='*80}")

        start_wall = time.time()

        self.solution_history = []
        self.best_solution_state = None
        self.best_solution_kpis = None

        self.build_ideals()
        self.exact_solution_state = self._capture_ideal_state()

        runs = max(1, int(n_grasp_runs or 1))
        best_score = None

        for run_index in range(1, runs + 1):
            self._restore_ideal_state(self.exact_solution_state)
            self.Pos_Weeks()

            kpis = self.evaluate_kpis()
            solution_state = self._capture_ideal_state()
            solution_table = self.to_table()

            if record_history:
                self.solution_history.append({
                    "run": run_index,
                    "kpis": copy.deepcopy(kpis),
                    "table": copy.deepcopy(solution_table),
                })

            # NOVO: escrever esta run para ficheiro imediatamente
            if history_file:
                with open(history_file, "a", encoding="utf-8") as fh:
                    fh.write(f"Run {run_index}: missed_mins={kpis['missed_mins']}, missed_ideals={kpis['missed_ideals']}\n")

            
            score = (kpis["missed_mins"], kpis["missed_ideals"])
            if best_score is None or score < best_score:
                best_score = score
                self.best_solution_state = solution_state
                self.best_solution_kpis = copy.deepcopy(kpis)

        if self.best_solution_state is not None:
            self._restore_ideal_state(self.best_solution_state)

        kpis = self.evaluate_kpis()

        print(f"  Mins por cumprir  : {kpis['missed_mins']}")
        print(f"  Ideais por cumprir: {kpis['missed_ideals']}")
        print(f"  Solucoes GRASP    : {runs}")

        wall_time = time.time() - start_wall
        print(f"\n[Heuristica] Concluído em {wall_time:.1f}s")

        note_filename = "/app/heuristica_note.txt"

        with open(note_filename, "a", encoding="utf-8") as note_file:
            note_file.write(f"Spacing: {self.spacing}\n")
            note_file.write(f"Heuristica completed in {wall_time:.1f} seconds.\n")
            note_file.write(f"Missed minimums: {kpis['missed_mins']}\n")
            note_file.write(f"Missed ideals: {kpis['missed_ideals']}\n")
            note_file.write(f"GRASP runs: {runs}\n")
            note_file.write("-" * 50 + "\n")

        return True

    # =========================================================================
    # STATE CAPTURE / RESTORE / RESET
    # =========================================================================

    def _capture_ideal_state(self):
        return {
            "assignment":              copy.deepcopy(self.assignment),
            "assignment_by_day":       copy.deepcopy(self.assignment_by_day),
            "Total_Days":              copy.deepcopy(self.Total_Days),
            "sundays_holidays_worked": copy.deepcopy(self.sundays_holidays_worked),
            "ideal_assignments":       copy.deepcopy(getattr(self, "ideal_assignments", defaultdict(list))),
        }

    def _restore_ideal_state(self, state):
        self.assignment              = copy.deepcopy(state["assignment"])
        self.assignment_by_day       = copy.deepcopy(state["assignment_by_day"])
        self.Total_Days              = copy.deepcopy(state["Total_Days"])
        self.sundays_holidays_worked = copy.deepcopy(state["sundays_holidays_worked"])
        self.ideal_assignments       = copy.deepcopy(state["ideal_assignments"])

    def _reset_for_new_outer(self):
        self.assignment              = defaultdict(list)
        self.assignment_by_day       = defaultdict(list)
        self.Total_Days              = {f: 0 for f in self.employees}
        self.sundays_holidays_worked = {f: 0 for f in self.employees}
        self.ideal_assignments       = defaultdict(list)

    # =========================================================================
    # OUTPUT
    # =========================================================================

    def export_csv(self, filename="schedule_weighted.csv"):
        export_schedule_to_csv(self, filename)

    def to_table(self):
        header = ["funcionario"] + [f"Dia {i}" for i in range(1, self.num_days + 1)]
        rows   = [header]
        label  = {1: "M_", 2: "T_", 3: "N_"}
        n_emps = len(self.employee_rows)

        for emp_id in range(1, n_emps + 1):
            vac_days  = set(self.vacs_1based.get(emp_id, []))
            day_to_st = {d: (s, t) for (d, s, t) in self.assignment.get(emp_id, [])}
            line      = [str(emp_id)]

            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_st:
                    s, team_id = day_to_st[d]
                    line.append(label.get(s, "") + TEAM_ID_TO_CODE.get(team_id, "A"))
                else:
                    line.append("0")
            rows.append(line)

        return rows

    def evaluate_kpis(self) -> dict:
        assigned_counts: dict = {}
        for emp_id, entries in self.assignment.items():
            for day_1b, shift, team_id in entries:
                if 1 <= day_1b <= self.num_days:
                    date = self.dates[day_1b - 1]
                    key  = (date, shift, team_id)
                    assigned_counts[key] = assigned_counts.get(key, 0) + 1

        missed_mins = 0
        for (date, shift, team_id), required in self.minimos.items():
            actual       = assigned_counts.get((date, shift, team_id), 0)
            missed_mins += max(0, required - actual)

        missed_ideals = 0
        for (date, shift, team_id), target in self.ideais.items():
            actual         = assigned_counts.get((date, shift, team_id), 0)
            missed_ideals += max(0, target - actual)

        return {"missed_mins": missed_mins, "missed_ideals": missed_ideals}


# =============================================================================
# ENTRY POINT
# =============================================================================

def solve(vacations=None, minimuns=None, employees=None, maxTime=None,
          year=2021, hours=13, work_blocks=None, rules=None, **kwargs):

    max_seconds = int(maxTime * 60) if maxTime else 3600
    grasp_runs = 3000
    solution_history_path = kwargs.get("solution_history_path")
    spacing_list = [3]
    history_file = "/app/grasp_history.txt"
    Full = False

    # Limpar o ficheiro antes de começar
    open(history_file, "w").close()

    timeout_event = threading.Event()
    timer = threading.Timer(max_seconds, timeout_event.set)

    def check_timeout():
        if timeout_event.is_set():
            raise SchedulerTimeout(f"O scheduler excedeu o tempo máximo ({max_seconds}s).")

    timer.start()
    best_table = None
    best_kpis  = {"missed_mins": float("inf"), "missed_ideals": float("inf")}

    try:
        for spacing in spacing_list:
            print(f"\n[Heuristica] Executando com spacing={spacing}...")

            # Escrever cabeçalho do spacing no ficheiro
            with open(history_file, "a", encoding="utf-8") as fh:
                fh.write(f"\n{'-'*58}\n")
                fh.write(f"Spacing = {spacing}\n")
                fh.write(f"{'-'*58}\n")

            scheduler = Heuristica(
                vacations_rows=vacations,
                minimums_rows=minimuns,
                employees=employees,
                maxTime=maxTime,
                year=year,
                shifts=hours,
                spacing=spacing,
                full=Full
            )

            check_timeout()
            scheduler.solve(n_grasp_runs=grasp_runs, record_history=True, history_file=history_file)
            check_timeout()

            scheduler.export_ilp_time_summary("/app/ilp_times.csv")
            n_weeks = len(scheduler.ilp_times_log)
            avg = scheduler.total_ilp_time / n_weeks if n_weeks else 0.0
            print(f"[Heuristica] Spacing {spacing}: tempo total ILP = "
                  f"{scheduler.total_ilp_time:.1f}s em {n_weeks} semanas "
                  f"(média {avg:.2f}s/semana)")

            kpis = scheduler.evaluate_kpis()
            if (kpis["missed_mins"], kpis["missed_ideals"]) < (best_kpis["missed_mins"], best_kpis["missed_ideals"]):
                best_kpis  = kpis
                best_table = scheduler.to_table()

    except SchedulerTimeout:
        print(f"\n[Heuristica] Timeout após {max_seconds}s — a retornar a melhor solução encontrada.")
        if best_table is None:
            raise SchedulerTimeout(f"O scheduler excedeu o tempo máximo ({max_seconds}s) antes de completar uma iteração.")
    finally:
        timer.cancel()

    return best_table
    