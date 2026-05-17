import copy
import csv
from collections import defaultdict
import datetime

import numpy as np
import pandas as pd
import pulp
import holidays
import time
import random

from algorithms.assignmentmap import print_daily_assignment_map

from algorithms.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code,
    count_minimum_failures,
    check_5_consecutive_days,
    rows_to_req_dicts_FIXED,
    count_minimum_shift_failures,
    build_calendar,
    export_schedule_to_csv,
)


class Heuristica:
    def __init__(self, vacations_rows, minimuns_rows, employees,
                 maxTime, year=2025, shifts=2, w_min=100, w_ideal=1):
        """
        Weighted ILP scheduler.

        employees: list of employee dicts (with "teams" etc.).
        Internally we index employees as 1..N for this ILP.
        """
        # Original employee dicts
        self.employee_rows = employees

        # Internal employee IDs: 1..N
        self.employees = list(range(1, len(employees) + 1))

        self.vacations_rows = vacations_rows
        self.minimuns_rows = minimuns_rows
        self.maxTime = maxTime
        self.year = year
        self.shifts = 3
        self.w_min = w_min
        self.w_ideal = w_ideal

        # === Preprocessing ===
        self.teams = self._build_teams(self.employee_rows)

        #print(f"Employee to Teams mapping: {self.teams}")

        self.emp_allowed_teams = self._build_emp_team_map(self.employee_rows)

        #print(f"Employee to Allowed Teams mapping: {self.emp_allowed_teams}")

        self.dates, sundays_idx = build_calendar(year)

        #print(f"Generated calendar for year {year} with {(self.dates)} days, {sundays_idx} Sundays.")

        self.num_days = len(self.dates)
        # convert sunday indices (1-based day numbers) to actual Timestamp objects
        sundays = {
            self.dates[idx - 1]
            for idx in sundays_idx
            if 1 <= idx <= len(self.dates)
        }

        #print(f"Identified {len(sundays)} Sundays: {sorted(sundays)}")

        # PT holidays
        pt_holidays = holidays.country_holidays("PT", years=[year])
        holiday_dates = {
            d
            for d in self.dates
            if d.date() in pt_holidays
        }

        #print(f"Identified {len(holiday_dates)} holidays: {sorted(holiday_dates)}")

        # Combined: Sundays + Holidays
        self.sundays_holidays = sorted(sundays | holiday_dates)

        #print(f"Total closed days (Sundays + Holidays): {len(self.sundays_holidays)}, Sundays + Holidays: {self.sundays_holidays}")

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

        #print(f"Processed vacations_1based for {len(self.vacs)} employees. Sample: {self.vacs}")
        #print(f"Processed vacations_dates for {len(self.vacations_dates)} employees. Sample: {self.vacations_dates}")

        mins_raw, ideals_raw = rows_to_req_dicts(minimuns_rows)
        self.minimos = {}
        self.ideais = {}
        for (day, shift, team_id), value in mins_raw.items():
            if 1 <= day <= self.num_days:
                self.minimos[(self.dates[day - 1], shift, team_id)] = int(value)
        for (day, shift, team_id), value in ideals_raw.items():
            if 1 <= day <= self.num_days:
                self.ideais[(self.dates[day - 1], shift, team_id)] = int(value)

        #print(f"Processed minimum requirements: {len(self.minimos)} entries. Sample: {(self.minimos)}")
        #print(f"Processed ideal requirements: {len(self.ideais)} entries. Sample: {(self.ideais)}")
        
        # Containers filled after solving
        self.assignment = defaultdict(list)

        # Global map after minimums

        self.Total_Days = {f: 0 for f in self.employees}
        self.sundays_holidays_worked = {f: 0 for f in self.employees}

        #print(f"assignment initialized as empty defaultdict(list): {self.assignment}")

        print(f"\n{'='*80}")
        print(f"[Heuristica] Initialized Heuristic Scheduler")
        print(f"{'='*80}")
        print(f"Year: {self.year}")
        print(f"Total Employees: {len(self.employees)}")
        print(f"Total Days: {self.num_days}")
        print(f"Store Closed Days (Sundays + Holidays): {len(self.sundays_holidays)}")
        print(f"  - {len(sundays)} Sundays")
        print(f"  - {len(holiday_dates)} Holidays")
        print(f"Total Vacations: {sum(len(v) for v in self.vacs.values())}")
        print(f"Total Minimum Requirements: {len(self.minimos)}")
        print(f"Total Ideal Requirements: {len(self.ideais)}")
        print(f"Teams: {len(self.teams)}")
        for team_id, emp_set in self.teams.items():
            print(f"  Team {TEAM_ID_TO_CODE.get(team_id, team_id)}: {len(emp_set)} employees")
        print(f"Max Time (minutes): {self.maxTime}")
        

    # ------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------
    def _build_emp_team_map(self, employees):
        """
        Map employee_id (1..N) -> list of allowed team_ids.
        """
        mapping = {}
        for i, e in enumerate(employees, start=1):
            codes = [get_team_code(t) for t in e.get("teams", []) if t]
            ids = [get_team_id(c) for c in codes if c]
            if not ids:
                ids = [get_team_id("A")]
            mapping[i] = ids
        return mapping

    def _build_teams(self, employees):
        """
        Build dictionary of teams: team_id → set of employee_ids (1..N)
        """
        teams = {}
        for i, e in enumerate(employees, start=1):
            codes = [get_team_code(t) for t in e.get("teams", []) if t]
            ids = [get_team_id(c) for c in codes if c]
            if not ids:
                ids = [get_team_id("A")]
            for t in ids:
                teams.setdefault(t, set()).add(i)
        return teams
    

    def choose_Employee2(self, Worked_Total_Days, Worked_Sequential_Days,
                        Worked_Previous_Day, emp_allowed_teams, f, d):
        """
        Heuristic scoring function for employee selection.
        Higher score = higher priority for assignment next day.
        """

        # -----------------------------
        # PARAMETERS (tunable weights)
        # -----------------------------
        W_TOTAL = 0.502   # Quem trabalhou menos tem prioridade
        W_WEEK  = 0.272   # Equilibrar dentro da semana
        W_TEAMS = 0       # Flexibilidade de equipas

        # -----------------------------
        # 1. TOTAL DAYS COMPONENT
        # -----------------------------
        total_days = Worked_Total_Days.get(f, 0)
        total_component = max(0.0, 1.0 - total_days / 223)

        # -----------------------------
        # 2. WEEKLY DAYS COMPONENT
        # -----------------------------
        week_days = Worked_Sequential_Days.get(f, 0)
        week_component = max(0.0, 1.0 - week_days / 5)

        # -----------------------------
        # 3. PREVIOUS DAY BLOCK PENALTY
        # -----------------------------
        prev_block = Worked_Previous_Day.get(f)
        critical_blocks = set(range(max(1, self.shifts - 1), self.shifts + 1))

        if prev_block in critical_blocks:
            block_component = -0.0
        else:
            block_component = 0.0

        # -----------------------------
        # 4. TEAM FLEXIBILITY BONUS
        # -----------------------------
        num_teams = len(emp_allowed_teams)
        max_teams = max(len(v) for v in self.emp_allowed_teams.values())

        if max_teams > 1:
            team_component = max(0.0, 1.0 - (num_teams) / (max_teams))
        else:
            team_component = 0.0

        # -----------------------------
        # FINAL SCORE
        # -----------------------------
        score = (
            W_TOTAL * total_component +
            W_WEEK  * week_component +
            W_TEAMS * team_component
        )

        return score
    
    def choose_Employee(self, Worked_Total_Days, Worked_Sequential_Days,
                        Worked_Previous_Day, emp_allowed_teams, f, d):
        import math

        W_PACE    = 0.69
        W_SEQ     = 0.25
        W_SUN_HOL = 0.00
        W_TEAMS   = 0.005
        W_TRANS   = 0.05

        # ── 1. PACE COMPONENT ──────────────────────────────────────────────────
        # Quantos dias de trabalho esperados até ao dia d
        total_days   = Worked_Total_Days.get(f, 0)
        # day_index é o número do dia atual (1-based), usado para calcular o ritmo esperado
        # day_index    = self.dates.index(d) + 1 if hasattr(d, 'date') else d
        # total_open_days = self.num_days - len(self.sundays_holidays)  # dias úteis no ano
# 
        # # Ritmo esperado: proporção do ano passada × dias máximos
        # expected_by_now = (day_index / self.num_days) * 223

        # Diferença: negativo = atrasado (deve ter prioridade ALTA)
        #            positivo = adiantado (deve ter prioridade BAIXA)
        pace_delta = total_days / 223

        # Normaliza para [0, 1]: atrasado → 1.0, adiantado → 0.0
        pace_component = max(0.0, min(1.0, 0.5 - pace_delta / 30.0))

        # ── 2. STREAK PRESSURE ─────────────────────────────────────────────────
        streak = Worked_Sequential_Days.get(f, 0)
        seq_component = max(0.0, 1.0 - (streak / 5) ** 2)

        # ── 3. SUNDAY/HOLIDAY EQUITY ───────────────────────────────────────────
        sun_hol = self.sundays_holidays_worked.get(f, 0)
        sun_hol_component = max(0.0, 1.0 - sun_hol / 22)

        # ── 4. TEAM FLEXIBILITY (fail-first) ───────────────────────────────────
        num_teams = len(emp_allowed_teams)
        max_teams = max(len(v) for v in self.emp_allowed_teams.values())
        # Quanto mais equipas um funcionário puder trabalhar, maior a penalização (prioridade menor)
        team_component = max(0.0, 0.6 - (num_teams) / (max_teams)) if max_teams > 1 else 0.0

        # ── 5. TRANSITION FEASIBILITY ──────────────────────────────────────────
        # Se o funcionário trabalhou um turno crítico ontem (2 ou 3), beneficia dando rank mais alto
        prev = Worked_Previous_Day.get(f) if isinstance(Worked_Previous_Day, dict) else Worked_Previous_Day
        
        if prev == 3:
            value = 0.75
        elif prev == 2:
            value = 0.5
        else:
            value = 0.0

        trans_component = value

        score = (
            W_PACE    * pace_component    +
            W_SEQ     * seq_component     +
            W_SUN_HOL * sun_hol_component +
            W_TEAMS   * team_component    +
            W_TRANS   * trans_component
        )
        return score
    

    def _validate_block_transition_beta(self, previous_shift, next_shift):
        if previous_shift is None or next_shift is None:
            return True
        return not (
            (previous_shift == 3 and next_shift == 1) or
            (previous_shift == 3 and next_shift == 2) or
            (previous_shift == 2 and next_shift == 1)
        )

    _validate_block_transition = _validate_block_transition_beta


    def order_of_ranks(self, Pontuation):
        """
        Recebe um dicionário {emp_id: pontuacao} e retorna uma lista de emp_id
        ordenada por pontuação decrescente.
        """
        ranked = list(Pontuation.items())
        random.shuffle(ranked)
        ranked.sort(key=lambda x: x[1], reverse=True)

        return [emp_id for emp_id, _ in ranked]

    def _print_daily_assignment_map(self, day, daily_assignments):
        """
        Print a cumulative day-by-day grid up to the current day.
        """
        day_index = self.dates.index(day) + 1
        shift_label = {1: 'M', 2: 'T', 3: 'N'}

        assignment_by_employee = defaultdict(dict)
        for emp_id, assignments in self.assignment.items():
            for assignment_day, shift, team_code in assignments:
                if assignment_day <= day_index:
                    team_code_label = TEAM_ID_TO_CODE.get(team_code, str(team_code))
                    assignment_by_employee[emp_id][assignment_day] = f"{shift_label.get(shift, shift)}{team_code_label}"

        header_cells = ["Emp"] + [f"D{idx}" for idx in range(1, day_index + 1)]
        column_width = 6

        print(f"\n{'=' * 80}")
        print(f"[Heuristica] Cumulative map up to Day {day_index} ({day.date()})")
        print(f"[Heuristica] Today's assignments: {len(daily_assignments)}")

        header_line = "".join(cell.center(column_width) for cell in header_cells)
        print(header_line)

        for emp_id in range(1, len(self.employee_rows) + 1):
            row_cells = [f"Emp{emp_id}"]
            emp_map = assignment_by_employee.get(emp_id, {})
            for current_day in range(1, day_index + 1):
                row_cells.append(emp_map.get(current_day, "x"))

            print("".join(str(cell).center(column_width) for cell in row_cells))

        print(f"{'=' * 80}")
    
    def evaluate_Day_Toshifts_mins(self, day, mins):
        """
        Build a dict: team_code → list of shifts needed to meet minimum/ideal
        requirements for that team on the given day.
         - For each team, the list will contain:
           - 'mandatory' shifts (up to the minimum requirement)
           - 'optional' shifts (between minimum and ideal)
         - This allows the heuristic to prioritize filling mandatory shifts
           first, then optional ones.
            - Example output:
            {
                'A': {'mandatory': [1, 1, 2], 'optional': [3]},
                'B': {'mandatory': [2], 'optional': []},
                'C': {'mandatory': [], 'optional': [1, 2]}
            }
        """
        result = {}
        for team_code in self.teams.keys():
            mandatory = []
            optional  = []
            for shift in range(1, self.shifts + 1):
                key = (shift, team_code)
                min_count   = mins.get(key, 0)
                mandatory.extend([shift] * min_count)

            random.shuffle(optional)  # Embaralha os opcionais para dar variedade na atribuição
            result[team_code] = {"mandatory": mandatory, "optional": optional}

        # print(f"[Heuristica] Shifts needed for {day}: {result}")
        return result
    
    def evaluate_Day_Toshifts_ideais(self, day, ideals):
        """
        Build a dict: team_code → list of shifts needed to meet minimum/ideal
        requirements for that team on the given day.
         - For each team, the list will contain:
           - 'mandatory' shifts (up to the minimum requirement)
           - 'optional' shifts (between minimum and ideal)
         - This allows the heuristic to prioritize filling mandatory shifts
           first, then optional ones.
            - Example output:
            {
                'A': {'mandatory': [1, 1, 2], 'optional': [3]},
                'B': {'mandatory': [2], 'optional': []},
                'C': {'mandatory': [], 'optional': [1, 2]}
            }
        """
        result = {}
        for team_code in self.teams.keys():
            mandatory = []
            optional  = []
            for shift in range(1, self.shifts + 1):
                key = (shift, team_code)
                ideal_count   = ideals.get(key, 0)
                if ideal_count > 0:
                    optional.append(shift)

            random.shuffle(optional)  # Embaralha os opcionais para dar variedade na atribuição
            result[team_code] = {"mandatory": mandatory, "optional": optional}

        # print(f"[Heuristica] Shifts needed for {day}: {result}")
        return result


    def build_model(self, debug_daily_trace=False, debug_day_delay_seconds=10.0):
        """Build the Heuristic model with shift constraints."""

        funcionarios = self.employees
        dias = self.dates
        turnos = range(1, self.shifts + 1)

        print(f"turnos: {turnos}")
        print(f"\n{'='*80}")
        print(f"[Heuristica] BUILDING HEURISTIC SCHEDULE")
        print(f"{'='*80}")

        # Heuristica - Tracking variables (one entry per employee)
        Worked_Sequential_Days = {}  # {Employee: Current consecutive-day streak}
        Worked_Previous_Day    = {}  # {Employee: Shift worked yesterday}
        Pontuation             = {f: 0 for f in funcionarios}  # {Employee: Score}

        for f in funcionarios:
            self.Total_Days[f]      = 0
            Worked_Sequential_Days[f] = 0
            Worked_Previous_Day[f]    = None
            Pontuation[f]             = 0
            self.sundays_holidays_worked[f]   = 0

        for d in dias:
            daily_assignments = []

            # Minimo do dia
            mins = {}
            for s in turnos:
                for team_code in self.teams.keys():
                    key = (d, s, team_code)
                    if key in self.minimos:
                        mins[(s, team_code)] = self.minimos[key]
            
            # Ideal do dia
            ideals = {}
            for s in turnos:
                for team_code in self.teams.keys():
                    key = (d, s, team_code)
                    if key in self.ideais:
                        ideals[(s, team_code)] = self.ideais[key]

            Shifts_Table = self.evaluate_Day_Toshifts_mins(d, mins)

            # Ordem de funcionarios pelo score (maior para menor)
            create_global_order = self.order_of_ranks(Pontuation)

            # ================================================================
            # FASE 1 — preencher os MÍNIMOS
            # ================================================================
            for f in create_global_order:

                if d in self.vacations_dates[f]:
                    Worked_Previous_Day[f]    = None
                    Worked_Sequential_Days[f] = 0
                    continue

                if d in self.sundays_holidays and self.sundays_holidays_worked[f] >= 22:
                    Worked_Previous_Day[f]    = None
                    Worked_Sequential_Days[f] = 0
                    continue

                if len(Shifts_Table) == 0:
                    Worked_Previous_Day[f]    = None
                    Worked_Sequential_Days[f] = 0
                    continue

                if Worked_Sequential_Days[f] >= 5:
                    Worked_Previous_Day[f]    = None
                    Worked_Sequential_Days[f] = 0
                    continue

                if self.Total_Days[f] >= 223:
                    Worked_Previous_Day[f]    = None
                    Worked_Sequential_Days[f] = 0
                    continue
        
                Emp_Teams = self.emp_allowed_teams[f]
                teams_most_needed = sorted(
                    ((team, len(shifts_needed["mandatory"]))
                     for team, shifts_needed in Shifts_Table.items()
                     if team in Emp_Teams and shifts_needed["mandatory"]),
                    key=lambda x: x[1],
                    reverse=True
                )

                assigned = False
                for team_code, shifts_needed_count in teams_most_needed:
                    if assigned:
                        break
                    
                    prev_shift = Worked_Previous_Day[f]
                    mandatory_shifts = Shifts_Table[team_code]["mandatory"]

                    for slot_index, candidate_shift in enumerate(mandatory_shifts):
                        if prev_shift is not None:
                            if not self._validate_block_transition(prev_shift, candidate_shift):
                                continue  # try next shift in this same team
                            
                        # Valid — assign this slot
                        assigned_shift = mandatory_shifts.pop(slot_index)

                        self.assignment[f].append((
                            self.dates.index(d) + 1,
                            assigned_shift,
                            team_code
                        ))
                        daily_assignments.append((f, assigned_shift, team_code))

                        self.Total_Days[f]        += 1
                        Worked_Sequential_Days[f] += 1
                        Worked_Previous_Day[f]     = assigned_shift
                        assigned = True

                        if d in self.sundays_holidays:
                            self.sundays_holidays_worked[f] += 1

                        break  # exits the inner shift loop
                    
                if not assigned:
                    Worked_Previous_Day[f]    = None
                    Worked_Sequential_Days[f] = 0


                Pontuation[f] = self.choose_Employee(
                    self.Total_Days,
                    Worked_Sequential_Days,
                    Worked_Previous_Day,
                    self.emp_allowed_teams[f],
                    f,
                    d,
                )

            # ================================================================
            
            if debug_daily_trace:
               print_daily_assignment_map(
                   scheduler          = self,
                   day                = d,
                   daily_assignments  = daily_assignments,
                   tracking           = {
                       "Worked_Total_Days":      self.Total_Days,
                       "Worked_Sequential_Days": Worked_Sequential_Days,
                       "Worked_Previous_Day":    Worked_Previous_Day,
                   },
                   mins  = mins,
                   wide  = False,
                   window = 30,
               )


        print(f"\n[DEBUG] Fim do dia {self.dates.index(d)+1} ({d.date()})")
        for f in funcionarios:
            print(f"  Emp {f}: Total={self.Total_Days[f]} Seq={Worked_Sequential_Days[f]} "
                  f"SunHol={self.sundays_holidays_worked[f]} Prev={Worked_Previous_Day[f]}")

        return True

    # =========================================================

    def log_ideals_day(self, d, day_date, ideals_table, days_assignments,
                   employees_worked_today, actual_streaks,
                   daily_new_assignments):
        """
        Log compacto das atribuições ideais para o dia d.
        Mostra: estado de cada slot ideal disponível, e o que foi atribuído.
        """
        SEP = "─" * 90
        shift_label = {1: "M", 2: "T", 3: "N"}

        print(f"\n{'═'*90}")
        print(f" [IDEAIS] Dia {d:>3}  ({day_date.date()})"
              f"  {'DOMINGO/FERIADO' if day_date in self.sundays_holidays else ''}")
        print(SEP)

        # ── Slots ideais disponíveis no início do dia ──────────────────────────
        slot_lines = []
        for team_code, buckets in ideals_table.items():
            for shift in buckets.get("optional", []):
                slot_lines.append(f"{shift_label[shift]}{team_code}")
        if slot_lines:
            print(f"  Slots ideais disponíveis : {', '.join(slot_lines)}")
        else:
            print(f"  Slots ideais disponíveis : (nenhum)")

        # ── Atribuições novas neste dia ────────────────────────────────────────
        print(SEP)
        if daily_new_assignments:
            print(f"  {'Emp':<6} {'Turno':<8} {'Equipa':<8} {'Dias Total':<12} "
                  f"{'Seq':<6} {'S/F':<5}")
            print(f"  {'---':<6} {'-----':<8} {'------':<8} {'----------':<12} "
                  f"{'---':<6} {'---':<5}")
            for (emp_id, shift, team_code, total, seq, sf) in daily_new_assignments:
                print(f"  {emp_id:<6} {shift_label[shift]+str(team_code):<8} {str(team_code):<8} "
                      f"{total:<12} {seq:<6} {sf:<5}")
        else:
            print("  (nenhuma atribuição ideal feita hoje)")

        # ── Funcionários que já trabalhavam hoje (mínimos) ─────────────────────
        worked_ids = sorted(employees_worked_today)
        print(SEP)
        print(f"  Já trabalhavam (mínimos) : {worked_ids if worked_ids else '(nenhum)'}")

        # ── Streaks actuais ────────────────────────────────────────────────────
        streak_warn = {f: s for f, s in actual_streaks.items() if s >= 4}
        if streak_warn:
            print(f"  Streaks ≥ 4             : "
                  + ", ".join(f"Emp{f}={s}" for f, s in sorted(streak_warn.items())))

        print(f"{'═'*90}")

    def recreate_days(self, assignment):

        """
        This creates a dictionary of assignments based on days instead of employees,
        with the format:
        {day: [(emp, shift, team_code), ...], ...}
        """
        days = defaultdict(list)
        
        for emp_id, entries in assignment.items():
            for day, shift, team_code in entries:
                key = (emp_id, shift, team_code)
                days[day].append(key)
        # keep the days ordered from 1 to 365 (or self.num_days)
        sorted_days = {
            day: sorted(days.get(day, []), key=lambda x: x[0])
            for day in range(1, self.num_days + 1)
        }
        # print(f"Recreated days from assignment: {sorted_days}")
        return sorted_days
        
    def get_next_assigned_shift(self, emp_id, day):
        """
        Retorna o turno já atribuído ao funcionário no dia seguinte (day+1),
        ou None se não tiver nada atribuído.
        Usa self.assignment como fonte da verdade.
        """
        for day_1b, shift, team_code in self.assignment.get(emp_id, []):
            if day_1b == day + 1:
                return shift
        return None
    
    def consecutivechecker(self, emp_id, day, assignment):
        """
        Checks if assigning employee emp_id on 'day' would violate the
        5 consecutive days rule.
        Looks backwards from (day - 1) to count how many consecutive days
        the employee has already worked. If that streak is already >= 5,
        assigning today would make it 6+ consecutive — return True (violation).
        Also looks forward from (day + 1) to check if the employee is already
        assigned on future days that would be consecutive with today, which
        could create a hidden violation window.
        Returns:
            Number of streak if assigned today (including today), or 0 if no violation. This
        """
        # Count consecutive days worked BEFORE 'day' (going backwards)
        streak_before = 0
        for past_day in range(day - 1, max(0, day - 6), -1):
            worked = any(emp == emp_id for emp, _, _ in assignment.get(past_day, []))
            if worked:
                streak_before += 1
            else:
                break  # streak broken
            
        # Count consecutive days worked AFTER 'day' (going forwards)
        # This catches cases where today fills a gap in an already-long forward run
        streak_after = 0
        for future_day in range(day + 1, day + 6):
            worked = any(emp == emp_id for emp, _, _ in assignment.get(future_day, []))
            if worked:
                streak_after += 1
            else:
                break
            
        # Total streak if we assign today = before + 1 (today) + after
        total_streak = streak_before + 1 + streak_after
        #print(f"Checking consecutive for Emp {emp_id} on Day {day}: "
        #      f"Streak Before={streak_before}, Streak After={streak_after}, Total if assigned today={total_streak}")
        return total_streak  

    def build_ideals(self, debug_daily_trace=False):
        """
        Phase 2: fill ideal slots.
        """

        print(f"\n{'='*80}")
        print(f"[Heuristica] BUILDING IDEALS (Fase 2)")
        print(f"{'='*80}")

        funcionarios = self.employees
        turnos       = range(1, self.shifts + 1)
        days = range(1, self.num_days + 1)
        random_days = random.sample(days, len(days))  # Embaralha a ordem dos dias para diversidade

        ideals_added_finally = 0
        Pontuation = {f: 0 for f in funcionarios}
        
        days_assignments = self.recreate_days(self.assignment)

        for d in random_days:

            # No início do loop `for d in days:`, adiciona este container:
            daily_new_assignments = []

            Actual_Streaks = {}

            for f in funcionarios:

                today_assign = self.consecutivechecker(f, d, days_assignments)
                Actual_Streaks[f] = today_assign
            
            #print(f"Day {d}: Assignments: {days_assignments.get(d, [])}")
            Employees_Worked_today = {emp for emp, _, _ in days_assignments.get(d, [])}
            Employees_Worked_Yesterday = {emp for emp,_,_ in days_assignments.get(d-1,[])}

            day_date = self.dates[d - 1]

            Previous_days_emp = {}

            # Build a map of employees who worked yesterday and their shifts, to enforce transition constraints for today's ideals.
            for j in Employees_Worked_Yesterday:
                    for emp, shift, team_code in days_assignments.get(d-1, []):
                        if emp == j:
                            Previous_days_emp[j] = shift

            # Ideal do dia
            ideals = {}
            for s in turnos:
                for team_code in self.teams.keys():
                    key = (day_date, s, team_code)
                    if key in self.ideais:
                        ideals[(s, team_code)] = self.ideais[key]

            ideals_Table = self.evaluate_Day_Toshifts_ideais(day_date, ideals)

            Order = self.order_of_ranks(Pontuation)

            for f in Order:

                # Ja trabalhou nesse dia
                if f in Employees_Worked_today:
                    continue

                if self.dates[d-1] in self.vacations_dates[f]:
                    Actual_Streaks[f] = 0
                    continue

                if self.Total_Days.get(f, 0) >= 223:
                    Actual_Streaks[f] = 0
                    continue

                if Actual_Streaks[f] > 5:
                    Actual_Streaks[f] = 0
                    continue

                if day_date in self.sundays_holidays and self.sundays_holidays_worked.get(f, 0) >= 22:
                    Actual_Streaks[f] = 0
                    continue
        
                Emp_Teams = self.emp_allowed_teams[f]

                most_needed = sorted(
                    ((team, len(shifts_needed["optional"]))
                     for team, shifts_needed in ideals_Table.items()
                     if team in Emp_Teams and shifts_needed["optional"]),
                    key=lambda x: x[1],
                    reverse=True,
                )

                assigned = False

                for team_code, shifts_needed_count in most_needed:

                    if assigned:
                        break

                    if team_code not in Emp_Teams:
                        continue

                    optional_shifts = ideals_Table[team_code]["optional"]
                    if not optional_shifts:
                        continue

                    for slot_index, candidate_shift in enumerate(optional_shifts):
                        # 1. Verifica transição do dia anterior → hoje
                        prev_shift = Previous_days_emp.get(f)
                        if prev_shift is not None:
                            if not self._validate_block_transition(prev_shift, candidate_shift):
                                # print(f"    Violação passado: Emp {f} shift {prev_shift} → {candidate_shift}")
                                continue

                        # 2. Verifica transição de hoje → dia seguinte já atribuído
                        next_shift = self.get_next_assigned_shift(f, d)
                        if next_shift is not None:
                            if not self._validate_block_transition(candidate_shift, next_shift):
                                # print(f"    Violação futuro: Emp {f} shift {candidate_shift} → {next_shift} (dia {d+1})")
                                continue

                        # Válido nos dois sentidos — atribui
                        assigned_shift = optional_shifts.pop(slot_index)
                        self.assignment[f].append((d, assigned_shift, team_code))
                        days_assignments[d].append((f, assigned_shift, team_code))
                        self.Total_Days[f] += 1
                        if day_date in self.sundays_holidays:
                            self.sundays_holidays_worked[f] += 1
                        assigned = True
                        break

                    if assigned:
                        break
                    
                if assigned:
                    seq_now = Actual_Streaks.get(f, 0)
                    sf_now  = self.sundays_holidays_worked.get(f, 0)
                    ideals_added_finally += 1
                    daily_new_assignments.append((
                        f, assigned_shift, team_code,
                        self.Total_Days.get(f, 0),
                        seq_now,
                        sf_now,
                    ))

                if not assigned:
                    Actual_Streaks[f] = 0

                Pontuation[f] = self.choose_Employee(
                    self.Total_Days,
                    Actual_Streaks,
                    Previous_days_emp,
                    self.emp_allowed_teams[f],
                    f,
                    d,
                )
            
            # self.log_ideals_day(
            #     d               = d,
            #     day_date        = day_date,
            #     ideals_table    = ideals_Table,   # estado DEPOIS das atribuições
            #     days_assignments= days_assignments,
            #     employees_worked_today = Employees_Worked_today,
            #     actual_streaks  = Actual_Streaks,
            #     daily_new_assignments  = daily_new_assignments,
            # )


        print(f"\n[build_ideals] Complete.")
        print(f"[build_ideals] Total assignments after ideals: "
              f"{sum(len(v) for v in self.assignment.values())}")

        return ideals_added_finally
    

    def complete_solution(self, **kwargs):
        """
        Phase 3: after building the model and filling ideals, we could add a final
        pass to try to fill any remaining gaps with valid assignments, even if they
        are not ideal. This would be a more "greedy" pass that tries to maximize total
        coverage while respecting all constraints.
        """
        print(f"\n{'='*80}")
        print(f"[Heuristica] COMPLETING SOLUTION (Fase 3)")
        print(f"{'='*80}")

        days = range(1, self.num_days + 1)
        random_days = random.sample(days, len(days))  # Embaralha a ordem dos dias para diversidade

        Days_Left_Per_Emp = {}

        for emp, assg in self.assignment.items():
            Days_Left_Per_Emp[emp] = 223 - len(assg)

        days_assignments = self.recreate_days(self.assignment)

        for emp, days_left in Days_Left_Per_Emp.items():

            if days_left <= 0:
                continue  # This employee has already reached max days
 
            counter = 0
            
            for d in random_days:

                if counter >= days_left:
                    continue  # This employee has already reached max days

                Actual_Streaks = {}

                day_date = self.dates[d - 1]

                if day_date in self.vacations_dates[emp]:
                    continue  # Employee is on vacation
            
                if day_date in self.sundays_holidays and self.sundays_holidays_worked.get(emp, 0) >= 22:
                    continue  # Employee has already worked too many Sundays/Holidays

                Employees_Worked_today = {emp for emp, _, _ in days_assignments.get(d, [])}
            
                if emp in Employees_Worked_today:
                    continue  # Already has an assignment today, skip

                today_assign = self.consecutivechecker(emp, d, days_assignments)
                Actual_Streaks[emp] = today_assign

                if Actual_Streaks[emp] > 5:
                    continue
                
                Emp_Teams = self.emp_allowed_teams[emp]

                Allowed_Shifts_To_Attribute_Today = []

                for empl, shift, team_code in days_assignments.get(d-1, []):
                    if empl == emp:
                        prev_shift = shift
                        for candidate_shift in range(1, self.shifts + 1):
                            if self._validate_block_transition(prev_shift, candidate_shift):
                                Allowed_Shifts_To_Attribute_Today.append(candidate_shift)

                for empl, shift, team_code in days_assignments.get(d+1, []):
                    if empl == emp:
                        next_shift = shift
                        for candidate_shift in range(1, self.shifts + 1):
                            if self._validate_block_transition(candidate_shift, next_shift):
                                Allowed_Shifts_To_Attribute_Today.append(candidate_shift)

                # if the shifts are duplicated only them can be assigned
                Allowed_Shifts_To_Attribute_Today = [shift for shift in set(Allowed_Shifts_To_Attribute_Today) if Allowed_Shifts_To_Attribute_Today.count(shift) > 1]

                if not Allowed_Shifts_To_Attribute_Today:
                    continue  # No valid shifts to assign today based on transitions

                self.assignment[emp].append((d, Allowed_Shifts_To_Attribute_Today[0], Emp_Teams[0]))  # Assign the first allowed shift and team
                days_assignments[d].append((emp, Allowed_Shifts_To_Attribute_Today[0], Emp_Teams[0]))
                self.Total_Days[emp] += 1
                if day_date in self.sundays_holidays:
                    self.sundays_holidays_worked[emp] += 1
                counter += 1
        
        print(f"\n[complete_solution] Complete.")

        return True


    def _capture_ideal_state(self):
        """Capture the mutable state that build_ideals changes."""
        return {
            "assignment": copy.deepcopy(self.assignment),
            "Total_Days": copy.deepcopy(self.Total_Days),
            "sundays_holidays_worked": copy.deepcopy(self.sundays_holidays_worked),
            "ideal_assignments": copy.deepcopy(getattr(self, "ideal_assignments", defaultdict(list))),
        }

    def _restore_ideal_state(self, state):
        """Restore a previously captured mutable state."""
        self.assignment = copy.deepcopy(state["assignment"])
        self.Total_Days = copy.deepcopy(state["Total_Days"])
        self.sundays_holidays_worked = copy.deepcopy(state["sundays_holidays_worked"])
        self.ideal_assignments = copy.deepcopy(state["ideal_assignments"])

    def _reset_for_new_outer(self):
        """Limpa o estado para um novo outer (novo build_model)."""
        self.assignment               = defaultdict(list)
        self.Total_Days               = {f: 0 for f in self.employees}
        self.sundays_holidays_worked  = {f: 0 for f in self.employees}
        self.ideal_assignments        = defaultdict(list)

    def solve(self, n_outer=1, n_inner=1,
              debug_daily_trace=False, debug_day_delay_seconds=0.0):

        print(f"\n{'='*80}")
        print(f"[Heuristica] EXECUTING — {n_outer} outer × {n_inner} inner")
        print(f"{'='*80}")

        start_wall = time.time()

        best_outer_score     = -1
        best_outer_assignment = None

        for outer in range(1, n_outer + 1):
            print(f"\n[Outer {outer}/{n_outer}] build_model()...")
            self.build_model(debug_daily_trace=debug_daily_trace,
                             debug_day_delay_seconds=debug_day_delay_seconds)

            # Snapshot do estado APÓS build_model, ANTES de qualquer ideal
            post_model_snapshot = self._capture_ideal_state()

            best_inner_score      = -1
            best_inner_assignment = None

            for inner in range(1, n_inner + 1):
                # Restaura sempre o estado pós-model para cada run
                self._restore_ideal_state(post_model_snapshot)

                ideals_added = self.build_ideals()

                if ideals_added > best_inner_score:
                    best_inner_score      = ideals_added
                    best_inner_assignment = self._capture_ideal_state()
                    print(f"  [Inner {inner:>3}] novo melhor: {ideals_added} ideais")

            # Restaura o melhor resultado do inner loop
            self._restore_ideal_state(best_inner_assignment)

            total_assigned = sum(len(v) for v in self.assignment.values())
            print(f"[Outer {outer}/{n_outer}] melhor inner={best_inner_score} "
                  f"total_dias={total_assigned}")

            if best_inner_score > best_outer_score:
                best_outer_score      = best_inner_score
                best_outer_assignment = self._capture_ideal_state()

            # Reinicia para o próximo outer (novo build_model)
            self._reset_for_new_outer()

        # Restaura o melhor resultado global
        self._restore_ideal_state(best_outer_assignment)

        self.complete_solution()

        wall_time = time.time() - start_wall
        print(f"\n[Heuristica] Concluído em {wall_time:.1f}s")
        print(f"[Heuristica] Melhor score global: {best_outer_score} ideais adicionados")
        for emp, assg in self.assignment.items():
            print(f"  Emp {emp}: {len(assg)} dias")

        return True


    def export_csv(self, filename="schedule_weighted.csv"):
        export_schedule_to_csv(self, filename)

    def to_table(self):
        """
        Build a table similar to ILP1/ILP2:
        First column = employee id
        Other columns = Dia 1..N with codes like M_A, T_B, F, 0, etc.
        """
        header = ["funcionario"] + [f"Dia {i}" for i in range(1, self.num_days + 1)]
        rows = [header]

        label = {1: "M_", 2: "T_", 3: "N_"}
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
    


def solve(vacations=None, minimuns=None, employees=None, maxTime=None,
          year=2021, hours=13, work_blocks=None, rules=None,
          debug_daily_trace=False, debug_day_delay_seconds=10.0,
          n_outer=1, n_inner=1, **kwargs):
    """
    Main solve function for hourly scheduling.
    """

    scheduler = Heuristica(
          vacations_rows=vacations,
          minimuns_rows=minimuns,
          employees=employees,
          maxTime=maxTime,
          year=year,
          shifts=hours,
      )
    
    scheduler.solve(
        n_outer=n_outer,
        n_inner=n_inner,
        debug_daily_trace=debug_daily_trace,
        debug_day_delay_seconds=debug_day_delay_seconds,
    )

    table = scheduler.to_table()
    return table
