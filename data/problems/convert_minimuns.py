"""
convert_minimuns.py — Convert API minimuns CSV to GA demand CSV format.

API format (wide, Portuguese date headers):
    Equipa,Tipo,Turno,1 jan,2 jan,...,31 dez
    Equipa A,Minimo,M,1,1,...
    Equipa A,Ideal,M,2,2,...
    ...

GA format (long, ISO dates):
    date,shift,team,minimum,ideal,estimated
    2025-01-01,M,A,1,2,2
    ...

Usage:
    python convert_minimuns.py <input_csv> <output_csv> [--year YEAR]

Examples:
    python convert_minimuns.py \\
        ../../src/api/src/main/resources/minimuns/minimuns_4teams_24emp.csv \\
        SMARTASK_4TEAMS_2025/demand.csv

    python convert_minimuns.py \\
        ../../src/api/src/main/resources/minimuns/minimuns_8teams_48emp.csv \\
        SMARTASK_8TEAMS_2025/demand.csv --year 2025
"""

import argparse
import csv
from datetime import date, timedelta

PT_MONTHS = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4,
    "mai": 5, "jun": 6, "jul": 7, "ago": 8,
    "set": 9, "out": 10, "nov": 11, "dez": 12,
}


def parse_date_columns(headers: list[str], year: int) -> list[date]:
    """
    Convert Portuguese date column headers ('1 jan', '2 fev', ...) to date objects.
    Skips the first 3 columns (Equipa, Tipo, Turno).
    """
    dates = []
    for h in headers[3:]:
        parts = h.strip().split()
        day   = int(parts[0])
        month = PT_MONTHS[parts[1].lower()]
        dates.append(date(year, month, day))
    return dates


def convert(input_path: str, output_path: str, year: int) -> None:
    # Read input
    with open(input_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        rows   = list(reader)

    headers   = rows[0]
    data_rows = rows[1:]
    dates     = parse_date_columns(headers, year)

    # Index rows by (team_letter, shift, tipo)
    # e.g. ("A", "M", "Minimo") -> [val_day0, val_day1, ...]
    indexed: dict[tuple, list] = {}
    for row in data_rows:
        if len(row) < 4:
            continue
        equipa, tipo, turno = row[0].strip(), row[1].strip(), row[2].strip()
        # "Equipa A" -> "A"
        team = equipa.split()[-1]
        values = [int(v) for v in row[3:]]
        indexed[(team, turno, tipo)] = values

    # Collect all (team, shift) combinations present
    combos = sorted(set((t, s) for (t, s, _) in indexed.keys()))

    # Write output
    with open(output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["date", "shift", "team", "minimum", "ideal", "estimated"])

        for d_idx, d in enumerate(dates):
            date_str = d.strftime("%Y-%m-%d")
            for team, shift in combos:
                minimum   = indexed.get((team, shift, "Minimo"),   [0] * len(dates))[d_idx]
                ideal     = indexed.get((team, shift, "Ideal"),    [0] * len(dates))[d_idx]
                estimated = indexed.get((team, shift, "Estimado"), [ideal] * len(dates))[d_idx]
                writer.writerow([date_str, shift, team, minimum, ideal, estimated])

    n_rows = len(dates) * len(combos)
    print(f"Converted {len(combos)} team-shift combinations × {len(dates)} days = {n_rows} rows")
    print(f"Teams: {sorted(set(t for t, _ in combos))}")
    print(f"Output → {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Convert API minimuns CSV to GA demand CSV.")
    parser.add_argument("input",          help="Path to API minimuns CSV")
    parser.add_argument("output",         help="Path to output demand CSV")
    parser.add_argument("--year", "-y",   type=int, default=2025, help="Year (default: 2025)")
    args = parser.parse_args()

    convert(args.input, args.output, args.year)


if __name__ == "__main__":
    main()
