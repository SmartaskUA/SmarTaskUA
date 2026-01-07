# HourlyILP_strict.py
import csv
from collections import defaultdict
import datetime
from time import time
import threading
import sys

import numpy as np
import pandas as pd

from algorithms.utils import (
    build_calendar,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv_shifts,
    TEAM_CODE_TO_ID,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    create_Blocks,
    drange,
    drange_indexed_h,
    rows_to_req_dicts_Half_Hour
)


class HeuristicOneScheduler:
    
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2021,
                 store_hours=13, work_blocks=None):
        self.year = year
        # Convert maxTime (minutes) to seconds, handle string input
        if maxTime is not None:
            try:
                maxTime_num = float(maxTime)
                self.maxTime_sec = int(maxTime_num * 60)
            except (ValueError, TypeError):
                self.maxTime_sec = 8 * 3600
        else:
            self.maxTime_sec = None

        # Calendar - keep same range
        self.dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
        self.num_days = len(self.dates)

        # Employees
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)

        self.store_hours = int(store_hours)
        self.last_7_days = {f: [] for f in self.employees}

        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks

        self.num_blocks = len(self.work_blocks)
        self.block_hours = [self._get_working_hours(b) for b in self.work_blocks]

        # Employee teams mapping
        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            if not teams:
                codes = ("A",)
            else:
                codes = tuple(get_team_code(team) for team in teams)
            self.emp_team_code[idx] = codes
            for c in codes:
                get_team_id(c)

        # teams -> members
        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        # Vacations
        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, [])
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        self.remaining_min = {
                    (self.dates[d-1], h, TEAM_ID_TO_CODE[t]): v
                    for (d, h, t), v in mins.items() if v > 0
                }
        
        self.worked_days = {f: set() for f in self.employees}
        self.consecutive = {f: 0 for f in self.employees}
        self.last_block = {f: None for f in self.employees}

        # Minimums
        mins, ideals = rows_to_req_dicts_Half_Hour(minimums_rows)
        self.minimos = {}
        for (day, hour, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, hour, team_code)] = int(val)

        # closed days set (if any team has -1 at some hour, we treat day as closed for all)
        self.closed_days = {d for (d, h, t), v in self.minimos.items() if v == -1}

        self.assignment = defaultdict(list)
        self.objective_value = None

        print(f"[HeuristicOneScheduler] Initialized with {self.num_employees} employees, "
              f"{len(self.vacations_dates)} vacation entries, "
              f"{len(self.minimos)} minimum requirements."
              f" Store hours: {self.store_hours}, Work blocks: {self.num_blocks}")
            
    def _generate_work_blocks(self):
        blocks = create_Blocks(0.5, 9, 22)
        print(f"[HeuristicOneScheduler] All possible work blocks (half-hour intervals):")
        for i, b in enumerate(blocks):
            print(f"  Block {i}: {b[0]:.1f} to {b[1]:.1f} (break at {b[2]:.1f})")
        return blocks
    
    def _get_working_hours(self, block):
        start, break_start, end = block
        hours = set(drange(start, break_start, 0.5))  # First period
        hours.update(drange(break_start + 1, end, 0.5))  # Second period (skip break hour)
        return hours

    def _validate_block_transition(self, block_today, block_tomorrow):
        end_today = block_today[2]
        start_tomorrow = block_tomorrow[0]
        rest_hours = (24 - end_today) + start_tomorrow
        return rest_hours >= 12

    def _block_coverage(self, d, block_idx, team_code):
        covered = 0
        for h in self.block_hours[block_idx]:
            key = (d, h, team_code)
            if key in self.remaining_min and self.remaining_min[key] > 0:
                covered += 1
        return covered
    
    def _hour_to_label(self, h):
        if h % 1 == 0:
            return f"{int(h):02d}.0-{int(h):02d}.5"
        else:
            return f"{int(h):02d}.5-{int(h)+1:02d}.0"
    
    def _day_has_minimums(self, d, team_codes):
        for (dd, h, t), v in self.remaining_min.items():
            if dd == d and t in team_codes and v > 0:
                return True
        print(f"[DEBUG] Day {d} has NO minimums for teams {team_codes}")
        return False
    
    def _worked_6_of_last_6(self, f):
        days = [x for x in self.last_7_days[f] if x is not None]
        return len(days) >= 6



    def _block_score(self, f, d, b, team_code):
        score = 0

        # 1️⃣ HARD — Cobertura de mínimos
        gain = 0
        for h in self.block_hours[b]:
            hour_label = self._hour_to_label(h)
            key = (d, hour_label, team_code)
            if self.remaining_min.get(key, 0) > 0:
                gain += 1

        if gain > 0:
            score += 1000 * gain   # HARD: domina tudo

        # MEDIUM — folga semanal (janela 7 dias)
        if self._worked_6_of_last_6(f):
            score -= 600   # forte, mas NÃO hard

        # 2️⃣ SOFT — cumprir 223 dias
        days_worked = len(self.worked_days[f])
        if days_worked < 223:
            score += (223 - days_worked) * 2  # força positiva

        if self.last_block[f] is not None:
            if not self._validate_block_transition(
                self.work_blocks[self.last_block[f]],
                self.work_blocks[b]
            ):
                score -= 1000  # continua quase proibido

        if self.last_block[f] == b:
            score -= 30

        return score


    def solve(self):

        print("[HeuristicOneScheduler] Starting corrected greedy solve")

        # Copiar mínimos
        self.remaining_min = {
            (d, h, t): v
            for (d, h, t), v in self.minimos.items()
            if v > 0
        }

        start_time = time()

        for d in self.dates:

            if d in self.closed_days:
                continue

            # Reset consecutivos se OFF no dia anterior
            for f in self.employees:
                if d not in self.worked_days[f]:
                    self.consecutive[f] = 0

            # Ordenar empregados: quem tem menos dias trabalhados primeiro
            employees_sorted = sorted(
                self.employees,
                key=lambda f: len(self.worked_days[f])
            )

            for f in employees_sorted:

                if d in self.vacations_dates[f]:
                    continue
                if d in self.worked_days[f]:
                    continue
                if len(self.worked_days[f]) >= 223:
                    continue

                best_score = -float("inf")
                best_block = None
                best_team = None

                # Equipas permitidas ao empregado
                for team_code in self.emp_team_code[f]:

                    for b in range(self.num_blocks):

                        # Validação transição
                        if self.last_block[f] is not None:
                            if not self._validate_block_transition(
                                self.work_blocks[self.last_block[f]],
                                self.work_blocks[b]
                            ):
                                continue

                        score = self._block_score(f, d, b, team_code)

                        if score > best_score:
                            best_score = score
                            best_block = b
                            best_team = team_code

                # Nenhum bloco aceitável → OFF
                day_has_min = self._day_has_minimums(d, self.emp_team_code[f])

                # HARD: se há mínimos, nunca OFF
                if best_block is None and day_has_min:
                    continue
                
                # SOFT: só OFF se não há mínimos e já está perto dos 223
                if best_block is None or (best_score <= 0 and not day_has_min):
                    if self._worked_6_of_last_6(f):
                        self.consecutive[f] = 0
            
                    # 🔴 ATUALIZAR HISTÓRICO SEMANAL (OFF)
                        self.last_7_days[f].append(None)
                        if len(self.last_7_days[f]) > 7:
                            self.last_7_days[f].pop(0)
                        continue
                

                # Aplicar atribuição
                self.assignment[f + 1].append(
                    (self.dates.index(d) + 1, best_block, get_team_id(best_team))
                )

                self.worked_days[f].add(d)
                self.consecutive[f] += 1
                self.last_block[f] = best_block

                # 🟢 ATUALIZAR HISTÓRICO SEMANAL (TRABALHO)
                self.last_7_days[f].append(d)
                if len(self.last_7_days[f]) > 7:
                    self.last_7_days[f].pop(0)


                # Atualizar mínimos
                for h in self.block_hours[best_block]:
                    hour_label = self._hour_to_label(h)
                    key = (d, hour_label, best_team)
                    if key in self.remaining_min:
                        self.remaining_min[key] = max(
                            0, self.remaining_min[key] - 1
                        )


                if self.maxTime_sec and time() - start_time > self.maxTime_sec:
                    print("[HeuristicOneScheduler] TIME LIMIT")
                    return "TIME_LIMIT"

        return "OK"


        

    def _extract_assignments(self):
        return

    def export_csv(self, filename="hourly_strict_schedule.csv"):
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(self.vacs_1based().get(emp_id, [])) if hasattr(self, "vacs_1based") else set()
                day_to_block = {d: (b, t) for (d, b, t) in self.assignment.get(emp_id, [])}
                row = [f'Emp{emp_id}']
                for d in range(1, self.num_days + 1):
                    if d in vac_days:
                        row.append('VACATION')
                    elif d in day_to_block:
                        block_idx, team_id = day_to_block[d]
                        block = self.work_blocks[block_idx]
                        team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                        row.append(f"{block[0]:.1f}-{block[1]:.1f}-{block[2]:.1f}_{team_code}")
                    else:
                        row.append('OFF')
                writer.writerow(row)

    def vacs_1based(self):
        return {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }
    
    def to_table(self):
        # returns rows as list of lists (same layout as ILP to_table)
        rows = []
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows.append(header)
        vacs_1b = self.vacs_1based()
        for emp_id in sorted([i + 1 for i in self.employees]):
            vac_days = set(vacs_1b.get(emp_id, []))
            day_to_block = {d: (b, t) for (d, b, t) in self.assignment.get(emp_id, [])}
            line = [f"Emp{emp_id}"]
            for d in range(1, self.num_days + 1):
                if d in vac_days:
                    line.append("F")
                elif d in day_to_block:
                    block_idx, team_id = day_to_block[d]
                    block = self.work_blocks[block_idx]
                    team_code = TEAM_ID_TO_CODE.get(team_id, 'A')
                    line.append(f"{block[0]:.1f}-{block[1]:.1f}-{block[2]:.1f}_{team_code}")
                else:
                    line.append("OFF")
            rows.append(line)
        return rows


def solve(vacations=None, minimuns=None, employees=None, maxTime=None, year=2021, hours=13, work_blocks=None, rules=None, **kwargs):
    print(f"\n{'='*80}")
    print(f"[HEURISTIC_1] GREEDY SCHEDULER")
    print(f"{'='*80}")
    print(f"  Employees: {len(employees) if employees else 0}")
    print(f"  Vacations: {len(vacations) if vacations else 0} rows")
    print(f"  Minimums: {len(minimuns) if minimuns else 0} rows")
    print(f"  Max time: {maxTime} minutes (type: {type(maxTime).__name__})" if maxTime else "  Max time: default (8 hours)")
    print(f"  Year: {year}")
    print(f"  Store hours: {hours}")
    
    print(f"\n[HEURISTIC_1] Initializing scheduler...")
    sched = HeuristicOneScheduler(
        vacations, 
        minimuns, 
        employees, 
        maxTime, 
        year=year, 
        store_hours=hours, 
        work_blocks=work_blocks
    )
    
    print(f"[HEURISTIC_1] Running greedy algorithm...")
    status = sched.solve()
    
    print(f"[HEURISTIC_1] Status: {status}")
    print(f"[HEURISTIC_1] Exporting schedule...")
    sched.export_csv("hourly_strict_schedule.csv")
    
    print(f"{'='*80}")
    print(f"[HEURISTIC_1] COMPLETE")
    print(f"{'='*80}\n")
    
    return sched.to_table()
