import sys
import traceback
import pandas as pd
import json
import datetime
from algorithm.kpiVerification_Hours import analyze as singleVerification
#import holidays as hl

def check_files(file_paths):
    headers = []
    for path in file_paths:
        with open(path, 'r') as f:
            header = f.readline().strip().split(',')
            headers.append(header)

    first = headers[0]
    for i, header in enumerate(headers[1:], start=1):
        if len(header) != len(first):
            print(f"File {file_paths[i]} has a different number of columns: {len(header)} vs {len(first)}")
            sys.exit(1)

    if any("Dia 1" not in h for h in headers):
        print("Wrong header format")
        sys.exit(1)

def analyze(file_path, holidays, minus="", employees="[]", year=2021):
    return singleVerification(file_path, holidays, minus, employees, year)


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python kpiComparison.py <file1> <file2> [<file3> ...]")
        sys.exit(1)

    ano = 2021
    holidays = {
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
    dias_ano = pd.date_range(start=f'{ano}-11-01', end=f'{ano+1}-10-31').to_list()
    start_date = dias_ano[0].date()
    holidays = {(d - start_date).days + 1 for d in holidays}
    file_paths = sys.argv[1:]

    print(f"Files to compare: {file_paths}")
    check_files(file_paths)

    results = {}
    for path in file_paths:
        print(f"Analyzing: {path}")
        try:
            results[path] = analyze(path, holidays, "", "[]", 2021)
        except Exception as e:
            print(f"[Comparison] Error: {e}")
            traceback.print_exc()

    print(json.dumps(results, indent=2))
