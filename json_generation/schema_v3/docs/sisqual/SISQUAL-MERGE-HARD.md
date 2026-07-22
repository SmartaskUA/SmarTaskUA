# Merge tier — Hard

Part of the [merge proposal index](SISQUAL-MERGE-PROPOSAL.md). The reading legend and the **foundational
decisions** are in [SISQUAL-MERGE.md](SISQUAL-MERGE.md) — the decisions below assume them.

There is exactly **one** genuinely hard merge: how a worker-day's option set (`H_wd`) is built. Every
other Sisqual-only feature has no v3 home and is [Set aside](SISQUAL-MERGE-SET-ASIDE.md), so this clash
is the whole tier.

## H0 — the clash: synthesis vs menu

Two opposite philosophies for populating the same thing — the set of assignments a worker may take on a
day (`H_wd`):

| | v3 — **synthesis** | Sisqual — **menu** |
|---|---|---|
| where options come from | *generated*: every contiguous contract-length block in the operating window, filtered by the cell and `T_d` | *curated*: pick one of a small pre-built `ScheduleCode` list (`InpScheduleUsedCollection`, `InpRosterSchedulesCollection`) |
| size of `H_wd` | large (dozens of positions) | small (a handful of approved shifts) |
| authored? | no shift menu exists — `assignmentCatalog` is the *output* of synthesis | the menu **is** the input |

v3 moved *off* a shift menu on purpose — MIGRATION removed v2.6's `workPeriodModel` /
`allowedStartTimes` and made work periods demand buckets. So this is a real philosophy gap, not a
detail. The merge has to let both populate `H_wd`.

## The insight that decides the tier

**A genuine multi-option menu has no v3 declarative form.** The declarative cell grammar only expresses
`A`, a number, `EQUALS`, `INCLUDE`, `EXCEPT` — never *"one of these N shifts."* So "this worker may take
`ScheduleCode` 1534, 1666, or 1508 today" cannot be authored declaratively. Only the **degenerate
single-option** case (a pin) has a declarative form — `EQUALS`. A real menu is therefore *inherently* an
**expanded-form** object. That is what forces H2 and makes expanded-layer ingest the natural default.

Put differently — **the expanded form *is* a menu.** Per worker-day it is literally the list of
assignments allowed (`assignmentIds`). So Sisqual's menu ≈ the expanded form (a problem "already
authored"), and v3's synthesis ≈ what the declarative form *compiles into* that menu. The two
philosophies therefore line up with the two forms along one axis: **a v3 problem lives in both forms
(interchangeable via transform); a Sisqual menu lives only in the expanded one.** H0 is *how the menu is
sourced*; H2 is *whether that menu also gets a declarative representation, or stays expanded-only*.

## H1 — the seam: the expanded form ✅

Both philosophies converge on the expanded shape already in v3: an `assignmentCatalog` (each entry
`{id, intervals}`) plus, per worker-day, an `assignmentIds` list drawn from it. The expanded form is
**mode-agnostic** — it does not record *how* the catalog was built, only what the options are. So:

- Keep v3's two-form **declarative + expanded** split (foundational).
- **Sisqual's menu docks at the expanded layer.** Its `Locked` is exactly `availability.days[].forced`,
  and its split shifts are exactly multi-interval catalog entries (both already supported and validated).

## H2 — how the menu ENTERS ✅ — expanded-only ingest

This is **not** about whether the declarative form exists — it does, universally, for every v3-native
(synthesized) problem. It is only about **Sisqual-imported menu problems**, which have no declarative
form because a multi-option menu ("take shift X *or* Y *or* Z") cannot be written in the cell grammar.

✅ **Decision — Option A: a Sisqual menu enters directly as an expanded problem** (`form: "expanded"`,
demand.csv, optional solution) — no declarative twin. The menu docks at `assignmentCatalog`, which
**already is** v3's shift catalog, on the assignment side. Declarative and schedule_input are untouched.

**Why not Option B (add a `shiftCatalog` block + a per-day "pick one of these codes" cell to the
declarative form).** It looks like it would complete the "every problem has both forms" invariant, but
it mixes three things that should stay separate:

1. **A second time-range vocabulary.** `shiftCatalog` (assignable shifts) would sit beside `workPeriods`
   (demand buckets) in the declarative layer — blurring the one line v3 holds hardest, *"work periods
   are demand buckets, not shifts."* The shift catalog already exists as the expanded
   `assignmentCatalog`; B duplicates it into the wrong layer.
2. **A bloated schedule_input.** A `MENU:code|code|code` cell widens a matrix that is deliberately tight.
3. **A schedule_input doing two jobs.** Its one purpose is the **availability** matrix (available? how
   long? which window? off?). `MENU:` adds **shift-selection** — an assignment concern — overloading it.

B only earns those costs if the v3 wizard must become the tool that *authors/edits* menu problems.

> ### ⚠️ The trade-off A accepts — flag for the meeting
> **A Sisqual-imported menu problem is expanded-only: it has no declarative form.** So v3's "every
> problem exists in both forms, both cohesive" invariant holds for everything the **wizard authors**,
> but **not** for menus imported from Sisqual — those can only be viewed/edited in expanded form (or in
> Sisqual itself). This is acceptable because (a) a menu is already compact and readable in expanded
> form, so the declarative form would compress nothing, and (b) Sisqual remains its own authoring tool.
> **But it is a real limitation to name, not hide:** if the team later wants menu problems editable in
> the v3 wizard, that is exactly when Option B (and its three costs) comes back on the table.

⚑ **Confirm with Sisqual / the team (this is what could reopen B):** does v3 need to **author/edit**
Sisqual-style menu problems, or only **ingest / solve / round-trip** them? A covers the second; only the
first needs B.

## H3 — ingest mechanics (Option A) ✅ — resolves M2.a + M6

Mapping a Sisqual roster into an expanded problem:

| Sisqual | → expanded |
|---|---|
| `InpScheduleUsedCollection` / `InpRosterSchedulesCollection` (`ScheduleCode`, `StartDate1/2`–`EndDate1/2`) | `assignmentCatalog[]` — **id carries the `ScheduleCode`** (round-trip); the date pair(s) → `intervals` (split shift = two intervals, already supported) |
| the codes available to a worker on a day | that day's `availability.assignmentIds` |
| a **single** available code | the degenerate pin → `forced` |
| `Locked` | `forced` |
| `ScheduleWeight` (paid min) | = sum of interval lengths — derivable, not stored |
| `DayType` | → **M3** (a rest classification, not an assignment property) |
| `Legend` / `Description` / `ScheduleAvailabilityCode` | advisory → drop on import |

Two prior items close here:
- **M2.a** — the pin is the *same* thing at two layers: `forced` (expanded, what Sisqual ingest uses)
  and `EQUALS` (declarative, what a v3 author writes). H3 uses `forced`; no contradiction.
- **M6** — `OutRosterTeamDays.ScheduleCode → solution.assignmentId` becomes an **identity** map, because
  the catalog id *is* the `ScheduleCode`.

## H4 — the `T_d` interaction ✅ (via the §2 directive)

A **synthesized** `H_wd` is `T_d`-filtered (blocks outside the demanded window are dropped). An
**ingested** menu is authoritative — its shifts are honoured regardless of demand. That is exactly the
**pins-bypass-`T_d`** solver directive already decided in M2.a (FUTURE §2): the two modes differ only on
`T_d`, and the directive is the switch. No schema change — it is a solver policy.

## Interactions with prior decisions

| decision | how Tier 3 touches it |
|---|---|
| **S2** (datetime, day-anchored) | Sisqual `StartDate/EndDate` datetimes → `intervals` (minutes), day-anchored — consistent |
| **M4** (team vs skill) | an assignment carries **no team** — skill choice (`y_wdts`) is separate — so the catalog is skill-agnostic and works for both modes and either org model |
| **M2.a / M6** | pin layering + the identity map, as in H3 |
| **ids** | synthesis mints `A0001…`; ingest reuses the `ScheduleCode`. Opaque strings — no schema change |
| **S1 / S3** (org, labour law) | orthogonal — neither touches how `H_wd` is populated |

## What the schema needs

- **Option A:** likely **nothing new**. The expanded schema already permits an arbitrary multi-interval
  `assignmentCatalog`, `forced`, and per-day `assignmentIds` (all exercised and validated). At most an
  optional `externalCode` for round-trip, or simply use the `ScheduleCode` as the catalog id.
- **Option B:** a new **declarative shift-catalog block** + a catalog-referencing cell — the heavier
  path, and the only one that changes the schema.

## Open choice for the meeting

| choice | question | lean |
|---|---|---|
| **H2** | does the menu enter expanded-only (ingest), or also via a declarative catalog mode? | A (ingest) unless v3 must *author* menu problems — ⚑ confirm the workflow |
