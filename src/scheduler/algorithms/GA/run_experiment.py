"""
run_experiments.py — Run all crossover × mutation combinations N times each
and save results to a CSV for analysis in the notebook.

Usage:
    python run_experiments.py

Output:
    results/experiment_results.csv  — one row per run
    results/convergence/            — one npy file per run with the fitness log
"""

import os
import csv
import time
import numpy as np

from problem import load_problem, _compute_penalties
from ga import run_ga

DATA_DIR   = "SMARTASK_SIMPLE_2025"
N_RUNS     = 5
OUTPUT_DIR = "results_future_init"
CONV_DIR   = os.path.join(OUTPUT_DIR, "convergence")

GA_PARAMS = {
    "num_generations": 1000,
    "pop_size":        150,
    "gene_mut_prob":   0.001,
    "early_stop_patience": 50,
}

# COMBINATIONS = [
#     {"crossover_type": "row_swap",   "mutation_type": "respect_constraints"},
#     {"crossover_type": "row_swap",   "mutation_type": "demand_guided"},
#     {"crossover_type": "row_swap",   "mutation_type": "swap"},
#     {"crossover_type": "row_swap",   "mutation_type": "both"},
#     {"crossover_type": "nbts",       "mutation_type": "respect_constraints"},
#     {"crossover_type": "nbts",       "mutation_type": "demand_guided"},
#     {"crossover_type": "nbts",       "mutation_type": "swap"},
#     {"crossover_type": "nbts",       "mutation_type": "both"},
#     {"crossover_type": "day_point",  "mutation_type": "respect_constraints"},
#     {"crossover_type": "day_point",  "mutation_type": "demand_guided"},
#     {"crossover_type": "day_point",  "mutation_type": "swap"},
#     {"crossover_type": "day_point",  "mutation_type": "both"},
# ]

COMBINATIONS = [
    {"crossover_type": "nbts",       "mutation_type": "demand_guided"}
]



CSV_FIELDS = [
    "crossover_type", "mutation_type", "run",
    "best_fitness", "min_coverage_unmet", "ideal_coverage_unmet",
    "stopped_at_gen", "elapsed_s",
]


def main():
    os.makedirs(CONV_DIR, exist_ok=True)

    print(f"Loading problem data from '{DATA_DIR}'...")
    problem_data = load_problem(DATA_DIR)
    print(f"  {problem_data['n_employees']} employees × {problem_data['n_days']} days\n")

    csv_path = os.path.join(OUTPUT_DIR, "experiment_results.csv")
    done_runs = set()
    write_mode = "w"
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                done_runs.add((row["crossover_type"], row["mutation_type"], int(row["run"])))
        write_mode = "a"

    csv_file = open(csv_path, write_mode, newline="")
    writer   = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    if write_mode == "w":
        writer.writeheader()

    total = len(COMBINATIONS) * N_RUNS
    done  = 0

    for combo in COMBINATIONS:
        cx  = combo["crossover_type"]
        mut = combo["mutation_type"]
        print(f"── {cx} + {mut} ──────────────────────────────")

        for run_idx in range(1, N_RUNS + 1):
            if (cx, mut, run_idx) in done_runs:
                print(f"  Run {run_idx} already completed, skipping.")
                done += 1
                continue
            done += 1
            print(f"  Run {run_idx}/{N_RUNS}  [{done}/{total}]", end="  ", flush=True)

            params = {**GA_PARAMS, **combo}
            t0 = time.time()
            best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, params)
            elapsed = time.time() - t0

            # Decode final schedule for coverage stats
            n_emp  = problem_data["n_employees"]
            n_days = problem_data["n_days"]
            schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)

            min_unmet, ideal_unmet = _compute_penalties(schedule, problem_data)

            print(f"fitness={best_fitness:.0f}  min_unmet={min_unmet}  gen={stopped_at}  {elapsed:.0f}s")

            # Save convergence curve
            conv_name = f"{cx}__{mut}__run{run_idx}.npy"
            bests = [r["best"] for r in logbook]
            np.save(os.path.join(CONV_DIR, conv_name), np.array(bests))

            # Write CSV row
            writer.writerow({
                "crossover_type":       cx,
                "mutation_type":        mut,
                "run":                  run_idx,
                "best_fitness":         best_fitness,
                "min_coverage_unmet":   min_unmet,
                "ideal_coverage_unmet": ideal_unmet,
                "stopped_at_gen":       stopped_at,
                "elapsed_s":            round(elapsed, 1),
            })
            csv_file.flush()

        print()

    csv_file.close()
    print(f"\nDone. Results saved to '{csv_path}'")
    print(f"Convergence curves saved to '{CONV_DIR}/'")


if __name__ == "__main__":
    main()
