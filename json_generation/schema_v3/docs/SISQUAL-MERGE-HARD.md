# Merge tier — Hard

Part of the [merge proposal index](SISQUAL-MERGE-PROPOSAL.md). The reading legend and the **foundational
decisions** are in [SISQUAL-MERGE.md](SISQUAL-MERGE.md).

> **Status: to build into decisions next.** The analysis is settled (see
> [SISQUAL-MERGE.md](SISQUAL-MERGE.md) → "Tier 3 — Hard"); this file will turn it into H-decisions with
> their choices, the way Easy and Medium are done.

## The one that actually clashes — shift catalog vs synthesized assignments

Sisqual picks a pre-built `ScheduleCode` from a menu (`InpScheduleUsedCollection`,
`InpRosterSchedulesCollection`). v3 has **no authored shift menu**: `transform.py` synthesizes every
contiguous block of the contract's length across the demand window, and `assignmentCatalog` is the
*output* of that, deduplicated.

Likely resolution (from the analysis): **ingest, don't synthesize** — treat each `ScheduleCode` as one
`assignmentCatalog` entry (its `StartDate1/2` become the `intervals`) and skip block-synthesis. v3's
expanded schema already permits an arbitrary, externally-fixed catalog, and its
`availability.days[].forced` is the exact shape of Sisqual's `Locked`. So Sisqual's shift world docks at
the **expanded** layer, leaving the **declarative** authoring layer untouched.

## The schema-form question this forces

Does the merged schema keep v3's **declarative + expanded** split, with Sisqual's catalog entering at the
expanded layer? This is the decision that resolves the two dependencies left open in Medium:

- **M2.a** — a fixed `ScheduleCode` on a day as an `EQUALS:` cell (declarative) vs a forced catalog id (expanded).
- **M6** — `ScheduleCode` → `assignmentId` becomes an identity map once the catalog is ingested.
