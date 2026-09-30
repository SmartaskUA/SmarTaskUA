# The v4 parser (`src/scheduler/problem_v4/`)

One parser reads a schema v4 package into one `V4Instance`, and every v4 solver works from that instance.
The same package also yields one score and one result format, whichever solver ran.

```
package dir ──► load_package() ──► V4Instance ──► solver ──► rows ──┬─► evaluate()        KPIs
               (+ partial result)                 ILP · CP-SAT ·     └─► write_package()   result.json + sidecar
                                                  Hybrid ×2 · GA                             (checked by the v4 validator)
```

## Rules

- **The parser owns meaning; solvers only reshape.** Cell grammar, which menu shift fits which day, levels,
  labour law and fixed days are decided once, in `problem_v4`. A solver turns the instance into its own
  variables (LP/CP variables, genes, greedy state) and never reads a CSV.
- **A partial result is a domain restriction.** A fixed day's candidate set shrinks to the shift the result
  names (or none, for a rest). Every solver already chooses from these sets, so none needs extra code for it.
  Without a result nothing is fixed and the code path is the same.
- **The validator is the reference.** Candidates are filtered with the validator's own `cell_conflict`,
  so every shift a solver can pick is one the validator accepts.

## Modules

| module | does |
|---|---|
| `schema_core.py` | Byte-identical copy of `json_generation/schema_v4/src/schema_v4/core.py` (the image only ships `src/scheduler/`). Guarded by `tests/test_vendored_core.py`: re-copy it, never edit it. |
| `loader.py` | `load_package(path)`: finds the problem and result by content, reads demand (alpha per slot and skill), employees, cells, the menu (synthesised when absent) and each day's candidate shifts. Raises `ParseError` listing every problem. |
| `partial.py` | Applies a partial result, checks each fixed day against its cell and the labour law, and prunes neighbouring shifts that would break the minimum rest. |
| `instance.py` | The dataclasses: `V4Instance`, `Employee`, `Shift`, `FixedDay`, `Legislation`. |
| `directives.py` | `SolveDirectives`: objective weights and the day-off swap. These are how to solve, not problem data. |
| `rows.py` | The row format every solver returns (`09:00-13:00@Responsibility/A+Team/T1`) and its parser. |
| `evaluate.py` | `evaluate(inst, rows)`: shortage, priority cost, unassigned days. The one yardstick for all solvers. |
| `result_writer.py` | `result_from_rows` / `write_package`: rows → `OutRosterTeamDays` + `result_schedules.csv`. Never writes into the input folder. |
| `runtime.py` | What a solver's `solve()` does around its model: load, report failures as `SisqualValidationError`, write the result on request. |

Shared solver code: `algorithms/md7_index.py` holds the index sets both MD7 models (ILP and CP-SAT) use,
and `algorithms/hybrid_sisqual_v4.py` holds the greedy pass both Hybrid variants use.

## Adding a v4 solver

1. `solve(problem_path, maxTime=None, **kwargs)` in `src/scheduler/algorithms/`.
2. Call `load_for_solver(problem_path, SolveDirectives.from_kwargs(kwargs), task_id, NAME)` to get the instance.
3. Choose one shift per employee-day from `inst.candidates[(employee, day)]`, with `inst.fixed_workday`
   and `inst.day_modes` telling which days must work. Cover `inst.alpha`.
4. Return rows with `format_worked_cell` / `rest_cell`, passed through `finish(inst, rows, kwargs)`.
5. Register it in `TaskManager.py` (`self.algorithms` and `V4_ALGORITHMS`), in the API's
   `SchedulingAlgorithmRegistry` (granularity `V4`), in `solve_command.V4_SOLVERS` and in the
   frontend's `V4_ALGORITHM_LABELS`.

## Tests

`src/scheduler/tests/` (`make test-scheduler`) covers the loader on the three examples and the rejections,
the scorer and writer, every solver keeping fixed days and producing valid results, and the `solve` CLI.
Why it is built this way: [ADR 0001](../adr/0001-schema-v4-solver-input.md).
