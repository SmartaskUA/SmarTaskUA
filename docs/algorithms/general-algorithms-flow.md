# General Algorithms Flow (problem.json → ILP/CSP General)

This document explains how the general algorithms (`ILP General` and `CSP General`) receive data from `problem.json`, and how that data becomes solver inputs.

Important: the Python solvers do not read `problem.json` directly. The Java API reads it, builds templates, and sends a RabbitMQ payload that the scheduler consumes.

> **See also:** `docs/architecture/problem-json-flow.md` — the end-to-end API→solver overview. This document focuses on the scheduler side: how the General solvers normalize inputs and apply the `ConstraintPlan`.
>
> Code references use `file → symbol()` (method/function names) rather than line numbers, which drift as the code changes.

## End-to-End Flow

1. A solve request is made to `POST /problems/{problemId}/solve`.
   Code: `src/api/src/main/java/smartask/api/controllers/ProblemsController.java → solveProblem()`
2. The API loads `problem.json` and builds a `ScheduleRequest`.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildScheduleRequest()`
3. The API ensures vacations and minimums templates exist (from CSVs referenced by `dataFile`).
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → ensureProblemTemplates()`
4. The API publishes a RabbitMQ payload.
   Code: `src/api/src/main/java/smartask/api/event/RabbitMqProducer.java → requestScheduleMessage()`
5. The Python scheduler consumes the payload and loads the referenced templates from MongoDB.
   Code: `src/scheduler/RabbitMQClient.py → consume_messages() (callback)`
6. `TaskManager` dispatches to the selected algorithm.
   Code: `src/scheduler/TaskManager.py → run_task()`
7. For `ILP General` and `CSP General`, the payload's `rules` map is passed as `constraints=`.
   Code: `src/scheduler/TaskManager.py → run_task()`
8. The general solver parses constraints, normalizes inputs, builds a model, and solves.
   Code: `src/scheduler/algorithms/general/constraints.py → parse_constraints()`
   Code: `src/scheduler/algorithms/general/ilp_general.py → solve()`
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`

## What problem.json Contributes

`ProblemService` is the bridge from `problem.json` to solver inputs.

1. It reads the JSON and extracts key sections like `metadata`, `temporalScope`, `demand`, and `constraints`.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildScheduleRequest()`
2. It scans the entire JSON for `dataFile` entries.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → collectDataFiles()`
3. It builds template names and rows for vacations and minimums.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → ensureProblemTemplates()`
4. It optionally reads employees from `employees.simple` when `employees.model` is `"team"` (or missing).
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → extractProblemEmployees()`

## How demand.csv Becomes minimuns Rows

When `problem.json` points to a demand CSV (for example `"demand": { "dataFile": "demand.csv" }`), the API converts that demand file into the minimums/ideals row format used by the scheduler.

1. The API prefers `demand.csv` if present.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → ensureProblemTemplates()`
2. It converts demand rows into day-of-year arrays per team and shift.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildMinimunsRowsFromDemand()`
3. It writes the resulting minimums rows into the `ReferenceTemplate` collection.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → upsertReferenceTemplate()`

Those rows later arrive at the solver as the `minimuns` argument.

## How constraints Reach the General Algorithms

The `constraints` object from `problem.json` is forwarded through the payload and parsed into a `ConstraintPlan`.

1. The API attaches `constraints` to the payload as `rules`.
   Code: `src/api/src/main/java/smartask/api/event/RabbitMqProducer.java → requestScheduleMessage()`
2. The scheduler reads `rules` from the message.
   Code: `src/scheduler/RabbitMQClient.py → consume_messages() (callback)`
3. `TaskManager` passes that map as `constraints` only for the general algorithms.
   Code: `src/scheduler/TaskManager.py → run_task()`
4. The parser supports both hard and soft rules.
   Code: `src/scheduler/algorithms/general/constraints.py → _normalize_constraints()`
   Code: `src/scheduler/algorithms/general/constraints.py → build_constraint_plan()`

## Shared Input Normalization in the General Solvers

Both general solvers perform similar preprocessing:

1. They parse constraints into a `ConstraintPlan`.
   Code: `src/scheduler/algorithms/general/ilp_general.py → solve()`
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`
2. They normalize year and infer the number of shifts from the minimums data.
   Code: `src/scheduler/algorithms/utils.py → infer_shift_count_from_dicts()`
3. They convert vacations and minimums rows into dictionaries keyed by `(day, shift, team)`.
   Code: `src/scheduler/algorithms/utils.py → rows_to_vac_dict()`
   Code: `src/scheduler/algorithms/utils.py → rows_to_req_dicts_from_demand()`

## ILP General: Where the Plan Affects the Model

`ILP General` translates the `ConstraintPlan` into model parameters, hard constraints, and objective weights.

1. Plan values are wired into the scheduler instance at construction time.
   Code: `src/scheduler/algorithms/general/ilp_general.py → ILPSchedulerWeighted.__init__()`
2. Minimum and ideal coverage can be soft (shortage variables) or hard (`>=`) depending on the plan flags.
   Code: `src/scheduler/algorithms/general/ilp_general.py → ILPSchedulerWeighted.build_model()`
3. Coverage weights affect the objective directly.
   Code: `src/scheduler/algorithms/general/ilp_general.py → ILPSchedulerWeighted.build_model()`

## CSP General: Where the Plan Affects the Model

`CSP General` uses the plan to decide whether coverage is hard or soft, and which penalties to minimize.

1. If coverage is soft, it introduces unmet-demand variables.
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`
2. Coverage weights become coefficients in the objective.
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`

## Quick Debug Path

If a field in `problem.json` does not seem to affect the general solvers, trace it in this order:

1. `ProblemService.buildScheduleRequest(...)`.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildScheduleRequest()`
2. `RabbitMqProducer.requestScheduleMessage(...)` payload construction.
   Code: `src/api/src/main/java/smartask/api/event/RabbitMqProducer.java → requestScheduleMessage()`
3. `RabbitMQClient.consume_messages(...)` and its `callback(...)`.
   Code: `src/scheduler/RabbitMQClient.py → consume_messages() (callback)`
4. `TaskManager.run_task(...)` general-algorithm branch.
   Code: `src/scheduler/TaskManager.py → run_task()`
5. `parse_constraints(...)` and the solver `solve(...)` function.
   Code: `src/scheduler/algorithms/general/constraints.py → parse_constraints()`
   Code: `src/scheduler/algorithms/general/ilp_general.py → solve()`
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`
