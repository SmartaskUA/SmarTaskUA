#!/usr/bin/env python3
"""
Convert hourly minimums CSV (e.g., "09-10") into 30-minute-slot minimums CSV
(e.g., "09:00-09:30" and "09:30-10:00") by duplicating headcount values.

Assumption:
- If minimum for 09-10 is 3, then both 09:00-09:30 and 09:30-10:00 are also 3.

Preserves:
- Header row
- Weekday names row (the row after header where first 2 cells are empty)
- Column ordering

Usage:
  python3 convert_minimums_to_30min.py --in Mins_R10-R62.csv --out Mins_R10-R62_30min.csv
"""

from __future__ import annotations
import argparse
import csv
import re
from typing import List, Tuple, Optional


HOUR_RE = re.compile(r'^(\d{1,2})\s*-\s*(\d{1,2})$')


def parse_hour_range(hour_range: str) -> Tuple[int, int]:
    """Parse '09-10' or '9-10' into (9, 10)."""
    s = hour_range.strip()
    m = HOUR_RE.fullmatch(s)
    if not m:
        raise ValueError(f"Unsupported hour range format: {hour_range!r}")
    start_h = int(m.group(1))
    end_h = int(m.group(2))
    if not (0 <= start_h <= 24 and 0 <= end_h <= 24):
        raise ValueError(f"Hour out of bounds in: {hour_range!r}")
    return start_h, end_h


def to_half_hour_ranges(start_h: int, end_h: int) -> Tuple[str, str]:
    """Convert (9, 10) into ('09:00-09:30', '09:30-10:00')."""
    return (
        f"{start_h:02d}:00-{start_h:02d}:30",
        f"{start_h:02d}:30-{end_h:02d}:00",
    )


def is_weekday_row(row: List[str]) -> bool:
    """Heuristic: weekday row has first two cells empty, and some text afterwards."""
    if len(row) < 3:
        return False
    return row[0].strip() == "" and row[1].strip() == ""


def is_data_row(row: List[str]) -> bool:
    """Heuristic: data rows start with 'Equipa' in col0 and have a non-empty hour_range in col1."""
    if len(row) < 2:
        return False
    team = row[0].strip().lower()
    hour = row[1].strip()
    return team.startswith("equipa") and hour != ""


def convert(in_path: str, out_path: str) -> dict:
    with open(in_path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.reader(f))

    if not rows:
        raise ValueError("Input CSV is empty")

    header = rows[0]
    out_rows: List[List[str]] = [header]

    idx = 1
    weekday_row: Optional[List[str]] = None
    if len(rows) > 1 and is_weekday_row(rows[1]):
        weekday_row = rows[1]
        out_rows.append(weekday_row)
        idx = 2

    # Collect valid data rows, preserving original order
    data_rows = []
    for r in rows[idx:]:
        if not r or not any(c.strip() for c in r):
            continue
        if not is_data_row(r):
            continue
        data_rows.append(r)

    # Expand each hour row into two half-hour rows
    for r in data_rows:
        start_h, end_h = parse_hour_range(r[1])
        hh1, hh2 = to_half_hour_ranges(start_h, end_h)

        r1 = r.copy()
        r2 = r.copy()
        r1[1] = hh1
        r2[1] = hh2

        out_rows.append(r1)
        out_rows.append(r2)

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        csv.writer(f).writerows(out_rows)

    return {
        "weekday_row_present": weekday_row is not None,
        "input_total_rows": len(rows),
        "input_data_rows": len(data_rows),
        "output_total_rows": len(out_rows),
        "output_data_rows": len(out_rows) - (2 if weekday_row is not None else 1),
    }


def sanity_check(in_path: str, out_path: str) -> None:
    """Quick sanity check:
      - output data row count == 2 * input data row count
      - for each original (team, HH-HH+1), both half-hour rows exist and values match exactly
    """
    def read_rows(path: str):
        with open(path, newline="", encoding="utf-8-sig") as f:
            rows = list(csv.reader(f))
        header = rows[0]
        weekday = rows[1] if len(rows) > 1 and is_weekday_row(rows[1]) else None
        start = 2 if weekday is not None else 1
        data = []
        for r in rows[start:]:
            if not r or not any(c.strip() for c in r):
                continue
            if is_data_row(r):
                data.append(r)
        return header, weekday, data

    _, _, in_data = read_rows(in_path)
    _, _, out_data = read_rows(out_path)

    if len(out_data) != 2 * len(in_data):
        raise AssertionError(
            f"Row count mismatch: out_data={len(out_data)} vs expected {2*len(in_data)}"
        )

    out_map = {(r[0], r[1]): r for r in out_data}

    for r in in_data:
        team, hr = r[0], r[1]
        start_h, end_h = parse_hour_range(hr)
        hh1, hh2 = to_half_hour_ranges(start_h, end_h)
        r1 = out_map.get((team, hh1))
        r2 = out_map.get((team, hh2))
        if r1 is None or r2 is None:
            raise AssertionError(f"Missing half-hour rows for ({team}, {hr})")
        if r1[2:] != r[2:] or r2[2:] != r[2:]:
            raise AssertionError(f"Value mismatch for ({team}, {hr})")

    print("[SANITY CHECK] OK ")
    print(f"  Input data rows:  {len(in_data)}")
    print(f"  Output data rows: {len(out_data)} (expected {2*len(in_data)})")
    print("  For every original row, both half-hour rows exist and values match exactly.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="Input hourly minimums CSV")
    ap.add_argument("--out", dest="out_path", required=True, help="Output 30-min minimums CSV")
    ap.add_argument("--check", action="store_true", help="Run sanity check after conversion")
    args = ap.parse_args()

    stats = convert(args.in_path, args.out_path)

    print("[CONVERT] Done ")
    for k, v in stats.items():
        print(f"  {k}: {v}")

    if args.check:
        sanity_check(args.in_path, args.out_path)


if __name__ == "__main__":
    main()
