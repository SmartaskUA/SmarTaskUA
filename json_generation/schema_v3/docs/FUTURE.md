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

## 3. Per-employee rules

Some rules target specific people (e.g. holiday entitlement, below), not everyone. That needs a rule
**`scope`** naming employees — which waits on the registry in §2, since v3.0 has no rules at all.

## 4. Org model

Teams vs competencies vs responsibilities (notes L23-24; the note marks itself *"perguntar e
verificar"*). v3.0 keeps v2.6's team+level model. V7 makes a change cheap: it dropped V5's per-level
demand `beta_dtsl`, so demand stays skill-keyed exactly as before — revisit only if the org model
genuinely needs more than team+level.

**Configurable org units (from the Sisqual merge).** Sisqual implies a level *above* team — the
roster/*quadro* (see `SISQUAL-MERGE-PROPOSAL.md` S1). Rather than hardcode a fixed depth, let the client
**define their own org hierarchy** — `store > roster > team`, or just `store > team` — and have the schema
adapt to however many levels they declare, each with date-ranged employee membership (the
`teamAssignments` pattern generalised). This is the general form of the open S1 question (how many levels
are real) and the concrete answer to "when the org model needs more than team+level".

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
