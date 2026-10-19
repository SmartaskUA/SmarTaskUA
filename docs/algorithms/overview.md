# Algorithms

Every algorithm is registered in `src/scheduler/TaskManager.py`. For each problem, the API reports which
algorithms can solve it, and the UI offers only those. How to run them: [how-to-solve.md](../how-to-solve.md).

## Schema v4 solvers (current)

They read v4 packages through the [v4 parser](../architecture/v4-parser.md), honour partial results, and are
scored by the same `problem_v4.evaluate`.

| name | CLI alias | method |
|---|---|---|
| `ILP_Sisqual_Hours_MathematicalDefinition7` | `ilp` | MathematicalDefinition7 as an ILP (PuLP + CBC); optimal on the examples in seconds |
| `CSP_Sisqual_Hours_MathematicalDefinition7` | `csp` | the same model in OR-Tools CP-SAT |
| `Hybrid_Heuristic_Sisqual_3` | `hybrid` | greedy block assignment, restarts over three day orders |
| `Hybrid_Heuristic_Sisqual_Levels_Included` | `hybrid-levels` | the same greedy, preferring higher-priority skills and levels |
| `Genetic Algorithm v4` | `ga` | one gene per employee-day; fixed days are frozen genes |

The `…MathematicalDefinition5` names are aliases of the MD7 pair. Benchmark: [ADR 0001](../adr/0001-schema-v4-solver-input.md).

## Legacy families (v2.x inputs)

These read v2.x bundles or the vacation/minimum templates, over a full year with M/T/N shifts. None reads v4.
The last column says what each would need to.

| family | members | what reading v4 would take |
|---|---|---|
| General | `ILP General`, `CSP General`, `Heuristic General` ([flow](general-algorithms-flow.md)) | calendar from `temporalScope`; `x[e][d][h]` over menu candidates; per-axis slot coverage; labour law as windows + weekly count + minute rest. The result is MD7, so retire for v4 |
| Rules engines | `CSP_ENGINE`, `ILP Engine`, `Greedy Randomized Engine`, `GRHC_ENGINE` | currently broken (stale `..rules.handlers` imports). The rule → per-backend handler pattern suits v4 labour law: contexts gain candidates, fixed days and slot demand |
| Shift ILP / CSP | `linear programming`, `linear programming 2`, `CSP`, `CSPv2`, `ilp_greedy` | as General |
| Hour blocks | `ILP_2`–`ILP_4`, `COP_1`/`COP_2` (and `_Half_Intervals`), `CSP_Afonso_Hours` | blocks from the menu, demand on the slot grid, the horizon calendar. They are MD7's predecessors: do not port |
| Shift heuristics | `hill climbing`, `Greedy Randomized` (+ `Hill Climbing`), `Heuristic Solver`, `Hybrid_Heuristic`, `R2_Heuristic`, `Puzzle_Heuristic`, `Heuristica_1` | state per employee-day = a candidate shift; fixed days seeded first. `Puzzle_Heuristic` is the most promising port: its weekly patterns match v4's weekly caps |
| GA 2/3-shift | `Genetic Algorithm 2-Shift`, `Genetic Algorithm 3-Shift` | superseded by `Genetic Algorithm v4` |
| Sisqual v2.2 | `ILP_Sisqual_Hours`, `CSP_Sisqual_Hours`, `Puzzle_Sisqual` | retire; the v4 solvers replace them |

## Adding an algorithm

A v4 solver: [v4-parser.md](../architecture/v4-parser.md#adding-a-v4-solver). A legacy solver receives
`vacations, minimuns, employees, maxTime, year, shifts, rules` and is registered in `TaskManager.py` and the
API's `SchedulingAlgorithmRegistry`.
