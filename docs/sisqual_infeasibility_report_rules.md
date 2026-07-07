# Sisqual Infeasibility Report Rules

This document lists the validation/report rules currently covered by the Sisqual infeasibility report flow.

The implementation is in `src/scheduler/validators/sisqual_feasibility.py`.

## Scope

- Runs before Sisqual ILP/CSP solver execution through `TaskManager`.
- Blocking validation errors skip solver execution and mark the task as `FAILED_VALIDATION`.
- Non-blocking warnings are kept in the report data but do not skip solver execution.
- If Definition7 ILP/CSP still returns infeasible after passing precheck, a solver-infeasible report is generated.

## Blocking Rules

| Code | Rule | What It Catches | Result |
| --- | --- | --- | --- |
| `MISSING_REFERENCED_FILE` | Referenced data file missing | A file referenced by `problem.json`, for example `demand.dataFile` or `scheduleInput.dataFile`, does not exist at the resolved bundle path. The report includes the exact JSON field and referenced filename. | `FAILED_VALIDATION` |
| `EMPTY_REFERENCED_FILE` | Referenced data file is empty | A file referenced by `problem.json`, for example `scheduleInput.dataFile`, exists but has no rows. The report includes the exact JSON field and referenced filename. | `FAILED_VALIDATION` |
| `INVALID_TARGET_PERIOD` | Invalid target period | Missing or malformed `temporalScope.targetPeriod.start/end`. | `FAILED_VALIDATION` |
| `INVALID_WORK_PERIOD` | Invalid work period time range | Work period with missing/malformed `timeRange.start/end`. | `FAILED_VALIDATION` |
| `DEMAND_DATE_OUTSIDE_TARGET` | Demand outside target period | The demand file referenced by `demand.dataFile` contains a date outside the configured target period. | `FAILED_VALIDATION` |
| `UNKNOWN_WORK_PERIOD` | Demand references unknown work period | A `workPeriod` value in the demand file referenced by `demand.dataFile` does not exist in `problem.json` work periods. | `FAILED_VALIDATION` |
| `SCHEDULE_DATES_MISMATCH` | Schedule dates do not match supported target period | The schedule file referenced by `scheduleInput.dataFile` must contain `employee_id`, optionally up to 5 contiguous dates immediately before `targetPeriod.start`, and then every target-period date. Dates after `targetPeriod.end` are not supported yet. | `FAILED_VALIDATION` |
| `SCHEDULE_HEADER` | Invalid schedule header | The schedule file referenced by `scheduleInput.dataFile` does not start with `employee_id`. | `FAILED_VALIDATION` |
| `SCHEDULE_HEADER_DATE` | Invalid schedule date header | A schedule file header column is not a valid `YYYY-MM-DD` date. | `FAILED_VALIDATION` |
| `EMPLOYEE_MISMATCH` | Employee mismatch | Employee IDs in `problem.json` and the schedule file referenced by `scheduleInput.dataFile` do not match exactly. | `FAILED_VALIDATION` |
| `SCHEDULE_ROW_LENGTH` | Schedule row length mismatch | A schedule row has a different number of columns from the header. | `FAILED_VALIDATION` |
| `UNSUPPORTED_MARKER` | Unsupported schedule marker | Marker is not one of supported absence/work/fixed-shift formats. | `FAILED_VALIDATION` |
| `INVALID_EQUALS_MARKER` | Invalid fixed shift marker | `EQUALS:*` marker does not match `EQUALS:HH:MM-HH:MM`. | `FAILED_VALIDATION` |
| `EQUALS_OUTSIDE_WORK_PERIODS` | Fixed shift outside available slots | Fixed shift starts before the earliest work period or ends after the latest work period. | `FAILED_VALIDATION` |
| `MAX_CONSECUTIVE_WORKDAYS` | More than 5 required consecutive workdays | Input schedule requires an employee to work more than 5 consecutive days. | `FAILED_VALIDATION` |
| `WEEKLY_WORKDAYS_CONFLICT` | Weekly required-workday conflict | Required workdays in a week conflict with the max-consecutive rule. | `FAILED_VALIDATION` |
| `MIN_REST_FIXED_SHIFT_CONFLICT` | Fixed adjacent shifts violate 11h rest | Consecutive-day `EQUALS:*` shifts leave less than configured minimum rest, default 11h. | `FAILED_VALIDATION` |
| `SOLVER_INFEASIBLE` | Solver reports infeasible | Definition7 ILP/CSP returns infeasible after precheck found no blocking structural issue. | `FAILED_VALIDATION` |

## Referenced Data Files

The validator does not require fixed filenames such as `demand.csv` or `schedule_input.csv`.
It reads the filenames configured in `problem.json`:

- `demand.dataFile`
- `scheduleInput.dataFile`

If one of those files is missing or empty, the report names the JSON field, the referenced filename, and the resolved path that was checked.

Example:

```text
MISSING_REFERENCED_FILE:
demand.dataFile references 'custom_missing_demand_file.csv',
but no file exists at /path/to/problem/custom_missing_demand_file.csv.
```

## Before-Context Dates

The schedule file may include up to 5 contiguous dates immediately before `targetPeriod.start`.
These dates are treated as fixed history for boundary checks:

- max 5 workdays in any 6 consecutive days
- minimum rest from a previous fixed `EQUALS:*` shift into the first target day

Before-context dates are not solver output dates. Dates after `targetPeriod.end` are still rejected in the current implementation.

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
