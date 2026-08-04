"""
run_3shifts.py — Multi-run experiment across all 3-shift scenarios.

Scenarios (all use shifts M, T, N):
    SMARTASK_3SHIFTS_2TEAMS_2025   (24  employees,  2 teams)
    SMARTASK_3SHIFTS_4TEAMS_2025   (48  employees,  4 teams)
    SMARTASK_3SHIFTS_8TEAMS_2025   (96  employees,  8 teams)
    SMARTASK_3SHIFTS_16TEAMS_2025  (192 employees, 16 teams)
    SMARTASK_3SHIFTS_32TEAMS_2025  (384 employees, 32 teams)

Config: nbts + demand_guided, pop=200, patience=100 (Config C, best from 2-shift tuning).

Output:
    results_3shifts/<scenario>/results.csv
    results_3shifts/<scenario>/convergence/run*.npy
    results_3shifts/summary.csv
"""

import os
import csv
import time
import numpy as np

from problem3 import load_problem, _compute_penalties, compute_phase2_violations
from ga3 import run_ga

DATA_DIR = os.path.join(os.path.dirname(__file__), "../../../../data/problems")

SCENARIOS = [
    ("SMARTASK_3SHIFTS_2TEAMS_2025",  3),
    ("SMARTASK_3SHIFTS_4TEAMS_2025",  3),
    ("SMARTASK_3SHIFTS_8TEAMS_2025",  3),
    ("SMARTASK_3SHIFTS_16TEAMS_2025",  2),
    ("SMARTASK_3SHIFTS_32TEAMS_2025",  2),
]

PARAMS = {
    "crossover_type":      "nbts",
    "mutation_type":       "demand_guided",
    "pop_size":            200,
    "gene_mut_prob":       0.003,
    "tournament_size":     7,
    "crossover_prob":      0.8,
    "num_generations":     1000,
    "early_stop_patience": 100,
}

CSV_FIELDS = [
    "run", "best_fitness", "min_coverage_unmet", "ideal_coverage_unmet",
    "stopped_at_gen", "elapsed_s",
    "viol_vacation", "viol_workday", "viol_window", "viol_special", "viol_backward",
]

SUMMARY_FIELDS = [
    "scenario", "n_teams", "n_employees",
    "mean_min_unmet", "std_min_unmet", "best_min_unmet", "worst_min_unmet",
    "mean_elapsed_s", "n_runs",
]


def run_scenario(scenario: str, n_runs: int, summary_rows: list) -> None:
    data_path  = os.path.join(DATA_DIR, scenario)
    output_dir = os.path.join("results_3shifts", scenario)
    conv_dir   = os.path.join(output_dir, "convergence")
    os.makedirs(conv_dir, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  {scenario}  ({n_runs} runs)")
    print(f"{'='*60}")

    problem_data = load_problem(data_path)
    n_emp   = problem_data["n_employees"]
    n_days  = problem_data["n_days"]
    n_teams = len(problem_data["teams"])
    print(f"  {n_teams} teams | {n_emp} employees | {n_days} days")
    print(f"  pop={PARAMS['pop_size']}  patience={PARAMS['early_stop_patience']}  "
          f"crossover={PARAMS['crossover_type']}  mutation={PARAMS['mutation_type']}\n")

    csv_path     = os.path.join(output_dir, "results.csv")
    min_results  = []
    elapsed_list = []

    with open(csv_path, "w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
        writer.writeheader()

        for run_idx in range(1, n_runs + 1):
            print(f"  Run {run_idx}/{n_runs} ...", flush=True)

            t0 = time.time()
            best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, PARAMS)
            elapsed = time.time() - t0

            schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
            min_unmet, ideal_unmet = _compute_penalties(schedule, problem_data)
            v = compute_phase2_violations(schedule, problem_data)

            print(f"    fitness={best_fitness:.0f}  min_unmet={min_unmet}  "
                  f"gen={stopped_at}  {elapsed:.0f}s")

            min_results.append(min_unmet)
            elapsed_list.append(elapsed)

            np.save(os.path.join(conv_dir, f"run{run_idx}.npy"),
                    np.array([r["best"] for r in logbook]))

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

    mean_u = np.mean(min_results)
    std_u  = np.std(min_results)
    print(f"\n  Best={min(min_results)}  Mean={mean_u:.1f}  Worst={max(min_results)}  "
          f"Std={std_u:.1f}  AvgTime={np.mean(elapsed_list):.0f}s")
    print(f"  Results → {csv_path}")

    summary_rows.append({
        "scenario":       scenario,
        "n_teams":        n_teams,
        "n_employees":    n_emp,
        "mean_min_unmet": round(mean_u, 2),
        "std_min_unmet":  round(std_u, 2),
        "best_min_unmet": min(min_results),
        "worst_min_unmet": max(min_results),
        "mean_elapsed_s": round(np.mean(elapsed_list), 1),
        "n_runs":         n_runs,
    })


def main():
    print("SmarTask — 3-Shift GA Experiment")
    print(f"Scenarios: {len(SCENARIOS)} | Config C (pop=200, patience=100)")

    summary_rows = []

    for scenario, n_runs in SCENARIOS:
        run_scenario(scenario, n_runs, summary_rows)

    os.makedirs("results_3shifts", exist_ok=True)
    summary_path = os.path.join("results_3shifts", "summary.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_FIELDS)
        writer.writeheader()
        writer.writerows(summary_rows)

    print(f"\n{'='*60}")
    print(f"  SUMMARY")
    print(f"{'='*60}")
    print(f"  {'Scenario':<35} {'teams':>5} {'mean':>6} {'std':>5} {'best':>5} {'worst':>6}")
    print(f"  {'-'*60}")
    for r in summary_rows:
        print(f"  {r['scenario']:<35} {r['n_teams']:>5} "
              f"{r['mean_min_unmet']:>6.1f} {r['std_min_unmet']:>5.1f} "
              f"{r['best_min_unmet']:>5} {r['worst_min_unmet']:>6}")
    print(f"\n  Summary → {summary_path}")


if __name__ == "__main__":
    main()
