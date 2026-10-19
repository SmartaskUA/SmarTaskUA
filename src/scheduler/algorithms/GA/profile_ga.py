"""
profile_ga.py — Measure time per generation with and without multiprocessing.

Usage:
    python profile_ga.py [scenario]
"""

import cProfile
import pstats
import io
import os
import sys
import time

if __name__ == "__main__":
    SCENARIO = sys.argv[1] if len(sys.argv) > 1 else "SMARTASK_4TEAMS_2025"

    # auto-detect 3-shift scenario
    if "3SHIFTS" in SCENARIO:
        from problem3 import load_problem
        from ga3 import run_ga
    else:
        from problem import load_problem
        from ga import run_ga

    PARAMS_BASE = {
        "crossover_type":      "nbts",
        "mutation_type":       "demand_guided",
        "pop_size":            200,
        "gene_mut_prob":       0.003,
        "tournament_size":     7,
        "crossover_prob":      0.8,
        "num_generations":     30,
        "early_stop_patience": 999,
    }

    problem_data = load_problem(SCENARIO)
    n_emp   = problem_data["n_employees"]
    n_teams = len(problem_data["teams"])
    print(f"Scenario : {SCENARIO}")
    print(f"Size     : {n_teams} teams, {n_emp} employees")
    print(f"Gens     : {PARAMS_BASE['num_generations']}  pop={PARAMS_BASE['pop_size']}\n")

    # ── 1. With multiprocessing (current default) ─────────────────────
    print("── Test 1: multiprocessing Pool (n_workers=None → all cores) ──")
    t0 = time.time()
    run_ga(problem_data, {**PARAMS_BASE, "n_workers": None})
    t_parallel = time.time() - t0
    print(f"   Total: {t_parallel:.1f}s  →  {t_parallel/PARAMS_BASE['num_generations']:.2f}s/gen\n")

    # ── 2. Sequential (n_workers=1 disables Pool parallelism) ─────────
    print("── Test 2: sequential (n_workers=1) ───────────────────────────")
    t0 = time.time()
    run_ga(problem_data, {**PARAMS_BASE, "n_workers": 1})
    t_seq = time.time() - t0
    print(f"   Total: {t_seq:.1f}s  →  {t_seq/PARAMS_BASE['num_generations']:.2f}s/gen\n")

    speedup = t_seq / t_parallel
    print(f"── Result ─────────────────────────────────────────────────────")
    print(f"   Parallel: {t_parallel:.1f}s   Sequential: {t_seq:.1f}s")
    print(f"   Speedup : {speedup:.2f}x  ({'parallel wins' if speedup > 1 else 'sequential wins — Pool overhead dominates'})")

    # ── 3. cProfile on sequential run (cleaner, no IPC noise) ─────────
    print("\n── cProfile (sequential, top 25 by tottime) ───────────────────")
    pr = cProfile.Profile()
    pr.enable()
    run_ga(problem_data, {**PARAMS_BASE, "n_workers": 1, "num_generations": 20})
    pr.disable()

    stream = io.StringIO()
    pstats.Stats(pr, stream=stream).sort_stats("tottime").print_stats(25)
    print(stream.getvalue())
