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
independent reasons, any one of which is fatal. **We have dropped Cenário 1 from
our examples entirely**; it is item 20, and it is the thing to open with.

**The second thing to raise** is item 5. It is not "please also send the with-meal
list" — it is that the catalogue we hold cannot dress a `PT_35` employee at *all*,
so a third of Cenário 2's full-timers have no legal shift to be given.

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

**5. The with-meal schedule catalogue is missing, and without it some employees
cannot be scheduled at all.**

`Schedules_Without_meal.xlsx` holds 1,277 codes, but its usable band is narrower
than that number suggests. Shifts run **180–360 minutes** in 15-minute steps, ~96
codes per duration — and then stop. Above six hours there are just 19 one-off codes,
mostly overnight or full-day blocks. So, against Cenário 2's own contracts:

| contract | needs | codes available |
|---|---|---|
| `PT_20`, `PT_12` | 240 min | 50 on the 30-min grid |
| `PT_25`, `PT_10` | 300 min | 49 on the 30-min grid |
| `PT_35` | 420 min | **zero. None exists.** |
| `PT_40` | 480 min | 3, of which only `1014` (08:00-16:00) suits a retail day — and it opens 30 min before demand does |

Six hours is the meal-break threshold, so this is the file's boundary, not a gap in
it. `ScheduleCode 100154` — the one in your own `import_1.Json`, shown in your
screenshot as `00:00-07:00` with a `04:00-04:30` break — is absent for the same
reason.

Concretely: our worked result for Cenário 2 has to substitute a 390-minute shift for
all 21 `PT_35` working days, because nothing of the right length exists. Please send
the with-meal catalogue.

**6. Two contracts can be identical in the export, and therefore unusable.**

`workMinutesPerDay` is the only field a contract carries, and it does not identify
one. In Cenário 2:

| what the export carries | contracts sharing it |
|---|---|
| `{"workMinutesPerDay": 300}` | `PT_10` — 10h/week over **2 days** · `PT_25` — 25h/week over **5 days** |
| `{"workMinutesPerDay": 240}` | `PT_12` — 12h/week over **3 days** · `PT_20` — 20h/week over **5 days** |

The weekly obligation survives only in the pre-filled day-off pattern of
`schedule_input.csv`. That is input data, not a constraint: it is correct in what
you sent, but nothing requires it to be, and a solver asked to *choose* the days off
could not honour the contract.

`InpContractCollection` already models this — `TotalWeeklyMinutes`,
`TotalWeeklyWorkDays`, `TotalMonthlyMinutes`, `TotalYearMinutes`, and the per-weekday
weights. Can the exporter carry them? See also item 23 and `FUTURE.md` §1.

**7. 914 of the 1,277 catalogue codes cannot be used on the grid you specify.**
The catalogue is built on a 15-minute grid (start times step 00:00, 00:15, 00:30 …)
while every bundle declares `timeGrid.slotMinutes: 30`. On a 30-minute grid, 914
codes are unreachable. Should the grid be 15, or should the catalogue be filtered?

**8. What is `ScheduleCode 1020`, "Flexible"?** It has a weight (480 minutes) but no
window — a length without a position, which is exactly v3.0's synthesis model
appearing inside the menu. May a solver emit it, and if so what does WFM do with it?

**9. The competency catalogue is never exported.** `JSON-Export.docx` defines
`InpTaskAbilityCollection` and `InResponsabilityCollection`, but neither appears in
any bundle, so the `(tableName, tableValue)` coordinates exist only implicitly. Worse,
the three places they appear **disagree** (item 13). v4.0 adds a required
`demand.dimensions[]` and our adapter synthesises it — can the exporter emit it
directly?

**10. `InpScheduleUsedCollection` is never exported either.** The shift catalogue
reached us as an email attachment. Can it ship inside the bundle, so a problem is
self-contained and versioned with the data it describes?

**11. Work periods are gone.** v3.0 declared named, reusable periods with a
`timeRange`; v4.0 has no catalogue and every demand row carries a literal window
(25 distinct ones in Cenário 2). Deliberate?

---

## Naming and format — we have already corrected these on our side

Our adapter fixes each of these and prints what it changed. They are listed so the
exporter can be aligned; nothing here blocks us.

**12. Three keys are misspelled.**
`contractAssigments` is missing an `n` (should be `contractAssignments`);
`priorityHierachy` is missing an `r` (should be `priorityHierarchy`);
`calendar.inpUAHolidaysCollection` leaks an internal `Inp…Collection` name into
the payload (we call it `calendar.holidays`).

**13. `tableName` is bilingual, and the two languages never meet.**
In one bundle, `employees[].competencyAssignments` says `Equipa` and `Piso`, while
`priorityHierachy` and the demand CSV say `Team` and `Responsibility`. The sets of
names have an **empty intersection** — only `tableValue` (`T1`, `A`, `C`, `G`)
joins. We map `Equipa → Team` and `Piso → Responsibility`; please confirm, and
please emit one language.

**14. Three enum values are capitalised.** `weekStart: "Monday"` and
`dayOffCodes[].kind: "Preferable"` / `"Unavailable"`. v3.0's enums were lowercase
and v4.0 keeps them that way.

**15. `"9999-12-31"` as an open-ended sentinel.** v4.0 uses `null`, which is what
v3.0 used and what "no end date" actually means.

**16. `EmployeeCode` is an integer in `OutRosterTeamDays` but a string everywhere in
the problem.** `JSON-Import.docx` says string. We accept both and warn.

**17. Three datetime formats coexist in one document:** `YYYY-MM-DD` (dates),
`…THH:MM:SSZ` (`metadata.createdAt`), and naive `…THH:MM:SS`
(`constraints.hard[].startDate`, `OutRosterTeamDays[].Date`).

**18. CSVs ship as UTF-8 **with BOM** and CRLF.** Read naively, the first column
comes back named `﻿date` and fails every lookup by a character nobody can see.
Plain UTF-8 with LF would be easier on every consumer.

---

## Proposed change — needs your agreement

**19. `schedule_input.csv` cells should be minutes, not hours.**

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

**20. Cenário 2: three employees hold the same competency twice, at two levels.**
`20067009` holds `Team/T1` at level 1 *and* level 3 over the same dates, and the
same for its three `Responsibility` coordinates; `20054956` (levels 2 and 4) and
`20062688` (levels 3 and 4) likewise. That leaves their competence level
undefined. We warn and take the lower number (the higher competence) — is that
right, or is it a duplicate from a join?

**21. Cenário 1 — the scenario we had to drop.**

We are not shipping it as an example, because a bundle that fails three independent
ways cannot be a reference for anything. It stays in our tree only as raw
provenance. The three:

- Contract `NL_36` is **432 minutes/day** on a **30-minute grid**. 432 is not a
  multiple of 30, so no shift of the contracted length can be placed on any day —
  335 unsatisfiable worker-days. A grid of 6, 8, 12, 16, 24 or 48 would work.
- Every one of its 12 employees has `competencyAssignments: []`, so nobody can
  cover any dimension.
- All three demand CSVs are **header-only**, so every day is closed and nothing
  needs staffing.

Reproduce all three at once with:

```bash
python3 -m schema_v4.sisqual_adapt \
  "IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_1" -o /tmp/c1
python3 -m schema_v4.validator /tmp/c1 -v
```

**22. The July bundle (`IntegracaoUA_SISQUAL/sisqual-alg-input/`) has `contracts.definitions: []`** while
all 15 employees reference contract `PT_40`. We keep it as a negative test fixture.

**23. `import_1.Json` is not valid JSON.** It is indented with U+2002 EN SPACE
characters — an Outlook paste artifact. Both `jq` and Python reject it.

---

## Scope — what we are dropping, and whether we should be

**24. `InpContractCollection` has 16 fields we do not carry**, among them
`TotalWeeklyMinutes`, `TotalMonthlyMinutes`, `TotalYearMinutes`,
`TotalWeeklyWorkDays`, the per-weekday weights `WeightMonday…WeightSunday`, and
`WeightHolidayBusinessDay/Saturday/Sunday`. v4.0 keeps only `TotalDailyMinutes` as
`workMinutesPerDay`. Which of the rest must the algorithm honour? We would rather
add a field than store one nothing reads.

**25. `priorityHierarchy` is a nine-field projection of `InpGenerationRules`
(~40 fields).** Which of the others are load-bearing for the result you expect —
`AlgorithmStep`, `FindScheduleType`, `FollowLevelByLevel`, the
`Responsability*` waste/override/cover settings, the per-weekday `GenerateOn*`
flags?

**26. Tasks and responsibilities are always empty.**
`OutRosterTeamDayTasks` and `OutRosterTeamDayResponsibilities` are `[]` in every
sample. Is intra-shift task allocation in scope for us, or yours?

---

## What our results will carry

**27. A result now ships a sidecar CSV naming the shifts it used.** A result at
`result.json` is accompanied by `result_schedules.csv`, in the same shape as the
schedule catalogue, holding exactly the `ScheduleCode`s that appear in the result:

```
code,description,scheduleWeightMinutes,startMin,endMin
1014,08:00-16:00,480,480,960
300000,10:00-16:30,390,600,990
```

This is **our convention, not part of your format**. We added it because a result
names numeric codes and carries no definition of them, so it cannot be read or
checked on its own. We kept it *beside* the file rather than inside it precisely so
that `OutRosterTeamDays` stays exactly as `JSON-Import.docx` specifies.

Two questions: does WFM want it, or would you rather we populate `OutScheduleUseds`
in the JSON instead? And if a result names a code your catalogue does not have, what
should happen on import?
