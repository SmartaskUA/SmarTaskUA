# Next meeting with Sisqual — agenda

Everything here comes from the two bundles they generated on 2026-09-17, the result payload they emailed on 2026-07-23, and their own `JSON-Export.docx` / `JSON-Import.docx`. Every claim is reproducible against the files under `reference/IntegracaoUA_SISQUAL/`.

**Where we stand.** v4.0 is finished and is the deliverable: two JSON Schemas, a validator, a worked example and a conformance suite. We are **not** shipping an adapter for their current export. The schema says what a problem looks like; where their generator differs, the list under *Naming* is what we need them to change. If they cannot, we will write the adapter then — but building one now would be building against a moving target.

**The two things to open with.** Item 5 (we mint our own schedule codes — does that work for WFM?) and item 21 (Cenário 1 cannot be solved, so we dropped it).

---

## Where we already agree

Worth saying first, because it is most of the picture. We checked v4.0 against every file under `reference/IntegracaoUA_SISQUAL/` — the two September bundles, the July one, the result sample, and both specification documents — and:

- **Every key in every bundle is covered** by `schema-v4-input.json`. Nothing your generator emits is unrepresentable.
- **The CSV headers match exactly**, all four kinds.
- **Our worked example's CSVs are byte-identical to yours** — 314 demand rows and 16 schedule-input rows, zero differences, once the decimal comma is normalised.
- **The result schema covers every field** in `import_1.Json` and every field `JSON-Import.docx` specifies. Nothing missing, nothing invented.

So the format is settled. What follows is the residue: 27 points, of which 9 need an answer from you, 6 are corrections we have already applied, 2 are changes we are proposing, 4 are defects in the data you sent, and 6 are scope questions.

### The differences in one table

Every way v4.0 departs from what your generator currently produces:

| kind | count | where |
|---|---|---|
| Keys we spell differently, or values we case differently | 8 | items 12–14 |
| Keys we add that you do not emit | 3 | `demand.dimensions[]`, `metadata.rosterCode`, `schedules.dataFile` |
| Collections of yours we model only in part | 2 | `InpContractCollection` (3 of 17), `InpGenerationRules` (9 of ~40) |
| Collections of yours we do not model at all | 5 | items 24 and 25 |
| Fields of yours with no v4.0 equivalent | 2 | `DayType`, `Legend` — item 6 |
| Places your two documents contradict each other | 3 | items 13, 15 |

---

## Blocking — we cannot validate, or cannot solve, without an answer

**1. What is the ordering of `minimum`, `ideal`, `estimated`?** v3.0 was ascending (`minimum ≤ empiric ≤ maximum`). v2.6 was `minimum ≤ estimated ≤ ideal` — `ideal` was the *upper* bound sitting in the *middle* column. The demand CSVs use the v2.6 header but write `0` in both columns in every row of every bundle, so the data cannot settle it. Until it is settled our validator enforces **no ordering at all**, only non-negativity, because guessing wrong is the failure mode that corrupts silently: the file still parses, every check still passes, and the staffing is wrong. `maxAlarmTableType: "MaxAlarmLevel_Estimate_Ideal_Minimum"` reads like a *fallback* order rather than a bound order — is that the same triple?

**2. `days_demand.csv` and `periods_demand.csv` have byte-identical headers but different units.** Per `JSON-Export.docx`, `InpServiceLevelByDays` is workload *minutes* and `InpServiceLevelByPeriods` is *headcount*. Nothing in either file says which it is; only the JSON key pointing at it does. Can the header carry the unit?

**3. What vocabulary does `shifts_demand.csv`'s `workPeriod` column use?** `JSON-Export.docx` says `InpServiceLevelByShifts.ShiftTypeCode` is `M`/`T`/`N`. The file is header-only in every bundle, so we have never seen a value.

**4. What is the element shape of `constraints.soft[]`?** It is present and empty in both bundles. Our schema leaves it deliberately unconstrained rather than invent one.

**5. We mint our own schedule codes. Does that work on your side?**

A `ScheduleCode` stands for a grouping of hours, and the catalogue CSV *is* the translation — nothing more. So v4.0 treats the menu as ours to author: if a roster needs a 420-minute shift, the menu gets a row for one.

```
code,description,scheduleWeightMinutes,startMin,endMin
9001,09:00-13:00,240,540,780
9012,09:00-16:00,420,540,960
```

The example ships a 19-shift menu on this basis. Codes `1`, `3` and `4` keep your numbers, because those carry WFM's own rest semantics on import; everything else is new and the numbering is arbitrary.

Two questions. **Does WFM accept a code it does not already hold**, or must every code be pre-registered on your side? And if it must, what is the registration path — do we send you a menu and get codes back?

*(This replaces what would otherwise have been three separate asks about your `Schedules_Without_meal.xlsx`. We are no longer deriving anything from it.)*

**6. Our shift menu cannot express `DayType`, and yours can.**

`InpScheduleUsedCollection` gives every schedule a `DayType` — `0` WeekDay, `1` WeekEndSaturday (*folga complementar*), `2` WeekEndSunday (*folga obrigatória*), `3` Empty (*V folga*) — plus a `Legend`. Our menu CSV has neither:

```
code,description,scheduleWeightMinutes,startMin,endMin
```

We recognise a rest code structurally instead — a row with no window and zero weight — which collapses your four day-types into a binary *works / does not work*. So a result of ours can say "this person rests on Sunday" but not "this is the obligatory Sunday rest rather than the complementary Saturday one".

**Does WFM need the distinction on import?** If it does, we add a `dayType` column and the rest-type becomes a first-class value. If it does not, we would rather not carry a field nothing reads. The same question decides whether the *input* side needs it: `AbsenceCodeCountAsDayOff` and the Folga types are the two things that would let labour law count rest by kind over a window.

**7. Two contracts can be identical in the export, and therefore unusable.**

`workMinutesPerDay` is the only field a contract carries, and it does not identify one. In Cenário 2:

| what the export carries | contracts sharing it |
|---|---|
| `{"workMinutesPerDay": 300}` | `PT_10` — 10h/week over **2 days** · `PT_25` — 25h/week over **5 days** |
| `{"workMinutesPerDay": 240}` | `PT_12` — 12h/week over **3 days** · `PT_20` — 20h/week over **5 days** |

The weekly obligation survives only in the pre-filled day-off pattern of `schedule_input.csv`. That is input data, not a constraint: it is correct in what you sent, but nothing requires it to be, and a solver asked to *choose* the days off could not honour the contract.

`InpContractCollection` already models this — `TotalWeeklyMinutes`, `TotalWeeklyWorkDays`, `TotalMonthlyMinutes`, `TotalYearMinutes`, and the per-weekday weights. Can the exporter carry them? See also item 22 and [FUTURE.md](docs/FUTURE.md) §1.

**8. The competency catalogue is never exported.** `JSON-Export.docx` defines `InpTaskAbilityCollection` and `InResponsabilityCollection`, but neither appears in any bundle, so the `(tableName, tableValue)` coordinates exist only implicitly — and the three places they appear **disagree** (item 11). v4.0 requires a `demand.dimensions[]` block that declares them. Can the exporter emit it?

**9. Work periods are gone.** v3.0 declared named, reusable periods with a `timeRange`; v4.0 has no catalogue and every demand row carries a literal window (25 distinct ones in Cenário 2). Deliberate?

---

## Naming and format — we have corrected these in v4.0

These are what a conforming export has to change. None of them is negotiable from our side in the sense that v4.0 already spells them the corrected way; they are listed so the exporter can be aligned.

| your export | v4.0 | why |
|---|---|---|
| `"form": "declarative"` | `"form": "input"` | it pairs with `result`; "declarative" only ever made sense against the expanded form v4.0 does not have |
| `schemaVersion: "3.0"` | `"4.0"` | the payload is not v3.0 — three v3.0-required keys are absent |
| `employees[].contractAssigments` | `contractAssignments` | misspelled: missing `n` |
| `priorityHierachy` (root) | `priorityHierarchy` | misspelled: missing `r` |
| `calendar.inpUAHolidaysCollection` | `calendar.holidays` | an internal `Inp…Collection` name leaking into the payload |
| `weekStart: "Monday"` | `"monday"` | v3.0's enum was lowercase and v4.0 keeps it |
| `dayOffCodes[].kind: "Preferable"` / `"Unavailable"` | lowercase | same |
| `end: "9999-12-31"` | `end: null` | a sentinel where the format already has a way to say "no end" |
| `tableName: "Equipa"` / `"Piso"` | `"Team"` / `"Responsibility"` | see item 12 |
| *(absent)* | `metadata.rosterCode` | a result carries `RosterCode` alone; stating the join once beats re-splitting `problemId` |
| *(absent)* | `demand.dimensions[]` | item 8 |
| CSV: UTF-8 **with BOM**, CRLF | plain UTF-8, LF | see item 12 |
| CSV: `"7,2"`, decimal comma | `7.2` | see item 17 |

**10. Three keys are misspelled** — the three in the table above. We have spelled them correctly; please align the exporter.

**11. `tableName` is bilingual, and the two languages never meet.** In one bundle, `employees[].competencyAssignments` says `Equipa` and `Piso`, while `priorityHierachy` and the demand CSV say `Team` and `Responsibility`. The sets of names have an **empty intersection** — only `tableValue` (`T1`, `A`, `C`, `G`) joins. We read it as `Equipa → Team` and `Piso → Responsibility`; please confirm, and please emit one language.

**12. CSVs ship as UTF-8 with a BOM and CRLF.** Read naively, the first column comes back named `﻿date` and fails every lookup by a character nobody can see. Our reader strips it, but plain UTF-8 with LF would be easier on every consumer.

**13. `EmployeeCode` is an integer in `OutRosterTeamDays` but a string everywhere in the problem.** `JSON-Import.docx` says string. We accept both and warn.

**14. Three datetime formats coexist in one document:** `YYYY-MM-DD` (dates), `…THH:MM:SSZ` (`metadata.createdAt`), and naive `…THH:MM:SS` (`constraints.hard[].startDate`, `OutRosterTeamDays[].Date`).

---

**15. `ScheduleWeight` is minutes in one of your documents and hours in the other.**

`JSON-Export.docx` gives `InpScheduleUsedCollection.ScheduleWeight` as *"peso do horário (unidade minutos)"*. `JSON-Import.docx` gives `OutScheduleUseds.ScheduleWeight` as *"peso do horário (h/dia)"*. Same field name, same concept, two units.

We read it as **minutes** on both sides, because the spreadsheet you sent is headed `ScheduleWeightMinutes` and its values (180, 240, 480) are unambiguously minutes. Please confirm, and fix whichever document is wrong.

## Proposed change — needs your agreement

**16. `schedule_input.csv` cells should be minutes, not hours.**

Today a contract states `workMinutesPerDay: 480` and the matching cell states `8` — one bundle, two units. Worse, the NL contract's 7.2 hours is written `"7,2"` with a decimal comma, so the field has to be quoted and parsed locale-aware, and `float("7,2")` throws in every language we use. `7.2 h` is exactly `432` minutes and is representable without loss; as a decimal it is not.

This is the same defect that forced v2.6 → v3.0 on our side. **Until you agree, v4.0 keeps hours** — our validator reads them and rejects anything above 24 as an unconverted minute count.

**17. And the decimal comma should go with it.** Even if cells stay hours, writing `7.2` rather than `"7,2"` removes a locale dependency and a quoting rule.

---

## Data defects in the bundles you sent

**18. Cenário 2: three employees hold the same competency twice, at two levels.** `20067009` holds `Team/T1` at level 1 *and* level 3 over the same dates, and the same for its three `Responsibility` coordinates; `20054956` (levels 2 and 4) and `20062688` (levels 3 and 4) likewise. That leaves their competence level undefined. We warn and take the lower number (the higher competence) — is that right, or is it a duplicate from a join?

**19. The July bundle (`reference/IntegracaoUA_SISQUAL/sisqual-alg-input/`) has `contracts.definitions: []`** while all 15 employees reference contract `PT_40`.

**20. `import_1.Json` is not valid JSON.** It is indented with U+2002 EN SPACE characters — an Outlook paste artifact. Both `jq` and Python reject it.

**21. Cenário 1 — the scenario we had to drop.**

We are not shipping it as an example, because a bundle that fails three independent ways cannot be a reference for anything. It stays in our tree as raw provenance only. The three:

- Contract `NL_36` is **432 minutes/day** on a **30-minute grid**. 432 is not a multiple of 30, so no shift of the contracted length can be placed on any day — 335 unsatisfiable worker-days. A grid of 6, 8, 12, 16, 24 or 48 would work.
- Every one of its 12 employees has `competencyAssignments: []`, so nobody can cover any dimension.
- All three demand CSVs are **header-only**, so every day is closed and nothing needs staffing.

---

## Scope — what we are dropping, and whether we should be

**22. `InpContractCollection` defines 17 fields and v4.0 carries 3.**

We keep `ContractCode` (as `id`), `Description` (as `name`) and `TotalDailyMinutes` (as `workMinutesPerDay`). The 14 we drop:

| dropped | what it would give us |
|---|---|
| `TotalWeeklyMinutes`, `TotalWeeklyWorkDays`, `TotalWeeklyWorkDaysMax` | **the fix for item 7** — the weekly obligation that currently separates `PT_10` from `PT_25` only by accident |
| `TotalMonthlyMinutes`, `TotalYearMinutes` | limits beyond the week |
| `WeightMonday`…`WeightSunday` (7) | a different shift length per weekday; our one `workMinutesPerDay` assumes every working day is the same |
| `WeightHolidayBusinessDay`, `WeightHolidaySaturday`, `WeightHolidaySunday` | the same, per holiday type |

Which must the algorithm honour? We would rather add a field than store one nothing reads — but the first row is not optional, it is item 7.

**23. `priorityHierarchy` is a nine-field projection of `InpGenerationRules` (~40 fields).** Which of the others are load-bearing for the result you expect — `AlgorithmStep`, `FindScheduleType`, `FollowLevelByLevel`, the `Responsability*` waste/override/cover settings, the per-weekday `GenerateOn*` flags?

**24. Three more collections we do not read at all.**

Beyond tasks and responsibilities, `JSON-Export.docx` defines three collections that have no v4.0 equivalent and that no bundle has exercised:

- **`InpRosterSchedulesCollection`** — per-roster shift availability, i.e. which `ScheduleCode`s a given roster may use. If this is how you expect a solver to be constrained, it overlaps directly with the menu question in item 5 and we should reconcile the two rather than invent a second mechanism.
- **`InpEmployeeLLabourLawLegislationCollection`** — per-employee legislation. v4.0's `constraints.hard[]` is roster-wide, so a rule that applies to one worker and not another is currently inexpressible.
- **`InpGroupRulesIndexDatesToExecuteCollection`** — when generation runs. That is orchestration rather than problem definition, so we think it is correctly outside the schema; confirm that you agree.

**25. Tasks and responsibilities are always empty.** `OutRosterTeamDayTasks` and `OutRosterTeamDayResponsibilities` are `[]` in every sample. Is intra-shift task allocation in scope for us, or yours?

**26. Breaks and meals are not modelled at all.** v4.0 has no break concept: a shift's paid length is its clock length. Deliberate for now — see [FUTURE.md](docs/FUTURE.md) §2 — but it means a shift long enough to require a meal break is currently indistinguishable from one that is not.

---

## What our results will carry

**27. A result ships a sidecar CSV naming the shifts it used.** A result at `result.json` is accompanied by `result_schedules.csv`, in the same shape as the menu, holding exactly the codes that appear in the result:

```
code,description,scheduleWeightMinutes,startMin,endMin
9001,09:00-13:00,240,540,780
9012,09:00-16:00,420,540,960
```

This is **our convention, not part of your format**. We added it because a result names numeric codes and carries no definition of them, so it cannot be read or checked on its own. We kept it *beside* the file rather than inside it precisely so that `OutRosterTeamDays` stays exactly as `JSON-Import.docx` specifies.

Does WFM want it, or would you rather we populate `OutScheduleUseds` in the JSON?
