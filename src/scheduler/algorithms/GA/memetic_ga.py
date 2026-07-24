"""
memetic_ga.py — Memetic GA: standard evolutionary loop with one-pass local
search applied to offspring after repair (Lamarckian).

Reuses all operators from ga.py (crossover, mutation, selection, repair).
The only addition is the call to local_search_one_pass after each offspring
is repaired and evaluated — improved individuals enter the population and
guide future crossover/mutation.

Use run_memetic.py to run experiments. ga.py and run_final.py are untouched.
"""

import random
import numpy as np
from multiprocessing import Pool

from ga import (
    cx_nbts, cx_row_swap, cx_day_point,
    mut_respect_constraints, mut_swap_days, mut_demand_guided,
    select_tournament, make_individual, clone,
    _init_worker, _evaluate_worker,
    POP_SIZE, NUM_GENERATIONS, CROSSOVER_PROB, GENE_MUT_PROB,
    TOURNAMENT_SIZE, ELITE_SIZE,
)
from problem import compute_fitness, local_search_one_pass


def run_memetic_ga(problem_data, params):
    """
    Memetic GA loop. Identical to run_ga() except that after parallel repair
    + evaluation, local_search_one_pass is applied to each offspring with
    probability ls_prob (default 1.0 — all offspring improved every generation).

    Extra param beyond run_ga:
        ls_prob (float, default 1.0): fraction of offspring that receive
            one-pass LS per generation. Reduce if runtime is too high.

    Returns:
        (best_individual, best_fitness, logbook, stopped_at_gen)
    """
    pop_size             = params.get("pop_size",             POP_SIZE)
    num_generations      = params.get("num_generations",      NUM_GENERATIONS)
    crossover_prob       = params.get("crossover_prob",       CROSSOVER_PROB)
    mutation_prob        = params.get("mutation_prob",        1.0)
    gene_mut_prob        = params.get("gene_mut_prob",        GENE_MUT_PROB)
    tournament_size      = params.get("tournament_size",      TOURNAMENT_SIZE)
    elite_size           = params.get("elite_size",           ELITE_SIZE)
    early_stop_patience  = params.get("early_stop_patience",  50)
    early_stop_min_delta = params.get("early_stop_min_delta", 10)
    crossover_type       = params.get("crossover_type",       "row_swap")
    mutation_type        = params.get("mutation_type",        "respect_constraints")
    indpb_emp            = params.get("indpb_emp",            0.3)
    n_workers            = params.get("n_workers",            None)
    ls_prob              = params.get("ls_prob",              1.0)

    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]

    if crossover_type == "day_point":
        cx = lambda a, b: cx_day_point(a, b, n_emp, n_days)
    elif crossover_type == "nbts":
        cx = lambda a, b: cx_nbts(a, b, n_emp, n_days, problem_data)
    else:
        cx = lambda a, b: cx_row_swap(a, b, n_emp, n_days)

    def _eval_population(pool, individuals):
        to_eval = [ind for ind in individuals if ind["fitness"] is None]
        if not to_eval:
            return 0
        results = pool.map(_evaluate_worker, [ind["genes"] for ind in to_eval])
        total_repair = 0
        for ind, (genes, fitness, repair_changes) in zip(to_eval, results):
            ind["genes"]   = genes
            ind["fitness"] = fitness
            total_repair  += repair_changes
        return total_repair

    def _apply_ls(individuals):
        """Apply one-pass LS to each individual with probability ls_prob."""
        for ind in individuals:
            if random.random() < ls_prob:
                schedule = np.array(ind["genes"], dtype=int).reshape(n_emp, n_days)
                schedule, n = local_search_one_pass(schedule, problem_data)
                if n > 0:
                    ind["genes"]   = schedule.flatten().tolist()
                    ind["fitness"] = compute_fitness(schedule, problem_data)

    with Pool(processes=n_workers,
              initializer=_init_worker,
              initargs=(problem_data,)) as pool:

        pop = [make_individual(problem_data) for _ in range(pop_size)]
        _eval_population(pool, pop)
        _apply_ls(pop)

        hof      = clone(max(pop, key=lambda ind: ind["fitness"]))
        logbook  = []
        fitnesses = [ind["fitness"] for ind in pop]
        logbook.append({"gen": 0, "best": max(fitnesses), "mean": np.mean(fitnesses)})

        best_so_far = hof["fitness"]
        no_improve  = 0
        stopped_at  = num_generations

        for gen in range(1, num_generations + 1):
            offspring = select_tournament(pop, len(pop) - elite_size, tournament_size)
            offspring = [clone(ind) for ind in offspring]

            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < crossover_prob:
                    cx(c1, c2)

            for mutant in offspring:
                if random.random() < mutation_prob:
                    if mutation_type == "swap":
                        mut_swap_days(mutant, problem_data, indpb_emp)
                    elif mutation_type == "both":
                        mut_respect_constraints(mutant, problem_data, gene_mut_prob)
                        mut_swap_days(mutant, problem_data, indpb_emp)
                    elif mutation_type == "demand_guided":
                        mut_demand_guided(mutant, problem_data, gene_mut_prob)
                    else:
                        mut_respect_constraints(mutant, problem_data, gene_mut_prob)

            _eval_population(pool, offspring)
            _apply_ls(offspring)   # ← Memetic step: LS inside the evolutionary loop

            current_best = max(offspring, key=lambda ind: ind["fitness"])
            if current_best["fitness"] > hof["fitness"]:
                hof = clone(current_best)
            pop = [clone(hof)] + offspring

            fitnesses = [ind["fitness"] for ind in pop]
            record = {"gen": gen, "best": max(fitnesses), "mean": np.mean(fitnesses)}
            logbook.append(record)

            if record["best"] > best_so_far + early_stop_min_delta:
                best_so_far = record["best"]
                no_improve  = 0
            else:
                no_improve += 1
            if no_improve >= early_stop_patience:
                stopped_at = gen
                break

    return hof, hof["fitness"], logbook, stopped_at
