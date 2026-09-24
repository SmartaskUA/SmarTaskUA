# JSON Generator — Schema v4.0

A wizard for authoring employee-scheduling problems in **schema v4.0**, the format
defined in [`json_generation/schema_v4/`](../../json_generation/schema_v4/). It produces an
input bundle that validates clean with that folder's validator:

```
problem.json          schemaVersion 4.0, form "input"
days_demand.csv       workload minutes, per date and dimension
periods_demand.csv    headcount, per date, dimension and window
shifts_demand.csv     headcount, per date, shift type, dimension and window
schedule_input.csv    one row per employee, one column per date — numeric cells are HOURS
schedules.csv         the shift menu (optional)
```

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
| 6 | **Demand** — periods via a weekly template (one lane per dimension) applied to a calendar; days and shifts as row tables; per-grain CSV import/export | the three demand CSVs |
| 7 | **Shift menu** — rest codes 1/3/4 plus worked shifts; can generate from contract lengths | `schedules.csv` |
| 8 | **Rules** — `priorityHierarchy` and labour law (`constraints.hard`) | `priorityHierarchy`, `constraints` |
| 9 | **Review** — validation, a preview of every file, per-file download and a flat ZIP | — |

Every step shows the validator's findings for that step. The Review step shows all of them,
and download unlocks when there are no errors.

## How it is built

All schema knowledge lives in `src/v4/`, plain JavaScript with no React:

| module | role |
|---|---|
| `core.js` | port of `schema_v4/src/schema_v4/core.py` — numbers (comma decimals), times, dates (UTC, DST-safe), the cell grammar, CSV reading (BOM, CRLF, `#` comments) |
| `generate.js` | state → bundle; the only producer used by preview, download and validation |
| `validate.js` | port of `common.py` + `validate_input.py`, run on the generated files; same checks, same wording, each finding tagged with its step |
| `schema.js` | JSON Schema layer (ajv) over the vendored `schema_v4/schema-v4-input.json` |
| `importBundle.js` | a v4 bundle (ZIP or files) → state; SISQUAL's current export is refused, not adapted |
| `operations.js` | pure state transforms: cascading renames/deletes, template application, menu generation, the weekly load |
| `state.js`, `persistence.js` | the state shape (mirrors the v4 document) and localStorage |

The React side is `src/steps/` (one file per step) and `src/components/`, all reading
`useWizard()` from `src/context/WizardContext.jsx`.

`schema_v4/schema-v4-input.json` is a vendored copy of the canonical schema: the dev container
mounts only this folder. A test fails if the two copies drift.

## Tests

```bash
npm test                                           # vitest: domain, parity, round trip, render
npx vite-node scripts/validate-with-python.mjs     # generated bundles through the Python validator
```

- `src/v4/parity.test.js` checks the JS validator reports exactly what the Python one does on the
  templates (clean) and on `cenario2_retail` (13 known warnings), and that importing then
  regenerating both packages reproduces every CSV byte for byte.
- `src/App.smoke.test.jsx` renders every step and the main dialogs, with an authored problem and
  with Cenário 2, and fails on any React warning.

## Customizing colors

Edit `src/theme.config.js`.
