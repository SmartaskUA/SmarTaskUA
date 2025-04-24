import sys
import pandas as pd
import json
from kpiVerification import analyze as singleVerification

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

def analyze(file_path, holidays):
    return singleVerification(file_path, holidays)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python kpiComparison.py <file1> <file2> [<file3> ...]")
        sys.exit(1)

    holidays = [1, 107, 109, 114, 121, 161, 170, 226, 276, 303, 333, 340, 357]
    file_paths = sys.argv[1:]

    print(f"Files to compare: {file_paths}")
    check_files(file_paths)

    results = {}
    for path in file_paths:
        print(f"Analyzing: {path}")
        results[path] = analyze(path, holidays)

    print(json.dumps(results, indent=2))
