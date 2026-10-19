"""
run_postprocess_vac.py — Post-processing on GA schedules for vacation scenarios 2, 3 and 4.

Reads from results_vac2/<scenario>/schedules/ and writes pp_results.csv
to the same folder. Logic identical to run_postprocess.py.

Run AFTER run_vac2.py has completed.

Usage:
    python run_postprocess_vac.py
"""

import os
import csv
import time
import numpy as np

from problem import load_problem, _compute_penalties, local_search_ideal, local_search_cyclic

SCENARIOS = [
    "SMARTASK_SIMPLE_2025_VAC2",
    "SMARTASK_SIMPLE_2025_VAC3",
    "SMARTASK_SIMPLE_2025_VAC4",
]

CSV_FIELDS = [
    "run", "ideal_unmet_ga", "ideal_unmet_pp", "improvement",
    "ls_swaps", "elapsed_s",
]


def postprocess_scenario(data_dir):
    base_dir  = os.path.join("results_vac2", data_dir)
    sched_dir = os.path.join(base_dir, "schedules")

    if not os.path.isdir(sched_dir):
        print(f"  No schedules found for {data_dir} — run run_vac2.py first.")
        return

    print(f"\n{'='*56}")
    print(f"  {data_dir} — post-processing")
    print(f"{'='*56}")

    problem_data = load_problem(data_dir)
    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]
    print(f"  {n_emp} employees × {n_days} days\n")

    csv_path   = os.path.join(base_dir, "pp_results.csv")
    done_runs  = set()
    write_mode = "w"
    if os.path.exists(csv_path):
        with open(csv_path, newline="") as f:
            for row in csv.DictReader(f):
                done_runs.add(int(row["run"]))
        write_mode = "a"

    pp_ideals = []
    csv_file  = open(csv_path, write_mode, newline="")
    writer    = csv.DictWriter(csv_file, fieldnames=CSV_FIELDS)
    if write_mode == "w":
        writer.writeheader()

    sched_files = sorted(
        f for f in os.listdir(sched_dir) if f.startswith("run") and f.endswith(".npy")
    )

    for fname in sched_files:
        run_idx = int(fname.replace("run", "").replace(".npy", ""))
        if run_idx in done_runs:
            print(f"  Run {run_idx:2d} already done, skipping.")
            continue

        schedule = np.load(os.path.join(sched_dir, fname))
        _, ideal_ga = _compute_penalties(schedule, problem_data)

        print(f"  Run {run_idx:2d}", end="  ", flush=True)
        t0 = time.time()

        total_swaps = 0
        s = schedule
        while True:
            s, sw1 = local_search_ideal(s, problem_data)
            s, sw2 = local_search_cyclic(s, problem_data)
            total_swaps += sw1 + sw2
            if sw1 == 0 and sw2 == 0:
                break
        schedule_pp = s

        elapsed = time.time() - t0
        _, ideal_pp = _compute_penalties(schedule_pp, problem_data)
        improvement = ideal_ga - ideal_pp
        pp_ideals.append(ideal_pp)

        print(f"ideal {ideal_ga}→{ideal_pp} (Δ{improvement})  swaps={total_swaps}  {elapsed:.1f}s")

        writer.writerow({
            "run":            run_idx,
            "ideal_unmet_ga": ideal_ga,
            "ideal_unmet_pp": ideal_pp,
            "improvement":    improvement,
            "ls_swaps":       total_swaps,
            "elapsed_s":      round(elapsed, 2),
        })
        csv_file.flush()

    csv_file.close()

    if pp_ideals:
        print(f"\n  Summary (after PP): best={min(pp_ideals)}  "
              f"mean={sum(pp_ideals)/len(pp_ideals):.1f}  worst={max(pp_ideals)}")
    print(f"  Saved to '{csv_path}'")


def main():
    for data_dir in SCENARIOS:
        postprocess_scenario(data_dir)


if __name__ == "__main__":
    main()
