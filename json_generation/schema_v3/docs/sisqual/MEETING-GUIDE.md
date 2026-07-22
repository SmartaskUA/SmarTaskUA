# Sisqual merge — meeting guide

A presentation organizer for the schema-merge discussion: what's decided, what the team should ratify,
what to **ask Sisqual**, and what is deliberately **future work**. Detail lives in the tier files (see
the [index](SISQUAL-MERGE-PROPOSAL.md)); this is the talking-points layer.

---

## 1. Status snapshot

**Already shipped in code (v3 schema + tooling):**

| what | state |
|---|---|
| Multi-window cells `EQUALS` / `INCLUDE` / `EXCEPT` (`a-b,c-d…`) | done — 96/96 conformance tests |
| **Split-shift authoring** (`EQUALS:07:30-14:00,18:15-21:15` → one two-interval assignment) | done |
| Overlap **coalescing** (`08:00-12:00,10:00-14:00` → `08:00-14:00`) | done |
| `mustCover` / `mustAvoid` recorded in expanded form + validator re-checks them | done |
| `forced` pin (expanded) — already present, now test-covered | done |
| **Worked solution example** (`examples/sisqual_example/solution.json`) — the third form now has an instance | done |
| **Solution cross-validator** (`validate_solution` / `--against`) — a solution is checked against its problem | done |

**Merge analysis (all four tiers decided):**

| tier | outcome |
|---|---|
| Easy | decided — renames + 3 structural decisions (S1 roster, S2 datetime, S3 labour law) |
| Medium | decided — M1–M6; three gated on Sisqual answers |
| Hard | decided — **A: expanded-only ingest**; 1 flagged limitation |
| Set aside | decided — defer-map + round-trip decision |

Headline: **no open item forces a schema change now.** Everything left is either a *question for
Sisqual* or *deferred future work*. The two immediately-buildable items — a worked solution example and
a solution cross-validator — are both **shipped** (see the status table above).

---

## 2. Schema-3 ↔ Sisqual, at a glance

**Read the direction first:** Sisqual **Export** (`Inp*`) is data going *into* their generator — it is
**the problem**. Sisqual **Import** (`Out*`) is the generator's result read *back* — it is **the
solution**. The full field-level map is in [SISQUAL-MERGE.md](SISQUAL-MERGE.md); the digest:

| concept | schema v3.0 | Sisqual |
|---|---|---|
| problem / board id | `metadata.problemId` | `RosterCode` |
| horizon | `temporalScope {start, end}` | `InpRosterDetail.StartDate/EndDate` |
| employee | `employees.list[].id` | `EmployeeCode` |
| contract | `contracts` + `contractAssignments` | `InpContractCollection` + `InpEmployeeContracts` |
| **skill** (+ level) | `teamAssignments {team, level}` | `InpEmployeeAbilities {AbilityID, Level}` |
| **org grouping** | roster level *(S1, future)* | `TeamCode` |
| demand | `demand.csv` (date, workPeriod, team, min/emp/max) | `InpServiceLevelBy{Shifts,Periods,Days}` |
| per-day input | `schedule_input.csv` cells | `InpRosterTeamDays` (`ScheduleCode`, `Locked`, `AbsenceCode…`) |
| shift | synthesized `assignmentCatalog` / `EQUALS` cell | `InpScheduleUsedCollection` (`ScheduleCode` + intervals) |
| day-off / rest | `dayOffCodes` (preferable / unavailable) | `DayType` (Folga complementar / obrigatória) |
| labour law | `labourLaw` level *(S3, future)* | `InpLabourLawCollection` |
| **the result** | `solution` (`assignmentId`, `skillPerSlot`, `shortfalls`) | `OutRosterTeamDays` + `OutScheduleUseds` |
| how-to-solve | — *(deferred, FUTURE §2)* | `InpGenerationRules` |

The one alignment to flag out loud: **v3's `team` ≈ Sisqual's `Ability`** (the skill/coverage axis), and
**Sisqual's `TeamCode` ≈ the future roster/org level** (M4 + S1). Per-field detail and the tier
decisions are in the tier files.

---

## 3. Where Sisqual import/export enters — the packages

v3 holds a problem in **packages**: a *declarative package* = `problem.json` + `demand.csv` +
`schedule_input.csv`; an *expanded package* = `problem.expanded.json` + `demand.csv` (+ optional
`solution.json`). Sisqual's two payloads dock onto these at the **adapter boundary** — everything inside
is v3 files the validator already checks (single file, whole package, or a folder).

```
Sisqual EXPORT  (Inp*:  RosterDetail · MasterData · ServiceLevelDetail · GenerationRules)   = the PROBLEM
    │  sisqual_import   (adapter — FUTURE §6)
    ▼
v3 DECLARATIVE package    problem.json + demand.csv + schedule_input.csv
    │  transform.py       (menu-based problems skip this: ingest straight to expanded — H2)
    ▼
v3 EXPANDED package       problem.expanded.json + demand.csv  ──►  solver  ──►  v3 solution.json
    ▲                                                                              │
    │  sisqual_export     (adapter)                                                 │
    └────────────  Sisqual IMPORT  (Out*: OutRosterTeamDays + OutScheduleUseds)  ◄──┘   = the RESULT
```

- **Export `Inp*` (the problem)** → the v3 **problem** side: a declarative package, or straight to an
  **expanded** package for menu-based problems (H2). `InpScheduleUsedCollection` → the `assignmentCatalog`.
- **Import `Out*` (the result)** → the v3 **solution** (`solution.json`) — cross-checked by
  `validate_solution` against the expanded — and the **warm-start seed** on a re-run (M2 / FUTURE §7).
- **`InpGenerationRules`** (how-to-solve) and the **set-aside features** (tasks, responsibilities, …) →
  *not* package files; they ride an adapter **sidecar** only if a lossless round-trip is required.

The boundary is the adapter (`sisqual_import.py` / `sisqual_export.py` — the edge adapter, FUTURE §6).
So a full round-trip is: **Sisqual → adapt → v3 package *(validated)* → solve → v3 solution *(validated)*
→ adapt → Sisqual.** The package/folder validation shipped this session is exactly the "validated" step.

---

## 4. Decisions to ratify (team sign-off)

- **v3.0 is the base schema** — grow it to absorb Sisqual concepts tier by tier; not a forever-adapter,
  not a full superset.
- **Keep the JSON + CSV hybrid** — Sisqual is receptive to CSVs, so the big matrices stay CSV.
- **Preserve Sisqual codes** in dedicated optional fields (`rosterCode`, `ScheduleCode`-as-id).
- **🔀 N1 — canonical vocabulary** *(the one open foundational fork)*: v3 names (`workMinutesPerDay`) vs
  Sisqual names (`TotalDailyMinutes`) vs the middle (v3 names + a published alias table). *Recommend v3
  names + alias table.*
- **Per-tier decisions** (one line each): datetime boundaries + grid (S2/S2.a) · labour-law level, built
  later (S3) · demand tables → `demand.csv`, carry `estimated` (M1) · pinned shift = `EQUALS` cell,
  roster → one warm-start seed (M2) · weekly target + cap both carried (M5) · result bridge = identity
  map (M6) · menus ingest into the expanded catalog (H2).

---

## 5. Questions for Sisqual

Each: **the question → why it matters → what the answer changes.**

- **S1 — Roster / org model.** Is *quadro*/roster a **persistent org unit** (a site people transfer
  between) or the **per-period board** being generated? And are team codes **roster-scoped** (same
  "Checkout" in two stores)? → decides whether roster is a first-class org level and whether `demand.csv`
  needs a `roster` column.
- **M1 — Demand tables.** Do all three service-level tables (`ByShifts`, `ByPeriods`, `ByDays`) actually
  appear in real exports, and is `EstimatedValue` meaningful or vestigial? → decides the `demand.csv`
  column set (whether we carry `estimated`).
- **M3 — Rest types.** Does the labour-law / generation logic **count** Folga types (*Obrigatória* vs
  *Complementar*) and `AbsenceCodeCountAsDayOff` **over a time window**? → decides whether v3's soft/hard
  day-off is enough, or the rest *type* must become a first-class, labour-law-linked value.
- **M4 — Team vs skill.** Is `TeamCode` **purely** org grouping, or does it carry coverage meaning? Is
  demand **ever** keyed on team, or **always** on Task/Ability? → decides whether we keep v3's
  `team = skill`, or split a distinct skill dimension from the org hierarchy (bundles with S1).
- **H2 — Menu authoring.** Must the v3 wizard **author/edit** Sisqual menu problems, or only
  **ingest / solve / round-trip** them? → decides whether menus stay expanded-only (recommended) or need
  a declarative catalog mode. *Note the accepted limitation:* imported menus have no declarative form.
- **Round-trip.** Is a **lossless** Sisqual→v3→Sisqual round-trip required, or is **one-way** (lossy on
  unmodeled features) import acceptable? → decides whether the adapter needs a sidecar for set-aside
  features.

---

## 6. What we do NOT have — future work

Deliberately deferred, **not lost**. The point to make: **most Sisqual-only features map onto a roadmap
v3 already wrote** — the merge *validates* the roadmap rather than adding to it. Full detail in
[`../FUTURE.md`](../FUTURE.md).

| # | future item | Sisqual driver |
|---|---|---|
| §1 | **Break logic** | (v3 cut; a contract attribute when re-added) |
| §2 | **Solve-directives registry** | `InpGenerationRules` (the whole "how to solve" block) |
| §3 | **Per-employee rules** | per-employee legislation / entitlement |
| §4 | **Org model** — configurable units + **tasks & responsibilities** | `TeamCode`/roster; `OutRosterTeamDayTasks`, `InResponsabilityCollection` |
| §5 | **Holiday entitlement** | workplace-vs-residence day-off rule |
| §6 | **Migrate a consumer onto v3** | the whole point — build the adapter |
| §7 | **Warm-start & re-runs** | `InpRosterTeamDays` roster as a seed; `Locked` |
| §8 | **Labour law** | `InpLabourLawCollection`, rest counting, min-rest |
| §9 | **Richer contracts & demand** | per-weekday/holiday weights, monthly/yearly caps, workload demand |

Two things worth calling out in the talk:
- **Tasks & responsibilities** have an *easy* path (carry + validate: a catalog + per-slot/day
  annotation) separate from the *hard* path (v3 optimizes them) — only the latter is deferred.
- **Workload demand** is the demand-half of tasks; it only matters once v3 optimizes task allocation.

---

## 7. Suggested flow

1. **Progress** — what already shipped (§1), so the merge is grounded in working code.
2. **The map & the plumbing** — how schema-3 lines up with Sisqual, and where their import/export enters
   our packages (§2–§3).
3. **The frame** — v3 as base, JSON+CSV hybrid; the merge grows two small hierarchies (org, rules) + a
   datetime time-model.
4. **What merges cleanly** — the Easy tier + the decided Medium/Hard calls (ratify §4).
5. **The real decisions** — the structural ones (roster, skill-vs-team, menu ingest) and the open
   questions for Sisqual (§5).
6. **Future work** — what's deferred and why it's the roadmap, not a gap (§6).
