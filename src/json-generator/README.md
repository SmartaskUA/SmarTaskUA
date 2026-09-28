# JSON Generator — Schema v4.0

A wizard for authoring employee-scheduling problems in **schema v4.0**, the format
defined in [`json_generation/schema_v4/`](../../json_generation/schema_v4/). It produces a
package that validates clean with that folder's validator:

```
problem.json            schemaVersion 4.0, form "input"
days_demand.csv         workload minutes, per date and dimension
periods_demand.csv      headcount, per date, dimension and window
shifts_demand.csv       headcount, per date, dimension and window (workPeriod written empty)
schedule_input.csv      one row per employee, one column per date — numeric cells are HOURS
schedules.csv           the shift menu (optional)
result.json             the fixed days, when any are fixed: a partial (or complete) result
result_schedules.csv    its sidecar — the menu rows for the codes the result uses
```

A result may be **partial**: its entries are fixed employee-days, each held as a hard rule to its
`schedule_input.csv` cell and to the labour law, and every day without an entry is open for the
solver (FORMAT.md, *Partial results*).

The canonical rules — units, the cell grammar, the grid, the traps — are in
[`json_generation/schema_v4/docs/FORMAT.md`](../../json_generation/schema_v4/docs/FORMAT.md).
The wizard is v4-only: v2.x output, projects and saved state are deprecated and are not migrated.

The app is served at **http://localhost/json-gen** through nginx; the Vite dev server alone runs on
port 5174 (`npm run dev`, then http://localhost:5174/json-gen/).

## The steps

| # | Step | Produces |
|---|---|---|
| 1 | **Setup** — problem id, roster code, slot grid, horizon, week start, holidays; or *start from a v4 bundle* | `metadata`, `timeGrid`, `temporalScope`, `calendar` |
| 2 | **Contracts** — length of one working day, in minutes, checked against the grid | `contracts.definitions` |
| 3 | **Dimensions** — the `(tableName, tableValue)` coordinates demand is keyed on | `demand.dimensions` |
| 4 | **Employees** — date-ranged contracts, date-ranged competencies with levels (1 = highest); CSV import/export | `employees.list` |
| 5 | **Schedule input** — the day-off palette (`preferable` / `unavailable`) and the matrix: `A`, hours, declared codes, `EQUALS`/`INCLUDE`/`WITHIN`/`EXCEPT` windows, blank | `scheduleInput`, `schedule_input.csv` |
| 6 | **Demand** — periods via a weekly template (one lane per dimension) applied to a calendar; days and shifts as row tables (v4 defines no shift types, so `workPeriod` is written empty); per-grain CSV import/export | the three demand CSVs |
| 7 | **Shift menu** — on by default; rest codes 1/3/4 plus worked shifts; can generate from contract lengths | `schedules.csv` |
| 8 | **Fixed days** — a grid of employee × date: fix a day to a menu code, change it, or open it again; each cell shows the `schedule_input` value it must agree with, and a contradiction is flagged with the validator's reason | `result.json`, `result_schedules.csv` |
| 9 | **Rules** — `priorityHierarchy` and labour law (`constraints.hard`) | `priorityHierarchy`, `constraints` |
| 10 | **Review** — validation, a preview of every file, per-file download and a flat ZIP | — |

Every step shows the validator's findings for that step. The Review step shows all of them,
and download unlocks when there are no errors.

Starting from a bundle takes the problem, its CSVs and, if present, one result with its
`<stem>_schedules.csv` sidecar: the result's entries become the fixed days, partial or complete.
Two results are refused, as the package rule says.

**How the files are identified.** JSON by content: `"form": "input"` is the problem, an
`OutRosterTeamDays` array is a result, whatever the files are called. A CSV's role comes first from
the name the problem gives it (`demand.dataFile*`, `scheduleInput.dataFile`, `schedules.dataFile`;
the sidecar by its `<stem>_schedules.csv` convention), and its columns must agree. When the named
file is missing or has another file's columns, the one selected CSV whose columns fit the role is
used and written back under the problem's name — days and periods, which share a header, are told
apart by their windows. Two candidates for one role bind nothing. Files are matched by base name, so
two *different* files with the same name (two package folders in one ZIP, say) are refused rather
than one silently replacing the other. The import preview lists what happened to every file.

**The menu and the result's sidecar.** The wizard keeps one list of codes, the shift menu:
`schedules.csv` is written from it whole, and the sidecar is rebuilt from it with just the codes the
fixed days use. On import nothing either file defines is dropped. A code only the sidecar has joins
the menu; a problem with no menu starts one from the sidecar. Where the two define a code differently,
the import asks which to keep, code by code: the menu's, the result's, or both (the result's under a
new code, which the fixed days that use it move to). A menu row that fixed days use cannot be deleted
in Shift Menu until those days change. Days are written back with the problem's
`rosterCode`, string `EmployeeCode`s and midnight `Date`s; `TeamCode`, tasks and responsibilities pass
through. No result is written while no day is fixed or the shift menu is off.

## How it is built

All schema knowledge lives in `src/v4/`, plain JavaScript with no React:

| module | role |
|---|---|
| `core.js` | port of `schema_v4/src/schema_v4/core.py` — numbers (comma decimals), times, dates (UTC, DST-safe), the cell grammar, CSV reading (BOM, CRLF, `#` comments) |
| `generate.js` | state → bundle; the only producer used by preview, download and validation |
| `validate.js` | port of `common.py` + `validate_input.py`, run on the generated files; same checks, same wording, each finding tagged with its step |
| `validateResult.js` | port of `validate_result.py`: each fixed day against its cell (`core.cellConflict`), the labour law over the fixed days, the sidecar, `rosterDaysLeft` |
| `schema.js` | JSON Schema layer (ajv) over the vendored `schema_v4/schema-v4-input.json` and `schema-v4-result.json` |
| `importBundle.js` | a v4 package (ZIP or files) → state, a result included; SISQUAL's current export is refused, not adapted |
| `operations.js` | pure state transforms: cascading renames/deletes (fixed days follow employees, scope and menu codes), template application, menu generation, fixing days, the weekly load |
| `state.js`, `persistence.js` | the state shape (mirrors the v4 document) and localStorage |

The React side is `src/steps/` (one file per step) and `src/components/`, all reading
`useWizard()` from `src/context/WizardContext.jsx`.

`schema_v4/schema-v4-input.json` and `schema-v4-result.json` are vendored copies of the canonical
schemas: the dev container mounts only this folder. A test fails if either copy drifts.

## Tests

```bash
npm test                                           # vitest: domain, parity, round trip, render
npx vite-node scripts/validate-with-python.mjs     # generated bundles through the Python validator
```

- `src/v4/parity.test.js` checks the JS validators report exactly what the Python ones do on the
  templates (clean), `cenario2_retail` (13 known warnings), the results of both and of
  `cenario2_partial` (105 fixed, 360 left), and one broken fixed day at a time; and that importing
  then regenerating each package reproduces every CSV byte for byte and every result entry.
- `src/App.smoke.test.jsx` renders every step and the main dialogs, with an authored problem and
  with Scenario 2 imported complete (`cenario2_retail`) and partial (`cenario2_partial`), drives the
  Fixed days grid, and fails on any React warning.

## Customizing colors

Edit `src/theme.config.js`.
