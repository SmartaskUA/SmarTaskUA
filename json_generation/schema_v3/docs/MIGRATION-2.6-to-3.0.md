# Migrating v2.6 → v3.0

A breaking change. Nothing auto-upgrades. Everything that changed is below: from → to, and why.

## Changed

| from (v2.6) | to (v3.0) | why |
|---|---|---|
| hours in contracts, `HH:MM` in periods, hours in `duration` | **minutes everywhere**, on `timeGrid.slotMinutes` (default 15) | one unit; `workHoursPerDay` was a float but cells were integers, so 7h45 couldn't be expressed — now `465` |
| `workHoursPerDay: 8`, `maxHoursPerWeek: 40` | `workMinutesPerDay: 480`, `maxMinutesPerWeek: 2400` | minutes |
| schedule_input cell `8` = 8 hours | cell `480` = 480 minutes | cells are minutes; `1–24` are **rejected** as unmigrated hours (8 min is not a shift) |
| bare `HH:MM`, roll-over inferred from `start > end` | minutes past 1440 (`22:00-06:30` → `1320-1830`) | no reader has to guess midnight-crossing |
| one problem form | **declarative + expanded** (`H_wd`/`δ`), compiler between them | authoring form vs the pre-processed form the solver reads |
| — | `schema-v3-solution.json` | the solution was not describable before |
| `date,workPeriod,team,minimum,ideal,estimated` | `date,workPeriod,competency,minimum,empiric,maximum` (ascending; `0` = unset) | see the callout below — this one bites |
| schema said `1 = junior` | **`1` = highest** | the maths always said `1` is highest; the prose was the bug — check your data against intent, don't flip it |
| `employees.simple[]` / `competency[]`, `model` selects semantics | one `employees.list[]`, **no `model`** — every worker holds **competencies with a level** | one list, one model; membership-without-level is gone, `level` is required |
| `teams[]` + `contractType` + `contractPeriods[]`, teams **static** | `contractAssignments[]` + `competencyAssignments[] {competency, level, start, end\|null}`, date-ranged | competencies change over time too; static membership → one open-ended entry; the coverage dimension is now **`competency`**, not `team` |
| `priorityHierarchy[] {rank, team, level:"N>=2"}` | `demand.priorityOrder[] {order, competency, level?}`, first match wins | `"N>=2"` parsed nowhere; you author no weights — the solver derives `p_sl` from position |
| `markingTypes` + `dayOffCodes` (same codes listed twice) | one `dayOffCodes` map keyed by code, each `{kind, description?}` | pure redundancy; `preferable` (soft, `D_wk`) vs `unavailable` (hard, `U_wk`) now one key with one `kind` |
| week start buried under advanced constraints | `calendar.weekStart`, any of 7 days | — |
| — | `calendar.holidays[]` with `hasEve` | a holiday can carry its own demand; the eve's date is the day before, so only its existence is stated |
| — | `form` and `timeGrid` now **required**; `scheduleInput` now **required** | the transformer can't build `H_wd` without them |

## Removed

| removed | why |
|---|---|
| `constraints` (whole block, incl. `min_rest_minutes`, `soft[]`, `advanced`) | solve directives that reached no solver; rest is hardcoded or read via the v2.6 `min_rest_hours` name — deferred to a registry (`FUTURE.md`) |
| `optimization` (whole block: `algorithm`, `pipeline`, `demandInterpretation`, `objectives`, `warmStart`, `maxTimeMinutes`) | connected to no algorithm — routing is orchestrator-driven, objectives/interpretation hardcoded — deferred (`FUTURE.md`) |
| `scheduleInput.markingTypes` | merged into `dayOffCodes`; it only added descriptions |
| `employees…restrictions` (`blackoutDates`, `cannotSwapDayOffs`, `preferredWorkPeriods`) | each already expressible: a `NOT` cell, an `FDO` cell, and a worker never works a *period* |
| `demand.workPeriods[].breaks[]` | inert and misplaced — a break belongs to the shift, not a demand bucket; redesign deferred (`FUTURE.md`) |
| `assignmentCatalog[].weightMinutes` / `workPeriod` (expanded) | existed only for breaks and provenance; an assignment is now purely `{id, intervals}` |
| `demand.workPeriodModel`, `workPeriods[].durationMinutes` / `allowedStartTimes` | the "flexible work period" model — a bucket now keeps a concrete `timeRange`; flexibility lives in the *worker's* block instead |
| `contracts…constraints.flexibleHours` | never defined or consumed |
| `temporalScope.year` / `numDays`, `targetPeriod` wrapper | redundant — the horizon is `temporalScope {start, end}`; the year lives in the dates, the span is counted from them |
| `minimuns`, `vacations` (top level) | misspelled/stub; read by nothing |
| `features` (whole object: `usePriorityOrder`, `useAdvancedConstraints`, `useWorkPeriodBasedScheduling`, `usePriorityHierarchy`) | gone — `priorityOrder` now applies whenever present (no toggle); the rest gated blocks or distinctions that no longer exist |

## The one that corrupts silently

**demand.csv's last two columns swap VALUES, not just names.** v2.6's rule was
`minimum ≤ estimated ≤ ideal`, so **`ideal` was the upper bound sitting in the middle column**. v3.0
is ascending — `minimum,empiric,maximum` — so `empiric ← estimated` and `maximum ← ideal`: the two
right-hand columns **exchange values**. Renaming the header alone inverts them and still usually
passes `minimum ≤ empiric ≤ maximum`, so nothing catches it. Swap the values. (An *unmigrated* header
still carrying `ideal`/`estimated` is rejected; a *half-migrated* one is not.)

## Checklist

1. Swap demand.csv's last two value columns, then rename the header. **Do not skip this.**
2. Multiply every hours field and numeric schedule_input cell by 60.
3. Leave competence levels alone; verify `1` = your most senior.
4. Fold `simple[]`/`competency[]` into `list[]`; drop `model`; convert to `contractAssignments` /
   `competencyAssignments {competency, level, start, end}` — **every** assignment needs a `level`
   (default your most senior, `1`, if the old data had none). Rename the demand key `team` →
   `competency` and the catalog `organizationalUnits.teams[]` → `competencies[]`.
   Delete `restrictions` (blackout → `NOT` cell, cannot-swap → `FDO` cells).
5. Fold `markingTypes` into `dayOffCodes` as `{code: {kind, description?}}`; list `VAC`/`NOT` too.
6. Rename `priorityHierarchy` → `priorityOrder`, `rank` → `order`, `team` → `competency`; drop
   free-form `level` strings.
7. Add `form` and `timeGrid`; set `temporalScope` to `{start, end}`; move `weekDefinition` to
   `calendar.weekStart`; give every work period a `timeRange`.
8. Delete the whole `constraints`, `optimization`, and `features` blocks.
9. `validator.py problem.json -v`, then `transform.py`, then validate the expansion.
