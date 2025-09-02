import csv
import os
from datetime import date
import pandas as pd

TEAM_LETTER_TO_ID = {'A': 1, 'B': 2}

def build_calendar(year: int):
    """
    Returns:
      dias_ano: list[pd.Timestamp] for every day of the given year
      sundays:  list[int] day-of-year indices (1..365/366) that fall on Sunday
    """
    dias_ano = pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31').to_list()
    sundays = [d.dayofyear for d in dias_ano if d.weekday() == 6]  # Monday=0 ... Sunday=6
    return dias_ano, sundays

def parse_vacs_file(file_path: str):
    """
    CSV format: rows like 'Employee 1,0,1,0,...'
    Returns: dict[int, list[int]] -> {emp_id: [day_numbers_with_vacation]}
    """
    vacs = {}
    with open(file_path, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if row and row[0].startswith("Employee"):
                emp_id = int(row[0].split()[1])
                vacs[emp_id] = [i + 1 for i, val in enumerate(row[1:]) if val.strip() == "1"]
    return vacs

def rows_to_vac_dict(vac_rows):
    """
    vac_rows: rows like ['Employee 3', '0','1','0',...]
    Returns: {emp_id: [day_numbers]}
    """
    vacs = {}
    for row in vac_rows:
        emp_id = int(row[0].split()[-1])
        vacs[emp_id] = [
            idx + 1
            for idx, bit in enumerate(row[1:])
            if bit.strip() == '1'
        ]
    return vacs

# -----------------------------
# Requirements parsing
# -----------------------------

def parse_requirements_file(file_path: str):
    """
    Reads a fixed 8-row CSV layout and returns mins/ideals using
    normalized keys: (day:int, shift:int [1=M,2=T], team:int [1=A,2=B])

    Expected row indices (after header row):
      1:  A, M, Minimo
      2:  A, M, Ideal
      3:  A, T, Minimo
      4:  A, T, Ideal
      5:  B, M, Minimo
      6:  B, M, Ideal
      7:  B, T, Minimo
      8:  B, T, Ideal
    We only read the numeric day columns starting at col index 3.
    """
    from .utils import TEAM_LETTER_TO_ID 

    mins, ideals = {}, {}
    with open(file_path, newline='', encoding='ISO-8859-1') as f:
        rows = list(csv.reader(f))
        # day columns are after the first 3 meta columns
        day_indices = list(range(1, len(rows[0]) - 3 + 1))

        layout = {
            ("A", 1, "Minimo"): 1,
            ("A", 1, "Ideal"):  2,
            ("A", 2, "Minimo"): 3,
            ("A", 2, "Ideal"):  4,
            ("B", 1, "Minimo"): 5,
            ("B", 1, "Ideal"):  6,
            ("B", 2, "Minimo"): 7,
            ("B", 2, "Ideal"):  8,
        }

        for (team_letter, shift, kind), row_idx in layout.items():
            values = rows[row_idx][3:]  # numeric day columns
            team_id = TEAM_LETTER_TO_ID[team_letter]
            for day, val in zip(day_indices, values):
                try:
                    n = int(val)
                except (ValueError, TypeError):
                    continue
                key = (day, shift, team_id)  # <-- (day, shift, team_id)
                (mins if kind.lower().startswith('min') else ideals)[key] = n

    return mins, ideals

def rows_to_req_dicts(req_rows):
    """
    req_rows: iterable of rows like:
      ['Team_A', 'Minimum', 'M', <day1>, <day2>, ...]
      ['Team_B', 'Ideal',   'T', <day1>, <day2>, ...]
    Returns:
      mins, ideals where keys are (day, shift, team_id).
    """
    mins, ideals = {}, {}
    for row in req_rows:
        team_label, kind, shift_code, *counts = row
        team_id = TEAM_LETTER_TO_ID[team_label[-1]]  # 'Team_A' or 'A' => 'A' is last
        shift = 1 if shift_code.strip().upper() == 'M' else 2
        target = mins if kind.lower().startswith('min') else ideals
        for day, value in enumerate(counts, start=1):
            if value.strip():
                target[(day, shift, team_id)] = int(value)
    return mins, ideals

def export_schedule_to_csv(scheduler, filename="schedule.csv", num_days=365):
    """
    Writes a wide CSV: one row per employee, one column per day.
    Values: 'F', 'M_A'/'M_B', 'T_A'/'T_B', or '0'
    """
    header = ["funcionario"] + [f"Dia {i+1}" for i in range(num_days)]
    with open(filename, mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)

        for emp in scheduler.employees:
            row = [emp]
            day_assignments = {day: (shift, team) for (day, shift, team) in scheduler.assignment[emp]}
            vacation_days = set(scheduler.vacs.get(emp, []))

            for day_num in range(1, num_days + 1):
                if day_num in vacation_days:
                    row.append("F")
                elif day_num in day_assignments:
                    shift, team = day_assignments[day_num]
                    row.append(("M_" if shift == 1 else "T_") + ("A" if team == 1 else "B"))
                else:
                    row.append("0")
            writer.writerow(row)
    print(f"Schedule exported to {filename}")
