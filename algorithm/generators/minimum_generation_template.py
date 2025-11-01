"""
------------------------------------------------------------
📘 MINIMUMS SCALER GENERATOR
------------------------------------------------------------
Goal:
  Automatically generate "minimuns" staffing templates for larger
  organizational scenarios (4, 8, 16 teams) based on a smaller base
  configuration (2 teams, 15 employees).

What this script does:
  1. Reads the base minimuns.csv (staffing per day per team/shift)
  2. Extracts one team’s pattern (Equipa A)
  3. Scales that pattern according to target teams and employee counts
  4. Ensures Ideal values stay within +40% of Minimo
  5. Normalizes daily totals so they don’t exceed workforce capacity
  6. Saves new minimuns_xxteams_xxemp.csv files

------------------------------------------------------------
"""

import pandas as pd
import numpy as np




base_file = "minimuns.csv"

# Base scenario info:
#   - 15 total employees
#   - Equipa A = 10 employees
#   - Equipa B = 5 employees
base_total_employees = 15
base_teams = 2

# Target scenarios: (number_of_teams, total_employees)
targets = [
    (4, 24),
    (8, 48),
    (16, 96),
]

# Adds small random ±1 variation to avoid identical rows
enable_variation = True

# Ideal upper bound: Ideal ≤ Minimo × (1 + 0.40)
max_increase_pct = 0.40

# Each employee can only work one shift per day
# (If you want to model absences, use < 1.0)
daily_capacity_utilization = 1.0


# =========================================================
# 📥 LOAD BASE MINIMUM FILE
# =========================================================

df_base = pd.read_csv(base_file)
print(f"Loaded base minimuns: {df_base.shape}")

# Split columns: metadata (first 3) vs day columns (D1..D365)
meta_cols = ["Equipa", "Tipo", "Turno"]
day_cols = [c for c in df_base.columns if c not in meta_cols]

# Convert all day values to integers, replace blanks with 0
df_base[day_cols] = (
    df_base[day_cols]
    .apply(pd.to_numeric, errors="coerce")
    .fillna(0)
    .astype(int)
)

# Extract only Equipa A’s 4-row pattern:
#   (Minimo/Ideal × Morning/Evening)
pattern_df = df_base[df_base["Equipa"].str.contains("A", case=False, na=False)].reset_index(drop=True)
pattern_df = pattern_df.head(4)
print(f"Using base pattern rows: {pattern_df.shape}")



def _enforce_ideal_bounds(df_scaled, day_cols, cap=max_increase_pct):
    """
    Enforce Ideal ≥ Minimo and Ideal ≤ Minimo × (1 + cap)
    for each shift type (Turno).
    """
    for turno in df_scaled["Turno"].unique():
        min_idx = df_scaled.query(f"Tipo == 'Minimo' and Turno == '{turno}'").index
        ideal_idx = df_scaled.query(f"Tipo == 'Ideal' and Turno == '{turno}'").index
        if min_idx.empty or ideal_idx.empty:
            continue

        # Compare values day-by-day
        minimo = df_scaled.loc[min_idx[0], day_cols].to_numpy(dtype=float)
        ideal = df_scaled.loc[ideal_idx[0], day_cols].to_numpy(dtype=float)

        # Enforce lower and upper bounds
        ideal = np.maximum(ideal, minimo)
        upper = np.round(minimo * (1.0 + cap))
        ideal = np.minimum(ideal, upper)

        # Write corrected values back into dataframe
        df_scaled.loc[ideal_idx[0], day_cols] = ideal.astype(int)


def generate_scaled_minimums(df_pattern, teams_target, employees_target):
    """
    Creates a new minimuns table for the given (teams, employees).

    Steps:
      1️⃣ Compute scaling factor per team (based on headcount ratio)
      2️⃣ Scale Equipa A pattern accordingly
      3️⃣ Add small random variation (optional)
      4️⃣ Enforce Ideal bounds (≤ +40%)
      5️⃣ Duplicate block across all teams (A, B, C, …)
      6️⃣ Normalize per-day totals so Minimo sum ≤ total employees
    """
    # Per-team scaling ratio
    base_emp_per_team = 10  # Actual size of Equipa A in base scenario
    target_emp_per_team = employees_target / teams_target
    per_team_scale = target_emp_per_team / base_emp_per_team

    print(f"\n📊 Generating for {teams_target} teams, {employees_target} employees")
    print(f"   Base emp/team = {base_emp_per_team:.2f}, Target emp/team = {target_emp_per_team:.2f}")
    print(f"   Per-team scale factor = x{per_team_scale:.3f}")

    # Step 1: Scale one team’s pattern numerically
    df_scaled_one = df_pattern.copy()
    df_scaled_one[day_cols] = np.round(df_pattern[day_cols].to_numpy(dtype=float) * per_team_scale).astype(int)

    # Step 2: Add small random variation ±1 (keeps results natural)
    if enable_variation:
        variation = np.random.randint(-1, 2, df_scaled_one[day_cols].shape)
        df_scaled_one[day_cols] = np.clip(df_scaled_one[day_cols] + variation, 0, None)

    # Step 3: Reapply Ideal ≤ Minimo × (1.4)
    _enforce_ideal_bounds(df_scaled_one, day_cols, max_increase_pct)

    # Step 4: Duplicate block for all teams (A..Z)
    teams = [f"Equipa {chr(65 + i)}" for i in range(teams_target)]
    df_all = pd.concat([df_scaled_one.assign(Equipa=team) for team in teams], ignore_index=True)

    # =========================================================
    # Step 5: DAILY CAPACITY NORMALIZATION
    # ---------------------------------------------------------
    # Ensures that the sum of all "Minimo" requirements per day
    # across all teams does not exceed total available employees.
    # =========================================================
    daily_capacity = int(np.floor(employees_target * daily_capacity_utilization))

    # Boolean masks for Minimo / Ideal rows
    minimo_mask = (df_all["Tipo"] == "Minimo")
    ideal_mask = (df_all["Tipo"] == "Ideal")

    for day in day_cols:
        total_min = df_all.loc[minimo_mask, day].sum()
        if total_min <= daily_capacity:
            continue

        # Scale down all Minimo rows proportionally
        scale = daily_capacity / total_min if total_min > 0 else 1.0
        scaled_vals = np.floor(df_all.loc[minimo_mask, day].to_numpy(dtype=float) * scale).astype(int)
        df_all.loc[minimo_mask, day] = scaled_vals

        # Enforce Ideal bounds again after normalization
        for turno in df_all["Turno"].unique():
            min_rows = df_all[(df_all["Turno"] == turno) & minimo_mask]
            ideal_rows = df_all[(df_all["Turno"] == turno) & ideal_mask]
            if min_rows.empty or ideal_rows.empty:
                continue

            # Adjust each team’s Ideal values accordingly
            for idx_team, min_row in min_rows.iterrows():
                same_team = (ideal_rows["Equipa"] == min_row["Equipa"])
                ideal_idx = ideal_rows[same_team].index
                if ideal_idx.empty:
                    continue

                minimo_val = int(df_all.at[idx_team, day])
                upper = int(np.round(minimo_val * (1.0 + max_increase_pct)))
                df_all.at[ideal_idx[0], day] = max(min(df_all.at[ideal_idx[0], day], upper), minimo_val)

    # Step 6: Final cleanup
    df_all[day_cols] = df_all[day_cols].clip(lower=0).astype(int)
    df_all = df_all[["Equipa", "Tipo", "Turno"] + day_cols]

    return df_all


# =========================================================
# 💾 GENERATE & SAVE ALL TARGET FILES
# =========================================================
for teams, employees in targets:
    df_new = generate_scaled_minimums(pattern_df, teams, employees)
    out_file = f"minimuns_{teams}teams_{employees}emp.csv"
    df_new.to_csv(out_file, index=False)
    print(f"✅ Saved: {out_file}")


"""
------------------------------------------------------------
📈 QUICK SUMMARY (how to explain)
------------------------------------------------------------
- The base minimuns.csv has 2 teams:
    Equipa A (10 employees)
    Equipa B (5 employees)
- We extract A’s staffing pattern and treat it as a “model team”.
- For each new scenario:
    • The per-team size shrinks (e.g., 10 → 6 employees)
    • We scale down all daily staffing requirements proportionally.
- The Ideal lines are automatically adjusted so that:
    Ideal ≤ Minimo × 1.4  (40% max increase)
- Finally, the script ensures that the total daily "Minimo" load
  never exceeds the available employee count for that scenario.
- The result is exported as new CSVs for 4, 8, and 16 teams.
------------------------------------------------------------
"""
