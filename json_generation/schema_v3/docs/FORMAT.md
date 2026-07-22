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

Both CSVs may carry documentation: a line whose first non-whitespace character is `#`, and blank
lines, are ignored by the readers (this is how the templates annotate themselves).

| column | meaning |
|---|---|
| `date` | `YYYY-MM-DD`, within `temporalScope` (`start`..`end`) |
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

The three numbers are **data**. Whether a solver reads each as a hard cap, a soft target, or
ignores it is **not stated in v3.0** — v3.0 is the problem definition only, and how to solve it
(algorithm, objectives, demand interpretation) is deferred to the solver (see
`FUTURE.md`). The V7 reference ILP, for instance, reads `minimum` only and treats it as a soft
target: its `alpha_dts` is the minimum number of workers **desired**, pursued only through the
shortfall variable `z_dts`, with no hard coverage constraint and no upper bound — so a perfectly
feasible solution may still under-cover, and `empiric`/`maximum` are carried for other solvers and
for KPI reporting.

### Holidays

`calendar.holidays` marks days so the enterprise can give them their own
`minimum/empiric/maximum` as ordinary rows on those dates. Setting `hasEve: true` says the
preceding day is that holiday's eve and may carry its own demand too — the eve's date is the
holiday's minus one, so only its existence needs stating. There is no day-class-keyed demand
construct: the wizard resolves the day class and emits concrete per-date rows. Marking a holiday
does **not** make anyone unavailable.

## What v3.0 does and does not carry — one fact, one place

v3.0 is the problem **definition**: the *what*. Every fact about the problem has exactly one home,
and none is stated twice:

| fact | where it lives |
|---|---|
| which day-off codes are soft vs hard | `scheduleInput.dayOffCodes` |
| daily/weekly limits, available days, max consecutive | contract `constraints` |
| a specific worker-day's requirement | the schedule_input cell (`EQUALS`/`INCLUDE`/`EXCEPT`, a number, `A`) |
| which team/level combinations fill first | `demand.priorityOrder` |
| how many workers each slice of the day wants | the demand.csv numbers |

What v3.0 does **not** carry is *how to solve* the problem — the algorithm, the objective weights,
which demand bound is hard or soft, and rules such as minimum rest. In v3.0 none of that reached a
solver (routing is orchestrator-driven; objectives and rest are hardcoded in each solver or read
via the v2.6 shape v3 replaced), so it was cut. Those solve directives return as **one explicit
registry**, consumed by the algorithm, when a v3 solver is built — see `FUTURE.md`. Until then a
leftover `optimization` or `constraints` block is a validation **error**, not a silently ignored
one.

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
| `EQUALS:a-b[,c-d…]` | work exactly this block; several comma-separated ranges = one **split shift** |
| `INCLUDE:a-b[,c-d…]` | one block that covers **all** listed windows; may extend |
| `EXCEPT:a-b[,c-d…]` | unavailable during **all** listed windows |
| any other code | must be declared in `dayOffCodes` (`VAC`, `NOT` included) |
| *(blank)* | **no assignments** — not "unconstrained" |

Numeric cells are **minutes**. Values in 1–24 are rejected: they are v2.6 hours that were never
migrated, and 8 minutes is not a shift.

Each of `EQUALS`/`INCLUDE`/`EXCEPT` takes one or more comma-separated `HH:MM-HH:MM` ranges.
Overlapping or touching ranges are **coalesced** into their union — `EQUALS:08:00-12:00,10:00-14:00`
means `08:00-14:00`, and `08:00-12:00,12:00-16:00` means `08:00-16:00` — so only a real gap
(`07:30-14:00,18:15-21:15`) yields a split shift. `INCLUDE`/`EXCEPT` record their windows into the
expanded form (`mustCover`/`mustAvoid`, below) so the constraint stays re-checkable there.

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
| `EQUALS:a-b[,c-d…]` | exactly that block, or one split-shift assignment across the (coalesced) ranges |
| `INCLUDE:a-b[,c-d…]` | contract length, must cover **every** window |
| `EXCEPT:a-b[,c-d…]` | contract length, must avoid **every** window |
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

`assignmentCatalog` holds every distinct assignment, deduplicated on coverage:

```json
{ "id": "A0007",
  "intervals": [ {"startMin": 510, "endMin": 930} ] }
```

- `intervals` — disjoint, ascending. More than one expresses a **split shift**, which v2.6's single
  `timeRange` could not represent. `delta_wdht` is derived from these plus the grid, and the paid
  span is just their total length — v3.0 has no break model, so paid always equals clock span (see
  MIGRATION §4b).
- An assignment is pure time coverage and carries **no team** and **no work-period tag**: which
  skill a worker serves in each slot is a separate decision (`y_wdts`), bounded only by their own
  skills `S_w`, and which demand bucket a block happens to align with is derivable from its
  intervals. One assignment can be shared by workers of different teams.

`availability` gives each worker's `H_wd` per day, plus `dayOff` (`preferable` | `unavailable`) and
an optional `forced` pre-commitment. An `unavailable` day must carry no assignments; a
`preferable` day must carry some.

An `INCLUDE`/`EXCEPT` cell also records its windows on the worker-day as `mustCover`/`mustAvoid`
(arrays of `{startMin, endMin}`). The transformer has already filtered `assignmentIds` to satisfy
them, but recording the windows lets the validator **re-verify** — every offered assignment must
cover each `mustCover` window and avoid each `mustAvoid` window — so the constraint holds against the
expanded file alone, even one produced or edited outside the transformer. `EQUALS` needs no such
field: its day offers exactly the one (possibly split) assignment it names.
