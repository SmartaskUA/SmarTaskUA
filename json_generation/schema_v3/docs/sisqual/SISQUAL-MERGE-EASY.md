# Merge tier — Easy

Part of the [merge proposal index](SISQUAL-MERGE-PROPOSAL.md). The reading legend and the **foundational
decisions** (v3.0 as base, JSON+CSV hybrid, canonical vocabulary, code preservation) live in
[SISQUAL-MERGE.md](SISQUAL-MERGE.md) — the tables below assume them.

Most of this tier is clean 1:1 renames. But the review surfaced three items that are **structural**, not
renames — and they share one shape, so they belong together up front.

> **Two hierarchies + one time-model.** The merge grows two small hierarchies, both built from the
> **date-ranged-assignment** pattern the schema already uses (`contractAssignments`, `teamAssignments`) —
> so it stays regular, not ad-hoc:
> - **Org:** roster ⊃ team (+level) — via `rosterAssignments` / `teamAssignments`.
> - **Rules:** labour law ⊃ contract — via `labourLawAssignments` / `contractAssignments`; a contract may
>   *tighten* within its labour-law bounds, never loosen them.
> - **Time:** an interval stays anchored to one scheduling day, its interior sliced by the `timeGrid`;
>   how its boundaries are *written* — `HH:MM` or minutes — is left open (S2).
>
> So "are we just tweaking v3?" — yes for the renames below, **and** the merge adds this small skeleton.
> The items behind it are **S1 / S2 / S3**, after the table — two decisions (S1, S3) and one open
> question (S2).

The clean renames:

| # | Concept | Sisqual (`Inp*`) | v3.0 | Merged schema — proposed | Status |
|---|---|---|---|---|---|
| E1 | Problem / roster identity | `RosterCode` | `metadata.problemId` | `metadata.problemId` (run id; may equal the roster code) **+ optional `metadata.rosterCode`** | ✅ / roster as an **org level** → **S1** |
| E2 | Horizon | `InpRosterDetail.StartDate/EndDate` (datetime) | `temporalScope {start,end}` (date) | `temporalScope {start,end}`, calendar dates (horizon is day-granular; see **S2**) | ✅ |
| E3 | Employee identity | `EmployeeCode` | `employees.list[].id` | `employees.list[].id` = the code; `name` optional | ✅ |
| E4 | Contract periods | `InpEmployeeContracts[]` | `contractAssignments[]` | `contractAssignments[] {contractType, start, end\|null}`; Sisqual far-future `EndDate` → `null` | ✅ |
| E5 | Skill + level | `InpEmployeeAbilities[] {AbilityID, Level}` | `teamAssignments[] {team, level}` | keep the `teamAssignments[]` container and `{…, start, end}` shape | ✅ container / → **M4** for team-vs-ability |
| E6a | Daily minutes | `TotalDailyMinutes` | `workMinutesPerDay` | `workMinutesPerDay` (minutes) | ✅ |
| E6b | Weekly limit | `TotalWeeklyMinutes` | `constraints.maxMinutesPerWeek` | `constraints.maxMinutesPerWeek` | ✅ as a cap / → **M5** for weekly *target* |
| E6c | Max consecutive days | `MaxConsecutiveWorkDaysInWeek` (LabourLaw) | `constraints.maxConsecutiveDays` | `constraints.maxConsecutiveDays` on the contract | ✅ / per-employee override → Set aside |
| E6d | Week start | `DayOfWeek` (LabourLaw, 0=Sun) | `calendar.weekStart` | `calendar.weekStart` (weekday name); convert the index | ✅ |
| E7 | Time unit & grid | ISO datetimes | minutes + `timeGrid.slotMinutes` | `timeGrid`-sliced interior, day-anchored (settled); boundary representation `HH:MM` vs minutes → **S2** | ❓ open |
| E8 | Holidays | `IsHolliday` per row | `calendar.holidays[]` | `calendar.holidays[]`; import folds the flags in, export stamps `IsHolliday` back onto dated rows | ✅ |

## Structural decisions (raised in review)

Three rows above are structural, not renames. Each reuses the date-ranged-assignment pattern.

### S1 — an org level above team ("roster")

✅ **Decision — add `roster` as an org level above `team`, with date-ranged membership.**

- `demand.organizationalUnits` gains `rosters[]`; every team belongs to a roster.
- Employees gain `rosterAssignments[] {roster, start, end|null}` — the **same shape** as `teamAssignments`,
  so an employee can **change roster** over time (a transfer) inside one problem, exactly as v3 already
  lets team membership change.
- `metadata.problemId` stays the run identity (it may equal the roster code for a single-roster run);
  `metadata.rosterCode` still carries the vendor code. Roster is therefore both the run's origin *and* a
  first-class org unit.

*Grounded, not invented:* Sisqual's data is already roster-scoped above team — every `OutRosterTeamDays`
row is stamped roster+team+employee, and service-level demand carries `RosterCode`.

🔀 **Choice S1.a — are team codes roster-scoped?** *(confirm with Sisqual)*

| | Option A — teams are roster-scoped | Option B — teams are globally unique |
|---|---|---|
| e.g. | "Checkout" exists in store 0533 *and* 0777 | one global "Checkout" |
| `demand.csv` | gains a `roster` column: `date,roster,workPeriod,team,…` | unchanged — roster derives from team |
| fits | multi-store transfers, reused team names | single-site, or unique team codes |

> **Semantics to confirm:** whether *quadro*/roster is a **persistent org unit** (a site people transfer
> between) or the **per-period board** being generated. If it is really the board, this level is better
> named `site`/`unit`; keep `roster` for interop and flag it.

*Future generalization:* rather than hardcoding roster ⊃ team, let the client define their own org
hierarchy depth (`store > roster > team`, or just `store > team`) and have the schema adapt — see
`../FUTURE.md` §4. That is the general form of this same S1 question.

### S2 — time boundary representation: `HH:MM` vs minutes (OPEN — to settle with Sisqual)

❓ **Open question — not a decision.** How a time boundary is *written* at the author (JSON/CSV) layer —
clock `HH:MM` or integer minutes — and how midnight roll-over is expressed. An earlier draft recorded this
as "full ISO datetime everywhere" (a since-withdrawn S2.a); that call is **dropped** because it forced an
absolute date onto reusable work-period buckets, which have no single date (see below). Reopened to settle
with Sisqual, whose export format is datetime-native and so is a direct input to the choice.

**Settled regardless of the outcome — this part is not in question:**
- **Day-anchor.** An assignment belongs to ONE scheduling `date`, so week partitioning and `n_wk` hold.
  Overnight is the *next day relative to that one anchor*, never a second anchor. Sisqual anchors the same
  way — an `OutRosterTeamDays` row carries a single `Date` while its datetimes may cross midnight.
- **`timeGrid.slotMinutes`.** The slice size of the interior, orthogonal to how a boundary is written —
  untouched by whatever S2 decides.
- **The model layer.** The expanded/solution forms already state grid-aligned **minutes from the day's
  start** (`startMin`/`endMin`, a value `≥ 1440` = past midnight). Whatever the author layer uses compiles
  down to these. This half is built.

**The decomposition that frames the choice.** Every boundary splits into an absolute part and a relative
part, and they have different needs — a fused date+time (`2030-10-02T06:30`) is never actually required:

| boundary | absolute part | relative (time-of-day) part |
|---|---|---|
| `temporalScope {start,end}` | **date** — day-granular, no hour | — |
| worker-day / assignment anchor | **date** — day-granular, no hour | — |
| **work-period `timeRange`** | **none** — a reusable template applied to every date; **cannot carry a date** | ✅ time-of-day |
| assignment interval (`intervals`) | inherited from the day-anchor | ✅ time-of-day (already minutes) |

So the absolute part is *always day-granular* (a `date`); only the **relative time-of-day part** needs a
representation chosen — and for work periods it must stay **date-free** (they are templates, not instances).

**The two candidates for that relative part:**

| | `HH:MM` string | minutes from day-start |
|---|---|---|
| author ergonomics | ✅ human-native (`22:00`) | ✗ mental math (`1320`) |
| arithmetic / grid-align | ✗ parse → convert first | ✅ plain `int`, `v % slotMinutes` |
| **overnight** | ✗ **inferred** from `end ≤ start` (field capped at 23:59) — the v2.6 trap, every reader re-implements | ✅ **stated** via `≥ 1440` |
| reusable across dates | ✅ date-free | ✅ date-free |

Today the author layer already mixes the two: `HH:MM` in work periods and cell windows, minutes in the
model. The question is whether to **unify on minutes** (killing the `end ≤ start` inference at the author
layer too) or **keep `HH:MM`** for ergonomics and remove only the *inference* — e.g. an explicit next-day
marker (`{time: "06:30", dayOffset: 1}`) instead of guessing from `end ≤ start`.

**Sub-question — the overnight marker**, independent of `HH:MM`-vs-minutes: infer from `end ≤ start`
(status quo) · an explicit `dayOffset` flag · minutes `≥ 1440`. The latter two remove the one inference;
the first keeps it.

⚑ **To resolve with Sisqual**, then build. Until then files are unchanged: `workPeriods[].timeRange` keeps
the `hhmm` def and a work period with `end <= start` still *infers* midnight-crossing — the one inference
this question exists to remove. Whichever way it lands, the build touches the declarative schema
(`$defs/hhmm`), the parser (`core.parse_range`), the templates and both examples.

### S3 — labour law as a ground-rules level above contracts

✅ **Decision — add a `labourLaw` level; contracts refine *within* it, never beyond it.** *(Promoted out of
Set aside.)*

- New top-level `labourLaw[]` (a.k.a. `legislation[]`): named baseline rule-sets — **min rest between
  shifts** (`DistanceBetweenShiftsInMinutes`, the one we cut), max consecutive days, max weekly minutes,
  week start.
- Employees reference one via date-ranged `labourLawAssignments[] {code, start, end|null}` — the pattern
  again; = Sisqual's `InpEmployeeLLabourLawLegislationCollection`.
- A contract's `constraints` may only **tighten** within the assigned labour-law bounds.

*Grounded:* Sisqual already separates `InpLabourLawCollection` (legal, per-employee, date-ranged) from
`InpContractCollection` (employment terms).

⚠️ **Scope — decided in principle, built later.** The *decision* (a labour-law level; contracts tighten
within it) stands. Its concrete **schema shape and enforcement are both future work**: a worked schema
example comes later, and the labour-law rules (tighten-never-loosen, min-rest) are enforced by the
**validator** — tracked under **FUTURE §2** (solve-directives registry). So the level is agreed now but
materialised later, not carried as half-built structure in the meantime.

## Note on E8 — holidays

v3's `hasEve` (an eve day that carries its own demand) has no Sisqual counterpart; it stays as a v3
addition. On export to Sisqual it simply resolves to an ordinary dated row, so nothing breaks.

## What this tier deliberately pushes down a level

Two things look easy (identical containers) but hide a real decision, so they go to the Medium tier:

- **E5 — team vs ability** → resolved at **[M4](SISQUAL-MERGE-MEDIUM.md)**. Sisqual keeps `TeamCode` (org
  unit) and `AbilityID` (skill GUID) **separate**; v3 collapses them into one `team` that *is* the skill
  dimension `S`. Merging the container is easy; whether to keep them separate is the org-model question —
  and it now sits *under* the roster level from **S1** (roster ⊃ team ⊃ ability?).
- **E6b — weekly minutes as target vs cap** → resolved at **[M5](SISQUAL-MERGE-MEDIUM.md)**. Sisqual's
  `TotalWeeklyMinutes` is *contracted* minutes (a target the generator aims to hit); v3's
  `maxMinutesPerWeek` is only a ceiling.
