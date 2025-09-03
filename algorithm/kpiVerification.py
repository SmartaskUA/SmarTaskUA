import csv
import pandas as pd
import sys
import json
import holidays as hl
import os

def analyze(file, holidays, vacs, mins, employees, year=2025):
    print(f"Analyzing file: {file}")
    df = pd.read_csv(file, encoding='ISO-8859-1')

    missed_work_days = 0
    missed_vacation_days = 0
    missed_team_min = 0
    workHolidays = 0
    consecutiveDays = 0
    total_morning = 0
    total_afternoon = 0
    total_tm_fails = 0
    single_team_violations = 0
    two_team_preference_level = {}
    balance = []
    var = 0
    percentages = []

    print(f"Year: {year}")
    print(f"Holidays: {holidays}")
    print(f"Minimuns: {mins}")
    print(f"Employees: {employees}")

    mins = parse_minimuns(mins)
    teams = parse_employees(employees)
    sunday = []
    for day in pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31'):
        if day.weekday() == 6:
            sunday.append(day.dayofyear)

    dia_cols = [col for col in df.columns if col.startswith("Dia ")]
    all_special_cols = [f'Dia {d}' for d in set(holidays).union(sunday) if f'Dia {d}' in df.columns]

    for _, row in df.iterrows():
        worked_days = sum(row[col] in ['M_A', 'T_A', 'N_A', 'M_B', 'T_B', 'N_B'] for col in dia_cols)
        vacation_days = sum(row[col] == 'F' for col in dia_cols)

        missed_work_days += abs(223 - worked_days)
        missed_vacation_days += abs(30 - vacation_days)

        total_worked_holidays = sum(row[col] in ['M_A', 'T_A', 'N_A', 'M_B', 'T_B', 'N_B'] for col in all_special_cols)
        if total_worked_holidays > 22:
            workHolidays += total_worked_holidays - 22

        work_sequence = [
            1 if row[col] in ['M_A', 'T_A', 'N_A', 'M_B', 'T_B', 'N_B'] else 0
            for col in dia_cols
        ]

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

        tm_fails = 0
        order = {
            'M_A': 1, 'M_B': 1,
            'T_A': 2, 'T_B': 2,
            'N_A': 3, 'N_B': 3,
        }
        for i in range(len(dia_cols) - 1):
            today = row[dia_cols[i]]
            tomorrow = row[dia_cols[i + 1]]

            t_ord = order.get(today)
            n_ord = order.get(tomorrow)

            # Count a fail if both are working shifts and tomorrow is "earlier" than today
            if t_ord is not None and n_ord is not None and n_ord < t_ord:
                tm_fails += 1

        total_tm_fails += tm_fails

        emp_id = row['funcionario']
        allowed_teams = teams.get(emp_id, [])
        team_counts = {1: 0, 2: 0}

        for col in dia_cols:
            shift_val = row[col]
            if shift_val in ['M_A', 'T_A', 'N_A']:
                team = 1
            elif shift_val in ['M_B', 'T_B', 'N_B']:
                team = 2
            else:
                continue
            team_counts[team] += 1

        if len(allowed_teams) == 1:
            allowed_team = allowed_teams[0]
            other_team = 2 if allowed_team == 1 else 1
            if team_counts[other_team] > 0:
                single_team_violations += 1
        elif len(allowed_teams) == 2:
            teamA_shifts = sum(row[col] in ['M_A', 'T_A'] for col in dia_cols)
            teamB_shifts = sum(row[col] in ['M_B', 'T_B'] for col in dia_cols)
            if (allowed_teams[0] == 1):
                print(f"Team A shifts: {teamA_shifts}, Team B shifts: {teamB_shifts}")
                balance.append(round(teamA_shifts / (teamB_shifts + teamA_shifts), 4)*100)
            else:
                print(f"Team B shifts: {teamB_shifts}, Team A shifts: {teamA_shifts}")
                balance.append(round(teamB_shifts / (teamB_shifts + teamA_shifts), 4)*100)

        total_morning += sum(row[col] in ['M_A', 'M_B'] for col in dia_cols)
        total_afternoon += sum(row[col] in ['T_A', 'T_B'] for col in dia_cols)

        total_shifts = total_morning + total_afternoon
        if total_shifts > 0:
            morning_percentage = (total_morning / total_shifts) * 100
            afternoon_percentage = (total_afternoon / total_shifts) * 100
            print(f"Morning percentage: {morning_percentage:.2f}%, Afternoon percentage: {afternoon_percentage:.2f}%")
            print(min(morning_percentage, afternoon_percentage))
            percentages.append(min(morning_percentage, afternoon_percentage))


    for i in range(len(balance)):
        var += balance[i]
    if balance:
        two_team_preference_level = round(var / len(balance), 2)
    else:
        two_team_preference_level = 0

    print(percentages)
    shift_balance = min(percentages) if percentages else 0

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

    for (day, team_label, shift), required in mins.items():
        col = f"Dia {day}"
        if col not in df.columns:
            continue

        code = givenShift(team_label, shift)
        assigned = (df[col] == code).sum()

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
        "shiftBalance": round(shift_balance, 2),
        "twoTeamPreferenceLevel": two_team_preference_level,
    }

def parse_minimuns(minimums):
    minimos = {}
    team_map = {"Equipa A": "A", "Equipa B": "B"}
    shift_map = {"M": 1, "T": 2, "N": 3}

    minimums = minimums.replace('\r\n', '\n').replace('\r', '\n').strip()
    lines = minimums.split('\n')
    print(f"Raw input (first 100 chars): {minimums[:100]}")
    print(f"Total lines after split: {len(lines)}")

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
        team, req_type, shift = parts[0], parts[1], parts[2]
        if req_type != "Minimo":
            continue
        values = parts[3:]
        if len(values) < 365:
            continue
        team_label = team_map.get(team)
        shift_num = shift_map.get(shift)
        if not team_label or not shift_num:
            continue
        for day, value in enumerate(values[:365], 1):  # Use only first 365 values
            try:
                minimos[(day, team_label, shift_num)] = int(value)
            except ValueError:
                continue
    return minimos

def parse_employees(employees):
    teams = {}
    team_map = {"Equipa A": 1, "Equipa B": 2}
    if isinstance(employees, str):
        employees = json.loads(employees)

    for emp in employees:
        emp_name = emp["name"]
        emp_id = int(emp_name.split(' ')[1])
        emp_teams = [team_map[team] for team in emp["teams"] if team in team_map]
        teams[emp_id] = emp_teams
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
    data = analyze(file, holidays, teams, ano)
    print(json.dumps(data, indent=4))