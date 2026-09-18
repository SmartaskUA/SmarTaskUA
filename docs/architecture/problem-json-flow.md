# problem.json Flow (API → RabbitMQ → Scheduler → ILP/CSP General)

This document explains how a `problem.json` (for example `data/problems/SMARTASK_SIMPLE_2025/problem.json`) becomes the inputs used by the Python general solvers (`ILP General` / `CSP General`).

> **See also:** `docs/algorithms/general-algorithms-flow.md` — the same journey viewed from the scheduler side, focused on how the General solvers normalize inputs and apply the constraint plan. This document is the end-to-end API→solver overview.
>
> Code references use `file → symbol()` (method/function names) rather than line numbers, which drift as the code changes.

## End-to-End Flow

1. A solve request hits the API endpoint `POST /problems/{problemId}/solve`.
   Code: `src/api/src/main/java/smartask/api/controllers/ProblemsController.java → solveProblem()`
2. The API loads and parses the `problem.json`, then builds a `ScheduleRequest`.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildScheduleRequest()`
3. The API publishes a RabbitMQ payload containing template names, settings, and constraints.
   Code: `src/api/src/main/java/smartask/api/event/RabbitMqProducer.java → requestScheduleMessage()`
4. The Python scheduler consumes the payload, loads the referenced templates from MongoDB, and selects employees.
   Code: `src/scheduler/RabbitMQClient.py → consume_messages() (callback)`
5. The scheduler delegates to `TaskManager`, which dispatches to the selected algorithm.
   Code: `src/scheduler/TaskManager.py → run_task()`
6. For `ILP General` and `CSP General`, the payload's `rules` map is passed as `constraints`.
   Code: `src/scheduler/TaskManager.py → run_task()`
7. The general solvers parse constraints into a `ConstraintPlan` and build/solve the model.
   Code: `src/scheduler/algorithms/general/constraints.py → parse_constraints()`
   Code: `src/scheduler/algorithms/general/ilp_general.py → solve()`
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`

## What problem.json Contributes

`ProblemService` is the main bridge from `problem.json` to solver inputs.

1. It reads the JSON file.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → readProblemJson()`
2. It pulls high-level settings from the JSON tree.
   Examples: `metadata`, `temporalScope`, `demand`, `constraints`.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildScheduleRequest()`
3. It discovers CSV files by scanning for any `dataFile` keys anywhere in the JSON.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → collectDataFiles()`
4. It ensures that "vacations" and "minimums" templates exist in MongoDB.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → ensureProblemTemplates()`

## How demand.csv Becomes minimuns Rows

If `problem.json` points to a demand file (like your `"demand": { "dataFile": "demand.csv" }`), the API converts it into the minimums row format expected by the scheduler.

1. The API prefers a demand CSV if present.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → ensureProblemTemplates()`
2. It transforms demand rows into minimums/ideals arrays by day-of-year, per team and shift.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → buildMinimunsRowsFromDemand()`
3. It writes the resulting rows into the `ReferenceTemplate` collection.
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → upsertReferenceTemplate()`

The scheduler later reads these rows as the `minimuns` argument.

## How employees from problem.json Are Used

`problem.json` can also override the employees sent to the solver.

1. The API reads employees from `employees.simple` when `employees.model` is `"team"` (or missing).
   Code: `src/api/src/main/java/smartask/api/services/ProblemService.java → extractProblemEmployees()`
2. Those employees are attached to the RabbitMQ payload.
   Code: `src/api/src/main/java/smartask/api/event/RabbitMqProducer.java → requestScheduleMessage()`
3. The scheduler uses them if present; otherwise it fetches employees from MongoDB and filters by the vacation template names.
   Code: `src/scheduler/RabbitMQClient.py → consume_messages() (callback)`

## How constraints (hard vs soft) Are Used

The `constraints` node from `problem.json` is forwarded to the general solvers and parsed into a `ConstraintPlan`.

1. The API forwards `constraints` as `rules` in the RabbitMQ payload.
   Code: `src/api/src/main/java/smartask/api/event/RabbitMqProducer.java → requestScheduleMessage()`
2. `TaskManager` passes that map as `constraints=` for `ILP General` and `CSP General`.
   Code: `src/scheduler/TaskManager.py → run_task()`
3. The parser distinguishes hard vs soft rules and supports top-level `hard` / `soft` lists.
   Code: `src/scheduler/algorithms/general/constraints.py → _normalize_constraints()`
4. The parser also supports a `rules` list with `kind: "hard" | "soft"`.
   Code: `src/scheduler/algorithms/general/constraints.py → _normalize_constraints()`

Important behavior details:

1. Many rules only take effect when marked hard.
   Examples: `max_consecutive_days`, `max_special_days`, `total_workdays`, `no_earlier_shift_next_day`, `vacation_block`.
   Code: `src/scheduler/algorithms/general/constraints.py → build_constraint_plan()`
2. Coverage rules support both hard and soft; soft affects objective weights, and hard adds explicit `>=` coverage constraints.
   Code: `src/scheduler/algorithms/general/constraints.py → build_constraint_plan()`
   Code: `src/scheduler/algorithms/general/ilp_general.py → ILPSchedulerWeighted.build_model()`

## Where the General Solvers Read These Inputs

Both general solvers consume the same high-level inputs: `vacations`, `minimuns`, `employees`, `year`, `shifts`, and `constraints`.

1. ILP General parses constraints and uses them to configure weights and hard constraints.
   Code: `src/scheduler/algorithms/general/ilp_general.py → solve()`
2. CSP General parses constraints and conditionally enforces them.
   Code: `src/scheduler/algorithms/general/csp_general.py → solve()`

In ILP General specifically:

1. `min_coverage_weight` and `ideal_coverage_weight` feed the objective.
   Code: `src/scheduler/algorithms/general/ilp_general.py → ILPSchedulerWeighted.build_model()`
2. `min_coverage_hard` and `ideal_coverage_hard` decide whether to add hard coverage constraints.
   Code: `src/scheduler/algorithms/general/ilp_general.py → ILPSchedulerWeighted.build_model()`

## Quick Mental Model

Think of the flow as three conversions:

1. `problem.json` → `ScheduleRequest` + template names (API side).
2. Template names → concrete rows (`vacations`, `minimuns`) + employees (scheduler side).
3. Constraints map → `ConstraintPlan` → model parameters and constraints (solver side).

If you want to debug a specific field from `problem.json`, start in `ProblemService.buildScheduleRequest(...)`, then follow the payload through `RabbitMqProducer.requestScheduleMessage(...)`, `RabbitMQClient.consume_messages(...)`, and finally into `ilp_general.solve(...)` or `csp_general.solve(...)`.
