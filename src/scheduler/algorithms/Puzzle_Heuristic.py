import copy
import csv
from collections import defaultdict
import datetime
from itertools import cycle, groupby
import threading
import os

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

    MAX_DAYS             = 223
    MAX_SUN_HOL          = 22
    MAX_CONSECUTIVE      = 5
    TARGET_DAYS_PER_WEEK = 201 / 52

    # ILP time limit por semana (segundos) — CBC abandona e retorna a melhor solução encontrada
    ILP_TIME_LIMIT_SECONDS = 30

    # Employee scoring weights
    W_PACE    = 0.52
    W_SEQ     = 0.38
    W_SUN_HOL = 0.00
    W_TEAMS   = 0.05
    W_TRANS   = 0.15

    def __init__(self, vacations_rows, minimums_rows, employees,
                 maxTime, year=2025, shifts=2, w_min=100, w_ideal=1):
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
        self.year = year
        self.shifts = 3
        self.w_min = w_min
        self.w_ideal = w_ideal

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

    def choose_Employee(self, Worked_Total_Days, Worked_Sequential_Days,
                        Worked_Previous_Day, emp_allowed_teams, f, d):

        total_days = Worked_Total_Days.get(f, 0)
        pace_delta = total_days / self.MAX_DAYS
        pace_component = max(0.0, 1.0 - pace_delta ** 2)

        streak = Worked_Sequential_Days.get(f, 0)
        seq_component = max(0.0, 1.0 - (streak / self.MAX_CONSECUTIVE) ** 2)

        sun_hol = self.sundays_holidays_worked.get(f, 0)
        sun_hol_component = max(0.0, 1.0 - sun_hol / self.MAX_SUN_HOL)

        num_teams = len(emp_allowed_teams)
        max_teams = max(len(v) for v in self.emp_allowed_teams.values())
        team_component = max(0.0, 0.6 - (num_teams) / (max_teams)) if max_teams > 1 else 0.0

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

    def build_Weekly_Possible_Atributions(self, week_length=7):
        weekly_attributions = {}

        if week_length <= 0:
            return weekly_attributions

        def backtrack(day_index, previous_shift, worked_streak, current_pattern):
            if day_index == week_length:
                zero_positions = [i for i, s in enumerate(current_pattern) if s == 0]
                if all(
                    (nz - pz) > self.MAX_CONSECUTIVE
                    for pz, nz in zip(zero_positions, zero_positions[1:])
                ):
                    weekly_attributions[tuple(current_pattern)] = 0
                return

            current_pattern.append(0)
            backtrack(day_index + 1, None, 0, current_pattern)
            current_pattern.pop()

            if worked_streak >= self.MAX_CONSECUTIVE:
                return

            for shift in range(1, self.shifts + 1):
                if previous_shift is not None and not self._validate_block_transition(previous_shift, shift):
                    continue
                current_pattern.append(shift)
                backtrack(day_index + 1, shift, worked_streak + 1, current_pattern)
                current_pattern.pop()

        backtrack(0, None, 0, [])
        return weekly_attributions

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
        sun_hol_set = set(self.sundays_holidays)

        # Offsets relativos à semana actual que são domingos ou feriados
        sun_hol_offsets = set()
        if week_start_day is not None:
            for offset in range(7):
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
                for offset in range(7):
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

            for pattern in Weekly_Attributions:
                start_streak = 0
                valid = True
                for shift in pattern:
                    if shift == 0:
                        break
                    if shift not in first_allowed:
                        valid = False
                        break
                    start_streak += 1

                if not valid or start_streak > max_start_streak:
                    continue

                masked = mask_pattern_emp(pattern, emp_vac_offsets)
                if masked not in seen:
                    seen.add(masked)
                    filtered.append(masked)

            if not filtered and Weekly_Attributions:
                filtered = [mask_pattern_emp(next(iter(Weekly_Attributions)), emp_vac_offsets)]

            admissible[emp_id] = filtered

        all_slots_min = {}
        all_slots_ideal = {}

        for day_1b, shift_team_dict in mins.items():
            offset = (day_1b - 1) % 7
            if offset in sun_hol_offsets:
                continue
            for (shift, team_code), count in shift_team_dict.items():
                key = (offset, shift, team_code)
                all_slots_min[key] = all_slots_min.get(key, 0) + count

        for day_1b, shift_team_dict in ideals.items():
            offset = (day_1b - 1) % 7
            if offset in sun_hol_offsets:
                continue
            for (shift, team_code), count in shift_team_dict.items():
                key = (offset, shift, team_code)
                all_slots_ideal[key] = all_slots_ideal.get(key, 0) + count

        all_patterns = set(p for patterns in admissible.values() for p in patterns)

        delta = {}
        for pattern in all_patterns:
            for offset in range(7):
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

        w_days = 2.6

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

        # timeLimit faz o CBC parar ao fim de N segundos e retornar
        # a melhor solução inteira encontrada até esse momento.
        solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=self.ILP_TIME_LIMIT_SECONDS)
        model.solve(solver)

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
        Weekly_Attributions = self.build_Weekly_Possible_Atributions()
        self.weekly_possible_attributions = Weekly_Attributions

        weeks = (self.num_days + 6) // 7

        employees = self.employees
        Previous_weekrank = {f: None for f in employees}

        for week_index in range(weeks):
            print(f"Week {week_index + 1}")

            week_number    = week_index + 1
            week_start_day = week_index * 7 + 1
            week_end_day   = min(week_start_day + 6, self.num_days)

            Weekly_Attributions_Dyn = {f: [] for f in employees}

            mins   = self.construct_mins_table(self.minimos, self.dates, self.teams, week_number, self.shifts)
            ideals = self.construct_ideals_table(self.ideais, self.dates, self.teams, week_number, self.shifts)

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
        return True

    # =========================================================================
    # MAIN SOLVE
    # =========================================================================

    def solve(self):

        print(f"\n{'='*80}")
        print(f"[Heuristica] EXECUTING")
        print(f"{'='*80}")

        start_wall = time.time()

        self.build_ideals()
        self.Pos_Weeks()

        kpis = self.evaluate_kpis()

        print(f"  Mins por cumprir  : {kpis['missed_mins']}")
        print(f"  Ideais por cumprir: {kpis['missed_ideals']}")

        wall_time = time.time() - start_wall
        print(f"\n[Heuristica] Concluído em {wall_time:.1f}s")

        note_filename = "/app/heuristica_note.txt"

        with open(note_filename, "a", encoding="utf-8") as note_file:
            note_file.write(f"Heuristica completed in {wall_time:.1f} seconds.\n")
            note_file.write(f"Missed minimums: {kpis['missed_mins']}\n")
            note_file.write(f"Missed ideals: {kpis['missed_ideals']}\n")
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

    # maxTime vem em minutos — converter para segundos
    max_seconds = int(maxTime * 60) if maxTime else 3600

    # threading.Event partilhado: quando activado, o loop verifica e lança SchedulerTimeout.
    # Funciona em qualquer thread, ao contrário de signal.SIGALRM.
    timeout_event = threading.Event()
    timer = threading.Timer(max_seconds, timeout_event.set)

    def check_timeout():
        if timeout_event.is_set():
            raise SchedulerTimeout(
                f"O scheduler excedeu o tempo máximo ({max_seconds}s)."
            )

    timer.start()
    best_table = None
    best_kpis  = {"missed_mins": float("inf"), "missed_ideals": float("inf")}

    try:
        scheduler = Heuristica(
            vacations_rows=vacations,
            minimums_rows=minimuns,
            employees=employees,
            maxTime=maxTime,
            year=year,
            shifts=hours,
        )

        for i in range(1, 11):
            check_timeout()

            print(f"\n{'='*80}")
            print(f"[Heuristica] Outer loop iteration {i}")
            print(f"{'='*80}")

            scheduler.solve()
            check_timeout()

            kpis = scheduler.evaluate_kpis()
            if (kpis["missed_mins"], kpis["missed_ideals"]) < (best_kpis["missed_mins"], best_kpis["missed_ideals"]):
                best_kpis  = kpis
                best_table = scheduler.to_table()

            scheduler._reset_for_new_outer()

    except SchedulerTimeout:
        print(f"\n[Heuristica] Timeout após {max_seconds}s — a retornar a melhor solução encontrada.")
        if best_table is None:
            raise SchedulerTimeout(
                f"O scheduler excedeu o tempo máximo ({max_seconds}s) "
                "antes de completar uma iteração."
            )
    finally:
        timer.cancel()

    return best_table