"""
run_elite5.py — GA validation runs with elite_size=5 and one-pass LS on elite.

Identical to run_final.py except elite_size=5. Results saved to results_elite5/
so existing results_final/ results are never overwritten.

Usage:
    python run_elite5.py
"""

import os
import csv
import time
import numpy as np

from problem import load_problem, _compute_penalties
from ga import run_ga

SCENARIOS = [
    {"data_dir": "SMARTASK_SIMPLE_2025",  "n_runs": 10, "early_stop_patience": 100, "n_workers": None},
    {"data_dir": "SMARTASK_4TEAMS_2025",  "n_runs": 10, "early_stop_patience": 100, "n_workers": None},
    {"data_dir": "SMARTASK_8TEAMS_2025",  "n_runs": 10, "early_stop_patience": 100, "n_workers": None},
    {"data_dir": "SMARTASK_16TEAMS_2025", "n_runs": 10, "early_stop_patience": 100, "n_workers": None},
    {"data_dir": "SMARTASK_32TEAMS_2025", "n_runs": 10, "early_stop_patience": 100, "n_workers": 4},
]

BASE_PARAMS = {
    "crossover_type":       "nbts",
    "mutation_type":        "demand_guided",
    "crossover_prob":       0.8,
    "pop_size":             200,
    "gene_mut_prob":        0.003,
    "tournament_size":      7,
    "num_generations":      1000,
    "early_stop_min_delta": 1,
    "elite_size":           5,   # changed from 1
}

CSV_FIELDS = [
    "run", "best_fitness", "min_coverage_unmet", "ideal_coverage_unmet",
    "stopped_at_gen", "elapsed_s",
]


def run_scenario(data_dir, n_runs, patience, n_workers):
    params = {**BASE_PARAMS, "early_stop_patience": patience, "n_workers": n_workers}

    output_dir = os.path.join("results_elite5", data_dir)
    conv_dir   = os.path.join(output_dir, "convergence")
    sched_dir  = os.path.join(output_dir, "schedules")
    os.makedirs(conv_dir,  exist_ok=True)
    os.makedirs(sched_dir, exist_ok=True)

    print(f"\n{'='*56}")
    print(f"  {data_dir}  (elite_size=5, patience={patience}, runs={n_runs})")
    print(f"{'='*56}")

    problem_data = load_problem(data_dir)
    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]
    print(f"  {n_emp} employees × {n_days} days\n")

    csv_path   = os.path.join(output_dir, "ga_results.csv")
    done_runs  = set()
    write_mode = "w"
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                done_runs.add(int(row["run"]))
        write_mode = "a"

    results  = []
    csv_file = open(csv_path, write_mode, newline="")
    writer   = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    if write_mode == "w":
        writer.writeheader()

    for run_idx in range(1, n_runs + 1):
        if run_idx in done_runs:
            print(f"  Run {run_idx:2d}/{n_runs} already done, skipping.")
            continue

        print(f"  Run {run_idx:2d}/{n_runs}", end="  ", flush=True)
        t0 = time.time()
        best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, params)
        elapsed = time.time() - t0

        schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
        min_unmet, ideal_unmet = _compute_penalties(schedule, problem_data)

        print(f"fitness={best_fitness:.0f}  min_unmet={min_unmet}  "
              f"ideal_unmet={ideal_unmet}  gen={stopped_at}  {elapsed:.0f}s")
        results.append(ideal_unmet)

        np.save(os.path.join(conv_dir,  f"run{run_idx}.npy"),
                np.array([r["best"] for r in logbook]))
        np.save(os.path.join(sched_dir, f"run{run_idx}.npy"), schedule)

        writer.writerow({
            "run":                  run_idx,
            "best_fitness":         best_fitness,
            "min_coverage_unmet":   min_unmet,
            "ideal_coverage_unmet": ideal_unmet,
            "stopped_at_gen":       stopped_at,
            "elapsed_s":            round(elapsed, 1),
        })
        csv_file.flush()

    csv_file.close()

    if results:
        print(f"\n  Summary (GA elite5): best={min(results)}  "
              f"mean={sum(results)/len(results):.1f}  worst={max(results)}")
    print(f"  Saved to '{csv_path}'")


def main():
    for s in SCENARIOS:
        run_scenario(s["data_dir"], s["n_runs"], s["early_stop_patience"], s["n_workers"])


if __name__ == "__main__":
    main()
