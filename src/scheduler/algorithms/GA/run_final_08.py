"""
run_final_08.py — Final validation run with best configuration and crossover_prob=0.8.

Configuration: nbts + demand_guided
Hyperparameters (tuned):
  - pop_size:        200
  - gene_mut_prob:   0.003
  - tournament_size: 7
  - crossover_prob:  0.8  ← differs from run_final.py (0.5)

Usage:
    python run_final_08.py

Output:
    results_final_08/final_results.csv  — one row per run
    results_final_08/convergence/       — one npy file per run
"""

import os
import csv
import time
import numpy as np

from problem import load_problem, _compute_penalties
from ga import run_ga

DATA_DIR   = "SMARTASK_SIMPLE_2025"
N_RUNS     = 10
OUTPUT_DIR = "results_final_08"
CONV_DIR   = os.path.join(OUTPUT_DIR, "convergence")

PARAMS = {
    "crossover_type":      "nbts",
    "mutation_type":       "demand_guided",
    "pop_size":            200,
    "gene_mut_prob":       0.003,
    "tournament_size":     7,
    "crossover_prob":      0.8,
    "num_generations":     1000,
    "early_stop_patience": 50,
}

CSV_FIELDS = [
    "run", "best_fitness", "min_coverage_unmet", "ideal_coverage_unmet",
    "stopped_at_gen", "elapsed_s",
]


def main():
    os.makedirs(CONV_DIR, exist_ok=True)

    print(f"Loading problem data from '{DATA_DIR}'...")
    problem_data = load_problem(DATA_DIR)
    print(f"  {problem_data['n_employees']} employees × {problem_data['n_days']} days\n")
    print(f"Configuration: nbts + demand_guided  (crossover_prob=0.8)")
    print(f"  pop_size={PARAMS['pop_size']}  gene_mut_prob={PARAMS['gene_mut_prob']}  tournament_size={PARAMS['tournament_size']}\n")

    csv_path = os.path.join(OUTPUT_DIR, "final_results.csv")
    done_runs = set()
    write_mode = "w"
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                done_runs.add(int(row["run"]))
        write_mode = "a"

    csv_file = open(csv_path, write_mode, newline="")
    writer   = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    if write_mode == "w":
        writer.writeheader()

    results = []

    for run_idx in range(1, N_RUNS + 1):
        if run_idx in done_runs:
            print(f"  Run {run_idx} already completed, skipping.")
            continue

        print(f"Run {run_idx}/{N_RUNS}", end="  ", flush=True)

        t0 = time.time()
        best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, PARAMS)
        elapsed = time.time() - t0

        n_emp  = problem_data["n_employees"]
        n_days = problem_data["n_days"]
        schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
        min_unmet, ideal_unmet = _compute_penalties(schedule, problem_data)

        print(f"fitness={best_fitness:.0f}  min_unmet={min_unmet}  gen={stopped_at}  {elapsed:.0f}s")
        results.append(min_unmet)

        conv_name = f"run{run_idx}.npy"
        bests = [r["best"] for r in logbook]
        np.save(os.path.join(CONV_DIR, conv_name), np.array(bests))

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
        print(f"\n── Final Summary (crossover_prob=0.8) ──────────────────────────────")
        print(f"  Runs        : {len(results)}")
        print(f"  Best        : {min(results)} worker-days")
        print(f"  Mean        : {sum(results)/len(results):.1f} worker-days")
        print(f"  Worst       : {max(results)} worker-days")
        print(f"  Optimal gap : {min(results) - 16} worker-days above ILP optimal (16)")
    print(f"\nResults saved to '{csv_path}'")


if __name__ == "__main__":
    main()
