# Future work

_v3.0 is the spec + tooling; no consumer speaks it yet. It defines the **problem** — the "how to
solve it" was cut because none of it reached a solver. This is what to build next, break logic first._

## 1. Break logic

v3.0 has no breaks. v2.6 hung them on work periods (demand buckets), where they were inert: a
worker's assignment is a free-floating block that almost never coincides with a bucket, so a break
rarely attached, and the paid minutes it fed (`weightMinutes`) were read by nothing.

**When re-added, a break is a property of the shift a worker works — a contract attribute**
(`shift ≥ X min → Y-min break`), not of a demand bucket. It needs three things v3.0 lacks:

- a defined **coverage effect** — does an unpaid break punch a hole and split the shift, or is the
  worker still counted as covering during it?
- a **consumer** for paid-vs-clock minutes — contract limits currently check `workMinutesPerDay`,
  not paid time, so nothing today would read a break-adjusted figure;
- a corresponding **term in the mathematical model** — V7 has no break concept.

Absent all three it would be stored-but-ignored — the dead-data trap the whole cleanup removed.

## 2. Solve-directives registry

v3.0 carries no algorithm selection, objectives, demand interpretation, or rules — its first draft
did, but none reached a solver (routing is orchestrator-driven; objectives are parsed from the v2.6
`constraints.soft[]` shape v3 replaced; rest is hardcoded or read via the v2.6 `min_rest_hours`
name).

**Bring them back as one explicit registry**: each constraint / rule / objective type defined once
with its params schema and semantics, referenced by the problem and consumed by the algorithm —
designed against a real reader instead of ahead of one. This is also where the question v3.0 leaves
open — *how a solver reads each demand bound (hard / soft / ignore)* — finally gets a home, instead
of the demand numbers being plain data.

One global directive the Sisqual merge already needs (`sisqual/SISQUAL-MERGE-MEDIUM.md` M2.a): **pins bypass
`T_d`** — a locked/`forced` (or `EQUALS`) assignment is honoured even outside the demanded window,
relaxing the hard `H_wd ⊆ T_d` invariant the transform and validator enforce today. The domain-specific
work that *rides* this registry has its own sections below: **warm-start** (§7) and **labour law**
(§8) — the registry is the mechanism; those are the rules that flow through it.

## 3. Per-employee rules

Some rules target specific people (e.g. holiday entitlement, below), not everyone. That needs a rule
**`scope`** naming employees — which waits on the registry in §2, since v3.0 has no rules at all.

## 4. Org model

Teams vs competencies vs responsibilities (notes L23-24; the note marks itself *"perguntar e
verificar"*). v3.0 keeps v2.6's team+level model. V7 makes a change cheap: it dropped V5's per-level
demand `beta_dtsl`, so demand stays skill-keyed exactly as before — revisit only if the org model
genuinely needs more than team+level.

**Configurable org units (from the Sisqual merge).** Sisqual implies a level *above* team — the
roster/*quadro* (see `sisqual/SISQUAL-MERGE-PROPOSAL.md` S1). Rather than hardcode a fixed depth, let the client
**define their own org hierarchy** — `store > roster > team`, or just `store > team` — and have the schema
adapt to however many levels they declare, each with date-ranged employee membership (the
`teamAssignments` pattern generalised). This is the general form of the open S1 question (how many levels
are real) and the concrete answer to "when the org model needs more than team+level".

**Finer assignment axes (from the Sisqual merge).** Sisqual assigns, within a shift, both
**responsibilities** (`InResponsabilityCollection` — cost-centre / group / pool) and **tasks**
(`OutRosterTeamDayTasks` + `InpTaskAbilityCollection` — a `TaskID` over a sub-interval, mapped to an
ability). v3 has only the day-level assignment plus a coarse per-slot skill (`y_wdts`). Both are
sub-assignment layers this section would grow to cover (see `sisqual/SISQUAL-MERGE-SET-ASIDE.md`); revisit if a
consumer needs intra-shift task/responsibility allocation.

## 5. Holiday entitlement

`calendar.holidays` lets a holiday carry its own demand; it does **not** decide who works — shops
open on holidays. Whether a given worker may take one off is the workplace-vs-residence rule, which
is per-employee (a §3 rule). Until then a holiday reaches `U_wk` only through that worker's
schedule_input cell, like any other day.

## 6. Migrate a consumer onto v3

Nothing speaks v3 yet — `sisqual_hours_utils.py`, the four Sisqual solvers, `ProblemService.java`,
`RabbitMQClient.py` and the json-generator wizard still speak v2.2/v2.6, and every bundle in
`data/problems/` is still `schemaVersion: "2.2"`. The schema is only worth having once something is
migrated onto it, so this is the item that unblocks the rest. Reconciling the Sisqual import/export
format (notes L26) and the workflow/PM platform (L38) live here too.

## 7. Warm-start & re-runs

Re-optimising from an existing schedule — a Sisqual `InpRosterTeamDays` roster, or a prior v3 solution.
Two pieces, both deferred until a warm-start consumer exists so neither is stored-but-ignored:

- **Seed lock** — an optional per-day `locked` flag on the solution/seed (hard = the expanded problem's
  `forced`; absent = a soft, re-optimizable seed), so a whole roster round-trips as one seed
  (`sisqual/SISQUAL-MERGE-MEDIUM.md` M2.a). The solver honours locked days as fixed, via the pins-bypass-`T_d`
  directive (§2).
- **Package validator** — the **solution↔problem cross-check is done**: `validator.py` now validates a
  solution against its expanded problem (`validate_solution` / `--against`) — `problemId` matches, every
  `assignmentId` resolves in that worker-day's `availability`, `skillPerSlot`/`workedPreferableDayOff`/
  `shortfalls` are consistent (see `../FORMAT.md` "Solution form"). What remains for warm-start is
  **lock-agreement** — once the `locked` seed flag exists, a `forced`/`locked` day must name the same
  assignment on both sides (never one locking assignment A while the other avoids it or locks B) — and
  bundling the whole package (expanded + demand.csv + seed) as one check.

## 8. Labour law

v3.0 has no labour-law layer; the merge adds one (`sisqual/SISQUAL-MERGE-EASY.md` S3): named rule-sets — min
rest between shifts (`DistanceBetweenShiftsInMinutes`, the rest cut in v3.0), max consecutive days, max
weekly minutes, week start — assigned to employees date-ranged, with contracts refining **within**
those bounds, never beyond. The level is decided; its schema shape and enforcement (the
tighten-never-loosen check and the rules below, run by the validator and the §2 registry) are the
build. Labour-law assignment is per-employee, so it also draws on §3.

- **Rest-type accounting** (`sisqual/SISQUAL-MERGE-MEDIUM.md` M3) — whether v3's soft/hard day-off `kind` is
  enough, or the rest *type* must be carried (Sisqual's *Folga Complementar* vs *Folga Obrigatória*),
  hinges on whether labour law must **count each type over a window** — e.g. "≥1 obligatory rest per
  week, ≥N complementary per period". If it does, the type becomes a labour-law-linked value and the
  per-type counts — with `AbsenceCodeCountAsDayOff` (whether an absence counts toward the rest quota) —
  are rules the registry enforces over the window. ⚑ Confirm with Sisqual whether their logic counts by
  type before building it.

## 9. Richer contracts & demand

Sisqual carries contract and demand richness v3.0 does not (see `sisqual/SISQUAL-MERGE-SET-ASIDE.md`). Each is a
small extension, deferred until a consumer reads it so none becomes stored-but-ignored:

- **Per-weekday & holiday contract weights** — `WeightMonday…Sunday`, `WeightHolidayBusinessDay/Saturday/Sunday`:
  a different shift length per weekday / per holiday type, where v3 has one `workMinutesPerDay`.
- **Monthly / yearly caps** — `TotalMonthlyMinutes`, `TotalYearMinutes`, beyond v3's daily/weekly limits.
  The cheapest to add — plain optional contract fields — but held back for the same reason as M5's
  weekly target: no solver reads them yet.
- **Workload demand mode** — `InpServiceLevelByDays` states demand as **minutes of workload**, not a
  headcount (`alpha_dts`); a second demand unit alongside the headcount `demand.csv` (merge M1).
