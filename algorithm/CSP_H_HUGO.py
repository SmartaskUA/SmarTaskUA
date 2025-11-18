import datetime
import time
import pandas as pd
from ortools.sat.python import cp_model
import numpy as np
from collections import defaultdict
import holidays as hl

from algorithm.utils import (
    rows_to_vac_dict,
    rows_to_req_dicts,
    TEAM_ID_TO_CODE,
    get_team_id,
    get_team_code,
    export_schedule_to_csv,
    build_calendar,
    schedule_to_table,
    to_table
)


def _build_allowed_teams(employees):
    """
    Convert employee 'teams' labels to internal numeric team IDs.
    Fallback to team 'A' when none provided.
    """
    allowed = []
    for Employees in employees:
        codes = [get_team_code(t) for t in Employees.get("teams", []) if t]
        ids = [get_team_id(c) for c in codes if c]
        if not ids:
            ids = [get_team_id("A")]
        allowed.append(ids)
    return allowed


def Holidays_in_year():

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
    
    return feriados_pt

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


def solve(*, vacations, minimuns, employees, maxTime=None, year=2021, hours=13, rules=None):

# ---------------------------- Dados iniciais ---------------------------- #

    num_days = 365
    n_employees = len(employees)

    print(f"Solving for {n_employees} employees over {num_days} days with {hours} working hours.")
    # Solving for 21 employees over 365 days with 13 working hours.
    print(f"Employees data sample: {employees}")
    # Employees data sample: [{'name': 'Employee 1', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 2', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 3', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 4', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 5', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 6', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 7', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 8', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 9', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 10', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 11', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 12', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 13', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 14', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 15', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 16', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 17', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 18', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 19', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 20', 'teams': ['Equipa A', 'Equipa B']}, {'name': 'Employee 21', 'teams': ['Equipa A', 'Equipa B']}]

    dates = pd.date_range(start=f"2021-11-01", end=f"2022-10-31").to_list()

    # H represents actual hours (9-22), not 1-13
    # This matches the work_blocks which use hours 9-22
    work_blocks = _generate_work_blocks(None)
    H = set()
    for (s, b, e) in work_blocks:
        H.update(range(s, b))           # manhã
        H.update(range(b+1, e))         # tarde

    H = sorted(H)   # ex: [9,10,11,12,14,15,16,17,20,21]

    Employees = range(n_employees)
    D = range(1, num_days + 1)

    #print("Building allowed teams per employee...")
    #print(f"S : {S}")
    # S : range(1, 14)
    #print(f"Employees : {Employees}")
    # Employees : range(0, 21)
    #print(f"Days : {D}")
    # Days : range(1, 366)


    for idx, emp in enumerate(employees):
        if not emp.get("teams"):
            print(f"[ERROR] Employee {idx+1} has NO teams assigned!")
            emp["teams"] = ["Equipa A"]     # fallback mínimo obrigatório

    allowed_teams_per_emp = _build_allowed_teams(employees)

    #print(f"Allowed teams per employee: {allowed_teams_per_emp}")
    # Allowed teams per employee: [[1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2], [1, 2]]

    vacs_dict = rows_to_vac_dict(vacations) 

    #print(f"Vacation dictionary: {vacs_dict}")
    # Vacation dictionary: {1: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30], 2: [31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49,

    mins_raw, ideals = rows_to_req_dicts(minimuns)

    #print(f"Minimum requirements raw data: {mins_raw}")
    # Minimum requirements raw data: ({(1, '09-10', 1): -1, (2, '09-10', 1): 4, (3, '09-10', 1): 3, (4, '09-10', 1): 2, (5, '09-10', 1): 3, (6, '09-10', 1): 4, (7, '09-10', 1): -1, (8, '09-10', 1): 3, (9, '09-10', 1): 3, (10, '09-10', 1): 3, (11, '09-10', 1): 4, (12, '09-10', 1): 4, (13, '09-10', 1): 4, (14, '09-10', 1): -1, (15, '09-10', 1): 3, (16, '09-10', 1): 3, (17, '09-10', 1): 3, (18, '09-10', 1): 3,

    min_required = {}
    # Parse requisitos: formato é (day_num, hour_str, team_id) -> valor
    for (day, hour, team_id), val in mins_raw.items():
        if 1 <= day <= num_days:
            team_code = TEAM_ID_TO_CODE.get(team_id)
            if team_code:
                try:
                    req_val = int(val)
                    min_required[(day, hour, team_code)] = req_val
                except (ValueError, TypeError):
                    pass

    #print(f"Processed minimum requirements: {min_required}")
    # Processed minimum requirements: {(Timestamp('2021-11-01 00:00:00'), '09-10', 'A'): -1, (Timestamp('2021-11-02 00:00:00'), '09-10', 'A'): 4, (Timestamp('2021-11-03 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-04 00:00:00'), '09-10', 'A'): 2, (Timestamp('2021-11-05 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-06 00:00:00'), '09-10', 'A'): 4, (Timestamp('2021-11-07 00:00:00'), '09-10', 'A'): -1, (Timestamp('2021-11-08 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-09 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-10 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-11 00:00:00'), '09-10', 'A'): 4, (Timestamp('2021-11-12 00:00:00'), '09-10', 'A'): 4, (Timestamp('2021-11-13 00:00:00'), '09-10', 'A'): 4, (Timestamp('2021-11-14 00:00:00'), '09-10', 'A'): -1, (Timestamp('2021-11-15 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-16 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-17 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-18 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-19 00:00:00'), '09-10', 'A'): 4, (Timestamp('2021-11-20 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-21 00:00:00'), '09-10', 'A'): -1, (Timestamp('2021-11-22 00:00:00'), '09-10', 'A'): 3, (Timestamp('2021-11-23 00:00:00')

    pt_holidays = Holidays_in_year()
    year = int(year) if year is not None else 2025
    sundays_holidays = [
        d for d in dates if d.weekday() == 6 or d.date() in pt_holidays
    ]

    #print(f"Calendar for year {year} built.")
    #print(f"Sundays (1-based): {sundays_1based}")
    # Sundays (1-based): [3, 10, 17, 24, 31, 38, 45, 52, 59, 66, 73, 80, 87, 94, 101, 108, 115, 122, 129, 136, 143, 150, 157, 164, 171, 178, 185, 192, 199, 206, 213, 220, 227, 234, 241, 248, 255, 262, 269, 276, 283, 290, 297, 304, 311, 318, 325, 332, 339, 346, 353, 360]

    #print(f"Days of the year: {dias_ano}")
    # Days of the year: [Timestamp('2021-01-01 00:00:00'), Timestamp('2021-01-02 00:00:00'), Timestamp('2021-01-03 00:00:00'), Timestamp('2021-01-04 00:00:00'), Timestamp('2021-01-05 00:00:00'), Timestamp('2021-01-06 00:00:00'), Timestamp('2021-01-07 00:00:00'), Timestamp('2021-01-08 00:00:00'), Timestamp('2021-01-09 00:00:00'), Timestamp('2021-01-10 00:00:00'), Timestamp('2021-01-11 00:00:00'), Timestamp('2021-01-12 00:00:00'), Timestamp('2021-01-13 00:00:00'), Timestamp('2021-01-14 00:00:00'), Timestamp('2021-01-15 00:00:00'), Timestamp('2021-01-16 00:00:00'), Timestamp('2021-01-17 00:00:00'), Timestamp('2021-01-18 00:00:00'), Timestamp('2021-01-19 00:00:00'), Timestamp('2021-01-20 00:00:00'), Timestamp('2021-01-21 00:00:00'), Timestamp('2021-01-22 00:00:00'), Timestamp('2021-01-23 00:00:00'), Timestamp('2021-01-24 00:00:00'), Timestamp('2021-01-25 00:00:00'), Timestamp('2021-01-26 00:00:00'), Timestamp('2021-01-27 00:00:00'), Timestamp('2021-01-28 00:00:00'), Timestamp('2021-01-29 00:00:00'), Timestamp('2021-01-30 00:00:00'), Timestamp('2021-01-31 00:00:00'), Timestamp('2021-02-01 00:00:00'), Timestamp('2021-02-02 00:00:00'), Timestamp('2021-02-03 00:00:00'), Timestamp('2021-02-04 00:00:00'), Timestamp('2021-02-05 00:00:00'), Timestamp('2021-02-06 00:00:00'), Timestamp('2021-02-07 00:00:00'), Timestamp('2021-02-08 00:00:00'), Timestamp('2021-02-09 00:00:00'), Timestamp('2021-02-10 00:00:00'), Timestamp('2021-02-11 00:00:00'), Timestamp('2021-02-12 00:00:00'), Timestamp('2021-02-13 00:00:00'), Timestamp('2021-02-14 00:00:00'), Timestamp('2021-02-15 00:00:00'), Timestamp('2021-02-16 00:00:00'), Timestamp('2021-02-17 00:00:00'), Timestamp('2021-02-18 00:00:00'), Timestamp('2021-02-19 00:00:00'), Timestamp('2021-02-20 00:00:00'), Timestamp('2021-02-21 00:00:00'), Timestamp('2021-02-22 00:00:00'), Timestamp('2021-02-23 00:00:00'), Timestamp('2021-02-24 00:00:00'), Timestamp('2021-02-25 00:00:00'), Timestamp('2021-02-26 00:00:00'), Timestamp('2021-02-27 00:00:00'), Timestamp('2021-02-28 00:00:00'), Timestamp('2021-03-01 00:00:00'), Timestamp('2021-03-02 00:00:00'), Timestamp('2021-03-03 00:00:00'), Timestamp('2021-03-04 00:00:00'), Timestamp('2021-03-05 00:00:00'), Timestamp('2021-03-06 00:00:00'), Timestamp('2021-03-07 00:00:00'), Timestamp('2021-03-08 00:00:00'), Timestamp('2021-03-09 00:00:00'), Timestamp('2021-03-10 00:00:00'), Timestamp('2021-03-11 00:00:00'), Timestamp('2021-03-12 00:00:00')

    start_date = dates[0]

    #print(f"Start date of the year: {start_date}")
    # Start date of the year: 2021-11-01

    # Converter sundays_holidays (lista de Timestamps) para índices 1-based (1-365)
    # sundays_holidays já contém domingos E feriados combinados
    special_days = {(d - start_date).days + 1 for d in sundays_holidays}
    # garantir special_days entre 1 e num_days
    special_days = {d for d in special_days if 1 <= d <= num_days}
    print(f"[DEBUG] special_days count (1..{num_days}): {len(special_days)}")


    #print(f"Special days (holidays + Sundays): {special_days}")
    # Special days (holidays + Sundays): {3, 262, 10, 269, 17, 276, 24, 283, 31, 545, 290, 38, 297, 554, 45, 304, 305, 52, 311, 59, 318, 66, 325, 73, 332, 592, 80, 339, 340, 342, 87, 346, 94, 353, 101, 359, 616, 360, 108, 366, 371, 115, 122, 129, 136, 650, 143, 150, 157, 164, 425, 171, 178, 185, 192, 199, 206, 469, 470, 213, 220, 227, 486, 487, 234, 241, 248, 255}

    print([(d, h, t) for (d, h, t), v in min_required.items() if v > 0 and d in special_days])
    # [(3, '09-10', 'A'), (10, '09-10', 'A'), (17, '09-10', 'A'), (24, '09-10', 'A'), (31, '09-10', 'A'), (45, '09-10', 'A'), (52, '09-10', 'A'), (59, '09-10', 'A'), (66, '09-10', 'A'), (73, '09-10', 'A'), (80, '09-10', 'A'), (87, '09-10', 'A'), (94, '09-10', 'A'), (101, '09-10', 'A'), (108, '09-10', 'A'), (115, '09-10', 'A'), (122, '09-10', 'A'), (129, '09-10', 'A'), (136, '09-10', 'A'), (143, '09-10', 'A'), (150, '09-10', 'A'), (157, '09-10', 'A'), (164, '09-10', 'A'), (171, '09-10', 'A'), (178, '09-10', 'A'), (185, '09-10', 'A'), (192, '09-10', 'A'), (199, '09-10', 'A'), (206, '09-10', 'A'), (213, '09-10', 'A'), (220, '09-10', 'A'), (227, '09-10', 'A'), (234, '09-10', 'A'), (248, '09-10', 'A'), (255, '09-10', 'A'), (262, '09-10', 'A'), (269, '09-10', 'A'), (276, '09-10', 'A'), (283, '09-10', 'A'), (290, '09-10', 'A'), (297, '09-10', 'A'), (304, '09-10', 'A'), (305, '09-10', 'A'), (311, '09-10', 'A'), (318, '09-10', 'A'), (325, '09-10', 'A'), (332, '09-10', 'A'), (339, '09-10', 'A'), (340, '09-10', 'A'), (342, '09-10', 'A'), (353, '09-10', 'A'), (359, '09-10', 'A'), (360, '09-10', 'A'), (3, '10-11', 'A'), (10, '10-11', 'A'), (17, '10-11', 'A'), (24, '10-11', 'A'), (31, '10-11', 'A'), (45, '10-11', 'A'), (52, '10-11', 'A'), (59, '10-11', 'A'), (66, '10-11', 'A'), (73, '10-11', 'A'), (80, '10-11', 'A'), (87, '10-11', 'A'), (94, '10-11', 'A'), (101, '10-11', 'A'), (108, '10-11', 'A'), (115, '10-11', 'A'), (122, '10-11', 'A'), (129, '10-11', 'A'), (136, '10-11', 'A'), (143, '10-11', 'A'), (150, '10-11', 'A'), (157, '10-11', 'A'), (164, '10-11', 'A'), (171, '10-11', 'A'), (178, '10-11', 'A'), (185, '10-11', 'A'), (192, '10-11', 'A'), (199, '10-11', 'A'), (206, '10-11', 'A'), (213, '10-11', 'A'), (220, '10-11', 'A'), (227, '10-11', 'A'), (234, '10-11', 'A'), (248, '10-11', 'A'), (255, '10-11', 'A'), (262, '10-11', 'A'), (269, '10-11', 'A'), (276, '10-11', 'A'), (283, '10-11', 'A'), (290, '10-11', 'A'), (297, '10-11', 'A'), (304, '10-11', 'A'), (305, '10-11', 'A'), (311, '10-11', 'A'), (318, '10-11', 'A'), (325, '10-11', 'A'), (332, '10-11', 'A'), (339, '10-11', 'A'), (340, '10-11', 'A'), (342, '10-11', 'A'), (353, '10-11', 'A'), (359, '10-11', 'A'), (360, '10-11', 'A'), (3, '11-12', 'A'), (10, '11-12', 'A'), (17, '11-12', 'A'), (24, '11-12', 'A'), (31, '11-12', 'A'), (45, '11-12', 'A'), (52, '11-12', 'A'), (59, '11-12', 'A'), (66, '11-12', 'A'), (73, '11-12', 'A'), (80, '11-12', 'A'), (87, '11-12', 'A'), (94, '11-12', 'A'), (101, '11-12', 'A'), (108, '11-12', 'A'), (115, '11-12', 'A'), (122, '11-12', 'A'), (129, '11-12', 'A'), (136, '11-12', 'A'), (143, '11-12', 'A'), (150, '11-12', 'A'), (157, '11-12', 'A'), (164, '11-12', 'A'), (171, '11-12', 'A'), (178, '11-12', 'A'), (185, '11-12', 'A'), (192, '11-12', 'A'), (199, '11-12', 'A'), (206, '11-12', 'A'), (213, '11-12', 'A'), (220, '11-12', 'A'), (227, '11-12', 'A'), (234, '11-12', 'A'), (248, '11-12', 'A'), (255, '11-12', 'A'), (262, '11-12', 'A'), (269, '11-12', 'A'), (276, '11-12', 'A'), (283, '11-12', 'A'), (290, '11-12', 'A'), (297, '11-12', 'A'), (304, '11-12', 'A'), (305, '11-12', 'A'), (311, '11-12', 'A'), (318, '11-12', 'A'), (325, '11-12', 'A'), (332, '11-12', 'A'), (339, '11-12', 'A'), (340, '11-12', 'A'), (342, '11-12', 'A'), (353, '11-12', 'A'), (359, '11-12', 'A'), (360, '11-12', 'A'), (3, '12-13', 'A'), (10, '12-13', 'A'), (17, '12-13', 'A'), (24, '12-13', 'A'), (31, '12-13', 'A'), (45, '12-13', 'A'), (52, '12-13', 'A'), (59, '12-13', 'A'), (66, '12-13', 'A'), (73, '12-13', 'A'), (80, '12-13', 'A'), (87, '12-13', 'A'), (94, '12-13', 'A'), (101, '12-13', 'A'), (108, '12-13', 'A'), (115, '12-13', 'A'), (122, '12-13', 'A'), (129, '12-13', 'A'), (136, '12-13', 'A'), (143, '12-13', 'A'), (150, '12-13', 'A'), (157, '12-13', 'A'), (164, '12-13', 'A'), (171, '12-13', 'A'), (178, '12-13', 'A'), (185, '12-13', 'A'), (192, '12-13', 'A'), (199, '12-13', 'A'), (206, '12-13', 'A'), (213, '12-13', 'A'), (220, '12-13', 'A'), (227, '12-13', 'A'), (234, '12-13', 'A'), (248, '12-13', 'A'), (255, '12-13', 'A'), (262, '12-13', 'A'), (269, '12-13', 'A'), (276, '12-13', 'A'), (283, '12-13', 'A'), (290, '12-13', 'A'), (297, '12-13', 'A'), (304, '12-13', 'A'), (305, '12-13', 'A'), (311, '12-13', 'A'), (318, '12-13', 'A'), (325, '12-13', 'A'), (332, '12-13', 'A'), (339, '12-13', 'A'), (340, '12-13', 'A'), (342, '12-13', 'A'), (353, '12-13', 'A'), (359, '12-13', 'A'), (360, '12-13', 'A'), (3, '13-14', 'A'), (10, '13-14', 'A'), (17, '13-14', 'A'), (24, '13-14', 'A'), (31, '13-14', 'A'), (45, '13-14', 'A'), (52, '13-14', 'A'), (59, '13-14', 'A'), (66, '13-14', 'A'), (73, '13-14', 'A'), (80, '13-14', 'A'), (87, '13-14', 'A'), (94, '13-14', 'A'), (101, '13-14', 'A'), (108, '13-14', 'A'), (115, '13-14', 'A'), (122, '13-14', 'A'), (129, '13-14', 'A'), (136, '13-14', 'A'), (143, '13-14', 'A'), (150, '13-14', 'A'), (157, '13-14', 'A')


    vac_mask = {(i, d): False for i in Employees for d in D}
    for emp_id, days in vacs_dict.items():
        i = emp_id  - 1
        for d in days:
            if 1 <= d <= num_days:
                vac_mask[(i, d)] = True

    #print(f"Vacation mask: {vac_mask}")
    # Vacation mask: {(0, 1): True, (0, 2): True, (0, 3): True, (0, 4): True, (0, 5): True, (0, 6): True, (0, 7): True, (0, 8): True, (0, 9): True, (0, 10): True, (0, 11): True, (0, 12): True, (0, 13): True, (0, 14): True, (0, 15): True, (0, 16): True, (0, 17): True, (0, 18): True, (0, 19): True, (0, 20): True, (0, 21): True, (0, 22): True, (0, 23): True, (0, 24): True, (0, 25): True, (0, 26): True, (0, 27): True, (0, 28): True, (0, 29): True, (0, 30): True, (0, 31): False, (0, 32): False, (0, 33): False, (0, 34): False, (0, 35): False, (0, 36): False, (0, 37): False, (0, 38): False, (0, 39): False, (0, 40): False, (0, 41): False, (0, 42): False, (0, 43): False, (0, 44): False, (0, 45): False, (0, 46): False, (0, 47): False, (0, 48): False, (0, 49): False, (0, 50): False, (0, 51): False, (0, 52): False, (0, 53): False, (0, 54): False, (0, 55): False, (0, 56): False, (0, 57): False, (0, 58): False, (0, 59): False, (0, 60): False, (0, 61): False, (0, 62): False, (0, 63): False, (0, 64): False, (0, 65): False, (0, 66): False, (0, 67): False, (0, 68): False, (0, 69): False, (0, 70): False, (0, 71): False, (0, 72): False, (0, 73): False, (0, 74): False, (0, 75): False, (0, 76): False, (0, 77): False, (0, 78): False, (0, 79): False, (0, 80): False, (0, 81): False, (0, 82): False, (0, 83): False, (0, 84): False, (0, 

# ---------------------------- Variáveis ---------------------------- #

    m = cp_model.CpModel()

    # variables
    y, off, hour_id = {}, {}, {}
    # Iterate over all employees and days to create the variables
    # variable y[e,d,h,t] = 1 if employee e works hour h in team t on day d (binary)
    # variable off[employee,day] = 1 if employee e is off on day d (binary)
    # variable hour_id[employee,day] = h if employee e works hour h on day d (0 if off) (integer)
    for employee in Employees:
        for day in D:
            off[(employee, day)] = m.NewBoolVar(f"off_{employee}_{day}")
            max_hour = max(H)
            hour_id[(employee, day)] = m.NewIntVar(0, max_hour, f"hour_{employee}_{day}")
            
            if not vac_mask[(employee, day)]:
                for h in H:
                    for t in allowed_teams_per_emp[employee]:
                        y[(employee, day, h, t)] = m.NewBoolVar(f"y_{employee}_{day}_{h}_{t}")

    print("Variables created.")

    for e in Employees:
        if all(vac_mask[(e,d)] for d in D):
            print(f"[WARNING] Employee {e+1} has EVERY DAY marked as vacation/off")


    for e in Employees:
        n_y = sum(1 for key in y if key[0] == e)
        print(f"employee {e+1} has {n_y} y-variables")

    # print(f"Sample variable y[0,1,1,1]: {y}")
    # (19, 175, 3, 1): y_19_175_3_1(0..1), (19, 175, 3, 2): y_19_175_3_2(0..1), (19, 175, 4, 1): y_19_175_4_1(0..1), (19, 175, 4, 2): y_19_175_4_2(0..1), (19, 175, 5, 1): y_19_175_5_1(0..1), (19, 175, 5, 2): y_19_175_5_2(0..1), (19, 175, 6, 1): y_19_175_6_1(0..1), (19, 175, 6, 2): y_19_175_6_2(0..1), (19, 175, 7, 1): y_19_175_7_1(0..1), (19, 175, 7, 2): y_19_175_7_2(0..1), (19, 175, 8, 1): y_19_175_8_1(0..1), (19, 175, 8, 2): y_19_175_8_2(0..1)
    # print(f"Sample variable off[0,1]: {off}")
    # Sample variable off[0,1]: {(0, 1): off_0_1(0..1), (0, 2): off_0_2(0..1), (0, 3): off_0_3(0..1), (0, 4): off_0_4(0..1), (0, 5): off_0_5(0..1), (0, 6): off_0_6(0..1), (0, 7): off_0_7(0..1), (0, 8): off_0_8(0..1), (0, 9): off_0_9(0..1), (0, 10): off_0_10(0..1), (0, 11): off_0_11(0..1), (0, 12): off_0_12(0..1), (0, 13): off_0_13(0..1), (0, 14): off_0_14(0..1), (0, 15): off_0_15(0..1), (0, 16): off_0_16(0..1), (0, 17): off_0_17(0..1), (0, 18): off_0_18(0..1), (0, 19): off_0_19(0..1), (0, 20): off_0_20(0..1), (0, 21): off_0_21(0..1), (0, 22): off_0_22(0..1), (0, 23): off_0_23(0..1), (0, 24): off_0_24(0..1), (0, 25): off_0_25(0..1), (0, 26): off_0_26(0..1), (0, 27): off_0_27(0..1), (0, 28): off_0_28(0..1)
    # print(f"Sample variable hour_id[0,1]: {hour_id}")
    # Sample variable hour_id[0,1]: {(0, 1): hoxur_0_1(0..13), (0, 2): hour_0_2(0..13), (0, 3): hour_0_3(0..13), (0, 4): hour_0_4(0..13), (0, 5): hour_0_5(0..13), (0, 6): hour_0_6(0..13), (0, 7): hour_0_7(0..13), (0, 8): hour_0_8(0..13), (0, 9): hour_0_9(0..13), (0, 10): hour_0_10(0..13), (0, 11): hour_0_11(0..13), (0, 12): hour_0_12(0..13), (0, 13): hour_0_13(0..13), (0, 14): hour_0_14(0..13), (0, 15): hour_0_15(0..13), (0, 16): hour_0_16(0..13), (0, 17): hour_0_17(0..13), (0, 18): hour_0_18(0..13), (0, 19): hour_0_19(0..13), (0, 20): hour_0_20(0..13), (0, 21): hour_0_21(0..13), (0, 22): hour_0_22(0..13), (0, 23): hour_0_23(0..13), (0, 24): hour_0_24(0..13), (0, 25): hour_0_25(0..13), (0, 26): hour_0_26(0..13), (0, 27): hour_0_27(0..13), (0, 28): hour_0_28(0..13), (0, 29): hour_0_29(0..13), (0, 30): hour_0_30(0..13), (0, 31): hour_0_31(0..13), (0, 32): hour_0_32(0..13)

# ---------------------------- Restrições ---------------------------- #

    for e in Employees:
        for d in D:
            if vac_mask[(e,d)]:
                continue
            if not any((e,d,h,t) in y for h in H for t in allowed_teams_per_emp[e]):
                print(f"[WARN] employee {e} day {d} has no available hours in any team")


    no_candidate_min = []
    for (day, hour_str, team), min_val in min_required.items():
        hour_num = int(hour_str.split('-')[0])
        team_id = get_team_id(team)
        cover = [ (e, day, hour_num, team_id) for e in Employees if (e, day, hour_num, team_id) in y ]
        if min_val > 0 and len(cover) == 0:
            no_candidate_min.append((day, hour_str, team, min_val))
    if no_candidate_min:
        print("[DEBUG] min_required entries with NO candidate variables (will cause infeasible):")
        print(no_candidate_min[:100])


        # DEBUG: Check if any min_required day conflicts with a special day
    conflicting_days = [
        (day, hour, team, min_required[(day, hour, team)])
        for (day, hour, team) in min_required
        if day in special_days and min_required[(day, hour, team)] > 0
    ]

    if conflicting_days:
        print("[WARNING] Found min_required on holidays/sundays:")
        for d in conflicting_days[:10]:
            print("  ", d)
        print(f"Total conflicts: {len(conflicting_days)}")
    else:
        print("[OK] No conflicting min_required days.")





    # ---------------------------------------------------------------
    #  ligação OFF <-> Y (ESSENCIAL!)
    # ---------------------------------------------------------------
    for e in Employees:
        for d in D:

            # recolhe todas as y existentes para este dia/funcionário
            active_hours = [
                y[(e, d, h, t)]
                for h in H
                for t in allowed_teams_per_emp[e]
                if (e, d, h, t) in y
            ]

            if active_hours:
                # off == 1 → todos y = 0
                m.Add(sum(active_hours) <= (1 - off[(e, d)]) * len(active_hours))

                # off == 0 → pelo menos um y = 1
                m.Add(sum(active_hours) >= 1 * (1 - off[(e, d)]))
            else:
                # zero horas = deve estar off
                m.Add(off[(e, d)] == 1)




    # Nos dias especiais, todos devem estar off
    for e in Employees:
        for d in special_days:
            m.Add(off[e, d] == 1)
            for h in H:
                for t in allowed_teams_per_emp[e]:
                    if (e, d, h, t) in y:
                        m.Add(y[e, d, h, t] == 0)

    # Nos dias de férias, todos devem estar off
    for e in Employees:
        for d in D:
            if vac_mask[(e, d)]:
                m.Add(off[e, d] == 1)
                for h in H:
                    for t in allowed_teams_per_emp[e]:
                        if (e, d, h, t) in y:  # só adiciona restrição se a variável existir
                            m.Add(y[e, d, h, t] == 0)


    # Cada funcionário tem no máximo um bloco de trabalho por dia:
    # permitir apenas blocos válidos
    for e in Employees:
        for d in D:
            valid_blocks = []
            for (start, break_start, end) in work_blocks:
                hours_in_block = [
                    y[e, d, h, t]
                    for h in _get_working_hours(None, (start, break_start, end))
                    for t in allowed_teams_per_emp[e]
                    if (e, d, h, t) in y
                ]
                if hours_in_block:
                    block_var = m.NewBoolVar(f"block_{e}_{d}_{start}")
                    for hvar in hours_in_block:
                        m.Add(hvar <= block_var)
                    valid_blocks.append(block_var)
    

    # Cover Minimum Requirements hard constraints
    for (day, hour_str, team), min_val in min_required.items():
        if min_val <= 0:
            continue
            # day is already an integer (1-365), hour_str is '09-10', team is 'A' or 'B'
        hour_num = int(hour_str.split('-')[0])
        team_id = get_team_id(team)
        print(f"[TEAM_ID] team {team} -> {team_id}")
        cover = [y[e,day,hour_num,team_id] for e in Employees if (e,day,hour_num,team_id) in y]

        if not cover:
            print("Not cover variables for min_required:", (day, hour_num, team_id, min_val, e))
            continue
        
        m.Add(sum(cover) >= min_val)
        
    # Workdays should be 223
    target_workdays = 223
    workdays = {employee: m.NewIntVar(0, target_workdays, f"work_{employee}") for employee in Employees}
    dev_under = {employee: m.NewIntVar(0, target_workdays, f"dev_under_{employee}") for employee in Employees}
    dev_over  = {employee: m.NewIntVar(0, target_workdays, f"dev_over_{employee}") for employee in Employees}
    for employee in Employees:
        m.Add(workdays[employee] == sum(1 - off[(employee, d)] for d in D))
        m.Add(workdays[employee] + dev_under[employee] - dev_over[employee] == target_workdays)

# ---------------------------- Função objetivo ---------------------------- #

    missed = []
    for (day, hour_str, team), min_val in min_required.items():
        if min_val > 0:
            hour_num = int(hour_str.split('-')[0])
            team_id = get_team_id(team)
            cover = [y[e, day, hour_num, team_id] for e in Employees if (e, day, hour_num, team_id) in y]
            if not cover:
                continue  # ignora se não há ninguém elegível
            covered = m.NewIntVar(0, n_employees, f"covered_{day}_{hour_num}_{team}")
            m.Add(covered == sum(cover))
            miss = m.NewIntVar(0, n_employees, f"miss_{day}_{hour_num}_{team}")
            m.Add(miss >= min_val - covered)
            missed.append(miss)
    # penaliza falhas de mínimos
    # m.Minimize(sum(missed))

    # O solver deve evitar missed_term, mas recompensar trabalho
    off_cost = sum(off[e, d] for e in Employees for d in D)

    m.Minimize(1000 * sum(missed) + 1 * off_cost)


# ---------------------------- Resolver modelo ---------------------------- #

    # Solve model
    # print("CHECK-OFF-Y:", "off_logic_ok" if "ACTIVE" else "off_logic_missing")
    # raise SystemExit
    solver = cp_model.CpSolver()
    if maxTime is not None:
        # maxTime is in minutes converted to seconds
        # solver.parameters.log_search_progress = True
        solver.parameters.max_time_in_seconds = float(int(maxTime) * 60)
    solver.parameters.num_search_workers = 8

    status = solver.Solve(m)

# ---------------------------- Extrair solução ---------------------------- #

    assign = defaultdict(list)
    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for employee in Employees:
            emp_id = employee + 1  # Convert 0-based index to 1-based employee ID
            for day in D:
                if solver.Value(off[(employee, day)]) == 0:
                    hour_val = solver.Value(hour_id[(employee, day)])
                    if hour_val > 0:
                        team_val = None
                        for t in allowed_teams_per_emp[employee]:
                            v = y.get((employee, day, hour_val, t))
                            if v is not None and solver.Value(v) == 1:
                                team_val = t
                                break
                        if team_val is not None:
                            # Find which block contains this hour
                            block_idx = None
                            for idx, (start, break_start, end) in enumerate(work_blocks):
                                working_hours = set(range(start, break_start))
                                working_hours.update(range(break_start + 1, end))
                                if hour_val in working_hours:
                                    block_idx = idx
                                    break
                            
                            if block_idx is not None:
                                assign[emp_id].append((day, block_idx, team_val))


# ---------------------------- Exportar e retornar tabela ---------------------------- #



    class View: pass
    v = View()
    v.employees = list(range(1, n_employees + 1))
    v.vacs = {emp_id: vacs_dict.get(emp_id, []) for emp_id in v.employees}
    v.assignment = assign
    export_schedule_to_csv(v, "schedule_cpsat.csv", num_days=num_days)

    return to_table(
        employees=v.employees,
        vacs=v.vacs,
        assignment=v.assignment,
        num_days=num_days,
        work_blocks=work_blocks
    )