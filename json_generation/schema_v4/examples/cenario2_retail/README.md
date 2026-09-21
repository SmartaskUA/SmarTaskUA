# cenario2_retail — retail store, January 2026

Adapted from the SISQUAL bundle at
`IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2/`
(generated 2026-09-17). The raw drop is untouched; this is its canonical form.

| | |
|---|---|
| Workers | 15 |
| Horizon | 2026-01-01 .. 2026-01-31 (31 days, all open) |
| Contracts | 6 — `PT_10` `PT_12` `PT_20` `PT_25` `PT_35` `PT_40` (240–480 min/day) |
| Dimensions | `Team/T1`, `Responsibility/A`, `Responsibility/C`, `Responsibility/G` |
| Demand | 313 rows, all on the **periods** grain; days and shifts are empty |
| Grid | 30 minutes |
| Calendar | one holiday, 2026-01-01 (New Year's Day), `hasEve: false` |

```bash
cd ../..                                                          # schema_v4/
PYTHONPATH=src python3 -m schema_v4.validator examples/cenario2_retail -v
```

Validates with no errors. Regenerate it from the raw bundle at any time:

```bash
PYTHONPATH=src python3 -m schema_v4.sisqual_adapt \
  "IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2" \
  -o examples/cenario2_retail --stats
```

## What it demonstrates

**Coverage on a two-dimensional coordinate.** Every demand row names a
`(tableName, tableValue)` pair rather than v3.0's single competency code, and the
same employee holds several at once — `Team/T1` plus three `Responsibility` floors.
The two dimensions overlap in time deliberately: a worker satisfies a Team row and
a Responsibility row in the same hour.

**Windows are inline, not named.** There is no work-period catalogue. Each row
carries its own `start`/`end`, and this bundle uses 25 distinct windows. `Team/T1`
rows tile each day contiguously (10:00–11:00, 11:00–13:00, …) while
`Responsibility` rows are sparse and may leave gaps.

**`priorityHierarchy` carries generation settings, not just an order.** Four ranks,
each with `maxAlarmTableType`, `generationSequenceType` and an ability-level range —
a nine-field projection of SISQUAL's ~40-field `InpGenerationRules`.

**Labour law arrives as data.** `constraints.hard[0]` is a `RosterLegislation`
entry whose `parameters` bag carries `MaxConsecutiveWorkDays: 5`,
`MaxConsecutiveWorkDaysInWeek: 5` and `MinDistanceBetweenShiftsInMinutes: 660`.
v3.0 had cut this block entirely; the validator now acts on the first two.

**One employee in five holds the same competency twice.** `20067009`, `20054956`
and `20062688` each hold their four coordinates at two different levels over the
same dates, which leaves their competence level ambiguous. The validator warns and
says which level to take (the lower number — the higher competence). This is real
SISQUAL output, not a transcription error, and it is
[next_meeting.md](../../docs/next_meeting.md) item 19.

## What the adapter changed

Nineteen distinct fixes, the notable ones being `contractAssigments` →
`contractAssignments` (×15), `priorityHierachy` → `priorityHierarchy`,
`inpUAHolidaysCollection` → `holidays`, `Equipa` → `Team` (×18) and `Piso` →
`Responsibility` (×54), three capitalised enums lowercased, fifteen
`"9999-12-31"` sentinels turned into `null`, a UTF-8 BOM and CRLF stripped from
four CSVs, and `demand.dimensions[]` synthesised from the four coordinates found
across employees, `priorityHierarchy` and the demand CSV.

Run the adapter with `--stats` for the current list.
