"""
run_3shifts_v4.py — run_3shifts.py on the schema v4 packages.

Same scenarios, parameters, metrics (including the phase-2 violation counts) and
output layout as run_3shifts.py, run on the v4 packages instead of the legacy
folders: each scenario is its V4_ name throughout - loaded from
data/problems/V4_<scenario> by legacy_v4.load_problem_v4, printed as V4_<scenario>,
written to results_3shifts/V4_<scenario>/. The GA is untouched, so these results
should be statistically equivalent to results_3shifts/<scenario>/.

Usage:
    python run_3shifts_v4.py                                       # every scenario in run_3shifts.py
    python run_3shifts_v4.py V4_SMARTASK_3SHIFTS_2TEAMS_2025       # only these
    python run_3shifts_v4.py V4_SMARTASK_3SHIFTS_2TEAMS_2025 --runs 2

Output (beside the legacy results, never over them):
    results_3shifts/V4_<scenario>/results.csv
    results_3shifts/V4_<scenario>/convergence/run*.npy
    results_3shifts/V4_<scenario>/schedules/run*.npy
    results_3shifts/summary_v4.csv          (the scenarios of this invocation)
"""

import argparse
import csv
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]   # problem3.py / ga3.py, and problem_v4

import run_3shifts
from legacy_v4 import load_problem_v4


def v4_name(name: str) -> str:
    return name if name.startswith("V4_") else f"V4_{name}"


def main():
    ap = argparse.ArgumentParser(description="run_3shifts.py on the schema v4 packages")
    ap.add_argument("scenarios", nargs="*", help="V4_ scenario names (default: all of run_3shifts.py's)")
    ap.add_argument("--runs", type=int, help="runs per scenario (default: run_3shifts.py's)")
    args = ap.parse_args()
    wanted = {v4_name(s) for s in args.scenarios}

    # run_scenario loads <DATA_DIR>/<scenario>; with V4_ names that is the v4 package.
    run_3shifts.load_problem = lambda path: load_problem_v4(path)[0]
    os.chdir(HERE)
    summary_rows = []
    for scenario, n_runs in run_3shifts.SCENARIOS:
        scenario = v4_name(scenario)
        if wanted and scenario not in wanted:
            continue
        run_3shifts.run_scenario(scenario, args.runs or n_runs, summary_rows)

    os.makedirs("results_3shifts", exist_ok=True)
    summary_path = os.path.join("results_3shifts", "summary_v4.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=run_3shifts.SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)
    print(f"\n  Summary → {summary_path}")


if __name__ == "__main__":
    main()
