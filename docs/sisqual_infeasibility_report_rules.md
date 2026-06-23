# Sisqual Infeasibility Report Rules

This document lists the validation/report rules currently covered by the Sisqual infeasibility report flow.

The implementation is in `src/scheduler/validators/sisqual_feasibility.py`.

## Scope

- Applies only to Sisqual problem bundles detected through `problem.json`, `demand.csv`, and `schedule_input.csv`.
- Runs before Sisqual ILP/CSP solver execution through `TaskManager`.
- Blocking validation errors skip solver execution and mark the task as `FAILED_VALIDATION`.
- Non-blocking warnings are kept in the report data but do not skip solver execution.
- If Definition7 ILP/CSP still returns infeasible after passing precheck, a solver-infeasible report is generated.

## Blocking Rules

| Code | Rule | What It Catches | Result |
| --- | --- | --- | --- |
| `MISSING_FILE` | Required bundle file missing | Missing `demand.csv` or `schedule_input.csv` referenced by `problem.json`. | `FAILED_VALIDATION` |
| `EMPTY_FILE` | Required CSV is empty | Empty `demand.csv` or `schedule_input.csv`. | `FAILED_VALIDATION` |
| `INVALID_TARGET_PERIOD` | Invalid target period | Missing or malformed `temporalScope.targetPeriod.start/end`. | `FAILED_VALIDATION` |
| `INVALID_WORK_PERIOD` | Invalid work period time range | Work period with missing/malformed `timeRange.start/end`. | `FAILED_VALIDATION` |
| `DEMAND_DATE_OUTSIDE_TARGET` | Demand outside target period | `demand.csv` contains a date outside the configured target period. | `FAILED_VALIDATION` |
| `UNKNOWN_WORK_PERIOD` | Demand references unknown work period | `demand.csv.workPeriod` does not exist in `problem.json` work periods. | `FAILED_VALIDATION` |
| `SCHEDULE_DATES_MISMATCH` | Schedule dates do not match target period | `schedule_input.csv` header dates are not exactly `employee_id` plus every date in target period. | `FAILED_VALIDATION` |
| `EMPLOYEE_MISMATCH` | Employee mismatch | Employee IDs in `problem.json` and `schedule_input.csv` do not match exactly. | `FAILED_VALIDATION` |
| `SCHEDULE_ROW_LENGTH` | Schedule row length mismatch | A schedule row has a different number of columns from the header. | `FAILED_VALIDATION` |
| `UNSUPPORTED_MARKER` | Unsupported schedule marker | Marker is not one of supported absence/work/fixed-shift formats. | `FAILED_VALIDATION` |
| `INVALID_EQUALS_MARKER` | Invalid fixed shift marker | `EQUALS:*` marker does not match `EQUALS:HH:MM-HH:MM`. | `FAILED_VALIDATION` |
| `EQUALS_OUTSIDE_WORK_PERIODS` | Fixed shift outside available slots | Fixed shift starts before the earliest work period or ends after the latest work period. | `FAILED_VALIDATION` |
| `MAX_CONSECUTIVE_WORKDAYS` | More than 5 required consecutive workdays | Input schedule requires an employee to work more than 5 consecutive days. | `FAILED_VALIDATION` |
| `WEEKLY_WORKDAYS_CONFLICT` | Weekly required-workday conflict | Required workdays in a week conflict with the max-consecutive rule. | `FAILED_VALIDATION` |
| `MIN_REST_FIXED_SHIFT_CONFLICT` | Fixed adjacent shifts violate 11h rest | Consecutive-day `EQUALS:*` shifts leave less than configured minimum rest, default 11h. | `FAILED_VALIDATION` |
| `SOLVER_INFEASIBLE` | Solver reports infeasible | Definition7 ILP/CSP returns infeasible after precheck found no blocking structural issue. | `FAILED_VALIDATION` |

## Warning Rules

These are reported but do not stop the solver because the Definition7 model can stay feasible through shortage variables.

| Code | Rule | What It Catches | Result |
| --- | --- | --- | --- |
| `NO_EMPLOYEE_WITH_SKILL` | No employee has demanded skill | A demand skill/team has no employee with that skill in `problem.json`. | Warning only |
| `ZERO_POSSIBLE_WORKERS` | Demand has zero possible workers | For a demanded skill/date, all skilled employees are hard-unavailable. | Warning only |

## Supported Schedule Markers

| Marker | Meaning in Precheck |
| --- | --- |
| Empty cell | Hard unavailable |
| `DO` | Preferred day off; can count as possible only when day-off swapping is enabled |
| `FDO` | Hard unavailable |
| `VAC` | Hard unavailable |
| `NOT` | Hard unavailable |
| `Med` / `MED` | Hard unavailable |
| `ENFD` | Hard unavailable |
| `DC-E` | Hard unavailable |
| Numeric marker, for example `4`, `5`, `8` | Required/template workday |
| `A` | Required/template workday |
| `EQUALS:HH:MM-HH:MM` | Fixed shift assignment |

## Report Outputs

When a blocking validation error or solver infeasibility happens, the scheduler writes:

- `shared_tmp/validation_reports/{taskId}/report.json`
- `shared_tmp/validation_reports/{taskId}/report.md`
- `shared_tmp/validation_reports/{taskId}/report.pdf`

The RabbitMQ task status includes:

- `status = FAILED_VALIDATION`
- `failureType`
- `failureSummary`
- `reportArtifacts`

The API exposes downloads at:

- `GET /tasks/{taskId}/report/json`
- `GET /tasks/{taskId}/report/md`
- `GET /tasks/{taskId}/report/pdf`

## Not Covered Yet

- Full IIS/conflict-refiner style explanations for solver infeasibility.
- Detailed per-constraint model proofs for infeasible ILP/CSP results.
- Generic non-Sisqual SMARTASK problem validation.
- Frontend display of warning-only reports for successful tasks.
