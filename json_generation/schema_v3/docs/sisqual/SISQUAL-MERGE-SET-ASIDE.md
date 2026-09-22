# Merge tier — Set aside

Part of the [merge proposal index](SISQUAL-MERGE-PROPOSAL.md). The reading legend and the **foundational
decisions** are in [SISQUAL-MERGE.md](SISQUAL-MERGE.md) — the decisions below assume them.

Sisqual capabilities with **no v3 home**. Unlike the other tiers there is no per-feature A/B fork — each
is a ✅ *defer to a `../FUTURE.md` item*. **Most** map onto the roadmap v3 already wrote (so this tier
validates `../FUTURE.md` rather than adding a new backlog); a few genuine extensions are collected under
`../FUTURE.md` §9 so every row points at a real item.

## The one cross-cutting decision — round-trip

✅ **Set-aside features never enter the merged schema.** If a lossless Sisqual→v3→Sisqual round-trip is
needed, that is the **adapter's** job — a sidecar keyed by `problemId` that stashes and restores the
unmodeled blocks — **not opaque blobs in the schema.** Putting unmodeled Sisqual structure *in the
schema* is exactly the mixing/bloat rejected at [H2](SISQUAL-MERGE-HARD.md) and by the v3 cleanup. (This
is consistent with the foundational "preserve Sisqual codes in dedicated optional fields" for the *small
recurring codes* like `rosterCode`; *whole unmodeled blocks* go to the sidecar.)

⚑ **Confirm with Sisqual:** is a **lossless round-trip** of features v3 doesn't model required, or is
**one-way import** (lossy on the set-aside parts) acceptable? That decides whether the adapter needs a
sidecar at all.

## Disposition — every set-aside feature

| Sisqual feature | what it is | on import | → FUTURE |
|---|---|---|---|
| **Tasks** — `OutRosterTeamDayTasks`, `InpTaskAbilityCollection` | intra-shift task allocation (a `TaskID` over a sub-interval, mapped to an ability); finer than v3's per-slot skill `y_wdts` | sidecar (result detail) | §4 |
| **Responsibilities** — `InResponsabilityCollection`, `InpResponsibilityAbilityCollection` | a second assignment axis — cost-centre / group / pool | sidecar | §4 |
| **Generation rules** — the whole `InpGenerationRules` block | algorithm steps, alarms, `GenerateOn*`, responsibility waste/override, blacklists, weekly-weight bounds — *how to solve* | drop / sidecar — it is *Sisqual's* solver config, not ours to honour | §2 |
| **Per-weekday / holiday contract weights** — `WeightMonday…Sunday`, `WeightHoliday*` | a different shift length per weekday / holiday type; v3 has one `workMinutesPerDay` | sidecar or future schema | §9 |
| **Monthly / yearly caps** — `TotalMonthlyMinutes`, `TotalYearMinutes` | limits beyond v3's daily/weekly | sidecar; **cheap to add** (see below) | §9 |
| **Workload demand** — `InpServiceLevelByDays` | demand as **minutes of workload**, not headcount (`alpha_dts`); from **M1** | sidecar | §9 |
| **`AbsenceCodeCountAsDayOff`** — from **M3** | whether an absence counts toward the rest quota; shifts `n_wk` | carry (it is a rule input) | §8 |
| **Minor advisory** — `Legend`/`Description`, `ScheduleAvailabilityCode`, `PotentialCycleScheduleWeightWhenScheduleIsSpace`, `InpEmployeeGeneratedParameterCollection`, `AlarmTable*` | display labels, cycle hints, generation params | drop on import | — |

**The one "could add now" candidate:** monthly / yearly caps are plain optional contract fields (like
`maxMinutesPerWeek`), so they are the cheapest to carry for round-trip value. Kept deferred anyway — no
solver reads them yet, and carrying an unenforced field is the stored-but-ignored trap the v3 cleanup
removed (the same discipline applied to M5's weekly target).

## Not here — already resolved

- **Labour law** — *not* set aside: promoted **into** the schema at [S3](SISQUAL-MERGE-EASY.md);
  enforcement is `../FUTURE.md` §8.
- **Split shifts** — **done** in both forms: multi-interval `assignmentCatalog` + the declarative
  `EQUALS:a-b,c-d` cell (see [M2.a](SISQUAL-MERGE-MEDIUM.md)).
- **Rest-type accounting** — the M3 question; it lives in `../FUTURE.md` §8, not here.

## In one line

Every row lands on a real roadmap item (§2, §4, §8, §9); **nothing here forces a schema change now.**
The merge's forward work *is* the roadmap — plus, only if a lossless round-trip is required, the adapter
sidecar.
