"""
run_tuning.py — Hyperparameter tuning for the best GA configuration (nbts + demand_guided).

Grid search over:
  - pop_size:       [100, 150, 200]
  - gene_mut_prob:  [0.0005, 0.001, 0.003]
  - tournament_size:[3, 5, 7]

27 combinations × 3 runs = 81 runs total (~7 hours).

Usage:
    python run_tuning.py

Output:
    results_tuning/tuning_results.csv  — one row per run
    results_tuning/convergence/        — one npy file per run
"""

import os
import csv
import time
import itertools
import numpy as np

from problem import load_problem, _compute_penalties
from ga import run_ga

DATA_DIR   = "SMARTASK_SIMPLE_2025"
N_RUNS     = 3
OUTPUT_DIR = "results_tuning"
CONV_DIR   = os.path.join(OUTPUT_DIR, "convergence")

# Fixed operator (best from experiment phase)
CROSSOVER_TYPE = "nbts"
MUTATION_TYPE  = "demand_guided"

# Fixed params (not being tuned)
BASE_PARAMS = {
    "num_generations":      1000,
    "early_stop_patience":  50,
    "crossover_type":       CROSSOVER_TYPE,
    "mutation_type":        MUTATION_TYPE,
}

# Tuning grid
POP_SIZES       = [100, 150, 200]
GENE_MUT_PROBS  = [0.0005, 0.001, 0.003]
TOURNAMENT_SIZES = [3, 5, 7]

CSV_FIELDS = [
    "pop_size", "gene_mut_prob", "tournament_size", "run",
    "best_fitness", "min_coverage_unmet", "ideal_coverage_unmet",
    "stopped_at_gen", "elapsed_s",
]


def main():
    os.makedirs(CONV_DIR, exist_ok=True)

    print(f"Loading problem data from '{DATA_DIR}'...")
    problem_data = load_problem(DATA_DIR)
    print(f"  {problem_data['n_employees']} employees × {problem_data['n_days']} days\n")

    csv_path = os.path.join(OUTPUT_DIR, "tuning_results.csv")
    done_runs = set()
    write_mode = "w"
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                done_runs.add((
                    int(row["pop_size"]),
                    float(row["gene_mut_prob"]),
                    int(row["tournament_size"]),
                    int(row["run"]),
                ))
        write_mode = "a"

    csv_file = open(csv_path, write_mode, newline="")
    writer   = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    if write_mode == "w":
        writer.writeheader()

    combinations = list(itertools.product(POP_SIZES, GENE_MUT_PROBS, TOURNAMENT_SIZES))
    total = len(combinations) * N_RUNS
    done  = 0

    for pop_size, gene_mut_prob, tournament_size in combinations:
        print(f"── pop={pop_size}  mut={gene_mut_prob}  tourn={tournament_size} ──────────────────")

        for run_idx in range(1, N_RUNS + 1):
            if (pop_size, gene_mut_prob, tournament_size, run_idx) in done_runs:
                print(f"  Run {run_idx} already completed, skipping.")
                done += 1
                continue
            done += 1
            print(f"  Run {run_idx}/{N_RUNS}  [{done}/{total}]", end="  ", flush=True)

            params = {
                **BASE_PARAMS,
                "pop_size":        pop_size,
                "gene_mut_prob":   gene_mut_prob,
                "tournament_size": tournament_size,
            }

            t0 = time.time()
            best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, params)
            elapsed = time.time() - t0

            n_emp  = problem_data["n_employees"]
            n_days = problem_data["n_days"]
            schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
            min_unmet, ideal_unmet = _compute_penalties(schedule, problem_data)

            print(f"fitness={best_fitness:.0f}  min_unmet={min_unmet}  gen={stopped_at}  {elapsed:.0f}s")

            # Save convergence curve
            conv_name = f"pop{pop_size}__mut{gene_mut_prob}__tourn{tournament_size}__run{run_idx}.npy"
            bests = [r["best"] for r in logbook]
            np.save(os.path.join(CONV_DIR, conv_name), np.array(bests))

            writer.writerow({
                "pop_size":            pop_size,
                "gene_mut_prob":       gene_mut_prob,
                "tournament_size":     tournament_size,
                "run":                 run_idx,
                "best_fitness":        best_fitness,
                "min_coverage_unmet":  min_unmet,
                "ideal_coverage_unmet": ideal_unmet,
                "stopped_at_gen":      stopped_at,
                "elapsed_s":           round(elapsed, 1),
            })
            csv_file.flush()

        print()

    csv_file.close()
    print(f"\nDone. Results saved to '{csv_path}'")
    print(f"Convergence curves saved to '{CONV_DIR}/'")


if __name__ == "__main__":
    main()
