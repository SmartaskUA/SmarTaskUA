"""
Vacation Template Generator
---------------------------
This script automatically creates *4 vacation scheduling cases* for any number of employees.
Each employee gets exactly **30 vacation days per year**, distributed according to different rules.

It outputs:
- One CSV per case with 0/1 daily schedule per employee (1 = vacation day)
- One CSV per case with per-month, per-week, and per-weekday statistics

Output structure:
VacationData/{employee_count}_employees/
    ├── templates/
    │     ├── VacationTemplate_Case1_X.csv
    │     ├── VacationTemplate_Case2_X.csv
    │     ├── VacationTemplate_Case3_X.csv
    │     └── VacationTemplate_Case4_X.csv
    └── statistics/
          ├── VacationStatistics_Case1_X.csv
          └── ...

Cases:
  1️⃣ Sequential 30-day rotation across the year
  2️⃣ Two random 15-day blocks per employee (non-overlapping)
  3️⃣ Same as Case 2, but biased around Tue/Thu holidays (long weekends)
  4️⃣ Summer-focused (June–August), still 30 days per employee
"""

import os
import pandas as pd
import numpy as np
import holidays


# =========================================================
# 📦 Utility Functions
# =========================================================

def ensure_dirs(base_dir, employee_count):
    """
    Ensure the folder structure exists for saving templates and stats.

    Example output path:
      VacationData/96_employees/templates/
      VacationData/96_employees/statistics/
    """
    base = os.path.join(base_dir, f"{employee_count}_employees")
    templates_dir = os.path.join(base, "templates")
    stats_dir = os.path.join(base, "statistics")

    os.makedirs(templates_dir, exist_ok=True)
    os.makedirs(stats_dir, exist_ok=True)

    return templates_dir, stats_dir


def _wrap_day(d, days_per_year):
    """Ensure day numbers wrap correctly (e.g., 366 → 1)."""
    return ((d - 1) % days_per_year) + 1


def _block_days(start_day, length, days_per_year):
    """Return `length` consecutive days, wrapping at year-end if necessary."""
    return [_wrap_day(start_day + k, days_per_year) for k in range(length)]


def _non_overlapping_two_blocks(days_per_year, rng):
    """
    Randomly generate two 15-day vacation periods that do NOT overlap.
    Used in Case 2 and Case 3.
    """
    start1 = rng.integers(1, days_per_year - 14)
    block1 = set(_block_days(start1, 15, days_per_year))

    valid_starts = [
        s for s in range(1, days_per_year - 14)
        if set(_block_days(s, 15, days_per_year)).isdisjoint(block1)
    ]

    if not valid_starts:
        valid_starts = [1]  # fallback, extremely rare
    start2 = int(rng.choice(valid_starts))
    return start1, start2


def _stats_from_schedule(vacation_schedule):
    """
    Compute vacation summary stats:
      - total vacation days
      - per-month distribution
      - per-week distribution
      - per-weekday distribution
    """
    days_per_year = len(vacation_schedule)
    num_weeks = (days_per_year // 7) + (1 if days_per_year % 7 else 0)
    month_lengths = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    per_month = [0] * 12
    per_weekday = [0] * 7
    per_week = [0] * num_weeks

    cur = 1
    for m_idx, m_len in enumerate(month_lengths):
        for day in range(cur, cur + m_len):
            if vacation_schedule[day - 1]:
                per_month[m_idx] += 1
                per_weekday[(day - 1) % 7] += 1
                per_week[(day - 1) // 7] += 1
        cur += m_len

    return sum(vacation_schedule), per_month, per_weekday, per_week


# =========================================================
# 🧩 CASE 1 – Sequential 30-day rotation
# =========================================================
def generate_case1(employee_count, days_per_year=365):
    """
    Every employee takes 30 consecutive days off,
    one after another, cycling through the year.
    """
    vacation_data, vacation_stats = {}, {}
    start_day = 1

    for emp_id in range(1, employee_count + 1):
        days = _block_days(start_day, 30, days_per_year)
        schedule = [1 if i + 1 in days else 0 for i in range(days_per_year)]

        total, per_month, per_weekday, per_week = _stats_from_schedule(schedule)
        vacation_data[f"Employee {emp_id}"] = schedule
        vacation_stats[emp_id] = {
            "total_vacation_days": total,
            "vacation_per_month": per_month,
            "vacation_per_weekday": per_weekday,
            "vacation_per_week": per_week,
        }

        # Next employee’s vacation starts right after previous one
        start_day = (start_day + 30) % days_per_year or 1

    return vacation_data, vacation_stats


# =========================================================
# 🧩 CASE 2 – Two random 15-day blocks
# =========================================================
def generate_case2(employee_count, days_per_year=365, seed=42):
    """Two random, non-overlapping 15-day periods per employee."""
    rng = np.random.default_rng(seed)
    vacation_data, vacation_stats = {}, {}

    for emp_id in range(1, employee_count + 1):
        s1, s2 = _non_overlapping_two_blocks(days_per_year, rng)
        days = set(_block_days(s1, 15, days_per_year)) | set(_block_days(s2, 15, days_per_year))
        schedule = [1 if i + 1 in days else 0 for i in range(days_per_year)]

        total, per_month, per_weekday, per_week = _stats_from_schedule(schedule)
        vacation_data[f"Employee {emp_id}"] = schedule
        vacation_stats[emp_id] = {
            "total_vacation_days": total,
            "vacation_per_month": per_month,
            "vacation_per_weekday": per_weekday,
            "vacation_per_week": per_week,
        }

    return vacation_data, vacation_stats


# =========================================================
# 🧩 CASE 3 – Long-weekend bias (Tue/Thu holidays)
# =========================================================
def generate_case3(employee_count, days_per_year=365, year=2025, seed=1337):
    """
    Similar to Case 2, but we bias some 15-day blocks
    so that they include Tue/Thu holidays → long weekends.
    """
    rng = np.random.default_rng(seed)
    vacation_data, vacation_stats = {}, {}

    # Collect all Tue/Thu Portuguese holidays for the year
    pt_holidays = holidays.Portugal(years=year)
    tuth_holidays = sorted([d for d in pt_holidays if d.weekday() in (1, 3)])  # Tue=1, Thu=3

    # Randomly assign ~50% of employees per relevant holiday
    holiday_targets = {d.timetuple().tm_yday: set() for d in tuth_holidays}
    for d in tuth_holidays:
        doy = d.timetuple().tm_yday
        chosen = rng.choice(np.arange(1, employee_count + 1),
                            size=max(1, employee_count // 2),
                            replace=False)
        holiday_targets[doy] = set(int(x) for x in chosen)

    # Build schedules
    for emp_id in range(1, employee_count + 1):
        s1, s2 = _non_overlapping_two_blocks(days_per_year, rng)

        # If employee is assigned to a holiday, center one 15-day block on it
        for doy, bucket in holiday_targets.items():
            if emp_id in bucket:
                start = _wrap_day(doy - 7, days_per_year)
                if rng.integers(1, 3) == 1:
                    s1 = start
                else:
                    s2 = start

        # Merge both 15-day blocks → 30 vacation days total
        days = set(_block_days(s1, 15, days_per_year)) | set(_block_days(s2, 15, days_per_year))
        # Handle rare overlaps by adding extra days
        while len(days) < 30:
            days.add(_wrap_day(max(days) + 1, days_per_year))

        schedule = [1 if i + 1 in days else 0 for i in range(days_per_year)]

        total, per_month, per_weekday, per_week = _stats_from_schedule(schedule)
        vacation_data[f"Employee {emp_id}"] = schedule
        vacation_stats[emp_id] = {
            "total_vacation_days": total,
            "vacation_per_month": per_month,
            "vacation_per_weekday": per_weekday,
            "vacation_per_week": per_week,
        }

    return vacation_data, vacation_stats


# =========================================================
# 🧩 CASE 4 – Summer-focused (June–August)
# =========================================================
def generate_case4(employee_count, days_per_year=365, year=2025):
    """
    All vacations fall between June 1 and August 31,
    with start dates evenly distributed across that window.
    Each employee still gets one continuous 30-day block.
    """
    vacation_data, vacation_stats = {}, {}

    summer_start, summer_end = 152, 243  # Day-of-year boundaries
    valid_starts = list(range(summer_start, summer_end - 29 + 1))  # 152–214
    n_slots = len(valid_starts)

    # Distribute employees evenly across possible start days
    if employee_count <= n_slots:
        idxs = np.linspace(0, n_slots - 1, employee_count)
        starts = [valid_starts[int(round(i))] for i in idxs]
    else:
        starts = [valid_starts[i % n_slots] for i in range(employee_count)]

    # Small phase shift every few employees to reduce clustering
    for i in range(employee_count):
        starts[i] = _wrap_day(starts[i] + (i // 7) % 3, days_per_year)

    for emp_id in range(1, employee_count + 1):
        s = starts[emp_id - 1]
        days = _block_days(s, 30, days_per_year)
        schedule = [1 if i + 1 in days else 0 for i in range(days_per_year)]

        total, per_month, per_weekday, per_week = _stats_from_schedule(schedule)
        vacation_data[f"Employee {emp_id}"] = schedule
        vacation_stats[emp_id] = {
            "total_vacation_days": total,
            "vacation_per_month": per_month,
            "vacation_per_weekday": per_weekday,
            "vacation_per_week": per_week,
        }

    return vacation_data, vacation_stats


# =========================================================
# 🧠 MASTER FUNCTION – Generate and save all cases
# =========================================================
def create_vacation_cases(employee_count=21, days_per_year=365, year=2025, output_base="VacationData"):
    """
    Create all 4 vacation distributions for a given number of employees
    and export them as CSV files.
    """
    templates_dir, stats_dir = ensure_dirs(output_base, employee_count)

    print(f"\n=== Generating vacation templates for {employee_count} employees ===")

    # Case 1 – Sequential 30-day block
    print("📘 Case 1: Sequential rotation...")
    case1, stats1 = generate_case1(employee_count, days_per_year)
    pd.DataFrame(case1).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case1_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats1, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case1_{employee_count}.csv"),
                                                          header=True, index=False)

    # Case 2 – Two random 15-day blocks
    print("📗 Case 2: Two random 15-day blocks...")
    case2, stats2 = generate_case2(employee_count, days_per_year)
    pd.DataFrame(case2).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case2_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats2, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case2_{employee_count}.csv"),
                                                          header=True, index=False)

    # Case 3 – Long-weekend bias
    print("📙 Case 3: Long-weekend bias (Tue/Thu holidays)...")
    case3, stats3 = generate_case3(employee_count, days_per_year, year)
    pd.DataFrame(case3).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case3_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats3, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case3_{employee_count}.csv"),
                                                          header=True, index=False)

    # Case 4 – Summer-focused
    print("📕 Case 4: Summer-focused staggered vacations...")
    case4, stats4 = generate_case4(employee_count, days_per_year, year)
    pd.DataFrame(case4).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case4_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats4, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case4_{employee_count}.csv"),
                                                          header=True, index=False)

    print(f"\n✅ All 4 vacation templates generated for {employee_count} employees!")
    print(f"📂 Saved in: {templates_dir}")
    print(f"📊 Stats in: {stats_dir}")


# =========================================================
# 🚀 Script entrypoint
# =========================================================
if __name__ == "__main__":
    # Example: generate data for 96 employees for year 2025
    create_vacation_cases(employee_count=96, year=2025)
