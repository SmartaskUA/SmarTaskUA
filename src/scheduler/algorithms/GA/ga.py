"""
ga.py — Shift scheduling GA (no external EA library).

Crossover operators available (set via crossover_type param in run_ga):
  - "row_swap"  : uniform row-swap — each employee row swapped with 50% prob (default)
  - "day_point" : Day-Point crossover — cut at random day D, column-wise split
                  (Patel et al. 2025 / Maenhout & Vanhoucke 2007 — DBOP)
  - "nbts"      : Nurse-Based Tournament Selection — greedily picks the row from
                  whichever parent covers more unmet demand
                  (Maenhout & Vanhoucke 2007 — NBTS)

Run:
    python ga.py
"""

import sys
import time
import random
import numpy as np
from multiprocessing import Pool
from pathlib import Path

# Ensure problem.py is importable regardless of working directory
sys.path.insert(0, str(Path(__file__).parent))

from problem import (
    load_problem, compute_fitness, random_schedule,
    decode_schedule, print_summary, export_schedule, repair_schedule,
    GENE_OFF, SHIFTS, SHIFT_IDX,
)

DATA_DIR = "SMARTASK_SIMPLE_2025"

# ── GA hyper-parameters (tuned via 2-round OFAT, March 2026) ─────────────────
NUM_GENERATIONS  = 1000
POP_SIZE         = 150
CROSSOVER_PROB   = 0.5
MUTATION_PROB    = 1.0  
GENE_MUT_PROB    = 0.001 #0.001
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
            ind1["genes"][start:end], ind2["genes"][start:end] = (
                ind2["genes"][start:end][:],
                ind1["genes"][start:end][:],
            )
    ind1["fitness"] = None
    ind2["fitness"] = None
    return ind1, ind2


def cx_day_point(ind1, ind2, n_emp, n_days):
    """
    Day-Point crossover (Patel et al. 2025 / Maenhout & Vanhoucke 2007 — DBOP).

    Selects a random day D. The schedule is split column-wise at D:
      child1 takes days 0..D-1 from parent1, days D..end from parent2.
      child2 takes the complement.

    Every employee is split at the same day D, so each employee's complete
    shift pattern within each half-year is preserved. The no-backward-shift
    constraint may be violated at the junction day D but is fixed by
    repair_schedule during fitness evaluation.
    """
    D = random.randint(1, n_days - 1)

    arr1 = np.array(ind1["genes"]).reshape(n_emp, n_days)
    arr2 = np.array(ind2["genes"]).reshape(n_emp, n_days)

    child1 = np.hstack([arr1[:, :D], arr2[:, D:]])
    child2 = np.hstack([arr2[:, :D], arr1[:, D:]])

    ind1["genes"] = child1.flatten().tolist()
    ind2["genes"] = child2.flatten().tolist()
    ind1["fitness"] = None
    ind2["fitness"] = None
    return ind1, ind2


def _coverage_contribution(row_arr, coverage, min_demand, ideal_demand, problem_data):
    """
    Score how much this employee's row helps cover unmet demand.
    - Each day below minimum counts W_MIN (100) — matches the fitness weight.
    - Each day below ideal but above minimum counts W_IDEAL (1).
    """
    # O4 — single np.where on the row, then lookup arrays for shift/team indices
    days = np.where(row_arr != GENE_OFF)[0]
    if not len(days):
        return 0
    genes = row_arr[days]
    s_arr = problem_data["gene_shift_arr"][genes]
    t_arr = problem_data["gene_team_arr"][genes]
    cov   = coverage[days, s_arr, t_arr]
    mn    = min_demand[days, s_arr, t_arr]
    id_   = ideal_demand[days, s_arr, t_arr]
    return int(np.sum(np.maximum(0, mn - cov)) * 100 +
               np.sum(np.maximum(0, id_ - np.maximum(cov, mn))))


def _update_coverage(row_arr, coverage, problem_data):
    """Add one employee row's worked assignments to the running coverage array."""
    # O3 — single np.where on the row, then np.add.at with lookup arrays
    days = np.where(row_arr != GENE_OFF)[0]
    if len(days):
        genes = row_arr[days]
        np.add.at(coverage,
                  (days,
                   problem_data["gene_shift_arr"][genes],
                   problem_data["gene_team_arr"][genes]),
                  1)


def cx_nbts(ind1, ind2, n_emp, n_days, problem_data):
    """
    Nurse-Based Tournament Selection crossover (Maenhout & Vanhoucke 2007 — NBTS).

    For each employee row, selects the row from whichever parent contributes
    more to covering the current unmet minimum demand. The selection is greedy
    and sequential: coverage is updated after each employee is assigned, so
    later decisions reflect the partial schedule already built.

    child1 evaluates employees forward  (0 → n_emp-1).
    child2 evaluates employees backward (n_emp-1 → 0) with reversed preference,
    producing a meaningfully different second offspring.
    """
    min_demand   = problem_data["min_demand"]    # (n_days, 2, 2)
    ideal_demand = problem_data["ideal_demand"]  # (n_days, 2, 2)

    arr1 = np.array(ind1["genes"]).reshape(n_emp, n_days)
    arr2 = np.array(ind2["genes"]).reshape(n_emp, n_days)

    child1 = np.empty((n_emp, n_days), dtype=int)
    child2 = np.empty((n_emp, n_days), dtype=int)

    # child1: forward greedy — pick the row that covers more unmet demand.
    # Ties broken randomly so later employees (after minimum is met) don't
    # always default to the same parent.
    cov1 = np.zeros_like(min_demand)
    for i in range(n_emp):
        s1  = _coverage_contribution(arr1[i], cov1, min_demand, ideal_demand, problem_data)
        s2  = _coverage_contribution(arr2[i], cov1, min_demand, ideal_demand, problem_data)
        if s1 > s2:
            row = arr1[i]
        elif s2 > s1:
            row = arr2[i]
        else:
            row = arr1[i] if random.random() < 0.5 else arr2[i]  # random tie-break
        child1[i] = row
        _update_coverage(row, cov1, problem_data)

    # child2: backward greedy with reversed preference — different evaluation
    # order yields a different partial coverage context at each step, so the
    # same parent rows may be ranked differently, producing a distinct child.
    cov2 = np.zeros_like(min_demand)
    for i in range(n_emp - 1, -1, -1):
        s1  = _coverage_contribution(arr1[i], cov2, min_demand, ideal_demand, problem_data)
        s2  = _coverage_contribution(arr2[i], cov2, min_demand, ideal_demand, problem_data)
        if s2 > s1:
            row = arr2[i]
        elif s1 > s2:
            row = arr1[i]
        else:
            row = arr2[i] if random.random() < 0.5 else arr1[i]  # random tie-break
        child2[i] = row
        _update_coverage(row, cov2, problem_data)

    ind1["genes"] = child1.flatten().tolist()
    ind2["genes"] = child2.flatten().tolist()
    ind1["fitness"] = None
    ind2["fitness"] = None
    return ind1, ind2

# cromossoma - horario inteiro
# gene 0,1,2,3,4
"""
Mutação implementada de raiz.

  O que faz atualmente:
  - Cada gene muda com probabilidade 0.003
  - Se é dia de férias → força OFF
  - Se não → escolhe aleatoriamente um gene válido do allowed_genes[i] do empregado

Novas técnicas de mutação que podes propor na reunião:

  1. Swap mutation — troca dois dias aleatórios do mesmo empregado entre si. Mantém o número de dias trabalhados exato.
  2. Shift-change mutation — em vez de mudar para qualquer gene, só muda o turno (M↔T) mantendo a equipa. Exploração mais localizada.
  3. Block mutation — em vez de genes individuais, muta um bloco contíguo de dias de um empregado. Mais disruptivo que gene a gene.
  
"""

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
                    individual["genes"][idx] = GENE_OFF
                else:
                    individual["genes"][idx] = random.choice(allowed_genes[i])
    individual["fitness"] = None


def mut_swap_days(individual, problem_data, indpb_emp):
    """
    Swap mutation: for each employee, with probability indpb_emp, two random
    non-vacation days are selected and their gene values swapped.
    Preserves the number of worked days exactly — rearranges the schedule
    rather than randomising it, so it is less disruptive than gene replacement.
    """
    n_emp    = problem_data["n_employees"]
    n_days   = problem_data["n_days"]
    vac_mask = problem_data["vac_mask"]

    for i in range(n_emp):
        if random.random() < indpb_emp:
            non_vac = [d for d in range(n_days) if not vac_mask[i, d]]
            if len(non_vac) < 2:
                continue
            d1, d2 = random.sample(non_vac, 2)
            idx1 = i * n_days + d1
            idx2 = i * n_days + d2
            individual["genes"][idx1], individual["genes"][idx2] = (
                individual["genes"][idx2], individual["genes"][idx1]
            )
    individual["fitness"] = None


def mut_demand_guided(individual, problem_data, indpb):
    """
    Demand-guided mutation: each gene is selected for mutation with probability
    indpb. When selected, instead of picking a random allowed gene, picks the
    gene that most covers unmet demand on that day (minimum first, then ideal).
    Falls back to random choice when all demand is already met.
    Coverage is computed once and updated after each gene change.
    """
    n_emp              = problem_data["n_employees"]
    n_days             = problem_data["n_days"]
    vac_mask           = problem_data["vac_mask"]
    allowed_genes      = problem_data["allowed_genes"]
    min_demand         = problem_data["min_demand"]
    ideal_demand       = problem_data["ideal_demand"]
    gene_to_shift_team = problem_data["gene_to_shift_team"]
    team_idx           = problem_data["team_idx"]
    gene_shift_arr     = problem_data["gene_shift_arr"]
    gene_team_arr      = problem_data["gene_team_arr"]
    n_teams            = len(problem_data["teams"])

    schedule = np.array(individual["genes"], dtype=int).reshape(n_emp, n_days)

    # O6 — build initial coverage vectorised
    coverage = np.zeros((n_days, len(SHIFTS), n_teams), dtype=int)
    emp_i, day_j = np.where(schedule != GENE_OFF)
    if len(emp_i):
        genes_present = schedule[emp_i, day_j]
        np.add.at(coverage,
                  (day_j, gene_shift_arr[genes_present], gene_team_arr[genes_present]),
                  1)

    # O5 — mutation mask generated upfront; vac days already excluded
    mut_mask  = (np.random.random((n_emp, n_days)) < indpb) & ~vac_mask
    positions = np.argwhere(mut_mask)

    for i, d in positions:
        idx = i * n_days + d

        # Remove current gene's contribution from coverage
        old_gene = individual["genes"][idx]
        if old_gene != GENE_OFF:
            coverage[d, SHIFT_IDX[gene_to_shift_team[old_gene][0]],
                        team_idx[gene_to_shift_team[old_gene][1]]] -= 1

        # Score each allowed gene by how much it covers unmet demand
        emp_genes = allowed_genes[i]
        scores    = []
        for g in emp_genes:
            if g == GENE_OFF:
                scores.append(0)
            else:
                s_idx = SHIFT_IDX[gene_to_shift_team[g][0]]
                t_idx = team_idx[gene_to_shift_team[g][1]]
                cov   = coverage[d, s_idx, t_idx]
                mn    = int(min_demand[d, s_idx, t_idx])
                id_   = int(ideal_demand[d, s_idx, t_idx])
                scores.append(max(0, mn - cov) * 100 + max(0, id_ - max(cov, mn)))

        max_score = max(scores)
        if max_score == 0:
            chosen = random.choice(emp_genes)
        else:
            chosen = random.choice([g for g, s in zip(emp_genes, scores)
                                    if s == max_score])

        individual["genes"][idx] = chosen
        if chosen != GENE_OFF:
            coverage[d, SHIFT_IDX[gene_to_shift_team[chosen][0]],
                        team_idx[gene_to_shift_team[chosen][1]]] += 1

    individual["fitness"] = None


# ── Selection ─────────────────────────────────────────────────────────────────

def select_tournament(population, k, tournsize):
    """
    Tournament selection: draw tournsize individuals at random, return the
    best. Repeat k times (with replacement across draws).
    """
    chosen = []
    for _ in range(k):
        pool = random.sample(population, tournsize)
        chosen.append(max(pool, key=lambda ind: ind["fitness"]))
    return chosen


# ── Evaluation ────────────────────────────────────────────────────────────────

def evaluate(individual, problem_data):
    """
    Repair (Lamarckian — repaired chromosome written back) then compute fitness.
    The individual's genes are updated in-place so crossover and mutation
    always operate on valid chromosomes.
    Returns (fitness, total_repair_changes).
    """
    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]
    schedule = np.array(individual["genes"], dtype=int).reshape(n_emp, n_days)
    schedule, changes = repair_schedule(schedule, problem_data, debug=True)
    individual["genes"] = schedule.flatten().tolist()
    return compute_fitness(schedule, problem_data), sum(changes.values())


# ── Individual helpers ────────────────────────────────────────────────────────

def make_individual(problem_data):
    return {"genes": random_schedule(problem_data).flatten().tolist(), "fitness": None}


def clone(ind):
    return {"genes": ind["genes"][:], "fitness": ind["fitness"]}


# ── Parallel evaluation helpers ───────────────────────────────────────────────
# Defined after evaluate() so the worker process can resolve the name on import.
# problem_data is loaded once per worker via the pool initializer — not
# re-serialised on every individual evaluation call.

_worker_problem_data = None

def _init_worker(problem_data):
    global _worker_problem_data
    _worker_problem_data = problem_data

def _evaluate_worker(genes):
    """Repair + fitness for one individual. Runs inside a worker process."""
    individual = {"genes": genes, "fitness": None}
    individual["fitness"], repair_changes = evaluate(individual, _worker_problem_data)
    return individual["genes"], individual["fitness"], repair_changes


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
    early_stop_patience  = params.get("early_stop_patience",  50)
    early_stop_min_delta = params.get("early_stop_min_delta", 10)
    crossover_type       = params.get("crossover_type",       "row_swap")
    mutation_type        = params.get("mutation_type",        "respect_constraints")
    indpb_emp            = params.get("indpb_emp",            0.3)
    n_workers            = params.get("n_workers",            None)  # None = all cores

    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]

    # Select crossover operator
    if crossover_type == "day_point":
        cx = lambda a, b: cx_day_point(a, b, n_emp, n_days)
    elif crossover_type == "nbts":
        cx = lambda a, b: cx_nbts(a, b, n_emp, n_days, problem_data)
    else:
        cx = lambda a, b: cx_row_swap(a, b, n_emp, n_days)

    def _eval_population(pool, individuals):
        """Evaluate a list of individuals in parallel (only those with fitness=None)."""
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

    with Pool(processes=n_workers,
              initializer=_init_worker,
              initargs=(problem_data,)) as pool:

        # Generate and evaluate initial population
        pop = [make_individual(problem_data) for _ in range(pop_size)]
        _eval_population(pool, pop)

        # Hall of fame — single best individual seen across all generations
        hof = max(pop, key=lambda ind: ind["fitness"])
        hof = clone(hof)

        logbook = []
        fitnesses = [ind["fitness"] for ind in pop]
        logbook.append({"gen": 0, "best": max(fitnesses), "mean": np.mean(fitnesses)})

        # Early stopping state
        best_so_far = hof["fitness"]
        no_improve  = 0
        stopped_at  = num_generations

        for gen in range(1, num_generations + 1):
            # Tournament selection: picks pop_size - elite_size individuals.
            # Randomly draws tournsize candidates, best one wins. Repeat k times.
            # Better individuals win more often — this is selection pressure.
            offspring = select_tournament(pop, len(pop) - elite_size, tournament_size)

            # Clone so crossover/mutation don't corrupt the current population.
            offspring = [clone(ind) for ind in offspring]

            # Crossover: pair up offspring, each pair has crossover_prob chance of mating.
            # Operators set fitness=None on modified individuals.
            for c1, c2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < crossover_prob:
                    cx(c1, c2)

            # Mutation: every offspring runs through mutation (probability=1.0).
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

            # Evaluate only individuals whose fitness was invalidated.
            total_repair = _eval_population(pool, offspring)
            # print(f"  [debug] gen {gen:4d} | repair changes: {total_repair}") # DEBUG

            # Elitism: always carry the all-time best into the new population.
            current_best = max(offspring, key=lambda ind: ind["fitness"])
            if current_best["fitness"] > hof["fitness"]:
                hof = clone(current_best)
            pop = [clone(hof)] + offspring

            fitnesses = [ind["fitness"] for ind in pop]
            record = {"gen": gen, "best": max(fitnesses), "mean": np.mean(fitnesses)}
            logbook.append(record)

            # Early stopping: halt if no meaningful improvement for patience generations.
            if record["best"] > best_so_far + early_stop_min_delta:
                best_so_far = record["best"]
                no_improve  = 0
            else:
                no_improve += 1
            if no_improve >= early_stop_patience:
                stopped_at = gen
                break

    return hof, hof["fitness"], logbook, stopped_at


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("=" * 55)
    print("  SmarTask — Shift Scheduling GA")
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

    params = {}
    best_ind, best_fitness, logbook, stopped_at = run_ga(pd_data, params)

    crossover_type = params.get("crossover_type", "row_swap")
    mutation_type  = params.get("mutation_type",  "respect_constraints")

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
    best_schedule = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)

    print(f"\nCompleted in {elapsed:.1f}s")
    print_summary(best_schedule, pd_data, label="Best Schedule")
    export_schedule(best_schedule, pd_data, path="schedule_ga.csv")

    # ── Plot ──────────────────────────────────────────────────────────────────
    import matplotlib.pyplot as plt
    gens  = [r["gen"]  for r in logbook]
    bests = [r["best"] for r in logbook]
    means = [r["mean"] for r in logbook]

    plt.figure(figsize=(10, 4))
    plt.plot(gens, bests, color="steelblue",  linewidth=1.5, label="Best fitness")
    plt.plot(gens, means, color="darkorange", linewidth=1.0,
             linestyle="--", label="Mean fitness")
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title(f"Fitness over Generations ({crossover_type} crossover, {mutation_type} mutation)")
    plt.legend()
    plt.tight_layout()
    plt.savefig("ga_fitness.png", dpi=120)
    print("Plot saved → ga_fitness.png")
    plt.show()


# ── TaskManager entry point ───────────────────────────────────────────────────

_GA_PARAMS = {
    "crossover_type":      "nbts",
    "mutation_type":       "demand_guided",
    "pop_size":            200,
    "gene_mut_prob":       0.003,
    "tournament_size":     7,
    "crossover_prob":      0.8,
    "num_generations":     1000,
    "early_stop_patience": 50,
}


def solve(problem_path, maxTime=None, **kwargs):
    """
    TaskManager-compatible entry point for the Genetic Algorithm.

    Args:
        problem_path: path to a SMARTASK scenario directory
                      (must contain problem.json, vacations.csv, demand.csv)
        maxTime:      ignored — GA uses early stopping instead
    Returns:
        list of lists: [header_row, emp1_row, ...]
        header: ["funcionario", "Dia 1", ..., "Dia 365"]
        cells:  "M_A" / "T_B" (worked), "F" (vacation), "0" (rest)
    """
    path = Path(str(problem_path))
    if path.is_file():
        path = path.parent
    problem_data = load_problem(str(path))

    best_ind, _, _, _ = run_ga(problem_data, _GA_PARAMS)

    n_emp  = problem_data["n_employees"]
    n_days = problem_data["n_days"]
    schedule           = np.array(best_ind["genes"], dtype=int).reshape(n_emp, n_days)
    gene_to_shift_team = problem_data["gene_to_shift_team"]
    vac_mask           = problem_data["vac_mask"]

    header = ["funcionario"] + [f"Dia {d}" for d in range(1, n_days + 1)]
    output = [header]
    for i in range(n_emp):
        row = [i + 1]
        for d in range(n_days):
            g = schedule[i, d]
            if g == GENE_OFF:
                row.append("F" if vac_mask[i, d] else "0")
            else:
                shift, team = gene_to_shift_team[g]
                row.append(f"{shift}_{team}")
        output.append(row)
    return output


if __name__ == "__main__":
    main()
