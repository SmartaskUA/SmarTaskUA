# Sisqual ↔ v3.0 — format comparison and merge proposal

How Sisqual's scheduling exchange format lines up with schema v3.0, tiered by how hard each piece is
to merge, plus what to do about the parts only Sisqual has. Sources compared:
`reference/sisqual-json-import-export/JSON-Import.md` and `JSON-Export.md` against the three v3.0
schemas (`schemas/`), the two CSVs, and the template. This is the reconnaissance for **`../FUTURE.md`
§6** ("Reconciling the Sisqual import/export format").

## TL;DR

- **The names are inverted — read this first.** Sisqual **Export** (`Inp*`) is data going *into* the
  generator — it is **the problem**. Sisqual **Import** (`Out*`) is the generator's result read *back*
  — it is **the solution**. Everything below follows from this.
- **The two formats describe the same problem.** Contracts, employees, skills+levels, holidays, and
  per-employee-per-day state map cleanly or with a small transform. Our move to minutes was partly
  *to* match Sisqual.
- **One deep divergence:** Sisqual picks shifts from a **pre-built catalog** (`ScheduleCode`); v3
  **synthesizes** assignments from contract length + demand window. Resolvable — *ingest* their
  catalog instead of synthesizing — and the **expanded form is the natural seam** for it.
- **What only Sisqual has is mostly the roadmap we already wrote.** Tasks, responsibilities,
  generation rules, labour-law objects — each lands on an existing `../FUTURE.md` item, not a new backlog.
- **Chosen path:** a **middle-ground merged schema** — v3.0 as the base, absorbing the Sisqual concepts
  that earn their place tier by tier; not a forever-adapter, not a full superset. Decisions live in the
  [tier files](SISQUAL-MERGE-PROPOSAL.md).

> **State of play.** No code reads the raw Sisqual JSON yet. The repo's Sisqual *solvers*
> (`src/scheduler/algorithms/{ILP,CSP}_Sisqual_Hours*.py`, `sisqual_hours_utils.py`) and the
> `data/problems/SISQUAL_*` bundles parse our *internal* problem JSON — so the **model** already
> absorbed Sisqual's problem shape, but the **format adapter** is the missing piece this proposal scopes.

## The correspondence

| Sisqual payload | direction | v3.0 form |
|---|---|---|
| **Export** `Inp*` — InpRosterDetail, InpMasterData, InpServiceLevelDetail, InpGenerationRules | into the generator = **problem** | **declarative** + `demand.csv` + `schedule_input.csv`; the shift catalog → **expanded** |
| **Import** `Out*` — OutRosterTeamDays, OutScheduleUseds | result read back = **solution** | **solution** (+ `OutScheduleUseds` ↔ **expanded** `assignmentCatalog`) |

The three tier tables plus the "Set aside" table below are, together, the complete field-level map:
every collection in both Sisqual docs appears in exactly one of them. These tables are the **analysis**;
the per-tier **decisions** built from them live in the tier files (see the [index](SISQUAL-MERGE-PROPOSAL.md)).

---

## Tier 1 — Easy (clean 1:1, or a mechanical transform)

| Sisqual (`Inp*`/`Out*`) | v3.0 home | note |
|---|---|---|
| `RosterCode` | `metadata.problemId` | the "quadro" is the problem identity |
| `InpRosterDetail.StartDate` / `EndDate` | `temporalScope.start` / `end` | ISO datetime → date |
| `EmployeeCode` | `employees.list[].id` | — |
| `InpRosterLineDataCollection[].InpEmployeeContracts[]` (`ContractCode`, `StartDate`, `EndDate`) | `employees.list[].contractAssignments[]` (`contractType`, `start`, `end`) | both date-ranged, both allow gaps |
| `InpEmployeeAbilities[]` (`AbilityID`, `Level`, dates) | `employees.list[].teamAssignments[]` (`team`, `level`, dates) | identical shape (granularity caveat → Tier 2) |
| `InpContractCollection.TotalDailyMinutes` | contract `workMinutesPerDay` | both minutes |
| `InpContractCollection.TotalWeeklyMinutes` | contract `constraints.maxMinutesPerWeek` | — |
| `InpLabourLawCollection.MaxConsecutiveWorkDaysInWeek` | contract `constraints.maxConsecutiveDays` | — |
| `InpLabourLawCollection.DayOfWeek` (0=Sun…6=Sat) | `calendar.weekStart` | index → weekday name |
| `IsHolliday` / `GenerateOnHoliday` marks | `calendar.holidays[]` | our `hasEve` is an extra we add |
| all `HH:MM:SS` / ISO datetimes | minutes-from-midnight on the `timeGrid` | mechanical; both minute-granular |

## Tier 2 — Medium (the concept maps, but structure or semantics differ — needs a decision)

| Sisqual | v3.0 home | decision to make |
|---|---|---|
| `InpServiceLevelByShifts[]` (`ShiftTypeCode` M/T/N; `Minimum/Empiric/Estimated/Maximum/Total Value`) and `InpServiceLevelByPeriods[]` (headcount per window) | `demand.csv` rows (`workPeriod`, `minimum`, `empiric`, `maximum`) | `ShiftTypeCode`/period ↔ `workPeriod`; Sisqual keys demand on `TableName`/`TableValue` (e.g. `"Task"/"7"`) ↔ our `team`; **drop `Estimated` + `Total`** (we kept `empiric`, dropped `estimated` in v2.6→3.0); float → int |
| `InpRosterSchedulesCollection[]` / `InpRosterTeamDays[]` per employee-day (`AbsenceCodeFullDay`, `ScheduleCode`, `Locked`, `ScheduleAvailabilityCode`) | `schedule_input.csv` cells; `Locked` → expanded `availability.days[].forced` | same role (per-worker-per-day input), different container (JSON ↔ CSV) and vocabulary (`ScheduleCode` ref ↔ `A`/minutes/`EQUALS`/`INCLUDE`/`EXCEPT`/code) |
| `DayType` (0 work, 1 *Folga Complementar*, 2 *Folga Obrigatória*, 3 *Folga*) + `AbsenceCodeCountAsDayOff` | `scheduleInput.dayOffCodes` (`kind`: `preferable`\|`unavailable`) | ours is *soft vs hard*; theirs is *which rest* (Sat-complementary vs Sun-obligatory) + *counts-toward-limits*. Build a code-translation table; the "counts as day off" bit has no home yet (→ set aside) |
| `InpEmployeeAbilities.AbilityID` vs `InpRosterLines.TeamCode` (skill and team are **separate**) | `teamAssignments[].team` (we conflate **team = skill dimension `S`**) | pick: collapse Ability→team, or keep team as an org grouping and map Ability→a v3 "team". Touches `../FUTURE.md` §4 |
| `OutRosterTeamDays[]` (`ScheduleCode` per emp-day) | `solution.assignments[].days[].assignmentId` | id-scheme bridge: `ScheduleCode` ↔ synthesized `A####` (depends on the catalog decision, Tier 3) |
| `OutScheduleUseds[]` (`ScheduleCode`, `ScheduleWeight` min, `StartDate1/2`–`EndDate1/2`) | expanded `assignmentCatalog[]` (`id`, `intervals[]`) | near-direct analog. Two date pairs = **split shift** = two `intervals`. `ScheduleWeight` (paid minutes) = total interval length (v3 has no break, so paid = clock) |

## Tier 3 — Hard (fundamental model divergence)

**Shift catalog vs synthesized assignments — the one that actually clashes.**
Sisqual chooses a pre-built `ScheduleCode` from a menu (`InpScheduleUsedCollection`,
`InpRosterSchedulesCollection`). v3 has **no authored shift menu**: `transform.py` synthesizes every
contiguous block of the contract's length across the demand window, and `assignmentCatalog` is the
*output* of that, deduplicated.

- **Resolution — ingest, don't synthesize.** Treat each Sisqual `ScheduleCode` as one
  `assignmentCatalog` entry (its `StartDate1/2` become the `intervals`) and skip the block-synthesis
  step. v3's expanded schema already permits an arbitrary, externally-fixed catalog — nothing about it
  assumes the transformer produced it.
- **The expanded form is the seam.** It already (a) carries a free-form `assignmentCatalog`, and (b)
  has `availability.days[].forced` for pre-committed days — the exact shape of Sisqual's `Locked`. So
  Sisqual's shift-catalog world docks at the **expanded** layer, and the **declarative** authoring
  layer stays untouched.

The other hard items are whole feature-areas v3 simply doesn't have. They have no home to merge
*into*, so they are collected under **Set aside** rather than forced into a tier.

---

## Set aside — what only Sisqual has (the backlog)

These are Sisqual capabilities with no v3.0 equivalent. The point of the list: **almost every one is
already a `../FUTURE.md` item** — Sisqual's extra surface validates our roadmap instead of adding to it.

| Sisqual feature | what it is | lands on |
|---|---|---|
| **Tasks** — `OutRosterTeamDayTasks[]` (`TaskID` + start/end within a shift), `InpTaskAbilityCollection[]` | intra-shift task allocation (worker does Task 8 07:30–09:30, Task 14 09:30–13:00…). Our `solution.skillPerSlot` is coarser (team per slot, not named task) | `../FUTURE.md` §4 (org model) |
| **Responsibilities** — `OutRosterTeamDayResponsibilities[]`, `InResponsabilityCollection[]` (cost-centre, group, pool, profile, type), `InpResponsibilityAbilityCollection[]` | a second assignment axis alongside tasks | `../FUTURE.md` §4 (explicitly names responsibilities) |
| **Generation rules** — the entire `InpGenerationRules` block (rule indices/versions, algorithm steps, alarm tables, generation sequence, per-weekday `GenerateOn*` flags, `GenerateScheduleGetPriorityType`, `FollowLevelByLevel`, responsibility waste/override/cover, schedule blacklists, min/max weekly weight, `FindScheduleType`, `DaysForwardToValidateLegislation`) | *how to solve* — algorithm selection, objectives, directives | `../FUTURE.md` §2 (solve-directives registry) — the big one |
| **Labour-law objects** — `InpLabourLawCollection[]` + per-employee `InpEmployeeLLabourLawLegislationCollection[]`; `DistanceBetweenShiftsInMinutes` | named, date-ranged, per-employee legislation. `DistanceBetweenShiftsInMinutes` is exactly the min-rest we cut | `../FUTURE.md` §1 (rest) + §2 (registry) + §3 (per-employee scope) |
| **Per-weekday & holiday contract weights** — `WeightMonday…Sunday`, `WeightHolidayBusinessDay/Saturday/Sunday` | different shift length per weekday / per holiday type; our `workMinutesPerDay` is one number | contract extension; relates to `../FUTURE.md` §5 |
| **Monthly / yearly caps** — `TotalMonthlyMinutes`, `TotalYearMinutes` | limits beyond daily/weekly | contract extension |
| ~~**Split-shift authoring**~~ — two `StartDate/EndDate` pairs per schedule | **DONE** — both forms now handle it: the expanded catalog is multi-interval and the declarative `EQUALS:a-b,c-d` cell authors it (see MEDIUM M2.a) | resolved |
| **Estimated + workload demand** — `EstimatedValue`; `InpServiceLevelByDays[]` (minutes of workload, not headcount) | our demand is headcount only (`alpha_dts`) | demand extension / new demand mode |
| **Minor advisory fields** — `Legend`/`Description`, `ScheduleAvailabilityCode`, `PotentialCycleScheduleWeightWhenScheduleIsSpace`, `InpEmployeeGeneratedParameterCollection`, `AlarmTable*` | display labels, cycle hints, generation params | drop on import, or fold into the §2 registry |

---

## Approaches considered

Two ways to reconcile the formats were weighed:

- **Edge adapter** — keep the v3 core untouched and translate Sisqual ↔ v3 at the boundary
  (`sisqual_import.py` / `sisqual_export.py`), ingesting `ScheduleCode`s as a fixed expanded
  `assignmentCatalog`. Smallest change, but the two formats never converge — you maintain a translator
  forever.
- **Superset schema** — fold every Sisqual concept (tasks, responsibilities, rules, labour law) into one
  schema. Round-trips natively, but reintroduces the breadth v3.0 deliberately cut.

### Chosen — a middle-ground merged schema

**v3.0 as the base, growing to absorb the Sisqual concepts that earn their place, tier by tier.** The
genuine additions surfaced in review (S1 roster, S2 datetime, S3 labour law, …) join the schema; the rest
stays deferred behind its `../FUTURE.md` item. Neither a forever-translator nor a full superset. The tiered
decisions live in the tier files — see the [index](SISQUAL-MERGE-PROPOSAL.md).

### What v3 brings that Sisqual doesn't (kept in the merge)

- **Open assignment synthesis** — no shift-code catalog to author and maintain.
- **Clean ordinal `priorityOrder`** — fill order is one small list; in Sisqual it is scattered through
  `InpGenerationRules` (`GenerateScheduleGetPriorityType`, `FollowLevelByLevel`, `AbilityLevelSignal/Value`).
- **Explicit shortfall reporting** — `solution.shortfalls[]` (`z_dts`); the Sisqual `Out*` format carries none.
- **Two interchangeable forms** (declarative ↔ expanded) with a **deterministic** transformer.

---

## Foundational decisions

The ground rules every tier assumes; they live here so they are stated once.

**Common ground — no debate:** minutes everywhere; per-employee, date-ranged assignments (v3 already
generalises Sisqual, open-ended via `end: null`); skill carries a level.

**The one principle:** where both schemas can express a fact, take **v3's structure as the canvas** and
make sure **every Sisqual value round-trips losslessly** — v3's shape, Sisqual's completeness.

✅ **v3.0 is the base schema** — the smaller, more regular one (one fact, one place); it already
generalises Sisqual's date-ranging, and its two-form architecture is where the shift catalog docks (Hard
tier). *(Alternatives: Sisqual-base, or greenfield — both heavier.)*

✅ **Keep the JSON + CSV hybrid** — Sisqual is receptive to CSVs, so JSON carries structure and CSV carries
the big matrices (`demand.csv`, `schedule_input.csv`). Sisqual's service-level / roster-day *collections*
become CSV rows, not more JSON.

🔀 **Choice N1 — canonical vocabulary:** v3 names (`workMinutesPerDay`, `teamAssignments`) *(recommended)*
vs Sisqual names (`TotalDailyMinutes`, `InpEmployeeAbilities`); the middle is v3 names + a published
Sisqual↔merged alias table. The tier files are written in v3 names as a placeholder — picking otherwise is
a find-replace, not a redesign.

✅ **Preserve Sisqual codes in dedicated optional fields** — `metadata.rosterCode` and the like, rather
than overloading a primary id. *(Alternative: a generic `externalRefs` bag — rejected as overkill.)*
