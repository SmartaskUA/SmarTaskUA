# Migrating v2.6 -> v3.0

v3.0 is a breaking change. Nothing auto-upgrades. This lists every change that alters meaning,
worst first.

## At a glance

| | v2.6 | v3.0 |
|---|---|---|
| Time unit | hours in contracts, minutes in breaks, HH:MM in periods, hours in `duration` | **minutes everywhere**, on a configurable `timeGrid.slotMinutes` (default 15) |
| Midnight crossing | bare HH:MM; readers inferred roll-over from `start > end` | minutes past 1440 (`22:00-06:30` -> `1320-1830`) |
| Problem forms | one | **two**: declarative + expanded (`H_wd`/`delta`), with a compiler between them |
| Solution | not describable | `schema-v3-solution.json` |
| Demand columns | `minimum,ideal,estimated` (`ideal` = upper bound, in the middle column) | `minimum,empiric,maximum`, ascending; `0` = unset |
| Hard/soft | fixed in the schema | per **algorithm phase** (`demandInterpretation`), so a pipeline can read the same demand differently |
| Contracts over time | date-ranged | date-ranged (unchanged) |
| Teams over time | **static** | date-ranged, symmetric with contracts |
| Holidays | none | `calendar.holidays`, with `hasEve` for the day before |
| Week start | `monday-sunday` \| `sunday-saturday`, buried under advanced constraints | `calendar.weekStart`, any of 7 days |
| Fill order | `{rank, team, level:"N>=2"}` -- a rank plus an unparseable string | `demand.priorityOrder`: ordered `{order, team, level?}`, first match wins; the solver derives the model's weights |
| Day-off kinds | one opaque code space | `preferable` (soft, `D_wk`) vs `unavailable` (hard, `U_wk`) |
| Competence level | schema said `1=junior`; the maths said `1=highest` | **`1` = highest**, matching the maths |

---

## 1. demand.csv: the last two columns swap VALUES, not just names

**This is the one that will silently corrupt data.**

v2.6's header was `date,workPeriod,team,minimum,ideal,estimated,start,end`, and its rule was
`minimum <= estimated <= ideal`. So **`ideal` was the upper bound, sitting in the middle column**
— the header order and the ordering rule disagreed.

v3.0 puts them in ascending order:

```
v2.6:  date,workPeriod,team,minimum,ideal,estimated,start,end
v3.0:  date,workPeriod,team,minimum,empiric,maximum,start,end
                              |       |       |
                              |       |       +-- was `ideal`      (upper)
                              |       +---------- was `estimated`  (middle)
                              +------------------ unchanged        (lower)
```

So the mapping is `empiric <- estimated` and `maximum <- ideal`: **the two right-hand columns
exchange values**. Renaming the header alone inverts the upper and middle bounds on every row.

It is easy to miss because both shipped examples had `ideal == estimated`, making the swap
invisible there.

The validator catches an **unmigrated** file — a header still carrying `ideal`/`estimated` is
rejected with a pointer to this section. It cannot catch a **half-migrated** one: if you rename the
columns without swapping the values, the result usually still satisfies
`minimum <= empiric <= maximum` and passes clean. Swap the values.

Also new: **`0` means "unset / ignore this bound"**, so the ordering rule binds only the non-zero
bounds. A row of `1,0,0` states a minimum of 1 and no opinion on the rest.

## 2. Competence level: `1` is the HIGHEST. Your data is probably already correct.

v2.6's `schema.json:267` documented `1=junior, 2=mid, 3=senior`. **Both MathematicalDefinition5 and
7 say the opposite** — *"l = 1 represents the highest level and l = |L| represents the lowest"* —
and the maths is the authority: it is what the solver implements. The v2.6 prose was a
documentation bug that contradicted the model it was documenting.

v3.0 states the maths convention, and the sisqual example's levels were carried over **unchanged**.

The example data corroborates this, though only weakly, and it is worth being straight about how
weakly. Its two `fullTime_8h` employees are Management levels 1 and 2, and its level-5 Checkout
employee is on the smallest `partTime_4h` contract — which reads naturally as 1 = highest. But the
correlation is **not** monotone: `20056459` is Checkout **level 1** on that same smallest
`partTime_4h` contract, and `20051291` is Storage level 1 on `partTime_7h`. Contract size is
suggestive here, not proof. Rely on the maths.

**Do not flip your levels** to migrate. Check them against intent instead: if your data really was
authored as `1=junior`, it disagreed with the maths under v2.6 too, and it is the data that needs
correcting, not the convention.

## 3. Everything is minutes

| v2.6 | v3.0 |
|---|---|
| `contracts.definitions[].workHoursPerDay: 8` | `workMinutesPerDay: 480` |
| `constraints.maxHoursPerWeek: 40` | `maxMinutesPerWeek: 2400` |
| `workPeriods[].breaks[].duration` (minutes) | `durationMinutes` (renamed so the unit is on the field, not in a doc) |
| `advanced.breaks.rules[].minWorkPeriodHours` | `minWorkMinutes` |
| `workPeriods[].duration` (hours, while every neighbour was minutes) | gone — see Removed below |
| schedule_input cell `8` = 8 hours | cell `480` = 480 minutes |

`workHoursPerDay` was a float while schedule_input cells were integers 1–16, so a 7.5h contract
could be declared but never expressed. Minutes remove that: 7h45 is `465`.

**schedule_input cells are the hazard.** An unmigrated `8` is valid v3 syntax meaning *8 minutes*.
The validator and transformer therefore **reject numeric cells in 1–24** and tell you to multiply
by 60 — no real assignment is under 25 minutes, so that range is always a migration miss.

## 4. Structural renames

- `employees.simple[]` / `employees.competency[]` -> a single `employees.list[]`; `model` still
  selects the semantics.
- `employee.teams[]` + `contractType` + `contractPeriods[]` -> `contractAssignments[]` and
  `teamAssignments[]`, both date-ranged (`{start, end|null}`), multiple and discontinuous allowed,
  overlap rejected. Static v2.6 membership migrates to one open-ended entry.
- `constraints.advanced.dayOffSwapping.weekDefinition` -> `calendar.weekStart`, now any of the 7
  days rather than two fixed choices.
- `demand.priorityHierarchy[]` -> `demand.priorityOrder[]`, an ordered list of
  `{order, team, level?}`. Nearly a rename: v2.6's `rank` becomes `order`, and `level` becomes a
  plain integer instead of a free-form expression string (`"N>=2"`), which nothing could parse.
  Sort by `order`, first match wins; a bare `{team}` matches any level; unlisted combinations sort
  last. **You author no weights.** The model's numeric weight (`p_sl`) is derived by the solver
  from the matched entry's position, so there is no direction to invert. If your v2.6 hierarchy
  ranked teams only — as the shipped example did — the migration is a 1:1 carry-over and you should
  add no levels.
- `scheduleInput` is now **required**. v2.6's schema made it optional while v2.6's own validator
  demanded it; the transformer cannot build `H_wd` without it.
- `calendar.holidays[]` replaces a separate eve list. An eve's date is always the holiday's date
  minus one, so only its *existence* needs stating: set `hasEve: true` on the holiday. There is no
  `holidayEves` array and no `deriveEves` flag.
- New required: `form` (`declarative` | `expanded` | `solution`) and `timeGrid`.

## 4b. The rule model shrank to what solvers actually read

v2.6's `constraints[]` accumulated `type` strings that no solver ever matched, plus prose. v3's
structural additions made most of them redundant. See FORMAT.md "Rules and objectives" for the
precedence; in migration terms:

- **`constraints.soft[]` is gone.** A soft constraint was a penalty term in the objective under
  another name. Move each to `optimization.objectives[]`: `min_coverage` →
  `minimize_shortages`, `day_off_swap_penalty` → `preferable_days_off_worked`. Drop its `params`
  (`penalty_within_week`/`penalty_outside_week` were dead — the model reads one flat weight).
- **`constraints.advanced` is gone.** `dayOffSwapping.rules` was English prose nothing parsed;
  `dayOffSwapping.enabled` was never read (the switch is a positive OF3 weight); `weekDefinition`
  already moved to `calendar.weekStart`; `advanced.breaks` was read by nothing.
- **`constraints.hard[]` is now typed** (`type` enum + schema'd `params`) and keeps only
  `min_rest_minutes`. Delete `vacation_block`, `forced_day_off`, `time_constraint` — all had empty
  params and restated `dayOffCodes` and the cells.
- **`optimization.objectives[].goal` is now an enum** of MathematicalDefinition7's three functions.
  `balance_workload` is dropped (it was in neither the maths nor any solver). A goal outside the
  enum is a validation error, where v2.6 silently ignored it.

### Removed

| removed | why |
|---|---|
| `minimuns` (top level) | misspelled, unused, read by nothing |
| `vacations` (top level) | stub; no example or validator ever used it |
| `features.useWorkPeriodBasedScheduling` | the distinction it toggled no longer exists |
| `features.usePriorityHierarchy` | renamed `usePriorityOrder` (gates `priorityOrder`) |
| `contracts…constraints.flexibleHours` | never defined or consumed |
| `demand.workPeriodModel` | only `fixed` remains, so the field had one legal value |
| `workPeriods[].durationMinutes` / `allowedStartTimes` | the "flexible work period" model |
| `constraints.soft[]`, `constraints.advanced` | soft = objective weights; advanced = prose/dead |
| `scheduleInput.markingTypes` | merged into `dayOffCodes` (see §5); it only added descriptions |

The last three are one removal. Once work periods are understood as **demand buckets**, a
"flexible" bucket — a duration plus a set of allowed start times, with no settled range — has no
time span for demand to attach to, and neither example ever used one. Flexibility now lives where
it belongs: the *worker's* assignment is a block placed anywhere in the operating window, which is
strictly more flexible than the old model, while the bucket keeps a concrete `timeRange`. Every
work period therefore requires `timeRange`. If you genuinely need variable-start buckets, this is
the thing to add back.

## 5. Day-off codes: one map that declares and classifies

v2.6 had `markingTypes` (declare a code + description) *and* `dayOffCodes` (classify it), which were
forced to list the same codes — pure redundancy. v3 has **only `scheduleInput.dayOffCodes`**, a map
keyed by code:

```json
"dayOffCodes": {
  "DO":  { "kind": "preferable",  "description": "Day off - swappable" },
  "FDO": { "kind": "unavailable", "description": "Forced day off" },
  "VAC": { "kind": "unavailable" }
}
```

To migrate: drop `markingTypes`; turn each `dayOffCodes` array entry into a keyed entry with
`kind`, folding the old `markingTypes` description in (optional). Two behaviour changes:

- **Every code you use must be declared, `VAC`/`NOT` included** — they are no longer implicitly
  accepted. If used, they must be `kind: "unavailable"`.
- A code can no longer be classified two ways: it is one key with one `kind`, so the "listed as both
  preferable and unavailable" mistake is now unrepresentable rather than merely validated against.

`kind` drives the model — **`preferable`** [`D_wk`] is soft (may be worked at a penalty,
ObjectiveFunction3), **`unavailable`** [`U_wk`] is hard (constraint 5 forbids any assignment). Both
feed the per-week **equality** `n_wk = open days − |U_wk| − |D_wk|`, so a misclassification shifts
every week's target. The split is not an invention — the live solver already encodes it as
`SISQUAL_UNAVAILABLE_MARKERS = OFF_MARKERS - {"DO"}`.

## 6. Work periods are demand buckets, not shifts

Unchanged in substance, but v2.6 never said so and it is easy to migrate on the wrong assumption.
A demand row on `CHECKOUT_1100_2100` asks for coverage over 11:00–21:00; nobody works a ten-hour
shift. A worker works a contiguous block of their contracted length anywhere in the operating
window. See README.

## 7. Blank schedule_input cells mean "no assignments"

Not "unconstrained". This matches the live solver, which treats an empty marker exactly like an
off marker. Be explicit instead.

## 8. Holidays do not create days off

`calendar.holidays` exists so a holiday can carry its own demand (notes.md L17). It does **not**
mark anyone unavailable — shops open on holidays. Whether a worker is entitled to take one off is
the workplace-vs-residence rule, which is per-employee and deferred to v3.1. In v3.0 a holiday
reaches `U_wk` only through that worker's schedule_input cell, exactly like any other day.

## 9. Rules are global only

`constraints.hard[]` entries accept `scope: "global"` (the default). Any other value is rejected
rather than ignored, so a v3.1 per-employee rule cannot silently do nothing on a v3.0 validator.

---

## Worked example

`examples/sisqual_example/` is the v2.6 example of the same name, migrated. Diff the two to see
every change on real data. Three cells in `examples/time_constraints_example/` were **repaired**
rather than migrated: `EQUALS:08:00-16:00` asked for 08:00 when the shop opens 08:30 (outside the
operating window and outside `T_d`), and `INCLUDE:08:00-20:00` asked an 8h contract to span a 12h
window. Both were unsatisfiable under v2.6 too.

## Checklist

1. Swap demand.csv's last two value columns; rename the header. **Do not skip step 1.**
2. Multiply every hours field and every numeric schedule_input cell by 60.
3. Leave competence levels alone; verify 1 = your most senior.
4. Fold `simple[]`/`competency[]` into `list[]`; convert to `contractAssignments`/`teamAssignments`.
5. Fold `markingTypes` into `dayOffCodes` as `{code: {kind, description?}}`; list `VAC`/`NOT` too.
6. Rename `priorityHierarchy` -> `priorityOrder`, `rank` -> `order`; drop any
   free-form `level` expression strings. Author no weights.
7. Add `form`, `timeGrid`; move `weekDefinition` to `calendar.weekStart`; drop
   `workPeriodModel`, `flexibleHours`, `minimuns`, `vacations`; give every work period a
   `timeRange`.
8. `python3 src/schema_v3/validator.py problem.json -v`, then transform and validate the expansion.
