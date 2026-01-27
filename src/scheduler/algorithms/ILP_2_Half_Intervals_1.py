import csv
from collections import defaultdict
import datetime
from time import sleep, time
from ortools.sat.python import cp_model

import numpy as np
import pandas as pd
import pulp
import holidays
import gurobipy

from algorithms.utils import (
    build_calendar,
    rows_to_req_dicts_Half_Hour,
    rows_to_vac_dict,
    rows_to_req_dicts,
    export_schedule_to_csv_shifts,
    TEAM_CODE_TO_ID,      
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code,
    create_Blocks    
)


def rows_to_req_dicts_FIXED(req_rows):
    """
    ✅ CRITICAL FIX: Return hour keys as FLOAT tuples, not strings!
    Build model uses: (pd.Timestamp, float, team_id)
    Example: (Timestamp('2021-11-02'), 9.0, 1) not (Timestamp, "9.0-9.5", 1)
    """
    import pandas as pd

    mins = {}
    dates = pd.date_range(start="2021-11-01", end="2022-10-31").to_list()

    print(f"[DEBUG] Created {len(dates)} dates for conversion")

    for row in req_rows:
        if not row or len(row) < 3:
            continue
        
        team_label = row[0].strip()
        if not team_label.upper().startswith('EQUIPA'):
            continue
        
        second_col = row[1].strip()
        team_code = get_team_code(team_label)
        team_id = get_team_id(team_code)

        # Check if hour-based
        if '-' not in second_col:
            continue
            
        hour_label = second_col
        counts = row[2:]

        # Convert "09:00-09:30" to float 9.0
        if ':' in hour_label:
            try:
                start_str, end_str = hour_label.split('-')
                start_hour, start_min = map(int, start_str.split(':'))
                
                # ✅ KEY FIX: Store as FLOAT, not string
                start_float = float(start_hour) + (0.5 if start_min == 30 else 0.0)

            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        else:
            # "09-10" format
            try:
                parts = hour_label.split('-')
                start_float = float(parts[0])
            except (ValueError, IndexError) as e:
                print(f"[ERROR] Failed to parse hour '{hour_label}': {e}")
                continue
        
        # ✅ Store with (Timestamp, FLOAT, team_id) format
        for day_num, val in enumerate(counts, start=1):
            v = str(val).strip()

            if not v:
                continue
            
            try:
                val_int = int(v)
            except ValueError:
                continue
            
            
            # Convert day number (1-365) to Timestamp
            if 1 <= day_num <= len(dates):
                date_key = dates[day_num - 1]
            else:
                continue
            
            try:
                val_int = int(v)
                # ✅ KEY: Store as (date, FLOAT hour, team_id)
                mins[(date_key, start_float, team_id)] = val_int
            except ValueError:
                continue
                
    print(f"[DEBUG] Processed {len(mins)} minimum entries")
    print(f"[DEBUG] Sample keys (first 10):")
    for i, (key, val) in enumerate(list(mins.items())[:10]):
        print(f"  {key} → {val}")

    return mins, {}


class HourlyILPScheduler:
    """
    ILP Scheduler that assigns employees to hourly blocks instead of shifts.
    Each employee works 8 hours per day with a 1-hour break (4h + break + 4h pattern).
    """

    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2025, 
                 store_hours=13, work_blocks=None):
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)
        self.store_hours = int(store_hours)

        if work_blocks is None:
            self.work_blocks = self._generate_work_blocks()
        else:
            self.work_blocks = work_blocks

        self.emp_team_code = {}
        for idx, emp in enumerate(employees):
            teams = emp.get("teams", [])
            if not teams:
                codes = ("A",)
            else:
                codes = tuple(get_team_code(team) for team in teams)
            self.emp_team_code[idx] = codes
            for code in codes:
                get_team_id(code)

        """
        self.emp_team_code = {
          0: ("A",),        # Emp 0 só pode trabalhar equipa A
          1: ("A", "B"),    # Emp 1 pode trabalhar equipas A e B
          2: ("B",),        # Emp 2 só pode trabalhar equipa B
          3: ("C",),        # Emp 3 só pode trabalhar equipa C
        }
        """

        self.teams = {}
        for idx, codes in self.emp_team_code.items():
            for code in codes:
                self.teams.setdefault(code, set()).add(idx)

        """
        self.teams = {
          "A": {0, 1},      # Equipa A tem empregados 0 e 1
          "B": {1, 2},      # Equipa B tem empregados 1 e 2
          "C": {3},         # Equipa C tem empregado 3
        }
        """

        vacs_dict = rows_to_vac_dict(vacations_rows)
        self.vacations_dates = {
            e_idx: {
                self.dates[day - 1] for day in vacs_dict.get(e_idx + 1, []) 
                if 1 <= day <= self.num_days
            }
            for e_idx in self.employees
        }

        """
        {
          0: {datetime(2021, 11, 5), datetime(2021, 11, 10), datetime(2021, 11, 15)},
          1: {datetime(2021, 11, 20), datetime(2021, 11, 21), datetime(2021, 11, 22)},
          2: {datetime(2021, 12, 8)},
        }
        """

        mins, ideals = rows_to_req_dicts_FIXED(minimums_rows)
        
        # DEBUG: Verificar quantos mínimos foram processados
        print(f"\n[DEBUG] rows_to_req_dicts returned {len(mins)} entries")
        
        # Contar por equipa e hora
        from collections import defaultdict
        by_team = defaultdict(set)
        by_hour = defaultdict(int)
        
        for (day, hour, team_id), val in mins.items():
            by_team[team_id].add(hour)
            by_hour[hour] += 1
        
        print(f"[DEBUG] Teams found: {list(by_team.keys())}")
        for team_id, hours in by_team.items():
            print(f"[DEBUG]   Team {team_id}: {len(hours)} unique hours → {sorted(hours)[:5]}...")
        
        print(f"[DEBUG] Unique hours: {len(by_hour)}")
        print(f"[DEBUG] Sample hours: {list(sorted(by_hour.keys()))[:10]}")
        
        # ✅ rows_to_req_dicts_FIXED already returns (Timestamp, float, team_id) format
        # No conversion needed - just copy directly!
        self.minimos = mins.copy()
        self.ideais = ideals.copy()

        """
        self.minimos = {
            (datetime(2021, 11, 1), '09.0-09.5', 'A'): -1,   # Fechado
            (datetime(2021, 11, 2), '09.0-09.5', 'A'): 4,    # 4 pessoas
            (datetime(2021, 11, 3), '09.0-09.5', 'A'): 3,    # 3 pessoas
          ...
        }
        """
        
        print(f"[DEBUG] Final self.minimos has {len(self.minimos)} entries")
        print(f"[DEBUG] Expected: {self.num_days} days × {len(by_hour)} hours × {len(by_team)} teams = {self.num_days * len(by_hour) * len(by_team)}")

        # Br Blocos que influenciam o dia seguinte
        self.Br = set()
        for b in self.work_blocks:
            for a in self.work_blocks:
                if not self._validate_block_transition(b, a):
                    self.Br.add(b)

        self.Ar = set()
        for b in self.work_blocks:
            for a in self.work_blocks:
                if not self._validate_block_transition(b, a):
                    self.Ar.add(a)

        self.slot_hours = [9.0, 9.5, 10.0, 10.5, 11.0, 11.5, 12.0, 12.5, 13.0, 13.5, 14.0, 14.5, 15.0, 15.5, 16.0, 16.5, 17.0, 17.5, 18.0, 18.5, 19.0, 19.5, 20.0, 20.5, 21.0, 21.5]
        
        # Model variables
        self.x = None
        self.model = None
        self.status = None
        self.assignment = defaultdict(list)
        self.vacs_1based = {
            i + 1: sorted([self.dates.index(d) + 1 for d in self.vacations_dates[i]])
            for i in self.employees
        }

        """
        Somente para o export
        self.vacs_1based = {
          1: [6, 11, 16],           # Emp 1 tem férias nos dias 6, 11, 16 (1-based)
          2: [21, 22, 23],          # Emp 2 tem férias nos dias 21, 22, 23
          3: [39],                  # Emp 3 tem férias no dia 39
        }
        """

        # Adiciona ao __init__ ou como método separado:
    def quick_feasibility_check(self):
        """Verificação rápida de viabilidade"""
        print("\n" + "="*80)
        print("QUICK FEASIBILITY CHECK")
        print("="*80)

        # 1. Total de horas necessárias vs disponíveis
        # ⚠️ IMPORTANTE: Cada equipa é independente (funcionários podem estar em múltiplas equipas)
        # Calculamos requisitos POR EQUIPA, não somados
        
        from collections import defaultdict
        total_by_team = defaultdict(int)
        slots_by_team = defaultdict(int)
        
        for (d, h, team_id), val in self.minimos.items():
            if val > 0:
                total_by_team[team_id] += val
                slots_by_team[team_id] += 1

        # Capacidade teórica POR EQUIPA
        work_days = 223
        hours_per_day = 16  # 16 meias-horas = 8 horas

        print(f"1. CAPACITY BY TEAM:")
        print(f"   Work days each: {work_days}")
        print(f"   Half-hours per day: {hours_per_day}")
        
        all_feasible = True
        for team_code, team_members in self.teams.items():
            team_id = get_team_id(team_code)
            team_size = len(team_members)
            team_capacity = team_size * work_days * hours_per_day
            team_required = total_by_team.get(team_id, 0)
            
            print(f"\n   Team {team_code}:")
            print(f"     Employees: {team_size}")
            print(f"     Total capacity: {team_capacity:,} half-hours")
            print(f"     Total required: {team_required:,} half-hours")
            print(f"     Surplus: {team_capacity - team_required:,} half-hours")
            
            if team_required > team_capacity:
                print(f"     ❌ IMPOSSIBLE: Team {team_code} requirements exceed capacity!")
                all_feasible = False
            else:
                utilization = (team_required / team_capacity * 100) if team_capacity > 0 else 0
                print(f"     ✅ Feasible (utilization: {utilization:.1f}%)")

        if not all_feasible:
            return False

        if not all_feasible:
            return False

        # 2. Verifica picos diários POR EQUIPA
        # ✅ CORRIGIDO: Verifica o pico MÁXIMO em qualquer intervalo, não a soma total
        print(f"\n2. DAILY PEAKS BY TEAM:")
        daily_max = defaultdict(lambda: defaultdict(int))

        for (d, h, team_id), val in self.minimos.items():
            if val > 0:
                # Guarda o MÁXIMO requisito em qualquer intervalo deste dia
                daily_max[d][team_id] = max(daily_max[d][team_id], val)

        impossible_days = []

        for d, team_reqs in daily_max.items():
            for team_id, max_req in team_reqs.items():
                # ✅ FIX: Convert team_id to team_code for lookup
                team_code = get_team_code(TEAM_ID_TO_CODE[team_id])
                team_size = len(self.teams.get(team_code, set()))

                # ✅ CORRIGIDO: Compara com tamanho da equipa, não com capacidade diária
                # Um intervalo só pode ter no máximo team_size pessoas
                if max_req > team_size:
                    impossible_days.append((d, team_code, max_req, team_size))

        if impossible_days:
            print(f"   ❌ Found {len(impossible_days)} impossible day-team combinations:")
            for d, tc, req, maxp in impossible_days[:5]:
                print(f"   {d.strftime('%Y-%m-%d')} Team {tc}: need {req}, max possible {maxp}")
            return False
        else:
            print("   ✅ No single day exceeds team capacity")

        # 3. Verifica distribuição de equipas e picos por intervalo
        print(f"\n3. TEAM DISTRIBUTION & INTERVAL PEAKS:")
        for team_code, members in self.teams.items():
            print(f"   Team {team_code}: {len(members)} employees")

            # ✅ FIX: Convert team_code to team_id for lookup in minimos
            team_id = get_team_id(team_code)
            
            # Requisito máximo para esta equipa num ÚNICO slot (intervalo de 30 min)
            max_req_single_slot = max((val for (d, h, t_id), val in self.minimos.items() 
                                      if t_id == team_id and val > 0), default=0)

            if max_req_single_slot > len(members):
                print(f"      ❌ Max single-slot requirement ({max_req_single_slot}) > team size ({len(members)})")
                print(f"         This means at some 30-minute interval, we need more people than exist in the team!")
                return False
            else:
                print(f"      ✅ Max single-slot requirement ({max_req_single_slot}) <= team size")
                
            # Mostra alguns exemplos de requisitos altos
            high_reqs = sorted([(d, h, val) for (d, h, t_id), val in self.minimos.items() 
                               if t_id == team_id and val > 0], key=lambda x: -x[2])[:3]
            if high_reqs:
                print(f"      Top 3 highest requirements:")
                for d, h, val in high_reqs:
                    print(f"        {d.strftime('%Y-%m-%d')} {h}: {val} people")

        # 4. Verifica férias em dias críticos POR EQUIPA
        print(f"\n4. VACATION CONFLICTS BY TEAM:")
        conflicts = 0
        conflict_details = []

        for d in self.dates:
            # Para cada equipa, verifica se há funcionários suficientes
            for team_code, members in self.teams.items():
                # Conta quantos desta equipa estão de férias
                on_vacation = sum(1 for emp in members 
                                 if d in self.vacations_dates.get(emp, set()))
                
                # ✅ FIX: Convert team_code to team_id for lookup in minimos
                team_id = get_team_id(team_code)
                
                # Requisito máximo neste dia para esta equipa
                day_team_reqs = [(h, val) for (date, h, t_id), val in self.minimos.items() 
                                if date == d and t_id == team_id and val > 0]
                
                if not day_team_reqs:
                    continue  # Dia fechado ou sem requisitos
                    
                max_day_req = max(val for h, val in day_team_reqs)
                available = len(members) - on_vacation
                
                if max_day_req > available:
                    conflicts += 1
                    conflict_details.append({
                        'date': d,
                        'team': team_code,
                        'required': max_day_req,
                        'available': available,
                        'on_vacation': on_vacation,
                        'team_size': len(members)
                    })

        if conflicts > 0:
            print(f"   ❌ Found {conflicts} days with vacation conflicts")
            print(f"   First 5 conflicts:")
            for c in conflict_details[:5]:
                print(f"   {c['date'].strftime('%Y-%m-%d')} Team {c['team']}: need {c['required']}, "
                      f"only {c['available']} available ({c['on_vacation']}/{c['team_size']} on vacation)")
            return False
        else:
            print("   ✅ No vacation conflicts")

        print("="*80 + "\n")
        return True

    def _generate_work_blocks(self):
        """
        Generate valid work blocks based on the specific combinations provided.
        Each tuple represents (start_hour, break_hour, end_hour).
        Examples:
        - (9, 13, 18): work 9-13 (4h), break 13-14, work 14-18 (4h) = 8h total
        - (9, 14, 18): work 9-14 (5h), break 14-15, work 15-18 (3h) = 8h total
        """
        blocks = create_Blocks(0.5, 9, 22)
        for b in blocks:
            print(f"  Block: {b[0]}-{b[1]}-{b[2]}")
            """
            scheduler  |   Block: 9.0-14.0-18.0
            scheduler  |   Block: 9.0-15.0-18.0
            scheduler  |   Block: 9.0-16.0-18.0
            scheduler  |   Block: 9.5-14.5-18.5
            scheduler  |   Block: 9.5-15.5-18.5
            scheduler  |   Block: 9.5-16.5-18.5
            scheduler  |   Block: 10.0-15.0-19.0
            scheduler  |   Block: 10.0-16.0-19.0
            scheduler  |   Block: 10.0-17.0-19.0
            """
        sleep(2)
        return blocks

    def _get_working_hours(self, block):
        start, break_start, end = block
        hours = []

        # Antes da pausa
        h = start
        while h < break_start:
            hours.append(round(h, 1))
            h += 0.5

        # Depois da pausa (pausa = 1h)
        h = break_start + 1
        while h < end:
            hours.append(round(h, 1))
            h += 0.5

        return hours



    def _blocks_overlap(self, block1, block2):
        """Check if two work blocks have overlapping working hours."""
        hours1 = self._get_working_hours(block1)
        hours2 = self._get_working_hours(block2)
        return len(hours1 & hours2) > 0

    def _validate_block_transition(self, block_today, block_tomorrow):
        """
        Check if transition from block_today to block_tomorrow is valid.
        Rules: 
        - Must have at least 12 hours rest between end and start
        """
        end_today = block_today[2]  # End hour of today's block
        start_tomorrow = block_tomorrow[0]  # Start hour of tomorrow's block
        rest_hours = (24 - end_today) + start_tomorrow
        return rest_hours >= 12

    # MUDANÇAS CRÍTICAS NO build_model():

    def build_model(self):
        """Build the ILP model with HARD minimum constraints."""
        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(len(self.work_blocks)))

        # Slots reais vindos dos mínimos (fonte da verdade)
        horas = self.slot_hours


        # Decision variables X (unchanged)
        self.x = {
            f: {
                d: {
                    b: {
                        team_code: pulp.LpVariable(
                            f"x_{f}_{d.strftime('%Y%m%d')}_{b}_{team_code}", 
                            cat="Binary"
                        )
                        for team_code in self.emp_team_code[f]
                    }
                    for b in blocos
                }
                for d in dias
            }
            for f in funcionarios
        }

        # Auxiliary Y variables (unchanged)
        self.y = {
            d: {
                h: {
                    team_code: pulp.LpVariable(
                        f"y_{d.strftime('%Y%m%d')}_h{h}_{team_code}",
                        lowBound=0, cat="Integer"
                    )
                    for team_code in self.teams.keys()
                }
                for h in horas
            }
            for d in dias
        }

        # ✅ CSP Model (NO objective - just feasibility)
        model = pulp.LpProblem("Hourly_Schedule_CSP", pulp.LpMinimize)
        model += (0, "Feasibility")  # Dummy objective

        print(f"[HourlyILP] Linking Y with X...")
        # Link Y with X: count workers at each hour
        for d in dias:
            for h in horas:
                for team_code, members in self.teams.items():
                    # working_hours_check = []
                    # for b in blocos:
                    #     working_hours = self._get_working_hours(self.work_blocks[b])
                    #     is_working = h in working_hours
                    #     working_hours_check.append((b, is_working, working_hours))
                    #     # if is_working:
                    #         #print(f"[DEBUG] h={h}, block={b} ({self.work_blocks[b]}), working_hours={working_hours}")
                    
                    model += (
                        self.y[d][h][team_code] ==
                        pulp.lpSum(
                            self.x[f][d][b][tc]
                            for f in members
                            for b in blocos
                            if h in self._get_working_hours(self.work_blocks[b])
                            for tc in self.emp_team_code[f]
                            if tc == team_code
                        ),
                        f"link_y_x_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                    )

        # ✅ HARD CONSTRAINTS: Minimum coverage MUST be met
        print(f"[HourlyILP] Adding HARD minimum coverage constraints...")
        min_constraints_added = 0

        for d in dias:
            for h in horas:
                for team_code in self.teams.keys():
                    # ✅ FIX: self.minimos uses (Timestamp, FLOAT, team_id) keys
                    team_id = get_team_id(team_code)
                    minimo = self.minimos.get((d, h, team_id), None)
                    
                    if minimo == -1:
                        # Closed - force to 0
                        model += (
                            self.y[d][h][team_code] == 0,
                            f"closed_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                        )

                    elif minimo is None:
                        model += self.y[d][h][team_code] == 0


                    else:
                        
                        # Relaxed constraint: coverage >= minimum - 1
                        model += (
                            self.y[d][h][team_code] >= minimo,
                            f"min_coverage_{d.strftime('%Y%m%d')}_h{h}_{team_code}"
                        )
                        min_constraints_added += 1

        print(f"  Added {min_constraints_added} hard minimum constraints")

        # CONSTRAINT 1: One block per day OR vacation
        print(f"[HourlyILP] Adding one-block-per-day constraints...")
        for f in funcionarios:
            for d in dias:
                is_vacation = 1 if d in self.vacations_dates[f] else 0
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 1 - is_vacation,
                    f"one_block_f{f}_{d.strftime('%Y%m%d')}"
                )

        # CONSTRAINT 2: 223 working days
        # print(f"[HourlyILP] Adding 223-days constraints...")
        # for f in funcionarios:
        #     model += (
        #         pulp.lpSum(
        #             self.x[f][d][b][tc]
        #             for d in dias
        #             for b in blocos
        #             for tc in self.emp_team_code[f]
        #         ) == 223,
        #         f"total_days_f{f}"
        #     )

        # 4. No work on days marked with -1 (closed days/holidays)
        # Identify all dates where minimum is -1 for any team
        closed_days = set()
        for (date_key, hora_str, team_code), minimo in self.minimos.items():
            if minimo == -1:
                closed_days.add(date_key)
        
        # Force no work on closed days
        # for f in funcionarios:
        #     for d in closed_days:
        model += (
            pulp.lpSum(
                self.x[f][d][b][tc]
                for f in funcionarios
                for d in closed_days
                for b in blocos
                for tc in self.emp_team_code[f]
            ) == 0,
            f"no_work_closed_day"
        )

        # CONSTRAINT 4: Max 5 consecutive days
        print(f"[HourlyILP] Adding max-5-consecutive constraints...")
        for f in funcionarios:
            for i in range(len(dias) - 5):
                window = dias[i:i + 6]
                model += (
                    pulp.lpSum(
                        self.x[f][d][b][tc]
                        for d in window
                        for b in blocos
                        for tc in self.emp_team_code[f]
                    ) <= 5,
                    f"max5_f{f}_d{i}"
                )

        # CONSTRAINT 5: ✅ OPTIMIZED - 12h rest
        # print(f"[HourlyILP] Pre-computing incompatible block pairs...")
        # incompatible_pairs = []
        # for b_idx, b in enumerate(self.work_blocks):
        #     for a_idx, a in enumerate(self.work_blocks):
        #         if not self._validate_block_transition(b, a):
        #             incompatible_pairs.append((b_idx, a_idx))
# 
        # print(f"  Found {len(incompatible_pairs)} incompatible pairs")
        # print(f"  Adding rest constraints...")
# 
        # for f in funcionarios:
        #     for i in range(len(dias) - 1):
        #         d_today = dias[i]
        #         d_next = dias[i + 1]
# 
        #         for (b_idx, a_idx) in incompatible_pairs:
        #             model += (
        #                 pulp.lpSum(self.x[f][d_today][b_idx][tc] for tc in self.emp_team_code[f]) +
        #                 pulp.lpSum(self.x[f][d_next][a_idx][tc] for tc in self.emp_team_code[f])
        #                 <= 1,
        #                 f"rest_f{f}_d{i}_b{b_idx}_{a_idx}"
        #             )

        self._validate_minimum_coverage_feasibility()

        all_hours = sorted({h for (_, h, _) in self.minimos})
        covered = sorted({h for b in self.work_blocks for h in self._get_working_hours(b)})

        print("Slots sem cobertura:", set(all_hours) - set(covered))


        self.model = model
        print("[HourlyILP] Model built successfully")
        print(f"  Variables: {model.numVariables():,}")
        print(f"  Constraints: {model.numConstraints():,}")


    def diagnose_solution(self):
        """Verifica se mínimos foram cumpridos na solução"""
        print("\n" + "="*80)
        print("SOLUTION DIAGNOSIS - CHECKING MINIMUM COVERAGE")
        print("="*80)

        total_violations = 0
        violations_detail = []

        for d in self.dates:
            h = 9.0
            while h < 22.0:
                for team_code in self.teams.keys():
                    # ✅ FIX: self.minimos uses (Timestamp, FLOAT, team_id) keys
                    team_id = get_team_id(team_code)
                    minimo = self.minimos.get((d, h, team_id), None)

                    if minimo is None or minimo == -1:
                        continue
                    
                    actual = pulp.value(self.y[d][h][team_code]) or 0

                    if actual < minimo:
                        deficit = minimo - actual
                        total_violations += deficit
                        violations_detail.append({
                            'date': d,
                            'hour': f"{h:.1f}-{h+0.5:.1f}",
                            'team': team_code,
                            'required': minimo,
                            'actual': int(actual),
                            'deficit': deficit
                        })

                h += 0.5

        if total_violations == 0:
            print("✅ ALL MINIMUM REQUIREMENTS SATISFIED!")
            print("   Solution is VALID and COMPLETE")
        else:
            print(f"❌ VIOLATIONS FOUND: {total_violations} total deficit")
            print(f"   Number of violated slots: {len(violations_detail)}")
            print(f"\n   First 10 violations:")
            for v in violations_detail[:10]:
                print(f"   {v['date'].strftime('%Y-%m-%d')} {v['hour']} Team {v['team']}: "
                      f"need {v['required']}, have {v['actual']} (deficit: {v['deficit']})")

            # Agrupa por dia
            from collections import defaultdict
            by_day = defaultdict(int)
            for v in violations_detail:
                by_day[v['date']] += v['deficit']

            worst_days = sorted(by_day.items(), key=lambda x: -x[1])[:5]
            print(f"\n   Worst 5 days:")
            for d, deficit in worst_days:
                print(f"   {d.strftime('%Y-%m-%d')}: {deficit} total deficit")

        print("="*80 + "\n")
        return total_violations

    def diagnose_specific_day(self, day_index, team_code='A'):
        """Diagnóstico detalhado de um dia específico, intervalo a intervalo"""
        d = self.dates[day_index - 1]  # Convert to 0-based
        
        print("\n" + "="*80)
        print(f"DETAILED DIAGNOSIS - Day {day_index} ({d.strftime('%Y-%m-%d')}) - Team {team_code}")
        print("="*80)
        
        # ✅ DIAGNOSE: Verify minimums are stored correctly
        print(f"\nChecking self.minimos for this day...")
        team_id = get_team_id(team_code)
        
        found_entries = []
        for (date_key, hora_str, tc), val in self.minimos.items():
            if date_key == d and (tc == team_code or tc == team_id):
                found_entries.append((hora_str, tc, val))
        
        if found_entries:
            print(f"Found {len(found_entries)} entries in self.minimos:")
            for hora_str, tc, val in sorted(found_entries)[:10]:
                print(f"  ({d.strftime('%Y-%m-%d')}, '{hora_str}', {tc}) = {val}")
            if len(found_entries) > 10:
                print(f"  ... and {len(found_entries) - 10} more")
        else:
            print(f"⚠️  NO ENTRIES FOUND in self.minimos for day {d.strftime('%Y-%m-%d')} team {team_code}/{team_id}")
            print(f"   This means rows_to_req_dicts_CORRECTED didn't process this day!")
            
            # Show sample of what IS in minimos
            print(f"\n   Sample of what IS in self.minimos:")
            for i, ((date_key, hora_str, tc), val) in enumerate(list(self.minimos.items())[:5]):
                print(f"     ({date_key}, '{hora_str}', {tc}) = {val}")
        
        print()
        
        # Get all employees in this team
        team_members = self.teams.get(team_code, set())
        
        print(f"\nTeam {team_code} has {len(team_members)} employees: {sorted([e+1 for e in team_members])}")
        
        # Get all blocks used by team members on this day
        print(f"\nBlocks assigned on this day:")
        blocos_usados = []
        for emp in team_members:
            emp_id = emp + 1
            for (day_idx, block_idx, team_id) in self.assignment.get(emp_id, []):
                if day_idx == day_index and get_team_code(TEAM_ID_TO_CODE[team_id]) == team_code:
                    block = self.work_blocks[block_idx]
                    blocos_usados.append((emp_id, block_idx, block))
                    print(f"  Employee {emp_id}: Block {block_idx} = {block}")
        
        print(f"\nInterval-by-interval coverage:")
        print(f"{'Hour':<15} {'Required':<10} {'Actual':<10} {'Status':<15} {'Employees'}")
        print("-" * 80)
        
        h = 9.0
        intervals_shown = 0
        while h < 22.0:
            hora_str = f"{h:.1f}-{h+0.5:.1f}"
            
            # ✅ FIX: self.minimos uses (Timestamp, FLOAT, team_id) keys
            team_id = get_team_id(team_code)
            minimo = self.minimos.get((d, h, team_id), None)
            
            # Get actual count from model
            actual = pulp.value(self.y[d][h][team_code]) if self.y else 0
            actual = actual or 0
            
            # Find which employees are working at this hour
            working_emps = []
            for emp_id, block_idx, block in blocos_usados:
                working_hours = self._get_working_hours(block)
                if h in working_hours:
                    working_emps.append(emp_id)
            
            # Show even if minimo is None or -1
            if minimo is None:
                req_str = "N/A"
                status = "⚪ No data"
            elif minimo == -1:
                req_str = "CLOSED"
                status = "🔒 Closed"
            else:
                req_str = str(minimo)
                diff = actual - minimo
                
                if diff < 0:
                    status = f"❌ -{int(-diff)}"
                elif diff > 0:
                    status = f"⚠️  +{int(diff)}"
                else:
                    status = "✅ OK"
            
            print(f"{hora_str:<15} {req_str:<10} {int(actual):<10} {status:<15} {sorted(working_emps)}")
            intervals_shown += 1
            h += 0.5
        
        print(f"\nTotal intervals shown: {intervals_shown}")
        
        # Show available blocks that could cover the deficit hours
        print("\n" + "="*80)
        print("AVAILABLE BLOCKS ANALYSIS")
        print("="*80)
        
        deficit_hours = [9.0, 9.5, 10.0, 20.0, 20.5, 21.0, 21.5]
        print(f"\nBlocks that could cover deficit hours {deficit_hours}:")
        
        for idx, block in enumerate(self.work_blocks):
            working_hours = self._get_working_hours(block)
            # Check if this block covers any deficit hour
            covers_deficit = any(h in working_hours for h in deficit_hours)
            
            if covers_deficit:
                covered = [h for h in deficit_hours if h in working_hours]
                print(f"  Block {idx}: {block}")
                print(f"    → Works: {min(working_hours):.1f} to {max(working_hours)+0.5:.1f}")
                print(f"    → Covers deficit hours: {covered}")
                
                # Check if this block was used by anyone on this day
                used_by = []
                for emp_id, block_idx, _ in blocos_usados:
                    if block_idx == idx:
                        used_by.append(emp_id)
                
                if used_by:
                    print(f"    ✅ Used by: {used_by}")
                else:
                    print(f"    ❌ NOT USED - Why?")
                    # Check if it violates rest constraint
                    print(f"       Possible reasons:")
                    print(f"       - Violates 12h rest with previous/next day blocks")
                    print(f"       - Employee needed in different hour slots")
                    print(f"       - Not enough employees in team")
        
        print("="*80 + "\n")
    
    def _validate_minimum_coverage_feasibility(self):
        impossible = []

        for (d, h, team_id), val in self.minimos.items():
            if val <= 0:
                continue

            covering_blocks = [
                b for b in self.work_blocks
                if h in self._get_working_hours(b)
            ]

            if not covering_blocks:
                impossible.append((d, h, team_id, val))

        if impossible:
            print("\n❌ SLOTS IMPOSSÍVEIS DETETADOS:")
            for d, h, t, v in impossible[:10]:
                print(f"  {d.strftime('%Y-%m-%d')} {h} team {t} min={v}")
            raise RuntimeError("Modelo impossível: slots sem blocos possíveis")


    def compute_iis(self):
        """Computa o IIS (Irreducible Inconsistent Subsystem) com Gurobi"""
        print("\n" + "="*80)
        print("🔍 COMPUTING IIS (Identifying Conflicting Constraints)")
        print("="*80)

        # Escreve o modelo para ficheiro LP
        lp_file = "/tmp/infeasible_model.lp"
        ilp_file = "/tmp/infeasible.ilp"
        
        self.model.writeLP(lp_file)
        print(f"Model written to: {lp_file}")

        # Cria modelo Gurobi diretamente
        import gurobipy as gp

        # Lê o modelo do ficheiro
        gurobi_model = gp.read(lp_file)

        # Computa IIS (suprime output do Gurobi)
        print("\nComputing IIS...")
        gurobi_model.setParam('OutputFlag', 0)  # Silencia Gurobi
        gurobi_model.computeIIS()

        # Escreve IIS para ficheiro
        gurobi_model.write(ilp_file)
        print(f"IIS written to: {ilp_file}")

        # Analisa constraints no IIS
        print("\n" + "="*80)
        print("CONFLICTING CONSTRAINTS (Root Causes):")
        print("="*80)

        constraint_types = {}

        for constr in gurobi_model.getConstrs():
            if constr.IISConstr:
                constr_name = constr.ConstrName

                # Identifica tipo de constraint
                if "min_coverage" in constr_name:
                    constraint_types.setdefault("⚠️  Minimum Coverage", []).append(constr_name)
                elif "total_days" in constr_name:
                    constraint_types.setdefault("📅 223 Days Exactly", []).append(constr_name)
                elif "one_block" in constr_name:
                    constraint_types.setdefault("🔄 One Block/Day", []).append(constr_name)
                elif "max5" in constr_name:
                    constraint_types.setdefault("🚫 Max 5 Consecutive", []).append(constr_name)
                elif "rest" in constr_name:
                    constraint_types.setdefault("😴 12h Rest", []).append(constr_name)
                elif "closed" in constr_name:
                    constraint_types.setdefault("🔒 Closed Days", []).append(constr_name)
                elif "link_y_x" in constr_name:
                    constraint_types.setdefault("🔗 Y-X Linking", []).append(constr_name)
                else:
                    constraint_types.setdefault("❓ Other", []).append(constr_name)

        # Resumo por tipo
        print("\nConstraint Types in Conflict:")
        total_conflicts = sum(len(clist) for clist in constraint_types.values())
        print(f"Total conflicting constraints: {total_conflicts}\n")
        
        for ctype, clist in sorted(constraint_types.items(), key=lambda x: -len(x[1])):
            pct = (len(clist) / total_conflicts * 100) if total_conflicts > 0 else 0
            print(f"{ctype}: {len(clist)} ({pct:.1f}%)")
            # Mostra alguns exemplos
            for c in clist[:2]:
                print(f"  └─ {c}")
            if len(clist) > 2:
                print(f"  └─ ... and {len(clist) - 2} more")
            print()

        print("\n" + "="*80)
        print("💡 RECOMMENDATIONS:")
        print("="*80)

        if "⚠️  Minimum Coverage" in constraint_types and "📅 223 Days Exactly" in constraint_types:
            print("1. CONFLICT: Minimum coverage ↔ 223 working days")
            print("   → Not enough total working hours to satisfy all minimums")
            print("   → Solutions:")
            print("      a) Reduce minimum requirements in CSV")
            print("      b) Hire more employees")
            print("      c) Relax 223 days constraint (allow ±5 days tolerance)")

        if "⚠️  Minimum Coverage" in constraint_types and "🔒 Closed Days" in constraint_types:
            print("\n2. CONFLICT: Minimum coverage ↔ Closed days")
            print("   → Some days are closed but still have minimum requirements > 0")
            print("   → Solution: Fix CSV - closed days should have minimum = -1")

        if "😴 12h Rest" in constraint_types:
            rest_count = len(constraint_types["😴 12h Rest"])
            print(f"\n3. CONFLICT: 12h rest is too restrictive ({rest_count} violations)")
            print("   → Block transitions don't allow 12h rest between shifts")
            print("   → Solutions:")
            print("      a) Relax to 11h or 11.5h rest")
            print("      b) Adjust work blocks to allow more transitions")
            print("      c) Remove/relax other constraints to compensate")

        if "🚫 Max 5 Consecutive" in constraint_types:
            print("\n4. CONFLICT: Max 5 consecutive days is too restrictive")
            print("   → Coverage requires longer consecutive work periods")
            print("   → Solution: Allow 6 or 7 consecutive days")

        if "📅 223 Days Exactly" in constraint_types and "🚫 Max 5 Consecutive" in constraint_types:
            print("\n5. CONFLICT: 223 days exactly ↔ Max 5 consecutive")
            print("   → Impossible to fit 223 days with max 5 consecutive pattern")
            print("   → Solution: Relax to 223 ± tolerance or allow 6 consecutive")

        print("="*80 + "\n")

        return constraint_types



    # ✅ ADICIONA ao solve():
    def solve(self, gap_rel=0.01):
        if self.model is None:
            self.build_model()

        print(f"\n{'='*80}")
        print(f"[HourlyILP] SOLVING CSP MODEL (Hard Constraints)")
        print(f"{'='*80}")

        # Use CBC solver (open-source, bundled with PuLP)
        solver = pulp.PULP_CBC_CMD(
            msg=True,
            timeLimit=self.maxTime_sec if self.maxTime_sec else None,
            gapRel=gap_rel,
            threads=8
        )

        self.status = self.model.solve(solver)

        status_map = {
            pulp.LpStatusOptimal: "Optimal",
            pulp.LpStatusNotSolved: "Not Solved",
            pulp.LpStatusInfeasible: "Infeasible",
            pulp.LpStatusUnbounded: "Unbounded",
            pulp.LpStatusUndefined: "Undefined"
        }
        

        print(f"[HourlyILP] Status: {status_map.get(self.status, 'Unknown')}")

        if self.status == pulp.LpStatusOptimal or self.status == pulp.LpStatusNotSolved:
            self._extract_assignments()

            # ✅ DIAGNÓSTICO
            violations = self.diagnose_solution()

            if violations > 0:
                print("⚠️  WARNING: Solution has violations despite being 'optimal'")
                print("   This suggests the constraints are too restrictive")
        elif self.status == pulp.LpStatusInfeasible:
            # ✅ COMPUTA IIS AUTOMATICAMENTE
            print("\n❌ INFEASIBLE: No solution exists that satisfies all constraints")
            try:
                iis_info = self.compute_iis()
            except Exception as e:
                print(f"\n⚠️  Could not compute IIS: {e}")
                print(f"   Error type: {type(e).__name__}")
                import traceback
                traceback.print_exc()

        return self.status

    def _extract_assignments(self):
        """Extract solution into assignment dict."""
        if self.x is None:
            return
        
        print(f"\n{'='*80}")
        print(f"EXTRACTING ASSIGNMENTS FROM SOLUTION")
        print(f"{'='*80}")
        
        # Use integer indices as in build_model
        blocos = list(range(len(self.work_blocks)))
        
        for f in self.employees:
            emp_id = f + 1
            team_codes = self.emp_team_code.get(f, ("A",))
            primary_team_code = team_codes[0] if team_codes else "A"
            primary_team_id = get_team_id(str(primary_team_code))
            
            emp_assignments = []
            
            for day_idx, d in enumerate(self.dates, start=1):
                # Find which block was assigned
                best_block = None
                best_val = 0
                best_team = primary_team_code
                
                for b in blocos:
                    for tc in team_codes:
                        val = pulp.value(self.x[f][d][b][tc]) or 0.0
                        if val > best_val:
                            best_val = val
                            best_block = b
                            best_team = tc
                
                if best_block is not None and best_val > 0.5:
                    team_id = get_team_id(str(best_team))
                    self.assignment[emp_id].append((day_idx, best_block, team_id))
                    emp_assignments.append((day_idx, best_block, team_id))
            
            # Print summary for this employee
            if emp_assignments:
                block_obj = self.work_blocks[emp_assignments[0][1]]
                print(f"\nEmployee {emp_id}:")
                print(f"  Total working days: {len(emp_assignments)}")
                print(f"  Teams: {team_codes}")
                print(f"  First 5 assignments: {emp_assignments[:5]}")
                print(f"  Sample block: {block_obj}")
        
        print(f"\n{'='*80}\n")

    def export_csv(self, filename="hourly_schedule.csv"):
        """Export schedule to CSV."""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            header = ['Employee'] + [f'Day{i}' for i in range(1, self.num_days + 1)]
            writer.writerow(header)
            
            # Each employee
            for emp_id in sorted([i + 1 for i in self.employees]):
                vac_days = set(self.vacs_1based.get(emp_id, []))
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
        
        print(f"[HourlyILP] Schedule exported to {filename}")

    def to_table(self):
        """Return schedule as table for display."""
        header = ["Employee"] + [f"Day{i}" for i in range(1, self.num_days + 1)]
        rows = [header]
        
        for emp_id in sorted([i + 1 for i in self.employees]):
            vac_days = set(self.vacs_1based.get(emp_id, []))
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


def solve(vacations, minimuns, employees, maxTime, year=2025, hours=13, 
          work_blocks=None, rules=None):
    """
    Main solve function for hourly scheduling.
    
    Args:
        vacations: Vacation data rows
        minimuns: Minimum requirements rows  
        employees: List of employee dicts
        maxTime: Maximum solving time in minutes
        year: Year for scheduling
        hours: Total store operating hours (default 13: 9am-10pm)
        work_blocks: Optional custom work blocks, otherwise auto-generated
        rules: Optional rules dict (for future extensions)
    
    Returns:
        Table representation of the schedule
    """
    scheduler = HourlyILPScheduler(
        vacations_rows=vacations,
        minimums_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        store_hours=hours,
        work_blocks=work_blocks
    )

    scheduler.quick_feasibility_check()
    scheduler.build_model()
    
    scheduler.solve(gap_rel=0.01)  # 1% optimality gap
    scheduler.diagnose_specific_day(4, 'A')
    scheduler.export_csv("hourly_schedule.csv")
    
    return scheduler.to_table()