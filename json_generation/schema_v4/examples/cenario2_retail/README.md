# cenario2_retail — retail store, January 2026

Adapted from the SISQUAL bundle at
`IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2/`
(generated 2026-09-17). The raw drop is untouched; this is its canonical form, with
a worked result alongside it.

It is the **only** shipped example. Sisqual's other September scenario, Cenário 1,
fails three independent ways and is kept as raw provenance only — see
[docs/next_meeting.md](../../docs/next_meeting.md) item 21.

| | |
|---|---|
| Workers | 15 |
| Horizon | 2026-01-01 .. 2026-01-31 (31 days, all open) |
| Contracts | 6 — `PT_10` `PT_12` `PT_20` `PT_25` `PT_35` `PT_40` (240–480 min/day) |
| Dimensions | `Team/T1`, `Responsibility/A`, `Responsibility/C`, `Responsibility/G` |
| Demand | 313 rows, all on the **periods** grain; days and shifts are empty |
| Grid | 30 minutes |
| Calendar | one holiday, 2026-01-01 (New Year's Day), `hasEve: false` |
| Catalogue | `schedules_without_meal.csv`, 1,277 codes |
| Result | `result.json` — 465 employee-days, with `result_schedules.csv` beside it |

```bash
cd ../..                                                          # schema_v4/
PYTHONPATH=src python3 -m schema_v4.validator examples/cenario2_retail -v
```

Both documents validate with no errors. Regenerate the whole package:

```bash
PYTHONPATH=src python3 -m schema_v4.sisqual_adapt \
  "IntegracaoUA_SISQUAL/JSON/20260917_JSON_Cenarios_GeradoSisqual/Cenário_2" \
  -o examples/cenario2_retail \
  --schedules reference/schedules/schedules_without_meal.csv --stats
PYTHONPATH=src python3 reference/build_example_result.py
```

## ⚠ `result.json` is a constructed artifact, not solver output

**No v4.0 solver exists yet.** `reference/build_example_result.py` assigns every
worker-day a shift by a fixed, stated rule — nearest duration first, then best
overlap with that day's demand — so that the result form and its sidecar have a
realistic instance to be validated against. It is a fixture, not a schedule anyone
should work.

Two of its choices are substitutions rather than fits, and both are recorded in the
file's own `_comment_substitutions` block:

| contract | needs | assigned | why |
|---|---|---|---|
| `PT_20`, `PT_12` | 240 min | exact fit | 50 codes available on the grid |
| `PT_25`, `PT_10` | 300 min | exact fit | 49 codes available |
| `PT_35` | 420 min | `300000` `10:00-16:30`, **390 min** | **no 420-minute code exists**; 21 days are 30 min short |
| `PT_40` | 480 min | `1014` `08:00-16:00` | right length, but opens 30 min before demand does — 66 days |

Both come from the same cause: the catalogue we hold is the *without-meal* one, and
its usable band stops at six hours. That is
[next_meeting.md](../../docs/next_meeting.md) item 5 and
[FUTURE.md](../../docs/FUTURE.md) §2.

## What it demonstrates

**Coverage on a two-dimensional coordinate.** Every demand row names a
`(tableName, tableValue)` pair rather than v3.0's single competency code, and the
same employee holds several at once — `Team/T1` plus three `Responsibility` floors.
The two dimensions overlap in time deliberately: a worker satisfies a Team row and a
Responsibility row in the same hour.

**Windows are inline, not named.** There is no work-period catalogue. Each row
carries its own `start`/`end`, and this bundle uses 25 distinct windows. `Team/T1`
rows tile each day contiguously while `Responsibility` rows are sparse.

**A result and its sidecar.** `result.json` names nine distinct `ScheduleCode`s;
`result_schedules.csv` defines exactly those nine. The validator checks both
directions, and checks each definition against the problem's own catalogue — a
solver may only use shifts the problem offers.

**`priorityHierarchy` carries generation settings, not just an order.** Four ranks,
each with `maxAlarmTableType`, `generationSequenceType` and an ability-level range —
a nine-field projection of SISQUAL's ~40-field `InpGenerationRules`.

**Labour law arrives as data.** `constraints.hard[0]` is a `RosterLegislation` entry
carrying `MaxConsecutiveWorkDays: 5`, `MaxConsecutiveWorkDaysInWeek: 5` and
`MinDistanceBetweenShiftsInMinutes: 660`. v3.0 had cut this block entirely; the
validator now acts on the first two.

## The warnings it raises, and why each is expected

- **Three employees hold the same competency at two levels.** `20067009`,
  `20054956` and `20062688` each hold their four coordinates twice over the same
  dates, at different levels, which leaves their competence level ambiguous. Real
  SISQUAL output, not a transcription error — item 20.
- **914 catalogue codes are off the 30-minute grid.** The catalogue is built on a
  15-minute grid; the bundle declares 30 — item 7.
- **`NOT` is declared but never used.** Harmless; the palette is wider than the data.
- **21 result days are 390 min against a 420-min contract.** The `PT_35`
  substitution above.

## Contracts are under-specified, and this bundle shows it

`PT_10` and `PT_25` are byte-identical in the schema (`workMinutesPerDay: 300`), as
are `PT_12` and `PT_20` (`240`). What separates them is 2 days a week versus 5 — and
that lives nowhere in the JSON, only in the pre-filled day-off pattern of
`schedule_input.csv`. The hours do add up here, but nothing requires them to.
[FUTURE.md](../../docs/FUTURE.md) §1 and
[next_meeting.md](../../docs/next_meeting.md) item 6.

## What the adapter changed

Nineteen distinct fixes: `contractAssigments` → `contractAssignments` (×15),
`priorityHierachy` → `priorityHierarchy`, `inpUAHolidaysCollection` → `holidays`,
`Equipa` → `Team` (×18) and `Piso` → `Responsibility` (×54), three capitalised enums
lowercased, fifteen `"9999-12-31"` sentinels turned into `null`, a UTF-8 BOM and
CRLF stripped from four CSVs, and `demand.dimensions[]` synthesised from the four
coordinates found across employees, `priorityHierarchy` and the demand CSV.

Run the adapter with `--stats` for the current list.
