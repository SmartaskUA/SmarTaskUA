# Next meeting with Sisqual — agenda

Everything here comes from the three bundles they generated, the result payload
they emailed, `Schedules_Without_meal.xlsx`, and their own `JSON-Export.docx` /
`JSON-Import.docx`. Every claim is reproducible: run

```bash
PYTHONPATH=src python3 -m schema_v4.sisqual_adapt <bundle> -o /tmp/out --stats
PYTHONPATH=src python3 -m schema_v4.validator /tmp/out -v
```

and the adapter prints the naming items while the validator prints the rest.

**The headline.** Of the two scenarios they generated on 2026-09-17, one
(Cenário 2) is sound and one (Cenário 1) cannot be solved at all — for three
independent reasons, any one of which is fatal. That is item 20, and it is the
thing to open with.

---

## Blocking — we cannot validate, or cannot solve, without an answer

**1. What is the ordering of `minimum`, `ideal`, `estimated`?**
v3.0 was ascending (`minimum ≤ empiric ≤ maximum`). v2.6 was
`minimum ≤ estimated ≤ ideal` — `ideal` was the *upper* bound sitting in the
*middle* column. The demand CSVs use the v2.6 header but write `0` in both
columns in every row of every bundle, so the data cannot settle it. Until it is
settled our validator enforces **no ordering at all**, only non-negativity, because
guessing wrong is the failure mode that corrupts silently: the file still parses,
every check still passes, and the staffing is wrong.
`maxAlarmTableType: "MaxAlarmLevel_Estimate_Ideal_Minimum"` reads like a *fallback*
order rather than a bound order — is that the same triple?

**2. `days_demand.csv` and `periods_demand.csv` have byte-identical headers but
different units.** Per `JSON-Export.docx`, `InpServiceLevelByDays` is workload
*minutes* and `InpServiceLevelByPeriods` is *headcount*. Nothing in either file
says which it is; only the JSON key pointing at it does. Can the header carry the
unit, or the files carry distinct column names?

**3. What vocabulary does `shifts_demand.csv`'s `workPeriod` column use?**
`JSON-Export.docx` says `InpServiceLevelByShifts.ShiftTypeCode` is `M`/`T`/`N`.
The file is header-only in all three bundles, so we have never seen a value.

**4. What is the element shape of `constraints.soft[]`?** It is present and empty
in both September bundles. Our schema leaves it deliberately unconstrained rather
than invent a shape.

**5. The with-meal schedule catalogue is missing.**
`Schedules_Without_meal.xlsx` holds 1,277 codes. `ScheduleCode 100154` — the one in
your own `import_1.Json` and visible in your screenshot as `00:00-07:00` with a
`04:00-04:30` break — **is not in it**, because it has a meal break. Without the
with-meal catalogue a solver cannot name any shift containing a break. Our
validator flags this concretely on `examples/cenario1_nlm/result.json`.

**6. 914 of the 1,277 catalogue codes cannot be used on the grid you specify.**
The catalogue is built on a 15-minute grid (start times step 00:00, 00:15, 00:30 …)
while every bundle declares `timeGrid.slotMinutes: 30`. On a 30-minute grid, 914
codes are unreachable. Should the grid be 15, or should the catalogue be filtered?

**7. What is `ScheduleCode 1020`, "Flexible"?** It has a weight (480 minutes) but no
window — a length without a position, which is exactly v3.0's synthesis model
appearing inside the menu. May a solver emit it, and if so what does WFM do with it?

**8. The competency catalogue is never exported.** `JSON-Export.docx` defines
`InpTaskAbilityCollection` and `InResponsabilityCollection`, but neither appears in
any bundle, so the `(tableName, tableValue)` coordinates exist only implicitly. Worse,
the three places they appear **disagree** (item 12). v4.0 adds a required
`demand.dimensions[]` and our adapter synthesises it — can the exporter emit it
directly?

**9. `InpScheduleUsedCollection` is never exported either.** The shift catalogue
reached us as an email attachment. Can it ship inside the bundle, so a problem is
self-contained and versioned with the data it describes?

**10. Work periods are gone.** v3.0 declared named, reusable periods with a
`timeRange`; v4.0 has no catalogue and every demand row carries a literal window
(25 distinct ones in Cenário 2). Deliberate?

---

## Naming and format — we have already corrected these on our side

Our adapter fixes each of these and prints what it changed. They are listed so the
exporter can be aligned; nothing here blocks us.

**11. Three keys are misspelled.**
`contractAssigments` is missing an `n` (should be `contractAssignments`);
`priorityHierachy` is missing an `r` (should be `priorityHierarchy`);
`calendar.inpUAHolidaysCollection` leaks an internal `Inp…Collection` name into
the payload (we call it `calendar.holidays`).

**12. `tableName` is bilingual, and the two languages never meet.**
In one bundle, `employees[].competencyAssignments` says `Equipa` and `Piso`, while
`priorityHierachy` and the demand CSV say `Team` and `Responsibility`. The sets of
names have an **empty intersection** — only `tableValue` (`T1`, `A`, `C`, `G`)
joins. We map `Equipa → Team` and `Piso → Responsibility`; please confirm, and
please emit one language.

**13. Three enum values are capitalised.** `weekStart: "Monday"` and
`dayOffCodes[].kind: "Preferable"` / `"Unavailable"`. v3.0's enums were lowercase
and v4.0 keeps them that way.

**14. `"9999-12-31"` as an open-ended sentinel.** v4.0 uses `null`, which is what
v3.0 used and what "no end date" actually means.

**15. `EmployeeCode` is an integer in `OutRosterTeamDays` but a string everywhere in
the problem.** `JSON-Import.docx` says string. We accept both and warn.

**16. Three datetime formats coexist in one document:** `YYYY-MM-DD` (dates),
`…THH:MM:SSZ` (`metadata.createdAt`), and naive `…THH:MM:SS`
(`constraints.hard[].startDate`, `OutRosterTeamDays[].Date`).

**17. CSVs ship as UTF-8 **with BOM** and CRLF.** Read naively, the first column
comes back named `﻿date` and fails every lookup by a character nobody can see.
Plain UTF-8 with LF would be easier on every consumer.

---

## Proposed change — needs your agreement

**18. `schedule_input.csv` cells should be minutes, not hours.**

Today a contract states `workMinutesPerDay: 480` and the matching cell states `8`
— one bundle, two units. Worse, the NL contract's 7.2 hours is written `"7,2"`,
with a decimal comma, so the field has to be quoted and parsed locale-aware, and
`float("7,2")` throws in every language we use. `7.2 h` is exactly `432` minutes
and is representable without loss; as a decimal it is not.

This is the same defect that forced v2.6 → v3.0 on our side, and it is the one
change we would most like. **Until you agree, v4.0 keeps hours** — our validator
reads them and rejects anything above 24 as an unconverted minute count.

---

## Data defects in the bundles you sent

**19. Cenário 2: three employees hold the same competency twice, at two levels.**
`20067009` holds `Team/T1` at level 1 *and* level 3 over the same dates, and the
same for its three `Responsibility` coordinates; `20054956` (levels 2 and 4) and
`20062688` (levels 3 and 4) likewise. That leaves their competence level
undefined. We warn and take the lower number (the higher competence) — is that
right, or is it a duplicate from a join?

**20. Cenário 1 cannot be solved, for three independent reasons.**
- Contract `NL_36` is **432 minutes/day** on a **30-minute grid**. 432 is not a
  multiple of 30, so no shift of the contracted length can be placed on any day —
  335 unsatisfiable worker-days. A grid of 6, 8, 12, 16, 24 or 48 would work.
- Every one of its 12 employees has `competencyAssignments: []`, so nobody can
  cover any dimension.
- All three demand CSVs are **header-only**, so every day is closed and nothing
  needs staffing.

**21. The July bundle (`sisqual-alg-input/`) has `contracts.definitions: []`** while
all 15 employees reference contract `PT_40`. We keep it as a negative test fixture.

**22. `import_1.Json` is not valid JSON.** It is indented with U+2002 EN SPACE
characters — an Outlook paste artifact. Both `jq` and Python reject it.

---

## Scope — what we are dropping, and whether we should be

**23. `InpContractCollection` has 16 fields we do not carry**, among them
`TotalWeeklyMinutes`, `TotalMonthlyMinutes`, `TotalYearMinutes`,
`TotalWeeklyWorkDays`, the per-weekday weights `WeightMonday…WeightSunday`, and
`WeightHolidayBusinessDay/Saturday/Sunday`. v4.0 keeps only `TotalDailyMinutes` as
`workMinutesPerDay`. Which of the rest must the algorithm honour? We would rather
add a field than store one nothing reads.

**24. `priorityHierarchy` is a nine-field projection of `InpGenerationRules`
(~40 fields).** Which of the others are load-bearing for the result you expect —
`AlgorithmStep`, `FindScheduleType`, `FollowLevelByLevel`, the
`Responsability*` waste/override/cover settings, the per-weekday `GenerateOn*`
flags?

**25. Tasks and responsibilities are always empty.**
`OutRosterTeamDayTasks` and `OutRosterTeamDayResponsibilities` are `[]` in every
sample. Is intra-shift task allocation in scope for us, or yours?
