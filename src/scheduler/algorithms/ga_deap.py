"""
ga_deap.py — Shift scheduling GA using DEAP.

Key difference vs PyGAD:
  - Row-swap crossover: swaps entire employee schedules between parents.
    This preserves each worker's vacation pattern and shift structure,
    producing more meaningful offspring than gene-by-gene crossover.
  - Custom mutation: respects per-employee team constraints and vacation mask.
  - Same fitness function and data as ga_pygad.py (shared problem.py).

Run:
    python ga_deap.py
"""

import time
import random
import numpy as np
import matplotlib.pyplot as plt
from deap import base, creator, tools

from problem import (
    load_problem, compute_fitness, random_schedule,
    decode_schedule, print_summary, export_schedule, repair_schedule, GENE_OFF,
)

DATA_DIR = "SMARTASK_SIMPLE_2025"

# ── GA hyper-parameters (tuned via 2-round OFAT, March 2026) ─────────────────
NUM_GENERATIONS  = 200
POP_SIZE         = 80     # baseline: 30  → tuned: 80
CROSSOVER_PROB   = 0.8  # VER baseline: 0.5 → tuned: 0.8 (crossover is more effective with row-swap)
MUTATION_PROB    = 1.0  
GENE_MUT_PROB    = 0.003  # baseline: 0.05 → tuned: 0.003
TOURNAMENT_SIZE  = 5      # baseline: 3   → tuned: 5
ELITE_SIZE       = 1


# ── Custom genetic operators ──────────────────────────────────────────────────

def cx_row_swap(ind1, ind2, n_emp, n_days):
    """
    Given two parent chromosomes, it loops over each employee row. For each row,
    with 50% chance, it swaps the entire row between the two parents. So child 1
    gets some employees from parent 1 and some from parent 2. This preserves each
    employee's vacation pattern and shift continuity — a standard gene-by-gene
    crossover would mix days from different employees which makes no structural sense.
    """
    for i in range(n_emp):
        if random.random() < 0.5:
            start, end = i * n_days, (i + 1) * n_days
            ind1[start:end], ind2[start:end] = (
                ind2[start:end][:],
                ind1[start:end][:],
            )
    return ind1, ind2


def mut_respect_constraints(individual, problem_data, indpb):
    """
    Mutation: each gene is replaced with a random allowed value with
    probability indpb. Vacation days are always reset to OFF.
    Team constraints are respected via each employee's allowed_genes.
    """
    n_emp         = problem_data["n_employees"]
    n_days        = problem_data["n_days"]
    vac_mask      = problem_data["vac_mask"]
    allowed_genes = problem_data["allowed_genes"]

    for i in range(n_emp):
        for d in range(n_days):
            if random.random() < indpb:
                idx = i * n_days + d
                if vac_mask[i, d]:
                    individual[idx] = GENE_OFF
                else:
                    individual[idx] = random.choice(allowed_genes[i])
    return (individual,)


# ── DEAP setup ────────────────────────────────────────────────────────────────

def build_toolbox(problem_data, tournament_size=TOURNAMENT_SIZE, gene_mut_prob=GENE_MUT_PROB):
    # Avoid re-creating if already registered 
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)

    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]

    toolbox = base.Toolbox()

    # Individual factory: flatten a random valid schedule into a list
    def make_individual():
        return creator.Individual(random_schedule(problem_data).flatten().tolist())

    toolbox.register("individual", make_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)

    # Fitness — repair for evaluation only (Baldwinian: chromosome is NOT modified)
    def eval_fitness(individual):
        schedule = np.array(individual, dtype=int).reshape(n_emp, n_days)
        schedule = repair_schedule(schedule, problem_data)   # Phase 2 hard constraints
        return (compute_fitness(schedule, problem_data),)

    toolbox.register("evaluate", eval_fitness)

    # Crossover: row-swap (pre-bind n_emp and n_days)
    toolbox.register("mate", cx_row_swap, n_emp=n_emp, n_days=n_days)

    # Mutation: constraint-respecting random gene replacement
    toolbox.register(
        "mutate", mut_respect_constraints,
        problem_data=problem_data,
        indpb=gene_mut_prob,
    )

    # Selection: tournament
    toolbox.register("select", tools.selTournament, tournsize=tournament_size)

    return toolbox


# ── Core GA runner ────────────────────────────────────────────────────────────

def run_ga(problem_data, params):
    """
    Run the evolutionary loop and return results.

    Args:
        problem_data: dict from load_problem()
        params: dict of hyperparameters (all optional, fall back to module constants):
            pop_size, num_generations, crossover_prob, mutation_prob,
            gene_mut_prob, tournament_size, elite_size,
            early_stop_patience (default 30), early_stop_min_delta (default 10)

    Returns:
        (best_individual, best_fitness, logbook, stopped_at_gen)
    """
    pop_size          = params.get("pop_size",          POP_SIZE)
    num_generations   = params.get("num_generations",   NUM_GENERATIONS)
    crossover_prob    = params.get("crossover_prob",    CROSSOVER_PROB)
    mutation_prob     = params.get("mutation_prob",     MUTATION_PROB)
    gene_mut_prob     = params.get("gene_mut_prob",     GENE_MUT_PROB)
    tournament_size   = params.get("tournament_size",   TOURNAMENT_SIZE)
    elite_size        = params.get("elite_size",        ELITE_SIZE)
    early_stop_patience  = params.get("early_stop_patience",  30)
    early_stop_min_delta = params.get("early_stop_min_delta", 10)

    toolbox = build_toolbox(problem_data, tournament_size=tournament_size, gene_mut_prob=gene_mut_prob)

    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("best", np.max)
    stats.register("mean", np.mean)

    hof = tools.HallOfFame(1)

    # Generate and evaluate initial population
    pop = toolbox.population(n=pop_size) # create 80 random chromosomes  
    fitnesses = list(map(toolbox.evaluate, pop)) # evaluate all of them
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit # store fitness score in each individual
    hof.update(pop) # hall of fame: remember the best one seen so far

    logbook = tools.Logbook()
    logbook.header = ["gen", "best", "mean"]

    record = stats.compile(pop)
    logbook.record(gen=0, **record)

    # Early stopping state
    best_so_far = max(ind.fitness.values[0] for ind in pop)
    no_improve  = 0
    stopped_at  = num_generations

    for gen in range(1, num_generations + 1):
        """
        Tournament selection: picks 79 individuals (80 - 1 elite slot) from the current
        population. In tournament selection, you randomly pick 5 individuals, the best one
        wins, repeat 79 times. The same individual can be picked more than once. This is
        how selection pressure works — better individuals get picked more often.
        """
        offspring = toolbox.select(pop, len(pop) - elite_size)

        """
        DEAP works with references, not copies. If you don't clone, modifying an offspring
        would also modify the original in pop. Cloning makes independent copies so crossover
        and mutation don't corrupt the current population.
        """
        offspring = list(map(toolbox.clone, offspring))

        # Crossover
        """
        Takes pairs of offspring (1+2, 3+4, 5+6...). Each pair has 80% chance of being crossed.
        cx_row_swap swaps employee rows between them. After crossing, their fitness scores are
        deleted — they are now different chromosomes and need to be re-evaluated.
        """
        for c1, c2 in zip(offspring[::2], offspring[1::2]):
            if random.random() < crossover_prob: # 80% chance
                toolbox.mate(c1, c2)
                del c1.fitness.values # mark fitness as invalid
                del c2.fitness.values

        # Mutation
        """
        Every single offspring goes through mutation (100% probability). But inside
        mut_respect_constraints, each individual gene only mutates with probability 0.003.
        So mutation always runs, but very few genes actually change. Same as before,
        fitness is deleted after mutation.
        """
        for mutant in offspring:
            if random.random() < mutation_prob:
                toolbox.mutate(mutant)
                del mutant.fitness.values

        # Evaluate only individuals whose fitness is now invalid
        invalid = [ind for ind in offspring if not ind.fitness.valid]
        for ind, fit in zip(invalid, map(toolbox.evaluate, invalid)):
            ind.fitness.values = fit

        # Elitism: always carry the all-time best into the new population
        pop[:] = [toolbox.clone(hof[0])] + offspring
        hof.update(pop)

        record = stats.compile(pop)
        logbook.record(gen=gen, **record)

        # Early stopping check
        """
        After each generation, check if the best fitness improved by more than 10 points.
        If not, increment a counter. If 30 consecutive generations pass without meaningful
        improvement, stop. This avoids wasting time when the algorithm has already converged.
        """
        current_best = record["best"]
        if current_best > best_so_far + early_stop_min_delta:
            best_so_far = current_best
            no_improve  = 0
        else:
            no_improve += 1
        if no_improve >= early_stop_patience:
            stopped_at = gen
            break

    best_ind     = hof[0]
    best_fitness = hof[0].fitness.values[0]

    return best_ind, best_fitness, logbook, stopped_at


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  SmarTask — Shift Scheduling GA  (DEAP)")
    print("=" * 55)

    # ── Load data ─────────────────────────────────────────────────────────────
    print("\nLoading problem data...")
    pd_data = load_problem(DATA_DIR)
    n_emp   = pd_data["n_employees"]
    n_days  = pd_data["n_days"]
    n_genes = n_emp * n_days
    print(f"  Employees : {n_emp}")
    print(f"  Days      : {n_days}")
    print(f"  Genes     : {n_genes} per chromosome")

    # ── Run GA ────────────────────────────────────────────────────────────────
    print(f"\nRunning {NUM_GENERATIONS} generations (pop={POP_SIZE})...")
    t0 = time.time()

    best_ind, best_fitness, logbook, stopped_at = run_ga(pd_data, {})

    elapsed = time.time() - t0

    if stopped_at < NUM_GENERATIONS:
        print(f"  Early stopping triggered at generation {stopped_at}")

    # ── Log output ────────────────────────────────────────────────────────────
    print("\nGeneration log (every 20 generations):")
    for record in logbook:
        if record["gen"] % 20 == 0 or record["gen"] == 1:
            print(
                f"  Gen {record['gen']:>3} | "
                f"best: {record['best']:.0f} | "
                f"mean: {record['mean']:.0f}"
            )

    # ── Results ───────────────────────────────────────────────────────────────
    best_schedule = np.array(best_ind, dtype=int).reshape(n_emp, n_days)
    best_schedule = repair_schedule(best_schedule, pd_data)   # apply Phase 2 before export

    print(f"\nCompleted in {elapsed:.1f}s")
    print_summary(best_schedule, pd_data, label="DEAP — Best Schedule")
    export_schedule(best_schedule, pd_data, path="schedule_deap.csv")

    # ── Plot ──────────────────────────────────────────────────────────────────
    gens  = logbook.select("gen")
    bests = logbook.select("best")
    means = logbook.select("mean")

    plt.figure(figsize=(10, 4))
    plt.plot(gens, bests, color="steelblue",  linewidth=1.5, label="Best fitness")
    plt.plot(gens, means, color="darkorange", linewidth=1.0,
             linestyle="--", label="Mean fitness")
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title("DEAP — Fitness over Generations (row-swap crossover)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("deap_fitness.png", dpi=120)
    print("Plot saved → deap_fitness.png")
    plt.show()


if __name__ == "__main__":
    main()
