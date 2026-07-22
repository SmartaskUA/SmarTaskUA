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

✅ **Decision M2.a — a pinned `ScheduleCode` becomes an `EQUALS` cell (Option A).** The
`EQUALS:a-b[,c-d…]` cell now authors **split shifts** (implemented — a Sisqual `ScheduleCode` with two
`StartDate/EndDate` pairs becomes `EQUALS:07:30-14:00,18:15-21:15`, compiling to one two-interval
assignment). This removes the single-interval blocker that made this a fork.

Option A and the old "Option B — forced catalog id" are **not rivals**: an `EQUALS` cell compiles to a
one-element `assignmentIds` (self-forcing), and `forced` is the same pin *materialised* in the expanded
form (or how an externally-supplied pin enters directly). So A is the authoring form; the Hard-tier
"ingest the catalog" path is now **optional**, not required for split shifts. Which layer a Sisqual pin
uses is settled in [Hard H3](SISQUAL-MERGE-HARD.md): ingest lands it as `forced` (expanded), while
`EQUALS` is the declarative form of the same pin.

**Routing — `Locked`, and the whole roster merges into ONE warm-start seed.** A Sisqual
`InpRosterTeamDays` roster carries a per-day `Locked`. Rather than split it across two v3 artifacts
(problem `forced` + a separate seed), carry the whole roster as **one warm-start seed** (the solution
schema) where each day is tagged:
- `Locked = true` → **hard** (same solver meaning as the expanded problem's `forced`).
- `Locked = false` → **soft** seed — a re-optimizable starting point.

This maps 1:1 to Sisqual's per-day flag and is exactly the re-run use case. v3 already has a hard-pin
mechanism (`forced` in the expanded problem); "lock" is the same solver concept, differing only in
provenance (problem-authored vs seed-carried), and the seed is its natural home for this round-trip.

✅ **Decision (deferred build) — the solution/seed gains an optional per-day `locked` flag** (hard =
`forced`; absent = soft seed). Decided now, **added when the warm-start solver is built** — deferred so
it is not stored-but-ignored, the same discipline as S3's labour law.

**T_d independence is a solver directive, not a schema gap.** A Sisqual locked shift is authoritative
regardless of demand, but today v3 enforces `H_wd ⊆ T_d` as a hard invariant (the transform drops, and
the validator rejects, any assignment outside the demanded window — `EQUALS` or `forced` alike). The
schema already *carries* the pin; whether the algorithm **honours a pin outside demand** is a
solve-directive — *"pinned/forced assignments bypass the `T_d` filter"* — belonging to the **FUTURE §2**
registry, where a pin-aware pipeline would relax that invariant. Not a schema change now. *(Minor:
Sisqual's `ScheduleWeight` = sum of interval lengths; their intervals are disjoint, so coalescing is a
no-op and the sum matches.)*

## M3 — Day-off / rest taxonomy

| Sisqual | v3.0 |
|---|---|
| `DayType`: 0 work · 1 *Folga Complementar* (Sat) · 2 *Folga Obrigatória* (Sun) · 3 *Folga* | `dayOffCodes.kind`: `preferable` \| `unavailable` |
| `AbsenceCodeCountAsDayOff` (counts toward limits, e.g. vacation) | — no home; it shifts `n_wk` |

v3 classifies a day off on one axis — **soft vs hard** (`preferable` may be worked at a penalty,
`unavailable` cannot). Sisqual classifies on another — the **legal type of rest** (complementary vs
obligatory). Both Folga types are just `unavailable` to us, so collapsing them loses the type.

**The real question: is `unavailable`/`preferable` enough, or must we carry the Folga types?** It
reduces to **one gate — does the labour-law layer need to _count Folga types over a time frame_?**

- **If not** — labour law only needs "off that day" → **soft/hard is enough**. Translate each `DayType`
  → `{preferable|unavailable}`, optionally carry the original code for export round-trip; the model
  never acts on the type.
- **If yes** — rules like *"≥1 obligatória per week, ≥N complementar per period"* count by **type**, so
  soft/hard cannot express them. The Folga type must be a **first-class value linked to the S3
  labour-law layer**, and the per-type counting is a labour-law rule (**FUTURE §2** registry).

⚑ **Confirm with Sisqual:** does the labour-law / generation logic **distinguish and count** Folga
types (obligatória vs complementar) — and `AbsenceCodeCountAsDayOff` — over a window? Their answer
decides it. So M3 is **not independently decidable: it is downstream of labour law (S3).**
`AbsenceCodeCountAsDayOff` rides the same gate — whether an absence *counts* toward the rest quota.

## M4 — Team vs ability *(resolves E5 — the org-model choice, the heaviest here)*

**How each side is built:**
- **Sisqual** — an employee sits on **one `TeamCode`** per roster (an org/section grouping) and holds
  **many `Ability`** (skills, leveled, date-ranged). Demand is stated per **`Task`**, and
  `InpTaskAbilityCollection` maps `Task → Ability`, so **coverage is keyed on skill, not team.**
- **v3** — an employee holds **many `teamAssignments`**, and **`team` *is* the skill dimension `S`**;
  demand keys on team. There is no separate org grouping.

**The alignment is not team↔team.** v3's `team` ≈ Sisqual's `Ability` (both: many-per-person, leveled,
demand-keyed); Sisqual's `TeamCode` ≈ the **S1** org/roster level v3 doesn't separately model. v3
conflates the two only because in a simple store your section *is* your skill.

**The most abstract model — three concepts, not two:**
1. **Skill / competency** — the coverage axis (leveled, many per employee, demand keyed on it) = v3
   `team` and Sisqual `Ability` unified.
2. **Org hierarchy** — configurable depth (`store > roster > team`), pure structural grouping the
   coverage maths ignores = Sisqual `TeamCode` + the S1 roster (FUTURE §4).
3. **Demand** — keyed on **skill**, optionally filtered by org unit.

This **subsumes both** as special cases (v3's team=skill is the degenerate case; Sisqual's
one-team-many-skills is the general one) and is cheap on the maths: V7 already keys demand on `S`, so it
is a **rename** (`team`→`skill`) plus an **added** org dimension the solver need not reason about.

🔀 **Choice M4.a:**

| | Option A — keep v3's conflation (interim) | Option B — the three-concept model (target) |
|---|---|---|
| model | `team` = skill; map Sisqual `Ability` → team; `TeamCode` folds into the **S1** roster grouping | distinct **skill** dimension + **configurable org hierarchy**; demand keys on skill |
| for | simplest; ships now; **loses no coverage** (coverage is skill-keyed either way) | matches Sisqual natively; separates "what you can do" from "where you sit"; future-proof |
| against | the org dimension stays unnamed | a real org-model change — bundles with S1 + M1 + FUTURE §4 |

**Recommendation: adopt B as the target; A is the safe interim** (no coverage semantics lost, the org
dimension just isn't named yet). Decide B together with **S1** (org levels) and **M1** (demand keying).

⚑ **Confirm with Sisqual** (this is what decides it): (1) is `TeamCode` **purely** org grouping, or does
it carry coverage meaning? (2) is demand **ever** keyed on team, or always on `Task`/`Ability`? Their
docs point to "always skill" — if confirmed, the three-concept split is unambiguously right.

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
