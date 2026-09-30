"""Genetic algorithm for a schema v4 package.

The evolutionary loop of `ga.py` - tournament selection, day-point crossover,
per-gene mutation, Lamarckian repair, a hall-of-fame elite and early stopping -
over the v4 encoding in `v4_encoding.py`. `ga.py` itself stays on its legacy
year-long M/T problem; nothing is imported from it, because importing it edits
sys.path and loads that problem module.

Differences from `ga.py`: individuals hold a numpy (employees x days) gene
matrix; fitness is cached per day column instead of spread over a process
pool; and `maxTime` is honoured as a wall-clock limit.
"""

from __future__ import annotations

import time
from typing import Dict, List, Optional

import numpy as np

from algorithms.GA.v4_encoding import V4Encoding
from problem_v4 import SolveDirectives
from problem_v4.runtime import finish, load_for_solver

ALGORITHM = "Genetic Algorithm v4"

GA_V4_PARAMS = {
    "pop_size": 60,
    "num_generations": 300,
    "tournament_size": 5,
    "crossover_prob": 0.8,
    "gene_mut_prob": 0.02,          # per open cell
    "early_stop_patience": 40,
}


# ── individuals and operators (the ga.py operators, on a gene matrix) ─────────

def make_individual(enc: V4Encoding, rng) -> Dict:
    genes = enc.random_genes(rng)
    enc.repair_rest(genes, rng)
    return {"genes": genes, "fitness": enc.fitness(genes)}


def clone(ind: Dict) -> Dict:
    return {"genes": ind["genes"].copy(), "fitness": ind["fitness"]}


def select_tournament(population: List[Dict], k: int, tournsize: int, rng) -> List[Dict]:
    """Draw `tournsize` individuals at random, keep the fittest; repeat k times."""
    chosen = []
    for _ in range(k):
        pool = [population[i] for i in rng.choice(len(population), size=tournsize, replace=False)]
        chosen.append(max(pool, key=lambda ind: ind["fitness"]))
    return chosen


def cx_day_point(ind1: Dict, ind2: Dict, cuts: List[int], rng) -> None:
    """Split both parents at one day and swap the tails (Maenhout & Vanhoucke's DBOP).

    Whole day columns move together, so frozen cells - equal in every parent -
    survive, and the fitness cache still knows every column.
    """
    cut = cuts[rng.integers(len(cuts))]
    tail1 = ind1["genes"][:, cut:].copy()
    ind1["genes"][:, cut:] = ind2["genes"][:, cut:]
    ind2["genes"][:, cut:] = tail1
    ind1["fitness"] = ind2["fitness"] = None


def mutate(ind: Dict, enc: V4Encoding, gene_mut_prob: float, rng) -> None:
    """Resample open cells within their domain; with the swap on, also swap work and rest in a week."""
    genes = ind["genes"]
    hits = (rng.random(genes.shape) < gene_mut_prob) & ~enc.frozen
    for e, d in zip(*np.nonzero(hits)):
        options = enc.domain[e][d]
        genes[e, d] = options[rng.integers(len(options))]
    if enc.directives.allow_day_off_swap and rng.random() < 0.5:
        e = rng.integers(enc.n_emp)
        week = enc.inst.weeks[rng.integers(len(enc.inst.weeks))]
        cells = [enc.inst.days.index(day) for day in week]
        working = [d for d in cells if genes[e, d] > 0 and not enc.frozen[e, d] and enc.may_rest[e, d]]
        resting = [d for d in cells if genes[e, d] == 0 and not enc.frozen[e, d] and len(enc.domain[e][d]) > 1]
        if working and resting:
            off, on = working[rng.integers(len(working))], resting[rng.integers(len(resting))]
            genes[e, off] = 0
            options = enc.domain[e][on][1:]
            genes[e, on] = options[rng.integers(len(options))]
    ind["fitness"] = None


# ── the loop ──────────────────────────────────────────────────────────────────

def run_ga_v4(enc: V4Encoding, params: Dict, time_limit_s: Optional[float], seed: Optional[int] = None) -> Dict:
    """Evolve and return the best individual found (its genes and fitness)."""
    rng = np.random.default_rng(seed)
    p = {**GA_V4_PARAMS, **params}
    deadline = time.monotonic() + time_limit_s if time_limit_s else None
    if enc.directives.allow_day_off_swap:
        cuts = [enc.inst.days.index(week[0]) for week in enc.inst.weeks[1:]] or [1]
    else:
        cuts = list(range(1, max(enc.n_days, 2)))

    pop = [make_individual(enc, rng) for _ in range(p["pop_size"])]
    hof = clone(max(pop, key=lambda ind: ind["fitness"]))
    best_so_far, no_improve = hof["fitness"], 0

    for _generation in range(p["num_generations"]):
        if deadline is not None and time.monotonic() > deadline:
            break
        offspring = [clone(ind) for ind in select_tournament(pop, len(pop) - 1, p["tournament_size"], rng)]
        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if rng.random() < p["crossover_prob"]:
                cx_day_point(c1, c2, cuts, rng)
        for child in offspring:
            mutate(child, enc, p["gene_mut_prob"], rng)
            enc.repair_rest(child["genes"], rng)
            child["fitness"] = enc.fitness(child["genes"])

        champion = max(offspring, key=lambda ind: ind["fitness"])
        if champion["fitness"] > hof["fitness"]:
            hof = clone(champion)
        pop = [clone(hof)] + offspring

        if hof["fitness"] > best_so_far:
            best_so_far, no_improve = hof["fitness"], 0
        else:
            no_improve += 1
            if no_improve >= p["early_stop_patience"]:
                break
    return hof


def solve(problem_path=None, maxTime=None, **kwargs):
    """TaskManager / CLI entry. kwargs: w1, w2, w3, allow_day_off_swap, seed, result_dir,
    and any GA_V4_PARAMS key (pop_size, num_generations, ...)."""
    directives = SolveDirectives.from_kwargs(kwargs)
    task_id = str(kwargs.get("task_id", "manual"))
    inst = load_for_solver(problem_path, directives, task_id, ALGORITHM)
    enc = V4Encoding(inst, directives)
    params = {k: type(GA_V4_PARAMS[k])(kwargs[k]) for k in GA_V4_PARAMS if kwargs.get(k) is not None}
    time_limit = float(maxTime) * 60 if maxTime not in (None, "") else None
    seed = int(kwargs["seed"]) if kwargs.get("seed") is not None else None
    best = run_ga_v4(enc, params, time_limit, seed)
    parts = enc.components(best["genes"])
    print(f"[{ALGORITHM}] best fitness {best['fitness']:.0f}: {parts}")
    return finish(inst, enc.rows(best["genes"]), kwargs)
