# v4.0 formats

JSON carries structure; four CSVs carry the matrices that would bloat it, and a fifth carries the shift menu. This document covers the CSVs and the semantics the JSON Schema cannot express. For what changed from v3.0 read [MIGRATION-3.0-to-4.0.md](MIGRATION-3.0-to-4.0.md) first; for where SISQUAL's current export differs from v4.0, see [next_meeting.md](../next_meeting.md) under *Naming and format*.

---

## Time, and the one place it is not minutes

Durations are **integer minutes** — `workMinutesPerDay`, `ScheduleWeightMinutes`, `startMin`/`endMin`, every `parameters` value ending in `Minutes`. `timeGrid.slotMinutes` (SISQUAL emits 30, must divide 1440) cuts the day into the timeslots `T` the model reasons over.

Clock times appear as `HH:MM` in the demand CSVs and as **minutes from 00:00** in the schedule catalogue. Minutes may exceed 1440 to express times after midnight, so `22:00-06:00` is `1320-1800`. A window whose `end <= start` is read as crossing midnight — the one place a reader still infers roll-over, and it is confined to the `HH:MM` layer; the catalogue states the minutes outright.

**The exception, and it is a real one:** `schedule_input.csv` cells are **hours**. A contract says `workMinutesPerDay: 480` and the matching cell says `8`. One bundle, two units. v3.0 was minutes everywhere and rejected a cell of `8` outright; v4.0 keeps hours because that is what SISQUAL's exporter emits and we do not control it. We are asking them to switch — [next_meeting.md](../next_meeting.md) item 16 ("should be minutes, not hours") — and until they do, a cell above 24 is rejected as an unconverted v3.0 minute count.

### Everything must fit the grid

Every duration must be a multiple of `slotMinutes`, and **that includes each contract's `workMinutesPerDay`**. This is not pedantry. Sisqual's Cenário 1 bundle (kept as raw provenance under `reference/`, and not shipped as an example because of this) declares contract `NL_36` at 432 minutes a day on a 30-minute grid; 432 is not a multiple of 30, so no shift of the contracted length can be placed on any day, and all 335 worker-days that ask for work are unsatisfiable. The validator reports the contract once and collapses the repeats.

## The coverage coordinate

v3.0 keyed coverage on a single `competency` code. v4.0 keys it on a **pair**, `(tableName, tableValue)` — a dimension and a value within it. `Team/T1` and `Responsibility/A` are two coordinates on two different axes, and a worker may hold both at once; a demand row on each must be satisfied independently, even in the same hour.

Every pair must be declared in **`demand.dimensions[]`**, which is required. This is the one piece v4.0 adds that SISQUAL does not emit, and it exists because without it nothing is checkable: their bundles declare no catalogue, and the three places a coordinate appears — employees, `priorityHierarchy`, the demand CSV — use two different languages for the dimension name with no overlap, so declaring the set explicitly is the only thing that makes any of it checkable.

## The three demand CSVs

SISQUAL splits demand along their own `InpServiceLevelDetail` sub-collections. **Two of the three are header-only in every bundle they have sent**, but all three pointers are required so that a package states its grains explicitly.

| file | JSON key | unit | grain |
|---|---|---|---|
| `days_demand.csv` | `demand.dataFileDays` | workload **minutes** | one row per (date, dimension) — whole day |
| `periods_demand.csv` | `demand.dataFilePeriods` | **headcount** | one row per (date, dimension, window) |
| `shifts_demand.csv` | `demand.dataFileShifts` | **headcount** | one row per (date, shift type, dimension) |

```
date,tableName,tableValue,minimum,ideal,estimated,start,end
2026-01-01,Team,T1,2,0,0,10:00,11:00
```

`shifts_demand.csv` inserts `workPeriod` at position 2; the other two are identical.

> **`days` and `periods` have byte-identical headers and different units.** Only the JSON key that points at a file says which it is. Never decide by looking at the file — and if you write a reader, take the grain as a parameter rather than sniffing, which is why `core.read_demand` does.

| column | meaning |
|---|---|
| `date` | `YYYY-MM-DD`, inside `temporalScope` |
| `tableName`, `tableValue` | the coverage coordinate; the pair must be in `demand.dimensions[]` |
| `minimum` | on the headcount grains, workers desired [`alpha_dts`] — **a float**, `4.5` occurs in real data. On the days grain, minutes of workload. |
| `ideal`, `estimated` | see below |
| `start`, `end` | `HH:MM`. **Mandatory** on the periods and shifts grains; unused on days. |

Rules:

- One row per `(date, tableName, tableValue, window)` — and per `workPeriod` too on the shifts grain.
- **A missing row means that coordinate is not operating in that window that day.** A date with no windowed row anywhere is closed and sits outside every week.
- Windows for one `(date, dimension)` should not overlap; a worker in the overlap would count toward both, so the validator warns.
- All three values must be non-negative. Following v3.0, **`0` means unset**, not zero workers.

### The ordering of `minimum`, `ideal`, `estimated` is NOT established

v3.0 was ascending — `minimum ≤ empiric ≤ maximum`. v2.6, whose header this is, was `minimum ≤ estimated ≤ ideal`: **`ideal` was the upper bound sitting in the middle column.** SISQUAL writes `0` in both columns in every row of every bundle, so the data cannot settle it.

The validator therefore enforces **no ordering between the three**, only non-negativity, and the column names are left exactly as SISQUAL writes them. Renaming them to v3.0's would assert an ordering nothing confirms, and that is the migration failure that corrupts silently: the file still parses, every check still passes, and the staffing is wrong. [next_meeting.md](../next_meeting.md) item 1 ("the ordering of") resolves it.

### Which bound is hard is not stated here

The three numbers are **data**. Whether a solver reads each as a hard cap, a soft target, or ignores it is not stated in v4.0 — this is the problem definition only.

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

The four operators are carried over from v3.0 and remain authorable, but **SISQUAL's exporter emits none of them** — every cell in every bundle is a number or a day-off code. Overlapping or touching ranges are coalesced into their union, so only a real gap yields a split shift.

`INCLUDE` and `WITHIN` are opposite containments. `INCLUDE:12:00-13:00` forces the shift to be present for all of noon–1pm and it extends around it; `WITHIN:08:00-20:00` requires the shift to sit inside 08:00–20:00.

### Day-off codes

Any cell that is not a number and not an operator window is a day-off code, and every one must be declared under `scheduleInput.dayOffCodes` — a map keyed by the code, each entry `{kind, name?, description?}`. There are no implicit codes. Keys may be non-ASCII: SISQUAL uses `Fér`.

`kind` is what the model acts on:

- **`preferable`** [`D_wk`] — soft. The solver may schedule over it at a penalty. Typically `DO`.
- **`unavailable`** [`U_wk`] — hard. No assignment permitted. Typically `HOL`, `NOT`, `Fér`.

Both feed the per-week equality `n_wk = |D_k| − |U_wk| − |D_wk|`, so a misclassification moves that week's working-day target. Because each code is a key with exactly one `kind`, classifying one two ways is unrepresentable.

## Competence levels

**Level 1 is the highest.** Larger numbers are progressively lower, so your most senior person is level 1 and `level: 5` is more junior than `level: 2`. This follows MathematicalDefinition7 — *"l = 1 represents the highest level and l = |L| represents the lowest level"*.

It reads backwards to most people, so it is worth stating twice: a `priorityHierarchy` entry with `minAbilityLevel: 1` reaches that coordinate's **most senior** workers, not its juniors.

> **Careful — "level" means two opposite things in this document.** A *competence* level is better when the number is **lower**. Demand's `ideal` and `estimated` are larger when you want **more** people. Same word, inverted direction.

Nothing can validate this for you. Author it backwards and every file still parses, every check still passes, and the schedule quietly staffs the wrong people.

One employee may hold several coordinates at once — that is normal. Holding the **same** coordinate twice over the same dates at two different levels leaves the level undefined; SISQUAL emits exactly that for three employees in Cenário 2, so the validator warns rather than errors and says to take the lower number.

## priorityHierarchy

Fill order, plus the alarm-table settings that drive it. Sort by `rank`; lower is filled first. Ordering follows `rank`, **not array position**, so re-sorting the array for display is always safe, and `rank` must be unique.

It is a nine-field projection of SISQUAL's ~40-field `InpGenerationRules`: `maxAlarmTableType` names which demand columns the alarm table consults and in what fallback order (`MaxAlarmLevel_Estimate_Ideal_Minimum` is the only value observed), `generationSequenceType` says how the generator walks the rank (`BY_LEVEL`, `BY_ALARM_TABLE`), and `minAbilityLevel`/`maxAbilityLevel` bound which competence levels the rank reaches — remembering that `min` is the **smaller number** and therefore the more senior.

## constraints

Rules above the contract level. v3.0 removed this block outright and treated a leftover as an error, on the principle that nothing enters the schema until a consumer reads it. v4.0 re-admits it because SISQUAL now emits real labour law here — `InpLabourLawCollection`:

```json
{ "id": "0101010101", "type": "RosterLegislation",
  "parameters": { "MaxConsecutiveWorkDays": 5,
                  "MaxConsecutiveWorkDaysInWeek": 5,
                  "MinDistanceBetweenShiftsInMinutes": 660 },
  "startDate": "2026-01-01T00:00:00", "enabled": true }
```

`parameters` is a deliberately open bag. The validator acts on `MaxConsecutiveWorkDays` and `MaxConsecutiveWorkDaysInWeek` and carries the rest unread — which is the stored-but-ignored trap v3.0 cleaned out, accepted here only because the block is genuinely populated and a consumer is coming.

`constraints.soft[]` is present and empty in every bundle, so its element shape is unknown and the schema leaves it unconstrained.

## The schedule menu

`schedules.dataFile` points at the menu a result may pick from.

```
code,description,scheduleWeightMinutes,startMin,endMin
3,Day off,0,,
9001,09:00-13:00,240,540,780
9012,09:00-16:00,420,540,960
```

**A code stands for a grouping of hours and nothing else — this file is the translation.** The numbering carries no meaning of its own: `9001` is `09:00-13:00` because that row says so. Need a grouping the menu does not have? Add a row with a new code. Codes are ours to define; nothing is derived from a vendor catalogue.

`startMin`/`endMin` are derived from `description` so the menu is usable without re-parsing strings, and `endMin` passes 1440 when the shift crosses midnight rather than leaving a reader to infer it. Every boundary must land on `slotMinutes`, or a solver on that grid cannot emit the code — the validator warns about any that do not.

A row with **no window and zero weight is a rest sentinel**, and that is how a sentinel is recognised: from the data, not from a hardcoded list. Three of them keep the numbers WFM uses on import (`1` Espaço, `3` Day off, `4` Vazio); a roster that mints the rest of its codes is not otherwise tied to those numbers.

> **What is not here: breaks.** A shift's paid length is its clock length — `scheduleWeightMinutes` equals `endMin - startMin`, always. v4.0 has no meal or break model, so a shift long enough to legally require one is indistinguishable from one that is not. See [FUTURE.md](FUTURE.md) §2.

## Result form

The output half: what a solver chose, in the shape WFM ingests. It does not restate the problem, it references it:

- `RosterCode` must equal the problem's `metadata.rosterCode`.
- `EmployeeCode` must be an employee, `Date` must be in `temporalScope`, and there must be at most one entry per employee-day.
- `ScheduleCode` must resolve in the menu, when one is supplied — a result may only use shifts the problem offers.
- A sentinel code means rest rather than a worked block.
- A day the problem marked `unavailable` may not carry a working ScheduleCode.

### The sidecar catalogue

A result names numeric `ScheduleCode`s and carries no definition of them, so on its own it can be neither read nor checked. It therefore ships a **sidecar CSV**: `result.json` pairs with `result_schedules.csv`, found by convention, in exactly the menu's shape.

```
code,description,scheduleWeightMinutes,startMin,endMin
1014,08:00-16:00,480,480,960
300000,10:00-16:30,390,600,990
```

It holds **the codes the result actually used** — not a copy of the menu. Whatever produces the result produces the sidecar; a row nobody uses is a warning, on the grounds that the file describes this result rather than the menu it drew from.

The convention is a file beside the document rather than a key inside it, and that is deliberate: `schema-v4-result.json` conforms to Sisqual's WFM import API verbatim, and adding a `dataFile` key for our own convenience would break that rule. Sisqual's native equivalent is `OutScheduleUseds` in the JSON; when both are present they must agree.

The validator checks that every code in the result is defined in the sidecar, that every sidecar row is used, and — when the problem also carries a menu — that every sidecar code is one the problem offers and is defined the same way there. A missing sidecar is a **warning**, not an error: a result that arrives from elsewhere will not carry one.

Because those references point into another file, the JSON Schema layer cannot enforce them; `validate_result.py` does, given the problem:

```bash
make validate DIR=result.json ARGS='--against problem.json'
# or, if a single input problem sits beside it, just:
make validate DIR=result.json
```

Without a problem to resolve against, the validator runs the schema layer only and **warns** that the cross-checks were skipped.
