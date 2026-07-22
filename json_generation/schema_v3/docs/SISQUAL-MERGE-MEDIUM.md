# Merge tier — Medium

Part of the [merge proposal index](SISQUAL-MERGE-PROPOSAL.md). The reading legend and the **foundational
decisions** are in [SISQUAL-MERGE.md](SISQUAL-MERGE.md) — the decisions below assume them.

Here the concept maps but the **structure or semantics differ**, so each item needs a call. Every one
keeps the JSON+CSV hybrid: Sisqual's *collections* become CSV rows, not more JSON.

## M1 — Demand: Sisqual's three service-level tables → `demand.csv`

Sisqual states coverage in three tables; v3 has one CSV keyed on `(date, workPeriod, team)`.

| Sisqual table | unit | → merged |
|---|---|---|
| `InpServiceLevelByShifts` (`ShiftTypeCode` M/T/N) | headcount | `demand.csv` rows — `ShiftTypeCode` ↔ `workPeriod` |
| `InpServiceLevelByPeriods` (start–end window) | headcount | `demand.csv` rows — window ↔ a `workPeriod` (or a row `start`/`end` override) |
| `InpServiceLevelByDays` | **workload minutes** | ✗ different unit → **Set aside** (a future workload-demand mode) |

✅ **Decision — the two headcount tables become `demand.csv` rows.** Sisqual keys demand on
`TableName`/`TableValue` (e.g. `"Task"/"7"`) → our `team`; a `roster` column is added iff **S1.a = A**.

🔀 **Choice M1.a — how many value columns?**

| | Option A — our three | Option B — carry `estimated` too *(recommended)* |
|---|---|---|
| columns | `minimum, empiric, maximum` | `minimum, empiric, estimated, maximum` |
| round-trip | drops Sisqual's `EstimatedValue` | lossless — the solver still reads only `minimum` |
| `TotalValue` | dropped in both (an aggregate, recomputable) | dropped in both |

*Recommend B* — lossless round-trip is a foundational rule, and the extra column costs the solver nothing.

✅ **Decision — headcount stays integer.** `minimum` is whole workers desired (`alpha_dts`); Sisqual's
float `empiric`/`maximum` round on import.

## M2 — Per-day worker state: `InpRosterTeamDays[]` → `schedule_input.csv`

The per-employee-per-day JSON collection becomes our CSV matrix (one row per employee, one column per date).

| Sisqual field (per day) | → merged |
|---|---|
| `AbsenceCodeFullDay` | a day-off code cell (translated via M3) |
| `ScheduleCode` (a fixed shift) | see M2.a |
| `Locked` | expanded `availability.days[].forced` |
| `ScheduleAvailabilityCode` | advisory → drop on import |

🔀 **Choice M2.a — a day pinned to a `ScheduleCode`:**

| | Option A — `EQUALS:HH:MM-HH:MM` cell | Option B — forced catalog id |
|---|---|---|
| where | declarative `schedule_input.csv` | expanded `forced` |
| means | re-synthesized to the same block | references the ingested `ScheduleCode` directly |
| depends on | — | the Hard-tier "ingest the catalog" decision |

Same underlying pin; A stays in the declarative CSV, B is exact but only works once the Hard tier fixes
the catalog.

## M3 — Day-off / rest taxonomy

| Sisqual | v3.0 |
|---|---|
| `DayType`: 0 work · 1 *Folga Complementar* (Sat) · 2 *Folga Obrigatória* (Sun) · 3 *Folga* | `dayOffCodes.kind`: `preferable` \| `unavailable` |
| `AbsenceCodeCountAsDayOff` (counts toward limits, e.g. vacation) | — no home; it shifts `n_wk` |

🔀 **Choice M3.a:**

- **Option A *(recommended now)*** — keep our soft/hard `kind`; a translation table maps each Sisqual rest
  type onto `{preferable|unavailable}` and carries the original code for round-trip.
- **Option B** — adopt complementary-vs-obligatory rest as first-class. But *which* rest is legally
  obligatory is a **labour-law** fact, so it belongs with **S3**, not the day-off code list.

`AbsenceCodeCountAsDayOff` → a small flag headed for the labour-law / registry work (it changes the
per-week working-day count `n_wk`). Noted, not resolved here.

## M4 — Team vs ability *(resolves E5 — the org-model choice, the heaviest here)*

Sisqual keeps two things v3 collapses into one: `TeamCode` (an org grouping) and `AbilityID` (a
skill/competency). v3's `team` *is* the skill dimension `S`.

🔀 **Choice M4.a:**

| | Option A — keep v3's conflation | Option B — separate org from skill |
|---|---|---|
| model | `team` = skill; map Sisqual `Ability` → team; `TeamCode` folds into the **S1** roster/org grouping | org hierarchy (roster ⊃ team) for grouping **+** a distinct **skill/competency** dimension; demand keys on skill |
| for | simplest; V7 already keys demand on skill | matches Sisqual (service levels key on Task ≈ skill) and S1; supports "one person, many skills, one team" |
| against | loses the team-as-org vs skill-as-competency distinction | a real org-model change — demand keying moves team → skill |
| lands on | — | **FUTURE §4** (org model) |

*Sisqual leans B.* This interacts with **S1** (org levels) and **M1** (what demand is keyed on) — decide
the three together.

## M5 — Weekly minutes: target vs cap *(resolves E6b)*

✅ **Decision — carry both.** Add `weeklyContractedMinutes` (Sisqual `TotalWeeklyMinutes`, a **target** the
generator aims to hit) alongside `maxMinutesPerWeek` (the **cap**). The field is added now for lossless
round-trip; whether a solver *treats* it as a target is a **FUTURE §2** directive (enforcement deferred).

## M6 — Result bridge (the solution side)

✅ **Decision — `OutScheduleUseds[]` → expanded `assignmentCatalog[]`.** `ScheduleCode` → `id`; the
`StartDate1/2`–`EndDate1/2` pairs → `intervals` (two pairs = a **split shift** = two intervals);
`ScheduleWeight` (paid minutes) = total interval length (v3 has no break, so paid = clock). Near-direct.

✅ **Decision — `OutRosterTeamDays.ScheduleCode` → `solution.assignments[].days[].assignmentId`.** This
becomes an **identity** map once we ingest each `ScheduleCode` as the catalog id — **the crux resolves in
the Hard tier**.

---

## Open choices for the meeting

| choice | question | lean |
|---|---|---|
| **M1.a** | demand value columns — 3, or carry `estimated`? | carry `estimated` (lossless) |
| **M2.a** | a fixed shift — `EQUALS:` cell or forced catalog id? | depends on Hard-tier catalog |
| **M3.a** | rest taxonomy — soft/hard + translation, or complementary/obligatory as first-class? | translation now, richer via S3 |
| **M4.a** | team vs ability — conflate, or separate org from skill? | org-model call; Sisqual leans separate |
