# Merge tier — Set aside

Part of the [merge proposal index](SISQUAL-MERGE-PROPOSAL.md). The reading legend and the **foundational
decisions** are in [SISQUAL-MERGE.md](SISQUAL-MERGE.md).

> **Status: to weigh next.** For each item the call will be *"into the merged schema now"* vs *"deferred
> behind a `FUTURE.md` item"*. Most already map onto the existing roadmap — see
> [SISQUAL-MERGE.md](SISQUAL-MERGE.md) → "Set aside" for the full analysis table.

Sisqual capabilities with no v3.0 home yet:

- **Tasks** — intra-shift task allocation (`OutRosterTeamDayTasks`, `InpTaskAbilityCollection`) → FUTURE §4.
- **Responsibilities** — `InResponsabilityCollection` (cost-centre / group / pool), `InpResponsibilityAbilityCollection` → FUTURE §4.
- **Generation rules** — the whole `InpGenerationRules` block (algorithm steps, alarms, `GenerateOn*`, responsibility waste/override, blacklists…) → FUTURE §2 (solve-directives registry) — the big one.
- **Per-weekday & holiday contract weights** — `WeightMonday…Sunday`, `WeightHoliday*` → contract extension (relates to FUTURE §5).
- **Monthly / yearly caps** — `TotalMonthlyMinutes`, `TotalYearMinutes` → contract extension.
- **Workload demand** — `InpServiceLevelByDays` (minutes, not headcount; from **M1**) → a new demand mode.
- **`AbsenceCodeCountAsDayOff`** — an absence that counts toward limits (from **M3**); shifts `n_wk` → labour-law / registry.
- **Minor advisory fields** — `Legend`/`Description`, `ScheduleAvailabilityCode`, `PotentialCycleScheduleWeightWhenScheduleIsSpace`, `InpEmployeeGeneratedParameterCollection`, `AlarmTable*` → drop on import, or fold into §2.

**Not here:** **labour law** was promoted *into* the schema at **S3** (Easy tier); only its *enforcement*
stays deferred (FUTURE §2). **Split-shift** representation already exists in the expanded form (see **M6**).
