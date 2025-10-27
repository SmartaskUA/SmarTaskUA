import pandas as pd
import numpy as np

def compute_vacation_statistics_from_file(file_path, days_per_year=None):
    """
    Compute vacation statistics (total, per month, per week, per weekday)
    from a generated vacation template CSV file.

    Automatically detects whether the file has 365 or 366 days.
    Works with files that have NO header (just 0s/1s per day).
    """
    # --- Load the CSV ---
    df = pd.read_csv(file_path, header=None)  # <-- no header row
    df = df.apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

    num_employees = len(df)

    # 🔍 Auto-detect number of days from the file
    if days_per_year is None:
        days_per_year = df.shape[1]
        print(f"Detected {days_per_year} days from file structure.")

    num_weeks = (days_per_year // 7) + (1 if days_per_year % 7 > 0 else 0)
    month_lengths = [31, 29 if days_per_year == 366 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    stats = {}

    for emp_idx in range(num_employees):
        schedule = df.iloc[emp_idx].to_numpy()

        # --- Compute aggregates ---
        total_vacation_days = int(np.sum(schedule))

        # Per month
        vacation_per_month = []
        day_counter = 0
        for month_length in month_lengths:
            vacation_per_month.append(int(np.sum(schedule[day_counter:day_counter + month_length])))
            day_counter += month_length

        # Per weekday (Mon=0 … Sun=6)
        weekdays = np.array([(i % 7) for i in range(days_per_year)])
        vacation_per_weekday = [int(np.sum(schedule[weekdays == w])) for w in range(7)]

        # Per week
        weeks = np.array([(i // 7) for i in range(days_per_year)])
        vacation_per_week = [int(np.sum(schedule[weeks == w])) for w in range(num_weeks)]

        # Store statistics
        stats[emp_idx + 1] = {
            "Total Vacation Days": total_vacation_days,
            **{f"Month_{i+1}": vacation_per_month[i] for i in range(12)},
            **{f"Weekday_{i}": vacation_per_weekday[i] for i in range(7)},
            **{f"Week_{i+1}": vacation_per_week[i] for i in range(num_weeks)},
        }

    stats_df = pd.DataFrame(stats).T
    stats_df.index.name = "Employee"

    print(f"\n✅ Processed {num_employees} employees from '{file_path}'")
    print(f"Average total vacation days: {stats_df['Total Vacation Days'].mean():.2f}")
    print(f"Min/Max total vacation days: {stats_df['Total Vacation Days'].min()} / {stats_df['Total Vacation Days'].max()}")

    return stats_df


# --- Run the function ---
stats = compute_vacation_statistics_from_file("VacationTemplate.csv")
stats.to_csv("VacationStatistics_FromFile.csv", index=True)
