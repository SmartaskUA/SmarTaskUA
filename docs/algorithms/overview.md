# Algorithms Overview

## Available Algorithms

SmarTask ships a range of scheduling algorithms with different approaches and performance characteristics. All are registered in `src/scheduler/TaskManager.py` (the `algorithms` dictionary); the primary ones are grouped by family below.

### General family (constraint-driven, read `problem.json`)

These consume the structured `constraints` from a `problem.json` (parsed into a `ConstraintPlan`) instead of the global `rules.json`, and are the focus of the flow docs (`docs/algorithms/general-algorithms-flow.md`).

| Algorithm Name | Type | Description |
|----------------|------|-------------|
| **ILP General** | Integer Linear Programming | General ILP solver driven by the `problem.json` constraint plan |
| **CSP General** | Constraint Satisfaction | General CP-SAT solver driven by the `problem.json` constraint plan |
| **Heuristic General** | Heuristic | General heuristic solver driven by the `problem.json` constraint plan |

### Classic families

| Algorithm Name | Type | Description |
|----------------|------|-------------|
| **CSP** (alias *CSP Scheduling*) | Constraint Satisfaction | Google OR-Tools CP-SAT solver to find feasible schedules |
| **CSPv2** | Constraint Satisfaction | Enhanced version of CSP with additional optimizations |
| **CSP_ENGINE** | Constraint Satisfaction | CSP with integrated rules engine for complex constraints |
| **linear programming** | Integer Linear Programming | ILP solver using PuLP library for optimization |
| **linear programming 2** | Integer Linear Programming | Alternative ILP implementation |
| **ILP Engine** | Integer Linear Programming | ILP with integrated rules engine |
| **Greedy Randomized** | Heuristic | Fast randomized greedy assignment approach |
| **Greedy Randomized Engine** | Heuristic | Greedy with rules engine integration |
| **Greedy Randomized + Hill Climbing** | Hybrid | Combines greedy initial solution with local search refinement |
| **GRHC_ENGINE** | Hybrid | Greedy + Hill Climbing with rules engine |
| **hill climbing** | Local Search | Iterative improvement through neighbor exploration |

### Experimental / hourly / legacy variants

`TaskManager.py` also registers interval- and hour-based experiments and dataset-specific solvers that are **not** part of the main flow: `ILP_2`, `ILP_3`, `ILP_4` (each with a `_Half_Intervals` variant), `ILP_Sisqual_Hours`, `CSP_Sisqual_Hours`, `CSP_Afonso_Hours`, and `ilp_greedy`. Treat these as experimental.

## Algorithm Types

**Constraint Satisfaction (CSP):** Finds schedules that satisfy all hard constraints. Best for complex constraint problems.

**Integer Linear Programming (ILP):** Optimizes an objective function while satisfying constraints. Good for optimization problems.

**Heuristic (Greedy):** Fast assignment using greedy rules. Quick but may not find optimal solutions.

**Local Search (Hill Climbing):** Improves solutions iteratively. Good for refinement.

**Hybrid:** Combines multiple approaches for better results.

**General (constraint-driven):** The `* General` solvers read the structured `constraints` block from `problem.json` (parsed into a `ConstraintPlan`) rather than the global `rules.json`. See `docs/algorithms/general-algorithms-flow.md`.

**Engine Variants:** Algorithms with "_ENGINE" or "Engine" suffix integrate the rules engine for better constraint handling.

## When to Use

- **Need fast results:** Greedy Randomized
- **Need optimal solutions:** CSP, ILP variants
- **Complex constraints:** CSP_ENGINE, ILP Engine
- **Balance speed/quality:** Hybrid algorithms (GRHC_ENGINE)
- **Refinement:** Hill Climbing on existing schedules

## Performance Considerations

- **CSP/ILP:** Slower but more thorough (may take minutes for large problems)
- **Greedy:** Fast (seconds) but less optimal
- **Hybrid:** Medium speed, good balance
- **maxTime parameter:** Limits algorithm execution time

## Implementation Details

- All algorithms defined in `src/scheduler/TaskManager.py`
- Algorithm implementations in `src/scheduler/algorithms/`
- Each algorithm receives: vacations, minimums, employees, maxTime, year, shifts, rules
- Results saved to MongoDB `schedules` collection
- General algorithms JSON flow: See `docs/algorithms/general-algorithms-flow.md`

## Adding New Algorithms

See `docs/development/getting-started.md` for instructions on adding new algorithms.

**Note:** Algorithm developers can expand this documentation with detailed implementation notes, pseudocode, or performance benchmarks.
