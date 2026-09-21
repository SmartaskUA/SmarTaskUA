# v4.0 formats

JSON carries structure; four CSVs carry the matrices that would bloat it. This
document covers the CSVs and the semantics the JSON Schema cannot express. For
what changed from v3.0 read [MIGRATION-3.0-to-4.0.md](MIGRATION-3.0-to-4.0.md)
first; for how SISQUAL's raw export differs from the canonical form, read
[DIALECT.md](DIALECT.md).

---

## Time, and the one place it is not minutes

Durations are **integer minutes** — `workMinutesPerDay`, `ScheduleWeightMinutes`,
`startMin`/`endMin`, every `parameters` value ending in `Minutes`.
`timeGrid.slotMinutes` (SISQUAL emits 30, must divide 1440) cuts the day into the
timeslots `T` the model reasons over.

Clock times appear as `HH:MM` in the demand CSVs and as **minutes from 00:00** in
the schedule catalogue. Minutes may exceed 1440 to express times after midnight, so
`22:00-06:00` is `1320-1800`. A window whose `end <= start` is read as crossing
midnight — the one place a reader still infers roll-over, and it is confined to the
`HH:MM` layer; the catalogue states the minutes outright.

**The exception, and it is a real one:** `schedule_input.csv` cells are **hours**.
A contract says `workMinutesPerDay: 480` and the matching cell says `8`. One
bundle, two units. v3.0 was minutes everywhere and rejected a cell of `8` outright;
v4.0 keeps hours because that is what SISQUAL's exporter emits and we do not
control it. We are asking them to switch — [next_meeting.md](next_meeting.md)
item 18 — and until they do, a cell above 24 is rejected as an unconverted v3.0
minute count.

### Everything must fit the grid

Every duration must be a multiple of `slotMinutes`, and **that includes each
contract's `workMinutesPerDay`**. This is not pedantry. `examples/cenario1_nlm/` is
a real SISQUAL bundle in which contract `NL_36` is 432 minutes a day on a
30-minute grid; 432 is not a multiple of 30, so no shift of the contracted length
can be placed on any day, and all 335 worker-days that ask for work are
unsatisfiable. The validator reports the contract once and collapses the repeats.

## The coverage coordinate

v3.0 keyed coverage on a single `competency` code. v4.0 keys it on a **pair**,
`(tableName, tableValue)` — a dimension and a value within it. `Team/T1` and
`Responsibility/A` are two coordinates on two different axes, and a worker may hold
both at once; a demand row on each must be satisfied independently, even in the
same hour.

Every pair must be declared in **`demand.dimensions[]`**, which is required. This
is the one piece v4.0 adds that SISQUAL does not emit, and it exists because
without it nothing is checkable: their bundles declare no catalogue, and the three
places a coordinate appears — employees, `priorityHierarchy`, the demand CSV —
use two different languages for the dimension name with no overlap. The adapter
synthesises the catalogue from the union of all three.

## The three demand CSVs

SISQUAL splits demand along their own `InpServiceLevelDetail` sub-collections.
**Two of the three are header-only in every bundle they have sent**, but all three
pointers are required so that a package states its grains explicitly.

| file | JSON key | unit | grain |
|---|---|---|---|
| `days_demand.csv` | `demand.dataFileDays` | workload **minutes** | one row per (date, dimension) — whole day |
| `periods_demand.csv` | `demand.dataFilePeriods` | **headcount** | one row per (date, dimension, window) |
| `shifts_demand.csv` | `demand.dataFileShifts` | **headcount** | one row per (date, shift type, dimension) |

```
date,tableName,tableValue,minimum,ideal,estimated,start,end
2026-01-01,Team,T1,2,0,0,10:00,11:00
```

`shifts_demand.csv` inserts `workPeriod` at position 2; the other two are
identical.

> **`days` and `periods` have byte-identical headers and different units.** Only
> the JSON key that points at a file says which it is. Never decide by looking at
> the file — and if you write a reader, take the grain as a parameter rather than
> sniffing, which is why `core.read_demand` does.

| column | meaning |
|---|---|
| `date` | `YYYY-MM-DD`, inside `temporalScope` |
| `tableName`, `tableValue` | the coverage coordinate; the pair must be in `demand.dimensions[]` |
| `minimum` | on the headcount grains, workers desired [`alpha_dts`] — **a float**, `4.5` occurs in real data. On the days grain, minutes of workload. |
| `ideal`, `estimated` | see below |
| `start`, `end` | `HH:MM`. **Mandatory** on the periods and shifts grains; unused on days. |

Rules:

- One row per `(date, tableName, tableValue, window)` — and per `workPeriod` too on
  the shifts grain.
- **A missing row means that coordinate is not operating in that window that day.**
  A date with no windowed row anywhere is closed and sits outside every week.
- Windows for one `(date, dimension)` should not overlap; a worker in the overlap
  would count toward both, so the validator warns.
- All three values must be non-negative. Following v3.0, **`0` means unset**, not
  zero workers.

### The ordering of `minimum`, `ideal`, `estimated` is NOT established

v3.0 was ascending — `minimum ≤ empiric ≤ maximum`. v2.6, whose header this is,
was `minimum ≤ estimated ≤ ideal`: **`ideal` was the upper bound sitting in the
middle column.** SISQUAL writes `0` in both columns in every row of every bundle,
so the data cannot settle it.

The validator therefore enforces **no ordering between the three**, only
non-negativity, and the column names are left exactly as SISQUAL writes them.
Renaming them to v3.0's would assert an ordering nothing confirms, and that is the
migration failure that corrupts silently: the file still parses, every check still
passes, and the staffing is wrong. [next_meeting.md](next_meeting.md) item 1
resolves it.

### Which bound is hard is not stated here

The three numbers are **data**. Whether a solver reads each as a hard cap, a soft
target, or ignores it is not stated in v4.0 — this is the problem definition only.

## schedule_input.csv

One row per employee, one column per date, spanning `temporalScope` exactly.

```
employee_id,2026-01-01,2026-01-02,2026-01-03
20072412,HOL,8,EQUALS:10:00-14:00
```

| cell | meaning |
|---|---|
| `A` | work the contract's `workMinutesPerDay` |
| `8` | work exactly 8 **hours** |
| `7.2` | fractional hours, if whole minutes (7.2 h = 432 min). SISQUAL writes `"7,2"`. |
| `EQUALS:a-b[,c-d…]` | work exactly this block; several ranges = one split shift |
| `INCLUDE:a-b[,c-d…]` | one block **covering** all listed windows (shift ⊇ window) |
| `WITHIN:a-b[,c-d…]` | one block fitting **inside** one listed window (shift ⊆ window) |
| `EXCEPT:a-b[,c-d…]` | unavailable during **all** listed windows |
| any other code | must be declared in `scheduleInput.dayOffCodes` |
| *(blank)* | **no assignments** — not "unconstrained" |

The four operators are carried over from v3.0 and remain authorable, but
**SISQUAL's exporter emits none of them** — every cell in every bundle is a number
or a day-off code. Overlapping or touching ranges are coalesced into their union,
so only a real gap yields a split shift.

`INCLUDE` and `WITHIN` are opposite containments. `INCLUDE:12:00-13:00` forces the
shift to be present for all of noon–1pm and it extends around it;
`WITHIN:08:00-20:00` requires the shift to sit inside 08:00–20:00.

### Day-off codes

Any cell that is not a number and not an operator window is a day-off code, and
every one must be declared under `scheduleInput.dayOffCodes` — a map keyed by the
code, each entry `{kind, name?, description?}`. There are no implicit codes. Keys
may be non-ASCII: SISQUAL uses `Fér`.

`kind` is what the model acts on:

- **`preferable`** [`D_wk`] — soft. The solver may schedule over it at a penalty.
  Typically `DO`.
- **`unavailable`** [`U_wk`] — hard. No assignment permitted. Typically `HOL`,
  `NOT`, `Fér`.

Both feed the per-week equality `n_wk = |D_k| − |U_wk| − |D_wk|`, so a
misclassification moves that week's working-day target. Because each code is a key
with exactly one `kind`, classifying one two ways is unrepresentable.

## Competence levels

**Level 1 is the highest.** Larger numbers are progressively lower, so your most
senior person is level 1 and `level: 5` is more junior than `level: 2`. This
follows MathematicalDefinition7 — *"l = 1 represents the highest level and
l = |L| represents the lowest level"*.

It reads backwards to most people, so it is worth stating twice: a
`priorityHierarchy` entry with `minAbilityLevel: 1` reaches that coordinate's **most
senior** workers, not its juniors.

> **Careful — "level" means two opposite things in this document.** A *competence*
> level is better when the number is **lower**. Demand's `ideal` and `estimated`
> are larger when you want **more** people. Same word, inverted direction.

Nothing can validate this for you. Author it backwards and every file still
parses, every check still passes, and the schedule quietly staffs the wrong people.

One employee may hold several coordinates at once — that is normal. Holding the
**same** coordinate twice over the same dates at two different levels leaves the
level undefined; SISQUAL emits exactly that for three employees in Cenário 2, so
the validator warns rather than errors and says to take the lower number.

## priorityHierarchy

Fill order, plus the alarm-table settings that drive it. Sort by `rank`; lower is
filled first. Ordering follows `rank`, **not array position**, so re-sorting the
array for display is always safe, and `rank` must be unique.

It is a nine-field projection of SISQUAL's ~40-field `InpGenerationRules`:
`maxAlarmTableType` names which demand columns the alarm table consults and in
what fallback order (`MaxAlarmLevel_Estimate_Ideal_Minimum` is the only value
observed), `generationSequenceType` says how the generator walks the rank
(`BY_LEVEL`, `BY_ALARM_TABLE`), and `minAbilityLevel`/`maxAbilityLevel` bound which
competence levels the rank reaches — remembering that `min` is the **smaller
number** and therefore the more senior.

## constraints

Rules above the contract level. v3.0 removed this block outright and treated a
leftover as an error, on the principle that nothing enters the schema until a
consumer reads it. v4.0 re-admits it because SISQUAL now emits real labour law
here — `InpLabourLawCollection`:

```json
{ "id": "0101010101", "type": "RosterLegislation",
  "parameters": { "MaxConsecutiveWorkDays": 5,
                  "MaxConsecutiveWorkDaysInWeek": 5,
                  "MinDistanceBetweenShiftsInMinutes": 660 },
  "startDate": "2026-01-01T00:00:00", "enabled": true }
```

`parameters` is a deliberately open bag. The validator acts on
`MaxConsecutiveWorkDays` and `MaxConsecutiveWorkDaysInWeek` and carries the rest
unread — which is the stored-but-ignored trap v3.0 cleaned out, accepted here only
because the block is genuinely populated and a consumer is coming.

`constraints.soft[]` is present and empty in every bundle, so its element shape is
unknown and the schema leaves it unconstrained.

## The ScheduleCode catalogue

`schedules.dataFile` points at the menu a result must pick from — SISQUAL's
`InpScheduleUsedCollection`, which their exporter does **not** emit; it arrived as
an email attachment.

```
code,description,scheduleWeightMinutes,startMin,endMin
9003,09:00-17:00,480,540,1020
9004,22:00-06:00,480,1320,1800
3,Day off,0,,
```

`startMin`/`endMin` are derived from `description` so the catalogue is usable
without re-parsing strings, and `endMin` passes 1440 when the shift crosses
midnight rather than leaving a reader to infer it.

Codes with no window leave both blank. The real catalogue has four:
`1 Espaço`, `3 Day off`, `4 Vazio`, and `1020 Flexible` — the last has a length
(480 minutes) but no fixed position, which is v3.0's synthesis model appearing
inside the menu, and nobody has told us what a solver may do with it.

Two facts about the real catalogue that matter to a solver: it holds 1,277 codes,
and it is built on a **15-minute** grid while every bundle declares a 30-minute
one, so **914 of its codes are unreachable** on the grid as specified. It is also
the *without-meal* catalogue: `ScheduleCode 100154`, which appears in SISQUAL's own
result sample, is not in it. See [next_meeting.md](next_meeting.md) items 5–7.

## Result form

The output half: what a solver chose, in the shape WFM ingests. It does not
restate the problem, it references it:

- `RosterCode` must equal the problem's `metadata.rosterCode`.
- `EmployeeCode` must be an employee, `Date` must be in `temporalScope`, and there
  must be at most one entry per employee-day.
- `ScheduleCode` must resolve in the catalogue, when one is supplied. Codes `1`,
  `3` and `4` mean rest rather than a worked block.
- A day the problem marked `unavailable` may not carry a working ScheduleCode.

Because those references point into another file, the JSON Schema layer cannot
enforce them; `validate_result.py` does, given the problem:

```bash
PYTHONPATH=src python3 -m schema_v4.validator result.json --against problem.json
# or, if a single declarative problem sits beside it, just:
PYTHONPATH=src python3 -m schema_v4.validator result.json
```

Without a problem to resolve against, the validator runs the schema layer only and
**warns** that the cross-checks were skipped.
