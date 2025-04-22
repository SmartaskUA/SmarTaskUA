import sys
import pandas as pd
import json

def check_files(file1, file2):
    with open(file1, 'r') as f1, open(file2, 'r') as f2:
        header1 = f1.readline().strip().split(',')
        header2 = f2.readline().strip().split(',')

    if len(header1) != len(header2):
        print(f"Files have different number of columns: {len(header1)} - {len(header2)}")
        sys.exit(1)
    if file1 == file2:
        print("Files are the same")
        sys.exit(1)
    if "Dia 1" not in header1 and "Dia 1" not in header2:
        print("Wrong header format")
        sys.exit(1)


def analyze(file, holidays):
    df = pd.read_csv(file)
    missed_work_days = 0
    missed_vacation_days = 0
    missed_team_min = 0
    workHolidays = 0
    consecutiveDays = 0
    holiday_cols = [f'Dia {d}' for d in holidays if f'Dia {d}' in df.columns]
    for _, row in df.iterrows():
        worked_days = int(row['Dias Trabalhados'])
        vacation_days = int(row['Dias de Férias'])

        missed_work_days += abs(223 - worked_days)
        missed_vacation_days += abs(30 - vacation_days)

        numHolidays = sum(row[col] in ['M_A', 'T_A', 'M_B', 'T_B'] for col in holiday_cols)
        if numHolidays > 22:
            workHolidays += numHolidays - 22

        work_sequence = [
            1 if row[col] in ['M_A', 'T_A', 'M_B', 'T_B'] else 0
            for col in df.columns if col.startswith("Dia ")
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


    for col in df.columns:
        if col.startswith('Dia'):
            M_A = sum(row[col] == 'M_A' for _, row in df.iterrows())
            T_A = sum(row[col] == 'T_A' for _, row in df.iterrows())
            M_B = sum(row[col] == 'M_B' for _, row in df.iterrows())
            T_B = sum(row[col] == 'T_B' for _, row in df.iterrows())
            if M_A < 2:
                missed_team_min += 1
            if T_A < 2:
                missed_team_min += 1
            if M_B < 1:
                missed_team_min += 1
            if T_B < 1:
                missed_team_min += 1
            

    return {
        "missedWorkDays": missed_work_days,
        "missedVacationDays": missed_vacation_days,
        "missedTeamMin": missed_team_min,
        "workHolidays": workHolidays,
        "consecutiveDays": consecutiveDays
    }

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python kpiComparison.py <file1> <file2>")
        sys.exit(1)

    holidays = [1, 107, 109, 114, 121, 161, 170, 226, 276, 303, 333, 340, 357]
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    check_files(file1, file2)

    dataFile1 = analyze(file1, holidays)
    dataFile2 = analyze(file2, holidays)


    print(json.dumps({
        "file1": dataFile1,
        "file2": dataFile2
    }))
