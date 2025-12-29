import pandas as pd
import numpy as np
import glob
import os

# === CONFIGURATION ===
file_pattern = "data/minimunsData/minimuns_*teams_*emp.csv"
base_file = "data/base_files/minimuns.csv"
output_file = "data/minimunsData/minimuns_Summary_Statistics.csv"
global_output = "data/minimunsData/Minimuns_Global_Averages.csv"

# === ENSURE DIRECTORIES EXIST ===
os.makedirs(os.path.dirname(output_file), exist_ok=True)
os.makedirs(os.path.dirname(global_output), exist_ok=True)


# === FUNCTION: analyze a single file (team-level only) ===
def analyze_minimum_file(file_path):
    df = pd.read_csv(file_path)
    print(f"Analyzing {file_path} ... ({df.shape[0]} rows, {df.shape[1]} cols)")

    meta_cols = ["Equipa", "Tipo", "Turno"]
    day_cols = [c for c in df.columns if c not in meta_cols]

    df[day_cols] = df[day_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    df["Mean_Value"] = df[day_cols].mean(axis=1)

    minimo_df = df[df["Tipo"].str.lower() == "minimo"].copy()
    ideal_df = df[df["Tipo"].str.lower() == "ideal"].copy()

    merged = pd.merge(
        minimo_df,
        ideal_df,
        on=["Equipa", "Turno"],
        suffixes=("_minimo", "_ideal")
    )

    merged["Ratio_Ideal_to_Minimo"] = (
        merged["Mean_Value_ideal"] / merged["Mean_Value_minimo"]
    )
    merged["File"] = os.path.basename(file_path)

    summary = merged.groupby("Equipa").agg({
        "Mean_Value_minimo": "mean",
        "Mean_Value_ideal": "mean",
        "Ratio_Ideal_to_Minimo": "mean"
    }).reset_index()

    summary["File"] = os.path.basename(file_path)
    summary["Teams"] = len(df["Equipa"].unique())
    summary["Total_Rows"] = df.shape[0]

    return summary


# === LOAD FILES ===
generated_files = glob.glob(file_pattern)
all_files = [base_file] + generated_files if os.path.exists(base_file) else generated_files

if not all_files:
    print("No minimuns files found.")
    exit()

all_summaries = []

for f in all_files:
    try:
        summary_df = analyze_minimum_file(f)
        all_summaries.append(summary_df)
    except Exception as e:
        print(f"Error analyzing {f}: {e}")


# === COMBINE TEAM-LEVEL SUMMARIES ===
final_summary = pd.concat(all_summaries, ignore_index=True)


# === COMPUTE TOTAL MINIMOS & IDEALS PER FILE (YEARLY) ===
file_totals = []

for f in all_files:
    df = pd.read_csv(f)

    meta_cols = ["Equipa", "Tipo", "Turno"]
    day_cols = [c for c in df.columns if c not in meta_cols]

    df[day_cols] = df[day_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

    total_minimos = df[df["Tipo"].str.lower() == "minimo"][day_cols].sum().sum()
    total_ideals = df[df["Tipo"].str.lower() == "ideal"][day_cols].sum().sum()

    file_totals.append({
        "File": os.path.basename(f),
        "Total_Minimos_Year": total_minimos,
        "Total_Ideals_Year": total_ideals
    })

file_totals_df = pd.DataFrame(file_totals)


# === GLOBAL AVERAGES PER FILE ===
global_summary = (
    final_summary.groupby("File")[["Mean_Value_minimo", "Mean_Value_ideal", "Ratio_Ideal_to_Minimo"]]
    .mean()
    .reset_index()
)

global_summary["Teams"] = final_summary.groupby("File")["Teams"].first().values

# Add yearly totals
global_summary = global_summary.merge(file_totals_df, on="File", how="left")


# === SAVE OUTPUTS ===
final_summary.to_csv(output_file, index=False)
print(f"Saved detailed team summary → {output_file}")

global_summary.to_csv(global_output, index=False)
print(f"Saved global averages → {global_output}")
