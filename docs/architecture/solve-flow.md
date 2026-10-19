# Solve flow: from a click to a stored schedule

How a solve request travels through the services. Code references are `file → symbol`.

## Schema v4 (current)

```
Browser ─► nginx /api ─► API ──RabbitMQ task-queue──► Scheduler ─► MongoDB schedules ─► API ─► Browser
                          │                             │
                          └── data/problems/ (bind-mounted into api and scheduler) ──┘
```

1. **Upload** (optional). `POST /problems/upload` receives the wizard's ZIP. The API checks its shape and
   writes it to `data/problems/uploads/<problemId>/`.
   `ProblemsController → uploadProblem`, `ProblemPackageImporter → importZip`.
2. **List.** `GET /problems` returns each problem with `schemaVersion`, its period, its employee count and
   the `algorithms` that can solve it. The frontend offers exactly those.
   `ProblemService → parseProblemListItem`, `SchedulingAlgorithmRegistry → problemAlgorithms` (granularity `V4`).
3. **Solve.** `POST /problems/{id}/solve` builds a `ScheduleRequest` carrying `problemPath`
   (`ProblemService → buildScheduleRequest`) and publishes it (`RabbitMqProducer`).
4. **Run.** `RabbitMQClient → callback` hands the request to `TaskManager.run_task`. For names in
   `V4_ALGORITHMS`, it parses the package (`problem_v4.load_package`), calls the solver, scores the rows
   (`problem_v4.evaluate`) and builds the result (`problem_v4.result_from_rows`).
5. **Store.** The schedule rows, `metadata.analysis.kpis`, `metadata.schemaVersion` and `sisqualExport`
   (the v4 `result.json`) go to MongoDB. The task status goes back on `status-queue`.
6. **Show.** The calendar page picks the hourly view from `schemaVersion`, the v4 KPI panel from the KPI
   keys, and serves `GET /schedules/fetch/{id}/sisqual-export` as the download.

A package the parser rejects, or a solver with no schedule, ends the task as `FAILED_VALIDATION` with the
reasons (`problem_v4/runtime.py`). See [how-to-solve.md](../how-to-solve.md#when-it-fails).

The CLI (`python -m scheduler solve`, `make solve`) skips steps 1-3 and 5: it calls the solver directly
and writes the result under `exports/`.

## Legacy v2.x bundles

Problems in `data/problems/` with `demand.shifts` or `demand.workPeriods` (v2.x) take the older path:

- **`ILP General` / `CSP General`** (`CONVERTED_TEMPLATE`). The API converts `demand.csv` into Mongo
  vacation and minimum templates (`ProblemService → ensureProblemTemplates`) and forwards `constraints` as
  rules. The solvers compile them into a `ConstraintPlan`. Details: [general-algorithms-flow](../algorithms/general-algorithms-flow.md).
- **GA 2/3-shift, `ILP/CSP_Sisqual_Hours`, `Puzzle_Sisqual`** (`PROBLEM_BUNDLE`). The scheduler reads the
  bundle folder itself.
- **Manual mode** (`POST /schedules/generate`). Template names chosen in the UI go straight to the scheduler.
