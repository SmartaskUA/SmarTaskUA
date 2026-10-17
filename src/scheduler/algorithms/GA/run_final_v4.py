"""
run_final_v4.py — run_final.py on the schema v4 packages.

Same scenarios, parameters, metrics and output layout as run_final.py, run on the
v4 packages instead of the legacy folders: each scenario is its V4_ name
throughout - loaded from data/problems/V4_<scenario> by legacy_v4.load_problem_v4,
printed as V4_<scenario>, written to results_final/V4_<scenario>/. The GA is
untouched, so these results should be statistically equivalent to
results_final/<scenario>/.

Usage:
    python run_final_v4.py                                  # every scenario in run_final.py
    python run_final_v4.py V4_SMARTASK_SIMPLE_2025          # only these
    python run_final_v4.py V4_SMARTASK_SIMPLE_2025 --runs 2 # fewer runs than run_final.py's

Output (beside the legacy results, never over them):
    results_final/V4_<scenario>/ga_results.csv
    results_final/V4_<scenario>/convergence/run*.npy
    results_final/V4_<scenario>/schedules/run*.npy
"""

import argparse
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE), str(HERE.parents[1])]   # problem.py / ga.py, and problem_v4

import run_final
from legacy_v4 import load_problem_v4

V4_PROBLEMS = HERE.parents[3] / "data" / "problems"


def v4_name(name: str) -> str:
    return name if name.startswith("V4_") else f"V4_{name}"


def main():
    ap = argparse.ArgumentParser(description="run_final.py on the schema v4 packages")
    ap.add_argument("scenarios", nargs="*", help="V4_ scenario names (default: all of run_final.py's)")
    ap.add_argument("--runs", type=int, help="runs per scenario (default: run_final.py's n_runs)")
    args = ap.parse_args()
    wanted = {v4_name(s) for s in args.scenarios}

    # run_scenario loads by name and writes under results_final/<name>.
    run_final.load_problem = lambda name: load_problem_v4(V4_PROBLEMS / name)[0]
    os.chdir(HERE)
    for s in run_final.SCENARIOS:
        scenario = v4_name(s["data_dir"])
        if wanted and scenario not in wanted:
            continue
        run_final.run_scenario(scenario, args.runs or s["n_runs"],
                               s["early_stop_patience"], s["n_workers"])


if __name__ == "__main__":
    main()
