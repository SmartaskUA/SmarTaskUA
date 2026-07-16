# v3.0 formats

JSON carries structure; two CSVs carry the matrices that would bloat it. This document covers the
CSVs and the semantics the JSON Schema cannot express. For what changed from v2.6 — especially the
demand column swap — read `MIGRATION-2.6-to-3.0.md` first.

---

## Time

Everything is **integer minutes**. `timeGrid.slotMinutes` (default 15, must divide 1440) cuts the
day into the timeslots `T` that the mathematical model reasons over.

Clock times appear as `HH:MM` in author-facing fields (work periods, time-window constraints) and
as **minutes from 00:00** in the expanded form. Minutes may exceed 1440 to express times after
midnight, so `22:00-06:30` is `1320-1830`. A work period whose `end <= start` is read as crossing
midnight. This is why v3 does not repeat v2.6's bare `HH:MM`, which forced every reader to infer
roll-over.

Every boundary must land on the grid. At the default 15 minutes, `08:30`, `15:30`, `21:00` and
`06:30` are all exact; at 60 minutes, `08:30` is not representable and the validator rejects it.
Slot count scales the model: 15-minute slots give 96 slots/day, 60-minute slots give 24.

## demand.csv

```
date,workPeriod,team,minimum,empiric,maximum,start,end
2025-10-01,STORAGE_0830_1530,Storage,1,1,1,,
2025-10-05,CHECKOUT_1100_2100,Checkout,2,3,4,10:00,20:00
```

| column | meaning |
|---|---|
| `date` | `YYYY-MM-DD`, within `temporalScope.targetPeriod` |
| `workPeriod` | a code from `demand.workPeriods[]` |
| `team` | a code from `demand.organizationalUnits.teams[]` — the skill dimension `S` |
| `minimum` | workers desired — the model's `alpha_dts` |
| `empiric` | observed/expected level |
| `maximum` | upper level |
| `start`,`end` | optional `HH:MM` override of the work period's times for this row only |

Rules:

- `minimum <= empiric <= maximum`, applied **only to non-zero values**.
- **`0` means unset**, not zero workers. `1,0,0` states a minimum of 1 and no opinion above it.
- `start`/`end` are both-or-neither.
- One row per `(date, workPeriod, team)`.
- **A missing row means that period is not operating that day.** A date with no rows at all is
  closed and sits outside the open-day set `D_o`, hence outside every week `D_k`.

### Which bound is hard is not stated here

The three numbers are data. How an algorithm reads each one lives in
`optimization.demandInterpretation`, per phase, so a pipeline can run one phase treating `maximum`
as a hard cap and the next treating it as a soft target over identical demand.

The V7 reference ILP is `{minimum: "soft", empiric: "ignore", maximum: "ignore"}`. Its `alpha_dts`
is the minimum number of workers **desired**, pursued only through the shortfall variable `z_dts`
in ObjectiveFunction1. **V7 defines no hard coverage constraint and no upper bound at all** — so a
perfectly feasible solution may still under-cover, and `empiric`/`maximum` are carried for other
phases and for KPI reporting.

### Holidays

`calendar.holidays` marks days so the enterprise can give them their own
`minimum/empiric/maximum` as ordinary rows on those dates. Setting `hasEve: true` says the
preceding day is that holiday's eve and may carry its own demand too — the eve's date is the
holiday's minus one, so only its existence needs stating. There is no day-class-keyed demand
construct: the wizard resolves the day class and emits concrete per-date rows. Marking a holiday
does **not** make anyone unavailable.

## Rules and objectives — one fact, one place

v3.0 has three ways to influence a schedule, and they do not overlap. Read this before adding a
`constraints.hard[]` entry — most of what you might reach for is already stated somewhere else.

| where | says | examples |
|---|---|---|
| **Structure** | what the data **is** | `dayOffCodes` (which codes are soft vs hard), contract `constraints` (daily/weekly limits, available days, max consecutive), the cells themselves (`EQUALS`/`INCLUDE`/`EXCEPT`), `priorityOrder`, `demandInterpretation` |
| **`optimization.objectives[]`** | what to **optimise**, and its cost | coverage shortfall, skill priority, days-off worked |
| **`constraints.hard[]`** | only what neither of the above can express | `min_rest_minutes` |

**Nothing may be stated twice.** In v2.6 coverage was declared three times over — a soft
constraint, an objective weight, and a demand-interpretation — with no defined winner. In v3 it is
two orthogonal facts: `demandInterpretation.minimum` (how the bound enters the model) and
`objectives[minimize_shortages].weight` (what a shortfall costs). A day-off being swappable is
`dayOffCodes.preferable`; the penalty for working it is
`objectives[preferable_days_off_worked].weight`. There is no third place.

### `constraints.hard[]` is typed

Each rule has an enumerated `type` and schema-checked `params`, so a typo is a validation error,
not a rule that silently does nothing (which is how v2.6 accumulated dead `type` strings). One type
exists today:

| type | params | meaning |
|---|---|---|
| `min_rest_minutes` | `{minutes}` | minimum rest between the end of one day's work and the start of the next |

The `type` list is a `oneOf`, so more can be added later without breaking existing files. What is
**not** there is deliberate: `vacation_block`, `forced_day_off`, `time_constraint`, `min_coverage`
and `day_off_swap_penalty` all restated structure or objectives and are gone;
`constraints.soft[]` and `constraints.advanced` are gone entirely (a soft constraint *was* an
objective; `advanced.dayOffSwapping.rules` was English prose no solver ever parsed).

### `optimization.objectives[]`

`goal` is one of MathematicalDefinition7's three objective functions — an unknown goal is a
validation error:

| goal | function |
|---|---|
| `minimize_shortages` | OF1 — minimise total under-staffing (`Σ z_dts`) |
| `skill_priority_weight` | OF2 — minimise the priority weight of assigned team/level combinations (`Σ p_sl·y'`), driven by `priorityOrder` |
| `preferable_days_off_worked` | OF3 — minimise preferable days-off that get worked (`Σ x'_wd`) |

## schedule_input.csv

One row per employee, one column per date.

```
employee_id,2025-10-01,2025-10-02,2025-10-03
20072412,480,DO,EQUALS:10:00-14:00
```

| cell | meaning |
|---|---|
| `A` | work the contract's `workMinutesPerDay` |
| `480` | work exactly 480 **minutes** |
| `EQUALS:HH:MM-HH:MM` | work exactly this range |
| `INCLUDE:HH:MM-HH:MM` | work at least this range; may extend |
| `EXCEPT:HH:MM-HH:MM` | unavailable during this range |
| any other code | must be declared in `dayOffCodes` (`VAC`, `NOT` included) |
| *(blank)* | **no assignments** — not "unconstrained" |

Numeric cells are **minutes**. Values in 1–24 are rejected: they are v2.6 hours that were never
migrated, and 8 minutes is not a shift.

### Day-off codes

Any cell code that is not `A`, a number, or an `EQUALS`/`INCLUDE`/`EXCEPT` window is a **day-off
code**, and every one you use must be declared under `scheduleInput.dayOffCodes` — a map keyed by
the code, each entry `{ kind, description? }`. There are no implicit codes: `VAC` and `NOT` are
listed like any other (and must be `unavailable`).

`kind` is the classification the model acts on:

- **`preferable`** [`D_wk`] — soft. Keeps its options: the solver may schedule over it and pay
  ObjectiveFunction3. Typically `DO`.
- **`unavailable`** [`U_wk`] — hard. Constraint (5) forbids any assignment. Typically `FDO`, `VAC`,
  `NOT`, `Med`.

Both feed the per-week **equality** `n_wk = |D_k| − |U_wk| − |D_wk|` (constraint 6), so a
misclassification moves that week's working-day target. Because each code is a key with exactly one
`kind`, it cannot be classified two ways — that mistake is unrepresentable.

## Competence levels

**Level 1 is the highest.** Larger numbers are progressively lower, so your most senior person is
level 1 and `level: 5` is more junior than `level: 2`. This follows MathematicalDefinition7 —
*"l = 1 represents the highest level and l = |L| represents the lowest level"*.

It reads backwards to most people, so it is worth stating twice: `{team: "Checkout", level: 1}`
means **Checkout's most senior**, not its juniors.

> **Careful — "level" means two opposite things in this document.** A *competence* level is better
> when the number is **lower**. But demand's `empiric` and `maximum` are described as "levels" too,
> and those are larger when you want **more** people. Same word, inverted direction. They never
> appear in the same field, but they do appear on the same page.

Nothing can validate this for you. If you believe 1 means junior and author accordingly, every file
still parses, every check still passes, and the schedule quietly staffs the wrong people. The
convention is the only defence.

### Fill order — `demand.priorityOrder`

Which team/level combinations get filled first:

```json
"priorityOrder": [
  { "order": 1, "team": "Management" },
  { "order": 2, "team": "Checkout", "level": 1 },
  { "order": 3, "team": "Storage" }
]
```

- Sort by `order`, then the **first entry matching** a worker's *(team, level)* decides their
  priority. Lower `order` is filled first.
- Ordering follows `order`, **not array position** — so the wizard can group or re-sort entries for
  display without changing meaning, and rearranging the JSON is always safe.
- `order` must be unique. Gaps are fine, so you can insert entries later.
- A bare `{team}` matches **any** level of that team. Add `level` to name one exactly.
- Because the first match wins, a bare `{team}` **shadows** any later entry for the same team. The
  validator warns about entries that can therefore never match.
- Anything **not listed** sorts last, all tied. Listing is opt-in; nothing is excluded from the
  model, it is just filled last.

This is ordinal on purpose. The model's numeric weight (`p_sl`, driving ObjectiveFunction2) is
derived by the solver from the matched entry's position — you never author a weight, so there is no
direction to get backwards.

## What a worker may actually work

Work periods are **demand buckets**, not a menu of shifts. A row asking for one person on
`CHECKOUT_1100_2100` wants coverage across 11:00–21:00; nobody works ten hours.

A daily working assignment is a **contiguous block of the required length, positioned anywhere on
the grid inside the operating window** (earliest start to latest end across all work periods). The
cell fixes length, position, or both:

| cell | resulting candidate blocks |
|---|---|
| `A` | contract length, every grid position |
| `480` | 480 minutes, every grid position |
| `EQUALS:a-b` | exactly that block |
| `INCLUDE:a-b` | contract length, must cover `[a,b]` |
| `EXCEPT:a-b` | contract length, must avoid `[a,b]` |
| `preferable` day off | contract length, every grid position (it is only a wish) |

This is what the live solver does with a numeric cell
(`src/scheduler/algorithms/sisqual_hours_utils.py:build_assignments`), and why the sisqual example
can ask a full-timer for 480 minutes when no declared period is 480 minutes long.

### The `T_d` rule

MathematicalDefinition7 states, in bold, that **`H_wd` does not include assignments with timeslots
`t` not belonging to `T_d`**. A candidate reaching outside the demanded window on that day is
**dropped whole — never trimmed to fit**. Trimming would invent an assignment the enterprise never
defined. `T_d` is the union of the demanded intervals on that date.

This does real work: on a day when only some periods operate, blocks that would spill into
non-operating time disappear rather than being silently reshaped.

## Expanded form

`assignmentCatalog` holds every distinct assignment, deduplicated on coverage + weight:

```json
{ "id": "A0007",
  "intervals": [ {"startMin": 510, "endMin": 930} ],
  "weightMinutes": 420 }
```

- `intervals` — disjoint, ascending. More than one expresses a **split shift**, which v2.6's single
  `timeRange` could not represent. `delta_wdht` is derived from these plus the grid.
- `weightMinutes` — **paid** minutes, deliberately separate from clock span because unpaid breaks
  make them differ. Contract limits check against this; coverage uses `intervals`.
- An assignment is pure time coverage and carries **no team**: which skill a worker serves in each
  slot is a separate decision (`y_wdts`), bounded only by their own skills `S_w`. One assignment
  can be shared by workers of different teams.

`availability` gives each worker's `H_wd` per day, plus `dayOff` (`preferable` | `unavailable`) and
an optional `forced` pre-commitment. An `unavailable` day must carry no assignments; a
`preferable` day must carry some.
