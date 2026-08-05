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

        print(f"Employee to Teams mapping: {self.teams}")

        self.emp_allowed_teams = self._build_emp_team_map(self.employee_rows)

        print(f"Employee to Allowed Teams mapping: {self.emp_allowed_teams}")

        self.dates, sundays_idx = build_calendar(year)

        print(f"Generated calendar for year {year} with {(self.dates)} days, {sundays_idx} Sundays.")

        self.num_days = len(self.dates)
        # convert sunday indices (1-based day numbers) to actual Timestamp objects
        sundays = {
            self.dates[idx - 1]
            for idx in sundays_idx
            if 1 <= idx <= len(self.dates)
        }

        print(f"Identified {len(sundays)} Sundays: {sorted(sundays)}")

        # PT holidays
        pt_holidays = holidays.country_holidays("PT", years=[year])
        holiday_dates = {
            d
            for d in self.dates
            if d.date() in pt_holidays
        }

        print(f"Identified {len(holiday_dates)} holidays: {sorted(holiday_dates)}")

        # Combined: Sundays + Holidays
        self.sundays_holidays = sorted(sundays | holiday_dates)

        print(f"Total closed days (Sundays + Holidays): {len(self.sundays_holidays)}, Sundays + Holidays: {self.sundays_holidays}")

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

        print(f"Processed vacations_1based for {len(self.vacs)} employees. Sample: {self.vacs}")
        print(f"Processed vacations_dates for {len(self.vacations_dates)} employees. Sample: {self.vacations_dates}")

        mins_raw, ideals_raw = rows_to_req_dicts(minimuns_rows)
        self.minimos = {}
        self.ideais = {}
        for (day, shift, team_id), value in mins_raw.items():
            if 1 <= day <= self.num_days:
                self.minimos[(self.dates[day - 1], shift, team_id)] = int(value)
        for (day, shift, team_id), value in ideals_raw.items():
            if 1 <= day <= self.num_days:
                self.ideais[(self.dates[day - 1], shift, team_id)] = int(value)

        print(f"Processed minimum requirements: {len(self.minimos)} entries. Sample: {(self.minimos)}")
        print(f"Processed ideal requirements: {len(self.ideais)} entries. Sample: {(self.ideais)}")
        
        # Containers filled after solving
        self.assignment = defaultdict(list)

        print(f"assignment initialized as empty defaultdict(list): {self.assignment}")

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
    

    def choose_Employee(self, Worked_Total_Days, Worked_Sequential_Days,  # BUG FIX B: era "Worked_Week_Days", renomeado para "Worked_Sequential_Days"
                        Worked_Previous_Day, emp_allowed_teams, f, d):
        """
        Heuristic scoring function for employee selection.

        Higher score = higher priority for assignment next day.

        BUG FIX B: O parâmetro chamava-se Worked_Week_Days mas o caller
        passava sempre Worked_Sequential_Days. O nome foi corrigido para
        corresponder ao que realmente é passado.
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
        # BUG FIX B: era Worked_Week_Days.get(f, 0) — variável inexistente,
        # causava KeyError silencioso ou usava o parâmetro errado.
        # -----------------------------
        week_days = Worked_Sequential_Days.get(f, 0)  # BUG FIX B

        week_component = max(0.0, 1.0 - week_days / 5)

        # -----------------------------
        # 3. PREVIOUS DAY BLOCK PENALTY
        # -----------------------------
        prev_block = Worked_Previous_Day.get(f)

        # Últimos 6 blocos são os mais tardios
        critical_blocks = set(range(max(1, self.shifts - 1), self.shifts + 1))

        if prev_block in critical_blocks:
            block_component = -0.0  # Penalização total
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
    

    def _validate_block_transition_beta(self, previous_shift, next_shift):
        if previous_shift is None or next_shift is None:
            return True
        return not ((previous_shift == 3 and next_shift == 1) or 
                    (previous_shift == 3 and next_shift == 2) or 
                    (previous_shift == 2 and next_shift == 1))

    _validate_block_transition = _validate_block_transition_beta


    
    def order_of_ranks(self, Pontuation):
        """
        Recebe um dicionário {emp_id: pontuacao} e retorna uma lista de emp_id ordenada por pontuação decrescente.
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
    
    def evaluate_Day_Toshifts(self, day, mins):
        """
        Determina o número de turnos total necessários para cobrir os mínimos do dia, 
        por equipa.
        """
        result = {}
        for team_code in self.teams.keys():
            shift_slots = []
            for shift in range(1, self.shifts + 1):
                key = (shift, team_code)
                shift_minimum = mins.get(key, 0)
                if shift_minimum:
                    shift_slots.extend([shift] * shift_minimum)

            result[team_code] = shift_slots

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

        Worked_Total_Days      = {}
        Worked_Sequential_Days = {}
        Worked_Previous_Day    = {}
        Pontuation             = {}
        SundayHolidayCounter   = {}

        for f in funcionarios:
            Worked_Total_Days[f]      = 0
            Worked_Sequential_Days[f] = 0
            Worked_Previous_Day[f]    = None
            Pontuation[f]             = 0
            SundayHolidayCounter[f]   = 0

        for d in dias:
            daily_assignments = []

            mins = {}
            for s in turnos:
                for team_code in self.teams.keys():
                    key = (d, s, team_code)
                    if key in self.minimos:
                        mins[(s, team_code)] = self.minimos[key]

            Shifts_Table = self.evaluate_Day_Toshifts(d, mins)

            # ── Pre-compute available pool per team for this day ─────────────
            # "Available" = not on vacation, not over consecutive limit, not over
            # annual cap, not over Sunday/holiday cap.  This is the denominator
            # for the urgency ratio: slots_open / available_employees.
            # A team with 1 slot and 1 available employee is more urgent than a
            # team with 3 slots and 15 available employees.
            team_available_count = {}
            for team_code, team_members in self.teams.items():
                count = 0
                for candidate in team_members:
                    if d in self.vacations_dates[candidate]:
                        continue
                    if d in self.sundays_holidays and SundayHolidayCounter[candidate] >= 22:
                        continue
                    if Worked_Sequential_Days[candidate] >= 5:
                        continue
                    if Worked_Total_Days[candidate] >= 223:
                        continue
                    count += 1
                team_available_count[team_code] = count

            create_global_order = self.order_of_ranks(Pontuation)

            for f in create_global_order:

                # ── Genuine rest day: vacation ───────────────────────────────
                if d in self.vacations_dates[f]:
                    Worked_Sequential_Days[f] = 0
                    Worked_Previous_Day[f]    = None
                    continue

                # ── Genuine rest day: Sunday/holiday cap reached ─────────────
                if d in self.sundays_holidays and SundayHolidayCounter[f] >= 22:
                    continue

                if not any(Shifts_Table.values()):
                    continue

                # ── Genuine rest day: consecutive-day limit ──────────────────
                if Worked_Sequential_Days[f] >= 5:
                    Worked_Sequential_Days[f] = 0
                    Worked_Previous_Day[f]    = None
                    continue

                # ── Hard cap on total annual days ────────────────────────────
                if Worked_Total_Days[f] >= 223:
                    continue

                # ── Build urgency-sorted team list ───────────────────────────
                # Urgency ratio = slots_open / available_employees_for_that_team.
                # Higher ratio → fewer people to cover the remaining slots →
                # assign to that team first.
                # available=0 gets ratio=inf so it sorts first (no one else can
                # cover it — this employee might be the only one left).
                Emp_Teams = self.emp_allowed_teams[f]

                def urgency(item):
                    team_code, shifts_needed = item
                    available = team_available_count.get(team_code, 0)
                    slots     = len(shifts_needed)
                    if available == 0:
                        return float('inf')
                    return slots / available

                teams_most_needed = sorted(
                    (
                        (team, shifts_needed)
                        for team, shifts_needed in Shifts_Table.items()
                        if team in Emp_Teams and shifts_needed
                    ),
                    key=urgency,
                    reverse=True,   # highest urgency first
                )

                assigned = False

                for team_code, shifts_needed in teams_most_needed:
                    if assigned:
                        break

                    prev_shift = Worked_Previous_Day[f]

                    for slot_index, candidate_shift in enumerate(shifts_needed):
                        if prev_shift is not None:
                            if not self._validate_block_transition(prev_shift, candidate_shift):
                                continue

                        # Found a valid slot — consume it atomically.
                        Shifts_Table[team_code].pop(slot_index)

                        # ── Decrement available pool for this team ───────────
                        # This employee is now assigned — they are no longer
                        # available to cover remaining slots for this team today.
                        if team_code in team_available_count:
                            team_available_count[team_code] = max(
                                0, team_available_count[team_code] - 1
                            )

                        self.assignment[f].append((
                            self.dates.index(d) + 1,
                            candidate_shift,
                            team_code,
                        ))
                        daily_assignments.append((f, candidate_shift, team_code))

                        Worked_Total_Days[f]      += 1
                        Worked_Sequential_Days[f] += 1
                        Worked_Previous_Day[f]     = candidate_shift
                        assigned = True

                        if d in self.sundays_holidays:
                            SundayHolidayCounter[f] += 1

                        break

                Pontuation[f] = self.choose_Employee(
                    Worked_Total_Days,
                    Worked_Sequential_Days,
                    Worked_Previous_Day,
                    self.emp_allowed_teams[f],
                    f,
                    d,
                )

            if debug_daily_trace:
                print_daily_assignment_map(
                    scheduler         = self,
                    day               = d,
                    daily_assignments = daily_assignments,
                    tracking          = {
                        "Worked_Total_Days":      Worked_Total_Days,
                        "Worked_Sequential_Days": Worked_Sequential_Days,
                        "Worked_Previous_Day":    Worked_Previous_Day,
                    },
                    mins   = mins,
                    wide   = False,
                    window = 30,
                )

        print(f"\n[DEBUG] Fim do dia {self.dates.index(d)+1} ({d.date()})")
        for f in funcionarios:
            print(f"  Emp {f}: Total={Worked_Total_Days[f]} Seq={Worked_Sequential_Days[f]} "
                  f"SunHol={SundayHolidayCounter[f]} Prev={Worked_Previous_Day[f]}")

        return True

    # =========================================================

    def solve(self, debug_daily_trace=False, debug_day_delay_seconds=0.0):
        """Execute the heuristic scheduling algorithm."""
        
        print(f"\n{'='*80}")
        print(f"[Heuristica] EXECUTING HEURISTIC SCHEDULER")
        print(f"{'='*80}")
        print(f"[Heuristica] Building schedule...")
        
        start_wall = time.time()
        start_cpu  = time.process_time()
        
        self.build_model(
            debug_daily_trace=debug_daily_trace,
            debug_day_delay_seconds=debug_day_delay_seconds,
        )
        
        end_wall = time.time()
        end_cpu  = time.process_time()
        
        wall_time = end_wall - start_wall
        cpu_time  = end_cpu  - start_cpu
        
        print(f"\n[Heuristica] Schedule completed")
        print(f"[Heuristica] Wall time: {wall_time:.2f}s ({wall_time/60:.2f} min)")
        print(f"[Heuristica] CPU time:  {cpu_time:.2f}s ({cpu_time/60:.2f} min)")
        print("[Heuristica] Employees with assignments:")
        for emp, assg in self.assignment.items():
            print(f"  Emp {emp}: {len(assg)} days")
        
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
          debug_daily_trace=False, debug_day_delay_seconds=10.0, **kwargs):
    """
    Main solve function for hourly scheduling.
    """
    total_seconds = 10
    import copy
    import time
    best_score      = None
    best_scheduler  = None
    best_assignment = None
    start  = time.time()
    n_iter = 2

    for iteration in range(1, n_iter):  # Arbitrary large number to allow multiple iterations until time runs out
        print(f"[Heuristica-Multi] Starting multi-iteration heuristic search for up to {total_seconds} seconds...")
        
        scheduler = Heuristica(
              vacations_rows=vacations,
              minimuns_rows=minimuns,
              employees=employees,
              maxTime=maxTime,
              year=year,
              shifts=hours,
          )
        
        scheduler.solve(
            debug_daily_trace=debug_daily_trace,
            debug_day_delay_seconds=debug_day_delay_seconds,
        )

        best_scheduler = scheduler
        best_assignment = copy.deepcopy(scheduler.assignment)
        table = best_scheduler.to_table()

        return table
    
    # while (time.time() - start < total_seconds) or (n_iter == 0):
# 
    #     scheduler = Heuristica(
    #         vacations_rows=vacations,
    #         minimuns_rows=minimuns,
    #         employees=employees,
    #         maxTime=maxTime,
    #         year=year,
    #         shifts=hours,
    #     )
    #     scheduler.solve(
    #         debug_daily_trace=debug_daily_trace,
    #         debug_day_delay_seconds=debug_day_delay_seconds,
    #     )
    #     score = count_minimum_shift_failures(scheduler)
# 
    #     if (best_score is None) or (score < best_score):
    #         best_score      = score
    #         best_scheduler  = scheduler
    #         best_assignment = copy.deepcopy(scheduler.assignment)
    #         print(f"[Heuristica-Multi] Nova melhor solução encontrada na iteração {n_iter+1} (falhas={score})")
    #     n_iter += 1
# 
    #     print(f"[Heuristica-Multi] Iteração {n_iter} concluída. Tempo decorrido: {time.time() - start:.2f}s")
    #     print(f"[Heuristica-Multi] Score desta iteração {score} Melhor score até agora: {best_score}")
# 
    # if best_scheduler and best_assignment:
    #     best_scheduler.assignment = best_assignment
    #     best_scheduler.export_csv("heuristic_schedule_best.csv")
    #     print(f"[Heuristica-Multi] Total de iterações: {n_iter}")
    #     print(f"[Heuristica-Multi] Melhor score: {-best_score if best_score is not None else None}")
    #     table = best_scheduler.to_table()
    #     
    #     violations = check_5_consecutive_days(table)
# 
    #     return table
    # else:
    #     print("[Heuristica00] Nenhuma solução encontrada, devolvendo tabela vazia.")
    #     return [["Employee"]]