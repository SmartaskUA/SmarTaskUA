"""
run_experiment.py — Single entry point for all GA experiments.

Usage:
    python run_experiment.py --experiment baseline_A --runs 5
    python run_experiment.py --experiment baseline_B --runs 5

Results are saved to:
    results/<experiment_name>/
        summary.json          — mean ± std across all runs
        run_1.json … run_N.json — per-run metrics
        logbook_1.csv … logbook_N.csv — gen-by-gen fitness
        fitness_curves.png    — all runs overlaid

After running multiple experiments, generate the comparison table:
    python run_experiment.py --compare
"""

import argparse
import csv
import json
import time
from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt

from problem_ga import load_problem, repair_schedule, _compute_penalties
from ga_deap import run_ga

DATA_DIR    = "SMARTASK_SIMPLE_2025"
RESULTS_DIR = Path("results")

# ── Experiment configurations ─────────────────────────────────────────────────
EXPERIMENTS = {
    "baseline_A": {
        "description": (
            "Literature-standard GA — random init, fixed rates. "
            "Params from timetabling literature (pop=100, cx=0.8, mut=0.01, tourn=3)."
        ),
        "pop_size":             100,
        "num_generations":      200,
        "crossover_prob":       0.8,
        "mutation_prob":        1.0,
        "gene_mut_prob":        0.01,
        "tournament_size":      3,
        "elite_size":           1,
        "early_stop_patience":  30,
        "early_stop_min_delta": 10,
    },
    "baseline_B": {
        "description": (
            "OFAT-tuned GA — random init, fixed rates. "
            "Parameters tuned via OFAT starting from Baseline A (pop=150, mut=0.003, tourn=7)."
        ),
        "pop_size":             150,
        "num_generations":      200,
        "crossover_prob":       0.8,
        "mutation_prob":        1.0,
        "gene_mut_prob":        0.003,
        "tournament_size":      7,
        "elite_size":           1,
        "early_stop_patience":  30,
        "early_stop_min_delta": 10,
    },
    # ── Experiment 1a: Day-Point crossover ────────────────────────────────────
    "exp1a_daypoint_cx": {
        "description": (
            "Day-Point crossover — column-wise split at random day D. "
            "Ref: Patel et al. 2025 (ECAI); Maenhout & Vanhoucke 2007 (DBOP). "
            "All other params identical to Baseline B."
        ),
        "crossover_type":       "day_point",
        "pop_size":             150,
        "num_generations":      200,
        "crossover_prob":       0.8,
        "mutation_prob":        1.0,
        "gene_mut_prob":        0.003,
        "tournament_size":      7,
        "elite_size":           1,
        "early_stop_patience":  30,
        "early_stop_min_delta": 10,
    },
    # ── Experiment 1b: NBTS crossover ─────────────────────────────────────────
    "exp1b_nbts_cx": {
        "description": (
            "Nurse-Based Tournament Selection crossover — greedily picks the "
            "employee row that covers more unmet demand. "
            "Ref: Maenhout & Vanhoucke 2007 (NBTS). "
            "All other params identical to Baseline B."
        ),
        "crossover_type":       "nbts",
        "pop_size":             150,
        "num_generations":      200,
        "crossover_prob":       0.8,
        "mutation_prob":        1.0,
        "gene_mut_prob":        0.003,
        "tournament_size":      7,
        "elite_size":           1,
        "early_stop_patience":  30,
        "early_stop_min_delta": 10,
    },
    # ── Experiment 2: Swap mutation ────────────────────────────────────────────
    "exp2_swap_mutation": {
        "description": (
            "Swap mutation — two random non-vacation days per employee are swapped "
            "instead of random gene replacement. Less destructive, allows higher "
            "per-employee rate (0.3). "
            "Ref: Maenhout & Vanhoucke 2007. "
            "All other params identical to Baseline B."
        ),
        "mutation_type":        "swap",
        "indpb_emp":            0.3,
        "pop_size":             150,
        "num_generations":      200,
        "crossover_prob":       0.8,
        "mutation_prob":        1.0,
        "gene_mut_prob":        0.003,   # unused for swap, kept for consistency
        "tournament_size":      7,
        "elite_size":           1,
        "early_stop_patience":  30,
        "early_stop_min_delta": 10,
    },
    "exp2b_swap_05": {
        "description": "Swap mutation indpb_emp=0.5 — ~6 employees swapped per individual. Baseline B params.",
        "mutation_type": "swap", "indpb_emp": 0.5,
        "pop_size": 150, "num_generations": 200, "crossover_prob": 0.8,
        "mutation_prob": 1.0, "gene_mut_prob": 0.003, "tournament_size": 7,
        "elite_size": 1, "early_stop_patience": 30, "early_stop_min_delta": 10,
    },
    "exp2c_swap_07": {
        "description": "Swap mutation indpb_emp=0.7 — ~8 employees swapped per individual. Baseline B params.",
        "mutation_type": "swap", "indpb_emp": 0.7,
        "pop_size": 150, "num_generations": 200, "crossover_prob": 0.8,
        "mutation_prob": 1.0, "gene_mut_prob": 0.003, "tournament_size": 7,
        "elite_size": 1, "early_stop_patience": 30, "early_stop_min_delta": 10,
    },
    # ── Experiment 2d: Demand-guided mutation ─────────────────────────────────
    "exp2d_demand_guided_mut": {
        "description": (
            "Demand-guided mutation — same indpb as gene_replacement (0.003) but "
            "picks the gene that best covers unmet demand on that day instead of "
            "random. Falls back to random when demand is fully met. "
            "All other params identical to Baseline B."
        ),
        "mutation_type":        "demand_guided",
        "pop_size":             150,
        "num_generations":      200,
        "crossover_prob":       0.8,
        "mutation_prob":        1.0,
        "gene_mut_prob":        0.003,
        "tournament_size":      7,
        "elite_size":           1,
        "early_stop_patience":  30,
        "early_stop_min_delta": 10,
    },
    # ── Future experiments ─────────────────────────────────────────────────────
    # "exp3_greedy_init": { ... },
    # "exp4_overinit":    { ... },
    # "exp5_combined":    { ... },
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def compute_coverage_metrics(best_ind, problem_data):
    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]
    sched  = np.array(best_ind, dtype=int).reshape(n_emp, n_days)
    sched  = repair_schedule(sched, problem_data)
    m, i   = _compute_penalties(sched, problem_data)
    return int(m), int(i)


def run_single(run_id, problem_data, params, out_dir):
    print(f"    Run {run_id}...", end=" ", flush=True)
    t0 = time.time()

    best_ind, best_fitness, logbook, stopped_at = run_ga(problem_data, params)

    elapsed     = time.time() - t0
    min_unmet, ideal_unmet = compute_coverage_metrics(best_ind, problem_data)

    result = {
        "run_id":         run_id,
        "best_fitness":   float(best_fitness),
        "min_unmet":      min_unmet,
        "ideal_unmet":    ideal_unmet,
        "stopped_at_gen": stopped_at,
        "elapsed_s":      round(elapsed, 1),
    }

    # Logbook CSV
    log_rows = [{"gen": r["gen"], "best": r["best"], "mean": r["mean"]} for r in logbook]
    with open(out_dir / f"logbook_{run_id}.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["gen", "best", "mean"])
        writer.writeheader()
        writer.writerows(log_rows)

    # Per-run JSON
    with open(out_dir / f"run_{run_id}.json", "w") as f:
        json.dump(result, f, indent=2)

    print(
        f"fitness={best_fitness:.0f}  min_unmet={min_unmet}  "
        f"stopped_gen={stopped_at}  ({elapsed:.1f}s)"
    )
    return result, logbook


def save_summary(experiment_name, params, all_results, out_dir):
    fitnesses   = [r["best_fitness"]   for r in all_results]
    min_unmets  = [r["min_unmet"]      for r in all_results]
    ideal_unmets= [r["ideal_unmet"]    for r in all_results]
    stop_gens   = [r["stopped_at_gen"] for r in all_results]
    elapsed_all = [r["elapsed_s"]      for r in all_results]

    summary = {
        "experiment":  experiment_name,
        "description": EXPERIMENTS[experiment_name]["description"],
        "n_runs":      len(all_results),
        "params":      params,
        "fitness": {
            "mean":   round(float(np.mean(fitnesses)),   2),
            "std":    round(float(np.std(fitnesses)),    2),
            "min":    round(float(np.min(fitnesses)),    2),
            "max":    round(float(np.max(fitnesses)),    2),
            "values": fitnesses,
        },
        "min_unmet": {
            "mean":   round(float(np.mean(min_unmets)),  2),
            "std":    round(float(np.std(min_unmets)),   2),
            "values": min_unmets,
        },
        "ideal_unmet": {
            "mean":   round(float(np.mean(ideal_unmets)), 2),
            "std":    round(float(np.std(ideal_unmets)),  2),
            "values": ideal_unmets,
        },
        "stopped_at_gen": {
            "mean":   round(float(np.mean(stop_gens)),  1),
            "values": stop_gens,
        },
        "elapsed_s": {
            "mean":  round(float(np.mean(elapsed_all)), 1),
            "total": round(float(np.sum(elapsed_all)),  1),
        },
    }

    with open(out_dir / "summary.json", "w") as f:
        json.dump(summary, f, indent=2)

    return summary


def plot_fitness_curves(all_logbooks, all_results, summary, out_dir):
    n_runs = len(all_logbooks)
    fig, ax = plt.subplots(figsize=(10, 4))
    colors  = plt.cm.Blues(np.linspace(0.4, 0.9, n_runs))

    for idx, (lb, col) in enumerate(zip(all_logbooks, colors)):
        gens  = lb.select("gen")
        bests = lb.select("best")
        ax.plot(gens, bests, color=col, linewidth=1.0, alpha=0.8,
                label=f"Run {idx+1}  (best={all_results[idx]['best_fitness']:.0f})")

    ax.set_xlabel("Generation")
    ax.set_ylabel("Fitness")
    ax.set_title(
        f"{summary['experiment']} — {n_runs} runs  "
        f"(mean={summary['fitness']['mean']:.0f} ± {summary['fitness']['std']:.0f})"
    )
    ax.legend(fontsize=8, loc="lower right")
    fig.tight_layout()
    fig.savefig(out_dir / "fitness_curves.png", dpi=120)
    plt.close(fig)


def print_summary(summary):
    f = summary["fitness"]
    m = summary["min_unmet"]
    s = summary["stopped_at_gen"]
    e = summary["elapsed_s"]
    print(f"\n  {'─'*50}")
    print(f"  Experiment : {summary['experiment']}")
    print(f"  Runs       : {summary['n_runs']}")
    print(f"  Fitness    : {f['mean']:.0f} ± {f['std']:.0f}"
          f"   (best {f['max']:.0f}, worst {f['min']:.0f})")
    print(f"  Min unmet  : {m['mean']:.1f} ± {m['std']:.1f} worker-days")
    print(f"  Stopped    : gen {s['mean']:.0f} avg")
    print(f"  Time       : {e['mean']:.1f}s avg  ({e['total']:.0f}s total)")
    print(f"  {'─'*50}")


# ── Comparison table ──────────────────────────────────────────────────────────

def build_comparison_table():
    """Read all summary.json files and write results/comparison_table.csv."""
    rows = []
    for exp_dir in sorted(RESULTS_DIR.iterdir()):
        summary_file = exp_dir / "summary.json"
        if not summary_file.exists():
            continue
        with open(summary_file) as f:
            s = json.load(f)
        rows.append({
            "experiment":        s["experiment"],
            "n_runs":            s["n_runs"],
            "fitness_mean":      s["fitness"]["mean"],
            "fitness_std":       s["fitness"]["std"],
            "fitness_best":      s["fitness"]["max"],
            "min_unmet_mean":    s["min_unmet"]["mean"],
            "min_unmet_std":     s["min_unmet"]["std"],
            "stopped_gen_mean":  s["stopped_at_gen"]["mean"],
            "elapsed_s_mean":    s["elapsed_s"]["mean"],
        })

    if not rows:
        print("No summary.json files found in results/.")
        return

    out_path = RESULTS_DIR / "comparison_table.csv"
    with open(out_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nComparison table saved → {out_path}")
    print(f"\n{'Experiment':<25} {'Fitness mean':>14} {'± std':>8} {'min_unmet':>10}")
    print("─" * 62)
    for r in rows:
        print(
            f"  {r['experiment']:<23} {r['fitness_mean']:>14.0f} "
            f"{r['fitness_std']:>8.0f} {r['min_unmet_mean']:>10.1f}"
        )


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--experiment", "-e",
        choices=list(EXPERIMENTS.keys()),
        help="Which experiment to run",
    )
    parser.add_argument("--runs",    "-r", type=int, default=5, help="Number of runs (default: 5)")
    parser.add_argument("--compare", "-c", action="store_true", help="Build comparison table from all saved results")
    args = parser.parse_args()

    if args.compare:
        build_comparison_table()
        return

    if not args.experiment:
        parser.print_help()
        print(f"\nAvailable experiments: {list(EXPERIMENTS.keys())}")
        return

    exp_name = args.experiment
    params   = {k: v for k, v in EXPERIMENTS[exp_name].items() if k not in ("description",)}
    out_dir  = RESULTS_DIR / exp_name
    out_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print(f"  {exp_name}")
    print(f"  {EXPERIMENTS[exp_name]['description']}")
    print(f"  {args.runs} runs × {params['num_generations']} generations"
          f"  (pop={params['pop_size']})")
    print("=" * 60)

    problem_data = load_problem(DATA_DIR)

    all_results  = []
    all_logbooks = []

    for run_id in range(1, args.runs + 1):
        result, logbook = run_single(run_id, problem_data, params, out_dir)
        all_results.append(result)
        all_logbooks.append(logbook)

    summary = save_summary(exp_name, params, all_results, out_dir)
    plot_fitness_curves(all_logbooks, all_results, summary, out_dir)
    print_summary(summary)

    print(f"\n  Results saved → {out_dir}/")
    print(f"  Run 'python run_experiment.py --compare' to update the comparison table.")


if __name__ == "__main__":
    main()
