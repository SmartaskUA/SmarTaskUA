import sys
import pandas as pd
import json
from kpiVerification import analyze

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

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python kpiComparison.py <file1> <file2>")
        sys.exit(1)

    holidays = [1, 107, 109, 114, 121, 161, 170, 226, 276, 303, 333, 340, 357]
    file1 = sys.argv[1]
    file2 = sys.argv[2]
    print(f"File 1: {file1}")
    print(f"File 2: {file2}")
    check_files(file1, file2)

    dataFile1 = analyze(file1, holidays)
    dataFile2 = analyze(file2, holidays)

    print(json.dumps({
        "file1": dataFile1,
        "file2": dataFile2
    }))
