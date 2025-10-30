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
  1st case: Sequential 30-day rotation across the year
  2nd case: Two random 15-day blocks per employee (non-overlapping)
  3rd case: Same as Case 2, but biased around Tue/Thu holidays (long weekends)
  4th case: Summer-focused (June–August)
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
# =========================================================
# 🧩 CASE 3 – Long-weekend bias (improved realism)
# =========================================================
def generate_case3(employee_count, days_per_year=365, year=2025, seed=1337):
    """
    Case 3: Two 15-day vacation blocks per employee,
    but ~60% of employees get one block biased around
    real Tue/Thu holidays or long weekends.

    Improvements:
      ✅ Limited % of employees per holiday (avoids everyone picking same week)
      ✅ Better spread across seasons
      ✅ Keeps variety and non-overlap
    """
    rng = np.random.default_rng(seed)
    vacation_data, vacation_stats = {}, {}

    # --- Step 1: Identify real Tue/Thu holidays in Portugal ---
    pt_holidays = holidays.Portugal(years=year)
    tuth_holidays = sorted([d for d in pt_holidays if d.weekday() in (1, 3)])  # Tue=1, Thu=3

    # Convert to day-of-year indexes
    holiday_days = [d.timetuple().tm_yday for d in tuth_holidays]
    if not holiday_days:
        print("⚠️ No Tue/Thu holidays found for this year; falling back to random blocks.")
        return generate_case2(employee_count, days_per_year, seed)

    # --- Step 2: Build holiday "clusters" (±7 days around each holiday) ---
    clusters = []
    for hday in holiday_days:
        start = _wrap_day(hday - 7, days_per_year)
        end = _wrap_day(hday + 7, days_per_year)
        clusters.append(set(_block_days(start, 15, days_per_year)))

    # --- Step 3: Randomly assign ~60% of employees to one of the clusters ---
    biased_emps = set(rng.choice(np.arange(1, employee_count + 1),
                                 size=int(0.6 * employee_count),
                                 replace=False))

    # Each cluster gets at most ~15% of all employees
    max_per_cluster = max(1, int(employee_count * 0.15))
    cluster_assignments = {i: [] for i in range(len(clusters))}
    for emp_id in biased_emps:
        chosen_cluster = rng.integers(0, len(clusters))
        if len(cluster_assignments[chosen_cluster]) < max_per_cluster:
            cluster_assignments[chosen_cluster].append(emp_id)
        else:
            # fallback to next available cluster
            for alt_idx in range(len(clusters)):
                if len(cluster_assignments[alt_idx]) < max_per_cluster:
                    cluster_assignments[alt_idx].append(emp_id)
                    break

    # --- Step 4: Generate two non-overlapping blocks per employee ---
    for emp_id in range(1, employee_count + 1):
        s1, s2 = _non_overlapping_two_blocks(days_per_year, rng)

        # If employee is biased → replace one block with cluster-based window
        for cluster_idx, members in cluster_assignments.items():
            if emp_id in members:
                cluster_days = sorted(clusters[cluster_idx])
                # Center first block around cluster (e.g., 15-day block covering that period)
                s1 = cluster_days[0]
                # Ensure the second block is far away (at least 60 days apart)
                while abs(s2 - s1) < 60:
                    s2 = rng.integers(1, days_per_year - 14)
                break  # assigned once only

        # Combine blocks and repair if any overlap
        days = set(_block_days(s1, 15, days_per_year)) | set(_block_days(s2, 15, days_per_year))
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

    print(f"Case 3 complete: {len(biased_emps)} employees biased toward long weekends.")
    return vacation_data, vacation_stats

# CASE 4 – Summer-focused (June–August)
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


# Main Function
def create_vacation_cases(employee_count=21, days_per_year=365, year=2025, output_base="VacationData"):
    """
    Create all 4 vacation distributions for a given number of employees
    and export them as CSV files.
    """
    templates_dir, stats_dir = ensure_dirs(output_base, employee_count)

    print(f"\n=== Generating vacation templates for {employee_count} employees ===")

    # Case 1 – Sequential 30-day block
    print("Case 1: Sequential rotation...")
    case1, stats1 = generate_case1(employee_count, days_per_year)
    pd.DataFrame(case1).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case1_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats1, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case1_{employee_count}.csv"),
                                                          header=True, index=False)

    # Case 2 – Two random 15-day blocks
    print("Case 2: Two random 15-day blocks...")
    case2, stats2 = generate_case2(employee_count, days_per_year)
    pd.DataFrame(case2).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case2_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats2, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case2_{employee_count}.csv"),
                                                          header=True, index=False)

    # Case 3 – Long-weekend bias
    print("Case 3: Long-weekend bias (Tue/Thu holidays)...")
    case3, stats3 = generate_case3(employee_count, days_per_year, year)
    pd.DataFrame(case3).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case3_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats3, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case3_{employee_count}.csv"),
                                                          header=True, index=False)

    # Case 4 – Summer-focused
    print("Case 4: Summer-focused staggered vacations...")
    case4, stats4 = generate_case4(employee_count, days_per_year, year)
    pd.DataFrame(case4).T.reset_index().to_csv(os.path.join(templates_dir, f"VacationTemplate_Case4_{employee_count}.csv"),
                                               header=False, index=False)
    pd.DataFrame.from_dict(stats4, orient="index").to_csv(os.path.join(stats_dir, f"VacationStatistics_Case4_{employee_count}.csv"),
                                                          header=True, index=False)

    print(f"\nAll 4 vacation templates generated for {employee_count} employees!")
    print(f"Saved in: {templates_dir}")
    print(f"Stats in: {stats_dir}")


if __name__ == "__main__":
    create_vacation_cases(employee_count=96, year=2025)
