import csv
import pandas as pd
import sys
import json
import holidays as hl
import os
import re

def analyze(file, holidays, mins, employees, year=2025):
    print(f"Analyzing file: {file}")
    df = pd.read_csv(file, encoding='ISO-8859-1')

    # --- helpers -------------------------------------------------------------
    def parse_shift(val):
        """Return (prefix, team) if val matches 'M_X'/'T_X'/'N_X', else (None, None)."""
        if not isinstance(val, str):
            return (None, None)
        m = re.match(r'^\s*([MTN])\s*_\s*([A-Za-z])\s*$', val)
        if m:
            return (m.group(1), m.group(2).upper())
        return (None, None)

    def is_work_shift(val):
        p, _ = parse_shift(val)
        return p in {'M', 'T', 'N'}

    # ------------------------------------------------------------------------

    missed_work_days = 0
    missed_vacation_days = 0
    missed_team_min = 0
    workHolidays = 0
    consecutiveDays = 0
    total_tm_fails = 0
    single_team_violations = 0
    two_team_balance_values = []   # keeps % on first of two allowed teams (legacy metric)
    per_employee_shift_balance = []  # min(M%, T%) per employee

    print(f"Year: {year}")
    print(f"Holidays: {holidays}")
    print(f"Minimuns: {mins}")
    print(f"Employees: {employees}")

    mins = parse_minimuns(mins)
    teams = parse_employees(employees)

    # Sundays of the given year (day-of-year numbers)
    sunday = []
    for day in pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31'):
        if day.weekday() == 6:
            sunday.append(day.dayofyear)

    dia_cols = [col for col in df.columns if col.startswith("Dia ")]
    all_special_cols = [f'Dia {d}' for d in set(holidays).union(sunday) if f'Dia {d}' in df.columns]

    # order of shifts during a day for TM fail detection
    shift_order = {'M': 1, 'T': 2, 'N': 3}

    for _, row in df.iterrows():
        # Work/vacation counting (generic)
        worked_days  = sum(is_work_shift(row[col]) for col in dia_cols)
        vacation_days = sum(str(row[col]).strip() == 'F' for col in dia_cols)

        missed_work_days += abs(223 - worked_days)
        missed_vacation_days += abs(30 - vacation_days)

        # Worked holidays/sundays (generic)
        total_worked_holidays = sum(is_work_shift(row[col]) for col in all_special_cols)
        if total_worked_holidays > 22:
            workHolidays += total_worked_holidays - 22

        # 6+ consecutive days worked
        work_sequence = [1 if is_work_shift(row[col]) else 0 for col in dia_cols]
        streak = 0
        fails = 0
        for day in work_sequence:
            if day == 1:
                streak += 1
                if streak >= 6:
                    fails += 1
            else:
                streak = 0
        consecutiveDays += fails

        # Tomorrow earlier than today (TM fails) — compare by M<T<N
        tm_fails = 0
        for i in range(len(dia_cols) - 1):
            p_today, _ = parse_shift(row[dia_cols[i]])
            p_tomorrow, _ = parse_shift(row[dia_cols[i + 1]])
            if p_today in shift_order and p_tomorrow in shift_order:
                if shift_order[p_tomorrow] < shift_order[p_today]:
                    tm_fails += 1
        total_tm_fails += tm_fails

        # Allowed teams for employee
        emp_id = row['funcionario']
        allowed_codes = teams.get(emp_id, [])  # e.g. ["A"], ["A","B"], ["B","C","D"], ...

        # Count assignments per team actually present in the row
        team_counts = {}
        for col in dia_cols:
            pfx, code = parse_shift(row[col])
            if pfx and code:
                team_counts[code] = team_counts.get(code, 0) + 1

        # Single-team violation: employee allowed only 1 code but worked others
        if len(allowed_codes) == 1:
            allowed = set(allowed_codes)
            worked_codes = set(team_counts.keys())
            other_work = worked_codes - allowed
            if other_work:
                single_team_violations += 1

        # Legacy metric: when exactly 2 allowed teams, compute % on the first team
        elif len(allowed_codes) >= 2:
            # count only shifts worked on allowed codes
            denom = sum(team_counts.get(code, 0) for code in allowed_codes)
            if denom > 0:
                percs = {
                    code: round((team_counts.get(code, 0) / denom) * 100.0, 2)
                    for code in allowed_codes
                }

                # Back-compat: keep pushing the % on the *first* allowed team
                primary = allowed_codes[0]
                two_team_balance_values.append(percs.get(primary, 0.0))

                # Optional: print a compact breakdown for diagnostics
                breakdown = ", ".join(f"{code}={percs[code]}%" for code in allowed_codes)
                print(f"{emp_id}: {breakdown}")

    # Per-employee shift balance (adapts to 2 or 3 shifts; best possible = 50)
    emp_morning  = sum(parse_shift(row[col])[0] == 'M' for col in dia_cols)
    emp_afternoon = sum(parse_shift(row[col])[0] == 'T' for col in dia_cols)
    emp_night    = sum(parse_shift(row[col])[0] == 'N' for col in dia_cols)

    total_emp_shifts_all = emp_morning + emp_afternoon + emp_night
    if total_emp_shifts_all > 0:
        morning_pct_all   = (emp_morning  / total_emp_shifts_all) * 100.0
        afternoon_pct_all = (emp_afternoon / total_emp_shifts_all) * 100.0
        night_pct_all     = (emp_night    / total_emp_shifts_all) * 100.0

        # Only consider shifts the employee actually worked (non-zero).
        pcts = [p for p in [morning_pct_all, afternoon_pct_all, night_pct_all] if p > 0]
        active_shifts = len(pcts)

        if active_shifts >= 2:
            min_pct = min(pcts)
            ideal_min = 100.0 / active_shifts        # 50.0 for 2 shifts, 33.333... for 3 shifts
            scale = 50.0 / ideal_min                 # maps ideal_min -> 50
            balanced_score = min(50.0, min_pct * scale)
        else:
            balanced_score = 0.0

        per_employee_shift_balance.append(balanced_score)


    # Aggregate legacy two-team balance metric
    if two_team_balance_values:
        two_team_preference_level = round(sum(two_team_balance_values) / len(two_team_balance_values), 2)
    else:
        two_team_preference_level = 0

    print(per_employee_shift_balance)
    shift_balance = round(min(per_employee_shift_balance), 2) if per_employee_shift_balance else 0

    def givenShift(team_label, shift):
        if shift == 1:
            prefix = "M"
        elif shift == 2:
            prefix = "T"
        elif shift == 3:
            prefix = "N"
        else:
            return None  # unknown shift; skip
        return f"{prefix}_{team_label}"

    # Minimums compliance (generic for any team code)
    for (day, team_label, shift), required in mins.items():
        col = f"Dia {day}"
        if col not in df.columns:
            continue
        code = givenShift(team_label, shift)
        if not code:
            continue
        assigned = sum(str(v).strip().upper() == code for v in df[col])
        missing = max(0, required - assigned)
        missed_team_min += int(missing)

    return {
        "missedWorkDays": missed_work_days,
        "missedVacationDays": missed_vacation_days,
        "workHolidays": workHolidays,
        "tmFails": total_tm_fails,
        "consecutiveDays": consecutiveDays,
        "singleTeamViolations": single_team_violations,
        "missedTeamMin": missed_team_min,
        "shiftBalance": shift_balance,
        "twoTeamPreferenceLevel": two_team_preference_level,  # kept for backward compatibility
    }

def parse_minimuns(minimums):
    """
    Returns dict[(day:int, team_code:str, shift:int) -> int]
    team_code is 'A','B','C',...
    shift: 1=M, 2=T, 3=N
    """
    minimos = {}
    shift_map = {"M": 1, "T": 2, "N": 3}

    minimums = minimums.replace('\r\n', '\n').replace('\r', '\n').strip()
    lines = minimums.split('\n')
    print(f"Raw input (first 100 chars): {minimums[:100]}")
    print(f"Total lines after split: {len(lines)}")

    # If a single huge CSV line slipped in, re-chunk by 368 cols (header+365 days+meta)
    if len(lines) == 1 and ',' in lines[0]:
        parts = lines[0].split(',')
        if len(parts) >= 368:
            lines = [','.join(parts[i:i+368]) for i in range(0, len(parts), 368)]

    for line_num, line in enumerate(lines, 1):
        line = line.strip()
        if not line:
            continue
        parts = line.split(',')
        if len(parts) < 4:
            continue

        team_label_raw, req_type, shift_code = parts[0].strip(), parts[1].strip(), parts[2].strip().upper()
        if req_type != "Minimo":
            continue

        # 'Equipa X' -> 'X' (last char)
        if not team_label_raw:
            continue
        team_code = team_label_raw.strip()[-1].upper()
        if not team_code.isalpha():
            continue

        shift_num = shift_map.get(shift_code)
        if not shift_num:
            continue

        values = parts[3:]
        if len(values) < 365:
            continue

        for day, value in enumerate(values[:365], 1):
            v = value.strip()
            if v:
                try:
                    minimos[(day, team_code, shift_num)] = int(v)
                except ValueError:
                    pass
    return minimos

def parse_employees(employees):
    """
    Returns dict[int -> list[str team_codes]]
    Example: { 5: ["A","B"], 7: ["C"] }
    """
    teams = {}
    if isinstance(employees, str):
        employees = json.loads(employees)

    for emp in employees:
        emp_name = emp["name"]
        emp_id = int(emp_name.split(' ')[1])

        codes = []
        for t in emp.get("teams", []):
            t = str(t).strip()
            if not t:
                continue
            codes.append(t[-1].upper())  # 'Equipa X' -> 'X'
        # de-dup while preserving order
        seen = set()
        codes = [c for c in codes if not (c in seen or seen.add(c))]
        teams[emp_id] = codes
    return teams


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python kpiVerification.py <file>")
        sys.exit(1)
    ano = 2026
    holidays = hl.country_holidays("PT", years=[ano])
    dias_ano = pd.date_range(start=f'{ano}-01-01', end=f'{ano}-12-31').to_list()
    start_date = dias_ano[0].date()
    holidays = {(d - start_date).days + 1 for d in holidays}
    file = sys.argv[1]
    teams = {
        1: [1], 2: [1], 3: [1], 4: [1],
        5: [1, 2], 6: [1, 2], 7: [1], 8: [1],
        9: [1], 10: [2], 11: [2, 1], 12: [2]
    }
    data = analyze(file=file, holidays=holidays, mins=minimums_text, employees=employees_json, year=ano)
    print(json.dumps(data, indent=4))