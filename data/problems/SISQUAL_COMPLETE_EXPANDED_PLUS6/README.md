# SISQUAL_COMPLETE_EXPANDED_PLUS6

## Purpose

`SISQUAL_COMPLETE_EXPANDED_PLUS6` is a larger October Sisqual benchmark derived from
`data/problems/SISQUAL_COMPLETE`, whose problem id is
`SISQUAL_HOURS_OCTOBER_COMPLETE_OBJ1_4_5`.

The goal is to test ILP and CSP behavior when the store has more workers available, but
the demand is also increased enough that the problem remains meaningful. This is not meant
to be a trivially easy "add workers and solve everything" case. It is meant to preserve the
same tradeoffs as the original problem while creating a bigger and more realistic scenario.

The scenario keeps the same:

- hard constraints
- soft objective types and weights
- priority hierarchy
- work periods
- October 2025 date range
- original workers and their original availability/time markings

## What Was Kept From The Original

All original workers from `SISQUAL_COMPLETE` are kept. Their `schedule_input.csv` rows must
remain unchanged, including working-hour markings, preferred days off, fixed days off,
vacations, medical/unavailable markings, and exact-time markings.

The same hard constraints are kept:

| Constraint | Meaning |
| --- | --- |
| Minimum rest hours | Employees must have at least 11 hours of rest between consecutive shifts. |
| Maximum consecutive working days | Employees should not work more than 5 consecutive days. |
| Vacation block | `VAC` days remain unavailable. |
| Forced day off | `FDO` days cannot be swapped or worked. |
| Time constraints | Exact time rules such as `EQUALS:10:00-14:00` remain fixed. |

The same soft objectives and weights are kept:

| Objective | Weight | Meaning |
| --- | ---: | --- |
| Minimum coverage | 1000 | Strongly prioritize covering required demand. |
| Preferred day-off swap penalty | 10 | Avoid working `DO` days unless needed. |
| Skill-priority assignment | 100 | Prefer assigning workers to higher-priority skills/levels. |

## What Was Added

Six workers are added. They are intentionally similar to existing workers so the new case
looks like a plausible staff expansion rather than a synthetic perfect-capacity scenario.

| New ID | Display name | Primary team | Secondary skills | Schedule pattern copied from | Why this worker was added |
| --- | --- | --- | --- | --- | --- |
| `900200001` | Storage Backup Expanded | Storage | Employees | `20051291` | Adds warehouse capacity without inventing a new storage contract pattern. |
| `900200002` | Manager Level 1 Backup Expanded | Management | Employees | `20072412` | Adds high-priority management coverage for supervision periods. |
| `900200003` | Manager Level 2 / Checkout Backup Expanded | Management | Checkout, Employees | `20066543` | Adds a manager who can also help checkout when priority tradeoffs require it. |
| `900200004` | Checkout Level 2 Peak Support Expanded A | Checkout | Employees | `20067696` | Adds realistic 4-hour checkout peak support. |
| `900200005` | Checkout Level 2 Peak Support Expanded B | Checkout | Employees | `20058959` | Adds another 4-hour checkout pattern while preserving part-time restrictions. |
| `900200006` | Checkout-L1 / Manager-L3 Flex Expanded | Checkout | Management, Employees | `20067009` | Adds a flexible 5-hour multi-skill worker to keep skill-priority decisions relevant. |

The added workers reuse existing schedule-input patterns because those patterns already
encode realistic availability, day-off rhythm, vacation/unavailable behavior, and contract
length. This avoids creating artificial workers with perfect availability.

The generated added capacity is:

| New ID | Copied pattern | Available schedule hours |
| --- | --- | ---: |
| `900200001` | `20051291` | 126 |
| `900200002` | `20072412` | 152 |
| `900200003` | `20066543` | 136 |
| `900200004` | `20067696` | 88 |
| `900200005` | `20058959` | 88 |
| `900200006` | `20067009` | 105 |

Total schedule capacity increases from 1183 hours to 1878 hours.

## Demand Changes

Demand is increased after adding workers. The increase is targeted, not global, so the
problem remains constrained and the KPI comparison remains useful.

Whenever demand is increased, `minimum`, `ideal`, and `estimated` are increased together.
This keeps the KPI interpretation consistent: minimum coverage, ideal staffing, and
estimated staffing all describe the same expanded business case.

| Team | Demand increase rule | Why |
| --- | --- | --- |
| Employees | Add `+1` to peak general-staffing rows that already require at least 2 workers, especially `10:00-14:00` and `17:00-22:00`. | The extra workers should create more pressure across the full store, not only in their primary departments. |
| Checkout | Add `+1` to `CHECKOUT_1100_2100` on Friday, Saturday, and Sunday. | Checkout is the most realistic place for peak-volume pressure when extra part-time workers are added. |
| Management | Add `+1` to weekend afternoon/evening management periods. | The added managers should be needed for supervision, not just absorbed into general employee coverage. |
| Storage | Add `+1` to selected high-load storage days, such as Mondays and Saturdays. | The added storage backup should matter, but storage should not dominate the whole scenario. |

These demand increases are designed to make the expanded case harder than simply adding
capacity. The expected result is better coverage than the base problem, but still enough
tension for day-off preservation, skill allocation, and employee-level behavior to matter.

The generated demand change touches 292 rows:

| Team | Changed rows | Original minimum worker-hours | Expanded minimum worker-hours |
| --- | ---: | ---: | ---: |
| Checkout | 13 | 356 | 486 |
| Employees | 263 | 698 | 961 |
| Management | 12 | 336 | 372 |
| Storage | 4 | 161 | 189 |

Total minimum worker-hours increase from 1551 to 2008. This keeps the case larger and
more realistic while still leaving enough extra capacity for the solvers to improve the
schedule if they allocate people well.

## Use Case

This scenario is intended for comparing:

- `ILP_Sisqual_Hours_MathematicalDefinition5`
- `CSP_Sisqual_Hours_MathematicalDefinition5`

It should help answer questions like:

- Does the solver use the extra employees effectively?
- Does minimum coverage improve compared with `SISQUAL_COMPLETE`?
- Does the solver still respect preferred days off when demand is higher?
- Does the skill-priority objective still keep strong workers on their best teams?
- Do employee-level KPIs reveal overuse, too many team switches, or poor allocation?

This use case is deliberately not expected to produce a perfect schedule automatically.
If every shortage disappears and every worker has perfect assignment quality, the demand
increase is probably too weak. If coverage remains almost unchanged, the demand increase is
probably too strong or assigned to the wrong periods.

## Expected KPI Behavior

Compared with `SISQUAL_COMPLETE`, the expanded problem should generally show:

- higher weighted minimum coverage
- more employees in `employeeAssignmentQuality`
- lower pressure on some original workers
- continued tradeoffs in preferred day-off preservation
- continued tradeoffs in skill-priority assignment
- possible remaining shortages in peak windows

The most important KPI checks are:

| KPI area | What to inspect |
| --- | --- |
| Coverage | `weightedMinimumCoverageRate`, `totalMinimumGap`, `criticalUnderfilledPeriods` |
| Day-off quality | `preferredDayOffWorkedDays`, `preferredDayOffPreservationRate` |
| Skill allocation | `skillPriorityPenaltyScore`, primary-team utilization, non-primary hours |
| Employee behavior | `employeeAssignmentQuality` for each original and added worker |
| Hard checks | availability, consecutive days, and minimum rest violations should remain 0 |

## How To Run

Use the generated problem path:

```text
data/problems/SISQUAL_COMPLETE_EXPANDED_PLUS6/problem.json
```

Run either MD5 solver:

```text
ILP_Sisqual_Hours_MathematicalDefinition5
CSP_Sisqual_Hours_MathematicalDefinition5
```

After generating a schedule, inspect it with the Sisqual KPI report. The key comparison is
against the original `data/problems/SISQUAL_COMPLETE/problem.json` run.

## Generation Notes

The expanded folder contains:

```text
README.md
problem.json
demand.csv
schedule_input.csv
```

The files are generated by:

```text
scripts/create_sisqual_expanded_problem.py
```

The generator:

- copies `SISQUAL_COMPLETE`
- appends the six workers listed above
- appends matching `schedule_input.csv` rows copied from existing patterns
- applies the targeted demand increases
- updates metadata to `SISQUAL_COMPLETE_EXPANDED_PLUS6`
- prints old/new employee count, added capacity, and old/new required worker-hours by team

## Validation Checklist

Before using the scenario for solver comparison:

- original employee rows are unchanged
- all new employee IDs are unique
- `problem.json` and `schedule_input.csv` contain the same employee set
- all schedule-input rows have the same date columns
- every changed demand row keeps `minimum == ideal == estimated`
- both ILP and CSP can load the problem path
- generated KPI payload includes all original and added workers in `employeeAssignmentQuality`
