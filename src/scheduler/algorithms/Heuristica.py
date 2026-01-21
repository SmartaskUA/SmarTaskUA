import csv
from collections import defaultdict
import datetime
from time import time

import numpy as np
import pandas as pd
import pulp
import holidays
from time import time, sleep

from algorithms.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_CODE_TO_ID,      
    TEAM_ID_TO_CODE,      
    get_team_id,   
    get_team_code       
)


class Heuristica:
    """
    ILP Scheduler that assigns employees to hourly blocks instead of shifts.
    Each employee works 8 hours per day with a 1-hour break (4h + break + 4h pattern).
    """
    
    def __init__(self, vacations_rows, minimums_rows, employees, maxTime, year=2025, 
                 store_hours=13, work_blocks=None):
        
        self.year = year
        self.maxTime_sec = int(maxTime) * 60 if maxTime is not None else None

        # Calendar - Using 2021-11-01 to 2022-10-31 as in original
        self.dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()
        self.num_days = len(self.dates)
        #print(f"[HourlyILP] Calendar has {self.num_days} days")

        # Employees
        self.employees = list(range(len(employees)))
        self.num_employees = len(self.employees)
        print(f"[HourlyILP] Employees: {self.employees}")
        
        # Store operating hours (9:00-22:00 = 13 hours)
        self.store_hours = int(store_hours)
        
        self.work_blocks = self._generate_work_blocks()   
        print(f"[HourlyILP] Work blocks: {self.work_blocks[:5]}... (showing first 5)")

        # Employee teams
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

        # Build team membership
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

        # Holidays and Sundays
        feriados_pt = {
            datetime.date(2022, 1, 1): "New Year's Day", 
            datetime.date(2022, 1, 6): 'Epiphany', 
            datetime.date(2022, 3, 1): 'Day of Baleares', 
            datetime.date(2022, 4, 14): 'Maundy Thursday', 
            datetime.date(2022, 4, 15): 'Good Friday', 
            datetime.date(2022, 5, 1): 'Labor Day', 
            datetime.date(2022, 5, 2): 'Madrid Day', 
            datetime.date(2022, 6, 29): 'Folga', 
            datetime.date(2022, 7, 8): 'Folga', 
            datetime.date(2022, 8, 15): 'Assumption Day', 
            datetime.date(2022, 9, 8): 'Regional Holiday', 
            datetime.date(2022, 10, 12): 'National Day',
            datetime.date(2021, 11, 1): "All Saints' Day", 
            datetime.date(2021, 12, 6): 'Constitution Day',
            datetime.date(2021, 12, 8): 'Immaculate Conception',
            datetime.date(2021, 12, 25): 'Christmas Day'
        }
    
        # Vacations
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

        # Minimum requirements per hour
        mins, ideals = rows_to_req_dicts(minimums_rows)
        self.minimos = {} #(1, '09-10', 1): -1, (2, '09-10', 1): 4, (3, '09-10', 1): 3, (4, '09-10', 1): 2, (5, '09-10', 1): 3, (6, '09-10', 1): 4, (7, '09-10', 1): -1, (8, '09-10', 1): 3, (9, '09-10', 1): 3, (10, '09-10', 1): 3
        self.ideais = {}
        
        for (day, hour, team_id), val in mins.items():
            if 1 <= day <= self.num_days:
                date_key = self.dates[day - 1]
                team_code = TEAM_ID_TO_CODE.get(team_id)
                if team_code:
                    self.minimos[(date_key, hour, team_code)] = int(val)

        """
        self.minimos = {
          (datetime(2021, 11, 1), '09-10', 'A'): -1,    # 1º dia, 09-10, equipa A → fechado
          (datetime(2021, 11, 2), '09-10', 'A'): 4,     # 2º dia, 09-10, equipa A → 4 pessoas
          (datetime(2021, 11, 3), '09-10', 'A'): 3,     # 3º dia, 09-10, equipa A → 3 pessoas
          ...
        }
        """

        #time.sleep(1000)  # para debug sequencial
        # Model variables

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

        self.closed_days = self.closed_days()

        """
        self.closed_days = {
          datetime(2021, 11, 1),  # 1 de novembro (feriado)
          datetime(2021, 11, 7),  # 7 de novembro (domingo)
        }      
        """


    def closed_days(self):
        closed_dayss = set()
        for (date_key, hora_str, team_code), minimo in self.minimos.items():
            if minimo == -1:
                closed_dayss.add(date_key)
        return closed_dayss

    def _generate_work_blocks(self):
        """
        Generate valid work blocks based on the specific combinations provided.
        Each tuple represents (start_hour, break_hour, end_hour).
        Examples:
        - (9, 13, 18): work 9-13 (4h), break 13-14, work 14-18 (4h) = 8h total
        - (9, 14, 18): work 9-14 (5h), break 14-15, work 15-18 (3h) = 8h total
        """
        blocks = [
            (9, 13, 18),   # 4h + 1h break + 4h
            (9, 14, 18),   # 5h + 1h break + 3h
            (9, 15, 18),   # 6h + 1h break + 2h
            (10, 14, 19),  # 4h + 1h break + 4h
            (10, 15, 19),  # 5h + 1h break + 3h
            (10, 16, 19),  # 6h + 1h break + 2h
            (11, 15, 20),  # 4h + 1h break + 4h
            (11, 16, 20),  # 5h + 1h break + 3h
            (11, 17, 20),  # 6h + 1h break + 2h
            (12, 16, 21),  # 4h + 1h break + 4h
            (12, 17, 21),  # 5h + 1h break + 3h
            (12, 18, 21),  # 6h + 1h break + 2h
            (13, 17, 22),  # 4h + 1h break + 4h
            (13, 18, 22),  # 5h + 1h break + 3h
            (13, 19, 22),  # 6h + 1h break + 2h
        ]
        
        return blocks

    def _get_working_hours(self, block):
        """
        Returns set of hours an employee is actually working (excluding break).
        For block (9, 13, 18): returns {9,10,11,12,14,15,16,17}
        """

        start, break_start, end = block
        hours = set(range(start, break_start))  # First period
        hours.update(range(break_start + 1, end))  # Second period (skip break hour)
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

    def choose_Employee(self, Worked_Total_Days, Worked_Week_Days, Worked_Previous_Day, emp_team_code, f):
        """
        Heuristic scoring function for employee selection.

        Higher score = higher priority for assignment next day.
        """

        # -----------------------------
        # PARAMETERS (tunable weights)
        # -----------------------------
        W_TOTAL = 0.50      # peso da equidade anual
        W_WEEK = 0.30       # peso da equidade semanal
        W_BLOCK = 0.10      # penalização por bloco crítico
        W_TEAMS = 0.10      # bónus por flexibilidade

        # -----------------------------
        # 1. TOTAL DAYS COMPONENT
        # -----------------------------
        total_days = Worked_Total_Days.get(f, 0)
        total_component = max(0.0, 1.0 - total_days / 223)

        # -----------------------------
        # 2. WEEKLY DAYS COMPONENT
        # -----------------------------
        week_days = Worked_Week_Days.get(f, 0)
        week_component = max(0.0, 1.0 - week_days / 5)

        # -----------------------------
        # 3. PREVIOUS DAY BLOCK PENALTY
        # -----------------------------
        prev_block = Worked_Previous_Day.get(f)

        # Últimos 6 blocos são os mais tardios
        critical_blocks = set(range(len(self.work_blocks) - 6, len(self.work_blocks)))

        if prev_block in critical_blocks:
            block_component = -0.3   # penalização leve
        else:
            block_component = 0.0

        # -----------------------------
        # 4. TEAM FLEXIBILITY BONUS
        # -----------------------------
        num_teams = len(emp_team_code)
        max_teams = max(len(v) for v in self.emp_team_code.values())

        if max_teams > 1:
            team_component = (num_teams - 1) / (max_teams - 1)
        else:
            team_component = 0.0

        # -----------------------------
        # FINAL SCORE
        # -----------------------------
        score = (
            W_TOTAL * total_component +
            W_WEEK * week_component +
            W_BLOCK * block_component +
            W_TEAMS * team_component
        )

        return score


    # Melhor combinacao de blocos para o dia, de forma a cobrir os minimos
    def evaluate_Day_ToBlocks(self, day, mins):
        """
        Determine the minimum multiset of blocks needed to cover all hourly minimums
        for each team independently.

        Args:
            day (datetime.date): current day
            mins (dict): {(hour, team_code): minimum_required}

        Returns:
            dict: {team_code: [block_index, block_index, ...]}
        """

        result = {team: [] for team in self.teams.keys()}

        # Pre-compute working hours for each block
        block_hours = {
            b_idx: self._get_working_hours(block)
            for b_idx, block in enumerate(self.work_blocks)
        }

        for team_code in self.teams.keys():

            # Build remaining demand for this team
            remaining = {
                h: mins.get((h, team_code), 0) # Formatação do dicionario
                for h in range(9, 22)
                if mins.get((h, team_code), 0) > 0
            }

            """
            remaining = {
              9: 4,    # Incluído (> 0)
              10: 3,   # Incluído (> 0)
              # 11 não aparece (= 0)
              14: 2    # Incluído (> 0)
            }
            """

            # Greedy covering
            while any(v > 0 for v in remaining.values()):

                best_block = None
                best_coverage = 0
                for b_idx, hours in block_hours.items():
                    coverage = sum(
                        1 for h in hours
                        if remaining.get(h, 0) > 0
                    )
                    if coverage > best_coverage:
                        best_coverage = coverage
                        best_block = b_idx

                # Safety check (infeasible day)
                if best_block is None or best_coverage == 0:
                    raise ValueError(
                        f"Infeasible coverage on {day} for team {team_code}. "
                        f"Remaining demand: {remaining}"
                    )

                # Assign block
                result[team_code].append(best_block)
                # Reduce remaining demand
                for h in block_hours[best_block]:
                    if h in remaining and remaining[h] > 0:
                        remaining[h] -= 1

        return result
    
    def _calculate_all_ranks(self, Pontuation):
        """
        Calculate ranks for all employees at once with random tie-breaking.
        This ensures consistent ranks across the same iteration.
        
        Args:
            Pontuation (dict): {Employee_ID: Pontuation_Score}
        
        Returns:
            dict: {Employee_ID: Rank}
        """
        import random
        
        # Create list of (employee_id, score, random_tiebreaker) tuples
        emp_scores = [
            (emp_id, score, random.random()) 
            for emp_id, score in Pontuation.items()
        ]
        
        # Sort by score (descending), then by random value to break ties
        emp_scores_sorted = sorted(
            emp_scores, 
            key=lambda x: (x[1], x[2]),  # Score descending, random for ties
            reverse=True
        )
        
        # Create rank dictionary
        ranks = {}
        for rank, (emp_id, _, _) in enumerate(emp_scores_sorted, start=1):
            ranks[emp_id] = rank
        
        return ranks
    
    def Pontuation_rank (self, Pontuation, employee_id):
        """
        Rank employees based on their pontuation values.
        No repeated ranks - employees with same score are ordered randomly.
        
        Args:
            Pontuation (dict): {Employee_ID: Pontuation_Score}
            employee_id (int): The employee ID to get rank for
        
        Returns:
            int: Rank of the employee (1 = highest pontuation, no ties)
        """
        import random
        
        # Create list of (employee_id, score) tuples
        emp_scores = [(emp_id, score) for emp_id, score in Pontuation.items()]
        
        # Sort by score (descending), then by random value to break ties
        emp_scores_sorted = sorted(
            emp_scores, 
            key=lambda x: (x[1], random.random()),  # Score descending, random for ties
            reverse=True
        )
        
        # Find the employee's position (1-based rank)
        for rank, (emp_id, _) in enumerate(emp_scores_sorted, start=1):
            if emp_id == employee_id:
                return rank
        
        # Should never happen, but return last rank as fallback
        return len(emp_scores_sorted)


    def build_model(self):

        """Build the Heuristic model with hourly constraints."""

        funcionarios = self.employees
        dias = self.dates
        blocos = list(range(len(self.work_blocks)))  
        # Block indices: [0, 1, 2, ..., 14] → 15 blocos
        horas = range(9, 22) # 13
        

# -------------------------------------------------------

        # Heuristica - Tracking variables (one entry per employee)
    
        Worked_Total_Days = {}      # {Employee: Total Days Worked} - incrementa por cada dia trabalhado
        Worked_Week_Days = {}       # {Employee: Days Worked this week} - reseta a cada 7 dias
        Worked_Previous_Day = {}    # {Employee: Block worked yesterday} - atualiza diariamente com bloco do dia anterior
        Pontuation = {}              # {Employee: Pontuation} - pontuacao acumulada passada do empregado

        for f in funcionarios:
            Worked_Total_Days[f] = 0        # Contador total de dias trabalhados
            Worked_Week_Days[f] = 0         # Contador semanal (0-5)
            Worked_Previous_Day[f] = None   # Bloco do dia anterior (None = não trabalhou)
            Pontuation[f] = 0               # Pontuação inicial

        for d in dias:

            if d in self.closed_days:
                continue  # Loja fechada, nenhum funcionário trabalha

            # Minimo do dia
            mins = {}
            for h in horas:
                for team_code in self.teams.keys():
                    key = (d, f"{h:02d}-{h+1:02d}", team_code)
                    if key in self.minimos:
                        mins[(h, team_code)] = self.minimos[key]
            
            # Avaliacao do dia e devolucao de um conjunto de indices de blocos a atribuir
            Block_Indexes = self.evaluate_Day_ToBlocks(d, mins)
            Nr_Emp_Needed = sum(len(blocks) for blocks in Block_Indexes.values())

            print(f"[Heuristica] Day {d}: Block Indexes to assign: {Block_Indexes}")
            print(f"[Heuristica] Day {d}: Employees needed: {Nr_Emp_Needed}")

            # Calculate all employee ranks ONCE before the loop (avoids inconsistent random ordering)
            employee_ranks = self._calculate_all_ranks(Pontuation)

            # Atribuicao dos blocos aos funcionarios
            for f in funcionarios:
                # Reset semanal a cada 7 dias (domingo)
                if d.weekday() == 0:  # Segunda-feira
                    Worked_Week_Days[f] = 0

                # Verificar se funcionário está de férias
                if d in self.vacations_dates[f]:
                    continue  # Pula para o próximo funcionário

                if len(Block_Indexes) == 0:
                    continue  # Nenhum bloco a atribuir

                if Worked_Week_Days[f] >= 5:
                    continue  # Funcionário já trabalhou 5 dias esta semana

                if Worked_Total_Days[f] >= 223:
                    continue  # Funcionário já atingiu o máximo anual de dias trabalhados

                # Get employee's rank from pre-calculated ranks
                rank = employee_ranks.get(f, len(funcionarios))
                emp_score = Pontuation.get(f, 0)

                print(f"[Heuristica] Day {d}, Emp {f}: Pontuation {emp_score:.4f}, Rank {rank}")

                if rank <= Nr_Emp_Needed:

                    Emp_Teams = self.emp_team_code[f]
                    # Ordenar equipas por número de blocos necessários (descendente)
                    teams_most_needed = sorted(
                        ((team, len(blocks)) for team, blocks in Block_Indexes.items() if team in Emp_Teams),
                        key=lambda x: x[1],
                        reverse=True
                    )

                    print(f"[Heuristica] Day {d}, Emp {f}: Teams most needed: {teams_most_needed}")

                    # teams_most_needed = [('A', 4), ('B', 3), ('C', 1)] → lista de tuplas (equipa, num_blocos)

                    if not teams_most_needed or teams_most_needed[0][1] == 0:
                        continue  # Nenhum bloco necessário para as equipas do funcionário

                    # Tentar atribuir bloco priorizando equipas com mais necessidades
                    assigned = False
                    for team_code, num_blocks in teams_most_needed:
                        if assigned:
                            break  # Já atribuiu, sair
                        
                        # Tentar cada bloco disponível desta equipa (remove após validação bem-sucedida)
                        while len(Block_Indexes[team_code]) > 0:
                            # Remove o primeiro bloco disponível para testar
                            assigned_block_idx = Block_Indexes[team_code][0]

                            print(f"[Heuristica] Day {d}, Emp {f}: Trying to assign block index {assigned_block_idx} for team {team_code}")

                            assigned_block = self.work_blocks[assigned_block_idx]

                            # Verificar transição de blocos
                            prev_block_idx = Worked_Previous_Day[f]
                            if prev_block_idx is not None:
                                prev_block = self.work_blocks[prev_block_idx]
                                if not self._validate_block_transition(prev_block, assigned_block):
                                    # Bloco inválido - remove da lista e tenta o próximo
                                    Block_Indexes[team_code].pop(0)
                                    continue

                            # Atribuição válida - remove bloco da lista
                            Block_Indexes[team_code].pop(0)
                            
                            self.assignment[f + 1].append((
                                self.dates.index(d) + 1, 
                                assigned_block_idx, 
                                get_team_id(team_code)
                            ))

                            print(f"[Heuristica] Day {d}, Emp {f}: Assigned block {assigned_block} (idx {assigned_block_idx}) for team {team_code}")

                            # sleep(1)  # Para evitar prints sobrepostos

                            # Atualizar variáveis de rastreamento
                            Worked_Total_Days[f] += 1
                            Worked_Week_Days[f] += 1
                            Worked_Previous_Day[f] = assigned_block_idx
                            assigned = True
                            break  # Bloco atribuído com sucesso


                # Atualizar pontuação 
                Pontuation[f] = self.choose_Employee(Worked_Total_Days, Worked_Week_Days, Worked_Previous_Day, self.emp_team_code[f], f)

                print(f"[Heuristica] Day {d}, Emp {f}: New Pontuation {Pontuation[f]:.4f}")
            
            print(f"[Heuristica] Day {d} completed.\n")

            sleep(0)  # Pequena pausa para clareza nos prints

        return True

#   # =========================================================

    def solve(self):
        """Execute the heuristic scheduling algorithm."""
        print(f"\n{'='*80}")
        print(f"[Heuristica] EXECUTING HEURISTIC SCHEDULER")
        print(f"{'='*80}")
        print(f"[Heuristica] Building schedule...")
        
        # Build model executes the heuristic and populates self.assignment
        self.build_model()
        
        print(f"\n[Heuristica] Schedule completed")
        print("[Heuristica] Employees with assignments:")
        for emp, assg in self.assignment.items():
            print(f"  Emp {emp}: {len(assg)} days")
        
        return True


    def export_csv(self, filename="heuristic_schedule.csv"):
        """Export heuristic schedule to CSV."""
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
        
        print(f"[Heuristica] Schedule exported to {filename}")

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
    scheduler = Heuristica(
        vacations_rows=vacations,
        minimums_rows=minimuns,
        employees=employees,
        maxTime=maxTime,
        year=year,
        store_hours=hours,
        work_blocks=work_blocks
    )

    scheduler.solve()
    scheduler.export_csv("heuristic_schedule.csv")
    
    return scheduler.to_table()



## Fazer regra de 5 dias consecutivos de trabalho
## Desenvolver kpis