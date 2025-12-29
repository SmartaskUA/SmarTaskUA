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
    
    def _init_state(self):
        self.worked_days = {f: set() for f in self.employees}
        self.consecutive = {f: 0 for f in self.employees}
        self.last_block = {f: None for f in self.employees}

    def _block_coverage(self, d, block_idx, team_code):
        covered = 0
        for h in self.block_hours[block_idx]:
            key = (d, h, team_code)
            if key in self.remaining_min and self.remaining_min[key] > 0:
                covered += 1
        return covered

    def _bad_decision_score(self, f, d, block_idx, team_code):
        score = 0

        # 1. Saturação anual
        saturation = len(self.worked_days[f]) / 223

        score += 5 * saturation

        # 2. Dias consecutivos
        if self.consecutive[f] >= 4:
            score += 20

        # 3. Transição futura
        if self.last_block[f] is not None:
            if not self._validate_block_transition(
                self.work_blocks[self.last_block[f]],
                self.work_blocks[block_idx]
            ):
                score += 100  # quase proibitivo

        # 4. Blocos extremos
        start, _, end = self.work_blocks[block_idx]
        if start <= 9.5 or end >= 21.5:
            score += 2

        # 5. Ganho de cobertura
        gain = self._block_coverage(d, block_idx, team_code)
        score -= 30 * gain

        return score

    def solve(self):

        print(f"[HeuristicOneScheduler] Starting solve with max time {self.maxTime_sec} seconds.")

        self._init_state()

        # copiar mínimos
        self.remaining_min = {
            (d, h, t): v
            for (d, h, t), v in self.minimos.items()
            if v > 0
        }

        start_time = time()

        for d in self.dates:
            if d in self.closed_days:
                continue

            # ordenar slots por pressão (maior mínimo primeiro)
            day_slots = sorted(
                [(h, t) for (dd, h, t), v in self.remaining_min.items() if dd == d],
                key=lambda x: -self.remaining_min.get((d, x[0], x[1]), 0)
            )

            for h, team_code in day_slots:
                while self.remaining_min.get((d, h, team_code), 0) > 0:

                    candidates = []

                    for f in self.teams.get(team_code, []):

                        print(f"[HeuristicOneScheduler] Considering employee {f} for date {d}, hour {h}, team {team_code}")

                        if d in self.vacations_dates[f]:
                            continue
                        if d in self.worked_days[f]:
                            continue

                        for b in range(self.num_blocks):

                            # Convert hour string "XX.X-YY.Y" to float XX.X for comparison
                            h_float = float(h.split('-')[0])
                            if h_float not in self.block_hours[b]:
                                print(f"[HeuristicOneScheduler]     Block {b} rejected for employee {f} as it does not cover hour {h}.")
                                continue
                            if self.last_block[f] is not None:
                                if not self._validate_block_transition(
                                    self.work_blocks[self.last_block[f]],
                                    self.work_blocks[b]
                                ):
                                    continue
                            
                            print(f"[HeuristicOneScheduler]     Block {b} is a candidate for employee {f}")
                            candidates.append((f, b))

                    print(f"[HeuristicOneScheduler] Found {len(candidates)} candidates for date {d}, hour {h}, team {team_code}")
                    
                    if not candidates:
                        print(f"[HeuristicOneScheduler] WARNING: No candidates found for date {d}, hour {h}, team {team_code}. Remaining minimum: {self.remaining_min.get((d, h, team_code), 0)}")
                        break  # não há como cumprir mais

                    best = min(
                        candidates,
                        key=lambda fb: self._bad_decision_score(
                            fb[0], d, fb[1], team_code
                        )
                    )

                    f, b = best

                    # aplicar
                    self.assignment[f + 1].append(
                        (self.dates.index(d) + 1, b, get_team_id(team_code))
                    )

                    self.worked_days[f].add(d)
                    self.consecutive[f] += 1
                    self.last_block[f] = b

                    # reduzir mínimos cobertos
                    for hh in self.block_hours[b]:
                        key = (d, hh, team_code)
                        if key in self.remaining_min:
                            self.remaining_min[key] = max(0, self.remaining_min[key] - 1)

                    if time() - start_time > self.maxTime_sec:
                        print(f"[HeuristicOneScheduler] Time limit reached after {self.maxTime_sec} seconds.")
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
                        row.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
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
                    line.append(f"{block[0]}-{block[1]}-{block[2]}_{team_code}")
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
