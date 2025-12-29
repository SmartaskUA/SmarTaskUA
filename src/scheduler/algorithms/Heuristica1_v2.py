from collections import defaultdict
from time import time
import pandas as pd
import random
import csv
from algorithms.utils import rows_to_vac_dict
from algorithms.utils import rows_to_req_dicts_Half_Hour
from algorithms.utils import (
    TEAM_ID_TO_CODE,
)


# =========================================================
# Utilidades temporais
# =========================================================

def hour_to_index(h):
    """9.0 -> 18, 9.5 -> 19"""
    return int(h * 2)

def index_to_hour(i):
    return i / 2

def build_half_hour_range(start, end):
    return list(range(hour_to_index(start), hour_to_index(end)))

# =========================================================
# Blocos de trabalho (9h com pausa de 1h)
# =========================================================

def create_blocks_half_hour(start=9, end=22, step=0.5):
    blocks = []
    s = start
    while s + 9 <= end:
        e = s + 9
        for pause_offset in [5, 5.5, 6]:
            work = set(build_half_hour_range(s, pause_offset))
            work |= set(build_half_hour_range(pause_offset + 1, e))
            blocks.append({
                "start": s,
                "end": e,
                "hours": work
            })
        s += step
    return blocks

# =========================================================
# Heurística corrigida
# =========================================================

class HeuristicSchedulerV2:

    def __init__(self, vacations_rows, minimums_rows, employees, year=2021, maxTime=300):

        self.dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()
        self.num_days = len(self.dates)
        self.employees = list(range(len(employees)))
        self.maxTime = maxTime

        # Equipas por empregado
        self.emp_teams = {
            i: tuple(emp.get("teams", ["A"]))
            for i, emp in enumerate(employees)
        }

        # Blocos
        self.blocks = create_blocks_half_hour()
        self.num_blocks = len(self.blocks)

        # Férias (formato do projeto)
        self.vacations = defaultdict(set)
        vacs = rows_to_vac_dict(vacations_rows)

        for emp_1b, days in vacs.items():
            emp = emp_1b - 1
            for d in days:
                if 1 <= d <= self.num_days:
                    self.vacations[emp].add(self.dates[d - 1])


        # Mínimos (meia-hora)
        self.min_req = defaultdict(int)
        self.closed_days = set()

        mins, _ = rows_to_req_dicts_Half_Hour(minimums_rows)

        for (day, half_hour, team_id), val in mins.items():
            date = self.dates[day - 1]
            team = TEAM_ID_TO_CODE[team_id]
            self.min_req[(date, half_hour, team)] = val


        # Dias realmente fechados
        for d in self.dates:
            closed = True
            for (dd, h, t), v in self.min_req.items():
                if dd == d and v >= 0:
                    closed = False
                    break
            if closed:
                self.closed_days.add(d)

        # Estado
        self.assigned = defaultdict(dict)  # emp -> day -> block
        self.last_block = {e: None for e in self.employees}
        self.consecutive = {e: 0 for e in self.employees}

    # -----------------------------------------------------

    def valid_transition(self, b1, b2):
        rest = (24 - b1["end"]) + b2["start"]
        return rest >= 12

    def block_gain(self, day, block, team):
        gain = 0
        for h in block["hours"]:
            k = (day, h, team)
            if self.min_req.get(k, 0) > 0:
                gain += 1
        return gain

    # -----------------------------------------------------

    def solve(self):

        start = time()

        for day in self.dates:
            if day in self.closed_days:
                continue

            # slots ordenados por maior pressão
            slots = sorted(
                [(h, t) for (d, h, t), v in self.min_req.items() if d == day and v > 0],
                key=lambda x: -self.min_req[(day, x[0], x[1])]
            )

            for h, team in slots:
                while self.min_req[(day, h, team)] > 0:

                    best = None
                    best_gain = -1

                    for e in self.employees:

                        if day in self.vacations[e]:
                            continue
                        if day in self.assigned[e]:
                            continue
                        if team not in self.emp_teams[e]:
                            continue

                        for b in self.blocks:
                            if h not in b["hours"]:
                                continue
                            if self.last_block[e] and not self.valid_transition(
                                self.last_block[e], b
                            ):
                                continue

                            g = self.block_gain(day, b, team)
                            if g > best_gain:
                                best = (e, b)
                                best_gain = g

                    if not best:
                        break

                    e, b = best
                    self.assigned[e][day] = b
                    self.last_block[e] = b
                    self.consecutive[e] += 1

                    for hh in b["hours"]:
                        k = (day, hh, team)
                        if self.min_req.get(k, 0) > 0:
                            self.min_req[k] -= 1

                    if time() - start > self.maxTime:
                        return "TIME_LIMIT"

        return "OK"
    
    def export_csv(self, filename="hourly_strict_schedule.csv"):
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            vacs_1b = self.vacs_1based()
            for emp in self.employees:
                emp_id = emp + 1
                vac_days = set(vacs_1b.get(emp_id, []))
                row = [f'Emp{emp_id}']
                for day_idx in range(1, self.num_days + 1):
                    day = self.dates[day_idx - 1]
                    if day_idx in vac_days:
                        row.append('VACATION')
                    elif day in self.assigned[emp]:
                        block = self.assigned[emp][day]
                        # Find which team this employee is assigned to (use first team for now)
                        team = self.emp_teams[emp][0]
                        row.append(f"{block['start']}-{block['start']+4}-{block['end']}_{team}")
                    else:
                        row.append('OFF')
                writer.writerow(row)

    def vacs_1based(self):
        return {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations[i]])
            for i in self.employees
        }
    
    def to_table(self):
        # returns rows as list of lists (same layout as ILP to_table)
        rows = []
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows.append(header)
        vacs_1b = self.vacs_1based()
        for emp in self.employees:
            emp_id = emp + 1
            vac_days = set(vacs_1b.get(emp_id, []))
            line = [f"Emp{emp_id}"]
            for day_idx in range(1, self.num_days + 1):
                day = self.dates[day_idx - 1]
                if day_idx in vac_days:
                    line.append("F")
                elif day in self.assigned[emp]:
                    block = self.assigned[emp][day]
                    # Find which team this employee is assigned to (use first team for now)
                    team = self.emp_teams[emp][0]
                    line.append(f"{block['start']}-{block['start']+4}-{block['end']}_{team}")
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
    
    print(f"[HEURISTIC_1] Initializing scheduler...")
    sched = HeuristicSchedulerV2(
        vacations, 
        minimuns, 
        employees, 
        year=year, 
        maxTime=maxTime
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
