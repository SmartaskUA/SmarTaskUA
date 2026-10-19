# Genetic Algorithm for Nurse/Shift Scheduling

This module solves the employee shift scheduling problem using a **Genetic Algorithm (GA)** with a demand-guided crossover and mutation. Two variants are implemented: a **2-shift** version (`ga.py` / `problem.py`) and a **3-shift** version (`ga3.py` / `problem3.py`), sharing the same algorithmic structure.

## Problem Description

### 2-Shift Problem

Each employee is assigned one of the following genes per day:

| Gene | Meaning |
|------|---------|
| 0 | OFF (rest or vacation) |
| 1 | Morning shift, Team A |
| 2 | Afternoon shift, Team A |
| 3 | Morning shift, Team B |
| 4 | Afternoon shift, Team B |

Shared employees (cross-team) have access to genes from both teams. Single-team employees are restricted to their own team's genes plus OFF.

### 3-Shift Problem

Adds a Night shift and extends the **no-backward-shift constraint**: any transition to an earlier shift on the next day is forbidden (Night → Morning, Night → Afternoon, and Afternoon → Morning). The gene space expands to include Morning, Afternoon and Night for each team.

### Constraints

- Vacation days are always forced to OFF
- Exactly 223 working days per employee per year
- At most 5 worked days in any rolling window of 6 consecutive days
- At most 22 special days (weekends/holidays) worked per year
- Employees assigned only to their allowed teams
- No backward shift transitions: working a later shift on day *d* forbids an earlier shift on day *d+1* (2-shift: Afternoon → Morning forbidden; 3-shift: additionally Night → Morning and Night → Afternoon forbidden)
- Meet minimum staffing demand per shift/team each day

### Objectives

The fitness function combines two staffing objectives, weighted to prioritize minimum coverage:

```python
def compute_fitness(schedule: np.ndarray, problem_data: dict) -> float:
    m, i = _compute_penalties(schedule, problem_data)
    return -float(m * 100 + i * 1)
```

- **min_unmet** (`m`): number of minimum staffing slots not filled (hard objective)
- **ideal_unmet** (`i`): number of ideal staffing slots not filled (soft objective, ideal = minimum + 1)

Maximizing fitness therefore minimizes unmet demand, with minimum coverage weighted 100× over ideal coverage.

---

## Chromosome Representation

A chromosome is a flat list of `n_employees × n_days` integer genes. During evaluation it is reshaped to an `(n_employees, n_days)` schedule matrix:

```
         day 0   day 1   day 2  ...  day 364
emp 0  [  1,      0,      2,   ...,    1   ]
emp 1  [  3,      3,      0,   ...,    4   ]
...
emp N  [  0,      2,      1,   ...,    0   ]
```

Each gene encodes a (shift, team) pair or OFF. The mapping is built from `problem.json` at load time and stored in `problem_data["gene_to_shift_team"]`.

---

## Algorithm Components

### Initialization

Each individual is initialized by a greedy heuristic (`make_individual`): for each day, employees are assigned greedily to cover unmet minimum demand first, then ideal demand, with random tie-breaking among equally good choices. This produces feasible starting solutions that already address coverage gaps rather than random initializations.

### Crossover — NBTS (Need-Based Team Swap)

Adapted from Maenhout & Vanhoucke (2007). For each employee row, the crossover selects the row from whichever parent contributes more to covering the current unmet minimum demand. Coverage is updated greedily and sequentially after each employee is placed, so later decisions reflect the partial schedule already built.

Two complementary children are produced:
- **child1**: forward pass (employee 0 → N), prefers the row covering more unmet demand
- **child2**: backward pass (employee N → 0) with reversed preference, producing a meaningfully different offspring

Ties are broken randomly, preventing systematic bias toward one parent.

```python
# child1: forward greedy
cov = np.zeros_like(min_demand)
for i in range(n_emp):
    s1 = _coverage_contribution(arr1[i], cov, min_demand, ideal_demand, problem_data)
    s2 = _coverage_contribution(arr2[i], cov, min_demand, ideal_demand, problem_data)
    if s1 > s2:
        row = arr1[i]
    elif s2 > s1:
        row = arr2[i]
    else:
        row = arr1[i] if random.random() < 0.5 else arr2[i]  # random tie-break
    child1[i] = row
    _update_coverage(row, cov, problem_data)
```

### Mutation — Demand-Guided

Each gene is selected for mutation with probability `indpb` (default: 0.003). When selected:

1. The gene's current coverage contribution is removed
2. Each allowed gene for that employee on that day is scored:
   ```
   score = max(0, min_demand − coverage) × 100
           + max(0, ideal_demand − max(coverage, min_demand))
   ```
3. The gene with the highest score is chosen (random among ties). If all demand is already met (all scores = 0), a random allowed gene is chosen.

```python
# Remove old gene's coverage contribution
old_gene = individual["genes"][i * n_days + d]
if old_gene != GENE_OFF:
    coverage[d, shift_of[old_gene], team_of[old_gene]] -= 1

# Score each allowed gene
scores = []
for g in allowed_genes[i]:
    if g == GENE_OFF:
        scores.append(0)
    else:
        cov = coverage[d, shift_of[g], team_of[g]]
        mn  = min_demand[d, shift_of[g], team_of[g]]
        id_ = ideal_demand[d, shift_of[g], team_of[g]]
        scores.append(max(0, mn - cov) * 100 + max(0, id_ - max(cov, mn)))

max_score = max(scores)
chosen = (random.choice(allowed_genes[i]) if max_score == 0
          else random.choice([g for g, s in zip(allowed_genes[i], scores) if s == max_score]))
```

This steers mutation toward filling actual coverage gaps rather than making random changes.

### Selection — Tournament

Standard tournament selection: `tournsize` individuals are sampled at random and the best is selected. With `tournsize = 7`, selection pressure is high enough to favour quality while maintaining population diversity.

### Repair

After crossover and mutation, each offspring is repaired before evaluation. Five operators are applied in sequence via `repair_schedule`:

1. **Vacation repair** — any gene assigning work on a vacation day is forced to OFF:
```python
schedule[vac_mask & (schedule > GENE_OFF)] = GENE_OFF
```

2. **Backward-shift repair** — scans consecutive day pairs. If tomorrow's shift is earlier in the order than today's (e.g. Afternoon → Morning in 2-shift; additionally Night → Morning or Night → Afternoon in 3-shift), tomorrow is upgraded to today's shift tier on the same team. If the upgrade gene is not in the employee's allowed set, tomorrow is set to OFF:
```python
for i in range(n_emp):
    for d in range(n_days - 1):
        g_today, g_tomorrow = schedule[i, d], schedule[i, d + 1]
        if g_today == GENE_OFF or g_tomorrow == GENE_OFF:
            continue
        if gene_shift_order[g_tomorrow] < gene_shift_order[g_today]:
            team     = gene_to_shift_team[g_tomorrow][1]
            upgraded = shift_team_to_gene.get((gene_to_shift_team[g_today][0], team))
            schedule[i, d + 1] = (
                upgraded if (upgraded is not None and upgraded in allowed_genes[i])
                else GENE_OFF
            )
```

3. **Special days cap** — if an employee exceeds 22 special days (weekends/holidays) worked, the excess are forced to OFF, prioritising days with the highest coverage surplus.

4. **6-day window cap** — in any rolling window of 6 consecutive days, at most 5 may be worked. When violated, the worked day with highest surplus is set to OFF. Direction (forward/backward) is randomised per employee to avoid systematic end-of-year bias.

5. **Workday count** — enforces exactly 223 worked days per employee. If too many: removes the day whose (shift, team) slot has the highest surplus above ideal demand. If too few: adds constraint-safe days from a candidate pool, preferring genes that most reduce unmet ideal demand.

### Elitism

A single best individual (`hof`) is tracked across all generations. At the start of each new generation, `hof` is inserted into the population directly, guaranteeing the best solution found is never lost:

```python
pop = [clone(hof)] + offspring
```

### Early Stopping

Evolution terminates early if the best fitness does not improve by at least `early_stop_min_delta = 1` for `early_stop_patience = 100` consecutive generations, avoiding unnecessary computation after convergence.

### Evolutionary Loop

The components above connect in the following order each generation:

```python
# Initialisation
pop = [make_individual(problem_data) for _ in range(pop_size)]
evaluate_all(pop)
hof = clone(max(pop, key=fitness))

for gen in range(num_generations):
    # 1. Select pop_size - 1 parents (hof fills the remaining slot)
    offspring = select_tournament(pop, pop_size - 1, tournament_size)
    offspring = [clone(ind) for ind in offspring]

    # 2. Crossover
    for c1, c2 in zip(offspring[::2], offspring[1::2]):
        if random() < crossover_prob:
            cx_nbts(c1, c2, ...)

    # 3. Mutation
    for ind in offspring:
        mut_demand_guided(ind, problem_data, gene_mut_prob)

    # 4. Repair + evaluate (fitness set to None by cx/mut, recomputed here)
    evaluate_all(offspring)   # includes repair_schedule before fitness

    # 5. Update hall of fame
    current_best = max(offspring, key=fitness)
    if current_best.fitness > hof.fitness:
        hof = clone(current_best)

    # 6. Elitism: hof always survives into the next generation
    pop = [clone(hof)] + offspring

    # 7. Early stopping check (tracks hof fitness, not population mean)
    if hof.fitness <= best_so_far + min_delta:
        no_improve += 1
    else:
        best_so_far = hof.fitness
        no_improve  = 0
    if no_improve >= patience:
        break
```

Note that repair is applied as part of evaluation (step 4), not as a separate pass — crossover and mutation mark `fitness = None`, triggering repair + re-evaluation when the worker pool processes each offspring.

---

## Post-Processing Local Search

After the GA terminates, a deterministic local search is applied to the best schedule found. It alternates between two operators until no further improvement is possible:

### Day-Swap Operator (`local_search_ideal`)

For each employee, finds days where their current shift/team is in surplus (coverage > ideal). Checks whether moving that employee to a free deficit day reduces ideal unmet demand. The swap is accepted only when it strictly improves coverage; the employee's total workday count is preserved exactly.

```python
# For each surplus day of this employee, try every free day
for d_surplus in surplus_days:
    for d_free in free_days:
        for g in work_genes[i]:  # try each allowed work gene on d_free
            if covers_deficit(g, d_free) and constraints_ok(i, d_free, d_surplus):
                schedule[i, d_surplus] = GENE_OFF
                schedule[i, d_free]    = g
                coverage[d_surplus, ...] -= 1
                coverage[d_free, ...]    += 1
```

### Cyclic Exchange Operator (`local_search_cyclic`)

For each pair of employees (A, B): if A has a surplus day `d1` and is free on `d2`, and B has a surplus day `d2` and is free on `d1`, swap them — A moves to `d2`, B moves to `d1`, each taking the best deficit gene at their new day. Captures improvements that day-swap alone cannot find because the target day is occupied rather than free.

```python
for i, j in combinations(range(n_emp), 2):
    for d1 in surplus_days[i]:       # A is in surplus on d1
        for d2 in surplus_days[j]:   # B is in surplus on d2
            if schedule[i, d2] == GENE_OFF and schedule[j, d1] == GENE_OFF:
                g_i = best_deficit_gene(i, d2)
                g_j = best_deficit_gene(j, d1)
                if gain(g_i, d2) + gain(g_j, d1) > 0 and constraints_ok(...):
                    # apply the exchange
```

Both operators verify all constraints (vacation, backward shift, window) before applying any change. The local search only targets ideal coverage; minimum coverage is not modified.

The two operators are applied in alternation until neither produces any further improvement:

```python
while True:
    schedule, sw1 = local_search_ideal(schedule, problem_data)
    schedule, sw2 = local_search_cyclic(schedule, problem_data)
    if sw1 == 0 and sw2 == 0:
        break
```

Typical improvement: **3–8% reduction in ideal unmet** in under 5 seconds, regardless of scenario size.

---

## Configuration

The final configuration used for all reported experiments (Config C):

| Parameter | Value |
|-----------|-------|
| Population size | 200 |
| Crossover type | NBTS |
| Crossover probability | 0.8 |
| Mutation type | Demand-guided |
| Gene mutation probability | 0.003 |
| Tournament size | 7 |
| Max generations | 1000 |
| Early stop patience | 100 |
| Early stop min delta | 1 |
| Elite size | 1 |
| Runs per scenario | 10 |

---

## Project Structure

```
GA/
├── ga.py                   # GA engine (2-shift)
├── ga3.py                  # GA engine (3-shift)
├── problem.py              # Problem loader, fitness, repair, local search (2-shift)
├── problem3.py             # Problem loader, fitness, repair, local search (3-shift)
├── run_final.py            # Run 10 GA runs across all 2-shift scenarios
├── run_3shifts.py          # Run 10 GA runs across all 3-shift scenarios
├── run_postprocess.py      # Post-processing local search on 2-shift GA output
├── run_postprocess3.py     # Post-processing local search on 3-shift GA output
├── run_vac2.py             # Run GA for vacation scenarios 2, 3, 4 (2-shift, 2 teams)
├── run_postprocess_vac.py  # Post-processing for vacation scenarios 2, 3, 4
├── results_final/          # GA results for 2-shift (10 runs per scenario)
├── results_3shifts/        # GA results for 3-shift (10 runs per scenario)
└── SMARTASK_*_2025/        # Problem data directories (demand, vacations, config)
```

---

## How to Run

```bash
# 2-shift GA
python run_final.py

# 2-shift post-processing local search
python run_postprocess.py

# 3-shift GA
python run_3shifts.py

# 3-shift post-processing local search
python run_postprocess3.py
```

Results are saved to `results_final/<scenario>/` and `results_3shifts/<scenario>/` with:
- `ga_results.csv` / `results.csv` — per-run metrics (min_unmet, ideal_unmet, time, generations)
- `schedules/run*.npy` — best schedule matrix per run
- `convergence/run*.npy` — best fitness per generation per run

Each script supports **resuming**: if a run's result already exists in the CSV it is skipped automatically.
