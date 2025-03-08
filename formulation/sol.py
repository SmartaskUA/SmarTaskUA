import pandas as pd

# Load CSV file and inspect structure
df = pd.read_csv("ex1.csv", skiprows=[0], header=0)

# Print the first few rows for debugging
print("Initial DataFrame:\n", df.head())

# Remove empty or unnamed columns
df = df.loc[:, ~df.columns.str.contains('^Unnamed')]

# Identify columns related to scheduling (assuming they start after fixed columns)
fixed_columns = 5  # Adjust this based on the CSV structure
schedule_columns = df.columns[fixed_columns:]

# Ensure schedule columns exist and have valid values
df[schedule_columns] = df[schedule_columns].astype(str).fillna("")

# Debugging check
print("Schedule Columns:", schedule_columns)
print("DataFrame after processing:\n", df.head())


# Function to fill missing shifts
def fill_gaps(df):
    for idx, row in df.iterrows():
        consecutive_days = 0
        last_shift = None

        for day in schedule_columns:
            if pd.isna(row[day]) or row[day] in ["nan", "None", ""]:
                new_shift = 'M' if last_shift != 'M' else 'T'

                # Enforce max 5 consecutive working days
                if consecutive_days < 5:
                    df.at[idx, day] = new_shift
                    consecutive_days += 1
                    last_shift = new_shift
                else:
                    df.at[idx, day] = 'F'  # Assign day off
                    consecutive_days = 0
            else:
                last_shift = row[day]
                consecutive_days = 0 if row[day] == 'F' else consecutive_days + 1

    return df


# Apply the gap-filling function
df = fill_gaps(df)

# Save the processed schedule
df.to_csv("filled_schedule.csv", index=False)
print("Minimal schedule generated and saved as 'filled_schedule.csv'")
