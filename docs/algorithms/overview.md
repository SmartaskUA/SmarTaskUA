# Algorithms Overview

## Available Algorithms

SmarTask supports 11 scheduling algorithms with different approaches and performance characteristics.

| Algorithm Name | Type | Description |
|----------------|------|-------------|
| **CSP** | Constraint Satisfaction | Uses Google OR-Tools CP-SAT solver to find feasible schedules |
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

## Algorithm Types

**Constraint Satisfaction (CSP):** Finds schedules that satisfy all hard constraints. Best for complex constraint problems.

**Integer Linear Programming (ILP):** Optimizes an objective function while satisfying constraints. Good for optimization problems.

**Heuristic (Greedy):** Fast assignment using greedy rules. Quick but may not find optimal solutions.

**Local Search (Hill Climbing):** Improves solutions iteratively. Good for refinement.

**Hybrid:** Combines multiple approaches for better results.

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
