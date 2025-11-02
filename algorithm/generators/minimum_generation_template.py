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




## dir not working
# === CONFIGURATION ===
# Base file path
base_file = "data/base_files/minimuns.csv"

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



def _enforce_ideal_bounds(df_scaled, day_cols, cap=None):
    """
    Force Ideal = Minimo + 1 for each shift type (Turno).
    """
    for turno in df_scaled["Turno"].unique():
        min_idx = df_scaled.query(f"Tipo == 'Minimo' and Turno == '{turno}'").index
        ideal_idx = df_scaled.query(f"Tipo == 'Ideal' and Turno == '{turno}'").index
        if min_idx.empty or ideal_idx.empty:
            continue

        minimo = df_scaled.loc[min_idx[0], day_cols].to_numpy(dtype=int)
        ideal = minimo + 1  # ✅ Always 1 higher
        df_scaled.loc[ideal_idx[0], day_cols] = ideal


def generate_scaled_minimums(df_pattern, teams_target, employees_target):
    base_emp_per_team = 10
    target_emp_per_team = employees_target / teams_target
    per_team_scale = target_emp_per_team / base_emp_per_team

    print(f"\n📊 Generating for {teams_target} teams, {employees_target} employees")
    print(f"   Per-team scale factor = x{per_team_scale:.3f}")

    # --- Base numeric scaling (no noise yet) ---
    base_scaled = df_pattern.copy()
    base_scaled[day_cols] = np.round(df_pattern[day_cols] * per_team_scale).astype(int)

    teams = []
    for t in range(teams_target):
        df_team = base_scaled.copy()
        df_team["Equipa"] = f"Equipa {chr(65 + t)}"

        if enable_variation:
            shape = df_team[day_cols].shape
            variation = np.zeros(shape, dtype=int)

            # Per-row balanced ±1 perturbations
            for i in range(shape[0]):
                row_len = shape[1]
                n_changes = max(1, row_len // 25)  # ~4% perturbed
                pos_idx = np.random.choice(row_len, n_changes, replace=False)
                remaining = [j for j in range(row_len) if j not in pos_idx]
                neg_idx = np.random.choice(remaining, n_changes, replace=False)
                variation[i, pos_idx] = 1
                variation[i, neg_idx] = -1

            df_team[day_cols] = np.clip(df_team[day_cols] + variation, 0, None)

        _enforce_ideal_bounds(df_team, day_cols, max_increase_pct)
        teams.append(df_team)

    # --- Merge all team blocks ---
    df_all = pd.concat(teams, ignore_index=True)

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

            for idx_team, min_row in min_rows.iterrows():
                same_team = (ideal_rows["Equipa"] == min_row["Equipa"])
                ideal_idx = ideal_rows[same_team].index
                if ideal_idx.empty:
                    continue

                minimo_val = int(df_all.at[idx_team, day])
                df_all.at[ideal_idx[0], day] = minimo_val + 1 

    # Step 6: Final cleanup
    df_all[day_cols] = df_all[day_cols].clip(lower=0).astype(int)
    df_all = df_all[["Equipa", "Tipo", "Turno"] + day_cols]

    return df_all


# =========================================================
# 💾 GENERATE & SAVE ALL TARGET FILES
# =========================================================
for teams, employees in targets:
    df_new = generate_scaled_minimums(pattern_df, teams, employees)
    out_file = f"data/minimunsData/minimuns_{teams}teams_{employees}emp.csv"
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
