# cenario2_retail — retail store, January 2026

The bundle SISQUAL generated on 2026-09-17 (`reference/IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2/`), corrected to v4.0, with a worked result beside it. The raw drop is untouched.

It is the **only** shipped example. Sisqual's other September scenario, Cenário 1, fails three independent ways and is kept as raw provenance only — see [next_meeting.md](../../next_meeting.md) item 21 ("the scenario we had to drop").

| | |
|---|---|
| Workers | 15 |
| Horizon | 2026-01-01 .. 2026-01-31 (31 days, all open) |
| Contracts | 6 — `PT_10` `PT_12` `PT_20` `PT_25` `PT_35` `PT_40` (240–480 min/day) |
| Dimensions | `Team/T1`, `Responsibility/A`, `Responsibility/C`, `Responsibility/G` |
| Demand | 313 rows, all on the **periods** grain; days and shifts are empty |
| Grid | 30 minutes |
| Menu | `schedules.csv` — 19 shifts covering all four contract lengths, plus 3 rest sentinels |
| Result | `result.json` — 465 employee-days, with `result_schedules.csv` beside it |

```bash
cd ../..                                    # schema_v4/
make validate DIR=examples/cenario2_retail ARGS=-v
```

Both documents validate with no errors.

## ⚠ `result.json` is a constructed artifact, not solver output

**No v4.0 solver exists yet.** `make result` runs `src/schema_v4/build_example_result.py`, which assigns every worker-day a shift by a fixed, stated rule — nearest duration first, then best overlap with that day's demand — so that the result form and its sidecar have a realistic instance to be validated against. It is a fixture, not a schedule anyone should work.

It does, however, approximate nothing: `_comment_substitutions` reads *"none — every worked day got a shift of exactly the contracted length"*, because the menu is ours to write and carries all four lengths.

## What it demonstrates

**Coverage on a two-dimensional coordinate.** Every demand row names a `(tableName, tableValue)` pair rather than v3.0's single competency code, and the same employee holds several at once — `Team/T1` plus three `Responsibility` floors. The two dimensions overlap in time deliberately: a worker satisfies a Team row and a Responsibility row in the same hour.

**Windows are inline, not named.** There is no work-period catalogue. Each row carries its own `start`/`end`, and this bundle uses 25 distinct windows. `Team/T1` rows tile each day contiguously while `Responsibility` rows are sparse.

**The menu is authored, not inherited.** `schedules.csv` defines 19 shifts at half-hourly starts inside the 08:30–22:00 demand window. A code means a grouping of hours and nothing else, so the numbering is arbitrary — `9001` is `09:00-13:00` because that row says so. Codes `1`, `3` and `4` keep WFM's rest semantics.

**A result and its sidecar.** `result.json` names 11 distinct codes; `result_schedules.csv` defines exactly those 11 and no more. The validator checks both directions, and checks each definition against the menu — a result may only use shifts the problem offers.

**`priorityHierarchy` carries generation settings, not just an order.** Four ranks, each with `maxAlarmTableType`, `generationSequenceType` and an ability-level range — a nine-field projection of SISQUAL's ~40-field `InpGenerationRules`.

**Labour law arrives as data.** `constraints.hard[0]` is a `RosterLegislation` entry carrying `MaxConsecutiveWorkDays: 5`, `MaxConsecutiveWorkDaysInWeek: 5` and `MinDistanceBetweenShiftsInMinutes: 660`. v3.0 had cut this block entirely; the validator now acts on the first two.

## The warnings it raises, and why each is expected

- **Three employees hold the same competency at two levels.** `20067009`, `20054956` and `20062688` each hold their four coordinates twice over the same dates, at different levels, which leaves their competence level ambiguous. Real SISQUAL output, not a transcription error — agenda item 18 ("the same competency twice").
- **`NOT` is declared but never used.** Harmless; the palette is wider than the data.

The result raises none.

## Contracts are under-specified, and this bundle shows it

`PT_10` and `PT_25` are byte-identical in the schema (`workMinutesPerDay: 300`), as are `PT_12` and `PT_20` (`240`). What separates them is 2 days a week versus 5 — and that lives nowhere in the JSON, only in the pre-filled day-off pattern of `schedule_input.csv`. The hours do add up here, but nothing requires them to. [FUTURE.md](../../docs/FUTURE.md) §1 and [next_meeting.md](../../next_meeting.md) item 7 ("Two contracts can be identical").

## Maintaining it

`problem.json` and the four CSVs are **hand-maintained**. v4.0 ships no converter from Sisqual's export, so there is no regeneration path for them — the corrections listed in [next_meeting.md](../../next_meeting.md) under *Naming and format* were applied once, and the file is now the artifact. Only `result.json` and `result_schedules.csv` are generated, by `make result`.
