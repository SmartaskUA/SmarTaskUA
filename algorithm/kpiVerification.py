import csv
import pandas as pd
import sys
import json
import holidays as hl
import os

def analyze(file, holidays, teams, vacs, minus, employees, year=2025):
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

    minimuns_file = os.path.join(os.path.dirname(__file__), "minimuns.csv")
    mins = parse_requirements(minimuns_file)
    sunday = []
    for day in pd.date_range(start=f'{year}-01-01', end=f'{year}-12-31'):
        if day.weekday() == 6:
            sunday.append(day.dayofyear)

    dia_cols = [col for col in df.columns if col.startswith("Dia ")]
    all_special_cols = [f'Dia {d}' for d in set(holidays).union(sunday) if f'Dia {d}' in df.columns]

    for _, row in df.iterrows():
        worked_days = sum(row[col] in ['M_A', 'T_A', 'M_B', 'T_B'] for col in dia_cols)
        vacation_days = sum(row[col] == 'F' for col in dia_cols)

        missed_work_days += abs(223 - worked_days)
        missed_vacation_days += abs(30 - vacation_days)

        total_worked_holidays = sum(row[col] in ['M_A', 'T_A', 'M_B', 'T_B'] for col in all_special_cols)
        if total_worked_holidays > 22:
            workHolidays += total_worked_holidays - 22

        work_sequence = [
            1 if row[col] in ['M_A', 'T_A', 'M_B', 'T_B'] else 0
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
        for i in range(len(dia_cols) - 1):
            today = row[dia_cols[i]]
            tomorrow = row[dia_cols[i + 1]]
            if today in ['T_A', 'T_B'] and tomorrow in ['M_A', 'M_B']:
                tm_fails += 1

        total_tm_fails += tm_fails

        emp_id = row['funcionario']
        allowed_teams = teams.get(emp_id, [])
        team_counts = {1: 0, 2: 0}

        for col in dia_cols:
            shift_val = row[col]
            if shift_val in ['M_A', 'T_A']:
                team = 1
            elif shift_val in ['M_B', 'T_B']:
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
        prefix = "M" if shift == 1 else "T"
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

def parse_requirements(file_path):
    minimos = {}
    with open(file_path, newline='') as f:
        reader = list(csv.reader(f))
        dias_colunas = list(range(1, len(reader[0]) - 3 + 1)) 

        linhas_requisitos = {
            ("A", 1, "Minimo"): 1,
            ("A", 2, "Minimo"): 3,
            ("B", 1, "Minimo"): 5,
            ("B", 2, "Minimo"): 7 
        }

        for (equipa, turno, tipo), linha_idx in linhas_requisitos.items():
            valores = reader[linha_idx][3:]
            for dia, valor in zip(dias_colunas, valores):
                try:
                    valor_int = int(valor)
                    if tipo == "Minimo":
                        minimos[(dia, equipa, turno)] = valor_int
                except ValueError:
                    continue 

    return minimos

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