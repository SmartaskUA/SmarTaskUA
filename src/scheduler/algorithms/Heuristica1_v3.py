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

        mins, ideals = rows_to_req_dicts_Half_Hour(minimums_rows)
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


# ----------------------------------------------------------------------------------------- --------------  

    def _feasible_employee_day(self, f, d):
        # férias
        if d in self.vacations_dates[f]:
            return False

        # já trabalhou nesse dia
        if d in self.worked_days[f]:
            return False

        # limite anual
        if len(self.worked_days[f]) >= 223:
            return False

        # regra 5 consecutivos (hard)
        last_days = [x for x in self.last_7_days[f] if x is not None]
        if len(last_days) >= 5:
            # se os últimos 5 dias foram consecutivos até ontem
            last_days_sorted = sorted(last_days)
            if (d - last_days_sorted[-1]).days == 1:
                return False

        return True


    def _feasible_block(self, f, b):
        if self.last_block[f] is None:
            return True

        return self._validate_block_transition(
            self.work_blocks[self.last_block[f]],
            self.work_blocks[b]
        )

    def _employee_scarcity(self, f, d):
        """
        Quantas meias-horas ainda existem nesse dia
        que este empregado consegue cobrir?
        Menor = mais raro = deve ser preservado
        """
        count = 0
        for (dd, h, t), v in self.remaining_min.items():
            if dd != d or v <= 0:
                continue
            if t not in self.emp_team_code[f]:
                continue
            for b in self._blocks_covering_hour(h):
                if self._feasible_block(f, b):
                    count += 1
                    break
        return count

    def _blocks_covering_hour(self, h):
        """Return list of blocks whose working-hours set covers the given hour label.

        Here ``h`` is a string label like '09.0-09.5' or '09.5-10.0', coming
        from the requirements dictionaries. We convert this label to the
        corresponding float start time (9.0 or 9.5, etc.) and check membership
        against ``self.block_hours[b]`` which is a set of floats.
        """
        # Convert label 'HH.H-HH.H' to the float start hour (e.g. '09.0-09.5' -> 9.0)
        try:
            start_str = str(h).split('-')[0]
            start_hour = float(start_str)
        except Exception:
            return []

        return [
            b for b in range(self.num_blocks)
            if start_hour in self.block_hours[b]
        ]

    def _criticality(self, d, h, team_code):
        count = 0

        for f in self.employees:
            if team_code not in self.emp_team_code[f]:
                continue
            if not self._feasible_employee_day(f, d):
                continue

            for b in self._blocks_covering_hour(h):
                if self._feasible_block(f, b):
                    count += 1
                    break

        return count


    def _coverage_score(self, d, b, team_code):
        score = 0
        for h in self.block_hours[b]:
            # ``h`` is a float hour (e.g. 9.0, 9.5). Minimum requirements
            # are indexed by string labels like '09.0-09.5' / '09.5-10.0'.
            # We map the float to the corresponding label before lookup.
            if h % 1 == 0:
                hour_label = f"{int(h):02d}.0-{int(h):02d}.5"
            else:
                hour_label = f"{int(h):02d}.5-{int(h)+1:02d}.0"

            key = (d, hour_label, team_code)
            if self.remaining_min.get(key, 0) > 0:
                score += 1
        return score


    def solve(self):
        print("[PHASE 1] Starting minimum coverage")

        # copiar mínimos
        self.remaining_min = {
            k: v for k, v in self.minimos.items() if v > 0
        }

        start_time = time()

        for d in self.dates:

            if d in self.closed_days:
                continue

            # mínimos do dia
            uncovered = {
                (h, t): v
                for (dd, h, t), v in self.remaining_min.items()
                if dd == d and v > 0
            }

            while uncovered:

                # escolher demanda mais crítica
                (h_star, t_star), _ = min(
                    uncovered.items(),
                    key=lambda x: self._criticality(d, x[0][0], x[0][1]) # x[0][0] = h, x[0][1] = t
                )

                best_choice = None
                best_score = -1

                for f in self.employees:

                    if t_star not in self.emp_team_code[f]:
                        continue
                    if not self._feasible_employee_day(f, d):
                        continue

                    for b in self._blocks_covering_hour(h_star):

                        if not self._feasible_block(f, b):
                            continue

                        score = self._coverage_score(d, b, t_star)

                        scarcity = self._employee_scarcity(f, d)

                        combined_score = (
                            1000 * score          # cobertura domina
                            - 10 * scarcity       # preserva empregados raros
                        )

                        if combined_score > best_score:
                            best_score = combined_score
                            best_choice = (f, b)


                # impossível cobrir
                if best_choice is None:
                    print(f"[PHASE 1] INFEASIBLE on {d} hour {h_star} team {t_star}")
                    print("Equipe B total:", len(self.teams.get('B', [])))

                    print("Blocos que cobrem 21.0:",
                          [b for b in range(self.num_blocks)
                           if 21.0 in self.block_hours[b]])
                    
                    for f in self.teams.get('B', []):
                        print("Emp", f,
                              "feasible_day:", self._feasible_employee_day(f, d),
                              "scarcity:", self._employee_scarcity(f, d))
                    
                
                    return "INFEASIBLE"

                f_star, b_star = best_choice

                # aplicar atribuição
                self.assignment[f_star + 1].append(
                    (self.dates.index(d) + 1, b_star, get_team_id(t_star))
                )

                self.worked_days[f_star].add(d)
                self.last_block[f_star] = b_star

                self.last_7_days[f_star].append(d)
                if len(self.last_7_days[f_star]) > 7:
                    self.last_7_days[f_star].pop(0)

                # atualizar mínimos
                for h in self.block_hours[b_star]:

                    if h % 1 == 0:
                        hour_label = f"{int(h):02d}.0-{int(h):02d}.5"
                    else:
                        hour_label = f"{int(h):02d}.5-{int(h)+1:02d}.0"

                    key = (d, hour_label, t_star)

                    if key in self.remaining_min:
                        self.remaining_min[key] -= 1
                        if self.remaining_min[key] <= 0:
                            del self.remaining_min[key]


                # atualizar uncovered
                uncovered = {
                    (h, t): v
                    for (h, t), v in uncovered.items()
                    if self.remaining_min.get((d, h, t), 0) > 0
                }

                # time limit
                if self.maxTime_sec and time() - start_time > self.maxTime_sec:
                    print("[PHASE 1] TIME LIMIT")
                    return "TIME_LIMIT"

        print("[PHASE 1] Minimum coverage completed")
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
