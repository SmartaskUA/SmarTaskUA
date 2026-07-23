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
> - **Time:** an interval stays anchored to one scheduling day, its boundaries defined by datetime, its
>   interior sliced by the `timeGrid`.
>
> So "are we just tweaking v3?" — yes for the renames below, **and** the merge adds this small skeleton.
> The three decisions behind it are **S1 / S2 / S3**, after the table.

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
| E7 | Time unit & grid | ISO datetimes | minutes + `timeGrid.slotMinutes` | **datetime-defined boundaries + `timeGrid`-sliced interior, day-anchored** → **S2** | ✅ (revised) |
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

### S2 — time: datetime-defined boundaries, grid-sliced interior, day-anchored

✅ **Decision — define interval boundaries as datetimes; keep the `timeGrid` and the scheduling-day anchor.**
This *merges* both logics rather than picking one:

| layer | representation | why |
|---|---|---|
| JSON boundaries (`temporalScope`, work-period ranges, assignment intervals) | ISO **datetime** (or `date`+time) | explicit dates kill all midnight-rollover ambiguity — Sisqual-native |
| CSV cells | `HH:MM` (date = the column header) | no bloat, still unambiguous |
| model | grid-aligned **minutes from the scheduling day's start**, derived | the ILP's `T` timeslots are unchanged |

- **Day-anchor kept:** an assignment still belongs to ONE `date`, so week partitioning and `n_wk` hold.
  Overnight becomes a next-day datetime (≡ v3's minutes > 1440). Sisqual anchors the same way — its
  `OutRosterTeamDays` row carries a single `Date` while the schedule's datetimes may cross midnight.
- **`timeGrid.slotMinutes` is untouched** — it is the slice size, orthogonal to how a boundary is written.

*(This revises the earlier "keep minutes, reject datetime" call: datetimes are actually **more** aligned
with why v3 dropped bare `HH:MM` — they remove the rollover guess entirely.)*

✅ **Decision S2.a — full ISO datetime at the JSON layer.** Verbose, but the least ambiguous and
Sisqual-native — the extra characters buy an explicit date on every boundary. *(The `date` + `HH:MM` pair
was the lighter alternative; rejected for the clarity.)*

⚠️ **Scope — decided in principle, built later.** The *decision* stands. Today's files are unchanged:
`workPeriods[].timeRange` still uses the `hhmm` def and a work period with `end <= start` still *infers*
midnight-crossing — the one inference S2 exists to remove. Building it touches the declarative schema
(`$defs/hhmm` → a datetime boundary), the parser (`core.parse_range`), the templates and both examples,
so it waits for ratification rather than pre-empting it. The minutes half of S2 — grid-sliced interior,
day-anchored, `startMin`/`endMin` in the expanded and solution forms — **is** already in place.

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
