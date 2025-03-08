import pandas as pd

# Load the existing schedule
input_file = "ex1.csv"
df = pd.read_csv(input_file, skiprows=[0], header=0)
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Define fixed and schedule columns
fixed_columns = ["Competencia", "Contrato", "Férias"]
schedule_columns = [col for col in df.columns if col not in fixed_columns]

# Convert schedule columns to string, replacing NaN values
df[schedule_columns] = df[schedule_columns].astype(str).fillna("")

# Define public holidays for Portugal (2025 example)
public_holidays = {"01-01", "04-25", "05-01", "06-10", "08-15", "10-05", "11-01", "12-01", "12-08", "12-25"}


def is_holiday(date_str):
    """Check if a given date (in day format) is a public holiday."""
    return date_str in public_holidays


def fill_schedule(df):
    for idx, row in df.iterrows():
        consecutive_days = 0
        last_shift = None
        sunday_holiday_count = 0
        workday_count = 0

        for day in schedule_columns:
            if row[day] in ["nan", "None", ""]:
                if workday_count >= 223:
                    df.at[idx, day] = "F"  # Enforce yearly work limit
                    continue

                if consecutive_days >= 5:
                    df.at[idx, day] = "F"  # Ensure max 5 consecutive work days
                    consecutive_days = 0
                    continue

                if is_holiday(day) or (day in ["7", "14", "21", "28"]):  # Assuming Sundays
                    if sunday_holiday_count >= 22:
                        df.at[idx, day] = "F"
                        continue
                    sunday_holiday_count += 1

                # Assign shift following valid transitions
                new_shift = "M" if last_shift != "M" else "T"
                df.at[idx, day] = new_shift
                last_shift = new_shift
                workday_count += 1
                consecutive_days += 1
            else:
                last_shift = row[day]
                consecutive_days = 0 if row[day] == "F" else consecutive_days + 1

    return df


# Apply scheduling logic
df = fill_schedule(df)

# Save the updated schedule
output_file = "filled_schedule2.csv"
df.to_csv(output_file, index=False)
print(f"✅ Schedule updated and saved as {output_file}")