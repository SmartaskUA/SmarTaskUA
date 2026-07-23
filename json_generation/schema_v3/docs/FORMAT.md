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
midnight — the one place a reader still infers roll-over, and it is confined to that author-facing
field: the expanded form the model reads always states the minutes outright. v2.6 by contrast made
every reader infer, everywhere, from bare `HH:MM`. Removing that last inference is merge decision
[S2](sisqual/SISQUAL-MERGE-EASY.md) (datetime-defined boundaries) — decided, not yet built.

Every boundary must land on the grid. At the default 15 minutes, `08:30`, `15:30`, `21:00` and
`06:30` are all exact; at 60 minutes, `08:30` is not representable and the validator rejects it.
Slot count scales the model: 15-minute slots give 96 slots/day, 60-minute slots give 24.

### Why minutes

The schema splits time by what a value **is**, not by where it appears: an **instant** is a point on
the calendar (a `date`, a clock time) and a **duration or offset** is a scalar — `workMinutesPerDay`,
`maxMinutesPerWeek`, `startMin`. Scalars are integer minutes because:

- **It is exact.** `7h45` is `465`. v2.6 held `workHoursPerDay` as a float while schedule-input cells
  were integers, so 7h45 was inexpressible in one of the two — the bug that forced the change.
- **Arithmetic needs no parsing.** Durations add, subtract and compare as plain `int`; grid alignment
  is `value % slotMinutes`; the model's slot index is `(mins - dayStart) // slotMinutes`. With
  `HH:MM` each of those becomes parse → convert → compute → format.
- **Roll-over is stated, not inferred.** `1320-1830` says "ends 06:30 next day" without a rule about
  `start > end`.
- **One unit.** v2.6 mixed three — hours in contracts, `HH:MM` in periods, hours in `duration`.
- **It is already Sisqual's unit** for durations (`TotalDailyMinutes`,
  `DistanceBetweenShiftsInMinutes`, `ScheduleWeight`), which is why that whole tier maps 1:1.

Not ISO-8601 durations (`PT7H45M`): `PT465M` and `PT7H45M` are one value spelled two ways, so
equality and de-duplication break; it needs a parser; and you convert to `465` to compute anyway.

## demand.csv

```
date,workPeriod,competency,minimum,empiric,maximum,start,end
2025-10-01,STORAGE_0830_1530,Storage,1,1,1,,
2025-10-05,CHECKOUT_1100_2100,Checkout,2,3,4,10:00,20:00
```

Both CSVs may carry documentation: a line whose first non-whitespace character is `#`, and blank
lines, are ignored by the readers (this is how the templates annotate themselves).

| column | meaning |
|---|---|
| `date` | `YYYY-MM-DD`, within `temporalScope` (`start`..`end`) |
| `workPeriod` | a code from `demand.workPeriods[]` (declared `{code, name, description?, timeRange}`) |
| `competency` | a code from `demand.organizationalUnits.competencies[]` (declared `{code, name, description?}`) — the skill dimension `S` |
| `minimum` | workers desired — the model's `alpha_dts` |
| `empiric` | observed/expected level |
| `maximum` | upper level |
| `start`,`end` | optional `HH:MM` override of the work period's times for this row only |

Rules:

- `minimum <= empiric <= maximum`, applied **only to non-zero values**.
- **`0` means unset**, not zero workers. `1,0,0` states a minimum of 1 and no opinion above it.
- `start`/`end` are both-or-neither.
- One row per `(date, workPeriod, competency)`.
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
does **not** make anyone unavailable. A holiday may also carry an optional `code`, `name` and
`description` — labels for the wizard/UI that the solver ignores; the `date` is the identifier.

## What v3.0 does and does not carry — one fact, one place

v3.0 is the problem **definition**: the *what*. Every fact about the problem has exactly one home,
and none is stated twice:

| fact | where it lives |
|---|---|
| which day-off codes are soft vs hard | `scheduleInput.dayOffCodes` |
| daily/weekly limits, available days, max consecutive | contract `constraints` |
| a specific worker-day's requirement | the schedule_input cell (`EQUALS`/`INCLUDE`/`WITHIN`/`EXCEPT`, a number, `A`) |
| which competency/level combinations fill first | `demand.priorityOrder` |
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
| `INCLUDE:a-b[,c-d…]` | one block that **covers** all listed windows (shift ⊇ window); may extend |
| `WITHIN:a-b[,c-d…]` | one block that fits **inside** one listed window (shift ⊆ window); "work somewhere in this range" |
| `EXCEPT:a-b[,c-d…]` | unavailable during **all** listed windows |
| any other code | must be declared in `dayOffCodes` (`VAC`, `NOT` included) |
| *(blank)* | **no assignments** — not "unconstrained" |

Numeric cells are **minutes**. Values in 1–24 are rejected: they are v2.6 hours that were never
migrated, and 8 minutes is not a shift.

**`INCLUDE` vs `WITHIN` — opposite containment.** `INCLUDE:12:00-13:00` forces the (contract-length)
shift to be **present for all** of noon–1pm and it extends around it; `INCLUDE:08:00-20:00` on an 8 h
contract is *infeasible* (no 8 h block covers 12 h). `WITHIN:08:00-20:00` is the reverse — the 8 h
shift must sit **inside** 08:00–20:00 (e.g. 09:00–17:00), which is exactly feasible. Several `WITHIN`
windows mean "inside **any one** of them" (split availability).

Each of `EQUALS`/`INCLUDE`/`WITHIN`/`EXCEPT` takes one or more comma-separated `HH:MM-HH:MM` ranges.
Overlapping or touching ranges are **coalesced** into their union — `EQUALS:08:00-12:00,10:00-14:00`
means `08:00-14:00`, and `08:00-12:00,12:00-16:00` means `08:00-16:00` — so only a real gap
(`07:30-14:00,18:15-21:15`) yields a split shift. `INCLUDE`/`WITHIN`/`EXCEPT` record their windows into
the expanded form (`mustCover`/`mustBeWithin`/`mustAvoid`, below) so the constraint stays re-checkable
there.

### Day-off codes

Any cell code that is not `A`, a number, or an `EQUALS`/`INCLUDE`/`WITHIN`/`EXCEPT` window is a **day-off
code**, and every one you use must be declared under `scheduleInput.dayOffCodes` — a map keyed by
the code, each entry `{ kind, name?, description? }`. There are no implicit codes: `VAC` and `NOT` are
listed like any other (and must be `unavailable`). This map is the **palette**: add a new day-off type
by adding one labelled entry, then use its code in the CSV. `name`/`description` are optional labels
the solver ignores; only `kind` and the code itself drive the model.

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

It reads backwards to most people, so it is worth stating twice: `{competency: "Checkout", level: 1}`
means **Checkout's most senior**, not its juniors.

> **Careful — "level" means two opposite things in this document.** A *competence* level is better
> when the number is **lower**. But demand's `empiric` and `maximum` are described as "levels" too,
> and those are larger when you want **more** people. Same word, inverted direction. They never
> appear in the same field, but they do appear on the same page.

Nothing can validate this for you. If you believe 1 means junior and author accordingly, every file
still parses, every check still passes, and the schedule quietly staffs the wrong people. The
convention is the only defence.

### Fill order — `demand.priorityOrder`

Which competency/level combinations get filled first:

```json
"priorityOrder": [
  { "order": 1, "competency": "Management" },
  { "order": 2, "competency": "Checkout", "level": 1 },
  { "order": 3, "competency": "Storage" }
]
```

- Sort by `order`, then the **first entry matching** a worker's *(competency, level)* decides their
  priority. Lower `order` is filled first.
- Ordering follows `order`, **not array position** — so the wizard can group or re-sort entries for
  display without changing meaning, and rearranging the JSON is always safe.
- `order` must be unique. Gaps are fine, so you can insert entries later.
- A bare `{competency}` matches **any** level of that competency. Add `level` to name one exactly.
- Because the first match wins, a bare `{competency}` **shadows** any later entry for the same
  competency. The validator warns about entries that can therefore never match.
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
| `INCLUDE:a-b[,c-d…]` | contract length, must cover **every** window (block ⊇ window) |
| `WITHIN:a-b[,c-d…]` | contract length, must fit **inside** one window (block ⊆ window) |
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
- An assignment is pure time coverage and carries **no competency** and **no work-period tag**: which
  competency a worker serves in each slot is a separate decision (`y_wdts`), bounded only by their own
  competencies `S_w`, and which demand bucket a block happens to align with is derivable from its
  intervals. One assignment can be shared by workers of different competencies.

`availability` gives each worker's `H_wd` per day, plus `dayOff` (`preferable` | `unavailable`) and
an optional `forced` pre-commitment. An `unavailable` day must carry no assignments; a
`preferable` day must carry some.

An `INCLUDE`/`WITHIN`/`EXCEPT` cell also records its windows on the worker-day as
`mustCover`/`mustBeWithin`/`mustAvoid` (arrays of `{startMin, endMin}`). The transformer has already
filtered `assignmentIds` to satisfy them, but recording the windows lets the validator **re-verify** —
every offered assignment must cover each `mustCover` window, fit inside one `mustBeWithin` window, and
avoid each `mustAvoid` window — so the constraint holds against the expanded file alone, even one
produced or edited outside the transformer. `EQUALS` needs no such field: its day offers exactly the
one (possibly split) assignment it names.

## Solution form

The third form (`schema-v3-solution.json`) is the **output** half: what a solver chose — the daily
assignment each worker took (`x_wdh`), optionally the competency served per slot (`competencyPerSlot`,
`y_wdts`), and where coverage fell short (`shortfalls`, `z_dts`). A solution does not restate the
problem; it *references* the expanded problem it solves:

- `problemId` must equal that problem's `metadata.problemId`.
- each day's `assignmentId` must be one of that worker-day's `availability.assignmentIds` (its `H_wd`),
  or `null` for not working.
- `workedPreferableDayOff` may be true only on a day the problem marked `dayOff: "preferable"`.
- each `competencyPerSlot.competency` must be a competency the worker holds that day, and its interval
  must lie inside the chosen assignment.
- `shortfalls` name a known competency on an in-horizon date, on the grid.

### Full solution or partial warm-start seed

The same file serves both roles. A worker-day is **seeded** when it names a non-null `assignmentId`.

- A **full solution** states every worker-day.
- A **partial seed** ("first completion") states only a subset: a non-null `assignmentId` is the seed,
  `null` (not working) and an **omitted** day are both **open** — the solver decides them. A declarative
  or expanded package re-runs from such a seed. (The seed lives at the expanded layer because it
  references `assignmentId`s.)

A seeded day is **soft** by default — the solver may change it. Whether it *penalises* changing a soft
seed is a solve-directive, not a validator rule (see [FUTURE.md](FUTURE.md) §2). Set **`locked: true`**
to make the day a **hard** pin the solver must keep — the solution-side twin of the expanded
`availability.days[].forced`. The validator enforces:

- `locked: true` requires a non-null `assignmentId` (you cannot lock a rest);
- **seed↔expanded merge coherence** — if the expanded worker-day carries a `forced` pin, a stated
  `assignmentId` must equal it (a seed may not contradict a pre-commitment).

### Merging a seed into a problem

`merge.py` applies a seed's hard decisions to a problem, producing a **seeded expanded**:

```bash
python3 src/schema_v3/merge.py problem.expanded.json solution.json   # expanded + seed
python3 src/schema_v3/merge.py problem.json          solution.json   # declarative + seed
```

- Each `locked` seed day becomes that worker-day's **`forced`** pin. A **declarative** input is
  transformed first (expansion is deterministic, so the seed's `A####` ids line up).
- **Locks only.** Soft seeds are left in the seed file — they are a starting point, not a problem
  constraint, and the expanded form has no field for one. A solver reads them alongside this output.
- The output is a **plain expanded** — it conforms to `schema-v3-expanded.json` unchanged and differs
  from its input only by the added pins, so any existing consumer honours it.
- The `demand.csv` the expanded references is copied next to the output, so the result is a complete
  package.
- Every incoherent lock is **fatal and nothing is written** (unknown worker-day, an id outside that
  day's `H_wd`, a `locked` day naming no assignment, a clash with an existing `forced`, or a
  `problemId` mismatch) — a partly-applied seed would not be the problem the seed described.

> Keeping `problem.expanded.json` and `problem.merged.expanded.json` in one folder makes a solution's
> sibling auto-locate ambiguous; validate the merged file explicitly, or pass `--against`.

Because these references point into another file, the JSON Schema layer cannot enforce them. The
validator does, given the problem to check against:

```bash
python3 src/schema_v3/validator.py solution.json --against problem.expanded.json
# or, if a single *.expanded.json sits beside the solution, just:
python3 src/schema_v3/validator.py solution.json
```

Without an expanded problem to resolve against, the validator runs the schema layer only and **warns**
that the cross-checks were skipped. `examples/sisqual_example/solution.json` is a worked instance.

Point the validator at a **folder** to validate whole packages — each directory's declarative /
expanded / solution forms (plus their CSVs), with a cross-form check that they name the same problem:

```bash
python3 src/schema_v3/validator.py examples/      # validates every package under it
```
