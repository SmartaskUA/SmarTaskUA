"""
run_nteams.py — Multi-run experiment for 4, 8, and 16 teams.

Configuration: nbts + demand_guided (best known config from 2-team experiments)
Hyperparameters: same as run_final_08.py

Runs per scenario:
    4 teams  → 10 runs
    8 teams  → 10 runs
    16 teams →  5 runs  (baseline only; hyperparameters may need tuning)

Output per scenario:
    results_nteams/<scenario>/results.csv
    results_nteams/<scenario>/convergence/run1.npy ...
"""

import os
import csv
import time
import numpy as np

from problem import load_problem, _compute_penalties, compute_phase2_violations
from ga import run_ga

SCENARIOS = [
    ("SMARTASK_4TEAMS_2025",  10),
    ("SMARTASK_8TEAMS_2025",  10),
    ("SMARTASK_16TEAMS_2025",  5),
]

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
    "viol_vacation", "viol_workday", "viol_window", "viol_special", "viol_backward",
]


def run_scenario(scenario: str, n_runs: int):
    output_dir = os.path.join("results_nteams", scenario)
    conv_dir   = os.path.join(output_dir, "convergence")
    os.makedirs(conv_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {scenario}  ({n_runs} runs)")
    print(f"{'='*60}")

    problem_data = load_problem(scenario)
    n_emp   = problem_data["n_employees"]
    n_days  = problem_data["n_days"]
    n_teams = len(problem_data["teams"])
    print(f"  {n_teams} teams | {n_emp} employees | {n_days} days")
    print(f"  pop={PARAMS['pop_size']}  gen={PARAMS['num_generations']}  "
          f"crossover={PARAMS['crossover_prob']}  mut={PARAMS['gene_mut_prob']}")

    csv_path = os.path.join(output_dir, "results.csv")
    min_results = []
    with open(csv_path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for run_idx in range(1, n_runs + 1):
            print(f"\n  Run {run_idx}/{n_runs} ...", flush=True)

            t0 = time.time()
            best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, PARAMS)
            elapsed = time.time() - t0

            schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
            min_unmet, ideal_unmet = _compute_penalties(schedule, problem_data)
            v = compute_phase2_violations(schedule, problem_data)

            print(f"  fitness={best_fitness:.0f}  "
                  f"min_unmet={min_unmet}  ideal_unmet={ideal_unmet}  "
                  f"gen={stopped_at}  {elapsed:.0f}s")

            min_results.append(min_unmet)
            np.save(
                os.path.join(conv_dir, f"run{run_idx}.npy"),
                np.array([r["best"] for r in logbook]),
            )
            writer.writerow({
                "run":                  run_idx,
                "best_fitness":         best_fitness,
                "min_coverage_unmet":   min_unmet,
                "ideal_coverage_unmet": ideal_unmet,
                "stopped_at_gen":       stopped_at,
                "elapsed_s":            round(elapsed, 1),
                "viol_vacation":        v["vacation"],
                "viol_workday":         v["workday"],
                "viol_window":          v["window"],
                "viol_special":         v["special"],
                "viol_backward":        v["backward"],
            })
            csv_file.flush()

    print(f"\n  ── Summary ──────────────────────────────────────────")
    print(f"  Best  : {min(min_results)} worker-days")
    print(f"  Mean  : {sum(min_results)/len(min_results):.1f} worker-days")
    print(f"  Worst : {max(min_results)} worker-days")
    print(f"  Results saved → {csv_path}")


def main():
    print("SmarTask — N-Teams GA Experiment")
    print(f"Config: {PARAMS['crossover_type']} + {PARAMS['mutation_type']}")

    for scenario, n_runs in SCENARIOS:
        run_scenario(scenario, n_runs)

    print("\nAll scenarios complete.")


if __name__ == "__main__":
    main()
